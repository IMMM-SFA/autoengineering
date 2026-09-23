# Item 5 Release A benchmark review

_Reviewed: 2026-09-04_

_Initial revision: `5c752c7`_

_Corrected implementation revision: `c38d6ca`_

## Final finding

No implementation defect remains in the corrected item 5 benchmark. The reviewer approved the
replacement run after rechecking the decision trace, methods, exact matrix audit, scientific
recomputation, failure retention, fallback classification, typed accounting, provenance,
publication behavior, optional imports, replay, and focused tests.

## Findings corrected before the replacement run

- The original SMAC adapter used a variable constraint penalty even though Decision 0001 required
  a fixed scalar penalty. Decision 0002 fixes the value at 10.0 for every failure or infeasible
  result.
- Count-only matrix checks trusted raw seed, index, configuration, cost, and scientific fields. The
  corrected reader and gate require the exact 5 by 5 by 30 matrix, indices 0 through 9, valid typed
  actions and results, deterministic evaluator replay, and recomputed scientific accounting.
- SMAC observation or adapter cleanup failures could omit completed evaluations. Completed results
  are now retained, the primary cause is preserved, and optimizer timing includes suggestion and
  observation work.
- Baseline diagnostic text was reported as fallback activity, while post-warm BoTorch cold-start
  extensions were excluded. Baseline fallback counts are now zero, and every BoTorch fallback from
  evaluation index 5 onward counts against the frozen limit.
- Generic exceptions and message matching could misclassify invalid proposals and budget overruns.
  Dedicated boundary exceptions now set those fields.
- The first source hash covered only the benchmark package. Corrected provenance covers the full
  optimization package, benchmark package, project and Pixi definitions, both decisions, a clean
  signed Git revision, and all relevant dependency versions.
- Tests did not independently anchor every decision equation or publication failure path. The
  corrected tests include hard-coded evaluator probes, exact seed and cost checks, interrupted
  publication, existing output preservation, and a simulated concurrent destination.

The initial results at `5c752c7` were invalidated before these corrections. They were not used to
change a problem, method setting, or numeric threshold.

## Replacement evidence

The checked replacement benchmark passed with 7,500 evaluation records, 750 complete runs, no run
errors, no invalid configurations, no budget overruns, and exact replay for all 600 native runs.
All 150 SMAC runs completed. The scientific audit reported zero issues. Three of 750 post-warm
BoTorch suggestions had unresolved fallbacks, for a rate of 0.004 and a maximum of one in any run.
The exact clean execution revision is recorded in `gate.json`.

BoTorch pooled mean final regret was 0.018496, compared with 0.058130 for random and 0.043001 for
Sobol. Its pooled mean regret area was 0.198245, compared with 0.236986 for random and 0.204547 for
Sobol. It met the per-problem limit on all five problems and was at or below random on all five.

Checks on the corrected evidence:

- `pixi run test`: 363 passed, 23 skipped;
- `pixi run -e bayes test-bayes`: 385 passed, 1 skipped, with five upstream deprecation warnings;
- `pixi run lint`: passed;
- `git diff --check`: passed;
- `pixi run -e bayes benchmark-release-a`: passed in read-only verification mode; and
- scoped Waterology constraints: 7 of 7 passed.

## Residual risks

- The publication lock protects concurrent benchmark commands, but a noncooperating process could
  create the destination between the final check and `os.replace`.
- A forced process termination can leave the sibling publication lock behind for manual removal.
- The checked replacement ran on macOS ARM. Cross-platform environment verification remains in
  item 6.
