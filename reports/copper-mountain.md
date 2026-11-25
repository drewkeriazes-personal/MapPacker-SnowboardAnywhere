# Pack report: Copper Mountain (`copper-mountain`)

Build `20261125T043540Z-bba078`, pipeline `3a50d0c`, format 1. Report 2026-11-25T04:36:06Z by `pipeline/pack_report.py` (FEAT-175).

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
| 1 | Resort config | ⚠️ | EPSG:26913 (13N); no start_run |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ✅ | EVT, EVC and EVH; 0.0% of the forest in EVT classes the species rules don't name (west rules) |
| 5 | Heights fine, mid, far | ✅ | 2948 to 4026 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ✅ | rock 1.2% (reference 1.1%), canopy 56% |
| 7 | Trees and shrubs with species | ✅ | 0.18 M crowns + 1.51 M stems = 31.2 k per km2 (80% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.66 M crowns in 258 cells |
| 9 | features.json | ✅ | 23 lifts, 156 runs, 237 buildings, 320 roads, 34 water, 1331 peaks, 154 labels |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on Ram's Run, top of Three Bears |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 115 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | 1 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ❌ | 0% of runs with a grooming record, 0 reports in raw; 4% of the green and blue run length groomed (few groomers: a grooming source missing or its names not matched to OSM, FEAT-256) |
| 16 | Place names | ✅ | GNIS CO; 1331 peaks, 154 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/copper-mountain/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | treeline 3550 m measured; canopy.grow_ndvi 0.155; canopy.leaf_ndvi 0.4074; canopy.veg_ndvi 0.3; rock.bare_ndvi 0.3; rock.dark 53.6667; rock.grey_sat 0.2; rock.ndvi 0.1939; treeline 3550 |
| 21 | Published figures | ✅ | 6 figures match (Wikipedia: Copper Mountain (Colorado); table below) |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 54.4 |  |
| Trees (crowns + stems) per km2 | 31,174 | 39,201 |
| Rock share | 1.2% | 1.1% |
| Canopy share | 56% | 66% |
| Canopy on run centre lines | 4.8% | 3.7% |
| Groomed share | 0.2% |  |
| Crowns per km within 5 m of lift lines | 6.2 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 0% |  |
| Runs groomed in OSM | 2% |  |
| Green and blue run length groomed | 4% |  |
| Groomed mask on groomed run centre lines | 100% |  |
| Far ring crowns | 661,825 |  |
| Mean mogulScore by difficulty | advanced 0.49, easy 0.0, expert 0.54, intermediate 0.26, none 0.0 | |

**Advanced or harder runs never over 15 deg:** Boardwalk (advanced, 14 deg)

**Lifts with the most crowns on the line:** Timberline Express (30), Excelerator (16), Super Bee (15), Woodward Express (14), Kokomo Express (11)

## Published figures (gathered 2026-11-13 by published.py)

| Figure | Published | Source | This pack | | Note |
|---|---:|---|---:|---|---|
| Summit | 3,753 m (12,313 ft) | Wikipedia: Copper Mountain (Colorado) | 3,755 m (12,320 ft) | ✅ | highest of the lift stations, +2 m |
| Base | 2,960 m (9,711 ft) | Wikipedia: Copper Mountain (Colorado) | 2,959 m (9,708 ft) | ✅ | lowest of the lift stations, -1 m |
| Vertical | 793 m (2,602 ft) | Wikipedia: Copper Mountain (Colorado) | 797 m (2,615 ft) | ✅ | +4 m (+1%) |
| Lifts | 23 | Wikipedia: Copper Mountain (Colorado) | 23 | ✅ | every lift (16 chairs and gondolas) |
| Runs | 140 | Wikipedia: Copper Mountain (Colorado) | 147 | ✅ | 147 run names over 156 segments, 1 unnamed; 105% of the published count |
| Skiable area | 10.0 km2 (2,466 acres) | Wikipedia: Copper Mountain (Colorado) | 10.1 km2 (2,498 acres) | ✅ | run lines widened 50 m each side, plus the area runs, 1.01 times the published |

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 2900 | 2.59 | 3,519 | 24,882 | 10,974 |
| 3000 | 5.55 | 18,928 | 178,945 | 35,679 |
| 3100 | 9.46 | 38,780 | 351,149 | 41,238 |
| 3200 | 8.42 | 39,068 | 332,466 | 44,139 |
| 3300 | 6.92 | 34,006 | 280,975 | 45,526 |
| 3400 | 6.79 | 29,451 | 229,587 | 38,148 |
| 3500 | 6.43 | 17,202 | 109,119 | 19,635 |
| 3600 | 4.86 | 2,170 | 5,541 | 1,586 |
| 3700 | 2.45 | 61 | 2 | 26 |
| 3800 | 0.68 | 0 | 0 | 0 |
| 3900 | 0.25 | 6 | 0 | 24 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 224 | 56.7 | 2026-11-25 |
| mid heights | yes | 25 | 11.6 | 2026-11-25 |
| far heights | yes | 16 | 2.8 | 2026-11-25 |
| mask | yes | 56 | 3.7 | 2026-11-25 |
| AO | yes | 56 | 3.9 | 2026-11-25 |
| piste directions | yes | 56 | 0.0 | 2026-11-25 |
| moguls | yes | 56 | 0.4 | 2026-11-25 |
| cover | yes | 4 | 13.0 | 2026-11-25 |
| trees (crowns) | yes | 56 | 4.4 | 2026-11-25 |
| stands (stems) | yes | 55 | 7.0 | 2026-11-25 |
| far tree ring | yes | 258 | 15.9 | 2026-11-25 |
| shrubs | yes | 56 | 0.5 | 2026-11-25 |
| rocks | yes | 55 | 0.3 | 2026-11-25 |
