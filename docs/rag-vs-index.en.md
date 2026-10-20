# Lightweight index vs full RAG: tradeoff conclusion

## Current state and measured baseline

Size of the real vault (`D:\agent\obsidian`):

- 44 Markdown files (excluding `.git`/`.obsidian`), about 13 files use tags and 9 use aliases;
- Highly regular structure: frontmatter (`document_type`, `knowledge_scope`, `tags`, `updated`), H1–H6 heading blocks, `[[Wikilink]]`, the `RUNBOOK/` directory convention, and board documents.

Measured on this machine on 2026-08-09 (Windows, uv/Python 3.12+; single call after cold start):

| Operation | Latency |
| --- | --- |
| Full-vault search (45 hits, all 44 files scanned) | ~72ms |
| Runbook lookup | ~64ms |
| Read the home page `元模型/个人平台总览.md` | ~1.4ms |
| Structured parse of the action board | ~1.3ms |

## Comparison of three options

### A. Scan on demand (current, recommended)

- Each request scans the current Markdown, splits heading blocks, and applies deterministic scoring;
- Advantages: zero synchronization, zero staleness, simple implementation and audit; a full-vault scan is on the order of 100ms;
- Disadvantages: retrieval is literal matching with no synonym or semantic understanding; it degrades linearly at very large file counts.

### B. Lightweight index (inverted index / heading cache)

- Build and cache an inverted index of headings, tags, paths, and links;
- Benefit: at 44 files the benefit is zero—scanning itself takes only tens of milliseconds, while an index adds the governance cost of "index staleness vs. vault changes";
- If the file count later reaches ~2k and scanning exceeds an acceptable latency, a read-only cache or inverted index can be added inside MCP first, without changing the tool contract.

### C. Full RAG (embedding + vector store)

- Benefits: synonym handling and semantic recall;
- Costs: embedding models and dependencies, a vector store (SQLite-vec/Chroma, etc.), index synchronization and staleness governance, and resident in-process resources;
- For this project: the vault has only 44 files and is already sufficiently structured; existing retrieval can locate documents by heading/tag/link/full-text dimensions; adding RAG would be "using a more complex system to solve a recall problem that does not exist."

## Conclusion and recommendation

**Do not implement RAG; keep scanning on demand.** Reasons:

1. Scale: 44 files, full scan <100ms, far below any interaction budget;
2. Structure: frontmatter tags, Wikilinks, and the `RUNBOOK/` convention already provide structured entry points; deterministic retrieval is sufficient;
3. Resources: for personal use on this machine, the cost of resident RAG models and a vector store exceeds the benefit;
4. Consistency: no index means no staleness problem, consistent with ADR-0001's boundary that "document snapshot ≠ live state."

When to reevaluate (any one triggers a review):

- The vault grows to ~2000+ files and a full scan exceeds ~500ms;
- A real, demonstrated recall failure occurs (a synonymous query cannot find an existing document) and cannot be solved by adding aliases/tags;
- The deployment model becomes cross-machine or multi-user (then HTTP + serviceization is the higher-priority issue).

If triggered, prefer option B (a lightweight index inside MCP with an unchanged interface) rather than jumping directly to full RAG.
