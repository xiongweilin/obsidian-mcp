# 工具契约（contracts）

本文件是五个 MCP 工具的稳定输入输出契约。实现位于 `src/ratio_mcp/`，模型定义在 `models.py`，确定性测试在 `tests/`。任何对参数、返回结构或错误语义的破坏性修改都需要新的 ADR。

## 0. 通用约定

### 错误语义分类

所有工具遵循同一套错误语义，调用方据此区分"出错"与"没有结果"：

| 类别 | 表现 | 处理 |
| --- | --- | --- |
| 输入错误 | 抛 `ValueError`，MCP 返回 tool error | 参数非法、路径越界、标题不存在等，调用方应修正输入 |
| 无结果 | 返回空结构（`items=[]`、`total_matches=0`） | 正常结果，不是错误；可换词或放宽 scope |
| 重复结果 | `find_runbook` 按路径去重保留最高分；`search_notes` 同一文档可因多 chunk 出现多次 | 语义不同，见各工具说明 |
| 过期结果 | 不可能发生：无缓存、无持久化；文档=快照（`source_kind=documentation`），运行时=实时（`is_live=true`） | 需要当前事实时必须调用 `query_runtime_status` |

### 长度限制汇总

| 输入 | 上限 | 工具 |
| --- | --- | --- |
| `query` / `topic` | 200 字符 | `search_notes`、`find_runbook` |
| 运行时 `query` 过滤 | 100 字符 | `query_runtime_status` |
| `path` | 260 字符，且必须为 vault 内相对 `.md` | `read_section` |
| `heading` | 200 字符 | `read_section` |
| `max_chars` | 500–20000（默认 12000） | `read_section` |
| `limit`（search） | 1–20（默认 10） | `search_notes` |
| `limit`（runbook） | 1–10（默认 5） | `find_runbook` |
| `limit`（runtime） | 1–100（默认 50） | `query_runtime_status` |

内部固定上限：搜索摘要 ≤360 字符，看板不设额外上限（单文件）。

### 返回前遮蔽

所有返回文本（搜索摘要、正文、看板条目）在返回前经过 `privacy.py::redact_sensitive_text`：遮蔽 PEM 私钥、`password/token/secret/api_key/authorization` 等赋值、带基本认证的 URL、JWT、常见 token 前缀（`ghp_`/`github_pat_`/`sk-`/`AKID` 等）。`redactions` 字段记录本次返回中的遮蔽次数；遮蔽值不写入日志、不持久化。

### 证据语义

- `source_kind=documentation`：来自 vault 的 Markdown，是快照证据；
- `source_kind=runtime` + `is_live=true`：本次调用实时取得的运行状态；
- 两者不可互相替代；文档快照永不冒充实时结果。

## 1. `find_runbook` — 运行手册定位

按关键词定位单一相关 RUNBOOK。先对 `元模型/个人平台总览.md`（路由表）中的 `RUNBOOK/...` Wikilink 打分（链接命中 +100），再对 `RUNBOOK/` 目录全文检索，最后按路径合并去重、保留最高分。

| 参数 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `topic` | str | 1–200 字符 | 运维主题或问题 |
| `limit` | int | 1–10，默认 5 | 返回数量上限 |

返回 `RunbookResponse`：

| 字段 | 说明 |
| --- | --- |
| `topic` | 规范化后的查询词 |
| `total_matches` / `returned` | 去重后命中总数 / 本次返回数 |
| `items` | `SearchHit[]`：`path`（vault 相对路径）、`title`、`heading`、`line_start`、`score`、`snippet`、`document_type`、`document_status`、`knowledge_scope`、`source_kind=documentation` |
| `router_path` | 恒为 `元模型/个人平台总览.md` |

错误语义：

- 无结果：`items=[]`、`total_matches=0`；
- 重复：同一 RUNBOOK 同时被路由与全文命中时只出现一次，保留最高分；
- 断链：路由表中指向不存在文件的链接静默跳过，不影响其他结果；
- 循环：路由只解析 `元模型/个人平台总览.md` 一层，不递归，天然终止。

## 2. `search_notes` — 确定性检索

检索维度与评分权重（首个词 ×2，其余 ×1）：

| 维度 | 权重 | 说明 |
| --- | --- | --- |
| 标题（title） | 60 | H1 标题或 frontmatter `title` |
| 标题块（heading） | 50 | H1–H6 小节标题 |
| 路径（path） | 35 | vault 相对路径 |
| 链接（wikilink 目标） | 30 | `[[目标]]` 的目标名 |
| 标签（tags） | 25 | frontmatter YAML 列表形式 `tags:` |
| 其他 frontmatter（含 aliases） | 20 | 全部元数据值 |
| 正文 | 8×次数（封顶 5 次） | 小节正文全文 |

scope：`all`（全部）、`runbook`（仅 `RUNBOOK/`）、`operational`（RUNBOOK/运维笔记/总览 + `knowledge_scope` 含 operational）、`conceptual`（非 operational）。

| 参数 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `query` | str | 1–200 字符 | 字面量词或短语 |
| `scope` | 枚举 | 见上，默认 `all` | 检索范围 |
| `limit` | int | 1–20，默认 10 | 返回数量上限 |

返回 `SearchResponse`：`query`、`scope`、`total_matches`、`returned`、`items`（`SearchHit[]`，按分数降序、路径、行号排序）、`source_root`（vault 根路径）。

错误语义：

- 无结果：`total_matches=0`、`items=[]`；
- 重复：**同一文档的多个标题块会各自成为一条命中**（这是设计），`total_matches` 是 chunk 级计数；按标题块精确定位请用 `read_section(path, heading)`。

## 3. `read_section` — 读取单文件或标题小节

| 参数 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `path` | str | 1–260，vault 内相对 `.md` | 由搜索工具返回的路径 |
| `heading` | str? | ≤200 | 精确标题文本（忽略 `#` 前缀、大小写与首尾空白） |
| `max_chars` | int | 500–20000，默认 12000 | 返回内容长度上限 |

返回 `SectionResponse`：

| 字段 | 说明 |
| --- | --- |
| `path` / `title` | vault 相对路径 / 文档标题 |
| `heading` | 命中的小节标题（未指定则为 null，返回整篇） |
| `line_start` / `line_end` | 1 基、闭区间；未指定 heading 时覆盖整篇 |
| `content` | 遮蔽后的正文；超过 `max_chars` 时截断并以 `\n\n[TRUNCATED]` 结尾 |
| `truncated` / `redactions` | 是否截断 / 遮蔽次数 |
| `source_kind` | 恒为 `documentation` |

错误语义（均为输入错误 → tool error）：

- 空路径、绝对路径、非 `.md`、路径超长、`..` 逃逸、符号链接逃逸、位于排除目录、文件不存在、指定标题不存在。

容错：非 UTF-8 编码以替换符（U+FFFD）读入，不崩溃；异常 Markdown（无标题、`#` 无空格、孤立 `#` 等）按正文处理。

## 4. `read_action_board` — 当前行动看板（结构化）

无参数。读取 vault 中的 `个人/当前行动看板.md`，按 Obsidian Kanban 格式解析为结构化列。

返回 `ActionBoardResponse`：

| 字段 | 说明 |
| --- | --- |
| `path` / `title` | 恒为 `个人/当前行动看板.md` / 文档标题 |
| `columns` | `ActionBoardColumn[]`：H2+ 标题作为列名（H1 文档标题不是列），列顺序与文档一致；**空列保留** |
| `columns[].items` | `ActionBoardItem[]`：`text`（勾选项正文）、`status`（`open`/`done`，对应 `- [ ]`/`- [x]`）、`details`（缩进或换行的子项文本，剥离 `- `/`* ` 前缀） |
| `total_items` / `open_items` / `done_items` | 计数 |
| `updated` / `last_verified` | frontmatter 中的日期，缺省为 null |
| `redactions` / `source_kind` | 遮蔽次数 / 恒为 `documentation` |

错误语义：`个人/当前行动看板.md` 不存在时抛 `ValueError`（tool error）。

## 5. `query_runtime_status` — 实时运行状态

| 参数 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `scope` | 枚举 | `windows_services` / `local_docker` / `cloud` | 查询范围 |
| `query` | str | ≤100，默认空 | 大小写不敏感结果过滤（kind/name/state/summary） |
| `limit` | int | 1–100，默认 50 | 返回数量上限 |

返回 `RuntimeStatusResponse`：

| 字段 | 说明 |
| --- | --- |
| `scope` / `query` / `returned` / `items` | 范围 / 过滤词 / 返回数 / `RuntimeItem[]`（kind、name、state、summary） |
| `observed_at` | 本次取样的 ISO 时间 |
| `warnings` | 非致命失败说明（脚本缺失、命令失败、解析无效行），无敏感值 |
| `source_kind` / `is_live` | 恒为 `runtime` / `true` |

语义：

- 每次调用即时执行代码内固定的只读命令，**无缓存**，`observed_at` 即取样时刻；
- 失败返回 `warnings` 而不是错误，且**不回退**到旧文档冒充实时结果；
- 命令白名单：Windows 服务脚本、`docker ps`、云端 systemd/Docker 查询（经 `Invoke-RatioSsh.ps1` 包装），不接受任何 shell 参数。
