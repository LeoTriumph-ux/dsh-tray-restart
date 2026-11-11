# dsh-tray-restart - one-line uninstaller
#
# Usage (Windows PowerShell):
#   irm https://raw.githubusercontent.com/LeoTriumph-ux/dsh-tray-restart/main/uninstall.ps1 | iex

$ErrorActionPreference = "Stop"

# ============================================================ change this
$REPO = "LeoTriumph-ux/dsh-tray-restart"
# ============================================================

function Say($text, $color) {
    if ($color) { Write-Host $text -ForegroundColor $color } else { Write-Host $text }
}

Say ""
Say "  DeepSeek Harness - restore stock tray menu" "Cyan"
Say "  ------------------------------------------" "DarkGray"
Say ""

$harness = Join-Path $env:LOCALAPPDATA "Programs\DeepSeek Harness"
$exe = Join-Path $harness "DeepSeek Harness.exe"
if (-not (Test-Path $exe)) {
    Say "[x] DeepSeek Harness not found at: $harness" "Red"
    return
}

$running = @(Get-Process -Name "DeepSeek Harness" -ErrorAction SilentlyContinue)
if ($running.Count -gt 0) {
    Say "[!] Harness is running - app.asar is locked." "Yellow"
    Say "    Quit it from the tray menu, then run this again." "Yellow"
    Say ""
    return
}

$script = $null
if ($PSScriptRoot) {
    $candidate = Join-Path $PSScriptRoot "restore.py"
    if (Test-Path $candidate) { $script = $candidate }
}
if (-not $script) {
    $script = Join-Path $env:TEMP "dsh-tray-restart-restore.py"
    $url = "https://raw.githubusercontent.com/$REPO/main/restore.py"
    Say "[*] Downloading restore script..." "DarkGray"
    try {
        Invoke-WebRequest -Uri $url -OutFile $script -UseBasicParsing
    } catch {
        Say "[x] Download failed: $url" "Red"
        return
    }
}

$py = Join-Path $env:USERPROFILE ".dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if (-not (Test-Path $py)) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $py = $cmd.Source }
}
if (-not $py) {
    Say "[x] Python not found." "Red"
    return
}

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

Say ""
& $py $script
$code = $LASTEXITCODE

Say ""
if ($code -eq 0) {
    Say "Done." "Green"
} else {
    Say "Failed - see the messages above." "Red"
}
