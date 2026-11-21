# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

19 attempts logged, 14 failed. Recovered inline: 20 calls; job re-runs: 0; real failures: 14. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 394 | 15 | 15 | 0 |
| overpass-api.de | 66 | 8 | 5 | 3 |
| download.geofabrik.de | 16 | 3 | 0 | 3 |
| lz4.overpass-api.de | 3 | 3 | 0 | 3 |
| overpass.private.coffee | 3 | 3 | 0 | 3 |

**By host**

| host | failures |
|---|---|
| (none) | 14 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 14 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 9 |
| probe / data hosts | 4 |
| build / paths | 1 |

