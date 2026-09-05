# Optimization study

## Recommendation

- Feasible: True
- Action: eval-000010
- Configuration: {"alpha":0.39240775350481266,"beta":1.6396836940199138,"cmax":837.2536427529778,"kfast":0.4930680178105832,"kslow":0.0010646093654879526,"pet":"hamon","pet_scale":0.7830921672284603}
- Objective and constraint observations: {"rmse":1.324806984326992}
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
- Manifest study hash: edc42d3ea886355de3f59b4b9a207741d7d7ac144049b143944f88e91f4fbad8
- Ledger hash: 57f9a229c9fb39cdc1abd20c9821bf624cbc23e2d0acb65ac9ea4d85865c7311

## Verification

- `python -m pytest tests -q -p no:cacheprovider`
- `ruff check src tests`
