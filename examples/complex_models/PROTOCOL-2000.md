# Reduced target-study cap

The user reduced the 10000-call limit to 2000 while the extended matrix was
running. This is a retrospective budget amendment, not a preregistered cap.
The frozen targets, domains, methods, seeds 3-7, model definitions and data
splits remain those of PROTOCOL-10000.md.

The interrupted 10000-call matrix and its source snapshots remain in
results/target-10000. Its ledger inventory freezes 53 studies and 49093 raw
observations. For each available study, results/target-2000 retains the exact
observation bytes through the first target hit or call 2000, whichever occurs
first. Configurations and improvements after that cutoff are excluded. The
minimum successful validation RMSE in the retained prefix determines the
recommendation, which is frozen before its held-out test score is recomputed.
A target first reached after call 2000 is reported as censored at 2000.

Projected records carry their source ledger and trajectory hashes. They contain
no copied controller recovery state and are not resumable optimizer studies.
Their timing is the cumulative trajectory timing at the retained final call,
excluding later computation and projection work. Original raw timings remain
available. The other 22 matrix members run normally with a 2000-call budget.
All target studies use the same benchmark-local ledger parsing cache.

Run the reduction and remaining studies with:

```sh
pixi run -e examples python -m scripts.cap_complex_models --source examples/complex_models/results/target-10000 --output examples/complex_models/results/target-2000 --cap 2000
```

For a fresh complete matrix, use the normal runner with --target-cap 2000.
The report verifies exact historical prefixes through the applicable cutoff
and independently recalculates retained validation and final held-out scores.
The three open-chain candidate comparisons remain separate finite experiments.
