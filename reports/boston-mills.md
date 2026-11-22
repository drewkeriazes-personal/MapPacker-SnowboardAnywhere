# Pack report: Boston Mills / Brandywine (`boston-mills`)

Build `20261122T163143Z-0b01b7`, pipeline `620c171`, format 1. Report 2026-11-22T16:31:55Z by `pipeline/pack_report.py` (FEAT-175).

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
| 1 | Resort config | ⚠️ | EPSG:26917 (17N); no start_run |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ✅ | EVT, EVC and EVH; 0.0% of the forest in EVT classes the species rules don't name (east rules) |
| 5 | Heights fine, mid, far | ✅ | 194 to 294 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ✅ | rock 0.1% (reference 1.1%), canopy 70% |
| 7 | Trees and shrubs with species | ⚠️ | 0.01 M crowns + 0.03 M stems = 10.0 k per km2 (25% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.54 M crowns in 238 cells |
| 9 | features.json | ⚠️ | 3 runs without a difficulty; 16 lifts, 20 runs, 84 buildings, 574 roads, 42 water, 68 peaks, 445 labels |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on Buttermilk, top of Lift 2 |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 11 runs of 150 m and 30 m drop or more |
| 13 | Attribution for every data set | ✅ | 10 lines |
| 14 | Validated | ⚠️ | 3 advanced+ runs never over 15 deg; 24 crowns per km within 5 m of lift lines; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ❌ | 0% of runs with a grooming record, 0 reports in raw; 19% of the green and blue run length groomed (few groomers: a grooming source missing or its names not matched to OSM, FEAT-256) |
| 16 | Place names | ✅ | GNIS MI, OH, PA, WV; 68 peaks, 445 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/boston-mills/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | no treeline: forested to the top of the box (measured); canopy.grow_ndvi 0.25; canopy.leaf_ndvi 0.45; canopy.veg_ndvi 0.4276; rock.bare_ndvi 0.4276; rock.dark 67.6667; rock.grey_sat 0.1075; rock.ndvi 0.25; Brandywine relocated (turned -25 deg, height shift +3.0 m) |
| 21 | Published figures | ✅ | 4 figures match (Wikipedia: Boston Mills/Brandywine Ski Resorts; table below) |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 3.8 |  |
| Trees (crowns + stems) per km2 | 9,956 | 39,201 |
| Rock share | 0.1% | 1.1% |
| Canopy share | 70% | 66% |
| Canopy on run centre lines | 0.6% | 3.7% |
| Groomed share | 0.4% |  |
| Crowns per km within 5 m of lift lines | 23.5 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 0% |  |
| Runs groomed in OSM | 15% |  |
| Green and blue run length groomed | 19% |  |
| Groomed mask on groomed run centre lines | 97% |  |
| Far ring crowns | 542,598 |  |
| Mean mogulScore by difficulty | advanced 0.45, easy 0.0, intermediate 0.06, none 0.0, novice 0.0 | |

**Advanced or harder runs never over 15 deg:** North Bowl (advanced, 12 deg), Champagne (advanced, 14 deg), Croyle (advanced, 14 deg)

**Lifts with the most crowns on the line:** Lift 1 (24), Lift 5 (12), Lift 2 (12), Ram Quad (7), Lift 3 (5)

## Published figures (gathered 2026-11-13 by published.py)

| Figure | Published | Source | This pack | | Note |
|---|---:|---|---:|---|---|
| Vertical | 73 m (240 ft) | Wikipedia: Boston Mills/Brandywine Ski Resorts | 70 m (230 ft) | ✅ | -3 m (-4%) |
| Lifts | 15 | Wikipedia: Boston Mills/Brandywine Ski Resorts | 16 | ✅ | every lift (11 chairs and gondolas) |
| Runs | 18 | Wikipedia: Boston Mills/Brandywine Ski Resorts | 18 | ✅ | 18 run names over 20 segments, 1 unnamed; 100% of the published count |
| Skiable area | 0.3 km2 (79 acres) | Wikipedia: Boston Mills/Brandywine Ski Resorts | 0.3 km2 (84 acres) | ✅ | run lines widened 50 m each side, plus the area runs, 1.06 times the published |

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 100 | 0.54 | 888 | 3,107 | 7,459 |
| 200 | 3.26 | 8,446 | 25,392 | 10,391 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 16 | 3.7 | 2026-11-22 |
| mid heights | yes | 25 | 9.7 | 2026-11-22 |
| far heights | yes | 16 | 1.3 | 2026-11-22 |
| mask | yes | 4 | 0.3 | 2026-11-22 |
| AO | yes | 4 | 0.3 | 2026-11-22 |
| piste directions | yes | 4 | 0.0 | 2026-11-22 |
| moguls | yes | 4 | 0.0 | 2026-11-22 |
| cover | yes | 4 | 8.7 | 2026-11-22 |
| trees (crowns) | yes | 4 | 0.2 | 2026-11-22 |
| stands (stems) | yes | 4 | 0.5 | 2026-11-22 |
| far tree ring | yes | 238 | 13.0 | 2026-11-22 |
| shrubs | yes | 3 | 0.0 | 2026-11-22 |
| rocks | yes | 4 | 0.0 | 2026-11-22 |
