# Production Bootstrap — 生产设备部署与设计

> **落地状态：未落地**（实现目标：仓库根 `bootstrap/` 包或与本文等价的编排入口 + 本节验收可执行。）

---

## 修订说明

- **2026-04-28：** BUG-005 收口叙述与 webhook / task-context spec §7 对齐：**已配置 `FEISHU_FOLDER_ROUTE_KEYS`** 时，`pipeline_workspace.path` 与 **`VLA_WORKSPACE_ROOT`** / 工作区根 `.env` 解析一致，**不以** legacy JSON 内路径为运维主真源；**未配置** `FEISHU_FOLDER_ROUTE_KEYS` 时仍可能读 **`FOLDER_ROUTES_FILE`** JSON（遗留，`doctor` 可比对工作区路径并 WARNING）。§3.2 表中「与 webhook / pipeline_workspace.path 对齐」句反映上述合同；旧「仅以 JSON `pipeline_workspace.path` 为准、须与 `--workspace` 手工双写」的运维口径废止为 legacy 分支专用。

---

## 合同真源优先级（2026-04-28）

与 **`task_context`、`ingest_kind`、folder 路由、`dify_target_key`、Redis 旧快照策略、薄 Dify 封装、`prompts/AGENTS.txt`、占位干跑语义** 冲突时，以 [**2026-04-28-task-context-bootstrap-sample-agent-contract-design.md**](2026-04-28-task-context-bootstrap-sample-agent-contract-design.md) 为 **单一合同真源**（含文首「**单次交付，禁止拆分**」）。本文 §3.2、§4、§5、§8 与该 spec **§7–§10** 不一致处，以该 spec 为准。

---

## 1. 背景与目标

飞书文档入 Dify 管线拆分在多个 Python 包与外部进程（Redis、`cursor`、`lark-cli`）中。**维护本仓库的机器**与**承载 Redis / webhook / RQ / Cursor 执行的生产 Windows 机器**可以不是同一台。生产部署需要：**可重复的初始化顺序**、对系统级依赖的 **可验证自检**（以仓库各 `pyproject.toml`、源码 import/子进程与合同为准），以及把「**维护仓库根**（克隆根）」「**执行工作区目录**」「**运行合同** `.env`（工作区根）」三者的职责说清楚。**[ThirdParty.md](../../../ThirdParty.md)** 仅供上述自检的交叉核对（该文为人肉汇总，**可能有疏漏**）。

本规格定义 **`bootstrap`** 模块的职责边界、环境与交接假设、以及与其他设计文档的分工。**不替代**既有 `onboard`、`webhook`、`feishu_fetch`、`dify_upload` 的业务规格；仅在「生产设备上如何把已有实现接起来」一层收敛口径。

**路径约定（全文）：**

- **维护仓库根** `{CLONE_ROOT}`：`git clone` **或** 将本仓库 **拷贝到客户机任意目录** 后的根路径；**每台机器、每次部署不同**，规格与 README **不写死**具体盘符或目录名。
- **执行工作区根** `{WORKSPACE_ROOT}`：由 **客户或现场运维指定** 的绝对路径，经 **`materialize-workspace --workspace`** 传入，且与 **`VLA_WORKSPACE_ROOT`**、webhook **`pipeline_workspace.path`**（解析来源：`.env` 路由优先 / JSON 回退，见 [task-context-bootstrap spec §7.1](../specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md)）规范化后一致；须满足 **§3.2**，**非**本规格替客户选定具体文件夹名。

---

## 2. P0 环境约束（与实现必选一致）

| 约束 | 说明 |
|------|------|
| 操作系统 | **Windows**（部署文档与自检以 PowerShell 调用方式为第一公民）。 |
| Python | **不使用 venv**。采用**单机统一解释器**（推荐 **Python 3.12**）。**统一部署所选解释器版本须不低于各子包 `requires-python` 声明下限的最大值**；与本仓库当前各包合并后对齐全线部署时为 **≥3.12**。各子包以 **`pip install -e <克隆路径下的子目录>`** 安装到同一环境。版本冲突以实现阶段锁定的单次解释器校验为准，不在本规格写死补丁策略。 |
| 仓库来源 | 生产机可将本仓库 **`git clone` 或拷贝至本地任意目录**，以该 **维护仓库根目录** 作为相对路径锚点（`bootstrap`、编排脚本、运维手册均不得假设固定盘符路径）。 |
| 设备关系 | **维护仓机器 ≠ 生产机**仍成立：`bootstrap` **不得假设**单机完成「开发提交」与「7×24 服务」两步；须在交接清单中写明 **谁在何时** 维护 **维护仓库根** `.env`（种子）与 **工作区根** `.env`（运行合同）。 |

---

## 2.1 两份 `.env`、何时出现、谁读谁写（维护仓库 vs 执行工作区）

**职责分离（结论先行）：**

| 位置 | 角色 | 是否运行合同唯一真源 |
|------|------|----------------------|
| **维护仓库根** `{CLONE_ROOT}/.env`（及 **[`.env.example`](../../../.env.example)**） | **维护侧**：本仓库/克隆机上的台账、密钥草稿、与 onboard 交互时的**输入或中间落点**；便于 `git pull` 后与本地对照。**不是**「Cursor / webhook / RQ 执行任务」时的运行合同真源。 | **否** |
| **执行工作区根** `{WORKSPACE_ROOT}/.env` | **运行合同唯一真源**：与 `materialize-workspace --workspace` 目录一致、与 `cursor agent` cwd 同层；`VLA_WORKSPACE_ROOT` 指向工作区时，进程加载的须是**这一份**。 | **是** |

**`.env` 怎么来、什么时候有：**

1. **维护仓库落到本机之后**（`git clone` 或拷贝）：推荐在 **`{CLONE_ROOT}`** 准备 **`.env`**（由 `.env.example` 复制并填键）**或**至少保留可读 **`.env.example`**，供首次物化使用；git **不追踪** `{CLONE_ROOT}/.env`。
2. **首次 `materialize-workspace`**：以 **`{CLONE_ROOT}/.env` 整份复制**到 `{WORKSPACE_ROOT}/.env`（UTF-8）。若工作区尚无 `.env` 且克隆根**没有** `.env` 仅有模板，实现允许：复制 `.env.example` 到工作区根，或使用 **`--seed-env`** 指定任意种子文件（见 implementation plan）。**自本步完成起，运行相关密钥与合同以工作区根 `.env` 为准维护。**
3. **首次 `install-packages`**：**一般不依赖** `.env`（仅以克隆路径为准）。
4. **`doctor --workspace`**：读 **`{WORKSPACE_ROOT}/.env`** 做 `REDIS_URL` 等依赖合同的检查；**无该文件**则须明确失败或提示先物化，**不得**把「仅有维护仓库根 `.env`」当成运行侧已就绪。
5. **初始化中的读写分工**：需读密钥/运行合同时，**以已存在的工作区根 `.env` 为准**。交互步骤（如 **`feishu-onboard`**）产生的新键、路由映射等 **须回写到 `{WORKSPACE_ROOT}/.env`**。当前 onboard 若仍写入 `{CLONE_ROOT}/.env`，运维须 **同步到工作区**（再跑 materialize、手工合并或后续专项改 onboard 写入路径），否则运行侧仍读旧工作区文件。
6. **维护仓库 `.env` 变更后**：若希望运行侧与维护侧键值对齐，使用 **`materialize-workspace --sync-env-from-clone`**（从 `{CLONE_ROOT}/.env` **覆盖**工作区 `.env`，见 implementation plan）**或** **手工合并** **或** **只改工作区 `.env`** 并以工作区为台账。**默认**再次 `materialize-workspace`（无该标志）**不覆盖**已有工作区 `.env`，避免无意冲掉生产已填密钥。

### 推荐流水线顺序（可写入 bootstrap README）

**与人验收唯一路径（产品交互）：** 取得维护仓库 → `Set-Location` 克隆根 → **`pip install -e …/bootstrap`** → **`bootstrap interactive-setup`**（终端内连续键入克隆根/工作区根等）→ 由该命令内部完成下列 **install → materialize → 提示编辑工作区 `.env` → doctor**；其后 **（按需）feishu-onboard**、**设置 `VLA_WORKSPACE_ROOT`**、起 Redis/webhook/RQ 仍由运维按 README 执行。

**等价分步（逻辑顺序，供实现与排障；分立 CLI 不单独作为签字路径）：**

```text
取得维护仓库（克隆根 = {CLONE_ROOT}，路径由现场决定）
  → （推荐）复制 .env.example 为 {CLONE_ROOT}/.env 并按阶段填键（维护侧种子）
  → pip install -e …（可无 .env）
  → materialize-workspace（{CLONE_ROOT}/.env 或 .env.example/--seed-env → {WORKSPACE_ROOT}/.env + §3.4 树）
  → 编辑 {WORKSPACE_ROOT}/.env 补全密钥/合同（运行真源）
  → doctor --workspace <同上 WORKSPACE>
  → （按需）feishu-onboard；产出须落到或同步到 {WORKSPACE_ROOT}/.env（§4.2）
  → 设置 VLA_WORKSPACE_ROOT = {WORKSPACE_ROOT}，启动 Redis / webhook / RQ …
```

**要点：** bootstrap **不**在维护仓库「发明」长期运行真源；**首次**从维护仓库种子**生成**工作区根 `.env` 后，**运行链路只认工作区根这一份**。

---

## 3. 术语与路径

### 3.1 术语表

| 术语 | 含义 |
|------|------|
| **克隆根**（维护仓库根） | 生产机上 **`git clone` 或拷贝**后的仓库根目录，含 `webhook/`、`onboard/`、`prompts/` 等。其下 **`.env`** 为 **维护侧种子/台账**（见 §2.1），**不是**管线运行时的合同唯一真源。 |
| **执行工作区**（亦即下文 **生产工作区**） | **Cursor Agent 执行任务时**所使用的目录；**必须与克隆根物理分离**（不同文件夹）。其上须物化出自 `prompts/` 的 `AGENTS.md` 与 `rules/**`（与任务目录约定、`feishu_fetch`/`doc` 链路一致）；工作区粒度说明可参考 [2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md](2026-04-26-feishu-fetch-lark-cli-workspace-init-design.md)**（可读，非本规格门禁）**。 |
| **运行合同 `.env` 真源** | **仅** **`{WORKSPACE_ROOT}/.env`**（不入库）。由 **`materialize-workspace`** 从维护仓库种子生成首份，其后 **`doctor`、webhook（`VLA_WORKSPACE_ROOT` 指向工作区时）** 等以**该文件**为加载目标。维护仓库根 `.env` 与 `.cursor/rules/env.mdc` 中「本仓库根 `.env`」指 **维护仓开发与排障**语境；**生产设备运行**以工作区根 `.env` 为准（§2.1）。dev 仅设 `VLA_WORKSPACE_ROOT` 时可仍读克隆根 `.env` 的行为以 webhook 实现为准，**不**改变「运行真源 = 工作区根」的交接语义。 |

### 3.2 生产工作区路径与显示名（硬性约定）

为减少 Windows 下 **`cursor`/子进程/JSON/`task_context`** 的路径编码歧义：**执行工作区的根路径**及其**盘上目录名**，须同时满足下列约束。**`bootstrap` 与运维文档中的示例、检查表默认值须遵守本节；** `--workspace`/`materialize-workspace` 目标若不符，**建议直接拒绝并给出可读错误**，而非静默继续。

| 维度 | 规则 |
|------|------|
| 字符集 | 路径字符串中每一段 **仅允许 ASCII**：英文字母、数字。**不允许**使用中文字符、Emoji、全角符号作为路径分量。 |
| 命名风格 | **仅建议** `kebab-case` 或小写 + 连字符，例如段名 `feishu-cursor-workspace`；避免出现易与选项混淆的 **`=`、`&`、`|`、未配对括号**。 |
| 标点 | **不推荐**空格。**禁止**在目录名中包含英文逗号、单引号、双引号、中文顿号、百分号等易被 shell、`subprocess`、JSON 包装误读的符号。**盘符**遵循 Windows 绝对路径约定（如 **`X:\...`**），**不**在本文写死具体盘符。**业务分层**仅通过目录层级与允许的 ASCII 段名区分。 |
| `materialize`/文档展示 | README、`doctor`/`materialize` 回显的路径一律 **英文字面**、盘上 **ASCII**，与 §3.2 段名规则一致。**勿**凭空写 **`WORKSPACE`**、**`CURSOR_WORKSPACE_ROOT`** 等为 webhook 的官方键——**现行 `webhook` 不以这些 env 传工作区根**（实现见 **`ExecutorSettings`、`load_routing_config`**）。 |
| 与 webhook / **`pipeline_workspace.path`** 对齐 | **合同**见 [task-context-bootstrap spec §7.1–§7.3](../specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md)：**配置了 `FEISHU_FOLDER_ROUTE_KEYS`** 时路由与 **`pipeline_workspace.path`** 以 **工作区 `.env`** 解析为准；**未配置**时 **回退**读 **`FOLDER_ROUTES_FILE` JSON**（遗留路径，警告）。**必须与** **`materialize-workspace --workspace`** 之 **`{WORKSPACE_ROOT}`** 规范化绝对路径一致。**`doctor`**：在 **JSON 回退模式且 JSON 可读时** 将 JSON 中 **`pipeline_workspace.path`** 与 **`Path(--workspace).resolve()`** 比对，**不一致须 WARNING**（stderr），P0 下**不**因该项单独失败退出；**`.env` 路由模式**下行为见该 spec §9。 |

### 3.3 工作区根路径形状（与 §3.2 合取）

**物理位置**：`{WORKSPACE_ROOT}` **不得**位于 `{CLONE_ROOT}` 之下（与仓库目录 **兄弟**、其它父路径或 **独立磁盘** 均可）。**具体盘符、父目录、叶目录名均由客户/运维选定**，须满足 §3.2（ASCII 段名、无空格等）；本文 **不**给出可照抄的示例绝对路径。

**形状说明（示意，非字面路径）：**

```text
{某盘或挂载点}\{可选父前缀}\{工作区根目录名}
```

- `{某盘或挂载点}\{可选父前缀}\`：运维统一管线相关目录时的前缀，**任选**，仍须 ASCII、无空格。  
- `{工作区根目录名}`：客户指定的 **执行工作区** 根文件夹名（如 `kebab-case`）；与 **`{CLONE_ROOT}`** **并排**（非嵌套）可避免任务文件误入仓库 `.git` 或与源码混放。

**禁止**：把工作区设为克隆根或其仓库树内子目录——若管理上必须共父，交接清单写明 **克隆根与工作区互不嵌套**（与 `bootstrap` 路径校验一致）。以下 **§3.4** 的树均相对 **`{WORKSPACE_ROOT}`** 展开。

---

### 3.4 生产工作区目录树（硬性约定）

本节约定 **管线 Cursor 执行工作区**（= `pipeline_workspace`，即 webhook 写入任务包、cwd=`cursor agent` 的那一层）之下的**必选相对布局**。**`bootstrap materialize-workspace`** 至少须创建本节中「初始化阶段」条目；「运行时写入」条目由 webhook/Agent 遵从同一树，不得在实现中静默改名。

**命名说明**：口语「**tasks / 任务目录**」与本仓既有实现中的 **`.cursor_task/`** 为同一语义；**盘上目录名固定为 `.cursor_task`**（前缀点号、`cursor_task`），与 `.cursor/rules/workplacestructure.mdc`、`webhook` 写入逻辑一致。**若未来将目录改为无点号的 `tasks/`，须同步改 webhook、与本节并重发版本——本规格默认值仍以 `.cursor_task` 为准。**

目录名一律 **ASCII**（含 §3.2）。

#### 约定的完整结构

```text
{WORKSPACE_ROOT}/
├── .env                            # 运行合同唯一真源（首份由 materialize 从维护仓库种子生成；见 §2.1）
├── tools/                          # 工具集根（初始化阶段由 bootstrap 创建布局）
│   ├── dify_upload/                # 与各工具模块同名；内容为克隆根的联接/占位策略见下
│   └── feishu_fetch/
├── rules/                          # 规则：*.mdc（由 prompts/rules/** 物化，不手写第二套正文）
│   └── …                           # 例：qa/…/*.mdc，以 prompts 为准
├── AGENTS.md                       # 由 prompts/AGENTS.txt 物化（仓库维护 txt，工作区为 md）
└── .cursor_task/                 # 单次任务根（webhook 每 run 写入；勿与「tasks」混为不同路径）
    └── {run_id}/
        ├── task_context.json
        ├── task_prompt.md
        └── outputs/                # 目录名 outputs（复数）；子路径由各工具写入约定
```

#### 各层职责

| 路径（相对工作区根） | 阶段 | 说明 |
|----------------------|------|------|
| **`.env`** | 初始化 + 运行 | **工作区根**下须存在 **`.env` 文件**——**运行合同唯一真源**（§2.1）。**首份**由 **`bootstrap materialize-workspace`** 从 **`{CLONE_ROOT}/.env`**（或 `.env.example` / `--seed-env`）**整份复制**（UTF-8）；其后运维 **以工作区根 `.env` 为台账** 填密钥、接 onboard 回写；**不得**将工作区 `.env` 提交进 git。维护仓库根 `.env` 仅作可选种子/备份；若采用 **硬链接/联接** 指向维护侧，须在 implementation plan 写明且 `doctor` 能验证。 |
| **`tools/`** | 初始化 | **工具集根目录**，其下**一级子目录名**须与克隆根中**可被本管线调用的 Python 包目录名**对齐；**至少**包含 **`dify_upload/`**、**`feishu_fetch/`**。**内容策略（二选一，实现 plan 里写死一种并验收）**：(A) **目录联接（Windows junction）** 指向克隆根下同名的 `dify_upload/`、`feishu_fetch/` 源码树，保证工作区内路径稳定、不双份维护；(B) **空目录 + README** 仅作约定占位，实际解释器仍从全局 `pip install -e <克隆根>` 导入——**不得**再引入 venv。**不作为** `tools/` 子目录的：`lark-cli`（全局 PATH）、通常也不包含 **`webhook/`**、**`onboard/`**（服务端/入轨在克隆根执行，除非产品明确要求在工作区呈现文档入口）。 |
| **`rules/**` | 初始化 | 与 `prompts/rules/**` 一致结构的 **`.mdc` 规则文件**；路径与 `task_context.json` 里 `qa_rule_file` 引用的工作区相对路径一致。 |
| **`AGENTS.md`** | 初始化 | 源文件在仓库为 **`prompts/AGENTS.txt`**；物化到工作区时 **目标文件名为 `AGENTS.md`**，内容同步。 |
| **`.cursor_task/{run_id}/`** | 运行时 | 由 **`webhook` `write_task_bundle`**（及同目录约定）创建；**每次任务**独立 `run_id` 子目录。与仓库 **`.cursor_task/{run_id}/`** 规则一致：须含 **`task_context.json`**、**`task_prompt.md`**、**`outputs/`**（**不是** `output` 单数），子工具产物（如 `outputs/feishu_fetch/`）遵循既有各模块文档。 |

#### 校验

- **`doctor`** / **`materialize-workspace`**：对工作区根执行 **存在性 + §3.2 路径合法** 校验；**须**校验工作区根 **`.env` 存在**（或 materialize 已写入）；可选比对与维护仓库种子的哈希/时间戳策略由 plan 定。可选校验 **`tools/dify_upload`**、**`tools/feishu_fetch`** 目标为 junction 且目标存在（若采用策略 A）。  
- **webhook / 任务代码**：创建 **`.cursor_task`** 时不得改为其他文件夹名，除非全仓变更与本节同步。

---

## 4. 与原模块文档及实现债的关系（不强制引用其它规格）

与 **onboard、webhook、root-env、`feishu_fetch`** 等相关的历史 **design spec**、[ThirdParty.md](../../../ThirdParty.md) 可作**推荐阅读**；**ThirdParty 非权威清单**（见该文首免责），**bootstrap `doctor` 的必检项**须来自 **对 `**/pyproject.toml`、关键 `import`、PATH 二进制约定** 的扫描或等价审计，再与 ThirdParty **对账**；发现缺失或错误应 **以源码与本规格为准** 并 **回写** ThirdParty 或本规格。

**已知与本主题强相关的仓库债（以 `BugList.md` 为准，关闭后须回写本节或删除表述）：**

| ID | 摘要 | 对接线的影响 |
|----|------|----------------|
| [BUG-004](../../../BugList.md) | `feishu-onboard` 与 webhook 对同一 **route** 对 `qa_rule_file`/`dataset_id` 等存在 **双重登记**；若运行时仍 **以 JSON 侧为生效源**，会与 **工作区根** `.env` **脱节**。 | 运维只改一侧会误判。**bootstrap/`doctor`/检查表不得暗示**「改过工作区 `.env` 即等价于 webhook 已用上新值」，须明示以 **`webhook` 解析路径**为准或待 BUG 修复后收敛。 |
| [BUG-005](../../../BugList.md) | 历史：仅 JSON 为路由源时易与 **工作区根 `.env` 运行合同**在「路由解析」层双写。 | **收口合同**见 [task-context-bootstrap spec §7](../specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md)（`.env` 优先、JSON 回退）；生产首启须能说明当前进程 **`load_routing_config` 实际分支**（以代码为准）；**工作区物理路径**与 **`--workspace` / `pipeline_workspace.path`** 对齐；**关单条件**以 **`BugList.md` + 实现** 为准，`doctor` 行为见该 spec §9。 |

**本规格承诺：** `bootstrap` 负责 **步骤可执行、自检与文档一致**；**不负责** 替代各业务模块关闭上述缺陷。BUG 修复并更新 `BugList` 后，应同步修订本节的「已知债」表与 `doctor` 行为。

### 4.2 `bootstrap` 不得将 `feishu-onboard` 简单复用为「唯一入轨黑箱」

**`feishu-onboard`（onboard）** 当前存在 **已知缺陷**（如 **BUG-004** 及关联 **BUG-005**）与 **`NiceToHave.md`** 等待优化项；与 webhook、**工作区根** `.env` 运行真源在**实现层**的完全对齐**尚未**由 onboard 单独保证。

因此 **本轮 `bootstrap`**：

- **不得**将总体设计退化为「安装依赖 → 调用 `feishu-onboard` → 收工」；**不得**假设跑通 onboard 即等于生产侧 **folder 路由、任务注入、webhook 读源** 已与设计合同一致。
- **须**在检查表与 `doctor` 中保留 **与 onboard 正交的** 步骤与提示：例如 **materialize-workspace（§3.4）**、**按代码核验 webhook 路由数据源**、**维护仓库种子与工作区根 `.env` 同步**、以及 **§4** 表格中的债项说明。
- **允许**文档/脚本中仍将 **「人工或交互式运行 `feishu-onboard`」** 列为**创夹、subscribe、写映射、做 `lark-cli` init** 的一环；若写入 **维护仓库根** `.env`，必须 **显式**注明：**运行真源为工作区根 `.env`，须同步或回写到 `{WORKSPACE_ROOT}/.env`**。该步 **不**消除 §4 所列债；运维须按 **BugList / 源码** 做补充核对或待专项修复后再简化流程。

**实现后果**：`bootstrap` 包以 **自有子命令**（`doctor` / `install-packages` / `materialize-workspace` 等）为主；**不**将 onboard 的 Python API **唯一**当作 bootstrap 内部实现（避免把 onboard 缺陷 **隐式**吞进 bootstrap 的「成功」语义）。若将来仅包装 CLI，也须在返回码与 stdout 中 **透传/标注** onboard 已知限制，而不是静默视为完成。

---

## 5. `bootstrap` 范围与非目标

### 5.1 范围内

1. **`doctor`**：**以代码与合同为源**（各子包 `pyproject.toml`、`feishu_fetch` 等对 `markitdown` 等运行时 import、PATH 上的 `cursor`/`lark-cli`、**工作区根** `.env` 合同），**[ThirdParty.md](../../../ThirdParty.md) 仅作交叉参考**；校验（至少）如下；**`{WORKSPACE_ROOT}/.env` 是否存在、以及如何分档自检**见 **§2.1**。具体项包括但不限于：
   - 当前 Python 版本是否满足统一部署策略；
   - `cursor`、`lark-cli` 是否可通过 **PATH** 解析；
   - **`{WORKSPACE_ROOT}/.env` 须存在**（与 `--workspace` 一致）；否则 **非零退出**，提示先 `materialize-workspace` 或 `--seed-env`。
   - 若工作区 `.env` 含 **`REDIS_URL`**：Redis 是否可 **连通**（失败则 **非零退出**）；**无该键**则跳过 Redis 项并明示（与 §2.1 弱化分档一致）。
   - 克隆根下各可编辑安装包是否已与「预期安装方式」一致（实现可采用「尝试 import」或等价轻量校验，细则在 implementation plan）；
   - **`markitdown`**：以 **`feishu_fetch` 源码**（如 `MARKITDOWN_SUFFIXES`、`import markitdown` 路径）为据，**生产 `doctor` 强制可 import**；**非**从 ThirdParty 照抄「建议」——ThirdParty 若仍写「建议」属历史表述，**本条与实现对齐源码**。未安装则 **`doctor` 非零退出**并给出可复制的 **`pip install markitdown`**（实现 plan 可捆绑进「装齐 runtime」一步）。
   - 传入或配置中的 **执行工作区根路径** 是否符合 §3.2（含字符集），否则 **非零退出或明确告警**。
   - **工作区路径 vs webhook**：**能**从 JSON 回退路径读取 **`pipeline_workspace.path`** 时，与 **`Path(--workspace).resolve()`** 比对，**不一致须 WARNING**（§3.2）；**`.env` 路由模式**下 `doctor` 检查以 [task-context spec §9](../specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md) 为准。**无**单独的 `CURSOR_WORKSPACE_ROOT`/`WORKSPACE` env 门禁键名。路由与 BUG-005 收口以 **task-context spec §7** + 实现为准。
2. **`install-packages`（命名可调整）**：在**同一解释器**下对 `webhook`、`onboard`、`dify_upload`、`feishu_fetch`**仅执行约定好的 `pip install -e`**，失败则非零退出（**目的**：可 import/可调用 CLI；**不**表示已信任 onboard **行为**无缺，见 **§4.2**）。
3. **`materialize-workspace`（P0）**：给定**执行工作区根路径**与 **克隆根路径**。**硬前提**：须能生成工作区根 **`.env`**——优先从 **`{CLONE_ROOT}/.env` 整份复制**；若克隆根无 `.env`，允许 **`.env.example` → 工作区** 或 **`--seed-env`**（见 **§2.1**、implementation plan）。在此前提下在工作区落下 **§3.4** 初始化树：**`tools/`**（及约定的子目录/联接策略）、**`prompts/AGENTS.txt` → `AGENTS.md`**、**`prompts/rules/**` → `rules/**`**；**不创建** `.cursor_task/{run_id}/`（由 webhook 运行时创建）。规则正文**不手写第二套**。
4. **编排说明（代码或文档必选其一，推荐代码打头 + README）**：固定顺序的**生产首启检查表**须与 **§2.1** 推荐流水线一致；**与人验收签字**须以 **`bootstrap interactive-setup`** 为**唯一交互入口**（内部编排下列分步，不得仅交付分立子命令而无该入口）。例如：  
   **（推荐）`.env.example` → `{CLONE_ROOT}/.env`（维护侧种子）** → **各包 install** → **`materialize-workspace`**（种子 → **`{WORKSPACE_ROOT}/.env`** 及 §3.4）→ **编辑 `{WORKSPACE_ROOT}/.env` 填运行密钥** → **`doctor --workspace`** → **（按需）[`feishu-onboard`](../../../onboard/README.md)**（产出 **同步到工作区根 `.env`**）→ **设置 `VLA_WORKSPACE_ROOT`** → **启动 Redis（若尚未）** → **启动 webhook/RQ**。  
   其中 **onboard 一步不得单独构成「布线完成」**（§4、**§4.2**）：**Webhook 不写文件夹、不在运行时创建映射台账**，且 **文件夹路由真源与双重登记债**仍以 **源码与 BugList** 为准。**`materialize-workspace`** 与 **`doctor`** 中与 §3.4/§4 相关的检查 **独立于** onboard 是否自认成功。**文件夹路由与任务的 `dataset_id`/`qa_rule_file` 等运行时以何为真源：** 必须以当前 **`webhook` 实现对 `resolve_folder_route`/`load_routing_config` 的数据源为准**（见 §4、BUG-004/BUG-005）；在未关闭相关缺陷前，`bootstrap`/检查表 **不得暗示**「仅改工作区 `.env` 或仅跑通 onboard 即等价于 JSON 侧已更新」。
5. **代码位置**：与前期共识一致——**与本主题相关的编排与自检代码落在仓库根 `bootstrap/`**（Python 包或可安装模块），避免散落在多处入口脚本且无版本对齐。

### 5.2 非目标（本轮不做或显式延后）

- 不引入 **venv**/虚拟环境作为主要机制。
- 不把 **`bootstrap`** 并入 webhook HTTP 路径或队列任务。
- **不自动化**运维方未书面同意的密钥生成、网络穿透、证书申请；与本仓库其它规格中「Cloudflare 临时隧道」等实验性文档互不强制绑定。
- 不在首版强求 **NSSM / Windows Service / 计划任务** 的自动生成；可提供**可复制**的示例命令与退出码语义，托管方式由运维选定。
- **不**将 **`feishu-onboard` 包**在 **行为语义**上当作无缺陷依赖（见 **§4.2**）；**不**用「仅 subprocess 调 onboard」替代 **materialize / doctor / 与 webhook 真源对齐** 的自有逻辑。

---

## 6. 人机分工（生产路径）

| 职责 | 建议承担方 |
|------|-------------|
| 克隆指定 tag/commit、`pip install -e`、`bootstrap materialize-workspace`、`bootstrap doctor --workspace` | 运维或自动化（CI 可只跑到 doctor/install）。 |
| 填写 **`{WORKSPACE_ROOT}/.env`** 中的密钥、`FEISHU_*`、`DIFY_*`、Redis 等与既有合同一致的键（运行真源）；可选维护 **`{CLONE_ROOT}/.env`** 作种子 | 人（或密钥管控系统注入），**不落 git**。 |
| 运行 **`feishu-onboard`** 完成夹级 subscribe、映射写入、`lark-cli config init`；**映射须落到或同步到工作区根 `.env`** | 人或在「生产机已成功 clone + 工作区已物化」条件下的交互/脚本。 |
| 长期运行 webhook、RQ worker、Redis（**`VLA_WORKSPACE_ROOT` = `{WORKSPACE_ROOT}`**） | 运维按 Windows 环境托管。 |

两台机器场景中：**工作区根 `.env`** 应明确为「运行侧主副本」如何分发（仅一台持有或通过安全通道同步）；本规格要求 **运行时进程加载的工作区 `.env` 与 `materialize --workspace` / `pipeline_workspace.path` 一致**，不强制具体同步工具。

---

## 7. 验收标准（本规格可结案条件）

1. 在**干净的 Windows + Python 3.12（无 venv）**环境中，**与人验收签字**须以 **`bootstrap interactive-setup`** 为**唯一引导路径**（`pip install -e` 克隆根下 `bootstrap` 后执行）：交互输入参数，由该子命令编排 **install → materialize → 编辑工作区 `.env` → `doctor`**，直至 **可解释的成功或非零退出**。`bootstrap --help` 须列出该子命令；**`doctor` / `install-packages` / `materialize-workspace` 分立调用**仅用于 CI、自动化与排障，**不**单独构成与人验收对等的并列入口（implementation plan Task 13）。
2. `doctor` 对 **经实现与仓库扫描确认的**硬性外部依赖有覆盖（含 PATH 二进制、Redis、`cursor` 等，**以源码/合同为准**，与 ThirdParty **对账但不盲从**），并对 **`markitdown`** 按 §5.1 **强制 import**，缺失则失败。
3. 存在可执行的路径：`materialize-workspace` 生成 **§3.4** 所列初始化产物（含工作区根 **`.env`**、`AGENTS.md`、`rules/**`、`tools/` 约定），与既定 `prompts/` 模板一致且无第二套分叉规则正文。
4. 编排顺序与 §5.1 第 4 点一致；「与 onboard/webhook 文档表面文字零冲突」不作为硬门禁。**若 BUG-004/BUG-005 仍存在**，以本节 §4、`BugList.md` 与 **`webhook` 源码读取路径** 为准校对 `README`/检查表措辞，避免因旧文档或未合并实现产生 **「仅改工作区 `.env` 即等于 JSON 侧已更新」误判**。
5. 维护仓与生产机**不同机**时的交接项在 **一页清单**（可放在 `bootstrap/README.md` 或与本规格互链）中能勾完。
6. **`doctor`**：**在 JSON 回退模式且 JSON 可读时**，将 **`FOLDER_ROUTES_FILE` → `pipeline_workspace.path`** 与 **`--workspace` 规范化路径** 比对；**不一致须 WARNING**（§3.2）；**`.env` 路由模式**见 [task-context spec §9](../specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md)。P0 **不**要求因此单独非零退出。

---

## 8. 开放问题（转 implementation plan）

### 已澄清

- **`materialize-workspace` 与「现有脚本」关系（2026-04-28）**  
  **结论**：本仓**当前无**与 §3.4 整树物化**等价**的已落地独立脚本（无整块重合实现）。**`bootstrap materialize-workspace` 作为唯一正式入口**实现 §3.4；**不与** `feishu-onboard` 合并为同一 CLI（分界见 **§4.2**）。若日后其它位置出现重复拷贝 `prompts/` 的逻辑，再在实现中抽公共代码或删重复，本条不阻挡先落地 `bootstrap`。

- **`doctor` × `markitdown`（2026-04-28）**  
  **结论**：**自检时强制要求已安装**。`doctor` **必须**验证当前 Python 环境可加载 **`markitdown`**（与 **`feishu_fetch` 源码** 中 MarkItDown 路径一致），**未安装 → 非零退出**，输出含 **可复制的 `pip install markitdown`** 及 **可选**指向 ThirdParty `feishu_fetch` 节 / 本条。**不采用**「仅告警、`exit 0`」作为主路径。**与 ThirdParty 关系**：ThirdParty 可能仍写「建议」——**以源码 + 本条为准**；ThirdParty 非 `doctor` 清单真源。

- **工作区根 vs webhook：`materialize` 与谁家字符串对齐（2026-04-28；本条随 task-context spec 修订）**  
  **结论**：**不**以虚构的 **`WORKSPACE` / `CURSOR_WORKSPACE_ROOT`** 为 webhook 约定。执行工作区根须与 **`pipeline_workspace.path`**（来自 **`load_routing_config`**：**.env` 路由优先 / JSON 回退**，见 [task-context-bootstrap spec §7.1](../specs/2026-04-28-task-context-bootstrap-sample-agent-contract-design.md)）规范化后与 **`materialize-workspace --workspace`** **同一物理路径**。**`bootstrap doctor`**、交接文档与此对齐；JSON 回退模式下 JSON 与 `--workspace` 不一致时 **WARNING**。生产须设 **`VLA_WORKSPACE_ROOT` = `{WORKSPACE_ROOT}`**，使 **`ExecutorSettings` 读工作区根 `.env`**（implementation plan Task 12）。**BUG-005** 收口以 **`BugList.md` + task-context spec §7** + 实现为准。

---

## 9. 后续步骤

撰写 **implementation plan**（`docs/superpowers/plans/` 下日期命名），挂载：`bootstrap/pyproject.toml`、包布局、`doctor`/`install`/`materialize` 子命令、`pytest` 范围（纯函数与 mock 外向依赖），以及与 `webhook/操作手册.md` 的生产章节互链。

