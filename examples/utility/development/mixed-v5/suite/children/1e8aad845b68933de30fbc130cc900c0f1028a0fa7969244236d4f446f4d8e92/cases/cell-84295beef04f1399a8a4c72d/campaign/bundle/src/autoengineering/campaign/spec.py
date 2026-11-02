"""Versioned author configuration, resolved before any import or execution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from autoengineering.optimization.run_spec import OptimizationRunSpec
from autoengineering.optimization.yaml_utils import safe_load_unique

from .records import (
    ArtifactRef,
    DataContract,
    ModelSnapshot,
    PortContract,
    Scalar,
    identifier,
    unique,
)
from .serialization import Record


@dataclass(frozen=True)
class BaselineSpec(Record):
    system: ArtifactRef
    model: ModelSnapshot
    adapter_id: str
    parameters: Mapping[str, Scalar]

    def _validate(self):
        identifier(self.adapter_id)


@dataclass(frozen=True)
class InterventionSpec(Record):
    target: str
    implementation_ids: tuple[str, ...]
    parameter_bounds: Mapping[str, tuple[float, float]]
    topology: Literal["preserve"] = "preserve"

    def _validate(self):
        identifier(self.target)
        if not self.implementation_ids:
            raise ValueError("intervention must declare implementations")
        unique(self.implementation_ids, "implementation")
        for value in self.implementation_ids:
            identifier(value)
        for name, (low, high) in self.parameter_bounds.items():
            identifier(name)
            if low >= high:
                raise ValueError("parameter bounds must increase")


@dataclass(frozen=True)
class CheckSpec(Record):
    name: str
    version: str
    required: bool
    scope: str
    options: Mapping[str, Scalar]


@dataclass(frozen=True)
class AcceptanceSpec(Record):
    primary_metric: Literal["rmse", "bias", "relative_bias", "correlation", "nse", "kge"]
    direction: Literal["minimize", "maximize"]
    minimum_gain: float
    secondary_tolerances: Mapping[str, float]
    checks: tuple[CheckSpec, ...]
    ranking: Literal["primary_then_id"] = "primary_then_id"
    tie: Literal["retain_eligible_baseline"] = "retain_eligible_baseline"

    def _validate(self):
        if self.minimum_gain < 0 or any(value < 0 for value in self.secondary_tolerances.values()):
            raise ValueError("acceptance tolerances must be nonnegative")
        allowed = {"rmse", "bias", "relative_bias", "correlation", "nse", "kge"}
        if not set(self.secondary_tolerances) <= allowed:
            raise ValueError("unknown secondary metric")
        if not self.checks:
            raise ValueError("acceptance must declare required checks")
        unique([check.name for check in self.checks], "check")


@dataclass(frozen=True)
class CalibrationSpec(Record):
    run: OptimizationRunSpec
    fitting_data_id: str

    def _validate(self):
        if self.run.study.noise.mode != "deterministic":
            raise ValueError("supplied campaign adapters require deterministic studies")
        if self.run.study.budget.cost_unit not in ("calls", "physical_executions", "model_call"):
            raise ValueError("campaign child cost must count physical executions")
        metrics = {"rmse", "bias", "relative_bias", "correlation", "nse", "kge"}
        if self.run.study.objective.outcome not in metrics or any(
            item.outcome not in metrics for item in self.run.study.constraints
        ):
            raise ValueError("calibration outcome is not supplied by the campaign evaluator")
        if self.run.evaluator_factory != "autoengineering.campaign.studies:campaign_evaluator":
            raise ValueError("calibration requires the supplied trusted campaign evaluator factory")
        if self.run.study.schema_version != "1.0" or self.run.study.backend != "system":
            raise ValueError("calibration requires a version 1 system study")
        if self.run.max_new_evaluations is not None:
            raise ValueError("invocation limits do not belong in immutable calibration")
        if self.run.study.budget.max_evaluations is None:
            raise ValueError("calibration requires an explicit physical execution limit")


@dataclass(frozen=True)
class WorkflowSpec(Record):
    required_stages: tuple[str, ...] = (
        "baseline",
        "diagnostics",
        "proposal",
        "admission",
        "evaluation",
        "review",
        "freeze",
        "confirmation",
        "report",
    )
    max_candidates: int = 2
    max_repairs: int = 2
    max_transport_requests: int = 100
    terminal_conditions: tuple[str, ...] = (
        "accepted_candidate",
        "retain_baseline",
        "no_suitable_intervention",
        "no_eligible_model",
        "insufficient_data",
        "invalid_task",
        "budget_exhausted",
        "cancelled",
        "failed_execution",
    )

    def _validate(self):
        if self.required_stages != WorkflowSpec.__dataclass_fields__["required_stages"].default:
            raise ValueError("unsupported workflow stages")
        if (
            self.terminal_conditions
            != WorkflowSpec.__dataclass_fields__["terminal_conditions"].default
        ):
            raise ValueError("unsupported terminal conditions")
        if self.max_candidates < 1 or self.max_repairs not in range(3):
            raise ValueError("invalid candidate/repair limits")
        if self.max_transport_requests < 1:
            raise ValueError("transport limit must be positive")


@dataclass(frozen=True)
class ExecutionSpec(Record):
    adapter_ids: tuple[str, ...]
    diagnostics: Literal["none", "causal_future_forcing_v1"] = "none"
    max_executions: int = 64
    timeout_seconds: float = 60.0
    termination_grace_seconds: float = 5.0
    kill_wait_seconds: float = 5.0
    active_deadline_seconds: float = 1800.0

    def _validate(self):
        if not self.adapter_ids or self.max_executions < 1:
            raise ValueError("execution requires adapters and a positive execution allowance")
        unique(self.adapter_ids, "adapter")
        for value in self.adapter_ids:
            identifier(value)
        for value in (
            self.timeout_seconds,
            self.termination_grace_seconds,
            self.kill_wait_seconds,
            self.active_deadline_seconds,
        ):
            if value <= 0:
                raise ValueError("execution time limits must be positive")


@dataclass(frozen=True)
class ConfirmationSpec(Record):
    mode: Literal["disabled", "once"]
    data_id: str | None = None
    protocol: str | None = None

    def _validate(self):
        supplied = self.data_id is not None and self.protocol is not None
        if self.mode == "once" and not supplied:
            raise ValueError("confirmation requires data and a protocol")
        if self.mode == "disabled" and (self.data_id is not None or self.protocol is not None):
            raise ValueError("disabled confirmation cannot reference data or protocol")


@dataclass(frozen=True)
class ProvenanceSpec(Record):
    sources: tuple[ArtifactRef, ...]
    environment_lock: ArtifactRef
    expected_outputs: tuple[PortContract, ...]

    def _validate(self):
        if not self.sources or not self.expected_outputs:
            raise ValueError("provenance requires sources and output contracts")
        unique([source.path for source in self.sources], "source")
        unique([port.name for port in self.expected_outputs], "expected output")


@dataclass(frozen=True)
class CampaignSpec(Record):
    schema_version: Literal["1.0"]
    name: str
    scientific_scope: str
    seed: int
    source_bundle: str
    baseline: BaselineSpec
    data: tuple[DataContract, ...]
    interventions: tuple[InterventionSpec, ...]
    acceptance: AcceptanceSpec
    calibration: CalibrationSpec | None
    workflow: WorkflowSpec
    execution: ExecutionSpec
    confirmation: ConfirmationSpec
    provenance: ProvenanceSpec

    def _validate(self):
        identifier(self.name)
        if self.seed < 0:
            raise ValueError("seed must be nonnegative")
        if not self.data or not self.interventions:
            raise ValueError("campaign requires data and allowed interventions")
        unique([data.id for data in self.data], "data ID")
        unique([item.target for item in self.interventions], "intervention target")
        if self.baseline.adapter_id not in self.execution.adapter_ids:
            raise ValueError("baseline adapter is not allowed")
        for intervention in self.interventions:
            if intervention.target not in self.baseline.model.implementations:
                raise ValueError("intervention target is absent from baseline")
        data_by_id = {data.id: data for data in self.data}
        if not any(data.role == "forcing" for data in self.data):
            raise ValueError("campaign needs forcing data")
        if not any(data.role == "comparison" for data in self.data):
            raise ValueError("campaign needs comparison data")
        forcing = [data for data in self.data if data.role == "forcing"]
        comparison = [data for data in self.data if data.role == "comparison"]
        if len(forcing) != 1 or forcing[0].ports != self.baseline.model.inputs:
            raise ValueError("forcing interface differs from baseline inputs")
        if len(comparison) != 1 or tuple(port.name for port in comparison[0].ports) != (
            "prediction",
        ):
            raise ValueError("campaign requires one comparison prediction observation contract")
        prediction = next(
            (port for port in self.baseline.model.outputs if port.name == "prediction"), None
        )
        if prediction is None:
            raise ValueError("baseline must expose prediction")
        for data in self.data:
            if data.role not in ("fitting", "comparison", "confirmation", "development_replay"):
                continue
            if len(data.ports) != 1:
                raise ValueError("observation variable or units differ from prediction")
            observed_port = data.ports[0]
            if any(
                getattr(observed_port, field) != getattr(prediction, field)
                for field in (
                    "name",
                    "units",
                    "dimensions",
                    "dtype_family",
                    "coordinates",
                    "grid_id",
                    "coordinate_digest",
                )
            ):
                raise ValueError("observation interface differs from prediction")
            observed_time = data.ports[0].time
            if (observed_time is None) != (prediction.time is None):
                raise ValueError("observation dimensions differ from prediction")
            if observed_time is not None and not set(observed_time.dates) <= set(
                prediction.time.dates
            ):
                raise ValueError("observation dates are outside simulation support")
            if observed_time is not None and any(
                getattr(observed_time, field) != getattr(prediction.time, field)
                for field in ("semantics", "timestep", "calendar", "timestamp")
            ):
                raise ValueError("observation time support differs from prediction")
        if self.confirmation.mode == "once" and self.confirmation.protocol != "eligibility-v1":
            raise ValueError("unregistered confirmation protocol")
        if self.calibration is not None:
            fitting = data_by_id.get(self.calibration.fitting_data_id)
            if fitting is None or fitting.role != "fitting":
                raise ValueError("calibration must reference fitting data")
            declared_paths = {item.artifact.path for item in self.data} | {
                item.path for item in self.provenance.sources
            }
            if not set(self.calibration.run.input_files) <= declared_paths:
                raise ValueError("calibration inputs must reference declared campaign artifacts")
            parameters = self.calibration.run.search_space.parameters
            allowed = {
                name: bounds
                for item in self.interventions
                for name, bounds in item.parameter_bounds.items()
            }
            for parameter in parameters:
                bounds = allowed.get(parameter.name)
                if bounds is None or not hasattr(parameter, "lower"):
                    raise ValueError(
                        "calibration parameter is outside allowed numeric interventions"
                    )
                if parameter.lower < bounds[0] or parameter.upper > bounds[1]:
                    raise ValueError("calibration parameter exceeds allowed bounds")
        if self.confirmation.mode == "once":
            data = data_by_id.get(self.confirmation.data_id)
            if data is None or data.role != "confirmation" or data.prior_exposure != "unexposed":
                raise ValueError("confirmation needs predeclared unexposed confirmation data")
        declared = {source.path: source for source in self.provenance.sources}
        for source in self.baseline.model.source_bundle:
            if declared.get(source.path) != source:
                raise ValueError("baseline sources are absent from declared source closure")
        if self.baseline.model.outputs != self.provenance.expected_outputs:
            raise ValueError("baseline outputs differ from expected artifact contract")

    def to_yaml(self, path: str | Path) -> None:
        Path(path).write_text(yaml.safe_dump(self.to_dict(), sort_keys=False), encoding="utf-8")

    @classmethod
    def from_yaml(cls, path: str | Path) -> CampaignSpec:
        # No model imports, artifact writes, or directory creation during validation.
        return cls.from_dict(safe_load_unique(Path(path).read_text(encoding="utf-8")))
