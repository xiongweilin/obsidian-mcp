from __future__ import annotations

from pathlib import Path

import pytest

from ratio_mcp.notes import ACTION_BOARD_PATH, NoteRepository


def test_read_action_board_structured_columns(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).read_action_board()

    assert result.path == ACTION_BOARD_PATH
    assert [column.name for column in result.columns] == ["当前主线", "已完成", "收件箱"]
    assert result.total_items == 3
    assert result.open_items == 2
    assert result.done_items == 1


def test_action_board_items_and_details(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).read_action_board()

    main_line = result.columns[0].items[0]
    assert main_line.status == "open"
    assert "正式会话 2" in main_line.text
    assert main_line.details == ["下一动作：先做预测。", "完成条件：能解释重试预算。"]

    done = result.columns[1].items[0]
    assert done.status == "done"
    assert done.details == ["证据：检查与测试全绿。"]


def test_action_board_frontmatter_fields(rich_vault: Path) -> None:
    result = NoteRepository(rich_vault).read_action_board()

    assert result.updated == "2026-08-09"
    assert result.last_verified == "2026-08-09"
    assert result.source_kind == "documentation"


def test_action_board_missing_raises(rich_vault: Path, tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(ValueError, match="does not exist"):
        NoteRepository(empty).read_action_board()
