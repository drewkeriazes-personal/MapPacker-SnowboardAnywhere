# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

62 attempts logged, 41 failed. Recovered inline: 64 calls; job re-runs: 0; real failures: 41. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 192 | 54 | 43 | 11 |
| elevation.nationalmap.gov | 1025 | 20 | 20 | 0 |
| download.geofabrik.de | 41 | 6 | 0 | 6 |
| overpass.private.coffee | 5 | 5 | 1 | 4 |
| lz4.overpass-api.de | 4 | 4 | 0 | 4 |

**By host**

| host | failures |
|---|---|
| (none) | 41 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 24 |
| cancelled (real) | 17 |

**By step**

| job / step | failures |
|---|---|
| queue / wait for the builds started before this one | 17 |
| build / fetch | 15 |
| probe / data hosts | 7 |
| build / paths | 1 |
| build / build | 1 |

