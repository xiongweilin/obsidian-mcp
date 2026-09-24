from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import unquote

from obsidian_mcp.models import (
    RunbookResponse,
    SearchHit,
    SearchResponse,
    SectionResponse,
)
from obsidian_mcp.privacy import redact_sensitive_text

SearchScope = Literal["all", "runbook", "operational", "conceptual"]
ROUTER_PATH = "README.md"

_EXCLUDED_PARTS = {".git", ".obsidian", ".venv", "node_modules", "__pycache__"}
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


@dataclass(frozen=True, slots=True)
class NoteDocument:
    path: Path
    relative_path: str
    lines: list[str]
    title: str
    metadata: dict[str, str]
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NoteChunk:
    document: NoteDocument
    heading: str | None
    line_start: int
    text: str


class NoteRepository:
    """Deterministic, non-persistent Markdown retrieval for the ratio vault."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def search(self, query: str, scope: SearchScope = "all", limit: int = 10) -> SearchResponse:
        clean_query = _validate_query(query)
        matches: list[SearchHit] = []
        for document in self._documents(scope):
            for chunk in _chunks(document):
                score = _score_chunk(chunk, clean_query)
                if score <= 0:
                    continue
                matches.append(_hit_from_chunk(chunk, score, clean_query))

        matches.sort(key=lambda item: (-item.score, item.path.casefold(), item.line_start))
        returned = matches[:limit]
        return SearchResponse(
            query=clean_query,
            scope=scope,
            total_matches=len(matches),
            returned=len(returned),
            items=returned,
            source_root=str(self.root),
        )

    def find_runbooks(self, topic: str, limit: int = 5) -> RunbookResponse:
        clean_topic = _validate_query(topic)
        direct = self.search(clean_topic, scope="runbook", limit=max(limit * 3, 10)).items
        routed = self._router_matches(clean_topic)
        by_path: dict[str, SearchHit] = {}
        for hit in [*routed, *direct]:
            current = by_path.get(hit.path)
            if current is None or hit.score > current.score:
                by_path[hit.path] = hit
        matches = sorted(by_path.values(), key=lambda item: (-item.score, item.path.casefold()))
        returned = matches[:limit]
        return RunbookResponse(
            topic=clean_topic,
            total_matches=len(matches),
            returned=len(returned),
            items=returned,
        )

    def read_section(
        self,
        path: str,
        heading: str | None = None,
        max_chars: int = 12_000,
    ) -> SectionResponse:
        document = self._load_relative(path)
        start_index = 0
        end_index = len(document.lines)
        matched_heading: str | None = None

        if heading:
            requested = _normalize_heading(heading)
            found: tuple[int, int, str] | None = None
            for index, line in enumerate(document.lines):
                match = _HEADING.match(line)
                if match and _normalize_heading(match.group(2)) == requested:
                    found = (index, len(match.group(1)), match.group(2).strip())
                    break
            if found is None:
                raise ValueError("Requested heading was not found in the Markdown document.")
            start_index, level, matched_heading = found
            for index in range(start_index + 1, len(document.lines)):
                match = _HEADING.match(document.lines[index])
                if match and len(match.group(1)) <= level:
                    end_index = index
                    break

        raw_content = "\n".join(document.lines[start_index:end_index]).strip()
        redacted, redactions = redact_sensitive_text(raw_content)
        truncated = len(redacted) > max_chars
        content = redacted[:max_chars]
        if truncated:
            content = content.rstrip() + "\n\n[TRUNCATED]"

        return SectionResponse(
            path=document.relative_path,
            title=document.title,
            heading=matched_heading,
            line_start=start_index + 1,
            line_end=end_index,
            content=content,
            truncated=truncated,
            redactions=redactions,
        )

    def _documents(self, scope: SearchScope) -> list[NoteDocument]:
        if not self.root.is_dir():
            raise ValueError("The configured ratio vault root is unavailable.")
        documents = []
        for path in sorted(self.root.rglob("*.md"), key=lambda item: str(item).casefold()):
            relative = path.relative_to(self.root)
            if any(part in _EXCLUDED_PARTS for part in relative.parts):
                continue
            try:
                document = _load_document(self.root, path)
            except OSError:
                # Unreadable files (permissions, locked handles) are skipped so one
                # broken note cannot take the whole retrieval surface down.
                continue
            if _in_scope(document, scope):
                documents.append(document)
        return documents

    def _load_relative(self, supplied_path: str) -> NoteDocument:
        if not supplied_path.strip():
            raise ValueError("A Markdown path is required.")
        relative = Path(supplied_path.replace("\\", "/"))
        if relative.is_absolute() or relative.suffix.casefold() != ".md":
            raise ValueError("Only relative Markdown paths inside the ratio vault are allowed.")
        if len(relative.as_posix()) > 260:
            raise ValueError("The requested path exceeds the 260 character limit.")
        candidate = (self.root / relative).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("The requested path escapes the ratio vault.")
        if not candidate.is_file():
            raise ValueError("The requested Markdown document does not exist.")
        if any(part in _EXCLUDED_PARTS for part in candidate.relative_to(self.root).parts):
            raise ValueError("The requested path is excluded from retrieval.")
        return _load_document(self.root, candidate)

    def _router_matches(self, topic: str) -> list[SearchHit]:
        router = self.root / ROUTER_PATH
        if not router.is_file():
            return []
        document = _load_document(self.root, router)
        routed: list[SearchHit] = []
        for chunk in _chunks(document):
            score = _score_chunk(chunk, topic)
            if score <= 0:
                continue
            for link in _document_links(chunk.text):
                normalized = unquote(link).replace("\\", "/").split("#", 1)[0]
                if not normalized.startswith("RUNBOOK/"):
                    continue
                relative = (
                    normalized
                    if normalized.casefold().endswith(".md")
                    else f"{normalized}.md"
                )
                try:
                    target = self._load_relative(relative)
                except ValueError:
                    continue
                routed.append(
                    SearchHit(
                        path=target.relative_path,
                        title=target.title,
                        heading=chunk.heading,
                        line_start=chunk.line_start,
                        score=score + 100,
                        snippet=_snippet(chunk.text, topic),
                        document_type=target.metadata.get("document_type"),
                        document_status=target.metadata.get("document_status"),
                        knowledge_scope=target.metadata.get("knowledge_scope"),
                    )
                )
        return routed


def _document_links(text: str) -> list[str]:
    links = list(_WIKILINK.findall(text))
    links.extend(_MARKDOWN_LINK.findall(text))
    return links


def _load_document(root: Path, path: Path) -> NoteDocument:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    metadata = _frontmatter(lines)
    tags = tuple(
        tag.strip().strip('"\'')
        for tag in metadata.get("tags", "").split(",")
        if tag.strip()
    )
    title = metadata.get("title") or path.stem
    for line in lines:
        match = _HEADING.match(line)
        if match and len(match.group(1)) == 1:
            title = match.group(2).strip()
            break
    return NoteDocument(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        lines=lines,
        title=title,
        metadata=metadata,
        tags=tags,
    )


def _frontmatter(lines: list[str]) -> dict[str, str]:
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, str] = {}
    list_key: str | None = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line[:1].isspace() and list_key:
            item = line.strip().lstrip("-").strip().strip('"\'')
            if item:
                current = metadata.get(list_key, "")
                metadata[list_key] = f"{current},{item}" if current else item
            continue
        list_key = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"\'')
        if not value.strip():
            list_key = key.strip()
    return metadata


def _chunks(document: NoteDocument) -> list[NoteChunk]:
    chunks: list[NoteChunk] = []
    current_heading: str | None = None
    current_start = 0
    for index, line in enumerate(document.lines):
        match = _HEADING.match(line)
        if not match:
            continue
        if index > current_start:
            text = "\n".join(document.lines[current_start:index]).strip()
            if text:
                chunks.append(
                    NoteChunk(document, current_heading, current_start + 1, text)
                )
        current_heading = match.group(2).strip()
        current_start = index
    text = "\n".join(document.lines[current_start:]).strip()
    if text:
        chunks.append(NoteChunk(document, current_heading, current_start + 1, text))
    return chunks


def _in_scope(document: NoteDocument, scope: SearchScope) -> bool:
    first_part = document.relative_path.split("/", 1)[0]
    if scope == "all":
        return True
    if scope == "runbook":
        return first_part == "RUNBOOK"
    knowledge_scope = document.metadata.get("knowledge_scope", "").casefold()
    if scope == "operational":
        return (
            "operational" in knowledge_scope
            or first_part in {"RUNBOOK", "运维笔记"}
            or document.relative_path == ROUTER_PATH
        )
    return not _in_scope(document, "operational")


def _validate_query(query: str) -> str:
    clean = " ".join(query.split())
    if not clean:
        raise ValueError("A non-empty search query is required.")
    if len(clean) > 200:
        raise ValueError("Search query exceeds 200 characters.")
    return clean


def _normalize_heading(heading: str) -> str:
    return heading.strip().lstrip("#").strip().casefold()


def _query_terms(query: str) -> list[str]:
    terms = [query.casefold()]
    terms.extend(part.casefold() for part in re.split(r"\s+", query) if len(part) >= 2)
    return list(dict.fromkeys(terms))


def _score_chunk(chunk: NoteChunk, query: str) -> int:
    terms = _query_terms(query)
    path = chunk.document.relative_path.casefold()
    title = chunk.document.title.casefold()
    heading = (chunk.heading or "").casefold()
    tags = " ".join(chunk.document.tags).casefold()
    links = " ".join(_document_links(chunk.text)).casefold()
    metadata = " ".join(chunk.document.metadata.values()).casefold()
    body = chunk.text.casefold()
    score = 0
    for index, term in enumerate(terms):
        multiplier = 2 if index == 0 else 1
        score += 60 * multiplier if term in title else 0
        score += 50 * multiplier if term in heading else 0
        score += 35 * multiplier if term in path else 0
        score += 25 * multiplier if term in tags else 0
        score += 30 * multiplier if term in links else 0
        score += 20 * multiplier if term in metadata else 0
        score += min(body.count(term), 5) * 8 * multiplier
    return score


def _snippet(text: str, query: str, width: int = 360) -> str:
    # Redact before collapsing whitespace: the assignment regex is anchored to
    # line starts, and a single-line compacted snippet would otherwise leak
    # `password: value` forms that never begin the compacted string.
    redacted_text, _ = redact_sensitive_text(text)
    compact = re.sub(r"\s+", " ", redacted_text).strip()
    lower = compact.casefold()
    positions = [lower.find(term) for term in _query_terms(query)]
    positions = [position for position in positions if position >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - width // 3)
    end = min(len(compact), start + width)
    snippet = compact[start:end]
    if start:
        snippet = "…" + snippet
    if end < len(compact):
        snippet += "…"
    return snippet


def _hit_from_chunk(chunk: NoteChunk, score: int, query: str) -> SearchHit:
    document = chunk.document
    return SearchHit(
        path=document.relative_path,
        title=document.title,
        heading=chunk.heading,
        line_start=chunk.line_start,
        score=score,
        snippet=_snippet(chunk.text, query),
        document_type=document.metadata.get("document_type"),
        document_status=document.metadata.get("document_status"),
        knowledge_scope=document.metadata.get("knowledge_scope"),
    )
