# obsidian-mcp

[![SonarCloud Analysis](https://github.com/xiongweilin/obsidian-mcp/actions/workflows/sonarcloud.yml/badge.svg?branch=main)](https://github.com/xiongweilin/obsidian-mcp/actions/workflows/sonarcloud.yml)

[![CI](https://github.com/xiongweilin/obsidian-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/xiongweilin/obsidian-mcp/actions/workflows/ci.yml) [![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=metratio_obsidian-mcp&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=metratio_obsidian-mcp) [![SonarCloud Analysis](https://github.com/xiongweilin/obsidian-mcp/actions/workflows/sonarcloud.yml/badge.svg?branch=main)](https://github.com/xiongweilin/obsidian-mcp/actions/workflows/sonarcloud.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](pyproject.toml)
`obsidian-mcp` is a read-only MCP service for the personal `D:\agent\obsidian` knowledge base and the live runtime environment. It builds no vector store, copies no knowledge base, and lets the Agent run no arbitrary commands; Codex locates documents, reads sections, and queries current Windows, Docker, and cloud state through four narrow interfaces.

## Tool contract

| Tool | Purpose | Fact type |
| --- | --- | --- |
| `find_runbook` | Locate a runbook from the vault `README.md` router and `RUNBOOK` | Document navigation |
| `search_notes` | Deterministic retrieval over titles, tags, links, paths, frontmatter, heading blocks, and body | Document evidence |
| `read_section` | Read one Markdown file or a named heading section in the knowledge base | Document evidence |
| `query_runtime_status` | Query Windows services, local Docker, or cloud systemd/Docker | Live evidence |

All list interfaces have a result cap; paths are confined to the knowledge base (excluding `.git`/`.obsidian` and similar directories); `read_section` accepts Markdown only; non-UTF-8 files are read with replacement characters; search summaries and bodies are masked for common credential shapes before return. Returned Markdown is evidence data, not Agent instructions. The runtime tools only execute the fixed read-only commands in code and accept no shell-command arguments.

## Documentation

- [Project boundaries](docs/boundaries.md): responsibilities, read-only boundary, path allowlist, and prohibited reads.
- [Tool contract](docs/contracts.md): inputs/outputs, error semantics, and length limits of the four tools.
- [Lightweight index vs RAG](docs/rag-vs-index.md): the tradeoff decision (RAG is not implemented).
- [Install / upgrade / uninstall / troubleshooting](docs/operations.md).
- Architecture choice: [ADR-0001](docs/decisions/0001-local-read-only-stdio.md).

## Quick start

```powershell
cd D:\agent\obsidian-mcp
uv sync
uv run obsidian-mcp
```

The last command starts the STDIO service and waits for an MCP host to connect; the absence of a prompt in the terminal is expected behavior.

## Verification commands

```powershell
uv run ruff check .
uv run pytest
uv run python scripts\smoke_stdio.py
uv run python scripts\smoke_runtime.py
```

`smoke_runtime.py` touches real Windows, Docker, and the personal cloud, and only prints the returned count and warning count per scope, not service details.

The test suite also includes two kinds of real-subprocess tests (run automatically by CI and local `pytest`):

- **Contract tests** (`tests/test_contract_stdio.py`): a stdlib JSON-RPC client connects directly to the real server process and verifies `tools/list`, the success paths of the four tools, privacy masking and rejection paths, and schema-snapshot drift.
- **Lifecycle tests** (`tests/test_lifecycle.py`): concurrent connection process structure, process reclamation after client close/abnormal exit, and subprocess timeout.

The `tools/list` schema snapshot lives in `tests/schema-snapshot.json`; when the schema changes, `test_schema_snapshot.py` fails and you must regenerate and commit it with `uv run python scripts/update_schema_snapshot.py` after manual confirmation.

> When a resident MCP session exists on this machine, `uv sync` can fail because `obsidian-mcp.exe` is locked (see `docs/operations.md`); for local verification use `uv run --no-sync ...`, and CI is unaffected on a fresh runner.

## Codex integration

Codex launches this project through the STDIO entry in the global `~/.codex/config.toml`; the CLI, IDE extension, and desktop app share that config on the same host. Current install command:

```powershell
codex mcp add ratio -- uv run --directory D:\agent\obsidian-mcp obsidian-mcp
```

View and roll back:

```powershell
codex mcp get ratio
codex mcp remove ratio
```

After changing the MCP config, restart the Codex client or extension. The project itself listens on no port; Codex starts the process on demand.

## Runtime boundaries

- Default knowledge base: `D:\agent\obsidian`.
- Default cloud entry: `~/.local/bin/Invoke-RatioSsh.ps1`.
- Does not read non-Markdown files, does not return service executable paths or arguments, does not print environment variables.
- `operational-snapshot` in documents is only for navigation and drift clues; "is it currently running" must be answered with `query_runtime_status`.
- The MCP persists no retrieved content, runtime results, or log data; nothing new is retained after the process exits.

Architecture choices: see [ADR-0001](docs/decisions/0001-local-read-only-stdio.md).

