# Menu stills and ghost takes for packs rebuilt in the cloud (FEAT-343)

What a pack's main menu loses when `build-pack.yml` rebuilds it on the free runner, whether the runner could
render it, whether the published menu can be carried over, and what to do. Researched 2026-11-20 against
MapPacker `main` 1638e74 and the game's `main` 2fb2d8b.

## Short answer

- **Today** a cloud rebuild of a pack published with a menu still and ghost takes ships `shots.json` and an empty
  `attract/index.json`: no still, no takes. Because the menu files are in `publish_pack.py`'s content key, it
  publishes even when nothing else changed. The game then opens the menu over the dark gradient on the first load
  and shows the shot with no riders on every load. Three published packs have a still and takes: Boston Mills v3,
  Park City v1 and Vail v8 (Vail's pack menu is unused: the game shows its own hand-made one).
- **Rendering on the runner** with SwiftShader works but is slow and the still is not menu quality: 18 minutes
  per still and 22 minutes for the ride on Drew's 12-thread PC (the GPU: 15 s and 21 s), so about 3.5 to 5
  hours on the 4-vCPU runner, and `lowgfx` (no shadows, a third of the trees). The takes, though, come out
  byte for byte the same as the GPU's.
- **Carrying the published menu over** costs seconds and needs no game: fetch the published `attract/` (1 to 4
  MB, by range reads of the release zip) into the pack before the `content` stage, and `gen_content.py
  write_attract` keeps it when the cameras are the same, as it already does on Drew's PC. A rebuild that changed
  nothing then publishes nothing. A changed pack keeps its riders (checked against the new heights) but its still
  stops showing, since the game shows a still only for the build it was rendered from.
- **Recommendation:** carry-over in the cloud build (with the take height check), a fresh still left to a GPU run
  (Drew's PC by hand, or FEAT-344's runner). Not built in this PR: it reads the release zip with FEAT-342's
  `RangeFile` (#168, not merged), and whether a changed pack may go out with the old riders and no still is
  Drew's call. Details at the end.

## 1. What a cloud rebuild ships today, and what the menu shows

**The stages.** `tools/ci/build_pack_ci.py build` runs `build_resort.py <slug> --from build --stop-after index`.
`content` runs (`gen_content.py --no-hand`, then `pack_content.py`); `attract` and `spots` are skipped by
`decide()` because there is no game checkout (`GAME_TOOL`, `game_tool()` is None: "no game/tools/auto_attract.mjs
in a game checkout"). The runner starts with an empty `packs/<slug>/`, so nothing of the published pack is there.

**The files.** `gen_content.py write_attract` finds no old `attract/index.json`, so it writes
`attract/shots.json` (the 5 generated cameras) and `attract/index.json` =
`{"shots": true, "generated": true, "stills": [], "ghosts": [], "looks": {}, "shotGhosts": {}}`, and sets
`meta.attract = {"generated": true}`. No `<shot>.jpg`, no `*-start-run-*.json` takes. (On Drew's PC the same
function keeps the still and takes when the shots are unchanged, because the old pack is in `packs/<slug>/`;
on the runner there is no old pack to keep them from.) `pack_report.py` line 17 then says WARN "no still of this
build, 0 ghost takes (the game's tools/auto_attract.mjs makes them)"; nothing fails.

**It always publishes.** `publish_pack.py content_key` hashes every file in the pack except `meta.json`'s
`build` / `pipeline` stamps and the report. `attract/index.json` (its `stills`, `looks`, `ghosts`) and the still
and take files are in the hash. So for a pack published with a still and takes, a cloud rebuild whose terrain,
trees and everything else came out identical still gets a different key, and `publish_pack.py`'s "nothing
changed" guard does not stop it: it publishes a new version whose only difference is that the menu still and the
riders are gone.

**What the game shows** (`game/src/world/AttractShots.ts`, `core/Game.ts`, `ui/MenuStill.ts`,
`world/AttractGhosts.ts`):
- The game's own hand-made entry in `game/public/attract/index.json` wins when it has one (Vail, Breckenridge);
  otherwise `loadAttractManifest` takes the pack's `attract/index.json` because `meta.attract` is set.
- Shots: `shots.json` is still there, so the menu sits on the same generated camera as before.
- Still: `cachedMenuStill` (the frame this browser kept at its last crossfade; keyed on the game build, the
  pack's `meta.build`, the shot and the quality) misses because the pack build is new, and `shippedStill`
  finds no still. The menu opens over the dark gradient while the session loads, then fades into the live view.
  From the second load on the browser's own kept frame serves as the still, so the loss is the first load
  after each new pack version (and every load in a private window or the dev server).
- Riders: `ghosts` is empty, so the live backdrop has no riders at all, on every load. This is the visible loss.

Note that a carried-over still could never show anyway: `shippedStill` shows a still only when its
`looks[shot].pack` equals the pack's `meta.build`, and every build has a new `meta.build`. Takes have no such
check (`AttractTake.build` is recorded but not read): a take ridden on another build is shown, floating or sunk if
the snow under it moved.

## 2. Which published packs have a still and takes now

Read from each release zip's central directory and its `attract/index.json` by ranged requests (no full
downloads), 2026-11-20:

| pack | version | menu |
|---|---|---|
| boston-mills | v3 | still `top-of-lift-3` (build 20261112T224417Z-7cba89) and 6 takes |
| park-city-mountain | v1 | still `top-of-dreamcatcher` and 6 takes |
| vail | v8 | still `born-free` and 6 takes, but the game shows its own hand-made Vail menu instead (and Vail is too big for the runner anyway, FEAT-344) |
| the other 16 resorts | | shots only: `stills: []`, `ghosts: []` |

So the packs a cloud rebuild would actually hurt are **Boston Mills and Park City** (Vail is built on Drew's PC
for size, and its pack menu is unused). The 16 others ship no still or riders today, so a cloud rebuild changes
nothing in their menu. FEAT-342's `needs_gpu_attract` leaves out exactly these three.

## 3. Rendering on the runner (SwiftShader)

**What it would take.** The runner would check out the game, `npm ci`, `npx playwright install --with-deps
chromium`, `npx vite build`, then run `auto_attract.mjs <slug>` (no GPU there, so `tools/browser.mjs` picks
SwiftShader and adds `&lowgfx`). The game's own CI does all but the last step in every `browser-checks` job: on
run 44849210566 checkout, setup-node, `npm ci`, the Playwright install (cached) and the build took about 1 minute.
`packs/index.json` must exist before the stage (the `index` stage writes it after `attract`; without it every page
logs a 404 and `auto_attract.mjs` exits 1, which `attract_run` reads as a warning).

**Measured.** Boston Mills v3 (60 MB, the published zip, sha256 checked against the catalog), unzipped into a
scratch folder and served with `SHOT_PACKS`, from a throwaway game worktree at `main` 2fb2d8b (so nothing was
written into a shared pack or the game's main checkout). This is the one exception to the GPU-only rule for
renders on Drew's PC, because the point was to measure the cloud's renderer.

| run on Drew's PC (12 threads, RTX 2070 SUPER) | what | time |
|---|---|---|
| `auto_attract.mjs boston-mills --gpu --no-ride` | 5 stills on the GPU, High preset | 76 s in all |
| `auto_attract.mjs boston-mills --cpu` | the first still on SwiftShader, `lowgfx` | 18 min (22:14:34 to 22:32:29); stopped there |
| `auto_attract.mjs boston-mills --cpu --no-stills` | the ride (one settled page, 3 variants of 2 riders) on SwiftShader | 22 min: 17 to settle the page, 5 to ride and save the preview frames |
| `auto_attract.mjs boston-mills --gpu --no-stills` | the same ride on the GPU | 21 s |

Each still loads and settles a fresh page (`shotPage`), so five stills on SwiftShader are about 5 x 18 = 90
minutes on this PC before the ride. The free runner has 4 vCPUs against this PC's 12 threads, and SwiftShader
scales with cores, so expect roughly two to three times that: three to four and a half hours for the stills, on
top of a build that already takes 30 to 90 minutes and a 6 hour job limit. Only the first still is the menu's
(the other four are for a person to look at, `game/shots/auto-attract/`), so an option to render one would cut it
to under an hour, still for a `lowgfx` picture.

**Looks.** Same pose, same pack (stills in the scratch folder, not committed):
- the GPU still (High preset): sun shadows under every tree and lift tower, full tree density, a clean far
  forest;
- the SwiftShader still (`lowgfx`: the Low preset, no shadows, tree density 0.3, forest density 0.35, no LOD0
  cards): no cast shadows (trees and lift towers stand on bare white snow), the near trees thinner, the far
  forest a grainy speckle of bare-tree cards. Readable as the place, but plainly a lower setting than the live menu it crossfades into
  (the menu runs at the player's preset), so the swap is a visible pop. It is not a menu still.

Rendering without `lowgfx` on SwiftShader (the full preset) is possible only by tricking `browser.mjs` (it adds
`lowgfx` to `SHOT_QUERY` unless the query already contains the text) and would be slower again. Not worth it.

The ghost ride is physics and does not depend on the renderer: the six takes ridden on SwiftShader are
byte for byte the same files as the six ridden on the GPU from the same game build and pack (all 33 waypoints
reached, no crashes). Takes made on the runner would be as good as the PC's; what is slow is settling the page
(streaming the terrain and trees in on a software renderer), not the ride. On the runner that is roughly 45 to
65 minutes for the takes alone.

Runner cost in all, scaled from this PC: the five stills and the ride, about 6 x 17 minutes here, so roughly
3.5 to 5 hours on the runner; the menu still and the ride only, 1.5 to 2 hours; the ride only, about an hour.

## 4. Carrying the published still and takes over

`gen_content.py write_attract` already does the carry-over on Drew's PC: when the old `attract/` is in the pack
folder and the new `shots.json` equals the old one, "the same shots as before: the still and ghost takes stay";
new shots drop them. The runner only lacks the old folder. So the carry-over is: before the `content` stage, put
the published pack's `attract/` into `packs/<slug>/attract/`, and let `write_attract` keep or drop it by camera
as it does on the PC.

- **Fetching it.** The published `attract/` is small: Boston Mills 1.1 MB (a 440 KB still, six 115 KB takes),
  Park City 3.6 MB. FEAT-342's `tools/ci/refresh_packs.py` (#168) already reads one member of a release zip by
  HTTP range requests (`RangeFile` + `zipfile`); the same reads fetch the listed files without downloading the
  60 to 245 MB zip.
- **Same cameras?** The shots come only from the pack's own heights, lifts, runs, trees and start
  (`choose_shots`), so they stay the same unless the pipeline change moved those. When they change, the
  takes ride a different shot's start run and `write_attract` drops them, which is right.
- **The still.** It can't show after a real change: the game compares `looks[shot].pack` with the new
  `meta.build`. It is still worth carrying, because of the next point.
- **No-op rebuilds stay no-ops.** With the published `attract/` copied in verbatim, a rebuild whose pack came
  out the same gets the same `content_key` as the published version, and `publish_pack.py` publishes nothing.
  That is what FEAT-342's refresh needs for these packs: today they would always republish, menu stripped.
- **A real change** publishes the new pack with the old takes and the old still. The game skips the still (first
  load over the gradient, then the browser keeps its own frame, as for the 16 packs without one) and rides the
  takes. A pipeline change that moved the snow under the start run could leave them floating or sunk, and the
  game does not check. The pipeline can: a take's on-ground samples (`f & 1`) sit on the pack's own heights.
  Measured on Boston Mills v3 with `gen_content.Ground` (the pipeline's fine heights) under its own six takes:
  z minus ground has median +0.02 to +0.03 m, 5th to 95th percentile -0.10 to +0.28 m, worst 0.82 m. A rule of
  "95th percentile of |dz| under 0.5 m, else drop the take" keeps every take on an unchanged pack and drops one
  whose run moved by more than a board's height. It needs only the new pack.
- `pack_report.py` line 17 already says WARN "no still of this build" for such a pack, which is accurate.

What this does not give: a fresh still or new riders for a changed pack. Those still need a GPU run of
`auto_attract.mjs` (Drew's PC, by hand or FEAT-344).

## 5. Drew's PC as a runner (FEAT-344)

A self-hosted runner on Drew's PC has the GPU, the game checkout and the raw data, so it would run the full
`build_resort.py` including `attract` (76 s for the five stills and 21 s for the ride on the RTX 2070 SUPER,
section 3) and publish a pack with a fresh still and new riders: the only option that gives a changed pack its
full menu back. Its costs are FEAT-344's: the PC must be on, the runner must take only `workflow_dispatch` runs on
`main` (a public repo), and it shares the GPU with Drew's play and other sessions' checks. For FEAT-343's two
packs it is more than they need: a refresh that changes nothing does not need a render at all (section 4), and one
that does can wait for the next time Drew's PC builds the pack.

## Recommendation

**Pick: carry the published menu over in the cloud build, and leave fresh stills to a GPU.**

1. **Carry-over** (small; after FEAT-342 #168 merges, reusing its `RangeFile`):
   - `build_pack_ci.py build`, before `build_resort.py`, when the catalog has a release for the slug: read that
     release's `attract/index.json`; when it is generated (not hand) and lists stills or ghosts, unzip
     `index.json`, `shots.json` and the files it lists into `packs/<slug>/attract/`. A read that fails: say so in
     the run summary and go on without it (today's behaviour).
   - Nothing else changes: `gen_content.py write_attract` keeps the folder when the new `shots.json` equals the
     published one and drops the still and takes when not, exactly as on Drew's PC.
   - In `gen_content.py`, when it keeps the folder: drop any take whose on-ground samples sit off the new pack's
     heights (95th percentile of |z - ground| over 0.5 m, section 4), and its names in `ghosts` /
     `shotGhosts`.
   - Tests: a fake release (a local zip) carried into a fresh pack; same shots keep it, new shots drop it; a
     take lifted 2 m is dropped; a failed read leaves today's output.
   - Effect: a cloud rebuild that changes nothing in the pack gets the published content key and publishes
     nothing (the menu stays as published). One that changes the pack publishes it with the same camera and
     riders; the still is dropped by the game (first load over the gradient, then the browser's own kept frame,
     like the 16 packs that never had one), and `pack_report.py` line 17 says WARN "no still of this build".
2. **Fresh stills** stay on a GPU: Drew's PC (`build_resort.py <slug> --force attract`, then publish) when he wants
   a changed pack's still back, or FEAT-344's self-hosted runner. Not SwiftShader on the free runner: hours of
   runner time for a `lowgfx` picture that pops when the live menu takes over.
3. **Optional later**, only if new riders are wanted for changed packs without the PC: `auto_attract.mjs
   --no-stills` on the runner (about an hour; takes as good as the GPU's). It needs the game checkout, `npm ci`,
   Playwright and a `packs/index.json` before the stage. Not worth it for two packs.

**What it changes in FEAT-342 (#168).** Its `needs_gpu_attract` reason exists because a cloud rebuild would
drop these menus and always republish. With the carry-over in, Boston Mills and Park City can be refreshed like
the rest: drop `needs_gpu_attract` from the left-out reasons (or keep the check and turn it into a note in the
run summary, "the menu still will be stale if the pack changes: re-render on a GPU", and FEAT-344's routing key if
Drew wants those re-rendered automatically). `attract_unread` stays. Vail stays out as `too_big`.

**Also found.** A republish (cloud or PC) of Breckenridge or Vail makes the game's own hand-made still
(`game/public/attract/index.json`, `looks[shot].pack`) name an old build, so the game stops showing it until a game
PR re-renders it (BUG-085, #526: PR #806 re-rendered Breckenridge for v4, #805 does Vail for v8). FEAT-342 checks only
the pack's `attract/`, so a refresh of Breckenridge would quietly bring the BUG-085 symptom back. Worth a line in
the refresh's summary for slugs in the game's attract manifest.
