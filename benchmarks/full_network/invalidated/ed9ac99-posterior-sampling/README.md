# Invalidated posterior-sampling benchmark run

This directory preserves the replacement run from revision
`ed9ac99a1af6bc20032aa56c37bc2c62515c28fe`. It is not valid Item 8 comparison evidence.

The run completed 39 of 40 closed loops. All frozen regret and fallback comparisons passed among
the completed records. The held-out calibration failed with 0.00625 coverage and a 0.3 constraint
Brier score.

Investigation found that posterior propagation requested one joint function sample over repeated
prediction rows. The rows represent independent propagation paths, so this collapsed uncertainty
at a fixed configuration instead of drawing the independent seeded component innovations required
by the Item 8 plan. The acquisition results and calibration therefore do not evaluate the declared
backend.

The raw audit also treated the evaluator's declared intermediate component outcomes as unexpected,
and the runner compared diagnostic warning lists during suggestion replay. One process-level Torch
warning appeared only once, which incorrectly ended one otherwise identical system-backend run.
The action itself replayed exactly.

Decision 0005 records the corrections. It retains all scientific problems, seeds, budgets,
settings, measurements, and thresholds from decision 0003.
