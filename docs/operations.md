# 安装 / 升级 / 卸载 / 故障排查

## 前置条件

- Windows + [uv](https://docs.astral.sh/uv/)（本项目只用 `uv sync` / `uv run`，不全局安装 Python 依赖）；
- Python ≥3.12（`uv` 自动管理）；
- 只读目标 vault `D:\agent\obsidian`（缺失时检索工具报错，见故障排查）。

## 安装

```powershell
cd D:\agent\obsidian-mcp
uv sync
```

本地手动启动（STDIO 服务，等待 MCP Host 连接；终端没有普通提示符是正常现象）：

```powershell
uv run obsidian-mcp
```

验证命令：

```powershell
uv run ruff check .
uv run pytest
uv run python scripts\smoke_stdio.py
uv run python scripts\smoke_runtime.py
```

`smoke_runtime.py` 会访问真实 Windows、Docker 和个人云端，只输出每个范围的返回数量与警告数，不输出服务详情。

## Codex 本地 MCP 配置

Codex 使用全局 `~/.codex/config.toml` 的 STDIO 条目启动本项目。当前机器上 `[mcp_servers.obsidian]` 已配置（含 `command` 与 `args` 键）。如需在另一台机器配置：

```powershell
codex mcp add obsidian -- uv run --directory D:\agent\obsidian-mcp obsidian-mcp
```

查看与回滚：

```powershell
codex mcp get obsidian
codex mcp remove obsidian
```

> `~/.codex/config.toml` 由运行时管理、可能含密钥；**不要手工编辑其中的密钥值**，也不要输出其值。修改 MCP 配置后需重启 Codex 客户端或扩展。

## 升级

```powershell
cd D:\agent\obsidian-mcp
git pull
uv sync
uv run ruff check .
uv run pytest
```

升级后重启 Codex 客户端（或触发新会话），让新代码生效。接口升级是加法的：新工具与字段直接可用，既有工具不破坏。

## 卸载

```powershell
codex mcp remove obsidian
```

然后删除项目目录（`D:\agent\obsidian-mcp`，含 `.venv`）。卸载不影响 vault 内容，本项目从不写 vault。

## 常见故障排查

| 现象 | 原因与处理 |
| --- | --- |
| 启动后终端无输出、无提示符 | 正常：STDIO 服务在等 MCP Host；按 Ctrl+C 退出 |
| Codex 报 MCP 启动超时 | 首次 `uv sync` 未完成或依赖未装；先手动 `uv sync` 再重试 |
| `search_notes`/`read_section` 报 vault 不可用 | `D:\agent\obsidian` 不存在或不可访问；确认路径 |
| 中文显示为替换符 `�` | vault 文件非 UTF-8 编码；按设计容错读入（`errors="replace"`），不会崩溃，但请尽量用 UTF-8 保存笔记 |
| `query_runtime_status` 返回 warnings | 脚本缺失、命令失败或云不可达；warnings 不含敏感值，也不回退到旧文档 |
| `uv sync` 报 `obsidian-mcp.exe` 被占用 | 存在残留 MCP server 进程；先终止命令行含 `D:\agent\obsidian-mcp` 的 `uv`/`python`/`obsidian-mcp.exe` 进程（Codex 会按需重新拉起），再 `uv sync` |
| `uv run` 反复报 `obsidian-mcp.exe` 被占用（有常驻会话时） | 只影响控制台脚本重建，不影响代码（editable 安装直指 `src/`）；本地验证改用 `uv run --no-sync ...`，待会话结束进程退出后再 `uv sync` |
| 检索不到刚改的笔记 | 无索引缓存，每次请求扫当前文件；确认文件是 `.md`、不在排除目录（`.git`/`.obsidian` 等） |

## 生命周期与契约测试

仓库测试分为三类，CI（`.github/workflows/ci.yml`）分别执行：

| 类别 | 内容 | 本地运行 |
| --- | --- | --- |
| 常规单元测试 | 检索/运行时解析/隐私遮蔽 | `uv run pytest -q -m "not windows_only"` |
| 契约测试 | 真实子进程 + 标准库 JSON-RPC 客户端：tools/list、五工具成功路径、隐私拒绝、schema 快照漂移 | `uv run pytest -q -m contract` |
| Windows 专属 | 进程树结构、pwsh 超时 | `uv run pytest -q -m windows_only` |

`tools/list` schema 变更时 `test_schema_snapshot.py` 失败；确认是有意变更后：

```powershell
uv run python scripts\update_schema_snapshot.py
```

并提交更新后的 `tests/schema-snapshot.json`。

## 环境变量覆盖（仅测试/CI 使用）

`Settings.defaults()` 支持只读环境变量覆盖，供测试与 CI 指向夹具 vault；
这些变量只承载路径或整数，不承载任何凭据：

| 变量 | 覆盖项 |
| --- | --- |
| `OBSIDIAN_MCP_VAULT_ROOT` | vault 根目录 |
| `OBSIDIAN_MCP_COMMAND_TIMEOUT_SECONDS` | 子进程超时秒数 |
| `OBSIDIAN_MCP_WINDOWS_STATUS_SCRIPT` / `OBSIDIAN_MCP_CLOUD_STATUS_SCRIPT` | 状态脚本路径 |
| `OBSIDIAN_MCP_SSH_WRAPPER` | 云端 SSH 包装脚本路径 |
