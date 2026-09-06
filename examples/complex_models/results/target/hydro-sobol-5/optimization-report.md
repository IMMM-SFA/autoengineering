# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000195
- Configuration: {"capacity":150.28037210926414,"pet":"hargreaves","recession":0.9394870708696543}
- Objective and constraint observations: {"rmse":2.2145477776302718}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 200.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 50316b14d09794d29979b54f4fa5ee2865ec921052648d3084c07ff71ac40f4d
- Ledger hash: ce69513d5815b49eb78ebd0906ac67fd1f28553d217efe37a0b9297ebedcdeb3

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
