# Build pack failures

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

109 attempts logged, 62 failed. Recovered inline: 123 calls; job re-runs: 13; real failures: 45. Retried runs: 9, of them passed in the end: 1 (11%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 281 | 107 | 81 | 26 |
| elevation.nationalmap.gov | 1358 | 35 | 35 | 0 |
| overpass.private.coffee | 11 | 11 | 1 | 10 |
| download.geofabrik.de | 74 | 9 | 0 | 9 |
| lz4.overpass-api.de | 10 | 9 | 2 | 7 |
| planetarycomputer.microsoft.com | 613 | 2 | 2 | 126 |
| libdrive.ethz.ch | 184 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 74 | 1 | 1 | 0 |

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

