# Frozen development acceptance

[task.yaml](task.yaml) fixes the routing comparison before host comparisons. The task is an
engineering fixture. Its tolerances express routing consistency and a development selection rule,
not a validated catchment model or an independent prediction threshold.

Fit from April 1 through December 31, 2019 after a 90-day warm-up. Run the model from January 1,
2019 without resetting state at the 2020 boundary. Compare January 1 through December 31, 2020.
Each family receives 16 fitting calls including its default, followed by the same seeded Sobol
policy. Parameter dimension differs because the supplied kernels differ. Report that difference
rather than calling the parameter searches identical. Every fitting call runs the full fixed
upstream chain's prepared drivers with the chosen routing, never comparison observations.

Select minimum fitting RMSE, breaking exact ties by action identity. Retain gamma only if both
selected families pass finite, aligned, nonnegative, causal, normalized-kernel, and routing/tail
accounting checks, gamma reduces comparison RMSE by at least 0.01 mm/day, KGE falls by no more
than 0.02, and absolute bias grows by no more than 0.05 mm/day. Otherwise retain triangular.
These fixed tolerances avoid selecting roundoff differences and prohibit substantial secondary
metric tradeoffs. They are engineering choices, not hydrologic skill standards.

Defaults are reported separately from calibrated choices. There are 32 fitting calls, four
comparison/default runs, and two causality perturbations: 38 routing executions, within the
40-call campaign reservation. A failed or uncertain call keeps its reservation. The evaluator
uses allowlisted supplied functions and never imports a candidate path. Model code generation,
full-system conservation, trained replacements, and production isolation remain outside admission.

Malformed requests, incompatible identities, and unsupported conclusions fail explicitly. A saved
result before acknowledgment is replayed once logically. An interrupted call without a saved result
is marked uncertain and requires reconciliation. The prototype does not promise exactly-once
physical computation. The child controller's existing persistence semantics remain unchanged.

The original frozen numerical task gives live workers zero resources. A separately recorded live
host envelope, version 2, permits only the user's ChatGPT subscription, no paid API calls. It does
not change scientific criteria or child study identity. Its token ceiling is observed between
calls: Codex has no verified in-flight hard token cap in this pilot. That is an unresolved boundary,
not a passing resource-limit test.
