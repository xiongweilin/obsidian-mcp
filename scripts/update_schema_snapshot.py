"""Regenerate ``tests/schema-snapshot.json`` from the live tools/list response.

Run this only after an *intentional, human-confirmed* change to the public tool
schema (tool names, descriptions, input schemas, annotations). The drift test
``tests/test_schema_snapshot.py`` fails when the wire schema differs from the
snapshot, which is the intended guard against accidental contract drift.

Usage: ``uv run python scripts/update_schema_snapshot.py``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from mcp_stdio_client import StdioMCPClient  # noqa: E402


def canonical(value: object) -> object:
    if isinstance(value, dict):
        return {key: canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    snapshot_path = repo / "tests" / "schema-snapshot.json"
    client = StdioMCPClient.spawn(repo)
    try:
        info = client.initialize()
        tools = client.list_tools()
        snapshot = {
            "generated_by": "scripts/update_schema_snapshot.py",
            "server_info": info["serverInfo"],
            "tools_list": tools,
        }
        payload = json.dumps(canonical(snapshot), indent=2, ensure_ascii=False) + "\n"
        snapshot_path.write_text(payload, encoding="utf-8")
        print(f"wrote {snapshot_path} ({len(tools['tools'])} tools)")
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
