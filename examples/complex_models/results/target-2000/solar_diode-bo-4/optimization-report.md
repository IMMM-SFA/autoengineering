# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000009
- Configuration: {"a_scale":0.8,"heat_loss":25.165812654228525,"io_scale":0.3,"irradiance_scale":0.85,"loss":0.7747684110551876,"rs_scale":0.7653610343349819,"rsh_scale":2.0}
- Objective and constraint observations: {"rmse":176.97847571102696}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 10.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: dd353b51cc8f0e328ffafa4d881ef2edd6e8754da66f7b0866a5891edfd9bc45
- Ledger hash: 0c8fe9cdaf02e049460bc16c82fae4d47bf6364585b5982c477be2aed9021c4e

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
