# Cloudflare Temp Tunnel Webhook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `c:\WorkPlace\NewVLA\test_tool` 生成一套最小联调脚本，安装 `cloudflared` 并把现有本地 `webhook` 服务暴露成临时公网 URL，供飞书事件订阅和 callback 测试。

**Architecture:** 复用现有 `webhook_cursor_executor.app:build_app` 作为本地 HTTP 服务，不改动业务逻辑。`test_tool` 只负责两件事：安装 `cloudflared`，以及启动本地 webhook + 临时 Cloudflare Tunnel 并输出完整回调 URL。为避免手工拼接路径，脚本从 `webhook` 模块读取默认回调路径 `/webhook/feishu`，并把 tunnel 日志落到 `test_tool\runtime\` 目录。

**Tech Stack:** PowerShell 5、`winget`、`cloudflared`、Python 3.13、`uv`、FastAPI、`uvicorn`

---

### Task 1: 让本地 webhook 可被脚本稳定启动

**Files:**
- Modify: `c:\WorkPlace\NewVLA\webhook\pyproject.toml`
- Test: `c:\WorkPlace\NewVLA\webhook\tests\test_app.py`

- [ ] **Step 1: 写失败测试，锁定默认 webhook path**

```python
def test_default_webhook_path_is_stable():
    settings = ExecutorSettings()
    assert settings.feishu_webhook_path == "/webhook/feishu"
```

- [ ] **Step 2: 运行测试，确认当前行为已被锁住**

Run: `python -m pytest webhook\tests\test_app.py -k default_webhook_path_is_stable -v`
Expected: `PASS`

- [ ] **Step 3: 补充本地启动所需依赖**

```toml
[project]
dependencies = [
  "fastapi>=0.115,<1.0",
  "redis>=6.0,<7.0",
  "rq>=2.2,<3.0",
  "pydantic>=2.11,<3.0",
  "pydantic-settings>=2.9,<3.0",
  "pycryptodome>=3.21,<4.0",
  "uvicorn>=0.34,<1.0"
]
```

- [ ] **Step 4: 运行聚焦测试，确认依赖改动没破坏应用**

Run: `python -m pytest webhook\tests\test_app.py -v`
Expected: all selected tests `PASS`

- [ ] **Step 5: 提交这一小步**

```bash
git add webhook/pyproject.toml webhook/tests/test_app.py
git commit -m "chore: add local webhook runner support"
```

### Task 2: 在 `test_tool` 生成安装与联调脚本

**Files:**
- Create: `c:\WorkPlace\NewVLA\test_tool\install_cloudflared.ps1`
- Create: `c:\WorkPlace\NewVLA\test_tool\start_temp_feishu_tunnel.ps1`
- Create: `c:\WorkPlace\NewVLA\test_tool\README.md`

- [ ] **Step 1: 先写脚本骨架，约束外部接口**

```powershell
param(
  [int]$Port = 8787
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\WorkPlace\NewVLA"
$WebhookRoot = Join-Path $ProjectRoot "webhook"
$RuntimeDir = Join-Path $ProjectRoot "test_tool\runtime"
$WebhookPath = "/webhook/feishu"
```

- [ ] **Step 2: 写 `install_cloudflared.ps1`，优先复用已有安装**

```powershell
$ErrorActionPreference = "Stop"

if (Get-Command cloudflared -ErrorAction SilentlyContinue) {
  $version = & cloudflared --version
  Write-Host "cloudflared already installed: $version"
  exit 0
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  throw "缺少 winget，无法自动安装 cloudflared。请先安装 App Installer。"
}

winget install --id Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
  throw "cloudflared 安装后仍不可用，请重新打开终端后再试。"
}

& cloudflared --version
```

- [ ] **Step 3: 写 `start_temp_feishu_tunnel.ps1`，自动启动 webhook 与 tunnel**

```powershell
param(
  [int]$Port = 8787
)

$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\WorkPlace\NewVLA"
$WebhookRoot = Join-Path $ProjectRoot "webhook"
$ToolRoot = Join-Path $ProjectRoot "test_tool"
$RuntimeDir = Join-Path $ToolRoot "runtime"
$WebhookPath = "/webhook/feishu"
$WebhookLog = Join-Path $RuntimeDir "webhook.log"
$TunnelLog = Join-Path $RuntimeDir "cloudflared.log"

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

if (-not (Test-Path (Join-Path $WebhookRoot ".venv\Scripts\python.exe"))) {
  Push-Location $WebhookRoot
  try {
    uv venv .venv --python 3.13
    uv pip install --python .\.venv\Scripts\python.exe -e .
  }
  finally {
    Pop-Location
  }
}

$webhookCmd = @"
Set-Location '$WebhookRoot'
`$env:FEISHU_ENCRYPT_KEY = ''
`$env:FEISHU_VERIFICATION_TOKEN = ''
`$env:FOLDER_ROUTES_FILE = '$WebhookRoot\config\folder_routes.example.json'
& '$WebhookRoot\.venv\Scripts\python.exe' -m uvicorn webhook_cursor_executor.app:build_app --factory --host 127.0.0.1 --port $Port *>> '$WebhookLog'
"@

$webhookProc = Start-Process powershell -ArgumentList @('-NoLogo','-NoProfile','-Command',$webhookCmd) -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 3

try {
  Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port$WebhookPath" -Method Post -ContentType "application/json" -Body '{"type":"url_verification","challenge":"ping"}' | Out-Null
}
catch {
  throw "本地 webhook 未成功启动，请查看 $WebhookLog"
}

$tunnelCmd = "cloudflared tunnel --url http://127.0.0.1:$Port *>> '$TunnelLog'"
$tunnelProc = Start-Process powershell -ArgumentList @('-NoLogo','-NoProfile','-Command',$tunnelCmd) -PassThru -WindowStyle Hidden

$publicBaseUrl = $null
for ($i = 0; $i -lt 30; $i++) {
  Start-Sleep -Seconds 1
  if (Test-Path $TunnelLog) {
    $match = Select-String -Path $TunnelLog -Pattern 'https://[-a-z0-9]+\.trycloudflare\.com' | Select-Object -First 1
    if ($match) {
      $publicBaseUrl = $match.Matches[0].Value
      break
    }
  }
}

if (-not $publicBaseUrl) {
  throw "未能从 cloudflared 日志中提取公网地址，请查看 $TunnelLog"
}

$callbackUrl = "$publicBaseUrl$WebhookPath"

[pscustomobject]@{
  webhook_pid = $webhookProc.Id
  tunnel_pid = $tunnelProc.Id
  webhook_url = "http://127.0.0.1:$Port$WebhookPath"
  callback_url = $callbackUrl
  webhook_log = $WebhookLog
  tunnel_log = $TunnelLog
} | ConvertTo-Json -Depth 3
```

- [ ] **Step 4: 写 README，告诉用户怎么拿飞书回调地址**

```markdown
# test_tool

## 目的

把本机 `webhook` 暴露为临时公网地址，供飞书事件订阅测试。

## 脚本

- `install_cloudflared.ps1`：安装或校验 `cloudflared`
- `start_temp_feishu_tunnel.ps1`：启动本地 webhook，并输出完整 callback URL

## 用法

```powershell
Set-Location c:\WorkPlace\NewVLA\test_tool
.\install_cloudflared.ps1
.\start_temp_feishu_tunnel.ps1
```

脚本会输出 JSON，其中 `callback_url` 就是飞书要填的地址。

## 注意

- 这是临时 `trycloudflare.com` 地址，每次重启可能变化
- 正式固定 URL 需要 Cloudflare 账号和已托管域名
```

- [ ] **Step 5: 运行脚本，确认能打印 callback URL**

Run: `powershell -ExecutionPolicy Bypass -File c:\WorkPlace\NewVLA\test_tool\start_temp_feishu_tunnel.ps1`
Expected: 输出 JSON，包含 `callback_url`、`webhook_pid`、`tunnel_pid`

- [ ] **Step 6: 提交这一小步**

```bash
git add test_tool/install_cloudflared.ps1 test_tool/start_temp_feishu_tunnel.ps1 test_tool/README.md
git commit -m "feat: add temporary cloudflare tunnel scripts"
```

### Task 3: 验证安装链路和脚本结果

**Files:**
- Modify: `c:\WorkPlace\NewVLA\test_tool\README.md`

- [ ] **Step 1: 安装 `cloudflared`**

Run: `powershell -ExecutionPolicy Bypass -File c:\WorkPlace\NewVLA\test_tool\install_cloudflared.ps1`
Expected: 输出 `cloudflared` 版本号

- [ ] **Step 2: 运行联调脚本**

Run: `powershell -ExecutionPolicy Bypass -File c:\WorkPlace\NewVLA\test_tool\start_temp_feishu_tunnel.ps1`
Expected: 输出如下结构的 JSON

```json
{
  "webhook_pid": 1234,
  "tunnel_pid": 5678,
  "webhook_url": "http://127.0.0.1:8787/webhook/feishu",
  "callback_url": "https://xxxx.trycloudflare.com/webhook/feishu",
  "webhook_log": "C:\\WorkPlace\\NewVLA\\test_tool\\runtime\\webhook.log",
  "tunnel_log": "C:\\WorkPlace\\NewVLA\\test_tool\\runtime\\cloudflared.log"
}
```

- [ ] **Step 3: 用 challenge 请求验证公网 URL 真能打到本地**

Run:

```powershell
$body = '{"type":"url_verification","challenge":"hello"}'
Invoke-WebRequest -UseBasicParsing -Uri "<callback_url>" -Method Post -ContentType "application/json" -Body $body
```

Expected: 响应正文包含 `{"challenge":"hello"}`

- [ ] **Step 4: 若日志或端口约束与实际不符，补充 README**

```markdown
## 故障排查

- 如果 `cloudflared` 命令不存在：重新开一个 PowerShell 窗口后再运行
- 如果脚本提示本地 webhook 未启动：查看 `runtime\webhook.log`
- 如果脚本拿不到公网地址：查看 `runtime\cloudflared.log`
```

- [ ] **Step 5: 重新跑一次文档中的命令，确认文档和脚本一致**

Run:

```powershell
Set-Location c:\WorkPlace\NewVLA\test_tool
.\install_cloudflared.ps1
.\start_temp_feishu_tunnel.ps1
```

Expected: 与 README 描述一致

- [ ] **Step 6: 提交最终验证**

```bash
git add test_tool/README.md
git commit -m "docs: document temporary tunnel workflow"
```
