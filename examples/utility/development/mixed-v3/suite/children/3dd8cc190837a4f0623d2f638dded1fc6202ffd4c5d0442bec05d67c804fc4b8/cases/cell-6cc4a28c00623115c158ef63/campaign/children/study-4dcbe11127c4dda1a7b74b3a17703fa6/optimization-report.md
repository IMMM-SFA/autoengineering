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
- Evaluator seconds: 20.788418334443122
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: ee60983e0ea7d116e1fe72c599cbf6178cdffc0700a02d9ba588f1561c7f3ad0
- Ledger hash: adae6c70c2fd71b20ef1d6534279d0ca3e84a1ac8602726e11df763f334d0e9c

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
