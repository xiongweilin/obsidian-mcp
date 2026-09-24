from __future__ import annotations

import time
from pathlib import Path

import pytest

from obsidian_mcp.notes import NoteRepository

_REAL_VAULT = Path(r"D:\agent\obsidian")


@pytest.fixture
def wide_vault(tmp_path: Path) -> Path:
    """A synthetic vault with ~120 notes to establish a deterministic scan baseline."""

    runbook = tmp_path / "RUNBOOK"
    runbook.mkdir()
    model = tmp_path / "元模型"
    model.mkdir()
    (model / "个人平台总览.md").write_text(
        "# 个人平台总览\n\n## 入口\n\n进入 [[RUNBOOK/手册 0]]。\n", encoding="utf-8"
    )
    for index in range(120):
        (runbook / f"手册 {index}.md").write_text(
            f"---\ndocument_type: runbook\nknowledge_scope: operational\n---\n"
            f"# 手册 {index}\n\n## 检查\n\n第 {index} 份手册的检查正文。\n",
            encoding="utf-8",
        )
    return tmp_path


def test_full_scan_stays_under_budget(wide_vault: Path) -> None:
    repository = NoteRepository(wide_vault)
    started = time.perf_counter()

    result = repository.search("检查", scope="runbook", limit=10)

    elapsed_ms = (time.perf_counter() - started) * 1000
    assert result.returned == 10
    assert elapsed_ms < 3000, f"full scan took {elapsed_ms:.0f}ms"


def test_router_read_stays_under_budget(wide_vault: Path) -> None:
    repository = NoteRepository(wide_vault)
    started = time.perf_counter()

    result = repository.read_section("元模型/个人平台总览.md")

    elapsed_ms = (time.perf_counter() - started) * 1000
    assert result.path == "元模型/个人平台总览.md"
    assert elapsed_ms < 500, f"router read took {elapsed_ms:.0f}ms"


@pytest.mark.skipif(
    not _REAL_VAULT.is_dir(),
    reason="real ratio vault is not available on this machine",
)
def test_real_vault_readonly_subset_baselines() -> None:
    """Read-only smoke against the real vault with a <200ms home-document budget."""

    repository = NoteRepository(_REAL_VAULT)

    started = time.perf_counter()
    home = repository.read_section("README.md")
    home_ms = (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    router = repository.read_section("RUNBOOK/项目与仓库索引.md")
    router_ms = (time.perf_counter() - started) * 1000

    search = repository.search("环境运维", scope="runbook", limit=5)

    assert home.path == "README.md"
    assert router.path == "RUNBOOK/项目与仓库索引.md"
    assert search.returned >= 1
    assert home_ms < 200, f"home README read took {home_ms:.0f}ms (budget 200ms)"
    assert router_ms < 200, f"router read took {router_ms:.0f}ms (budget 200ms)"
