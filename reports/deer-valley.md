# Pack report: Deer Valley (`deer-valley`)

Build `20261125T044636Z-6467cc`, pipeline `3a50d0c`, format 1. Report 2026-11-25T04:47:02Z by `pipeline/pack_report.py` (FEAT-175).

**Tier: gold** (FEAT-225: the weakest layer's)

| Layer | Source | Tier |
|---|---|---|
| terrain | 3DEP 1 m | gold |
| trees | lidar crowns + stands | gold |
| surface | NAIP | gold |

**Playable**: every DATA-022 MVP line passes.

| # | Item | | Detail |
|---|---|---|---|
| F | Pack format current | ✅ | formatVersion 1 |
| 1 | Resort config | ⚠️ | EPSG:26912 (12N); no start_run |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ✅ | EVT, EVC and EVH; 14.1% of the forest in EVT classes the species rules don't name (west rules) |
| 5 | Heights fine, mid, far | ✅ | 1756 to 3047 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ✅ | rock 0.7% (reference 1.1%), canopy 46% |
| 7 | Trees and shrubs with species | ⚠️ | 0.28 M crowns + 1.15 M stems = 15.7 k per km2 (40% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.63 M crowns in 190 cells |
| 9 | features.json | ⚠️ | 57 runs without a difficulty; 32 lifts, 377 runs, 2943 buildings, 2320 roads, 29 water, 684 peaks, 147 labels |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on Orion, top of Empire Express |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 169 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | canopy 15% on run centre lines (trail cuts missing?); 3 advanced+ runs never over 15 deg; 24 crowns per km within 5 m of lift lines; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ❌ | 0% of runs with a grooming record, 0 reports in raw; 0% of the green and blue run length groomed (few groomers: a grooming source missing or its names not matched to OSM, FEAT-256) |
| 16 | Place names | ✅ | GNIS UT, WY; 684 peaks, 147 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/deer-valley/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | treeline 2900 m measured; canopy.grow_ndvi 0.08; canopy.leaf_ndvi 0.3; canopy.veg_ndvi 0.2; rock.bare_ndvi 0.2; rock.dark 72.3333; rock.grey_sat 0.0909; rock.ndvi 0.05; treeline 2900 |
| 21 | Published figures | ➖ | no English Wikipedia article with an Infobox ski area for Deer Valley Resort |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 91.0 |  |
| Trees (crowns + stems) per km2 | 15,698 | 39,201 |
| Rock share | 0.7% | 1.1% |
| Canopy share | 46% | 66% |
| Canopy on run centre lines | 15.1% | 3.7% |
| Groomed share | 0.0% |  |
| Crowns per km within 5 m of lift lines | 24.5 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 0% |  |
| Runs groomed in OSM | 0% |  |
| Green and blue run length groomed | 0% |  |
| Far ring crowns | 630,497 |  |
| Mean mogulScore by difficulty | advanced 0.41, easy 0.0, expert 0.58, freeride 0.15, intermediate 0.2, none 0.0 | |

**Advanced or harder runs never over 15 deg:** Pick Axe (freeride, 11 deg), Boulder Bumps (advanced, 14 deg), Anchor Treess (advanced, 15 deg)

**Lifts with the most crowns on the line:** East Village Gondola (144), Keetley Express (69), Vulcan Express (58), Sultan Express (56), Pioche Express (51)

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 1700 | 2.06 | 5,157 | 10,554 | 7,616 |
| 1800 | 6.05 | 7,807 | 8,336 | 2,666 |
| 1900 | 8.04 | 22,447 | 12,020 | 4,289 |
| 2000 | 6.02 | 24,653 | 22,593 | 7,842 |
| 2100 | 7.97 | 25,084 | 62,302 | 10,960 |
| 2200 | 10.19 | 37,975 | 81,473 | 11,717 |
| 2300 | 8.98 | 39,016 | 105,960 | 16,145 |
| 2400 | 9.42 | 31,427 | 174,029 | 21,809 |
| 2500 | 10.36 | 29,378 | 240,159 | 26,010 |
| 2600 | 10.87 | 29,019 | 264,175 | 26,977 |
| 2700 | 8.1 | 17,871 | 132,827 | 18,597 |
| 2800 | 2.37 | 6,300 | 34,556 | 17,230 |
| 2900 | 0.44 | 747 | 2,215 | 6,732 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 360 | 96.8 | 2026-11-25 |
| mid heights | yes | 25 | 11.4 | 2026-11-25 |
| far heights | yes | 16 | 2.3 | 2026-11-25 |
| mask | yes | 90 | 11.4 | 2026-11-25 |
| AO | yes | 90 | 6.1 | 2026-11-25 |
| piste directions | yes | 90 | 0.0 | 2026-11-25 |
| moguls | yes | 90 | 0.5 | 2026-11-25 |
| cover | yes | 4 | 14.3 | 2026-11-25 |
| trees (crowns) | yes | 100 | 6.6 | 2026-11-25 |
| stands (stems) | yes | 100 | 11.0 | 2026-11-25 |
| far tree ring | yes | 190 | 15.1 | 2026-11-25 |
| shrubs | yes | 100 | 0.6 | 2026-11-25 |
| rocks | yes | 100 | 0.4 | 2026-11-25 |
