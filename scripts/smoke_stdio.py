from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def smoke() -> None:
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
        expected = {"find_runbook", "search_notes", "read_section", "query_runtime_status"}
        if names != expected:
            raise RuntimeError(f"Unexpected MCP tool set: {sorted(names)}")
        result = await session.call_tool("search_notes", {"query": "环境运维", "limit": 1})
        if result.is_error or not result.structured_content:
            raise RuntimeError("search_notes MCP call did not return structured content")
        print(f"ratio MCP stdio OK: {', '.join(sorted(names))}")


if __name__ == "__main__":
    asyncio.run(smoke())
