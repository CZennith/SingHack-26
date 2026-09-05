# Evidence packet v1

## Purpose

An evidence packet is a deterministic, validated review envelope for an RM. Version 1.0.0 supports
only `exposure_change_review`. It assembles a validated client snapshot context, an existing
`exposure_changes` calculator result, supporting evidence, warnings, assumptions, and provenance.
It does not calculate new financial values, interpret events or notes, call an LLM, or make
recommendations.

The packet is intended to be reviewed by an RM before any future interpretation step. Source data
remains authoritative and recommendations are explicitly prohibited.

## Relationship to inputs

The snapshot supplies the client identity, snapshot dates, selected client context, and data-quality
flags. The packet builder validates it with `validate_snapshot()` and does not copy the full client,
portfolio, holdings, notes, events, or database record.

Calculator inputs are validated through the existing `validate_result()` contract. Only results
whose `calculator_name` is `exposure_changes` are supported. The builder copies facts, findings,
evidence, warnings, and assumptions; it never recreates or recalculates exposure changes.

## Structure and privacy

The top-level envelope contains `packet_metadata`, `client_context`, `facts`, `findings`, `evidence`,
`warnings`, `assumptions`, and `governance`. Metadata preserves packet schema/version independently
from snapshot and calculator versions. All dates are ISO strings and all values are JSON-compatible.

`client_context` is deliberately minimized to `client_id`, `base_currency`, `risk_profile`,
`risk_tolerance_score`, `investment_horizon_years`, `liquidity_needs`, `objectives`, and
`life_stage`. Objectives are copied exactly as stored. Client name, age, gender, nationality, tax
domicile, source of wealth, PEP status, and full RM identity are excluded by default.

The governance fields are always:

```json
{
  "requires_rm_review": true,
  "recommendations_allowed": false,
  "llm_interpretation_allowed": true,
  "source_data_is_authoritative": true
}
```

## Provenance and deduplication

Facts, findings, evidence, warnings, and assumptions retain source calculator and version where
applicable. IDs are deterministically namespaced, for example `exposure_changes:F-001` and
`exposure_changes:E-001`. Finding fact/evidence references and fact evidence references are updated
with the same mapping.

Evidence must contain the packet client in `source_keys.client_id`. It is deduplicated only when
`source_calculator`, `source_table`, `source_keys`, `field`, `value`, and `source_date` all match.
A different source key or date is retained. Snapshot quality flags are preserved as
`snapshot:W-####` warnings with their source references.

## Warnings and assumptions

Snapshot and calculator warnings are retained without lowering their severity. Assembly warnings
identify missing calculator results and omitted context. With no exposure-change result, the packet
is explicitly `partial` and contains `missing_calculator_result`; it is not presented as complete.

Calculator assumptions are copied. The builder adds only the assembly assumption that v1 includes
exposure-change results and does not provide liquidity, event, suitability, performance, or
recommendation analysis.

## API, CLI, and selection policy

```python
from src.pipeline import build_evidence_packet, dumps_packet, loads_packet

packet = build_evidence_packet(snapshot, [exposure_change_result])
validated = loads_packet(dumps_packet(packet))
```

The all-client helper accepts `{client_id: snapshot}` and `{client_id: [result, ...]}` mappings,
sorts client IDs, and fails with a client-specific error if a client is inconsistent.

```bash
python3 -m src.pipeline.evidence_packet \
  --snapshot outputs/snapshots/CL-0001/as_of_2026-08-26__period_2026-01-01_to_2026-08-26.json \
  --calculator-result outputs/exposure_changes/CL-0001/2026-06-30_to_2026-08-26.json \
  --packet-type exposure_change_review \
  --output-root outputs
```

This writes the canonical path
`outputs/evidence_packets/CL-0001/exposure_change_review__2026-06-30_to_2026-08-26.json`.
Use `--output exact/path.json` for an exact destination. Omit both output options to print valid
JSON to stdout, and use `--overwrite` only to intentionally replace an existing generated packet.
The CLI only reads its inputs and writes the packet output; it never opens or modifies DuckDB.

Version 1.0.0 includes selected context, direct exposure-change facts/findings/evidence, warnings,
assumptions, and provenance. It excludes raw holdings, raw transactions, all RM notes, market
events, full client records, recommendations, event relevance, liquidity, suitability, and LLM
prompts. Future packet types such as `liquidity_review`, `market_event_review`, and
`client_review_preparation` must be added explicitly.

Invalid packets include mismatched clients or dates, unsupported types, invalid dates/statuses,
duplicate IDs, missing references, evidence without a traceable client key, recommendation fields,
and blocked packets without warnings.
