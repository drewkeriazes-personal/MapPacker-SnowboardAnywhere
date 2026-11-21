# FEAT-344: the job-started hook of the self-hosted runner on Drew's PC (ACTIONS_RUNNER_HOOK_JOB_STARTED in the
# runner's .env; docs/pc-runner.md). The runner runs it before every job it takes, and a non-zero exit fails the
# job before any of its steps run.
#
# The repo is public, so this is the lock no pull request can open: build-pack.yml's own checks (the where step,
# the build job's `if:`) live in a workflow file, and a fork PR or a branch can edit a workflow file to ask for the
# sba-pc label. This copy lives outside every checkout (install_hook.ps1 copies it with main's maintainers.txt), so
# only Drew changes it. It lets through one thing: Build pack, from main, dispatched by a maintainer (or re-run by
# build-pack-retry.yml as github-actions[bot] for a run a maintainer started, FEAT-314).
#
# Test it: powershell -File job_started.ps1 with the GITHUB_* variables set (pipeline/tests/test_pc_runner.py).

$repo = 'drewkeriazes-personal/MapPacker-SnowboardAnywhere'
$workflowRef = "$repo/.github/workflows/build-pack.yml@refs/heads/main"
$retryBot = 'github-actions[bot]'

$here = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$listPath = Join-Path $here 'maintainers.txt'
$trusted = @()
if (Test-Path -LiteralPath $listPath) {
    $trusted = @(Get-Content -LiteralPath $listPath | ForEach-Object { ($_ -split '#')[0].Trim() } | Where-Object { $_ })
}

$actor = "$env:GITHUB_ACTOR"
$by = if ($env:GITHUB_TRIGGERING_ACTOR) { "$env:GITHUB_TRIGGERING_ACTOR" } else { $actor }
$why = @()
if ($trusted.Count -eq 0) { $why += "no maintainers in $listPath (install_hook.ps1 copies main's .github/maintainers.txt)" }
if ("$env:GITHUB_REPOSITORY" -cne $repo) { $why += "repository is '$env:GITHUB_REPOSITORY', not $repo" }
if ("$env:GITHUB_EVENT_NAME" -cne 'workflow_dispatch') { $why += "event is '$env:GITHUB_EVENT_NAME', not workflow_dispatch" }
if ("$env:GITHUB_REF" -cne 'refs/heads/main') { $why += "ref is '$env:GITHUB_REF', not refs/heads/main" }
if ("$env:GITHUB_WORKFLOW_REF" -cne $workflowRef) { $why += "workflow is '$env:GITHUB_WORKFLOW_REF', not $workflowRef" }
if ("$env:GITHUB_HEAD_REF") { $why += "the run has a head ref ('$env:GITHUB_HEAD_REF'): pull request code" }
if (-not $actor -or ($trusted -cnotcontains $actor)) { $why += "actor '$actor' is not a maintainer" }
if ($by -cne $actor -and $by -cne $retryBot -and ($trusted -cnotcontains $by)) { $why += "'$by' (who re-ran it) is not a maintainer" }

if ($why.Count -gt 0) {
    Write-Output "::error::This runner (Drew's PC, FEAT-344) takes only Build pack from main, dispatched by a maintainer. Refused:"
    $why | ForEach-Object { Write-Output "  - $_" }
    exit 1
}
Write-Output "Drew's PC runner: $workflowRef dispatched by $actor, allowed"
exit 0
