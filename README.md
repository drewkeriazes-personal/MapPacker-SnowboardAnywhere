# Build pack failures

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

98 attempts logged, 59 failed. Recovered inline: 114 calls; job re-runs: 10; real failures: 45. Retried runs: 6, of them passed in the end: 0 (0%).

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 263 | 97 | 73 | 24 |
| elevation.nationalmap.gov | 1272 | 35 | 35 | 0 |
| download.geofabrik.de | 64 | 9 | 0 | 9 |
| overpass.private.coffee | 9 | 9 | 1 | 8 |
| lz4.overpass-api.de | 8 | 8 | 1 | 7 |
| planetarycomputer.microsoft.com | 564 | 2 | 2 | 126 |
| libdrive.ethz.ch | 172 | 1 | 1 | 0 |
| tnmaccess.nationalmap.gov | 64 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 59 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 28 |
| cancelled (real) | 17 |
| log-unreadable (transient) | 14 |

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

