# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000002
- Configuration: {"heat_loss":52.402018806897104,"loss":0.6217362124007195,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":176.4353468192891}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 3.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 052e76363b99aac92650614ac22bba74c023c83710697bceff540f012cde3ac0
- Ledger hash: 42c65c7964291a3d3a8716f6c5e95623ea6368dbf662d920328ffdb98a1df6ae

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
