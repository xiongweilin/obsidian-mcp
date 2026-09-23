from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    runbook = tmp_path / "RUNBOOK"
    runbook.mkdir()
    (tmp_path / "README.md").write_text(
        """---
document_type: moc
document_status: active
knowledge_scope: operational
---
# 个人平台总览

## 网络入口

公网和 Tailscale 故障进入 [[RUNBOOK/环境运维手册]]。
""",
        encoding="utf-8",
    )
    (runbook / "环境运维手册.md").write_text(
        """---
document_type: runbook
document_status: active
knowledge_scope: operational
---
# 环境运维手册

## 网络

先检查 Tailscale 当前路径。

token: should-not-leave-the-server

## Docker

使用 Docker 管理平面确认状态。
""",
        encoding="utf-8",
    )
    (tmp_path / "概念.md").write_text("# 不变量\n\n状态可以变化。\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def rich_vault(tmp_path: Path) -> Path:
    """Deterministic vault exercising tags, aliases, links, a board, and malformed notes."""

    runbook = tmp_path / "RUNBOOK"
    runbook.mkdir()
    model = tmp_path / "领域模型"
    model.mkdir()
    (tmp_path / "README.md").write_text(
        """---
document_type: moc
document_status: active
knowledge_scope: operational
tags:
  - moc
  - dev-environment
---
# 个人平台总览

## 网络入口

公网故障进入 [[RUNBOOK/网络手册]]，恢复流程见 [[RUNBOOK/缺失手册]]。

## 循环入口

进入 [[RUNBOOK/循环甲]]。
""",
        encoding="utf-8",
    )
    (runbook / "网络手册.md").write_text(
        """---
document_type: runbook
document_status: active
knowledge_scope: operational
aliases:
  - 代号甲
  - 网络恢复
tags:
  - wifi
  - 网络
---
# 网络手册

## 检查

先看 Tailscale 状态。

password: do-not-leak-me
""",
        encoding="utf-8",
    )
    (runbook / "循环甲.md").write_text(
        "---\ndocument_type: runbook\nknowledge_scope: operational\n---\n"
        "# 循环甲\n\n进入 [[RUNBOOK/循环乙]]。\n"
    )
    (runbook / "循环乙.md").write_text(
        "---\ndocument_type: runbook\nknowledge_scope: operational\n---\n"
        "# 循环乙\n\n回到 [[RUNBOOK/循环甲]]。\n"
    )
    (model / "无标签词.md").write_text(
        """---
document_type: domain-model
tags:
  - unique-tag-xyz
---
# 无标签词

正文不包含标签词。
""",
        encoding="utf-8",
    )
    # Non-UTF-8 (GBK) file: must be tolerated, not crash the repository.
    (tmp_path / "编码测试.md").write_bytes("标题\n内容包含中文。\n".encode("gbk"))
    # Abnormal Markdown: no headings, malformed heading syntax, lone hashes.
    (tmp_path / "异常笔记.md").write_text(
        "只有正文，没有标题。\n#无空格标题\n###\n#### 尾随空格  \n---\n", encoding="utf-8"
    )
    return tmp_path
