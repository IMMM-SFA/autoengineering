"""Offline reconstruction of fixed output diagnostics from producer evidence.

No daemon, executable factory, model, source-file fallback or raw guest-output
loading. The caller pins the original request, producer sources and parser sources.
Saved observations attest producer-reported facts, not an independent OS audit.
"""

from __future__ import annotations

import copy
import hashlib

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory
from autoengineering.utility.guest_attach import MAX_STDOUT
from autoengineering.utility.guest_bootstrap import RESPONSE_MAGIC
from examples.utility import guest_resources as policy

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
MESSAGES = {
    "malformed_stdio": ("StoreError", "guest transport frame version differs"),
    "oversized_stdout": ("GuestAttachError", "guest attach stdout exceeds bound"),
}


def _read(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 1024**2:
        raise ValueError("output evidence exceeds bound")
    raw = path.read_bytes()
    if len(raw) > 1024**2:
        raise ValueError("output evidence exceeds bound")
    return raw


def _json(root, name):
    return unique_json(_read(root, name).decode())


def _same(left, right):
    return canonical_json(left) == canonical_json(right)


def _configuration(mode, nonce, source):
    expected = policy._configuration(
        "read_only_root", nonce, source, image_id=policy.DERIVATIVE_IMAGE
    )
    expected["Cmd"] = [mode, nonce]
    expected["Labels"]["org.autoengineering.purpose"] = PURPOSE
    expected["Labels"]["org.autoengineering.diagnostic"] = mode
    return expected


def _owned(value, mode, nonce, cid, source):
    expected = _configuration(mode, nonce, source)
    config = value.get("Config", {})
    if (
        value.get("Name") != "/ae-guest-output-" + nonce
        or config.get("Cmd") != expected["Cmd"]
        or config.get("Labels") != expected["Labels"]
    ):
        raise ValueError("saved output ownership differs")
    projected = copy.deepcopy(value)
    projected["Name"] = "/ae-guest-resource-" + nonce
    projected["Config"]["Cmd"] = ["read_only_root", nonce]
    projected["Config"]["Labels"]["org.autoengineering.purpose"] = policy.PURPOSE
    projected["Config"]["Labels"]["org.autoengineering.diagnostic"] = "read_only_root"
    return policy.verify_owned(
        projected, "read_only_root", nonce, cid=cid, source=source, image_id=policy.DERIVATIVE_IMAGE
    )


def read_completion(root, *, expected_request_digest, expected_sources, expected_reader_sources):
    root = checked_directory(root)
    q = _json(root, "request.json")
    if (
        digest(q) != expected_request_digest
        or q.get("runtime_qualified") is not False
        or q.get("owner_loss_cleanup_qualified") is not False
        or q["schema"] != "utility-guest-output-diagnostics-v1"
        or not _same(q["limits"], LIMITS)
        or q["sources"] != expected_sources
        or q["reader_sources"] != expected_reader_sources
        or [c["mode"] for c in q["cases"]] != list(MODES)
        or len({c["nonce"] for c in q["cases"]}) != 2
    ):
        raise ValueError("saved output request differs from explicit caller pins")
    source = _read(root, "worker.py.txt").decode()
    if (
        hashlib.sha256(source.encode()).hexdigest() != q["worker_sha256"]
        or hashlib.sha256(_read(root, "controller.py.txt")).hexdigest()
        != q["sources"]["guest_output_diagnostics.py"]
    ):
        raise ValueError("saved output producer source differs")
    intent = _json(root, "execution-intent.json")
    if not _same(intent, {"request_digest": expected_request_digest, "limits": LIMITS}):
        raise ValueError("saved output execution intent differs")
    cases = []
    container_ids = set()
    for case in q["cases"]:
        mode, nonce = case["mode"], case["nonce"]

        def read(name):
            return _json(root, mode + "/" + name)

        config = _configuration(mode, nonce, source)
        if digest(config) != case["configuration_digest"]:
            raise ValueError("saved output configuration differs")
        if not _same(
            read("create-intent.json"),
            {"name": "ae-guest-output-" + nonce, "configuration_digest": digest(config)},
        ):
            raise ValueError("saved output creation intent differs")
        cid = read("created.json")["Id"]
        if cid in container_ids:
            raise ValueError("saved output cases duplicate one container")
        container_ids.add(cid)
        before = _owned(read("before.json"), mode, nonce, cid, source)
        if before["Status"] != "created" or before["Running"] or before["Pid"] != 0:
            raise ValueError("saved output did not start from created")
        if not _same(read("start-intent.json"), {"container_id": cid, "starts": 1}):
            raise ValueError("saved output start count differs")
        if not _same(
            read("start-response.json"),
            {"status": 204, "body_size": 0, "body_sha256": hashlib.sha256(b"").hexdigest()},
        ):
            raise ValueError("saved output START was not acknowledged")
        refusal = read("refusal.json")
        if set(refusal) != {
            "exception",
            "message",
            "stdout_bytes_accepted",
            "stdout_bytes_declared",
            "stderr_bytes_discarded",
        }:
            raise ValueError("saved output refusal fields differ")
        if (refusal["exception"], refusal["message"]) != MESSAGES[mode]:
            raise ValueError("saved output refused at a different boundary")
        accepted, declared, stderr = (
            refusal[k]
            for k in ("stdout_bytes_accepted", "stdout_bytes_declared", "stderr_bytes_discarded")
        )
        if any(type(v) is not int or v < 0 for v in (accepted, declared, stderr)) or stderr != 0:
            raise ValueError("saved output byte counts differ")
        if mode == "malformed_stdio":
            if accepted != len(RESPONSE_MAGIC) or declared != accepted:
                raise ValueError("saved malformed payload count differs")
        elif not 0 < accepted <= MAX_STDOUT < declared <= MAX_STDOUT + 65536:
            raise ValueError("saved oversized stream did not cross the bound")
        _owned(read("after-refusal.json"), mode, nonce, cid, source)
        _owned(read("cleanup-before.json"), mode, nonce, cid, source)
        if not _same(read("delete-intent.json"), {"container_id": cid, "nonce": nonce}):
            raise ValueError("saved output cleanup intent differs")
        if not _same(read("delete-response.json"), {"status": 204, "body_size": 0}):
            raise ValueError("saved output DELETE was not acknowledged")
        if not _same(
            read("cleanup.json"),
            {"container_id": cid, "absent": True, "owner_loss_cleanup_qualified": False},
        ):
            raise ValueError("saved output original cleanup differs")
        result = {
            "mode": mode,
            "container_id": cid,
            "container_creations": 1,
            "container_starts": 1,
            "refusal": refusal,
            "cleanup_absent": True,
            "scientific_starts": 0,
        }
        if not _same(read("complete.json"), result):
            raise ValueError("saved output case summary differs")
        cases.append(result)
    expected = {
        "schema": "utility-guest-output-diagnostics-completion-v1",
        "request_digest": expected_request_digest,
        "cases": cases,
        "container_creations": 2,
        "container_starts": 2,
        "scientific_starts": 0,
        "runtime_qualified": False,
        "owner_loss_cleanup_qualified": False,
        "automatic_retries": 0,
    }
    if not _same(_json(root, "complete.json"), expected):
        raise ValueError("saved output completion differs")
    return expected
