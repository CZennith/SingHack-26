"""Provider-independent interpreter orchestration and optional CLI."""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path
from typing import Any

from ..output_files import OutputWriteError, atomic_write_json
from ..output_paths import OutputPathError, interpretation_output_path
from .openai_client import OpenAIInterpreterClient
from .validation import (
    InterpretationRetryExhausted,
    InterpretationValidationError,
    InterpreterError,
    validate_interpretation,
    validate_interpreter_packet,
)


def _call_client(llm_client: Any, packet: dict, validation_feedback: str | None) -> dict:
    method = llm_client.interpret
    if validation_feedback is not None:
        try:
            supports_feedback = "validation_feedback" in inspect.signature(method).parameters
        except (TypeError, ValueError):
            supports_feedback = False
        if supports_feedback:
            return method(packet, validation_feedback=validation_feedback)
    return method(packet)


def interpret_exposure_packet(packet: dict, llm_client) -> dict:
    """Validate and interpret one exposure-change evidence packet."""
    normalized_packet = validate_interpreter_packet(packet)
    feedback: str | None = None
    last_error: InterpretationValidationError | None = None
    for _attempt in range(2):
        try:
            candidate = _call_client(llm_client, normalized_packet, feedback)
            return validate_interpretation(candidate, normalized_packet).model_dump(mode="json")
        except InterpretationValidationError as exc:
            last_error = exc
            feedback = str(exc)[:500]
    raise InterpretationRetryExhausted(
        f"interpretation remained invalid after one retry: {last_error}"
    ) from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Interpret a validated exposure-change evidence packet")
    parser.add_argument("--packet", required=True, help="Validated evidence-packet JSON")
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--output", help="Exact output JSON path")
    destination.add_argument("--output-root", help="Root under which the canonical output path is created")
    parser.add_argument("--overwrite", action="store_true", help="Intentionally replace an existing generated output")
    args = parser.parse_args(argv)
    if args.overwrite and not (args.output or args.output_root):
        print("Interpretation failed: --overwrite requires --output or --output-root", file=sys.stderr)
        return 1

    try:
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
        validate_interpreter_packet(packet)
        client = OpenAIInterpreterClient.from_environment()
        result = interpret_exposure_packet(packet, client)
        rendered = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output_root:
            output_root = Path(args.output_root)
            metadata = result["interpretation_metadata"]
            output = interpretation_output_path(
                output_root,
                metadata["client_id"],
                metadata["packet_type"],
                metadata["comparison_date"],
                metadata["as_of_date"],
            )
        elif args.output:
            output = Path(args.output)
            output_root = output.parent
        else:
            print(rendered, end="")
            return 0
        metadata = result["interpretation_metadata"]
        written = atomic_write_json(
            output,
            rendered,
            output_root=output_root,
            overwrite=args.overwrite,
            artifact_description=(
                f"{metadata['packet_type']} interpretation for client {metadata['client_id']}, "
                f"dates {metadata['comparison_date']} to {metadata['as_of_date']}"
            ),
        )
        print(written)
    except (InterpreterError, OutputPathError, OutputWriteError, OSError, json.JSONDecodeError) as exc:
        print(f"Interpretation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
