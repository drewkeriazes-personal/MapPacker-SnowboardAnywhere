# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

22 attempts logged, 17 failed. Recovered inline: 23 calls; job re-runs: 0; real failures: 17. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 423 | 15 | 15 | 0 |
| overpass-api.de | 79 | 11 | 8 | 3 |
| download.geofabrik.de | 19 | 4 | 0 | 4 |
| lz4.overpass-api.de | 3 | 3 | 0 | 3 |
| overpass.private.coffee | 3 | 3 | 0 | 3 |

**By host**

| host | failures |
|---|---|
| (none) | 17 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 17 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 11 |
| probe / data hosts | 5 |
| build / paths | 1 |

