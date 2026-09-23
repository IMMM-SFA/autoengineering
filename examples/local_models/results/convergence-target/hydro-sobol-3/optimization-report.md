# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000044
- Configuration: {"capacity":186.84088258072734,"pet":"hargreaves","recession":0.8986374843865632}
- Objective and constraint observations: {"rmse":2.4373551567681786}
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
- Manifest study hash: c82a9d3bfc0a03afc1a3c0df8767c2315a2a5a2b2b8ffb3989b735bb08fc7406
- Ledger hash: f558373697b51ebef34de6721c244fa8919ff401a04e572f5f472b3956dd3bfd

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
