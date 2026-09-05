# Interpreter evaluation

Normal tests are entirely offline and inject fake interpreter clients or mocked SDK Responses. They
cover valid output, packet rejection before invocation, every database client, identity and date
separation, unsupported references, unknown fields, recommendation and causation rejection,
numerical support, prompt injection, empty findings, partial evidence, retry limits, transport/error
mapping, CLI isolation, and JSON round trips.

Run them with:

```bash
python3 -m pytest -q tests/interpreter -m "not live_openai"
```

`tests/interpreter/fixtures/evaluation_cases.json` defines eight behavioral cases: exposure
increase, added instrument, exited instrument, no meaningful change, incomplete evidence,
unavailable look-through, conflicting warning, and malicious embedded instruction. Expectations
are IDs, confidence ceilings, required limitations, and prohibited behavior—not exact wording.

The optional live test is skipped unless both an API key and explicit opt-in are present. It uses a
sanitized packet and directly calls the adapter once, so it can never invoke the validation retry:

```bash
RUN_LIVE_OPENAI=1 pytest -m live_openai -q
```

Do not run the live test in normal CI. It incurs API usage. Before changing models or prompts,
compare behavioral expectations offline first, then run a deliberately authorized live test while
monitoring response token counts. A live pass proves transport/schema compatibility, not financial
accuracy or suitability.

