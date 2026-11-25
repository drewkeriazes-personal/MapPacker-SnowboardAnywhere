# Build pack failures

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

119 attempts logged, 64 failed. Recovered inline: 126 calls; job re-runs: 15; real failures: 45. Retried runs: 10, of them passed in the end: 1 (10%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 292 | 114 | 84 | 30 |
| elevation.nationalmap.gov | 1367 | 35 | 35 | 0 |
| overpass.private.coffee | 15 | 15 | 1 | 14 |
| lz4.overpass-api.de | 14 | 12 | 2 | 10 |
| download.geofabrik.de | 83 | 11 | 0 | 11 |
| planetarycomputer.microsoft.com | 639 | 2 | 2 | 126 |
| libdrive.ethz.ch | 193 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 83 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 64 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 28 |
| log-unreadable (transient) | 19 |
| cancelled (real) | 17 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 20 |
| queue / wait for the builds started before this one | 17 |
| build / build | 15 |
| probe / data hosts | 7 |
| build / pc setup | 2 |
| build / paths | 1 |
| build /  | 1 |
| build / publish | 1 |

