"""Minimal Vercel-compatible health function.

This endpoint intentionally has no database, external-service, or credential
dependency. It is safe for preview deployments and local import smoke tests.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler


def health_payload() -> dict[str, str]:
    return {"status": "ok"}


class handler(BaseHTTPRequestHandler):
    """Vercel Python function handler for GET /api/health."""

    def do_GET(self) -> None:  # noqa: N802 - Vercel's handler protocol uses this name.
        body = json.dumps(health_payload()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        self.send_error(405, "Method Not Allowed")
