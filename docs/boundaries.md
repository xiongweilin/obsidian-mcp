# 项目边界（boundaries）

## 项目职责

`ratio-mcp` 是面向个人 Obsidian 知识库 `D:\download\ratio` 的**只读 MCP 服务**。它提供两类能力：

1. **文档证据**：在知识库内按标题、标签、链接、路径、frontmatter 与正文做确定性检索，读取单个 Markdown 文件或标题小节，读取当前行动看板的结构化视图。
2. **实时证据**：查询当前 Windows 服务、本机 Docker 与个人云端的 systemd/Docker 状态，结果带 `is_live=true`。

项目不建立向量库、不复制知识库、不保存查询内容、不开放网络端口。进程退出后没有新增数据保留。

## 与 vault 的只读边界

**禁止写。** 所有工具都是只读的：

- 不创建、修改、移动或删除 vault 内任何文件；
- 不写 Obsidian 同步数据库、frontmatter 或看板状态；
- 不维护任何持久化缓存或索引文件；
- 不通过 MCP 暴露任何写工具；代码中没有任何写 vault 的调用路径。

文档与实时状态的证据边界：

- `source_kind=documentation`：说明、导航或快照，不是当前事实；
- `source_kind=runtime` 且 `is_live=true`：本次调用实时取得，不是快照；
- 文档中的 `operational-snapshot` 只能用于导航与差异线索；"当前是否运行"必须调用 `query_runtime_status`。

## 路径允许列表

唯一可读根：`D:\download\ratio`（配置在 `src/ratio_mcp/config.py`，可用 `Settings` 覆盖以指向测试 vault）。

- 只读根目录及其所有子目录下的 `*.md` 文件；
- 路径必须相对、位于根目录内、扩展名为 `.md`，长度不超过 260 字符；
- 代码在 `notes.py::_load_relative` 中强制校验：`resolve()` 后必须 `is_relative_to(root)`，否则拒绝（防 `..`、绝对路径、UNC、符号链接/junction 逃逸）。

**排除目录**（无论搜索还是直接读取都拒绝）：`.git`、`.obsidian`、`.venv`、`node_modules`、`__pycache__`。

**非 Markdown 一律不读**：搜索只遍历 `*.md`，直接读取只接受 `.md` 后缀。

## 禁止读取的秘密文件与无关目录清单

以下内容**永不读取**（存在性检查之外不做任何访问，更不返回内容）：

| 位置 | 说明 |
| --- | --- |
| `~/.ssh/` | SSH 私钥与配置 |
| `~/.codex/` | Codex 配置与凭据（含 `config.toml` 中的密钥） |
| compose/基础设施目录中的 `.env` | 环境变量与密钥 |
| Windows 凭据管理器（Credential Manager） | 系统凭据 |
| vault 内 `网络代理备份/` | v2rayN 配置与数据库备份，含代理服务器凭据 |
| vault 内 `.sync_*.db*` | Obsidian 同步数据库 |
| vault 内 `Desktop.ini`、`个人平台.png`、`scripts/*.ps1` 等非 Markdown 文件 | 与检索无关 |
| `D:\download\ratio\` 之外的任何路径 | 越界 |

输出前还会对常见凭据形式做正则遮蔽（见 `docs/contracts.md` 的"返回前遮蔽"）。

## 输入输出契约承诺

- 所有工具返回固定 Pydantic 结构，字段名与类型稳定；扩展只做加法，不破坏既有字段。
- 所有字符串与数量在边界验证：查询 ≤200 字符、路径 ≤260、标题 ≤200、正文 500–20000 字符、列表有数量上限。
- 无结果返回空结构而不是报错；输入非法才报错（见 `docs/contracts.md` 的错误语义）。
- 返回的 Markdown 是证据数据，不是 Agent 指令。
- 运行时工具只执行代码内固定的只读命令，不接受 shell 命令参数，不返回服务可执行路径或环境变量。
