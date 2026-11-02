"""Bounded wind-native proposals with separate wake and gradient call evidence."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Literal

from autoengineering.campaign.serialization import Record
from examples.utility.wind_native import NativeWindResult, native_layout
from examples.utility.wind import WindTask
from examples.utility.wind_parameters import WindGeometry
from autoengineering.campaign.records import sha256


@dataclass(frozen=True)
class WindNativeSpec(Record):
    schema: Literal["utility-wind-native-spec-v1", "utility-wind-native-spec-v2"]
    geometry: WindGeometry
    maximum_iterations: int
    maximum_wake_calls: int
    maximum_gradient_calls: int
    resource_digest: str | None = None

    def to_dict(self):
        value = super().to_dict()
        if self.schema == "utility-wind-native-spec-v1":
            value.pop("resource_digest")
        return value

    @classmethod
    def from_dict(cls, value):
        if (
            isinstance(value, Mapping)
            and value.get("schema") == "utility-wind-native-spec-v1"
            and "resource_digest" in value
        ):
            raise ValueError("resource binding requires native wind spec v2")
        return super().from_dict(value)

    def _validate(self):
        if len(self.geometry.x) != 4 or (
            self.schema == "utility-wind-native-spec-v1" and self.geometry.direction_step != 30
        ):
            raise ValueError("native wind profile requires four turbines and a 30-degree objective")
        if self.schema == "utility-wind-native-spec-v2":
            if self.resource_digest is None:
                raise ValueError("native wind spec v2 requires an explicit resource binding")
            sha256(self.resource_digest)
        elif self.resource_digest is not None:
            raise ValueError("legacy native wind cannot carry a resource binding")
        if not 1 <= self.maximum_iterations <= 1000:
            raise ValueError("native wind iteration cap must be in 1..1000")
        if min(self.maximum_wake_calls, self.maximum_gradient_calls) < 1 or (
            self.maximum_wake_calls + self.maximum_gradient_calls > 128
        ):
            raise ValueError("native wind needs positive wake/gradient caps with at most 128 calls")


@dataclass(frozen=True)
class WindNativeProposal(Record):
    schema: Literal["utility-wind-native-proposal-v1", "utility-wind-native-proposal-v2"]
    specification: WindNativeSpec
    result: NativeWindResult
    eligibility: Literal["fresh_evaluation_required"] = "fresh_evaluation_required"

    def _validate(self):
        spec, result = self.specification, self.result
        if self.schema.rsplit("-", 1)[-1] != spec.schema.rsplit("-", 1)[-1]:
            raise ValueError("wind proposal version differs from its native specification")
        if (
            result.maximum_iterations,
            result.maximum_wake_calls,
            result.maximum_gradient_calls,
        ) != (spec.maximum_iterations, spec.maximum_wake_calls, spec.maximum_gradient_calls):
            raise ValueError("native wind result changed its frozen limits")
        if len(result.x) != len(spec.geometry.x) or any(
            len(call.x) != len(spec.geometry.x) for call in result.calls
        ):
            raise ValueError("native wind result changed fixed hardware")
        if result.feasible:
            WindTask(
                {"native": (result.x, result.y)},
                (spec.geometry.x, spec.geometry.y),
                direction_step=spec.geometry.direction_step,
            ).validate({"layout_id": "native"})

    @property
    def configuration(self):
        if (
            self.result.status not in ("converged", "not_converged")
            or not self.result.feasible
            or any(c.status == "started" for c in self.result.calls)
        ):
            return None
        try:
            return self.specification.geometry.configuration(self.result.x, self.result.y)
        except ValueError:
            return None

    @property
    def work(self):
        """Callback entries, not inferred inner wake solves or CPU work."""
        return {
            kind: {
                "attempted": sum(c.kind == kind for c in self.result.calls),
                "completed": sum(
                    c.kind == kind and c.status == "completed" for c in self.result.calls
                ),
                "failed": sum(c.kind == kind and c.status == "failed" for c in self.result.calls),
                "unresolved": sum(
                    c.kind == kind and c.status == "started" for c in self.result.calls
                ),
            }
            for kind in ("wake", "gradient")
        }


def propose(specification: WindNativeSpec, *, resource=None):
    """Invoke the original driver. A returned layout remains an unscored proposal."""
    options = {}
    if specification.schema == "utility-wind-native-spec-v2":
        from examples.utility.wind_resource import WindResource

        if (
            not isinstance(resource, WindResource)
            or resource.digest != specification.resource_digest
        ):
            raise ValueError("native proposal requires its original supplied resource")
        resource.validate_geometry(specification.geometry)
        options["resource"] = resource
    elif resource is not None:
        raise ValueError("legacy native proposal cannot override bundled weather")
    result = native_layout(
        (specification.geometry.x, specification.geometry.y),
        max_iterations=specification.maximum_iterations,
        max_wake_calls=specification.maximum_wake_calls,
        max_gradient_calls=specification.maximum_gradient_calls,
        **options,
    )
    version = specification.schema.rsplit("-", 1)[-1]
    return WindNativeProposal("utility-wind-native-proposal-" + version, specification, result)
