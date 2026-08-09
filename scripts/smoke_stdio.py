from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ratio_mcp.config import Settings


def _ensure_vault() -> None:
    """Point the spawned server at a real vault, creating a fixture if needed.

    Local runs use the configured vault root (D:\\download\\ratio); CI environments with
    no vault get a disposable fixture so the stdio smoke stays meaningful.
    """

    if os.environ.get("RATIO_MCP_VAULT_ROOT"):
        return
    if Settings.defaults().vault_root.is_dir():
        return
    vault = Path(tempfile.mkdtemp(prefix="ratio-mcp-smoke-vault-"))
    runbook = vault / "RUNBOOK"
    runbook.mkdir()
    (vault / "个人平台总览.md").write_text(
        "---\ndocument_type: moc\n---\n# 总览\n\n## 网络\n\n进入 [[RUNBOOK/环境运维手册]]。\n",
        encoding="utf-8",
    )
    (runbook / "环境运维手册.md").write_text(
        "---\ndocument_type: runbook\n---\n# 环境运维手册\n\n## 检查\n\n先看环境状态。\n",
        encoding="utf-8",
    )
    os.environ["RATIO_MCP_VAULT_ROOT"] = str(vault)


async def smoke() -> None:
    _ensure_vault()
    project = Path(__file__).resolve().parents[1]
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "ratio_mcp.server"],
        cwd=str(project),
    )
    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        await session.send_ping()
        tools = await session.list_tools()
        names = {tool.name for tool in tools.tools}
        expected = {
            "find_runbook",
            "search_notes",
            "read_section",
            "read_action_board",
            "query_runtime_status",
        }
        if names != expected:
            raise RuntimeError(f"Unexpected MCP tool set: {sorted(names)}")
        result = await session.call_tool("search_notes", {"query": "环境运维", "limit": 1})
        if result.is_error or not result.structured_content:
            raise RuntimeError("search_notes MCP call did not return structured content")
        print(f"ratio MCP stdio OK: {', '.join(sorted(names))}")


if __name__ == "__main__":
    asyncio.run(smoke())
