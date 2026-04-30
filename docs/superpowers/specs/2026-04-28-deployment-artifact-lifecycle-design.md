# 部署介质生命周期 — Design

> **落地状态：未落地。** 本文只写 **REQ + 验证**；**不设**与某份 implementation plan 的 Task 编号对照（**对照在 plan 写好之后加**，或由 plan 作者从本文 **import REQ-ID**）。**上层 P0 合同**仍以 **[2026-04-28-production-bootstrap-deployment-design.md](2026-04-28-production-bootstrap-deployment-design.md)** 为准；本文与其 **并行**，不重复 §3.4 文件树。

---

## 修订说明

- **2026-04-28：** 重写；**2026-04-28：** 去掉对 **未就绪/未定稿 plan** 的伪 Task 对齐，避免假追溯。已知 **`pip`/`cwd`/路径空格**：**`BugList.md` BUG-007**。
- **2026-04-28：** 增补 **§2**：区分 **`{WORKSPACE_ROOT}`** 与 **webhook 进程代码来源**；**删克隆**与 **editable** 关系；避免 REQ-L002 被误读成「克隆可随便删」。

---

## 1. 目的

**问题：** 只说「克隆维护仓」易让人以为 **现场必须长期 `git pull`**，或以为 **物化工作区默认要含 `webhook/` 源码树**。

**本文写清（可验收）：**

1. **长期运维锚点** = **`{WORKSPACE_ROOT}`** + **`{WORKSPACE_ROOT}/.env`**（与 production-bootstrap **§2.1** 一致）。
2. **`{CLONE_ROOT}`** = 编排 CLI（`materialize` / `install-packages` / `doctor`）用的 **源码树锚点**；**不要求**与远端 Git **持续同步** 作为管线运行前提。
3. **webhook/RQ** = **本机 Python 进程**，`import webhook_cursor_executor`，**代码来自当前解释器里已安装的包**（**不是**「必须先拷进 `{WORKSPACE_ROOT}`」）。运维常在 **`{CLONE_ROOT}`** 下 **cwd** 起 `uvicorn`/`rq`（相对路径、习惯）；**cwd** 与 **`{WORKSPACE_ROOT}`** **可以不同**。

---

## 2. 运行时代码、工作区、克隆目录（必读）

| 概念 | 是什么 |
|------|--------|
| **`{WORKSPACE_ROOT}`** | Cursor Agent、`task_context`、`.cursor_task/`；**运行合同** `.env`。 |
| **webhook/RQ 进程** | **同一台机**上的 Python；包体在 **`site-packages`**（wheel）或 **editable 指向的源码路径**（`-e`）。 |
| **删 `{CLONE_ROOT}`** | **`pip install -e .\webhook`**（ editable 指向克隆树）→ **删克隆会破坏 import**，进程无法再跑，除非 **重装为非 editable** 或保留介质。**wheel/普通安装** → 代码副本在 **`site-packages`** → **仅从「能 import」角度**克隆可删；启动脚本、`FOLDER_ROUTES_FILE` 相对路径等仍须一并迁移（运维负责）。 |

**结论：** 「物化 **不**把工作区做成 webhook 源码目录」≠「克隆可随时删」。**删克隆前先分清安装形态。** README / 操作手册 **不得**暗示「删掉克隆不影响 webhook」而不区分 **editable / 非 editable**。

---

## 3. 范围与非目标

| 纳入 | 排除 |
|------|------|
| CLI：**`--clone-root`**、推导失败时的失败语义 | MSI/安装向导步骤 |
| README：**克隆根 ≠ 必须长期 SCM 维护** 的表述 | K8s/Docker 必选拓扑 |
| webhook：**`VLA_WORKSPACE_ROOT` → 工作区 `.env`**（与 deployment-design §2.1 一致） | 改写 production-bootstrap **§3.4** 整树 |

---

## 4. 规范性需求（REQ）

每条：**陈述 → 验证（代码/文档/测试）→「plan 职责」一句话（不立 Task 号）。**

### REQ-L001 — 编排锚点显式化

**陈述：** `materialize-workspace`、`install-packages`、`doctor` **必须**支持 **`--clone-root`**（或等价命名）；推导失败（wheel/site-packages）时 **非零退出** 并提示 **`--clone-root`**，禁止静默错位路径。

**验证：** `bootstrap` 内 **`assert_clone_root_looks_sane`**（或等价）+ 测试覆盖非法目录。

**plan 职责：** 某 implementation plan **须**包含实现与单测条目，**可追溯至 REQ-L001**。

---

### REQ-L002 — 物化不把 webhook/onboard 拷入工作区（≠ webhook 无处运行）

**陈述：** `materialize-workspace` 落盘的初始化树 **不得**把 **`webhook/`、`onboard/`** 列为 **必选**写入 **`{WORKSPACE_ROOT}`**（**`tools/`** 联接 `dify_upload`/`feishu_fetch` 等按 deployment-design §3.4）。

**澄清：** 本条 **只约束「Cursor 执行工作区」目录树**，**不**定义 webhook **装在哪**。webhook/RQ **运行在解释器已安装的包上**，通常 **`cwd`** 仍为 **`{CLONE_ROOT}`**（启动命令、相对路径）；**工作区与克隆根分立**时 **照常**：生产设好 **`VLA_WORKSPACE_ROOT`** → **`ExecutorSettings`** 读 **`{WORKSPACE_ROOT}/.env`**。

**验证：** deployment-design §3.4 与物化代码 **一致**；无「必拷 webhook 入工作区」路径。

**plan 职责：** 同上，映射 **REQ-L002**。

---

### REQ-L003 — `doctor` 以工作区 `.env` 为门禁真源

**陈述：** `doctor --workspace` **不得以**「仅有克隆根 `.env`」判定运行侧就绪（对齐 deployment-design **§2.1**）。

**验证：** `doctor` 实现 + 单测。

**plan 职责：** 同上，映射 **REQ-L003**。

---

### REQ-L004 — README 不写死「必须长期维护 Git 克隆」

**陈述：** `bootstrap/README.md` 须可读说明：取得 `{CLONE_ROOT}` 可用 **clone / 解压 / 拷贝**；**持续 `git pull` 不是**管线 **运行**的 **验收前提**（可写为推荐/可选）。

**验证：** reviewer 检查 README **无**「必须长期维护克隆仓库」类 **Mandatory** 措辞与本文矛盾。

**plan 职责：** 同上，映射 **REQ-L004**。

---

### REQ-L005 — 生产 webhook 读工作区 `.env`

**陈述：** 设 **`VLA_WORKSPACE_ROOT` = `{WORKSPACE_ROOT}`** 时，**`ExecutorSettings`（或等价）**加载 **该目录 `.env`**。

**验证：** `webhook` 侧单测或合同测试 + 与 deployment-design **§2.1** 一致。

**plan 职责：** 同上，映射 **REQ-L005**（可与 **webhook/settings**、**task_context** 合同同批 plan 声明，仍以 **REQ-ID** 追溯）。

---

### REQ-L006 — 分发形态（延后意向）

**陈述（非当期硬 MUST）：** 若发布 **wheel/解压包**，仍须满足 **REQ-L001**（**`--clone-root`** 兜底）；不得假定仅靠 **`__file__` 推导**。

**闭合：** 出现 **命名工件** 后，由 **专项 implementation plan** 写闭合验收；本文 **REQ-L006** 届时改为 **已闭合** 或删除「延后」。

---

## 5. 本文结案条件（与 plan 的关系）

| # | 条件 |
|---|------|
| A | **REQ-L001～L005** 每条在 **至少一份已落地的 implementation plan** 中有 **显式条目**（表格/Task/ checklist 均可），且 **写明 REQ-ID**。 |
| B | **REQ-L004** 与 **`bootstrap/README.md`** 人工审阅一致。 |
| C | **REQ-L006** 未闭合前 **不得**把安装盘/向导写进本文 **MUST**。 |

**在 plan 缺失阶段：** 本文作为 **输入**；**不得**宣称已与某 Task「对齐」——**对齐发生在 plan 写好并引用 REQ-ID 之后**。

---

## 6. 阅读顺序（文档）

1. **[production-bootstrap-deployment-design.md](2026-04-28-production-bootstrap-deployment-design.md)**
2. **本文（REQ）**
3. **implementation plan（待定稿）** — 承担 **HOW**，且 **引用 REQ-ID**

---

## 7. 非目标

- **不**替代 webhook 业务设计 spec。
- **不**单独定义 **`task_context` 字段**。
- **不**裹挟 **NTH-008**（探活）。
