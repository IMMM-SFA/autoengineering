# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000062
- Configuration: {"a_scale":0.8742847277278215,"heat_loss":30.344480103872524,"io_scale":0.6748368098744587,"irradiance_scale":1.0545984287574808,"loss":0.621717438655792,"rs_scale":0.7856542146653639,"rsh_scale":1.9885669985739216}
- Objective and constraint observations: {"rmse":175.19874750768628}
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
- Manifest study hash: cc521bd6e4c76132d2231746de5231d2951a5b406607215b89cb1333abbab0de
- Ledger hash: c7b61b4c0a1124d8330c90685540af1d404b02f31b4e20a0a3be1dbfe06ae8a2

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
