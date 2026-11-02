# Scientific interoperability

Part 4 is qualified for bounded macOS ARM64 delivery. The package has scalar/daily BMI and scalar OpenMDAO
lifecycle adapters, an experimental serial Optuna policy, a versioned UTC
five-minute sample contract, and local solar/circuit development examples.
The [progress record](reviews/part-4-progress.md) records actual checks and
unresolved gates. These integrations do not establish general optimizer gains,
predictive skill or value from multiple agents.

## Model adapters

`autoengineering.adapters.bmi.BmiAdapter` accepts a trusted callable factory and
an explicit ISO date origin. The factory receives PrepareContext and creates a
fresh model for one attempt. The initial profile requires scalar float64 exchange,
exact declared units, numeric start/current zero, step one, end equal to sample
count and time units `d`. Ports must declare daily semantics and start/end timestamps. Instantaneous
inputs use interval start, and instantaneous state outputs use interval end. The adapter copies exchange values, checks advancement, rejects
unsupported grids and attempts finalization after partial initialization. It
cannot restore a killed model's internal state. A restart is a new attempt.

`autoengineering.adapters.openmdao.OpenMdaoAdapter` accepts a trusted Problem
factory, explicit VariableBinding mappings and a convergence/work inspector.
The complete coupled problem remains intact. Evaluation invokes `run_model`,
never `run_driver`. Initial ports are scalar floats with exact units and shapes.
Finite but nonconverged outputs fail. Native optimization is a separate study
whose inner solves and derivatives must be counted explicitly. Problem cleanup
runs through the common ModelAdapter lifecycle.

Adapters do not install dependencies or register arbitrary worker imports.
Trusted applications supply factories and source closures. Generic BMI or
OpenMDAO support through worker-selected import strings is not provided.

## Search and time semantics

The selected [Optuna policy](optimization.md#experimental-optuna-policy) is
experimental. It replays a disposable in-memory session from committed ledger
results, verifies old proposals and derives its recommendation from successful
feasible observations. The controller persists proposal intent before ask and
exact proposal evidence before dispatch. Missing pending evidence blocks recovery.
Logical experiment/trial IDs are retained with every proposal. Tell intent and
synchronization receipts bind committed results to those IDs. Campaign receipts
reference existing physical attempts. Standalone evaluator dispatches retain
action-ledger accounting. Missing or conflicting committed receipts block resume.
Only an exact pending-result transition may finish interrupted synchronization.
Pruning and framework retries are disabled.

The original daily TimeContract remains unchanged. SubdailyTimeContract version
2.0 admits canonical UTC five-minute instantaneous samples, explicit gaps and
state resets. It does not convert sampled power to interval energy, interpolate
missing values or infer a calendar/timezone conversion. The solar example keeps
the preserved localization rules and records its conversion explicitly.

The [development examples](../examples/interoperability/README.md) include the
Ax/Optuna/Sobol comparison, coupled circuit and verified-cache solar path. Ax
limitations and failures are retained. DAKOTA, Ray and PyMT extensions remain
subject to the [recorded need gates](decisions/part-4-integrations.md).

## Offline evidence reports

The package can verify archived bytes and reconstruct reports without optional
frameworks or scientific execution. The caller supplies a trusted SHA-256 pin
for the strict archive index. Unpinned, missing or changed evidence fails.
Pins and raw retained records are in
[`examples/interoperability/evidence`](../examples/interoperability/evidence/pins.json).
For example, from the repository root:

```sh
pixi run python -m autoengineering.integrations.evidence \
  examples/interoperability/evidence/circuit-v3 \
  --expected-sha256 76bc11734b2fedffa978c34342a9bf616f6db90a5cbac43f758afc11461ed4aa
```

The reader verifies file bounds, paths, sizes and hashes. Circuit reconstruction
also checks retained parity and derivative differences against the recorded
tolerances. It does not authenticate a self-supplied pin or certify scientific
utility. The solar archive is a report snapshot. It omits raw labels, forcing
and the full resumable run bundle pending data redistribution terms. The
original local run remains preserved in outputs. No omitted input is inferred
from a passing report check.

The final wheel passed all three installed examples and seven pinned report
reconstructions outside the checkout. Optional framework imports were blocked
during report and CLI-help checks. See the
[completion audit](reviews/part-4-completion-audit.md) for regression status and
exact receipts. Runtime checks cover macOS ARM64; Linux resolution alone is
not runtime qualification.

Run admitted framework checks with
`pixi run -e interoperability test-interoperability`. The Ax comparison keeps
its separate locked prototype environment.
