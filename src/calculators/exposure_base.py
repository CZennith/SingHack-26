"""Build direct exposure summaries from one validated client snapshot."""

from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation
from typing import Any

from ..client_snapshot import validate_snapshot


EXPOSURE_VERSION = "1.0.0"
TOLERANCE = Decimal("0.00000001")
DIMENSIONS = (
    ("asset_class", "asset_class"),
    ("sub_asset_class", "sub_asset_class"),
    ("sector", "sector"),
    ("region", "region"),
    ("currency", "instrument_ccy"),
    ("instrument", "instrument_id"),
)


class ExposureInputError(ValueError):
    """The snapshot cannot safely be used to build a direct exposure base."""


def _decimal(value: Any, path: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ExposureInputError(f"{path}: market_value_usd is required and must be numeric")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ExposureInputError(f"{path}: malformed numeric value {value!r}") from exc
    if not parsed.is_finite():
        raise ExposureInputError(f"{path}: numeric value must be finite")
    return parsed


def _number(value: Decimal) -> float:
    return float(value)


def _key(value: Any, path: str) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ExposureInputError(f"{path}: key must be JSON-compatible")
        return value
    raise ExposureInputError(f"{path}: dimension key must be a scalar or null")


def _group_record(
    dimension: str,
    key: Any,
    scope_level: str,
    portfolio_id: str | None,
    instrument_id: str | None,
    instrument_name: str | None,
    market_value_usd: Decimal,
    holding_count: int,
    client_total: Decimal,
    underlying_reference: str | None = None,
) -> dict[str, Any]:
    weight = Decimal(0) if abs(client_total) <= TOLERANCE else market_value_usd / client_total * Decimal(100)
    result = {
        "dimension": dimension,
        "key": _key(key, f"{dimension}.key"),
        "scope_level": scope_level,
        "portfolio_id": portfolio_id,
        "instrument_id": instrument_id,
        "instrument_name": instrument_name,
        "market_value_usd": _number(market_value_usd),
        "weight_pct": _number(weight),
        "holding_count": holding_count,
    }
    if dimension == "instrument":
        result.update({
            "underlying_reference": underlying_reference,
            "look_through_included": False,
        })
    return result


def _aggregate(
    holdings: list[dict[str, Any]],
    dimension: str,
    source_field: str,
    total: Decimal,
    *,
    scope_level: str = "client",
    portfolio_id: str | None = None,
) -> list[dict[str, Any]]:
    groups: dict[Any, dict[str, Any]] = {}
    for holding in holdings:
        key = _key(holding.get(source_field), f"holdings.{source_field}")
        group = groups.setdefault(key, {"value": Decimal(0), "count": 0, "instrument_name": None, "instrument_id": None, "underlying_reference": None})
        group["value"] += _decimal(holding.get("market_value_usd"), f"holdings.{holding.get('portfolio_id')}/{holding.get('instrument_id')}")
        group["count"] += 1
        if dimension == "instrument":
            group["instrument_id"] = holding.get("instrument_id")
            group["instrument_name"] = holding.get("instrument_name")
            group["underlying_reference"] = holding.get("underlying_reference")
    return [
        _group_record(dimension, key, scope_level, portfolio_id, group["instrument_id"], group["instrument_name"], group["value"], group["count"], total, group["underlying_reference"])
        for key, group in sorted(groups.items(), key=lambda item: (item[0] is not None, str(item[0])))
    ]


def _source_reference(client_id: str, holding: dict[str, Any]) -> dict[str, Any]:
    return {
        "table": "client_snapshot.holdings",
        "keys": {
            "client_id": client_id,
            "snapshot_date": holding.get("snapshot_date"),
            "portfolio_id": holding.get("portfolio_id"),
            "instrument_id": holding.get("instrument_id"),
        },
    }


def build_exposure_base(snapshot: dict) -> dict:
    """Build direct, USD-based exposure summaries from one snapshot.

    Aggregations use only direct ``holdings[].market_value_usd`` values.
    No database query, look-through calculation, event interpretation, or
    materiality policy is performed here.
    """
    snapshot = validate_snapshot(snapshot)
    metadata = snapshot["snapshot_metadata"]
    client = snapshot["client"]
    client_id = metadata["client_id"]
    as_of = metadata["as_of_date"]
    if client.get("client_id") != client_id:
        raise ExposureInputError("snapshot.client.client_id must match snapshot metadata")
    portfolios = snapshot["portfolios"]
    portfolio_ids = set()
    for index, portfolio in enumerate(portfolios):
        portfolio_id = portfolio.get("portfolio_id")
        if not isinstance(portfolio_id, str) or not portfolio_id:
            raise ExposureInputError(f"portfolios[{index}].portfolio_id must be a non-empty string")
        if portfolio_id in portfolio_ids:
            raise ExposureInputError(f"portfolios: duplicate portfolio_id {portfolio_id!r}")
        portfolio_ids.add(portfolio_id)
        if portfolio.get("client_id") != client_id:
            raise ExposureInputError(f"portfolios[{index}].client_id does not match client {client_id}")

    holdings = []
    identities = set()
    for index, holding in enumerate(snapshot["holdings"]):
        path = f"holdings[{index}]"
        if not isinstance(holding, dict):
            raise ExposureInputError(f"{path}: must be an object")
        if holding.get("snapshot_date") != as_of:
            continue
        if holding.get("client_id") != client_id:
            raise ExposureInputError(f"{path}.client_id does not match client {client_id}")
        if holding.get("portfolio_id") not in portfolio_ids:
            raise ExposureInputError(f"{path}.portfolio_id does not belong to client {client_id}")
        if not holding.get("instrument_id"):
            raise ExposureInputError(f"{path}.instrument_id is required for holdings exposure")
        identity = (holding.get("snapshot_date"), holding.get("portfolio_id"), holding.get("instrument_id"))
        if identity in identities:
            raise ExposureInputError(f"holdings: duplicate holding identity {identity!r}")
        identities.add(identity)
        _decimal(holding.get("market_value_usd"), path)
        holdings.append(holding)

    total = sum((_decimal(item.get("market_value_usd"), "holdings") for item in holdings), Decimal(0))
    portfolio_values = {portfolio_id: [item for item in holdings if item.get("portfolio_id") == portfolio_id] for portfolio_id in sorted(portfolio_ids)}
    by_portfolio = []
    for portfolio_id, items in portfolio_values.items():
        value = sum((_decimal(item.get("market_value_usd"), "holdings") for item in items), Decimal(0))
        # Portfolio weights use that portfolio's own USD total, not the
        # consolidated client denominator.
        by_portfolio.append(_group_record("portfolio", portfolio_id, "portfolio", portfolio_id, None, None, value, len(items), value))

    result = {
        "exposure_metadata": {
            "client_id": client_id,
            "as_of_date": as_of,
            "exposure_type": "direct",
            "currency_basis": "USD",
            "look_through_included": False,
            "calculator_name": "exposure_base",
            "calculator_version": EXPOSURE_VERSION,
            "snapshot_schema_version": "1.0.0",
            "snapshot_calculation_version": metadata["calculation_version"],
        },
        "client_total": {
            "market_value_usd": _number(total),
            "holding_count": len(holdings),
            "portfolio_count": len(portfolios),
        },
        "by_portfolio": by_portfolio,
        "by_asset_class": _aggregate(holdings, "asset_class", "asset_class", total),
        "by_sub_asset_class": _aggregate(holdings, "sub_asset_class", "sub_asset_class", total),
        "by_sector": _aggregate(holdings, "sector", "sector", total),
        "by_region": _aggregate(holdings, "region", "region", total),
        "by_currency": _aggregate(holdings, "currency", "instrument_ccy", total),
        "by_instrument": _aggregate(holdings, "instrument", "instrument_id", total),
        "warnings": [],
        "source_references": [_source_reference(client_id, holding) for holding in holdings],
    }
    warnings = []
    for dimension, source_field in DIMENSIONS[:-1]:
        null_group = next((group for group in result[f"by_{dimension}"] if group["key"] is None), None)
        if null_group is not None:
            sample = next(item for item in holdings if item.get(source_field) is None)
            warnings.append({
                "warning_id": f"W-{len(warnings) + 1:03d}",
                "warning_type": "missing_dimension",
                "severity": "warning",
                "message": f"A holding has no {dimension} value; it was retained in a null group.",
                "dimension": dimension,
                "source_reference": _source_reference(client_id, sample),
            })
    if not holdings:
        warnings.append({
            "warning_id": f"W-{len(warnings) + 1:03d}",
            "warning_type": "empty_holdings",
            "severity": "info",
            "message": "No holdings were present at the requested snapshot date; exposure totals are zero.",
            "source_reference": {"table": "client_snapshot.holdings", "keys": {"client_id": client_id, "snapshot_date": as_of}},
        })
    result["warnings"] = warnings
    return json.loads(json.dumps(result, allow_nan=False))
