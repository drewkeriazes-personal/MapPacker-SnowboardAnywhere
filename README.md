# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

59 attempts logged, 40 failed. Recovered inline: 60 calls; job re-runs: 0; real failures: 40. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 179 | 47 | 39 | 8 |
| elevation.nationalmap.gov | 931 | 20 | 20 | 0 |
| download.geofabrik.de | 39 | 6 | 0 | 6 |
| overpass.private.coffee | 5 | 5 | 1 | 4 |
| lz4.overpass-api.de | 4 | 4 | 0 | 4 |

**By host**

| host | failures |
|---|---|
| (none) | 40 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 23 |
| cancelled (real) | 17 |

**By step**

| job / step | failures |
|---|---|
| queue / wait for the builds started before this one | 17 |
| build / fetch | 14 |
| probe / data hosts | 7 |
| build / paths | 1 |
| build / build | 1 |

