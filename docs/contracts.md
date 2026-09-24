# 工具契约（contracts）

本文件定义 obsidian-mcp 0.3 的四个只读 MCP 工具。知识库文档只提供文档证据；Responsibility / Work 等运行状态必须从其权威运行时 owner 获取，不能从 Markdown 推断。

## 通用约定

- 文档结果：`source_kind=documentation`，是知识库证据，不是 current runtime truth。
- 运行状态：`source_kind=runtime` 且 `is_live=true`，来自本次固定只读查询。
- Markdown 返回前经过凭据形式遮蔽；不持久化查询、文档或运行结果。
- vault 读取只允许根目录内相对 Markdown 路径；排除 `.git`、`.obsidian`、`.venv`、`node_modules`、`__pycache__`。
- 无结果返回空结构；非法输入返回 tool error。

## 1. find_runbook

从 vault 根 `README.md` 的 RUNBOOK 链接与 `RUNBOOK/` 全文中定位相关运行手册。README 是 locator/router，不复制项目 current truth。

输入：`topic` 1–200 字符；`limit` 1–10。  
返回：`RunbookResponse`，`router_path="README.md"`。

路由只解析 README 一层；不存在的目标静默跳过，再由 RUNBOOK 全文检索补充结果。

## 2. search_notes

对标题、heading、路径、Markdown/Wikilink、tags、frontmatter 与正文做确定性检索，不建立向量库或持久索引。

`scope`：`all` / `runbook` / `operational` / `conceptual`。  
`query` ≤200 字符；`limit` 1–20。

## 3. read_section

读取 vault 内一个 Markdown 文件或精确 heading 小节。

- path 必须为 vault 内相对 `.md`，≤260 字符；
- heading ≤200 字符；
- max_chars 500–20000，默认 12000；
- 路径逃逸、排除目录、非 Markdown、文件/heading 不存在均为 tool error。

## 4. query_runtime_status

只执行代码内固定的只读 Windows / Docker / cloud 查询，不接受 shell 命令参数。

`scope`：`windows_services` / `local_docker` / `cloud`。  
运行失败以 warnings 返回，不回退到旧文档冒充实时状态。
