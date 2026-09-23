# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000132
- Configuration: {"capacity":144.050523750484,"pet":"hargreaves","recession":0.9482419997453689}
- Objective and constraint observations: {"rmse":2.1594096362053903}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 133.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: c3457fddae55b37e96e7dcfca1297df0d192d8bfda682d8bcc3cd7b5111618a2
- Ledger hash: f354750cfcfae16b5b69c2dd56abf95bdcaac3b956820a39004eda442d6c68fe

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
