"""Trusted source-response staging and bounded checks above a frozen campaign.

Workers return text, not paths, commands, test receipts or registration authority.
Preparation never admits a snapshot into the originating scientific campaign.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal
import hashlib
import uuid

from autoengineering.campaign.artifacts import confined_file, read_bytes, reference
from autoengineering.campaign.serialization import Record, canonical_json, unique_json
from autoengineering.campaign.store import (
    checked_directory,
    durable_write,
    StoreError,
    sync_directory,
)

from .broker import action_id
from .containers import ContainerResult
from .container_recovery import reconcile_container
from .interface import (
    InterfaceSpec,
    InterfaceReceipt,
    InterfaceCheck,
    check_interface,
    verify_interface,
    _sources,
    _manifest,
    _check_result,
    runner_identity,
)
from .qualification import verify_qualification
from .records import SourceDraft, ImplementationPreparation, ImplementationBundle
from .scheduler import validate_run_spec
from .store import serialized_operation
from .workspaces import CandidateWorkspace, WorkspaceManifest, WorkspacePolicy, SourceCapture


@dataclass(frozen=True)
class PreparationSpec(Record):
    schema_version: Literal["1.0"]
    run_digest: str
    proposal_digest: str
    parent_revision: int
    parent_head: str
    baseline_sha256: str
    specification: InterfaceSpec
    qualification_digest: str
    policy: WorkspacePolicy
    maximum_container_starts: int

    def _validate(self):
        from autoengineering.campaign.records import sha256

        for value in (
            self.run_digest,
            self.proposal_digest,
            self.parent_head,
            self.baseline_sha256,
            self.qualification_digest,
        ):
            sha256(value)
        if self.maximum_container_starts != len(self.specification.cases):
            raise ValueError("preparation check allowance differs from its frozen fixtures")


def _read(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 65536:
        raise StoreError("preparation record exceeds 64 KiB")
    return path.read_text()


class SourcePreparation:
    def __init__(self, broker, qualification_root: Path, qualification_digest: str):
        self.broker, self.store = broker, broker.store
        self.qualification_root = checked_directory(qualification_root)
        self.qualification_digest = qualification_digest
        validate_run_spec(self.store.spec)
        if self.store.spec.execution_mode != "generated":
            raise StoreError("source preparation requires explicit generated mode")
        verify_qualification(self.qualification_root, expected_digest=qualification_digest)

    def _current(self, preparation_id):
        return self.store.replay().preparations[preparation_id]

    def _workspace(self, value):
        root = self.store.root / value.workspace
        manifest = WorkspaceManifest.from_json(_read(root, "manifest.json"))
        workspace = CandidateWorkspace(root, manifest)
        capture = SourceCapture.from_json(read_bytes(self.store.root, value.capture).decode())
        workspace.verify_capture(capture)
        spec = PreparationSpec.from_json(read_bytes(self.store.root, value.configuration).decode())
        if (
            spec.run_digest != self.store.spec.digest
            or spec.qualification_digest != self.qualification_digest
        ):
            raise StoreError("preparation source or qualification identity changed")
        return workspace, capture, spec

    def _commit(self, value):
        with self.store.writer():
            return self.store.commit(replace(value, recorded_at=self.broker.scheduler.clock()))

    def _private(self, record, name):
        with self.store.writer():
            return self.store.put_private(
                record.to_json().encode(), name=name, media_type="application/json"
            )

    def prepare(self, *, baseline: bytes, specification: InterfaceSpec):
        """Obtain one source response, capture it, then run or reconcile its checks."""
        controller = self.broker.controller
        state, projection = controller.state(), controller.store.replay()
        if (
            projection.state != "candidate_pending"
            or controller.spec.baseline.parameters
            or controller.spec.calibration
        ):
            raise StoreError("initial source preparation requires a pending parameterless proposal")
        if len(controller.spec.baseline.model.implementations) != 1 or (
            specification.inputs != controller.spec.baseline.model.inputs
            or specification.outputs != controller.spec.baseline.model.outputs
        ):
            raise StoreError("public interface differs from the initial single-component campaign")
        proposal = next(p for p in state.proposals if p.id == state.active_candidate)
        preparation_id = action_id("source", proposal.id)
        policy = WorkspacePolicy(
            "1.0", max_bytes=min(65536, (self.store.spec.limits.workspace_bytes - 4096) // 5)
        )
        config = PreparationSpec(
            "1.0",
            self.store.spec.digest,
            proposal.digest,
            projection.revision,
            projection.head_hash,
            hashlib.sha256(baseline).hexdigest(),
            specification,
            self.qualification_digest,
            policy,
            len(specification.cases),
        )
        directory = self.store.root / "preparations" / preparation_id
        with self.store.operation():
            parent = self.store.root / "preparations"
            parent.mkdir(mode=0o700, exist_ok=True)
            checked_directory(parent)
            directory.mkdir(mode=0o700, exist_ok=True)
            checked_directory(directory)
            path = directory / "configuration.json"
            if path.exists():
                if PreparationSpec.from_json(_read(directory, path.name)) != config:
                    raise StoreError("preparation configuration changed")
            else:
                durable_write(path, config.to_json().encode())
            workspace_root = directory / "workspace"
            if not workspace_root.exists():
                # Publish a complete relative workspace atomically. Interrupted
                # staging directories remain preserved and cannot authorize work.
                staged = directory / f".workspace-{uuid.uuid4().hex}"
                CandidateWorkspace.create(
                    staged,
                    run_id=self.store.spec.id,
                    task_id=action_id("implementer", f"source-{proposal.id}"),
                    baseline={"adapter.py": baseline},
                    policy=policy,
                )
                staged.rename(workspace_root)
                sync_directory(directory)
            workspace = CandidateWorkspace(
                workspace_root, WorkspaceManifest.from_json(_read(workspace_root, "manifest.json"))
            )
        existing = self.store.replay().preparations.get(preparation_id)
        if existing is None:
            self.broker._coordinate(f"source-implement-{proposal.id}", "implementer")

            def validate(handoff):
                draft = handoff.output
                if (
                    not isinstance(draft, SourceDraft)
                    or draft.base_snapshot != workspace.manifest.digest
                ):
                    raise ValueError("source response differs from its reserved baseline")
                if len(draft.files["adapter.py"].encode()) > policy.max_bytes:
                    raise ValueError("source response exceeds the reserved workspace")

            handoff = self.broker._role(
                "implementer",
                f"source-{proposal.id}",
                "Return only the permitted adapter source. Do not claim checks or admission.",
                candidate_id=proposal.id,
                expected_schema="role-handoff-1.1",
                context={
                    "proposal": proposal.to_dict(),
                    "base_snapshot": workspace.manifest.digest,
                    "baseline": baseline.decode("utf-8"),
                    "policy": policy.to_dict(),
                    "public_interface": specification.to_dict(),
                },
                validate=validate,
            )
            with self.store.operation():
                existing = self.store.replay().preparations.get(preparation_id)
                if existing is None:
                    if controller.store.replay().head_hash != config.parent_head:
                        raise StoreError(
                            "originating scientific proposal changed during preparation"
                        )
                    durable_write(
                        workspace.candidate / "adapter.py",
                        handoff.output.files["adapter.py"].encode(),
                        replace=True,
                    )
                    capture = workspace.capture()
                    existing = self._commit(
                        ImplementationPreparation(
                            "1.0",
                            preparation_id,
                            self.store.spec.id,
                            handoff.task_id,
                            handoff.invocation_id,
                            proposal.id,
                            proposal.digest,
                            handoff.output.digest,
                            str(workspace.root.relative_to(self.store.root)),
                            self._private(config, "preparation-spec.json"),
                            self._private(capture, "source-capture.json"),
                            "captured",
                            "source_captured_before_checks",
                        )
                    )
        return self.check(existing.id)

    def _finish(self, value, workspace, capture, config, receipt):
        output = workspace.root.parent / "interface"
        verified = verify_interface(
            output,
            workspace,
            capture,
            config.specification,
            qualification_root=self.qualification_root,
            qualification_digest=self.qualification_digest,
            expected_receipt_digest=receipt.digest,
        )
        interface = self._private(verified, "interface-receipt.json")
        if verified.status != "pass":
            return self._commit(
                replace(
                    value,
                    state="reconciliation_required"
                    if verified.status == "reconciliation_required"
                    else "failed",
                    reason=verified.status,
                    interface=interface,
                )
            )
        bundle_root = workspace.root.parent / "bundle"
        bundle_root.mkdir(mode=0o700, exist_ok=True)
        checked_directory(bundle_root)
        files = {
            "adapter.py": read_bytes(
                workspace.root, capture.sources["adapter.py"], max_bytes=65536
            ),
            "patch.diff": read_bytes(workspace.root, capture.patch, max_bytes=65536),
            "interface.json": verified.to_json().encode(),
            "qualification.json": confined_file(
                self.qualification_root, "qualification.json"
            ).read_bytes(),
        }
        for name, raw in files.items():
            path = bundle_root / name
            if path.exists():
                if confined_file(bundle_root, name).read_bytes() != raw:
                    raise StoreError("prepared implementation evidence changed")
            else:
                durable_write(path, raw)

        def ref(name):
            return reference(
                bundle_root,
                name,
                media_type="application/octet-stream",
                producer="trusted-preparation",
            )

        bundle = ImplementationBundle(
            capture.base_snapshot,
            ref("patch.diff"),
            (ref("adapter.py"),),
            ("adapter.py",),
            config.policy.dependencies,
            (ref("interface.json"),),
            ref("qualification.json"),
            None,
        )
        return self._commit(
            replace(
                value,
                state="checked",
                reason="trusted_public_interface_passed",
                interface=interface,
                bundle=self._private(bundle, "implementation-bundle.json"),
            )
        )

    @serialized_operation
    def check(self, preparation_id):
        value = self._current(preparation_id)
        workspace, capture, config = self._workspace(value)
        if value.state not in ("captured", "checking", "reconciliation_required"):
            return value
        output = workspace.root.parent / "interface"
        if value.state != "captured":
            return self._recover(value, workspace, capture, config)
        if capture.issues or capture.patch.size_bytes > 65536:
            return self._commit(
                replace(
                    value,
                    state="failed",
                    reason=(
                        "source_policy:" + ",".join(capture.issues or ("patch_allowance_exceeded",))
                    )[:2048],
                )
            )
        try:
            self.broker._require_time()
        except StoreError:
            return self._commit(
                replace(value, state="failed", reason="cancelled_or_expired_before_checks")
            )
        value = self._commit(
            replace(value, state="checking", reason="interface_allowance_reserved")
        )
        try:
            with self.broker._deadline():
                receipt = check_interface(
                    workspace,
                    capture,
                    config.specification,
                    qualification_root=self.qualification_root,
                    qualification_digest=self.qualification_digest,
                    output=output,
                    cancelled=self.broker.scheduler._cancelled,
                )
            return self._finish(value, workspace, capture, config, receipt)
        except (ValueError, OSError, TypeError):
            return self._commit(
                replace(
                    value,
                    state="reconciliation_required" if output.exists() else "failed",
                    reason="interface_interrupted" if output.exists() else "interface_not_launched",
                )
            )

    def _recover(self, value, workspace, capture, config):
        """The operation lease excludes a live owner. Never repeat an interface start."""
        output = workspace.root.parent / "interface"
        if not output.exists():
            return self._commit(
                replace(value, state="failed", reason="interrupted_before_checks_not_repeated")
            )
        sources = _sources(workspace, capture)
        qualified = verify_qualification(
            self.qualification_root, expected_digest=self.qualification_digest
        )
        manifest = unique_json(_read(output, "manifest.json"))
        if manifest != _manifest(capture, config.specification, qualified, sources, str(output)):
            raise StoreError("interrupted interface manifest changed")
        checks, complete = [], True
        for index, case in enumerate(config.specification.cases):
            root = output / f"case-{index:03d}"
            if checks and checks[-1].status != "pass":
                if root.exists():
                    raise StoreError("unexpected interface execution after a failed case")
                checks.append(
                    InterfaceCheck(case.id, "not_attempted", "earlier_case_did_not_pass", None)
                )
                continue
            if not root.exists():
                complete = False
                continue
            try:
                physical = reconcile_container(
                    root,
                    qualification_root=self.qualification_root,
                    qualification_digest=self.qualification_digest,
                    sources=sources,
                    payload=canonical_json(
                        {"schema_version": "1.0", "inputs": case.to_dict()["inputs"]}
                    ).encode(),
                    stop=True,
                )
                if not physical.stopped:
                    if value.state == "reconciliation_required":
                        return value
                    return self._commit(
                        replace(
                            value,
                            state="reconciliation_required",
                            reason="interface_stop_unverified",
                        )
                    )
                if physical.result_digest is None:
                    complete = False
                    continue
                raw = unique_json(_read(root, "result.json"))
                result = ContainerResult(
                    physical.result_status,
                    physical.container_id,
                    physical.stdout,
                    b"",
                    True,
                    raw["oom_killed"],
                    raw["elapsed_seconds"],
                    physical.result_digest,
                )
                status, reason = _check_result(result, case, config.specification)
                checks.append(InterfaceCheck(case.id, status, reason, physical.result_digest))
            except (ValueError, OSError, KeyError, TypeError):
                if value.state == "reconciliation_required":
                    return value
                return self._commit(
                    replace(
                        value, state="reconciliation_required", reason="interface_stop_unverified"
                    )
                )
        if not complete or len(checks) != len(config.specification.cases):
            return self._commit(
                replace(value, state="failed", reason="interrupted_checks_not_repeated")
            )
        receipt = InterfaceReceipt(
            "1.0",
            capture.source_digest,
            capture.digest,
            config.specification.digest,
            self.qualification_digest,
            runner_identity(),
            "pass" if all(c.status == "pass" for c in checks) else "fail",
            tuple(checks),
        )
        path = output / "receipt.json"
        if path.exists():
            if InterfaceReceipt.from_json(_read(output, path.name)) != receipt:
                raise StoreError("saved interface receipt contradicts recovered execution")
        else:
            durable_write(path, (receipt.to_json() + "\n").encode())
        return self._finish(value, workspace, capture, config, receipt)

    @serialized_operation
    def register(self, preparation_id, *, review, trusted_review_digest: str, output: Path):
        """Separate trusted approval. No worker operation exposes this method."""
        from .admission import register_candidate
        from autoengineering.adapters.registration import load_registration

        value = self._current(preparation_id)
        if self.broker.scheduler._cancelled():
            raise StoreError("cancelled preparation cannot publish an admission")
        workspace, capture, config = self._workspace(value)
        if review.digest != trusted_review_digest or review.decision != "approve":
            raise StoreError("preparation requires a separately pinned approval")
        proposal = next(
            p for p in self.broker.controller.state().proposals if p.digest == value.proposal_digest
        )
        if review.target != proposal.target or review.capture_digest != capture.digest:
            raise StoreError("admission review differs from the originating source proposal")
        if value.state not in ("checked", "registered", "forked"):
            raise StoreError("source preparation is not eligible for registration")
        if value.state in ("registered", "forked"):
            registration, _ = load_registration(
                output, expected_identity=value.registration_identity
            )
            if registration.review != review:
                raise StoreError("registered review changed")
            return registration
        if output.exists():
            from autoengineering.adapters.registration import SourceRegistration

            registration = SourceRegistration.from_json(
                _read(output / "generated", "registration.json")
            )
            load_registration(output, expected_identity=registration.digest)
            if (
                registration.review != review
                or registration.capture != capture
                or registration.specification != config.specification
            ):
                raise StoreError("existing registration differs from the pending admission")
        else:
            registration = register_candidate(
                workspace,
                capture,
                config.specification,
                interface_root=workspace.root.parent / "interface",
                qualification_root=self.qualification_root,
                review=review,
                trusted_review_digest=trusted_review_digest,
                output=output,
            )
        self._commit(
            replace(
                value,
                state="registered",
                reason="trusted_review_registered_exact_source",
                registration_identity=registration.digest,
                admission=self._private(registration, "admitted-registration.json"),
            )
        )
        return registration

    @serialized_operation
    def fork(self, preparation_id, *, registration_root: Path, name: str, execution, output: Path):
        """Create, but do not execute, a new campaign under an explicit new budget."""
        from autoengineering.adapters.registration import load_registration
        from autoengineering.campaign.controller import CampaignController
        from autoengineering.campaign.execution import pending_cancellations
        from autoengineering.campaign.identity import (
            scientific_source_paths,
            scientific_identity,
            verify_runtime_sources,
        )
        from autoengineering.campaign.records import ArtifactRef
        from autoengineering.campaign.spec import InterventionSpec, CampaignSpec, ExecutionSpec

        value = self._current(preparation_id)
        if value.state not in ("registered", "forked"):
            raise StoreError("a fork requires separate trusted registration")
        registration_root, output = Path(registration_root).absolute(), Path(output).absolute()
        registration, generated = load_registration(
            registration_root, expected_identity=value.registration_identity
        )
        parent = self.broker.controller
        original, state, projection = parent.spec, parent.state(), parent.store.replay()
        # A new source profile may add isolation helpers, but must not silently
        # replace the engine that defined the originating baseline and rules.
        verify_runtime_sources(original)
        if self.broker.scheduler._cancelled() or pending_cancellations(
            parent.store.root, original.name
        ):
            raise StoreError("cancelled origin cannot create a successor campaign")
        workspace, capture, config = self._workspace(value)
        if (
            projection.head_hash != config.parent_head
            or state.active_candidate != value.candidate_id
            or state.budget.unresolved_attempts
            or original.baseline.parameters
            or original.calibration
            or any(a.startswith("generated-") for a in original.execution.adapter_ids)
        ):
            raise StoreError(
                "originating proposal is not a stable parameterless source preparation"
            )
        if (
            name == original.name
            or not isinstance(execution, ExecutionSpec)
            or execution.adapter_ids != (original.baseline.adapter_id, registration.adapter_id)
        ):
            raise StoreError("successor requires a new name and explicit matching execution budget")
        if (
            registration.capture != capture
            or registration.review.interface_digest
            != InterfaceReceipt.from_json(
                read_bytes(self.store.root, value.interface).decode()
            ).digest
        ):
            raise StoreError("registered source differs from the checked preparation")
        proposal = next(p for p in state.proposals if p.digest == value.proposal_digest)
        handoff = self.broker.scheduler.handoff(
            self.store.replay().invocations[value.invocation_id]
        )
        link = {
            "schema_version": "1.0",
            "originating_campaign_identity": self.store.spec.campaign_identity,
            "originating_specification_digest": original.digest,
            "originating_head": config.parent_head,
            "originating_proposal": proposal.to_dict(),
            "originating_physical_attempts": len(state.budget.attempts),
            "worker_run_digest": self.store.spec.digest,
            "preparation_id": value.id,
            "handoff_digest": handoff.digest,
            "capture_digest": capture.digest,
            "interface_digest": registration.interface_receipt.digest,
            "review_digest": registration.review.digest,
            "registration_identity": registration.digest,
        }
        link_raw = canonical_json(link).encode()
        origin = ArtifactRef(
            "generated/origin.json",
            hashlib.sha256(link_raw).hexdigest(),
            len(link_raw),
            "application/json",
            "trusted-source-fork",
            {},
        )
        package = Path(__file__).resolve().parents[1]
        engine = tuple(
            replace(
                reference(
                    package,
                    path.removeprefix("src/autoengineering/"),
                    media_type="application/octet-stream",
                    producer="trusted-source-fork",
                ),
                path=path,
            )
            for path in scientific_source_paths(version="2")
        )
        old_sources = tuple(
            ref
            for ref in original.provenance.sources
            if not ref.path.startswith("src/autoengineering/")
        )
        sources = (*old_sources, *engine, *generated, origin)
        successor = replace(
            original,
            name=name,
            source_bundle=f"linked-source-{registration.digest[:24]}",
            baseline=replace(
                original.baseline, model=replace(original.baseline.model, source_bundle=sources)
            ),
            provenance=replace(original.provenance, sources=sources),
            execution=execution,
            interventions=(
                InterventionSpec(
                    proposal.target,
                    (
                        original.baseline.model.implementations[proposal.target],
                        registration.adapter_id,
                    ),
                    {},
                ),
            ),
        )
        intent = {
            "schema_version": "1.0",
            "successor_specification": successor.digest,
            "origin": origin.sha256,
            "execution": execution.to_dict(),
            "name": name,
        }
        checked_directory(output.parent)
        if output.is_symlink():
            raise StoreError("fork directory cannot be a symlink")
        output.mkdir(mode=0o700, exist_ok=True)
        checked_directory(output)
        intent_path = output / "fork-intent.json"
        if intent_path.exists():
            if unique_json(_read(output, intent_path.name)) != intent:
                raise StoreError("successor intent cannot change on recovery")
        else:
            if any(output.iterdir()):
                raise StoreError("successor requires a fresh directory")
            durable_write(intent_path, canonical_json(intent).encode())
        source = output / "source"
        source.mkdir(mode=0o700, exist_ok=True)
        checked_directory(source)
        copies = [
            (
                parent.bundle,
                (
                    original.baseline.system,
                    original.provenance.environment_lock,
                    *old_sources,
                    *(data.artifact for data in original.data),
                ),
            ),
            (registration_root, generated),
        ]
        payloads = {origin.path: link_raw}
        for root, refs in copies:
            for ref in refs:
                raw = read_bytes(root, ref)
                if ref.path in payloads and payloads[ref.path] != raw:
                    raise StoreError("successor has conflicting artifact paths")
                payloads[ref.path] = raw
        for ref in engine:
            payloads[ref.path] = read_bytes(
                package, replace(ref, path=ref.path.removeprefix("src/autoengineering/"))
            )
        for relative, raw in payloads.items():
            target = source / relative
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            checked_directory(target.parent)
            if target.exists():
                if confined_file(source, relative).read_bytes() != raw:
                    raise StoreError("successor artifact changed during recovery")
            else:
                durable_write(target, raw)
        identity = scientific_identity(successor, source)
        path = output / "campaign.yaml"
        if path.exists():
            if CampaignSpec.from_yaml(confined_file(output, path.name)) != successor:
                raise StoreError("successor specification changed")
        else:
            successor.to_yaml(path)
        campaign = output / "campaign"
        if campaign.exists():
            controller = CampaignController.open(campaign)
            if controller.spec != successor:
                raise StoreError("successor campaign changed")
        else:
            staged = output / f".campaign-{uuid.uuid4().hex}"
            CampaignController.create(path, source, staged)
            staged.rename(campaign)
            sync_directory(output)
            controller = CampaignController.open(campaign)
        record = {
            "schema_version": "1.0",
            "preparation_id": value.id,
            "origin": link,
            "successor_identity": identity,
            "successor_specification_digest": successor.digest,
            "campaign_path": str(campaign),
            "new_execution_budget": execution.to_dict(),
            "scientific_starts_during_fork": 0,
        }
        raw = canonical_json(record).encode()
        receipt = output / "fork-receipt.json"
        if receipt.exists():
            if confined_file(output, receipt.name).read_bytes() != raw:
                raise StoreError("successor receipt changed")
        else:
            durable_write(receipt, raw)
        if value.state == "forked":
            if (
                read_bytes(self.store.root, value.fork) != raw
                or value.successor_identity != identity
            ):
                raise StoreError("fork acknowledgment differs from its committed identity")
        else:
            with self.store.writer():
                ref = self.store.put_private(
                    raw, name="campaign-fork.json", media_type="application/json"
                )
                self.store.commit(
                    replace(
                        value,
                        state="forked",
                        reason="new_frozen_campaign_created_without_execution",
                        fork=ref,
                        successor_identity=identity,
                        recorded_at=self.broker.scheduler.clock(),
                    )
                )
        return controller
