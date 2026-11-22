# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

44 attempts logged, 37 failed. Recovered inline: 31 calls; job re-runs: 0; real failures: 37. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 99 | 19 | 15 | 4 |
| elevation.nationalmap.gov | 448 | 16 | 16 | 0 |
| download.geofabrik.de | 24 | 5 | 0 | 5 |
| lz4.overpass-api.de | 3 | 3 | 0 | 3 |
| overpass.private.coffee | 3 | 3 | 0 | 3 |

**By host**

| host | failures |
|---|---|
| (none) | 37 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 20 |
| cancelled (real) | 17 |

**By step**

| job / step | failures |
|---|---|
| queue / wait for the builds started before this one | 17 |
| build / fetch | 12 |
| probe / data hosts | 6 |
| build / paths | 1 |
| build / build | 1 |

