# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000007
- Configuration: {"capacity":159.8829458888144,"pet":"hargreaves","recession":0.7692523218244088}
- Objective and constraint observations: {"rmse":3.5643115938853236}
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
- Manifest study hash: 255804dea35f7d5e9b1c516a3c026e5382b94835b3d6c0a1ad73a89d3f4cf58f
- Ledger hash: 8ba77b5f6447a95ed66d66a3ddc09bed2a04b057e8a00aa070896017de386937

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
