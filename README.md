# Build pack failures

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

115 attempts logged, 63 failed. Recovered inline: 125 calls; job re-runs: 14; real failures: 45. Retried runs: 10, of them passed in the end: 1 (10%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 287 | 111 | 83 | 28 |
| elevation.nationalmap.gov | 1364 | 35 | 35 | 0 |
| overpass.private.coffee | 13 | 13 | 1 | 12 |
| download.geofabrik.de | 80 | 10 | 0 | 10 |
| lz4.overpass-api.de | 12 | 10 | 2 | 8 |
| planetarycomputer.microsoft.com | 630 | 2 | 2 | 126 |
| libdrive.ethz.ch | 190 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 80 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 63 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 28 |
| log-unreadable (transient) | 18 |
| cancelled (real) | 17 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 20 |
| queue / wait for the builds started before this one | 17 |
| build / build | 14 |
| probe / data hosts | 7 |
| build / pc setup | 2 |
| build / paths | 1 |
| build /  | 1 |
| build / publish | 1 |

