# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000012
- Configuration: {"a_scale":0.9267526727361975,"heat_loss":22.33804046922797,"io_scale":1.4927007615322263,"irradiance_scale":1.0340196247962843,"loss":0.6244788234960684,"rs_scale":0.6684850702251943,"rsh_scale":1.6541657835517813}
- Objective and constraint observations: {"rmse":175.0871725624283}
- Message: best feasible observed configuration

## Evidence

- Standard errors: {}
- Total evaluator cost: 13.0
- Evaluator seconds: 0.0
- Optimizer overhead seconds: 0.0
- Stop reason: not_terminal
- Resume pending actions: 0

## Diagnostics

- Fallback events: ["baseline policy does not fit a surrogate"]
- Warnings: []
- Manifest study hash: 3016707723c2af2bec04f503c8a18862196327b8adb42c5d6233cf57aa5bac28
- Ledger hash: 242869791045b8f1b0fb39dc02731347d24af769abdf3ab62a22d47bd4cecfb5

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
