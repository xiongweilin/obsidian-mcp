# ratio-mcp

`ratio-mcp` 是面向个人 `D:\download\ratio` 知识库和真实运行环境的只读 MCP 服务。它不建立向量库，不复制知识库，也不让 Agent 执行任意命令；Codex 通过四个窄接口定位文档、读取小节并查询当前 Windows、Docker 与云端状态。

## 工具契约

| 工具 | 用途 | 事实类型 |
| --- | --- | --- |
| `find_runbook` | 从 `个人平台总览.md` 和 `RUNBOOK` 中定位单一运行手册 | 文档导航 |
| `search_notes` | 按标题、路径、frontmatter、标题块和正文做确定性检索 | 文档证据 |
| `read_section` | 读取知识库内一个 Markdown 文件或指定标题小节 | 文档证据 |
| `query_runtime_status` | 查询 Windows 服务、本机 Docker 或云端 systemd/Docker | 实时证据 |

所有列表接口都有数量上限；路径被限制在知识库内；`read_section` 只接受 Markdown；搜索摘要和正文返回前会遮蔽常见凭据形式。返回的 Markdown 是证据数据而不是 Agent 指令。运行时工具只执行代码中固定的只读命令，不接受 shell 命令参数。

## 快速开始

```powershell
cd D:\download\agent\ratio-mcp
uv sync
uv run ratio-mcp
```

最后一条命令启动 STDIO 服务并等待 MCP Host 连接，终端中没有普通提示符是正常行为。

## 验证命令

```powershell
uv run ruff check .
uv run pytest
uv run python scripts\smoke_stdio.py
uv run python scripts\smoke_runtime.py
```

`smoke_runtime.py` 会访问真实 Windows、Docker 和个人云端，只输出每个范围的返回数量与警告数，不输出服务详情。

## Codex 接入

Codex 使用全局 `~/.codex/config.toml` 中的 STDIO 条目启动本项目；CLI、IDE 扩展和桌面 App 在同一台主机上共享该配置。当前安装命令为：

```powershell
codex mcp add ratio -- %USERPROFILE%\scoop\shims\uv.exe run --directory D:\download\agent\ratio-mcp ratio-mcp
```

查看与回滚：

```powershell
codex mcp get ratio
codex mcp remove ratio
```

修改 MCP 配置后需要重启 Codex 客户端或扩展。项目本身不监听端口，Codex 按需启动进程。

## 运行边界

- 默认知识库：`D:\download\ratio`。
- 默认云端入口：`%USERPROFILE%\.local\bin\Invoke-RatioSsh.ps1`。
- 不读取非 Markdown 文件，不返回服务可执行路径或参数，不打印环境变量。
- 文档中的 `operational-snapshot` 只能用于导航和差异线索；“当前是否运行”必须调用 `query_runtime_status`。
- MCP 不保存检索内容、运行时结果或日志数据；进程退出后没有新增数据保留。

架构选择见 [ADR-0001](docs/decisions/0001-local-read-only-stdio.md)。
