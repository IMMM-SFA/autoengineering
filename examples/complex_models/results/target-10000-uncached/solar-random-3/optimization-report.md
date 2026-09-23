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
- Manifest study hash: 65406007f860738a4002072b7b875fee8c275bfce14250ff6c78ef79bf64670c
- Ledger hash: 12ea7330b7ea914ebfa34d62b1837a2dbb9777ce35f1d6bce1c66f6a5f5ef126

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
