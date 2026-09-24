from __future__ import annotations

from pathlib import Path

import pytest
from mcp import Client

from obsidian_mcp.config import Settings
from obsidian_mcp.server import create_server


@pytest.mark.anyio
async def test_mcp_contract_and_structured_search(rich_vault: Path, tmp_path: Path) -> None:
    settings = Settings(
        vault_root=rich_vault,
        windows_status_script=tmp_path / "missing.ps1",
        cloud_status_script=tmp_path / "missing-cloud.ps1",
        ssh_wrapper=tmp_path / "missing-ssh.ps1",
        powershell_exe="pwsh",
        docker_exe=None,
    )
    server = create_server(settings)

    async with Client(server) as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools.tools} == {
            "find_runbook",
            "search_notes",
            "read_section",
            "query_runtime_status",
        }
        result = await client.call_tool("search_notes", {"query": "Tailscale"})

    assert result.structured_content is not None
    assert result.structured_content["returned"] >= 1
    assert result.structured_content["items"][0]["source_kind"] == "documentation"
