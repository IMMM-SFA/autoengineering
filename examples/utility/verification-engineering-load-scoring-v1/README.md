# Coupled load-scoring kernel

One fixed 0.05 A design completed 24 coupled OpenMDAO solves on previously exposed
control inputs. Every case passed the required absolute node-voltage, convergence,
constitutive-residual and nonnegative source-power checks. The run recorded 390
nonlinear iterations, 6,360 component calls and 1,950 component-linearization calls.
No fitting, design selection, agent/provider call or dependency installation ran.
This is a standalone development evaluation, not independent confirmation or an
activated private scorer.

The new kernel requires exactly 24 uniformly weighted cases, a frozen model digest,
its own code digest, a declared voltage requirement and an empty private output
scope. It validates the entire input envelope before model creation. Every attempted
solve gets an intent first. Each fresh adapter preserves the intact coupled solver
and prescribed initialization, and lifecycle cleanup remains authoritative. The
fixed factory caps Newton iteration at 100 for each case. No retry or additional
case can obtain a new allowance from the consumed output scope.

Mean source power uses current times node-one voltage relative to ground. Every
case must be feasible. A physical failure vetoes the aggregate without a penalty
objective. A failed model stops execution and retains the attempted start, unknown
last-attempt inner work and separate counters for completed cases. The kernel
selects no design and opens no private source itself. The existing source-binding
service must supply authorized inputs. A complete protected callback and real task
registration remain separate work.

The existing interoperability environment used OpenMDAO 3.41.0, NumPy 2.5.4,
SciPy 1.18.1 and NetworkX 3.7. The request captured versions and source hashes before
execution. Its cap was 24 starts and 100 solver iterations per case. The actual
model factory and counters are tied to that framework profile. Neither the trusted
process nor this iteration cap establishes OS deadlines, aggregate RSS limits or
a Linux/installed-package qualification.

The executed kernel initially described its derivative counter as explicit
`compute_totals` requests. Inspection showed that the pinned model increments it
for component `_linearize` invocations, including Newton linearization. The numeric
counter was correct. `counter-scope-correction.json` corrects only the interpretation
and binds the original private completion and factory source. The executed source
snapshot and raw private result remain unchanged. The current kernel differs only
in that description, as the cold checker verifies. No numerical rerun was performed.

Fourteen authored kernel tests cover exact aggregation, all-case physical veto,
nonfinite output, failed model/counter handling, preflight refusals, permanent
consumption and unknown inner work. The related regression passed 44 tests. A
fresh standard-library-only guarded reader verifies metadata, recorded checks,
per-case work sums, source snapshots and the scope correction without NumPy,
OpenMDAO, SciPy, private sources, private model outputs, new imports, processes,
network, writes or clocks after initialization. It does not recompute physics.

Only metadata, check verdicts, work counts and cryptographic commitments are
archived. The operating inputs and numerical outputs remain in local private
control scopes. The original source-binding fixture's constant score is unchanged.
These development cases must not become independent confirmation data. No real task,
useful-gain margin, protected scorer, full cost regime or Part 5 gate is admitted
by this result. The full matched comparison remains unexecuted.
