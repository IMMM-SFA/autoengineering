"""Annual callback binds selected layouts, original source reads and saved work."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.store import StoreError
from autoengineering.utility.contracts import ResourceCap
from autoengineering.utility.scoring import ConfirmationGrant, ConfirmationService
from examples.utility import wind_annual_callback as callback
from examples.utility import wind_annual_source as source
from test_utility_confirmation import selected_suite
from test_utility_wind_annual_scoring import inputs

ROOT = Path(__file__).resolve().parents[1]


def setup(
    tmp_path, monkeypatch, *, change=None, fail_model=False, native=False, analysis_plan=None
):
    geometry, plan, drivers, policy = inputs()
    expected = callback.model_snapshot(geometry, plan, ROOT)
    public, private, work = (tmp_path / name for name in ("public", "private", "work"))
    for path in (public, private, work):
        path.mkdir(mode=0o700)
    captures = {"calls": [], "reads": []}
    resources = (
        ResourceCap("scientific_starts", "count", 1, "reservation"),
        ResourceCap("wind_model_starts", "count", 3, "reservation"),
        ResourceCap("private_wind_reads", "count", 3, "reservation"),
        ResourceCap("private_wind_bytes", "count", 420864, "reservation"),
        ResourceCap("active_time", "s", 60, "reservation"),
    )

    def before(store):
        for ref in expected.source_bundle:
            target = store.root / ref.path
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(read_bytes(ROOT, ref))
        artifact = source.prepare(store, "task", plan, drivers, public, private)
        captures["scorer"] = callback.TrustedAnnualWindScorer(
            store,
            artifact,
            public,
            private,
            ROOT,
            work,
            geometry=geometry,
            expected_model=expected,
            policy=policy,
        )

    def transform(spec):
        budget = spec.budgets[0]
        totals = tuple(replace(cap, limit=cap.limit * len(spec.cells)) for cap in resources[1:4])
        regime = "fixed_total_cost" if change == "regime" else "fixed_evaluations"
        return replace(
            spec,
            tasks=(replace(spec.tasks[0], family="wind", partition_digest=plan.digest),),
            cells=tuple(replace(c, scenario_digest=plan.digest, regime=regime) for c in spec.cells),
            budgets=(
                replace(
                    budget,
                    regime=regime,
                    caps=(*budget.caps, *totals),
                    confirmation_reserve=(*budget.confirmation_reserve, *totals, resources[-1]),
                ),
            ),
        )

    configuration = geometry.baseline
    configuration["x_0"] = True if change == "configuration" else 10.0
    store, manifest, contract = selected_suite(
        tmp_path,
        analysis_plan=analysis_plan,
        suite_transform=transform,
        before_selection=before,
        model_override=expected,
        selected_configuration=configuration,
        outcome_contract_override=callback.outcome_contract(policy),
    )
    scorer = captures["scorer"]
    if change == "allowance":
        resources = tuple(cap for cap in resources if cap.name != "wind_model_starts")
    grant = ConfirmationGrant(
        store.spec.digest,
        manifest.cells[0].cell_digest,
        plan.digest,
        scorer.identity,
        contract.digest,
        manifest.cells[0].model.sha256,
        store.replay()["frozen"],
        resources,
    )
    service = ConfirmationService(
        store, scorer, scorer_digest=scorer.identity, outcome_contract=contract
    )
    original_read = source.read_bytes

    def read(root, artifact, **kwargs):
        if artifact.path.endswith(".f64le"):
            captures["reads"].append(artifact.path)
        return original_read(root, artifact, **kwargs)

    def backend():
        def model(**kwargs):
            captures["calls"].append(kwargs)
            if fail_model and len(captures["calls"]) == 2:
                raise RuntimeError("private annual canary must not escape")
            return SimpleNamespace(
                time=SimpleNamespace(values=kwargs["time"]),
                h=SimpleNamespace(values=kwargs["h"]),
                Power=SimpleNamespace(
                    transpose=lambda *dims: SimpleNamespace(
                        values=np.full((4, len(kwargs["time"])), 1e6)
                    )
                ),
            )

        return model, None

    monkeypatch.setattr(source, "read_bytes", read)
    if native:
        original_backend = callback.kernel.wind_hourly._backend

        def native_backend():
            model, turbine = original_backend()

            def tracked(**kwargs):
                captures["calls"].append(kwargs)
                return model(**kwargs)

            return tracked, turbine

        monkeypatch.setattr(callback.kernel.wind_hourly, "_backend", native_backend)
    else:
        monkeypatch.setattr(callback.kernel.wind_hourly, "_backend", backend)
        monkeypatch.setattr(callback, "version", lambda name: "2.6.20")
    captures.update(
        store=store,
        grant=grant,
        service=service,
        model=manifest.cells[0].model,
        private=private,
        public=public,
        work=work,
    )
    return captures


def test_callback_executes_exact_frozen_layout_and_publishes_pinned_annual_work(
    tmp_path, monkeypatch
):
    context = setup(tmp_path, monkeypatch)
    receipt = context["service"].confirm(context["grant"])
    assert receipt.score.value == pytest.approx((35.136 + 35.04 + 35.04) / 3)
    assert len(context["calls"]) == len(context["reads"]) == 3
    assert all(call["x"][0] == 10.0 for call in context["calls"])
    artifact = context["scorer"].public_work(context["grant"], context["model"])
    proof = callback.AnnualWindWork.from_json(read_bytes(context["store"].root, artifact).decode())
    assert proof.attempted_model_starts == proof.completed_model_starts == 3
    assert proof.score == receipt.score
    assert proof.task_admitted is proof.private_boundary_qualified is False
    assert context["service"].confirm(context["grant"]) == receipt
    assert len(context["calls"]) == len(context["reads"]) == 3
    assert not any(
        ref.path.endswith(".f64le") for ref in context["scorer"].expected_model.source_bundle
    )


def test_model_failure_keeps_unknown_work_unattempted_year_and_no_retry(tmp_path, monkeypatch):
    context = setup(tmp_path, monkeypatch, fail_model=True)
    receipt = context["service"].confirm(context["grant"])
    artifact = context["scorer"].public_work(context["grant"], context["model"])
    proof = callback.AnnualWindWork.from_json(read_bytes(context["store"].root, artifact).decode())
    assert receipt.score.status == "model_failure" and receipt.score.value is None
    assert proof.attempted_model_starts == 2 and proof.completed_model_starts == 1
    assert proof.last_attempt_work_unknown is True
    assert [item.status for item in proof.run.results] == [
        "success",
        "model_failure",
        "not_attempted",
    ]
    assert len(context["calls"]) == 2 and len(context["reads"]) == 3
    assert "private annual canary" not in read_bytes(context["store"].root, artifact).decode()
    assert context["service"].confirm(context["grant"]) == receipt
    assert len(context["calls"]) == 2


@pytest.mark.parametrize("change", ["configuration", "allowance", "regime"])
def test_unqualified_configuration_budget_and_cost_regime_refuse_before_source(
    tmp_path, monkeypatch, change
):
    context = setup(tmp_path, monkeypatch, change=change)
    with pytest.raises(StoreError, match="uncertain"):
        context["service"].confirm(context["grant"])
    assert context["reads"] == context["calls"] == []
    with pytest.raises(StoreError, match="retry refused"):
        context["service"].confirm(context["grant"])


def lose_score_publication(context):
    def fail(stage):
        if stage == "confirmation_score_created":
            raise RuntimeError("authored suite score publication loss")

    context["store"].fault = fail
    with pytest.raises(RuntimeError, match="publication loss"):
        context["service"].confirm(context["grant"])
    context["store"].fault = lambda stage: None


def test_saved_work_recovers_commit_loss_without_weather_kernel_or_private_journal(
    tmp_path, monkeypatch
):
    context = setup(tmp_path, monkeypatch)
    lose_score_publication(context)
    assert len(context["calls"]) == len(context["reads"]) == 3
    with pytest.raises(StoreError, match="retry refused"):
        context["service"].confirm(context["grant"])

    def denied(*args, **kwargs):
        pytest.fail("recovery attempted private weather or a model")

    monkeypatch.setattr(source, "open_for_confirmation", denied)
    monkeypatch.setattr(callback.kernel, "score_annual", denied)
    monkeypatch.setattr(callback.kernel.wind_hourly, "_backend", denied)
    monkeypatch.setattr(callback, "version", denied)
    for path in context["private"].iterdir():
        path.unlink()  # Authored disposable fixture, not acquired data.
    private_kernel = context["work"] / context["grant"].digest / "kernel"
    for path in private_kernel.iterdir():
        path.unlink()
    recovered = context["service"].recover(context["grant"])
    assert recovered.score.status == "success"
    assert len(context["calls"]) == len(context["reads"]) == 3
    events = len(context["store"].replay()["events"])
    assert context["service"].confirm(context["grant"]) == recovered
    assert context["service"].recover(context["grant"]) == recovered
    assert len(context["store"].replay()["events"]) == events


@pytest.mark.parametrize("change", ["work_bytes", "read_metadata", "missing_anchor"])
def test_altered_or_missing_original_evidence_refuses_recovery_without_new_work(
    tmp_path, monkeypatch, change
):
    context = setup(tmp_path, monkeypatch)
    lose_score_publication(context)
    if change == "work_bytes":
        artifact = context["scorer"].public_work(context["grant"], context["model"])
        path = context["store"].root / artifact.path
        path.write_bytes(path.read_bytes() + b" ")
    elif change == "read_metadata":
        path = (
            context["store"].root
            / source.ACCESSES
            / f"{context['grant'].digest}-2012-complete.json"
        )
        path.write_bytes(path.read_bytes() + b" ")
    else:
        (context["work"] / context["grant"].digest / "complete.json").unlink()
    with pytest.raises(StoreError, match="unverified"):
        context["service"].recover(context["grant"])
    assert len(context["calls"]) == len(context["reads"]) == 3


def test_callback_anchor_loss_retains_charges_and_cannot_scan_for_a_new_pin(tmp_path, monkeypatch):
    context = setup(tmp_path, monkeypatch)
    original = callback.durable_write

    def lose(path, data, **kwargs):
        if path.name == "complete.json":
            raise OSError("authored callback anchor loss")
        return original(path, data, **kwargs)

    monkeypatch.setattr(callback, "durable_write", lose)
    with pytest.raises(StoreError, match="uncertain"):
        context["service"].confirm(context["grant"])
    monkeypatch.setattr(callback, "durable_write", original)
    with pytest.raises(StoreError, match="unverified"):
        context["service"].recover(context["grant"])
    assert len(context["calls"]) == len(context["reads"]) == 3


def test_wrong_dependency_refuses_before_private_weather_and_model(tmp_path, monkeypatch):
    context = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(callback, "version", lambda name: "0.0")
    with pytest.raises(StoreError, match="uncertain"):
        context["service"].confirm(context["grant"])
    assert context["calls"] == context["reads"] == []


@pytest.mark.parametrize(
    "changed",
    [
        "wind_annual_scoring.py",
        "wind_hourly.py",
        "wind_annual_callback.py",
        "wind_annual_source.py",
    ],
)
def test_declared_source_copy_cannot_substitute_code_for_the_actual_implementation(
    tmp_path,
    monkeypatch,
    changed,
):
    context = setup(tmp_path, monkeypatch)
    scorer = context["scorer"]
    other = tmp_path / "other-code"
    other.mkdir(mode=0o700)
    for ref in scorer.expected_model.source_bundle:
        target = other / ref.path
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes(read_bytes(ROOT, ref))
    path = other / "examples/utility" / changed
    path.write_bytes(path.read_bytes() + b"\n# changed declared implementation\n")
    with pytest.raises(ValueError, match="declared sources differ"):
        callback.model_snapshot(scorer.geometry, scorer.binding.plan, other)
    assert context["calls"] == context["reads"] == []
