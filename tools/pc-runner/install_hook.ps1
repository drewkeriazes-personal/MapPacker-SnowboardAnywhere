# FEAT-344: set up the self-hosted runner on Drew's PC for Build pack, after config.cmd has registered it
# (docs/pc-runner.md has every step; this does steps 4 and 5). It never registers a runner and never touches the
# repo's settings or secrets.
#
#   powershell -ExecutionPolicy Bypass -File tools\pc-runner\install_hook.ps1 [-RunnerDir C:\actions-runner]
#       [-HookDir C:\sba-runner-hook] [-RawRoots <root>;<root>] [-IndexDir <folder>]
#
# - copies job_started.ps1 and main's .github/maintainers.txt to HookDir, outside the runner folder (GitHub's rule
#   for hook scripts) and outside every checkout, so no PR can change the lock
# - writes into <RunnerDir>\.env: ACTIONS_RUNNER_HOOK_JOB_STARTED (the hook), SBA_RAW_ROOTS (the raw roots, the
#   first the default for a new resort; build_pack_ci.py pc-setup picks the one that holds a resort's data) and
#   SBA_INDEX_DIR (the OpenSkiData index, one copy whichever root a resort is in). Other lines are kept.
# Re-run it after .github/maintainers.txt changes on main, and with -RawRoots / -IndexDir when a raw folder moves.
# Restart the runner after (it reads .env at start).
param(
    [string]$RunnerDir = 'C:\actions-runner',
    [string]$HookDir = 'C:\sba-runner-hook',
    [string]$RawRoots = 'C:\Users\Drew\Documents\snowboard-sim\raw',
    [string]$IndexDir = 'C:\Users\Drew\Documents\snowboard-sim\raw\_index'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$runnerFull = [System.IO.Path]::GetFullPath($RunnerDir).TrimEnd('\') + '\'
$hookFull = [System.IO.Path]::GetFullPath($HookDir).TrimEnd('\') + '\'
if (-not (Test-Path -LiteralPath (Join-Path $RunnerDir 'config.cmd'))) {
    throw "no runner at $RunnerDir (config.cmd): download and register it first (docs/pc-runner.md steps 1 to 3)"
}
if ($hookFull.StartsWith($runnerFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "HookDir $HookDir is inside the runner folder: GitHub says hook scripts must live outside it"
}
$probe = $HookDir
while ($probe -and -not (Test-Path -LiteralPath $probe)) { $probe = Split-Path -Parent $probe }
for ($d = $probe; $d; $d = Split-Path -Parent $d) {
    if (Test-Path -LiteralPath (Join-Path $d '.git')) { throw "HookDir $HookDir is inside the git checkout ${d}: pick a folder no checkout holds" }
}

# main's maintainers, not a branch's
& git -C $repoRoot fetch -q origin main
if ($LASTEXITCODE -ne 0) { throw "git fetch origin main failed in $repoRoot" }
$maintainers = & git -C $repoRoot show origin/main:.github/maintainers.txt
if ($LASTEXITCODE -ne 0) { throw "no .github/maintainers.txt on origin/main" }

New-Item -ItemType Directory -Force -Path $HookDir | Out-Null
$hookSrc = & git -C $repoRoot show origin/main:tools/pc-runner/job_started.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Warning "tools/pc-runner/job_started.ps1 is not on origin/main yet: copying this checkout's"
    $hookSrc = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'job_started.ps1')
}
Set-Content -LiteralPath (Join-Path $HookDir 'job_started.ps1') -Value $hookSrc -Encoding UTF8
Set-Content -LiteralPath (Join-Path $HookDir 'maintainers.txt') -Value $maintainers -Encoding UTF8

# Build pack's shell steps run `bash`; Git for Windows puts git.exe on PATH but not its bash unless Git\bin is added
$bash = Get-Command bash -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $bash) {
    Write-Warning "bash is not on PATH, so Build pack fails at its first shell step: add Git for Windows' bin folder (C:\Program Files\Git\bin) to PATH, then restart the runner"
} elseif ($bash.Source -like "$env:SystemRoot\*") {
    Write-Warning "bash on PATH is $($bash.Source) (WSL), not Git for Windows' bash: put C:\Program Files\Git\bin ahead of it in PATH, then restart the runner"
}

foreach ($r in $RawRoots.Split(';')) {
    if ($r.Trim() -and -not (Test-Path -LiteralPath $r.Trim())) { Write-Warning "raw root $r is not a folder" }
}
$want = [ordered]@{
    'ACTIONS_RUNNER_HOOK_JOB_STARTED' = (Join-Path $HookDir 'job_started.ps1')
    'SBA_RAW_ROOTS' = $RawRoots
    'SBA_INDEX_DIR' = $IndexDir
}
$envPath = Join-Path $RunnerDir '.env'
$lines = @()
if (Test-Path -LiteralPath $envPath) {
    $lines = @(Get-Content -LiteralPath $envPath | Where-Object { $want.Keys -notcontains ($_ -split '=', 2)[0] })
}
$lines += $want.Keys | ForEach-Object { "$_=$($want[$_])" }
# no BOM: the runner reads .env as plain KEY=VALUE lines
[System.IO.File]::WriteAllLines($envPath, [string[]]$lines, (New-Object System.Text.UTF8Encoding($false)))

Write-Output "hook:  $(Join-Path $HookDir 'job_started.ps1') (maintainers: $((($maintainers | ForEach-Object { ($_ -split '#')[0].Trim() }) | Where-Object { $_ }) -join ', '))"
Write-Output ".env:  $envPath"
$want.Keys | ForEach-Object { Write-Output "       $_=$($want[$_])" }
Write-Output "Restart the runner (close its window, run.cmd again) so it reads .env."
