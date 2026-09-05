"""CSV-backed data access for the wealth-intelligence backend."""

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


@lru_cache(maxsize=None)
def load_csv(filename: str) -> pd.DataFrame:
    """Load each source file once per process; use copy() before mutating it."""
    return pd.read_csv(DATA_DIR / filename)


@lru_cache(maxsize=None)
def load_json(filename: str) -> list[dict[str, Any]]:
    """Load a JSON source once per process."""
    with (DATA_DIR / filename).open(encoding="utf-8") as source:
        payload: Any = json.load(source)
    if not isinstance(payload, list):
        raise ValueError(f"Expected {filename} to contain a JSON list.")
    return payload


def _for_client(filename: str, client_id: str) -> pd.DataFrame:
    """Return an independent client-scoped frame safe for service mutation."""
    frame = load_csv(filename)
    return frame.loc[frame["client_id"] == client_id].copy()


def reload_data() -> None:
    """Clear process-local CSV/JSON caches; useful after source-data refreshes."""
    load_csv.cache_clear()
    load_json.cache_clear()


def get_clients() -> pd.DataFrame:
    return load_csv("clients.csv").copy()


def get_client(client_id: str) -> pd.Series | None:
    clients = load_csv("clients.csv")
    matches = clients.loc[clients["client_id"] == client_id]
    return None if matches.empty else matches.iloc[0].copy()


def get_client_portfolios(client_id: str) -> pd.DataFrame:
    return _for_client("portfolios.csv", client_id)


def get_client_holdings(client_id: str) -> pd.DataFrame:
    return _for_client("holdings.csv", client_id)


def get_client_facilities(client_id: str) -> pd.DataFrame:
    return _for_client("credit_facilities.csv", client_id)


def get_client_commitments(client_id: str) -> pd.DataFrame:
    return _for_client("commitments.csv", client_id)


def get_client_cash_needs(client_id: str) -> pd.DataFrame:
    return _for_client("planned_cash_needs.csv", client_id)


def get_client_transactions(client_id: str) -> pd.DataFrame:
    return _for_client("transactions.csv", client_id)


def get_client_rm_notes(client_id: str) -> pd.DataFrame:
    notes = pd.DataFrame(load_json("rm_notes.json"))
    if notes.empty:
        return notes
    return notes.loc[notes["client_id"] == client_id].copy()


def get_instruments() -> pd.DataFrame:
    return load_csv("instruments.csv").copy()


def get_instruments_for_holdings(holdings: pd.DataFrame) -> pd.DataFrame:
    """Return instrument metadata for a holdings frame, keyed by instrument_id."""
    if holdings.empty:
        return get_instruments().iloc[0:0].copy()
    instrument_ids = holdings["instrument_id"].dropna().unique()
    return get_instruments().loc[lambda frame: frame["instrument_id"].isin(instrument_ids)].copy()


def get_mandates() -> pd.DataFrame:
    return load_csv("mandates.csv").copy()


def get_mandate(mandate_code: str) -> pd.DataFrame:
    return get_mandates().loc[lambda frame: frame["mandate_code"] == mandate_code].copy()


def get_market_context() -> pd.DataFrame:
    return load_csv("market_context.csv").copy()


def get_market_context_for_snapshot(snapshot_date: str) -> pd.DataFrame:
    return get_market_context().loc[lambda frame: frame["snapshot_date"] == snapshot_date].copy()


def get_event_log() -> pd.DataFrame:
    return load_csv("event_log.csv").copy()
