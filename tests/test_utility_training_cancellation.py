"""Actual cancellation after the supplied worker's durable fitting intent."""

from datetime import date, timedelta
import json
from pathlib import Path
import threading
import time

import numpy as np
import pytest

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.agents.batch import BatchStore
from autoengineering.agents.batch_science import BatchCampaignController
from autoengineering.campaign.execution import cancellation_intent
from autoengineering.utility.campaign_costs import join_campaign_costs
from autoengineering.utility.hydrology_training import RoutingTrainingProfile
from test_utility_campaign_training_costs import setup, CELL
from test_utility_training_terminal import terminal


def long_authored_fixture(tmp_path, cap=120):
    from examples.utility.hydrology_site import HydrologySite
    from examples.utility.hydrology_learned import context, _route
    from examples.leaf_river.models.pet_hamon import hamon_pet
    from examples.leaf_river.models.soil_moisture import soil_bucket

    n = 2000
    dates = tuple((date(2000, 1, 1) + timedelta(days=i)).isoformat() for i in range(n + 40))
    site = HydrologySite("utility-hydrology-site-v1", "authored", "basin", 40.0, 10.0)
    mask = np.arange(n) >= 10
    profile = RoutingTrainingProfile(dates[:n], 10, tuple(bool(v) for v in mask), cap)
    scratch = tmp_path / "training"
    scratch.mkdir(mode=0o700)
    ctx = context(
        site,
        profile,
        dates,
        {"capacity": 100.0, "pet": "hamon"},
        scratch,
        warmup_mask=(True,) * 10 + (False,) * (len(dates) - 10),
        scoring_mask=(False,) * n + (True,) * 40,
    )
    rain = np.random.default_rng(17).uniform(0.0, 70.0, len(dates))
    rain[::3] = 0.0
    forcing = {
        "precip_mm": rain,
        "tmean_c": np.full(len(dates), 15.0),
        "tmin_c": np.full(len(dates), 10.0),
        "tmax_c": np.full(len(dates), 20.0),
        "day_of_year": np.asarray([date.fromisoformat(d).timetuple().tm_yday for d in dates]),
    }
    pet = hamon_pet(forcing["tmean_c"], forcing["day_of_year"], latitude=40.0)
    _, excess, _ = soil_bucket(rain, pet, 100.0, 50.0)
    truth, _ = _route(excess, (-1.3, 1.1))
    fitting = {k: v[:n].copy() for k, v in forcing.items()} | {
        "labels": np.where(mask, truth[:n], 0.0),
        "mask": mask,
    }
    return site, profile, ctx, forcing, fitting, truth


@pytest.mark.parametrize("recover,conflicting", [(False, False), (True, False), (False, True)])
def test_cancel_after_training_intent_keeps_one_charge_and_unknown_partial_work(
    tmp_path, monkeypatch, recover, conflicting
):
    import autoengineering.campaign.controller as module
    import test_utility_hydrology_learned as models

    monkeypatch.setattr(models, "fixture", long_authored_fixture)
    original = module.supervise
    observations = []
    roots = []
    pins = []

    class AuthoredLoss(BaseException):
        pass

    def supervised(command, **kwargs):
        job = json.loads(Path(command[-1]).read_text())
        scratch = Path(job["context"]["scratch_path"])
        errors = []

        def cancel_after_intent():
            try:
                deadline = time.monotonic() + 20
                intent = scratch / "training-intent.json"
                while not intent.is_file():
                    if time.monotonic() >= deadline:
                        raise AssertionError("registered worker never wrote its fitting intent")
                    time.sleep(0.001)
                assert not (scratch / "training-result.json").exists()
                observations.append(json.loads(intent.read_text()))
                cancellation_intent(
                    kwargs["root"], "authored-training-stop", campaign_id=kwargs["campaign_id"]
                )
            except BaseException as error:
                errors.append(error)

        watcher = threading.Thread(target=cancel_after_intent, daemon=True)
        watcher.start()
        result = original(command, **kwargs)
        watcher.join(timeout=25)
        assert not watcher.is_alive() and not errors, errors
        assert result.stopped and result.stop_reason == "cancelled"
        if conflicting:
            roots.append(kwargs["root"])
            path = kwargs["root"] / "attempts/attempt-000001/supervisor-result.json"
            proof = json.loads(path.read_text())
            proof["identity"]["nonce"] = "authored-conflict"
            path.write_text(json.dumps(proof))
            raise AuthoredLoss()
        return result

    monkeypatch.setattr(module, "supervise", supervised)
    if conflicting:
        with pytest.raises(AuthoredLoss):
            setup(
                tmp_path,
                monkeypatch,
                registered=True,
                on_create=lambda batch, _controller: pins.append(batch.digest),
            )
        batch = BatchStore(tmp_path / "batch", expected_digest=pins[0])
        controller = BatchCampaignController.open(roots[0], batch=batch, case_id="model")
        monkeypatch.setattr(
            module, "supervise", lambda *_a, **_k: pytest.fail("recovery relaunched")
        )
        controller.recover()
        assert controller.state().outcome == "cancelled"
        assert controller.state().budget.unresolved_attempts == 1
        assert not controller.state().evaluations
        assert len(batch.replay().reservations) == len(batch.replay().pending) == 1
        return
    batch, controller = setup(tmp_path, monkeypatch, registered=True, recover=recover)
    assert observations and len(observations) == 1
    assert controller.state().outcome == "cancelled"
    assert len(controller.state().budget.attempts) == 1
    assert controller.state().budget.unresolved_attempts == 0
    ref, evidence = terminal(controller)
    assert evidence.disposition == "captured" and evidence.intent is not None
    assert evidence.result is None and evidence.fit is None
    assert (
        json.loads(read_bytes(controller.store.root, evidence.intent))["training_id"]
        == observations[0]["training_id"]
    )
    costs = join_campaign_costs(batch, {"model": CELL})
    values = {r.resource: r.quantity for r in costs}
    assert values["campaign_process_starts"] == values["training_starts"] == 1
    assert values["training_routing_starts"] is None and values["training_elapsed"] is None
    assert batch.report()["scientific_reservations_charged"] == 1
    before = batch.replay()
    controller.reconcile_batch()
    assert batch.replay() == before
    assert ref.producer == "attempt-000001"
