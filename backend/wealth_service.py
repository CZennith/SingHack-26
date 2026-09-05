"""Read-only application services for the frontend wealth-data API."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from src.calculators.exposure_base import build_exposure_base
from src.calculators.exposure_changes import calculate_exposure_changes
from src.client_snapshot import build_client_snapshot, validate_snapshot
from src.contracts.validation import validate_result


API_SCHEMA_VERSION = "1.0.0"


class WealthServiceError(ValueError):
    """A request cannot be fulfilled safely from the configured data source."""


class UnknownClientError(WealthServiceError):
    """The requested client does not exist."""


class UnsupportedDateError(WealthServiceError):
    """The requested date is not present in the database."""


def _connect(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise WealthServiceError(f"wealth database does not exist: {path}")
    return duckdb.connect(str(path), read_only=True)


def _iso_date(value: str | None, field: str, *, required: bool = False) -> str | None:
    if value is None or value == "":
        if required:
            raise WealthServiceError(f"{field} is required")
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise WealthServiceError(f"{field} must be a real ISO date in YYYY-MM-DD format") from exc
    if parsed.isoformat() != value:
        raise WealthServiceError(f"{field} must be an ISO date in YYYY-MM-DD format")
    return value


def _json_scalar(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _available_dates(con: duckdb.DuckDBPyConnection) -> list[str]:
    return [row[0].isoformat() for row in con.execute(
        "SELECT DISTINCT snapshot_date FROM holdings_snapshots ORDER BY snapshot_date"
    ).fetchall()]


def _require_date(con: duckdb.DuckDBPyConnection, value: str | None, field: str) -> str:
    parsed = _iso_date(value, field, required=True)
    assert parsed is not None
    available = _available_dates(con)
    if parsed not in available:
        raise UnsupportedDateError(
            f"{field} {parsed!r} is not available; supported dates: {', '.join(available)}"
        )
    return parsed


def _require_client(con: duckdb.DuckDBPyConnection, client_id: str | None) -> str:
    if not isinstance(client_id, str) or not client_id.strip():
        raise WealthServiceError("client_id is required")
    client_id = client_id.strip()
    exists = con.execute("SELECT 1 FROM clients WHERE client_id = ?", [client_id]).fetchone()
    if exists is None:
        raise UnknownClientError(f"unknown client_id {client_id!r}")
    return client_id


def _metadata(
    result_type: str,
    *,
    client_id: str | None = None,
    as_of_date: str | None = None,
    comparison_date: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    schema_version: str = API_SCHEMA_VERSION,
) -> dict[str, Any]:
    return {
        "result_type": result_type,
        "schema_version": schema_version,
        "client_id": client_id,
        "as_of_date": as_of_date,
        "comparison_date": comparison_date,
        "period_start": period_start,
        "period_end": period_end,
    }


def get_snapshot_dates(db_path: str | Path, client_id: str | None = None) -> dict[str, Any]:
    """Return valid point-in-time dates without exposing the database connection."""
    con = _connect(db_path)
    try:
        if client_id is not None:
            client_id = _require_client(con, client_id)
        dates = _available_dates(con)
        return {
            "response_metadata": _metadata("snapshot_dates", client_id=client_id),
            "dates": [
                {
                    "as_of_date": item,
                    "holdings": True,
                    "valuations": con.execute(
                        "SELECT EXISTS(SELECT 1 FROM portfolio_valuations WHERE snapshot_date = ?)", [item]
                    ).fetchone()[0],
                    "facilities": con.execute(
                        "SELECT EXISTS(SELECT 1 FROM facility_snapshots WHERE snapshot_date = ?)", [item]
                    ).fetchone()[0],
                    "market_context": con.execute(
                        "SELECT EXISTS(SELECT 1 FROM market_context WHERE snapshot_date = ?)", [item]
                    ).fetchone()[0],
                }
                for item in dates
            ],
        }
    finally:
        con.close()


def get_clients(db_path: str | Path, as_of_date: str | None = None) -> dict[str, Any]:
    """Return all client identities and factual, date-scoped summary fields."""
    con = _connect(db_path)
    try:
        selected = _require_date(con, as_of_date, "as_of_date") if as_of_date else _available_dates(con)[-1]
        cursor = con.execute(
            """
            SELECT c.client_id, c.client_name, c.age, c.base_currency, c.wealth_band,
                   c.risk_profile, c.risk_tolerance_score, c.investment_horizon_years,
                   c.liquidity_needs, c.client_since, c.rm_id, c.rm_name, c.rm_desk,
                   c.life_stage, c.objectives,
                   COALESCE(h.aum_usd, 0) AS aum_usd_at_as_of,
                   COALESCE(p.portfolio_count, 0) AS portfolio_count,
                   COALESCE(f.facility_count, 0) AS facility_count,
                   f.max_ltv_pct_at_as_of
            FROM clients c
            LEFT JOIN (
                SELECT client_id, SUM(market_value_usd) AS aum_usd
                FROM holdings_snapshots
                WHERE snapshot_date = ?
                GROUP BY client_id
            ) h ON h.client_id = c.client_id
            LEFT JOIN (
                SELECT client_id, COUNT(*) AS portfolio_count
                FROM portfolios
                GROUP BY client_id
            ) p ON p.client_id = c.client_id
            LEFT JOIN (
                SELECT f.client_id, COUNT(*) AS facility_count,
                       MAX(s.ltv_pct) AS max_ltv_pct_at_as_of
                FROM credit_facilities f
                LEFT JOIN facility_snapshots s
                  ON s.facility_id = f.facility_id AND s.snapshot_date = ?
                GROUP BY f.client_id
            ) f ON f.client_id = c.client_id
            ORDER BY c.client_id
            """,
            [selected, selected],
        )
        rows = cursor.fetchall()
        columns = [item[0] for item in cursor.description]
        clients = [dict(zip(columns, row)) for row in rows]
        for client in clients:
            for key, value in list(client.items()):
                client[key] = _json_scalar(value)
        return {
            "response_metadata": _metadata("client_list", as_of_date=selected),
            "clients": clients,
        }
    finally:
        con.close()


def get_snapshot(
    db_path: str | Path,
    client_id: str,
    as_of_date: str,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, Any]:
    """Build one validated snapshot with the existing read-only service."""
    con = _connect(db_path)
    try:
        client_id = _require_client(con, client_id)
        selected = _require_date(con, as_of_date, "as_of_date")
        start = _iso_date(period_start, "period_start")
        end = _iso_date(period_end, "period_end")
        snapshot = validate_snapshot(build_client_snapshot(con, client_id, selected, start, end))
        # The local builder records its source path for auditability. Do not
        # disclose a server filesystem path to the browser response.
        snapshot["snapshot_metadata"].pop("database_path", None)
        metadata = snapshot["snapshot_metadata"]
        return {
            "response_metadata": _metadata(
                "client_snapshot",
                client_id=client_id,
                as_of_date=metadata["as_of_date"],
                period_start=metadata["period_start"],
                period_end=metadata["period_end"],
                schema_version="1.0.0",
            ),
            "snapshot": snapshot,
        }
    finally:
        con.close()


def get_exposure_changes(
    db_path: str | Path,
    client_id: str,
    as_of_date: str,
    comparison_date: str,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, Any]:
    """Build the existing direct exposure-change result for two explicit dates."""
    con = _connect(db_path)
    try:
        client_id = _require_client(con, client_id)
        current_date = _require_date(con, as_of_date, "as_of_date")
        previous_date = _require_date(con, comparison_date, "comparison_date")
        if previous_date == current_date:
            raise WealthServiceError("comparison_date must differ from as_of_date")
        start = _iso_date(period_start, "period_start")
        end = _iso_date(period_end, "period_end")
        current = build_client_snapshot(con, client_id, current_date, start, end)
        previous = build_client_snapshot(con, client_id, previous_date)
        result = validate_result(calculate_exposure_changes(
            build_exposure_base(current), build_exposure_base(previous)
        )).to_dict()
        metadata = result["result_metadata"]
        return {
            "response_metadata": _metadata(
                "exposure_changes",
                client_id=client_id,
                as_of_date=metadata["as_of_date"],
                comparison_date=metadata["comparison_date"],
                period_start=current["snapshot_metadata"]["period_start"],
                period_end=current["snapshot_metadata"]["period_end"],
                schema_version=metadata["schema_version"],
            ),
            "result": result,
        }
    finally:
        con.close()


def get_exposure(
    db_path: str | Path,
    client_id: str,
    as_of_date: str,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict[str, Any]:
    """Build the existing consolidated exposure base for one snapshot."""
    con = _connect(db_path)
    try:
        client_id = _require_client(con, client_id)
        selected = _require_date(con, as_of_date, "as_of_date")
        start = _iso_date(period_start, "period_start")
        end = _iso_date(period_end, "period_end")
        snapshot = build_client_snapshot(con, client_id, selected, start, end)
        exposure = build_exposure_base(snapshot)
        return {
            "response_metadata": _metadata(
                "exposure_base",
                client_id=client_id,
                as_of_date=snapshot["snapshot_metadata"]["as_of_date"],
                period_start=snapshot["snapshot_metadata"]["period_start"],
                period_end=snapshot["snapshot_metadata"]["period_end"],
            ),
            "exposure": exposure,
        }
    finally:
        con.close()


def get_market_context(db_path: str | Path, as_of_date: str) -> dict[str, Any]:
    """Return raw dated market-context records; no market interpretation is added."""
    con = _connect(db_path)
    try:
        selected = _require_date(con, as_of_date, "as_of_date")
        cursor = con.execute(
            """
            SELECT snapshot_date, series_id, series_name, category, unit, value, snapshot_label
            FROM market_context
            WHERE snapshot_date = ?
            ORDER BY series_id
            """,
            [selected],
        )
        columns = [item[0] for item in cursor.description]
        records = []
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            record = {key: _json_scalar(value) for key, value in record.items()}
            records.append(record)
        return {
            "response_metadata": _metadata("market_context", as_of_date=selected),
            "records": records,
        }
    finally:
        con.close()
