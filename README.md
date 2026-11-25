# Build pack failures

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

116 attempts logged, 63 failed. Recovered inline: 125 calls; job re-runs: 14; real failures: 45. Retried runs: 10, of them passed in the end: 1 (10%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 288 | 112 | 83 | 29 |
| elevation.nationalmap.gov | 1365 | 35 | 35 | 0 |
| overpass.private.coffee | 14 | 14 | 1 | 13 |
| download.geofabrik.de | 81 | 11 | 0 | 11 |
| lz4.overpass-api.de | 13 | 11 | 2 | 9 |
| planetarycomputer.microsoft.com | 633 | 2 | 2 | 126 |
| libdrive.ethz.ch | 191 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 81 | 1 | 1 | 0 |

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

