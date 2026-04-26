$ErrorActionPreference = "Stop"

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

$cloudflaredExe = Resolve-CloudflaredExe
if ($cloudflaredExe) {
    & $cloudflaredExe --version
    exit 0
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget is required to install cloudflared automatically."
}

winget install --id Cloudflare.cloudflared --accept-source-agreements --accept-package-agreements

$cloudflaredExe = Resolve-CloudflaredExe
if (-not $cloudflaredExe) {
    throw "cloudflared was installed but no executable was found. Reopen PowerShell and retry."
}

& $cloudflaredExe --version
