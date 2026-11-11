# dsh-tray-restart - one-line installer
#
# Usage (Windows PowerShell):
#   irm https://raw.githubusercontent.com/LeoTriumph-ux/dsh-tray-restart/main/install.ps1 | iex
#
# It does three things: locate Harness, fetch patch.py, run it with the Python
# that ships inside Harness. No extra runtime, no system changes.
#
# NOTE: this file is intentionally ASCII-only. PowerShell 5.1 reads BOM-less
# scripts as ANSI, so any non-ASCII here would corrupt the whole file.

$ErrorActionPreference = "Stop"

# ============================================================ change this
$REPO = "LeoTriumph-ux/dsh-tray-restart"
# ============================================================

function Say($text, $color) {
    if ($color) { Write-Host $text -ForegroundColor $color } else { Write-Host $text }
}

Say ""
Say "  DeepSeek Harness - tray restart patch" "Cyan"
Say "  ------------------------------------" "DarkGray"
Say ""

# ---------------------------------------------------------------- 1. locate
$harness = Join-Path $env:LOCALAPPDATA "Programs\DeepSeek Harness"
$exe = Join-Path $harness "DeepSeek Harness.exe"
if (-not (Test-Path $exe)) {
    Say "[x] DeepSeek Harness not found at:" "Red"
    Say "    $harness" "DarkGray"
    Say "    If it lives elsewhere, download patch.py and run it directly:" "DarkGray"
    Say "    python patch.py `"D:\path\to\resources\app.asar`"" "DarkGray"
    return
}
Say "[*] Harness: $harness" "DarkGray"

# ---------------------------------------------------------------- 2. not running
$running = @(Get-Process -Name "DeepSeek Harness" -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    Say ""
    Say "[!] Harness is running - app.asar is locked." "Yellow"
    Say "    Quit it from the tray menu, then run this command again." "Yellow"
    Say ""
    return
}

# ---------------------------------------------------------------- 3. get patch.py
$patch = $null
if ($PSScriptRoot) {
    $candidate = Join-Path $PSScriptRoot "patch.py"
    if (Test-Path $candidate) { $patch = $candidate }
}
if (-not $patch) {
    $patch = Join-Path $env:TEMP "dsh-tray-restart-patch.py"
    $url = "https://raw.githubusercontent.com/$REPO/main/patch.py"
    Say "[*] Downloading patch script..." "DarkGray"
    try {
        Invoke-WebRequest -Uri $url -OutFile $patch -UseBasicParsing
    } catch {
        Say "[x] Download failed: $url" "Red"
        Say "    Check your network, or that the repo path is right." "DarkGray"
        return
    }
}

# ---------------------------------------------------------------- 4. find python
# Prefer the one bundled with Harness - if Harness is installed, it is there.
$py = Join-Path $env:USERPROFILE ".dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $py)) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $py = $cmd.Source }
}
if (-not $py) {
    Say "[x] Python not found." "Red"
    Say "    Harness normally ships one; its runtime layout may have changed." "DarkGray"
    Say "    Workaround: install Python, then run patch.py manually." "DarkGray"
    return
}
Say "[*] Python: $py" "DarkGray"

# make sure Python's output renders correctly in this console
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

# ---------------------------------------------------------------- 5. patch
Say ""
& $py $patch
$code = $LASTEXITCODE

Say ""
if ($code -eq 0) {
    Say "Done. Open DeepSeek Harness and right-click the tray icon." "Green"
} else {
    Say "Failed - see the messages above." "Red"
}
