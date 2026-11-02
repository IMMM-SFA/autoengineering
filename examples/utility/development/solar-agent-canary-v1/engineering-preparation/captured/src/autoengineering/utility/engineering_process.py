"""Trusted source-closed scalar engineering scenarios under process supervision.

This profile is for supplied development code, not generated-code isolation or
private confirmation. Existing batch receipts own every physical start.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import math
from importlib.metadata import distributions
import ast
from importlib.machinery import PathFinder
from pathlib import Path
import sys
from typing import Literal

from autoengineering.agents.batch import PhysicalReservation, PhysicalObservation
from autoengineering.agents.process import supervise_process, recover_completed_process
from autoengineering.campaign.artifacts import read_bytes, confined_file
from autoengineering.campaign.records import ArtifactRef, CheckResult, EvaluationRecord, Scalar
from autoengineering.campaign.serialization import Record, digest
from autoengineering.campaign.store import StoreError, checked_directory, durable_write
from .contracts import identifier
from .outcomes import ScenarioScore, EngineeringEvaluation, aggregate, scenario_checks
from .studies import EngineeringStudySpec


@dataclass(frozen=True)
class EngineeringScenario(Record):
    scenario_id: str
    forcing: Mapping[str, float]

    def _validate(self):
        identifier(self.scenario_id)
        if not self.forcing:
            raise ValueError("engineering scenario needs explicit scalar forcing")
        for name in self.forcing:
            identifier(name)


def execution_identity(entrypoint, sources, lock, scenarios, timeout_seconds, output_bytes, *, profile="supervised-engineering-v1"):
    return digest({"profile": profile, "entrypoint": entrypoint,
        "sources": [ref.to_dict() for ref in sources], "lock": lock.to_dict(),
        "scenarios": [scenario.to_dict() for scenario in scenarios],
        "timeout_seconds": timeout_seconds, "output_bytes": output_bytes})


@dataclass(frozen=True)
class EngineeringExecutionSpec(Record):
    schema: Literal["utility-engineering-execution-v1", "utility-engineering-execution-v2"]
    study: EngineeringStudySpec
    entrypoint: str
    sources: tuple[ArtifactRef, ...]
    lock: ArtifactRef
    scenarios: tuple[EngineeringScenario, ...]
    timeout_seconds: float
    output_bytes: int

    def _validate(self):
        module, separator, function = self.entrypoint.partition(":")
        if not separator or not all(part.isidentifier() for part in module.split(".")) or not function.isidentifier():
            raise ValueError("engineering executor needs a trusted module:function registration")
        if not self.sources or len({r.path for r in self.sources}) != len(self.sources):
            raise ValueError("engineering executor needs a unique complete source inventory")
        if tuple(s.scenario_id for s in self.scenarios) != self.study.scenario_ids:
            raise ValueError("engineering execution scenarios differ from study")
        if self.timeout_seconds <= 0 or not 1 <= self.output_bytes <= 65536:
            raise ValueError("engineering process limits must be positive and bounded")
        if self.study.source_identity != execution_identity(self.entrypoint, self.sources, self.lock,
                self.scenarios, self.timeout_seconds, self.output_bytes,
                profile="supervised-engineering-v2" if self.schema.endswith("v2") else "supervised-engineering-v1"):
            raise ValueError("engineering execution differs from study source identity")


def verify_sources(spec, source_root, *, additional_entrypoints=()):
    """Check all source bytes before any supplied evaluator code can be imported."""
    root = Path(source_root)
    declared = {ref.path: ref for ref in spec.sources}
    for ref in (*spec.sources, spec.lock):
        read_bytes(root, ref)
    permitted = set(declared) | {spec.lock.path}
    for path in root.rglob("*"):
        if path.is_symlink() or (not path.is_dir() and str(path.relative_to(root)) not in permitted):
            raise StoreError("engineering input contains an undeclared file or symlink")
    package = Path(__file__).resolve().parents[1]
    for path in package.rglob("*.py"):
        relative = "src/autoengineering/"+str(path.relative_to(package))
        ref = declared.get(relative)
        if ref is None or read_bytes(root, ref) != path.read_bytes():
            raise StoreError("engineering runtime source closure is incomplete or changed")
    for entrypoint in (spec.entrypoint, *additional_entrypoints):
        module = entrypoint.split(":")[0]
        # find_spec can import parents. Require their files in the closure first.
        search = [str(root), *sys.path]
        for index, part in enumerate(module.split("."), 1):
            name = ".".join(module.split(".")[:index])
            key = name.replace(".", "/")
            keys = (key+".py", key+"/__init__.py", "src/"+key+".py", "src/"+key+"/__init__.py")
            info = PathFinder.find_spec(part, search)
            if info is None:
                raise StoreError("engineering evaluator registration is unavailable")
            if info.origin is not None:
                candidates = [declared[key] for key in keys if key in declared]
                if len(candidates) != 1 or confined_file(Path(info.origin).parent, Path(info.origin).name).read_bytes() != read_bytes(root, candidates[0]):
                    raise StoreError("engineering evaluator module or parent is outside source closure")
                if name == module:
                    tree = ast.parse(Path(info.origin).read_bytes())
                    function = entrypoint.split(":")[1]
                    if not any(isinstance(node, ast.FunctionDef) and node.name == function for node in tree.body):
                        raise StoreError("engineering registration must name a supplied synchronous function")
            search = [str(Path(directory or ".") / part) for directory in search
                      if (Path(directory or ".") / part).is_dir()]


def runtime_packages():
    return sorted({(d.metadata["Name"].lower().replace("_", "-"), d.version)
                   for d in distributions() if d.metadata["Name"]})


def engineering_invocation_identity(spec, action, scenario_id, case_id):
    value = {"action":action.to_dict(), "scenario":scenario_id, "profile":spec.study.digest}
    if spec.schema == "utility-engineering-execution-v2":
        value["case_id"] = case_id
    return digest(value)


def runtime_binding(spec, source_root):
    from autoengineering.agents.identity import host_environment_identity
    return {"execution": spec.to_dict(), "source_root": str(source_root),
            "python": sys.executable, "runtime": host_environment_identity(),
            "packages": runtime_packages()}


@dataclass(frozen=True)
class EngineeringScenarioJob(Record):
    schema: Literal["utility-engineering-job-v1"]
    execution: EngineeringExecutionSpec
    action_id: str
    configuration: Mapping[str, Scalar]
    seed: int
    scenario_id: str
    source_root: str
    scratch_path: str
    binding_digest: str

    def _validate(self):
        from .contracts import sha256
        identifier(self.action_id)
        sha256(self.binding_digest)
        if self.scenario_id not in self.execution.study.scenario_ids or not 0 <= self.seed < 2**63:
            raise ValueError("invalid engineering scenario job")


@dataclass(frozen=True)
class EngineeringScenarioResult(Record):
    schema: Literal["utility-engineering-result-v1"]
    job_digest: str
    score: ScenarioScore
    solver_work: Mapping[str, float]
    lifecycle_seconds: float
    solver_units: Mapping[str, Literal["count", "boolean", "A", "V", "s"]] = field(default_factory=dict)

    def _validate(self):
        from .contracts import sha256
        sha256(self.job_digest)
        if self.lifecycle_seconds < 0 or any(value < 0 for value in self.solver_work.values()):
            raise ValueError("engineering work must be nonnegative")
        if set(self.solver_units) != set(self.solver_work):
            raise ValueError("engineering diagnostics require explicit units")
        if any((self.solver_units[name] == "count" and value != int(value)) or
               (self.solver_units[name] == "boolean" and value not in (0., 1.))
               for name, value in self.solver_work.items()):
            raise ValueError("engineering counters or flags have invalid values")


class SupervisedEngineeringExecutor:
    def __init__(self, spec, batch, case_id, source_root, *, fault=lambda _: None, cancelled=lambda: False):
        if not callable(cancelled):
            raise ValueError("engineering cancellation predicate must be callable")
        self.cancelled = cancelled
        self.spec, self.batch, self.case_id = spec, batch, case_id
        self.source_root, self.fault = checked_directory(source_root), fault
        if batch._trusted_pin != batch.digest or batch.replay().active_case != case_id:
            raise StoreError("engineering executor requires its pinned active batch case")
        case = next(c for c in batch.spec.cases if c.id == case_id)
        ceiling = spec.study.run.study.budget.max_evaluations*len(spec.scenarios)
        if case.scientific_starts < ceiling:
            raise StoreError("batch cannot cover the full engineering scenario reserve")
        verify_sources(spec, self.source_root)
        case_root = batch.root / "cases" / case_id
        case_root.mkdir(mode=0o700, exist_ok=True)
        checked_directory(case_root)
        self.directory = case_root / "engineering-processes"
        if self.directory.is_symlink():
            raise StoreError("engineering process directory cannot be a symlink")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        checked_directory(self.directory)
        binding = runtime_binding(spec, self.source_root)
        from autoengineering.campaign.serialization import canonical_json
        raw = canonical_json(binding)
        self.binding_digest = digest(binding)
        path = self.directory / "execution.json"
        with self.batch.operation():
            if path.exists():
                if confined_file(self.directory, path.name).read_text() != raw:
                    raise StoreError("engineering execution, input root or environment identity changed")
            else:
                if any(r.case_id == case_id for r in self.batch.replay().reservations.values()):
                    raise StoreError("existing scientific work lacks its original execution binding")
                durable_write(path, raw.encode())

    def identity(self, action, scenario):
        return engineering_invocation_identity(self.spec, action, scenario.scenario_id, self.case_id)

    def reservations(self, action):
        state = self.batch.replay()
        return [state.reservations["science-"+self.identity(action, s)[:32]] for s in self.spec.scenarios]

    def __call__(self, action):
        return self._evaluate(action, launch=True)

    def recover_completed(self, action):
        """Read completed original scenarios only. Never dispatch a new one."""
        return self._evaluate(action, launch=False)

    def _evaluate(self, action, *, launch):
        self.spec.study.run.search_space.encode(action.config)
        verify_sources(self.spec, self.source_root)
        if action.replicates != 1 or action.component is not None:
            raise StoreError("engineering process profile supports single system actions only")
        scores, statuses, seconds = [], [], 0.
        for scenario in self.spec.scenarios:
            identity = self.identity(action, scenario)
            reservation_id, nonce = "science-"+identity[:32], "engineering-"+identity[:32]
            root = self.directory / identity
            job = EngineeringScenarioJob("utility-engineering-job-v1", self.spec, action.id,
                action.config, action.seed, scenario.scenario_id, str(self.source_root), str(root), self.binding_digest)
            state = self.batch.replay()
            reservation = state.reservations.get(reservation_id)
            if reservation is None:
                if not launch or state.pending or self.cancelled():
                    raise StoreError("engineering scenario is undispatched or physical work remains uncertain")
                if root.exists():
                    checked_directory(root)
                    if any(root.iterdir()):
                        raise StoreError("undispatched engineering scenario contains unexplained files")
                else:
                    root.mkdir(mode=0o700)
                checked_directory(root)
                reservation = PhysicalReservation(reservation_id, self.case_id, "science", identity,
                    None, self.batch.clock(), self.spec.timeout_seconds+5., 0, 0, 0)
                # Permission is durable before job creation, supervisor or evaluator import.
                with self.batch.operation():
                    self.batch.reserve(reservation)
                    durable_write(root / "scenario.json", job.to_json().encode())
                    self.fault("engineering_scenario_reserved")
                    now = self.batch.clock()
                    if not math.isfinite(now) or now < reservation.recorded_at or now+reservation.timeout_seconds > self.batch.created_at+self.batch.spec.limits.elapsed_seconds:
                        raise StoreError("batch deadline changed before engineering launch; charge retained")
                    process = supervise_process((sys.executable, "-I", "-B", "-m", "autoengineering.utility.engineering_worker",
                        str(root / "scenario.json")), directory=root / "process", cwd=root,
                        environment={}, nonce=nonce, stdin=b"", timeout_seconds=self.spec.timeout_seconds,
                        max_output_bytes=self.spec.output_bytes, on_launch=lambda _: None, parent_watchdog=True, cancelled=self.cancelled)
                    self.fault("engineering_scenario_process_saved")
                    self._observe(reservation, root, job, process)
            else:
                if (reservation.case_id != self.case_id or reservation.invocation_digest != identity
                        or reservation.timeout_seconds != self.spec.timeout_seconds+5.):
                    raise StoreError("original engineering reservation differs")
                if confined_file(root, "scenario.json").read_text() != job.to_json():
                    raise StoreError("original engineering scenario input differs")
                process = recover_completed_process(root / "process", nonce=nonce, max_output_bytes=self.spec.output_bytes)
                with self.batch.operation():
                    self._observe(reservation, root, job, process)
            status, result = self._decode(job, process)
            statuses.append(status)
            seconds += process.elapsed_seconds
            if result is None:
                forcing = self._forcing_digest(scenario)
                checks = tuple(CheckResult(c.name, c.version, "fail", c.required, c.scope, None, None,
                    "Scenario execution did not produce a valid result", ()) for c in self.spec.study.rules.checks)
                scores.append(ScenarioScore(scenario.scenario_id, forcing,
                              {o.name: None for o in self.spec.study.rules.outcomes}, checks))
            else:
                scores.append(result.score)
            self.fault("engineering_scenario_observed")
        status = next((s for s in statuses if s != "success"), "success")
        rules = self.spec.study.rules
        metrics = {o.name: aggregate([score.values.get(o.name) for score in scores], o.aggregation) for o in rules.outcomes}
        evaluation = EvaluationRecord(action.id, "supplied-engineering", action.config, status, metrics,
            scenario_checks(scores, rules.checks), (), "development-fitting", action.id, seconds,
            {"engineering_rules": rules.digest, "executor": self.spec.digest})
        return EngineeringEvaluation(rules.digest, tuple(scores), evaluation)

    @staticmethod
    def _forcing_digest(scenario):
        import numpy as np
        return digest({name: {"shape": [], "dtype": np.asarray(value).dtype.str,
                       "sha256": hashlib.sha256(np.asarray(value).tobytes()).hexdigest()}
                       for name, value in scenario.forcing.items()})

    def _decode(self, job, process):
        if not process.stopped:
            raise StoreError("engineering process stop is unverified")
        if process.status == "timeout":
            return "timeout", None
        if process.status != "completed" or process.returncode != 0 or process.truncated:
            return ("model_failure" if process.returncode == 3 or process.status == "output_limit"
                    else "infrastructure_failure"), None
        try:
            result = EngineeringScenarioResult.from_json(process.stdout.decode())
            rules = self.spec.study.rules
            if (result.job_digest != job.digest or result.score.scenario_id != job.scenario_id
                    or set(result.score.values) != {o.name for o in rules.outcomes}
                    or result.score.forcing_digest != self._forcing_digest(next(
                        s for s in self.spec.scenarios if s.scenario_id == job.scenario_id))):
                raise ValueError("scenario output identity differs")
            if len(result.score.checks) != len(rules.checks) or {c.name for c in result.score.checks} != {c.name for c in rules.checks}:
                raise ValueError("scenario check set differs from frozen rules")
            for declared in rules.checks:
                observed = next(c for c in result.score.checks if c.name == declared.name)
                if (observed.version, observed.required, observed.scope) != (declared.version, declared.required, declared.scope):
                    raise ValueError("scenario check semantics differ")
            return ("success" if all(v is not None for v in result.score.values.values()) else "model_failure"), result
        except (ValueError, UnicodeError):
            return "model_failure", None

    def _observe(self, reservation, root, job, process):
        status, result = self._decode(job, process)
        proof = self.batch.evidence({"profile": "supervised-engineering-v1", "job_digest": job.digest,
            "execution_digest": self.spec.digest, "process_directory": str((root / "process").relative_to(self.batch.root)),
            "status": status, "stop_verified": process.stopped,
            "process_status": process.status, "process_identity": process.identity.to_dict() if process.identity else None,
            "result": result.to_dict() if result else None})
        self.batch.observe(PhysicalObservation(reservation.id, status, process.stopped, 0, {}, None,
                            "not_applicable", process.elapsed_seconds, (proof,)))
