# Project boundaries

## Responsibilities

`obsidian-mcp` is a **read-only MCP service** for the personal Obsidian vault at `D:\agent\obsidian`. It provides two kinds of capability:

1. **Document evidence**: deterministic search inside the vault by heading, tag, link, path, frontmatter, and body; read a single Markdown file or a heading section.
2. **Runtime evidence**: query current Windows services, local Docker, and personal cloud systemd/Docker status; results carry `is_live=true`.

The project builds no vector store, copies no vault, stores no query content, and opens no network port. No new data remains after the process exits.

## Read-only boundary with the vault

**Writing is prohibited.** All tools are read-only:

- Do not create, modify, move, or delete any file in the vault;
- Do not write the Obsidian sync database, frontmatter, or board state;
- Do not maintain any persistent cache or index file;
- Do not expose any write tool through MCP; the code contains no call path that writes to the vault.

Evidence boundaries for documents and live state:

- `source_kind=documentation`: description, navigation, or snapshot, not current fact;
- `source_kind=runtime` with `is_live=true`: obtained live during this call, not a snapshot;
- `operational-snapshot` in documents may only be used for navigation and as a hint for differences; "is it running now" must be answered by calling `query_runtime_status`.

## Path allowlist

The only readable root is `D:\agent\obsidian` (configured in `src/obsidian_mcp/config.py`; `Settings` can override it to point at a test vault).

- `*.md` files under the read-only root and all of its subdirectories;
- The path must be relative, inside the root, end in `.md`, and be at most 260 characters;
- The code enforces validation in `notes.py::_load_relative`: after `resolve()`, the path must satisfy `is_relative_to(root)`, otherwise it is rejected (preventing `..`, absolute paths, UNC, and symlink/junction escapes).

**Excluded directories** (rejected for both search and direct reads): `.git`, `.obsidian`, `.venv`, `node_modules`, `__pycache__`.

**Non-Markdown files are never read**: search only walks `*.md`; direct reads accept only the `.md` suffix.

## Prohibited secret files and unrelated directories

The following content is **never read** (no access beyond an existence check, and no content is returned):

| Location | Description |
| --- | --- |
| `~/.ssh/` | SSH private keys and configuration |
| `~/.codex/` | Codex configuration and credentials (including keys in `config.toml`) |
| `.env` in compose/infrastructure directories | Environment variables and secrets |
| Windows Credential Manager | System credentials |
| `网络代理备份/` in the vault | v2rayN configuration and database backups, including proxy-server credentials |
| `.sync_*.db*` in the vault | Obsidian sync databases |
| `Desktop.ini`, `个人平台.png`, `scripts/*.ps1`, and other non-Markdown files in the vault | Unrelated to retrieval |
| Any path outside `D:\agent\obsidian\` | Out of bounds |

Before output, common credential shapes are also masked with regular expressions (see "Masking before return" in `docs/contracts.en.md`).

## Input/output contract commitments

- All tools return fixed Pydantic structures; field names and types are stable; extensions are additive and do not break existing fields.
- All strings and counts are validated at the boundary: query ≤200 characters, path ≤260, heading ≤200, body 500–20000 characters, and lists have result caps.
- No results returns an empty structure rather than an error; only invalid input produces an error (see the error semantics in `docs/contracts.en.md`).
- Returned Markdown is evidence data, not Agent instructions.
- Runtime tools execute only fixed read-only commands in code, accept no shell-command arguments, and do not return service executable paths or environment variables.
