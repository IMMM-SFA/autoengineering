# Review of the newer BO results

## Summary Assessment

The larger BMI suite at `a262556` demonstrates useful validation-target search
behavior in hydrology, but does not establish better held-out prediction or a
general runtime advantage. Its 45 fixed and 75 target studies are newer than
the common-utility matrix. These are whole-system searches and do not change
the failed partial-observation gate.

## Strengths

The protocol distinguishes validation selection from held-out scoring, uses
separate target-study seeds, preserves capped runs, and records fallbacks and
timing. Fresh reconstruction reproduced the report and trajectory CSV exactly.
The new seven-parameter models completed without recorded BO fallback actions.
Negative outcomes and withdrawn sensor diagnostics remain visible.

## Critical Issues

No integrity error was found in the checks performed. A broad claim that BO
improves prediction would be unsupported: at 96 calls BO does not beat both
baselines on median held-out RMSE for any of the five models.

| Model | Random test RMSE | Sobol test RMSE | BO test RMSE |
| --- | ---: | ---: | ---: |
| hydro | 2.8141 | 2.8179 | 2.8839 |
| solar | 122.8638 | 120.2928 | 122.0261 |
| copper | 0.2479 | 0.2479 | 0.2479 |
| hymod | 2.6758 | 2.5505 | 2.5731 |
| solar_diode | 128.4311 | 124.6517 | 124.9850 |

These are medians over three seeds. Copper is tied at displayed precision.
Units differ by model and should not be pooled. Validation gains alongside
weaker test results are consistent with limited validation generalization,
but do not identify its cause.

## Major Issues

1. __Target success and predictive quality give different answers.__ Simple
   hydrology BO reaches the target in all five seeds using 6-7 calls, versus
   random 4/5 and Sobol 1/5 by 200. This is a clear result for the declared
   validation target. Its median test RMSE is nevertheless 2.8839 versus
   2.8513 and 2.8218. HYMOD BO reaches 4/5 versus 0/5 for either baseline,
   but test RMSE is 2.6660 versus 2.3870 and 2.4586. Target-run test comparisons
   describe the stopping policies, not equal-budget predictive performance.
2. __HYMOD saves calls without saving measured time.__ Mean calls consumed are
   126.6 for BO versus 200 for either baseline. Median study times are 58.95
   seconds versus 30.20 and 24.93. The methods have unequal target success,
   so neither the mean capped cost nor the successful-only median of 106.5
   calls establishes a general speed ratio. Study timing excludes setup and
   held-out scoring.
3. __Legacy fixed-budget BO often becomes Sobol fallback.__ After initialization,
   hydro has 248/276 fallback actions (89.9%), solar 131/276 (47.5%), and copper
   140/276 (50.7%). These are hybrid realized trajectories. They do not isolate
   sustained adaptive BO performance. The final hydro seed-0 snapshot records
   a duplicate-candidate retry failure, but causes were not reconstructed for
   every action. HYMOD and solar_diode have zero recorded fallbacks.
4. __Several targets barely exercise BO.__ Solar target runs have zero adaptive
   BO actions and exactly the same call counts as Sobol. Copper and solar_diode
   each have only four adaptive actions across five target seeds. Target success
   on these cases is weak evidence about the acquisition policy.

## Minor Issues

The fixed comparison has three seeds and the target comparison five. Checkpoints
share trajectories, the two new models reuse existing datasets, and the targets
are development-derived quality thresholds rather than convergence guarantees.
Keep these limits when presenting the larger study count.

All 639 module-temperature observations equal 3276.7 C. The withdrawal of
temperature RMSE and ranking claims is appropriate. Retained AC-power objectives
use simulated temperature and were not changed by this correction. This does not
certify the remaining sensors. HYMOD's 90-day warmup also does not establish
equilibrium for its slowest reservoir, so initialization remains consequential.

## Reproducibility and Verification

Fresh report regeneration passed matrix, source/input hash, ledger/trajectory,
target, cap, historical-prefix, and audit-hash checks. Both generated outputs
matched their committed bytes. The original result checkout remained clean.
An independent reviewer checked raw summary values and action labels and found
no numerical correction. Its interpretation agrees with the findings above.

The existing numerical audits cover 8,942 calls and 300 recommendation records.
Their matching hashes were checked, but the numerical audits and historical
tests were not rerun. HYMOD's audit reruns the same BMI implementation with a
water-balance check; it is not an independent implementation oracle. Solar diode
uses an alternate Lambert-W solver. No new experiment was launched.

## Inline Annotations

- Results, fixed-budget table: lower validation RMSE at 96 calls should not be
  described as better held-out prediction. The table above preserves that distinction.
- Results, target table: HYMOD 4/5 is the useful search result. Its 106.5-call
  median excludes the capped seed and is not an all-run convergence estimate.
- Results, timing table: large fallback counts are a substantive interpretation
  limit even though failed model attempts equal zero.
- Results, sensor correction: withdrawn temperature evidence must remain excluded
  from component-ranking or intermediate-observation claims.

## Recommendation

Retain this as evidence of validation optimization with mixed generalization.
Simple hydrology provides the strongest observed target-speed result. HYMOD
provides stronger target attainment, with higher runtime and worse test error.
The solar and materials cases do not establish a compelling BO advantage here.

Before claiming broader benefit, a separately approved study should address
validation representativeness, initialization sensitivity, and fallback behavior,
with independent evaluation periods and an explicit practical benefit criterion.
Do not tune against the already inspected test outcomes or change existing gates.

## Sources

- [Results](../examples/complex_models/results/RESULTS.md)
- [Protocol](../examples/complex_models/PROTOCOL.md)
- [Fixed records](../examples/complex_models/results/fixed/results.json)
- [Target records](../examples/complex_models/results/target/results.json)
- [Recorded verification](../examples/complex_models/results/verification.json)
- [Fresh review evidence](.drafts/complex-bo-results-review-evidence.md)
