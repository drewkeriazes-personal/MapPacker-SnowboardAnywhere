# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

94 attempts logged, 55 failed. Recovered inline: 108 calls; job re-runs: 7; real failures: 45. Retried runs: 4, of them passed in the end: 0 (0%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 256 | 90 | 69 | 21 |
| elevation.nationalmap.gov | 1202 | 35 | 35 | 0 |
| download.geofabrik.de | 62 | 9 | 0 | 9 |
| overpass.private.coffee | 9 | 9 | 1 | 8 |
| lz4.overpass-api.de | 8 | 8 | 1 | 7 |
| libdrive.ethz.ch | 168 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 62 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 55 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 28 |
| cancelled (real) | 17 |
| log-unreadable (transient) | 10 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 19 |
| queue / wait for the builds started before this one | 17 |
| build / build | 10 |
| probe / data hosts | 7 |
| build / paths | 1 |
| build / pc setup | 1 |

