# Sonar MCP 只读配置候选（已停用，未启用）

> 状态：**候选配置，已停用，未启用**。恢复启用需要：① 人工在
> `~/.codex/config.toml` 填入 `SONARQUBE_TOKEN`；② 重启 Codex 客户端；
> ③ 确认不再产生 `sonarqube-mcp` 容器泄漏（见下文历史）。

## 背景与历史（2026-08-09）

SonarQube MCP（`sonarsource/sonarqube-mcp`）通过 SonarQube CLI
`sonar.exe run mcp` 以容器方式运行：**每个 MCP 连接都会执行一次
`docker run --rm sonarsource/sonarqube-mcp`**，且会话结束后进程与容器不被
客户端回收，会累积运行中的 `sonarqube-mcp` 容器与 `sonar.exe` 进程
（详见 vault《环境运维手册》2026-08-09 记录）。据此，`[mcp_servers.sonarqube]`
已于 2026-08-09 从 Codex 配置移除（config.toml 中保留注释块）。本文件记录
只读候选形态，供未来环境修复后重新评估。

## 候选配置（stdin/stdout 形态）

```toml
[mcp_servers.sonarqube]
command = "sonar"
args = ["run", "mcp", "--read-only", "--toolsets", "issues,quality-gates"]
# env 由人工填写，不在文档中落值：
#   SONARQUBE_TOKEN=<人工填写>
#   SONARQUBE_URL=https://...（SonarQube Server 时；Cloud 用 SONARQUBE_ORG）
```

本机 CLI 版本 `sonar.exe run mcp` v1.2.0 实测支持 `--read-only` 与
`--toolsets`（`sonar.exe run mcp --help` 输出确认）。

## 与官方工具清单的核对

- 官方文档：<https://docs.sonarsource.com/sonarqube-mcp-server/reference/tools>
  （工具清单）与
  <https://docs.sonarsource.com/sonarqube-mcp-server/reference/environment-variables>
  （环境变量约定）。
- 候选 `--toolsets issues,quality-gates` 与官方 toolset 名称一致：
  `issues`（issue 读取/搜索）、`quality-gates`（质量门状态）；`projects`
  toolset 官方总是自动启用（其他工具依赖它）。
- 只读约束：CLI 的 `--read-only` 与容器形态的 `SONARQUBE_READ_ONLY=true`
  等价；候选同时只启用只读语义的 toolset，不启用 `webhooks`、`cag` 等
  写向工具。
- 环境约定：官方要求 `SONARQUBE_TOKEN`（用户 token），Server 形态另需
  `SONARQUBE_URL`，Cloud 形态用 `SONARQUBE_ORG`。**token 只能由人工填写**
  且本仓库任何文档都不记录其值。

## 启用前置条件（当前不满足，故保持停用）

1. 容器泄漏根因修复：Codex 客户端需能回收其拉起的 stdio MCP 进程/容器
   （vault 记录表明 2026-08-09 起由 `DataRotationWeekly` 每周兜底清理，
   根因在客户端侧）。
2. 人工在 config.toml 的 `[mcp_servers.sonarqube]` env 中填写
   `SONARQUBE_TOKEN`（不提交到任何仓库）。
3. 重启 Codex 客户端使配置生效，并确认 `docker ps` 不再累积
   `sonarqube-mcp` 容器。

在条件满足前，质量门禁继续走 `sonar-scanner` CLI（env-doctor 现有检查），
不依赖 MCP。
