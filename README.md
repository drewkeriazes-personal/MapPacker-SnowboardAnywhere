# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

7 attempts logged, 2 failed. Recovered inline: 9 calls; job re-runs: 0; real failures: 2. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 60 | 8 | 8 | 0 |
| overpass-api.de | 14 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 2 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 2 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 1 |
| build / paths | 1 |

