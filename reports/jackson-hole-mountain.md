# Pack report: Jackson Hole Mountain (`jackson-hole-mountain`)

Build `20261125T043452Z-0c3d9f`, pipeline `3a50d0c`, format 1. Report 2026-11-25T04:35:02Z by `pipeline/pack_report.py` (FEAT-175).

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
| 1 | Resort config | ⚠️ | EPSG:26912 (12N); no start_run |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ✅ | EVT, EVC and EVH; 0.0% of the forest in EVT classes the species rules don't name (west rules) |
| 5 | Heights fine, mid, far | ✅ | 1908 to 3270 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ⚠️ | rock 10.2% (reference 1.1%), canopy 33% : more rock than the reference by over 3x, check the thresholds (FEAT-175 step 2) |
| 7 | Trees and shrubs with species | ⚠️ | 0.08 M crowns + 0.31 M stems = 10.5 k per km2 (27% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.22 M crowns in 121 cells |
| 9 | features.json | ✅ | 17 lifts, 262 runs, 644 buildings, 1051 roads, 26 water, 614 peaks, 53 labels |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on East Ridge Traverse, top of Aerial Tram |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 114 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | 6 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ❌ | 0% of runs with a grooming record, 0 reports in raw; 15% of the green and blue run length groomed (few groomers: a grooming source missing or its names not matched to OSM, FEAT-256) |
| 16 | Place names | ✅ | GNIS ID, MT, WY; 614 peaks, 53 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/jackson-hole-mountain/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | treeline 2525 m measured; canopy.grow_ndvi 0.1205; canopy.leaf_ndvi 0.3889; canopy.veg_ndvi 0.3; rock.bare_ndvi 0.3; rock.dark 65.3333; rock.grey_sat 0.1375; rock.ndvi 0.18; treeline 2525 |
| 21 | Published figures | ➖ | no English Wikipedia article with an Infobox ski area for Jackson Hole Mountain Resort |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 37.0 |  |
| Trees (crowns + stems) per km2 | 10,491 | 39,201 |
| Rock share | 10.2% | 1.1% |
| Canopy share | 33% | 66% |
| Canopy on run centre lines | 5.1% | 3.7% |
| Groomed share | 0.9% |  |
| Crowns per km within 5 m of lift lines | 13.5 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 0% |  |
| Runs groomed in OSM | 18% |  |
| Green and blue run length groomed | 15% |  |
| Groomed mask on groomed run centre lines | 100% |  |
| Far ring crowns | 217,541 |  |
| Mean mogulScore by difficulty | advanced 0.37, easy 0.0, expert 0.41, extreme 0.21, freeride 0.26, intermediate 0.12 | |

**Advanced or harder runs never over 15 deg:** unnamed (advanced, 10 deg), Expert Chutes (expert, 11 deg), unnamed (freeride, 12 deg), Secret Slope (advanced, 13 deg), Cirque (advanced, 14 deg), Rock Springs Upper Traverse (freeride, 15 deg)

**Lifts with the most crowns on the line:** Bridger Gondola (83), Teton Lift (31), Apres Vous High Speed Quad (23), Marmot Double (18), Aerial Tram (17)

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 1900 | 8.97 | 12,573 | 105,657 | 13,180 |
| 2000 | 2.54 | 8,300 | 67,566 | 29,915 |
| 2100 | 1.88 | 5,198 | 26,516 | 16,883 |
| 2200 | 2.2 | 5,436 | 21,545 | 12,244 |
| 2300 | 2.85 | 7,530 | 26,965 | 12,110 |
| 2400 | 3.31 | 9,581 | 22,901 | 9,802 |
| 2500 | 3.09 | 7,915 | 19,614 | 8,911 |
| 2600 | 2.73 | 6,467 | 10,526 | 6,232 |
| 2700 | 2.47 | 4,189 | 5,589 | 3,951 |
| 2800 | 3.06 | 4,804 | 4,639 | 3,085 |
| 2900 | 2.39 | 2,189 | 1,134 | 1,388 |
| 3000 | 1.16 | 846 | 927 | 1,522 |
| 3100 | 0.33 | 45 | 26 | 215 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 156 | 40.5 | 2026-11-25 |
| mid heights | yes | 25 | 11.1 | 2026-11-25 |
| far heights | yes | 16 | 2.5 | 2026-11-25 |
| mask | yes | 42 | 6.2 | 2026-11-25 |
| AO | yes | 42 | 3.0 | 2026-11-25 |
| piste directions | yes | 42 | 0.1 | 2026-11-25 |
| moguls | yes | 42 | 0.4 | 2026-11-25 |
| cover | yes | 4 | 9.9 | 2026-11-25 |
| trees (crowns) | yes | 42 | 1.8 | 2026-11-25 |
| stands (stems) | yes | 41 | 3.6 | 2026-11-25 |
| far tree ring | yes | 121 | 5.2 | 2026-11-25 |
| shrubs | yes | 42 | 0.5 | 2026-11-25 |
| rocks | yes | 39 | 1.6 | 2026-11-25 |
