# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

39 attempts logged, 33 failed. Recovered inline: 25 calls; job re-runs: 0; real failures: 33. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 435 | 15 | 15 | 0 |
| overpass-api.de | 91 | 14 | 10 | 4 |
| download.geofabrik.de | 21 | 4 | 0 | 4 |
| lz4.overpass-api.de | 3 | 3 | 0 | 3 |
| overpass.private.coffee | 3 | 3 | 0 | 3 |

**By host**

| host | failures |
|---|---|
| (none) | 33 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 18 |
| cancelled (real) | 15 |

**By step**

| job / step | failures |
|---|---|
| queue / wait for the builds started before this one | 15 |
| build / fetch | 12 |
| probe / data hosts | 5 |
| build / paths | 1 |

