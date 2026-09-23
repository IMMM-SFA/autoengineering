# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000002
- Configuration: {"a_scale":0.8181798393629074,"heat_loss":16.14930677995928,"io_scale":0.30007820507411803,"irradiance_scale":1.0729922243090857,"loss":0.8062496871841458,"rs_scale":1.5442248196247186,"rsh_scale":0.595623412728885}
- Objective and constraint observations: {"rmse":179.67599970223029}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 3.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: c31025d94f51e75ff347e65df4a6d5584e6e95e91c65835eb6913d8bfaf4fd04
- Ledger hash: 67fb8deb1fee8503f05645dd4b40b2a2c5e8af448df8e1f49bb9ea0fbc597915

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
