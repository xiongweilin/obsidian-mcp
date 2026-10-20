# ADR-0001: Adopt a local read-only STDIO MCP

## Status

Accepted

## Date

2026-08-08

## Context

`D:\agent\obsidian` contains only a few dozen structured Markdown files, yet it includes changing Windows, Docker, and cloud facts. Agents need to locate the source of a fact repeatably and query the real management plane when necessary. A fixed vector index would duplicate the existing frontmatter, Wikilinks, and directory structure, and would easily mistake historical snapshots for current facts.

## Decision

Create a standalone Python project that exposes four read-only tools through MCP Python SDK v2. Document retrieval scans heading blocks at request time and performs deterministic ranking; runtime queries call only predefined commands. Codex starts the service over local STDIO; no network port is opened, no database is created, and no query content is stored.

The interface explicitly distinguishes:

- `source_kind=documentation`: description, navigation, or snapshot;
- `source_kind=runtime` with `is_live=true`: state obtained fresh during this call.

All outputs use fixed Pydantic models; paths, counts, and string lengths are validated at the boundary; common credential shapes are masked before return.

## Alternatives

### Full vector RAG

Rejected. The current corpus is small and already sufficiently structured; the cost of adding an index, embeddings, and staleness governance exceeds the benefit. If real evaluation later shows that deterministic retrieval cannot handle synonymous expressions, an optional retrieval implementation can be added inside MCP without changing the tool contract.

### Streamable HTTP

Not adopted for now. The service is currently used only by personal Codex on the same Windows host; HTTP would add ports, authentication, and service-lifecycle management. Migrate when cross-machine or multi-user use is required.

### Arbitrary command tool

Rejected. It would turn MCP into a remote shell and increase the risk of prompt injection, secret leakage, and mistakes. Runtime queries must continue to use an in-code allowlist.

## Consequences

- Codex can call the same personal tools across projects; source code and configuration remain separate.
- Each retrieval scans the current Markdown, avoiding index synchronization but making the design unsuitable for tens of thousands of documents.
- Cloud state depends on the existing SSH wrapper and network connectivity; failures return warnings without sensitive values and never fall back to old documents presented as live results.
- Adding write operations, HTTP exposure, or a persistent index requires a new ADR and explicit authorization.
