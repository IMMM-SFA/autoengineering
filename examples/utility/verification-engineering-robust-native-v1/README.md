# Native design without a combined load corner

`examples.utility.engineering_load_robust_native:execute` adds a separate native
recipe for up to 24 supplied circuit load cases. The existing combined-corner
recipe and its rejection rules are unchanged. No core schema or runtime changed.

For each case, let `v = minimum_voltage - ground`. Kirchhoff and Ohm laws give
`I_required = v/R1 + (1 + R2/R1) * Is * expm1(v/Vt)` for the fixed diode, with
`Is=1e-15 A` and `Vt=0.025875 V`. This relation strictly increases with voltage
for positive resistances. The supplied case with the largest required current
therefore controls the common absolute voltage constraint, even if no combined
worst corner exists. Source power strictly increases with positive current in
every case. Minimizing the controlling case's power has the same current
minimizer as the uniformly weighted mean power. This is an exact reduction for
this fixed scalar-current model, not a general circuit or nonlinear-program rule.

SLSQP still solves the intact coupled OpenMDAO model using its native derivatives.
The selected threshold case is identified before model construction. The recipe
checks the actual diode options before optimization and refuses physics drift.
It reserves room for one fresh solve of every supplied case, enforces the inner
solve cap and cleans up on failure. All cases get their original order and inputs.
Final feasibility retains finite outputs, convergence, `1e-10 A` residual,
100-iteration, absolute voltage and passive-power checks. No criterion was relaxed.
The supervised native result remains a proposal. Authoritative scenario evaluation
and selection acceptance remain separate.

The authored regression used 24 public synthetic cases with no combined corner.
The supervised native job returned `0.022793262535515797 A`, using 35 inner calls
within the 40-call cap. These comprise driver calls plus 24 fresh scenario solves.
A separate scientific evaluation launched 24 freshly reserved scenario processes.
All 24 passed the unchanged checks at the authored `0.66 V` requirement. Mean
source power was `0.05198172873029417 W`. The batch had 25 physical reservations:
one native process and 24 independent final-check processes. Inner calls are
nested work, not additional process starts. No baseline gain is claimed.

Native costs retain the last driver snapshot separately from independent scenario
counters. The reported 280 driver derivative calls count component `_linearize`
invocations, including Newton work. They are not 280 optimizer Jacobians or FLOPs.
The original framework-specific counter limits remain. Tests ran OpenMDAO 3.41.0.

[Summary](summary.json), [public evidence](public-evidence/native-report.json),
[specification](public-evidence/native-spec.json) and
[scientific evaluation](public-evidence/scientific-evaluation.json) retain the
source/job/process/parent commitments. Native and scenario recovery returned the
original results with launch functions forbidden and no new reservations.
The [manifest](evidence-manifest.json) binds every copied evidence file.

An isolated process outside the checkout used the existing installed core-only
225-source wheel to verify the relocated native report and parent batch. Every
installed Python payload matched current core source. Model imports were blocked
from startup. After metadata initialization, guards denied processes, sockets,
clocks, writes, new imports and outside evidence reads. The reader reconstructed
native costs, 120 scenario cost records and the arithmetic mean from saved scores.
It used base dependencies with no OpenMDAO or example import. This qualifies this
offline receipt path. The new model recipe itself has not been installed or run
on Linux. It is not part of the frozen 316-source v6 inference image.

Validation passed 22 optional-environment tests, including the unchanged corner
recipe, and 33 base/documentation tests with eight expected optional-runtime skips.
The six OpenMDAO warnings describe its treatment of coupled nonlinear groups as
atomic during relevance analysis. Tests cover missing/invalid cases, changed diode
physics, exhausted budgets, both interior and bound optima, neighboring feasibility,
all-case checks, mean power and exact saved recovery.

The first test fixture accidentally asked for a neighbor below the valid current
lower bound. Interior-optimum and lower-bound cases now have separate checks.
The first supervised fixture retained a two-case batch cap and correctly refused
before native launch. A fresh fixture declared a sufficient 48-start batch cap,
while retaining the same 40-inner-call cap. Those initial results remain saved.

No proposed final grid or generated private confirmation source was opened.
These are exposed authored development cases, not independent confirmation. The
recipe is application supplied through `NativeDriverSpec`; final task admission,
protected scoring and a real comparative route study remain open. The separate
guest-container accounting register is unchanged because these native regression
fixtures are outside its scope.

The strengthened reader also matches every saved scenario score to its original
verified parent receipt, job, configuration and action. A separate copy with
consistently forged scenario and aggregate metrics was rejected without executing
models. The initial reader and the strengthened reader are both preserved.

Ruff, formatting, whitespace and final documentation checks passed. The original
evidence hashes and existing v6 code alignment verified. See
[final checks](final-checks.json) and the
[source inventory](../source-inventory-engineering-robust-native-v1.json). The full
default suite was not rerun for this separate example/test increment.
