# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"source_current":0.03456821138970554}
- Objective and constraint observations: {"source_power":0.11854625333653068}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.18458128720521927
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: d46443f574b90037c9647bb8e6f93f1a677ef3abd0f4095c986727d1af9ccfa7
- Ledger hash: 03b9cd48a96342785897412d1150b61cfd65c491c4824f5b6954290cccc285d9

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
