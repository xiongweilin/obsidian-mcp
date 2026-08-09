"""Guard against non-compatible drift of the public tools/list schema.

The snapshot in ``tests/schema-snapshot.json`` is the human-approved contract.
When the wire schema changes, this test fails and a human must confirm the
change is intentional, then regenerate the snapshot with
``uv run python scripts/update_schema_snapshot.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp_stdio_client import StdioMCPClient

pytestmark = pytest.mark.contract


def _canonical(value: object) -> object:
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    return value


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_tools_list_schema_matches_approved_snapshot(repo_root: Path) -> None:
    snapshot_path = repo_root / "tests" / "schema-snapshot.json"
    assert snapshot_path.is_file(), "schema snapshot is missing; run the update script"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    client = StdioMCPClient.spawn(repo_root)
    try:
        info = client.initialize()
        tools = client.list_tools()
    finally:
        client.close()

    live = _canonical(
        {
            "server_info": info["serverInfo"],
            "tools_list": tools,
        }
    )
    approved = _canonical(
        {
            "server_info": snapshot["server_info"],
            "tools_list": snapshot["tools_list"],
        }
    )
    assert live == approved, (
        "tools/list schema drifted from the approved snapshot. If the change is "
        "intentional and human-confirmed, regenerate the snapshot with "
        "`uv run python scripts/update_schema_snapshot.py` and commit it."
    )
