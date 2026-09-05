# Evidence-bound exposure interpreter

The interpreter explains an already validated `exposure_change_review` evidence packet for a
Relationship Manager. It is the final, narrow layer after DuckDB, snapshots, calculators, result
validation, and packet construction. `interpret_exposure_packet(packet, llm_client)` validates the
packet before invoking the injected client and validates the structured response against that same
packet before returning a dictionary.

The interpreter explains existing evidence. It does not calculate exposure. It does not retrieve
market information. It does not determine suitability. It does not make recommendations. All
outputs require RM review.

## OpenAI adapter

`OpenAIInterpreterClient` is the server-side adapter. It uses the official Python SDK's Responses
API and Pydantic Structured Outputs. Requests set `store=False`, provide no tools, use foreground
execution, and send only the versioned interpreter instructions and serialized validated packet.
The default model is `gpt-5.6-luna`; there is no fallback.

Configuration is read only from the backend environment:

```text
OPENAI_API_KEY             required
OPENAI_MODEL               default: gpt-5.6-luna
OPENAI_REASONING_EFFORT    default: low
OPENAI_TIMEOUT_SECONDS     default: 30
```

Change models by setting `OPENAI_MODEL`. An unavailable model raises a typed error and is never
silently replaced. The request is capped at 4,000 output tokens, uses low reasoning by default,
and permits at most one retry for invalid structured or post-validation output. Authentication,
permission, model access, rate-limit, timeout, connection, refusal, and incomplete-response errors
are not retried by the interpreter.

Official references: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create),
and [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data). `store=False`
disables response application-state storage for this request; normal platform abuse-monitoring and
the organization's configured retention controls still apply.

## CLI

```bash
python3 -m src.interpreter.interpreter \
  --packet outputs/evidence_packets/CL-0001/exposure_change_review__2026-06-30_to_2026-08-26.json \
  --output-root outputs
```

The canonical destination is
`outputs/interpretations/{client_id}/exposure_change_review__{comparison_date}_to_{as_of_date}.json`.
Use `--output` for an exact path or omit both destination options to print JSON to stdout. Existing
files require `--overwrite`; the shared protected atomic writer prevents replacement of source,
data, database, and test-fixture files. The CLI reports the written path.

## Security and privacy

- The API key is read only from `OPENAI_API_KEY`; it is never logged, serialized, returned to the
  frontend, or present in React code.
- Packet strings are explicitly marked as untrusted data. Embedded instructions cannot override
  the developer prompt.
- No web search, file search, code interpreter, function tools, or external retrieval is enabled.
- Errors contain a stable category, not the API exception body or complete packet.
- Response IDs and token counts are recorded when available. Hidden reasoning is never requested
  or exposed.

## Known limitations

The interpreter can explain only the packet it receives. It cannot fill missing look-through,
valuation, comparison, liquidity, event, suitability, or performance data. Its deterministic
post-validation conservatively rejects trade language, causal claims, and literal numbers not found
in cited facts/evidence; it is not a substitute for RM review or broader compliance controls.

