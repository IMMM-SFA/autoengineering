"""Six exposed-fixture refusal controls before driver access or guest dispatch.

These exercise the production facade with transport, process and array reads
blocked. They establish preflight behavior, not daemon or kernel enforcement.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, timedelta
import hashlib
import os
from pathlib import Path
import sys

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import checked_directory, StoreError
from autoengineering.utility.guest_archive import publisher_identity
from autoengineering.utility.guest_attach import GuestAttachCancelled
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_executor import GuestRoutingExecutor
from autoengineering.utility.scoring import CompositeConfirmationGrant
from autoengineering.utility.store import SuiteStore
from examples.utility import guest_inference_smoke as fixture

CASES = {
    "wrong_source": (ValueError, "artifact type/size mismatch"),
    "wrong_model": (StoreError, "confirmation model is not the sealed selection"),
    "wrong_fit_seed": (ValueError, "frozen inference seed differs from the original fit"),
    "wrong_axis": (ValueError, "frozen inference daily replay or initialization differs"),
    "wrong_partition": (StoreError, "confirmation data/outcome identity differs"),
    "cancel_before_access": (GuestAttachCancelled, "guest executor cancelled"),
}


def altered(grant, case):
    if case not in CASES:
        raise ValueError("unknown fixed preflight control")
    if case == "wrong_model":
        return replace(grant, model_digest="0" * 64)
    if case == "wrong_partition":
        return replace(grant, partition_digest="0" * 64)
    if case == "wrong_fit_seed":
        return replace(grant, inference=replace(grant.inference, seed=grant.inference.seed + 1))
    if case == "wrong_axis":
        ports = tuple(
            replace(
                port,
                time=replace(
                    port.time,
                    dates=tuple(
                        (date.fromisoformat(day) + timedelta(days=1)).isoformat()
                        for day in port.time.dates
                    ),
                ),
            )
            for port in grant.inference.forcing.ports
        )
        return replace(
            grant,
            inference=replace(
                grant.inference, forcing=replace(grant.inference.forcing, ports=ports)
            ),
        )
    return grant


class Guard:
    def __init__(self, drivers):
        self.drivers = str(Path(drivers).absolute()) + os.sep
        self.active = False
        self.counts = dict(driver_or_array_reads=0, daemon_requests=0, processes=0, sockets=0)

    def audit(self, event, args):
        if not self.active:
            return
        kind = None
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            name = os.fsdecode(args[0])
            if str(Path(name).absolute()).startswith(self.drivers) or name.endswith(".npz"):
                kind = "driver_or_array_reads"
        elif event in ("subprocess.Popen", "os.fork", "os.posix_spawn", "os.system", "os.exec"):
            kind = "processes"
        elif event in ("socket.__new__", "socket.connect", "socket.bind"):
            kind = "sockets"
        if kind:
            self.counts[kind] += 1
            raise RuntimeError("preflight control attempted forbidden " + kind)

    def request(self, *args, **kwargs):
        self.counts["daemon_requests"] += 1
        raise RuntimeError("preflight control attempted a daemon request")


def prepare(frozen_fixture, resources, environment, *, resource_digest, output):
    frozen_fixture = checked_directory(frozen_fixture)
    output = Path(output).absolute()
    fixture.build.guest_image._public_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("preflight output must be absent")
    output.mkdir(mode=0o700)
    requests = {}
    for case in CASES:
        q = fixture.prepare(
            frozen_fixture / "owner",
            frozen_fixture / "suite",
            frozen_fixture / "source",
            frozen_fixture / "drivers",
            resources,
            environment,
            resource_digest=resource_digest,
            output=output / case,
        )
        # Keep the prepared source and request unchanged. The intended fault is
        # injected once, after its own durable control intent during execution.
        requests[case] = digest(q)
    q = {
        "schema": "utility-guest-preflight-controls-v1",
        "case_requests": requests,
        "expected_refusals": {k: [c.__name__, m] for k, (c, m) in CASES.items()},
        "scope_digest": digest(str(output)),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "container_creations_allowed": 0,
        "container_starts_allowed": 0,
        "scientific_starts_allowed": 0,
        "driver_reads_allowed": 0,
        "automatic_retries": 0,
        "independent_confirmation": False,
    }
    fixture.save(output, "request.json", q)
    from autoengineering.campaign.store import durable_write

    durable_write(output / "runner.py.txt", Path(__file__).read_bytes())
    return q


def run_case(root, case):
    q, binding = fixture.read(root, "request.json"), fixture.read(root, "bindings.json")
    store = SuiteStore(root / "suite")
    grant = CompositeConfirmationGrant.from_dict(q["grant"])
    tested = altered(grant, case)
    api = GuestDaemonAPI(
        binding["endpoint"],
        api_version=q["daemon"]["api_version"],
        server_digest=q["daemon"]["server_digest"],
    )
    if api.profile.to_dict() != q["daemon"]:
        raise ValueError("preflight daemon implementation changed")
    guard = Guard(root / "drivers")
    api._request = guard.request
    executor = GuestRoutingExecutor(
        store,
        root / "source",
        root / "drivers",
        root / "work",
        sources=tuple(ArtifactRef.from_dict(v) for v in q["sources"]),
        lock=ArtifactRef.from_dict(q["lock"]),
        guest=fixture.guest_resources.validate_profile(q["guest"]),
        environment=ArtifactRef.from_dict(q["environment"]),
        api=api,
        publisher_digest=publisher_identity(),
    )
    fixture.save(
        root,
        "control-intent.json",
        {
            "case": case,
            "original_grant": grant.digest,
            "tested_grant": tested.to_dict(),
            "expected_exception": CASES[case][0].__name__,
            "expected_reason": CASES[case][1],
            "physical_starts_allowed": 0,
            "driver_reads_allowed": 0,
        },
    )
    if case == "wrong_source":
        path = root / "source/src/autoengineering/utility/inference_worker.py"
        with path.open("ab") as stream:
            stream.write(b"\n# authored preflight source mismatch\n")
    sys.addaudithook(guard.audit)
    with store.writer():
        args = dict(
            cell_digest=grant.cell_digest,
            attempt_id="confirmation-" + grant.cell_digest[:48],
            child_digest=grant.digest,
            phase="confirmation",
        )
        store.append(
            request_id="control-reserve", operation="reserve", resources=grant.resources, **args
        )
        store.append(request_id="control-start", operation="start", **args)
        ref = put_bytes(
            store.root,
            grant.to_json().encode(),
            name="confirmation-grant.json",
            media_type="application/json",
            producer="authored-preflight",
        )
        store.append(
            request_id="control-access",
            operation="confirmation_access",
            result_digest=ref.sha256,
            **args,
        )
        guard.active = True
        try:
            executor.execute(tested, cancelled=lambda: case == "cancel_before_access")
        except Exception as error:
            observed = [type(error).__name__, str(error)]
        else:
            observed = ["none", "unexpected success"]
        finally:
            guard.active = False
    expected = [CASES[case][0].__name__, CASES[case][1]]
    passed = observed == expected and all(v == 0 for v in guard.counts.values())
    result = {
        "case": case,
        "expected": expected,
        "observed": observed,
        "attempted_forbidden_operations": guard.counts,
        "passed": passed,
        "original_parent_reservation_retained": True,
        "physical_starts": 0,
    }
    fixture.save(root, "control-result.json", result)
    if not passed:
        raise ValueError("preflight control did not produce its exact expected refusal: " + case)
    return result


def execute(root, *, expected_digest):
    root = checked_directory(root)
    q = fixture.read(root, "request.json")
    if (
        digest(q) != expected_digest
        or q["scope_digest"] != digest(str(root))
        or q["runner_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        or q["expected_refusals"] != {k: [c.__name__, m] for k, (c, m) in CASES.items()}
        or tuple(q["case_requests"]) != tuple(sorted(CASES))
    ):
        raise ValueError("preflight control scope, source or request changed")
    for case in CASES:
        if digest(fixture.read(root / case, "request.json")) != q["case_requests"][case]:
            raise ValueError("prepared control changed")
    intent = root / "execution-intent.json"
    if intent.exists() or intent.is_symlink():
        raise ValueError("preflight controls consumed; no retries")
    fixture.save(
        root, "execution-intent.json", {"request_digest": expected_digest, "starts_allowed": 0}
    )
    results = [run_case(root / case, case) for case in CASES]
    done = {
        "schema": "utility-guest-preflight-completion-v1",
        "request_digest": expected_digest,
        "results": results,
        "all_passed": True,
        "physical_starts": 0,
        "driver_reads": 0,
        "daemon_requests": 0,
        "runtime_qualified": False,
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
    result = (
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
    print(canonical_json({"digest": digest(result), "schema": result["schema"]}))


if __name__ == "__main__":
    main()
