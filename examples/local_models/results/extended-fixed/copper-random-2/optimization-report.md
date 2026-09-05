# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000013
- Configuration: {"model":"rational3","ridge":1.5349820686061922e-07}
- Objective and constraint observations: {"rmse":0.19597480608250212}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: f3fe8b12603c7d7ee6876e9446f817fd416c8b11e20dc0b0e8cb66f668e185d9
- Ledger hash: cc0cbadee397e9a7139bf8d8e5df91fd88260e0b67920c5abd50ce8eaa8369e4

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
