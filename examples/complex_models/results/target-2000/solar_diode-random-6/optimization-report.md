# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000002
- Configuration: {"a_scale":0.839410137436055,"heat_loss":59.398007444991265,"io_scale":0.410987399410038,"irradiance_scale":0.8777379338085054,"loss":0.726755305247748,"rs_scale":0.6797125678458801,"rsh_scale":1.5205022679734461}
- Objective and constraint observations: {"rmse":175.414405410332}
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
- Manifest study hash: ee588a448bcd1030adb58f3625c0812affafbde24abfb4b24683ed4fdbbcb15f
- Ledger hash: e8c6df25fba5a278eb0cea76a21f5eb656f2e73ee7c91db83a3f6717afcb3da7

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
