# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000003
- Configuration: {"a_scale":0.9793859664350748,"heat_loss":51.97851564735174,"io_scale":0.33616302929103364,"irradiance_scale":0.9891725318506359,"loss":0.6722938197199255,"rs_scale":0.7839089335811297,"rsh_scale":0.8296128756290438}
- Objective and constraint observations: {"rmse":182.1031038282294}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 4.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: ccf073787444e323687174be9c1c93c813cfcd3439c269fc49a1a8eeb03968b8
- Ledger hash: 9b34fe0be5e3cd5d621f9f8dd3bf0363624d057d7f23815e824cc80844373d7e

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
