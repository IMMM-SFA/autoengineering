# Extended BMI search comparison

Registered on 2026-09-05 before new runs, following the user's request for more
complete-model evaluations and an iterations-to-convergence comparison.
Base source: signed commit `25f406b`. Earlier results and gates remain intact.
This is a fixed experiment, with no adaptive changes to models or algorithms.

## Fixed-budget extension

Run the same BMI models, data splits, spaces, objectives and optimizer settings
for 24 complete-model evaluations, using the original seeds 0, 1 and 2.
Rerun in fresh directories and verify the first 12 actions and objective values
against the original ledgers. Compare validation and held-out errors at 12 and
24. These are paired extensions, not additional independent seeds. Keep four
initial BO points, two acquisition restarts and 32 raw samples.

## Validation target and stopping

For each domain, take the lowest successful validation RMSE across all original
BMI development ledgers, pooled across methods and seeds. Multiply by 1.05.
Freeze those targets and hashes of the source ledgers in convergence-targets.json
before any new objective evaluation. Do not read test scores to construct targets.
The tolerance is a prospective experimental choice, not a scientific accuracy
standard. Historical data informed the target, so this is a development benchmark.

Use new seeds 3, 4, 5, 6 and 7, with the same seed labels for all methods. Different
algorithms need not share initial points. Stop immediately after the first observed
validation RMSE <= target, or at 60 complete-model calls. Count initial points and
failed model evaluations. Backend termination before the cap is a separate outcome.
There is no plateau rule: lack of improvement can reflect failed exploration.
These deterministic objectives require no repeat confirmation of the same point.
This defines time to a common observed quality target, not mathematical convergence
or evidence of a global optimum. No partial-observation BO is evaluated here.

Only validation outcomes enter the optimizer. Save the final recommendation before
computing test metrics. Do not revise targets, caps, methods or seeds from results.
Application stopping is recorded separately from the durable controller state,
which may retain an open budget. No suite resume or budget mutation is performed.

## Reporting, timing and verification

Report every seed, success fraction, iterations to first target, and attained
validation/test error. Never report a capped run as convergence at 60. Show the
median iterations among successful runs only with its denominator, and the mean
calls consumed across all seeds as a restricted cost through the cap. If methods
have different success rates, that restricted cost alone is not an efficiency ranking.

Measure cumulative model and study seconds after each controller step. Study time
includes optimizer fitting/acquisition, durable bookkeeping and application logging,
but excludes imports, input loading, backend construction and held-out evaluation.
The final study timer excludes the final extra recommendation read and final artifact
write. The trajectory timer is taken before that step's progress logging. Fixed-budget
runs use the original driver; convergence adds a recommendation check after each call.
Compare time only within the same experiment. Rotate method order by seed. Use local
Pixi examples environment, one Torch CPU thread, sequential studies, no inflated costs.

Archive raw ledgers, configurations, frozen recommendations, trajectories, environment,
source/data/protocol hashes and execution logs. Recalculate objectives and held-out
recommendations. Validate earliest target crossing and cap handling against ledgers.
Report expensive-model implications only conditionally: fewer calls can save time when
saved evaluation cost exceeds additional optimizer overhead. No added sleep experiment
or unmeasured runtime claim is needed.

Maximum work: 27 x 24 = 648 fixed calls and 45 x 60 = 2700 target calls.
Commands, from repository root:

```bash
pixi run -e examples python -m examples.local_models.convergence --mode fixed --output examples/local_models/results/extended-fixed
pixi run -e examples python -m examples.local_models.convergence --mode target --output examples/local_models/results/convergence-target
```

## Implementation review before target runs

After the fixed extension finished and before target runs, review corrected
unexpected-exception accounting: every committed attempt is counted and evaluator
timing is saved in a finally block. The target driver imports pvlib before timing.
The completed fixed extension's first solar study includes a lazy pvlib import;
its time must not be treated as steady-state timing. This affects timing only.
The fixed suite retains its exact earlier driver and protocol in source/.
Fixed-study directories require their outer suite manifest for the new protocol
and target identity. Target studies include those hashes individually.
The target driver checks historical ledger hashes before running.
No targets, algorithm settings, splits, seeds or caps changed in this correction.
