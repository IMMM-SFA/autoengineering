"""Composite metadata is verified before any reserved driver or label access."""

from dataclasses import replace
from datetime import date, timedelta
import json
import subprocess
import sys

import pytest

from autoengineering.campaign.artifacts import put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef, DataContract
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import StoreError
from autoengineering.utility.confirmation import read_selected_state, freeze
from autoengineering.utility.contracts import ResourceCap, ScoredTaskSpec
from autoengineering.utility.execution import ScriptedCoordinator
from autoengineering.utility.inference_contracts import FrozenRoutingInference
from autoengineering.utility.outcomes import OutcomeSpec
from autoengineering.utility.scoring import (
    ConfirmationGrant,
    CompositeConfirmationGrant,
    ConfirmationService,
    validate_grant,
)
from autoengineering.utility.store import SuiteStore
from test_utility_contracts import H
from test_utility_trained_execution import setup


def prepared(tmp_path, monkeypatch, *, details=False):
    original, plan, source = setup(tmp_path, monkeypatch, routes=("baseline",))
    contract = OutcomeSpec("engineering-outcome-v1", "rmse", "mm/day", "minimize", "mean", H)
    task = ScoredTaskSpec.from_dict(
        original.spec.tasks[0].to_dict()
        | {
            "schema": "utility-task-scoring-v2",
            "scoring_outcome_digest": contract.digest,
            "required_capabilities": ["frozen_trained_inference", "protected_frozen_routing_score"],
        }
    )
    budget = replace(
        original.spec.budgets[0],
        confirmation_reserve=(
            ResourceCap("scientific_starts", "count", 2, "reservation"),
            ResourceCap("active_time", "s", 128, "reservation"),
        ),
    )
    routes, cells = plan.routes.expand((task,), (budget,))
    store = SuiteStore.create(
        tmp_path / "composite",
        replace(original.spec, tasks=(task,), budgets=(budget,), routes=routes, cells=cells),
    )
    coordinator = ScriptedCoordinator(store, plan, source)
    coordinator.run()
    manifest = coordinator.selection_manifest()
    freeze(store, manifest)
    cell = manifest.cells[0]
    bound = read_selected_state(store.root, cell.selected_state)
    profile = json.loads((source / "routing-runtime.json").read_text())
    profile["selected_state"] = cell.selected_state.to_dict()
    runtime = put_bytes(
        store.root,
        canonical_json(profile).encode(),
        name="routing-runtime.json",
        media_type="application/json",
        producer="author",
    )
    old = bound.model.inputs[0].time
    end = date.fromisoformat(old.dates[-1])
    dates = old.dates + tuple((end + timedelta(days=i)).isoformat() for i in range(1, 21))
    ports = tuple(
        replace(
            p,
            time=replace(
                p.time,
                dates=dates,
                warmup_mask=p.time.warmup_mask + (False,) * 20,
                scoring_mask=(False,) * len(old.dates) + (True,) * 20,
            ),
        )
        for p in bound.model.inputs
    )
    forcing = DataContract(
        "reserved-drivers",
        ArtifactRef("reserved/drivers.npz", H, 1000, "application/x-npz", "author", {}),
        ports,
        "forcing",
        "unexposed",
    )
    replay = FrozenRoutingInference(
        "utility-frozen-routing-inference-v1",
        cell.selected_state,
        runtime,
        forcing,
        int(bound.evaluation.provenance["execution_seed"]),
        20,
        8388608,
    )
    grant = CompositeConfirmationGrant(
        store.spec.digest,
        cell.cell_digest,
        task.partition_digest,
        H,
        contract.digest,
        cell.model.sha256,
        store.replay()["frozen"],
        (
            ResourceCap("scientific_starts", "count", 2, "reservation"),
            ResourceCap("active_time", "s", 94, "reservation"),
        ),
        "utility-confirmation-grant-v2",
        replay,
    )
    if details:
        return store, grant, contract, plan, source
    return store, grant, contract


def test_composite_metadata_roundtrip_and_vector_service_refusal_before_access(
    tmp_path, monkeypatch
):
    store, grant, outcome = prepared(tmp_path, monkeypatch)
    assert ConfirmationGrant.from_json(grant.to_json()) == grant
    assert isinstance(ConfirmationGrant.from_json(grant.to_json()), CompositeConfirmationGrant)
    assert validate_grant(store, grant, store.replay()["frozen"]).model.sha256 == grant.model_digest
    assert not (store.root / grant.inference.forcing.artifact.path).exists()
    calls = []
    service = ConfirmationService(
        store, lambda *_a: calls.append(1), scorer_digest=H, outcome_contract=outcome
    )
    before = store.replay()
    for operation in (service.confirm, service.recover):
        with pytest.raises(StoreError, match="vector-only"):
            operation(grant)
        assert store.replay() == before
    assert not calls and not before["confirmation_accesses"]
    assert not before["confirmation_scores"]


def test_changed_seed_axis_units_or_runtime_refuses_without_driver_reads(tmp_path, monkeypatch):
    store, grant, _ = prepared(tmp_path, monkeypatch)
    replay = grant.inference
    first = replay.forcing.ports[0]
    shifted = tuple(
        (date.fromisoformat(d) + timedelta(days=1)).isoformat() for d in first.time.dates
    )
    variants = [
        replace(replay, seed=replay.seed + 1),
        replace(replay, selected_state=replace(replay.selected_state, sha256="3" * 64)),
        replace(
            replay,
            forcing=replace(
                replay.forcing, ports=(replace(first, units="m"), *replay.forcing.ports[1:])
            ),
        ),
        replace(
            replay,
            forcing=replace(
                replay.forcing,
                ports=tuple(
                    replace(p, time=replace(p.time, dates=shifted)) for p in replay.forcing.ports
                ),
            ),
        ),
        replace(
            replay,
            forcing=replace(
                replay.forcing,
                ports=tuple(
                    replace(p, time=replace(p.time, warmup_mask=(False,) * len(p.time.dates)))
                    for p in replay.forcing.ports
                ),
            ),
        ),
    ]
    for variant in variants:
        with pytest.raises(ValueError):
            validate_grant(store, replace(grant, inference=variant), store.replay()["frozen"])
    document = json.loads(read_bytes(store.root, replay.runtime_profile))
    document["site"]["latitude_deg"] = 41.0
    wrong = put_bytes(
        store.root,
        canonical_json(document).encode(),
        name="runtime.json",
        media_type="application/json",
        producer="author",
    )
    with pytest.raises(ValueError, match="original fit"):
        validate_grant(
            store,
            replace(grant, inference=replace(replay, runtime_profile=wrong)),
            store.replay()["frozen"],
        )
    assert not store.replay()["confirmation_accesses"]


def test_two_stage_resources_are_explicit_and_bounded(tmp_path, monkeypatch):
    _, grant, _ = prepared(tmp_path, monkeypatch)
    for change in ("starts_one", "starts_three", "time", "training", "hosts"):
        resources = list(grant.resources)
        if change.startswith("starts"):
            resources[0] = replace(resources[0], limit=1 if change == "starts_one" else 3)
        elif change == "time":
            resources[1] = replace(resources[1], limit=93)
        else:
            resources.append(
                ResourceCap(
                    "training_starts" if change == "training" else "host_invocations",
                    "count",
                    1,
                    "reservation",
                )
            )
        with pytest.raises(ValueError):
            replace(grant, resources=tuple(resources))


def test_legacy_grant_keeps_exact_fields_bytes_and_one_start():
    raw = {
        name: H
        for name in (
            "suite_digest",
            "cell_digest",
            "partition_digest",
            "scorer_digest",
            "outcome_digest",
            "model_digest",
            "selection_digest",
        )
    }
    raw["resources"] = [ResourceCap("scientific_starts", "count", 1, "reservation").to_dict()]
    legacy = ConfirmationGrant.from_dict(raw)
    assert type(legacy) is ConfirmationGrant and legacy.to_json() == canonical_json(raw)
    with pytest.raises(ValueError):
        ConfirmationGrant.from_dict(raw | {"schema": "unknown-v3"})
    with pytest.raises(ValueError):
        replace(legacy, resources=(ResourceCap("scientific_starts", "count", 2, "reservation"),))


def test_composite_access_keeps_two_reservations_and_rejects_legacy_score_receipt(
    tmp_path, monkeypatch
):
    from autoengineering.utility.scoring import ConfirmationReceipt, PublicScore

    store, grant, contract = prepared(tmp_path, monkeypatch)
    attempt = "confirmation-" + grant.cell_digest[:48]
    arguments = dict(
        cell_digest=grant.cell_digest,
        attempt_id=attempt,
        child_digest=grant.digest,
        phase="confirmation",
    )
    with store.writer():
        store.append(
            request_id="authored-reserve",
            operation="reserve",
            resources=grant.resources,
            **arguments,
        )
        store.append(request_id="authored-start", operation="start", **arguments)
        ref = put_bytes(
            store.root,
            grant.to_json().encode(),
            name="confirmation-grant.json",
            media_type="application/json",
            producer="author",
        )
        store.append(
            request_id="authored-access",
            operation="confirmation_access",
            result_digest=ref.sha256,
            **arguments,
        )
        receipt = ConfirmationReceipt(
            grant.digest, ref.sha256, PublicScore("success", "rmse", "mm/day", 0.0, True), contract
        )
        score = put_bytes(
            store.root,
            receipt.to_json().encode(),
            name="confirmation-score.json",
            media_type="application/json",
            producer="author",
        )
        with pytest.raises(StoreError, match="two-stage execution"):
            store.append(
                request_id="authored-rejected-score",
                operation="confirmation_score",
                result_digest=score.sha256,
                **arguments,
            )
    state = store.replay()
    assert state["phase_used"][("fixed_evaluations", "confirmation", "scientific_starts")] == 2
    assert len(state["confirmation_accesses"]) == 1 and not state["confirmation_scores"]


def test_cold_validation_reads_no_arrays_or_models_and_executes_nothing(tmp_path, monkeypatch):
    store, grant, _ = prepared(tmp_path, monkeypatch)
    script = """
import importlib.abc,json,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,*args):
  if fullname.split('.')[0] in {'examples','torch','openmdao','pvlib','py_wake'}:raise AssertionError('model import')
sys.meta_path.insert(0,NoModels())
from pathlib import Path
from autoengineering.utility.scoring import ConfirmationGrant,validate_grant
from autoengineering.utility.store import SuiteStore
import scipy.optimize,subprocess,socket,os
def forbidden(*args,**kwargs):raise AssertionError('execution attempted')
scipy.optimize.least_squares=scipy.optimize.minimize=subprocess.Popen=socket.socket=forbidden
root=Path(sys.argv[1]);allowed={p for p in root.rglob('*') if p.is_file() and p.suffix!='.npz'}
old=Path.open;old_os=os.open
def guarded(path,*args,**kwargs):
 if path not in allowed:raise AssertionError('ungranted read')
 return old(path,*args,**kwargs)
def guarded_os(path,flags,*args,**kwargs):
 if Path(path) not in allowed or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT):raise AssertionError('ungranted read/write')
 return old_os(path,flags,*args,**kwargs)
Path.open=guarded;os.open=guarded_os
grant=ConfirmationGrant.from_json(sys.argv[2]);store=SuiteStore(root)
print(validate_grant(store,grant,store.replay()['frozen']).model.sha256)
"""
    process = subprocess.run(
        [sys.executable, "-c", script, str(store.root), grant.to_json()],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert process.stdout.strip() == grant.model_digest
