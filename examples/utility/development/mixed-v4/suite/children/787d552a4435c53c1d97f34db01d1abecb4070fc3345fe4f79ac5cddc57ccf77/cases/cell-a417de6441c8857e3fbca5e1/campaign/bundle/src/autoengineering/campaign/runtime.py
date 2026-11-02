"""Supplied trusted local runtimes. Requests can select IDs, never factories or commands."""

from __future__ import annotations

from pathlib import Path

from autoengineering.adapters.contracts import AdapterRegistration, AdapterRegistry
from autoengineering.adapters.python import PythonAdapter


def linear_adapter():
    from examples.campaign_contracts.fixture_model import linear

    def validate(parameters):
        if set(parameters) != {"multiplier"} or type(parameters["multiplier"]) not in (float, int):
            raise ValueError("linear adapter requires a numeric multiplier")
        if not 0 <= parameters["multiplier"] <= 2:
            raise ValueError("multiplier exceeds fixture bounds")

    return PythonAdapter(
        lambda inputs, params: {"prediction": linear(inputs["forcing"], params["multiplier"])},
        validate,
    )


def hydrology_adapter():
    from examples.campaign_contracts.hydrology import HydrologyAdapter

    return HydrologyAdapter()


def fixed_linear_adapter():
    from examples.campaign_contracts.fixture_model import linear

    def validate(parameters):
        if parameters:
            raise ValueError("fixed linear adapter has no parameters")

    return PythonAdapter(
        lambda inputs, params: {"prediction": linear(inputs["forcing"], 1.0)}, validate
    )


RUNTIME_ROOT = Path(__file__).resolve().parents[2]
if RUNTIME_ROOT.name == "src":
    RUNTIME_ROOT = RUNTIME_ROOT.parent


def registry(*, spec=None, root: Path | None = None) -> AdapterRegistry:
    # This list is application code. Extending it requires an implementation change
    # with a declared dependency closure, not a worker-supplied import string.
    entries = [
        AdapterRegistration(
            "solar-pvlib", "1", solar_adapter,
            ("examples/interoperability/solar/model.py", "examples/open_chains/solar/models.py"),
            source_root=RUNTIME_ROOT,
        ),
        AdapterRegistration(
            "routing",
            "1",
            routing_adapter,
            (
                "examples/leaf_river/models/__init__.py",
                "examples/campaign_contracts/routing.py",
                "examples/leaf_river/models/routing.py",
                "examples/leaf_river/models/routing_calibrated.py",
            ),
            source_root=RUNTIME_ROOT,
        ),
        AdapterRegistration(
            "linear",
            "1",
            linear_adapter,
            ("examples/campaign_contracts/fixture_model.py",),
            source_root=RUNTIME_ROOT,
        ),
        AdapterRegistration(
            "linear-fixed",
            "1",
            fixed_linear_adapter,
            ("examples/campaign_contracts/fixture_model.py",),
            source_root=RUNTIME_ROOT,
        ),
        AdapterRegistration(
            "hydrology",
            "1",
            hydrology_adapter,
            (
                "examples/leaf_river/models/__init__.py",
                "examples/campaign_contracts/hydrology.py",
                "examples/leaf_river/models/pet_hamon.py",
                "examples/leaf_river/models/pet_hargreaves.py",
                "examples/leaf_river/models/soil_moisture.py",
            ),
            source_root=RUNTIME_ROOT,
        ),
    ]
    if spec is not None:
        generated = [name for name in spec.execution.adapter_ids if name.startswith("generated-")]
        if generated:
            validate_policy(spec)
            from autoengineering.adapters.isolated import registration_entry
            from .identity import verify_runtime_sources

            if root is None:
                raise ValueError("generated registration requires its frozen source bundle")
            verify_runtime_sources(spec)
            for name in generated:
                entries.append(
                    registration_entry(root, expected_identity=name.removeprefix("generated-"))
                )
    return AdapterRegistry(tuple(entries))


def routing_adapter():
    from examples.campaign_contracts.routing import adapter

    return adapter()


def solar_adapter():
    from examples.interoperability.solar.model import adapter

    return adapter()


def validate_policy(spec):
    """Check optional policy availability without importing its numerical dependencies."""
    import importlib.util

    generated = [name for name in spec.execution.adapter_ids if name.startswith("generated-")]
    if generated:
        import re
        from .identity import ISOLATED_SCIENTIFIC_CLOSURE

        if len(generated) != 1 or not re.fullmatch(r"generated-[0-9a-f]{64}", generated[0]):
            raise ValueError("initial generated catalogue requires one exact registered digest")
        if ISOLATED_SCIENTIFIC_CLOSURE not in {ref.path for ref in spec.provenance.sources}:
            raise ValueError("generated execution requires scientific closure version 2")
        if spec.calibration is not None or spec.baseline.parameters:
            raise ValueError("initial generated campaigns require fixed parameterless adapters")

    if (
        spec.calibration
        and spec.calibration.run.policy == "botorch"
        and importlib.util.find_spec("botorch") is None
    ):
        raise ValueError("the botorch policy requires the optional bayes environment")
    if spec.calibration is not None and spec.calibration.run.policy == "optuna":
        from autoengineering.optimization.command import build_backend
        from .identity import SCIENTIFIC_CLOSURE, INTEROPERABILITY_SCIENTIFIC_CLOSURE

        declared = {ref.path for ref in spec.provenance.sources}
        if SCIENTIFIC_CLOSURE in declared and INTEROPERABILITY_SCIENTIFIC_CLOSURE not in declared:
            raise ValueError("Optuna requires scientific closure version 3 or the entire package")
        if "src/autoengineering/optimization/optuna_backend.py" not in declared:
            raise ValueError("Optuna implementation is missing from the scientific source closure")

        # Validate dependency/version before reserving or starting model work.
        build_backend(spec.calibration.run)
