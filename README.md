# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

11 attempts logged, 6 failed. Recovered inline: 14 calls; job re-runs: 0; real failures: 6. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 172 | 11 | 11 | 0 |
| overpass-api.de | 28 | 5 | 3 | 2 |
| download.geofabrik.de | 8 | 2 | 0 | 2 |
| lz4.overpass-api.de | 2 | 2 | 0 | 2 |
| overpass.private.coffee | 2 | 2 | 0 | 2 |

**By host**

| host | failures |
|---|---|
| (none) | 6 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 6 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 3 |
| probe / data hosts | 2 |
| build / paths | 1 |

