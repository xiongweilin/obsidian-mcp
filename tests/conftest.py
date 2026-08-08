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
    (tmp_path / "个人平台总览.md").write_text(
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
