# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000002
- Configuration: {"x_0":16.953522190451622,"x_1":588.8567230477929,"x_2":17.066110596060753,"x_3":576.4395950362086,"y_0":15.329660661518574,"y_1":20.670292526483536,"y_2":594.8552502319217,"y_3":593.6996821314096}
- Objective and constraint observations: {"annual_energy":30.068129320901953}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 4.0
- Evaluator seconds: 4.7389501659199595
- Optimizer overhead seconds: 0.0
- Stop reason: max_cost
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: be14d8b4eda2d895162409dad8b9f09dc52faa0a90d31af6478d50f16ca28c7e
- Ledger hash: 4e2053283cb764b869aad8024a8990230def26243dc80eb666dd723104e41014

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
