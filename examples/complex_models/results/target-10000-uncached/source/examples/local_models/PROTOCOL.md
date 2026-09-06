# Local real-model examples

Registered before optimization runs on 2026-09-05. This is a new application suite based on
revision `16f730e`. Decisions 0007-0010 and their failed partial-observation evidence stay intact.
The user authorized new local testing and examples. This suite does not replace those gates.

## Questions and examples

1. Water: does selecting PET and calibrating a soil bucket plus linear reservoir improve observed
   Leaf River discharge? Use existing USGS/NOAA cache for 2019-2020. Warm up January-March 2019,
   train April-September, select on October-December, and test on all of 2020. Simulate continuously
   across split boundaries, without assimilation or resetting storage. These are conditional
   hindcasts with observed weather, not forecasts. Intermediate water stores have no measured truth.
2. Solar energy: does a Ross temperature model followed by PVWatts DC and inverter models improve
   measured inverter output? Use OEDI PVDAQ system 9068, January 1-7, 2024. Train January 1-4,
   select January 5, test January 6-7. The window was selected by calendar and download size before
   inspecting scores. Measured module temperature supports a separate component diagnostic. Use
   inverter 2 and half the documented system DC rating. Wind is unavailable in this excerpt.
   Cell/module temperature equality and plant-average irradiance are explicit approximations.
3. Materials: can replacing a polynomial with rational regression improve prediction of copper
   thermal expansion? Use all 236 NIST Hahn1 measurements. Rank temperature stably, assigning
   ranks modulo five 0 to test, 1 to validation, and others to train. This primarily tests interpolation; the held-out endpoints include two
   small extrapolations beyond the training temperature range. Rational denominators have nonnegative coefficients to prevent poles at
   positive temperatures. This constrained family is not the exact NIST certified fit.

## Comparison and limits

Use the same spaces, splits, and budgets for random, Sobol and whole-system BoTorch search.
Default development run: seeds 0, 1, 2 and 12 complete-model calls each. BoTorch uses four initial
points, two acquisition restarts and 32 raw samples. Retain all failures and warnings. Fit
regression parameters only on training rows. Optimizers see validation RMSE only. Test outcomes
are computed after a recommendation is frozen and are never sent to a backend. No selection of
seeds or methods using test scores. Fixed model swaps are selected on validation as a separate
workflow baseline. Report each seed, model time, optimizer time and end-to-end elapsed time.

The model objective is deterministic conditional on the fixed noisy measurements. This does not
mean the measurements are noise free. Budgets count model calls; elapsed seconds are measured
separately and must be included when discussing practical benefit. No sleeps or inflated costs.
These small samples establish runnable examples, not broad superiority or a new release gate.

## Partial observation tests

Start with measured solar temperature and real model component evaluations. Check a downstream
power re-evaluation with a saved temperature trace against a full rerun. Check which component
has measured validation targets, and measure component runtime. Do not substitute model outputs
or inferred baseflow for observed intermediate truth.

The current function-network surrogates accept scalar couplings. A time-series mean is generally
insufficient to determine downstream power or discharge. Before a partial BO application comparison,
verify a representation that preserves the complete downstream dependency. Preserve a failed
representation test as a blocker instead of replacing traces with convenient scalar proxies.
A single-condition scalar solar test can exercise the backend but cannot establish improvement
on the time-series application. Any claim of partial BO benefit requires repeated, matched-budget
comparisons against whole-system and random-component policies, with observed terminal outcomes.

## Exit conditions

Produce offline runnable models and source hashes, immutable input splits, model-swap and BO
results, physical/held-out leakage checks, and a measured component reuse experiment. Preserve
adverse results. Run focused tests, lint and Waterology constraints. Do not merge or publish.
Stop a model if its inputs, rights or numeric contracts cannot be established. Keep explicit
unresolved status for partial BO when its representation or measured cost advantage is absent.


## BMI requirement and implementation corrections

On 2026-09-05, the user required the example models to use BMI. The final application matrix
therefore runs eight CSDMS BMI components through the declared system graphs. The earlier complete
matrix is retained under `results/pre-bmi-development` as preliminary evidence. It is not the final
BMI comparison. Numerical parity checks compare the new component execution with the original
vectorized functions. Splits, search spaces, candidate families, seeds, budgets and selection rules
are unchanged. The intermediate probe is rerun through BMI to report actual interface costs.

The pre-BMI matrix also discovered a decoder boundary bug. Its interrupted evidence is preserved
under `results/interrupted-boundary`. The fix returns exact declared endpoints and bounds the
rounding of interior decoding without relaxing external validation. New studies hash package source
as well as input data. Historical studies must retain their original code for exact replay; this
work does not claim cross-version resume compatibility at affected endpoints.

Only copper fits coefficients from training labels. Water training weather supplies state history;
solar training rows support component diagnostics. Opportunity ranks use the training-mean terminal
response evaluated on validation rows as a reference, and the ambient-only solar temperature as
an intermediate reference. These diagnostics do not change the optimizer objective or selection.
