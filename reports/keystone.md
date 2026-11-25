# Pack report: Keystone (`keystone`)

Build `20261125T044240Z-35db2c`, pipeline `3a50d0c`, format 1. Report 2026-11-25T04:43:03Z by `pipeline/pack_report.py` (FEAT-175).

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
| 5 | Heights fine, mid, far | ✅ | 2804 to 3845 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ✅ | rock 0.9% (reference 1.1%), canopy 67% |
| 7 | Trees and shrubs with species | ✅ | 0.30 M crowns + 2.42 M stems = 38.0 k per km2 (97% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.93 M crowns in 280 cells |
| 9 | features.json | ✅ | 20 lifts, 200 runs, 525 buildings, 644 roads, 38 water, 1326 peaks, 202 labels (1 lifts with towers spaced by the pipeline, no OSM pylons) |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on Ten Mile, top of Bergman Express |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 125 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | 7 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ✅ | 38% of runs with a grooming record, 24 reports in raw; 86% of the green and blue run length groomed |
| 16 | Place names | ✅ | GNIS CO; 1326 peaks, 202 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/keystone/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | treeline 3575 m measured; canopy.grow_ndvi 0.1067; canopy.leaf_ndvi 0.3659; canopy.veg_ndvi 0.2582; rock.bare_ndvi 0.2582; rock.dark 60.0; rock.grey_sat 0.2; rock.ndvi 0.1315; treeline 3575 |
| 21 | Published figures | ✅ | 6 figures match (Wikipedia: Keystone Resort; table below) |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 71.5 |  |
| Trees (crowns + stems) per km2 | 37,986 | 39,201 |
| Rock share | 0.9% | 1.1% |
| Canopy share | 67% | 66% |
| Canopy on run centre lines | 5.5% | 3.7% |
| Groomed share | 2.9% |  |
| Crowns per km within 5 m of lift lines | 7.5 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 38% |  |
| Runs groomed in OSM | 48% |  |
| Green and blue run length groomed | 86% |  |
| Groomed mask on groomed run centre lines | 98% |  |
| Far ring crowns | 934,958 |  |
| Mean mogulScore by difficulty | advanced 0.54, easy 0.0, extreme 0.17, intermediate 0.1, novice 0.0 | |

**Advanced or harder runs never over 15 deg:** unnamed (advanced, 4 deg), sampler (advanced, 7 deg), Coyote Caper (advanced, 10 deg), to lower go devil (advanced, 11 deg), Richter (advanced, 11 deg), Coyote Caper (advanced, 12 deg), Park Lane (advanced, 15 deg)

**Lifts with the most crowns on the line:** River Run Gondola (37), Outpost Gondola (31), Summit Express (26), Wayback (16), Santiago Express (10)

## Published figures (gathered 2026-11-13 by published.py)

| Figure | Published | Source | This pack | | Note |
|---|---:|---|---:|---|---|
| Summit | 3,782 m (12,408 ft) | Wikipedia: Keystone Resort | 3,742 m (12,277 ft) | ✅ | highest of the lift stations, -40 m |
| Base | 2,829 m (9,281 ft) | Wikipedia: Keystone Resort | 2,829 m (9,281 ft) | ✅ | lowest of the lift stations, +0 m |
| Vertical | 953 m (3,127 ft) | Wikipedia: Keystone Resort | 913 m (2,995 ft) | ✅ | -40 m (-4%) |
| Lifts | 21 | Wikipedia: Keystone Resort | 20 | ✅ | every lift (13 chairs and gondolas) |
| Runs | 135 | Wikipedia: Keystone Resort | 149 | ✅ | 149 run names over 200 segments, 36 unnamed; 110% of the published count |
| Skiable area | 12.7 km2 (3,148 acres) | Wikipedia: Keystone Resort | 10.2 km2 (2,516 acres) | ✅ | run lines widened 50 m each side, plus the area runs, 0.80 times the published |

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 2800 | 5.04 | 13,110 | 93,682 | 21,179 |
| 2900 | 6.29 | 28,745 | 246,873 | 43,824 |
| 3000 | 7.95 | 37,739 | 326,303 | 45,798 |
| 3100 | 7.95 | 40,698 | 355,104 | 49,774 |
| 3200 | 9.98 | 52,501 | 437,169 | 49,044 |
| 3300 | 10.52 | 56,940 | 464,350 | 49,540 |
| 3400 | 8.26 | 41,097 | 329,629 | 44,908 |
| 3500 | 7.12 | 23,048 | 163,912 | 26,261 |
| 3600 | 5.49 | 1,487 | 5,054 | 1,192 |
| 3700 | 2.76 | 38 | 6 | 16 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 300 | 75.6 | 2026-11-25 |
| mid heights | yes | 25 | 11.7 | 2026-11-25 |
| far heights | yes | 16 | 2.7 | 2026-11-25 |
| mask | yes | 80 | 5.3 | 2026-11-25 |
| AO | yes | 80 | 4.8 | 2026-11-25 |
| piste directions | yes | 80 | 0.2 | 2026-11-25 |
| moguls | yes | 80 | 0.2 | 2026-11-25 |
| cover | yes | 4 | 15.6 | 2026-11-25 |
| trees (crowns) | yes | 80 | 7.1 | 2026-11-25 |
| stands (stems) | yes | 78 | 10.4 | 2026-11-25 |
| far tree ring | yes | 280 | 22.4 | 2026-11-25 |
| shrubs | yes | 79 | 0.3 | 2026-11-25 |
| rocks | yes | 77 | 0.3 | 2026-11-25 |
