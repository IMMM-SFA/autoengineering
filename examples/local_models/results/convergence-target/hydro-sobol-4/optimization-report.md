# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000019
- Configuration: {"capacity":151.45953606814146,"pet":"hargreaves","recession":0.9285466043278574}
- Objective and constraint observations: {"rmse":2.298887175851291}
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
- Manifest study hash: 321c37298c66268cbb614d20c347414b34b7adc3a649896c317b3acacf33a567
- Ledger hash: b82588f75d4d7f48cb301064846161f992196a69ab8e5077d4d1f9d4e5288f05

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
