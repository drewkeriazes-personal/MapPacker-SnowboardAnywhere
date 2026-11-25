# Build pack failures

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

105 attempts logged, 60 failed. Recovered inline: 120 calls; job re-runs: 11; real failures: 45. Retried runs: 7, of them passed in the end: 1 (14%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 277 | 104 | 79 | 25 |
| elevation.nationalmap.gov | 1354 | 35 | 35 | 0 |
| overpass.private.coffee | 10 | 10 | 1 | 9 |
| download.geofabrik.de | 70 | 9 | 0 | 9 |
| lz4.overpass-api.de | 9 | 8 | 1 | 7 |
| planetarycomputer.microsoft.com | 602 | 2 | 2 | 126 |
| libdrive.ethz.ch | 180 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 70 | 1 | 1 | 0 |

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

