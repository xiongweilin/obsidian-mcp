"""Wire-level MCP contract tests driven by a standard-library JSON-RPC client.

These tests spawn the real ``uv run ratio-mcp`` server as a subprocess and speak
newline-delimited JSON-RPC over stdio with no ``mcp`` SDK on the client side.
They cover tools/list, one success path per tool, privacy redaction, and the
invalid-argument / privacy-denial error paths.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp_stdio_client import StdioMCPClient, process_alive, spawn_with_temp_vault

pytestmark = pytest.mark.contract

EXPECTED_TOOLS = {
    "find_runbook",
    "search_notes",
    "read_section",
    "read_action_board",
    "query_runtime_status",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def contract_vault_module(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Module-scoped fixture vault (module-scoped server needs it module-scoped)."""

    return contract_vault_factory(tmp_path_factory.mktemp("contract-vault"))


def contract_vault_factory(tmp_path: Path) -> Path:
    runbook = tmp_path / "RUNBOOK"
    runbook.mkdir()
    model = tmp_path / "元模型"
    model.mkdir()
    (model / "个人平台总览.md").write_text(
        """---
document_type: moc
document_status: active
---
# 个人平台总览

## 网络入口

公网故障进入 [[RUNBOOK/环境运维手册]]。
""",
        encoding="utf-8",
    )
    (runbook / "环境运维手册.md").write_text(
        """---
document_type: runbook
document_status: active
---
# 环境运维手册

## 网络

先检查 Tailscale 当前路径。

password: contract-secret-must-not-leak
""",
        encoding="utf-8",
    )
    personal = tmp_path / "个人"
    personal.mkdir()
    (personal / "当前行动看板.md").write_text(
        """---
document_type: kanban
updated: 2026-08-09
---
# 当前行动看板

## 当前主线

- [ ] 完成契约测试
      - 下一动作：断言五个工具的成功路径。

## 已完成

- [x] 建立只读边界
""",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def contract_vault(tmp_path: Path) -> Path:
    return contract_vault_factory(tmp_path)


@pytest.fixture(scope="module")
def server(repo_root: Path, contract_vault_module: Path) -> StdioMCPClient:
    """One real server process shared by the contract assertions in this module."""

    client = spawn_with_temp_vault(repo_root, contract_vault_module)
    try:
        client.initialize()
    except Exception:
        client.kill()
        client.proc.wait(timeout=10)
        raise
    yield client
    client.close()


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return _repo_root()


def test_tools_list_matches_public_contract(server: StdioMCPClient) -> None:
    tools = server.list_tools()

    names = {tool["name"] for tool in tools["tools"]}
    assert names == EXPECTED_TOOLS
    for tool in tools["tools"]:
        assert tool["name"]
        assert tool["description"]
        assert isinstance(tool["inputSchema"], dict)
        assert "type" in tool["inputSchema"]
    annotations = {tool["name"]: tool.get("annotations", {}) for tool in tools["tools"]}
    assert all(ann.get("readOnlyHint") for ann in annotations.values())


def test_find_runbook_success(server: StdioMCPClient) -> None:
    result = server.call_tool("find_runbook", {"topic": "环境运维"})

    assert result["isError"] is False
    content = result["structuredContent"]
    assert content["returned"] >= 1
    assert content["items"][0]["source_kind"] == "documentation"


def test_search_notes_success_and_privacy_redaction(server: StdioMCPClient) -> None:
    result = server.call_tool("search_notes", {"query": "Tailscale", "limit": 5})

    assert result["isError"] is False
    content = result["structuredContent"]
    assert content["returned"] >= 1
    assert content["items"][0]["source_kind"] == "documentation"

    # The fixture note contains `password: contract-secret-must-not-leak`; the
    # wire response must never carry the raw value.
    serialized = json.dumps(content, ensure_ascii=False)
    assert "contract-secret-must-not-leak" not in serialized


def test_read_section_success(server: StdioMCPClient) -> None:
    result = server.call_tool(
        "read_section",
        {"path": "RUNBOOK/环境运维手册.md", "heading": "网络"},
    )

    assert result["isError"] is False
    content = result["structuredContent"]
    assert content["path"] == "RUNBOOK/环境运维手册.md"
    assert "Tailscale" in content["content"]
    assert "contract-secret-must-not-leak" not in content["content"]
    assert content["redactions"] >= 1


def test_read_action_board_success(server: StdioMCPClient) -> None:
    result = server.call_tool("read_action_board", {})

    assert result["isError"] is False
    content = result["structuredContent"]
    assert content["total_items"] >= 1
    assert content["open_items"] >= 1
    assert content["columns"][0]["name"]
    assert content["source_kind"] == "documentation"


def test_query_runtime_status_success_shape(server: StdioMCPClient) -> None:
    result = server.call_tool("query_runtime_status", {"scope": "windows_services", "limit": 5})

    # The live query may legitimately return warnings (missing script, no pwsh,
    # cloud unreachable), but it must never fail the call or fabricate results.
    assert result["isError"] is False
    content = result["structuredContent"]
    assert content["scope"] == "windows_services"
    assert content["source_kind"] == "runtime"
    assert content["is_live"] is True
    assert isinstance(content["warnings"], list)


@pytest.mark.parametrize(
    ("tool", "arguments", "reason"),
    [
        ("search_notes", {"query": ""}, "empty query"),
        ("search_notes", {"query": "x", "limit": 0}, "limit below minimum"),
        ("search_notes", {"query": "x" * 201}, "query over 200 chars"),
        ("find_runbook", {"topic": ""}, "empty topic"),
        ("read_section", {"path": ""}, "empty path"),
        ("read_section", {"path": "../outside.md"}, "path traversal"),
        ("read_section", {"path": "C:/Windows/win.ini"}, "absolute path"),
        ("read_section", {"path": "notes/.env"}, "non-markdown secret file"),
        ("read_section", {"path": ".git/config.md"}, "excluded directory"),
        ("query_runtime_status", {"scope": "bogus"}, "invalid scope"),
        ("query_runtime_status", {"scope": "cloud", "query": "x" * 101}, "filter over 100 chars"),
    ],
)
def test_invalid_arguments_are_tool_errors(
    server: StdioMCPClient,
    tool: str,
    arguments: dict[str, object],
    reason: str,
) -> None:
    result = server.call_tool(tool, arguments)

    assert result["isError"] is True, f"expected tool error for {reason}"
    assert result.get("content"), f"expected error content for {reason}"


def test_unknown_tool_is_rejected(server: StdioMCPClient) -> None:
    result = server.call_tool("no_such_tool", {})

    assert result["isError"] is True


def test_server_stays_healthy_after_errors(server: StdioMCPClient) -> None:
    server.call_tool("query_runtime_status", {"scope": "bogus"})
    server.call_tool("read_section", {"path": "../escape.md"})

    result = server.call_tool("search_notes", {"query": "Tailscale"})
    assert result["isError"] is False
    assert result["structuredContent"]["returned"] >= 1


def test_initialize_handshake_reports_ratio_server(repo_root: Path, contract_vault: Path) -> None:
    client = spawn_with_temp_vault(repo_root, contract_vault)
    try:
        info = client.initialize()
        assert info["serverInfo"]["name"] == "ratio"
        assert info["protocolVersion"]
        assert "tools" in info.get("capabilities", {})
    finally:
        client.close()


def test_ping_roundtrip(server: StdioMCPClient) -> None:
    assert server.ping() == {}


def test_clean_close_exits_server_process(repo_root: Path, contract_vault: Path) -> None:
    client = spawn_with_temp_vault(repo_root, contract_vault)
    client.initialize()
    pid = client.proc.pid

    returncode = client.close(wait_timeout=30)

    assert returncode == 0
    assert not process_alive(pid), f"server process {pid} still alive after clean close"


def test_read_section_rejects_outside_vault(server: StdioMCPClient) -> None:
    result = server.call_tool("read_section", {"path": "RUNBOOK/../../secret.md"})

    assert result["isError"] is True
    serialized = json.dumps(result, ensure_ascii=False)
    assert "contract-secret-must-not-leak" not in serialized


def test_error_path_never_exposes_raw_secret(server: StdioMCPClient) -> None:
    # The vault's own secret lives in a fixture note; even error paths must not
    # echo raw credential values back over the wire.
    result = server.call_tool("search_notes", {"query": "contract-secret"})

    serialized = json.dumps(result, ensure_ascii=False)
    assert "contract-secret-must-not-leak" not in serialized
    if not result["isError"]:
        # The fixture note holds a `password: ...` assignment; the redacted
        # marker must have replaced the value on the wire.
        assert "[REDACTED]" in serialized
