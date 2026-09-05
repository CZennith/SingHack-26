"""Database-integrity checks for the local DuckDB database."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import duckdb

from .build_database import SNAPSHOT_DATES


EXPECTED_COUNTS = {
    "raw_clients": 20, "raw_commitments": 5, "raw_credit_facilities": 5,
    "raw_event_log": 16, "raw_holdings": 1015, "raw_instruments": 62,
    "raw_mandates": 48, "raw_market_context": 115,
    "raw_planned_cash_needs": 20, "raw_portfolios": 24,
    "raw_transactions": 393, "raw_rm_notes": 28,
    "clients": 20, "portfolios": 24, "instruments": 62,
    "mandate_rules": 48, "holdings_snapshots": 1015, "transactions": 393,
    "commitments": 5, "credit_facilities": 5, "facility_snapshots": 25,
    "planned_cash_needs": 20, "market_context": 115, "event_log": 16,
    "rm_notes": 28, "portfolio_valuations": 120, "instrument_prices": 310,
}


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _scalar(conn: duckdb.DuckDBPyConnection, query: str) -> int:
    return int(conn.execute(query).fetchone()[0])


def _check(name: str, passed: bool, detail: str) -> CheckResult:
    return CheckResult(name, passed, detail)


def _count_checks(conn: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    results = []
    for table, expected in EXPECTED_COUNTS.items():
        actual = _scalar(conn, f"SELECT COUNT(*) FROM {table}")
        results.append(_check(f"row count: {table}", actual == expected, f"expected {expected}, found {actual}"))
    return results


def _key_checks(conn: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    keys = {
        "clients": ["client_id"], "portfolios": ["portfolio_id"],
        "instruments": ["instrument_id"], "transactions": ["transaction_id"],
        "commitments": ["commitment_id"], "credit_facilities": ["facility_id"],
        "planned_cash_needs": ["need_id"], "rm_notes": ["note_id"],
        "holdings_snapshots": ["snapshot_date", "portfolio_id", "instrument_id"],
        "portfolio_valuations": ["portfolio_id", "snapshot_date"],
        "instrument_prices": ["instrument_id", "snapshot_date"],
        "facility_snapshots": ["facility_id", "snapshot_date"],
        "mandate_rules": ["mandate_code", "asset_class"],
        "market_context": ["snapshot_date", "series_id"],
    }
    results = []
    for table, columns in keys.items():
        grouped = ", ".join(columns)
        duplicate_count = _scalar(conn, f"SELECT COUNT(*) FROM (SELECT {grouped}, COUNT(*) AS n FROM {table} GROUP BY {grouped} HAVING COUNT(*) > 1)")
        null_count = _scalar(conn, f"SELECT COUNT(*) FROM {table} WHERE " + " OR ".join(f"{c} IS NULL" for c in columns))
        results.append(_check(f"key uniqueness: {table}", duplicate_count == 0 and null_count == 0, f"duplicate groups {duplicate_count}; null key rows {null_count}"))
    return results


def _foreign_key_checks(conn: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    relationships = [
        ("portfolios.client_id -> clients.client_id", "portfolios", "client_id", "clients", "client_id", ""),
        ("holdings_snapshots.portfolio_id -> portfolios.portfolio_id", "holdings_snapshots", "portfolio_id", "portfolios", "portfolio_id", ""),
        ("holdings_snapshots.client_id -> clients.client_id", "holdings_snapshots", "client_id", "clients", "client_id", ""),
        ("holdings_snapshots.instrument_id -> instruments.instrument_id", "holdings_snapshots", "instrument_id", "instruments", "instrument_id", ""),
        ("transactions.portfolio_id -> portfolios.portfolio_id", "transactions", "portfolio_id", "portfolios", "portfolio_id", ""),
        ("transactions.client_id -> clients.client_id", "transactions", "client_id", "clients", "client_id", ""),
        ("transactions.instrument_id -> instruments.instrument_id", "transactions", "instrument_id", "instruments", "instrument_id", "AND child.instrument_id IS NOT NULL"),
        ("commitments.client_id -> clients.client_id", "commitments", "client_id", "clients", "client_id", ""),
        ("commitments.portfolio_id -> portfolios.portfolio_id", "commitments", "portfolio_id", "portfolios", "portfolio_id", ""),
        ("credit_facilities.client_id -> clients.client_id", "credit_facilities", "client_id", "clients", "client_id", ""),
        ("credit_facilities.collateral_portfolio_id -> portfolios.portfolio_id", "credit_facilities", "collateral_portfolio_id", "portfolios", "portfolio_id", ""),
        ("planned_cash_needs.client_id -> clients.client_id", "planned_cash_needs", "client_id", "clients", "client_id", ""),
        ("rm_notes.client_id -> clients.client_id", "rm_notes", "client_id", "clients", "client_id", ""),
        ("facility_snapshots.facility_id -> credit_facilities.facility_id", "facility_snapshots", "facility_id", "credit_facilities", "facility_id", ""),
        ("portfolio_valuations.portfolio_id -> portfolios.portfolio_id", "portfolio_valuations", "portfolio_id", "portfolios", "portfolio_id", ""),
        ("portfolio_valuations.client_id -> clients.client_id", "portfolio_valuations", "client_id", "clients", "client_id", ""),
        ("instrument_prices.instrument_id -> instruments.instrument_id", "instrument_prices", "instrument_id", "instruments", "instrument_id", ""),
    ]
    results = []
    for name, child_table, child_col, parent_table, parent_col, predicate in relationships:
        orphan_count = _scalar(conn, f"SELECT COUNT(*) FROM {child_table} child LEFT JOIN {parent_table} parent ON child.{child_col} = parent.{parent_col} WHERE parent.{parent_col} IS NULL {predicate}")
        results.append(_check(f"foreign key: {name}", orphan_count == 0, f"orphan rows {orphan_count}"))
    return results


def _type_checks(conn: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    expected = {
        "clients": {"client_id": "VARCHAR", "age": "INTEGER", "total_aum_usd": "DECIMAL", "client_since": "DATE", "kyc_review_due": "DATE"},
        "portfolios": {"portfolio_id": "VARCHAR", "inception_date": "DATE", "aum_usd_current": "DECIMAL"},
        "holdings_snapshots": {"snapshot_date": "DATE", "quantity": "DECIMAL", "price_local": "DECIMAL", "valuation_date": "DATE", "acquired_date": "DATE"},
        "transactions": {"trade_date": "DATE", "settlement_date": "DATE", "amount": "DECIMAL", "transaction_id": "VARCHAR"},
        "commitments": {"committed": "DECIMAL", "called_to_date": "DECIMAL", "uncalled": "DECIMAL"},
        "credit_facilities": {"credit_limit": "DECIMAL", "interest_rate_pct": "DECIMAL", "margin_call_ltv_pct": "DECIMAL"},
        "facility_snapshots": {"snapshot_date": "DATE", "drawn": "DECIMAL", "ltv_pct": "DECIMAL"},
        "planned_cash_needs": {"amount": "DECIMAL", "due_from": "DATE", "due_to": "DATE"},
        "market_context": {"snapshot_date": "DATE", "value": "DECIMAL"},
        "event_log": {"event_date": "DATE"}, "rm_notes": {"note_date": "DATE"},
        "portfolio_valuations": {"snapshot_date": "DATE", "aum": "DECIMAL"},
        "instrument_prices": {"snapshot_date": "DATE", "price": "DECIMAL"},
    }
    results = []
    for table, columns in expected.items():
        for column, expected_prefix in columns.items():
            actual = conn.execute("SELECT data_type FROM information_schema.columns WHERE table_name = ? AND column_name = ?", [table, column]).fetchone()
            actual_type = actual[0] if actual else "MISSING"
            passed = actual_type == expected_prefix or actual_type.startswith(expected_prefix + "(")
            results.append(_check(f"data type: {table}.{column}", passed, f"expected {expected_prefix}, found {actual_type}"))
    return results


def _date_checks(conn: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    expected = set(SNAPSHOT_DATES)
    results = []
    for table in ("holdings_snapshots", "portfolio_valuations", "instrument_prices", "facility_snapshots", "market_context"):
        actual = {row[0].isoformat() for row in conn.execute(f"SELECT DISTINCT snapshot_date FROM {table} ORDER BY snapshot_date").fetchall()}
        results.append(_check(f"snapshot dates: {table}", actual == expected, f"expected {sorted(expected)}, found {sorted(actual)}"))
    for table, column in (("clients", "client_since"), ("clients", "kyc_review_due"), ("portfolios", "inception_date"), ("transactions", "trade_date"), ("transactions", "settlement_date"), ("planned_cash_needs", "due_from"), ("planned_cash_needs", "due_to"), ("event_log", "event_date"), ("rm_notes", "note_date")):
        invalid = _scalar(conn, f"SELECT COUNT(*) FROM {table} WHERE {column} IS NOT NULL AND typeof({column}) <> 'DATE'")
        results.append(_check(f"date column: {table}.{column}", invalid == 0, f"invalid typed rows {invalid}"))
    return results


def _normalized_checks(conn: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    results = []
    for table, expected in (("portfolio_valuations", 120), ("instrument_prices", 310), ("facility_snapshots", 25)):
        actual = _scalar(conn, f"SELECT COUNT(*) FROM {table}")
        results.append(_check(f"wide-to-long completeness: {table}", actual == expected, f"expected {expected}, found {actual}"))
    return results


def _view_checks(conn: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    views = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' AND table_type = 'VIEW'").fetchall()
    return [_check("scope: no analytical views", not views, f"found {len(views)} view(s)")]


def _fidelity_checks(conn: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    # The raw layer is the comparison baseline. NULLIF maps a CSV blank to
    # the curated NULL while leaving all non-empty source text untouched.
    queries = [
        ("fidelity: clients", "SELECT COUNT(*) FROM raw_clients r JOIN clients c ON r.client_id = c.client_id WHERE c.client_name IS DISTINCT FROM NULLIF(r.client_name, '') OR c.age IS DISTINCT FROM TRY_CAST(NULLIF(r.age, '') AS INTEGER) OR c.total_aum_usd IS DISTINCT FROM TRY_CAST(NULLIF(r.total_aum_usd, '') AS DECIMAL(38,18)) OR c.client_since IS DISTINCT FROM TRY_CAST(NULLIF(r.client_since, '') AS DATE)"),
        ("fidelity: portfolios", "SELECT COUNT(*) FROM raw_portfolios r JOIN portfolios c ON r.portfolio_id = c.portfolio_id WHERE c.client_id IS DISTINCT FROM NULLIF(r.client_id, '') OR c.inception_date IS DISTINCT FROM TRY_CAST(NULLIF(r.inception_date, '') AS DATE) OR c.aum_usd_current IS DISTINCT FROM TRY_CAST(NULLIF(r.aum_usd_current, '') AS DECIMAL(38,18))"),
        ("fidelity: instruments", "SELECT COUNT(*) FROM raw_instruments r JOIN instruments c ON r.instrument_id = c.instrument_id WHERE c.instrument_name IS DISTINCT FROM NULLIF(r.instrument_name, '') OR c.underlying_reference IS DISTINCT FROM NULLIF(r.underlying_reference, '')"),
        ("fidelity: holdings", "SELECT COUNT(*) FROM raw_holdings r JOIN holdings_snapshots c ON c.snapshot_date = TRY_CAST(NULLIF(r.snapshot_date, '') AS DATE) AND c.portfolio_id = r.portfolio_id AND c.instrument_id = r.instrument_id WHERE c.client_id IS DISTINCT FROM r.client_id OR c.quantity IS DISTINCT FROM TRY_CAST(NULLIF(r.quantity, '') AS DECIMAL(38,18)) OR c.price_local IS DISTINCT FROM TRY_CAST(NULLIF(r.price_local, '') AS DECIMAL(38,18)) OR c.market_value_base IS DISTINCT FROM TRY_CAST(NULLIF(r.market_value_base, '') AS DECIMAL(38,18)) OR c.valuation_date IS DISTINCT FROM TRY_CAST(NULLIF(r.valuation_date, '') AS DATE)"),
        ("fidelity: transactions", "SELECT COUNT(*) FROM raw_transactions r JOIN transactions c ON c.transaction_id = r.transaction_id WHERE c.trade_date IS DISTINCT FROM TRY_CAST(NULLIF(r.trade_date, '') AS DATE) OR c.settlement_date IS DISTINCT FROM TRY_CAST(NULLIF(r.settlement_date, '') AS DATE) OR c.instrument_id IS DISTINCT FROM NULLIF(r.instrument_id, '') OR c.amount IS DISTINCT FROM TRY_CAST(NULLIF(r.amount, '') AS DECIMAL(38,18))"),
        ("fidelity: commitments", "SELECT COUNT(*) FROM raw_commitments r JOIN commitments c ON c.commitment_id = r.commitment_id WHERE c.client_id IS DISTINCT FROM r.client_id OR c.committed IS DISTINCT FROM TRY_CAST(NULLIF(r.committed, '') AS DECIMAL(38,18))"),
        ("fidelity: facility static fields", "SELECT COUNT(*) FROM raw_credit_facilities r JOIN credit_facilities c ON c.facility_id = r.facility_id WHERE c.client_id IS DISTINCT FROM r.client_id OR c.credit_limit IS DISTINCT FROM TRY_CAST(NULLIF(r.credit_limit, '') AS DECIMAL(38,18)) OR c.margin_call_ltv_pct IS DISTINCT FROM TRY_CAST(NULLIF(r.margin_call_ltv_pct, '') AS DECIMAL(38,18))"),
        ("fidelity: mandate rules", "SELECT COUNT(*) FROM raw_mandates r JOIN mandate_rules c ON c.mandate_code = r.mandate_code AND c.asset_class = r.asset_class WHERE c.mandate_name IS DISTINCT FROM NULLIF(r.mandate_name, '') OR c.min_pct IS DISTINCT FROM TRY_CAST(NULLIF(r.min_pct, '') AS DECIMAL(38,18)) OR c.mandate_notes IS DISTINCT FROM NULLIF(r.mandate_notes, '')"),
        ("fidelity: planned cash needs", "SELECT COUNT(*) FROM raw_planned_cash_needs r JOIN planned_cash_needs c ON c.need_id = r.need_id WHERE c.client_id IS DISTINCT FROM r.client_id OR c.description IS DISTINCT FROM NULLIF(r.description, '') OR c.amount IS DISTINCT FROM TRY_CAST(NULLIF(r.amount, '') AS DECIMAL(38,18)) OR c.due_from IS DISTINCT FROM TRY_CAST(NULLIF(r.due_from, '') AS DATE)"),
        ("fidelity: market context", "SELECT COUNT(*) FROM raw_market_context r JOIN market_context c ON c.snapshot_date = TRY_CAST(NULLIF(r.snapshot_date, '') AS DATE) AND c.series_id = r.series_id WHERE c.series_name IS DISTINCT FROM NULLIF(r.series_name, '') OR c.value IS DISTINCT FROM TRY_CAST(NULLIF(r.value, '') AS DECIMAL(38,18)) OR c.snapshot_label IS DISTINCT FROM NULLIF(r.snapshot_label, '')"),
        ("fidelity: event log", "SELECT COUNT(*) FROM (SELECT event_date, event_type, region, description, primary_transmission, severity FROM raw_event_log EXCEPT ALL SELECT CAST(event_date AS VARCHAR), event_type, region, description, primary_transmission, severity FROM event_log)"),
        ("fidelity: RM notes", "SELECT COUNT(*) FROM raw_rm_notes r JOIN rm_notes c ON c.note_id = r.note_id WHERE c.client_id IS DISTINCT FROM r.client_id OR c.note_date IS DISTINCT FROM TRY_CAST(NULLIF(r.note_date, '') AS DATE) OR c.note IS DISTINCT FROM NULLIF(r.note, '')"),
        ("fidelity: facility snapshots", "SELECT COUNT(*) FROM raw_credit_facilities r JOIN facility_snapshots c ON c.facility_id = r.facility_id WHERE c.drawn IS DISTINCT FROM TRY_CAST(NULLIF(CASE WHEN c.snapshot_date = DATE '2025-12-31' THEN r.\"drawn_2025-12-31\" WHEN c.snapshot_date = DATE '2026-02-27' THEN r.\"drawn_2026-02-27\" WHEN c.snapshot_date = DATE '2026-03-31' THEN r.\"drawn_2026-03-31\" WHEN c.snapshot_date = DATE '2026-06-30' THEN r.\"drawn_2026-06-30\" ELSE r.\"drawn_2026-08-26\" END, '') AS DECIMAL(38,18)) OR c.headroom IS DISTINCT FROM TRY_CAST(NULLIF(CASE WHEN c.snapshot_date = DATE '2025-12-31' THEN r.\"headroom_2025-12-31\" WHEN c.snapshot_date = DATE '2026-02-27' THEN r.\"headroom_2026-02-27\" WHEN c.snapshot_date = DATE '2026-03-31' THEN r.\"headroom_2026-03-31\" WHEN c.snapshot_date = DATE '2026-06-30' THEN r.\"headroom_2026-06-30\" ELSE r.\"headroom_2026-08-26\" END, '') AS DECIMAL(38,18))"),
        ("fidelity: portfolio valuations", "SELECT COUNT(*) FROM raw_portfolios r JOIN portfolio_valuations c ON c.portfolio_id = r.portfolio_id WHERE c.client_id IS DISTINCT FROM r.client_id OR c.aum IS DISTINCT FROM TRY_CAST(NULLIF(CASE WHEN c.snapshot_date = DATE '2025-12-31' THEN r.\"aum_2025-12-31\" WHEN c.snapshot_date = DATE '2026-02-27' THEN r.\"aum_2026-02-27\" WHEN c.snapshot_date = DATE '2026-03-31' THEN r.\"aum_2026-03-31\" WHEN c.snapshot_date = DATE '2026-06-30' THEN r.\"aum_2026-06-30\" ELSE r.\"aum_2026-08-26\" END, '') AS DECIMAL(38,18))"),
        ("fidelity: instrument prices", "SELECT COUNT(*) FROM raw_instruments r JOIN instrument_prices c ON c.instrument_id = r.instrument_id WHERE c.price IS DISTINCT FROM TRY_CAST(NULLIF(CASE WHEN c.snapshot_date = DATE '2025-12-31' THEN r.\"price_2025-12-31\" WHEN c.snapshot_date = DATE '2026-02-27' THEN r.\"price_2026-02-27\" WHEN c.snapshot_date = DATE '2026-03-31' THEN r.\"price_2026-03-31\" WHEN c.snapshot_date = DATE '2026-06-30' THEN r.\"price_2026-06-30\" ELSE r.\"price_2026-08-26\" END, '') AS DECIMAL(38,18))"),
    ]
    results = []
    for name, query in queries:
        mismatches = _scalar(conn, query)
        results.append(_check(name, mismatches == 0, f"representative mismatched rows {mismatches}"))
    return results


def _null_checks(conn: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    raw_nulls = _scalar(conn, "SELECT COUNT(*) FROM raw_transactions WHERE instrument_id = ''")
    curated_nulls = _scalar(conn, "SELECT COUNT(*) FROM transactions WHERE instrument_id IS NULL")
    results = [_check("null preservation: transaction instrument_id", raw_nulls == 65 and curated_nulls == 65, f"raw blank {raw_nulls}; curated NULL {curated_nulls}")]
    for table, column, expected in (("clients", "age", 1), ("holdings_snapshots", "sector", 5), ("holdings_snapshots", "avg_cost_local", 5), ("instruments", "underlying_reference", 53)):
        actual = _scalar(conn, f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")
        results.append(_check(f"null preservation: {table}.{column}", actual == expected, f"expected {expected}, found {actual}"))
    return results


def run_validation(conn: duckdb.DuckDBPyConnection) -> list[CheckResult]:
    """Run all integrity checks and return structured results."""
    return [*_count_checks(conn), *_key_checks(conn), *_foreign_key_checks(conn), *_type_checks(conn), *_date_checks(conn), *_normalized_checks(conn), *_fidelity_checks(conn), *_null_checks(conn), *_view_checks(conn)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default="db/wealth.duckdb")
    args = parser.parse_args(argv)
    try:
        conn = duckdb.connect(str(Path(args.db_path).resolve()), read_only=True)
    except Exception as exc:
        print(f"Could not open database: {exc}", file=sys.stderr)
        return 1
    try:
        results = run_validation(conn)
    finally:
        conn.close()
    failed = [result for result in results if not result.passed]
    for result in results:
        print(f"{'PASS' if result.passed else 'FAIL'}  {result.name}: {result.detail}")
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
