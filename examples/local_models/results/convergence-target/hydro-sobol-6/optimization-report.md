# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000051
- Configuration: {"capacity":174.051646143198,"pet":"hargreaves","recession":0.9240855702199041}
- Objective and constraint observations: {"rmse":2.2719076382488574}
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
- Manifest study hash: 444375e4e60fde5391b049f8d333184e9e4535cc9d54aef35068b08d6cf0633e
- Ledger hash: 214fc2617fcfc2bdbc8a9127ed05805cc0f1ebad7315c46986cd082dcd00f689

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
