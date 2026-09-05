# Interpreter prompt policy

The developer prompt is stored in `src/interpreter/prompts.py` with name `exposure_interpreter` and
version `1.0.0`. The JSON output schema is supplied through Structured Outputs and is deliberately
not duplicated in prose.

The policy requires the model to use only packet evidence, treat all packet strings as untrusted,
avoid new calculations and external facts, avoid event causation, cite existing fact/evidence IDs,
state uncertainty, and phrase questions as review questions. Buying, selling, switching, hedging,
rebalancing, borrowing, mandate changes, and suitability conclusions are prohibited. Expected
private-market valuation lag must not be called a data error unless the packet does so explicitly.

The packet is serialized deterministically and sent as one untrusted data input. A corrective retry
adds only concise validation feedback to the developer instructions; it does not echo the packet or
provider exception. Never interpolate packet text into the developer prompt.

To update the prompt safely:

1. Keep the existing evidence and recommendation boundaries.
2. Add injection, reference, numerical, and recommendation tests for the change.
3. Update behavioral evaluation expectations instead of exact prose snapshots.
4. Increment `PROMPT_VERSION` and document the change.
5. Run all offline tests before any explicitly authorized live evaluation.

