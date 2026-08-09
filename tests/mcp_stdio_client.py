"""Minimal MCP stdio client built only on the Python standard library.

Used by contract and lifecycle tests to prove the on-the-wire JSON-RPC
contract without depending on the ``mcp`` SDK on the client side. Framing is
newline-delimited JSON over stdin/stdout, per the MCP stdio transport.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = "2025-06-18"


class MCPClientError(RuntimeError):
    """Raised when the server returns a JSON-RPC error or the wire misbehaves."""


def process_alive(pid: int) -> bool:
    """Cross-platform existence check without third-party dependencies."""

    if sys.platform == "win32":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"],
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return str(pid) in result.stdout and "No tasks" not in result.stdout
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


class StdioMCPClient:
    """Spawn ``uv run ratio-mcp`` and drive it with newline-delimited JSON-RPC."""

    def __init__(
        self,
        proc: subprocess.Popen[str],
        ready_timeout: float = 45.0,
    ) -> None:
        self.proc = proc
        self._next_id = 0
        self._lock = threading.Lock()
        self.notifications: list[dict[str, Any]] = []
        self.stderr_lines: list[str] = []
        self._ready_timeout = ready_timeout
        self._stderr_thread = threading.Thread(target=self._drain_stderr, daemon=True)
        self._stderr_thread.start()

    @classmethod
    def spawn(
        cls,
        repo: Path,
        *,
        extra_env: Mapping[str, str] | None = None,
        timeout: float = 45.0,
    ) -> StdioMCPClient:
        """Start one ``uv run ratio-mcp`` server for the given repository."""

        uv = shutil.which("uv")
        if not uv:
            raise MCPClientError("uv executable not found on PATH")
        # --no-sync: the venv is already synced, and re-syncing would rebuild
        # the console script, which live MCP sessions lock on Windows. The
        # editable install already points at src/, so the current code runs.
        command = [uv, "run", "--no-sync", "--directory", str(repo), "ratio-mcp"]
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(repo),
            creationflags=creationflags,
        )
        return cls(proc, ready_timeout=timeout)

    def _drain_stderr(self) -> None:
        if self.proc.stderr is None:
            return
        for line in self.proc.stderr:
            self.stderr_lines.append(line.rstrip("\n"))

    def _read_line(self, timeout: float) -> str:
        if self.proc.stdout is None:
            raise MCPClientError("server stdout is not available")
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPClientError(f"timed out waiting for server response (pid={self.proc.pid})")
            line = self.proc.stdout.readline()
            if line == "":
                raise MCPClientError(
                    f"server stdout closed unexpectedly (pid={self.proc.pid}, "
                    f"stderr={self.stderr_lines[-3:]})"
                )
            if line.strip():
                return line

    def _send(self, payload: dict[str, Any]) -> None:
        if self.proc.stdin is None or self.proc.stdin.closed:
            raise MCPClientError("server stdin is closed")
        self.proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()

    def _request(self, method: str, params: dict[str, Any], timeout: float) -> dict[str, Any]:
        with self._lock:
            self._next_id += 1
            request_id = self._next_id
            self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise MCPClientError(f"timeout waiting for {method!r} response")
                line = self._read_line(remaining)
                try:
                    message = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise MCPClientError(f"non-JSON line on MCP wire: {line[:120]!r}") from exc
                if not isinstance(message, dict) or "jsonrpc" not in message:
                    raise MCPClientError(f"malformed MCP message: {line[:120]!r}")
                if "id" not in message:
                    # Server-originated notification (e.g. logging); record and continue.
                    self.notifications.append(message)
                    continue
                if message.get("id") != request_id:
                    raise MCPClientError(
                        f"unexpected message id {message.get('id')!r} for {request_id}"
                    )
                if "error" in message:
                    error = message["error"]
                    raise MCPClientError(
                        f"{method} failed: code={error.get('code')} {error.get('message')}"
                    )
                return message.get("result", {})

    def initialize(self) -> dict[str, Any]:
        result = self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "ratio-mcp-stdlib-client", "version": "0.1.0"},
            },
            timeout=self._ready_timeout,
        )
        self._send(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            }
        )
        return result

    def ping(self, timeout: float = 15.0) -> dict[str, Any]:
        return self._request("ping", {}, timeout=timeout)

    def list_tools(self, timeout: float = 20.0) -> dict[str, Any]:
        return self._request("tools/list", {}, timeout=timeout)

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        return self._request(
            "tools/call",
            {"name": name, "arguments": arguments},
            timeout=timeout,
        )

    def close(self, wait_timeout: float = 30.0) -> int | None:
        """Close stdin (clean client shutdown) and wait for the server to exit."""

        try:
            if self.proc.stdin and not self.proc.stdin.closed:
                self.proc.stdin.close()
        except OSError:
            pass
        try:
            return self.proc.wait(timeout=wait_timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            return self.proc.wait(timeout=10)

    def kill(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()


def spawn_with_temp_vault(repo: Path, vault: Path, **kwargs: Any) -> StdioMCPClient:
    """Spawn the server pointed at a fixture vault via ``RATIO_MCP_VAULT_ROOT``."""

    return StdioMCPClient.spawn(repo, extra_env={"RATIO_MCP_VAULT_ROOT": str(vault)}, **kwargs)


def require_uv(repo: Path) -> str:
    uv = shutil.which("uv")
    if not uv:
        raise MCPClientError("uv executable not found on PATH")
    return uv


if __name__ == "__main__":  # pragma: no cover - manual smoke path
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    client = StdioMCPClient.spawn(repo)
    try:
        info = client.initialize()
        tools = client.list_tools()
        names = sorted(tool["name"] for tool in tools["tools"])
        print(f"smoke OK: {info['serverInfo']}; tools={names}")
    finally:
        client.close()
