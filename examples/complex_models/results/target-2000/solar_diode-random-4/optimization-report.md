# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000004
- Configuration: {"a_scale":0.8347592755321248,"heat_loss":27.363385709943998,"io_scale":1.683487332957199,"irradiance_scale":0.9346710161071522,"loss":0.7547333109608979,"rs_scale":0.5349258268393575,"rsh_scale":1.103770217578356}
- Objective and constraint observations: {"rmse":174.52558844617283}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 5.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 9a98222e9e1616168bf89bb33ecdd51459c5cc646f7c16d0e49ac8a1da7cc933
- Ledger hash: c2ec393dcc31170b85ae56629795b52c277c78f01d924c527488bcc0017c9905

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
