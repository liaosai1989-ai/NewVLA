# Encoding: UTF-8
# bootstrap Task 14 — unattended acceptance gate (not human sign-off substitute)
# Python >= 3.12 (bootstrap/pyproject.toml). Default interpreter: resolve via `py -3.12` when `-PythonExe` omitted; override with -PythonExe if needed.
# -Workspace must satisfy spec §3.2 (ASCII segments, no spaces). Paths under dirs like "...\Cursor WorkSpace\..." FAIL validation—use e.g. $env:TEMP\...\folder.

param(
    [switch]$SkipDoctor,
    [string]$Workspace = "",
    [string]$CloneRoot = "",
    [string]$PythonExe = ""
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

& $PythonExe -m pip install -e ".\bootstrap[test]"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonExe -m bootstrap install-packages --clone-root $CloneRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PythonExe -m bootstrap materialize-workspace --workspace $Workspace --clone-root $CloneRoot --no-junction-tools --force
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

exit 0
