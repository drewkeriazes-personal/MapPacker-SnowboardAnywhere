# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

77 attempts logged, 46 failed. Recovered inline: 80 calls; job re-runs: 1; real failures: 45. Retried runs: 1, of them passed in the end: 0 (0%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 222 | 74 | 57 | 17 |
| elevation.nationalmap.gov | 1075 | 21 | 21 | 0 |
| download.geofabrik.de | 51 | 6 | 0 | 6 |
| overpass.private.coffee | 5 | 5 | 1 | 4 |
| lz4.overpass-api.de | 4 | 4 | 0 | 4 |
| libdrive.ethz.ch | 151 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 46 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 28 |
| cancelled (real) | 17 |
| log-unreadable (transient) | 1 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 19 |
| queue / wait for the builds started before this one | 17 |
| probe / data hosts | 7 |
| build / build | 2 |
| build / paths | 1 |

