# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

20 attempts logged, 15 failed. Recovered inline: 22 calls; job re-runs: 0; real failures: 15. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 405 | 15 | 15 | 0 |
| overpass-api.de | 72 | 10 | 7 | 3 |
| download.geofabrik.de | 17 | 3 | 0 | 3 |
| lz4.overpass-api.de | 3 | 3 | 0 | 3 |
| overpass.private.coffee | 3 | 3 | 0 | 3 |

**By host**

| host | failures |
|---|---|
| (none) | 15 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 15 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 10 |
| probe / data hosts | 4 |
| build / paths | 1 |

