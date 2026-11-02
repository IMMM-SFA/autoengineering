# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"capacity":74.72642179578543,"recession":0.8600565404631197}
- Objective and constraint observations: {"bias":-0.19870980391534127,"correlation":0.7939428636005004,"kge":0.7153786472141006,"nse":0.6248415150579498,"relative_bias":-0.10846002185123127,"rmse":1.999105603875805}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 16.0
- Evaluator seconds: 22.245641583111137
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: ee60983e0ea7d116e1fe72c599cbf6178cdffc0700a02d9ba588f1561c7f3ad0
- Ledger hash: 973bcdfb19c1139b88af1d3673a55c8f443638f861e12d86cc28cab85011eafc

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
