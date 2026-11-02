"""Source-bound attempt ownership, without a live Docker daemon."""

from dataclasses import replace
import json
from types import SimpleNamespace

import numpy as np
import pytest

from autoengineering.agents.container_recovery import ContainerRecovery
from autoengineering.campaign import container_execution as module
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.controller import CampaignController
from test_agent_admission import stage, context
from test_agent_interface import run as run


@pytest.fixture
def attempt(run, tmp_path):
    registration, bundle = stage(run, tmp_path)
    root = tmp_path / "campaign"
    root.mkdir(mode=0o700)
    (root / "artifacts").mkdir(mode=0o700)
    bundle.rename(root / "bundle")
    (root / "jobs").mkdir(mode=0o700)
    (root / "attempts").mkdir(mode=0o700)
    attempt_id, nonce = "attempt-000001", "a" * 32
    (root / "attempts" / attempt_id).mkdir(mode=0o700)
    scratch = module.scratch_path(root, attempt_id, nonce)
    ctx = replace(context(registration, root / "bundle", tmp_path), scratch_path=str(scratch))
    (root / "bundle/forcing.json").write_text('{"forcing":1.5}')
    forcing_ref = reference(
        root / "bundle", "forcing.json", media_type="application/json", producer="fixture"
    )
    job = {
        "attempt_id": attempt_id,
        "nonce": nonce,
        "adapter_id": registration.adapter_id,
        "bundle_root": str(root / "bundle"),
        "output_path": str(root / "jobs" / f"{attempt_id}.npz"),
        "forcing": forcing_ref.to_dict(),
        "forcing_root": str(root / "bundle"),
        "context": ctx.to_dict(),
    }
    return SimpleNamespace(
        root=root, job=job, id=attempt_id, nonce=nonce, scratch=scratch, context=ctx
    )


def reserve_execution(attempt):
    attempt.scratch.mkdir(mode=0o700)
    handle = attempt.scratch / ("isolated-" + "e" * 32)
    handle.mkdir(mode=0o700)
    execution = handle / "execution"
    execution.mkdir(mode=0o700)
    declaration = {"nonce": "b" * 32, "image_id": "sha256:" + "c" * 64}
    (execution / "intent.json").write_text(json.dumps(declaration))
    (execution / "container-id").write_text("d" * 64)
    receipt = {
        "container_id": "d" * 64,
        "nonce": declaration["nonce"],
        "intent_digest": digest(declaration),
        "image_id": declaration["image_id"],
    }
    return execution, receipt


def reconcile(attempt, **kwargs):
    return module.reconcile_attempt(
        attempt.root, attempt.job, attempt_id=attempt.id, nonce=attempt.nonce, **kwargs
    )


def bind(attempt, execution, receipt):
    observe = module.launch_observer(
        attempt.root, attempt.job, attempt_id=attempt.id, nonce=attempt.nonce
    )
    observe(execution, receipt)
    return observe


def test_callback_commits_binding_before_container_start_and_never_replaces_it(attempt):
    execution, receipt = reserve_execution(attempt)
    observe = bind(attempt, execution, receipt)
    path = attempt.root / "attempts" / attempt.id / "container-launch.json"
    binding = json.loads(path.read_text())
    assert binding["attempt_nonce"] == attempt.nonce
    assert binding["container_id"] == receipt["container_id"]
    assert binding["execution_path"] == str(execution.relative_to(attempt.root))
    with pytest.raises(FileExistsError):
        observe(execution, receipt)


@pytest.mark.parametrize(
    "field,value",
    [
        ("nonce", "f" * 32),
        ("bundle_root", "/wrong"),
        ("attempt_id", "another-attempt"),
        ("output_path", "/wrong"),
    ],
)
def test_changed_outer_job_cannot_bind_a_container(attempt, field, value):
    attempt.job[field] = value
    with pytest.raises(ValueError, match="reserved"):
        reconcile(attempt, stop=True)


def test_absent_execution_proves_no_launch_only_after_the_owner_has_stopped(attempt):
    proof = reconcile(attempt)
    assert proof.stopped and proof.no_launch and proof.physical is None
    with pytest.raises(ValueError, match="no recovered"):
        proof.outputs(attempt.context.model.outputs)
    attempt.scratch.mkdir(mode=0o700)
    assert reconcile(attempt).no_launch
    handle = attempt.scratch / ("isolated-" + "e" * 32)
    handle.mkdir(mode=0o700)
    assert reconcile(attempt).no_launch


def test_binding_without_execution_cannot_be_relabelled_as_no_launch(attempt):
    execution, receipt = reserve_execution(attempt)
    bind(attempt, execution, receipt)
    execution.rename(execution.parent / "missing")
    with pytest.raises(ValueError, match="disappeared"):
        reconcile(attempt)


def test_ambiguous_workspace_cannot_choose_a_convenient_execution(attempt):
    reserve_execution(attempt)
    (attempt.scratch / ("isolated-" + "f" * 32)).mkdir(mode=0o700)
    with pytest.raises(ValueError, match="ambiguous"):
        reconcile(attempt)


def test_bound_success_reconstructs_forcing_and_outputs_without_importing_source(
    attempt, monkeypatch
):
    execution, receipt = reserve_execution(attempt)
    bind(attempt, execution, receipt)
    calls = []

    def physical(root, **kwargs):
        calls.append(kwargs)
        assert root == execution
        assert set(kwargs["sources"]) == {"adapter.py", "driver.py"}
        assert json.loads(kwargs["payload"]) == {
            "schema_version": "1.0",
            "inputs": {"forcing": 1.5},
        }
        assert not kwargs["stop"]
        raw = b'{"schema_version":"1.0","inputs_unchanged":true,"outputs":{"prediction":3.0}}'
        return ContainerRecovery(
            receipt["container_id"],
            receipt["nonce"],
            receipt["intent_digest"],
            True,
            True,
            False,
            "f" * 64,
            "success",
            raw,
        )

    monkeypatch.setattr(module, "reconcile_container", physical)
    proof = reconcile(attempt)
    assert proof.stopped and proof.binding_digest
    assert np.array_equal(
        proof.outputs(attempt.context.model.outputs)["prediction"], np.asarray(3.0)
    )
    assert len(calls) == 1


def test_changed_binding_cannot_signal_even_a_matching_physical_container(attempt, monkeypatch):
    execution, receipt = reserve_execution(attempt)
    bind(attempt, execution, receipt)
    path = attempt.root / "attempts" / attempt.id / "container-launch.json"
    binding = json.loads(path.read_text())
    binding["container_id"] = "9" * 64
    path.write_text(json.dumps(binding))
    monkeypatch.setattr(
        module,
        "reconcile_container",
        lambda *a, **k: pytest.fail("must validate binding before signal"),
    )
    with pytest.raises(ValueError, match="identity differs"):
        reconcile(attempt, stop=True)


def test_incomplete_creation_is_unresolved_instead_of_no_launch(attempt, monkeypatch):
    reserve_execution(attempt)
    monkeypatch.setattr(
        module,
        "reconcile_container",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("missing immutable ID")),
    )
    with pytest.raises(ValueError, match="missing immutable"):
        reconcile(attempt, stop=True)


def test_recovery_without_durable_binding_cannot_supply_a_scientific_result():
    proof = module.IsolatedAttemptRecovery(
        True,
        False,
        "execution",
        ContainerRecovery(
            "d" * 64, "b" * 32, "e" * 64, True, True, False, "f" * 64, "success", b"{}"
        ),
    )
    with pytest.raises(ValueError, match="no recovered"):
        proof.outputs(())


def controller_proof(attempt, monkeypatch, *, live=()):
    from autoengineering.campaign import execution

    (attempt.root / "attempts" / attempt.id / "process.json").write_text(
        json.dumps({"pid": 98765, "pgid": 98765, "nonce": attempt.nonce, "started": "fixture"})
    )
    monkeypatch.setattr(execution, "live_members", lambda group: live)
    controller = object.__new__(CampaignController)
    controller.store = SimpleNamespace(root=attempt.root)
    controller.spec = SimpleNamespace(
        execution=SimpleNamespace(adapter_ids=(attempt.job["adapter_id"],))
    )
    return controller, SimpleNamespace(id=attempt.id, launch_nonce=attempt.nonce)


def test_controller_refuses_inner_access_until_native_owner_is_stopped(attempt, monkeypatch):
    controller, record = controller_proof(attempt, monkeypatch, live=(98765,))
    monkeypatch.setattr(
        module, "reconcile_attempt", lambda *a, **k: pytest.fail("native owner still alive")
    )
    with pytest.raises(ValueError, match="native owner stop"):
        controller._isolated_proof(record, job=attempt.job, stop=True)


def test_controller_does_not_accept_native_outputs_without_matching_container_output(
    attempt, monkeypatch
):
    controller, record = controller_proof(attempt, monkeypatch)
    raw = b'{"schema_version":"1.0","inputs_unchanged":true,"outputs":{"prediction":3.0}}'
    physical = ContainerRecovery(
        "d" * 64, "b" * 32, "e" * 64, True, True, False, "f" * 64, "success", raw
    )
    proof = module.IsolatedAttemptRecovery(True, False, "execution", physical, "9" * 64)
    monkeypatch.setattr(module, "reconcile_attempt", lambda *a, **k: proof)
    with pytest.raises(ValueError, match="native outputs differ"):
        controller._isolated_proof(record, job=attempt.job, outputs={"prediction": np.asarray(4.0)})
    recovered, receipt = controller._isolated_proof(
        record, job=attempt.job, outputs={"prediction": np.asarray(3.0)}
    )
    assert recovered == proof
    assert receipt.producer == "controller"
    assert receipt.size_bytes > 0


def test_controller_requires_the_frozen_registered_catalogue(attempt, monkeypatch):
    controller, record = controller_proof(attempt, monkeypatch)
    controller.spec.execution.adapter_ids = ("linear",)
    monkeypatch.setattr(
        module, "reconcile_attempt", lambda *a, **k: pytest.fail("adapter not admitted")
    )
    with pytest.raises(ValueError, match="frozen catalogue"):
        controller._isolated_proof(record, job=attempt.job)


def test_controller_preserves_uncertainty_if_inner_stop_is_unresolved(attempt, monkeypatch):
    controller, record = controller_proof(attempt, monkeypatch)
    job_path = attempt.root / "jobs" / f"{attempt.id}.json"
    job_path.write_text(json.dumps(attempt.job))
    proof = module.IsolatedAttemptRecovery(False, False, "execution", None, "9" * 64)
    monkeypatch.setattr(module, "reconcile_attempt", lambda *a, **k: proof)
    stopped, receipts = controller._stop_unresolved((record,))
    assert not stopped and len(receipts) == 1


def test_generated_registry_requires_v2_parameterless_frozen_profile(attempt):
    from autoengineering.campaign.runtime import registry
    from examples.agent_campaign.fixture import agent_fixture

    native = agent_fixture()
    spec = replace(
        native,
        execution=replace(native.execution, adapter_ids=("linear", attempt.job["adapter_id"])),
    )
    with pytest.raises(ValueError, match="version 2"):
        registry(spec=spec, root=attempt.root / "bundle")
    with pytest.raises(ValueError, match="not registered"):
        registry().create(attempt.job["adapter_id"])


def test_missing_generated_job_cannot_be_manually_reconciled_as_stopped(attempt, monkeypatch):
    from autoengineering.campaign.service import CampaignError

    controller, record = controller_proof(attempt, monkeypatch)
    record.state = "uncertain"
    state = SimpleNamespace(budget=SimpleNamespace(attempts=(record,)))
    request = SimpleNamespace(payload={"reconcile_attempt_id": record.id})
    with pytest.raises(CampaignError, match="reconciliation_required"):
        controller._reconcile(request, state)
