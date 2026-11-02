"""Freeze native comparison inputs without credentials, dispatch or execution clocks.

This proposal is not permission to
call a provider or execute the measured Leaf River scientific campaigns.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore
from autoengineering.agents.conformance import load_conformance
from autoengineering.agents.conformance_report import read_report as conformance_report
from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.agents.permissions import POLICY_DIGEST
from autoengineering.agents.records import AgentRecord, AgentRunSpec, HostSelection, ResourceLimits
from autoengineering.agents.scheduler import template_digests, validate_run_spec
from autoengineering.agents.single_agent import single_agent_spec
from autoengineering.campaign.artifacts import confined_file, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef, sha256
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import StoreError, checked_directory, durable_write

from . import prepare_leafriver as leaf
from .comparison_status import read_json

VERSION = "native-matched-preparation-1.1"
DRIVER_FILES = (
    "native_runtime.py",
    "native_interruption.py",
    "native_evidence.py",
    "native_status.py",
    "comparison_runtime.py",
    "comparison_status.py",
    "native_run.py",
)
LIMITS = ResourceLimits(40, 32, 8, 2, 1800, 30, 2097152, 131072)
PROTOCOL = {
    "version": VERSION,
    "routes": list(leaf.ROUTES),
    "candidate_order": ["pet-hamon-v1", "pet-hargreaves-v1"],
    "route_worker_limits": leaf.LIVE_LIMITS.to_dict(),
    "aggregate_limits": LIMITS.to_dict(),
    "scientific_starts": 114,
    "scientific_starts_per_route": 38,
    "physical_host_calls": {"scripted": 0, "single_agent": 20, "four_role": 20},
    "required_conformance": "completed real-provider runtime bound to captured preparation",
    "interruption": "one owned-supervisor stop before credential preflight in each live route, within original allowances",
    "remote_computation_stop": "unknown",
    "static_control": "same output-unit mutation and actual admission validator for each route; no worker feedback",
    "provider_proof": "fixed-worker proof and observed model required for completed native role calls",
    "execution_implemented": True,
}
PROTOCOL_DIGEST = digest(PROTOCOL)


@dataclass(frozen=True)
class NativeCase(AgentRecord):
    id: Literal["scripted", "single_agent", "four_role"]
    scientific: ArtifactRef
    worker: AgentRunSpec

    def _validate(self):
        if self.scientific.path != f"leaf/campaigns/{self.id}.yaml":
            raise ValueError("native comparison scientific path differs")
        route = "single_agent" if self.id == "single_agent" else "four_role"
        if (
            self.worker.workflow_route != route
            or self.worker.limits != leaf.LIVE_LIMITS
            or self.worker.execution_mode != "supplied"
        ):
            raise ValueError("native comparison route, mode or allowance differs")
        if self.worker.host.kind != ("fake" if self.id == "scripted" else "codex"):
            raise ValueError("native comparison host differs from case")

    @property
    def configuration_digest(self):
        return digest({"protocol": PROTOCOL_DIGEST, "case": self.to_dict()})


def _bindings(cases):
    return tuple(
        BatchCase(c.id, "comparison", c.configuration_digest, 0 if c.id == "scripted" else 20, 38)
        for c in cases
    )


@dataclass(frozen=True)
class NativePreparation(AgentRecord):
    schema_version: Literal["native-matched-preparation-1.1"]
    protocol_digest: str
    runtime_root: str
    leaf: ArtifactRef
    conformance: ArtifactRef
    template: ArtifactRef
    recipe: ArtifactRef
    driver_sources: tuple[ArtifactRef, ...]
    cases: tuple[NativeCase, ...]
    batch: BatchSpec

    def _validate(self):
        sha256(self.protocol_digest)
        if (
            self.protocol_digest != PROTOCOL_DIGEST
            or self.leaf.path != "leaf/leaf-preparation.json"
            or self.conformance.path != "conformance/conformance.json"
            or self.template.path != "worker-template.json"
            or self.recipe.path != "native-comparison-recipe.py"
            or tuple(r.path for r in self.driver_sources)
            != tuple(f"driver/{n}" for n in DRIVER_FILES)
            or tuple(c.id for c in self.cases) != leaf.ROUTES
            or not Path(self.runtime_root).is_absolute()
            or self.batch.host.kind != "codex"
            or self.batch.host.adapter_version != "2.1"
            or self.batch.limits != LIMITS
            or self.batch.scientific_starts != 114
            or self.batch.cases != _bindings(self.cases)
        ):
            raise ValueError("native preparation differs from fixed protocol")
        for case in self.cases:
            if (
                case.worker.source_identity != self.batch.source_identity
                or case.worker.environment_identity != self.batch.environment_identity
            ):
                raise ValueError("native worker/batch source differs")
            if case.id != "scripted" and case.worker.host != self.batch.host:
                raise ValueError("live comparison workers must share the selected host")


def _scope(output, runtime, conformance_runtime, *, allow_runtime=False):
    checked_directory(output.parent)
    checked_directory(runtime.parent)
    if runtime.is_symlink() or (runtime.exists() and not allow_runtime):
        raise ValueError("native comparison runtime must be absent")
    paths = (output.resolve(), runtime.resolve(), Path(conformance_runtime).resolve())
    if any(
        a.is_relative_to(b) or b.is_relative_to(a)
        for i, a in enumerate(paths)
        for b in paths[i + 1 :]
    ):
        raise ValueError("native preparation and both execution roots must be separate")


def _workers(template, proposal):
    result = []
    for row in proposal.routes:
        worker = replace(
            template,
            schema_version="1.0",
            workflow_route="four_role",
            id=f"matched-worker-{row.route.replace('_', '-')}",
            campaign_id=f"matched-leaf-{row.route.replace('_', '-')}-v1",
            campaign_identity=row.scientific_identity,
            role_templates=template_digests(),
            permitted_interventions=("hamon-v1", "hargreaves-v1"),
            tool_policy_digest=POLICY_DIGEST,
            limits=leaf.LIVE_LIMITS,
        )
        if row.route == "single_agent":
            worker = single_agent_spec(worker, run_id=worker.id)
        elif row.route == "scripted":
            worker = replace(worker, host=HostSelection("fake", "none", "scripted", "1.0"))
        result.append(
            NativeCase(
                row.route, replace(row.specification, path=f"leaf/{row.specification.path}"), worker
            )
        )
    return tuple(result)


def _write(root, relative, raw):
    path = root / relative
    parent = root
    for part in Path(relative).parts[:-1]:
        parent = parent / part
        parent.mkdir(mode=0o700, exist_ok=True)
        checked_directory(parent)
    durable_write(path, raw)


def _ref(root, name, *, media_type="application/json"):
    return reference(root, name, media_type=media_type, producer="native-comparison-preparation")


def prepare(
    leaf_root,
    *,
    leaf_digest,
    conformance_root,
    conformance_digest,
    template,
    configuration,
    output,
    runtime_root,
):
    """Capture frozen child proposals, without opening a credential or a runtime."""
    leaf_root, conformance_root = checked_directory(leaf_root), checked_directory(conformance_root)
    proposal = leaf.load(leaf_root, expected_digest=leaf_digest)
    conformance = load_conformance(
        conformance_root,
        expected_digest=conformance_digest,
        configuration=configuration,
        allow_runtime=True,
    )
    output, runtime = Path(output).absolute(), Path(runtime_root).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("native preparation requires an absent output directory")
    _scope(output, runtime, conformance.runtime_root)
    configuration.check_scope(
        output, runtime, leaf_root, conformance_root, Path(conformance.runtime_root)
    )
    validate_run_spec(template)
    if (
        template.workflow_route != "four_role"
        or template.execution_mode != "supplied"
        or template.host != conformance.worker.host
    ):
        raise ValueError("native template differs from captured supplied host conformance")
    cases = _workers(template, proposal)
    host = configuration.build(cases[-1].worker)
    if host.capabilities() != conformance.batch.capabilities:
        raise ValueError("native comparison/conformance capabilities differ")
    # Verify and collect all bytes before creating the destination.
    raw = {
        "leaf/leaf-preparation.json": confined_file(
            leaf_root, "leaf-preparation.json"
        ).read_bytes(),
        "conformance/conformance.json": confined_file(
            conformance_root, "conformance.json"
        ).read_bytes(),
    }
    leaf_refs = (
        proposal.template,
        proposal.recipe,
        proposal.audit,
        *proposal.inputs,
        *(r.specification for r in proposal.routes),
    )
    for ref in leaf_refs:
        raw[f"leaf/{ref.path}"] = read_bytes(leaf_root, ref, max_bytes=4194304)
    for ref in (
        conformance.worker_template,
        conformance.scientific_specification,
        *conformance.inputs,
    ):
        raw[f"conformance/{ref.path}"] = read_bytes(conformance_root, ref, max_bytes=4194304)
    if len(raw) > 512 or sum(map(len, raw.values())) > 134217728:
        raise ValueError("native preparation capture exceeds limits")
    output.mkdir(mode=0o700)
    for name, value in sorted(raw.items()):
        _write(output, name, value)
    _write(output, "worker-template.json", template.to_json().encode())
    _write(output, "native-comparison-recipe.py", Path(__file__).read_bytes())
    for name in DRIVER_FILES:
        _write(output, f"driver/{name}", Path(__file__).with_name(name).read_bytes())
    batch = BatchSpec(
        "1.0",
        "matched-leaf-native-v1",
        template.source_identity,
        template.environment_identity,
        template.host,
        host.capabilities(),
        configuration.digest,
        LIMITS,
        114,
        _bindings(cases),
    )
    plan = NativePreparation(
        VERSION,
        PROTOCOL_DIGEST,
        str(runtime),
        _ref(output, "leaf/leaf-preparation.json"),
        _ref(output, "conformance/conformance.json"),
        _ref(output, "worker-template.json"),
        _ref(output, "native-comparison-recipe.py", media_type="text/x-python"),
        tuple(_ref(output, f"driver/{name}", media_type="text/x-python") for name in DRIVER_FILES),
        cases,
        batch,
    )
    durable_write(output / "native-comparison.json", plan.to_json().encode())
    return plan


def load(root, *, expected_digest, configuration, allow_runtime=False):
    sha256(expected_digest)
    root = checked_directory(root)
    value = read_json(root, "native-comparison.json")
    if digest(value) != expected_digest:
        raise ValueError("native preparation differs from trusted pin")
    plan = NativePreparation.from_dict(value)
    for ref in (plan.leaf, plan.conformance, plan.template, plan.recipe):
        read_bytes(root, ref, max_bytes=65536)
    if read_bytes(root, plan.recipe) != Path(__file__).read_bytes():
        raise ValueError("native preparation recipe changed")
    for name, ref in zip(DRIVER_FILES, plan.driver_sources):
        if read_bytes(root, ref, max_bytes=65536) != Path(__file__).with_name(name).read_bytes():
            raise ValueError("native comparison driver source changed")
    proposal = leaf.load(root / "leaf", expected_digest=plan.leaf.sha256)
    conformance = load_conformance(
        root / "conformance",
        expected_digest=plan.conformance.sha256,
        configuration=configuration,
        allow_runtime=True,
    )
    _scope(root, Path(plan.runtime_root), conformance.runtime_root, allow_runtime=allow_runtime)
    configuration.check_scope(root, Path(plan.runtime_root), Path(conformance.runtime_root))
    template = AgentRunSpec.from_json(read_bytes(root, plan.template).decode())
    validate_run_spec(template)
    if (
        template.workflow_route != "four_role"
        or template.execution_mode != "supplied"
        or template.host != conformance.worker.host
        or plan.cases != _workers(template, proposal)
    ):
        raise ValueError("native cases differ from original template and Leaf proposal")
    for case in plan.cases:
        validate_run_spec(case.worker)
        read_bytes(root, case.scientific, max_bytes=1048576)
    host = configuration.build(plan.cases[-1].worker)
    if (
        configuration.digest != plan.batch.host_configuration_digest
        or host.capabilities() != plan.batch.capabilities
        or host.capabilities() != conformance.batch.capabilities
    ):
        raise ValueError("native host configuration or capabilities changed")
    return plan


def inspect(root, *, expected_digest, configuration):
    plan = load(root, expected_digest=expected_digest, configuration=configuration)
    return {
        "status": "prepared",
        "preparation_digest": expected_digest,
        "protocol_digest": PROTOCOL_DIGEST,
        "runtime_root": plan.runtime_root,
        "runtime_created": False,
        "clock_started": False,
        "credential_opened": False,
        "provider_calls": 0,
        "scientific_starts": 0,
        "execution_ready": False,
        "missing_execution_handlers": [],
        "authorization": "not_granted_by_preparation",
        "batch_specification_digest": plan.batch.digest,
        "conformance_preparation_digest": plan.conformance.sha256,
        "case_workers": {c.id: c.worker.digest for c in plan.cases},
        "physical_host_limits": {c.id: c.host_invocations for c in plan.batch.cases},
        "scientific_start_limit": 114,
    }


def verify_conformance_prerequisite(
    root, *, expected_digest, configuration, runtime_digest, allow_runtime=False
):
    """Read completed real-provider proof. This never starts the matched clock."""
    plan = load(
        root,
        expected_digest=expected_digest,
        configuration=configuration,
        allow_runtime=allow_runtime,
    )
    required = load_conformance(
        Path(root) / "conformance",
        expected_digest=plan.conformance.sha256,
        configuration=configuration,
        allow_runtime=True,
    )
    proof = conformance_report(required.runtime_root, expected_digest=runtime_digest)
    if proof["status"] != "completed" or proof["live_conformance_complete"] is not True:
        raise StoreError("real-provider conformance is not complete")
    observed = BatchStore(required.runtime_root, expected_digest=runtime_digest)
    if proof["preparation_digest"] != plan.conformance.sha256 or observed.spec != required.batch:
        raise StoreError("completed conformance differs from frozen native prerequisite")
    return {
        "conformance_runtime_digest": runtime_digest,
        "conformance_preparation_digest": plan.conformance.sha256,
        "conformance_specification_digest": required.batch.digest,
        "conformance_report_digest": digest(proof),
        "conformance_head": observed.replay().events[-1].digest
        if observed.replay().events
        else None,
        "authorization": "not_granted_by_prerequisite",
        "matched_runtime_created": False,
        "execution_ready": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leaf-preparation", type=Path, required=True)
    parser.add_argument("--leaf-digest", required=True)
    parser.add_argument("--conformance-preparation", type=Path, required=True)
    parser.add_argument("--conformance-digest", required=True)
    parser.add_argument("--worker-template", type=Path, required=True)
    parser.add_argument("--host-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    args = parser.parse_args()
    configuration = HostConfiguration.from_file(args.host_config)
    plan = prepare(
        args.leaf_preparation,
        leaf_digest=args.leaf_digest,
        conformance_root=args.conformance_preparation,
        conformance_digest=args.conformance_digest,
        template=AgentRunSpec.from_file(args.worker_template),
        configuration=configuration,
        output=args.output,
        runtime_root=args.runtime_root,
    )
    print(
        canonical_json(
            inspect(args.output, expected_digest=plan.digest, configuration=configuration)
        )
    )


if __name__ == "__main__":
    main()
