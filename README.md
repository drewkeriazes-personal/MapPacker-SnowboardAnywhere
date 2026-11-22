# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

47 attempts logged, 38 failed. Recovered inline: 31 calls; job re-runs: 0; real failures: 38. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 107 | 20 | 15 | 5 |
| elevation.nationalmap.gov | 451 | 16 | 16 | 0 |
| download.geofabrik.de | 27 | 6 | 0 | 6 |
| lz4.overpass-api.de | 4 | 4 | 0 | 4 |
| overpass.private.coffee | 4 | 4 | 0 | 4 |

**By host**

| host | failures |
|---|---|
| (none) | 38 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 21 |
| cancelled (real) | 17 |

**By step**

| job / step | failures |
|---|---|
| queue / wait for the builds started before this one | 17 |
| build / fetch | 12 |
| probe / data hosts | 7 |
| build / paths | 1 |
| build / build | 1 |

