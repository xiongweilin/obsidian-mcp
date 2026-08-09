# ratio-mcp project guidance

- Use `uv sync` and `uv run`; do not install project dependencies globally.
- Keep every MCP tool read-only unless a later user-approved interface change explicitly adds writes.
- Never expose arbitrary shell execution, arbitrary filesystem roots, service command lines, environment values, credentials, cookies, private keys, or `.env` contents.
- Treat Markdown as documentation evidence and runtime queries as current evidence; never present a document snapshot as live state.
- Preserve the existing public tool names and structured result shapes. Extend contracts additively and record breaking decisions in `docs/decisions/`.
- Run `uv run ruff check .`, `uv run pytest` (contract + lifecycle + windows markers included), `uv run python scripts/smoke_stdio.py`, and `uv run python scripts/smoke_runtime.py` before claiming completion. Report a remote-path failure rather than substituting documentation for live evidence.
- When live MCP sessions lock `ratio-mcp.exe` on this machine, local validation may use `uv run --no-sync ...`; CI runners are unaffected. Do not terminate live Codex sessions' MCP processes without approval.
- The `tools/list` schema snapshot (`tests/schema-snapshot.json`) is human-approved; intentional schema changes require regenerating it with `uv run python scripts/update_schema_snapshot.py` and committing both.
