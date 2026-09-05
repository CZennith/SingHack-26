"""Read-only wealth data endpoint used by the frontend integration."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from backend.config import ConfigurationError, load_runtime_config
from backend.wealth_service import (
    WealthServiceError,
    get_clients,
    get_exposure,
    get_exposure_changes,
    get_market_context,
    get_snapshot,
    get_snapshot_dates,
)


def _configured_db_path():
    config = load_runtime_config()
    if config.demo_mode:
        raise ConfigurationError(
            "wealth data API is disabled in DEMO_MODE; set DEMO_MODE=false and WEALTH_DB_PATH"
        )
    assert config.wealth_db_path is not None
    return config.wealth_db_path


def _one(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key, [])
    return values[0] if values else None


def dispatch(query: dict[str, list[str]]) -> dict:
    resource = _one(query, "resource")
    db_path = _configured_db_path()
    if resource == "dates":
        return get_snapshot_dates(db_path, _one(query, "client_id"))
    if resource == "clients":
        return get_clients(db_path, _one(query, "as_of_date"))
    client_id = _one(query, "client_id")
    as_of_date = _one(query, "as_of_date")
    if resource == "snapshot":
        return get_snapshot(
            db_path,
            client_id or "",
            as_of_date or "",
            _one(query, "period_start"),
            _one(query, "period_end"),
        )
    if resource == "exposure":
        return get_exposure(
            db_path,
            client_id or "",
            as_of_date or "",
            _one(query, "period_start"),
            _one(query, "period_end"),
        )
    if resource == "exposure_changes":
        return get_exposure_changes(
            db_path,
            client_id or "",
            as_of_date or "",
            _one(query, "comparison_date") or "",
            _one(query, "period_start"),
            _one(query, "period_end"),
        )
    if resource == "market_context":
        return get_market_context(db_path, as_of_date or "")
    raise WealthServiceError("resource must be one of dates, clients, snapshot, exposure, exposure_changes, market_context")


class handler(BaseHTTPRequestHandler):
    """Vercel Python handler for the read-only wealth API."""

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        cors_origin = os.environ.get("CORS_ORIGIN", "")
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        cors_origin = os.environ.get("CORS_ORIGIN", "")
        if cors_origin:
            self.send_header("Access-Control-Allow-Origin", cors_origin)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        try:
            query = parse_qs(urlparse(self.path).query, keep_blank_values=True)
            self._send(200, dispatch(query))
        except (ConfigurationError, WealthServiceError, OSError) as exc:
            status = 404 if "unknown client" in str(exc).lower() else 400
            if isinstance(exc, ConfigurationError):
                status = 503
            self._send(status, {"error": {"type": type(exc).__name__, "message": str(exc)}})
        except Exception:
            self._send(500, {"error": {"type": "InternalServerError", "message": "wealth data request failed"}})
