"""Exact source bytes enter existing confirmation identity and access accounting."""

from dataclasses import replace

import pytest

from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.contracts import ResourceCap
from autoengineering.utility.scoring import ConfirmationGrant, ConfirmationService, PublicScore
from examples.utility import engineering_source_binding as binding
from examples.utility import engineering_scenarios as source
from test_utility_confirmation import selected_suite

H = "1" * 64


def setup(tmp_path, monkeypatch, *, entropy=None):
    policy = source.ScenarioPolicy(
        "utility-engineering-generated-scenarios-v1",
        "task",
        {
            "ground_voltage": (-0.05, 0.05),
            "resistor1_ohm": (95.0, 105.0),
            "resistor2_ohm": (9500.0, 10500.0),
        },
        source.source_identity(),
    )
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    monkeypatch.setattr(source.secrets, "token_bytes", entropy or (lambda n: b"a" * 32))
    captured = {}

    def before(store):
        metadata = source.prepare(
            store, policy, public, private, expected_suite_digest=store.spec.digest
        )
        ref = binding.seal(store, public, expected_manifest_digest=digest(metadata))
        assert binding.seal(store, public, expected_manifest_digest=digest(metadata)) == ref
        captured.update(metadata=metadata, ref=ref)

    def transform(spec):
        return replace(
            spec,
            tasks=(replace(spec.tasks[0], partition_digest=policy.digest),),
            cells=tuple(replace(c, scenario_digest=policy.digest) for c in spec.cells),
        )

    store, manifest, contract = selected_suite(
        tmp_path, suite_transform=transform, before_selection=before
    )
    fixed = binding.read_binding(store, captured["ref"])
    grant = ConfirmationGrant(
        store.spec.digest,
        manifest.cells[0].cell_digest,
        policy.digest,
        binding.scorer_identity(fixed, H),
        contract.digest,
        manifest.cells[0].model.sha256,
        store.replay()["frozen"],
        (ResourceCap("scientific_starts", "count", 1, "reservation"),),
    )
    return store, grant, contract, captured["ref"], public, private, captured["metadata"]


def test_core_confirmation_access_precedes_one_source_read_and_completed_replay_reads_none(
    tmp_path, monkeypatch
):
    store, grant, contract, ref, public, private, _ = setup(tmp_path, monkeypatch)
    calls = []
    original = source.read_private

    def read(*args, **kwargs):
        assert (store.root / binding.ACCESS_DIRECTORY / (grant.digest + ".json")).exists()
        calls.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(source, "read_private", read)

    def scorer(active, model):
        rows = binding.open_for_confirmation(
            store, active, ref, public, private, scorer_code_digest=H
        )
        assert len(rows) == 24
        return PublicScore(
            "success", "power", "W", 3.0, True
        )  # Authored score, never a circuit result.

    service = ConfirmationService(
        store, scorer, scorer_digest=grant.scorer_digest, outcome_contract=contract
    )
    receipt = service.confirm(grant)
    assert calls == [1] and receipt.score.value == 3.0
    monkeypatch.setattr(
        source, "read_private", lambda *a, **kw: pytest.fail("completed score reopened source")
    )
    monkeypatch.setattr(
        source.secrets, "token_bytes", lambda n: pytest.fail("confirmation redrew source")
    )
    resumed = ConfirmationService(
        store,
        lambda *a: pytest.fail("completed score rescored"),
        scorer_digest=grant.scorer_digest,
        outcome_contract=contract,
    )
    assert resumed.confirm(grant) == receipt
    assert (
        store.replay()["phase_used"][("fixed_evaluations", "confirmation", "scientific_starts")]
        == 1
    )


def test_a_valid_barrier_and_grant_do_not_replace_access_receipt(tmp_path, monkeypatch):
    store, grant, _, ref, public, private, _ = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(
        source, "read_private", lambda *a, **kw: pytest.fail("unreserved source open")
    )
    with pytest.raises(ValueError):
        binding.open_for_confirmation(store, grant, ref, public, private, scorer_code_digest=H)
    assert not (store.root / binding.ACCESS_DIRECTORY).exists()


@pytest.mark.parametrize(
    "change", ["grant_scorer", "scorer_code", "binding_bytes", "public_bytes", "source_code"]
)
def test_changed_code_or_source_is_refused_before_private_read(tmp_path, monkeypatch, change):
    store, grant, _, ref, public, private, _ = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(
        source, "read_private", lambda *a, **kw: pytest.fail("changed source opened")
    )
    code = H
    if change == "grant_scorer":
        grant = replace(grant, scorer_digest="0" * 64)
    elif change == "scorer_code":
        code = "0" * 64
    elif change == "binding_bytes":
        (store.root / ref.path).write_text("changed")
    elif change == "public_bytes":
        (public / "manifest.json").write_text("changed")
    else:
        monkeypatch.setattr(source, "source_identity", lambda: "0" * 64)
    with pytest.raises(ValueError):
        binding.open_for_confirmation(store, grant, ref, public, private, scorer_code_digest=code)


def test_uncertain_source_access_keeps_original_charge_and_cannot_read_again(tmp_path, monkeypatch):
    store, grant, contract, ref, public, private, _ = setup(tmp_path, monkeypatch)
    calls = []

    def private_failure(*a, **kw):
        calls.append(1)
        raise RuntimeError("PRIVATE-SOURCE-ERROR-71953")

    monkeypatch.setattr(source, "read_private", private_failure)

    def scorer(active, model):
        binding.open_for_confirmation(store, active, ref, public, private, scorer_code_digest=H)
        pytest.fail("failed source became score")

    service = ConfirmationService(
        store, scorer, scorer_digest=grant.scorer_digest, outcome_contract=contract
    )
    with pytest.raises(StoreError) as caught:
        service.confirm(grant)
    assert "PRIVATE" not in str(caught.value)
    assert calls == [1]
    with pytest.raises(ValueError):
        binding.open_for_confirmation(store, grant, ref, public, private, scorer_code_digest=H)
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)
    assert calls == [1]
    assert len(store.replay()["confirmation_accesses"]) == 1
    assert not store.replay()["confirmation_scores"]


def test_source_seal_cannot_be_recreated_after_selection(tmp_path, monkeypatch):
    store, _, _, ref, public, _, metadata = setup(tmp_path, monkeypatch)
    before = binding.read_binding(store, ref)
    with pytest.raises(ValueError):
        binding.seal(store, public, expected_manifest_digest=digest(metadata))
    assert binding.read_binding(store, ref) == before
    changed = replace(before, private_record_digest="0" * 64)
    assert binding.scorer_identity(before, H) != binding.scorer_identity(changed, H)


def test_read_binding_is_metadata_only_and_rejects_a_refreshed_other_role(tmp_path, monkeypatch):
    store, _, _, ref, _, _, _ = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(
        source, "read_private", lambda *a, **kw: pytest.fail("metadata read private")
    )
    monkeypatch.setattr(source, "derive", lambda *a: pytest.fail("metadata derived private"))
    assert binding.read_binding(store, ref).task_id == "task"
    with pytest.raises(ValueError):
        binding.read_binding(store, replace(ref, media_type="text/plain"))


def test_active_confirmation_refuses_changed_public_bytes_before_private_open(
    tmp_path, monkeypatch
):
    store, grant, contract, ref, public, private, _ = setup(tmp_path, monkeypatch)
    (public / "manifest.json").write_text("changed after sealing")
    calls = []

    def private_read(*a, **kw):
        calls.append(1)
        pytest.fail("changed public source reached private data")

    monkeypatch.setattr(source, "read_private", private_read)

    def scorer(active, model):
        binding.open_for_confirmation(store, active, ref, public, private, scorer_code_digest=H)
        pytest.fail("changed source produced a score")

    service = ConfirmationService(
        store, scorer, scorer_digest=grant.scorer_digest, outcome_contract=contract
    )
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)
    assert not calls
    state = store.replay()
    assert len(state["confirmation_accesses"]) == 1 and not state["confirmation_scores"]
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)
    assert not calls
