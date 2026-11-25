# Build pack failures

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

108 attempts logged, 61 failed. Recovered inline: 122 calls; job re-runs: 12; real failures: 45. Retried runs: 8, of them passed in the end: 1 (12%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 280 | 106 | 80 | 26 |
| elevation.nationalmap.gov | 1357 | 35 | 35 | 0 |
| overpass.private.coffee | 11 | 11 | 1 | 10 |
| download.geofabrik.de | 73 | 9 | 0 | 9 |
| lz4.overpass-api.de | 10 | 9 | 2 | 7 |
| planetarycomputer.microsoft.com | 611 | 2 | 2 | 126 |
| libdrive.ethz.ch | 183 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 73 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 61 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 28 |
| cancelled (real) | 17 |
| log-unreadable (transient) | 16 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 20 |
| queue / wait for the builds started before this one | 17 |
| build / build | 12 |
| probe / data hosts | 7 |
| build / pc setup | 2 |
| build / paths | 1 |
| build /  | 1 |
| build / publish | 1 |

