"""Real supervised authored training with committed cost reconstruction.

The helper's application-owned adapter injection is declared test source.
It is not a public runtime registration or an independent/private task admission.
"""

from dataclasses import replace
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

from autoengineering.agents.batch import BatchCase, BatchStore
from autoengineering.agents.batch_science import BatchCampaignController
from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.records import DataContract
from autoengineering.campaign.spec import (
    BaselineSpec,
    ExecutionSpec,
    InterventionSpec,
    TrainingSpec,
)
from autoengineering.utility.campaign_costs import join_campaign_costs
from autoengineering.utility.costs import reconcile
from autoengineering.utility.hydrology_training import TrainingWork

CELL = "1" * 64

HELPER = """
import json,sys
from pathlib import Path
from dataclasses import replace
import numpy as np
from autoengineering.adapters.contracts import PrepareContext,TrainingArtifactBundle
from autoengineering.campaign.artifacts import read_arrays,read_bytes,put_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.spec import CampaignSpec
from autoengineering.campaign import model_worker as worker
from autoengineering.utility.hydrology_training import RoutingTrainingProfile
from examples.utility.hydrology_site import HydrologySite
from examples.utility.hydrology_learned import LearnedRoutingAdapter,load_training
path=Path(sys.argv[1]);job=json.loads(path.read_text());root=Path(job['bundle_root'])
spec=CampaignSpec.from_yaml(path.parent.parent/'campaign.yaml')
config=json.loads((root/'authored-config.json').read_text())
site=HydrologySite.from_dict(config['site']);profile=RoutingTrainingProfile.from_dict(config['profile'])
context=PrepareContext.from_dict(job['context'])
frozen=None
if config['frozen'] is not None:
 ref=ArtifactRef.from_dict(config['frozen'])
 frozen=load_training(root,ref)
 bundle_ref=ArtifactRef.from_json(ref.metadata['training_bundle'])
 bundle=TrainingArtifactBundle.from_json(read_bytes(root,bundle_ref).decode())
 scratch=Path(context.scratch_path);(scratch/'artifacts').mkdir(mode=0o700,exist_ok=True)
 for item in (bundle.primary,*bundle.companions,bundle_ref):
  saved=put_bytes(scratch,read_bytes(root,item),name=Path(item.path).name,
      media_type=item.media_type,producer=item.producer)
  assert saved.path==item.path
 import scipy.optimize
 def forbidden(*args,**kwargs):raise AssertionError('frozen helper retrained')
 scipy.optimize.least_squares=forbidden
original_registry=worker.registry()
class Registry:
 def validate(self,*args):original_registry.validate(*args)
 def create(self,adapter_id):
  original_registry.create(adapter_id)
  return LearnedRoutingAdapter(site,profile,frozen)
worker.registry=lambda:Registry()
worker.main(path)
"""


def setup(
    tmp_path,
    monkeypatch,
    *,
    frozen=False,
    reject=False,
    recover=False,
    science=1,
    registered=False,
    cap=120,
    timeout=20,
    run=True,
    on_create=None,
):
    from test_utility_hydrology_learned import fixture, fit
    from test_agent_batch import specification
    from examples.campaign_contracts.build_fixture import fixture as campaign_fixture, ROOT
    import autoengineering.campaign.controller as module

    site, profile, ctx, forcing, data, truth = fixture(tmp_path, cap=cap)
    prepared = fit(site, profile, ctx, forcing, data) if frozen else None
    base = campaign_fixture()
    source = tmp_path / "source"
    source.mkdir(mode=0o700)
    sources = {r.path: r for r in (*base.provenance.sources, *ctx.model.source_bundle)}
    for ref in (*sources.values(), base.baseline.system, base.provenance.environment_lock):
        target = source / ref.path
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_bytes(read_bytes(ROOT, ref))

    def array_file(name, arrays):
        stream = io.BytesIO()
        np.savez(stream, **arrays)
        (source / name).write_bytes(stream.getvalue())
        return reference(source, name, media_type="application/x-npz", producer="author")

    driver = array_file("forcing.npz", forcing)
    labels = array_file("comparison.npz", {"prediction": truth})
    fitting = array_file("fitting.npz", {"prediction": data["labels"]})
    extra = []
    adapter_id = "hydrology"
    if registered:
        from examples.utility.hydrology_runtime import (
            ADAPTER_ID,
            PROFILE_PATH,
            RoutingRuntimeProfile,
        )

        assert not frozen
        adapter_id = ADAPTER_ID
        (source / PROFILE_PATH).write_text(
            RoutingRuntimeProfile("utility-routing-runtime-v1", site, profile, None).to_json()
        )
        extra.append(
            reference(source, PROFILE_PATH, media_type="application/json", producer="author")
        )
    if frozen:
        from autoengineering.adapters.contracts import TrainingArtifactBundle
        from autoengineering.campaign.records import ArtifactRef

        bundle_ref = ArtifactRef.from_json(prepared.training.artifact.metadata["training_bundle"])
        bundle = TrainingArtifactBundle.from_json(
            read_bytes(Path(ctx.scratch_path), bundle_ref).decode()
        )
        for ref in (bundle.primary, *bundle.companions, bundle_ref):
            target = source / ref.path
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            target.write_bytes(read_bytes(Path(ctx.scratch_path), ref))
            extra.append(ref)
    config = {
        "site": site.to_dict(),
        "profile": profile.to_dict(),
        "frozen": None if prepared is None else prepared.training.artifact.to_dict(),
    }
    (source / "authored-config.json").write_text(json.dumps(config))
    (source / "authored-helper.py").write_text(HELPER)
    (source / "control").mkdir(mode=0o700)
    (source / "control/launcher.py").write_text(
        "from pathlib import Path\nimport runpy,sys\n"
        "from autoengineering.campaign.runtime import RUNTIME_ROOT\n"
        "sys.path.insert(0,str(RUNTIME_ROOT))\n"
        "job=Path(sys.argv[1])\n"
        "runpy.run_path(str(job.parent.parent/'bundle/authored-helper.py'),run_name='__main__')\n"
    )
    extra.extend(
        reference(source, name, media_type=kind, producer="author")
        for name, kind in (
            ("authored-config.json", "application/json"),
            ("authored-helper.py", "text/x-python"),
            ("control/launcher.py", "text/x-python"),
        )
    )
    output = next(p for p in ctx.model.outputs if p.name == "prediction")
    prefix = replace(
        output,
        time=replace(
            output.time,
            dates=profile.fitting_dates,
            warmup_mask=output.time.warmup_mask[: len(profile.fitting_dates)],
            scoring_mask=profile.valid_mask,
        ),
    )
    checks = base.acceptance.checks
    if reject:
        from autoengineering.campaign.spec import CheckSpec

        checks = (*checks, CheckSpec("nonnegative", "1", True, "outputs", {"tolerance": -1.0}))
    spec = replace(
        base,
        schema_version="1.0" if frozen else "1.1",
        training=None
        if frozen
        else TrainingSpec("daily-prefix-supervised-v1", (adapter_id,), "fitting"),
        name="authored-routing-accounting",
        scientific_scope="Authored daily routing training accounting fixture",
        baseline=BaselineSpec(base.baseline.system, ctx.model, adapter_id, ctx.parameters),
        data=(
            DataContract("forcing", driver, ctx.model.inputs, "forcing", "exposed"),
            DataContract("fitting", fitting, (prefix,), "fitting", "exposed"),
            DataContract("comparison", labels, (output,), "comparison", "exposed"),
        ),
        interventions=(InterventionSpec("routing", ("logistic-storage-release-v1",), {}),),
        execution=ExecutionSpec((adapter_id,), timeout_seconds=timeout),
        acceptance=replace(base.acceptance, checks=checks),
        provenance=replace(
            base.provenance,
            sources=tuple(sources.values()) + tuple(extra),
            expected_outputs=ctx.model.outputs,
        ),
    )
    path = source / "campaign.yaml"
    spec.to_yaml(path)
    batch = BatchStore.create(
        tmp_path / "batch",
        replace(
            specification(science=science),
            cases=(BatchCase("model", "comparison", CELL, 0, science),),
        ),
    )
    batch.start_case("model", CELL)
    case = batch.root / "cases/model"
    case.mkdir(mode=0o700)
    controller = BatchCampaignController.create(
        path, source, case / "campaign", batch=batch, case_id="model"
    )
    if on_create is not None:
        on_create(batch, controller)
    original = module.supervise

    def authored(command, **kwargs):
        job = Path(command[-1])
        return original(
            (command[0], str(controller.bundle / "control/launcher.py"), str(job)), **kwargs
        )

    if not registered:
        monkeypatch.setattr(module, "supervise", authored)
    if not run:
        return batch, controller
    if recover:
        checkpoint = controller._checkpoint

        class AuthoredLoss(BaseException):
            pass

        def lost(target, state, reason, artifacts=()):
            if reason == "action_finished":
                raise AuthoredLoss()
            return checkpoint(target, state, reason, artifacts)

        monkeypatch.setattr(controller, "_checkpoint", lost)
        with pytest.raises(AuthoredLoss):
            controller.advance()
        monkeypatch.setattr(controller, "_checkpoint", checkpoint)

        def forbidden(*args, **kwargs):
            raise AssertionError("recovery relaunched science")

        monkeypatch.setattr(module, "supervise", forbidden)
        controller.reconcile_batch()
    else:
        controller.remaining = 1
        controller.advance()
    return batch, controller


@pytest.mark.parametrize("recover", [False, True])
def test_actual_supervised_fit_projects_only_its_committed_original_work(
    tmp_path, monkeypatch, recover
):
    batch, controller = setup(tmp_path, monkeypatch, recover=recover)
    assert len(controller.state().budget.attempts) == 1
    assert controller.state().evaluations[0].status == "success"
    costs = join_campaign_costs(batch, {"model": CELL})
    values = {r.resource: r.quantity for r in costs}
    assert values["campaign_process_starts"] == values["training_starts"] == 1
    assert 3 <= values["training_routing_starts"] <= 120
    assert values["training_completed_routing_days"] == 80 * values["training_routing_starts"]
    work_ref = next(
        r
        for event in controller.store.replay().events
        for r in event.artifacts
        if r.path.endswith("/training-result.json")
    )
    work = TrainingWork.from_json(read_bytes(controller.store.root, work_ref).decode())
    assert values["training_elapsed"] == work.training_seconds
    assert reconcile(costs, tuple(r.receipt_id for r in costs))["complete"]
    assert join_campaign_costs(batch, {"model": CELL}) == costs
    assert batch.report()["scientific_reservations_charged"] == 1


def test_successful_training_cost_is_retained_when_scientific_checks_reject_the_model(
    tmp_path, monkeypatch
):
    batch, controller = setup(tmp_path, monkeypatch, reject=True)
    assert not controller.state().evaluations[0].eligible
    costs = join_campaign_costs(batch, {"model": CELL})
    assert next(r.quantity for r in costs if r.resource == "training_starts") == 1


def test_frozen_inference_does_not_claim_free_or_repeated_training(tmp_path, monkeypatch):
    batch, controller = setup(tmp_path, monkeypatch, frozen=True)
    assert controller.state().evaluations[0].status == "success"
    costs = join_campaign_costs(batch, {"model": CELL})
    values = {r.resource: r.quantity for r in costs}
    assert "training_starts" not in values
    assert values["frozen_fit_inference_reuses"] == 1
    assert values["unverified_training_preparation"] is None
    assert not reconcile(costs, tuple(r.receipt_id for r in costs))["complete"]


def test_cold_relocated_cost_reader_needs_only_committed_public_evidence(tmp_path, monkeypatch):
    batch, controller = setup(tmp_path, monkeypatch)
    expected = join_campaign_costs(batch, {"model": CELL})
    copied = tmp_path / "copied"
    shutil.copytree(batch.root, copied)
    campaign = copied / controller.store.root.relative_to(batch.root)
    # Mutable scratch and projection caches cannot supply training authority.
    shutil.rmtree(campaign / "jobs")
    # Source modules, forcing and fitting/comparison labels are unnecessary.
    shutil.rmtree(campaign / "bundle")
    (campaign / "state.json").write_text("invalid projection cache")
    script = """
import importlib.abc,json,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,*args):
  if fullname.split('.')[0] in {'examples','torch','openmdao','pvlib','py_wake'}:raise AssertionError('model import')
sys.meta_path.insert(0,NoModels())
from pathlib import Path
from autoengineering.agents.batch import BatchStore
from autoengineering.utility.campaign_costs import join_campaign_costs
import scipy.optimize,subprocess,socket,os
def forbidden(*args,**kwargs):raise AssertionError('execution attempted')
scipy.optimize.least_squares=scipy.optimize.minimize=subprocess.Popen=socket.socket=forbidden
root=Path(sys.argv[1]);allowed={p for p in root.rglob('*') if p.is_file()}
old=Path.open;old_os=os.open
def guarded(path,*args,**kwargs):
 if path not in allowed:raise AssertionError('ungranted read')
 return old(path,*args,**kwargs)
def guarded_os(path,flags,*args,**kwargs):
 if Path(path) not in allowed or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT):raise AssertionError('ungranted read/write')
 return old_os(path,flags,*args,**kwargs)
Path.open=guarded;os.open=guarded_os
print(json.dumps([r.to_dict() for r in join_campaign_costs(BatchStore(root),{'model':'1'*64})],sort_keys=True))
"""
    process = subprocess.run(
        [sys.executable, "-c", script, str(copied)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert json.loads(process.stdout) == [r.to_dict() for r in expected]


def test_committed_training_closure_corruption_refuses_cost_reconstruction(tmp_path, monkeypatch):
    batch, controller = setup(tmp_path, monkeypatch)
    expected = join_campaign_costs(batch, {"model": CELL})
    refs = {
        Path(r.path).name: r
        for event in controller.store.replay().events
        for r in event.artifacts
        if Path(r.path).name
        in {
            "training-profile.json",
            "training-intent.json",
            "training-result.json",
            "training-bundle.json",
            "routing-fit.json",
            "lifecycle.json",
        }
    }
    assert {
        "training-profile.json",
        "training-intent.json",
        "training-result.json",
        "training-bundle.json",
        "routing-fit.json",
        "lifecycle.json",
    } == set(refs)
    for ref in refs.values():
        path = controller.store.root / ref.path
        original = path.read_bytes()
        path.write_bytes(b"corrupt committed training evidence")
        try:
            with pytest.raises(ValueError):
                join_campaign_costs(batch, {"model": CELL})
        finally:
            path.write_bytes(original)
    assert join_campaign_costs(batch, {"model": CELL}) == expected


def test_training_cannot_borrow_closure_from_a_later_event(tmp_path, monkeypatch):
    from autoengineering.utility.campaign_costs import _campaign, _training
    from autoengineering.campaign.store import StoreError

    batch, _ = setup(tmp_path, monkeypatch)
    observation = next(iter(batch.replay().observations.values()))
    document = json.loads(read_bytes(batch.root, observation.evidence[0]))
    campaign = _campaign(batch, "model", document)
    index = next(
        i
        for i, event in enumerate(campaign.events)
        if any(r.path.endswith("/training-profile.json") for r in event.artifacts)
    )
    original = campaign.events[index]
    incomplete = replace(
        original,
        artifacts=tuple(
            r for r in original.artifacts if not r.path.endswith("/training-profile.json")
        ),
    )
    events = (*campaign.events[:index], incomplete, *campaign.events[index + 1 :], original)
    with pytest.raises(StoreError, match="original lifecycle commit"):
        _training(replace(campaign, events=events), observation, document, CELL)
