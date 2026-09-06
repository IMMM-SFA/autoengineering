# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000008
- Configuration: {"a_scale":0.9089433308690786,"heat_loss":54.13117772899568,"io_scale":1.0349910307386425,"irradiance_scale":0.9289976802654564,"loss":0.837648831680417,"rs_scale":1.3996792116800651,"rsh_scale":0.7259125245628196}
- Objective and constraint observations: {"rmse":181.736419852539}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 9.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 28377a8e2a7ba58d7afdcfa608a1be2d785422f1f1ec86fe84dbf464b3f959bb
- Ledger hash: f3c2bb590fa54c89398ed766b9571b48260822f9557d6b59031cedc3fb4678a8

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
