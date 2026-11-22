# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

42 attempts logged, 35 failed. Recovered inline: 30 calls; job re-runs: 0; real failures: 35. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 97 | 18 | 14 | 4 |
| elevation.nationalmap.gov | 446 | 16 | 16 | 0 |
| download.geofabrik.de | 22 | 4 | 0 | 4 |
| lz4.overpass-api.de | 3 | 3 | 0 | 3 |
| overpass.private.coffee | 3 | 3 | 0 | 3 |

**By host**

| host | failures |
|---|---|
| (none) | 35 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 18 |
| cancelled (real) | 17 |

**By step**

| job / step | failures |
|---|---|
| queue / wait for the builds started before this one | 17 |
| build / fetch | 12 |
| probe / data hosts | 5 |
| build / paths | 1 |

