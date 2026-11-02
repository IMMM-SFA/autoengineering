"""Annual wind custody requires exact preselection binding and charged access."""

from dataclasses import replace
import json

import pytest

from autoengineering.utility.contracts import ResourceCap
from autoengineering.utility.scoring import ConfirmationGrant, ConfirmationService, PublicScore
from examples.utility import wind_annual_source as source
from test_utility_confirmation import selected_suite
from test_utility_wind_annual_scoring import inputs

CODE = "a" * 64


def setup(tmp_path, *, before=None):
    _, plan, drivers, _ = inputs()
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    captured = {}
    caps = (
        ResourceCap("private_wind_reads", "count", len(drivers), "reservation"),
        ResourceCap(
            "private_wind_bytes", "count", sum(16 * len(d.time_utc) for d in drivers), "reservation"
        ),
    )

    def transform(spec):
        budget = spec.budgets[0]
        total = tuple(replace(cap, limit=cap.limit * len(spec.cells)) for cap in caps)
        return replace(
            spec,
            tasks=(replace(spec.tasks[0], family="wind", partition_digest=plan.digest),),
            cells=tuple(replace(cell, scenario_digest=plan.digest) for cell in spec.cells),
            budgets=(
                replace(
                    budget,
                    caps=(*budget.caps, *total),
                    confirmation_reserve=(*budget.confirmation_reserve, *total),
                ),
            ),
        )

    def prepare(store):
        if before:
            before(store, plan, drivers, public, private)
        artifact = source.prepare(store, "task", plan, drivers, public, private)
        captured["artifact"] = artifact

    store, manifest, contract = selected_suite(
        tmp_path,
        suite_transform=transform,
        before_selection=prepare,
    )
    artifact = captured["artifact"]
    bound = source.read_binding(store, artifact)
    grant = ConfirmationGrant(
        store.spec.digest,
        manifest.cells[0].cell_digest,
        plan.digest,
        source.scorer_identity(bound, CODE),
        contract.digest,
        manifest.cells[0].model.sha256,
        store.replay()["frozen"],
        (ResourceCap("scientific_starts", "count", 1, "reservation"), *caps),
    )
    return store, grant, contract, artifact, public, private, drivers


def open_data(context, grant=None, *, code=CODE):
    store, original, _, artifact, public, private, _ = context
    return source.open_for_confirmation(
        store,
        grant or original,
        artifact,
        public,
        private,
        scorer_code_digest=code,
    )


def service(context, scorer, grant=None):
    store, original, contract, *_ = context
    return ConfirmationService(
        store,
        scorer,
        scorer_digest=(grant or original).scorer_digest,
        outcome_contract=contract,
    )


def track_reads(monkeypatch, context):
    reads = []
    original = source.read_bytes
    store, grant = context[:2]

    def read(root, artifact, **kwargs):
        if artifact.path.endswith(".f64le"):
            assert (store.root / source.ACCESSES / (grant.digest + ".json")).exists()
            assert (
                "confirmation-" + grant.cell_digest[:48] in store.replay()["confirmation_accesses"]
            )
            reads.append(artifact.path)
        return original(root, artifact, **kwargs)

    monkeypatch.setattr(source, "read_bytes", read)
    return reads


def test_complete_barrier_charged_access_one_read_per_year_and_saved_replay(tmp_path, monkeypatch):
    context = setup(tmp_path)
    reads = track_reads(monkeypatch, context)

    def scorer(grant, model):
        actual = open_data(context, grant)
        assert [d.manifest_digest for d in actual] == [d.manifest_digest for d in context[-1]]
        # Authored custody-only result, not a wind model or energy evaluation.
        return PublicScore("success", "power", "W", 3.0, True)

    receipt = service(context, scorer).confirm(context[1])
    assert reads == ["year-2012.f64le", "year-2013.f64le", "year-2014.f64le"]
    reads.clear()
    resumed = service(context, lambda *a: pytest.fail("saved score reopened annual weather"))
    assert resumed.confirm(context[1]) == receipt
    assert reads == []
    state = context[0].replay()
    assert state["phase_used"][("fixed_evaluations", "confirmation", "private_wind_reads")] == 3
    completion = context[0].root / source.ACCESSES / f"{context[1].digest}-complete.json"
    assert json.loads(completion.read_text())["completed_private_reads"] == 3


def test_freeze_alone_does_not_authorize_source_access(tmp_path, monkeypatch):
    context = setup(tmp_path)
    reads = track_reads(monkeypatch, context)
    with pytest.raises(ValueError, match="no automatic retry"):
        open_data(context)
    assert reads == []
    assert not (context[0].root / source.ACCESSES).exists()


@pytest.mark.parametrize(
    "change",
    ["public_bytes", "source_code", "kernel_code", "scorer_code", "missing_reserve", "wrong_bytes"],
)
def test_invalid_identity_or_reservation_opens_no_private_payload(tmp_path, monkeypatch, change):
    context = setup(tmp_path)
    reads = track_reads(monkeypatch, context)
    grant = context[1]
    code = CODE
    if change == "public_bytes":
        path = context[4] / "binding.json"
        path.write_bytes(path.read_bytes() + b" ")
    elif change == "source_code":
        monkeypatch.setattr(source, "source_identity", lambda: "f" * 64)
    elif change == "kernel_code":
        monkeypatch.setattr(source.kernel, "source_identity", lambda: "f" * 64)
    elif change == "scorer_code":
        code = "f" * 64
    elif change == "missing_reserve":
        grant = replace(
            grant, resources=tuple(c for c in grant.resources if c.name != "private_wind_reads")
        )
    else:
        grant = replace(
            grant,
            resources=tuple(
                replace(cap, limit=0) if cap.name == "private_wind_bytes" else cap
                for cap in grant.resources
            ),
        )

    def scorer(active, model):
        with pytest.raises(ValueError):
            open_data(context, active, code=code)
        return PublicScore("model_failure", "power", "W", None, None)

    receipt = service(context, scorer, grant).confirm(grant)
    assert receipt.score.status == "model_failure"
    assert reads == []
    assert not (context[0].root / source.ACCESSES).exists()


def test_partial_read_consumes_intent_and_refuses_second_open(tmp_path, monkeypatch):
    context = setup(tmp_path)
    path = context[5] / "year-2013.f64le"
    blob = path.read_bytes()
    path.write_bytes(b"\0" * len(blob))
    reads = track_reads(monkeypatch, context)

    def scorer(active, model):
        with pytest.raises(ValueError):
            open_data(context, active)
        first = list(reads)
        with pytest.raises(ValueError):
            open_data(context, active)
        assert reads == first == ["year-2012.f64le", "year-2013.f64le"]
        return PublicScore("model_failure", "power", "W", None, None)

    receipt = service(context, scorer).confirm(context[1])
    assert receipt.score.status == "model_failure"
    assert (context[0].root / source.ACCESSES / (context[1].digest + ".json")).exists()
    assert not any("year-2014" in item for item in reads)
    access = context[0].root / source.ACCESSES
    assert (access / f"{context[1].digest}-2012-complete.json").exists()
    assert (access / f"{context[1].digest}-2013-start.json").exists()
    assert not (access / f"{context[1].digest}-2013-complete.json").exists()
    assert not (access / f"{context[1].digest}-complete.json").exists()


@pytest.mark.parametrize("change", ["permissions", "symlink"])
def test_private_file_boundary_is_checked_before_bytes(tmp_path, monkeypatch, change):
    context = setup(tmp_path)
    path = context[5] / "year-2012.f64le"
    if change == "permissions":
        path.chmod(0o644)
    else:
        saved = context[5] / "other-file"
        path.rename(saved)
        path.symlink_to(saved)
    reads = track_reads(monkeypatch, context)

    def scorer(active, model):
        with pytest.raises(ValueError):
            open_data(context, active)
        return PublicScore("model_failure", "power", "W", None, None)

    service(context, scorer).confirm(context[1])
    assert reads == []


def test_preparation_cannot_repeat_after_selection_or_change_private_data(tmp_path):
    context = setup(tmp_path)
    store, _, _, artifact, public, private, drivers = context
    original = {p.name: p.read_bytes() for p in private.iterdir()}
    binding = source.read_binding(store, artifact)
    with pytest.raises(ValueError):
        source.prepare(store, "task", binding.plan, drivers, public, private)
    assert original == {p.name: p.read_bytes() for p in private.iterdir()}


def test_preparation_intent_blocks_restarting_at_fresh_paths(tmp_path, monkeypatch):
    captured = {}
    original = source.durable_write

    def before(store, plan, drivers, public, private):
        def fail_private(path, data, **kwargs):
            if path.suffix == ".f64le":
                raise OSError("authored private publication loss")
            return original(path, data, **kwargs)

        monkeypatch.setattr(source, "durable_write", fail_private)
        with pytest.raises(ValueError):
            source.prepare(store, "task", plan, drivers, public, private)
        claim_path = store.root / source.CLAIMS / "task.json"
        captured["claim"] = claim_path.read_bytes()
        a, b = tmp_path / "other-public", tmp_path / "other-private"
        a.mkdir(mode=0o700)
        b.mkdir(mode=0o700)
        monkeypatch.setattr(source, "durable_write", original)
        with pytest.raises(ValueError):
            source.prepare(store, "task", plan, drivers, a, b)
        assert claim_path.read_bytes() == captured["claim"]
        assert not list(a.iterdir()) and not list(b.iterdir())
        # End this fixture before its ordinary successful preparation.
        raise RuntimeError("verified consumed preparation")

    with pytest.raises(RuntimeError, match="verified consumed"):
        setup(tmp_path, before=before)
    assert json.loads(captured["claim"])["automatic_retries"] == 0


def test_source_open_before_any_selection_or_barrier_reads_no_payload(tmp_path, monkeypatch):
    reads = []
    original = source.read_bytes

    def read(root, artifact, **kwargs):
        if artifact.path.endswith(".f64le"):
            reads.append(artifact.path)
            pytest.fail("pre-barrier source access opened private bytes")
        return original(root, artifact, **kwargs)

    monkeypatch.setattr(source, "read_bytes", read)

    def before(store, plan, drivers, public, private):
        artifact = source.prepare(store, "task", plan, drivers, public, private)
        bound = source.read_binding(store, artifact)
        grant = ConfirmationGrant(
            store.spec.digest,
            store.spec.cells[0].digest,
            plan.digest,
            source.scorer_identity(bound, CODE),
            "a" * 64,
            "a" * 64,
            "a" * 64,
            (ResourceCap("scientific_starts", "count", 1, "reservation"),),
        )
        assert store.replay()["frozen"] is None
        with pytest.raises(ValueError):
            source.open_for_confirmation(
                store, grant, artifact, public, private, scorer_code_digest=CODE
            )
        assert not (store.root / source.ACCESSES).exists()
        raise RuntimeError("verified pre-barrier refusal")

    with pytest.raises(RuntimeError, match="verified pre-barrier"):
        setup(tmp_path, before=before)
    assert reads == []
