# Optimization study

## Recommendation

- Feasible: True
- Action: eval-001182
- Configuration: {"alpha":0.3002336960285902,"beta":0.1312835557386279,"cmax":383.8166001943065,"kfast":0.49634642750024793,"kslow":0.004458660310757379,"pet":"hamon","pet_scale":0.958974277600646}
- Objective and constraint observations: {"rmse":1.2409272271422602}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 10000.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: d053fc49e2f3429ff07c157f0fa9b6e17855ab1d46a9f0e1890231d345e36d12
- Ledger hash: 4cd42ff822cb7df3b3723d164bef5142340e3cb8fa7c310bed9028d871df16b4

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
