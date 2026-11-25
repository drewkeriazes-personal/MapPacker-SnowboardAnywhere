# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

93 attempts logged, 54 failed. Recovered inline: 107 calls; job re-runs: 6; real failures: 45. Retried runs: 3, of them passed in the end: 0 (0%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 255 | 89 | 69 | 20 |
| elevation.nationalmap.gov | 1201 | 35 | 35 | 0 |
| download.geofabrik.de | 61 | 9 | 0 | 9 |
| overpass.private.coffee | 8 | 8 | 1 | 7 |
| lz4.overpass-api.de | 7 | 7 | 0 | 7 |
| libdrive.ethz.ch | 167 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 61 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 54 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 28 |
| cancelled (real) | 17 |
| log-unreadable (transient) | 9 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 19 |
| queue / wait for the builds started before this one | 17 |
| build / build | 10 |
| probe / data hosts | 7 |
| build / paths | 1 |

