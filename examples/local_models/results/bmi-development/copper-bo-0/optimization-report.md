# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000009
- Configuration: {"model":"rational3","ridge":1.6822844249512906e-07}
- Objective and constraint observations: {"rmse":0.19597569307340712}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 89113bdfa9e4dc39eee6ed523fc98c7986cd2e6b2fe942bf5bc553be85f7004c
- Ledger hash: c2b98a5f0027151f1ec568151731ea6d30bf0015f05e2ce383c27ef07c3710a8

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
