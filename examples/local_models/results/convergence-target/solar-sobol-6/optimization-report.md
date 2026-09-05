# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"heat_loss":44.866151036694646,"loss":0.7044127462897449,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":180.38855162774908}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 2.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 836307fd48f58da152fc9be7b60cf0606f6d6c34dfbdf46e5150b33a9661d4d1
- Ledger hash: d25782be2cbc0685753119a39474e7125332ec9919623d24084d381a02a5d3dd

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
