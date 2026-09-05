from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from backend.wealth_service import (
    UnknownClientError,
    UnsupportedDateError,
    WealthServiceError,
    get_clients,
    get_exposure,
    get_exposure_changes,
    get_market_context,
    get_snapshot,
    get_snapshot_dates,
)
from src.contracts.validation import validate_result


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "db" / "wealth.duckdb"


@pytest.mark.integration
def test_read_only_service_covers_every_client_and_supported_date_without_writes():
    before_mtime = DB_PATH.stat().st_mtime_ns
    dates_response = get_snapshot_dates(DB_PATH)
    json.dumps(dates_response)
    dates = [item["as_of_date"] for item in dates_response["dates"]]
    assert dates == sorted(dates)
    assert dates

    clients_response = get_clients(DB_PATH, dates[-1])
    json.dumps(clients_response)
    client_ids = [client["client_id"] for client in clients_response["clients"]]
    assert len(client_ids) == 20
    assert clients_response["response_metadata"]["as_of_date"] == dates[-1]

    for client_id in client_ids:
        for as_of_date in dates:
            snapshot = get_snapshot(DB_PATH, client_id, as_of_date, as_of_date, as_of_date)["snapshot"]
            metadata = snapshot["snapshot_metadata"]
            assert metadata["client_id"] == client_id
            assert metadata["as_of_date"] == as_of_date
            assert all(item["client_id"] == client_id for item in snapshot["holdings"])
            assert all(item["client_id"] == client_id for item in snapshot["transactions"])
            assert all(item["client_id"] == client_id for item in snapshot["rm_notes"])

        exposure = get_exposure(DB_PATH, client_id, dates[-1], dates[-2], dates[-1])
        assert exposure["response_metadata"]["client_id"] == client_id
        assert all(ref["keys"]["client_id"] == client_id for ref in exposure["exposure"]["source_references"])

        changes = get_exposure_changes(
            DB_PATH, client_id, dates[-1], dates[-2], dates[-2], dates[-1]
        )
        result = validate_result(changes["result"])
        assert result.result_metadata.client_id == client_id
        assert all(fact.scope.client_id == client_id for fact in result.facts)
        assert all(evidence.source_keys["client_id"] == client_id for evidence in result.evidence)
        assert not any(
            other_id in json.dumps(changes["result"], sort_keys=True)
            for other_id in client_ids
            if other_id != client_id
        )

    market_context = get_market_context(DB_PATH, dates[-1])
    json.dumps(market_context)
    assert market_context["response_metadata"]["as_of_date"] == dates[-1]
    assert all(record["snapshot_date"] == dates[-1] for record in market_context["records"])

    read_only = duckdb.connect(str(DB_PATH.resolve()), read_only=True)
    try:
        with pytest.raises(duckdb.Error):
            read_only.execute("CREATE TABLE integration_service_write_probe (probe INTEGER)")
    finally:
        read_only.close()
    assert DB_PATH.stat().st_mtime_ns == before_mtime


@pytest.mark.integration
def test_read_only_service_rejects_unknown_clients_and_invalid_dates():
    with pytest.raises(UnknownClientError):
        get_snapshot_dates(DB_PATH, "CL-DOES-NOT-EXIST")
    with pytest.raises(UnknownClientError):
        get_snapshot(DB_PATH, "CL-DOES-NOT-EXIST", "2026-08-26")
    with pytest.raises(UnsupportedDateError):
        get_clients(DB_PATH, "2026-08-27")
    with pytest.raises(WealthServiceError, match="real ISO date"):
        get_market_context(DB_PATH, "2026-02-30")
