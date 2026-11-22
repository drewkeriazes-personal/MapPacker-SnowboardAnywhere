# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

66 attempts logged, 43 failed. Recovered inline: 77 calls; job re-runs: 0; real failures: 43. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| overpass-api.de | 208 | 67 | 54 | 13 |
| elevation.nationalmap.gov | 1059 | 21 | 21 | 0 |
| download.geofabrik.de | 43 | 6 | 0 | 6 |
| overpass.private.coffee | 5 | 5 | 1 | 4 |
| lz4.overpass-api.de | 4 | 4 | 0 | 4 |
| libdrive.ethz.ch | 143 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 43 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 26 |
| cancelled (real) | 17 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 17 |
| queue / wait for the builds started before this one | 17 |
| probe / data hosts | 7 |
| build / paths | 1 |
| build / build | 1 |

