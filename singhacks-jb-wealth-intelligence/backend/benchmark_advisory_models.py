"""Benchmark model/reasoning choices for the Risks & Opportunities call.

Example (from `backend/`):

    python benchmark_advisory_models.py --client-ids CL-0001 CL-0002 CL-0003

Put ``OPENAI_API_KEY`` in ``backend/.env`` (which is gitignored), then run this
file directly. The run is sequential so every recorded latency belongs to one
model call. A checkpoint JSON file is updated after every successful call, and
includes the complete raw and structured output plus reviewer fields.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

from client_data_service import build_client_llm_context


# Five clients x ten configurations is 50 API calls. Pass --client-ids with
# three IDs for a smaller first pass.
DEFAULT_CLIENT_IDS = ("CL-0001", "CL-0002", "CL-0003", "CL-0004", "CL-0005")
EXPERIMENTS = (
    ("gpt-5.6-luna", "low"),
    ("gpt-5.6-luna", "medium"),
    ("gpt-5.6-terra", "none"),
    ("gpt-5.6-terra", "low"),
    ("gpt-5.6-terra", "medium"),
    ("gpt-5.6-terra", "high"),
    ("gpt-5.6-sol", "none"),
    ("gpt-5.6-sol", "low"),
    ("gpt-5.6-sol", "medium"),
    ("gpt-5.6-sol", "high"),
)

# Keep this prefix byte-for-byte identical across every request to make the
# comparison fair and permit prompt-cache reuse for stable instructions.
INSTRUCTIONS = """You are an assistant for a private-banking Relationship Manager. Identify the
most material client-specific discussion points from the supplied JSON.

Use only supplied facts. RM notes are dated observations, not independently
verified facts. For events occurring in 2026, portfolio_evidence.event_log_2026
is authoritative and overrides your prior knowledge. Do not invent facts,
prices, events, exposures, or client preferences.

Return 1–3 risks and 1–3 opportunities. Each item needs a concise 1–4 word
title and a client-specific description of no more than 55 words. Risks should
describe a supported exposure, constraint, or unresolved issue. Opportunities
must be framed as an RM-reviewed planning discussion, never an instruction or
a promise of outcome. Do not recommend named securities or products.
"""

# Public list prices per million text tokens. Reasoning tokens are output tokens.
PRICES_PER_MILLION = {
    "gpt-5.6-luna": {"input": 0.20, "cached_input": 0.02, "output": 1.20},
    "gpt-5.6-terra": {"input": 2.00, "cached_input": 0.20, "output": 12.00},
    "gpt-5.6-sol": {"input": 4.00, "cached_input": 0.40, "output": 20.00},
}


class AdvicePoint(BaseModel):
    title: str
    description: str


class ProactiveAdvice(BaseModel):
    risks: list[AdvicePoint]
    opportunities: list[AdvicePoint]


def records(frame: Any) -> list[dict[str, Any]]:
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def advisory_input(context: dict[str, Any]) -> str:
    """Use the same data contract as llm_service.generate_proactive_advice."""
    payload = {
        "client_description": context["profile_summary"]["client_description"],
        "rm_notes": context["profile_summary"]["rm_notes"],
        "portfolio_snapshot": context["dossier"],
        "portfolio_evidence": context["portfolio_explanation"],
        "facilities": records(context["facilities"]),
        "planned_cash_needs": records(context["cash_needs"]),
        "outstanding_commitments": records(context["commitments"]),
        "transactions": records(context["transactions"]),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def usage_dict(response: Any) -> dict[str, int]:
    usage = response.usage
    input_details = getattr(usage, "input_tokens_details", None)
    output_details = getattr(usage, "output_tokens_details", None)
    return {
        "input_tokens": usage.input_tokens or 0,
        "cached_input_tokens": getattr(input_details, "cached_tokens", 0) or 0,
        "output_tokens": usage.output_tokens or 0,
        "reasoning_tokens": getattr(output_details, "reasoning_tokens", 0) or 0,
        "total_tokens": usage.total_tokens or 0,
    }


def estimated_cost_usd(model: str, usage: dict[str, int]) -> float:
    prices = PRICES_PER_MILLION[model]
    uncached = usage["input_tokens"] - usage["cached_input_tokens"]
    return round(
        (uncached * prices["input"]
         + usage["cached_input_tokens"] * prices["cached_input"]
         + usage["output_tokens"] * prices["output"]) / 1_000_000,
        8,
    )


def run_one(client: OpenAI, client_id: str, model: str, effort: str) -> dict[str, Any]:
    context = build_client_llm_context(client_id)
    started = time.perf_counter()
    response = client.responses.parse(
        model=model,
        reasoning={"effort": effort},
        instructions=INSTRUCTIONS,
        input=advisory_input(context),
        text_format=ProactiveAdvice,
    )
    usage = usage_dict(response)
    return {
        "client_id": client_id,
        "client_name": context["client"]["client_name"],
        "model": model,
        "reasoning_effort": effort,
        "latency_seconds": round(time.perf_counter() - started, 3),
        "usage": usage,
        "estimated_text_cost_usd": estimated_cost_usd(model, usage),
        "response_id": response.id,
        "raw_output_text": response.output_text,
        "output": response.output_parsed.model_dump(),
        "review": {
            "key_risks_and_tensions_found": None,
            "manual_correction_needed": None,
            "reviewer_notes": "",
        },
    }


def summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["model"], row["reasoning_effort"]), []).append(row)
    return [
        {
            "model": model,
            "reasoning_effort": effort,
            "runs": len(group),
            "mean_latency_seconds": round(sum(r["latency_seconds"] for r in group) / len(group), 3),
            "mean_estimated_text_cost_usd": round(sum(r["estimated_text_cost_usd"] for r in group) / len(group), 8),
            "total_estimated_text_cost_usd": round(sum(r["estimated_text_cost_usd"] for r in group), 8),
        }
        for (model, effort), group in grouped.items()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-ids", nargs="+", default=list(DEFAULT_CLIENT_IDS))
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("benchmark_results"))
    args = parser.parse_args()
    load_dotenv(Path(__file__).with_name(".env"))
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("Add OPENAI_API_KEY=... to backend/.env before running this benchmark.")

    client = OpenAI()
    rows = []
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"advisory_model_benchmark_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"

    def save_checkpoint() -> None:
        result = {
            "purpose": "Compare advisory risk/opportunity generation across model and reasoning effort.",
            "completed_at_utc": datetime.now(UTC).isoformat(),
            "experiments": [{"model": model, "reasoning_effort": effort} for model, effort in EXPERIMENTS],
            "client_ids": args.client_ids,
            "completed_runs": len(rows),
            "planned_runs": len(EXPERIMENTS) * len(args.client_ids),
            "results": rows,
            "summary": summary(rows),
            "review_scale": {
                "key_risks_and_tensions_found": "Reviewer enters yes/no/partial.",
                "manual_correction_needed": "Reviewer enters none/minor/major.",
            },
        }
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for model, effort in EXPERIMENTS:
        for client_id in args.client_ids:
            print(f"Running {model} ({effort}) for {client_id}…", flush=True)
            rows.append(run_one(client, client_id, model, effort))
            save_checkpoint()
    print(f"Saved {output_path}")
    for item in summary(rows):
        print(item)


if __name__ == "__main__":
    main()
