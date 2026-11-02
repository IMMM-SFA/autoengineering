"""Reject numeric overflow in one unchanged guest worker using authored drivers.

Only the post-fitting temperature suffix changes. All inputs remain finite and
ordered. This is a numerical stress control, never an admitted meteorological
series. No fitting, scoring, image changes or retries are permitted.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import io
from pathlib import Path
import time

import numpy as np

from autoengineering.campaign.artifacts import put_bytes, read_arrays, reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import checked_directory, durable_write, StoreError
from autoengineering.utility.confirmation import read_selected_state
from autoengineering.utility.guest_archive import publisher_identity
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_executor import GuestRoutingExecutor
from autoengineering.utility.inference_execution import driver_limits
from autoengineering.utility.scoring import CompositeConfirmationGrant
from autoengineering.utility.store import SuiteStore
from examples.utility import guest_inference_smoke as fixture, guest_resources
from examples.utility.guest_owner_loss_controls import APIJournal

TEMPERATURES = {"tmin_c": 19999.0, "tmean_c": 20000.0, "tmax_c": 20001.0}
MEMBERS = {"precip_mm", "tmin_c", "tmean_c", "tmax_c", "day_of_year"}
LIMITS = {
    "container_creations": 1,
    "container_starts": 1,
    "inference_starts": 1,
    "fitting_starts": 0,
    "scoring_starts": 0,
    "automatic_retries": 0,
}


def overflow_suffix(original, prefix):
    """Copy five finite equal-length driver vectors, preserving the fitting prefix."""
    if set(original) != MEMBERS or type(prefix) is not int:
        raise ValueError("numeric control forcing members or prefix differ")
    arrays = {name: np.asarray(value) for name, value in original.items()}
    if (
        any(
            a.ndim != 1 or a.dtype.kind not in "fiu" or not np.isfinite(a).all()
            for a in arrays.values()
        )
        or len({len(a) for a in arrays.values()}) != 1
    ):
        raise ValueError("numeric control requires aligned finite numeric vectors")
    size = len(arrays["tmean_c"])
    if not 0 < prefix < size:
        raise ValueError("numeric control needs a nonempty post-fitting suffix")
    result = {name: value.astype(float, copy=True) for name, value in arrays.items()}
    for name, value in TEMPERATURES.items():
        result[name][prefix:] = value
    if (
        (result["precip_mm"] < 0).any()
        or (result["tmin_c"] > result["tmean_c"]).any()
        or (result["tmean_c"] > result["tmax_c"]).any()
    ):
        raise ValueError("numeric control violates input ordering or precipitation domain")
    return result


def helper_sources():
    return {
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in (
            "guest_numeric_control.py",
            "guest_inference_smoke.py",
            "guest_owner_loss_controls.py",
        )
    }


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
    store = SuiteStore(root / "suite")
    original = CompositeConfirmationGrant.from_dict(q["grant"])
    bound = read_selected_state(store.root, original.inference.selected_state)
    if bound.model.implementations.get("pet") != "hamon":
        raise ValueError("numeric control requires the frozen Hamon implementation")
    prefix = len(bound.model.inputs[0].time.dates)
    profile = fixture.read(store.root, bound.training.profile.path)
    fitting_rows = len(profile["fitting_dates"])
    if not 0 < fitting_rows <= prefix:
        raise ValueError("numeric control fitting axis differs from selected replay")
    arrays = read_arrays(
        root / "drivers",
        original.inference.forcing.artifact,
        limits=driver_limits(original.inference),
    )
    changed = overflow_suffix(arrays, prefix)
    prefix_digest = digest(
        {k: np.asarray(v[:fitting_rows], dtype=float).tolist() for k, v in arrays.items()}
    )
    changed_prefix = digest({k: v[:fitting_rows].tolist() for k, v in changed.items()})
    fit = fixture.read(store.root, bound.training.fit.path)
    if prefix_digest != changed_prefix or fit["fitting_forcing_digest"] != prefix_digest:
        raise ValueError("numeric control changed the original fitting prefix")
    buffer = io.BytesIO()
    np.savez(buffer, **changed)
    filename = "reserved/overflow-drivers.npz"
    durable_write(root / "drivers" / filename, buffer.getvalue())
    forcing = replace(
        original.inference.forcing,
        artifact=reference(
            root / "drivers", filename, media_type="application/x-npz", producer="authored-numeric"
        ),
    )
    grant = replace(original, inference=replace(original.inference, forcing=forcing))
    control = {
        "schema": "utility-guest-numeric-control-v1",
        "prepared_request_digest": digest(q),
        "scope_digest": digest(str(root)),
        "sources": helper_sources(),
        "grant": grant.to_dict(),
        "limits": LIMITS,
        "original_driver": original.inference.forcing.artifact.to_dict(),
        "fitting_rows": fitting_rows,
        "unchanged_selected_prefix_rows": prefix,
        "fitting_prefix_digest": prefix_digest,
        "input_rows": len(changed["tmean_c"]),
        "all_input_values_finite": True,
        "temperature_ordering_preserved": True,
        "changed_members": list(TEMPERATURES),
        "expected_status": "model_failure",
        "expected_outputs": None,
        "expected_predictions": None,
        "runtime_qualified": False,
        "independent_confirmation": False,
    }
    fixture.save(root, "numeric-request.json", control)
    durable_write(root / "controller.py.txt", Path(__file__).read_bytes())
    return control


def execute(root, *, expected_digest):
    root = checked_directory(root)
    control = fixture.read(root, "numeric-request.json")
    if (
        digest(control) != expected_digest
        or control.get("schema") != "utility-guest-numeric-control-v1"
        or control["scope_digest"] != digest(str(root))
        or control["sources"] != helper_sources()
        or control["limits"] != LIMITS
        or any(type(control["limits"][k]) is not int for k in LIMITS)
    ):
        raise ValueError("numeric control request, sources, scope or limits differ")
    marker = root / "numeric-execution-intent.json"
    if marker.exists() or marker.is_symlink():
        raise StoreError("numeric control consumed; saved-evidence recovery only")
    q, bindings = fixture.read(root, "request.json"), fixture.read(root, "bindings.json")
    if (
        digest(q) != control["prepared_request_digest"]
        or digest(bindings) != q["bindings_digest"]
        or fixture.build._endpoint(bindings["endpoint"]) != q["endpoint"]
    ):
        raise ValueError("numeric control prepared inputs differ")
    store = SuiteStore(root / "suite")
    grant = CompositeConfirmationGrant.from_dict(control["grant"])
    guest = guest_resources.validate_profile(q["guest"])
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
        guest=guest,
        environment=ArtifactRef.from_dict(q["environment"]),
        api=api,
        publisher_digest=publisher_identity(),
    )
    fixture.save(
        root,
        marker.name,
        {"request_digest": expected_digest, "grant_digest": grant.digest, "limits": LIMITS},
    )
    journal = APIJournal(api, root / "api", starts_allowed=1, create_allowed=1)
    with store.writer():
        args = dict(
            cell_digest=grant.cell_digest,
            attempt_id="confirmation-" + grant.cell_digest[:48],
            child_digest=grant.digest,
            phase="confirmation",
        )
        store.append(
            request_id="numeric-reserve", operation="reserve", resources=grant.resources, **args
        )
        store.append(request_id="numeric-start", operation="start", **args)
        access = put_bytes(
            store.root,
            grant.to_json().encode(),
            name="confirmation-grant.json",
            media_type="application/json",
            producer="authored-numeric",
        )
        store.append(
            request_id="numeric-access",
            operation="confirmation_access",
            result_digest=access.sha256,
            **args,
        )
        result = executor.execute(grant)
    fixture.save(root, "result.json", result.to_dict())
    if (
        result.status != "model_failure"
        or result.result is None
        or result.result.outputs is not None
        or result.result.predictions is not None
        or result.result.checks
        or journal.creations != 1
        or journal.starts != 1
    ):
        raise ValueError("numeric overflow did not preserve the required non-scoring failure")
    recovered = GuestRoutingExecutor.for_recovery(store, grant, root / "work").recover(grant)
    if recovered != result:
        raise ValueError("numeric control recovery differs")
    before = journal.calls
    with store.writer():
        try:
            executor.execute(grant)
        except StoreError as error:
            if (
                str(error)
                != "guest attempt already intended; explicit saved-evidence recovery only"
            ):
                raise
        else:
            raise ValueError("numeric control allowed redispatch")
    if journal.calls != before:
        raise ValueError("numeric redispatch refusal contacted the daemon")
    if api.inspect(result.container_id, deadline=time.monotonic() + 10) is not None:
        raise ValueError("numeric control container remains present")
    done = {
        "schema": "utility-guest-numeric-control-completion-v1",
        "request_digest": expected_digest,
        "grant_digest": grant.digest,
        "container_id": result.container_id,
        "container_absent": True,
        "container_creations": 1,
        "container_starts": 1,
        "charged_inference_starts": 1,
        "worker_status": result.result.status,
        "outputs": None,
        "predictions": None,
        "checks": [],
        "saved_recovery_equal": True,
        "retry_daemon_requests": 0,
        "fitting_starts": 0,
        "scoring_starts": 0,
        "parent_reserved_starts": 2,
        "parent_reservation_unfinished": True,
        "runtime_qualified": False,
        "independent_confirmation": False,
    }
    fixture.save(root, "complete.json", done)
    return done


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for name in ("fixture", "resources", "environment", "output"):
        prep.add_argument(name, type=Path)
    prep.add_argument("--resource-digest", required=True)
    run = sub.add_parser("execute")
    run.add_argument("root", type=Path)
    run.add_argument("--expected-digest", required=True)
    a = p.parse_args()
    value = (
        prepare(
            a.fixture,
            a.resources,
            a.environment,
            resource_digest=a.resource_digest,
            output=a.output,
        )
        if a.command == "prepare"
        else execute(a.root, expected_digest=a.expected_digest)
    )
    print(canonical_json({"schema": value["schema"], "digest": digest(value)}))


if __name__ == "__main__":
    main()
