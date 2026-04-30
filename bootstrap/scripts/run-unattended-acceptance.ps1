# Encoding: UTF-8
# bootstrap Task 14 — unattended acceptance gate (not human sign-off substitute)
# Python >= 3.12 (bootstrap/pyproject.toml). Default interpreter: resolve via `py -3.12` when `-PythonExe` omitted; override with -PythonExe if needed.
# -Workspace must satisfy spec §3.2 (ASCII segments, no spaces). Paths under dirs like "...\Cursor WorkSpace\..." FAIL validation—use e.g. $env:TEMP\...\folder.
#
# Frozen sequence (embedded-runtime plan Task 5): pip install bootstrap[test] -> (optional clone install-packages)
# -> materialize-workspace -> install-workspace-editables -> sample .env -> doctor -> probe
# Default SkipInstallPackages=$true: skips clone-side install-packages (avoids editable prefix clash with workspace doctor); use -SkipInstallPackages:$false to run it.

param(
    [switch]$SkipDoctor,
    [string]$Workspace = "",
    [string]$CloneRoot = "",
    [string]$PythonExe = "",
    [bool]$SkipInstallPackages = $true,
    [switch]$SkipProbe,
    [switch]$SkipProbeHttp
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $candidate = py -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) {
            $PythonExe = "$candidate".Trim()
        }
    }
    if ([string]::IsNullOrWhiteSpace($PythonExe)) {
        Write-Warning "Could not resolve Python 3.12 via py -3.12; using python.exe (must be >=3.12)."
        $PythonExe = "python"
    }
}
else {
    $PythonExe = $PythonExe.Trim()
}

if (-not $CloneRoot) {
    $CloneRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
else {
    $CloneRoot = (Resolve-Path $CloneRoot).Path
}

if (-not $Workspace) {
    if ($env:VLA_UNATTENDED_WORKSPACE -and $env:VLA_UNATTENDED_WORKSPACE.Trim()) {
        $Workspace = $env:VLA_UNATTENDED_WORKSPACE.Trim()
    }
    else {
        Write-Error "Specify -Workspace or set env:VLA_UNATTENDED_WORKSPACE"
        exit 1
    }
}

$Workspace = $Workspace.Trim()

Set-Location $CloneRoot

# BUG-007: install from inside bootstrap with "-e ." — not ".\bootstrap[test]" from clone root
# when paths contain spaces (pip file: dependency resolution).
Push-Location (Join-Path $CloneRoot "bootstrap")
try {
    & $PythonExe -m pip install -e ".[test]"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}

if (-not $SkipInstallPackages) {
    & $PythonExe -m bootstrap install-packages --clone-root $CloneRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $PythonExe -m bootstrap materialize-workspace --workspace $Workspace --clone-root $CloneRoot --force
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonExe -m bootstrap install-workspace-editables --workspace $Workspace
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$sample = Join-Path $CloneRoot "docs\superpowers\samples\pipeline-workspace-root.env.example"
if (-not (Test-Path -LiteralPath $sample)) {
    Write-Error "Missing sample env file: $sample"
    exit 1
}

$wsEnv = Join-Path $Workspace ".env"
Copy-Item -LiteralPath $sample -Destination $wsEnv -Force

if (-not $SkipDoctor) {
    & $PythonExe -m bootstrap doctor --workspace $Workspace --clone-root $CloneRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

if (-not $SkipProbe) {
    # Doctor runs above when -SkipDoctor is unset; probe only adds HTTP / no-http (+ optional RQ warn), not a second doctor.
    $probeArgs = @(
        "-m", "bootstrap", "probe",
        "--workspace", $Workspace,
        "--clone-root", $CloneRoot,
        "--skip-doctor"
    )
    if ($SkipProbeHttp) {
        $probeArgs += "--no-http"
    }
    & $PythonExe @probeArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

exit 0
