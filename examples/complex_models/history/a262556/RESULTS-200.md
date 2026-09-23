# Larger BMI models: 96-call checkpoints and 200-call targets

Completed 45 fixed studies (4320 calls) and 75 target studies (4622 calls). Verified 27 historical fixed prefixes and 45 historical target prefixes.

Two new seven-parameter chains extend hydrology and solar modeling. The existing three models, datasets, splits and accuracy targets stay unchanged. The new models reuse existing datasets; they add model complexity, not independent data or new domains.

## Sensor QA correction

All 639 cached module-temperature readings equal 3276.7 C and are unusable. Measured-temperature RMSE/ranking and earlier claims of observed intermediate temperature truth are withdrawn. Frozen raw diagnostics remain for provenance, but are not valid accuracy evidence. The AC-power objectives use simulated module temperature, plausible ambient-temperature and irradiance forcing, and measured AC power. No rows, splits, targets or primary optimization results were changed. Sensor range screening does not certify their accuracy.

## Fixed-budget comparison

Median held-out RMSE across seeds 0-2. Each row uses checkpoints of the same search trajectory; these are paired observations, not independent replications. Only validation error selects recommendations. Lower is better. Hydrology uses mm/day, solar uses kW, and copper retains the source's unresolved native unit multiplier.

| Model | Method | Test at 12 | Test at 24 | Test at 48 | Test at 96 | Validation at 96 | Study seconds at 96 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hydro | random | 2.8250 | 2.8250 | 2.8141 | 2.8141 | 2.4865 | 6.92 |
| hydro | sobol | 2.8271 | 2.8093 | 2.8093 | 2.8179 | 2.2707 | 6.72 |
| hydro | bo | 2.8839 | 2.8839 | 2.8839 | 2.8839 | 2.0660 | 18.43 |
| solar | random | 116.8577 | 123.3546 | 122.8638 | 122.8638 | 175.0851 | 6.37 |
| solar | sobol | 118.9642 | 119.6787 | 120.2928 | 120.2928 | 175.1134 | 6.56 |
| solar | bo | 121.9417 | 121.9401 | 122.0450 | 122.0261 | 175.0775 | 92.18 |
| copper | random | 0.2489 | 0.2479 | 0.2479 | 0.2479 | 0.1960 | 6.54 |
| copper | sobol | 0.2477 | 0.2477 | 0.2477 | 0.2479 | 0.1960 | 5.82 |
| copper | bo | 0.2479 | 0.2479 | 0.2479 | 0.2479 | 0.1960 | 37.93 |
| hymod | random | 2.8613 | 2.7309 | 2.7309 | 2.6758 | 1.4167 | 7.69 |
| hymod | sobol | 2.6846 | 2.6846 | 2.5527 | 2.5505 | 1.3248 | 7.39 |
| hymod | bo | 2.7735 | 2.9156 | 2.7403 | 2.5731 | 1.1238 | 24.67 |
| solar_diode | random | 135.6157 | 128.7039 | 128.7039 | 128.4311 | 174.4857 | 24.61 |
| solar_diode | sobol | 124.5879 | 123.8332 | 121.3327 | 124.6517 | 174.2282 | 21.27 |
| solar_diode | bo | 124.5879 | 124.5879 | 122.9228 | 124.9850 | 173.8745 | 33.93 |

Median validation RMSE across the same seeds:

| Model | Method | Validation at 12 | Validation at 24 | Validation at 48 | Validation at 96 |
| --- | --- | ---: | ---: | ---: | ---: |
| hydro | random | 2.7876 | 2.7876 | 2.4972 | 2.4865 |
| hydro | sobol | 3.4011 | 2.5899 | 2.5899 | 2.2707 |
| hydro | bo | 2.0660 | 2.0660 | 2.0660 | 2.0660 |
| solar | random | 175.6803 | 175.4546 | 175.0851 | 175.0851 |
| solar | sobol | 176.1332 | 175.2584 | 175.1134 | 175.1134 |
| solar | bo | 175.0776 | 175.0776 | 175.0775 | 175.0775 |
| copper | random | 0.1963 | 0.1960 | 0.1960 | 0.1960 |
| copper | sobol | 0.1960 | 0.1960 | 0.1960 | 0.1960 |
| copper | bo | 0.1960 | 0.1960 | 0.1960 | 0.1960 |
| hymod | random | 1.6944 | 1.5993 | 1.4582 | 1.4167 |
| hymod | sobol | 1.6417 | 1.6417 | 1.3656 | 1.3248 |
| hymod | bo | 1.5052 | 1.3678 | 1.2994 | 1.1238 |
| solar_diode | random | 176.1847 | 175.3630 | 175.3630 | 174.4857 |
| solar_diode | sobol | 176.3502 | 175.1064 | 174.5390 | 174.2282 |
| solar_diode | bo | 176.3502 | 175.1064 | 173.9397 | 173.8745 |

## Calls to the frozen validation target

Five separate seeds (3-7), stopping immediately at the target or after 200 attempts. Existing targets are unchanged. Each new target is 1.05 times the lowest validation RMSE in its fixed matrix, frozen before these five seeds. This is a development quality target, not global convergence.

| Model | Target | Method | Reached | Calls by seed 3-7 | Median successful calls | Mean calls consumed | Median study seconds | Median test RMSE |
| --- | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: |
| hydro | 2.1693 | random | 4/5 | 161, 199, 168, >200, 89 | 164.5 | 163.4 | 13.927 | 2.8513 |
| hydro | 2.1693 | sobol | 1/5 | 133, >200, >200, >200, >200 | 133 | 186.6 | 16.934 | 2.8218 |
| hydro | 2.1693 | bo | 5/5 | 6, 6, 7, 6, 7 | 6 | 6.4 | 0.517 | 2.8839 |
| solar | 183.8314 | random | 5/5 | 5, 2, 11, 3, 2 | 3 | 4.6 | 0.217 | 120.6910 |
| solar | 183.8314 | sobol | 5/5 | 3, 1, 4, 2, 4 | 3 | 2.8 | 0.249 | 137.8004 |
| solar | 183.8314 | bo | 5/5 | 3, 1, 4, 2, 4 | 3 | 2.8 | 0.234 | 137.8004 |
| copper | 0.2058 | random | 5/5 | 1, 8, 3, 7, 2 | 3 | 4.2 | 0.184 | 0.2513 |
| copper | 0.2058 | sobol | 5/5 | 4, 1, 5, 1, 12 | 4 | 4.6 | 0.235 | 0.2492 |
| copper | 0.2058 | bo | 5/5 | 4, 1, 5, 1, 7 | 4 | 3.6 | 0.246 | 0.2492 |
| hymod | 1.1383 | random | 0/5 | >200, >200, >200, >200, >200 | NA | 200.0 | 30.197 | 2.3870 |
| hymod | 1.1383 | sobol | 0/5 | >200, >200, >200, >200, >200 | NA | 200.0 | 24.925 | 2.4586 |
| hymod | 1.1383 | bo | 4/5 | 158, 62, 146, 67, >200 | 106.5 | 126.6 | 58.948 | 2.6660 |
| solar_diode | 182.1066 | random | 5/5 | 3, 5, 8, 3, 13 | 5 | 6.4 | 1.144 | 137.1321 |
| solar_diode | 182.1066 | sobol | 5/5 | 13, 9, 1, 5, 4 | 5 | 6.4 | 1.175 | 114.9054 |
| solar_diode | 182.1066 | bo | 5/5 | 10, 10, 1, 5, 4 | 5 | 6.0 | 1.095 | 115.8841 |

A >200 value is censored, not convergence at 200. Successful-only medians exclude capped or terminated runs. Mean calls consumed is a restricted computational cost and cannot alone rank methods with unequal success rates. Missing scores are not silently dropped. Individual JSON records retain actual termination reasons.

## Timing, adaptive actions and failures

Study time includes optimization and durable bookkeeping. Model time covers BMI evaluation, including model initialization and any copper training fit. Imports, input loading, backend construction and held-out scoring are outside the study timer. Runs are sequential with one Torch CPU thread. These are single-machine measurements; model-dependent cost and bookkeeping matter alongside evaluation counts.

| Experiment | Model | Method | Median model seconds | Median optimizer/controller seconds | Adaptive BO actions | Fallback actions | Failed attempts |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| fixed | hydro | random | 1.531 | 5.390 | 0 | 0 | 0 |
| fixed | hydro | sobol | 1.534 | 5.212 | 0 | 0 | 0 |
| fixed | hydro | bo | 1.587 | 16.845 | 28 | 248 | 0 |
| fixed | solar | random | 1.215 | 5.160 | 0 | 0 | 0 |
| fixed | solar | sobol | 1.280 | 5.282 | 0 | 0 | 0 |
| fixed | solar | bo | 1.315 | 90.806 | 145 | 131 | 0 |
| fixed | copper | random | 0.814 | 5.731 | 0 | 0 | 0 |
| fixed | copper | sobol | 0.764 | 5.065 | 0 | 0 | 0 |
| fixed | copper | bo | 0.930 | 36.998 | 136 | 140 | 0 |
| fixed | hymod | random | 1.660 | 6.031 | 0 | 0 | 0 |
| fixed | hymod | sobol | 1.615 | 5.730 | 0 | 0 | 0 |
| fixed | hymod | bo | 1.649 | 23.092 | 264 | 0 | 0 |
| fixed | solar_diode | random | 18.298 | 5.969 | 0 | 0 | 0 |
| fixed | solar_diode | sobol | 15.342 | 5.923 | 0 | 0 | 0 |
| fixed | solar_diode | bo | 15.025 | 18.971 | 264 | 0 | 0 |
| target | hydro | random | 2.710 | 11.217 | 0 | 0 | 0 |
| target | hydro | sobol | 3.096 | 13.839 | 0 | 0 | 0 |
| target | hydro | bo | 0.101 | 0.416 | 12 | 0 | 0 |
| target | solar | random | 0.044 | 0.173 | 0 | 0 | 0 |
| target | solar | sobol | 0.048 | 0.202 | 0 | 0 | 0 |
| target | solar | bo | 0.048 | 0.187 | 0 | 0 | 0 |
| target | copper | random | 0.023 | 0.161 | 0 | 0 | 0 |
| target | copper | sobol | 0.034 | 0.201 | 0 | 0 | 0 |
| target | copper | bo | 0.034 | 0.211 | 4 | 0 | 0 |
| target | hymod | random | 5.554 | 24.609 | 0 | 0 | 0 |
| target | hymod | sobol | 4.287 | 20.638 | 0 | 0 | 0 |
| target | hymod | bo | 2.906 | 55.763 | 593 | 0 | 0 |
| target | solar_diode | random | 0.849 | 0.295 | 0 | 0 | 0 |
| target | solar_diode | sobol | 0.895 | 0.280 | 0 | 0 | 0 |
| target | solar_diode | bo | 0.820 | 0.275 | 4 | 0 | 0 |

For an expensive model, fewer calls can reduce time when saved evaluation cost exceeds additional optimizer overhead. This is conditional on unchanged search behavior and is not a measured speedup on another model. A capped baseline provides a lower bound on calls to target, not an exact eventual convergence time.

## Evidence and limitations

The audit checks every successful objective and each checkpoint/final recommendation. Existing models use vector kernels as a reference. Solar diode uses an independent vector Lambert-W solver against the scalar Brent BMI implementation. HYMOD is rerun through BMI with a daily water-balance check. Audit JSON files retain counts and hashes.

HYMOD states are conditional on the chosen initialization; slow reservoirs are not guaranteed to equilibrate during the inherited warmup. The solar module is a representative CEC snapshot, not the identified site hardware. Its parameters need not be identifiable from aggregate AC measurements. Model complexity does not establish physical realism or predictive skill. Validation optimization and held-out improvement remain distinct. Partial-observation BO is not evaluated by this suite.

See ../PROTOCOL.md for sources, bounds, targets and timing definitions. workflow/results.json retains actual BMI component-swap diagnostics. fixed/ and target/ retain ledgers, manifests, timings and frozen recommendations. Each retains the exact earlier workflow.py and README.md under source/. The later diagnostic fix deep-copies component metadata before swapping. Initial incorrect swap diagnostics are preserved in workflow-initial/. Intermediate diagnostics before sensor QA are in workflow-before-temperature-qa/; corrected diagnostics are in workflow/.
