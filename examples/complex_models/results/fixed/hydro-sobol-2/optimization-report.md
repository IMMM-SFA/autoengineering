# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000065
- Configuration: {"capacity":154.16147004812956,"pet":"hargreaves","recession":0.9310304195620119}
- Objective and constraint observations: {"rmse":2.270650852440263}
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
- Manifest study hash: d597c83973daad230a746385bdf80dcb3c7716b49a0b5c15145db1afcd88ff8e
- Ledger hash: 3a3fb92c37139552597fac3bca1b40528d6dd998d9085f35c8959e5208d14449

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
