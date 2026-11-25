# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

82 attempts logged, 47 failed. Recovered inline: 86 calls; job re-runs: 2; real failures: 45. Retried runs: 2, of them passed in the end: 0 (0%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 232 | 81 | 62 | 19 |
| elevation.nationalmap.gov | 1080 | 21 | 21 | 0 |
| download.geofabrik.de | 56 | 8 | 0 | 8 |
| overpass.private.coffee | 7 | 7 | 1 | 6 |
| lz4.overpass-api.de | 6 | 6 | 0 | 6 |
| libdrive.ethz.ch | 156 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 56 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 47 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 28 |
| cancelled (real) | 17 |
| log-unreadable (transient) | 2 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 19 |
| queue / wait for the builds started before this one | 17 |
| probe / data hosts | 7 |
| build / build | 3 |
| build / paths | 1 |

