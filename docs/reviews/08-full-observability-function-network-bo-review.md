# Item 8 review: full-observability function-network BO

_Review date: 2026-09-04_

_Passing execution revision: `2a6894e`_

_Evidence revision: `4e064ed`_

## Scope

This review covers the optional full-observability backend, verified component training data,
posterior propagation, system-only acquisition, deterministic action replay, numerical fixtures,
the preregistered comparison, correction history, and passing evidence. Component action selection
belongs to Item 9 and is not reviewed here.

## Backend contract

`FullNetworkBayesBackend` requires exact agreement among the study, global search space, function
network, and system. Every scalar component output must be observed during a complete system
evaluation. Training rows come from digest-verified NPZ traces reconstructed by Item 7. The backend
rejects component-scope ledger rows.

The backend fits an independent double-precision `SingleTaskGP` for each executable component
output. Source outputs use empirical constants. Local parameters use their declared coordinates,
and upstream features use the component-table standardization. Posterior propagation draws
independent seeded innovations for each output and path in topological order. The acquisition is
constrained Monte Carlo expected improvement over 64 deterministic Sobol candidates with 128
samples. Suggestions have system scope, and recommendations refer only to observed feasible system
results.

## Numerical checks

The affine fixture uses 65,536 posterior samples and passes the frozen mean, variance, constraint
probability, nonnegative variance, and byte replay limits. Fresh fitted instances reproduce
posterior arrays and actions. State and identity records contain constructor settings and
diagnostics, not fitted model objects. The base optimization package remains importable without
Torch or BoTorch.

## Preregistration and corrections

Decision 0003 froze two problems, ten seeds, four shared Sobol observations, ten evaluations per
run, calibration data, and all numeric limits before the comparison. Later decisions retain the
original protocol while correcting execution or implementation defects:

1. Revision `34b9984` failed before evaluation because the platform temporary path used a symlinked
   alias that the evaluator correctly rejected. Decision 0004 resolved the temporary root, sorted
   audit output, retained partial records, and strengthened trace checks.
2. Revision `ed9ac99` exposed collapsed posterior uncertainty. The backend requested one joint
   function draw over repeated propagation rows instead of the independent innovations stated in
   the plan. Decision 0005 corrected the draw and two evidence checks.
3. Revision `b287c82` produced valid evidence. Every comparison passed except pooled 90 percent
   coverage, which was 0.65625 against the frozen 0.75 minimum. This adverse iteration remains at
   `benchmarks/full_network/iterations/b287c82-undercoverage/`.
4. Investigation found that local and upstream features were transformed twice. Decision 0006
   removed only the second fitted min-max transform. A calibration-only diagnostic passed the
   unchanged limits before the replacement closed loop.

The first two raw directories remain under `benchmarks/full_network/invalidated/`. They do not
evaluate the declared method. The third directory is scientifically valid and is not labeled
invalid.

## Passing evidence

The replacement matrix contains 40 complete runs, 400 system evaluations, 240 post-warm
acquisition records, 320 objective calibration records, and 160 constraint probability records.
Raw audit and derived-file reconstruction report zero issues. All actions have system scope, every
action replay matches a fresh backend, and no unresolved full-network fallback occurred.

| Criterion | Result | Value or comparison |
| --- | --- | --- |
| Complete matrix | Pass | 40 runs, 400 evaluations, 240 acquisitions |
| Raw reconstruction | Pass | 0 issues |
| System scope | Pass | 40 of 40 runs |
| Action replay | Pass | 40 of 40 runs |
| Constraint Brier score | Pass | 0.198223, maximum 0.20 |
| Pooled 90 percent coverage | Pass | 0.828125, minimum 0.75 |
| Smooth-chain coverage | Pass | 0.75 |
| Constrained-branch coverage | Pass | 0.90625 |
| Pooled median final regret | Pass | full 0.002048, system 0.002215 |
| Smooth-chain median final regret | Pass | full 0.002160, system 0.007331 |
| Constrained-branch median final regret | Pass | full 0.001889, system 0.001144 |
| Pooled median regret area | Pass | full 0.170017, system 0.175902 |
| Full-network fallbacks | Pass | 0 of 120 post-warm suggestions |

The calibration correction changed the smooth-chain closed-loop trajectory and pooled regret area,
but both methods still use identical four-point warm starts, ten-evaluation budgets, and frozen
comparison limits. The constraint Brier score passes narrowly and remains visible rather than
being combined with coverage.

## Result

Item 8 passes its completion gate. Component models fit from verified full-observation tables,
posterior propagation passes each separate numerical criterion, acquisition returns reproducible
system actions, recommendations remain observed, and the raw comparison reconstructs exactly.
The method matches the whole-system backend under the two preregistered synthetic problems. This
does not establish performance for partial observation, correlated component outputs, functional
outputs, cyclic systems, or other objective classes.

`FullNetworkBayesBackend` is a validated research backend, not part of Release A. Item 9 may begin
under the parent plan after the final repository checks for Item 8 pass.
