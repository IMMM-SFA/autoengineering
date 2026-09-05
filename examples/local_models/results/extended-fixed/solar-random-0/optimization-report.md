# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000021
- Configuration: {"heat_loss":57.52982634545167,"loss":0.6635024759223785,"temperature":"ross"}
- Objective and constraint observations: {"rmse":175.45455563953095}
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
- Manifest study hash: 0540cc40aee096d3372dd5bb65709aadcff01fc7d5eb5bf90986cca0119e3309
- Ledger hash: e66cff43064ef956515c3cd2f280bb4f3522dfb39730afe486f4c55a7ac0b4f3

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
