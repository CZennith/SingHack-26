from __future__ import annotations

import subprocess
from pathlib import Path

import duckdb
import pytest

from api.health import health_payload
from backend.config import ConfigurationError, load_runtime_config


ROOT = Path(__file__).resolve().parents[2]


def test_frontend_build_succeeds_from_repository_root():
    completed = subprocess.run(
        ["npm", "run", "build"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert (ROOT / "dist" / "index.html").is_file()


def test_vercel_surface_health_imports_and_keeps_private_data_out_of_bundle():
    assert health_payload() == {"status": "ok"}
    old_wrapper_name = "singhacks-" + "jb-wealth-intelligence"
    assert not (ROOT / old_wrapper_name).exists()

    vercel_ignore = (ROOT / ".vercelignore").read_text(encoding="utf-8")
    for pattern in ("data/*.csv", "data/*.json", "db/*.duckdb", "outputs/"):
        assert pattern in vercel_ignore
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert 'DEMO_MODE="true"' in env_example
    assert "WEALTH_DB_PATH" in env_example

    text_suffixes = {".py", ".ts", ".tsx", ".json", ".md", ".toml", ".txt", ".html"}
    excluded_parts = {".git", ".venv", "node_modules", "dist", ".pytest_cache", "outputs"}
    absolute_home_prefix = "/" + "home/"
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in text_suffixes or excluded_parts.intersection(path.parts):
            continue
        content = path.read_text(encoding="utf-8")
        assert old_wrapper_name not in content
        assert absolute_home_prefix not in content


def test_local_duckdb_access_is_read_only():
    db_path = ROOT / "db" / "wealth.duckdb"
    connection = duckdb.connect(str(db_path.resolve()), read_only=True)
    try:
        try:
            connection.execute("CREATE TABLE deployment_smoke_probe (probe INTEGER)")
        except duckdb.Error:
            pass
        else:
            raise AssertionError("local deployment smoke test opened DuckDB with write access")
    finally:
        connection.close()


def test_runtime_configuration_defaults_to_demo_and_requires_private_path():
    demo = load_runtime_config({"DEMO_MODE": "true", "WEALTH_DB_PATH": ""})
    assert demo.demo_mode is True
    assert demo.wealth_db_path is None

    private = load_runtime_config({"DEMO_MODE": "false", "WEALTH_DB_PATH": "db/private.duckdb"})
    assert private.demo_mode is False
    assert private.wealth_db_path == (ROOT / "db" / "private.duckdb").resolve()

    with pytest.raises(ConfigurationError, match="WEALTH_DB_PATH"):
        load_runtime_config({"DEMO_MODE": "false", "WEALTH_DB_PATH": ""})
