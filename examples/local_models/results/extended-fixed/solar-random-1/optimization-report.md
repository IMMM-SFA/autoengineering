# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000013
- Configuration: {"heat_loss":56.2440591862284,"loss":0.6498768672765514,"temperature":"ambient"}
- Objective and constraint observations: {"rmse":175.07793636465613}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 24.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 3a7f1d70101bc240a4705fc158553a15e6ebdfc95c09397c14202b9a949bb0f7
- Ledger hash: ad0e94be4c2c749257a34050e596946d1e127615a04d9a413e980becdc46b84c

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
