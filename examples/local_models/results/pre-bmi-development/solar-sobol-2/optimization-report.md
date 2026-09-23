# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000001
- Configuration: {"heat_loss":49.196209190413356,"loss":0.6946907972451299,"temperature":"ross"}
- Objective and constraint observations: {"rmse":177.05495208936324}
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
- Manifest study hash: a0082501ae8c4f16e7a97cf053ab7fe6bb744ed1ae0988cf626847c7de03ec3d
- Ledger hash: 63700e21064e6b857ad1bb01170ecd5cf1d55d5327b4615c472aa7ca9fc98af5

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
