# Part 4 integration decisions

Status: investigation in progress, 2026-10-27. No external optimizer selected.
The source inventory is in
[the starting inventory](../reviews/part-4/starting-source-inventory.json).
The [progress record](../reviews/part-4-progress.md) separates implementation
from qualification. All six systems remain subject to the parent plan's gates.

## Ownership

Autoengineering owns action identity, physical reservations, result commits,
recovery and scientific acceptance. An optimizer may suggest and consume a
projection of committed results. BMI owns numerical stepping inside one attempt.
OpenMDAO owns the internal coupled solve and derivatives inside one attempt.
Neither a framework trial nor a checkpoint authorizes a physical model start.
No integration may retry without a new charged attempt.

## Dispositions and capability review

| System | Current disposition | Need and candidate interface | Burden and revisit condition |
| --- | --- | --- | --- |
| BMI | Adopted for implementation, qualification open | Reuse scalar daily local models through trusted factories and the existing adapter lifecycle. BMI control, variable, grid and time methods validate exchange metadata. | Removes a bespoke loop for each model. Requires explicit interval semantics and date origin. Qualify local parity and an independent implementation before advertising support. |
| OpenMDAO | Adopted for implementation, qualification open | Preserve a complete coupled engineering problem behind a trusted Problem factory, using setup, set_val, run_model, get_val and cleanup. | Keeps nonlinear solvers and derivatives inside their framework. Requires a real engineering model and explicit inner-call accounting before comparison. |
| Ax | Deferred pending comparison | Public client API for serial suggestions and observed outcomes. Do not use internal Experiment/Trial classes as a compatibility promise. | Snapshot/API/version and Torch footprint must pass prototype gates. Revisit after resolved environment and fault tests. |
| Optuna | Deferred pending comparison | Public study ask/tell API, explicit distributions and coarse failed-trial projection. | Durable sampler reconstruction is unresolved. Database persistence alone does not prove sampler recovery. Revisit with identical comparison cases and crash tests. |
| DAKOTA | Deferred, need gate unmet | External simulation interface can request sensitivity/UQ samples. Broker must own evaluation and response commits. | No current model decision requires a DAKOTA-specific method. Revisit when a named uncertain-input decision and estimator cannot be addressed adequately by existing sampling tools. |
| Ray Tune | Deferred, need gate unmet | Trial scheduling offers resource management, but overlaps controller ownership. Ray Core is a separate candidate if Tune cannot preserve that boundary. | No measured serial bottleneck justifies a scheduler dependency. Revisit after representative profiling and local process-pool comparison shows a numerical throughput target. |

PyMT is separately deferred. The scalar/daily examples do not establish a
spatial exchange need. Revisit for a concrete pair needing time/grid exchange,
then compare PyMT direct and wrapped results. BMI support alone will not be
reported as PyMT compatibility.

## Inspected sources and compatibility limits

Official pages inspected on 2026-10-27:

- [BMI specification](https://bmi.csdms.io/en/stable/) documents the control,
  variable, time and grid interface. The adapter uses no bmipy import in base.
- [OpenMDAO features](https://openmdao.org/newdocs/versions/latest/features/core_features/index.html)
  cover coupled solves, derivative computation, scaling and recorders.
- [Ax experiment documentation](https://ax.dev/docs/experiment/) explicitly
  labels the discussed internal objects as non-API components. A supported
  public client must be verified against the installed version.
- [Optuna ask/tell](https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/009_ask_and_tell.html)
  separates suggestion and observation from evaluation.
- [DAKOTA interfaces](https://snl-dakota.github.io/docs/latest_release/users/usingdakota/inputfile/interfaces.html)
  connect simulation parameters and responses.
- [Ray Tune](https://docs.ray.io/en/latest/tune/index.html) covers trial tuning
  and resource management. This does not establish scientific recovery parity.

Upstream license locations were inspected for
[Ax](https://github.com/facebook/Ax/blob/main/LICENSE),
[Optuna](https://github.com/optuna/optuna/blob/master/LICENSE),
[OpenMDAO](https://github.com/OpenMDAO/OpenMDAO/blob/master/LICENSE.txt),
[Ray](https://github.com/ray-project/ray/blob/master/LICENSE) and
[DAKOTA](https://github.com/snl-dakota/dakota/blob/devel/LICENSE).
These moving branches are discovery references, not resolved distribution
license attestations. BMI Python's attempted license URL was unavailable.
Exact distribution licenses, transitive dependencies, Python 3.12 compatibility
and platform resolution remain unverified for all proposed extras. Do not
promote a policy until those findings are recorded against pinned artifacts.

The available default Python environment currently contains none of bmipy,
pvlib, ax-platform, optuna, openmdao, ray or torch. No installation was attempted.
This is a dependency inventory, not evidence of incompatibility.

## Frozen prototype limits

The executable protocol is
[`protocol.json`](../../examples/interoperability/optimizer_comparison/protocol.json).
It freezes three seeds, three cases and three policies, 12 physical evaluations
each, four shared initial points, one attempt per action and no repairs,
pruning, concurrency or framework retries. The total ceiling is 324 starts,
including failures. Individual cases have a 120-second deadline and 4 GiB
process ceiling. The whole comparison has a 3600-second ceiling. Collect three
individual timing samples for import and cheap suggestion/tell work.

Conditional spaces use an explicit versioned branch mapping with canonical
inactive defaults and active-configuration deduplication. Both prototypes must
use the same mapping, initial points, evaluator and scientific checks. Freeze
exact configurations, versions, source hashes and output root in a resolved
manifest before execution. These limits do not authorize installations or
expensive runs. No prototype or model comparison has yet executed.

No winner may be chosen from the strongest single score. Apply public API,
license, translation, recovery, resource and documented value gates in order.
Record blocked or adverse outcomes without weakening a gate.

## Coupled engineering selection before comparison

Select the resistor/diode circuit supplied in OpenMDAO 3.41.0's
`openmdao.test_suite.scripts.circuit_analysis.Circuit` as the engineering model.
It contains two implicit node-voltage balances, two resistors and a Shockley
diode. This is an electrical circuit analysis task with physical current and
voltage units, beyond the analytic wiring fixture. Import only the Circuit
class, without executing the module's demonstration block. Preserve upstream
license/attribution and bind the installed source bytes into the manifest.

The proposed design decision is source current needed to reach a target diode
voltage while respecting node-voltage and current limits. Use input source
current in [0.01, 0.1] A, ground voltage zero, initial node guesses 10 V and 1 V,
and retain native Newton/Direct solvers and derivatives. Freeze exact target,
physical limits, solver tolerance, sampling starts, derivative checks and
physical-call ceilings before any comparison. This choice requires no external
data download. It does not establish predictive accuracy for a fabricated
circuit or replace the required native-driver/selected-policy comparison.

Count nonlinear component execution, residual evaluations and derivative work
explicitly, including inner solver calls. Report driver runs separately if a
hard inner-call ceiling cannot be enforced. Direct/wrapped voltage parity and
Kirchhoff current residuals need separate frozen tolerances. OpenMDAO API parity
on an ExecComp fixture is only a wiring check and does not close this gate.

## Prototype comparison outcome and support selection

Select Optuna 4.5.0 for the supported-policy implementation increment. Public
promotion remains gated on controller identity, strict configuration, campaign
construction, complete crash recovery and installed-artifact tests in 4.5.
This selection does not assert a general optimization advantage.

The retained [v2 report](../reviews/part-4/optimizer-comparison-v2.md) reconstructs
251 committed analytic starts. Full records are in
`examples/interoperability/optimizer_comparison/results-v2/`. Manifests confirm
identical shared initial points and working source inventories across all three
policies for each case/seed. The preceding v1 remains diagnostic evidence only.

Optuna and Sobol completed all nine cells. Ax completed two continuous cells
(one stopped on a duplicate proposal without dispatch). Another continuous cell
required more feasible initial observations. All mixed cases failed adaptive
fitting with an object-array conversion error in the pinned environment.
Conditional cases failed Ax's hierarchy requirement: common independent x/y
variables plus family produce multiple roots. Retain these failures and revisit
Ax when its public client supports that hierarchy and the resolved array stack
passes mixed adaptive fitting. Do not replace these failures with penalty scores.

The ordered selection gates support choosing Optuna for further implementation:

1. Its installed distribution license and third-party notices were captured in
   `docs/reviews/part-4/installed-license-evidence.json`. Python 3.12 runtime
   succeeded. The prototype uses public ask/tell APIs.
2. Numeric, integer, categorical and conditional cases completed with explicit
   active decisions. Failed/infeasible trials retained full reasons and no
   objective. Constraints remain authoritative outside the optimizer.
3. Every completed cell checked replayed proposals and duplicate result delivery
   against durable result digests. Dedicated tests also cover transaction faults.
   Full controller physical-start recovery remains a promotion gate.
4. Base imports remain independent. Sampled process-group RSS and deadlines are
   retained for each run. Optional dependencies live in a separate locked Pixi
   project. Linux runtime remains unverified.
5. The common journal and policy interface replace direct caller management of
   trial IDs, failure projection and repeated-delivery reconciliation. This is
   the intended integration burden reduction. The public calibration example
   must demonstrate it end to end before final qualification. No optimization
   benefit is inferred from the strongest score or these analytic tasks.

## Independent BMI and PyMT investigation

On 2026-10-28, inspected the independent CSDMS
[BmiHeat implementation](https://raw.githubusercontent.com/csdms/bmi-example-python/master/heat/bmi_heat.py)
and its [heat model](https://raw.githubusercontent.com/csdms/bmi-example-python/master/heat/heat.py).
The BMI declares uniform_rectilinear grid exchange, temperature in K and time
in seconds. The model defaults to a 10 by 20 plate with a .25-second step.
Those semantics are outside the admitted scalar/daily profile. No flattening,
implicit seconds-to-days conversion or grid averaging will be introduced to make
this model appear compatible. The existing rejection tests cover those grid/time
mismatches before stepping.

Disposition: unsupported by the current subset, investigated through source
inspection, runtime qualification not attempted. The inspected URLs use a moving
branch and are not a tested distribution/version pin. The separate raw license
URL was unavailable during this check. No dependency was installed or model run.
Revisit for a named spatial heat-transfer/coupling need, with an immutable source
pin, license review and an explicit grid/time contract before any execution.

The [PyMT guide](https://pymt.readthedocs.io/en/latest/) describes coupling across
space/time scales. Neither selected development example needs such spatial
exchange. Keep PyMT deferred and do not advertise compatibility from BMI-only
parity. A future concrete model pair must pass direct exchange and grid/time
semantics checks before admission.

## Measured extension need gate

The retained [serial solar profile](../reviews/part-4/ray-need-profile.json)
contains 15 attempts, 35.68 seconds supervised wall time, 24.13 seconds summed
attempt time, median 1.60 seconds and maximum 2.04 seconds per attempt. The current
adaptive policy admits one outstanding action and has no predeclared independent
batch. These timings do not demonstrate useful Ray throughput or justify changing
scientific execution order. A local pool/Ray experiment is deferred until a named
workload provides at least 32 independent preauthorized attempts and a target of
2x throughput versus a bounded local process pool with equal recovery/accounting.
This threshold is a future admission test, not a measured speedup claim.

No development protocol declares a decision requiring uncertainty propagation or
sensitivity estimation from justified probability distributions. Current parameter
bounds are design/search domains, not uncertainty distributions. DAKOTA remains
deferred until such a named decision and method gap exist. No UQ distribution,
failed-sample treatment or proprietary solver interface is invented for this part.
PyMT remains deferred under its separate spatial/time exchange need gate.

## Qualification and burden evidence

The [burden record](../reviews/part-4/integration-burden.md) compares direct
workflow responsibilities with the delivered shared interfaces. Its resource
summary retains repeated timings, memory, failed cells and timing limitations.
The benefit claimed for admission is reusable lifecycle and transaction handling.
The analytic and development examples do not establish optimizer superiority.
Final strict qualification receipts and installed-wheel evidence are linked from
[the completion audit](../reviews/part-4-completion-audit.md).
