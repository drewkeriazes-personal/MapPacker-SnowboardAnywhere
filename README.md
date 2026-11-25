# Build pack failures

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

107 attempts logged, 60 failed. Recovered inline: 122 calls; job re-runs: 11; real failures: 45. Retried runs: 7, of them passed in the end: 1 (14%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 279 | 106 | 80 | 26 |
| elevation.nationalmap.gov | 1356 | 35 | 35 | 0 |
| overpass.private.coffee | 11 | 11 | 1 | 10 |
| download.geofabrik.de | 72 | 9 | 0 | 9 |
| lz4.overpass-api.de | 10 | 9 | 2 | 7 |
| planetarycomputer.microsoft.com | 608 | 2 | 2 | 126 |
| libdrive.ethz.ch | 182 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 72 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 60 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 28 |
| cancelled (real) | 17 |
| log-unreadable (transient) | 15 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 20 |
| queue / wait for the builds started before this one | 17 |
| build / build | 11 |
| probe / data hosts | 7 |
| build / pc setup | 2 |
| build / paths | 1 |
| build /  | 1 |
| build / publish | 1 |

