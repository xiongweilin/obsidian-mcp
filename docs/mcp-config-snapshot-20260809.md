# Codex MCP 配置脱敏快照（2026-08-09）

> 本文件记录 `~/.codex/config.toml` 的 `[mcp_servers]` 结构快照（键名 + 命令 + 参数；**值已脱敏**）。
> 生成时间：2026-08-09。凭据值（token、密码、env 值）一律不记录，任何字段都不含密钥值。

## Sonar MCP 移除记录

- **`[mcp_servers.sonarqube]` 已于 2026-08-09 从 Codex 配置移除**（config.toml 中仅保留注释块，见候选文档 [sonar-mcp-candidate.md](sonar-mcp-candidate.md)）。
- 移除原因：`sonar.exe run mcp` 每次连接拉起 `sonarqube-mcp` 容器且客户端不回收，导致容器/进程泄漏（vault《环境运维手册》2026-08-09 记录）。
- 质量门禁改用 `sonar-scanner` CLI，不受影响。

## mcp_servers 结构快照

| Server | 启动方式（command + args） | 备注（值脱敏） |
| --- | --- | --- |
| `github` | `%USERPROFILE%\scoop\shims\pwsh.exe -NoProfile -NonInteractive -File %USERPROFILE%\.local\bin\codex-credential-broker.ps1 run-mcp github-mcp` | startup_timeout_sec=[REDACTED]；tool_timeout_sec=[REDACTED]；default_tools_approval_mode=[REDACTED] |
| `node_repl` | `%USERPROFILE%\AppData\Local\OpenAI\Codex\runtimes\cua_node\f1bf3cd3a5929acd\bin\node_repl.exe` | env 键名: BROWSER_USE_AVAILABLE_BACKENDS, BROWSER_USE_CODEX_APP_BUILD_FLAVOR, BROWSER_USE_CODEX_APP_VERSION, CODEX_CLI_PATH, CODEX_HOME, NODE_REPL_INSTRUCTIONS_USE_CASE_BROWSER, NODE_REPL_INSTRUCTIONS_USE_CASE_CHROME, NODE_REPL_NATIVE_PIPE_CONNECT_TIMEOUT_MS, NODE_REPL_NODE_MODULE_DIRS, NODE_REPL_NODE_PATH, NODE_REPL_TRUSTED_BROWSER_CLIENT_SHA256S, NODE_REPL_TRUSTED_CODE_PATHS, SKY_CUA_NATIVE_PIPE, SKY_CUA_NATIVE_PIPE_DIRECTORY（值脱敏）；startup_timeout_sec=[REDACTED] |
| `openaiDeveloperDocs` | `remote url=https://developers.openai.com/mcp` | default_tools_approval_mode=[REDACTED] |
| `ratio` | `%USERPROFILE%\scoop\shims\uv.exe run --directory D:\download\agent\ratio-mcp ratio-mcp` |  |

## 关键结论

- GitHub MCP 通过 `codex-credential-broker.ps1 run-mcp github-mcp` 启动（命令 + 参数如上表）；
  凭据存于 Windows 凭据管理器，**MCP 配置不引用任何凭据值**，token 只在进程环境里按需注入并随后清除。
- 所有 env 值、approval 模式、超时等字段在快照中统一脱敏为 `[REDACTED]`；
  本快照本身可安全提交，但**不代表未来配置不变**——修改 MCP 配置后需重新生成。
