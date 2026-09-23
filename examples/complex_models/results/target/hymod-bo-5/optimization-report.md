# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000145
- Configuration: {"alpha":0.35488793886854947,"beta":0.1,"cmax":205.19330142921058,"kfast":0.478754642057046,"kslow":0.0013358082049128482,"pet":"hamon","pet_scale":0.9613939708623401}
- Objective and constraint observations: {"rmse":1.1278788060587643}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 146.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: []
- Warnings: []
- Manifest study hash: 24c4c53f9b804cf8de78e6af8bd32edcf03661dceb2b3fef5a48fb2424b8e676
- Ledger hash: a2aafdfb3b14385e5022ee2e29d91137329eecec3c26586bc0a0d3bc82b645c4

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
