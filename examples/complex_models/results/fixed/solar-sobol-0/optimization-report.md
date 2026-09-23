# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000021
- Configuration: {"heat_loss":36.033795210532844,"loss":0.6555993669200688,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.14632469072916}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 96.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: b65c7154eeba75a920a74ac81ed944a2bb7cc41d4084deb678a207b89d24b658
- Ledger hash: 121a80ac093ec747141e1ed9172dbf1d988cd2e6b26d0f21d18d8238c997f8e2

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
