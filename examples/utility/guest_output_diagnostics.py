"""Fixed real-daemon output diagnostics; no inference executor or model admission.

The production attach reader and bootstrap header parser consume two bounded
producers in the cached image. No worker selection, inputs or private labels.
Producer self-timeout bounds orphan work; owner-loss cleanup is not qualified.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
from pathlib import Path
import time
from uuid import uuid4

from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write, StoreError
from autoengineering.utility.guest_attach import attach, GuestAttachError, MAX_STDOUT
from autoengineering.utility.guest_bootstrap import (
    _header,
    RESPONSE_MAGIC,
    GuestBootstrapResponse,
    MAX_RESULT_HEADER,
)
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.contracts import sha256
from autoengineering.utility import guest_attach as transport, guest_bootstrap as framing
from examples.utility import guest_inference_smoke as fixture
from examples.utility import guest_resources as resources
from examples.utility import guest_resource_reader

MODES = ("malformed_stdio", "oversized_stdout")
PURPOSE = "utility-guest-output-diagnostic-v1"
LIMITS = {
    "container_creations": 2,
    "container_starts": 2,
    "scientific_starts": 0,
    "automatic_retries": 0,
    "active_seconds": 120,
    "case_seconds": 50,
    "cleanup_seconds": 10,
    "producer_seconds": 40,
}
EXPECTED = {
    "malformed_stdio": (StoreError, "guest transport frame version differs"),
    "oversized_stdout": (GuestAttachError, "guest attach stdout exceeds bound"),
}


def worker_source():
    # Only the already reviewed resource-context function is used. Its main is
    # disabled by a different __name__; the fixed output program follows it.
    source = resources.worker_source()
    return (
        "import os, signal, sys\n"
        "signal.signal(signal.SIGALRM, lambda *args: os._exit(70))\n"
        "signal.alarm(40)\n"
        "scope = {'__name__': 'resource_context'}\n"
        f"exec({source!r}, scope)\n"
        "scope['context']()\n"
        "mode, nonce = sys.argv[1:]\n"
        "if mode == 'malformed_stdio':\n"
        f"    os.write(1, b'?' * {len(RESPONSE_MAGIC)})\n"
        "elif mode == 'oversized_stdout':\n"
        f"    remaining = {MAX_STDOUT + 65536}\n"
        "    block = b'x' * 65536\n"
        "    while remaining:\n"
        "        written = os.write(1, block[:remaining])\n"
        "        remaining -= written\n"
        "else:\n"
        "    os._exit(71)\n"
    )


def configuration(mode, nonce):
    if mode not in MODES:
        raise ValueError("unknown output diagnostic")
    value = resources._configuration(
        "read_only_root", nonce, worker_source(), image_id=resources.DERIVATIVE_IMAGE
    )
    value["Cmd"] = [mode, nonce]
    value["Labels"]["org.autoengineering.purpose"] = PURPOSE
    value["Labels"]["org.autoengineering.diagnostic"] = mode
    return value


def verify_owned(value, mode, nonce, cid):
    """Check changed profile fields explicitly, then reuse the strict policy reader.

    The original observation remains untouched. Only verified naming/profile
    fields are normalized in a copy for the existing common limit/command checks.
    The actual entrypoint and exact fixed producer source are never normalized.
    """
    expected = configuration(mode, nonce)
    config = value.get("Config", {})
    if (
        value.get("Name") != "/ae-guest-output-" + nonce
        or config.get("Cmd") != expected["Cmd"]
        or config.get("Labels") != expected["Labels"]
    ):
        raise ValueError("output diagnostic ownership differs")
    projection = copy.deepcopy(value)
    projection["Name"] = "/ae-guest-resource-" + nonce
    projection["Config"]["Cmd"] = ["read_only_root", nonce]
    projection["Config"]["Labels"]["org.autoengineering.purpose"] = resources.PURPOSE
    projection["Config"]["Labels"]["org.autoengineering.diagnostic"] = "read_only_root"
    return resources.verify_owned(
        projection,
        "read_only_root",
        nonce,
        cid=cid,
        source=worker_source(),
        image_id=resources.DERIVATIVE_IMAGE,
    )


def sources():
    return {
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in ("guest_output_diagnostics.py", "guest_resources.py", "guest_resource_probe.py")
    }


def reader_sources():
    return {
        name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        for name, module in (("guest_attach.py", transport), ("guest_bootstrap.py", framing))
    }


def prepare(resource_root, *, resource_digest, output):
    resource_root = checked_directory(resource_root)
    guest_resource_reader.read_completion(resource_root, expected_digest=resource_digest)
    old = fixture.read(resource_root, "request.json")
    if old["profile"]["image_id"] != resources.DERIVATIVE_IMAGE:
        raise ValueError("output diagnostic requires the derivative resource evidence")
    binding = fixture.read(resource_root, "bindings.json")
    root = Path(output).absolute()
    fixture.build.guest_image._public_directory(root.parent)
    if root.exists() or root.is_symlink():
        raise ValueError("output diagnostic scope already exists")
    root.mkdir(mode=0o700)
    bindings = {"endpoint": binding["endpoint"], "scope": str(root)}
    cases = [{"mode": mode, "nonce": uuid4().hex} for mode in MODES]
    for case in cases:
        case["configuration_digest"] = digest(configuration(case["mode"], case["nonce"]))
    request = {
        "schema": "utility-guest-output-diagnostics-v1",
        "sources": sources(),
        "reader_sources": reader_sources(),
        "bindings_digest": digest(bindings),
        "resource_digest": resource_digest,
        "daemon": old["daemon"],
        "endpoint": old["endpoint"],
        "cases": cases,
        "limits": LIMITS,
        "worker_sha256": hashlib.sha256(worker_source().encode()).hexdigest(),
        "runtime_qualified": False,
        "owner_loss_cleanup_qualified": False,
    }
    fixture.save(root, "request.json", request)
    fixture.save(root, "bindings.json", bindings)
    durable_write(root / "controller.py.txt", Path(__file__).read_bytes())
    durable_write(root / "worker.py.txt", worker_source().encode())
    return request


def inspect(api, target, deadline):
    status, raw = api._request("GET", f"/containers/{target}/json", deadline=deadline)
    if status == 404:
        return None
    if status != 200:
        raise ValueError("output diagnostic inspection unverified")
    return unique_json(raw.decode())


def run_case(root, api, endpoint, case, *, overall_deadline):
    mode, nonce = case["mode"], case["nonce"]
    name = "ae-guest-output-" + nonce
    config = configuration(mode, nonce)
    if digest(config) != case["configuration_digest"]:
        raise ValueError("output diagnostic configuration differs")
    work = root / mode
    work.mkdir(mode=0o700)
    deadline = min(time.monotonic() + 50, overall_deadline - 10)
    fixture.save(work, "create-intent.json", {"name": name, "configuration_digest": digest(config)})
    cid = None
    session = None
    refusal = None
    observation = None
    try:
        created = api._json(
            "POST", "/containers/create?name=" + name, config, expected=201, deadline=deadline
        )
        fixture.save(work, "created.json", created)
        cid = created["Id"]
        sha256(cid)
        before = inspect(api, cid, deadline)
        fixture.save(work, "before.json", before)
        state = verify_owned(before, mode, nonce, cid)
        if state["Status"] != "created" or state["Running"] or state["Pid"] != 0:
            raise ValueError("output diagnostic already started")
        session = attach(endpoint, api.profile.api_version, cid, deadline=deadline)
        fixture.save(work, "start-intent.json", {"container_id": cid, "starts": 1})
        status, raw = api._request("POST", f"/containers/{cid}/start", deadline=deadline)
        fixture.save(
            work,
            "start-response.json",
            {
                "status": status,
                "body_size": len(raw),
                "body_sha256": hashlib.sha256(raw).hexdigest(),
            },
        )
        if status != 204 or raw:
            raise ValueError("output diagnostic START unverified")
        kind, message = EXPECTED[mode]
        try:
            if mode == "malformed_stdio":
                _header(session, RESPONSE_MAGIC, GuestBootstrapResponse, MAX_RESULT_HEADER)
            else:
                while session.read(65536):
                    pass
        except kind as error:
            if str(error) != message:
                raise
            refusal = {
                "exception": kind.__name__,
                "message": message,
                "stdout_bytes_accepted": session.stdout_bytes,
                "stdout_bytes_declared": session._declared_stdout,
                "stderr_bytes_discarded": session.stderr_bytes,
            }
            fixture.save(work, "refusal.json", refusal)
        else:
            raise ValueError("output diagnostic was unexpectedly accepted")
        if mode == "oversized_stdout" and not (
            session.stdout_bytes <= MAX_STDOUT < session._declared_stdout
        ):
            raise ValueError("output diagnostic did not cross the actual stream bound")
        observation = inspect(api, cid, deadline)
        fixture.save(work, "after-refusal.json", observation)
        verify_owned(observation, mode, nonce, cid)
    finally:
        if session is not None:
            session.close()
        cleanup_deadline = min(time.monotonic() + 10, overall_deadline)
        current = inspect(api, cid or name, cleanup_deadline)
        fixture.save(work, "cleanup-before.json", current)
        if current is not None:
            actual = current["Id"]
            verify_owned(current, mode, nonce, actual)
            fixture.save(work, "delete-intent.json", {"container_id": actual, "nonce": nonce})
            status, raw = api._request(
                "DELETE", f"/containers/{actual}?force=1&v=1", deadline=cleanup_deadline
            )
            fixture.save(work, "delete-response.json", {"status": status, "body_size": len(raw)})
            if status not in (204, 404):
                raise ValueError("output diagnostic cleanup unverified")
            if inspect(api, actual, cleanup_deadline) is not None:
                raise ValueError("output diagnostic original remains present")
        fixture.save(
            work,
            "cleanup.json",
            {"container_id": cid, "absent": True, "owner_loss_cleanup_qualified": False},
        )
    done = {
        "mode": mode,
        "container_id": cid,
        "container_creations": 1,
        "container_starts": 1,
        "refusal": refusal,
        "cleanup_absent": True,
        "scientific_starts": 0,
    }
    fixture.save(work, "complete.json", done)
    return done


def execute(root, *, expected_digest):
    root = checked_directory(root)
    q = fixture.read(root, "request.json")
    b = fixture.read(root, "bindings.json")
    if (
        digest(q) != expected_digest
        or q.get("schema") != "utility-guest-output-diagnostics-v1"
        or q["reader_sources"] != reader_sources()
        or len({c["nonce"] for c in q["cases"]}) != len(MODES)
        or q["sources"] != sources()
        or q["bindings_digest"] != digest(b)
        or b["scope"] != str(root)
        or q["limits"] != LIMITS
        or any(type(q["limits"][k]) is not int for k in LIMITS)
        or [c["mode"] for c in q["cases"]] != list(MODES)
        or fixture.build._endpoint(b["endpoint"]) != q["endpoint"]
    ):
        raise ValueError("output diagnostic request or scope differs")
    marker = root / "execution-intent.json"
    if marker.exists() or marker.is_symlink():
        raise StoreError("output diagnostics consumed; no retry")
    fixture.save(root, marker.name, {"request_digest": expected_digest, "limits": LIMITS})
    deadline = time.monotonic() + 120
    api = GuestDaemonAPI(
        b["endpoint"],
        api_version=q["daemon"]["api_version"],
        server_digest=q["daemon"]["server_digest"],
    )
    metadata_deadline = min(deadline, time.monotonic() + 10)
    server = api._json("GET", "/version", deadline=metadata_deadline)
    if digest(server) != q["daemon"]["server_digest"]:
        raise ValueError("diagnostic daemon changed")
    image = api._json(
        "GET", "/images/" + resources.DERIVATIVE_IMAGE + "/json", deadline=metadata_deadline
    )
    resources.verify_image(image, resources.DERIVATIVE_IMAGE)
    cases = [
        run_case(root, api, b["endpoint"], case, overall_deadline=deadline) for case in q["cases"]
    ]
    done = {
        "schema": "utility-guest-output-diagnostics-completion-v1",
        "request_digest": expected_digest,
        "cases": cases,
        "container_creations": 2,
        "container_starts": 2,
        "scientific_starts": 0,
        "runtime_qualified": False,
        "owner_loss_cleanup_qualified": False,
        "automatic_retries": 0,
    }
    fixture.save(root, "complete.json", done)
    return done


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("resources", type=Path)
    prep.add_argument("output", type=Path)
    prep.add_argument("--resource-digest", required=True)
    run = sub.add_parser("execute")
    run.add_argument("root", type=Path)
    run.add_argument("--expected-digest", required=True)
    a = p.parse_args()
    value = (
        prepare(a.resources, resource_digest=a.resource_digest, output=a.output)
        if a.command == "prepare"
        else execute(a.root, expected_digest=a.expected_digest)
    )
    print(canonical_json({"schema": value["schema"], "digest": digest(value)}))


if __name__ == "__main__":
    main()
