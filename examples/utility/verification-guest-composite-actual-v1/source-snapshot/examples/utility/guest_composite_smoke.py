"""One actual guest-to-container score chain on the existing authored selection.

A separate request reserves one inference and one scoring container, no fitting,
retry, provider call or real observations. Neither runtime gains admission.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import math
from pathlib import Path
import time

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import checked_directory, durable_write, StoreError
from autoengineering.utility.composite_scoring import (
    GuestCompositeRMSEScorer,
    GuestCompositeConfirmationService,
)
from autoengineering.utility.costs import join_confirmation_costs
from autoengineering.utility.guest_archive import publisher_identity
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_executor import GuestRoutingExecutor
from autoengineering.utility.outcomes import OutcomeSpec
from autoengineering.utility.private_container_runtime import FixedScorerRuntime
from autoengineering.utility.scoring import CompositeConfirmationGrant
from autoengineering.utility.store import SuiteStore
from examples.utility import guest_inference_smoke as fixture, guest_resources
from examples.utility.guest_owner_loss_controls import APIJournal


def controller_sources():
    return {
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in (
            "guest_composite_smoke.py",
            "guest_inference_smoke.py",
            "guest_owner_loss_controls.py",
        )
    }


def context(root):
    q, bindings = fixture.read(root, "request.json"), fixture.read(root, "bindings.json")
    store = SuiteStore(root / "suite")
    api = GuestDaemonAPI(
        bindings["endpoint"],
        api_version=q["daemon"]["api_version"],
        server_digest=q["daemon"]["server_digest"],
    )
    executor = GuestRoutingExecutor(
        store,
        root / "source",
        root / "drivers",
        root / "work",
        sources=tuple(ArtifactRef.from_dict(r) for r in q["sources"]),
        lock=ArtifactRef.from_dict(q["lock"]),
        guest=guest_resources.validate_profile(q["guest"]),
        environment=ArtifactRef.from_dict(q["environment"]),
        api=api,
        publisher_digest=publisher_identity(),
    )
    original = CompositeConfirmationGrant.from_dict(q["grant"])
    outcome = OutcomeSpec("engineering-outcome-v1", "rmse", "mm/day", "minimize", "mean", "1" * 64)
    if outcome.digest != original.outcome_digest:
        raise ValueError("authored outcome identity differs")
    runtime = FixedScorerRuntime(
        Path(bindings["endpoint"]), server_sha256=q["daemon"]["server_digest"]
    )
    labels = reference(
        root / "private",
        "labels.json",
        media_type="application/json",
        producer="authored-composite",
    )
    scorer = GuestCompositeRMSEScorer(
        executor,
        root / "private",
        labels=labels,
        runtime=runtime,
        inference=original.inference,
        partition_digest=original.partition_digest,
        outcome_contract=outcome,
    )
    grant = replace(original, scorer_digest=scorer.identity)
    service = GuestCompositeConfirmationService(
        store,
        scorer,
        scorer_digest=scorer.identity,
        outcome_contract=outcome,
    )
    return q, bindings, executor, grant, scorer, service


def prepare(frozen_fixture, resources, environment, *, resource_digest, output):
    frozen_fixture = checked_directory(frozen_fixture)
    q = fixture.prepare(
        frozen_fixture / "owner",
        frozen_fixture / "suite",
        frozen_fixture / "source",
        frozen_fixture / "drivers",
        resources,
        environment,
        resource_digest=resource_digest,
        output=output,
    )
    root = checked_directory(output)
    original = CompositeConfirmationGrant.from_dict(q["grant"])
    clock = original.inference.forcing.ports[0].time
    (root / "private").mkdir(mode=0o700)
    # Authored labels are deliberately unrelated to observations and model outputs.
    fixture.save(
        root / "private",
        "labels.json",
        {"labels": [0.0] * len(clock.dates), "mask": list(clock.scoring_mask)},
    )
    _, _, executor, grant, scorer, _ = context(root)
    control = {
        "schema": "utility-authored-guest-composite-smoke-v1",
        "prepared_request_digest": digest(q),
        "scope_digest": digest(str(root)),
        "sources": controller_sources(),
        "grant": grant.to_dict(),
        "registration": scorer.registration.to_dict(),
        "max_container_creations": 2,
        "max_container_starts": 2,
        "inference_starts_allowed": 1,
        "scoring_starts_allowed": 1,
        "fitting_starts_allowed": 0,
        "automatic_retries": 0,
        "parent_active_seconds_reserved": 94,
        "runtime_qualified": False,
        "inference_runtime_digest": executor.registration.runtime_digest,
        "scoring_runtime_digest": scorer.runtime.identity,
        "data_scope": "existing exposed authored drivers and newly authored zero labels",
    }
    fixture.save(root, "composite-request.json", control)
    durable_write(root / "controller.py.txt", Path(__file__).read_bytes())
    return control


def execute(root, *, expected_digest):
    root = checked_directory(root)
    control = fixture.read(root, "composite-request.json")
    if (
        digest(control) != expected_digest
        or control["scope_digest"] != digest(str(root))
        or control["sources"] != controller_sources()
        or control["schema"] != "utility-authored-guest-composite-smoke-v1"
    ):
        raise ValueError("composite request, controller or scope differs")
    limits = {
        "max_container_creations": 2,
        "max_container_starts": 2,
        "inference_starts_allowed": 1,
        "scoring_starts_allowed": 1,
        "fitting_starts_allowed": 0,
        "automatic_retries": 0,
        "parent_active_seconds_reserved": 94,
        "runtime_qualified": False,
    }
    if any(type(control[k]) is not type(v) or control[k] != v for k, v in limits.items()):
        raise ValueError("composite smoke limits differ")
    if (root / "composite-execution-intent.json").exists():
        raise StoreError("authored composite attempt consumed; saved evidence only")
    q, bindings, executor, grant, scorer, service = context(root)
    if (
        digest(q) != control["prepared_request_digest"]
        or grant.to_dict() != control["grant"]
        or scorer.registration.to_dict() != control["registration"]
        or digest(bindings) != q["bindings_digest"]
        or fixture.build._endpoint(bindings["endpoint"]) != q["endpoint"]
    ):
        raise ValueError("composite inputs or endpoint differ")
    if grant.inference.forcing.prior_exposure != "exposed":
        raise ValueError("composite smoke requires exposed authored inputs")
    fixture.save(
        root,
        "composite-execution-intent.json",
        {
            "request_digest": expected_digest,
            "grant_digest": grant.digest,
            "max_creations": 2,
            "max_starts": 2,
            "automatic_retries": 0,
        },
    )
    # Read-only runtime/image checks precede either actual launch or label staging.
    scorer.runtime.preflight()
    journal = APIJournal(executor.api, root / "inference-api", starts_allowed=1, create_allowed=1)
    result = service.confirm(grant)
    fixture.save(root, "composite-result.json", result.to_dict())
    if result.score.status != "success" or result.composite.inner_execution is None:
        raise ValueError("authored composite did not produce a complete successful score")
    child = result.composite.inner_execution
    inference = executor.recover(grant)
    if inference.status != "success" or inference.result is None:
        raise ValueError("authored inference completion differs")
    # Independent arithmetic over public predictions, not another scientific run.
    prediction = fixture.read(executor.store.root, inference.result.predictions.path)["prediction"]
    clock = grant.inference.forcing.ports[0].time
    kept = [v for v, keep in zip(prediction, clock.scoring_mask, strict=True) if keep]
    expected = math.sqrt(math.fsum(v * v for v in kept) / len(kept))
    if not math.isclose(result.score.value, expected, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError("authored score differs from independent public-vector arithmetic")
    before = journal.calls
    if service.confirm(grant) != result or service.recover(grant) != result:
        raise ValueError("saved composite replay differs")
    if journal.calls != before:
        raise ValueError("saved composite replay contacted inference daemon")
    costs = {r.resource: r.quantity for r in join_confirmation_costs(executor.store)}
    for key in (
        "confirmation_inference_starts",
        "confirmation_scoring_starts",
        "confirmation_inference_container_starts",
        "confirmation_scoring_container_starts",
    ):
        if costs[key] != 1:
            raise ValueError("authored composite physical counts differ")
    if costs["confirmation_container_starts"] != 2 or journal.creations != 1 or journal.starts != 1:
        raise ValueError("authored composite total starts differ")
    # Both production receipts include original cleanup. Verify absence separately.
    ids = [inference.container_id, child.container_id]
    for cid in ids:
        if executor.api.inspect(cid, deadline=time.monotonic() + 10) is not None:
            raise ValueError("original composite container remains present")
    done = {
        "schema": "utility-authored-guest-composite-smoke-completion-v1",
        "request_digest": expected_digest,
        "grant_digest": grant.digest,
        "result_digest": result.digest,
        "container_ids": ids,
        "containers_absent": True,
        "container_creations": 2,
        "container_starts": 2,
        "fitting_starts": 0,
        "inference_starts": 1,
        "scoring_starts": 1,
        "automatic_retries": 0,
        "independent_public_vector_parity": True,
        "costs": costs,
        "private_boundary_qualified": False,
        "runtime_qualified": False,
        "independent_confirmation": False,
    }
    fixture.save(root, "complete.json", done)
    return done


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for name in ("fixture", "resources", "environment", "output"):
        prep.add_argument(name, type=Path)
    prep.add_argument("--resource-digest", required=True)
    run = sub.add_parser("execute")
    run.add_argument("root", type=Path)
    run.add_argument("--expected-digest", required=True)
    args = parser.parse_args()
    value = (
        prepare(
            args.fixture,
            args.resources,
            args.environment,
            resource_digest=args.resource_digest,
            output=args.output,
        )
        if args.command == "prepare"
        else execute(args.root, expected_digest=args.expected_digest)
    )
    print(canonical_json({"schema": value["schema"], "digest": digest(value)}))


if __name__ == "__main__":
    main()
