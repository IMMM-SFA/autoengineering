# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000003
- Configuration: {"a_scale":0.9793859664350748,"heat_loss":51.97851564735174,"io_scale":0.33616302929103364,"irradiance_scale":0.9891725318506359,"loss":0.6722938197199255,"rs_scale":0.7839089335811297,"rsh_scale":0.8296128756290438}
- Objective and constraint observations: {"rmse":182.1031038282294}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 4.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 74f4cdf9e2d395b627a3db31c54a74b969d9889b433a0b319d4d911a7454c2f0
- Ledger hash: 171f7a42e87a318a73c27865a8586b89c4619e41b4928152cead80a0fa6dff44

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
