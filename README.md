# Build pack failures

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

111 attempts logged, 62 failed. Recovered inline: 124 calls; job re-runs: 13; real failures: 45. Retried runs: 9, of them passed in the end: 1 (11%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 283 | 109 | 82 | 27 |
| elevation.nationalmap.gov | 1360 | 35 | 35 | 0 |
| overpass.private.coffee | 12 | 12 | 1 | 11 |
| download.geofabrik.de | 76 | 9 | 0 | 9 |
| lz4.overpass-api.de | 11 | 9 | 2 | 7 |
| planetarycomputer.microsoft.com | 619 | 2 | 2 | 126 |
| libdrive.ethz.ch | 186 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 76 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 62 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 28 |
| cancelled (real) | 17 |
| log-unreadable (transient) | 17 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 20 |
| queue / wait for the builds started before this one | 17 |
| build / build | 13 |
| probe / data hosts | 7 |
| build / pc setup | 2 |
| build / paths | 1 |
| build /  | 1 |
| build / publish | 1 |

