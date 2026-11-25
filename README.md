# Build pack failures

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

112 attempts logged, 62 failed. Recovered inline: 124 calls; job re-runs: 13; real failures: 45. Retried runs: 9, of them passed in the end: 1 (11%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 284 | 110 | 82 | 28 |
| elevation.nationalmap.gov | 1361 | 35 | 35 | 0 |
| overpass.private.coffee | 13 | 13 | 1 | 12 |
| download.geofabrik.de | 77 | 10 | 0 | 10 |
| lz4.overpass-api.de | 12 | 10 | 2 | 8 |
| planetarycomputer.microsoft.com | 622 | 2 | 2 | 126 |
| libdrive.ethz.ch | 187 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 77 | 1 | 1 | 0 |

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

