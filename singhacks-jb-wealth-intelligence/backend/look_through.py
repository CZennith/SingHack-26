"""Look-through concentration analyzer.

This module implements Algorithm 4 from the design document.  It maps every
holding for a client through to its *effective* (post-look-through) asset class
and sector, aggregates by that effective key, compares against mandate limits,
and surfaces hidden concentrations where structured-product look-through
materially changes the picture.

Public API
----------
concentration_table(client_id, data, as_of) -> list[ConcentrationRow]
    Returns one ConcentrationRow per unique (asset_class, sector) combination.
    The hidden_concentration_discoveries are embedded in a parallel helper;
    callers that need them should call concentration_result() instead.

concentration_result(client_id, data, as_of) -> dict
    Returns {concentrations, hidden_concentration_discoveries, total_aum_usd}.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from typing import Any

import pandas as pd

if __package__:
    from .stress_types import ConcentrationRow
else:
    from stress_types import ConcentrationRow

AS_OF = "2026-08-26"

# When the gap between post- and pre-look-through pct exceeds this threshold
# (in percentage-point terms), we flag it as a hidden concentration.
HIDDEN_CONCENTRATION_GAP_PP = 5.0

# An exposure qualifies as ELEVATED when its post-look-through weight is
# between this fraction and 100% of the mandate limit.
ELEVATED_THRESHOLD_FRACTION = 0.80


# ---------------------------------------------------------------------------
# Internal helpers (same pattern as stress_test.py)
# ---------------------------------------------------------------------------

def _text(value: Any) -> str:
    return "" if pd.isna(value) else str(value).strip()


def _number(value: Any, default: float = 0.0) -> float:
    converted = pd.to_numeric(value, errors="coerce")
    return default if pd.isna(converted) else float(converted)


def _instrument_index(instruments: pd.DataFrame) -> dict[str, pd.Series]:
    """Return {instrument_id: row} for quick O(1) lookup."""
    return {
        _text(row["instrument_id"]): row
        for _, row in instruments.iterrows()
        if _text(row.get("instrument_id"))
    }


def _resolve_exposure(
    holding: pd.Series,
    instruments_by_id: dict[str, pd.Series],
) -> tuple[str, str, bool]:
    """Return (effective_asset_class, effective_sector, look_through_applied).

    The logic mirrors Algorithm 1 Step 1 in stress_test.py:
    - If the instrument has a non-empty underlying_reference, follow it.
    - Use the underlying's asset_class and sector.
    - Otherwise use the holding's own classification.
    """
    instrument = instruments_by_id.get(_text(holding.get("instrument_id")))
    underlying_ref = (
        _text(instrument.get("underlying_reference"))
        if instrument is not None
        else ""
    )
    underlying = instruments_by_id.get(underlying_ref) if underlying_ref else None
    if underlying is not None:
        return (
            _text(underlying.get("asset_class")),
            _text(underlying.get("sector")),
            True,
        )
    return (
        _text(holding.get("asset_class")),
        _text(holding.get("sector")),
        False,
    )


def _build_mandate_limits(
    client_id: str,
    portfolios: pd.DataFrame,
    mandates: pd.DataFrame,
) -> dict[str, float]:
    """Return {asset_class: max_single_position_pct} for the client's managed portfolios.

    We exclude Custody portfolios because the mandate guard (Task 6) also
    excludes them — Custody portfolios have no investable mandate.

    The mandate limit used is `max_single_position_pct` from mandates.csv,
    applied per asset class for portfolios where concentration_limit_applies = "Y"
    in instruments.csv (that filtering happens at the row level in the caller).

    Here we just return the per-asset-class cap so the caller can look it up.
    """
    client_portfolios = portfolios[
        portfolios["client_id"].eq(client_id)
        & ~portfolios["service_model"].str.contains("Custody", case=False, na=False)
    ]
    mandate_codes = set(client_portfolios["mandate_code"].dropna().astype(str))

    # Build {asset_class: min max_single_position_pct across relevant mandates}.
    # When a client has multiple mandate codes we use the most restrictive limit.
    limits: dict[str, list[float]] = defaultdict(list)
    for _, row in mandates.iterrows():
        code = _text(row.get("mandate_code"))
        if code in mandate_codes:
            ac = _text(row.get("asset_class"))
            cap = _number(row.get("max_single_position_pct"))
            if ac and cap:
                limits[ac].append(cap)

    return {ac: min(caps) for ac, caps in limits.items() if caps}


# ---------------------------------------------------------------------------
# Main public functions
# ---------------------------------------------------------------------------

def concentration_result(
    client_id: str,
    data: Mapping[str, pd.DataFrame],
    as_of: str = AS_OF,
) -> dict[str, Any]:
    """Full look-through concentration analysis.

    Returns
    -------
    dict with keys:
      concentrations                  list[ConcentrationRow]
      hidden_concentration_discoveries list[dict]
      total_aum_usd                   float
    """
    holdings_df = data["holdings"]
    instruments_df = data["instruments"]
    portfolios_df = data["portfolios"]
    mandates_df = data["mandates"]

    # -----------------------------------------------------------------------
    # STEP 1 — filter to client snapshot
    # -----------------------------------------------------------------------
    snapshot = holdings_df[
        holdings_df["client_id"].eq(client_id)
        & holdings_df["snapshot_date"].astype(str).eq(as_of)
    ]

    if snapshot.empty:
        return {
            "concentrations": [],
            "hidden_concentration_discoveries": [],
            "total_aum_usd": 0.0,
        }

    instruments_by_id = _instrument_index(instruments_df)
    total_aum = snapshot["market_value_usd"].apply(_number).sum()

    if total_aum == 0.0:
        return {
            "concentrations": [],
            "hidden_concentration_discoveries": [],
            "total_aum_usd": 0.0,
        }

    # -----------------------------------------------------------------------
    # STEP 2 — pre-look-through aggregation (using stated asset_class/sector)
    # -----------------------------------------------------------------------
    pre: dict[tuple[str, str], float] = defaultdict(float)
    for _, holding in snapshot.iterrows():
        key = (_text(holding.get("asset_class")), _text(holding.get("sector")))
        pre[key] += _number(holding.get("market_value_usd"))

    # -----------------------------------------------------------------------
    # STEP 3 — post-look-through aggregation (using effective asset_class/sector)
    # -----------------------------------------------------------------------
    # We also track which instruments have concentration_limit_applies = "Y"
    # so we know whether a mandate limit is relevant for that holding.
    post: dict[tuple[str, str], float] = defaultdict(float)
    concentration_limit_keys: set[tuple[str, str]] = set()

    for _, holding in snapshot.iterrows():
        eff_ac, eff_sector, looked_through = _resolve_exposure(holding, instruments_by_id)
        key = (eff_ac, eff_sector)
        value = _number(holding.get("market_value_usd"))
        post[key] += value

        # Check whether the instrument itself has concentration_limit_applies = "Y".
        # If it does, this (effective) exposure bucket should be checked against
        # the mandate's max_single_position_pct.
        instrument = instruments_by_id.get(_text(holding.get("instrument_id")))
        if instrument is not None:
            if _text(instrument.get("concentration_limit_applies")).upper() == "Y":
                concentration_limit_keys.add(key)

    # -----------------------------------------------------------------------
    # STEP 4 — mandate limits
    # -----------------------------------------------------------------------
    mandate_limits = _build_mandate_limits(client_id, portfolios_df, mandates_df)
    # mandate_limits is keyed by asset_class (e.g., "Equity" → 15.0)

    # -----------------------------------------------------------------------
    # STEP 5 — classify each (asset_class, sector) bucket
    # -----------------------------------------------------------------------
    # Build the union of all keys (pre and post may differ when look-through
    # moves value between buckets).
    all_keys = set(pre) | set(post)

    rows: list[ConcentrationRow] = []
    for key in sorted(all_keys):  # stable sort for consistent output ordering
        ac, sector = key
        pre_value = pre.get(key, 0.0)
        post_value = post.get(key, 0.0)
        pre_pct = pre_value / total_aum * 100.0
        post_pct = post_value / total_aum * 100.0

        # Mandate limit applies only when any instrument with
        # concentration_limit_applies="Y" contributes to this bucket.
        mandate_limit: float | None = None
        if key in concentration_limit_keys:
            mandate_limit = mandate_limits.get(ac)  # None if no mandate row

        # Classify status.
        if mandate_limit is None:
            status = "NO_LIMIT"
        elif post_pct >= mandate_limit:
            status = "BREACH"
        elif post_pct >= mandate_limit * ELEVATED_THRESHOLD_FRACTION:
            status = "ELEVATED"
        else:
            status = "OK"

        # Exposure name: prefer sector if distinct from asset class,
        # otherwise fall back to asset class.
        exposure_name = sector if sector and sector != ac else ac

        rows.append(
            ConcentrationRow(
                exposure_name=exposure_name,
                asset_class=ac,
                sector=sector,
                pre_look_through_value_usd=pre_value,
                post_look_through_value_usd=post_value,
                pre_look_through_pct=round(pre_pct, 4),
                post_look_through_pct=round(post_pct, 4),
                mandate_limit_pct=mandate_limit,
                status=status,
            )
        )

    # -----------------------------------------------------------------------
    # STEP 6 — hidden concentration discovery
    # -----------------------------------------------------------------------
    # A hidden concentration is flagged when look-through causes the
    # post-pct to exceed the pre-pct by more than HIDDEN_CONCENTRATION_GAP_PP.
    hidden: list[dict[str, Any]] = []
    for row in rows:
        gap = row.post_look_through_pct - row.pre_look_through_pct
        if gap > HIDDEN_CONCENTRATION_GAP_PP:
            hidden.append({
                "exposure_name": row.exposure_name,
                "pre_pct": round(row.pre_look_through_pct, 4),
                "post_pct": round(row.post_look_through_pct, 4),
                "gap_pct": round(gap, 4),
                "explanation": (
                    f"Gap attributable to look-through of structured products into "
                    f"{row.asset_class} / {row.sector}. "
                    f"Post-look-through exposure is {row.post_look_through_pct:.2f}% of AUM, "
                    f"versus {row.pre_look_through_pct:.2f}% on a stated-classification basis."
                ),
            })

    return {
        "concentrations": rows,
        "hidden_concentration_discoveries": hidden,
        "total_aum_usd": round(total_aum, 2),
    }


def concentration_table(
    client_id: str,
    data: Mapping[str, pd.DataFrame],
    as_of: str = AS_OF,
) -> list[ConcentrationRow]:
    """Convenience wrapper that returns only the ConcentrationRow list."""
    return concentration_result(client_id, data, as_of)["concentrations"]
