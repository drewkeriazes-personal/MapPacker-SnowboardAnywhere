# Pack report: Breckenridge (`breckenridge`)

Build `20261122T154313Z-28aa89`, pipeline `874dd77`, format 1. Report 2026-11-22T15:43:33Z by `pipeline/pack_report.py` (FEAT-175).

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
| 1 | Resort config | ✅ | EPSG:26913 (13N) |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ✅ | EVT, EVC and EVH; 0.0% of the forest in EVT classes the species rules don't name (west rules) |
| 5 | Heights fine, mid, far | ✅ | 2829 to 4223 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ⚠️ | rock 3.5% (reference 1.1%), canopy 48% : more rock than the reference by over 3x, check the thresholds (FEAT-175 step 2) |
| 7 | Trees and shrubs with species | ✅ | 0.32 M crowns + 2.50 M stems = 26.6 k per km2 (68% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 1.01 M crowns in 332 cells |
| 9 | features.json | ✅ | 37 lifts, 375 runs, 5463 buildings, 2528 roads, 163 water, 1337 peaks, 168 labels |
| 10 | Default start on a run, on snow, clear of trees | ✅ | Starts at the top of Imperial Bowl (placed, resorts/breckenridge/start.json), on Imperial Bowl |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 154 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | 13 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ✅ | 32% of runs with a grooming record, 36 reports in raw; 94% of the green and blue run length groomed |
| 16 | Place names | ✅ | GNIS CO; 1337 peaks, 168 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/breckenridge/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | treeline 3525 m measured; canopy.grow_ndvi 0.1187; canopy.leaf_ndvi 0.3796; canopy.veg_ndvi 0.2575; rock.bare_ndvi 0.2575; rock.dark 60.0; rock.grey_sat 0.2; rock.ndvi 0.1523; treeline 3525 |
| 21 | Published figures | ✅ | 6 figures match (Wikipedia: Breckenridge Ski Resort; breckenridge.com terrain status, 2026-04-01; table below) |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 106.0 |  |
| Trees (crowns + stems) per km2 | 26,584 | 39,201 |
| Rock share | 3.5% | 1.1% |
| Canopy share | 48% | 66% |
| Canopy on run centre lines | 4.8% | 3.7% |
| Groomed share | 3.1% |  |
| Crowns per km within 5 m of lift lines | 5.7 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 32% |  |
| Runs groomed in OSM | 56% |  |
| Green and blue run length groomed | 94% |  |
| Groomed mask on groomed run centre lines | 97% |  |
| Far ring crowns | 1,011,130 |  |
| Mean mogulScore by difficulty | advanced 0.43, easy 0.0, expert 0.75, extreme 0.36, intermediate 0.02, none 0.0 | |

**Advanced or harder runs never over 15 deg:** Elk Dance (advanced, 7 deg), North Bowl Traverse (advanced, 8 deg), Elk Dance (advanced, 9 deg), Tunnel (advanced, 10 deg), unnamed (advanced, 10 deg), Shock Hill (advanced, 11 deg), unnamed (advanced, 12 deg), Hoo Doo Voo Doo (advanced, 12 deg), and 5 more

**Lifts with the most crowns on the line:** BreckConnect Gondola (48), Snowflake (37), Peak 8 SuperConnect Lower (19), Freedom Superchair (12), Horseshoe Bowl T-Bar (11)

## Published figures (gathered 2026-11-13 by published.py)

| Figure | Published | Source | This pack | | Note |
|---|---:|---|---:|---|---|
| Summit | 3,962 m (12,999 ft) | Wikipedia: Breckenridge Ski Resort | 3,914 m (12,841 ft) | ✅ | highest of the lift stations, -48 m |
| Base | 2,926 m (9,600 ft) | Wikipedia: Breckenridge Ski Resort | 2,913 m (9,557 ft) | ✅ | lowest of the lift stations, -13 m |
| Vertical | 1,036 m (3,399 ft) | Wikipedia: Breckenridge Ski Resort | 1,001 m (3,284 ft) | ✅ | -35 m (-3%) |
| Lifts | 20 | Wikipedia: Breckenridge Ski Resort | 37 | ✅ | 23 chairs and gondolas match: the published count leaves out surface lifts (37 in all) |
| Runs | 187 | Wikipedia: Breckenridge Ski Resort | 253 | ✅ | 253 run names over 375 segments, 17 unnamed; 135% of the published count; of the 192 trails on breckenridge.com terrain status, 2026-04-01, 188 have an OSM run and 4 have none (the OSM to-do below: not mapped in OSM, or named differently); 66 OSM names are not on the list |
| Skiable area | 11.8 km2 (2,908 acres) | Wikipedia: Breckenridge Ski Resort | 17.6 km2 (4,352 acres) | ✅ | run lines widened 50 m each side, plus the area runs, 1.50 times the published |

**OSM to-do: published trails with no OSM run** (4 of 192 on breckenridge.com terrain status, 2026-04-01). Map each one in OpenStreetMap (or fix its name there) and the next build has it; the link opens the editor where the trail's area's other runs are.

| Trail | Area | Difficulty | Where |
|---|---|---|---|
| Freeway | Peak 8 | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/39.47514/-106.07377) |
| Freeway Terrain Park | Peak 8 | terrain park | [edit](https://www.openstreetmap.org/edit#map=16/39.47514/-106.07377) |
| Toyota Banked Slalom | Peak 8 | terrain park | [edit](https://www.openstreetmap.org/edit#map=16/39.47514/-106.07377) |
| Wonderland | Peak 6 | expert | [edit](https://www.openstreetmap.org/edit#map=16/39.49124/-106.10227) |

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 2800 | 3.69 | 7,633 | 37,961 | 12,355 |
| 2900 | 14.56 | 42,879 | 322,887 | 25,113 |
| 3000 | 17.84 | 67,828 | 599,493 | 37,397 |
| 3100 | 12.27 | 57,020 | 498,523 | 45,287 |
| 3200 | 9.58 | 48,156 | 403,278 | 47,126 |
| 3300 | 8.61 | 42,517 | 319,462 | 42,057 |
| 3400 | 7.96 | 33,401 | 234,771 | 33,685 |
| 3500 | 7.47 | 16,101 | 79,472 | 12,790 |
| 3600 | 7.87 | 2,285 | 5,235 | 955 |
| 3700 | 7.13 | 34 | 5 | 6 |
| 3800 | 4.9 | 76 | 0 | 16 |
| 3900 | 2.41 | 96 | 0 | 40 |
| 4000 | 1.3 | 64 | 0 | 49 |
| 4100 | 0.36 | 33 | 0 | 91 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 420 | 108.4 | 2026-11-22 |
| mid heights | yes | 25 | 11.6 | 2026-11-22 |
| far heights | yes | 16 | 2.7 | 2026-11-22 |
| mask | yes | 110 | 10.5 | 2026-11-22 |
| AO | yes | 110 | 7.7 | 2026-11-22 |
| piste directions | yes | 110 | 0.4 | 2026-11-22 |
| moguls | yes | 110 | 0.5 | 2026-11-22 |
| cover | yes | 4 | 17.9 | 2026-11-22 |
| trees (crowns) | yes | 120 | 7.6 | 2026-11-22 |
| stands (stems) | yes | 111 | 12.5 | 2026-11-22 |
| far tree ring | yes | 332 | 24.3 | 2026-11-22 |
| shrubs | yes | 120 | 0.6 | 2026-11-22 |
| rocks | yes | 111 | 1.5 | 2026-11-22 |
