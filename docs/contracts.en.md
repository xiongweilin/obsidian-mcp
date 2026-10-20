# Tool contracts

obsidian-mcp 0.3 exposes four read-only MCP tools. Vault documents provide only document evidence; runtime state such as Responsibility / Work must come from its authoritative runtime owner and must not be inferred from Markdown.

## Common conventions

- Document results: `source_kind=documentation`, vault evidence, not current runtime truth.
- Runtime state: `source_kind=runtime` with `is_live=true`, from a fixed read-only query made during this call.
- Markdown is masked for credential shapes before return; queries, documents, and runtime results are not persisted.
- Vault reads allow only relative Markdown paths inside the root; `.git`, `.obsidian`, `.venv`, `node_modules`, and `__pycache__` are excluded.
- No results returns an empty structure; invalid input returns a tool error.

## 1. find_runbook

Locate a relevant runbook from the RUNBOOK links in the vault-root `README.md` and the full text under `RUNBOOK/`. The README is a locator/router and does not duplicate project current truth.

Input: `topic` 1–200 characters; `limit` 1–10.  
Returns: `RunbookResponse`, `router_path="README.md"`.

Routing parses only one level of the README; nonexistent targets are skipped silently, and full-text RUNBOOK search then supplements the results.

## 2. search_notes

Perform deterministic retrieval over titles, headings, paths, Markdown/Wikilinks, tags, frontmatter, and body without building a vector store or persistent index.

`scope`: `all` / `runbook` / `operational` / `conceptual`.  
`query` ≤200 characters; `limit` 1–20.

## 3. read_section

Read one Markdown file or an exact heading section in the vault.

- path must be a relative `.md` inside the vault, ≤260 characters;
- heading ≤200 characters;
- max_chars 500–20000, default 12000;
- path escape, excluded directories, non-Markdown files, and missing files/headings are all tool errors.

## 4. query_runtime_status

Execute only fixed read-only Windows / Docker / cloud queries in code; accept no shell-command arguments.

`scope`: `windows_services` / `local_docker` / `cloud`.  
Runtime failures are returned as warnings; the tool never falls back to old documents and presents them as live state.
