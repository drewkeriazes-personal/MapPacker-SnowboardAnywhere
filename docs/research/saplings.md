# Saplings and young conifers (FEAT-357)

Why Vail's tree records hold nothing under 2.65 m, whether a lower lidar floor would find real saplings, and where
small trees should come from instead. Measured 2026-11-23 on Vail's raw data (`build_pack.py` run to the end of
stage 5, the pipeline-grid-dump approach, about 3 minutes a run) at the 18 Street View spots in the game's
`docs/compare/vail/`, once on today's depth-9 lidar and once with DATA-011's deep pilot (depth 10 and 11 nodes within
150 m of seven spots, `raw/vail/ept_deep_pilot/`, 8 to 15 times the points).

## The cause

Three rules in `pipeline/build_pack.py` (line numbers at 5d2d9f1), all on purpose:

1. **The crown detector's floor.** `peaks_mask = (chm_s == maxf) & (chm_s > 2.5) & canopy` (line 1205): a crown is a
   local maximum over 3 x 3 cells (6 m) of the CHM smoothed with a 0.8 cell Gaussian, and it must be over 2.5 m.
2. **The crown's height is the tallest return round it.** `chm_top = ndimage.maximum_filter(chm, size=3)` (line 1215,
   BUG-023), and the CHM there has had a 3 x 3 grey closing (line 362). The unsmoothed maximum is never below the
   smoothed value, so a crown kept at 2.5 m smoothed comes out a little taller: 2.65 m is the lowest of Vail's 521,225.
3. **The canopy mask** the crowns must sit in (line 456) wants `chm > 2.5`, or `chm > 1.2` with leafy NDVI. It lets
   some 1.2 to 2.5 m cells in, but rule 1 still drops their peaks.

The generated stems have a floor too: stand height `h4 = np.clip(h4, 3.0, 45.0)` (line 1343), drawn 0.75 to 1 times
that in the game (`stands.ts`), so no stem is under 2.25 m. Not causes: the krummholz rule (`species.py:463`) only
relabels trees the lidar measured at 1 to 4 m near treeline, it drops nothing; `packwriter.py` clamps no height.

The floor is there because the CHM is the highest return in a 2 m cell minus the mean 1 m DEM: on a steep slope that
difference alone reaches 1 to 2 m (the comment at line 453), and buildings, lift towers, rocks and stray returns read
1 to 2.5 m too.

## Would a lower floor find saplings?

Local maxima of the smoothed CHM by height, the whole Vail pack (33.9 M cells of 2 m, 136 km2):

| peak height | all peaks | in the canopy mask | on vegetated ground (NDVI > 0.30) | of those, slope > 30 deg | on bare ground (NDVI < 0.30) |
|---|---|---|---|---|---|
| 1.0 to 1.5 m | 10,416 | 1,608 | 1,870 | 588 | 8,512 |
| 1.5 to 2.0 m | 7,556 | 2,446 | 1,883 | 569 | 5,631 |
| 2.0 to 2.5 m | 6,212 | 3,024 | 1,845 | 557 | 4,320 |
| over 2.5 m (today's crowns) | 537,838 | 503,903 | 331,517 | 69,371 | 200,745 |

(The canopy mask and the vegetated set overlap but are not the same: the mask also takes BUG-028's grey crowns.)

- Lowering the floor to 1 m inside the canopy mask adds **7,078 crowns, 1.4 %** of today's. Most of the 24,184
  peaks between 1 and 2.5 m (**76 %**) are on bare, unvegetated cells: noise, rock, roofs, the slope artefact.
- The deep pilot changes nothing. At the 12 spots it reaches, with 0.9 to 5.3 returns per m2 instead of 0.2 to 0.5, 83 to
  100 % of the 2 m cells have a return (was 66 to 82 %), yet the 1 to 2.5 m peaks on vegetated ground per hectare of the 150 m disc stay at 0 to 0.5
  (Mid-Vail 0.1 to 0.5, Prima 0 to 0, The Divide 0.4 to 0.2, Born Free 0 to 0), and the peaks on bare ground go
  up (Prima 0.4 to 3.8 per ha at 1 to 1.5 m). The pack-wide counts move by under 1 % because the pilot covers so
  little.
- Single 2 m cells reading 1 to 2.5 m (no closing, no smoothing): 0 to 4 % of the open vegetated cells at a spot,
  and about the same share of the bare flat cells (0 to 5 %; 1 to 60 % on bare ground over 30 deg). So a short
  return over open vegetation is about as likely to be noise as a plant, and willow, juniper and oak are in the same
  height range anyway.
- Against the Street View pairs: the one spot whose notes describe short trees, **Blue Sky In the Wuides** ("a scatter
  of short, bushy, snow-dusted conifers within a few tens of metres", 1 tree in the pack within 15 m), is also the
  spot with the most 1 to 2.5 m peaks on vegetated ground, 2.4 per ha (17 in the 7.1 ha disc). It also has 4.9 per ha
  of the same peaks on bare ground, and no deep pilot points. The other notes ask for more tall trees (BUG-023), not
  small ones.
- Under closed canopy the detector can't see a sapling at any density: the 2 m DSM keeps the highest return in the
  cell, and the 6 m maximum filter folds a small top into the crown beside it.

So a lower floor finds a few thousand bumps, most of them not trees, and the trees among them can't be told from
shrubs. Nor does density fix it at the 2 m grid, as DATA-011 found for the tall crowns.

## Literature

- Naesset and Nelson (2007), *Using airborne laser scanning to monitor tree migration in the boreal-alpine transition
  zone*, Remote Sensing of Environment 110: 357 to 369. At about 7.7 points per m2, over 90 % of trees 1 m or taller
  had echoes above the ground, while for trees under 1 m it was 5 to 73 %. Commission errors reached up to 490 % with a
  commonly smoothed terrain model (as summarised in [Remote Sens. 8(7):548](https://mdpi.com/2072-4292/8/7/548) and
  [Remote Sens. 6(10):10152](https://mdpi.com/2072-4292/6/10/10152)). Vail's depth-9 cloud is a tenth to a twentieth of that.
- Stumberg et al. (2014), forest-tundra ecotone: 46 % of small trees detected overall, 80 % over 3 m (as cited in
  [Remote Sens. 8(5):407](https://api.crossref.org/works/10.3390%2FRS8050407)).
- Imangholiloo et al. (2020), *Using Leaf-Off and Leaf-On Multispectral Airborne Laser Scanning Data to Characterize
  Seedling Stands*, [Remote Sens. 12(20):3328](https://doi.org/10.3390/rs12203328): seedling stand density and height
  became usable only at about 57 to 60 points per m2 (Norway spruce density best at a 0.4 m threshold, still 38 % rRMSE),
  and earlier work at 1 to 15 points per m2 underestimated seedling heights.
- [Identifying regenerated saplings by stratifying the overstory](https://spj.science.org/doi/10.34133/plantphenomics.0145)
  (Plant Phenomics): point density is the limit on understory saplings, which come out too short, the shortest most.
  Hamraz et al. ([arXiv 1802.08872](https://arxiv.org/pdf/1802.08872)) classified understory conifers at 69 % (understory
  deciduous 92 %), because the cloud catches only part of an understory crown.
- Regeneration in Rocky Mountain spruce-fir: spruce seedlings mostly in gaps or next to fir, fir also under canopy,
  strongly clumped ([Demographic Aspects of Coexistence in Engelmann Spruce and Subalpine Fir](https://digitalcommons.usu.edu/barkbeetles/30));
  after the beetle at Fraser Experimental Forest, subalpine fir regeneration of 2,870 to 4,690 stems per ha, most of
  it small (Pelz et al. 2018, [Forests 9(9):536](https://www.mdpi.com/1999-4907/9/9/536); figures from the search
  summary, the full text was not readable here). Most of those stems are under a metre and sit under the snowpack in
  winter.

The pattern: airborne lidar finds trees from about 1 m only at 5 to 10+ points per m2 and with ground models tuned for
it, and saplings under a canopy stay out of reach. USGS 3DEP QL2 (2 points per m2 nominal) at full depth would not
be enough, and the pack fetches a few tenths of a point per m2.

## Pick: generate saplings in the game, per stand, at load

Keep the lidar floor. Generate young conifers at load from the `stands/` image the game already has, like FEAT-074's
stems: a seeded hash per 4 m cell, more where the stand is open (gaps, glade edges, sparse stands), few under closed
canopy, none off the stand.

- **Where it lives:** a game card (EPIC-01). The chance a sapling stands in a cell comes from the stem chance round
  it (R over about 20 m): low, but not zero, where the stand is full, highest where it is half open, none where no
  cell nearby has a stem (runs, built ground and cliffs are already 0 in the image). Species from the image's species
  byte (spruce or fir, lodgepole in lodgepole stands; aspen and hardwood none), height 0.5 to 3 m, weighted
  short. Hand them to the shrubs' young-conifer path (`Shrubs.ts`), which already draws them with the kit's LOD1
  spruce and fir, buries them in the snowpack and gives one standing over 1.5 m above the snow a trunk to hit
  (`TRUNK_H`). The near ring only, like the shrubs.
- **Numbers to start from:** up to about 300 per ha where the stand is half open, about 30 per ha under closed
  canopy. That is a tenth of the Fraser regeneration counts, for the share tall enough to poke out of a mid-winter
  snowpack. Today the pack's young conifers (pipeline `SHRUB_RULES`, 15 per ha of forest edge, open ground only) are
  7,368 over all of Vail, 1.3 to 3.7 m (10th to 90th percentile). The pipeline's young conifers stay as they are for
  the open ground outside the stands.
- **Pack format:** none. The game reads only what `stands/` already holds (chance, height, species, ground);
  `formatVersion` stays 1, and nothing is added to the Contract unless a tuning value is later shared with the
  pipeline. Every lidar and non-lidar pack gets saplings with no rebuild.
- **With FEAT-336:** the burial then has something to bury. Early season the glades show their saplings, by
  February the 1.4 m snowpack hides most of them.

Not picked: a lower floor (1.4 % more crowns, most of the candidates noise, and no saplings under canopy at any
density); a sapling layer written by the pipeline (bytes in every pack for what a hash of the stands gives for free).

## Not checked

The counts are the raw grids at the 18 Street View spots and pack-wide, not checked against field data or the NAIP
shadows. The deep pilot reaches 12 of the 18 spots and none of the forest in between. No game stills: what density reads right on screen is for the build
card to tune on Drew's GPU.
