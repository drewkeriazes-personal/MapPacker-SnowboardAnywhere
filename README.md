# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

18 attempts logged, 13 failed. Recovered inline: 20 calls; job re-runs: 0; real failures: 13. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 393 | 15 | 15 | 0 |
| overpass-api.de | 65 | 7 | 5 | 2 |
| download.geofabrik.de | 15 | 3 | 0 | 3 |
| lz4.overpass-api.de | 2 | 2 | 0 | 2 |
| overpass.private.coffee | 2 | 2 | 0 | 2 |

**By host**

| host | failures |
|---|---|
| (none) | 13 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 13 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 9 |
| probe / data hosts | 3 |
| build / paths | 1 |

