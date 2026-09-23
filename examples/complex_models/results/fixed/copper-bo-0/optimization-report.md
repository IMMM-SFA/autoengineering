# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000009
- Configuration: {"model":"rational3","ridge":1.6822844249512906e-07}
- Objective and constraint observations: {"rmse":0.19597569307340712}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 5109223b96906ab0b9e9fa28072b2b20668ae29d20b59eedf0f44898db6b2398
- Ledger hash: d3b9923d8b9f010e187157d74c7d185b8ec9e59326c5868bffe7fac640b1d779

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
