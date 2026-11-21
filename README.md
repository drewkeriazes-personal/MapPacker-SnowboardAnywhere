# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

10 attempts logged, 5 failed. Recovered inline: 14 calls; job re-runs: 0; real failures: 5. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 171 | 11 | 11 | 0 |
| overpass-api.de | 27 | 4 | 3 | 1 |
| download.geofabrik.de | 7 | 1 | 0 | 1 |
| lz4.overpass-api.de | 1 | 1 | 0 | 1 |
| overpass.private.coffee | 1 | 1 | 0 | 1 |

**By host**

| host | failures |
|---|---|
| (none) | 5 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 5 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 3 |
| build / paths | 1 |
| probe / data hosts | 1 |

