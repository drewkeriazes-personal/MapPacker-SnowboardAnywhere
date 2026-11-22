# Pack report: Killington (`killington`)

Build `20261122T153453Z-1463c9`, pipeline `874dd77`, format 1. Report 2026-11-22T15:35:10Z by `pipeline/pack_report.py` (FEAT-175).

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
| 1 | Resort config | ⚠️ | EPSG:26918 (18N); no start_run |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ✅ | EVT, EVC and EVH; 0.6% of the forest in EVT classes the species rules don't name (east rules) |
| 5 | Heights fine, mid, far | ✅ | 309 to 1289 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ✅ | rock 0.1% (reference 1.1%), canopy 80% |
| 7 | Trees and shrubs with species | ✅ | 0.20 M crowns + 1.11 M stems = 24.7 k per km2 (63% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.73 M crowns in 199 cells |
| 9 | features.json | ⚠️ | 1 of 20 chairs and gondolas without towers; 26 lifts, 228 runs, 258 buildings, 347 roads, 9 water, 2994 peaks, 266 labels (1 lifts with towers spaced by the pipeline, no OSM pylons) |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on Great Northern, top of K-1 Express Gondola |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 118 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | canopy 16% on run centre lines (trail cuts missing?); 8 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ❌ | 0% of runs with a grooming record, 0 reports in raw; 79% of the green and blue run length groomed |
| 16 | Place names | ✅ | GNIS MA, NH, NY, VT; 2994 peaks, 266 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/killington/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | treeline 1200 m measured; canopy.grow_ndvi 0.08; canopy.leaf_ndvi 0.3; canopy.veg_ndvi 0.2185; rock.bare_ndvi 0.2185; rock.dark 88.0; rock.grey_sat 0.2; rock.ndvi 0.0927; treeline 1200 |
| 21 | Published figures | ✅ | 5 figures match (Wikipedia: Killington Ski Resort; table below) |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 52.9 |  |
| Trees (crowns + stems) per km2 | 24,748 | 39,201 |
| Rock share | 0.1% | 1.1% |
| Canopy share | 80% | 66% |
| Canopy on run centre lines | 15.8% | 3.7% |
| Groomed share | 2.8% |  |
| Crowns per km within 5 m of lift lines | 11.3 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 0% |  |
| Runs groomed in OSM | 36% |  |
| Green and blue run length groomed | 79% |  |
| Groomed mask on groomed run centre lines | 89% |  |
| Far ring crowns | 725,546 |  |
| Mean mogulScore by difficulty | advanced 0.36, easy 0.0, expert 0.51, freeride 0.26, intermediate 0.16, none 0.0, novice 0.0 | |

**Advanced or harder runs never over 15 deg:** OL Express (expert, 8 deg), Old Sunrise Trail (freeride, 9 deg), Nivis Walk (advanced, 9 deg), Conclusion (advanced, 11 deg), Horn (freeride, 11 deg), Cascade Runout (advanced, 12 deg), Old Sundog (freeride, 13 deg), Cascade Runout (advanced, 15 deg)

**Lifts with the most crowns on the line:** Snowshed Double (38), Canyon Quad (35), Snowshed Express Quad (34), K-1 Express Gondola (22), Superstar Express Six (20)

## Published figures (gathered 2026-11-14 by published.py)

| Figure | Published | Source | This pack | | Note |
|---|---:|---|---:|---|---|
| Summit | 1,293 m (4,242 ft) | Wikipedia: Killington Ski Resort | 1,262 m (4,140 ft) | ✅ | highest of the lift stations, -31 m |
| Base | 355 m (1,165 ft) | Wikipedia: Killington Ski Resort | 324 m (1,063 ft) | ✅ | lowest of the lift stations, -31 m |
| Vertical | 938 m (3,077 ft) | Wikipedia: Killington Ski Resort | 938 m (3,077 ft) | ✅ | +0 m (+0%) |
| Runs | 155 | Wikipedia: Killington Ski Resort | 164 | ✅ | 164 run names over 228 segments, 27 unnamed; 106% of the published count |
| Skiable area | 6.1 km2 (1,510 acres) | Wikipedia: Killington Ski Resort | 9.3 km2 (2,305 acres) | ✅ | run lines widened 50 m each side, plus the area runs, 1.53 times the published |

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 300 | 3.99 | 11,357 | 25,941 | 9,357 |
| 400 | 3.93 | 14,127 | 27,996 | 10,706 |
| 500 | 6.0 | 21,242 | 56,346 | 12,930 |
| 600 | 11.72 | 39,452 | 154,232 | 16,519 |
| 700 | 8.06 | 28,348 | 161,433 | 23,536 |
| 800 | 4.84 | 19,101 | 182,046 | 41,542 |
| 900 | 6.01 | 27,450 | 268,056 | 49,144 |
| 1000 | 5.22 | 26,613 | 166,421 | 36,989 |
| 1100 | 2.84 | 14,657 | 62,616 | 27,250 |
| 1200 | 0.25 | 773 | 1,688 | 9,743 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 224 | 58.1 | 2026-11-22 |
| mid heights | yes | 25 | 11.1 | 2026-11-22 |
| far heights | yes | 16 | 2.4 | 2026-11-22 |
| mask | yes | 56 | 4.0 | 2026-11-22 |
| AO | yes | 56 | 4.2 | 2026-11-22 |
| piste directions | yes | 56 | 0.3 | 2026-11-22 |
| moguls | yes | 56 | 0.2 | 2026-11-22 |
| cover | yes | 4 | 10.9 | 2026-11-22 |
| trees (crowns) | yes | 56 | 4.9 | 2026-11-22 |
| stands (stems) | yes | 56 | 9.0 | 2026-11-22 |
| far tree ring | yes | 199 | 17.4 | 2026-11-22 |
| shrubs | yes | 50 | 0.0 | 2026-11-22 |
| rocks | yes | 45 | 0.0 | 2026-11-22 |
