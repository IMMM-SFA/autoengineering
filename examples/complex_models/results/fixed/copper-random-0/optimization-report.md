# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000037
- Configuration: {"model":"rational3","ridge":1.420234878594517e-07}
- Objective and constraint observations: {"rmse":0.19597447845574165}
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
- Manifest study hash: 995eba300f67aa59cd13215038ef6a1f9e12e9c7964920956538a754788b2f85
- Ledger hash: 83fd9d7456fcdd2c5112e04baa839ae157d461db40e43647885841fea16b1f6a

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
