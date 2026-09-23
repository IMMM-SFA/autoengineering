# Decision 0004: full-network evidence corrections

_Status: Accepted after the invalidated run and before the replacement run_

_Date: 2026-09-04_

_Invalidated run revision: `34b9984b09ff00f97c196e2dc34e308bddbabc76`_

_Corrected implementation revision: `6a0a9c7f1388aaf5805546e18e7637dce80c24af`_

## Context

The first full-network benchmark attempt did not evaluate the scientific comparison. All 40 runs
failed before their first evaluation because the benchmark created trace directories through the
macOS `/var` alias. The evaluator correctly rejects symlinks in artifact-root ancestry. The failed
run has 40 error records and no evaluation, acquisition, or calibration records.

Verification of that failed evidence also found that audit issues were emitted in set iteration
order. The gate values were unchanged, but `gate.json` and `report.md` could reorder messages across
processes. This prevented exact reconstruction.

The failed evidence is retained at
`benchmarks/full_network/invalidated/34b9984-artifact-root/`. It is not scientific comparison
evidence and cannot satisfy Item 8.

## Corrections

1. Resolve the platform temporary root to its real path before creating per-run trace directories.
   The evaluator's symlink rejection remains unchanged.
2. Sort the exact expected problem, method, and seed matrix before emitting audit issues.
3. Retain completed evaluation and calibration records when a later step in the same run fails.
4. Permit an empty recommendation when no feasible observation exists. A nonempty recommendation
   must still identify an observed action.
5. Audit the portable trace identifier and SHA-256 field for every evaluation record.
6. Bind replacement evidence to this correction decision as well as decision 0003.

The regression suite executes an evaluation through the resolved temporary root and forces a later
recommendation failure. It confirms that the trace succeeds and the completed evaluation remains
available in the raised run record.

## Unchanged protocol

The scientific problems, component functions, seeds, shared Sobol starts, budgets, methods,
surrogate settings, posterior sample counts, calibration points, measurements, and acceptance
thresholds from decision 0003 are unchanged. The replacement run will use the same 40-run matrix.
Failed runs and adverse scientific results remain visible.

The corrected aggregate source hash is
`f50dfe46d60276e78cebecca56de1700c1a048a23e1a689dd37486188b3cf435`.
Only these source file hashes differ from decision 0003:

| Source | SHA-256 |
| --- | --- |
| `src/autoengineering/benchmarks/full_network/__main__.py` | `e0da4baa6fcdd5a00e6d8a158f350b96afed3878a14e18ff7e8dd52565dd22a6` |
| `src/autoengineering/benchmarks/full_network/runner.py` | `aa61faf523ddb626a28e32154fd07c3de35edb5fea3575647c57432ed1fa1587` |
| `src/autoengineering/benchmarks/full_network/summary.py` | `4b7cf60b9238bd775fbcb7b1dbbfb5abb4dc23277c78cd3da4c092c00dad2c52` |

The invalidated raw evidence hashes are:

| Artifact | SHA-256 |
| --- | --- |
| `calibration.json` | `634dd6ceb91dca4154956feefe7ed97520d0bf37e239e6cca6d2ecfd1fcd9b11` |
| `gate.json` | `f7f279f25d641f0a2223f4889c1013d6f93cfaec6fc2e2df39fccf543b26cf8d` |
| `raw-records.jsonl` | `5d3507a4d2c4e54698c01f7eaf639a733af7bd2b73be635474f88c60a1c86c06` |
| `report.md` | `803ab2c388fddd077355d8486151d228dc930d910e703820fc59eeb7690e3d10` |
| `run-summary.csv` | `e3ac63a90657d61c655fc018919206835840b111f08fa5be31031968d6c638f0` |
