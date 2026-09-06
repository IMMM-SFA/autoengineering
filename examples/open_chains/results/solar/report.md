# Open model chain comparison

Observed plant validation, conditional on measured POA; 2018 selection, 2019 held-out test

Objective: selection AC power RMSE (kW) (minimize).
Selected: steady_faiman_ablation.

| Trial | Objective | Seconds | Status |
| --- | ---: | ---: | --- |
| baseline | 269.766 | 0.266 | evaluated |
| steady_faiman_ablation | 267.507 | 0.226 | evaluated |
| sapm_module | 269.616 | 0.232 | evaluated |
| faiman_u0_30 | 271.71 | 0.270 | evaluated |

Candidate selection uses the declared selection objective only.
A zero gain or failed candidate remains part of the result.

See manifest.json, trials.json, summary.json and the NPZ arrays for evidence.
