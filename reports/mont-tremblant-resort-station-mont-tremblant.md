# Pack report: Mont Tremblant Resort, Station Mont Tremblant (`mont-tremblant-resort-station-mont-tremblant`)

Build `20261122T153048Z-9f4c7e`, pipeline `874dd77`, format 1. Report 2026-11-22T15:31:02Z by `pipeline/pack_report.py` (FEAT-175).

**Tier: bronze** (FEAT-225: the weakest layer's)

| Layer | Source | Tier |
|---|---|---|
| terrain | Mapterhorn z15, 1.7 m | silver |
| trees | stands from ETH canopy height + WorldCover | silver |
| surface | WorldCover 10 m | bronze |

**Playable**: every DATA-022 MVP line passes.

| # | Item | | Detail |
|---|---|---|---|
| F | Pack format current | ✅ | formatVersion 1 |
| 1 | Resort config | ⚠️ | EPSG:32618 (18N); no start_run |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ⚠️ | outside the US, where LANDFIRE has no data: species from elevation and aspect only (FEAT-225) |
| 5 | Heights fine, mid, far | ✅ | 206 to 933 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ✅ | rock 0.0% (reference 1.1%), canopy 92% |
| 7 | Trees and shrubs with species | ⚠️ | 0.00 M crowns + 1.09 M stems = 17.5 k per km2 (45% of the reference) (no lidar: every tree is a stand stem, from the ETH canopy height) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.93 M crowns in 286 cells generated on the ETH canopy height and WorldCover tree cover, not lidar (FEAT-257) |
| 9 | features.json | ⚠️ | 15 runs without a difficulty; 12 lifts, 205 runs, 722 buildings, 1210 roads, 31 water, 225 peaks, 0 labels |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on La Garette, top of Duncan Express |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 91 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 5 lines |
| 14 | Validated | ⚠️ | canopy 56% on run centre lines (trail cuts missing?); 11 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ❌ | 0% of runs with a grooming record, 0 reports in raw; 45% of the green and blue run length groomed |
| 16 | Place names | ❌ | no GNIS file in raw/names; 225 peaks, 0 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/mont-tremblant-resort-station-mont-tremblant/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ❌ | no treeline: forested to the top of the box (measured); rock and canopy thresholds are Vail's (FEAT-175 step 2) |
| 21 | Published figures | ➖ | no English Wikipedia article with an Infobox ski area for Mont Tremblant Resort, Station Mont Tremblant |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 62.4 |  |
| Trees (crowns + stems) per km2 | 17,515 | 39,201 |
| Rock share | 0.0% | 1.1% |
| Canopy share | 92% | 66% |
| Canopy on run centre lines | 55.6% | 3.7% |
| Groomed share | 1.9% |  |
| Runs with a grooming record | 0% |  |
| Runs groomed in OSM | 30% |  |
| Green and blue run length groomed | 45% |  |
| Groomed mask on groomed run centre lines | 100% |  |
| Far ring crowns | 931,117 |  |
| Mean mogulScore by difficulty | advanced 0.34, easy 0.0, expert 0.49, intermediate 0.24, none 0.0, novice 0.0 | |

**Advanced or harder runs never over 15 deg:** Vertigo (advanced, 7 deg), unnamed (advanced, 9 deg), Vertigo (advanced, 10 deg), Vertigo (advanced, 12 deg), Johannsen (expert, 12 deg), Grand-Téton (expert, 12 deg), Boomerang (advanced, 12 deg), Vertigo (advanced, 13 deg), and 3 more

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 200 | 9.18 | 0 | 98,607 | 10,742 |
| 300 | 13.8 | 0 | 200,545 | 14,530 |
| 400 | 10.66 | 0 | 148,951 | 13,971 |
| 500 | 9.13 | 0 | 130,021 | 14,233 |
| 600 | 9.6 | 0 | 157,405 | 16,400 |
| 700 | 7.01 | 0 | 206,313 | 29,427 |
| 800 | 2.8 | 0 | 143,702 | 51,292 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 256 | 64.3 | 2026-11-22 |
| mid heights | yes | 25 | 10.9 | 2026-11-22 |
| far heights | yes | 16 | 2.1 | 2026-11-22 |
| mask | yes | 64 | 0.6 | 2026-11-22 |
| AO | yes | 64 | 4.1 | 2026-11-22 |
| piste directions | yes | 64 | 0.2 | 2026-11-22 |
| moguls | yes | 64 | 0.1 | 2026-11-22 |
| cover | yes | 4 | 7.3 | 2026-11-22 |
| trees (crowns) | no | 0 | 0.0 |  |
| stands (stems) | yes | 72 | 7.0 | 2026-11-22 |
| far tree ring | yes | 286 | 22.3 | 2026-11-22 |
| shrubs | yes | 14 | 0.0 | 2026-11-22 |
| rocks | yes | 9 | 0.0 | 2026-11-22 |
