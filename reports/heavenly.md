# Pack report: Heavenly Mountain (`heavenly`)

Build `20261125T045014Z-42e79d`, pipeline `3a50d0c`, format 1. Report 2026-11-25T04:50:40Z by `pipeline/pack_report.py` (FEAT-175).

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
| 1 | Resort config | ⚠️ | EPSG:26911 (11N); no start_run |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ⚠️ | EVT, EVC and EVH; 41.2% of the forest in EVT classes the species rules don't name (west rules): over 20%, map them in species.classify_evt |
| 5 | Heights fine, mid, far | ✅ | 1790 to 3066 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ✅ | rock 2.3% (reference 1.1%), canopy 55% |
| 7 | Trees and shrubs with species | ✅ | 0.20 M crowns + 1.09 M stems = 19.7 k per km2 (50% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.50 M crowns in 174 cells |
| 9 | features.json | ⚠️ | 9 runs without a difficulty; 24 lifts, 173 runs, 2090 buildings, 1841 roads, 20 water, 918 peaks, 183 labels |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on Skyline Trail, top of Sky Express |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 99 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | 1 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ✅ | 35% of runs with a grooming record, 36 reports in raw; 96% of the green and blue run length groomed |
| 16 | Place names | ✅ | GNIS CA, NV; 918 peaks, 183 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/heavenly/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | treeline 2800 m measured; canopy.grow_ndvi 0.08; canopy.leaf_ndvi 0.3; canopy.veg_ndvi 0.2; rock.bare_ndvi 0.2; rock.dark 90.0; rock.grey_sat 0.05; rock.ndvi 0.0792; treeline 2800 |
| 21 | Published figures | ⚠️ | skiable area off (Wikipedia: Heavenly Mountain Resort; table below) |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 65.5 |  |
| Trees (crowns + stems) per km2 | 19,674 | 39,201 |
| Rock share | 2.3% | 1.1% |
| Canopy share | 55% | 66% |
| Canopy on run centre lines | 2.9% | 3.7% |
| Groomed share | 3.1% |  |
| Crowns per km within 5 m of lift lines | 13.3 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 35% |  |
| Runs groomed in OSM | 57% |  |
| Green and blue run length groomed | 96% |  |
| Groomed mask on groomed run centre lines | 97% |  |
| Far ring crowns | 499,456 |  |
| Mean mogulScore by difficulty | advanced 0.39, easy 0.0, expert 0.1, intermediate 0.14, none 0.0 | |

**Advanced or harder runs never over 15 deg:** Mott Canyon Trail (advanced, 12 deg)

**Lifts with the most crowns on the line:** Heavenly Gondola (71), Mott Canyon (38), Gunbarrel Express (31), Galaxy (25), Stagecoach Express (24)

## Published figures (gathered 2026-11-13 by published.py)

| Figure | Published | Source | This pack | | Note |
|---|---:|---|---:|---|---|
| Summit | 3,068 m (10,066 ft) | Wikipedia: Heavenly Mountain Resort | 3,036 m (9,961 ft) | ✅ | highest of the lift stations, -32 m |
| Base | 1,907 m (6,257 ft) | Wikipedia: Heavenly Mountain Resort | 1,916 m (6,286 ft) | ✅ | lowest of the lift stations, +9 m |
| Vertical | 1,162 m (3,812 ft) | Wikipedia: Heavenly Mountain Resort | 1,120 m (3,675 ft) | ✅ | -42 m (-4%) |
| Lifts | 25 | Wikipedia: Heavenly Mountain Resort | 24 | ✅ | every lift (20 chairs and gondolas) |
| Runs | 97 | Wikipedia: Heavenly Mountain Resort | 129 | ✅ | 129 run names over 173 segments, 38 unnamed; 133% of the published count |
| Skiable area | 19.4 km2 (4,799 acres) | Wikipedia: Heavenly Mountain Resort | 7.4 km2 (1,826 acres) | ⚠️ | run lines widened 50 m each side, plus the area runs, 0.38 times the published: the resort counts more ground than its runs cover (glades, bowls and trees mapped as lines, or not at all); with the lifts all there, likely no part missing |

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 1800 | 2.23 | 1,727 | 7,215 | 4,008 |
| 1900 | 12.98 | 37,360 | 175,953 | 16,438 |
| 2000 | 7.55 | 24,400 | 111,883 | 18,049 |
| 2100 | 6.89 | 21,762 | 154,124 | 25,522 |
| 2200 | 6.52 | 18,910 | 145,542 | 25,221 |
| 2300 | 5.08 | 16,460 | 107,902 | 24,468 |
| 2400 | 5.49 | 18,182 | 104,985 | 22,452 |
| 2500 | 4.99 | 17,949 | 96,998 | 23,038 |
| 2600 | 5.4 | 17,469 | 92,306 | 20,321 |
| 2700 | 4.12 | 14,480 | 58,890 | 17,804 |
| 2800 | 2.61 | 8,909 | 22,923 | 12,181 |
| 2900 | 1.39 | 4,369 | 6,836 | 8,090 |
| 3000 | 0.27 | 687 | 831 | 5,649 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 272 | 70.8 | 2026-11-25 |
| mid heights | yes | 25 | 8.8 | 2026-11-25 |
| far heights | yes | 16 | 2.6 | 2026-11-25 |
| mask | yes | 72 | 11.1 | 2026-11-25 |
| AO | yes | 72 | 4.6 | 2026-11-25 |
| piste directions | yes | 72 | 0.3 | 2026-11-25 |
| moguls | yes | 72 | 0.1 | 2026-11-25 |
| cover | yes | 4 | 15.0 | 2026-11-25 |
| trees (crowns) | yes | 70 | 4.9 | 2026-11-25 |
| stands (stems) | yes | 70 | 10.1 | 2026-11-25 |
| far tree ring | yes | 174 | 12.0 | 2026-11-25 |
| shrubs | yes | 72 | 0.2 | 2026-11-25 |
| rocks | yes | 71 | 0.9 | 2026-11-25 |
