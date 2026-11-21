"""FEAT-344: tools/pc-runner/job_started.ps1, the PC runner's job-started hook, the lock no workflow edit reaches"""
import os
import shutil
import subprocess

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
HOOK = os.path.join(ROOT, "tools", "pc-runner", "job_started.ps1")
PS = shutil.which("powershell") or shutil.which("pwsh")
pytestmark = pytest.mark.skipif(not PS, reason="no PowerShell")

REPO = "drewkeriazes-personal/MapPacker-SnowboardAnywhere"
OK = {"GITHUB_REPOSITORY": REPO, "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REF": "refs/heads/main",
      "GITHUB_WORKFLOW_REF": f"{REPO}/.github/workflows/build-pack.yml@refs/heads/main",
      "GITHUB_ACTOR": "drewkeriazes", "GITHUB_TRIGGERING_ACTOR": "drewkeriazes", "GITHUB_HEAD_REF": ""}


def hook(tmp_path, env, maintainers="# who\ndrewkeriazes\n"):
    shutil.copy(HOOK, tmp_path / "job_started.ps1")
    if maintainers is not None:
        (tmp_path / "maintainers.txt").write_text(maintainers, encoding="utf-8")
    base = {k: v for k, v in os.environ.items() if not k.startswith("GITHUB_")}
    p = subprocess.run([PS, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-command",
                        f". '{tmp_path / 'job_started.ps1'}'"], env={**base, **env}, capture_output=True, text=True)
    return p.returncode, p.stdout


def test_a_maintainers_dispatch_of_build_pack_on_main_runs(tmp_path):
    code, out = hook(tmp_path, OK)
    assert code == 0, out
    assert hook(tmp_path, {**OK, "GITHUB_TRIGGERING_ACTOR": "github-actions[bot]"})[0] == 0     # FEAT-314 retry


@pytest.mark.parametrize("change, why", [
    ({"GITHUB_EVENT_NAME": "pull_request"}, "not workflow_dispatch"),
    ({"GITHUB_EVENT_NAME": "pull_request_target"}, "not workflow_dispatch"),
    ({"GITHUB_REF": "refs/pull/7/merge"}, "not refs/heads/main"),
    ({"GITHUB_WORKFLOW_REF": f"{REPO}/.github/workflows/checks.yml@refs/heads/main"}, "workflow is"),
    ({"GITHUB_WORKFLOW_REF": f"{REPO}/.github/workflows/build-pack.yml@refs/heads/x"}, "workflow is"),
    ({"GITHUB_REPOSITORY": "someone/fork"}, "repository is"),
    ({"GITHUB_HEAD_REF": "patch-1"}, "head ref"),
    ({"GITHUB_ACTOR": "someone", "GITHUB_TRIGGERING_ACTOR": "someone"}, "not a maintainer"),
    ({"GITHUB_TRIGGERING_ACTOR": "someone"}, "who re-ran it"),
    ({"GITHUB_ACTOR": "", "GITHUB_TRIGGERING_ACTOR": ""}, "not a maintainer"),
])
def test_anything_else_fails_before_a_step_runs(tmp_path, change, why):
    code, out = hook(tmp_path, {**OK, **change})
    assert code == 1 and why in out and "::error::" in out


def test_no_maintainers_list_lets_nothing_through(tmp_path):
    code, out = hook(tmp_path, OK, maintainers=None)
    assert code == 1 and "no maintainers" in out
