# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"heat_loss":19.75890921894461,"loss":0.6400053611956537,"temperature":"ross"}
- Objective and constraint observations: {"rmse":180.00165734869987}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 1.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 586dc50ea0f0087dea7bc0ce94db5d158b3768737d1b5bf2dab2783d7ef78f87
- Ledger hash: d8a47b1ebc19445c0025cecca4ea2e233bac2689e2f95debb44e1ee7b3e0ef6b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
