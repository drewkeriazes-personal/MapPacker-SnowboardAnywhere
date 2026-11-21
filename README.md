# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

9 attempts logged, 4 failed. Recovered inline: 12 calls; job re-runs: 0; real failures: 4. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 102 | 11 | 11 | 0 |
| overpass-api.de | 21 | 2 | 1 | 1 |
| download.geofabrik.de | 6 | 1 | 0 | 1 |
| lz4.overpass-api.de | 1 | 1 | 0 | 1 |
| overpass.private.coffee | 1 | 1 | 0 | 1 |

**By host**

| host | failures |
|---|---|
| (none) | 4 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 4 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 2 |
| build / paths | 1 |
| probe / data hosts | 1 |

