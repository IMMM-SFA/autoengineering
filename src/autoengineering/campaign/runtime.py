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


RUNTIME_ROOT = Path(__file__).resolve().parents[3]


def registry() -> AdapterRegistry:
    # This list is application code. Extending it requires an implementation change
    # with a declared dependency closure, not a worker-supplied import string.
    return AdapterRegistry(
        (
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
        )
    )


def routing_adapter():
    from examples.campaign_contracts.routing import adapter

    return adapter()


def validate_policy(spec):
    """Check optional policy availability without importing its numerical dependencies."""
    import importlib.util

    if (
        spec.calibration
        and spec.calibration.run.policy == "botorch"
        and importlib.util.find_spec("botorch") is None
    ):
        raise ValueError("the botorch policy requires the optional bayes environment")
