# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000060
- Configuration: {"capacity":178.18073878064752,"pet":"hargreaves","recession":0.9334500428289174}
- Objective and constraint observations: {"rmse":2.1961420965485825}
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
- Manifest study hash: d56096f8c291c8ee6682cc33e886c08e470c220d7a9692bb1ad7923c6a783644
- Ledger hash: 39201bfe85d245e3792e65669fc8c46dac214548cb299f97057e887208a897a1

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
