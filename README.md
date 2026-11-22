# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

53 attempts logged, 39 failed. Recovered inline: 42 calls; job re-runs: 0; real failures: 39. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 143 | 32 | 26 | 6 |
| elevation.nationalmap.gov | 701 | 16 | 16 | 0 |
| download.geofabrik.de | 33 | 6 | 0 | 6 |
| lz4.overpass-api.de | 4 | 4 | 0 | 4 |
| overpass.private.coffee | 4 | 4 | 0 | 4 |

**By host**

| host | failures |
|---|---|
| (none) | 39 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 22 |
| cancelled (real) | 17 |

**By step**

| job / step | failures |
|---|---|
| queue / wait for the builds started before this one | 17 |
| build / fetch | 13 |
| probe / data hosts | 7 |
| build / paths | 1 |
| build / build | 1 |

