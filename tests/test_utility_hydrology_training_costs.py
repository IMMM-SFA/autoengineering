"""Offline training costs preserve attempts, unknown work and artifact binding."""

from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
import json
import shutil
import subprocess
import sys

import pytest

from autoengineering.campaign.artifacts import put_bytes, reference
from autoengineering.campaign.serialization import canonical_json
from autoengineering.utility.costs import reconcile
from autoengineering.utility.hydrology_training import (
    RoutingFit,
    RoutingTrainingProfile,
    TrainingIntent,
    TrainingWork,
    read_training_costs,
)


def fixture(root):
    (root / "artifacts").mkdir(mode=0o700)
    profile = RoutingTrainingProfile(
        tuple((date(2000, 1, 1) + timedelta(days=i)).isoformat() for i in range(20)),
        0,
        (True,) * 20,
        30,
    )
    intent = TrainingIntent(
        "learned-routing-training-intent-v2", "training-" + "a" * 32, "1" * 64, 17, 30, 20
    )
    fit = RoutingFit("1" * 64, "2" * 64, "3" * 64, (-1.0, 1.0), 17, 5, 100, 1, 0.2, "authored")
    artifact = put_bytes(
        root,
        fit.to_json().encode(),
        name="routing-fit.json",
        media_type="application/json",
        producer="authored",
    )
    work = TrainingWork(
        "learned-routing-training-result-v2",
        intent.training_id,
        intent.identity,
        "trained",
        0.3,
        5,
        100,
        5,
        100,
        False,
        1,
        1,
        False,
        artifact,
    )
    return profile, intent, work


def refs(root, intent, work):
    for name, value in (("intent", intent), ("result", work)):
        if value is not None:
            (root / (name + ".json")).write_text(
                value.to_json() if hasattr(value, "to_json") else canonical_json(value)
            )

    def ref(name):
        return reference(root, name + ".json", media_type="application/json", producer="authored")

    return ref("intent"), None if work is None else ref("result")


def read(root, profile, intent_ref, work_ref):
    return read_training_costs(
        root,
        intent_ref,
        work_ref,
        identity="1" * 64,
        profile=profile,
        seed=17,
        cell_digest="4" * 64,
    )


def test_trained_costs_and_duplicate_charging(tmp_path):
    profile, intent, work = fixture(tmp_path)
    records = read(tmp_path, profile, *refs(tmp_path, intent, work))
    values = {r.resource: r.quantity for r in records}
    assert values["training_starts"] == 1 and values["training_routing_starts"] == 5
    assert values["training_completed_routing_days"] == 100
    assert values["training_elapsed"] == 0.3
    assert reconcile(records, tuple(r.receipt_id for r in records))["complete"]
    with pytest.raises(ValueError, match="duplicate physical"):
        reconcile((*records, *records), tuple(r.receipt_id for r in records))
    other = replace(intent, training_id="training-" + "b" * 32)
    repeated = read(
        tmp_path, profile, *refs(tmp_path, other, replace(work, training_id=other.training_id))
    )
    combined = (*records, *repeated)
    result = reconcile(combined, tuple(r.receipt_id for r in combined))
    assert result["complete"]
    assert (
        next(v["quantity"] for v in result["known_totals"] if v["resource"] == "training_starts")
        == 2
    )


def test_missing_result_preserves_one_intent_and_unknown_quantities(tmp_path):
    profile, intent, _ = fixture(tmp_path)
    records = read(tmp_path, profile, *refs(tmp_path, intent, None))
    assert records[0].quantity == 1 and all(r.quantity is None for r in records[1:])
    assert not reconcile(records, tuple(r.receipt_id for r in records))["complete"]


def test_partial_failure_is_neither_zero_work_nor_a_completed_fit(tmp_path):
    profile, intent, work = fixture(tmp_path)
    work = replace(
        work,
        status="failed",
        trained_artifact=None,
        completed_routing_rollouts=4,
        completed_routing_days=80,
        partial_routing_work_unknown=True,
    )
    records = read(tmp_path, profile, *refs(tmp_path, intent, work))
    values = {r.resource: r.quantity for r in records}
    assert values["training_routing_starts"] == 5 and values["training_routing_completions"] == 4
    assert values["training_partial_routing_days"] is None
    assert not reconcile(records, tuple(r.receipt_id for r in records))["complete"]


@pytest.mark.parametrize(
    "change",
    [
        {"training_id": "another"},
        {"identity": "0" * 64},
        {"routing_rollouts": 31},
        {"completed_routing_days": 99},
        {"reserved_routing_days": 99},
        {"completed_routing_rollouts": 6},
        {"partial_routing_work_unknown": True},
        {"flux_preparation_runs": 0},
        {"training_seconds": 0.1},
        {"routing_rollouts": True},
        {"unknown": 1},
        {"schema": "learned-routing-training-result-v1"},
    ],
)
def test_rehashed_inconsistent_result_refuses(tmp_path, change):
    profile, intent, work = fixture(tmp_path)
    with pytest.raises(ValueError):
        read(tmp_path, profile, *refs(tmp_path, intent, work.to_dict() | change))


def test_expected_seed_limits_identity_and_artifact_integrity(tmp_path):
    profile, intent, work = fixture(tmp_path)
    i, r = refs(tmp_path, intent, work)
    for kwargs in (
        {"seed": 18},
        {"seed": True},
        {"identity": "0" * 64},
        {"profile": replace(profile, max_rollouts=31)},
    ):
        options = dict(identity="1" * 64, profile=profile, seed=17, cell_digest="4" * 64) | kwargs
        with pytest.raises(ValueError):
            read_training_costs(tmp_path, i, r, **options)
    (tmp_path / work.trained_artifact.path).write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        read(tmp_path, profile, i, r)


def test_actual_fit_reconstructs_from_relocated_artifacts_without_models(tmp_path):
    from test_utility_hydrology_learned import fixture as model_fixture, fit

    site, profile, ctx, forcing, data, _ = model_fixture(tmp_path)
    result = fit(site, profile, ctx, forcing, data)
    root = Path(ctx.scratch_path)
    i = reference(root, "training-intent.json", media_type="application/json", producer="training")
    r = reference(root, "training-result.json", media_type="application/json", producer="training")
    work = TrainingWork.from_json((root / r.path).read_text())
    intent = TrainingIntent.from_json((root / i.path).read_text())
    again = tmp_path / "repeat"
    again.mkdir(mode=0o700)
    site2, profile2, ctx2, forcing2, data2, _ = model_fixture(again)
    fit(site2, profile2, ctx2, forcing2, data2)
    intent2 = TrainingIntent.from_json(
        (Path(ctx2.scratch_path) / "training-intent.json").read_text()
    )
    assert intent2.identity == intent.identity and intent2.training_id != intent.training_id
    copied = tmp_path / "copied"
    copied.mkdir(mode=0o700)
    for ref in (i, r, result.training.artifact):
        target = copied / ref.path
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copyfile(root / ref.path, target)
    request = {
        "root": str(copied),
        "intent": i.to_dict(),
        "result": r.to_dict(),
        "profile": profile.to_dict(),
        "identity": intent.identity,
        "seed": ctx.seed,
    }
    script = """
import importlib.abc,json,sys
class NoModels(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in {'examples','torch','openmdao','pvlib','py_wake'}:
            raise AssertionError('model import')
sys.meta_path.insert(0,NoModels())
from pathlib import Path
from autoengineering.campaign.records import ArtifactRef
from autoengineering.utility.hydrology_training import RoutingTrainingProfile,read_training_costs
import subprocess,socket,scipy.optimize,os
def forbidden(*args,**kwargs): raise AssertionError('execution attempted')
subprocess.Popen=socket.socket=forbidden
scipy.optimize.least_squares=scipy.optimize.minimize=forbidden
x=json.loads(sys.argv[1]);root=Path(x['root'])
allowed={root/x['intent']['path'],root/x['result']['path']}
work=json.loads((root/x['result']['path']).read_bytes())
allowed.add(root/work['trained_artifact']['path'])
original=Path.open
def guarded(path,*args,**kwargs):
    if path not in allowed: raise AssertionError('read outside relocated artifacts')
    return original(path,*args,**kwargs)
Path.open=guarded
original_os_open=os.open
def guarded_os_open(path,flags,*args,**kwargs):
    if Path(path) not in allowed or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT):
        raise AssertionError('read outside relocated artifacts or attempted write')
    return original_os_open(path,flags,*args,**kwargs)
os.open=guarded_os_open
records=read_training_costs(root,ArtifactRef.from_dict(x['intent']),ArtifactRef.from_dict(x['result']),
    identity=x['identity'],profile=RoutingTrainingProfile.from_dict(x['profile']),seed=x['seed'],cell_digest='4'*64)
print(json.dumps({r.resource:r.quantity for r in records}))
"""
    process = subprocess.run(
        [sys.executable, "-c", script, json.dumps(request)],
        text=True,
        capture_output=True,
        timeout=20,
        check=True,
    )
    values = json.loads(process.stdout)
    assert values["training_routing_starts"] == result.training.cost == work.routing_rollouts
    assert values["training_elapsed"] == work.training_seconds
