# ratio-mcp project guidance

- Use `uv sync` and `uv run`; do not install project dependencies globally.
- Keep every MCP tool read-only unless a later user-approved interface change explicitly adds writes.
- Never expose arbitrary shell execution, arbitrary filesystem roots, service command lines, environment values, credentials, cookies, private keys, or `.env` contents.
- Treat Markdown as documentation evidence and runtime queries as current evidence; never present a document snapshot as live state.
- Preserve the four public tool names and structured result shapes. Extend contracts additively and record breaking decisions in `docs/decisions/`.
- Run `uv run ruff check .`, `uv run pytest`, `uv run python scripts/smoke_stdio.py`, and `uv run python scripts/smoke_runtime.py` before claiming completion. Report a remote-path failure rather than substituting documentation for live evidence.
