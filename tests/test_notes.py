from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_mcp.notes import NoteRepository


def test_search_returns_heading_chunk(vault: Path) -> None:
    result = NoteRepository(vault).search("Tailscale", scope="operational", limit=5)

    assert result.returned >= 1
    assert result.items[0].path == "RUNBOOK/环境运维手册.md"
    assert result.items[0].heading == "网络"
    assert result.items[0].source_kind == "documentation"


def test_find_runbook_uses_router_link(vault: Path) -> None:
    result = NoteRepository(vault).find_runbooks("公网", limit=5)

    assert result.returned >= 1
    assert result.items[0].path == "RUNBOOK/环境运维手册.md"
    assert result.items[0].score >= 100


def test_read_section_redacts_secret_assignment(vault: Path) -> None:
    result = NoteRepository(vault).read_section("RUNBOOK/环境运维手册.md", "网络")

    assert "should-not-leave" not in result.content
    assert "token: [REDACTED]" in result.content
    assert result.redactions == 1
    assert "## Docker" not in result.content


def test_read_section_rejects_path_escape(vault: Path) -> None:
    with pytest.raises(ValueError, match="escapes"):
        NoteRepository(vault).read_section("../outside.md")


def test_scope_separates_conceptual_notes(vault: Path) -> None:
    result = NoteRepository(vault).search("状态", scope="conceptual")

    assert [item.path for item in result.items] == ["概念.md"]
