# FEAT-342: Refresh packs (design)

Card: #168. Follow-ups: BUG-166 (#169, the rebuild list), FEAT-343 (#170, menu stills and ghosts in the cloud), FEAT-344 (#171, packs too big for the runner: Drew's PC as a runner, or a split build).

## Why

Improving the pipeline does nothing for players until the packs are rebuilt with it. Today each pack is rebuilt by hand, one at a time. Drew wants one trigger that brings every published pack up to what the current `main` builds, so players and his own testing get the newest look, nobody rebuilds by hand after pipeline PRs, and anything that fell behind catches up.

## Goals

- One `Refresh packs` workflow, run by hand (Actions tab or `gh workflow run refresh-packs.yml`), typically once at the end of a day after several PRs merged.
- A `mode` dropdown: *needs updating* (default), *all*, *list only*.
- Several builds at once instead of one at a time.
- Every pack the run can't build is named in the run summary with the reason, never dropped silently.

## Non-goals

- Running on every merge to `main` (Drew: it would pile up builds). A nightly schedule is a possible later add, not part of this.
- Building packs the free runner can't build, or rendering menu stills and ghost takes in the cloud: FEAT-344, FEAT-343.
- Fixing the static rebuild list: BUG-166. This workflow reads `catalog.json` at run time and needs no list.

## Anti-goals

- A refresh that quietly makes a pack worse: drops a menu still and ghost takes it had, or publishes a pack built from a commit that is not on `main`.
- A refresh that knocks over the data hosts or the build queue so that a hand-started Build pack run waits behind 19 refresh builds with no way to tell.

## Approaches

- **A. A plan job that starts one Build pack run per pack, several at once (picked).** Reuses everything `build-pack.yml` already has: the probe, the fetch retries, the outcome log and retry workflow, the publish PR with the App token, automerge, and `publish_pack.py`'s "publish nothing when the content equals the published version".
- **B. Drew's PC as a self-hosted runner doing every build.** Has the GPU, the game and Vail's raw data, but one build at a time and the PC is busy for a day. Not now.
- **C. A, with Drew's PC taking what the cloud can't do.** Drew picked it as the follow-up (FEAT-344).

Within A, two ways to run the builds: a matrix of `workflow_call` jobs inside one run, or one `workflow_dispatch` of `build-pack.yml` per pack. **Dispatch (my call)**: each build stays its own run, so its `outcome` job, `build-pack-retry.yml` (which re-runs a run's failed jobs) and the game's progress view all keep working unchanged. The cost is that the refresh run only starts the builds and links them; it does not wait for them.

## Design

**`refresh-packs.yml`** (workflow_dispatch; input `mode`: `needs updating` | `all` | `list only`; permissions `actions: write`, `contents: read`). One job, `tools/ci/refresh_packs.py`:

1. **Pick.** Read `catalog.json` on `main`; take each resort and test pack with a config in `resorts/<slug>/` (not `source_only`).
   - *needs updating*: the pack's `pipeline` stamp is behind `main` in a path its build reads: `pipeline/` except `pipeline/tests/` and Markdown, `resorts/<slug>/`, and the `resorts/` folders of its `raw_from` and relocate sources. (`git diff --quiet <stamp> origin/main -- <paths>`.) A stamp git can't find counts as needing it.
   - *all*: every pack.
   - A wrong "needs updating" only costs runner time: the content check skips the publish.
2. **Leave out, with a reason**, packs the runner can't build yet: too big for the runner, and packs whose published `attract/index.json` is generated with `stills` or `ghosts` (built on Drew's PC; a cloud rebuild would drop them, FEAT-343). How to know "too big" and read the published `attract/` is the builder's call (a flag in the resort config, the published `bytes`, a ranged read of the release zip).
3. **Start.** *list only* stops here and writes the plan to the run summary. Otherwise `gh workflow run build-pack.yml -f slug=<slug>` per picked pack (an existing slug is rebuilt from its config), with `requested_by` set to `refresh-packs` so the publish PR says where it came from.
4. **Summary**: a table, one row per pack: started (with the run link), up to date, or left out and why.

**Several at once.** `wait_turn.py` gets a slot count (`--slots N`, default 1 so nothing else changes): a run waits while N or more earlier runs are still active. `build-pack.yml` passes a repo variable `BUILD_SLOTS` (my call: 3 to start, raised once FEAT-314's host log shows the data hosts cope). Hand-started builds and refresh builds share the same queue and slots, in start order, as today.

**Publishing.** Unchanged: each build opens its own publish PR, labelled automerge (the triggering actor is Drew), and `publish-merge.yml` merges it. FEAT-264 (#24, hold big changes until accepted) matters more once publishes happen without anyone watching each one; not part of this card.

**Docs.** README > Build pack: the refresh workflow, its modes and what it leaves out; `wait_turn.py`'s slots.

**Checks.** pytest for `refresh_packs.py`'s pick (stamp behind / up to date / missing stamp / raw_from source changed / left-out packs) with git and the catalog faked, `test_workflows.py`'s existing rules (inputs only through env), and `wait_turn.py` with slots. First live run in *list only*.

## Left to the builder

- How "too big for the runner" is known.
- How the published `attract/` is read.
- Whether test packs (synth) are included by default.
