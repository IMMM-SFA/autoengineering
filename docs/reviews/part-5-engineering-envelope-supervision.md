# Source-closed engineering envelope controller check

The actual engineering envelope registration now passed the supervised controller
path on the 24 public development cases. The controller evaluated the unchanged
0.05 A baseline, ran one registered native job, freshly scored its returned current,
reviewed the evidence and froze the selection. The recorded decision is
`accepted_candidate`. This closes the actual source-closed supervision gap in
the [registration checkpoint](part-5-engineering-envelope-registration.md).

Mean baseline power was 0.24974500426467053 W. The selected current was
0.013916199412190763 A, with mean power 0.019410607545283756 W. Its development
reduction exceeds the previously bound 0.012487250213233526 W useful-gain proposal.
Fresh physical checks passed. The trusted producer also checked each selected
case's power against the frozen 1% degradation limit before review. That guard is
recorded separately from the controller's built-in voltage and acceptance rules.

The optimizer-buffer flag remains false. No threshold was relaxed. The native
result records the corner check as independent support, outside the 24 scored
scenarios. Driver snapshots remain cumulative and are not summed as fresh work.

| Work | Original observed quantity |
| --- | ---: |
| Baseline scenario child processes | 24 |
| Native driver child processes | 1 |
| Native inner root model calls, including support and scenario checks | 35 |
| Fresh selected-current scenario child processes | 24 |
| Total outer process reservations and terminal observations | 49 |
| Total root model calls | 83 |

All 49 process observations have verified stops. No physical operation remains
pending. The existing generic campaign reserves 73 outer starts, including 24
unused calibration slots. The frozen producer called only its four declared
operations. Its native inner cap was 53, with 20 SLSQP iterations. The native
process deadline was 20 seconds and each scenario deadline was 10 seconds.
The 1,200-second overall producer limit was logical. CPU/RSS and complete total
cost remain unqualified. These calls are additional to earlier development
profiles and the direct registration test.

All scientific code and the dependency lock were copied into a pinned source
closure before the first dispatch. The controller retained its original source,
environment, process, scenario and selection identities. No host provider,
network fetch, confirmation source, container or remote machine was used.
This qualifies the recorded local macOS ARM64 trusted development path. It does
not establish generated-code isolation or a protected private runtime.

After selection froze, the producer tried to publish one completion record larger
than the batch store's 64 KiB evidence limit. The store refused. The original
failure and all scientific receipts remain intact. A separate metadata-only
finisher published pinned report, evaluation, cost, decision and selection
records, followed by a small completion receipt. It appended the passed terminal
case without another driver or model invocation.

The [archive](../../examples/utility/verification-engineering-envelope-supervised-v1/README.md)
replayed after relocation using the existing core-only installed wheel. The reader
verified the original process receipts, both evaluations, selection, native/support
costs and all-case power limit. After core reader initialization, a filesystem
guard allowed only evidence reads and denied writes, new imports and execution.
All 235 installed payloads matched the pinned wheel. A rehashed replacement
completion that dropped the native work was rejected against the original
terminal event. No model or source execution occurred during replay.

The adjacent archive, registration and documentation regression passed 37 tests
with one optional OpenMDAO skip in the default environment. Ruff passed. The full
default suite was not rerun for this evidence and regression increment.

This is exposed development qualification, not independent confirmation or a
four-family utility comparison. The four original task dossiers remain blocked.
Source admission for hydrology, solar and wind, protected confirmation execution,
the complete matrix/budget freeze and remaining platform checks still require
evidence.
