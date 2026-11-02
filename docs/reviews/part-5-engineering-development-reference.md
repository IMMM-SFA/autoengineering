# Revised engineering development definition and reference

The [engineering-v3 proposal](../../examples/utility/proposals/engineering-v3/README.md)
now has a measured public development reference. At the fixed 0.05 A baseline,
mean source power is 0.24974500426467053 W. The previously proposed 5% rule gives
an absolute useful-gain threshold of 0.012487250213233526 W for this revised
question. This is a development reference, not a measured improvement or an
admitted confirmation task.

The revised question retains source-current design, the intact OpenMDAO circuit,
mean modeled power and a 0.62 V absolute node-2 requirement. It uses the existing
public 24-case fixture from `test_utility_engineering_load_robust_native.scenarios`,
with its fixed seed 41. Its declared operating support is ground voltage
[-0.02, 0.02] V, R1 [90, 110] ohm and R2 [9000, 11000] ohm. Future uniform draws
include lower bounds and exclude upper bounds. Preparation checked that none of
those 24 inputs equals a case in the older proposed reserve
grid. The older v2 proposal, dossiers and failed private attempt remain intact.
The new reference cannot be substituted into them.

The development inputs, baseline, source closure, physical rules and parity
tolerances were frozen before the run. The conventional source-current domain
remains [0.01, 0.1] A. All cases require convergence, constitutive residual at most
1e-10 A, at most 100 solver iterations, positive source power and node voltage at
least 0.62 V. A 1% case-power degradation rule is proposed for later comparison.
No candidate design or native optimization was run in this increment.

Each of 24 durable physical reservations executed one coupled baseline solve and
one independently implemented scalar reference solve. The scalar reference uses
Kirchhoff/Ohm relations and the same ideal diode constants. With v measured above
ground, the equation is:

```text
I = v/R1 + (1 + R2/R1) Is expm1(v/Vt)
Is = 1e-15 A, Vt = 0.025875 V
```

Monotone bisection on [0, I R1] was capped at 200 steps. These reference solves
are additional numerical work, not independent empirical observations. All 24
coupled results passed physical checks. Maximum voltage difference was
3.022693206844451e-11 V against a frozen 1e-7 V tolerance. Maximum power difference
was 4.471423231677818e-14 W against 1e-8 W. All 24 cleanup calls returned.

The run recorded 382 nonlinear solver iterations, 6,232 component calls and 1,910
component linearizations. The 24 scalar references used 1,176 bisection steps.
Linearizations include Newton work and are not FLOPs. Initialization and per-case
operation durations are retained separately from their nested lifecycle durations.
CPU and peak RSS remain unknown. Ten-second case reservations and the batch's
240-second logical budget are not OS-enforced deadlines. No host, container,
network or private-source operation was invoked by the scientific loop.
The recorded intervals exclude process startup and final archive publication,
so complete first-use cost is not established.

The actual environment was native macOS ARM64 with Python 3.12.16 and OpenMDAO
3.41.0. This does not qualify Linux or the changed daemon. The independent equation
checks this supplied model's implementation, not real-world circuit accuracy.
The small instructional circuit supports only the stated modeled design question.

`development-reference.json` binds the exact model, input and execution-receipt
identities. `gain-reference.json` additionally names the revised proposal digest.
A guarded core reader reconstructed 24 successful observations, physical/parity
checks and the threshold without executing either solver. Relocated replay
passed; binding it to the old v2 proposal was rejected. The initial reader used
an incorrect projection field name and was corrected without model reruns.
The existing installed core wheel also passed outside the checkout with relocated
evidence and model imports denied. All 235 installed package payloads matched
that wheel. No rebuild or installation was needed. The focused regression passed
52 tests and skipped 16 optional OpenMDAO cases in the base environment. The actual
24-case baseline used the interoperability environment separately. Documentation
checks and lint passed.

The future 24-case confirmation sampler is declared prospectively under the
existing one-use generated-source policy. No seed or confirmation rows were
generated. The complete route matrix, conventional recipe, numeric study budgets,
analysis/dependence rules, current protected runtime and final task admission
remain open. All four original dossiers still say `blocked_draft`.
