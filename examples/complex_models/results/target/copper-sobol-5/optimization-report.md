# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000004
- Configuration: {"model":"rational3","ridge":1.5030681329180061e-06}
- Objective and constraint observations: {"rmse":0.1969853492470523}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 5.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: b4450e9b0fa6d63428eb1881d3fdeeb6e9270c395a355849ae7b69a46999d277
- Ledger hash: 3b5f350703dbb6e4993a83174f80b6f332229e522cd8c090ad7567e518df3b1a

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
