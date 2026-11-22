# Pack report: Park City Mountain (`park-city-mountain`)

Build `20261122T154834Z-ceb136`, pipeline `874dd77`, format 1. Report 2026-11-22T15:49:12Z by `pipeline/pack_report.py` (FEAT-175).

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
| 1 | Resort config | ✅ | EPSG:26912 (12N) |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ✅ | EVT, EVC and EVH; 7.2% of the forest in EVT classes the species rules don't name (west rules) |
| 5 | Heights fine, mid, far | ✅ | 1952 to 3174 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ✅ | rock 1.8% (reference 1.1%), canopy 24% |
| 7 | Trees and shrubs with species | ⚠️ | 0.25 M crowns + 1.17 M stems = 10.8 k per km2 (27% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.14 M crowns in 82 cells |
| 9 | features.json | ⚠️ | 40 runs without a difficulty; 41 lifts, 616 runs, 6190 buildings, 5063 roads, 94 water, 681 peaks, 146 labels |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on Panorama, top of Dreamscape |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 309 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | 14 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ✅ | 39% of runs with a grooming record, 43 reports in raw; 62% of the green and blue run length groomed |
| 16 | Place names | ✅ | GNIS UT, WY; 681 peaks, 146 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 6 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/park-city-mountain/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | no treeline: forested to the top of the box (measured); canopy.grow_ndvi 0.08; canopy.leaf_ndvi 0.3055; canopy.veg_ndvi 0.2; rock.bare_ndvi 0.2; rock.dark 81.6667; rock.grey_sat 0.05; rock.ndvi 0.0638 |
| 21 | Published figures | ✅ | 6 figures match (Wikipedia: Park City Mountain Resort; parkcitymountain.com terrain status, 2026-04-01; table below) |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 131.8 |  |
| Trees (crowns + stems) per km2 | 10,774 | 39,201 |
| Rock share | 1.8% | 1.1% |
| Canopy share | 24% | 66% |
| Canopy on run centre lines | 3.3% | 3.7% |
| Groomed share | 3.8% |  |
| Crowns per km within 5 m of lift lines | 9.6 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 39% |  |
| Runs groomed in OSM | 39% |  |
| Green and blue run length groomed | 62% |  |
| Groomed mask on groomed run centre lines | 99% |  |
| Far ring crowns | 142,813 |  |
| Mean mogulScore by difficulty | advanced 0.52, easy 0.0, expert 0.67, freeride 0.3, intermediate 0.09, none 0.0 | |

**Advanced or harder runs never over 15 deg:** Ligity Split (advanced, 8 deg), Barrel Roll Nordic Trail (advanced, 9 deg), Barrel Roll Nordic Trail (advanced, 9 deg), unnamed (expert, 10 deg), Farm Nordic Trail (advanced, 10 deg), Sleep Walker (advanced, 11 deg), Illusion (advanced, 11 deg), Pick Axe (freeride, 11 deg), and 6 more

**Lifts with the most crowns on the line:** Quicksilver Gondola (51), Payday Hi-Speed Six-Pack (39), Motherlode Express (34), Crescent Hi-Speed Quad (25), Bonanza Hi-Speed Six-Pack (25)

## Published figures (gathered 2026-11-13 by published.py)

| Figure | Published | Source | This pack | | Note |
|---|---:|---|---:|---|---|
| Summit | 3,056 m (10,026 ft) | Wikipedia: Park City Mountain Resort | 3,041 m (9,977 ft) | ✅ | highest of the lift stations, -15 m |
| Base | 2,103 m (6,900 ft) | Wikipedia: Park City Mountain Resort | 2,051 m (6,729 ft) | ✅ | lowest of the lift stations, -52 m |
| Vertical | 975 m (3,199 ft) | Wikipedia: Park City Mountain Resort | 990 m (3,248 ft) | ✅ | +15 m (+2%) |
| Lifts | 41 | Wikipedia: Park City Mountain Resort | 41 | ✅ | every lift (37 chairs and gondolas) |
| Runs | 324 | Wikipedia: Park City Mountain Resort | 416 | ✅ | 416 run names over 616 segments, 78 unnamed; 128% of the published count; of the 349 trails on parkcitymountain.com terrain status, 2026-04-01, 325 have an OSM run and 24 have none (the OSM to-do below: not mapped in OSM, or named differently); 95 OSM names are not on the list |
| Skiable area | 27.1 km2 (6,699 acres) | Wikipedia: Park City Mountain Resort | 28.1 km2 (6,939 acres) | ✅ | run lines widened 50 m each side, plus the area runs, 1.04 times the published |

**OSM to-do: published trails with no OSM run** (24 of 349 on parkcitymountain.com terrain status, 2026-04-01). Map each one in OpenStreetMap (or fix its name there) and the next build has it; the link opens the editor where the trail's area's other runs are.

| Trail | Area | Difficulty | Where |
|---|---|---|---|
| Alloy Alley | Payday/Town/Crescent | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/40.63950/-111.51395) |
| Berg's Bowl | Bonanza/McConkey's/Pioneer | expert | [edit](https://www.openstreetmap.org/edit#map=16/40.62106/-111.52639) |
| Bonanza Access | Payday/Town/Crescent | easy | [edit](https://www.openstreetmap.org/edit#map=16/40.63950/-111.51395) |
| Half Pipe | Payday/Town/Crescent | terrain park | [edit](https://www.openstreetmap.org/edit#map=16/40.63950/-111.51395) |
| Homerun (Full) | Bonanza/McConkey's/Pioneer | easy | [edit](https://www.openstreetmap.org/edit#map=16/40.62106/-111.52639) |
| King Con Access | King Con | easy | [edit](https://www.openstreetmap.org/edit#map=16/40.64743/-111.52104) |
| Ladies' Slalom | Payday/Town/Crescent | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/40.63950/-111.51395) |
| Lite's Out | Jupiter | expert | [edit](https://www.openstreetmap.org/edit#map=16/40.62353/-111.54750) |
| Little Kings | Bonanza/McConkey's/Pioneer | terrain park | [edit](https://www.openstreetmap.org/edit#map=16/40.62106/-111.52639) |
| Men's Slalom | Payday/Town/Crescent | advanced | [edit](https://www.openstreetmap.org/edit#map=16/40.63950/-111.51395) |
| Mid-Mountain | Bonanza/McConkey's/Pioneer | easy | [edit](https://www.openstreetmap.org/edit#map=16/40.62106/-111.52639) |
| Mid-Mountain Cutoff | Bonanza/McConkey's/Pioneer | easy | [edit](https://www.openstreetmap.org/edit#map=16/40.62106/-111.52639) |
| Mini Pipe | Payday/Town/Crescent | terrain park | [edit](https://www.openstreetmap.org/edit#map=16/40.63950/-111.51395) |
| OO2 | Day Break / Dreamscape / Dreamcatcher | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/40.65155/-111.56433) |
| One Hundred Turns | Condor | expert | [edit](https://www.openstreetmap.org/edit#map=16/40.69057/-111.58630) |
| Paradise Bowl | Peak 5/9990/Tombstone | advanced | [edit](https://www.openstreetmap.org/edit#map=16/40.66437/-111.57372) |
| Pinecone Bowl | Jupiter | expert | [edit](https://www.openstreetmap.org/edit#map=16/40.62353/-111.54750) |
| Rendezvous Bowl | Condor | advanced | [edit](https://www.openstreetmap.org/edit#map=16/40.69057/-111.58630) |
| Snowonder | Iron Mountain | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/40.65809/-111.54926) |
| Sweet Pea | OBX/Saddleback/Sun Peak | easy | [edit](https://www.openstreetmap.org/edit#map=16/40.68254/-111.57797) |
| The Chutes | Bonanza/McConkey's/Pioneer | expert | [edit](https://www.openstreetmap.org/edit#map=16/40.62106/-111.52639) |
| The Drain | OBX/Saddleback/Sun Peak | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/40.68254/-111.57797) |
| Tombstone Alley | Peak 5/9990/Tombstone | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/40.66437/-111.57372) |
| Tube | OBX/Saddleback/Sun Peak | advanced | [edit](https://www.openstreetmap.org/edit#map=16/40.68254/-111.57797) |

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 1900 | 7.1 | 4,096 | 27,356 | 4,430 |
| 2000 | 16.89 | 22,839 | 155,071 | 10,534 |
| 2100 | 10.55 | 17,563 | 123,270 | 13,347 |
| 2200 | 8.33 | 18,198 | 114,815 | 15,975 |
| 2300 | 8.41 | 18,486 | 105,599 | 14,747 |
| 2400 | 11.02 | 24,105 | 115,150 | 12,633 |
| 2500 | 13.21 | 28,084 | 123,154 | 11,449 |
| 2600 | 17.57 | 39,549 | 171,880 | 12,035 |
| 2700 | 17.94 | 35,367 | 133,024 | 9,384 |
| 2800 | 13.05 | 25,730 | 73,623 | 7,613 |
| 2900 | 6.36 | 10,918 | 22,879 | 5,316 |
| 3000 | 1.22 | 1,989 | 5,322 | 5,996 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 528 | 136.3 | 2026-11-22 |
| mid heights | yes | 25 | 11.7 | 2026-11-22 |
| far heights | yes | 16 | 2.3 | 2026-11-22 |
| mask | yes | 132 | 17.5 | 2026-11-22 |
| AO | yes | 132 | 8.8 | 2026-11-22 |
| piste directions | yes | 132 | 0.6 | 2026-11-22 |
| moguls | yes | 132 | 0.6 | 2026-11-22 |
| cover | yes | 4 | 15.6 | 2026-11-22 |
| trees (crowns) | yes | 124 | 5.9 | 2026-11-22 |
| stands (stems) | yes | 124 | 12.8 | 2026-11-22 |
| far tree ring | yes | 82 | 3.4 | 2026-11-22 |
| shrubs | yes | 119 | 0.3 | 2026-11-22 |
| rocks | yes | 140 | 1.5 | 2026-11-22 |
