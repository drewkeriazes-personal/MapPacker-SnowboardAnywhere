# Build pack on Drew's PC (FEAT-344)

Some packs can't be built on the free GitHub runner (about 14 GB of disk, 16 GB of RAM, 6 hours a job): Vail
today, and any resort whose menu still and ghost takes need the GPU (the attract stage, FEAT-343). `build-pack.yml`
can run its `build` job on a self-hosted runner on Drew's PC instead:

```
gh workflow run build-pack.yml -f rebuild=vail -f build_on=pc
```

or in the Actions tab: **Build pack > Run workflow**, pick the pack, set **Where the build runs** to `pc`. The run
is the same run as a cloud build (the `queue` and `probe` jobs on the free runner, the `build` job with its stage
steps, the same publish PR, the `outcome` job), so the game's build progress and the failure metrics read it as
usual. On the PC the build job:

- checks out this repo's `main` (as in the cloud) and the game's `main` into `sba-game/` in the job's folder, then
  `npm ci` and the Playwright Chromium there. The attract and spots stages (`build_resort.py`, the game's
  `tools/auto_attract.mjs` and `tools/propose_spots.py`) run against that checkout, on the GPU, instead of
  skipping. Drew's own game checkout, which may be on any branch, is never used. Proposed compare spots (only for a
  resort with none on the game's `main`) are uploaded as the `compare-spots-<attempt>` artifact, to add to the
  game's `docs/compare/<slug>/` with their Street View links.
- uses the PC's own `python` (the packages `pipeline/requirements.txt` lists are already installed; the step
  installs only what is missing) and node, and Git for Windows' bash for the shell steps. That bash must be on the runner's PATH
  (`C:\Program Files\Git\bin`; Git's installer adds only `Git\cmd` by default), or the first shell step fails with
  `bash: command not found`; `install_hook.ps1` warns when it isn't.
- builds on the raw data already on the PC: `build_pack_ci.py pc-setup` picks, from the runner's `SBA_RAW_ROOTS`,
  the root that already holds most of the resort's raw layers (Vail's full set is in
  `C:\Users\Drew\Documents\snowboard-sim\raw`, the rest in `C:\Users\Drew\git\SnowboardAnywhere\raw`) and sets
  `SBA_RAW_ROOT` to it. The fetch stage then skips what `build_resort.json` says is done and downloads only what is
  missing, as on Drew's own builds. A resort whose `raw_from` or relocate source is only in another root is refused
  (the fetch would download that one again): move one so they share a root. The OpenSkiData index stays in one
  place (`SBA_INDEX_DIR`). The build stage itself builds again into the job's `packs/<slug>/` (a different pack
  folder from Drew's checkout, so his next local build of that resort builds again too).
- publishes with the App token as in the cloud. The publish step gives git a global config of its own
  (`GIT_CONFIG_GLOBAL` in the job's temp folder), so Drew's global git config is left alone and his stored
  credential never pushes in place of the App.

The job may take 24 hours (`timeout-minutes` 1440; the free runner's 350 stays for the cloud).

## Security: a public repo and a runner on Drew's PC

GitHub's guidance is that self-hosted runners should almost never be used with public repositories, because anyone
can open a pull request, and a runner can be persistently compromised by untrusted code in a workflow. A fork pull
request runs the PR's own version of a workflow file, so it could edit a workflow to ask for the `sba-pc` label.
The runner therefore only ever runs Build pack, from `main`, dispatched by a maintainer, behind three locks:

1. **The `where` step** (probe job, `build_pack_ci.py where`) refuses `build_on: pc` unless the run is a
   `workflow_dispatch` on `refs/heads/main` whose actor is in `.github/maintainers.txt` (a re-run by
   `build-pack-retry.yml`, FEAT-314, comes from `github-actions[bot]` for a run a maintainer started, and is let
   through). Only then is the probe job's `runner` output `pc`.
2. **The build job's `if:`** takes the PC only for `runner == 'pc'` and a `workflow_dispatch` on
   `refs/heads/main`. The workflow has no other trigger.
3. **The runner's job-started hook** (`tools/pc-runner/job_started.ps1`, run by the runner before every job, a
   non-zero exit fails the job before any step runs) checks the repository, the event, the ref,
   `GITHUB_WORKFLOW_REF` (`.../build-pack.yml@refs/heads/main`), that there is no head ref (no PR), and that the
   actor is in its copy of `maintainers.txt`. It lives outside every checkout (`C:\sba-runner-hook\`), so no PR or
   branch can change it. Locks 1 and 2 are in a workflow file and hold for `main`'s copy; lock 3 is the one that
   stops a fork PR or a branch that edits a workflow.

And the repo settings below: fork PR workflows wait for approval, and the runner is registered on this repository
only.

## Drew's steps (once)

Nothing here is done by a PR; each step is Drew's, on his PC or in the repo's settings.

1. **Repo settings** (Settings > Actions > General, drewkeriazes-personal/MapPacker-SnowboardAnywhere):
   - *Approval for running fork pull request workflows from contributors*: **Require approval for all external
     contributors**. Never approve a fork PR's run that changes `.github/workflows/` without reading it (the hook
     refuses it anyway; this keeps it from reaching the runner at all).
   - *Workflow permissions*: keep **Read repository contents** (the default; the workflows ask for more per job).
   - Register the runner on this repository (below), not in the organization's runner group: an org runner in the
     Default group would be offered to the org's other repositories too, and a public repo can use it only after
     the group's "allow public repositories" override, which stays off.
2. **Download the runner.** Settings > Actions > Runners > **New self-hosted runner**, Windows x64. Run its
   *Download* commands in PowerShell in `C:\actions-runner` (outside every checkout, a short path), checking the
   sha256 it shows.
3. **Register it.** The page's token lasts an hour; or make one with
   `gh api -X POST repos/drewkeriazes-personal/MapPacker-SnowboardAnywhere/actions/runners/registration-token --jq .token`.
   Then, in `C:\actions-runner`:

   ```
   .\config.cmd --url https://github.com/drewkeriazes-personal/MapPacker-SnowboardAnywhere --token <token> --name sba-pc --labels sba-pc --work _work --unattended
   ```

   Do **not** add `--runasservice`: a service runs in Windows' session 0, without Drew's desktop, and the attract
   stage's Chrome needs the GPU his own builds use. The runner runs as Drew, in his session (step 6).
4. **Install the hook and the runner's environment.** From the MapPacker main checkout, once this PR is merged:

   ```
   powershell -ExecutionPolicy Bypass -File tools\pc-runner\install_hook.ps1
   ```

   It copies `job_started.ps1` and `main`'s `.github/maintainers.txt` to `C:\sba-runner-hook\` and writes
   `C:\actions-runner\.env`:

   ```
   ACTIONS_RUNNER_HOOK_JOB_STARTED=C:\sba-runner-hook\job_started.ps1
   SBA_RAW_ROOTS=C:\Users\Drew\git\SnowboardAnywhere\raw;C:\Users\Drew\Documents\snowboard-sim\raw
   SBA_INDEX_DIR=C:\Users\Drew\git\SnowboardAnywhere\raw\_index
   ```

   (`-RunnerDir`, `-HookDir`, `-RawRoots`, `-IndexDir` change them; the first raw root is where a new resort's data
   goes.) Run it again whenever `.github/maintainers.txt` changes on `main`.
5. **Secrets:** the fetch step already gets `LANDFIRE_EMAIL` and the publish step the App's secrets, environment secrets of `publish` that only a job on `main` can read (BUG-113, README, "The publish environment"). For Refresh packs to start PC builds, add `PC_DISPATCH_TOKEN` there too (below, "The dispatch token").
6. **Start it** in Drew's session: `C:\actions-runner\run.cmd` (a console window; closing it takes the runner
   offline). To start it at every logon:

   ```
   schtasks /Create /TN "SBA runner" /TR "C:\actions-runner\run.cmd" /SC ONLOGON /RL LIMITED
   ```

   Settings > Actions > Runners then shows `sba-pc` Idle, with the labels `self-hosted`, `Windows`, `X64`, `sba-pc`.
7. **First run:** `gh workflow run build-pack.yml -f rebuild=vail -f build_on=pc` (it publishes, like any Build
   pack run). The build job's log starts with the hook's "Drew's PC runner: ... allowed" line; the attract step's
   log names the renderer, which must be the GPU, not SwiftShader.

To take the PC out: close `run.cmd` (runs then wait for it, below), or remove it for good with
`.\config.cmd remove --token <removal token>` (Settings > Actions > Runners > sba-pc > Remove).

## The queue: the PC has no cloud slot

The PC is one runner, so GitHub itself runs its jobs one at a time, and a job waits in GitHub's queue while the PC
is busy or offline, for at most 24 hours before it fails. `wait_turn.py` (the `queue` job, then "still my turn" in
the build job) therefore leaves the PC out of `BUILD_SLOTS`: a PC run (`build_on: pc`) never waits there, and a
cloud run does not count the runs ahead of it whose `build` job is on the PC (the job's labels name `sba-pc`, read
from the run's jobs). A run whose build job does not exist yet (its queue and probe jobs, a few minutes) or whose
jobs can't be read still counts, so the error is always toward waiting. So a PC build waiting for an offline PC
holds no cloud build back.

What that gives up: a PC build and a cloud build of the same resort can now run at the same time (Refresh packs
never starts both: a pack goes to one or the other by its `runner.json`; only two hand-started runs can).
`publish_pack.py` then publishes the second only when its content differs from the first's publish PR.

## Refresh packs and the PC

Refresh packs (`refresh-packs.yml`, README > Refresh packs) picks a pack whose `resorts/<slug>/runner.json` says
`{"cloud": false, "reason": "too_big"}` (Vail) by the same rules as the rest (behind `main` in a path its build
reads, or every pack in `all` mode), and sends it to the PC instead of leaving it out. *list only* shows it as
"would go to Drew's PC". The PC's locks take only a maintainer's dispatch, and the refresh job's own starts are
`github-actions[bot]`'s, so the refresh job does not start these: it hands their slugs to a second job, `pc`, which
starts each with Drew's token (below):

```
build-pack.yml on main: slug=<slug>, build_on=pc, requested_by=refresh-packs, refresh_run=<the refresh run's id>
```

The build's actor is then Drew, so all three locks let it through (no lock changed), `publish_pack.py` labels its
publish PR `automerge` as his, and `publish_merge.py` trusts the label through `build_run_actor` (a run on `main`
whose triggering actor is a maintainer). The `Refresh:` time window (`REFRESH_SLACK_S`) is not needed for it, so a
PC build that waited hours in the queue still merges itself. Its publish PR names the refresh run (`Refresh:`) like
a cloud build's.

The `pc` job's summary, "Refresh packs: Drew's PC", has a row per pack: "building on Drew's PC" with a link to the
Build pack run, or "queued: PC runner offline" (also linked: the build waits in GitHub's queue until the PC is back,
24 hours at most). The runner's status comes from `GET /repos/{repo}/actions/runners` with the same token, which
needs **Administration: read**; without it the line above the table says the status is not readable and the rows
say "building". When the token is missing or GitHub refuses it, the summary says so, each row says "not started"
with the command for a hand build, and the job fails:

```
gh workflow run build-pack.yml -f slug=vail -f build_on=pc
```

## The dispatch token

`PC_DISPATCH_TOKEN` is a fine-grained personal access token on Drew's account, with access to this repository
only and the permission **Actions: read and write** (and, optional, **Administration: read**, only so the summary
can say whether `sba-pc` is online). It is an environment secret of `publish` (deployment branches: `main` only,
BUG-113), and only the one step "start on Drew's PC" in Refresh packs' `pc` job names it; that job runs nothing but
`refresh_packs.py --start-pc` on `main`'s checkout, with the slugs the refresh job picked, each checked again
against its `runner.json`. Everything else keeps the workflow token. With it, a holder could start or cancel any
workflow run here as Drew, which is why it stays out of every other job.

It expires (fine-grained tokens have an expiry date, a year at most). After that, the `pc` job's start fails with
HTTP 401: the summary says GitHub refused the token, the PC packs are not built, and the job is red; cloud packs
are not affected. To rotate it: github.com > Settings > Developer settings > Fine-grained tokens > Generate new
token (resource owner drewkeriazes-personal, repository MapPacker-SnowboardAnywhere only, Actions: read and write),
then Settings > Environments > publish > `PC_DISPATCH_TOKEN` > Update, and delete the old token. Or, with gh:
`gh secret set PC_DISPATCH_TOKEN --env publish --repo drewkeriazes-personal/MapPacker-SnowboardAnywhere`.

## Later: a split build (design only, not built)

Drew's idea for packs too big for one free runner: estimate the size first, build parts of the pack in parallel
jobs, each uploading its part as an artifact, and join them in a last job. What each stage would need:

| stage | today | split |
|---|---|---|
| resolve, plan, nodes, manifest | one config, one manifest for the whole box | unchanged, plus a size estimate (the plan's download total and the fine tile count) that picks the number of parts, and a part list: ranges of fine-tile columns, each with a halo |
| fetch, landfire, grooming | one raw folder per resort | per part: only the manifest items whose bbox meets the part plus its halo (DEM tiles, EPT nodes, NAIP, LANDFIRE clips); OSM, grooming and the mid and far rings once, in the join job or a small first job. Needs a bbox filter in `fetch.ps1` / `gen_manifest.py`, and raw over 14 GB split this way too |
| build (`build_pack.py`) | one process: whole-pack mosaics in memory (DEM, lidar returns, NAIP, LANDFIRE), then masks, moguls, piste directions, AO, trees, far trees, cover | the biggest change. The per-cell work (fine heights, masks, AO, moguls, trees, cover) per part, cutting at tile edges with a halo wide enough for every filter (AO's reach, mogul and smoothing kernels, tree stand clustering). The whole-pack parts stay in the join: OSM features and runs, piste directions along whole runs, the per-pack fits (stage 5b's canopy thresholds from this pack's own LANDFIRE classes: computed once from all parts' class histograms and handed to the parts first, so a two-pass build), far trees, mid, far and coarse sets, `features.json`, `meta.json` and the content hash. The output must equal the one-job build byte for byte, or `publish_pack.py`'s content compare publishes a new version for nothing |
| content, attract, spots, index, published, report | on the assembled pack | unchanged, in the join job (attract and spots still skip without a GPU) |

Rough effort: the fetch filter and the part list a few days; `build_pack.py` split into per-part and whole-pack
passes with halos, plus a test that a split build equals the one-job build on synth and one real resort, two to
four weeks, most of it in the stages that read neighbours (AO, moguls, stands) and in the per-pack fits. The PC
runner covers today's case (Vail) without any of that, so the split waits until a resort needs more than the PC or
the PC is not around to build.
