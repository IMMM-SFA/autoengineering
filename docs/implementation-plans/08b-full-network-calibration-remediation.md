# Item 8 calibration remediation plan

_Parent plan: [`08-full-observability-function-network-bo.md`](08-full-observability-function-network-bo.md)_

_Baseline revision: `6d087aa`_

## Outcome

Correct one input-scaling mismatch in the full-observability backend, preserve the valid failed
benchmark, and repeat the frozen Item 8 gate from a clean signed revision. Do not change the
problems, warm starts, seeds, budgets, held-out points, posterior sample counts, or acceptance
limits in decision 0003.

## Evidence and diagnosis

The valid `b287c82` evidence passes numerical propagation, replay, regret, fallback, scope, raw
audit, and constraint Brier checks. Pooled 90 percent objective coverage is 0.65625, below the
frozen minimum of 0.75. Across the 320 held-out predictions, mean signed error is -0.00958, mean
absolute error is 0.11152, and mean posterior standard deviation is 0.08784. The small aggregate
bias and larger error spread indicate underestimated predictive uncertainty.

Two calibration-only diagnostics used the original warm observations, held-out points, posterior
sample count, and thresholds:

1. Excluding zero-variance columns from the kernel raised coverage to 0.696875 and produced a
   constraint Brier score of 0.13263912. This does not explain or resolve the failure.
2. Removing the fitted min-max `Normalize` transform raised coverage to 0.815625 and produced a
   constraint Brier score of 0.19829645. Both frozen calibration limits pass.

The second result matches the declared Item 8 feature contract. Local numeric features are already
mapped by their declared bounds, categorical values are already mapped by declaration order, and
upstream features are already standardized from the component table. The additional fitted
min-max transform rescales those features a second time from only four warm observations. It also
differs from `SystemBayesBackend`, which consumes its existing encoded space without a fitted input
transform.

A Student-t variance multiplier is not part of this correction. A Student-t process is a distinct
prior with a data-dependent predictive covariance, not a post hoc multiplier on a fitted Gaussian
process. Shah, Wilson, and Ghahramani describe that model and its use in Bayesian optimization at
<https://proceedings.mlr.press/v33/shah14.html>.

## Ordered implementation

1. Add a regression test that fits one scalar component model and verifies that its training and
   prediction inputs use the declared encoded and standardized coordinates without a second input
   transform.
2. Remove `Normalize` from `_fit_one`. Retain `SingleTaskGP`, `Standardize`, double precision,
   deterministic fit seeds, noise handling, retry limits, and independent posterior innovations.
3. Run focused backend and benchmark tests, then the Bayesian test suite and lint.
4. Preserve `benchmarks/full_network/results/` as a valid undercoverage iteration. Move it to
   `benchmarks/full_network/iterations/b287c82-undercoverage/` with a README that distinguishes it
   from the two invalidated runs.
5. Update evidence provenance to bind decision 0006. Test exact reconstruction and rejection of a
   changed decision or source hash.
6. Add decision 0006 after the corrected source and provenance commit. Record the diagnosis, the
   calibration-only diagnostics, unchanged protocol, source revision, and exact source hashes
   before any replacement closed-loop run.
7. Run the full 40-run comparison once from the clean signed source revision. Publish only to the
   now absent canonical result directory and retain the evidence regardless of outcome.
8. If every frozen criterion passes, update the Item 8 review, status, optimization guide, and
   parent-plan evidence. If any criterion fails, keep the backend experimental and stop before
   Item 9.
9. Run lint, default tests, Bayesian tests, Release A reconstruction, Item 8 reconstruction, scoped
   Waterology checks, whitespace checks, signed-commit verification, and a fresh signed-archive
   review at the final revision.

## Stop conditions

- Do not edit decision 0003 or any numeric acceptance limit.
- Do not combine the diagnosed scaling correction with constant-column pruning, Student-t
  innovations, variance inflation, new kernels, extra warm observations, or altered held-out data.
- Do not overwrite or relabel scientifically valid adverse evidence as invalid.
- Do not begin Item 9 unless all Item 8 gates pass at one signed revision.

## Completion gate

The remediation is complete only when the regression test proves the declared feature coordinates
reach each component GP unchanged, decision 0006 predates the replacement closed-loop evidence,
the prior adverse run remains reconstructable, the new raw evidence reconstructs exactly, and all
frozen Item 8 criteria pass at one signed revision.
