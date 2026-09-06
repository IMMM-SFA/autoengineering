# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000005
- Configuration: {"capacity":200.0,"pet":"hargreaves","recession":0.95}
- Objective and constraint observations: {"rmse":2.0659955546313915}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 6.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 80940dae667073b8511e15cbaecb89ebcafea40c97ba96aeb2706eac54bf2847
- Ledger hash: cf3923bb20d3d37b692975aebd6346b1fd98c18eddebb4835ef3f7934182eb52

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
