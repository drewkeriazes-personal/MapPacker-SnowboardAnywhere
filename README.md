# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

13 attempts logged, 8 failed. Recovered inline: 16 calls; job re-runs: 0; real failures: 8. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 232 | 13 | 13 | 0 |
| overpass-api.de | 40 | 5 | 3 | 2 |
| download.geofabrik.de | 10 | 2 | 0 | 2 |
| lz4.overpass-api.de | 2 | 2 | 0 | 2 |
| overpass.private.coffee | 2 | 2 | 0 | 2 |

**By host**

| host | failures |
|---|---|
| (none) | 8 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 8 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 5 |
| probe / data hosts | 2 |
| build / paths | 1 |

