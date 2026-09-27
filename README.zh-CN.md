# obsidian-mcp

[![CI](https://github.com/xiongweilin/obsidian-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/xiongweilin/obsidian-mcp/actions/workflows/ci.yml) [![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=metratio_obsidian-mcp&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=metratio_obsidian-mcp) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](pyproject.toml) [![Docs: EN / 中文](https://img.shields.io/badge/docs-EN%20%7C%20%E4%B8%AD%E6%96%87-blue.svg)](README.zh-CN.md)

[English](README.md) | [简体中文](README.zh-CN.md)

`obsidian-mcp` 是面向个人 `D:\agent\obsidian` 知识库和实时运行环境的只读 MCP 服务。它不构建向量库、不复制知识库，也不允许 Agent 执行任意命令；Codex 只通过四个边界明确的接口定位文档、读取章节，并查询当前 Windows、Docker 和云端状态。

## 工具契约

| 工具 | 用途 | 事实类型 |
| --- | --- | --- |
| `find_runbook` | 通过知识库 `README.md` 路由和 `RUNBOOK` 定位 runbook | 文档导航 |
| `search_notes` | 对标题、标签、链接、路径、frontmatter、标题块和正文进行确定性检索 | 文档证据 |
| `read_section` | 读取知识库中的一个 Markdown 文件或指定标题章节 | 文档证据 |
| `query_runtime_status` | 查询 Windows 服务、本地 Docker 或云端 systemd/Docker | 实时证据 |

所有列表接口都有结果数量上限；路径被限制在知识库内（排除 `.git`、`.obsidian` 等目录）；`read_section` 只接受 Markdown；非 UTF-8 文件会用替换字符读取；搜索摘要和正文在返回前会遮蔽常见敏感值格式。返回的 Markdown 是证据数据，不是 Agent 指令。运行时工具只执行代码中固定的只读命令，不接受 shell 命令参数。

## 文档

- [项目边界](docs/boundaries.md)：职责、只读边界、路径 allowlist 和禁止读取项。
- [工具契约](docs/contracts.md)：四个工具的输入/输出、错误语义和长度限制。
- [轻量索引与 RAG](docs/rag-vs-index.md)：权衡决策（未实现 RAG）。
- [安装 / 升级 / 卸载 / 排障](docs/operations.md)。
- 架构决策：[ADR-0001](docs/decisions/0001-local-read-only-stdio.md)。

## 快速开始

```powershell
cd D:\agent\obsidian-mcp
uv sync
uv run obsidian-mcp
```

最后一条命令会启动 STDIO 服务并等待 MCP host 连接；终端里没有出现提示符属于预期行为。

## 验证命令

```powershell
uv run ruff check .
uv run pytest
uv run python scripts\smoke_stdio.py
uv run python scripts\smoke_runtime.py
```

`smoke_runtime.py` 会触达真实 Windows、Docker 和个人云环境，但只打印每个 scope 返回的数量和警告数量，不打印服务细节。

测试套件还包含两类真实子进程测试（CI 和本地 `pytest` 都会自动运行）：

- **契约测试**（`tests/test_contract_stdio.py`）：stdlib JSON-RPC 客户端直接连接真实 server 进程，验证 `tools/list`、四个工具的成功路径、隐私遮蔽、拒绝路径以及 schema snapshot 漂移。
- **生命周期测试**（`tests/test_lifecycle.py`）：验证并发连接进程结构、客户端正常关闭/异常退出后的进程回收，以及子进程超时。

`tools/list` schema snapshot 位于 `tests/schema-snapshot.json`。schema 发生变化时，`test_schema_snapshot.py` 会失败；人工确认后，需要运行 `uv run python scripts/update_schema_snapshot.py` 重新生成并提交 snapshot。

> 当本机存在常驻 MCP session 时，`uv sync` 可能因为 `obsidian-mcp.exe` 被锁定而失败（见 `docs/operations.md`）；本地验证请使用 `uv run --no-sync ...`，全新 runner 上的 CI 不受影响。

## Codex 集成

Codex 通过全局 `~/.codex/config.toml` 中的 STDIO 条目启动本项目；同一主机上的 CLI、IDE 扩展和桌面应用共用这份配置。当前安装命令：

```powershell
codex mcp add obsidian -- uv run --directory D:\agent\obsidian-mcp obsidian-mcp
```

查看和回滚：

```powershell
codex mcp get obsidian
codex mcp remove obsidian
```

修改 MCP 配置后，重启 Codex 客户端或扩展。本项目本身不监听端口；Codex 按需启动进程。

## 运行时边界

- 默认知识库：`D:\agent\obsidian`。
- 默认云端入口：`~/.local/bin/Invoke-MetratioSsh.ps1`。
- 不读取非 Markdown 文件，不返回服务可执行文件路径或参数，也不打印环境变量。
- 文档中的 `operational-snapshot` 只用于导航和漂移线索；“当前是否正在运行”必须通过 `query_runtime_status` 回答。
- MCP 不持久化检索内容、运行时结果或日志数据；进程退出后不会新增保留内容。

架构选择见 [ADR-0001](docs/decisions/0001-local-read-only-stdio.md)。
