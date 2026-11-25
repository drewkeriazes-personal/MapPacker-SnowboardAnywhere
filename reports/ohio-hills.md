# Pack report: Ohio Hills (custom mashup) (`ohio-hills`)

Build `20261125T044457Z-9d6f58`, pipeline `3a50d0c`, format 1. Report 2026-11-25T04:45:07Z by `pipeline/pack_report.py` (FEAT-175).

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
| 1 | Resort config | ✅ | EPSG:26917 (17N) |
| 2 | Raw: DEMs, lidar, NAIP, Mapterhorn, OSM | ✅ | all present |
| 3 | Raw: land cover and pistes_wide | ✅ | all present |
| 4 | Raw: LANDFIRE | ✅ | EVT, EVC and EVH; 0.0% of the forest in EVT classes the species rules don't name (east rules) |
| 5 | Heights fine, mid, far | ✅ | 194 to 309 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ✅ | rock 0.0% (reference 1.1%), canopy 67% |
| 7 | Trees and shrubs with species | ⚠️ | 0.01 M crowns + 0.04 M stems = 10.3 k per km2 (26% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.54 M crowns in 238 cells |
| 9 | features.json | ⚠️ | 3 runs without a difficulty; 27 lifts, 34 runs, 94 buildings, 579 roads, 43 water, 68 peaks, 445 labels |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on Outer Limits, top of Ram Quad |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 18 runs of 216 m and 43 m drop or more |
| 13 | Attribution for every data set | ✅ | 13 lines |
| 14 | Validated | ⚠️ | 8 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ❌ | 0% of runs with a grooming record, 0 reports in raw; 10% of the green and blue run length groomed (few groomers: a grooming source missing or its names not matched to OSM, FEAT-256) |
| 16 | Place names | ✅ | GNIS MI, OH, PA, WV; 68 peaks, 445 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/ohio-hills/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | no treeline: forested to the top of the box (measured); canopy.grow_ndvi 0.25; canopy.leaf_ndvi 0.5288; canopy.veg_ndvi 0.45; rock.bare_ndvi 0.45; rock.dark 63.6667; rock.grey_sat 0.1124; rock.ndvi 0.25; Brandywine relocated (turned -25 deg, height shift +3.0 m); Mad River Mountain relocated (turned -90 deg, height shift -135.6 m) |
| 21 | Published figures | ➖ | a mashup: Mad River Mountain is pasted in from another resort's data, so no one resort's figures fit |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 5.3 |  |
| Trees (crowns + stems) per km2 | 10,255 | 39,201 |
| Rock share | 0.0% | 1.1% |
| Canopy share | 67% | 66% |
| Canopy on run centre lines | 3.2% | 3.7% |
| Groomed share | 0.4% |  |
| Crowns per km within 5 m of lift lines | 15.2 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 0% |  |
| Runs groomed in OSM | 12% |  |
| Green and blue run length groomed | 10% |  |
| Groomed mask on groomed run centre lines | 88% |  |
| Far ring crowns | 538,212 |  |
| Mean mogulScore by difficulty | advanced 0.42, easy 0.0, freeride 0.0, intermediate 0.06, none 0.0, novice 0.0 | |

**Advanced or harder runs never over 15 deg:** L.V.L.P (freeride, 7 deg), Captial Park (freeride, 11 deg), Kicker Lane (freeride, 11 deg), Sidewinder Glades (advanced, 11 deg), North Bowl (advanced, 12 deg), Champagne (advanced, 14 deg), Sugarbush (advanced, 14 deg), Croyle (advanced, 14 deg)

**Lifts with the most crowns on the line:** Lift 1 (21), Lift 2 (9), Lift 5 (8), Ram Quad (7), Fourstar Express (7)

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 100 | 0.53 | 871 | 2,945 | 7,154 |
| 200 | 4.76 | 11,787 | 38,904 | 10,638 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 24 | 5.2 | 2026-11-25 |
| mid heights | yes | 25 | 9.7 | 2026-11-25 |
| far heights | yes | 16 | 1.3 | 2026-11-25 |
| mask | yes | 6 | 0.4 | 2026-11-25 |
| AO | yes | 6 | 0.4 | 2026-11-25 |
| piste directions | yes | 6 | 0.0 | 2026-11-25 |
| moguls | yes | 6 | 0.0 | 2026-11-25 |
| cover | yes | 4 | 8.9 | 2026-11-25 |
| trees (crowns) | yes | 6 | 0.3 | 2026-11-25 |
| stands (stems) | yes | 6 | 0.7 | 2026-11-25 |
| far tree ring | yes | 238 | 12.9 | 2026-11-25 |
| shrubs | yes | 5 | 0.0 | 2026-11-25 |
| rocks | yes | 5 | 0.0 | 2026-11-25 |
