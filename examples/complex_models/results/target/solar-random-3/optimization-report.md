# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000004
- Configuration: {"heat_loss":35.5098830702,"loss":0.6527908306005816,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.09818261672692}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 5.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 6eff407c4ae11f4d38aaab480ba6eaca3d4de5e75b720ef3764a1eae6d10c2dd
- Ledger hash: 12ea7330b7ea914ebfa34d62b1837a2dbb9777ce35f1d6bce1c66f6a5f5ef126

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
