# Larger BMI examples and longer searches

This suite adds two seven-parameter models to the existing hydrology, solar and
materials examples. HYMOD-style hydrology adds distributed soil capacity and four
routing reservoirs. The solar chain uses a representative CEC module's single-diode
model, solved by pvlib, with calibrated thermal, electrical and plant parameters.
All numerical chains execute through BMI and declare their connections in YAML.

The data are real observations reused from [the local examples](../local_models/README.md).
The models are more complex, but these are not new datasets or additional domains.
The solar module is a documented proxy, not an identified site component. See
[the protocol](PROTOCOL.md) for equations, bounds, references and limitations.

From the repository root:

```bash
pixi run -e examples python -m examples.complex_models.run --mode fixed --output examples/complex_models/results/fixed
pixi run -e examples python -m examples.complex_models.run --mode freeze-targets --fixed examples/complex_models/results/fixed --output examples/complex_models/results/targets.json
pixi run -e examples python -m examples.complex_models.run --mode target --targets examples/complex_models/results/targets.json --output examples/complex_models/results/target
```

Use fresh output paths for repeat runs. Keep target source directories under the
repository for portable recorded paths. Fixed runs save recommendations at 12, 24,
48 and 96 calls from one trajectory. Target runs use five different seeds and stop
at the frozen validation target or 200 attempts. Test scores never enter search or
stopping. Previous targets stay fixed; new-model targets use the complete fixed matrix.

[Results](results/RESULTS.md) include model calls, elapsed time, held-out scores,
failures and capped searches. A capped run is not reported as convergence. All
original partial-observation gates remain unchanged; these are whole-system runs.
