# Exposure interpretation output contract

`src/interpreter/models.py` is the source of truth for schema version `1.0.0`. Every Pydantic model
uses strict validation and forbids unexpected fields. The top-level envelope contains:

```text
interpretation_metadata
executive_summary
observations
questions_for_rm
limitations
warnings
requires_rm_review
```

Metadata preserves packet type, packet schema version, client ID, as-of date, and comparison date.
It also records model and prompt provenance. `openai_response_id` and input/output/total token counts
are nullable because fake clients and some failed provider responses do not expose them. There is no
generation timestamp, preserving stable semantic fixture comparisons.

Every observation has a unique ID, title, explanation, confidence, uncertainty, and non-empty fact
and evidence ID arrays. IDs must resolve in the source packet. Literal numerical claims in the title
or explanation must equal a value in the cited facts or evidence. Low- and medium-confidence
observations must state uncertainty. Packets without findings cannot produce observations.

Every RM question has a unique ID and may reference only observation IDs in the same output.
Questions and all other model-authored fields are checked for recommendation, trade, mandate, and
suitability language. Outputs always set `requires_rm_review` to `true`.

Post-response checks additionally require exact packet identity/dates/type/version, valid reference
relationships, no unsupported causation, limitations for partial or blocked packets, and JSON
round-trip serialization. A response that only matches the JSON Schema but fails these checks is
not returned as successful.

To change the contract, update the Pydantic models and post-validator together, add migration and
compatibility tests, update this document, and bump `INTERPRETATION_SCHEMA_VERSION`. Do not reuse
the packet schema version as the interpretation schema version.

