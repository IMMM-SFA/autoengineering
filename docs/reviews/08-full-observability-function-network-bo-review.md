# Item 8 review: full-observability function-network BO

_Review date: 2026-09-04_

_Final execution revision: `b287c82`_

_Evidence revision: `01f1844`_

## Scope

This review covers the optional full-observability backend, verified component training data,
posterior propagation, system-only acquisition, deterministic action replay, numerical fixtures,
the preregistered comparison, invalidated runs, and final evidence. It does not review component
action selection because Item 9 has not started.

## Backend contract

`FullNetworkBayesBackend` requires an exact match among the study, global search space, function
network, and system. Every scalar component output must be observed during a complete system
evaluation. Training rows come from digest-verified NPZ traces reconstructed by Item 7. A
component-scope ledger row is rejected.

The backend fits an independent double-precision `SingleTaskGP` for each executable component
output. Source outputs use empirical constants. Local parameters and sampled upstream coupling
values form each component input. Posterior propagation draws independent seeded innovations for
each output and path in topological order. The acquisition is constrained Monte Carlo expected
improvement over 64 deterministic Sobol candidates with 128 samples. Suggestions have system scope,
and recommendations always refer to observed feasible system results.

## Numerical checks

The affine fixture uses 65,536 posterior samples and passes the frozen mean, variance, constraint
probability, nonnegative variance, and byte replay limits. Fresh fitted instances reproduce
posterior arrays and actions. State and identity records contain constructor settings and
diagnostics, not fitted model objects. The base optimization package remains importable without
Torch or BoTorch.

## Preregistration and corrections

Decision 0003 froze two problems, ten seeds, four shared Sobol observations, ten evaluations per
run, calibration data, and all numeric limits before the comparison. Two invalidated runs are
retained:

1. Revision `34b9984` failed before evaluation because the platform temporary path used a symlinked
   alias that the evaluator correctly rejected. Decision 0004 resolved the temporary root, sorted
   audit output, retained partial records, and strengthened trace checks.
2. Revision `ed9ac99` exposed collapsed posterior uncertainty. The backend requested one joint
   function draw over repeated propagation rows instead of the independent innovations stated in
   the plan. Its audit also rejected valid intermediate outcomes and compared process-dependent
   warning lists. Decision 0005 corrected those defects without changing the scientific protocol.

Both raw evidence directories remain under `benchmarks/full_network/invalidated/` with their
reports, gates, and provenance.

## Final evidence

The final matrix contains 40 complete runs, 400 system evaluations, 240 post-warm acquisition
records, 320 objective calibration records, and 160 constraint probability records. Raw audit and
derived-file reconstruction report zero issues. All actions have system scope, every action replay
matches a fresh backend, and no unresolved full-network fallback occurred.

| Criterion | Result | Value or comparison |
| --- | --- | --- |
| Complete matrix | Pass | 40 runs, 400 evaluations, 240 acquisitions |
| Raw reconstruction | Pass | 0 issues |
| System scope | Pass | 40 of 40 runs |
| Action replay | Pass | 40 of 40 runs |
| Constraint Brier score | Pass | 0.134541, maximum 0.20 |
| Pooled 90 percent coverage | Fail | 0.65625, minimum 0.75 |
| Pooled median final regret | Pass | full 0.002048, system 0.002215 |
| Smooth-chain median final regret | Pass | full 0.002729, system 0.007331 |
| Constrained-branch median final regret | Pass | full 0.001889, system 0.001144 |
| Pooled median regret area | Pass | full 0.176417, system 0.175902 |
| Full-network fallbacks | Pass | 0 of 120 post-warm suggestions |

Coverage was 0.63125 on the smooth chain and 0.68125 on the constrained branch. It was not a
single-problem or bookkeeping failure. Four observations were insufficient for calibrated nominal
90 percent intervals under the fitted independent Gaussian process assumptions, even though the
closed-loop decisions matched the whole-system method.

The checked command reconstructs every derived artifact and exits 1 because the coverage criterion
fails. This is the intended gate behavior, not a command error.

## Result

Item 8 does not pass its completion gate. The implementation provides a reproducible experimental
backend and a clean null-to-favorable optimization comparison, but its uncertainty intervals are
undercovered under the frozen protocol. The criterion was not relaxed and no proxy replaced it.
`FullNetworkBayesBackend` remains experimental. The parent plan forbids Item 9 until the Item 8
numerical, calibration, replay, and comparison gates all pass, so partial-observability work has not
started.
