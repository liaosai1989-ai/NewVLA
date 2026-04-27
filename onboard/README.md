# feishu-onboard

在管线仓库根为飞书 **App 文件夹** 做入轨：创建文件夹、为「分享委托人」加云空间文件夹协作者、两阶段写根目录 `.env`，并在输入完成后对当前工作区执行 `lark-cli config init`（`--app-secret-stdin`）。

## 安装

在仓库中：

```powershell
cd path\to\NewVLA\onboard
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .[test]
```

安装后本机应有入口 `feishu-onboard`（由 `pyproject` 的 `[project.scripts]` 注册）。

## 人工操作手册（一步一步）

### 0. 弄清「根目录」指哪里

- 工具会读写**管线维护仓库根目录**下的 `.env`：默认取 `feishu-onboard` 包在磁盘上的位置向上推算（editable 安装时即本仓库 `NewVLA` 根目录）。
- 若用 **非 editable** 安装（包在 `site-packages`），在运行前必须在**同一会话**里设置环境变量：
  - `FEISHU_ONBOARD_REPO_ROOT` = 管线仓根的**绝对路径**（例：`C:\Cursor WorkSpace\NewVLA`）。

### 1. 进入终端工作目录

- 建议在**管线仓根**打开终端（与上面「根」一致），便于后续检查 `rules/` 与 `.env`。
- Windows PowerShell 5.1 下用分号 `;` 链命令，不要用 bash 的 `&&`。

### 2. 准备根目录 `.env`（必须先满足，否则不会成功写业务映射）

在**上述根目录**的 `.env` 中确认至少包含：

- `FEISHU_APP_ID`、`FEISHU_APP_SECRET`：非空，供获取 `tenant_access_token` 与建文件夹。
- `FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID`：**必须**，入轨时为该 `open_id` 加文件夹协作者；可选 `FEISHU_ONBOARD_FOLDER_DELEGATE_MEMBER_TYPE`（默认 `openid`）、`FEISHU_ONBOARD_FOLDER_DELEGATE_PERM`（默认 `full_access`）。
- 你将要填的 `dify_target_key` 所对应的 **完整** `DIFY_TARGET_<该大写键>_*` 组：实现会逐项检查该组键均非空（键名以仓库内 Dify/根 `.env` 合同 spec 为准）。

### 3. 准备 QA 规则文件（真实文件）

- 在仓库根下必须**已存在**该文件；输入的 `qa_rule_file` 与路径**逐字一致**（含大小写、正斜杠）。
- `qa_rule_file` 仅允许相对路径，且须以 `rules/` **或** `prompts/rules/` 开头，禁止 `..`、禁止绝对路径。例：`rules/qa/foo.md`、`prompts/rules/qa/folders/folder_rule_template.mdc`。
- 维护仓库可直接指向 `prompts/rules/` 模板，不必再复制到 `rules/`；执行工作区仍按 spec 在初始化时物化到 `rules/`（见主仓 spec §4.1、§5.3）。

### 4. 准备本机 `lark-cli`

- 须按飞书/团队文档**安装 lark-cli**，并保证在**用于运行本工具的环境**中可从 **PATH** 执行命令名 **`lark-cli`**。入轨与 `feishu_fetch` 均**不**读根 `.env` 的 `LARK_CLI_COMMAND`（已废弃）。不配置自定义可执行文件路径。子进程用 `shutil.which("lark-cli")` 解析（见 `lark_cli.py`）。
- 建议先执行 `lark-cli config init --help`，确认存在 **`--app-secret-stdin`**（与 spec 验收项一致）。若本机或 CI 的 PATH 未含 npm 全局 `bin` 目录，应在**该运行环境**配置 PATH，而不是在应用内写死可执行文件路径。

### 5. 可选：先跑单元测试（非真网，但可确认包未坏）

```powershell
cd path\to\NewVLA\onboard
.\.venv\Scripts\python.exe -m pytest tests -v
```

### 5.1 联调子命令 `verify-delegate`（真网）

在根 `.env` 已含 `FEISHU_APP_ID`、`FEISHU_APP_SECRET` 的前提下，可**不跑完整入轨**，仅验证「建临时文件夹 + `POST .../permissions/.../members?type=folder` 加用户协作者」是否与现场一致（与入轨里 `add_folder_user_collaborator` 同源）：

```powershell
# 建议在管线仓根执行，使默认识别到根目录 .env
feishu-onboard verify-delegate --open-id "ou_…"
```

常用可选参数：`--env-path`（显式指定 `.env`）、`--print-token`（成功时 stdout 打出完整 `folder_token`，勿写入公开日志）、`--member-type`、`--perm`、`--parent-folder-token`、`--name-prefix`。子命令会新建**带时间戳后缀的临时文件夹**，用于联调而非替代正式 `route_key` 入轨。

### 6. 启动交互式入轨

```powershell
# 已激活 venv 或 PATH 含 feishu-onboard 时：
feishu-onboard --help
feishu-onboard
```

- 需要**在已有** `FEISHU_FOLDER_<KEY>_TOKEN` 时**仍再建新文件夹**时，用：
  `feishu-onboard --force-new-folder`

### 7. 按提示逐项输入（回车可留空时以程序提示为准；下列为字段含义）

| 提示项 | 含义与注意 |
|--------|------------|
| `route_key` | 业务路由键，会转为**大写**，并用于 `FEISHU_FOLDER_<KEY>_` 等键名。须匹配 `^[A-Z][A-Z0-9_]*$`（首字符大写字母，其后大写字母/数字/下划线）。 |
| `folder_name` | 飞书侧新建文件夹显示名；若为空，实现里会落到默认名。 |
| `dify_target_key` | 与 `.env` 中 `DIFY_TARGET_<KEY>_` 那组的 `<KEY>` 一致（大写、同上字符集规则）。 |
| `dataset_id` | 该 route 命中的 Dify 数据集 ID，写入 `FEISHU_FOLDER_<KEY>_DATASET_ID`。 |
| `qa_rule_file` | 仅填相对路径，如 `rules/qa/your.md` 或 `prompts/rules/...`，且文件已在仓根下存在。 |
| `parent_folder_token` | **默认留空**（不填=在**企业租户**云空间根下建夹，与「共享文件夹在租户根」一致）。留空时由实现按飞书能力依次用 `create_folder`（空串/显式根 `token`）或 explorer 兜底；仅高级场景才填某父级 `token`。有值时须对该父级有建子项权限。 |

**续跑/冲突**：若该 `route_key` 在 `.env` 里**已有** `FEISHU_FOLDER_<KEY>_TOKEN` 且**未**使用 `--force-new-folder`，则当次输入的 `dify_target_key`、`dataset_id`、`qa_rule_file` 必须与已落盘值一致，否则直接失败（避免误覆盖）。

### 8. 执行过程中工具会做什么（便于你对照现象）

1. 校验输入与 `.env` 中 Dify 组、本地 `qa_rule_file` 指向的真实文件。
2. 若无 token 或带了 `--force-new-folder`：调飞书 API 建夹（父级留空时先取根目录元数据，见上表 `parent_folder_token`），并**阶段 A** 原子写入 `FEISHU_FOLDER_<KEY>_` 等键。
3. 为该文件夹调用 `POST .../permissions/.../members?type=folder` 加**分享委托人**协作者；失败不撤销已建夹，见主仓 spec。
4. 在**仓根**对 `lark-cli` 做 `config init`（`app_secret` 经 stdin，不出现在命令行参数）。
5. 仅当**加协作者成功**与 **`lark-cli`+校验**均成功时，**阶段 B** 写入/追加 `FEISHU_FOLDER_ROUTE_KEYS`（把本 `route_key` 登记进索引进而可进索引）。

### 9. 看结果：终端文案与退出码

- **0**：全成功，阶段 B 已写 `FEISHU_FOLDER_ROUTE_KEYS`。
- **2**：校验失败、飞书硬错误、与已有 route 冲突、缺少 `FEISHU_APP_ID`/`FEISHU_APP_SECRET`、缺少 `FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID` 等（未进入「部分成功」语义）。
- **3**：部分完成（常见：加协作者未成功，或 lark/校验未过）：阶段 A 可能已写入，但**未**写阶段 B 索引；可按 stderr 中的 `folder_token`/URL 在飞书侧补授权后**再跑**（具体以主仓 spec 为准）。
- **1**：Ctrl+C 或程序未捕获异常。

### 10. 人工核对清单

- 根 `.env`：新增或更新 `FEISHU_FOLDER_<KEY>_NAME`、`..._TOKEN`、`..._DIFY_TARGET_KEY`、`..._DATASET_ID`、`..._QA_RULE_FILE`；成功跑满时还有 `FEISHU_FOLDER_ROUTE_KEYS` 含该 KEY。
- 飞书：用浏览器打开工具给出的文件夹 URL，或到目标父目录下看到新夹。
- `lark-cli`：在仓根下 `lark config show`（或你们约定的校验方式）中 `appId` 与 `FEISHU_APP_ID` 一致，且**不要**把 `app_secret` 打到日志里。

### 11. 脱敏与排障

- 勿在录屏/公共日志中暴露 `FEISHU_APP_SECRET`、Dify `API_KEY`、`tenant_access_token`、完整 HTTP 体、lark 子进程 **stderr 全文**。
- 需要对外沟通时，可单独说明 `folder_token`、文件夹 URL 等；飞书限流/错误码见本文「限流与错误码」与主仓 spec §6.2。

## 运行

```powershell
feishu-onboard --help
feishu-onboard
```

（交互模式见上文「人工操作手册」。）

## 退出码

| 码 | 含义 |
|----|------|
| 0 | 全成功，阶段 B 已写入 `FEISHU_FOLDER_ROUTE_KEYS` |
| 2 | 参数/校验/硬失败或业务拒绝（不进入部分成功语义） |
| 3 | 部分完成：例如协作者未添加成功、lark 失败等，或阶段 A 已落盘但阶段 B 未写 |
| 1 | 未预期错误（如交互中断、未捕获异常） |

若父进程只接受 0/1，可在外层用脚本将 2/3 映射为所需行为。

## 前置条件

- `qa_rule_file` 在维护仓内可直接写 `prompts/rules/...`（文件须存在）；执行工作区侧仍须在初始化时物化 `rules/...`（见 `docs/superpowers/specs/2026-04-26-feishu-app-folder-onboard-design.md` §4.1、§5.3）。
- 根 `.env` 已含完整 `DIFY_TARGET_<KEY>_*` 静态组及 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`、**`FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID`** 等，键名以 spec §5 为准，并与同目录下 `2026-04-26-root-env-and-dify-target-contract-design.md` 的 webhook 侧约定可衔接。
- 本机已安装 `lark-cli`（或等效命令名），并支持以 stdin 传 `app_secret` 的 `config init` 子命令；实现默认调用名 `lark-cli`（见 `lark_cli.py`）。
- 若以 **非 editable** 方式安装、包落在 `site-packages` 中，**必须** 设置环境变量 `FEISHU_ONBOARD_REPO_ROOT` 为**绝对路径**的管线仓根，否则无法定位根目录 `.env`。

## 脱敏

勿把 `FEISHU_APP_SECRET`、`tenant_access_token`、Dify `API_KEY`、完整 HTTP 响应体及不可信子进程 **stderr 全文** 输出到未受控 stdout/持久化日志。终端交互场景下为排障可展示 `folder_token` 与 URL；录屏/CI 掩码见同 spec §7.1。

`lark-cli` 失败时仅依退出码与**可认为安全**的短消息提示；不假定 `stderr` 可原样回显。

## 限流与错误码（飞书）

以 [飞书开放平台](https://open.feishu.cn) 当时文档为准，常见参考：

- 应用权限：`auth/v3/tenant_access_token`（[文档入口](https://open.feishu.cn/document/ukTMukTMukTM/ukTMzUjLwMzM14SNyE3LTAj) 以平台为准）
- 根目录元数据（父级留空建夹前）：`GET .../drive/explorer/v2/root_folder/meta`
- 建目录：`POST .../drive/v1/files/create_folder`
- 企内/全员在飞书侧由人改「分享」；实现**不**调 `PATCH .../public`，只调一次 [增加协作者 / drive v1 / `type=folder`](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/drive-v1/permission-member/create)。根 `.env` **必须**含 **`FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID`**=用户 [open_id](https://open.feishu.cn)（`ou_…`），可选 **`FEISHU_ONBOARD_FOLDER_DELEGATE_MEMBER_TYPE`**、**`FEISHU_ONBOARD_FOLDER_DELEGATE_PERM`**（见 env 缺省）。`OnboardResult.public_ok` 仅表示协作者已加。`lark-cli` 的调用：入轨**只**用命令名 `lark-cli` + PATH（`lark_cli._resolve_lark_cli_exe`）。`feishu_fetch` 亦固定同命令名，**不**读已废弃的 `LARK_CLI_COMMAND`。见 `lark_cli.py`。

典型码（随官方可能调整）：`1061045`、`1062507`、`1063003` 等。详细表与重试见仓库内 `docs/superpowers/specs/2026-04-26-feishu-app-folder-onboard-design.md` **§6.2**。

### 分享委托人协作者（与实现一致，唯一路径）

1. 根 `.env` **必须** 配置 `FEISHU_ONBOARD_FOLDER_DELEGATE_OPEN_ID` 等，见上条。
2. 加协作者成功后，**分享委托人**在飞书客户端内把该文件夹的「分享」范围改为组织内/全员等。
3. 错误码 `1063002` 等见 [云文档常见问题 3](https://open.feishu.cn/document/ukTMukTMukTM/uczNzUjL3czM14yN3MTN#16c6475a)。

## 原子与权限（`.env`）

两阶段各一次同目录 `tmp` + `os.replace`；UTF-8 编码。Unix 临时文件模式 `0600`； Windows 为尽力缩小权限面，**以当前 OS 实际行为为准**（`chmod` 与 ACL 与 Unix 不完全等价）。

## 开发

```powershell
cd onboard
.\.venv\Scripts\python.exe -m pip install -e .[test]
.\.venv\Scripts\python.exe -m pytest tests -v
```

## Python 版本

`pyproject.toml` 中 `requires-python` 为 **>=3.10** 以便常见环境可跑测试；**实现计划**推荐 **3.12+** 为正式基线。若你使用 3.12+ 可在本地保持与 CI 一致。
