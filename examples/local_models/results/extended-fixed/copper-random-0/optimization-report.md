# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000020
- Configuration: {"model":"rational3","ridge":1.0992973567494855e-07}
- Objective and constraint observations: {"rmse":0.1959753352224791}
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
- Manifest study hash: 295b4d860d615d75333cbd6239034d3b703988da1ad62db8835520d6fe9f3854
- Ledger hash: d8708bbfb57eba982c6e768d5f4cf9cc586ca3da87ef6fa354237b1044007576

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
