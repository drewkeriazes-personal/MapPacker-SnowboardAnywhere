# Pack report: Beaver Creek Resort (Arrowhead Mountain) (`beaver-creek-resort-arrowhead-mountain`)

Build `20261125T043538Z-181ecf`, pipeline `3a50d0c`, format 1. Report 2026-11-25T04:35:52Z by `pipeline/pack_report.py` (FEAT-175).

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
| 5 | Heights fine, mid, far | ✅ | 2211 to 3617 m, void 0.00% inside the bounds |
| 6 | Surface: mask, AO, directions, moguls, rocks | ✅ | rock 1.9% (reference 1.1%), canopy 60% |
| 7 | Trees and shrubs with species | ✅ | 0.25 M crowns + 2.11 M stems = 30.4 k per km2 (78% of the reference) |
| 8 | Far terrain: cover levels pack, mid, far | ✅ | three levels |
| 8b | Far tree ring (crowns round the resort) | ✅ | 0.99 M crowns in 288 cells |
| 9 | features.json | ✅ | 25 lifts, 311 runs, 2571 buildings, 1657 roads, 54 water, 1251 peaks, 100 labels |
| 10 | Default start on a run, on snow, clear of trees | ✅ | generated (gen_content.py) on Red Buffalo, top of Cinch Express Lift |
| 11 | In the resort picker | ✅ | in packs/index.json, in the catalog |
| 12 | Time trial courses | ✅ | 126 runs of 300 m and 60 m drop or more |
| 13 | Attribution for every data set | ✅ | 9 lines |
| 14 | Validated | ⚠️ | 3 advanced+ runs never over 15 deg; ride from the start and views from the top not checked here (shoot.mjs) |
| | **Polish (not gated)** | | |
| 15 | Grooming history | ✅ | 51% of runs with a grooming record, 33 reports in raw; 78% of the green and blue run length groomed |
| 16 | Place names | ✅ | GNIS CO; 1251 peaks, 100 town labels |
| 17 | Main menu shot and ghosts | ⚠️ | generated (gen_content.py): 5 shots, no still of this build, 0 ghost takes (the game's tools/auto_attract.mjs makes them) |
| 18 | Landmark | ❌ | none (optional: resorts/beaver-creek-resort-arrowhead-mountain/landmarks.json) |
| 19 | Compare spots against photos | ➖ | no SnowboardAnywhere checkout at /home/runner/work/MapPacker-SnowboardAnywhere/SnowboardAnywhere (--game-repo or SBA_GAME_REPO) |
| 20 | Values derived for the resort, not copied from Vail | ✅ | treeline 3525 m measured; canopy.grow_ndvi 0.1224; canopy.leaf_ndvi 0.3296; canopy.veg_ndvi 0.2407; rock.bare_ndvi 0.2407; rock.dark 72.3333; rock.grey_sat 0.189; rock.ndvi 0.1503; treeline 3525 |
| 21 | Published figures | ✅ | 1 figures match (beavercreek.com terrain status, 2026-04-18; table below) |

## Numbers (reference: vail `20261111T145558Z-c2847e`)

| Measure | This pack | Reference |
|---|---:|---:|
| Area, km2 | 77.6 |  |
| Trees (crowns + stems) per km2 | 30,386 | 39,201 |
| Rock share | 1.9% | 1.1% |
| Canopy share | 60% | 66% |
| Canopy on run centre lines | 3.7% | 3.7% |
| Groomed share | 4.5% |  |
| Crowns per km within 5 m of lift lines | 9.5 |  |
| Stems per km within 5 m of lift lines | 0.0 |  |
| Runs with a grooming record | 51% |  |
| Runs groomed in OSM | 57% |  |
| Green and blue run length groomed | 78% |  |
| Groomed mask on groomed run centre lines | 97% |  |
| Far ring crowns | 993,258 |  |
| Mean mogulScore by difficulty | advanced 0.5, easy 0.0, expert 0.45, intermediate 0.1, none 0.0 | |

**Advanced or harder runs never over 15 deg:** West Fall Road (advanced, 7 deg), Upper Stone Creek (expert, 11 deg), Ripsaw (advanced, 12 deg)

**Lifts with the most crowns on the line:** Lower Beaver Creek Mountain Express Lift (45), Rose Bowl Express Lift (38), Centennial Express Lift (36), Upper Beaver Creek Mountain Express Lift (34), Arrow Bahn Express Lift (22)

## Published figures (gathered 2026-11-14 by published.py)

| Figure | Published | Source | This pack | | Note |
|---|---:|---|---:|---|---|
| Runs | 181 | beavercreek.com terrain status, 2026-04-18 | 163 | ✅ | 163 run names over 311 segments, 52 unnamed; of the 181 trails on beavercreek.com terrain status, 2026-04-18, 153 have an OSM run and 28 have none (the OSM to-do below: not mapped in OSM, or named differently); 28 OSM names are not on the list |

**OSM to-do: published trails with no OSM run** (28 of 181 on beavercreek.com terrain status, 2026-04-18). Map each one in OpenStreetMap (or fix its name there) and the next build has it; the link opens the editor where the trail's area's other runs are.

| Trail | Area | Difficulty | Where |
|---|---|---|---|
| 4 Get About It | Beaver Creek Lower | advanced | [edit](https://www.openstreetmap.org/edit#map=16/39.59127/-106.51229) |
| Anderson's Alley | Resort Skiways | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.61613/-106.53588) |
| BC Expressway - Lower | Larkspur | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.58465/-106.53660) |
| BC Expressway - Upper | Larkspur | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.58465/-106.53660) |
| Beginner Area Ch. #2 | Beaver Creek Lower | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.59127/-106.51229) |
| Big Bark/Little Bark | Beaver Creek Lower | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/39.59127/-106.51229) |
| Borders | Resort Skiways | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.61613/-106.53588) |
| Camp Robber RD | Grouse Mountain | advanced | [edit](https://www.openstreetmap.org/edit#map=16/39.57652/-106.52492) |
| Creekside | Resort Skiways | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.61613/-106.53588) |
| Gallagher Glade | Arrowhead | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/39.62205/-106.55600) |
| Golden Eagle Connector | Beaver Creek Lower | advanced | [edit](https://www.openstreetmap.org/edit#map=16/39.59127/-106.51229) |
| Larkspur - Lower | Larkspur | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/39.58465/-106.53660) |
| Larkspur - Upper | Larkspur | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/39.58465/-106.53660) |
| Latigo Flats | Beaver Creek Lower | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/39.59127/-106.51229) |
| Lumber Yard | Beaver Creek Lower | terrain park | [edit](https://www.openstreetmap.org/edit#map=16/39.59127/-106.51229) |
| Park 101 | Beaver Creek Upper | terrain park | [edit](https://www.openstreetmap.org/edit#map=16/39.58387/-106.50626) |
| Pines/Chateau | Resort Skiways | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.61613/-106.53588) |
| Primrose- BG to AH | Larkspur | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.58465/-106.53660) |
| Primrose- Straw. Park to BG | Strawberry Park | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.60119/-106.53081) |
| Primrose-Larkspur to Straw | Strawberry Park | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.60119/-106.53081) |
| Rhubarb | Resort Skiways | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.61613/-106.53588) |
| Ridgepoint | Resort Skiways | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.61613/-106.53588) |
| Ripperoo's Retreat | Rose Bowl | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.58468/-106.50026) |
| Saddleridge Skiway | Resort Skiways | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.61613/-106.53588) |
| Stone Creek Chutes | Rose Bowl | extreme | [edit](https://www.openstreetmap.org/edit#map=16/39.58468/-106.50026) |
| Toyota Race Center | Beaver Creek Lower | intermediate | [edit](https://www.openstreetmap.org/edit#map=16/39.59127/-106.51229) |
| Wampum | Resort Skiways | easy | [edit](https://www.openstreetmap.org/edit#map=16/39.61613/-106.53588) |
| Zoom Room | Beaver Creek Upper | terrain park | [edit](https://www.openstreetmap.org/edit#map=16/39.58387/-106.50626) |

## Trees by elevation band

| Band, m | Area, km2 | Crowns | Stems | Per km2 |
|---|---:|---:|---:|---:|
| 2200 | 6.73 | 8,384 | 49,370 | 8,580 |
| 2300 | 7.29 | 11,127 | 90,393 | 13,928 |
| 2400 | 7.83 | 19,244 | 162,798 | 23,250 |
| 2500 | 8.81 | 23,819 | 204,592 | 25,927 |
| 2600 | 7.78 | 24,630 | 236,457 | 33,572 |
| 2700 | 6.51 | 22,054 | 201,247 | 34,322 |
| 2800 | 6.23 | 21,684 | 205,449 | 36,455 |
| 2900 | 5.92 | 19,218 | 191,432 | 35,562 |
| 3000 | 5.25 | 19,597 | 184,616 | 38,882 |
| 3100 | 4.42 | 20,766 | 174,577 | 44,165 |
| 3200 | 4.2 | 22,990 | 183,127 | 49,033 |
| 3300 | 3.85 | 20,818 | 157,586 | 46,357 |
| 3400 | 1.91 | 9,432 | 58,680 | 35,659 |
| 3500 | 0.8 | 2,310 | 11,524 | 17,304 |

## Layers

| Layer | In meta | Files | MB | Modified |
|---|---|---:|---:|---|
| fine heights | yes | 304 | 81.9 | 2026-11-25 |
| mid heights | yes | 25 | 11.9 | 2026-11-25 |
| far heights | yes | 16 | 2.8 | 2026-11-25 |
| mask | yes | 80 | 8.3 | 2026-11-25 |
| AO | yes | 80 | 5.5 | 2026-11-25 |
| piste directions | yes | 80 | 0.4 | 2026-11-25 |
| moguls | yes | 80 | 0.2 | 2026-11-25 |
| cover | yes | 4 | 16.5 | 2026-11-25 |
| trees (crowns) | yes | 80 | 5.9 | 2026-11-25 |
| stands (stems) | yes | 80 | 11.4 | 2026-11-25 |
| far tree ring | yes | 288 | 23.8 | 2026-11-25 |
| shrubs | yes | 80 | 0.3 | 2026-11-25 |
| rocks | yes | 80 | 0.7 | 2026-11-25 |
