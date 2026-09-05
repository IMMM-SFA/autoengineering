# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000076
- Configuration: {"a_scale":0.9019914783537388,"heat_loss":26.954654906876385,"io_scale":1.1482460641413244,"irradiance_scale":1.121814269479364,"loss":0.6269811049103736,"rs_scale":0.8522531180659161,"rsh_scale":0.7084739921700118}
- Objective and constraint observations: {"rmse":175.44886106225874}
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
- Manifest study hash: a260c26b96acba8d6d75b0b1c8a9d50fd1b21d108251ea4f87fe431719b8a494
- Ledger hash: 7ef5d6f55a7af9dd862d634379adbb6c043c39147d737b2344eb301bcbfd9dd1

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
