param(
    [int]$Port = 8787
)

$ErrorActionPreference = "Stop"

function Get-ProjectRoot {
    return Split-Path -Parent $PSScriptRoot
}

function Resolve-CloudflaredExe {
    $command = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidates = @(
        (Join-Path $env:ProgramFiles "cloudflared\cloudflared.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "cloudflared\cloudflared.exe"),
        (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\cloudflared.exe")
    ) | Where-Object { $_ }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $wingetRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path $wingetRoot) {
        $packageDir = Get-ChildItem -Path $wingetRoot -Directory -Filter "Cloudflare.cloudflared_*" |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($packageDir) {
            $exe = Get-ChildItem -Path $packageDir.FullName -Filter "cloudflared.exe" -File -Recurse |
                Select-Object -First 1
            if ($exe) {
                return $exe.FullName
            }
        }
    }

    return $null
}

function Get-PythonExe {
    $uvList = & uv python list
    if ($LASTEXITCODE -ne 0) {
        throw "uv python list failed."
    }

    $match = $uvList | Select-String -Pattern "cpython-3\.13\.\d+-windows-x86_64-none\s+([A-Z]:\\.+python\.exe)"
    if ($match) {
        return $match.Matches[0].Groups[1].Value
    }

    $fallback = $uvList | Select-String -Pattern "cpython-3\.\d+\.\d+-windows-x86_64-none\s+([A-Z]:\\.+python\.exe)" | Select-Object -First 1
    if ($fallback) {
        return $fallback.Matches[0].Groups[1].Value
    }

    throw "No usable Python interpreter was found."
}

function Ensure-Venv {
    param(
        [string]$WebhookRoot,
        [string]$PythonExe
    )

    $venvPython = Join-Path $WebhookRoot ".venv\Scripts\python.exe"
    Push-Location $WebhookRoot
    try {
        if (-not (Test-Path $venvPython)) {
            & uv venv .venv --python $PythonExe
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to create the webhook virtual environment."
            }
        }

        & uv pip install --python .\.venv\Scripts\python.exe -e .[test]
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install webhook dependencies."
        }
    }
    finally {
        Pop-Location
    }

    return $venvPython
}

function Wait-ForPublicUrl {
    param(
        [string]$TunnelLog
    )

    for ($i = 0; $i -lt 45; $i++) {
        Start-Sleep -Seconds 1
        if (-not (Test-Path $TunnelLog)) {
            continue
        }

        $match = Select-String -Path $TunnelLog -Pattern 'https://[-a-z0-9]+\.trycloudflare\.com' | Select-Object -First 1
        if ($match) {
            return $match.Matches[0].Value
        }
    }

    return $null
}

function Wait-ForLocalWebhook {
    param(
        [int]$Port,
        [string]$WebhookPath,
        [string]$VerificationToken
    )

    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Seconds 1
        try {
            $body = (@{
                type = "url_verification"
                challenge = "health-check"
                token = $VerificationToken
            } | ConvertTo-Json -Compress)
            $response = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}{1}" -f $Port, $WebhookPath) -Method Post -ContentType "application/json" -Body $body
            if ($response.challenge -eq "health-check") {
                return $true
            }
        }
        catch {
        }
    }

    return $false
}

function Stop-ExistingWebhookProcesses {
    # Match by command line only: uvicorn may run under python.exe, python3.12.exe,
    # py.exe (launcher), or venv\Scripts\python.exe — Name-only filter misses duplicates.
    $existing = Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -like "*uvicorn webhook_cursor_executor.app:build_app*"
        } |
        Select-Object -ExpandProperty ProcessId

    foreach ($processId in ($existing | Select-Object -Unique)) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }

    if ($existing) {
        Start-Sleep -Seconds 1
    }
}

function Start-TunnelProcess {
    param(
        [string]$CloudflaredExe,
        [int]$Port,
        [string]$ToolRoot,
        [string]$TunnelLog,
        [string]$TunnelErrLog
    )

    @("", "") | Set-Content -Path $TunnelLog -Encoding utf8
    @("", "") | Set-Content -Path $TunnelErrLog -Encoding utf8

    return Start-Process -FilePath $CloudflaredExe `
        -ArgumentList @("tunnel", "--url", "http://127.0.0.1:$Port") `
        -WorkingDirectory $ToolRoot `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $TunnelLog `
        -RedirectStandardError $TunnelErrLog
}

$projectRoot = Get-ProjectRoot
$toolRoot = Join-Path $projectRoot "test_tool"
$runtimeDir = Join-Path $toolRoot "runtime"
$webhookRoot = Join-Path $projectRoot "webhook"
$webhookLog = Join-Path $runtimeDir "webhook.log"
$webhookErrLog = Join-Path $runtimeDir "webhook.err.log"
$tunnelLog = Join-Path $runtimeDir "cloudflared.log"
$tunnelErrLog = Join-Path $runtimeDir "cloudflared.err.log"
$statusFile = Join-Path $runtimeDir "last_tunnel.json"

New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
Stop-ExistingWebhookProcesses

@("", "") | Set-Content -Path $webhookLog -Encoding utf8
@("", "") | Set-Content -Path $webhookErrLog -Encoding utf8
@("", "") | Set-Content -Path $tunnelLog -Encoding utf8
@("", "") | Set-Content -Path $tunnelErrLog -Encoding utf8

$cloudflaredExe = Resolve-CloudflaredExe
if (-not $cloudflaredExe) {
    throw "cloudflared was not found. Run test_tool\\install_cloudflared.ps1 first."
}

$pythonExe = Get-PythonExe
$venvPython = Ensure-Venv -WebhookRoot $webhookRoot -PythonExe $pythonExe

# Folder 路由首选执行工作区根 .env：`FEISHU_FOLDER_ROUTE_KEYS` + 每组 `FEISHU_FOLDER_<KEY>_*`（含 NAME，五键）。
# Legacy：`FEISHU_FOLDER_ROUTE_KEYS` 留空时使用 `FOLDER_ROUTES_FILE` JSON；下方为该键注入占位，勿当作生产真源优先级。
$settingsJson = & $venvPython -c "from webhook_cursor_executor.settings import get_executor_settings; import json; s=get_executor_settings(); print(json.dumps({'path': s.feishu_webhook_path, 'routes_file': s.folder_routes_file, 'verification_token': s.feishu_verification_token}, ensure_ascii=False))"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to read webhook settings."
}

$settings = $settingsJson | ConvertFrom-Json
$webhookPath = [string]$settings.path
$routesFile = [string]$settings.routes_file
$verificationToken = [string]$settings.verification_token

$webhookCommand = @"
`$env:FOLDER_ROUTES_FILE = '$routesFile'
Set-Location '$webhookRoot'
& '$venvPython' -m uvicorn webhook_cursor_executor.app:build_app --factory --host 127.0.0.1 --port $Port
"@

$webhookProc = Start-Process -FilePath "powershell" `
    -ArgumentList @(
        "-NoLogo",
        "-NoProfile",
        "-Command",
        $webhookCommand
    ) `
    -WorkingDirectory $webhookRoot `
    -PassThru `
    -WindowStyle Hidden `
    -RedirectStandardOutput $webhookLog `
    -RedirectStandardError $webhookErrLog

if (-not (Wait-ForLocalWebhook -Port $Port -WebhookPath $webhookPath -VerificationToken $verificationToken)) {
    throw "Local webhook did not start correctly. Check $webhookLog"
}

$tunnelProc = $null
$publicBaseUrl = $null
for ($attempt = 1; $attempt -le 3; $attempt++) {
    $tunnelProc = Start-TunnelProcess `
        -CloudflaredExe $cloudflaredExe `
        -Port $Port `
        -ToolRoot $toolRoot `
        -TunnelLog $tunnelLog `
        -TunnelErrLog $tunnelErrLog

    $publicBaseUrl = Wait-ForPublicUrl -TunnelLog $tunnelLog
    if ($publicBaseUrl) {
        break
    }

    Stop-Process -Id $tunnelProc.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

if (-not $publicBaseUrl) {
    throw "Could not extract a public URL from cloudflared logs after retries. Check $tunnelErrLog"
}

$callbackUrl = "{0}{1}" -f $publicBaseUrl, $webhookPath
$result = [pscustomobject]@{
    webhook_pid = $webhookProc.Id
    tunnel_pid = $tunnelProc.Id
    webhook_url = "http://127.0.0.1:$Port$webhookPath"
    callback_url = $callbackUrl
    webhook_log = $webhookLog
    tunnel_log = $tunnelLog
    webhook_err_log = $webhookErrLog
    tunnel_err_log = $tunnelErrLog
}

$result | ConvertTo-Json -Depth 3 | Set-Content -Path $statusFile -Encoding utf8
$result | ConvertTo-Json -Depth 3
