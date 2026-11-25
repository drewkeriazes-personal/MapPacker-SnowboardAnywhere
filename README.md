# Build pack failures

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

97 attempts logged, 58 failed. Recovered inline: 109 calls; job re-runs: 9; real failures: 45. Retried runs: 5, of them passed in the end: 0 (0%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 257 | 91 | 70 | 21 |
| elevation.nationalmap.gov | 1203 | 35 | 35 | 0 |
| download.geofabrik.de | 63 | 9 | 0 | 9 |
| overpass.private.coffee | 9 | 9 | 1 | 8 |
| lz4.overpass-api.de | 8 | 8 | 1 | 7 |
| libdrive.ethz.ch | 169 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 63 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 58 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 28 |
| cancelled (real) | 17 |
| log-unreadable (transient) | 13 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 19 |
| queue / wait for the builds started before this one | 17 |
| build / build | 11 |
| probe / data hosts | 7 |
| build / pc setup | 2 |
| build / paths | 1 |
| build /  | 1 |

