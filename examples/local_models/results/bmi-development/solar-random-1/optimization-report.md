# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"heat_loss":57.77086633466709,"loss":0.6648718257238352,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.50436318663702}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 12.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 3285e88e8b41dafa38da5de46da38edea7915ff059cbc1f157c855cf076ff81d
- Ledger hash: b891052fee2a0f2bee5a712838f93be5f1945bdb0455430757377384899faf72

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
