# Pack report: Crystal Mountain (`crystal-mountain`)

Build `20261125T043558Z-bff98c`, pipeline `3a50d0c`, format 1. Report 2026-11-25T04:36:09Z by `pipeline/pack_report.py` (FEAT-175).

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
| 1 | Resort config | ⚠️ | EPSG:26910 (10N); no start_run |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ⚠️ | EVT, EVC and EVH; 33.9% of the forest in EVT classes the species rules don't name (west rules): over 20%, map them in species.classify_evt |
| 5 | Heights fine, mid, far | ✅ | 979 to 2135 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ⚠️ | rock 6.9% (reference 1.1%), canopy 13% : more rock than the reference by over 3x, check the thresholds (FEAT-175 step 2) |
| 7 | Trees and shrubs with species | ⚠️ | 0.03 M crowns + 0.16 M stems = 4.9 k per km2 (12% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.47 M crowns in 131 cells |
| 9 | features.json | ✅ | 11 lifts, 156 runs, 105 buildings, 192 roads, 16 water, 1097 peaks, 226 labels |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on Chairline Left, top of Chair 6 |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 63 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | 2 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ❌ | 0% of runs with a grooming record, 0 reports in raw; 7% of the green and blue run length groomed (few groomers: a grooming source missing or its names not matched to OSM, FEAT-256) |
| 16 | Place names | ✅ | GNIS OR, WA; 1097 peaks, 226 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/crystal-mountain/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | treeline 1850 m measured; canopy.grow_ndvi 0.15; canopy.leaf_ndvi 0.3575; canopy.veg_ndvi 0.3; rock.bare_ndvi 0.3; rock.dark 70.6667; rock.grey_sat 0.0811; rock.ndvi 0.1878; treeline 1850 |
| 21 | Published figures | ✅ | 6 figures match (Wikipedia: Crystal Mountain (Washington); table below) |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 40.0 |  |
| Trees (crowns + stems) per km2 | 4,851 | 39,201 |
| Rock share | 6.9% | 1.1% |
| Canopy share | 13% | 66% |
| Canopy on run centre lines | 0.9% | 3.7% |
| Groomed share | 0.2% |  |
| Crowns per km within 5 m of lift lines | 0.0 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 0% |  |
| Runs groomed in OSM | 3% |  |
| Green and blue run length groomed | 7% |  |
| Groomed mask on groomed run centre lines | 100% |  |
| Far ring crowns | 472,156 |  |
| Mean mogulScore by difficulty | advanced 0.42, easy 0.0, expert 0.44, extreme 0.29, freeride 0.45, intermediate 0.24, none 0.0 | |

**Advanced or harder runs never over 15 deg:** 13-F (advanced, 11 deg), Upper Boondoggle. (advanced, 15 deg)

## Published figures (gathered 2026-11-13 by published.py)

| Figure | Published | Source | This pack | | Note |
|---|---:|---|---:|---|---|
| Summit | 2,131 m (6,991 ft) | Wikipedia: Crystal Mountain (Washington) | 2,125 m (6,972 ft) | ✅ | highest of the lift stations, -6 m |
| Base | 1,341 m (4,400 ft) | Wikipedia: Crystal Mountain (Washington) | 1,338 m (4,390 ft) | ✅ | lowest of the lift stations, -3 m |
| Vertical | 790 m (2,592 ft) | Wikipedia: Crystal Mountain (Washington) | 787 m (2,582 ft) | ✅ | -3 m (-0%) |
| Lifts | 11 | Wikipedia: Crystal Mountain (Washington) | 11 | ✅ | every lift (10 chairs and gondolas) |
| Runs | 80 | Wikipedia: Crystal Mountain (Washington) | 143 | ✅ | 143 run names over 156 segments, 8 unnamed; 179% of the published count |
| Skiable area | 10.5 km2 (2,600 acres) | Wikipedia: Crystal Mountain (Washington) | 8.7 km2 (2,160 acres) | ✅ | run lines widened 50 m each side, plus the area runs, 0.83 times the published |

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 1100 | 0.66 | 0 | 0 | 0 |
| 1200 | 1.88 | 0 | 0 | 0 |
| 1300 | 2.99 | 876 | 5,972 | 2,291 |
| 1400 | 3.98 | 3,284 | 21,467 | 6,214 |
| 1500 | 4.75 | 4,494 | 21,518 | 5,476 |
| 1600 | 6.36 | 7,005 | 43,491 | 7,940 |
| 1700 | 6.95 | 7,445 | 46,947 | 7,830 |
| 1800 | 6.47 | 5,002 | 19,773 | 3,828 |
| 1900 | 4.31 | 1,791 | 3,973 | 1,337 |
| 2000 | 1.36 | 233 | 570 | 589 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 165 | 45.7 | 2026-11-25 |
| mid heights | yes | 25 | 12.2 | 2026-11-25 |
| far heights | yes | 16 | 2.6 | 2026-11-25 |
| mask | yes | 48 | 3.0 | 2026-11-25 |
| AO | yes | 48 | 2.7 | 2026-11-25 |
| piste directions | yes | 48 | 0.0 | 2026-11-25 |
| moguls | yes | 48 | 0.3 | 2026-11-25 |
| cover | yes | 4 | 8.6 | 2026-11-25 |
| trees (crowns) | yes | 20 | 0.7 | 2026-11-25 |
| stands (stems) | yes | 20 | 1.4 | 2026-11-25 |
| far tree ring | yes | 131 | 11.3 | 2026-11-25 |
| shrubs | yes | 46 | 0.2 | 2026-11-25 |
| rocks | yes | 48 | 1.0 | 2026-11-25 |
