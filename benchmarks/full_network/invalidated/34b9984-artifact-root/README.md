# Invalidated full-network benchmark run

This directory preserves the first run from revision
`34b9984b09ff00f97c196e2dc34e308bddbabc76`. It is not Item 8 comparison evidence.

All 40 runs failed before their first evaluation because the benchmark used the platform temporary
directory through its `/var` alias. The evaluator correctly rejected that symlinked artifact-root
ancestry. The run therefore contains 40 error records, no evaluations, no acquisitions, and no
calibration records.

Independent verification also exposed unstable ordering in audit messages for failed runs. The
scientific problems, seeds, budgets, methods, and acceptance thresholds were not exercised and were
not changed after this run. Decision 0004 records the implementation corrections required before a
replacement run.
