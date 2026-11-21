# Build pack failures (FEAT-314)

Written by `tools/ci/build_failures.py record` on every Build pack attempt; the rows are in `build-failures.jsonl`.

8 attempts logged, 3 failed. Recovered inline: 12 calls; job re-runs: 0; real failures: 3. Retried runs: 0, of them passed in the end: 0.

**Inline retries by host** (a host that needs more and more of them is getting worse)

| host | calls | retried | recovered | failed |
|---|---|---|---|---|
| elevation.nationalmap.gov | 101 | 11 | 11 | 0 |
| overpass-api.de | 20 | 1 | 1 | 0 |

**By host**

| host | failures |
|---|---|
| (none) | 3 |

**By reason**

| reason | failures |
|---|---|
| unknown (real) | 3 |

**By step**

| job / step | failures |
|---|---|
| build / fetch | 2 |
| build / paths | 1 |

