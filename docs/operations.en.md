# Install / upgrade / uninstall / troubleshooting

## Prerequisites

- Windows + [uv](https://docs.astral.sh/uv/) (this project uses only `uv sync` / `uv run`; Python dependencies are not installed globally);
- Python ≥3.12 (managed automatically by `uv`);
- The read-only target vault `D:\agent\obsidian` (retrieval tools report an error when it is missing; see troubleshooting).

## Install

```powershell
cd D:\agent\obsidian-mcp
uv sync
```

Start manually for local use (STDIO service waiting for an MCP Host connection; no ordinary prompt in the terminal is expected):

```powershell
uv run obsidian-mcp
```

Verification commands:

```powershell
uv run ruff check .
uv run pytest
uv run python scripts\smoke_stdio.py
uv run python scripts\smoke_runtime.py
```

`smoke_runtime.py` accesses the real Windows, Docker, and personal cloud environments and prints only the result count and warning count for each scope, never service details.

## Codex local MCP configuration

Codex starts this project from a STDIO entry in the global `~/.codex/config.toml`. On this machine `[mcp_servers.obsidian]` is already configured (with `command` and `args` keys). To configure another machine:

```powershell
codex mcp add obsidian -- uv run --directory D:\agent\obsidian-mcp obsidian-mcp
```

Inspect and roll back:

```powershell
codex mcp get obsidian
codex mcp remove obsidian
```

> `~/.codex/config.toml` is managed by the runtime and may contain secrets; **do not manually edit secret values in it**, and do not print their values. Restart the Codex client or extension after changing the MCP configuration.

## Upgrade

```powershell
cd D:\agent\obsidian-mcp
git pull
uv sync
uv run ruff check .
uv run pytest
```

After upgrading, restart the Codex client (or start a new session) so the new code takes effect. Interface upgrades are additive: new tools and fields become available directly, and existing tools do not break.

## Uninstall

```powershell
codex mcp remove obsidian
```

Then delete the project directory (`D:\agent\obsidian-mcp`, including `.venv`). Uninstalling does not affect the vault; this project never writes to the vault.

## Common troubleshooting

| Symptom | Cause and handling |
| --- | --- |
| No output or prompt after startup | Normal: the STDIO service is waiting for an MCP Host; press Ctrl+C to exit |
| Codex reports an MCP startup timeout | The first `uv sync` did not finish or dependencies are missing; run `uv sync` manually and retry |
| `search_notes`/`read_section` reports the vault is unavailable | `D:\agent\obsidian` does not exist or is inaccessible; verify the path |
| Chinese text appears as replacement characters `�` | The vault file is not UTF-8; by design it is read with replacement (`errors="replace"`) and does not crash, but save notes as UTF-8 when possible |
| `query_runtime_status` returns warnings | A script is missing, a command failed, or the cloud is unreachable; warnings contain no sensitive values and do not fall back to old documents |
| `uv sync` reports `obsidian-mcp.exe` is in use | A residual MCP server process exists; first terminate `uv`/`python`/`obsidian-mcp.exe` processes whose command line contains `D:\agent\obsidian-mcp` (Codex restarts it on demand), then run `uv sync` |
| `uv run` repeatedly reports `obsidian-mcp.exe` is in use (when resident sessions exist) | This affects only console-script rebuilding, not the code (the editable install points directly at `src/`); use `uv run --no-sync ...` for local verification and run `uv sync` after the processes exit |
| A just-edited note cannot be found | There is no index cache; each request scans the current files; confirm the file is `.md` and is not in an excluded directory (`.git`/`.obsidian`, etc.) |

## Lifecycle and contract tests

Repository tests fall into three categories, each run by CI (`.github/workflows/ci.yml`):

| Category | Content | Local command |
| --- | --- | --- |
| Regular unit tests | Retrieval / runtime parsing / privacy masking | `uv run pytest -q -m "not windows_only"` |
| Contract tests | Real subprocess + standard-library JSON-RPC client: tools/list, five-tool success paths, privacy rejection, schema snapshot drift | `uv run pytest -q -m contract` |
| Windows-only | Process-tree structure, pwsh timeout | `uv run pytest -q -m windows_only` |

When the `tools/list` schema changes, `test_schema_snapshot.py` fails; after confirming the change is intentional:

```powershell
uv run python scripts\update_schema_snapshot.py
```

Then commit the updated `tests/schema-snapshot.json`.

## Environment-variable overrides (test/CI only)

`Settings.defaults()` supports read-only environment-variable overrides so tests and CI can point at a fixture vault; these variables carry only paths or integers, never credentials:

| Variable | Override |
| --- | --- |
| `OBSIDIAN_MCP_VAULT_ROOT` | Vault root directory |
| `OBSIDIAN_MCP_COMMAND_TIMEOUT_SECONDS` | Subprocess timeout in seconds |
| `OBSIDIAN_MCP_WINDOWS_STATUS_SCRIPT` / `OBSIDIAN_MCP_CLOUD_STATUS_SCRIPT` | Status-script paths |
| `OBSIDIAN_MCP_SSH_WRAPPER` | Cloud SSH wrapper-script path |
