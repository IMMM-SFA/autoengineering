# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000367
- Configuration: {"capacity":179.30001353845,"pet":"hargreaves","recession":0.9466763549484312}
- Objective and constraint observations: {"rmse":2.1028862464851716}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 368.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 8f7d7e514a2911dfc2aa7e0e502abb1863e09bd22b5ba4fc5f249663d218a498
- Ledger hash: efe24f16e3c6708efc7d56c62c105734cf052e0111a67243f476baab42d6b150

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
