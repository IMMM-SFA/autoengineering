# Coupled callback development evidence

The application-owned callback now joins the sealed generated source, selected
model and coupled-load scoring kernel through the existing confirmation service.
This control used an authored selected-state fixture at 0.05 A. It did not select
or optimize that design, admit a real task or establish independent utility.

The immutable [request](public/request.json) reserved one scoring callback, 24
inner model starts, 2,400 nonlinear iterations and 60 seconds of active time.
Active time is an allocation, with no qualified OS deadline or aggregate RSS
boundary. The source was generated and sealed before selection. One source-read
intent preceded private access. Every native case had its own durable start
intent. The control used OpenMDAO 3.41.0 on the local macOS host.

All 24 solves passed the voltage, convergence, residual and passive-power checks.
[Recorded work](public/result.json) totals 395 nonlinear iterations, 6,440 component
calls and 1,975 component `_linearize` calls, including Newton linearization.
These counters do not measure FLOPs. One scoring callback and all 24 reserved
native starts remain charged. Earlier development runs retain their own charges.

The saved service receipt replayed with source reads and scorer calls denied.
The [guarded reader](cold-reader.py.txt) reconstructs source, model, outcome,
scorer, grant, receipt and work identities from public evidence. It verifies
per-case work sums without reading private input rows or per-case model values.
The exported service receipt contains the public aggregate score. Source values,
seed and individual model responses remain only in the private local output.

Run the reader from the worktree root:

```sh
.pixi/envs/default/bin/python -B \
  examples/utility/verification-engineering-load-callback-v1/cold-reader.py.txt \
  examples/utility/verification-engineering-load-callback-v1/public .
```

[Executed source snapshots](executed-source) preserve the exact source used by the
native control. The current test file adds a publication-loss test after that
run. Callback and kernel bytes used by the native run are unchanged. The control
script refuses changed request pins or an existing execution intent.

Full cost projection, protected runtime, task owner margins, exposure history,
installed/Linux qualification and actual independent host evidence remain open.
The original grid proposal and frozen core/guest sources remain unchanged.
Use [summary.json](summary.json) for test counts and verification results.
