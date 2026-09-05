"""Liquidity Coverage Ratio engine and life-event flag detection.

Public API
----------
compute_lcr(client_id, data, as_of) -> LiquidityResult
    Computes the 60-day LCR, sell-to-cover ranking, and life-event flags
    for the given client at the specified snapshot date.

life_event_flags(client_id, lcr_result, data, as_of) -> list[dict]
    Returns Life-Event Flag dicts when a client's upcoming cash need (within
    18 months) exceeds 20% of Tier-1 Liquid Value AND a life-stage keyword
    matches.  Exposed separately so the router can surface flags independent
    of a full LCR run.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any

import pandas as pd

from stress_test import _build_fx_rates, _number, _text, to_usd
from stress_types import LiquidityResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AS_OF = date(2026, 8, 26)
SNAPSHOT_DATE_STR = "2026-08-26"

# 60-day LCR window
LCR_DAYS = 60

# Sell-to-cover: always T+2 for Daily-liquid holdings
SETTLE_DAYS = 2

# Life-event planning: 18-month look-forward from AS_OF
LIFE_EVENT_MONTHS = 18

# The 20% threshold: a need exceeding this fraction of Tier-1 triggers a flag.
LIFE_EVENT_TIER1_THRESHOLD = 0.20

# LCR < 1.2 threshold referenced in Req 6.7 for the life-event liquidity flag.
LIFE_EVENT_LCR_WARN_THRESHOLD = 1.2

# Life-stage keywords that activate life-event flag checking (Req 13.5)
LIFE_EVENT_KEYWORDS = [
    "pre-liquidity event",
    "succession",
    "business sale",
    "retirement",
    "charitable foundation",
    "property purchase",
    "family office formation",
    # Partial-match variants that appear in clients.csv
    "pre-retirement",
    "succession and estate",
    "retired",
    "multi-generational",
]

# Quarter start dates used when parsing "2026 Q4"-style call windows.
# Q1 → Jan 1, Q2 → Apr 1, Q3 → Jul 1, Q4 → Oct 1
_QUARTER_START_MONTH = {1: 1, 2: 4, 3: 7, 4: 10}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_quarter_start(window_str: str) -> date | None:
    """Extract the start date from a free-text call-window string.

    Recognises patterns like:
      "2026 Q4 to 2028 Q2"
      "2027 Q1 to 2028 Q2"
      "2026Q4"
    Returns a date corresponding to the first day of the start quarter, or
    None if the string cannot be parsed.
    """
    # Match the first "YYYY Q[1-4]" occurrence in the string.
    m = re.search(r"(\d{4})\s*Q([1-4])", window_str or "")
    if not m:
        return None
    year = int(m.group(1))
    quarter = int(m.group(2))
    month = _QUARTER_START_MONTH[quarter]
    return date(year, month, 1)


def _lcr_cutoff(as_of: date) -> date:
    return as_of + timedelta(days=LCR_DAYS)


def _life_event_cutoff(as_of: date) -> date:
    """18 months forward — approximate as 548 days (365 + 183)."""
    # Use a month-aware approach: add 18 months directly.
    month = as_of.month + LIFE_EVENT_MONTHS
    year = as_of.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    return as_of.replace(year=year, month=month)


def _life_stage_matches(life_stage: str) -> bool:
    """Return True if the client's life_stage contains any keyword."""
    ls = (life_stage or "").lower()
    return any(kw in ls for kw in LIFE_EVENT_KEYWORDS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_lcr(
    client_id: str,
    data: Mapping[str, pd.DataFrame],
    as_of: date = AS_OF,
) -> LiquidityResult:
    """Compute the 60-day Liquidity Coverage Ratio for *client_id*.

    Steps follow Algorithm 3 from the design document:

    1. Load 60-day cash obligations (planned_cash_needs + unfunded commitments).
    2. Normalise all obligation amounts to USD.
    3. Sum Tier-1 liquid holdings (liquidity_tier = "Daily").
    4. Compute LCR; handle zero-obligations edge case.
    5. Build sell-to-cover ranked list (top 5).
    6. Detect life-event flags.
    """
    snapshot_str = as_of.strftime("%Y-%m-%d")
    cutoff = _lcr_cutoff(as_of)
    fx_rates = _build_fx_rates(data["market_context"], snapshot_str)

    # -----------------------------------------------------------------------
    # Step 1a: 60-day planned cash needs
    # -----------------------------------------------------------------------
    cash_needs_df = data["planned_cash_needs"]
    client_needs = cash_needs_df[cash_needs_df["client_id"].eq(client_id)].copy()

    # Parse due_from as date; keep rows whose due_from ≤ cutoff AND ≥ as_of.
    client_needs["_due_from"] = pd.to_datetime(
        client_needs["due_from"], errors="coerce"
    ).dt.date

    in_window = client_needs[
        (client_needs["_due_from"] >= as_of)
        & (client_needs["_due_from"] <= cutoff)
    ]

    obligations_cash_usd = sum(
        to_usd(
            _number(row["amount"]),
            _text(row.get("currency")) or "USD",
            fx_rates,
        )
        for _, row in in_window.iterrows()
    )

    # -----------------------------------------------------------------------
    # Step 1b: unfunded commitments whose call window starts ≤ cutoff
    # -----------------------------------------------------------------------
    commitments_df = data["commitments"]
    client_commitments = commitments_df[
        commitments_df["client_id"].eq(client_id)
    ]

    obligations_commitment_usd = 0.0
    for _, row in client_commitments.iterrows():
        window_start = _parse_quarter_start(_text(row.get("expected_call_window")))
        if window_start is None:
            continue
        if window_start <= cutoff:
            uncalled = _number(row.get("uncalled"))
            ccy = _text(row.get("currency")) or "USD"
            obligations_commitment_usd += to_usd(uncalled, ccy, fx_rates)

    total_obligations = obligations_cash_usd + obligations_commitment_usd

    # -----------------------------------------------------------------------
    # Step 2: Tier-1 liquid holdings
    # -----------------------------------------------------------------------
    holdings_df = data["holdings"]
    snapshot_holdings = holdings_df[
        holdings_df["client_id"].eq(client_id)
        & holdings_df["snapshot_date"].astype(str).eq(snapshot_str)
    ]
    tier1 = snapshot_holdings[
        snapshot_holdings["liquidity_tier"].astype(str).str.strip().eq("Daily")
    ]
    tier1_value = tier1["market_value_usd"].apply(_number).sum()

    # -----------------------------------------------------------------------
    # Step 3: LCR formula
    # -----------------------------------------------------------------------
    if total_obligations == 0.0:
        # Guard: no obligations → effectively infinite coverage.
        lcr: float | None = None
        status = "COVERED"
        surplus_or_gap = tier1_value
        note = "No obligations in window"
    else:
        lcr_raw = tier1_value / total_obligations
        lcr = round(lcr_raw, 2)
        status = "COVERED" if lcr >= 1.0 else "SHORTFALL"
        surplus_or_gap = tier1_value - total_obligations
        note = ""

    # -----------------------------------------------------------------------
    # Step 4: Sell-to-cover ranked list (top 5 Tier-1 holdings)
    # -----------------------------------------------------------------------
    # Sort by: (1) unrealised_pnl_base ascending (largest loss first — tax
    # efficiency), then (2) market_value_usd descending (size tiebreaker).
    sell_list: list[dict[str, Any]] = []
    if not tier1.empty:
        tier1_sorted = tier1.copy()
        tier1_sorted["_pnl"] = tier1_sorted["unrealised_pnl_base"].apply(_number)
        tier1_sorted["_val"] = tier1_sorted["market_value_usd"].apply(_number)
        tier1_sorted = tier1_sorted.sort_values(
            by=["_pnl", "_val"],
            ascending=[True, False],
        )
        for rank, (_, h) in enumerate(tier1_sorted.head(5).iterrows(), start=1):
            sell_list.append({
                "rank": rank,
                "instrument_name": _text(h.get("instrument_name")),
                "current_value_usd": _number(h.get("market_value_usd")),
                "unrealised_pnl_usd": _number(h.get("unrealised_pnl_base")),
                "estimated_settle_days": SETTLE_DAYS,
            })

    # -----------------------------------------------------------------------
    # Step 5: Life-event flags
    # -----------------------------------------------------------------------
    flags = life_event_flags(
        client_id,
        tier1_value=tier1_value,
        lcr=lcr,
        data=data,
        as_of=as_of,
    )

    return LiquidityResult(
        total_60d_obligations_usd=round(total_obligations, 2),
        tier1_liquid_value_usd=round(tier1_value, 2),
        lcr=lcr,  # type: ignore[arg-type]  # None is valid (zero-obligation case)
        status=status,
        surplus_or_gap_usd=round(surplus_or_gap, 2),
        sell_to_cover=sell_list,
        life_event_flags=flags,
    )


def life_event_flags(
    client_id: str,
    tier1_value: float,
    lcr: float | None,
    data: Mapping[str, pd.DataFrame],
    as_of: date = AS_OF,
) -> list[dict[str, Any]]:
    """Detect life-event planning flags (Requirements 6.7, 13.1–13.5).

    A flag is emitted when ALL of the following hold:
      1. The client's life_stage contains a recognised keyword (Req 13.5).
      2. A planned_cash_need within 18 months has amount_usd > 20% of Tier-1.
      3. LCR < 1.2 (additional liquidity warning signal per Req 6.7), OR
         the need alone exceeds Tier-1 (unconditional flag regardless of LCR).

    The function can also be called independently of compute_lcr (e.g. for
    the urgency score drilldown) by the caller supplying tier1_value and lcr.
    """
    snapshot_str = as_of.strftime("%Y-%m-%d")
    life_event_cutoff = _life_event_cutoff(as_of)
    fx_rates = _build_fx_rates(data["market_context"], snapshot_str)

    # Fetch client life_stage.
    clients_df = data["clients"]
    client_rows = clients_df[clients_df["client_id"].eq(client_id)]
    if client_rows.empty:
        return []
    life_stage = _text(client_rows.iloc[0].get("life_stage"))

    if not _life_stage_matches(life_stage):
        return []

    # Filter planned cash needs within 18 months.
    cash_needs_df = data["planned_cash_needs"]
    client_needs = cash_needs_df[cash_needs_df["client_id"].eq(client_id)].copy()
    client_needs["_due_from"] = pd.to_datetime(
        client_needs["due_from"], errors="coerce"
    ).dt.date

    upcoming = client_needs[
        (client_needs["_due_from"] >= as_of)
        & (client_needs["_due_from"] <= life_event_cutoff)
    ]

    flags: list[dict[str, Any]] = []
    for _, row in upcoming.iterrows():
        amount_usd = to_usd(
            _number(row.get("amount")),
            _text(row.get("currency")) or "USD",
            fx_rates,
        )

        # Threshold check: need > 20% of Tier-1.
        threshold = tier1_value * LIFE_EVENT_TIER1_THRESHOLD
        if amount_usd <= threshold:
            continue

        # LCR check: flag if LCR < 1.2 OR the need alone exceeds Tier-1.
        lcr_below_threshold = (lcr is None) or (lcr < LIFE_EVENT_LCR_WARN_THRESHOLD)
        need_exceeds_tier1 = amount_usd > tier1_value
        if not (lcr_below_threshold or need_exceeds_tier1):
            continue

        coverage_ratio = (tier1_value / amount_usd) if amount_usd > 0 else float("inf")
        due_from_str = _text(row.get("due_from"))

        flags.append({
            "description": _text(row.get("description")),
            "due_date": due_from_str,
            "amount_usd": round(amount_usd, 2),
            "coverage_ratio": round(coverage_ratio, 2),
            "life_stage_note": (
                f"{life_stage.capitalize()} — "
                f"{_text(row.get('description'))} due {due_from_str} "
                f"represents {amount_usd / tier1_value * 100:.1f}% of daily-liquid assets "
                f"(Tier-1 = USD {tier1_value:,.0f}); "
                f"insufficient daily-liquid assets to cover without disrupting the portfolio structure."
                if tier1_value > 0
                else f"{life_stage.capitalize()} — {_text(row.get('description'))} due {due_from_str}; no Tier-1 liquid assets on record."
            ),
        })

    return flags
