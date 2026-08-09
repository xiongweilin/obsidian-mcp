from __future__ import annotations

from pathlib import Path

import pytest

from ratio_mcp.notes import NoteRepository


def test_search_matches_title(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).search("网络手册", scope="all")

    assert any(item.path == "RUNBOOK/网络手册.md" for item in result.items)


def test_search_matches_yaml_list_tag(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).search("unique-tag-xyz", scope="all")

    # The tag is the only signal, so every hit must be this file (per-chunk hits
    # for the same document are expected and documented).
    assert len(result.items) >= 1
    assert {item.path for item in result.items} == {"领域模型/无标签词.md"}


def test_search_matches_alias_from_yaml_list(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).search("代号甲", scope="all")

    assert any(item.path == "RUNBOOK/网络手册.md" for item in result.items)


def test_search_matches_wikilink_target(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).search("循环乙", scope="all")

    paths = [item.path for item in result.items]
    assert "RUNBOOK/循环乙.md" in paths
    assert "RUNBOOK/循环甲.md" in paths  # found through the [[RUNBOOK/循环乙]] link


def test_search_fulltext_without_headings(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).search("正文不包含标签词", scope="all")

    assert [item.path for item in result.items] == ["领域模型/无标签词.md"]


def test_non_utf8_file_is_tolerated(rich_vault: Path) -> None:
    repository = NoteRepository(rich_vault)

    result = repository.search("中文", scope="all")
    section = repository.read_section("编码测试.md")

    assert section.path == "编码测试.md"
    assert "\ufffd" in section.content or "中文" in section.content
    assert result.returned >= 0  # the GBK file must never crash the scan


def test_abnormal_markdown_is_tolerated(rich_vault: Path) -> None:
    repository = NoteRepository(rich_vault)

    result = repository.read_section("异常笔记.md")

    assert "只有正文" in result.content
    assert result.heading is None
    assert repository.search("尾随空格").returned >= 1


def test_path_accepts_backslashes_and_dots(rich_vault: Path) -> None:
    repository = NoteRepository(rich_vault)

    backslash = repository.read_section("RUNBOOK\\网络手册.md")
    dotted = repository.read_section("./RUNBOOK/网络手册.md")
    traversal_inside = repository.read_section("RUNBOOK/../RUNBOOK/网络手册.md")

    assert backslash.path == "RUNBOOK/网络手册.md"
    assert dotted.path == "RUNBOOK/网络手册.md"
    assert traversal_inside.path == "RUNBOOK/网络手册.md"


@pytest.mark.parametrize(
    "bad_path",
    [
        "../outside.md",
        "..\\outside.md",
        "RUNBOOK/../../outside.md",
        str(Path.cwd() / "outside.md"),
        "C:\\Windows\\win.ini",
        "\\\\server\\share\\note.md",
        "notes.txt",
        "",
        "RUNBOOK/" + "a" * 300 + ".md",
    ],
)
def test_path_rejects_escape_and_invalid_forms(rich_vault: Path, bad_path: str) -> None:
    with pytest.raises(ValueError):
        NoteRepository(rich_vault).read_section(bad_path)


def test_read_section_rejects_unknown_heading(rich_vault: Path) -> None:
    with pytest.raises(ValueError, match="not found"):
        NoteRepository(rich_vault).read_section("RUNBOOK/网络手册.md", "不存在的标题")


def test_read_section_accepts_heading_with_hash_prefix(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).read_section("RUNBOOK/网络手册.md", "## 检查")

    assert result.heading == "检查"
    assert "Tailscale" in result.content


def test_read_section_truncates_and_marks(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).read_section(
        "当前行动看板.md", max_chars=100
    )

    assert result.truncated
    assert result.content.endswith("[TRUNCATED]")
    assert len(result.content) <= 100 + len("\n\n[TRUNCATED]")


def test_read_section_redacts_secret_assignment(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).read_section("RUNBOOK/网络手册.md", "检查")

    assert "do-not-leak-me" not in result.content
    assert result.redactions >= 1


def test_query_validation_bounds(rich_vault: Path) -> None:
    repository = NoteRepository(rich_vault)

    with pytest.raises(ValueError, match="non-empty"):
        repository.search("   ")
    with pytest.raises(ValueError, match="200 characters"):
        repository.search("词" * 201)
    with pytest.raises(ValueError, match="200 characters"):
        repository.find_runbooks("词" * 201)
