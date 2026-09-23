# Extended BMI search results

Fixed comparison: 27 studies, 648 calls. Target comparison: 45 studies, 745 calls.

## 12 versus 24 complete-model evaluations

Median RMSE across the same three seeds. Lower is better. All 27 extended runs reproduce their original first 12 ledger entries exactly. Test results are computed only after validation selects the recommendation.

| Domain | Method | Validation at 12 | Validation at 24 | Test at 12 | Test at 24 |
| --- | --- | ---: | ---: | ---: | ---: |
| hydro | random | 2.787593 | 2.787593 | 2.825035 | 2.825035 |
| hydro | sobol | 3.401117 | 2.589878 | 2.827094 | 2.809316 |
| hydro | bo | 2.065996 | 2.065996 | 2.883923 | 2.883923 |
| solar | random | 175.680321 | 175.454556 | 116.857693 | 123.354578 |
| solar | sobol | 176.133176 | 175.258418 | 118.964160 | 119.678749 |
| solar | bo | 175.077562 | 175.077562 | 121.941722 | 121.940106 |
| copper | random | 0.196292 | 0.195975 | 0.248874 | 0.247905 |
| copper | sobol | 0.195993 | 0.195993 | 0.247674 | 0.247674 |
| copper | bo | 0.195978 | 0.195976 | 0.247930 | 0.247930 |

## Evaluations to a frozen validation target

Targets are 1.05 times the lowest original validation RMSE, pooled across all methods. Five new seeds (3-7) are used. The limit is 60 calls, including initialization. This measures time to a quality target, not convergence to a global optimum.

| Domain | Target RMSE | Method | Reached | Calls, seeds 3-7 | Median calls among successes | Mean calls consumed | Median study seconds, all runs | Median test RMSE, all runs |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| hydro | 2.169295 | random | 0/5 | >60, >60, >60, >60, >60 | NA | 60.0 | 5.685 | 2.797928 |
| hydro | 2.169295 | sobol | 0/5 | >60, >60, >60, >60, >60 | NA | 60.0 | 5.627 | 2.819464 |
| hydro | 2.169295 | bo | 5/5 | 6, 6, 7, 6, 7 | 6 | 6.4 | 0.753 | 2.883923 |
| solar | 183.831438 | random | 5/5 | 5, 2, 11, 3, 2 | 3 | 4.6 | 0.297 | 120.690982 |
| solar | 183.831438 | sobol | 5/5 | 3, 1, 4, 2, 4 | 3 | 2.8 | 0.310 | 137.800383 |
| solar | 183.831438 | bo | 5/5 | 3, 1, 4, 2, 4 | 3 | 2.8 | 0.307 | 137.800383 |
| copper | 0.205774 | random | 5/5 | 1, 8, 3, 7, 2 | 3 | 4.2 | 0.227 | 0.251350 |
| copper | 0.205774 | sobol | 5/5 | 4, 1, 5, 1, 12 | 4 | 4.6 | 0.388 | 0.249160 |
| copper | 0.205774 | bo | 5/5 | 4, 1, 5, 1, 7 | 4 | 3.6 | 0.380 | 0.249160 |

A >60 entry is censored: the target was not reached within the budget. Median successful calls exclude those runs and must be read alongside the success fraction. Mean calls consumed includes caps and is a restricted computational cost, not an estimated mean time to eventual success. Unequal success rates prevent a standalone ranking by that mean. Backend termination is labeled separately with its actual horizon. Missing test results are shown as NA, not silently dropped.

## Interpretation

Hydrology shows a clear validation-search benefit for BO at this frozen target: every BO run succeeds, while random and Sobol exhaust the cap. However, the BO recommendations have worse median held-out RMSE than either baseline. Efficient validation optimization is distinct from better generalization.

Every solar BO run stops within its four initial Sobol points. This target does not exercise adaptive BO on solar. Copper targets are also usually reached quickly, with only a small difference in consumed calls. Future more demanding targets would need a separate protocol; these targets were not changed after seeing the outcomes.

## Timing and expensive-model implications

Study seconds include optimizer and durable controller work. Model seconds measure BMI evaluations. Imports, input loading, backend construction and held-out scoring are excluded. Runs are sequential with rotated method order and one Torch CPU thread. Target mode also checks a recommendation after each call, so compare timing within each experiment. The fixed extension first solar study includes a lazy pvlib import; target runs preimport pvlib. These are single-machine measurements, not repeated timing trials.

| Domain | Method | Median model seconds | Median optimizer/controller seconds |
| --- | --- | ---: | ---: |
| hydro | random | 1.5272 | 4.1579 |
| hydro | sobol | 1.4444 | 4.1830 |
| hydro | bo | 0.1374 | 0.6155 |
| solar | random | 0.0623 | 0.2350 |
| solar | sobol | 0.0694 | 0.2406 |
| solar | bo | 0.0671 | 0.2388 |
| copper | random | 0.0320 | 0.1953 |
| copper | sobol | 0.0636 | 0.3244 |
| copper | bo | 0.0562 | 0.3236 |

For a hypothetical constant model cost C, study time is approximately N*C + H, where N is calls and H is optimizer/controller overhead. When BO reaches the same target in fewer calls, its break-even cost against another method is (H_BO - H_other)/(N_other - N_BO), floored at zero. This projection assumes unchanged search trajectories and overhead. It is not a measurement on a more complex model. Fewer evaluations cannot be claimed when BO uses more calls or fails to hit the target.

## Individual target runs

| Domain | Method | Seed | Status | Calls | Validation RMSE | Test RMSE | Model seconds | Study seconds |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| hydro | random | 3 | evaluation_cap | 60 | 2.660527 | 2.797928 | 1.2021 | 4.4757 |
| hydro | sobol | 3 | evaluation_cap | 60 | 2.437355 | 2.813549 | 1.1799 | 4.4878 |
| hydro | bo | 3 | target_reached | 6 | 2.065996 | 2.883923 | 0.1214 | 1.3487 |
| hydro | sobol | 4 | evaluation_cap | 60 | 2.298887 | 2.812725 | 1.2529 | 4.7172 |
| hydro | bo | 4 | target_reached | 6 | 2.065996 | 2.883923 | 0.1266 | 0.5796 |
| hydro | random | 4 | evaluation_cap | 60 | 2.474048 | 2.790474 | 1.4513 | 5.3685 |
| hydro | bo | 5 | target_reached | 7 | 2.065996 | 2.883923 | 0.1374 | 0.7529 |
| hydro | random | 5 | evaluation_cap | 60 | 2.650838 | 2.838764 | 1.5272 | 5.6851 |
| hydro | sobol | 5 | evaluation_cap | 60 | 2.424767 | 2.820940 | 1.5460 | 5.9707 |
| hydro | random | 6 | evaluation_cap | 60 | 2.393811 | 2.820809 | 1.5841 | 5.9892 |
| hydro | sobol | 6 | evaluation_cap | 60 | 2.271908 | 2.819464 | 1.4444 | 5.6275 |
| hydro | bo | 6 | target_reached | 6 | 2.065996 | 2.883923 | 0.1520 | 0.6948 |
| hydro | sobol | 7 | evaluation_cap | 60 | 2.252318 | 2.821831 | 1.5451 | 6.0335 |
| hydro | bo | 7 | target_reached | 7 | 2.065996 | 2.883923 | 0.1799 | 0.9217 |
| hydro | random | 7 | evaluation_cap | 60 | 2.747812 | 2.791899 | 1.6929 | 6.3618 |
| solar | random | 3 | target_reached | 5 | 175.098183 | 120.690982 | 0.1328 | 0.5206 |
| solar | sobol | 3 | target_reached | 3 | 176.435347 | 136.142367 | 0.0694 | 0.3100 |
| solar | bo | 3 | target_reached | 3 | 176.435347 | 136.142367 | 0.0679 | 0.3067 |
| solar | sobol | 4 | target_reached | 1 | 180.001657 | 156.260847 | 0.0221 | 0.1449 |
| solar | bo | 4 | target_reached | 1 | 180.001657 | 156.260847 | 0.0197 | 0.1410 |
| solar | random | 4 | target_reached | 2 | 175.534471 | 116.719455 | 0.0389 | 0.2268 |
| solar | bo | 5 | target_reached | 4 | 176.715677 | 137.800383 | 0.0671 | 0.3066 |
| solar | random | 5 | target_reached | 11 | 176.715621 | 114.106477 | 0.2638 | 0.9992 |
| solar | sobol | 5 | target_reached | 4 | 176.715677 | 137.800383 | 0.0845 | 0.3823 |
| solar | random | 6 | target_reached | 3 | 176.559347 | 124.325159 | 0.0623 | 0.2973 |
| solar | sobol | 6 | target_reached | 2 | 180.388552 | 114.677625 | 0.0449 | 0.2200 |
| solar | bo | 6 | target_reached | 2 | 180.388552 | 114.677625 | 0.0393 | 0.2306 |
| solar | sobol | 7 | target_reached | 4 | 176.892497 | 138.327203 | 0.1153 | 0.4152 |
| solar | bo | 7 | target_reached | 4 | 176.892497 | 138.327203 | 0.0857 | 0.3474 |
| solar | random | 7 | target_reached | 2 | 176.343837 | 129.342677 | 0.0440 | 0.2009 |
| copper | random | 3 | target_reached | 1 | 0.196072 | 0.248394 | 0.0096 | 0.0898 |
| copper | sobol | 3 | target_reached | 4 | 0.204167 | 0.256626 | 0.0636 | 0.3879 |
| copper | bo | 3 | target_reached | 4 | 0.204167 | 0.256626 | 0.0562 | 0.3798 |
| copper | sobol | 4 | target_reached | 1 | 0.195984 | 0.247734 | 0.0170 | 0.1321 |
| copper | bo | 4 | target_reached | 1 | 0.195984 | 0.247734 | 0.0126 | 0.1333 |
| copper | random | 4 | target_reached | 8 | 0.198310 | 0.251350 | 0.1020 | 0.6400 |
| copper | bo | 5 | target_reached | 5 | 0.195979 | 0.247773 | 0.0573 | 0.5313 |
| copper | random | 5 | target_reached | 3 | 0.205729 | 0.257931 | 0.0320 | 0.2273 |
| copper | sobol | 5 | target_reached | 5 | 0.196985 | 0.249880 | 0.0811 | 0.4222 |
| copper | random | 6 | target_reached | 7 | 0.199712 | 0.252712 | 0.0932 | 0.5355 |
| copper | sobol | 6 | target_reached | 1 | 0.196463 | 0.249160 | 0.0117 | 0.1037 |
| copper | bo | 6 | target_reached | 1 | 0.196463 | 0.249160 | 0.0181 | 0.1292 |
| copper | sobol | 7 | target_reached | 12 | 0.195981 | 0.247751 | 0.1761 | 1.0353 |
| copper | bo | 7 | target_reached | 7 | 0.196505 | 0.249225 | 0.1095 | 1.0183 |
| copper | random | 7 | target_reached | 2 | 0.195982 | 0.247744 | 0.0278 | 0.1906 |

## Evidence and limits

Raw evidence is in extended-fixed/ and convergence-target/. Both include manifests, ledgers and frozen recommendations. Target trajectories retain cumulative costs. Targets and source ledger hashes are in ../convergence-targets.json. The report generator checks source hashes, full study matrices, exact paired prefixes, earliest crossings and trajectory accounting. Separate audit JSON files recalculate every model objective and held-out recommendation.

These remain three small BMI applications with short or limited validation data. The targets are informed by earlier development runs, and five seeds provide limited precision. More optimization can improve validation while worsening held-out error. Hydrology cache quality flags, solar allocation assumptions, and copper's unresolved unit multiplier remain as documented in ../README.md. Application partial BO is still untested. No algorithm settings or target thresholds were tuned after results.
