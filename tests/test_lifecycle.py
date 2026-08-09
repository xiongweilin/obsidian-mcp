"""Real-subprocess lifecycle tests for the ratio MCP server.

These tests spawn actual ``uv run ratio-mcp`` processes (the same launch shape
Codex uses) and verify process structure under concurrent connections, clean
shutdown after clients close, and reaping when a client dies abnormally. Only
processes spawned by the test are inspected; unrelated sessions are never
touched.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from mcp_stdio_client import StdioMCPClient, process_alive, spawn_with_temp_vault

pytestmark = pytest.mark.lifecycle

CONNECTIONS = 3
EXIT_TIMEOUT = 45.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _windows_process_rows() -> dict[int, dict[str, object]]:
    """Snapshot Win32 processes keyed by PID (Windows only)."""

    script = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        timeout=30,
    )
    if result.returncode != 0:
        pytest.skip(f"Win32 process enumeration unavailable: {result.stderr[:200]}")
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.skip("Win32 process enumeration returned no usable JSON")
    if isinstance(rows, dict):
        rows = [rows]
    return {
        int(row["ProcessId"]): {
            "ppid": int(row.get("ParentProcessId") or 0),
            "cmdline": row.get("CommandLine") or "",
        }
        for row in rows
    }


def _descendants_windows(root_pids: set[int]) -> dict[int, str]:
    """Return PID -> command line for every descendant of the given roots."""

    rows = _windows_process_rows()
    children: dict[int, list[int]] = {}
    for pid, info in rows.items():
        children.setdefault(int(info["ppid"]), []).append(pid)
    descendants: dict[int, str] = {}
    frontier = list(root_pids)
    while frontier:
        current = frontier.pop()
        for child in children.get(current, []):
            if child not in descendants and child not in root_pids:
                descendants[child] = str(rows[child]["cmdline"])
                frontier.append(child)
    return descendants


def _descendants_posix(root_pids: set[int]) -> dict[int, str]:
    descendants: dict[int, str] = {}
    frontier = list(root_pids)
    while frontier:
        current = frontier.pop()
        result = subprocess.run(
            ["pgrep", "-P", str(current)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            continue
        for pid_text in result.stdout.split():
            pid = int(pid_text)
            descendants[pid] = ""
            frontier.append(pid)
    return descendants


def _descendants(root_pids: set[int]) -> dict[int, str]:
    if sys.platform == "win32":
        return _descendants_windows(root_pids)
    return _descendants_posix(root_pids)


def _wait_until_gone(root_pids: set[int], timeout: float = EXIT_TIMEOUT) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any(process_alive(pid) for pid in root_pids):
            return True
        time.sleep(0.5)
    return False


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return _repo_root()


@pytest.fixture(scope="module")
def lifecycle_vault(tmp_path_factory: pytest.TempPathFactory) -> Path:
    vault = tmp_path_factory.mktemp("lifecycle-vault")
    runbook = vault / "RUNBOOK"
    runbook.mkdir()
    (vault / "个人平台总览.md").write_text(
        "---\ndocument_type: moc\n---\n# 总览\n\n## 网络\n\n进入 [[RUNBOOK/手册]]。\n",
        encoding="utf-8",
    )
    (runbook / "手册.md").write_text("# 手册\n\n## 检查\n\n先看状态。\n", encoding="utf-8")
    return vault


@pytest.mark.windows_only
def test_three_concurrent_connections_have_isolated_server_processes(
    repo_root: Path,
    lifecycle_vault: Path,
) -> None:
    """N Codex tasks each get their own server process; nothing is shared."""

    if sys.platform != "win32":
        pytest.skip("process-tree structure assertion is Windows-specific")
    clients: list[StdioMCPClient] = []
    root_pids: set[int] = set()
    try:
        for _ in range(CONNECTIONS):
            client = spawn_with_temp_vault(repo_root, lifecycle_vault)
            client.initialize()
            clients.append(client)
        root_pids = {client.proc.pid for client in clients}
        descendants = _descendants(root_pids)

        assert len(clients) == CONNECTIONS
        # Each connection must own at least one descendant whose command line
        # names the ratio server (uv wrapper or python interpreter).
        ratio_descendants = {
            pid: cmdline
            for pid, cmdline in descendants.items()
            if "ratio" in cmdline.casefold() or "ratio_mcp" in cmdline.casefold()
        }
        assert len(ratio_descendants) >= CONNECTIONS, (
            f"expected at least {CONNECTIONS} server processes, got {len(ratio_descendants)}"
        )
        # Every connection's tree is non-empty (uv wrapper + interpreter).
        assert len(descendants) >= CONNECTIONS * 2
    finally:
        for client in clients:
            client.close(wait_timeout=EXIT_TIMEOUT)

    # After closing every client the whole test-owned tree must be gone.
    assert _wait_until_gone(root_pids), "ratio MCP processes survived clean client close"


def test_concurrent_clients_all_serve_requests(
    repo_root: Path,
    lifecycle_vault: Path,
) -> None:
    clients: list[StdioMCPClient] = []
    try:
        for _ in range(CONNECTIONS):
            clients.append(spawn_with_temp_vault(repo_root, lifecycle_vault))
        for client in clients:
            client.initialize()
        for client in clients:
            tools = client.list_tools()
            names = {tool["name"] for tool in tools["tools"]}
            assert names == {
                "find_runbook",
                "search_notes",
                "read_section",
                "read_action_board",
                "query_runtime_status",
            }
            result = client.call_tool("search_notes", {"query": "状态", "limit": 5})
            assert result["isError"] is False
            assert result["structuredContent"]["returned"] >= 1
    finally:
        for client in clients:
            client.close(wait_timeout=EXIT_TIMEOUT)


def test_server_exits_after_client_closes_stdin(
    repo_root: Path,
    lifecycle_vault: Path,
) -> None:
    client = spawn_with_temp_vault(repo_root, lifecycle_vault)
    client.initialize()
    root_pids = {client.proc.pid}

    returncode = client.close(wait_timeout=EXIT_TIMEOUT)

    assert returncode == 0
    assert _wait_until_gone(root_pids), "server process tree survived stdin close"
    assert _descendants(root_pids) == {}


def test_client_crash_leaves_no_orphan_server_processes(repo_root: Path) -> None:
    """Kill the MCP host hard; the server chain must be reaped, not orphaned."""

    helper = Path(__file__).resolve().parent / "client_crash_helper.py"
    uv = shutil.which("uv")
    assert uv, "uv must be on PATH to run this test"
    host = subprocess.Popen(
        [sys.executable, str(helper), uv, str(repo_root)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    server_pid: int | None = None
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        line = host.stderr.readline()
        if not line:
            break
        if line.startswith("SERVER_PID="):
            server_pid = int(line.strip().split("=", 1)[1])
        if line.strip() == "READY":
            break
    assert server_pid is not None, "helper did not report the server PID"
    assert process_alive(server_pid), "server should be up before the crash"

    # Abnormal client exit: terminate the host without any clean shutdown.
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/PID", str(host.pid)],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    else:
        host.kill()

    assert _wait_until_gone({server_pid}), (
        f"ratio MCP server chain {server_pid} survived client crash"
    )
    assert _descendants({server_pid}) == {}


def test_subprocess_timeout_is_bounded(repo_root: Path) -> None:
    from ratio_mcp.runtime import _run

    started = time.monotonic()
    result = _run([sys.executable, "-c", "import time; time.sleep(10)"], timeout=1)
    elapsed = time.monotonic() - started

    assert result.returncode == 124
    assert elapsed < 8, f"subprocess timeout took {elapsed:.1f}s instead of ~1s"


@pytest.mark.windows_only
def test_runtime_query_reports_timeout_as_warning(repo_root: Path, tmp_path: Path) -> None:
    from ratio_mcp.config import Settings
    from ratio_mcp.runtime import RuntimeStatusService

    slow_script = tmp_path / "slow.ps1"
    slow_script.write_text("Start-Sleep -Seconds 10\n", encoding="utf-8")
    settings = Settings(
        vault_root=tmp_path,
        windows_status_script=slow_script,
        cloud_status_script=tmp_path / "missing.ps1",
        ssh_wrapper=tmp_path / "missing-ssh.ps1",
        powershell_exe="pwsh",
        docker_exe=None,
        command_timeout_seconds=1,
    )

    started = time.monotonic()
    result = RuntimeStatusService(settings).query("windows_services", limit=5)
    elapsed = time.monotonic() - started

    assert result.returned == 0
    assert any("124" in warning for warning in result.warnings)
    assert elapsed < 8, f"runtime query ignored timeout, took {elapsed:.1f}s"
