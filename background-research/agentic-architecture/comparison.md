# Architecture comparison

The CLI and standalone deterministic routes produced identical candidate identities, parameter
choices, scientific checks, metric values, decisions, and counts in all six runs. Both selected
supplied gamma routing under the frozen development rule. The
[raw run table](comparison/runs.csv), [parity record](comparison/parity.json), and
[representative result](comparison/cli-0/evaluation.json) contain the measurements.

| Selected family | Fitting RMSE | 2020 RMSE | 2020 NSE | 2020 KGE | 2020 bias |
| --- | ---: | ---: | ---: | ---: | ---: |
| Triangular | 2.090231 | 2.811270 | 0.428595 | 0.390455 | -0.648695 |
| Gamma | 2.172884 | 2.593293 | 0.513770 | 0.531075 | -0.024537 |

Flow errors and bias use mm/day. Gamma reduced comparison RMSE by 0.217977 mm/day. Its selected
parameters were the supplied default. Triangular's fitted choice improved its default comparison
RMSE from 3.126358 to 2.811270. These are development results after prior exposure to both years,
not independent predictive confirmation. No whole-catchment conservation claim follows.

CLI elapsed times were 8.885, 9.789, and 10.470 seconds. Direct standalone times were 5.591,
5.386, and 5.319 seconds. Each included 38 routing executions and five tool calls. The difference
includes interpreter and import startup from repeated CLI calls. Runs were ordered, unpaired in
time, and local. Scientific time was not separately instrumented, so this does not establish the
standalone architecture's general speed advantage. Numerical workers were deterministic stubs
and incurred no LLM tokens or charges.

The [real recovery run](reference-recovery/recovery.json) stopped after saving evaluation but
before acknowledgment. Restart and a duplicate request returned the same decision without a new
reservation or physical evaluation. Its result matches the six clean runs. The earlier
`runs/reference` attempt failed on a noncanonical default action ID after one fitting call. That
attempt is preserved, its call counted, and the backend adapter was repaired before comparable
runs. It is not resumed under the changed source.

The [live record](live/summary.json) contains one complete fresh CLI campaign, with investigator,
implementer, and reviewer outputs in [handoffs.json](live/handoffs.json). Codex used ChatGPT
subscription authentication, with API-key variables removed and user provider configuration
ignored. Every worker ran inside the repository-denial sandbox. The worker described the supplied
adapter rather than writing executable code. The parent brokered the same five tools. This tests
a bounded role contract, not autonomous model implementation.

The three calls reported 18,494, 18,548, and 19,086 input-plus-output tokens. Total usage was
56,128, exceeding the 50,000 observed-token stop threshold by 6,128 on the final call. The runner
stopped before a fourth call. No paid API calls were made. Subscription cost attribution is
unknown. There were no worker tool events in these transcripts. A live standalone run, five
remaining repetitions, and a second host were not attempted after the stop.

The implementation initially reserved a fresh live campaign plus five saved-result replays to
stay inside the numerical budget. Replays would not count as clean fresh scientific runs. None
of those five live replays occurred. This deviation from six planned clean live runs is retained
explicitly. Mandatory resource/cancellation/portability checks prevent a settled choice.

Numerical execution accounting is 3 preflight baseline calls, 1 failed initial fitting call,
38 reference/recovery calls, 228 deterministic comparison calls, and 38 fresh live calls: 308.
Contract tests use synthetic arrays or fixture evaluators. No benchmark matrices were rerun.
Twelve executions remain under the investigation ceiling, insufficient for another full campaign.

The live runner used the installed Codex default model without recording its resolved model ID.
JSONL receipts expose usage and final messages but not the full model-visible system context.
Command-level user prompts were reconstructed from the exact runner expression and saved feedback
in `live/reconstructed-user-prompts.json`; they were not captured at dispatch. These provenance
limits prevent a claim of a fully auditable model invocation. Part 2 must save prompts before
dispatch and record the resolved model/provider identity.
