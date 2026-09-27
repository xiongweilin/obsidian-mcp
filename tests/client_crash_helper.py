"""Standalone helper for the client-crash lifecycle test.

Simulates a real MCP host: spawns ``uv run obsidian-mcp`` as its own child
process, completes the initialize handshake, reports the server PID on stderr,
then idles while holding the stdio connection. Killing this helper hard is
equivalent to a Codex task dying without a clean shutdown; the test asserts the
server chain is reaped anyway.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time


def main() -> None:
    uv = sys.argv[1]
    repo = sys.argv[2]
    server = subprocess.Popen(
        [uv, "run", "--no-sync", "--directory", repo, "obsidian-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    print(f"SERVER_PID={server.pid}", file=sys.stderr, flush=True)
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "crash-helper", "version": "0.1"},
        },
    }
    try:
        server.stdin.write(json.dumps(request) + "\n")
        server.stdin.flush()
        # 等待 initialize 响应，确保服务完全启动后
        # 测试再终止本进程。
        if server.stdout:
            for _ in range(60):
                line = server.stdout.readline()
                if not line:
                    break
                if '"id":1' in line:
                    break
                time.sleep(0.1)
        print("READY", file=sys.stderr, flush=True)
    except (BrokenPipeError, OSError):
        pass
    # 使用有界空闲时间，即使测试在终止本进程前失败，泄漏的 helper
    # 也会自行退出，作为测试清理之外的额外保险。
    time.sleep(120)


if __name__ == "__main__":
    main()
