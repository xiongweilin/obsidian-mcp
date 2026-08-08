from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    path: str = Field(description="Path relative to the ratio vault.")
    title: str
    heading: str | None = None
    line_start: int = Field(ge=1)
    score: int = Field(ge=0)
    snippet: str
    document_type: str | None = None
    document_status: str | None = None
    knowledge_scope: str | None = None
    source_kind: Literal["documentation"] = "documentation"


class SearchResponse(BaseModel):
    query: str
    scope: str
    total_matches: int = Field(ge=0)
    returned: int = Field(ge=0)
    items: list[SearchHit]
    source_root: str


class RunbookResponse(BaseModel):
    topic: str
    total_matches: int = Field(ge=0)
    returned: int = Field(ge=0)
    items: list[SearchHit]
    router_path: str = "个人平台总览.md"


class SectionResponse(BaseModel):
    path: str
    title: str
    heading: str | None = None
    line_start: int = Field(ge=1)
    line_end: int = Field(ge=1)
    content: str
    truncated: bool
    redactions: int = Field(ge=0)
    source_kind: Literal["documentation"] = "documentation"


class RuntimeItem(BaseModel):
    kind: str
    name: str
    state: str
    summary: str = ""


class RuntimeStatusResponse(BaseModel):
    scope: str
    observed_at: str
    query: str
    returned: int = Field(ge=0)
    items: list[RuntimeItem]
    warnings: list[str]
    source_kind: Literal["runtime"] = "runtime"
    is_live: Literal[True] = True
