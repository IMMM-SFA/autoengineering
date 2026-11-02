"""Sealed training closure integrity, relocation and suite barrier tests."""

from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

from autoengineering.adapters.contracts import TrainingArtifactBundle
from autoengineering.campaign.artifacts import commit_worker_lifecycle, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef, EvaluationRecord
from autoengineering.campaign.serialization import canonical_json
from autoengineering.utility.confirmation import (
    SelectedState,
    TrainedSelectedState,
    read_selected_state,
)
from autoengineering.utility.trained_selection import RoutingSelectionArtifacts


def fixture(tmp_path):
    from test_utility_hydrology_learned import fixture as model_fixture, fit

    site, profile, ctx, forcing, data, _ = model_fixture(tmp_path)
    result = fit(site, profile, ctx, forcing, data)
    root = tmp_path / "parent"
    root.mkdir(mode=0o700)
    (root / "artifacts").mkdir(mode=0o700)
    stream = io.BytesIO()
    np.savez(stream, **result.outputs)
    raw = stream.getvalue()
    outputs = put_bytes(
        root, raw, name="outputs.npz", media_type="application/x-npz", producer="attempt-000001"
    )
    metadata = canonical_json(
        {
            "training": result.training.to_dict(),
            "elapsed_seconds": result.elapsed_seconds,
            "output_sha256": hashlib.sha256(raw).hexdigest(),
        }
    ).encode()
    captured = commit_worker_lifecycle(
        root,
        Path(ctx.scratch_path),
        metadata,
        output_sha256=outputs.sha256,
        producer="attempt-000001",
    )
    bundle_ref = ArtifactRef.from_json(result.training.artifact.metadata["training_bundle"])
    bundle = TrainingArtifactBundle.from_json(read_bytes(root, bundle_ref).decode())

    def companion(suffix):
        return next(r for r in bundle.companions if r.path.endswith("/" + suffix))

    training = RoutingSelectionArtifacts(
        "utility-routing-selection-artifacts-v1",
        bundle.primary,
        companion("training-profile.json"),
        companion("training-intent.json"),
        companion("training-result.json"),
        bundle_ref,
        captured[0],
    )
    evaluation = EvaluationRecord(
        "selected",
        ctx.model.digest,
        ctx.parameters,
        "success",
        {"rmse": 0.0},
        (),
        (outputs,),
        "selection",
        "attempt-000001",
        result.elapsed_seconds,
        {"execution_seed": "17", "lifecycle_record": captured[0].sha256},
    )
    bound = TrainedSelectedState(
        "utility-selected-state-v2", ctx.model, ctx.parameters, evaluation, training
    )
    return root, bound


def save(root, bound):
    return put_bytes(
        root,
        bound.to_json().encode(),
        name="selected-state.json",
        media_type="application/json",
        producer="selection",
    )


def test_roundtrip_frozen_fit_and_legacy_refusal(tmp_path):
    root, bound = fixture(tmp_path)
    ref = save(root, bound)
    assert read_selected_state(root, ref) == bound
    with pytest.raises(ValueError):
        SelectedState.from_json(bound.to_json())
    with pytest.raises(ValueError, match="trained selected-state"):
        SelectedState(
            "utility-selected-state-v1", bound.model, bound.configuration, bound.evaluation
        )
    with pytest.raises(ValueError):
        TrainedSelectedState.from_dict(
            {k: v for k, v in bound.to_dict().items() if k != "training"}
        )


@pytest.mark.parametrize("document", [[], None, 1, "invalid"])
def test_selected_state_reader_rejects_nonmapping_json(tmp_path, document):
    (tmp_path / "artifacts").mkdir(mode=0o700)
    ref = put_bytes(
        tmp_path,
        canonical_json(document).encode(),
        name="selected-state.json",
        media_type="application/json",
        producer="authored",
    )
    with pytest.raises(ValueError, match="mapping"):
        read_selected_state(tmp_path, ref)


@pytest.mark.parametrize("name", ["fit", "profile", "intent", "result", "bundle", "lifecycle"])
def test_every_training_artifact_is_digest_verified(tmp_path, name):
    root, bound = fixture(tmp_path)
    ref = save(root, bound)
    original = getattr(bound.training, name)
    (root / original.path).write_bytes((root / original.path).read_bytes() + b" ")
    with pytest.raises(ValueError):
        read_selected_state(root, ref)


@pytest.mark.parametrize(
    "change", ["configuration", "seed", "lifecycle", "output", "prefix", "units"]
)
def test_rehashed_state_cannot_reinterpret_a_fit(tmp_path, change):
    root, bound = fixture(tmp_path)
    if change == "configuration":
        parameters = dict(bound.configuration) | {"capacity": 101.0}
        bound = replace(
            bound,
            configuration=parameters,
            evaluation=replace(bound.evaluation, configuration=parameters),
        )
    elif change == "seed":
        bound = replace(
            bound,
            evaluation=replace(
                bound.evaluation,
                provenance=dict(bound.evaluation.provenance) | {"execution_seed": "18"},
            ),
        )
    elif change == "lifecycle":
        bound = replace(
            bound,
            training=replace(
                bound.training,
                lifecycle=replace(bound.training.lifecycle, producer="another-attempt"),
            ),
        )
    elif change == "output":
        bound = replace(bound, evaluation=replace(bound.evaluation, outputs=()))
    elif change == "units":
        model = replace(
            bound.model, inputs=(replace(bound.model.inputs[0], units="m"), *bound.model.inputs[1:])
        )
        bound = replace(
            bound, model=model, evaluation=replace(bound.evaluation, model_id=model.digest)
        )
    else:
        # Keep the model graph and source identity while shortening its clock.
        def crop(port):
            t = port.time
            return (
                port
                if t is None
                else replace(
                    port,
                    time=replace(
                        t,
                        dates=t.dates[:70],
                        warmup_mask=t.warmup_mask[:70],
                        scoring_mask=t.scoring_mask[:70],
                    ),
                )
            )

        model = replace(
            bound.model,
            inputs=tuple(map(crop, bound.model.inputs)),
            outputs=tuple(map(crop, bound.model.outputs)),
        )
        bound = replace(
            bound, model=model, evaluation=replace(bound.evaluation, model_id=model.digest)
        )
    with pytest.raises(ValueError):
        read_selected_state(root, save(root, bound))


def test_cold_reader_uses_only_copied_closure_without_training(tmp_path):
    root, bound = fixture(tmp_path)
    ref = save(root, bound)
    copied = tmp_path / "copied"
    copied.mkdir(mode=0o700)
    for artifact in (ref, *bound.training.references()):
        target = copied / artifact.path
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copyfile(root / artifact.path, target)
    script = """
import importlib.abc,json,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,*args):
  if fullname.split('.')[0] in {'examples','torch','openmdao','pvlib','py_wake'}:raise AssertionError('model import')
sys.meta_path.insert(0,NoModels())
from pathlib import Path
from autoengineering.campaign.records import ArtifactRef
from autoengineering.utility.confirmation import read_selected_state
import scipy.optimize,subprocess,socket,os
def forbidden(*args,**kwargs):raise AssertionError('execution attempted')
scipy.optimize.least_squares=scipy.optimize.minimize=subprocess.Popen=socket.socket=forbidden
x=json.loads(sys.argv[1]);root=Path(x['root']);allowed={root/p for p in x['allowed']}
old=Path.open;old_os=os.open
def guarded(path,*args,**kwargs):
 if path not in allowed:raise AssertionError('ungranted read')
 return old(path,*args,**kwargs)
def guarded_os(path,flags,*args,**kwargs):
 if Path(path) not in allowed or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT):raise AssertionError('ungranted read/write')
 return old_os(path,flags,*args,**kwargs)
Path.open=guarded;os.open=guarded_os
print(read_selected_state(root,ArtifactRef.from_dict(x['ref'])).digest)
"""
    request = {
        "root": str(copied),
        "ref": ref.to_dict(),
        "allowed": [r.path for r in (ref, *bound.training.references())],
    }
    process = subprocess.run(
        [sys.executable, "-c", script, json.dumps(request)],
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    assert process.stdout.strip() == bound.digest


@pytest.mark.parametrize("change", ["duration", "cost", "worker", "inference_cost"])
def test_rehashed_lifecycle_still_must_match_original_training(tmp_path, change):
    root, bound = fixture(tmp_path)
    document = json.loads(read_bytes(root, bound.training.lifecycle))
    if change == "duration":
        document["elapsed_seconds"] = 0.0
    elif change == "cost":
        document["training"]["cost"] += 1
        document["worker_training"]["cost"] += 1
    elif change == "worker":
        document["worker_training"]["cost"] += 1
    else:
        for field in ("training", "worker_training"):
            document[field]["status"] = "not_applicable"
            document[field]["cost"] = 0.0
    lifecycle = put_bytes(
        root,
        canonical_json(document).encode(),
        name="lifecycle.json",
        media_type="application/json",
        producer=bound.evaluation.attempt_id,
    )
    bound = replace(
        bound,
        training=replace(bound.training, lifecycle=lifecycle),
        evaluation=replace(
            bound.evaluation,
            provenance=dict(bound.evaluation.provenance) | {"lifecycle_record": lifecycle.sha256},
        ),
    )
    with pytest.raises(ValueError):
        read_selected_state(root, save(root, bound))


@pytest.mark.parametrize("mode", ["valid", "missing_capability", "wrong_seed", "wrong_family"])
def test_suite_archive_and_barrier_retain_the_complete_training_closure(tmp_path, mode):
    from autoengineering.utility.confirmation import SelectedCell, SelectionManifest, freeze
    from autoengineering.utility.controller import UtilityController, CaseBinding
    from autoengineering.utility.execution import archive_selected_state
    from autoengineering.utility.store import SuiteStore
    from test_utility_contracts import suite, H
    from test_agent_batch import specification

    root, bound = fixture(tmp_path)
    template = suite()
    spec = replace(
        template,
        tasks=(
            replace(
                template.tasks[0],
                family="engineering" if mode == "wrong_family" else "hydrology",
                candidate_digests=(bound.model.digest,),
                required_capabilities=()
                if mode == "missing_capability"
                else ("frozen_trained_inference",),
            ),
        ),
        cells=tuple(replace(c, seed=18 if mode == "wrong_seed" else 17) for c in template.cells),
    )
    store = SuiteStore.create(tmp_path / "suite", spec)
    batch = specification()
    batch = replace(batch, cases=tuple(replace(c, configuration_digest=H) for c in batch.cases))
    coordinator = UtilityController(store)
    child = coordinator.prepare_batch(
        batch, tuple(CaseBinding(c.digest, b.id) for c, b in zip(spec.cells, batch.cases))
    )
    source_root = Path(__file__).resolve().parents[1]
    selections = []

    def select(child, case):
        chosen, evidence = archive_selected_state(
            store, child, bound, source_root, training_root=root
        )
        selections.append(chosen)
        child.finish_case(case, "passed", evidence)

    for cell in spec.cells:
        coordinator.dispatch(child.root.name, cell.digest, select)
    choices = []
    for cell, chosen in zip(spec.cells, selections):
        attempt = "child-" + cell.digest[:48]
        event = next(
            e
            for e in store.replay()["events"]
            if e.operation == "finish" and e.attempt_id == attempt
        )
        choices.append(
            SelectedCell(
                cell.digest,
                "selected",
                attempt,
                event.result_digest,
                ArtifactRef.from_dict(chosen["model"]),
                "Authored trained selection closure",
                ArtifactRef.from_dict(chosen["selected_state"]),
            )
        )
    manifest = SelectionManifest(
        "utility-selection-v2", spec.digest, spec.protocol_digest, tuple(choices)
    )
    if mode != "valid":
        with pytest.raises(ValueError, match="seed|capability"):
            freeze(store, manifest)
        return
    identity = freeze(store, manifest)
    assert store.replay()["frozen"] == identity
    for artifact in bound.training.references():
        read_bytes(store.root, artifact)
    (store.root / bound.training.fit.path).write_bytes(b"tampered")
    with pytest.raises(ValueError):
        SuiteStore(store.root).replay()


def test_trained_baseline_references_keep_the_original_fit_seed(tmp_path):
    from types import SimpleNamespace
    from autoengineering.agents.batch import BatchCase
    from autoengineering.utility.contracts import BaselineReuseGroup, BaselineReusePolicy
    from autoengineering.utility.confirmation import SelectedCell, SelectionManifest, freeze
    from autoengineering.utility.controller import UtilityController, CaseBinding
    from autoengineering.utility.execution import archive_selected_state
    from autoengineering.utility.baseline_selection import reuse_selection_reference
    from autoengineering.utility.store import SuiteStore
    from autoengineering.campaign.serialization import digest
    from test_utility_contracts import suite, H
    from test_agent_batch import specification

    root, bound = fixture(tmp_path)
    template = suite(repetitions=2)
    cells = tuple(replace(c, seed=17 + c.repetition) for c in template.cells)
    group = BaselineReuseGroup(
        tuple(c.digest for c in cells),
        cells[0].digest,
        bound.model.digest,
        digest(dict(bound.configuration)),
        H,
        (0.25,) * 4,
    )
    policy = BaselineReusePolicy(
        "utility-baseline-reuse-v2", H, (group,), selection_reuse="frozen_reference"
    )
    spec = replace(
        template,
        schema="utility-suite-v2",
        protocol_digest=policy.digest,
        baseline_reuse=policy,
        cells=cells,
        routes=tuple(replace(r, kind="baseline") for r in template.routes),
        tasks=(
            replace(
                template.tasks[0],
                family="hydrology",
                candidate_digests=(bound.model.digest,),
                required_capabilities=("frozen_trained_inference",),
            ),
        ),
    )
    store = SuiteStore.create(tmp_path / "suite", spec)
    runtime = UtilityController(store)
    cases = tuple(
        BatchCase(
            "case-" + str(i), "comparison" if i == 0 else "reference", H, 0, 1 if i == 0 else 0
        )
        for i in range(4)
    )
    child = runtime.prepare_batch(
        replace(specification(), schema_version="1.1", cases=cases),
        tuple(CaseBinding(c.digest, b.id) for c, b in zip(cells, cases)),
    )
    coordinator = SimpleNamespace(
        store=store,
        runtime=runtime,
        plan=SimpleNamespace(schema="authored-trained-reference"),
        fault=lambda _: None,
    )
    chosen = {}

    def source(batch, case):
        selected, evidence = archive_selected_state(
            store, batch, bound, Path(__file__).resolve().parents[1], training_root=root
        )
        chosen.update(selected)
        summary = batch.evidence(
            {
                "profile": coordinator.plan.schema,
                "cell": cells[0].digest,
                "selection": selected,
                "outcome": "authored_precomputed_fit",
            }
        )
        batch.finish_case(case, "passed", (summary, *evidence))

    runtime.dispatch(child.root.name, cells[0].digest, source)
    for cell in cells[1:]:
        runtime.dispatch(
            child.root.name,
            cell.digest,
            lambda batch, case, cell=cell: reuse_selection_reference(
                coordinator, batch, case, cell
            ),
        )
    selections = []
    for cell in cells:
        attempt = "child-" + cell.digest[:48]
        event = next(
            e
            for e in store.replay()["events"]
            if e.operation == "finish" and e.attempt_id == attempt
        )
        selections.append(
            SelectedCell(
                cell.digest,
                "selected",
                attempt,
                event.result_digest,
                ArtifactRef.from_dict(chosen["model"]),
                "Authored frozen fit reference",
                ArtifactRef.from_dict(chosen["selected_state"]),
            )
        )
    identity = freeze(
        store,
        SelectionManifest(
            "utility-selection-v2", spec.digest, spec.protocol_digest, tuple(selections)
        ),
    )
    assert store.replay()["frozen"] == identity
    assert len({c.seed for c in cells}) == 2
    assert len({c.selected_state.sha256 for c in selections}) == 1
    assert not child.replay().reservations


def test_rehashed_closure_cannot_exceed_the_parent_companion_limit(tmp_path, monkeypatch):
    import autoengineering.utility.trained_selection as module

    root, bound = fixture(tmp_path)
    old = bound.training
    raw = read_bytes(root, old.profile)
    profile = put_bytes(
        root,
        raw + b" " * (4 * 1024 * 1024 - len(raw)),
        name="training-profile.json",
        media_type="application/json",
        producer=old.profile.producer,
    )
    bundle = TrainingArtifactBundle(
        "training-artifact-bundle-v1", old.fit, (profile, old.intent, old.result)
    )
    bundle_ref = put_bytes(
        root,
        bundle.to_json().encode(),
        name="training-bundle.json",
        media_type="application/json",
        producer=old.bundle.producer,
    )
    lifecycle = json.loads(read_bytes(root, old.lifecycle))
    for field in ("training", "worker_training"):
        lifecycle[field]["artifact"]["metadata"]["training_bundle"] = bundle_ref.to_json()
    lifecycle_ref = put_bytes(
        root,
        canonical_json(lifecycle).encode(),
        name="lifecycle.json",
        media_type="application/json",
        producer=old.lifecycle.producer,
    )
    bound = replace(
        bound,
        training=replace(old, profile=profile, bundle=bundle_ref, lifecycle=lifecycle_ref),
        evaluation=replace(
            bound.evaluation,
            provenance=dict(bound.evaluation.provenance)
            | {"lifecycle_record": lifecycle_ref.sha256},
        ),
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("oversized training closure was read")

    monkeypatch.setattr(module, "read_bytes", forbidden)
    with pytest.raises(ValueError, match="companion bytes"):
        read_selected_state(root, save(root, bound))
