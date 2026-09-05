"""LLM-owned copy for the client detail page.

Each generator represents one independently configurable LLM call. The
deterministic client-data service is the only permitted source of model input;
the FastAPI response models validate the returned dictionaries before they are
sent to the frontend.
"""

import json
import logging
import os
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from collections.abc import Iterator
from datetime import datetime
from functools import lru_cache
from typing import Any
from pathlib import Path
from zoneinfo import ZoneInfo

if __package__:
    from .client_data_service import build_client_llm_context
else:  # Support ``uvicorn main:app`` from inside ``backend``.
    from client_data_service import build_client_llm_context

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

load_dotenv(Path(__file__).with_name(".env"))

logger = logging.getLogger(__name__)

# Production configuration selected from the advisory benchmark.
MODEL = "gpt-5.6-terra"
REASONING = {"effort": "none"}


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """Create the client only when an insight request needs it.

    Deferring construction keeps health checks and static data endpoints usable
    when a deployment is missing its runtime secret.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured for insight generation.")
    return OpenAI()


def generated_at() -> str:
    return datetime.now(ZoneInfo("Asia/Singapore")).strftime("%Y-%m-%d %H:%M SGT")


def generate_profile_summary(context: dict[str, Any]) -> dict:
    """Call the profile-summary LLM with factual client context only.

    This optional section summarises the client's stated objectives and current
    situation. It must not infer personal facts missing from ``context``.
    """
    instructions = (
        """
        You are an assistant for a private-banking Relationship Manager.

Write a concise, factual client context summary based only on the supplied JSON.

Requirements:
- Use only information explicitly present in the JSON.
- Summarize the RM notes.
- Highlight any key points for the RM to take note. Flag any contradictions or tensions between stated objectives and current situation or behavior.
- Do not calculate figures or introduce recommendations, market views, products, securities, or events.
- Do not mention missing fields or describe your process.
- Use professional, neutral language suitable for an internal RM briefing.
- Write one short paragraph. 
- Be concise. Keep the response below 75 words.
        """
    )
    output = get_openai_client().responses.create(
        model=MODEL,
        reasoning=REASONING,

        instructions=instructions,
        input=json.dumps(context["profile_summary"], ensure_ascii=False, separators=(",", ":")),
    )

    logger.info("Generated client profile summary (%s tokens).", output.usage.total_tokens)

    return {
        "generatedAt": generated_at(),
        "title": "Client context summary",
        "summary": (
            output.output_text
            if output.output_text
            else "No summary generated. Please check the model response."
        ),
    }


def generate_portfolio_explanation(context: dict[str, Any]) -> dict:
    """Call the portfolio-explanation LLM with sourced, dated facts.

    This is retrospective attribution only: explain portfolio movement and its
    supported causes, without recommending trades.
    """
    _ = context

    class ExplanationPoint(BaseModel):
        title: str
        description: str

    class PortfolioExplanation(BaseModel):
        overview: str
        whatMovedAndWhy: list[ExplanationPoint]
        whatToWatch: list[ExplanationPoint]

    response = get_openai_client().responses.parse(
        model=MODEL,
        reasoning=REASONING,
        instructions="""
    Explain the portfolio in clear, client-friendly language.

    Use only the supplied input. For events in 2026, event_log_2026 is
    authoritative and overrides your prior knowledge. Connect an event to a
    holding only when the event transmission channel and the holding's exposure
    metadata support that link.

    Do not present correlation as certainty. If quantity_changed is true, do not
    attribute the full value change to market performance. Do not recommend trades.

    Return 1–3 titled points for whatMovedAndWhy and 1–3 titled points for
    whatToWatch. Each point must have a short 1-4 word title and a client-friendly
    description. Each section should be no more than 100 words.
    """,
        input=json.dumps(
            context["portfolio_explanation"],
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        text_format=PortfolioExplanation,
    )
    output = response.output_parsed
    if output is None:
        raise RuntimeError("The portfolio explanation model returned no structured output.")
    logger.info("Generated portfolio explanation (%s tokens).", response.usage.total_tokens)
    return {
        "generatedAt": generated_at(),
        "title": "Intelligent Portfolio Explanation",
        "overview": (
            output.overview
            if output.overview
            else "No overview generated. Please check the model response."
        ),
        # ``ExplanationPoint`` is local to this OpenAI parse schema. Convert
        # it to plain dictionaries so FastAPI can validate it as its public
        # ``StrategicPoint`` response model.
        "whatMovedAndWhy": [point.model_dump() for point in output.whatMovedAndWhy],
        "whatToWatch": [point.model_dump() for point in output.whatToWatch],
    }


def generate_proactive_advice(context: dict[str, Any]) -> dict:
    """Call the advisory LLM for RM-reviewed risks and opportunities.

    Advice must be traceable to deterministic inputs and framed as a
    discussion item for Relationship Manager review.
    """
    class AdvicePoint(BaseModel):
        title: str
        description: str

    class ProactiveAdvice(BaseModel):
        risks: list[AdvicePoint]
        opportunities: list[AdvicePoint]

    def records(frame) -> list[dict]:
        """Convert repository data frames to JSON-safe source records."""
        return json.loads(frame.to_json(orient="records", date_format="iso"))

    advisory_context = {
        "client_description": context["profile_summary"]["client_description"],
        "rm_notes": context["profile_summary"]["rm_notes"],
        "portfolio_snapshot": context["dossier"],
        "portfolio_evidence": context["portfolio_explanation"],
        "facilities": records(context["facilities"]),
        "planned_cash_needs": records(context["cash_needs"]),
        "outstanding_commitments": records(context["commitments"]),
        "transactions": records(context["transactions"]),
    }

    response = get_openai_client().responses.parse(
        model=MODEL,
        reasoning=REASONING,

        instructions="""
You are an assistant for a private-banking Relationship Manager. Identify the
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
        """,
        input=json.dumps(advisory_context, ensure_ascii=False, separators=(",", ":")),
        text_format=ProactiveAdvice,
    )

    output = response.output_parsed
    if output is None:
        raise RuntimeError("The advisory model returned no structured output.")
    logger.info("Generated proactive advice (%s tokens).", response.usage.total_tokens)

    return {
        "generatedAt": generated_at(),
        "risks": [point.model_dump() for point in output.risks],
        "opportunities": [point.model_dump() for point in output.opportunities],
    }


def build_client_insights(client_id: str) -> dict:
    """Build context once, then generate the independent sections concurrently.

    Each generator receives the same immutable, deterministic context and does
    not consume another generator's output. A small, fixed pool prevents one
    client request from creating unbounded concurrent model calls.
    """
    context = build_client_llm_context(client_id)

    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="client-insight") as executor:
        profile_summary = executor.submit(generate_profile_summary, context)
        portfolio_explanation = executor.submit(generate_portfolio_explanation, context)
        advisory = executor.submit(generate_proactive_advice, context)

        # Calling result in a stable order preserves the public response shape
        # and propagates a generation failure as the endpoint's normal error.
        return {
            "profileSummary": profile_summary.result(),
            "portfolioExplanation": portfolio_explanation.result(),
            "advisory": advisory.result(),
        }


def stream_client_insight_sections(client_id: str) -> Iterator[tuple[str, dict]]:
    """Yield each independently generated insight as soon as it is complete.

    This preserves the same bounded concurrency as the aggregate endpoint but
    enables an SSE transport to update the UI one validated section at a time.
    """
    context = build_client_llm_context(client_id)
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="client-insight") as executor:
        futures = {
            executor.submit(generate_profile_summary, context): "profileSummary",
            executor.submit(generate_portfolio_explanation, context): "portfolioExplanation",
            executor.submit(generate_proactive_advice, context): "advisory",
        }
        while futures:
            completed, _ = wait(futures, timeout=15, return_when=FIRST_COMPLETED)
            if not completed:
                # Keeps intermediaries from timing out an otherwise healthy
                # generation request. The SSE route emits this as a comment.
                yield "heartbeat", {}
                continue
            for future in completed:
                section = futures.pop(future)
                yield section, future.result()
