# Revised engineering conventional profile

The supplied SLSQP recipe now completes on the revised public engineering task.
It selects 0.013916199412190763 A. Fresh checks on the same 24 public development
cases give mean power 0.019410607545283756 W, a development reduction of
0.23033439671938677 W from the fixed baseline. All original scientific checks pass.
This is conventional development evidence, not an agent comparison or independent
confirmation.

The recipe uses the declared load envelope's controlling corner: minimum ground,
minimum R1 and maximum R2. The ideal passive circuit's monotone voltage/current
relations support that reduction. This support case and recipe are to be available
to every future route. Source current remains within [0.01, 0.1] A. The physical
node-2 requirement remains 0.62 V. Before execution, the optimizer target was set
to 0.62001 V to provide a numerical buffer. No physical limit, useful-gain margin,
load bound or public development case was changed after looking at results.

The fresh corner voltage was 0.6200099999935591 V. It passes the original physical
requirement but falls about 6.4e-12 V below the exact buffered optimizer target.
The helper's stricter `feasible` flag is retained as false. Driver success and the
original final physical checks are reported separately, following the rule frozen
before the first profile. No tolerance was changed to convert that flag to true.

Two profiling errors preceded completion. The original observer required final
circuit convergence after an OpenMDAO pre-optimization pass that had not executed
the circuit. The second observer accepted native passes but rejected the load
adapter's documented internal ground-only model projection. Both runs stopped,
returned cleanup and left no pending physical operation. Their receipts, original
statuses and charges remain unchanged. Failed-case terminal events were appended
using the original manifest and environment. Corrected profiles had explicit new
source identities and reduced remaining allowances.

| Profile | Charged native model invocations | Passes with observed circuit work | Outcome |
| --- | ---: | ---: | --- |
| First observer | 1 | 0 | Failed observer check |
| Corrected pass observer | 10 | 9 | Failed projection check |
| Corrected exact model views | 35 | 34 | Completed development profile |
| Total | 46 | 43 | Within original 64-invocation cap |

All three native driver invocations and 28 constructed OpenMDAO problems are
retained in accounting. All 28 cleanup calls returned. The three passes without
circuit activity remain charged. OpenMDAO's atomic nonlinear-group relevance
warning was observed in each profile. It explains why a root model pass is not
necessarily a fresh circuit solve.

[The new example helper](../../examples/utility/engineering_native_accounting.py)
uses cumulative component/linearization deltas to distinguish fresh work from
retained circuit diagnostics. It never judges design eligibility. A pass without
circuit work contributes zero fresh nonlinear iterations even if the stored
snapshot retains earlier iterations. Counter resets and malformed values refuse.
This does not reinterpret legacy core records or migrate their accounting.

For the completed profile, final counters over all 26 problem instances record
7,927 component calls, 2,435 component linearizations and 480 nonlinear iterations.
Of those totals, 77 component calls and 35 linearizations occurred between the
recorded nonlinear passes. They remain included in the final per-problem totals.
The failed profiles lack complete final counter snapshots, so combined inner-work
totals remain unknown. CPU, peak RSS and total first-use cost also remain unknown.
Logical reservations do not establish OS-enforced deadlines.

[Saved evidence](../../examples/utility/verification-engineering-v3-conventional-v1/README.md)
contains all three batches, exact recipes/producers, the unchanged baseline receipt
and post-run joins. The core-only installed reader reproduced the result outside
the checkout using relocated evidence with models/network/processes denied. It
rejected a report that dropped the 11 earlier charges. No wheel build or dependency
installation was repeated.

The initial regression had 49 passes, ten process-supervision failures caused by
sandbox denial of `ps`, and nine optional skips. No owned test workers remained.
Only those ten tests were rerun with process inspection permitted; all passed.
The original failure record remains. This is 59 passing unique cases and nine
skips across the two executions, not a clean original suite run.

No private source, confirmation seed/rows, container or agent host was used. The
older failed private grant remains untouched. The full route matrix, global
budgets, protected runtime, task admission and independent four-family study are
still incomplete. The development reduction does not establish scientific utility
for agents or role removal.
