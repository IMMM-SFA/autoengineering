# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000060
- Configuration: {"capacity":199.44663639164142,"pet":"hargreaves","recession":0.9322684485292018}
- Objective and constraint observations: {"rmse":2.1783949225998622}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 200.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: f6e3cf07c28717111c148e1f8dbfd8fcc660198d7fc2488c6919da320a94040e
- Ledger hash: 7efdf8916d7a44c100eec9110e22cc75fd1e9f340a1c83d9ad220e5cb0645fdb

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
