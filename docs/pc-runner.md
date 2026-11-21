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
5. **Secrets:** none new. The fetch step already gets `LANDFIRE_EMAIL` and the publish step the App's secrets.
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

## The queue: one machine, shared slots

The PC is one runner, so GitHub itself runs its jobs one at a time, and a job waits in GitHub's queue while the PC
is offline, for at most 24 hours before it fails. `wait_turn.py` (the `queue` job, then "still my turn" in the build
job) counts every Build pack run, cloud or PC: today that is one build at a time across both, and with FEAT-342's
`BUILD_SLOTS` (#168) a PC run takes one of the slots like a cloud run. That is safe (no two builds write the same raw
folders at once on the PC, and the PC's builds never run beside a cloud build of the same resort) but it means a PC
run waiting for an offline PC holds a slot, and the cloud builds behind it wait (up to the queue's 5.5 hours, then
they give up and the failure metrics retry them). Start PC builds while the PC is on.

The follow-up once #168 merges: PC runs get a slot of their own. `wait_turn.py` would count, for a cloud run, only
the runs ahead of it that build in the cloud, and for a PC run only the PC runs (or none: the runner already
serialises them); a run's place is known from its `build` job's labels (`sba-pc`) or, before that job exists, the
probe job's `runner` output. The same follow-up routes FEAT-342's left-out packs to the PC: the refresh workflow
starts Build pack with `-f build_on=pc` for the packs it leaves out with the reason codes `too_big` and
`needs_gpu_attract`, instead of listing them as "build on Drew's PC".

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
