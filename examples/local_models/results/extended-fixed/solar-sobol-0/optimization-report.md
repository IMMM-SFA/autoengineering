# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000021
- Configuration: {"heat_loss":36.033795210532844,"loss":0.6555993669200688,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.14632469072916}
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
- Manifest study hash: 7ac2d049ac17850eb7fef7587e8b42ca9710a81d25092c5a72d5028a830da009
- Ledger hash: e8e2f2b0def145d3585117d429d0b025fccacbf80a51795cd906f1508b9193fd

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
