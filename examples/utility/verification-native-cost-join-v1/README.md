# Native work cost joins

Suite accounting now reads original native reports from science observations and
maps them to exactly their reserved cells. It accepts only the known circuit,
callback and wind schemas. It checks frozen typed jobs, original reservation/job
identity, observed report bytes and original process output. No registered model
or driver is imported for execution. Job metadata is capped at 4 MiB. Invalid
native evidence becomes an accounting blocker, not reported work.

Circuit counters separate outer process starts, inner model-call records, final
shared-problem snapshots and independent scenario counters. Shared driver snapshots
are never summed. Callback and wind entries keep attempted/completed/failed/
unresolved counts and do not stand for inner wake solves or derivative operations.
Failed callback traces retain unknowns for every kind in the frozen specification.
Native process starts are subsets of generic science reservations, not additional
starts to add to the generic count. Missing native observations remain covered by
the generic unknown science records. Complete cost evidence stays false.

The circuit verifier previously checked typed/observed reports but not original
stdout. It now verifies job/completion identity, command, stop and bounded stdout
before projecting counters. The existing callback/wind verifiers retain their
own original-output checks. Corrupted original stdout is rejected in suite reports.

Focused regressions passed 36 with one optional skip. The final integration,
recovery, accounting, wind and documentation subset passed 145 with two optional
skips in 365.37 seconds. Ruff and whitespace checks passed. Source snapshots stayed
fixed. Tests cover scope mapping, repeated offline reads, separate callback kinds,
unknown failed traces, reserved-but-unobserved work and corrupt job/output data.
These are authored drivers and synthetic task values, not scientific model gains.
No full default/Bayes suite or new scientific matrix was run.

A fresh wheel matched 193 core Python files. It was extracted into a fresh venv
with cached base dependencies. Copied authored batches projected 8 circuit rows,
10 callback rows and 9 wind rows. Original checkout and original case roots were
denied, with six tested denial controls. Sockets and subprocesses were denied.
The reader had no captured model implementation or optional PyWake, TOPFARM,
OpenMDAO, Anthropic, Torch or BoTorch packages. Original absolute paths remain in
metadata, but were not read. This verifies relocated cost projection, not a fresh
dependency solve, installed model execution or independent provenance audit.
Wheel, reader/guard text, copied batches and their source indexes are preserved.
The reader/guard text is for inspection, not automatic archive execution.

The original exposed four-family rehearsal was also read without process/network
access. It reconstructed 28 assigned cells and 108 native cost rows, with no
blockers, no confirmation receipts and the same journal head. The saved projection
adds no model/scorer/provider work or independent evidence. Original study bytes
remain separate from this new projection and must not be rewritten.

Independent tasks/data, private scorer and actual host/platform qualification,
full solver/training/resource/provider/human-effort closure and the full Part 5
remain open. No real/private confirmation data or provider was accessed.
