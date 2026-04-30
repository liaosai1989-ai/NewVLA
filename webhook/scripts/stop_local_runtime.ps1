#Requires -Version 5.1
# Encoding: UTF-8
# Stop local FastAPI webhook + RQ worker for this pipeline (Windows taskkill helper).
# Matches by Win32_CommandLine so py.exe / python3.12.exe / venv python all get picked up.
param(
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Test-IsVlaWebhookUvicorn {
    param([string]$CommandLine)
    return $CommandLine -like "*uvicorn*webhook_cursor_executor.app:build_app*"
}

function Test-IsVlaDefaultRqWorker {
    param([string]$CommandLine)
    if ($CommandLine -notlike "*vla:default*") {
        return $false
    }
    # python -m rq.cli worker …  or  rq worker … (console script)
    if ($CommandLine -like "*rq.cli*worker*") {
        return $true
    }
    if ($CommandLine -like "*\rq.exe*worker*" -or $CommandLine -like "*\rq.EXE*worker*") {
        return $true
    }
    if ($CommandLine -like "*rq*worker*-w*SimpleWorker*") {
        return $true
    }
    return $false
}

$candidates = @(Get-CimInstance Win32_Process |
    Where-Object {
        $c = $_.CommandLine
        if (-not $c) {
            return $false
        }
        return (Test-IsVlaWebhookUvicorn -CommandLine $c) -or (Test-IsVlaDefaultRqWorker -CommandLine $c)
    } |
    Sort-Object ProcessId -Unique)

if (-not $candidates) {
    Write-Host "stop_local_runtime: no matching processes (uvicorn build_app or RQ vla:default)."
    exit 0
}

foreach ($p in $candidates) {
    $snippet = if ($p.CommandLine.Length -gt 120) {
        $p.CommandLine.Substring(0, 117) + "..."
    }
    else {
        $p.CommandLine
    }
    Write-Host ("stop_local_runtime: PID={0} Name={1}" -f $p.ProcessId, $p.Name)
    Write-Host ("  {0}" -f $snippet)
    if (-not $DryRun) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

if ($DryRun) {
    Write-Host "stop_local_runtime: DryRun set; no processes stopped."
}

exit 0
