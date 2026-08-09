# ratio-mcp — 公开说明（脱敏骨架）

> 本文档是公开可分享的脱敏版本：不含任何个人路径、主机名、凭据或真实目录细节。可在开源/分享场景下作为 README 骨架使用。

## 这是什么

`ratio-mcp` 是一个**只读**的 MCP（Model Context Protocol）服务器，面向个人 Markdown 知识库。它让 Codex 等 Agent 通过窄接口定位文档、读取小节、查看行动看板，并查询本机与云端的运行状态——但不给 Agent 任意命令执行或任意文件访问。

设计要点：

- 只读：不写知识库，不持久化查询，不监听网络端口；
- 确定性检索：按标题、标签、链接、路径、frontmatter 与正文打分，无向量库、无 embedding；
- 安全边界：路径白名单 + 排除目录 + 输出前凭据遮蔽；
- 明确证据语义：文档结果是快照（`source_kind=documentation`），运行状态是实时（`source_kind=runtime`）。

## 目录结构

```text
ratio-mcp/
├── pyproject.toml          # uv 工程配置
├── src/ratio_mcp/
│   ├── server.py           # MCP 工具定义
│   ├── notes.py            # Markdown 检索、小节读取、行动看板解析
│   ├── runtime.py          # 只读运行状态查询
│   ├── privacy.py          # 凭据遮蔽
│   ├── config.py           # 路径与命令配置
│   └── models.py           # 返回结构（Pydantic）
├── scripts/                # smoke 验证与只读查询脚本
├── tests/                  # 确定性测试（假知识库 + 可选真实库只读基线）
└── docs/                   # 边界、契约、评估与运维文档
```

## 工具列表

| 工具 | 用途 |
| --- | --- |
| `find_runbook` | 按运维主题定位单一相关运行手册 |
| `search_notes` | 按标题/标签/链接/全文做确定性检索 |
| `read_section` | 读取一个 Markdown 文件或指定标题小节（有长度上限） |
| `read_action_board` | 把行动看板解析为结构化列与勾选项 |
| `query_runtime_status` | 查询本机服务、容器与云端的实时状态 |

## 如何接入

1. 使用 `uv sync` 安装依赖；
2. 在 MCP 客户端配置中注册 STDIO 启动命令：`uv run --directory <repo-path> ratio-mcp`；
3. 重启客户端后即可调用上述工具。

详细安装、升级、卸载与故障排查见 `docs/operations.md`。

## 安全承诺

- 不执行任意 shell 命令、不访问任意文件系统根、不读取凭据文件；
- 返回内容经过凭据形式遮蔽；
- 无索引、无缓存、无持久化；进程退出即无状态残留。
