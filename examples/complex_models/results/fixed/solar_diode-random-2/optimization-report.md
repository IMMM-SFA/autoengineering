# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000051
- Configuration: {"a_scale":0.8500128720140719,"heat_loss":55.68109964899428,"io_scale":0.40856443828676553,"irradiance_scale":1.0024290680650878,"loss":0.6996272497531815,"rs_scale":0.6428639511494002,"rsh_scale":0.8010927184163252}
- Objective and constraint observations: {"rmse":174.48570979819846}
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
- Manifest study hash: b7da60c5cef095096b612867d4e2aaf310fa8ec694391f6eb3ae2b5e9f59b733
- Ledger hash: 736343821c2172bfd61a3f40aa5776ca71756f535c40aeecca6fac17c6c6102b

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
