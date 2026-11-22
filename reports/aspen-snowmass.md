# Pack report: Aspen Snowmass (`aspen-snowmass`)

Build `20261122T160405Z-ac0fa6`, pipeline `4d3807e`, format 1. Report 2026-11-22T16:04:18Z by `pipeline/pack_report.py` (FEAT-175).

**Tier: silver** (FEAT-225: the weakest layer's)

| Layer | Source | Tier |
|---|---|---|
| terrain | 3DEP 1 m | gold |
| trees | lidar crowns + stands | silver |
| surface | NAIP | gold |

**Playable**: every DATA-022 MVP line passes.

| # | Item | | Detail |
|---|---|---|---|
| F | Pack format current | ✅ | formatVersion 1 |
| 1 | Resort config | ⚠️ | EPSG:26913 (13N); no start_run |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ✅ | EVT, EVC and EVH; 0.0% of the forest in EVT classes the species rules don't name (west rules) |
| 5 | Heights fine, mid, far | ✅ | 2406 to 3994 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ⚠️ | rock 5.4% (reference 1.1%), canopy 11% : more rock than the reference by over 3x, check the thresholds (FEAT-175 step 2) |
| 7 | Trees and shrubs with species | ⚠️ | 0.05 M crowns + 0.35 M stems = 5.8 k per km2 (15% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.28 M crowns in 124 cells |
| 9 | features.json | ✅ | 18 lifts, 196 runs, 1341 buildings, 643 roads, 46 water, 994 peaks, 82 labels (2 lifts with towers spaced by the pipeline, no OSM pylons) |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on High Pass, top of Cirque T-Bar |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 116 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | 8 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ❌ | 0% of runs with a grooming record, 0 reports in raw; 14% of the green and blue run length groomed (few groomers: a grooming source missing or its names not matched to OSM, FEAT-256) |
| 16 | Place names | ✅ | GNIS CO; 994 peaks, 82 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/aspen-snowmass/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | treeline 3600 m measured; canopy.grow_ndvi 0.1319; canopy.leaf_ndvi 0.3263; canopy.veg_ndvi 0.2336; rock.bare_ndvi 0.2336; rock.dark 65.6667; rock.grey_sat 0.2; rock.ndvi 0.1545; treeline 3600 |
| 21 | Published figures | ➖ | no English Wikipedia article with an Infobox ski area for Aspen Snowmass |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 68.9 |  |
| Trees (crowns + stems) per km2 | 5,773 | 39,201 |
| Rock share | 5.4% | 1.1% |
| Canopy share | 11% | 66% |
| Canopy on run centre lines | 0.0% | 3.7% |
| Groomed share | 0.8% |  |
| Crowns per km within 5 m of lift lines | 0.0 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 0% |  |
| Runs groomed in OSM | 24% |  |
| Green and blue run length groomed | 14% |  |
| Groomed mask on groomed run centre lines | 100% |  |
| Far ring crowns | 275,524 |  |
| Mean mogulScore by difficulty | advanced 0.53, easy 0.0, expert 0.53, intermediate 0.13 | |

**Advanced or harder runs never over 15 deg:** Terminator (advanced, 4 deg), Hanging Valley Exit (expert, 9 deg), Hanging Valley Exit (expert, 10 deg), Terminator (advanced, 12 deg), Weird Woods (expert, 12 deg), Terminator (advanced, 13 deg), Terminator (advanced, 13 deg), Wildcat (Lower) (advanced, 13 deg)

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 2400 | 2.69 | 0 | 0 | 0 |
| 2500 | 7.16 | 0 | 0 | 0 |
| 2600 | 6.6 | 3 | 10 | 2 |
| 2700 | 6.67 | 965 | 10,880 | 1,776 |
| 2800 | 5.54 | 3,131 | 29,668 | 5,921 |
| 2900 | 5.56 | 4,286 | 41,883 | 8,303 |
| 3000 | 6.1 | 6,351 | 59,059 | 10,724 |
| 3100 | 5.47 | 6,486 | 55,387 | 11,304 |
| 3200 | 5.17 | 6,964 | 52,344 | 11,478 |
| 3300 | 4.99 | 7,416 | 48,411 | 11,188 |
| 3400 | 3.87 | 5,223 | 29,965 | 9,085 |
| 3500 | 3.35 | 4,074 | 20,338 | 7,297 |
| 3600 | 3.01 | 1,363 | 3,387 | 1,579 |
| 3700 | 1.75 | 24 | 7 | 17 |
| 3800 | 0.78 | 2 | 0 | 3 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 289 | 69.3 | 2026-11-22 |
| mid heights | yes | 25 | 12.1 | 2026-11-22 |
| far heights | yes | 16 | 2.8 | 2026-11-22 |
| mask | yes | 81 | 5.1 | 2026-11-22 |
| AO | yes | 81 | 4.2 | 2026-11-22 |
| piste directions | yes | 81 | 0.1 | 2026-11-22 |
| moguls | yes | 81 | 0.4 | 2026-11-22 |
| cover | yes | 4 | 8.8 | 2026-11-22 |
| trees (crowns) | yes | 24 | 1.1 | 2026-11-22 |
| stands (stems) | yes | 24 | 2.2 | 2026-11-22 |
| far tree ring | yes | 124 | 6.6 | 2026-11-22 |
| shrubs | yes | 80 | 0.5 | 2026-11-22 |
| rocks | yes | 79 | 1.5 | 2026-11-22 |
