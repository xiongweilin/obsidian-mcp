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
    router_path: str = "元模型/个人平台总览.md"


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


class ActionBoardItem(BaseModel):
    text: str = Field(description="Main line of the checkbox item.")
    status: Literal["open", "done"] = Field(description="Checkbox state: open or done.")
    details: list[str] = Field(
        default_factory=list,
        description="Indented sub-bullets under the item (e.g. 下一动作/完成条件/证据).",
    )


class ActionBoardColumn(BaseModel):
    name: str = Field(description="Section heading of the board column.")
    items: list[ActionBoardItem]


class ActionBoardResponse(BaseModel):
    path: str = Field(description="Path relative to the ratio vault.")
    title: str
    columns: list[ActionBoardColumn]
    total_items: int = Field(ge=0)
    open_items: int = Field(ge=0)
    done_items: int = Field(ge=0)
    updated: str | None = None
    last_verified: str | None = None
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
