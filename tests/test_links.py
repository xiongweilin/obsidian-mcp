from __future__ import annotations

from pathlib import Path

from ratio_mcp.notes import NoteRepository


def test_find_runbook_skips_broken_router_links(rich_vault: Path) -> None:
    """The router points at RUNBOOK/缺失手册.md which does not exist: no crash, no hit."""

    result = NoteRepository(rich_vault).find_runbooks("公网故障", limit=5)

    paths = [item.path for item in result.items]
    assert "RUNBOOK/缺失手册.md" not in paths
    assert "RUNBOOK/网络手册.md" in paths


def test_find_runbook_dedupes_by_path_keeping_best_score(rich_vault: Path) -> None:
    """Router routing and direct search may both match; the same file appears once."""

    result = NoteRepository(rich_vault).find_runbooks("网络手册", limit=10)

    paths = [item.path for item in result.items]
    assert paths.count("RUNBOOK/网络手册.md") == 1
    assert result.returned == len(result.items)


def test_cyclic_runbook_links_terminate(rich_vault: Path) -> None:
    """循环甲 -> 循环乙 -> 循环甲: routing must terminate and return both files once."""

    result = NoteRepository(rich_vault).find_runbooks("循环", limit=10)

    paths = [item.path for item in result.items]
    assert paths.count("RUNBOOK/循环甲.md") == 1
    assert paths.count("RUNBOOK/循环乙.md") == 1
    assert result.total_matches >= 2


def test_search_with_no_results_returns_empty_structure(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).search("绝无此词xyzzy", scope="all")

    assert result.total_matches == 0
    assert result.returned == 0
    assert result.items == []
