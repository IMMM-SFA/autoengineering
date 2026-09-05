# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000004
- Configuration: {"capacity":173.049956804522,"pet":"hargreaves","recession":0.8801238177977585}
- Objective and constraint observations: {"rmse":2.6104276849140033}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 06832d8741e7e14f4ae8e52385adca81baa92b7a8c2229f3559c6f2cde7ca9e9
- Ledger hash: 6e921c6a04afee3c691aa59570842045ea1285b1bcbff7e12c70d6044f48f947

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
