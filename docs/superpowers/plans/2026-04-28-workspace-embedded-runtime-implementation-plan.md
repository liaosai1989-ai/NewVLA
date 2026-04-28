# Workspace 内嵌 Runtime（NTH-008 / workspace-embedded-runtime） Implementation Plan

> **落地状态：已落地（主路径）**（2026-04-28；实现见 **`bootstrap/`**（**`doctor`**、**`probe`**、**`install-workspace-editables`**、物化 **`vla_env_contract/`** / **`runtime/webhook/`** / **`tools/*`**）、工作区同源树；旧 **`production-bootstrap-deployment-design.md` §3.4 / 旧 production-bootstrap implementation plan** **Task 10** 单列修订，与本 plan 收口非同一 PR 必选。）

> **For agentic workers:** REQUIRED SUB-SKILL: **`superpowers:subagent-driven-development`** — **按 Task 分派子代理、Task 间评审**。**备选**（单会话连续执行）：**`superpowers:executing-plans`**。Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使 `bootstrap materialize-workspace` **仅递归物理拷贝** 将 **`webhook`**（落 **`runtime/webhook`**）、**`dify_upload`** / **`feishu_fetch`**（落 **`tools/*`**）、以及 **键名合同包 **`vla_env_contract`**（落 **`{WORKSPACE_ROOT}/vla_env_contract`**，见 **Task 0**、附录 A）迁入 **`{WORKSPACE_ROOT}`**。**不再** 将 **`onboard/`** 迁入生产工作区（**方向一：拆依赖**，避免 CLI/入轨树污染运行目录）。**废除** **`tools`** junction 链路与相关 CLI/API；扩展 **`doctor --workspace`** 满足 **`2026-04-28-workspace-embedded-runtime-design.md`** §6 P0 与 §10（**物化树以 Task 0 后附录 A 为准**，**须**同批改该 spec §3–§4 正文）；交付 **`bootstrap probe`** **静态段 + HTTP 段**（与 **同 spec §8.1「探活分段」** 一致，**Task 8**）；验收脚本 / README / 样本 **`.env`** / **`webhook/*.md`** 联动见 **Task 9**；**`production-bootstrap-deployment-design.md` 与旧版 `…-production-bootstrap-deployment-implementation-plan.md`** **不**在本批次改正文，见 **Task 10**。

**Architecture:** **先**完成 **Task 0**：从 **`feishu_onboard.env_contract`** 抽出 **`vla_env_contract`**（PyPI 名建议 **`vla-env-contract`**），**`webhook` / `bootstrap` / `onboard`** 均改为依赖该小包的 **`file:`** 路径（克隆根 **`../vla_env_contract`**）；**`webhook`** **不再**依赖 **`feishu-onboard`**。在 **`bootstrap/materialize.py`** 用 **单一物化语义**（`shutil.copytree` + **可配置 ignore**）替代 **`link_tools` / `ensure_junction`**；删除 **`bootstrap/junction.py`** 及 **CLI `--no-junction-tools`**；**`doctor`** 增加 **实目录 / 非联接克隆** 与 **import 解析路径前缀** 校验。物化 **须**含 **`vla_env_contract`**；**`runtime/webhook/pyproject.toml`** 内 **`file:../vla_env_contract`**（相对 **克隆根 **`webhook/`** 深度）在拷贝到 **`runtime/webhook`** 后 **须** 变为 **`file:../../vla_env_contract`**：**Task 1 Step 3** **post-copy** 对 **`runtime/webhook/pyproject.toml`** **做字面串替换**（附录 A.1），否则 **BUG-007** 类解析与安装失败。**探活：** 子命令 **`bootstrap probe`**；**分段**——**静态**（目录、配置键、不与 webhook 监听冲突的 **`REDIS_URL`/`doctor` 可复用之项**）；**HTTP 开关** 文档与 CLI **统一名** **`--no-http`**（附录 B）。**HTTP 全量**（**`GET {WEBHOOK_PROBE_BASE}/health`**，`WEBHOOK_PROBE_BASE` 见 **`docs/superpowers/samples/pipeline-workspace-root.env.example`**），**须**在 **Redis + webhook(+按需 RQ) 已按 §4.2 启动后** 执行。**`interactive-setup`** **仅**链 **`doctor` → `probe --no-http`**（名称以 README 冻结为准），避免首跑未起服务即 **FAIL**。**RQ worker：** **不**作为本批次 **FAIL** 必选项；若在 **`probe`** 内检查队列：**未实现** 队列探测时 **stderr WARN** + README **固定一句**；**不**将 RQ 列为 **FAIL**（与 **spec §8.1** 尾段一致）。

**Tech Stack:** Python ≥3.12、标准库 **`shutil`/`pathlib`/`urllib.request`/`importlib`**（**`probe` HTTP** **只用** **`urllib.request`**；**不**新增 **`httpx`**）；**redis**（已有）；**pytest**；**PowerShell**；包名 **`webhook-cursor-executor`** → **`webhook_cursor_executor`**。**`bootstrap/pyproject.toml`**：**`redis`** + **`vla-env-contract @ file:../vla_env_contract`**（**Task 0** 后替换原 **`feishu-onboard @ file:`**）。

**关联：** **`BugList.md` BUG-007**（`cwd` + 工作区 **`pip install -e .`** —— **Task 0 后** **四处** **`vla_env_contract` / `runtime/webhook` / `tools/dify_*`**；可选复审 **Task 10**）；**`NiceToHave.md` NTH-008**（索引与 **`bootstrap probe`** 文案，**Task 9**）；**NTH-009** 排除；双 env：**`env.mdc`**。

---

## 文件结构（落点）

| 文件 / 目录 | 职责 |
|-------------|------|
| `bootstrap/src/bootstrap/materialize.py` | 递归拷贝 + ignore；**不再** `ensure_junction`；**`vla_env_contract/`**、`runtime/webhook/`、`tools/*`；**不**拷贝 **`onboard/`** |
| **`vla_env_contract/`**（**Task 0 新建**） | 自 **`onboard` 抽出** **`env_contract` API**；纯键名/分组函数，**无**飞书 CLI |
| **`bootstrap/src/bootstrap/junction.py`**（**Task 2 删文件**） | **Task 1** 先去引用；**Task 2** 物理删除；junction 作废 |
| `bootstrap/src/bootstrap/cli.py` | 去掉 **`--no-junction-tools`**；新增 **`probe [--no-http]`**（详见 **附录 B**） |
| `bootstrap/src/bootstrap/interactive_setup.py` | 去掉 **`no_junction_tools`**；**`doctor` → `probe --no-http`**；**`dry-run`** 跳过 **probe** |
| `bootstrap/src/bootstrap/paths.py` | **`assert_clone_root_looks_sane`** 继续只验**克隆根**；与工作区校验分工写进 **README**（**Task 9**） |
| `bootstrap/src/bootstrap/doctor.py` | P0：**实目录**/禁联接、`import` 路径前缀、FAIL/WARN 分档 |
| `bootstrap/src/bootstrap/install_packages.py` | （可选增强）与工作区安装的文档关系；**不改变** BUG-007 语义 |
| **`bootstrap/src/bootstrap/`**（逻辑可 **`probe.py` 旁置模块**） | **`install-workspace-editables`** 子命令（**Task 6 必做**）：对 **`vla_env_contract`、`runtime/webhook`、`tools/dify_upload`、`tools/feishu_fetch`** 按 BUG-007 逐目录 **`pip install -e .`**（**顺序**：先 **`vla_env_contract`** 再 **`runtime/webhook`**）。**`README` 与 unattended 脚本** **只**引用该子命令完成四轮 **（不**再并列「手抄四轮 PowerShell」为第二套真源）**。 |
| `bootstrap/tests/test_materialize.py` | 改为 **拷贝** 断言；**删** junction 专属用例；覆盖 **`runtime/webhook`**、**`vla_env_contract`** 存在；**断言无** **`onboard/`** |
| **删除** `bootstrap/tests/test_junction.py` | 如无其它引用 |
| `bootstrap/tests/test_doctor.py` | 新增：联接克隆 → FAILmock；路径前缀 cases |
| `bootstrap/tests/test_cli.py` | 快照无 **`--no-junction-tools`** |
| **`bootstrap/src/bootstrap/probe.py`（新建）** | **`run_probe(...)`**：全量探活（Task 8）；退出码 **README 表格式定义**（FAIL / WARN 成功 / 跳过项） |
| **`bootstrap/tests/test_probe.py`（新建）** | **mock** Redis / HTTP / 文件；**不**强依赖本机起真实 webhook |
| **`webhook/src/webhook_cursor_executor/app.py`** | 增加 **`GET /health`**（JSON 200）→ 物化后为 **`runtime/webhook`** 同源 |
| `bootstrap/scripts/run-unattended-acceptance.ps1` | **去掉** **`--no-junction-tools`**；物化后对 **工作区** **`pip`**；可选 **`-SkipProbe`**；全量签字含 **`probe`** |
| `bootstrap/README.md` | junction 删除；物化树 **`vla_env_contract/`**（**无** **`onboard/`**）；**签字链** 两段（**`doctor` → `probe --no-http`**；服务起后 **`probe` 全量**）；**附录 B** |
| `docs/superpowers/samples/pipeline-workspace-root.env.example` | **`WEBHOOK_PROBE_BASE`**（已与 **Task 9** 对齐样例） |
| `webhook/README.md`、`webhook/阶段性验收手册.md`、`webhook/操作手册.md` | 工作区路径 **`runtime/webhook`**、**`/health`**、与 **`bootstrap probe`** 关系（**Task 9**） |
| **`production-bootstrap-deployment-design.md`（旧 §3.4）** | **不**在本 PR 改正文 → **Task 10** |

---

## 附录 A：规格强制承接块（可复制到评审 / CI 对照）

### A.1 物化拷贝「排除 / 保留」清单（对齐 spec §3.2）

| 类别 | 规则 |
|------|------|
| **排除（目录名；另可配 glob）** | **`__pycache__`**、**`.pytest_cache`**、**`.mypy_cache`**、**`.ruff_cache`**、**`.git`**（subtree 误带时）、**`*.pyc`**；glob **`**/__pycache__/**`** **与上表目录名** **`ignore`** **同时生效**。 |
| **保留（禁止列入默认 exclude）** | **`pyproject.toml`**、**`requirements*.txt`**、**包内 **`src/**` 外** 非 `.py` 资源**（如 **`py.typed`**、数据 / stub / TOML / JSON 等）——与 spec §3.2「禁止删掉 pip/MANIFEST 依赖资源」一致；**实现与单测**须覆盖「含非 py 文件 subtree 仍被拷贝」之例。 |
| **源 → 目标** | **`{CLONE}/vla_env_contract` → `{WS}/vla_env_contract`**；**`{CLONE}/webhook` → `{WS}/runtime/webhook`**（拷贝后 **修补** **`pyproject.toml`** 内 **`file:../vla_env_contract` → `file:../../vla_env_contract`**，与 **Task 1** 一致）；**`{CLONE}/dify_upload` → `{WS}/tools/dify_upload`**；**`{CLONE}/feishu_fetch` → `{WS}/tools/feishu_fetch`**。**`onboard/`** **不**物化。 |

### A.2 `doctor` FAIL / WARN 分档表（最低门槛 + 可扩展）

| 条件 | 退出 | 阻塞生产签字 |
|------|------|----------------|
| 缺 **`{WS}/runtime/webhook/pyproject.toml`** | **FAIL** | 是 |
| **`{WS}/tools/dify_upload`** **未**同时满足「**是**目录 **且** 含 **`pyproject.toml`**（包根）」 | **FAIL** | 是 |
| **`{WS}/tools/feishu_fetch`** **未**同时满足「**是**目录 **且** 含 **`pyproject.toml`**（包根）」 | **FAIL** | 是 |
| **`{WS}/vla_env_contract/pyproject.toml`** 缺失 | **FAIL** | 是 |
| **`tools/dify_upload`、`tools/feishu_fetch`、`runtime/webhook`、`vla_env_contract`** **各**经 **`Path.resolve()`** 后 **路径已不在 **`{WS}`** 规范化前缀下**（含 junction 指回 **`{CLONE_ROOT}`**） | **FAIL** | 是 |
| **`{WS}/onboard/`** 存在（**遗留污染**；方向一 **不应** 出现） | **FAIL**（**README 冻结**） | 是 |
| **`importlib.util.find_spec` + 模块 `__file__`**：下列 **工作区链包** 解析到 **非 `{WS}` 前缀**（含仍指克隆 editable） | **FAIL** | 是 |
| **`REDIS_URL` 未设** | **WARN**（仅 stderr 提示，现行行为可延续） | 否 |
| **JSON **`pipeline_workspace.path`** 与 `--workspace` 漂移**（无 **`FEISHU_FOLDER_ROUTE_KEYS` 时） | **WARN**（现 **`_warn_json_drift`**） | 否（与现 spec P0「不单独因该项失败」一致；**spec 将来改 P0 时再随 spec 改 doctor**） |

### A.3 import 顶层包名列表（与工作区前缀校验对齐 spec §10.4）

须在 **`doctor` 中与 §6 smoke 一致**（与当前 **`_import_pipeline_packages`** 对齐 **并收紧路径**）：

| 模块名（`import …`） | 预期安装名 / 备注 |
|----------------------|-------------------|
| **`feishu_fetch`** | **`feishu-fetch`** editable under **`tools/feishu_fetch`** |
| **`dify_upload`** | **`dify-upload`** editable under **`tools/dify_upload`** |
| **`webhook_cursor_executor`** | **`webhook-cursor-executor`** editable under **`runtime/webhook`** |
| **`vla_env_contract`** | **`vla-env-contract`** editable under **`vla_env_contract`** |

**不**将 **`markitdown`** 纳入「须落 **`{WS}`** 前缀」列表（第三方 wheel，与现 doctor 行为一致）；其 **ImportError** 仍为 **FAIL**。

---

## 附录 B：`bootstrap probe` 分段与开关（对齐 spec §8.1）

| 模式 | 行为 | 典型调用时机 |
|------|------|----------------|
| **`--no-http`** | **静态段**：§6 延伸之目录/联接检查、`.env` 键、**已与 doctor 对齐**的配置探针、`REDIS_URL` ping；**不打** webhook HTTP | **`interactive-setup` 单次会话末尾** |
| **默认（无 `--no-http`）** | **全量**：静态段 **+** **`GET {WEBHOOK_PROBE_BASE}/health`** | **Redis/webhook(+按需 RQ) 已启动后**，生产签字 |
| **RQ 队列探测** | **未实现** 时：**stderr WARN** + **`README` 固定一句**；**不 FAIL** | 与 **spec §8.1「RQ worker」** 尾句一致 |

**退出码：** 在 **`bootstrap/README.md`** 用表固定（**0** 成功；**1** 硬失败；**2** 仅 WARN 成功等），**单测**对齐。

---

## Task 0: 抽出 **`vla_env_contract`**（方向一 / **须**在 **Task 1 前**合入；**最晚**与 **本 plan 代码** **同一合并批次**）

**动机：** **`webhook`** 仅消费 **`env_contract`** 键名 API；**`bootstrap/doctor`** 同。**`feishu-onboard @ file:../onboard`** 迫使生产工作区物化整棵 **`onboard/`**，与运行期职责无关。

**Files（最小集，实现时可微调路径）：**

- **新建** **`vla_env_contract/pyproject.toml`**、**布局** **`vla_env_contract/src/vla_env_contract/__init__.py`**（导出 **公共 API**）**+ **`env_contract.py`**（**由原** **`onboard/.../env_contract.py`** **整文件迁入**，避免双真源）。
- **修改** **`onboard/pyproject.toml`**：增加 **`vla-env-contract @ file:../vla_env_contract`**；**`onboard`** 内 **`validate.py` / `flow.py`** **等**：**一律** **`from vla_env_contract import …`**。**删除** **`onboard`** 侧 **手写** **`env_contract` 逻辑**（**不**再保留 **第二大套** **`feishu_onboard` 内并联实现**）。
- **修改** **`webhook/pyproject.toml`**：删除 **`feishu-onboard`**；增加 **`vla-env-contract @ file:../vla_env_contract`**；**`[tool.pytest.ini_options] pythonpath`** 加入 **`../vla_env_contract/src`**，**去掉** **`../onboard/src`**。
- **修改** **`webhook/src/webhook_cursor_executor/settings.py`**：**`from vla_env_contract import …`** —— **导入名** **`vla_env_contract/__init__.py`** **已导出**者。
- **修改** **`bootstrap/pyproject.toml`**：**依赖** 改为 **`vla-env-contract @ file:../vla_env_contract`**；**`pythonpath`** 同步。
- **修改** **`bootstrap/src/bootstrap/doctor.py`**：**`from vla_env_contract import …`**。
- **修改** **`bootstrap/src/bootstrap/install_packages.py`**：**`_EDITABLE_PACKAGES`** **须**含 **`vla_env_contract`**，且 **排序** **`vla_env_contract` 先于 `webhook` / `onboard`**（**`file:`** 依赖）；**`onboard`** **保留**（维护仓 CLI 开发仍装，**不**进生产工作区物化）。
- **测试：** **`onboard/tests/test_env_contract.py`** → **`vla_env_contract/tests/`**（**随迁**断言 **import** **`vla_env_contract`**）；**`bootstrap/tests/test_doctor.py`**、**`bootstrap/tests/test_install_packages.py`**：**mock / 断言可编辑目录集与顺序** 须与 **`install_packages.py` 之 `_EDITABLE_PACKAGES`** 最终实现 **一致**（含 **`vla_env_contract`**，排序 **`vla_env_contract` 先于 `webhook`**）。

- [ ] **Step 1:** 新建包 + 搬迁源码；**`pytest onboard/tests` / `webhook/tests` / `bootstrap/tests`** 在克隆根 **全绿**（**`install-packages` / 各目录 `pip install -e .`** 按 README）；**显式** **`pytest bootstrap/tests/test_install_packages.py -q`** —— 期望集与 **`_EDITABLE_PACKAGES`**、包序 **无漂移**。
- [ ] **Step 2:** **`grep -r "feishu_onboard.env_contract\|from feishu_onboard import"`** 仓库内 **除 onboard 包内可选薄层 / 历史文档链接外** 无生产路径残留。
- [ ] **Step 3:** **`2026-04-28-workspace-embedded-runtime-design.md`**：§3.1 **树** **删** **`onboard/`**、**增** **`vla_env_contract/`**；§3.2、§4.1 **「三处」** **改为** **四处** **`pip install -e .`**（**含** **`vla_env_contract`**，**顺序** **Task 5**）；**删** **`file:../onboard`**。**`2026-04-28-task-context-bootstrap-sample-agent-contract-design.md`**：**按** **`docedit.mdc`** **追加修订说明**；**表** **与** **正文** **删** **junction** **叙事**，**改** **实拷贝** **与** **`runtime/webhook`**。**两 spec** **与** **Task 8.3 / Task 9** **同一文档 PR** **合入**。
- [ ] **Step 4: Commit** `refactor: extract vla_env_contract from feishu-onboard for runtime deps`

**阻塞：** **未完成 Task 0** 则 **勿** 按旧附录物化 **`onboard/`**；**Task 1** 起以 **本文附录 A** 为准。

---

## Task 1: `copytree` 辅助与 `materialize_workspace` 重写

**Depends:** **Task 0**（**`{CLONE}/vla_env_contract`** 已存在）。

**Files:**
- Create: **`bootstrap/src/bootstrap/copy_trees.py`** — **`copytree` + `ignore`** **专责**；**`materialize.py` 只编排**（**避免** **> ~40 行** **拷贝细节** **堆进** **`materialize_workspace`**）
- Modify: `bootstrap/src/bootstrap/materialize.py` — **去掉** 对 **`junction` / `link_tools`** 的引用（**勿**于此任务删除 **`junction.py` 磁盘文件；**删除见 Task 2**）
- Test: `bootstrap/tests/test_materialize.py`

- [ ] **Step 1: 写失败单测**（期望：无 junction、**`runtime/webhook`** 与 **`vla_env_contract`** 存在；**无** **`onboard`**）

```python
def test_materialize_copies_webhook_runtime_and_vla_env_contract(tmp_path):
    clone = tmp_path / "clone"
    ws = tmp_path / "ws"
    clone.mkdir()
    (clone / ".env").write_text("K=v\n", encoding="utf-8")
    (clone / ".env.example").write_text("K=v\n", encoding="utf-8")
    (clone / "prompts" / "AGENTS.txt").write_text("a", encoding="utf-8")
    (clone / "prompts" / "rules").mkdir(parents=True)
    (clone / "vla_env_contract" / "pyproject.toml").write_text("[project]\nname=dummy-vla-env\n", encoding="utf-8")
    (clone / "webhook" / "pyproject.toml").write_text(
        '[project]\nname=dummy-wh\ndependencies = ["vla-env-contract @ file:../vla_env_contract"]\n',
        encoding="utf-8",
    )
    (clone / "dify_upload" / "pyproject.toml").write_text("[project]\nname=x\n", encoding="utf-8")
    (clone / "feishu_fetch" / "pyproject.toml").write_text("[project]\nname=y\n", encoding="utf-8")
    materialize_workspace(
        clone_root=clone,
        workspace_root=ws,
        seed_env=None,
    )
    assert (ws / "runtime" / "webhook" / "pyproject.toml").is_file()
    assert (ws / "vla_env_contract" / "pyproject.toml").is_file()
    assert (ws / "tools" / "dify_upload" / "pyproject.toml").is_file()
    assert not (ws / "onboard").exists()
    wh_toml = (ws / "runtime" / "webhook" / "pyproject.toml").read_text(encoding="utf-8")
    assert "file:../../vla_env_contract" in wh_toml
    assert "file:../vla_env_contract" not in wh_toml
```

Adjust API: **删掉** **`link_tools=`** kwargs — 与本任务 Step 3 一并改调用方前先让测试 **编译失败**，再 Step 3 接线。

- [ ] **Step 2:** 运行 `pytest bootstrap/tests/test_materialize.py::test_materialize_copies_webhook_runtime_and_vla_env_contract -q` → **FAIL**

- [ ] **Step 3: 最小实现**

在 **`materialize_workspace`**：
1. **`shutil.copytree(..., dirs_exist_ok=False, ignore=...)`**，**`ignore`** 函数排除 **附录 A.1** 目录名；
2. 源 **`clone_root / "vla_env_contract"`** → **`workspace_root / "vla_env_contract"`**；
3. 源 **`clone_root / "webhook"`** → **`workspace_root / "runtime" / "webhook"`**；拷贝完成后 **修补** **`runtime/webhook/pyproject.toml`**：**`file:../vla_env_contract` → `file:../../vla_env_contract`**（与 **Task 0** 字面一致；**实现** **整行字面替换** **；** **`test_materialize_copies_webhook_runtime_and_vla_env_contract`** **锁结果**）。
4. 源 **`dify_upload`、`feishu_fetch`** → **`workspace_root / "tools" / …`**；
5. **删掉** **`from bootstrap.junction import ensure_junction`** 分支与 **`link_tools`** 参数；**不**拷贝 **`onboard`**。

函数签名示意：

```python
def materialize_workspace(
    *,
    clone_root: Path,
    workspace_root: Path,
    seed_env: Path | None = None,
    sync_env_from_clone: bool = False,
    dry_run: bool = False,
    force: bool = False,
) -> None:
```

- [ ] **Step 4:** 同上用例 **PASS**；**全文件** `pytest bootstrap/tests/test_materialize.py -q` 并修旧测（见 Task 4）。

- [ ] **Step 5: Commit** `feat(bootstrap): materialize vla_env_contract + runtime/webhook path patch`

---

## Task 2: 移除 junction 模块与 CLI / 交互路径

**Files:**
- Delete: `bootstrap/src/bootstrap/junction.py`
- Modify: `bootstrap/src/bootstrap/cli.py`, `bootstrap/src/bootstrap/interactive_setup.py`
- Delete: `bootstrap/tests/test_junction.py`

- [ ] **Step 1:** **`bootstrap/`** 内 **`grep`/`rg`**（`junction`、`link_tools`、`no_junction`）列清单；逐项删引用。**全仓** 同模式可再跑一遍建 **残留清单**：**样本/脚本** 须改；**仅文档** 且属 **`production-bootstrap-deployment-design` / 旧 implementation plan`** 者 **刻意** 归 **Task 10**，勿与「bootstrap 已绿」混为一谈。

**`cli.py`：** **`materialize-workspace`** 去掉 **`--no-junction-tools`**；调用 **`materialize_workspace`** 不再传 **`link_tools`**。**`interactive-setup`** 去掉 **`--no-junction-tools`**；**`run_interactive_setup`** 删掉 **`no_junction_tools`** 参数。

- [ ] **Step 2:** **`pytest bootstrap/tests/test_cli.py bootstrap/tests/test_interactive_setup.py -q`** 并更新快照 / 期望值。

- [ ] **Step 3: Commit** `refactor(bootstrap): remove junction tools and CLI flags`

---

## Task 3: `doctor` §6 — 路径与 import

**Files:**
- Modify: `bootstrap/src/bootstrap/doctor.py`
- Test: `bootstrap/tests/test_doctor.py`

- [ ] **Step 1: 新增单测**：用 **`unittest.mock.patch`** **`Path.resolve`**，使 **`tools/dify_upload`**（**及**任一受检路径）**解析落入** **克隆根** —— **`run_doctor` → 1**。**不**依赖 **真实 junction** **（兼容** **无权** **`mklink`** **之 CI）**。

- [ ] **Step 2:** 实现 **`_workspace_import_paths_ok(workspace: Path)`**：对 **附录 A.3** 四模块，`importlib.util.find_spec` + **`spec.origin` / submodule_search_locations** 取路径，规范化后必须以 **`workspace.resolve()`** 为前缀（参阅 **spec §8.2**）。

- [ ] **Step 3:** 实现 **`_tools_and_runtime_are_not_clone_links(workspace: Path, clone_root: Path)`**：对 **`tools/dify_upload`、`tools/feishu_fetch`、`runtime/webhook`、`vla_env_contract`**：**`resolved = p.resolve();`** **须** **`os.path.normcase(str(resolved)).startswith(os.path.normcase(str(workspace.resolve()))`**；**且** **`not str(resolved).startswith(os.path.normcase(str(clone_root.resolve())))`** 对「内容目录」语义 —— **精细实现时注意 Windows 大小写**。若 junction：`resolve()` 落入克隆 → 第二条件触发 **FAIL**.

- [ ] **Step 4:** `pytest bootstrap/tests/test_doctor.py -q`。

- [ ] **Step 5: Commit** `feat(bootstrap): doctor workspace-embedded checks`

---

## Task 4: 重写 `test_materialize` 旧 junction 用例并全绿

**Files:**
- Modify: `bootstrap/tests/test_materialize.py`

- [ ] **Step 1:** **删** **`test_materialize_tools_junctions`**。**新增 **`test_materialize_tools_are_real_directories`**：**拷贝物化后** **`tools/dify_upload`** **`resolve()`** **仍在** **`ws`** **规范化前缀内**。

- [ ] **Step 2:** 所有 **`materialize_workspace(..., link_tools=...)`** 调用改为 **无上款参数**。

- [ ] **Step 3:** `pytest bootstrap/tests -q`。

- [ ] **Step 5: Commit** `test(bootstrap): align materialize tests with embedded copy`

---

## Task 5: 验收脚本与「工作区 editable 安装」唯一写法

**Depends:** **Task 6** **须** **先** **合入**（**`install-workspace-editables`** **存在** **后** **本 Task** **改** **`run-unattended-acceptance.ps1`** **调用** **该子命令**）。**本文** **Task 编号** **不重排**。

**Files:**
- Modify: `bootstrap/scripts/run-unattended-acceptance.ps1`
- Modify: **`bootstrap/README.md`**「分步命令」小节

约定（对齐 **BUG-007 + §4.1**；**Task 0** 后 **四** 包）：

1. **`pip install -e .\bootstrap`** 仍在 **克隆根 **`bootstrap`** 目录 cwd**；
2. **`unattended` 签字路径（冻结）：** **`materialize-workspace`** → **`bootstrap install-workspace-editables --workspace <Workspace>`**（**Task 6**）→ **`doctor`** → **`probe`**（**段落** **按** README）。**默认** **`$SkipInstallPackages = $true`**：**不**调用 **`bootstrap install-packages --clone-root`** **（克隆侧 editable **与 **`doctor`** **工作区前缀** **易冲突**）**。**维护者** **本地** **`install-packages`** **仍可用**：**不**记入 ** unattended 正文**。**README「分步命令」** **写死** **上序列**。**Task 5 结尾 **`pytest`** + **脚本 dry run** **验证** **该序列** **`ExitCode`** **与** **`test_install_packages`** **`_EDITABLE_PACKAGES`** **语义** **无矛盾**。

在 **`run-unattended-acceptance.ps1`**：**删除** **`--no-junction-tools`**；**`materialize-workspace`** 成功后 **调用 **`install-workspace-editables`** **（四轮 **`pip`** **封装在同一子命令**）**。**

- [ ] **Step 3（验收）：** **`pytest bootstrap/tests/test_install_packages.py -q`**：**`_EDITABLE_PACKAGES`** **仍** **测** **克隆侧** **`install-packages`** **单元**；**unattended** **默认路径** **见上文** **`$SkipInstallPackages`**。**两路** **不得**互相覆盖 **期望值**——**Task 5 结尾 PR** **`pytest`** **全绿** **即**关闭。

- [ ] **Step 4: Commit** `ci(bootstrap): unattended uses workspace editable installs`

---

## Task 6: 子命令 **`install-workspace-editables`**（**必做**）

实现 **固定 CLI**：

```text
bootstrap install-workspace-editables --workspace <WS>
```

内部 **`subprocess`** **`sys.executable -m pip install -e .`**，**cwd** **严格依次** **`WS/vla_env_contract`** → **`WS/runtime/webhook`** → **`WS/tools/dify_upload`** → **`WS/tools/feishu_fetch`**。单测：**mock subprocess** **断言** **四轮** **`cwd`** **与顺序**。**`README`**、**workspace-embedded §4.1「唯一写法」**、**`run-unattended-acceptance.ps1`** **只**指向 **本条子命令**，**禁止**并列 **「手抄 PowerShell 四轮」第二套**。**注：** **`probe`** **与** **`install-workspace-editables`** **在** **`bootstrap/cli.py`** **注册** **为** **子命令**；**`pyproject.toml` `[project.scripts]`** **只** **保留** **现有 **`bootstrap`** **入口** **一行**。

- [ ] **Commit** `feat(bootstrap): install-workspace-editables for BUG-007`

---

## Task 7:（编号占位）

本节 **故意留空**（无独立交付物），**避免** 与历史文档/外部引用对 **Task 编号** 重排。下一节 **Task 8** 不变。

---

## Task 8: 全量探活 + Plan 落地 renew（NTH-008 本期必交付）

**对齐：** **`NiceToHave.md` §NTH-008**；**`workspace-embedded-runtime-design.md` §8.1「探活分段」**。**本节禁止**「下期」「占位」「仅文档」代之 —— **`GET /health`**（**webhook**）**与 **`bootstrap probe`** **同** **`NTH-008`** **代码 PR** **合入**。

### 8.1 Webhook 侧：HTTP 锚点（P0）

- [ ] 在 **`webhook/src/webhook_cursor_executor/app.py`** 之 **`create_app`** 注册 **`GET /health`**：`JSONResponse({"status":"ok"}, 200)`，**无副作用**（**不查** Redis、**不写**队列；**仅用**静态 JSON **应答**）。
- [ ] **`webhook/tests/`** 单测：**TestClient GET `/health`** → 200。
- [ ] **`WEBHOOK_PROBE_BASE`**：**`ExecutorSettings`** **须** **登记** **同名 **`env`** **字段**（**`str`**）。**`webhook/README.md`** **与 **`docs/superpowers/samples/pipeline-workspace-root.env.example`** **写** **键名**、**示例 **`http://127.0.0.1:<PORT>`** **（** **`<PORT>`** **与** **启动命令** **文档** **同一** **）**。**`bootstrap` `run_probe`**：**自** **工作区 **`.env`** **读** **该键**；**键** **缺失** **且** **CLI** **未** **传** **`--webhook-http-base`** **→** **FAIL** **（** **无法** **拼** **`GET …/health`** **）**。

### 8.2 `bootstrap probe`：静态段 + HTTP 段（**附录 B**）

- [ ] **`bootstrap/src/bootstrap/probe.py`**：**公共段**（**`doctor` 已通过后仍可复跑**）：**Redis**（若 **`REDIS_URL` 非空** → ping）、路由/配置探针与同 **`doctor`** **可共享**的逻辑（勿重复两套键名）。
- [ ] **`--no-http`**：**不发起** **`GET …/health`**；用于 **`interactive-setup`**。**默认（无 **`--no-http`**）**：再做 **HTTP**；连接拒绝 → **FAIL**（**惟**全流程生产签字语义；Merge 闸见下）。
- [ ] **`cli.py`**：**`bootstrap probe --workspace <path> [--no-http]`**；**脚本用** **`-SkipProbeHttp`**/**`-SkipProbe`**（与 **`run-unattended-acceptance.ps1`**）**仅 Merge/A 档**：README 标明 **≠** 全流程签字。
- [ ] **`test_probe.py`**：mock **`urllib`/socket**；覆盖 **两段** CLI。
- [ ] **`interactive_setup`**：**在进程内** **调用 **`run_probe(..., http=False)`** **（** **不** **依赖** **用户** **手输** **`probe` CLI`** **）**。
- [ ] **`run-unattended-acceptance.ps1`**：若 **不能**在本机起 listener，**`-SkipProbeHttp`** 仅跳过 **HTTP 子段**，**`-SkipProbe`** 跳过整条 **probe**；**文档**写清 **B 档**要求。

### 8.3 Workspace spec 落地态 + prompts renew（闸门）

- [ ] **`2026-04-28-workspace-embedded-runtime-design.md`**：文首 **落地状态** 与 **`docedit.mdc`** 成对（**本章 spec 已实现**）。
- [ ] **`2026-04-28-task-context-bootstrap-sample-agent-contract-design.md`**：**文改** **条目** **已在** **Task 0 Step 3** **写死**；**本** **闸门** **仅** **核对** **同一** **Task 9** **PR** **含** **该** **文件** **修订** **已** **合入**。
- [ ] **`prompts/AGENTS.txt`**、根 **`AGENTS.md`**：**`plan-landed-renew-agents-rules.mdc`**，与 **物化树 + **`probe`** 两段**一致；**「长期静态资产」** 细则 **见 Task 9**（**勿**漏 **`vla_env_contract/`**）。

---

## Task 9: 本站联动文档与索引（与实现 **同 PR**）

- [ ] **`prompts/AGENTS.txt`**：**「长期静态资产」** 列表（约 **L71–L76**）**与 **`2026-04-28-workspace-embedded-runtime-design.md` §3.1** 对齐：**增 **`vla_env_contract/`**（**`vla-env-contract`** 源码树，**.env 键名合同**）；**保留 **`tools/`**、**`runtime/webhook/`** 及规格链；**不得** 将 **`onboard/`** 列为工作区物化长期资产（入轨 **仅** 维护仓/克隆根 **`feishu-onboard`**）。物化后 **根 `AGENTS.md`**：**若** **由** **`materialize`** **从** **本模板** **生成** **则** **与** **`prompts/AGENTS.txt`** **同条**；**若** **已** **存在** **则** **按** **`plan-landed-renew-agents-rules.mdc`** **renew** **补** **同条**。
- [ ] **`bootstrap/README.md`**：junction 删除；物化树 **`vla_env_contract/`**、**无 `onboard/`**；§4.1 **四处** **`pip install -e .`**（**cwd** = 对应目录，**先** **`vla_env_contract`**）；**两段签字链**（**`interactive-setup`：** **`doctor` → `probe --no-http`**；**生产：** 服务起 **`probe`** 全量）；**附录 B** 退出码。
- [ ] **`NiceToHave.md`**：**总表 NTH-008** **`plan`** 列 **同时** **保留** **`…-production-bootstrap-deployment-implementation-plan.md`** **链接** **并** **追加** **`…/2026-04-28-workspace-embedded-runtime-implementation-plan.md`**；**方案草案**：**`bootstrap probe`** 定型（**替** **`probe-all`**）。
- [ ] **`docs/superpowers/samples/pipeline-workspace-root.env.example`**：与 **`WEBHOOK_PROBE_BASE`** **键名** **及** Task 8 **`ExecutorSettings`** **字段** **同名** **复核**；**`FOLDER_ROUTES_FILE`** **注释与示例** **一律** **`{WORKSPACE_ROOT}`** **相对路径** **`runtime/webhook/config/…`** **（** **对齐 **`workspace-embedded` §3.1`** **ASCII** **）**，**禁止** **保留** **裸 **`webhook/config/…`** **（** **易** **等同** **克隆根** **`webhook/`** **）**。
- [ ] **仓库根 `.env.example`**：**`FOLDER_ROUTES_FILE`** 等提及 **`webhook/config/`** 的注释/占位，与 **`runtime/webhook`**（内嵌 runtime）**对齐复核**（与上条同源：工作区路由文件 **相对工作区根**）。
- [ ] **`webhook/README.md`、`webhook/阶段性验收手册.md`、`webhook/操作手册.md`**：以 **`{WORKSPACE_ROOT}/runtime/webhook`** 为主线；**/health**、**`WEBHOOK_PROBE_BASE`、`bootstrap probe`**（**具体操作见各文件，勿与 Task 10 重叠**）。
- [ ] **Commit** `docs: workspace embedded linkage (prompts/AGENTS, readme, samples, webhook md, NiceToHave)`

---

## Task 10: 延后修订（**须在** NTH-008 **代码已合入主分支之后** **开** **单独 PR**）

**口径（与 **`workspace-embedded-runtime-design.md` §2 / §10.2**）：** 嵌入 runtime **代码**与 **workspace-embedded spec**/**本 plan Task 8–9** **同批次合入**；**`production-bootstrap-deployment-design` / 旧 `-production-bootstrap-deployment-implementation-plan`** 改正文 **紧随其后** 的 **单独 PR** **仍计作** **NTH-008 交付收尾**——仅 **避免**「deployment 正文先改、主干仍 junction」的 **假一致**，**不等于**拖到无关批次。

以下 **援引** **`production-bootstrap-deployment-design` / `-implementation-plan`** **旧 junction 真源**，**不在**本仓库 **同一次**嵌入 runtime **代码** PR 改正文——避免「文档已改、主干仍 junction」之 **假一致**：

- [ ] **`docs/superpowers/specs/2026-04-28-production-bootstrap-deployment-design.md`**：**§3.4** **删除** **`tools/`** **junction** **策略段**；**新增** **指向** **`2026-04-28-workspace-embedded-runtime-design.md`** **§3** **「实拷贝」** **的单段交叉引用**；**`doctor` 相关表中** **删除** **`junction`** **字样**；
- [ ] **`docs/superpowers/plans/2026-04-28-production-bootstrap-deployment-implementation-plan.md`**：**文顶** **废止通告**——**junction Task 及架构段** supersede by **`2026-04-28-workspace-embedded-runtime-implementation-plan.md`**；
- [ ] **`BugList.md` BUG-007`**：**建议** **本 Task** **顺手** **做**：总表「相关链接」**补** **`workspace` implementation plan** **链接**；正文 **补** **一行**——工作区 **`pip`** **四处** **目录** **`vla_env_contract`、`runtime/webhook`、`tools/dify_*`**（**Task 0** **后**）。

---

## Self-review（自检）

| 检查项 | 状态 |
|--------|------|
| **方向一拆依赖** | **Task 0** + **附录 A** 同步 **`vla_env_contract`** / **去 **`onboard/`** 物化** |
| **spec §3–§4、§6–§8、§10**（design 须跟 Task 0 改树） | **Task 0 Step 3** + **Task 1–9 + A/B** |
| **§10.4** 三块（清单、分档、import 列表）均在 **附录 A** | ✓（**A.3** 已换 **`vla_env_contract`**） |
| **探活分段 + RQ WARN**（spec §8.1 尾） | **附录 B + Task 8** |
| **延后旧 production bootstrap 文** | **Task 10**（**紧随合码**，见 Task 10 文首口径） |
| 根 `.env.example` + `docs/.../pipeline-workspace-root.env.example`：`FOLDER_ROUTES` 类路径与 `runtime/webhook` | **Task 9** |
| **task-context-bootstrap design** 无 junction **双真源** | **Task 9** **文档 PR** **（** **与 Task 0 Step 3 ** **同文** **）** |
| **`grep` 范围**：`bootstrap` vs 全仓 vs Task 10 **文档** | **Task 2** / **Self-review** |
| **占位符** | **无** |
| **CLI** `materialize` / **`install-workspace-editables`** / `probe` | Task 1–2、**6（必）**、8；**挂载** **`bootstrap.cli`** **；无** **`console_scripts`** |

**已知 gaps（已闭合）：** 克隆侧 **`install-packages`** 与工作区 **`doctor`** 前缀检查冲突：**Task 5** 冻结 unattended 默认 **`$SkipInstallPackages = $true`**。**Task 1** 对 **`runtime/webhook/pyproject.toml`** **post-copy** 字面替换；**`test_materialize_copies_webhook_runtime_and_vla_env_contract`** **断言** **`file:../../vla_env_contract`**。

---

## Plan 作者 review（本轮追加后）

| 项 | 结论 |
|----|------|
| **与方向一一致性** | **Task 0** 抽 **单包**；**webhook/bootstrap** 不再拉 **整棵 onboard**；生产树 **仅** 多 **`vla_env_contract`**。 |
| **依赖顺序** | **`vla_env_contract` → `runtime/webhook`**；**合入顺序** **Task 6 → Task 5**；**`_EDITABLE_PACKAGES`** **先** 小合同包。 |
| **路径修补** | **物化** 后 **`webhook` 深一层**，**`file:../`** 不够；**Task 1** **TOML 替换** + **单测断言**，避免 **BUG-007** 复发。 |
| **doctor 表** | **A.2** **`onboard/`** **存在 →** **FAIL** **（** **README** **冻结** **）**。 |
| **遗漏风险** | **`install_packages` 元组**、**`test_install_packages`**（**Task 0 Step 1** + **Task 5 Step 3** 显式 **`pytest`**）、**各文 **`feishu_onboard.env_contract`** 指针** —— **Task 0** 已点 **`install_packages`**；**`grep`** —— **Task 2**。**`prompts/AGENTS.txt` 长期资产** —— **Task 9** 首条 **显式**。**根 `.env.example` / 样本 **`FOLDER_ROUTES_FILE`** —— **Task 9**。**task-context** 已落地 spec —— **Task 0 Step 3**、**Task 8.3**。 |
| **spec 双真源** | **workspace-embedded design** 仍写 **旧树** 至 **Task 0 Step 3** 合入；**task-context-bootstrap** —— **同上 + Task 8.3**；**Goal** 已声明 **须同批改 §3–§4**。 |

---

## Execution handoff

**Plan complete and saved to `docs/superpowers/plans/2026-04-28-workspace-embedded-runtime-implementation-plan.md`.**

**Two execution options:**

1. **Subagent-driven (recommended)** — fresh subagent per task, review between tasks. **REQUIRED SUB-SKILL:** superpowers:subagent-driven-development.
2. **Inline execution** — execute tasks here with checkpoints. **REQUIRED SUB-SKILL:** superpowers:executing-plans.

**Which approach?**