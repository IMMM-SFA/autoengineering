from examples.utility.engineering_common_confirmation import CommonConfirmationLoadScorer
from test_utility_engineering_load_callback import setup, authored_solver


def test_common_confirmation_cost_selection_is_scored_once(tmp_path, monkeypatch):
    calls = authored_solver(monkeypatch)
    store, grant, service, captured, work = setup(
        tmp_path, monkeypatch, change="regime", scorer_class=CommonConfirmationLoadScorer
    )
    first = service.confirm(grant)
    assert first.score.status == "success"
    assert len(calls) == 24
    assert service.confirm(grant) == first
    assert len(calls) == 24


def test_common_confirmation_recovers_without_new_solver_or_source(tmp_path, monkeypatch):
    import pytest
    from examples.utility import engineering_source_binding
    from autoengineering.campaign.store import StoreError

    calls = authored_solver(monkeypatch)
    store, grant, service, _, _ = setup(
        tmp_path, monkeypatch, change="regime", scorer_class=CommonConfirmationLoadScorer
    )

    def lost(stage):
        if stage == "confirmation_score_created":
            raise RuntimeError("lost score publication")

    store.fault = lost
    with pytest.raises((RuntimeError, StoreError)):
        service.confirm(grant)
    store.fault = lambda stage: None

    def denied(*args, **kwargs):
        pytest.fail("recovery opened original scenarios")

    monkeypatch.setattr(engineering_source_binding, "open_for_confirmation", denied)
    receipt = service.recover(grant)
    assert receipt.score.status == "success"
    assert len(calls) == 24
