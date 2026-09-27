# obsidian-mcp 项目指南

- 使用 `uv sync` 和 `uv run`；不要在全局安装项目依赖。
- 所有 MCP 工具保持只读，除非后续经过用户批准的接口变更明确增加写能力。
- 不得暴露任意 shell 执行、任意文件系统根、服务命令行、环境变量值、凭据、cookie、私钥或 `.env` 内容。
- 把 Markdown 视为文档证据，把运行时查询视为当前证据；绝不能把文档快照表述成实时状态。
- 保持现有公开工具名和结构化结果形态。契约扩展采用加法；破坏性决策记录在 `docs/decisions/`。
- 宣称完成前运行 `uv run ruff check .`、`uv run pytest`（包含 contract + lifecycle + windows markers）、`uv run python scripts/smoke_stdio.py` 和 `uv run python scripts/smoke_runtime.py`。远端路径失败时应报告失败，而不是用文档替代实时证据。
- 当本机活跃 MCP session 锁定 `obsidian-mcp.exe` 时，本地验证可使用 `uv run --no-sync ...`；CI runner 不受影响。未经批准，不要终止活跃 Codex session 的 MCP 进程。
- `tools/list` schema snapshot（`tests/schema-snapshot.json`）需要人工批准；有意的 schema 变更必须使用 `uv run python scripts/update_schema_snapshot.py` 重新生成，并同时提交。
