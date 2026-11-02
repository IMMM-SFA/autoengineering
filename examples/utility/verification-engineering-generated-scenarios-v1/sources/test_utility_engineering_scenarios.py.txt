"""Preselection generation and post-barrier access is once per task, source-bound and solver-free."""

from dataclasses import replace
import math

import pytest

from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.utility.store import SuiteStore
from autoengineering.utility.confirmation import freeze
from examples.utility import engineering_scenarios as module
from test_utility_contracts import suite
from test_utility_confirmation import unattempted


def setup(tmp_path, *, frozen=False):
    policy = module.ScenarioPolicy(
        "utility-engineering-generated-scenarios-v1",
        "task",
        {
            "ground_voltage": (-0.05, 0.05),
            "resistor1_ohm": (95.0, 105.0),
            "resistor2_ohm": (9500.0, 10500.0),
        },
        module.source_identity(),
    )
    spec = suite()
    spec = replace(
        spec,
        tasks=(replace(spec.tasks[0], partition_digest=policy.digest),),
        cells=tuple(replace(c, scenario_digest=policy.digest) for c in spec.cells),
    )
    store = SuiteStore.create(tmp_path / "suite", spec)
    if frozen:
        freeze(store, unattempted(spec))
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    return (
        store,
        policy,
        public,
        private,
        dict(expected_suite_digest=spec.digest),
    )


def generate(values):
    store, policy, public, private, kwargs = values
    return module.prepare(store, policy, public, private, **kwargs)


def test_generation_waits_for_all_claims_and_keeps_raw_scenarios_private(tmp_path, monkeypatch):
    values = setup(tmp_path)
    store, policy, public, private, _ = values
    draws = []

    def entropy(size):
        assert size == 32
        assert (store.root / module.CLAIMS / "task.json").exists()
        assert (public / "preparation-claim.json").exists() and (
            private / "preparation-claim.json"
        ).exists()
        draws.append(1)
        return b"a" * 32

    monkeypatch.setattr(module.secrets, "token_bytes", entropy)
    result = generate(values)
    assert draws == [1] and result["scenario_count"] == 24
    blob = (public / "manifest.json").read_text()
    assert "seed_hex" not in blob and '"forcing"' not in blob and (b"a" * 32).hex() not in blob
    identity = freeze(store, unattempted(store.spec))
    scenarios = module.read_private(
        store,
        public,
        private,
        expected_manifest_digest=digest(result),
        expected_selection_digest=identity,
    )
    assert len(scenarios) == 24 and len({r["scenario_id"] for r in scenarios}) == 24
    assert math.isclose(sum(r["weight"] for r in scenarios), 1.0)
    for row in scenarios:
        assert set(row["forcing"]) == set(module.UNITS)
        for name, value in row["forcing"].items():
            assert policy.bounds[name][0] <= value <= policy.bounds[name][1]
    assert result["outputs_evaluated"] is False and result["task_admitted"] is False
    assert (
        not result["historical_data_independence_attested"]
        and not result["private_boundary_qualified"]
    )


@pytest.mark.parametrize("change", ["frozen", "suite", "policy", "source", "family"])
def test_wrong_or_unfrozen_binding_generates_nothing(tmp_path, monkeypatch, change):
    values = setup(tmp_path, frozen=change == "frozen")
    store, policy, public, private, kwargs = values
    monkeypatch.setattr(
        module.secrets, "token_bytes", lambda n: pytest.fail("invalid binding drew entropy")
    )
    if change == "suite":
        kwargs["expected_suite_digest"] = "0" * 64
    elif change == "policy":
        policy = replace(policy, bounds=dict(policy.bounds) | {"ground_voltage": (-0.04, 0.04)})
    elif change == "source":
        policy = replace(policy, sampler_source_sha256="0" * 64)
    elif change == "family":
        spec = replace(store.spec, tasks=(replace(store.spec.tasks[0], family="wind"),))
        store = SuiteStore.create(tmp_path / "other-suite", spec)
        kwargs = dict(expected_suite_digest=spec.digest)
    with pytest.raises(ValueError):
        module.prepare(store, policy, public, private, **kwargs)
    assert not list(public.iterdir()) and not list(private.iterdir())


def test_different_output_scope_cannot_redraw_a_consumed_task(tmp_path, monkeypatch):
    values = setup(tmp_path)
    monkeypatch.setattr(module.secrets, "token_bytes", lambda n: b"b" * 32)
    first = generate(values)
    store, policy, public, private, kwargs = values
    fresh_public, fresh_private = tmp_path / "another-public", tmp_path / "another-private"
    fresh_public.mkdir(mode=0o700)
    fresh_private.mkdir(mode=0o700)
    monkeypatch.setattr(
        module.secrets, "token_bytes", lambda n: pytest.fail("consumed task drew again")
    )
    with pytest.raises(ValueError):
        module.prepare(store, policy, fresh_public, fresh_private, **kwargs)
    assert not list(fresh_public.iterdir()) and not list(fresh_private.iterdir())
    assert module.read_public(public, expected_manifest_digest=digest(first)) == first


@pytest.mark.parametrize("boundary", ["before_entropy", "before_private", "before_public"])
def test_interrupted_source_never_redraws_and_only_committed_source_can_recover(
    tmp_path, monkeypatch, boundary
):
    values = setup(tmp_path)
    store, policy, public, private, kwargs = values
    draws = []

    def entropy(n):
        draws.append(1)
        return b"c" * 32

    monkeypatch.setattr(module.secrets, "token_bytes", entropy)
    original = module._save

    def save(root, name, value):
        if (
            (boundary == "before_entropy" and root == private and name == "preparation-claim.json")
            or (boundary == "before_private" and root == private and name == "scenarios.json")
            or (boundary == "before_public" and root == public and name == "manifest.json")
        ):
            raise RuntimeError("PRIVATE-ERROR-7613")
        return original(root, name, value)

    monkeypatch.setattr(module, "_save", save)
    with pytest.raises(ValueError) as caught:
        generate(values)
    assert caught.value.__context__ is None and "PRIVATE" not in str(caught.value)
    assert len(draws) == int(boundary != "before_entropy")
    claim = unique_json((store.root / module.CLAIMS / "task.json").read_text())
    assert claim["entropy_draws_reserved"] == 1 and claim["automatic_retries"] == 0
    monkeypatch.setattr(module, "_save", original)
    monkeypatch.setattr(module.secrets, "token_bytes", lambda n: pytest.fail("recovery redrew"))
    if boundary == "before_public":
        recovered = module.recover_public(
            store, public, private, expected_claim_digest=digest(claim)
        )
        assert recovered == module.recover_public(
            store, public, private, expected_claim_digest=digest(claim)
        )
        identity = freeze(store, unattempted(store.spec))
        assert (
            len(
                module.read_private(
                    store,
                    public,
                    private,
                    expected_manifest_digest=digest(recovered),
                    expected_selection_digest=identity,
                )
            )
            == 24
        )
    else:
        with pytest.raises(ValueError):
            module.recover_public(store, public, private, expected_claim_digest=digest(claim))
    p2, q2 = tmp_path / "p2", tmp_path / "q2"
    p2.mkdir(mode=0o700)
    q2.mkdir(mode=0o700)
    with pytest.raises(ValueError):
        module.prepare(store, policy, p2, q2, **kwargs)


def test_public_reader_does_not_derive_or_draw_and_rejects_unknown_fields(tmp_path, monkeypatch):
    values = setup(tmp_path)
    monkeypatch.setattr(module.secrets, "token_bytes", lambda n: b"d" * 32)
    result = generate(values)
    public = values[2]
    monkeypatch.setattr(
        module, "derive", lambda *a: pytest.fail("public reader derived private scenarios")
    )
    monkeypatch.setattr(
        module.secrets, "token_bytes", lambda n: pytest.fail("public reader drew entropy")
    )
    assert module.read_public(public, expected_manifest_digest=digest(result)) == result
    changed = dict(result) | {"unexpected": "PRIVATE"}
    (public / "manifest.json").unlink()
    module._save(public, "manifest.json", changed)
    with pytest.raises(ValueError):
        module.read_public(public, expected_manifest_digest=digest(changed))


@pytest.mark.parametrize("field", ["seed_hex", "scenarios", "units", "extra"])
def test_changed_private_draw_never_becomes_another_valid_source(tmp_path, monkeypatch, field):
    values = setup(tmp_path)
    monkeypatch.setattr(module.secrets, "token_bytes", lambda n: b"e" * 32)
    result = generate(values)
    private = values[3]
    data = unique_json((private / "scenarios.json").read_text())
    if field == "seed_hex":
        data[field] = "0" * 64
    elif field == "scenarios":
        data[field][0]["forcing"]["resistor1_ohm"] = 96.0
    elif field == "units":
        data[field]["resistor1_ohm"] = "kohm"
    else:
        data["extra"] = "unexpected"
    (private / "scenarios.json").unlink()
    module._save(private, "scenarios.json", data)
    with pytest.raises(ValueError):
        identity = freeze(values[0], unattempted(values[0].spec))
        module.read_private(
            values[0],
            values[2],
            private,
            expected_manifest_digest=digest(result),
            expected_selection_digest=identity,
        )


def test_path_aliases_and_stale_public_pin_refuse(tmp_path, monkeypatch):
    values = setup(tmp_path)
    store, policy, public, private, kwargs = values
    monkeypatch.setattr(module.secrets, "token_bytes", lambda n: pytest.fail("aliased output drew"))
    with pytest.raises(ValueError):
        module.prepare(store, policy, public, public, **kwargs)
    inside = store.root / "inside"
    inside.mkdir(mode=0o700)
    with pytest.raises(ValueError):
        module.prepare(store, policy, inside, private, **kwargs)
    monkeypatch.setattr(module.secrets, "token_bytes", lambda n: b"f" * 32)
    generate(values)
    with pytest.raises(ValueError):
        module.read_public(public, expected_manifest_digest="0" * 64)


def test_private_source_cannot_open_before_complete_barrier(tmp_path, monkeypatch):
    values = setup(tmp_path)
    monkeypatch.setattr(module.secrets, "token_bytes", lambda n: b"g" * 32)
    result = generate(values)
    original = module._read

    def read(root, name, limit=65536):
        if root == values[3]:
            pytest.fail("pre-barrier private source access")
        return original(root, name, limit)

    monkeypatch.setattr(module, "_read", read)
    with pytest.raises(ValueError):
        module.read_private(
            values[0],
            values[2],
            values[3],
            expected_manifest_digest=digest(result),
            expected_selection_digest="1" * 64,
        )


def test_prior_selection_activity_refuses_new_draw(tmp_path, monkeypatch):
    from test_utility_store import operation

    values = setup(tmp_path)
    store = values[0]
    with store.writer():
        store.append(**operation(store.spec))
    monkeypatch.setattr(
        module.secrets, "token_bytes", lambda n: pytest.fail("late source generation")
    )
    with pytest.raises(ValueError):
        generate(values)
    assert not list(values[2].iterdir()) and not list(values[3].iterdir())


def test_unbounded_numeric_domain_and_short_seed_refuse(tmp_path):
    values = setup(tmp_path)
    policy = values[1]
    with pytest.raises(ValueError):
        replace(policy, bounds=dict(policy.bounds) | {"ground_voltage": (-1e308, 1e308)})
    with pytest.raises(ValueError):
        module.derive(b"short", policy, "1" * 64, "2" * 64)
