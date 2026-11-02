# Scientific interoperability development examples

Part 4 is in progress. These examples test supplied implementations and preserve
failed work. They do not establish prediction skill, optimizer superiority or
agent utility. The [progress record](../../docs/reviews/part-4-progress.md)
tracks remaining acceptance gates.

## Environment

The prototypes use a separate locked Pixi project, including Ax 1.1.2, Optuna
4.5.0, OpenMDAO 3.41.0, BMI Python 2.0.1 and pvlib 0.15.2. This environment is
separate from the package's optional Optuna environment.

```sh
pixi install --manifest-path examples/interoperability/optimizer_comparison/pixi.toml
```

Run commands from the repository root, with `PYTHONPATH=src` if using another
checkout's interpreter. Pixi's prototype manifest can launch its Python:

```sh
pixi run --manifest-path examples/interoperability/optimizer_comparison/pixi.toml \
  python -m examples.interoperability.optimizer_comparison.report \
  examples/interoperability/optimizer_comparison/results-v2 \
  --output outputs/optimizer-comparison-report.md
```

The report reads retained results without optimizer imports or model calls.
Create the output parent directory first. The checked v2 comparison completed
251 analytic evaluations. Optuna and Sobol completed nine cells each. Ax's
partial results and API/environment failures remain in the evidence. The
[decision record](../../docs/decisions/part-4-integrations.md) selects Optuna for
implementation and preserves its remaining promotion gates.

## Coupled electrical circuit

```sh
pixi run --manifest-path examples/interoperability/optimizer_comparison/pixi.toml \
  python -m examples.interoperability.circuit.run --output outputs/circuit-development
```

Use a fresh directory. This runs the upstream OpenMDAO resistor/diode circuit
with implicit node balances, checks direct/wrapped outputs, audits a total
derivative, executes 12 Optuna attempts and runs native SLSQP separately.
The native derivative and nonlinear methods are retained. Inner work is counted,
and the comparison is labeled unmatched because the budgets differ. Instrumentation
uses explicit hooks pinned to OpenMDAO 3.41.0, not a portable API promise.
Original framework code is imported under its Apache-2.0 license.

The protocol declares limits, but end-to-end memory/deadline supervision and
installed report reconstruction remain open. Run only as a local development
example until those gates pass.

## Verified OEDI solar cache

```sh
pixi run --manifest-path examples/interoperability/optimizer_comparison/pixi.toml \
  python -m examples.interoperability.solar.parity \
  --cache /path/to/existing/9068-cache --output outputs/solar-parity
```

The cache must contain the four files declared by the preserved solar source
manifest. This command verifies existing bytes and never downloads or changes
them. It reads the frozen June 2018 development window, using measured pad-2
irradiance and inverter-2 AC observations. UTC five-minute instantaneous ports
preserve power units, explicit gaps, state resets and warmup masks. Energy and
confirmation are not reported. Raw inputs remain outside version control.

The baseline includes Faiman plus Prilliman transience, the CEC electrical model
and Sandia inverter. Steady Faiman and SAPM module temperature are supplied
alternatives. A bounded extra DC loss can reduce output but cannot introduce
a gain greater than one. Night-time Sandia standby behavior is preserved.
A scripted campaign is available from an installed package as well as a checkout:

```sh
python -m examples.interoperability.solar.campaign \
  --cache /path/to/existing/9068-cache --output work/solar-prepared
autoengineering campaign run work/solar-prepared/campaign.yaml \
  --source-root work/solar-prepared/source --workdir work/solar-campaign
```

Preparation captures a fresh source/input bundle and does not write into the
installed package. Fitting observations precede June 5, and comparison observations
start on June 5. The campaign allows 18 physical starts with a 120-second active
allowance. No independent confirmation is attempted. The [upstream example
README](../open_chains/solar/README.md) records equipment assumptions, QA limits,
data terms and previous exposure.

## Installed model examples

The wheel includes the solar and circuit modules, their protocols, and the
preserved solar chain metadata. With Python 3.12, install the admitted optional
dependencies using `autoengineering[interoperability]`. The separate Pixi
`interoperability` environment resolves these dependencies without adding Ax or
changing existing solve groups. The Ax comparison retains its own environment.
Raw data, result archives and local outputs are not wheel payloads.

Installed solar preparation and pause/resume completed 15 accounted starts
outside the checkout. The installed circuit example is checked separately.
Use a fresh private working directory for verification. An initial check in the
shared temporary directory failed because an unrelated inspect.py shadowed the
standard-library module in a child process. That infrastructure attempt is
preserved and is not a model failure or a successful parity result.

## BMI daily reservoir parity

```sh
python -m examples.interoperability.bmi.run --output work/bmi-parity
```

This installed command reuses the preserved local reservoir class and direct BMI
driver with three supplied daily inputs. It compares all flow/storage outputs
exactly and checks water balance independently. Rates use interval-mean daily
values labeled at interval end. Storage is an instantaneous end-of-interval
state. No measured inputs, downloads or implicit time/unit conversion occur.
The wheel includes the local model helpers required by this command. It does not
bundle the historical local-model data caches.

## Resource-supervised development runs

```sh
python -m autoengineering.integrations.supervision bmi --output work/bmi-bounded
python -m autoengineering.integrations.supervision circuit --output work/circuit-bounded
python -m autoengineering.integrations.supervision solar \
  --cache /path/to/existing/9068-cache --output work/solar-bounded
```

Use fresh output roots. The supervisor launches only these named trusted examples,
records code/protocol identity before work, and watches the observed process tree
with pinned psutil. It enforces a wall deadline and sampled aggregate RSS limits.
This is not a kernel instantaneous memory quota, and unobserved detached work is
outside the boundary. The admitted examples do not detach work. A failed monitor
stops observed processes and reports failure. It never supplies a numerical
objective or restarts a scientific attempt. Interrupted campaigns require ledger
reconciliation before any authorized restart.

The circuit records intent and work receipts for each native coupled solve,
including aggregate solver iterations and derivative/component work. Its native
and Optuna budgets remain unmatched. Reports preserve this limitation.
