"""Parent-bounded dispatch through existing child batch accounting.

Only a caller-supplied trusted runner executes a case. No provider or scientific
factory is selected here. A lost dispatch requires evidence reconciliation, never
an automatic replay of the runner.
"""
from __future__ import annotations

from dataclasses import dataclass

from autoengineering.campaign.artifacts import (
    confined_file, put_bytes, read_bytes, reference,
)
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, digest, unique_json
from autoengineering.campaign.store import StoreError, durable_write
from .contracts import ResourceCap, identifier, sha256
from .store import SuiteStore


@dataclass(frozen=True)
class CaseBinding(Record):
    cell_digest: str
    case_id: str
    training_starts: int = 0
    training_routing_starts: int = 0

    def _validate(self):
        sha256(self.cell_digest)
        identifier(self.case_id)
        if self.training_starts < 0 or self.training_routing_starts < 0:
            raise ValueError("training reservations must be nonnegative")
        if bool(self.training_starts) != bool(self.training_routing_starts):
            raise ValueError("routing training needs both start and inner-work reservations")

    def to_dict(self):
        result = super().to_dict()
        if not self.training_starts:
            result.pop("training_starts")
            result.pop("training_routing_starts")
        return result


class UtilityController:
    def __init__(self, store: SuiteStore):
        self.store = store

    def _binding(self, batch_spec, bindings):
        if {b.case_id for b in bindings} != {c.id for c in batch_spec.cases}:
            raise StoreError("binding must cover exactly the child cases")
        if len({b.cell_digest for b in bindings}) != len(bindings) or len(
                {b.case_id for b in bindings}) != len(bindings):
            raise StoreError("duplicate child binding")
        cells = {c.digest: c for c in self.store.spec.cells}
        routes = {r.route_id: r for r in self.store.spec.routes}
        for binding in bindings:
            cell = cells.get(binding.cell_digest)
            if cell is None:
                raise StoreError("unknown utility cell")
            case = next(c for c in batch_spec.cases if c.id == binding.case_id)
            if binding.training_starts > case.scientific_starts:
                raise StoreError("training reservation exceeds scientific attempt allowance")
            from .baseline_selection import follower_group
            follower = follower_group(self.store.spec, cell.digest)
            if (case.kind == "reference") != (follower is not None):
                raise StoreError("child reference kind differs from frozen baseline policy")
            if case.configuration_digest != routes[cell.route_id].configuration_digest:
                raise StoreError("child configuration differs from frozen route")
        return {"batch_spec": batch_spec.to_dict(),
                "bindings": [b.to_dict() for b in bindings]}

    def prepare_batch(self, batch_spec, bindings: tuple[CaseBinding, ...]):
        """Reserve all child allowances before creation. Preparation launches nothing."""
        from autoengineering.agents.batch import BatchStore

        document = self._binding(batch_spec, bindings)
        identity = digest(document)
        root = self.store.root / "children" / identity
        with self.store.writer():
            mapping = self.store.root / "children" / f"{identity}.json"
            if mapping.exists():
                if unique_json(confined_file(self.store.root, str(mapping.relative_to(
                        self.store.root))).read_text()) != document:
                    raise StoreError("child binding changed")
            else:
                durable_write(mapping, (record_json(document)).encode())
            self.store.fault("after_child_mapping")
            for binding in bindings:
                case = next(c for c in batch_spec.cases if c.id == binding.case_id)
                attempt = "child-" + binding.cell_digest[:48]
                self.store.append(
                    request_id="reserve-" + binding.cell_digest[:48], operation="reserve",
                    cell_digest=binding.cell_digest, attempt_id=attempt, child_digest=identity,
                    resources=(
                        ResourceCap("scientific_starts", "count", case.scientific_starts,
                                    "reservation"),
                        ResourceCap("host_invocations", "count", case.host_invocations,
                                    "reservation"),
                        ResourceCap("training_starts", "count",
                                    binding.training_starts, "reservation"),
                        *((ResourceCap("training_routing_starts", "count",
                            binding.training_routing_starts, "reservation"),)
                          if binding.training_routing_starts else ()),
                        ResourceCap("active_time", "s", batch_spec.limits.elapsed_seconds,
                                    "reservation"),
                    ))
            self.store.fault("after_parent_reservations")
            pin = self.store.root / "children" / f"{identity}-manifest.json"
            if root.exists():
                if not pin.exists():
                    raise StoreError("child creation interrupted before manifest pin; inspect required")
                child = BatchStore(root)
                if child.spec != batch_spec:
                    raise StoreError("existing child differs from prepared specification")
            else:
                child = BatchStore.create(root, batch_spec)
                self.store.fault("after_child_creation")
                manifest_ref = reference(root, "batch.json", media_type="application/json",
                                         producer="utility-preparation")
                durable_write(pin, record_json(manifest_ref.to_dict()).encode())
            self.store.fault("after_child_manifest_pin")
            manifest_ref = ArtifactRef.from_json(confined_file(
                self.store.root, str(pin.relative_to(self.store.root))).read_text())
            read_bytes(root, manifest_ref)
            return BatchStore(root, expected_digest=child.digest)

    def _child(self, identity):
        from autoengineering.agents.batch import BatchSpec, BatchStore

        sha256(identity)
        path = f"children/{identity}.json"
        document = unique_json(confined_file(self.store.root, path).read_text())
        if set(document) != {"batch_spec", "bindings"} or digest(document) != identity:
            raise StoreError("child mapping identity mismatch")
        spec = BatchSpec.from_dict(document["batch_spec"])
        bindings = tuple(CaseBinding.from_dict(b) for b in document["bindings"])
        self._binding(spec, bindings)
        child = BatchStore(self.store.root / "children" / identity)
        pin = ArtifactRef.from_json(confined_file(
            self.store.root, f"children/{identity}-manifest.json").read_text())
        read_bytes(child.root, pin)
        if child.spec != spec:
            raise StoreError("child specification changed")
        return BatchStore(child.root, expected_digest=child.digest), bindings

    def dispatch(self, identity, cell_digest, runner):
        """Run a reserved case once; runner must use child physical reservations."""
        with self.store.writer():
            child, bindings = self._child(identity)
            binding = next((b for b in bindings if b.cell_digest == cell_digest), None)
            if binding is None:
                raise StoreError("cell is not bound to child")
            attempt_id = "child-" + cell_digest[:48]
            allocation, state = self.store.replay()["attempts"][attempt_id]
            if allocation.child_digest != identity:
                raise StoreError("allocation child differs")
            if state == "finished":
                return self.verify_result(attempt_id)
            if state == "started":
                raise StoreError("dispatch uncertain; reconcile saved child evidence")
            self.store.append(request_id="start-" + cell_digest[:48], operation="start",
                              cell_digest=cell_digest, attempt_id=attempt_id, child_digest=identity)
            case = next(c for c in child.spec.cases if c.id == binding.case_id)
            child.start_case(case.id, case.configuration_digest)
            runner(child, case.id)
            return self._finish(child, binding, allocation)

    def _finish(self, child, binding, allocation):
        projection = child.replay()
        if binding.case_id not in projection.finished or projection.pending:
            raise StoreError("child lacks finished, fully reconciled evidence")
        refs = projection.finished[binding.case_id].evidence
        for ref in refs:
            read_bytes(child.root, ref)
        manifest = reference(child.root, "batch.json", media_type="application/json",
                             producer="utility-child")
        result = {"child_digest": allocation.child_digest, "cell_digest": binding.cell_digest,
                  "case_id": binding.case_id, "manifest": manifest.to_dict(),
                  "case_result": projection.finished[binding.case_id].to_dict()}
        from .baseline_selection import validate_reference_result
        prefix = self.store.replay()
        validate_reference_result(self.store, result, prefix["attempts"], prefix["events"])
        ref = put_bytes(self.store.root, record_json(result).encode(), name="child-result.json",
                        media_type="application/json", producer="utility-controller")
        self.store.append(request_id="finish-" + binding.cell_digest[:48], operation="finish",
                          cell_digest=binding.cell_digest, attempt_id=allocation.attempt_id,
                          child_digest=allocation.child_digest, result_digest=ref.sha256)
        return result

    def reconcile(self, identity, cell_digest):
        """Acknowledge committed child evidence without invoking a runner."""
        with self.store.writer():
            child, bindings = self._child(identity)
            binding = next(b for b in bindings if b.cell_digest == cell_digest)
            allocation, state = self.store.replay()["attempts"]["child-" + cell_digest[:48]]
            if allocation.child_digest != identity or state == "reserved":
                raise StoreError("no matching started dispatch")
            if state == "finished":
                return self.verify_result(allocation.attempt_id)
            return self._finish(child, binding, allocation)

    def verify_result(self, attempt_id):
        """Offline reconstruction verifies the child manifest and original evidence."""
        state = self.store.replay()
        return self._verify_result_prefix(attempt_id, state["attempts"], state["events"])

    def _verify_result_prefix(self, attempt_id, attempts, events):
        allocation, status = attempts[attempt_id]
        if status != "finished":
            raise StoreError("attempt has no committed result")
        finish = next(e for e in events if e.attempt_id == attempt_id
                      and e.operation == "finish")
        path = f"artifacts/{finish.result_digest}/child-result.json"
        ref = reference(self.store.root, path, media_type="application/json", producer="reader")
        if ref.sha256 != finish.result_digest:
            raise StoreError("child result digest mismatch")
        result = unique_json(read_bytes(self.store.root, ref).decode())
        child, bindings = self._child(allocation.child_digest)
        binding = next(b for b in bindings if b.cell_digest == allocation.cell_digest)
        read_bytes(child.root, ArtifactRef.from_dict(result["manifest"]))
        projection = child.replay()
        actual = projection.finished[binding.case_id]
        if (result["child_digest"] != allocation.child_digest
                or result["cell_digest"] != binding.cell_digest
                or result["case_id"] != binding.case_id or result["case_result"] != actual.to_dict()):
            raise StoreError("saved result differs from authoritative child")
        for evidence in actual.evidence:
            read_bytes(child.root, evidence)
        from .baseline_selection import validate_reference_result
        validate_reference_result(self.store, result, attempts, events)
        return result


def record_json(document):
    from autoengineering.campaign.serialization import canonical_json
    return canonical_json(document) + "\n"
