"""Freeze reviewable conformance inputs without starting an execution clock.

This preparation reads no credential and launches no native client or model.
It is not approval, real-provider conformance or a completed execution driver.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, read_bytes, reference
from autoengineering.campaign.identity import (
    scientific_identity,
    scientific_source_paths,
    verify_runtime_sources,
)
from autoengineering.campaign.records import ArtifactRef, sha256, unique
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.campaign.spec import (
    AcceptanceSpec,
    CampaignSpec,
    CheckSpec,
    ExecutionSpec,
    WorkflowSpec,
)
from autoengineering.campaign.store import StoreError, checked_directory, durable_write

from .batch import BatchCase, BatchSpec
from .host_configuration import HostConfiguration
from .records import AgentRecord, AgentRunSpec
from .scheduler import validate_run_spec

from .conformance_protocol import (
    VERSION as VERSION,
    POLICIES as POLICIES,
    PROTOCOL_DIGEST as PROTOCOL_DIGEST,
    LIMITS as LIMITS,
    ROLE_LIMITS as ROLE_LIMITS,
    MALFORMED_LIMITS as MALFORMED_LIMITS,
    IMPLEMENTED_CASES as IMPLEMENTED_CASES,
)


def _case_bindings(worker, scientific_digest):
    return tuple(
        BatchCase(
            kind,
            kind,
            digest(
                {
                    "protocol": PROTOCOL_DIGEST,
                    "case": kind,
                    "worker": worker.digest,
                    "scientific": scientific_digest,
                    "criterion": criterion,
                }
            ),
            hosts,
            science,
        )
        for kind, hosts, science, criterion in POLICIES
    )


@dataclass(frozen=True)
class ConformancePreparation(AgentRecord):
    schema_version: Literal["host-conformance-preparation-1.0"]
    protocol_digest: str
    runtime_root: str
    batch: BatchSpec
    worker: AgentRunSpec
    worker_template: ArtifactRef
    scientific_specification: ArtifactRef
    scientific_digest: str
    inputs: tuple[ArtifactRef, ...]

    def _validate(self):
        sha256(self.protocol_digest)
        sha256(self.scientific_digest)
        unique([ref.path for ref in self.inputs], "prepared input path")
        if (
            self.protocol_digest != PROTOCOL_DIGEST
            or self.batch.limits != LIMITS
            or self.worker.limits != ROLE_LIMITS
            or self.batch.scientific_starts != 2
            or self.batch.cases != _case_bindings(self.worker, self.scientific_digest)
            or self.worker.host != self.batch.host
            or self.worker.execution_mode != "supplied"
            or self.worker.workflow_route != "four_role"
            or self.worker.host.kind != "codex"
            or self.worker.host.adapter_version != "2.1"
            or self.worker.source_identity != self.batch.source_identity
            or self.worker.environment_identity != self.batch.environment_identity
            or not Path(self.runtime_root).is_absolute()
            or not 1 <= len(self.inputs) <= 256
            or sum(ref.size_bytes for ref in self.inputs) > 67108864
        ):
            raise ValueError("conformance preparation differs from fixed protocol or scope")


def _json(root, name):
    path = confined_file(root, name)
    with path.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("conformance metadata exceeds 64 KiB")
    return unique_json(raw.decode())


def _runtime_scope(root, runtime, *, allow_existing=False):
    runtime = Path(runtime).absolute()
    resolved = runtime.resolve()
    if resolved.is_relative_to(root.resolve()) or root.resolve().is_relative_to(resolved):
        raise StoreError("conformance preparation and runtime must have separate roots")
    checked_directory(runtime.parent)
    if runtime.is_symlink() or (runtime.exists() and not allow_existing):
        raise StoreError("conformance runtime directory must be absent")
    if runtime.exists():
        checked_directory(runtime)
    runtime = runtime.parent.resolve() / runtime.name
    if runtime.is_relative_to(root) or root.is_relative_to(runtime):
        raise StoreError("conformance preparation and runtime must have separate roots")
    return runtime


def _synthetic(spec, source):
    if (
        spec.baseline.adapter_id != "linear"
        or spec.source_bundle != "scientific-core-v1"
        or {ref.path for ref in spec.provenance.sources}
        != {"examples/campaign_contracts/fixture_model.py", *scientific_source_paths()}
        or spec.baseline.model.source_bundle != spec.provenance.sources
        or spec.baseline.system.path != "examples/campaign_contracts/system.yaml"
        or spec.provenance.environment_lock.path != "pixi.lock"
        or spec.acceptance
        != AcceptanceSpec(
            "rmse", "minimize", 0.01, {}, (CheckSpec("finite", "1", True, "outputs", {}),)
        )
        or spec.workflow != WorkflowSpec()
        or spec.execution != ExecutionSpec(("linear",))
        or spec.calibration is not None
        or spec.confirmation.mode != "disabled"
        or spec.baseline.parameters != {"multiplier": 1.0}
        or tuple((i.target, i.implementation_ids) for i in spec.interventions)
        != (("response", ("linear-v1", "linear-v2")),)
        or {item.id for item in spec.data} != {"forcing", "fitting", "comparison"}
    ):
        raise ValueError("conformance requires the supplied synthetic scalar campaign")
    for item in spec.data:
        if item.artifact.path != f"examples/campaign_contracts/{item.id}.json":
            raise ValueError("conformance data path differs from fixed public scalar fixture")
        expected = {"forcing": 2.0} if item.id == "forcing" else {"prediction": 3.0}
        if unique_json(read_bytes(source, item.artifact, max_bytes=65536).decode()) != expected:
            raise ValueError("conformance scientific inputs differ from public scalar fixtures")


def prepare_conformance(
    worker: AgentRunSpec,
    campaign: Path,
    configuration: HostConfiguration,
    output: Path,
    runtime_root: Path,
) -> ConformancePreparation:
    """Capture only declared science inputs. No worker/batch runtime is created."""
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise StoreError("conformance preparation requires a fresh directory")
    runtime = _runtime_scope(output, runtime_root)
    campaign = checked_directory(campaign)
    configuration.check_scope(output, runtime, campaign)
    validate_run_spec(worker)
    if (
        worker.execution_mode != "supplied"
        or worker.host.kind != "codex"
        or worker.workflow_route != "four_role"
    ):
        raise ValueError("conformance requires an explicit supplied Codex run")
    spec_path = confined_file(campaign, "campaign.yaml")
    if spec_path.stat().st_size > 65536:
        raise ValueError("conformance scientific specification exceeds limit")
    scientific = CampaignSpec.from_yaml(spec_path)
    identity = _json(campaign, "identity.json")
    source = checked_directory(campaign / "bundle")
    from autoengineering.campaign.store import EventStore

    if EventStore(campaign).replay().events:
        raise ValueError("conformance requires an unused prepared scientific campaign")
    _synthetic(scientific, source)
    verify_runtime_sources(scientific)
    science_id = scientific_identity(scientific, source)
    if (
        worker.campaign_id,
        worker.campaign_identity,
        identity["spec_digest"],
        identity["scientific_identity"],
    ) != (scientific.name, science_id, scientific.digest, science_id):
        raise ValueError("conformance worker/scientific binding mismatch")
    allowed = {value for item in scientific.interventions for value in item.implementation_ids}
    if not set(worker.permitted_interventions) <= allowed:
        raise ValueError("conformance worker expands scientific interventions")
    template = worker
    worker = replace(worker, id="conformance-roles", limits=ROLE_LIMITS)
    host = configuration.build(worker)
    references = (
        scientific.baseline.system,
        scientific.provenance.environment_lock,
        *scientific.provenance.sources,
        *(item.artifact for item in scientific.data),
    )
    copied = {}
    for ref in references:
        if ref.path in copied and hashlib.sha256(copied[ref.path]).hexdigest() != ref.sha256:
            raise ValueError("conflicting conformance scientific source")
        copied[ref.path] = read_bytes(source, ref, max_bytes=4194304)
    if len(copied) > 256 or sum(map(len, copied.values())) > 67108864:
        raise ValueError("conformance captured inputs exceed limit")
    output.mkdir(mode=0o700)
    durable_write(output / "worker-template.json", template.to_json().encode())
    durable_write(output / "scientific.yaml", spec_path.read_bytes())
    inputs = []
    for name, raw in sorted(copied.items()):
        path = output / "captured_source" / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        durable_write(path, raw)
        inputs.append(
            reference(
                output,
                str(path.relative_to(output)),
                media_type="application/octet-stream",
                producer="conformance-preparation",
            )
        )
    batch = BatchSpec(
        "1.0",
        "host-conformance",
        worker.source_identity,
        worker.environment_identity,
        worker.host,
        host.capabilities(),
        configuration.digest,
        LIMITS,
        2,
        _case_bindings(worker, scientific.digest),
    )
    plan = ConformancePreparation(
        VERSION,
        PROTOCOL_DIGEST,
        str(runtime),
        batch,
        worker,
        reference(
            output,
            "worker-template.json",
            media_type="application/json",
            producer="conformance-preparation",
        ),
        reference(
            output,
            "scientific.yaml",
            media_type="application/yaml",
            producer="conformance-preparation",
        ),
        scientific.digest,
        tuple(inputs),
    )
    # Manifest last. Partial captures are not resumable executable preparations.
    durable_write(output / "conformance.json", plan.to_json().encode())
    return plan


def load_conformance(root, *, expected_digest, configuration=None, allow_runtime=False):
    """Verify a preparation. Existing runtimes are accepted only for explicit recovery."""
    sha256(expected_digest)
    root = checked_directory(root)
    path = confined_file(root, "conformance.json")
    with path.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536 or hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError("conformance preparation differs from trusted pin")
    plan = ConformancePreparation.from_json(raw.decode())
    template = AgentRunSpec.from_json(
        read_bytes(root, plan.worker_template, max_bytes=65536).decode()
    )
    if replace(template, id="conformance-roles", limits=ROLE_LIMITS) != plan.worker:
        raise ValueError("conformance worker differs from captured template and fixed protocol")
    _runtime_scope(root, plan.runtime_root, allow_existing=allow_runtime)
    validate_run_spec(plan.worker)
    spec_raw = read_bytes(root, plan.scientific_specification, max_bytes=65536)
    spec = CampaignSpec.from_yaml(confined_file(root, plan.scientific_specification.path))
    if spec.digest != plan.scientific_digest or not spec_raw:
        raise ValueError("conformance scientific specification changed")
    for ref in plan.inputs:
        if not ref.path.startswith("captured_source/"):
            raise ValueError("conformance input lies outside captured source")
        read_bytes(root, ref, max_bytes=4194304)
    _synthetic(spec, root / "captured_source")
    verify_runtime_sources(spec)
    if scientific_identity(spec, root / "captured_source") != plan.worker.campaign_identity:
        raise ValueError("captured conformance scientific identity changed")
    if configuration is not None:
        configuration.check_scope(root, Path(plan.runtime_root))
        host = configuration.build(plan.worker)
        if (
            configuration.digest != plan.batch.host_configuration_digest
            or host.capabilities() != plan.batch.capabilities
        ):
            raise ValueError("conformance host configuration or capabilities changed")
    return plan


def inspect_conformance(root, *, expected_digest, configuration=None):
    """Verify review inputs and readiness without starting a runtime or reading a lease."""
    plan = load_conformance(root, expected_digest=expected_digest, configuration=configuration)
    template = AgentRunSpec.from_json(
        read_bytes(root, plan.worker_template, max_bytes=65536).decode()
    )
    return {
        "status": "prepared",
        "preparation_digest": expected_digest,
        "protocol_digest": PROTOCOL_DIGEST,
        "runtime_root": plan.runtime_root,
        "runtime_created": False,
        "clock_started": False,
        "provider_calls": 0,
        "scientific_starts": 0,
        "credential_opened": False,
        "host_profile_checked": configuration is not None,
        "execution_ready": all(row[0] in IMPLEMENTED_CASES for row in POLICIES),
        "implemented_execution_handlers": list(IMPLEMENTED_CASES),
        "missing_execution_handlers": [
            row[0] for row in POLICIES if row[0] not in IMPLEMENTED_CASES
        ],
        "batch_specification_digest": plan.batch.digest,
        "worker_template_digest": template.digest,
        "role_worker_digest": plan.worker.digest,
        "role_worker_limits": plan.worker.limits.to_dict(),
        "authorization": "not_granted_by_preparation",
    }
