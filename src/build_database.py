"""Build the local DuckDB database from the read-only source files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

import duckdb


SNAPSHOT_DATES = ("2025-12-31", "2026-02-27", "2026-03-31", "2026-06-30", "2026-08-26")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = PROJECT_ROOT / "db" / "wealth.duckdb"
CSV_SOURCES = {
    "raw_clients": "clients.csv",
    "raw_commitments": "commitments.csv",
    "raw_credit_facilities": "credit_facilities.csv",
    "raw_event_log": "event_log.csv",
    "raw_holdings": "holdings.csv",
    "raw_instruments": "instruments.csv",
    "raw_mandates": "mandates.csv",
    "raw_market_context": "market_context.csv",
    "raw_planned_cash_needs": "planned_cash_needs.csv",
    "raw_portfolios": "portfolios.csv",
    "raw_transactions": "transactions.csv",
}
RAW_COLUMNS = {
    "raw_clients": ["client_id", "client_name", "age", "gender", "nationality", "country_of_residence", "tax_domicile", "booking_centre", "rm_id", "rm_name", "rm_desk", "base_currency", "wealth_band", "total_aum_usd", "life_stage", "source_of_wealth", "risk_profile", "risk_tolerance_score", "investment_horizon_years", "liquidity_needs", "objectives", "client_since", "kyc_review_due", "pep_status", "reporting_language"],
    "raw_commitments": ["commitment_id", "client_id", "portfolio_id", "fund_name", "currency", "committed", "called_to_date", "uncalled", "expected_call_window"],
    "raw_credit_facilities": ["facility_id", "client_id", "collateral_portfolio_id", "facility_type", "facility_ccy", "credit_limit", "interest_rate_pct", "margin_call_ltv_pct", *[f"{field}_{d}" for d in SNAPSHOT_DATES for field in ("drawn", "collateral_market_value", "lending_value", "ltv_pct", "headroom")], "utilisation_pct_current"],
    "raw_event_log": ["event_date", "event_type", "region", "description", "primary_transmission", "severity"],
    "raw_holdings": ["snapshot_date", "portfolio_id", "client_id", "instrument_id", "instrument_name", "asset_class", "sub_asset_class", "sector", "region", "instrument_ccy", "quantity", "price_local", "market_value_local", "portfolio_ccy", "market_value_base", "market_value_usd", "weight_pct", "avg_cost_local", "cost_basis_base", "unrealised_pnl_base", "unrealised_pnl_pct", "lending_value_base", "advance_rate_pct", "liquidity_tier", "valuation_date", "acquired_date"],
    "raw_instruments": ["instrument_id", "instrument_name", "asset_class", "sub_asset_class", "sector", "region", "currency", "liquidity_tier", "underlying_reference", "sustainability_excluded", "concentration_limit_applies", *[f"price_{d}" for d in SNAPSHOT_DATES]],
    "raw_mandates": ["mandate_code", "mandate_name", "asset_class", "min_pct", "target_pct", "max_pct", "max_single_position_pct", "mandate_notes"],
    "raw_market_context": ["snapshot_date", "series_id", "series_name", "category", "unit", "value", "snapshot_label"],
    "raw_planned_cash_needs": ["need_id", "client_id", "description", "currency", "amount", "due_from", "due_to", "recurrence", "certainty"],
    "raw_portfolios": ["portfolio_id", "client_id", "portfolio_name", "mandate_code", "mandate_name", "service_model", "base_currency", "inception_date", "benchmark", *[f"aum_{d}" for d in SNAPSHOT_DATES], "aum_usd_current"],
    "raw_transactions": ["transaction_id", "trade_date", "settlement_date", "portfolio_id", "client_id", "transaction_type", "instrument_id", "instrument_name", "quantity", "price_local", "currency", "amount", "narrative"],
    "raw_rm_notes": ["note_id", "client_id", "note_date", "rm_id", "rm_name", "channel", "note"],
}


class DataParseError(ValueError):
    """An input value could not be converted to the curated type."""


def _blank(value: str | None) -> str | None:
    return None if value is None or value == "" else value


def _parse_decimal(value: str | None, filename: str, column: str, row: int) -> Decimal | None:
    value = _blank(value)
    if value is None:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise DataParseError(f"{filename}, column {column}, row {row}: invalid value {value!r}; {exc}") from exc


def _parse_int(value: str | None, filename: str, column: str, row: int) -> int | None:
    value = _blank(value)
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError) as exc:
        raise DataParseError(f"{filename}, column {column}, row {row}: invalid value {value!r}; {exc}") from exc


def _parse_date(value: str | None, filename: str, column: str, row: int) -> date | None:
    value = _blank(value)
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise DataParseError(f"{filename}, column {column}, row {row}: invalid value {value!r}; {exc}") from exc


def _text(value: str | None) -> str | None:
    return _blank(value)


def read_csv_source(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise DataParseError(f"{path.name}: missing header row")
            expected = RAW_COLUMNS[f"raw_{path.stem}"]
            if reader.fieldnames != expected:
                raise DataParseError(f"{path.name}: expected columns {expected!r}, found {reader.fieldnames!r}")
            rows: list[dict[str, Any]] = []
            for row in reader:
                if None in row:
                    raise DataParseError(f"{path.name}, row {reader.line_num}: extra fields {row[None]!r}")
                rows.append({"__rownum": reader.line_num, **row})
            return rows
    except UnicodeDecodeError as exc:
        raise DataParseError(f"{path.name}: could not decode as UTF-8; {exc}") from exc
    except OSError as exc:
        raise DataParseError(f"{path.name}: could not read source; {exc}") from exc


def read_notes_source(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DataParseError(f"{path.name}: could not read JSON source; {exc}") from exc
    if not isinstance(data, list):
        raise DataParseError(f"{path.name}: expected a JSON array")
    expected = RAW_COLUMNS["raw_rm_notes"]
    rows = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict) or list(item.keys()) != expected:
            raise DataParseError(f"{path.name}, row {index + 1}: expected keys {expected!r}")
        rows.append({"__rownum": index + 1, **item})
    return rows


def _raw_value(value: Any) -> Any:
    # CSV blanks remain empty strings in raw tables. JSON null remains SQL NULL.
    return value


def _insert_rows(conn: duckdb.DuckDBPyConnection, table: str, columns: list[str], rows: Iterable[dict[str, Any]]) -> None:
    placeholders = ", ".join("?" for _ in columns)
    quoted = ", ".join(f'"{column}"' for column in columns)
    conn.executemany(f"INSERT INTO {table} ({quoted}) VALUES ({placeholders})", [[_raw_value(row.get(column)) for column in columns] for row in rows])


def _curated_rows(table: str, rows: list[dict[str, Any]], filename: str) -> list[list[Any]]:
    text = lambda row, col: _text(row.get(col))
    if table == "clients":
        cols = RAW_COLUMNS["raw_clients"]
        return [[text(r, c) if c not in {"age", "total_aum_usd", "risk_tolerance_score", "investment_horizon_years", "client_since", "kyc_review_due"} else ({"age": _parse_int, "total_aum_usd": _parse_decimal, "risk_tolerance_score": _parse_int, "investment_horizon_years": _parse_int, "client_since": _parse_date, "kyc_review_due": _parse_date}[c])(r.get(c), filename, c, r["__rownum"]) for c in cols] for r in rows]
    if table == "portfolios":
        cols = ["portfolio_id", "client_id", "portfolio_name", "mandate_code", "mandate_name", "service_model", "base_currency", "inception_date", "benchmark", "aum_usd_current"]
        return [[(_parse_date if c == "inception_date" else _parse_decimal if c == "aum_usd_current" else text)(r.get(c), filename, c, r["__rownum"]) if c in {"inception_date", "aum_usd_current"} else text(r, c) for c in cols] for r in rows]
    if table == "instruments":
        return [[text(r, c) for c in RAW_COLUMNS["raw_instruments"][:11]] for r in rows]
    if table == "mandate_rules":
        return [[text(r, c) if c not in {"min_pct", "target_pct", "max_pct", "max_single_position_pct"} else _parse_decimal(r.get(c), filename, c, r["__rownum"]) for c in RAW_COLUMNS["raw_mandates"]] for r in rows]
    if table == "holdings_snapshots":
        date_cols = {"snapshot_date", "valuation_date", "acquired_date"}
        numeric_cols = {"quantity", "price_local", "market_value_local", "market_value_base", "market_value_usd", "weight_pct", "avg_cost_local", "cost_basis_base", "unrealised_pnl_base", "unrealised_pnl_pct", "lending_value_base", "advance_rate_pct"}
        cols = RAW_COLUMNS["raw_holdings"]
        return [[(_parse_date if c in date_cols else _parse_decimal if c in numeric_cols else text)(r.get(c), filename, c, r["__rownum"]) if c in date_cols or c in numeric_cols else text(r, c) for c in cols] for r in rows]
    if table == "transactions":
        numeric_cols = {"quantity", "price_local", "amount"}
        date_cols = {"trade_date", "settlement_date"}
        cols = RAW_COLUMNS["raw_transactions"]
        return [[(_parse_date if c in date_cols else _parse_decimal if c in numeric_cols else text)(r.get(c), filename, c, r["__rownum"]) if c in date_cols or c in numeric_cols else text(r, c) for c in cols] for r in rows]
    if table == "commitments":
        numeric_cols = {"committed", "called_to_date", "uncalled"}
        return [[_parse_decimal(r.get(c), filename, c, r["__rownum"]) if c in numeric_cols else text(r, c) for c in RAW_COLUMNS["raw_commitments"]] for r in rows]
    if table == "credit_facilities":
        cols = ["facility_id", "client_id", "collateral_portfolio_id", "facility_type", "facility_ccy", "credit_limit", "interest_rate_pct", "margin_call_ltv_pct", "utilisation_pct_current"]
        numeric_cols = set(cols[5:])
        return [[_parse_decimal(r.get(c), filename, c, r["__rownum"]) if c in numeric_cols else text(r, c) for c in cols] for r in rows]
    if table == "planned_cash_needs":
        cols = RAW_COLUMNS["raw_planned_cash_needs"]
        numeric_cols = {"amount"}
        date_cols = {"due_from", "due_to"}
        return [[(_parse_date if c in date_cols else _parse_decimal if c in numeric_cols else text)(r.get(c), filename, c, r["__rownum"]) if c in date_cols or c in numeric_cols else text(r, c) for c in cols] for r in rows]
    if table == "market_context":
        cols = RAW_COLUMNS["raw_market_context"]
        return [[(_parse_date if c == "snapshot_date" else _parse_decimal if c == "value" else text)(r.get(c), filename, c, r["__rownum"]) if c in {"snapshot_date", "value"} else text(r, c) for c in cols] for r in rows]
    if table == "event_log":
        cols = RAW_COLUMNS["raw_event_log"]
        return [[(_parse_date(r.get(c), filename, c, r["__rownum"]) if c == "event_date" else text(r, c)) for c in cols] for r in rows]
    if table == "rm_notes":
        cols = RAW_COLUMNS["raw_rm_notes"]
        return [[(_parse_date(r.get(c), filename, c, r["__rownum"]) if c == "note_date" else text(r, c)) for c in cols] for r in rows]
    raise KeyError(table)


def _insert_curated(conn: duckdb.DuckDBPyConnection, table: str, rows: list[list[Any]]) -> None:
    columns = {
        "clients": RAW_COLUMNS["raw_clients"],
        "portfolios": ["portfolio_id", "client_id", "portfolio_name", "mandate_code", "mandate_name", "service_model", "base_currency", "inception_date", "benchmark", "aum_usd_current"],
        "instruments": RAW_COLUMNS["raw_instruments"][:11],
        "mandate_rules": RAW_COLUMNS["raw_mandates"], "holdings_snapshots": RAW_COLUMNS["raw_holdings"],
        "transactions": RAW_COLUMNS["raw_transactions"], "commitments": RAW_COLUMNS["raw_commitments"],
        "credit_facilities": ["facility_id", "client_id", "collateral_portfolio_id", "facility_type", "facility_ccy", "credit_limit", "interest_rate_pct", "margin_call_ltv_pct", "utilisation_pct_current"],
        "planned_cash_needs": RAW_COLUMNS["raw_planned_cash_needs"], "market_context": RAW_COLUMNS["raw_market_context"],
        "event_log": RAW_COLUMNS["raw_event_log"], "rm_notes": RAW_COLUMNS["raw_rm_notes"],
    }[table]
    _insert_rows(conn, table, columns, [dict(zip(columns, row)) for row in rows])


def _insert_normalized(conn: duckdb.DuckDBPyConnection, portfolio_rows: list[dict[str, Any]], instrument_rows: list[dict[str, Any]], facility_rows: list[dict[str, Any]], filenames: dict[str, str]) -> None:
    pv = []
    for r in portfolio_rows:
        for snapshot in SNAPSHOT_DATES:
            pv.append([_text(r.get("portfolio_id")), _text(r.get("client_id")), date.fromisoformat(snapshot), _parse_decimal(r.get(f"aum_{snapshot}"), filenames["portfolios.csv"], f"aum_{snapshot}", r["__rownum"]), _text(r.get("base_currency"))])
    _insert_rows(conn, "portfolio_valuations", ["portfolio_id", "client_id", "snapshot_date", "aum", "currency"], [dict(zip(["portfolio_id", "client_id", "snapshot_date", "aum", "currency"], row)) for row in pv])

    ip = []
    for r in instrument_rows:
        for snapshot in SNAPSHOT_DATES:
            ip.append([_text(r.get("instrument_id")), date.fromisoformat(snapshot), _parse_decimal(r.get(f"price_{snapshot}"), filenames["instruments.csv"], f"price_{snapshot}", r["__rownum"]), _text(r.get("currency"))])
    _insert_rows(conn, "instrument_prices", ["instrument_id", "snapshot_date", "price", "currency"], [dict(zip(["instrument_id", "snapshot_date", "price", "currency"], row)) for row in ip])

    fs = []
    for r in facility_rows:
        for snapshot in SNAPSHOT_DATES:
            fs.append([_text(r.get("facility_id")), date.fromisoformat(snapshot), *[_parse_decimal(r.get(f"{field}_{snapshot}"), filenames["credit_facilities.csv"], f"{field}_{snapshot}", r["__rownum"]) for field in ("drawn", "collateral_market_value", "lending_value", "ltv_pct", "headroom")]])
    _insert_rows(conn, "facility_snapshots", ["facility_id", "snapshot_date", "drawn", "collateral_market_value", "lending_value", "ltv_pct", "headroom"], [dict(zip(["facility_id", "snapshot_date", "drawn", "collateral_market_value", "lending_value", "ltv_pct", "headroom"], row)) for row in fs])


def build_database(data_dir: str | os.PathLike[str], db_path: str | os.PathLike[str]) -> Path:
    data_dir = Path(data_dir).resolve()
    db_path = Path(db_path).resolve()
    required = [data_dir / filename for filename in [*CSV_SOURCES.values(), "rm_notes.json"]]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing source file(s): " + ", ".join(missing))

    source_rows: dict[str, list[dict[str, Any]]] = {}
    for table, filename in CSV_SOURCES.items():
        source_rows[table] = read_csv_source(data_dir / filename)
    source_rows["raw_rm_notes"] = read_notes_source(data_dir / "rm_notes.json")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{db_path.name}.", suffix=".tmp", dir=db_path.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    # DuckDB creates the database file itself; an empty mkstemp placeholder is
    # not a valid database and cannot be opened by duckdb.connect().
    temp_path.unlink()
    try:
        conn = duckdb.connect(str(temp_path))
        try:
            sql_dir = Path(__file__).resolve().parents[1] / "sql"
            conn.execute((sql_dir / "001_raw_tables.sql").read_text(encoding="utf-8"))
            conn.execute((sql_dir / "002_curated_tables.sql").read_text(encoding="utf-8"))
            loaded_at = datetime.now(timezone.utc).replace(tzinfo=None)
            for table, rows in source_rows.items():
                _insert_rows(conn, table, RAW_COLUMNS[table], rows)
                filename = "rm_notes.json" if table == "raw_rm_notes" else CSV_SOURCES[table]
                sha = hashlib.sha256((data_dir / filename).read_bytes()).hexdigest()
                conn.execute("INSERT INTO ingestion_metadata VALUES (?, ?, ?, ?)", [filename, sha, loaded_at, len(rows)])

            order = ["clients", "portfolios", "instruments", "mandate_rules", "holdings_snapshots", "transactions", "commitments", "credit_facilities", "planned_cash_needs", "market_context", "event_log", "rm_notes"]
            mapping = {"clients": "raw_clients", "portfolios": "raw_portfolios", "instruments": "raw_instruments", "mandate_rules": "raw_mandates", "holdings_snapshots": "raw_holdings", "transactions": "raw_transactions", "commitments": "raw_commitments", "credit_facilities": "raw_credit_facilities", "planned_cash_needs": "raw_planned_cash_needs", "market_context": "raw_market_context", "event_log": "raw_event_log", "rm_notes": "raw_rm_notes"}
            for table in order:
                curated = _curated_rows(table, source_rows[mapping[table]], "rm_notes.json" if table == "rm_notes" else CSV_SOURCES[mapping[table]])
                _insert_curated(conn, table, curated)
            _insert_normalized(conn, source_rows["raw_portfolios"], source_rows["raw_instruments"], source_rows["raw_credit_facilities"], {v: v for v in CSV_SOURCES.values()})
            conn.execute("CHECKPOINT")
        finally:
            conn.close()
        os.replace(temp_path, db_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise
    return db_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Directory containing the source CSV and JSON files")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="Output DuckDB path")
    args = parser.parse_args(argv)
    try:
        path = build_database(args.data_dir, args.db_path)
    except Exception as exc:
        print(f"Database build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
