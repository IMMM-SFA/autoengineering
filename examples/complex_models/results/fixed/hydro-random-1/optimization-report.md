# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000054
- Configuration: {"capacity":197.6008587259287,"pet":"hargreaves","recession":0.947583551610397}
- Objective and constraint observations: {"rmse":2.0813210754763407}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 4acfcaf14b74920374ccc4158fff2b19bb52ff0b62fc4c31ec80680cc2044ef7
- Ledger hash: 5e88023ea4a3bcf8bf917798e762fc9b383a2332d2bb30ea3ce90262cd6a5bc9

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
