# Pack report: Big Sky (`bigsky`)

Build `20261125T171011Z-b5534c`, pipeline `fe446d9`, format 1. Report 2026-11-25T17:10:50Z by `pipeline/pack_report.py`.

**Tier: gold** (the weakest layer's)

| Layer | Source | Tier |
|---|---|---|
| terrain | 3DEP 1 m | gold |
| trees | lidar crowns + stands | gold |
| surface | NAIP | gold |

**Playable**: every MVP line passes.

| # | Item | | Detail |
|---|---|---|---|
| F | Pack format current | ✅ | formatVersion 1 |
| 1 | Resort config | ✅ | EPSG:26912 (12N) |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ✅ | EVT, EVC and EVH; 0.0% of the forest in EVT classes the species rules don't name (west rules) |
| 5 | Heights fine, mid, far | ✅ | 1925 to 3405 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ⚠️ | rock 3.5% (reference 1.1%), canopy 57% : more rock than the reference by over 3x, check the thresholds |
| 7 | Trees and shrubs with species | ✅ | 0.46 M crowns + 2.54 M stems = 26.0 k per km2 (66% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.66 M crowns in 212 cells |
| 9 | features.json | ✅ | 40 lifts, 602 runs, 1367 buildings, 1443 roads, 43 water, 513 peaks, 58 labels (3 lifts with towers spaced by the pipeline, no OSM pylons) |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on Morningstar, top of Powder Seeker 6 |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 217 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | 15 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ❌ | 0% of runs with a grooming record, 0 reports in raw; 10% of the green and blue run length groomed (few groomers: a grooming source missing or its names not matched to OSM) |
| 16 | Place names | ✅ | GNIS ID, MT, WY; 513 peaks, 58 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/bigsky/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | treeline 2700 m measured; canopy.grow_ndvi 0.15; canopy.leaf_ndvi 0.5135; canopy.veg_ndvi 0.3615; rock.bare_ndvi 0.3615; rock.dark 35.0; rock.grey_sat 0.0833; rock.ndvi 0.18; treeline 2700 |
| 21 | Published figures | ✅ | 6 figures match (Wikipedia: Big Sky Resort; table below) |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 115.6 |  |
| Trees (crowns + stems) per km2 | 25,957 | 39,201 |
| Rock share | 3.5% | 1.1% |
| Canopy share | 57% | 66% |
| Canopy on run centre lines | 5.6% | 3.7% |
| Groomed share | 0.3% |  |
| Crowns per km within 5 m of lift lines | 11.8 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 0% |  |
| Runs groomed in OSM | 4% |  |
| Green and blue run length groomed | 10% |  |
| Groomed mask on groomed run centre lines | 87% |  |
| Far ring crowns | 662,746 |  |
| Mean mogulScore by difficulty | advanced 0.42, easy 0.0, expert 0.39, extreme 0.11, intermediate 0.14, none 0.0 | |

**Advanced or harder runs never over 15 deg:** Comet (advanced, 6 deg), unnamed (advanced, 8 deg), LRT Traverse (advanced, 10 deg), Summit (advanced, 10 deg), unnamed (advanced, 10 deg), Siberia (advanced, 10 deg), unnamed (advanced, 11 deg), Iron Horse (advanced, 12 deg), and 7 more

**Lifts with the most crowns on the line:** Highlands (48), One and Only (47), Southern Comfort (44), Ramcharger 8 - High Speed (44), Thunder Wolf (33)

## Published figures (gathered 2026-11-13 by published.py)

| Figure | Published | Source | This pack | | Note |
|---|---:|---|---:|---|---|
| Summit | 3,403 m (11,165 ft) | Wikipedia: Big Sky Resort | 3,402 m (11,161 ft) | ✅ | highest of the lift stations, -1 m |
| Base | 2,073 m (6,801 ft) | Wikipedia: Big Sky Resort | 2,078 m (6,818 ft) | ✅ | lowest of the lift stations, +5 m |
| Vertical | 1,326 m (4,350 ft) | Wikipedia: Big Sky Resort | 1,324 m (4,344 ft) | ✅ | -2 m (-0%) |
| Lifts | 40 | Wikipedia: Big Sky Resort | 40 | ✅ | every lift (28 chairs and gondolas) |
| Runs | 320 | Wikipedia: Big Sky Resort | 331 | ✅ | 331 run names over 602 segments, 142 unnamed; 103% of the published count |
| Skiable area | 23.7 km2 (5,849 acres) | Wikipedia: Big Sky Resort | 21.3 km2 (5,263 acres) | ✅ | run lines widened 50 m each side, plus the area runs, 0.90 times the published |

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 1900 | 0.62 | 2,453 | 4,811 | 11,694 |
| 2000 | 5.14 | 26,582 | 59,082 | 16,674 |
| 2100 | 11.65 | 51,352 | 236,309 | 24,690 |
| 2200 | 17.68 | 72,058 | 494,757 | 32,063 |
| 2300 | 19.48 | 82,168 | 583,008 | 34,143 |
| 2400 | 18.94 | 79,712 | 548,135 | 33,142 |
| 2500 | 16.35 | 69,192 | 413,139 | 29,500 |
| 2600 | 11.98 | 46,698 | 179,829 | 18,908 |
| 2700 | 5.99 | 18,793 | 19,551 | 6,402 |
| 2800 | 3.6 | 6,263 | 3,751 | 2,782 |
| 2900 | 1.99 | 1,455 | 450 | 959 |
| 3000 | 1.12 | 25 | 0 | 22 |
| 3100 | 0.57 | 0 | 0 | 0 |
| 3200 | 0.29 | 0 | 0 | 0 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 462 | 125.9 | 2026-11-25 |
| mid heights | yes | 25 | 11.6 | 2026-11-25 |
| far heights | yes | 16 | 2.5 | 2026-11-25 |
| mask | yes | 121 | 18.7 | 2026-11-25 |
| AO | yes | 121 | 8.8 | 2026-11-25 |
| piste directions | yes | 121 | 0.1 | 2026-11-25 |
| moguls | yes | 121 | 0.8 | 2026-11-25 |
| cover | yes | 4 | 19.8 | 2026-11-25 |
| trees (crowns) | yes | 121 | 11.0 | 2026-11-25 |
| stands (stems) | yes | 121 | 16.6 | 2026-11-25 |
| far tree ring | yes | 212 | 15.9 | 2026-11-25 |
| shrubs | yes | 121 | 1.8 | 2026-11-25 |
| rocks | yes | 121 | 2.0 | 2026-11-25 |
