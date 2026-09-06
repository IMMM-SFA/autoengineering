# Open model chain comparison

HOPP design scenario, not observed accuracy; one-year resource simulation

Objective: negative energy revenue (USD) (minimize).
Selected: cbc_buffered_soc.

| Trial | Objective | Seconds | Status |
| --- | ---: | ---: | --- |
| baseline | -1.06197e+07 | 4.667 | evaluated |
| cbc_dispatch | -1.08493e+07 | 20.694 | infeasible |
| cbc_buffered_soc | -1.08159e+07 | 21.326 | evaluated |

Candidate selection uses the declared selection objective only.
A zero gain or failed candidate remains part of the result.

See manifest.json, trials.json, summary.json and the NPZ arrays for evidence.
