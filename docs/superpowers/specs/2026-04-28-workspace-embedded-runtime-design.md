# 单机生产：工作区内嵌运行时代码

> **落地状态：未落地**（实现目标：`materialize-workspace` 或等价子命令物化本节树；`doctor` 可校验；运维可仅从工作区启动 webhook/RQ，不依赖 `{CLONE_ROOT}` 路径常驻。）

---

## 修订说明

- **2026-04-28：** 初稿。**单机 Windows**，工作区内 **目录拷贝** 物化 `webhook` 与 `tools` 同源树，运行期不依赖 `{CLONE_ROOT}` 常驻。
- **2026-04-28：** 删 **§3.3**（junction 与开发/生产并存）。本文只约定 **实目录拷贝**；联接克隆根 **不在**本规格内。
- **2026-04-28：** 新增 **§10**：**NTH-008 交付中** **implementation plan 须** 列任务以拆除 `bootstrap` 内 **tools junction** 相关代码、CLI 开关与单测，并回写 README / 验收脚本；**`2026-04-28-production-bootstrap-deployment-design.md` §3.4** **在交付批次中** 与本文对齐（见 **§9、§10.2**）。
- **2026-04-28：** **§4.2 / §7** 统归 **`NiceToHave.md` NTH-008**（内嵌 runtime + **§10** + `doctor` 后探活）。**增量升级 / 免全量 bootstrap** **不**入本文，见 **NTH-009**。**`prompts/AGENTS.txt`**、根 **`AGENTS.md`** 随 NTH-008 plan 落地后 **renew**（`plan-landed-renew-agents-rules.mdc`）。
- **2026-04-28：** 删原 **§5**「升级与同步」流程；**约定**每次发版 **完整重新 bootstrap**。**NTH-009** 登记远期增量需求。
- **2026-04-28：** 复审：**§2** 补与 **`production-bootstrap-deployment-design.md` §3.4** 的冲突口径；**§5** 列举式标点，避免引号歧义。
- **2026-04-28：** 去 **「主规格」** 称呼；只指 **具体文件名**，避免误读成仓库合同层级。
- **2026-04-28：** 评审修订：**§2** 部署介质表述改挂 **`production-bootstrap-deployment-design.md`**（去掉断链）；**§3.2** 拷贝排除原则；**§4.1** 生产 **`pip install -e`** 升格为 **须**；**§4.2** 共同要求 + **形态 A/B**；**§6** 「P0 建议项」→ **P0 门禁**；**§8** 补验收前置；**§7** 与 **§5** / NTH-009 边界写清。
- **2026-04-28：** 消歧：**§4.1** 工作区 **`pip install -e`** 路径均落 **`{WORKSPACE_ROOT}/…`**（**处数** 以 **修订说明** 最新条为准；**末条** 起为 **四处** 含 **`vla_env_contract`**）；**§4.2** 区分 **Windows 服务** 与 **非服务前台进程**，二者均须满足 **§4.1** 与同解释器；**§6** 门禁路径写全；**§8** 正式拆 **§8.1 / §8.2**；**§7** NTH-008 与 **§5** 关系写清。
- **2026-04-28：** **§2 / §9 / §10.2**：旧 **`production-bootstrap-deployment-design.md`** 与旧 **implementation plan** 的修订 **列为 NTH-008 预期交付**；**不要求**在单独文档阶段先行改稿。
- **2026-04-28：** **§3.2 / §6 / §9 / §10.4**：**NTH-008** implementation plan **须**正文承接 **物化拷贝排除·保留清单** 与 **`doctor` FAIL/WARN 分档**，**禁止**仅以「实现里再定」代写。
- **2026-04-28：** **方向一（拆依赖）**：**`feishu-onboard`** **不再**作为工作区物化内容；**`.env` 键名合同**迁至独立包 **`vla_env_contract`**（分发名 **`vla-env-contract`**，实现见 **`docs/superpowers/plans/2026-04-28-workspace-embedded-runtime-implementation-plan.md` Task 0**）。**§3.1** 树 **删** **`onboard/`**、**增** **`vla_env_contract/`**；**§4.1** 生产签字 **四处** **`pip install -e .`**（**先** **`vla_env_contract`** 再 **`runtime/webhook`** 等）；**`runtime/webhook`** 拷贝后 **须** 修正 **`pyproject.toml`** 内 path 依赖 **`file:../vla_env_contract` → `file:../../vla_env_contract`**（与 **该 plan 附录 A.1** 一致，避免 [BUG-007](../../BugList.md) 类错位）。

---

## 1. 背景与目标

### 1.1 问题

[`2026-04-28-production-bootstrap-deployment-design.md`](2026-04-28-production-bootstrap-deployment-design.md) **§3.4** 等早期工作区树约定中，曾出现 **`tools/*` 联接回 `{CLONE_ROOT}`**、**`webhook` 未落工作区**、运行期 **在克隆根启动** 等形态。结果是：**7×24 仍绑定「维护仓库克隆路径」**，与「**克隆仅作部署介质、可不在运行期保留**」不一致。**本文**以内嵌 **`runtime/webhook`、`vla_env_contract`、物理拷贝 `tools/*`**（§3–§4）为交付主线；**旧 junction 方案不作为**本节验收默认。

### 1.2 目标（本规格）

| 项 | 约定 |
|----|------|
| **拓扑** | **单机**：Redis、webhook、RQ worker、**`cursor agent`**、**`{WORKSPACE_ROOT}`** 同一台 **Windows** 设备；无分布式、无跨机共享工作区。 |
| **运行真源** | 与现有合同一致：**`{WORKSPACE_ROOT}/.env`**、**`VLA_WORKSPACE_ROOT`** 指向工作区根；与 [task-context-bootstrap spec §7](2026-04-28-task-context-bootstrap-sample-agent-contract-design.md) 不冲突（同 spec **§2** 字段表亦约束工作区根路径）。 |
| **内嵌 runtime** | 由 **bootstrap 物化**（或 **`materialize-workspace` 等价步骤**）将 **`webhook/`**、**`dify_upload/`**、**`feishu_fetch/`**、**`vla_env_contract/`**（**键名合同**，自 **`feishu_onboard.env_contract` 抽出**）的**源码树**以**物理拷贝**落入工作区约定路径。**`onboard/`**（CLI 入轨）**不**进 **`{WORKSPACE_ROOT}`**；运维 **仅在维护仓 / 克隆根** 使用 **`feishu-onboard`**。 |
| **克隆根职责** | **`{CLONE_ROOT}`** 仅用于：**单次**部署流程中取得源码、执行 **`install-packages` / `materialize-workspace`**（本文 **不**约定「在线升级」；新版本 **重新 bootstrap**，见 **§5**）；**不**要求运行期进程 cwd 或只读依赖必须解析到克隆根。 |

---

## 2. 与现有规格的关系

- **[`2026-04-28-production-bootstrap-deployment-design.md`](2026-04-28-production-bootstrap-deployment-design.md)**：**§2.1** 两份 `.env`、**§3.2** 路径门禁、**§3.4** 工作区树——**继续适用**。**双读冲突时：** 该文 **§3.4** 里 **`tools/`** junction / 空目录占位等，与本文 **实拷贝 + `runtime/webhook`**、**§10** 废 junction **不一致 → 以本文为内嵌 runtime 交付与验收门禁**。**该文 §3.4** 与本文对齐的修订 **纳入 NTH-008 落地交付**（与代码 / §10 **同批或紧随回写**），见 **§9、§10.2**；**当前阶段** **不**要求仓库内已先行改该文。除 **`tools/`、`runtime/`** 外，该 **§3.4** 其余句仍从该文。
- **Task-context / webhook 路由**：不改变字段与解析优先级；仅改变 **进程启动时代码与解释器所见的磁盘布局**。
- **部署介质 vs 长期运维**：**持久运维锚点**仍为 **`{WORKSPACE_ROOT}`**——与 [`2026-04-28-production-bootstrap-deployment-design.md`](2026-04-28-production-bootstrap-deployment-design.md) 文内「部署介质 vs 长期运维」及 **`{CLONE_ROOT}`** 角色表述一致（该文亦链到 **deployment-artifact-lifecycle** 专稿；专稿未入库前以该文为准）。**本文**不定义「保留克隆仅做增量同步」；发版 **重新 bootstrap** 时再用新 **`{CLONE_ROOT}`** 介质即可。

---

## 3. 工作区目录树（内嵌 runtime）

在 **[production bootstrap §3.4](2026-04-28-production-bootstrap-deployment-design.md)** 既有树基础上 **增加** **`runtime/webhook/`**，并将 **`tools/dify_upload`**、**`tools/feishu_fetch`** 定为 **实目录拷贝**。

### 3.1 完整结构（内嵌 runtime 启用时）

```text
{WORKSPACE_ROOT}/
├── .env
├── AGENTS.md
├── rules/
├── vla_env_contract/         # 自 {CLONE_ROOT}/vla_env_contract 递归拷贝；webhook/bootstrap 共用键名合同（vla-env-contract），非 feishu-onboard CLI
├── tools/
│   ├── dify_upload/          # 自 {CLONE_ROOT}/dify_upload 递归拷贝
│   └── feishu_fetch/         # 自 {CLONE_ROOT}/feishu_fetch 递归拷贝
├── runtime/
│   └── webhook/              # 自 {CLONE_ROOT}/webhook 递归拷贝（可安装包根，含 pyproject.toml；依赖 file:../../vla_env_contract，见 §3.2）
└── .cursor_task/
    └── {run_id}/
        └── …
```

### 3.2 路径与命名

- **§3.2（ASCII、无空格等）** 与 **`production-bootstrap-deployment-design.md` §3.2** 合取；目录段名 **`runtime`**、**`webhook`** 固定为本节字面。
- **拷贝范围**：以克隆根下 **`webhook/`**、**`dify_upload/`**、**`feishu_fetch/`**、**`vla_env_contract/`** 目录为源。**`onboard/`** **不**拷贝进 **`{WORKSPACE_ROOT}`**（与 **§1.2**、**修订说明** 方向一一致）。**`runtime/webhook`** 自 **`webhook/`** 落入 **`{WORKSPACE_ROOT}/runtime/webhook`** 后，**须** 将包内 **`pyproject.toml`** 所载 **`vla-env-contract @ file:../vla_env_contract`**（相对 **克隆根 **`webhook/`** 深度）**改写**为 **`file:../../vla_env_contract`**，使 **`pip install -e .`**（**`cwd`** = **`runtime/webhook`**）能解析 **`{WORKSPACE_ROOT}/vla_env_contract`**；**具体替换规则** 以 **NTH-008** implementation plan **附录 A.1** 为真源。**排除** 不必运行时的体积（如 **`__pycache__`**、**`.pytest_cache`**、**`.git`** 若误出现在子树）——**至少**保证 **`pip install -e .`** 与既有入口模块可解析。**禁止**在默认排除规则中删掉包内 **`pip`/MANIFEST/入口所依赖** 的非 `.py` 资源（配置、数据、stub 等）；遗漏 = 实现缺陷，**非**「规格未要求」。
- **Plan 承接（硬要求）：** **NTH-008** 在内嵌 runtime 上的 **物化拷贝排除/保留、`doctor` 分档、`import` 列表** **须** 以 **`docs/superpowers/plans/2026-04-28-workspace-embedded-runtime-implementation-plan.md`** 附录 **A** 为真源。**`2026-04-28-production-bootstrap-deployment-implementation-plan.md`** 中仍写 **junction** 与旧 **§3.4** 策略的段落 **须在 NTH-008 代码已合入后修订或废止**（见该 workspace implementation plan **Task 10**）；**不得**仅以「见代码默认」或无清单交叉引用代替可审计条目。

---

## 4. Python 安装与启动

### 4.1 可编辑安装

- **运行期**须以 **同一全局解释器**（无 venv，与 **`production-bootstrap-deployment-design.md` §2** P0 表一致）加载 **`webhook`**（及其依赖 **`vla_env_contract`**）、**`dify_upload`**、**`feishu_fetch`**。**`doctor` 所验解释器** 与 **§4.2 中实际承担 webhook / RQ worker 运行的 Python 解释器**（无论 **已注册 Windows 服务** 或 **前台/计划任务直接启动**）**须为同一安装**（同一 **`python.exe` 解析结果**），否则视为未达标。
- **须（生产签字路径）**：物化完成后，在工作区所在机对下列 **四处目录各执行一次** **`pip install -e .`**，且每次命令的 **`cwd`** **就是** 该次目标目录（避免 [BUG-007](../../BugList.md) 相对 `file:` 依赖错位）；**顺序** **须** 满足 **`vla_env_contract` 先于 `runtime/webhook`**（后者依赖前者）：**`{WORKSPACE_ROOT}/vla_env_contract`**、**`{WORKSPACE_ROOT}/runtime/webhook`**、**`{WORKSPACE_ROOT}/tools/dify_upload`**、**`{WORKSPACE_ROOT}/tools/feishu_fetch`**。**不得**仅以克隆根路径上的 **`pip install -e`** 代替上述四处工作区安装而宣称达标。**`feishu-onboard`** **不**列入工作区 **editable** 签字路径（**不**要求 **`{WORKSPACE_ROOT}/onboard`**）。
- **克隆根 `install-packages`** 仅可作 **首次装机 / 开发便利**（维护仓可仍装 **`onboard`** 等，**不**替代 **§4.1** 工作区四处安装）；**生产验收** 以 **§4.1** 四处 **`{WORKSPACE_ROOT}/…`** **`pip install -e .`** 与 **§6 / §8** 为准。

### 4.2 进程启动

**共同要求（与是否安装 Windows 服务无关）：** **webhook**、**RQ worker** 的运行进程 **须** 设 **`VLA_WORKSPACE_ROOT={WORKSPACE_ROOT}`**（规范化绝对路径）；**须** 使用 **§4.1** 同一解释器；**工作目录（cwd）与命令行入口** **须** 与 implementation plan / 操作手册中的 **唯一**受支持写法一致（**不得**同时文档化两种 cwd 或两种入口而不注明何者用于签字验收）。

**形态 A — 已注册为 Windows 服务（NSSM / WinSW 等）：** 除上述共同要求外，服务配置 **须** 写死以下字段语义（避免「程序 / 工作目录」多种解读）：
  - **Application**：**§4.1 所用同一 `python.exe` 的绝对路径**。
  - **Arguments**：与既有 **`webhook` / RQ worker** 启动方式一致的 **模块或脚本参数**（由 implementation plan / 操作手册给出 **唯一**受支持写法）。
  - **Start in（工作目录）**：**`{WORKSPACE_ROOT}`**（规范化绝对路径）。若某受支持写法 **必须** 以 **`{WORKSPACE_ROOT}/runtime/webhook`** 为 cwd，plan **须** **仅**保留该一种并 **与单测、§8 验收脚本一致**。
  - **环境变量**：在服务配置中 **显式** 设置 **`VLA_WORKSPACE_ROOT`**（值同共同要求）。

**形态 B — 未注册为服务**（例如交互调试、计划任务直接调用 **`python -m …`**）：**不**要求填写 NSSM/WinSW 三字段，但 **仍须** 满足本节 **共同要求**；**实际启动命令** 中的解释器路径、cwd、**`VLA_WORKSPACE_ROOT`** **须** 与 plan/手册中 **为形态 B 单独写明的唯一写法**一致（若仓库 **仅**支持形态 A，plan **须**写清「生产签字以形态 A 为准」，形态 B **不得**作为未文档化的灰色路径）。

- **服务安装脚本** 可由 bootstrap **生成**；**是否**在 `materialize` 末尾自动注册服务 **非** P0，由 **`NiceToHave.md` NTH-008** 的 implementation plan **分期**收录，与 **探活** 环节在 README 写清顺序。
- **`NiceToHave`：** 本条（**§3** 树与物化、**§4**、**§6 / §8 / §10**）与 **「`doctor` 之后探活」** 统归 **NTH-008** **同一** plan 与验收。**增量升级** 另见 **NTH-009**，**不**并入 NTH-008。

---

## 5. 版本迭代与本文范围

- **本文不**规定：「在线升级」；「增量同步 **`runtime/webhook`** / **`tools/*`** / **`vla_env_contract`**」；以及「**`prompts`** 与运行时代码分步调版本」。**每次**要上新版本介质时，运维 **完整重新执行** [production bootstrap design](2026-04-28-production-bootstrap-deployment-design.md) **§2.1** 推荐流水线（含 **`materialize-workspace`**、**§4.1** 四处 **`{WORKSPACE_ROOT}/…`** 下 **`pip install -e .`**、按 **§4.2** 起服务），等同 **重新 bootstrap**。
- **远期**若需 **少停机 / 免全量重跑物化** 的同步策略，见 **`NiceToHave.md` NTH-009**（**无** spec/plan 真源前 **不**实现）。

---

## 6. 校验（`doctor` / `materialize`）

**P0 门禁**（生产签字 **须** 通过；**语义**为硬门槛，**非**「可忽略的 WARN 集合」。**FAIL/WARN 分档、import 包名列表** **须**写在 **NTH-008** plan 正文，**最低标准**见 **§10.4**）：

- **`{WORKSPACE_ROOT}/vla_env_contract/pyproject.toml`**（或等价包根标记）存在；**`{WORKSPACE_ROOT}/runtime/webhook/pyproject.toml`**（或等价包根标记）存在；**`{WORKSPACE_ROOT}/tools/dify_upload`**、**`{WORKSPACE_ROOT}/tools/feishu_fetch`** 为目录且含预期包根。
- **`{WORKSPACE_ROOT}/tools/*`**（在本规格下即 **`dify_upload`**、**`feishu_fetch`** 两子树）、**`{WORKSPACE_ROOT}/runtime/webhook`** 与 **`{WORKSPACE_ROOT}/vla_env_contract`** 须为 **实目录树**；**不得**为指向 **`{CLONE_ROOT}`** 的目录联接/重解析点（**FAIL/WARN 分档** **须**见 **NTH-008** plan 正文，**最低要求** **§10.4**；**生产签字** 下本条 **须** **FAIL**，**不得**整项降为 WARN）。**`{WORKSPACE_ROOT}/onboard/`** **不应**作为物化结果出现；若 **plan** 将「目录存在」定为 **FAIL**（推荐），**`doctor`** **须**与之对齐。
- **import 路径**：使用 **§4.1 同一解释器**，从该解释器 **`import`** 与任务链相关的顶层包名（具体包名与现有 `doctor` 一致，**须**在 **NTH-008** plan 正文 **列全包名列表**），**须**验证解析出的包/模块文件系统路径落在 **`{WORKSPACE_ROOT}`** 前缀下（规范化后比较）；**若仍解析到 `{CLONE_ROOT}` 或工作区外 editable** → **未达标**（与 **§8.2** 判定同一标准）。
- **Plan 承接（硬要求）：** **NTH-008** implementation plan **须**给出 **`doctor` / `materialize` 校验** 的 **FAIL 与 WARN 分档表**（条件 × 退出语义 × 是否阻塞生产签字）。**生产签字路径**下：**§6** 本条各 bullet **不得**整体降级为「仅 WARN 可忽略」；**至少**下列情形 **须**为 **FAIL**（或与实现等价之硬退出）：**`{WORKSPACE_ROOT}/runtime/webhook`**、**`{WORKSPACE_ROOT}/vla_env_contract`** 或 **`{WORKSPACE_ROOT}/tools/*`** **为指向 `{CLONE_ROOT}` 的联接/重解析点**；**import 解析路径前缀不在 `{WORKSPACE_ROOT}`**（含仍指向克隆或工作区外 editable）；**缺本节所列包根标记**（如 **`pyproject.toml`** 或 plan 声明的等价物）。**WARN** 仅允许用于 **非阻塞**、**不**替代上述 FAIL 的辅助项（具体条目 **须**写在分档表内，**禁止**空表或「见代码」）。

---

## 7. 与 BugList / NiceToHave 的对接

| 编号 | 关系 |
|------|------|
| **BUG-007** | **`pip install -e .`** 的 **`cwd`** **必须** 分别为 **`{WORKSPACE_ROOT}/vla_env_contract`**、**`{WORKSPACE_ROOT}/runtime/webhook`**、**`{WORKSPACE_ROOT}/tools/dify_upload`**、**`{WORKSPACE_ROOT}/tools/feishu_fetch`**（**顺序** 与 **§4.1** 一致）；文档与脚本 **禁止** 在生产仅从克隆根对子包传绝对路径 **`-e`** 而跳过上述四处工作区安装。 |
| **NTH-008** | **探活** + 本条 **§3–§4、§6、§8、§10**（物化、废 junction）。implementation plan **须** 列 **§10** 与探活；**须**含 **§3.2 拷贝清单**、**§6 FAIL/WARN 分档表**、**§6 import 包名列表**（见 **§10.4**）。**不**在 NTH-008 内实现 **NTH-009** 所列「增量同步 / 免全量 bootstrap」；**但** **§5** 正文「每次全量 re-bootstrap」**仍须**遵守，**非**可选项。 |
| **NTH-009** | **仅**登记 **§5** 排除的 **增量同步 / 免全量 bootstrap** 需求；**有** spec/plan 后再实现，**不**阻塞 NTH-008。 |

**未**在本规格关闭其他 **BUG**；若未来 **`production-bootstrap-deployment-design.md` §3.4** 合并本节树，须同步该文 **文首落地状态** 与 **§3.4** 表。

---

## 8. 验收要点（摘要）

### 8.1 新机整条链路

克隆 → **`install-packages`（可选）** → **`materialize-workspace`（内嵌 runtime）** → 按 **§4.1** 对 **`{WORKSPACE_ROOT}/vla_env_contract`**、**`{WORKSPACE_ROOT}/runtime/webhook`**、**`{WORKSPACE_ROOT}/tools/dify_upload`**、**`{WORKSPACE_ROOT}/tools/feishu_fetch`** **各执行一次** **`pip install -e .`**（每次 **`cwd`** 为该目录）→ **`doctor --workspace`**（**§6** P0 门禁 **须**通过）→ **（人机首跑可到此为止；见下「探活分段」）** → 起 Redis → 按 **§4.2** 受支持写法起 webhook、RQ worker（形态 A 或 B **须**与 plan/手册一致）→ **`bootstrap probe`** **全量**（含对 **`GET {WEBHOOK_PROBE_BASE}/health`** 或 plan 约定之唯一 HTTP 探针，**须**在 webhook 已监听后执行；**不得**在进程未起时把 **连接拒绝** 当作 **§6** 已通过后的**唯一**验收结论）。

**探活分段（与 NTH-008 implementation plan 一致）：**

1. **`doctor` 之后、Redis/webhook/RQ worker 未起或未监听前**：允许仅运行 **`bootstrap probe`** **静态段**（目录/配置键/§6 已覆盖之 import／**可选**不依赖 webhook 进程的项；**CLI 形如 `--no-http` 或等价**，以 plan/README 命名为准）——用于 **`interactive-setup` 单次会话不打假失败**。
2. **生产签字或与 §8.2 同属「删除克隆依赖」语义链**：在 **Redis 与 webhook（及按需 RQ worker）已启动** 后运行 **`bootstrap probe`** **完整段**（**含 HTTP** **`/health`**；**`WEBHOOK_PROBE_BASE`** 或等价键见工作区 `.env` 示例 **`docs/superpowers/samples/pipeline-workspace-root.env.example`**）。

**RQ worker：** §8 **不**强求单独 **TCP/队列探针**（与 **Redis + webhook HTTP** 为不同维度）；若在 **NTH-008 plan** 中列为 **WARN 或跳过项**，须在 plan/README **明示**，避免「全量」一词被误解为包含 **worker 端到端 enqueue**。

### 8.2 删除 `{CLONE_ROOT}` 依赖性试验

**目的：** 验证运行期 **不**依赖克隆根路径常驻。

**前置（缺一不可）：** 已 **完整**完成 **§8.1**（含 **§4.1** 四处工作区 **`pip install -e .`** 与 **`doctor` P0 通过**）。**不得**以「仅在克隆根执行过 `-e`、工作区四处未按 §4.1 重装」作为本试验起点。

**步骤：** 在 **不影响已按 §4.1 写入的 editable 元数据**（即元数据已指向 **`{WORKSPACE_ROOT}`** 下路径）的前提下，**模拟删除或重命名 `{CLONE_ROOT}`**。

**通过：** 已启动的 webhook / RQ worker **仍能**处理任务（与 **§4.2** 所选形态一致）。

**未通过：** **editable**、**`.dist-info`**、**import 解析** 仍指向克隆路径或工作区外路径 — 与 **§6 import 路径** 门禁 **同一判定**。

---

## 9. 后续文档动作（非本文正文义务）

**范围：** 下列项为 **NTH-008 预期交付** 中的文档工作；**与实现同批次完成即可**。**撰写或评审本文时** **不**强制先行修改旧 plan / 旧 bootstrap spec（避免「文档先行、代码未动」的单独工单）。

- **Implementation plan**：在 **`2026-04-28-production-bootstrap-deployment-implementation-plan.md`** 扩写任务块，指向本节；**须覆盖 §10**；**须**按 **§3.2、§6** 与 **§10.4** 写入 **拷贝清单**、**FAIL/WARN 分档**、**import 包名列表**；挂钩 **`NiceToHave.md` NTH-008**（与探活 **同一** plan）。
- **文档合并（可选）**：落地后可将 [`2026-04-28-production-bootstrap-deployment-design.md`](2026-04-28-production-bootstrap-deployment-design.md) **§3.4** 工具策略与 **`runtime/webhook`** 并入该文正文，并在该文 **修订说明** 引用本节 **文件名**。

---

## 10. Implementation plan 必选：废除 junction 实现

本节为 **硬要求**：**NTH-008** 的 **implementation plan** 必须 **显式列任务并完成** 下列项，**不得**只改文档而保留「工作区 `tools/*` 联接 `{CLONE_ROOT}`」代码路径。

### 10.1 代码与 CLI（`bootstrap/`）

| 要求 | 说明 |
|------|------|
| **移除 tools junction 分支** | **`materialize_workspace`**（及任何封装）**不得**再调用 **`ensure_junction`** 向 **`{WORKSPACE_ROOT}/tools/dify_upload`**、**`{WORKSPACE_ROOT}/tools/feishu_fetch`**（物化目标路径）建联接；物化 **仅** **递归拷贝** 源树至上述路径，并拷贝 **`{WORKSPACE_ROOT}/runtime/webhook`** 与 **`{WORKSPACE_ROOT}/vla_env_contract`**（**不**拷贝 **`onboard/`**）。 |
| **删除相关参数与开关** | 移除 **`link_tools`** 及 CLI **`--no-junction-tools`**、**`interactive_setup` 的 `no_junction_tools`** 等 **仅为 junction 服务** 的 API；调用方改为单一物化语义（拷贝 + `runtime/webhook`）。 |
| **删除或内联 `junction` 模块** | **`bootstrap/junction.py`** 若 **无其它调用方** → **删除**；**`bootstrap/tests/test_junction.py`**、**`test_materialize` 中仅测 junction 的用例** → **删除或改写** 为 **拷贝** 断言。 |
| **非 Windows** | 原 **`link_tools` 非 Win 抛错** 分支随 junction 删除；**不再**以 junction 定义 Windows 与 Linux 行为差。 |

### 10.2 脚本与文档（仓库内）

| 要求 | 说明 |
|------|------|
| **验收 / 自动化脚本** | 凡传入 **`--no-junction-tools`** 或 **依赖「默认 junction」** 的脚本（如 **`bootstrap/scripts/run-unattended-acceptance.ps1`**）→ **改为** 与 **唯一物化语义** 一致，**不得**再假设存在联接路径。 |
| **`bootstrap/README.md`** | **废除** 以 **junction 为生产默认或签字前提** 的表述；**与 §3 树 + 拷贝** 对齐。 |
| **`production-bootstrap-deployment-design.md` §3.4** | 该文 **`tools/`** 「策略 A：junction」**须在 NTH-008 交付中** 修订或删除，改为与本节 **实拷贝 + `runtime/webhook`** 一致；**策略 B**（空目录占位）若与内嵌 runtime 冲突，**须在 plan 中写清取舍**（通常 **仅保留拷贝**）。**不要求**在本文定稿前单独改该文。 |

### 10.3 验收

- **CI / 单测**：`materialize` 相关测试 **覆盖**「**`tools/*`、`vla_env_contract`、`runtime/webhook`** 均为拷贝、**无** **`onboard/`**」；**无** 对 **junction 创建成功** 的依赖。
- **§8** 整机验收与 **§6** `doctor` 规则 **在 plan 中有对应任务**，且 **与 10.1–10.2 同 PR 或可合并批次** 交付，避免文档宣称已废除 junction 而代码仍默认联接。

### 10.4 Plan 须承接 §3.2 清单与 §6 分档（**非**「开口约定」）

**NTH-008** implementation plan **正文** **必须**包含下列可审计块（可单开章节或附录，**不得**仅链到 issue/口头约定）：

| 承接项 | 最低要求 |
|--------|----------|
| **物化拷贝清单** | 与 **§3.2** 对齐的 **排除 / 保留** 规则表；**须**可对照 `materialize` 实现与单测 **逐条核对**。 |
| **`doctor` 分档表** | **FAIL / WARN** 条件枚举、与 **§6** 及 **§8.2** 对齐；**生产签字**路径下 **§6** 核心项 **不得**仅靠 WARN。 |
| **import 包名列表** | **§6** 烟测涉及的 **顶层包名** **完整列表**（与现有/目标 `doctor` 行为一致）。 |

**未**在 plan 中写明上述三块，**视为** NTH-008 交付 **不完整**，**不得**以「spec 已写见 plan」闭环签字。
