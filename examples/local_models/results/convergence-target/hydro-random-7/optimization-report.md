# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000035
- Configuration: {"capacity":135.0558748777375,"pet":"hamon","recession":0.922497524189437}
- Objective and constraint observations: {"rmse":2.747811523367349}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 60.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: aef8bd0bd9286c46c6fd0a6f5cbc0908d69d012f07153aa11b6f62a182f3e1fb
- Ledger hash: 06de1c73ec7ce0bafea07360c43ad5a94dedd64c633a6d1f146b495e3027edd5

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
