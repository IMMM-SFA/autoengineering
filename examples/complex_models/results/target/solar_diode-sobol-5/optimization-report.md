# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000000
- Configuration: {"a_scale":0.9028908483684063,"heat_loss":43.41083140578121,"io_scale":1.3357027321400123,"irradiance_scale":0.9210562103427946,"loss":0.7819669059477746,"rs_scale":1.035137489767569,"rsh_scale":1.232563232319926}
- Objective and constraint observations: {"rmse":178.84804051742753}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 1.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: bf560f86b21ac05d0b68962d86b651472364d97080f2b5bcbc0323137b0fbfbf
- Ledger hash: dd0d307d14bc82538c106d709e229de196d16ebbdc794dc47d7b6f4c9dbeef76

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
