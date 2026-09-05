# Direct exposure base

`build_exposure_base(snapshot)` is a pure aggregation over one validated client snapshot. It does
not query DuckDB, write data, interpret holdings, or apply a materiality policy.

## Input and output

The input is the existing snapshot dictionary validated by `validate_snapshot()`. Holdings must be
at the snapshot's `snapshot_metadata.as_of_date`; other snapshot sections are retained as input
context but are not used for exposure arithmetic.

The output contains `exposure_metadata`, a `client_total`, and deterministic lists grouped by
portfolio, asset class, sub-asset class, sector, region, currency, and instrument. Each group has
`dimension`, `key`, `scope_level`, `portfolio_id`, `instrument_id`, `instrument_name`,
`market_value_usd`, `weight_pct`, and `holding_count`. Instrument groups also retain
`underlying_reference` and `look_through_included: false`.

## Aggregation semantics

- All client and portfolio totals use the holding field `market_value_usd`.
- Client weights are `group USD value / client USD total × 100`.
- Portfolio-level weights use each portfolio's own USD total; portfolio weights are not summed to
  create a client weight.
- Identical instruments are consolidated only in the client-level `by_instrument` list. Portfolio
  groups retain their portfolio IDs, so portfolios remain distinguishable.
- `market_value_base` is never summed across portfolios.
- A zero client total produces zero weights rather than division by zero.
- The numerical comparison tolerance is `0.00000001` internally. It is a precision tolerance, not
  a materiality or recommendation threshold.

## Nulls and look-through

Null dimension values remain `key: null` and stay in their aggregation group. A warning identifies
the missing dimension. A client with no as-of holdings receives a valid zero-exposure result and an
informational warning. Optional instrument metadata remains null when null in the snapshot.

`underlying_reference` is carried as metadata only. It is never parsed, expanded, or added to direct
totals, so structured products are counted exactly once.

## Example

```python
from src.calculators.exposure_base import build_exposure_base

exposure = build_exposure_base(validated_snapshot)
print(exposure["client_total"])
# {"market_value_usd": 46571821.48, "holding_count": 11, "portfolio_count": 2}
```

Known limitations: this base is direct exposure only, does not perform currency conversion, and
does not calculate performance, liquidity, suitability, risk, event effects, or recommendations.
