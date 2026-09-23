# Decision 0006: full-network calibration correction

_Status: Accepted after calibration investigation and before replacement execution_

_Date: 2026-09-04_

_Valid adverse run revision: `b287c826e8188ca4e02536718a6a2b495a252fbf`_

_Corrected backend revision: `87e13b3`_

_Provenance implementation revision: `4ac5f0852005217cdbfd648e73b28985d2e2551a`_

## Context

The valid Item 8 run passes raw reconstruction, replay, scope, numerical propagation, regret,
fallback, and constraint Brier criteria. Its pooled 90 percent objective interval coverage is
0.65625, below the frozen minimum of 0.75. The evidence remains at
`benchmarks/full_network/iterations/b287c82-undercoverage/` as a valid adverse result.

Across the 320 held-out records, mean signed error is -0.00958, mean absolute error is 0.11152,
and mean posterior standard deviation is 0.08784. This indicates underestimated predictive spread
without a comparable pooled mean bias.

The backend applied two input transformations. `_encode_feature` maps local numeric values using
declared bounds, maps categories by declaration order, and standardizes upstream features from the
component table. `_fit_one` then applied BoTorch's fitted min-max `Normalize` transform using only
the four warm observations. The second transform was not part of the Item 8 feature contract and
did not match the whole-system backend's use of its already encoded coordinates.

## Calibration-only diagnostics

Two diagnostic variants used the original warm observations, deterministic held-out points, 256
posterior samples, and unchanged gate calculations. Neither variant ran a replacement closed loop.

1. Ignoring zero-variance columns in the ARD kernel produced 0.696875 pooled coverage and a
   0.13263912 constraint Brier score. The coverage criterion still failed, so this variant was
   rejected.
2. Removing only the second input transform produced 0.815625 pooled coverage and a 0.19829645
   constraint Brier score. Both frozen calibration criteria passed.

We do not add a Student-t multiplier or other interval inflation. A Student-t process uses a
distinct prior and data-dependent predictive covariance. It is not equivalent to multiplying the
posterior variance of a fitted Gaussian process. Shah, Wilson, and Ghahramani describe the model
and its Bayesian optimization use at <https://proceedings.mlr.press/v33/shah14.html>.

## Correction

1. Pass the declared encoded and standardized component coordinates directly to `SingleTaskGP`.
2. Retain one independent `SingleTaskGP` for each scalar output, `Standardize` outcome transforms,
   double precision, deterministic fit seeds, existing noise handling, bounded retries, and
   independent posterior innovations.
3. Add a regression test that fits component models and confirms no fitted input transform changes
   their training or prediction coordinates.
4. Bind replacement evidence to this decision in addition to decisions 0003, 0004, and 0005.
5. Run the full 40-run matrix once from a clean signed revision. Retain the result whether it passes
   or fails.

## Unchanged protocol

Decision 0003 remains authoritative. The problems, analytic functions, ten seeds, shared four-point
warm starts, ten-evaluation budgets, candidate counts, posterior sample counts, held-out points,
measurements, and acceptance limits do not change. The replacement run will still stop Item 9 if
any frozen criterion fails.

## Source binding

The corrected aggregate source hash is
`de14145ef1ac5041f898ecaba64da4d78c6b9e20e5dec8f5815057e34b598de4`.

| Source | SHA-256 |
| --- | --- |
| `pixi.lock` | `2a14a7a6c4c74870ee2820028f69140151e80efb897a825c8e3359c4e2d82fd5` |
| `pixi.toml` | `3f4b1488f360aced5f79e3f38305ac05eed4ac6ed6eef5ffc384915a0e570868` |
| `pyproject.toml` | `50367045d7d43a42adb4a2d4ca90b5c9d642ed7babe512ac6a62800c194a2ca9` |
| `src/autoengineering/benchmarks/full_network/__init__.py` | `6c00c1757a15bd7faf1e01bd5740a0a47274c27df32312301aca7165843a8b4c` |
| `src/autoengineering/benchmarks/full_network/__main__.py` | `3f4212bd6d2ed02ccb2c2864965e2850e76eef4fd52a61ca474be19af54059d5` |
| `src/autoengineering/benchmarks/full_network/problems.py` | `8e7fc03a382b293617fbedf5c68397ca51257c123de0c00ada3b2f68277fa5df` |
| `src/autoengineering/benchmarks/full_network/runner.py` | `49b403a80683b857e2130b40d7249ece0609871ae9009301268cc0eb801a4df8` |
| `src/autoengineering/benchmarks/full_network/summary.py` | `8592c48dd075a1a3c0f585c37f349b4f6704bbb89acdfa3c27fcd7d3f31e6c87` |
| `src/autoengineering/optimization/backend.py` | `50ef7eed714678b6b5b9cde4e8aa47d2d28de45bd3d8e64944e8ca1a41e1a7a9` |
| `src/autoengineering/optimization/full_network_backend.py` | `f4ddbb0d2f3b2f655f0945a06aa88bb2474f086ec1570e957482aefde28dd848` |
| `src/autoengineering/optimization/function_network.py` | `b076160c472aa6aeb9ddd33d06aa53badbf115764c27d57825463b1ca50f4376` |
| `src/autoengineering/optimization/function_network_evaluator.py` | `9ffbc1b4d35d39c55982c2cd91034223aeb7852030bb891b4ab11a05085bec15` |
| `src/autoengineering/optimization/ledger.py` | `e137064014cc337a0643cc76b3cf7f4adc5772ca920ed5cd8c078310b3dbda63` |
| `src/autoengineering/optimization/records.py` | `47f92d0c169c4026f813b5a8b58522e550eb4510c43f767351b6cd1de0ed8425` |
| `src/autoengineering/optimization/space.py` | `7b8ebfb55ae072ea2e82f57a3f8ff00c6895be4bd4adc9d8bbc6ef4fc7e54652` |
| `src/autoengineering/optimization/spec.py` | `87df5c77ed379718fa547add64233c02ff9551cde21426be23c7a7a6d46a597e` |
| `src/autoengineering/optimization/system_backend.py` | `d24a83776010691d425b9aabfd6b3abf03e44423396796ea434c45a75624d0cf` |
| `src/autoengineering/research/runner.py` | `3c56db99d10bb90f5230e5c197a82721df00a4a454830755e8d9598735821fec` |
