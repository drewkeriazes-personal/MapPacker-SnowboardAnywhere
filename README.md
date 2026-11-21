# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

16 attempts logged, 11 failed. Recovered inline: 20 calls; job re-runs: 0; real failures: 11. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 352 | 15 | 15 | 0 |
| overpass-api.de | 58 | 7 | 5 | 2 |
| download.geofabrik.de | 13 | 2 | 0 | 2 |
| lz4.overpass-api.de | 2 | 2 | 0 | 2 |
| overpass.private.coffee | 2 | 2 | 0 | 2 |

**By host**

| host | failures |
|---|---|
| (none) | 11 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 11 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 8 |
| probe / data hosts | 2 |
| build / paths | 1 |

