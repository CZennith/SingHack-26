"""Build deterministic, read-only client snapshots from DuckDB.

This module deliberately consolidates facts only. It does not calculate
performance, interpret events, make suitability decisions, or recommend action.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb

from .build_database import SNAPSHOT_DATES
from .output_files import OutputExistsError, OutputWriteError, atomic_write_json
from .output_paths import OutputPathError, require_unique_output_paths, snapshot_output_path
from .snapshot_models import DataQualityFlag, SourceReference


CALCULATION_VERSION = "1.0.0"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "db" / "wealth.duckdb"
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SNAPSHOT_KEYS = {"snapshot_metadata", "client", "portfolios", "portfolio_summaries", "holdings", "transactions", "planned_cash_needs", "commitments", "credit_facilities", "rm_notes", "market_events", "data_quality_flags", "source_references"}


class SnapshotInputError(ValueError):
    """A requested client or date range is invalid."""


def _parse_iso_date(value: str, field_name: str) -> date:
    if not isinstance(value, str) or not _ISO_DATE.fullmatch(value):
        raise SnapshotInputError(f"Invalid {field_name} {value!r}; expected YYYY-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SnapshotInputError(f"Invalid {field_name} {value!r}; expected a real calendar date.") from exc
    if parsed.isoformat() != value:
        raise SnapshotInputError(f"Invalid {field_name} {value!r}; expected YYYY-MM-DD.")
    return parsed


def _resolve_period(as_of: date, available_dates: tuple[str, ...], period_start: str | None, period_end: str | None) -> tuple[date, date]:
    if period_end is None:
        end = as_of
    else:
        end = _parse_iso_date(period_end, "period_end")
    if period_start is None:
        index = available_dates.index(as_of.isoformat())
        start = date.fromisoformat(available_dates[max(0, index - 1)])
    else:
        start = _parse_iso_date(period_start, "period_start")
    if start > end:
        raise SnapshotInputError(f"Invalid period: period_start {start.isoformat()} is after period_end {end.isoformat()}.")
    return start, end


def _database_path(con: duckdb.DuckDBPyConnection) -> str:
    try:
        rows = con.execute("PRAGMA database_list").fetchall()
        if rows and rows[0][2]:
            return str(rows[0][2])
    except duckdb.Error:
        pass
    return "unknown"


def validate_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Validate the generated snapshot envelope without changing it.

    This is intentionally a structural validator for the existing snapshot
    contract, not an analytics validator. It rejects missing/unknown envelope
    fields, malformed metadata dates, and client identity mismatches.
    """
    if not isinstance(snapshot, dict):
        raise SnapshotInputError("snapshot must be an object")
    try:
        json.dumps(snapshot, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise SnapshotInputError(f"snapshot must be JSON-serializable: {exc}") from exc
    missing = sorted(SNAPSHOT_KEYS - set(snapshot))
    unknown = sorted(set(snapshot) - SNAPSHOT_KEYS)
    if missing:
        raise SnapshotInputError(f"snapshot: missing required field(s): {', '.join(missing)}")
    if unknown:
        raise SnapshotInputError(f"snapshot: unexpected field(s): {', '.join(unknown)}")
    metadata = snapshot["snapshot_metadata"]
    if not isinstance(metadata, dict):
        raise SnapshotInputError("snapshot.snapshot_metadata must be an object")
    required_metadata = {"client_id", "as_of_date", "period_start", "period_end", "calculation_version"}
    missing_metadata = sorted(required_metadata - set(metadata))
    if missing_metadata:
        raise SnapshotInputError(f"snapshot.snapshot_metadata: missing required field(s): {', '.join(missing_metadata)}")
    client_id = metadata["client_id"]
    if not isinstance(client_id, str) or not client_id:
        raise SnapshotInputError("snapshot.snapshot_metadata.client_id must be a non-empty string")
    for field in ("as_of_date", "period_start", "period_end"):
        _parse_iso_date(metadata[field], f"snapshot.snapshot_metadata.{field}")
    if metadata["period_start"] > metadata["period_end"]:
        raise SnapshotInputError("snapshot.snapshot_metadata.period_start must be on or before period_end")
    if not isinstance(metadata["calculation_version"], str) or not metadata["calculation_version"]:
        raise SnapshotInputError("snapshot.snapshot_metadata.calculation_version must be a non-empty string")
    client = snapshot["client"]
    if not isinstance(client, dict) or client.get("client_id") != client_id:
        raise SnapshotInputError("snapshot.client.client_id must match snapshot_metadata.client_id")
    for section in ("portfolios", "portfolio_summaries", "holdings", "transactions", "planned_cash_needs", "commitments", "credit_facilities", "rm_notes", "market_events", "data_quality_flags", "source_references"):
        if not isinstance(snapshot[section], list):
            raise SnapshotInputError(f"snapshot.{section} must be an array")
    return snapshot


def _available_snapshot_dates(con: duckdb.DuckDBPyConnection) -> tuple[str, ...]:
    rows = con.execute("SELECT DISTINCT snapshot_date FROM holdings_snapshots ORDER BY snapshot_date").fetchall()
    return tuple(row[0].isoformat() for row in rows)


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        # JSON has no decimal type. Keep values numeric for consumers while
        # avoiding Python-only Decimal objects in the public result.
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _query_dicts(con: duckdb.DuckDBPyConnection, query: str, params: list[Any] | tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cursor = con.execute(query, params)
    columns = [description[0] for description in cursor.description]
    return [{column: _json_value(value) for column, value in zip(columns, row)} for row in cursor.fetchall()]


def _one_dict(con: duckdb.DuckDBPyConnection, query: str, params: list[Any] | tuple[Any, ...], label: str) -> dict[str, Any]:
    rows = _query_dicts(con, query, params)
    if not rows:
        raise SnapshotInputError(f"Unknown client_id {params[0]!r}. No matching {label} record exists.")
    return rows[0]


def _ref(table: str, **keys: Any) -> dict[str, Any]:
    return SourceReference(table, _json_value(keys)).to_dict()


def _add_flag(flags: list[DataQualityFlag], flag_type: str, severity: str, message: str, table: str, **keys: Any) -> None:
    flags.append(DataQualityFlag(flag_type, severity, message, SourceReference(table, _json_value(keys))))


def _sort_flags(flags: list[DataQualityFlag]) -> list[dict[str, Any]]:
    return [flag.to_dict() for flag in sorted(flags, key=lambda item: (item.flag_type, item.source_reference.table, json.dumps(item.source_reference.keys, sort_keys=True)))]


def _portfolio_rules(con: duckdb.DuckDBPyConnection, portfolio: dict[str, Any]) -> list[dict[str, Any]]:
    if not portfolio.get("mandate_code"):
        return []
    return _query_dicts(con, """
        SELECT mandate_code, mandate_name, asset_class, min_pct, target_pct,
               max_pct, max_single_position_pct, mandate_notes
        FROM mandate_rules
        WHERE mandate_code = ?
        ORDER BY asset_class
    """, [portfolio["mandate_code"]])


def _build_flags(
    con: duckdb.DuckDBPyConnection,
    client_id: str,
    as_of: str,
    portfolios: list[dict[str, Any]],
    holdings: list[dict[str, Any]],
    notes: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    flags: list[DataQualityFlag] = []
    portfolio_ids = {portfolio["portfolio_id"] for portfolio in portfolios}

    holding_instrument_ids = {holding.get("instrument_id") for holding in holdings}
    for instrument_id in sorted(item for item in holding_instrument_ids if item is not None):
        metadata = _query_dicts(con, "SELECT instrument_id, currency, underlying_reference FROM instruments WHERE instrument_id = ?", [instrument_id])
        if not metadata:
            _add_flag(flags, "missing_instrument_metadata", "warning", "A holding references an instrument with no matching instrument metadata.", "holdings_snapshots", snapshot_date=as_of, instrument_id=instrument_id)
        else:
            item = metadata[0]
            if item.get("underlying_reference") is None:
                _add_flag(flags, "missing_underlying_reference", "info", "The instrument has no stored underlying_reference value.", "instruments", instrument_id=instrument_id)
            if item.get("currency") is None:
                _add_flag(flags, "missing_currency", "warning", "The referenced instrument has no currency value.", "instruments", instrument_id=instrument_id)

    for holding in holdings:
        if holding.get("instrument_id") is None:
            _add_flag(flags, "holding_with_no_instrument_id", "warning", "A holding has no instrument identifier.", "holdings_snapshots", snapshot_date=as_of, portfolio_id=holding.get("portfolio_id"))
        if holding.get("valuation_date") is None:
            _add_flag(flags, "missing_valuation_date", "warning", "A holding has no valuation_date value.", "holdings_snapshots", snapshot_date=as_of, portfolio_id=holding.get("portfolio_id"), instrument_id=holding.get("instrument_id"))
        if holding.get("instrument_ccy") is None:
            _add_flag(flags, "missing_currency", "warning", "A holding has no instrument_ccy value.", "holdings_snapshots", snapshot_date=as_of, portfolio_id=holding.get("portfolio_id"), instrument_id=holding.get("instrument_id"))

    holding_portfolios = {holding.get("portfolio_id") for holding in holdings}
    for portfolio_id in sorted(portfolio_ids - holding_portfolios):
        _add_flag(flags, "portfolio_with_no_holdings", "info", "The portfolio has no holdings at the requested snapshot date.", "portfolios", portfolio_id=portfolio_id)

    for note in notes:
        if note.get("note_date") is None:
            _add_flag(flags, "missing_rm_note_date", "warning", "An RM note in the requested period has no note_date value.", "rm_notes", note_id=note.get("note_id"), client_id=client_id)
    for event in events:
        if not event.get("primary_transmission"):
            _add_flag(flags, "incomplete_event_transmission", "info", "An event in the requested period has no primary_transmission value.", "event_log", event_date=event.get("event_date"), event_type=event.get("event_type"))
    return _sort_flags(flags)


def build_client_snapshot(
    con: duckdb.DuckDBPyConnection,
    client_id: str,
    as_of_date: str,
    period_start: str | None = None,
    period_end: str | None = None,
) -> dict:
    """Build a deterministic, JSON-serializable snapshot for one client.

    The connection is only queried; this function never creates, updates, or
    deletes database objects. The CLI opens its connection in read-only mode.
    """
    if not isinstance(client_id, str) or not client_id:
        raise SnapshotInputError("client_id is required and must be a non-empty string.")
    as_of = _parse_iso_date(as_of_date, "as_of_date")
    available_dates = _available_snapshot_dates(con)
    valid_dates = ", ".join(available_dates) or ", ".join(SNAPSHOT_DATES)
    if as_of.isoformat() not in available_dates:
        raise SnapshotInputError(f"Invalid as_of_date {as_of_date!r}; valid available snapshot dates: {valid_dates}.")
    start, end = _resolve_period(as_of, available_dates, period_start, period_end)

    client = _one_dict(con, "SELECT * FROM clients WHERE client_id = ?", [client_id], "client")
    portfolios = _query_dicts(con, """
        SELECT portfolio_id, client_id, portfolio_name, mandate_code, mandate_name,
               service_model, base_currency, inception_date, benchmark
        FROM portfolios
        WHERE client_id = ?
        ORDER BY portfolio_id
    """, [client_id])
    for portfolio in portfolios:
        portfolio["mandate_rules"] = _portfolio_rules(con, portfolio)
    holdings = _query_dicts(con, """
        SELECT h.*, i.underlying_reference, i.sustainability_excluded,
               i.concentration_limit_applies
        FROM holdings_snapshots h
        LEFT JOIN instruments i ON i.instrument_id = h.instrument_id
        WHERE h.client_id = ? AND h.snapshot_date = ?
        ORDER BY h.portfolio_id, h.instrument_id
    """, [client_id, as_of])

    summaries = _query_dicts(con, """
        SELECT p.portfolio_id, p.client_id, p.portfolio_name, p.base_currency,
               COUNT(h.instrument_id) AS holding_count,
               COALESCE(SUM(h.market_value_usd), 0) AS market_value_usd_total,
               COALESCE(SUM(h.market_value_base), 0) AS market_value_base_total,
               COALESCE(SUM(h.weight_pct), 0) AS weight_pct_total
        FROM portfolios p
        LEFT JOIN holdings_snapshots h
          ON h.portfolio_id = p.portfolio_id
         AND h.client_id = p.client_id
         AND h.snapshot_date = ?
        WHERE p.client_id = ?
        GROUP BY p.portfolio_id, p.client_id, p.portfolio_name, p.base_currency
        ORDER BY p.portfolio_id
    """, [as_of, client_id])

    transactions = _query_dicts(con, """
        SELECT transaction_id, trade_date, settlement_date, portfolio_id,
               client_id, transaction_type, instrument_id, instrument_name,
               quantity, price_local, currency, amount, narrative
        FROM transactions
        WHERE client_id = ? AND trade_date >= ? AND trade_date <= ?
        ORDER BY trade_date, transaction_id
    """, [client_id, start, end])
    cash_needs = _query_dicts(con, """
        SELECT need_id, client_id, description, currency, amount, due_from,
               due_to, recurrence, certainty
        FROM planned_cash_needs
        WHERE client_id = ?
        ORDER BY due_from NULLS LAST, need_id
    """, [client_id])
    commitments = _query_dicts(con, """
        SELECT commitment_id, client_id, portfolio_id, fund_name, currency,
               committed, called_to_date, uncalled, expected_call_window
        FROM commitments
        WHERE client_id = ?
        ORDER BY commitment_id
    """, [client_id])
    facilities = _query_dicts(con, """
        SELECT f.facility_id, f.client_id, f.collateral_portfolio_id,
               f.facility_type, f.facility_ccy, f.credit_limit,
               f.interest_rate_pct, f.margin_call_ltv_pct,
               f.utilisation_pct_current, s.snapshot_date, s.drawn,
               s.collateral_market_value, s.lending_value, s.ltv_pct, s.headroom
        FROM credit_facilities f
        LEFT JOIN facility_snapshots s
          ON s.facility_id = f.facility_id AND s.snapshot_date = ?
        WHERE f.client_id = ?
        ORDER BY f.facility_id
    """, [as_of, client_id])
    notes = _query_dicts(con, """
        SELECT note_id, client_id, note_date, rm_id, rm_name, channel, note
        FROM rm_notes
        WHERE client_id = ? AND note_date >= ? AND note_date <= ?
        ORDER BY note_date, note_id
    """, [client_id, start, end])
    events = _query_dicts(con, """
        SELECT event_date, event_type, region, description,
               primary_transmission, severity
        FROM event_log
        WHERE event_date >= ? AND event_date <= ?
        ORDER BY event_date, event_type, region, description,
                 primary_transmission, severity
    """, [start, end])

    source_references: list[dict[str, Any]] = [_ref("clients", client_id=client_id)]
    source_references.extend(_ref("portfolios", client_id=client_id, portfolio_id=item["portfolio_id"]) for item in portfolios)
    source_references.extend(_ref("mandate_rules", mandate_code=item["mandate_code"]) for item in portfolios if item.get("mandate_code"))
    source_references.extend(_ref("holdings_snapshots", snapshot_date=as_of, portfolio_id=item["portfolio_id"], instrument_id=item["instrument_id"]) for item in holdings)
    source_references.extend(_ref("transactions", transaction_id=item["transaction_id"]) for item in transactions)
    source_references.extend(_ref("planned_cash_needs", need_id=item["need_id"]) for item in cash_needs)
    source_references.extend(_ref("commitments", commitment_id=item["commitment_id"]) for item in commitments)
    source_references.extend(_ref("credit_facilities", facility_id=item["facility_id"], client_id=client_id) for item in facilities)
    source_references.extend(_ref("facility_snapshots", facility_id=item["facility_id"], snapshot_date=as_of) for item in facilities)
    source_references.extend(_ref("rm_notes", note_id=item["note_id"]) for item in notes)
    source_references.extend(_ref("event_log", event_date=item["event_date"], event_type=item["event_type"], region=item["region"]) for item in events)

    snapshot = {
        "snapshot_metadata": {
            "client_id": client_id,
            "as_of_date": as_of.isoformat(),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "database_path": _database_path(con),
            "calculation_version": CALCULATION_VERSION,
        },
        "client": client,
        "portfolios": portfolios,
        "portfolio_summaries": summaries,
        "holdings": holdings,
        "transactions": transactions,
        "planned_cash_needs": cash_needs,
        "commitments": commitments,
        "credit_facilities": facilities,
        "rm_notes": notes,
        "market_events": events,
        "data_quality_flags": _build_flags(con, client_id, as_of.isoformat(), portfolios, holdings, notes, events),
        "source_references": source_references,
    }
    return _json_value(snapshot)


def build_all_client_snapshots(
    con: duckdb.DuckDBPyConnection,
    as_of_date: str,
    period_start: str | None = None,
    period_end: str | None = None,
) -> list[dict]:
    """Build one snapshot for every client in deterministic client-id order."""
    client_ids = [row[0] for row in con.execute("SELECT client_id FROM clients ORDER BY client_id").fetchall()]
    snapshots = []
    for client_id in client_ids:
        try:
            snapshots.append(build_client_snapshot(con, client_id, as_of_date, period_start, period_end))
        except (duckdb.Error, SnapshotInputError) as exc:
            raise SnapshotInputError(f"client {client_id}: {exc}") from exc
    return snapshots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build read-only JSON client snapshots")
    parser.add_argument("--db-path", default=os.environ.get("WEALTH_DB_PATH") or str(DEFAULT_DB_PATH))
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--client-id")
    scope.add_argument("--all-clients", action="store_true", help="Build snapshots for every client in deterministic order")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--period-start")
    parser.add_argument("--period-end")
    destination = parser.add_mutually_exclusive_group()
    destination.add_argument("--output", help="Exact output JSON path")
    destination.add_argument("--output-root", help="Root under which the canonical output path is created")
    parser.add_argument("--overwrite", action="store_true", help="Intentionally replace an existing generated output")
    args = parser.parse_args(argv)
    if args.overwrite and not (args.output or args.output_root):
        print("Snapshot build failed: --overwrite requires --output or --output-root", file=sys.stderr)
        return 1
    if args.all_clients and args.output:
        print("Snapshot build failed: --all-clients requires --output-root or stdout; one exact --output cannot hold multiple clients", file=sys.stderr)
        return 1
    db_path = Path(args.db_path)
    if not db_path.is_file():
        print(f"Database file does not exist: {db_path}", file=sys.stderr)
        return 1
    try:
        con = duckdb.connect(str(db_path.resolve()), read_only=True)
        try:
            if args.all_clients:
                snapshots = build_all_client_snapshots(con, args.as_of_date, args.period_start, args.period_end)
            else:
                snapshots = [build_client_snapshot(con, args.client_id, args.as_of_date, args.period_start, args.period_end)]
        finally:
            con.close()
    except (duckdb.Error, SnapshotInputError) as exc:
        print(f"Snapshot build failed: {exc}", file=sys.stderr)
        return 1
    try:
        rendered_snapshots = [json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n" for snapshot in snapshots]
        if not (args.output or args.output_root):
            rendered = (
                json.dumps(snapshots, ensure_ascii=False, indent=2) + "\n"
                if args.all_clients else rendered_snapshots[0]
            )
            print(rendered, end="")
            return 0
        if args.output_root:
            output_root = Path(args.output_root)
            outputs = []
            for snapshot in snapshots:
                metadata = snapshot["snapshot_metadata"]
                outputs.append(snapshot_output_path(
                    output_root, metadata["client_id"], metadata["as_of_date"],
                    metadata["period_start"], metadata["period_end"],
                ))
        else:
            outputs = [Path(args.output)]
            output_root = outputs[0].parent
        require_unique_output_paths(outputs)
        if not args.overwrite:
            for output, snapshot in zip(outputs, snapshots):
                if output.exists():
                    metadata = snapshot["snapshot_metadata"]
                    raise OutputExistsError(
                        f"output already exists at {output.resolve()} for snapshot for client "
                        f"{metadata['client_id']}, as_of_date {metadata['as_of_date']}, period "
                        f"{metadata['period_start']} to {metadata['period_end']}; use --overwrite "
                        "if replacement is intentional"
                    )
        for output, snapshot, rendered in zip(outputs, snapshots, rendered_snapshots):
            metadata = snapshot["snapshot_metadata"]
            description = (
                f"snapshot for client {metadata['client_id']}, as_of_date {metadata['as_of_date']}, "
                f"period {metadata['period_start']} to {metadata['period_end']}"
            )
            try:
                atomic_write_json(
                    output, rendered, output_root=output_root, overwrite=args.overwrite,
                    artifact_description=description,
                )
            except OSError as exc:
                raise OutputWriteError(f"{description}: {exc}") from exc
    except (OutputPathError, OutputWriteError, OSError) as exc:
        print(f"Snapshot output failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
