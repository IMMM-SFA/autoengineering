"""Read pinned creator-termination controls without daemon queries or execution.

The manifest digest must be retained separately. This checks saved evidence and
its consistency, not independent OS/daemon attestation or runtime admission.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re

from autoengineering.utility import private_container_runtime as policy
from verify_utility_local_runtime_archive import read, decode, require


CONTROLS = tuple(
    (phase, kind, code)
    for phase in ("before-ack", "before-pipe", "after-arm")
    for kind, code in (("cancel", -15), ("owner-loss", -9))
)


def load(root, manifest_sha256):
    require(bool(re.fullmatch(r"[0-9a-f]{64}", manifest_sha256)), "invalid manifest digest")
    raw = read(root, "execution-files.json")
    require(hashlib.sha256(raw).hexdigest() == manifest_sha256, "manifest digest differs")
    manifest = decode(raw)
    require(isinstance(manifest, dict) and 0 < len(manifest) <= 256, "invalid owner archive size")
    files = {}
    for name, digest in manifest.items():
        require(isinstance(name, str) and isinstance(digest, str), "invalid owner manifest entry")
        require(
            Path(name).name not in ("job.json", "labels.json"),
            "owner-control archive must contain metadata only",
        )
        content = read(root, "executions/" + name)
        require(hashlib.sha256(content).hexdigest() == digest, "archive member digest differs")
        files[name] = content
    return files


def verify(root, manifest_sha256):
    files = load(root, manifest_sha256)
    ids = set()
    nonces = set()
    results = []
    for phase, kind, exit_code in CONTROLS:
        name = phase + "-" + kind

        def raw(member):
            return files[name + "/" + member]

        def document(member):
            return decode(raw(member))

        result = document("control-result.json")
        settings = document("control.json")
        termination = document("owner-termination-intent.json")
        pending = document("container/creation-pending.json")
        config = document("container/create-intent.json")
        cid, nonce = result["container_id"], pending["nonce"]
        require(
            bool(re.fullmatch(r"[0-9a-f]{64}", cid)) and cid not in ids and nonce not in nonces,
            "reused or invalid original identity",
        )
        ids.add(cid)
        nonces.add(nonce)
        require(
            result["name"] == name and result["phase"] == phase and settings["phase"] == phase,
            "owner control phase differs",
        )
        require(
            result["owner_exit"] == exit_code
            and settings["signal"] == -exit_code
            and termination == {"pid": result["owner_pid"], "signal": -exit_code, "phase": phase},
            "owner termination evidence differs",
        )
        require(type(result["owner_pid"]) is int and result["owner_pid"] > 0, "invalid owner PID")
        require(
            pending["configuration_sha256"] == policy.sha(policy.encode(config))
            and config == policy.configuration(nonce, "score", Path(pending["stage"])),
            "original creation configuration differs",
        )
        runtime_sha = policy.sha(raw("container/runtime.py"))
        wrapper_sha = policy.sha(raw("container/stage/private_container_worker.py"))
        worker_sha = policy.sha(raw("container/stage/private_score_worker.py"))
        identity = policy.sha(
            policy.encode(
                {
                    "profile": policy.PURPOSE,
                    "socket": settings["endpoint"],
                    "server": settings["server_sha256"],
                    "image": policy.IMAGE,
                    "runtime": runtime_sha,
                    "wrapper": wrapper_sha,
                    "worker": worker_sha,
                    "memory": policy.MEMORY,
                    "output": policy.OUTPUT,
                    "watchdog_seconds": 10,
                }
            )
        )
        require(
            pending["runtime_sha256"] == runtime_sha
            and pending["runtime_identity"] == settings["runtime_identity"] == identity,
            "executed runtime/source identity differs",
        )
        require(
            pending["socket_path"] == settings["endpoint"]
            and pending["api_version"] == settings["api_version"]
            and pending["job_sha256"] == settings["job_sha256"]
            and pending["labels_sha256"] == settings["labels_sha256"],
            "creator configuration binding differs",
        )
        require(document("transport-created.json")["container_id"] == cid, "transport ID differs")
        plan = {**pending, "container_id": cid}
        cleanup = document("container/cleanup.json")
        before = document("container/cleanup-before.json")
        policy.verify_owned(before, plan)
        require(
            before["State"]["Running"] is False
            and before["State"]["Status"] == "created"
            and before["State"]["Pid"] == 0,
            "original object started or stop is unverified",
        )
        require(
            cleanup["container_id"] == cid
            and cleanup["nonce"] == nonce
            and cleanup["removed"] is True,
            "original cleanup receipt differs",
        )
        require(
            result["nonce"] == nonce
            and result["created_objects"] == 1
            and result["container_starts"] == result["scoring_starts"] == 0
            and result["original_id_removed"] is True
            and result["live_absence_confirmed"] is True,
            "control outcome differs",
        )
        require(
            result["all_job_label_copies_deleted"] is True
            and not any(
                name + "/" + scope + "/" + field in files
                for scope in ("workspace", "container/stage")
                for field in ("job.json", "labels.json")
            ),
            "job/label copies remain in owner-control archive",
        )
        operations = [decode(line) for line in raw("creator-requests.jsonl").splitlines()]
        creates = [
            op
            for op in operations
            if op["method"] == "POST" and op["path"].startswith("/containers/create?")
        ]
        starts = [
            op for op in operations if op["method"] == "POST" and op["path"].endswith("/start")
        ]
        require(
            creates
            == [{"method": "POST", "path": "/containers/create?name=ae-private-rmse-" + nonce}],
            "creator made a replacement or foreign create request",
        )
        if phase == "before-ack":
            require(
                name + "/container/plan.json" not in files,
                "ID acknowledged before injected boundary",
            )
        else:
            require(document("container/plan.json") == plan, "acknowledged original plan differs")
        if phase == "after-arm":
            ready = document("container/watchdog-ready.json")
            require(
                starts == [{"method": "POST", "path": "/containers/" + cid + "/start"}]
                and result["start_attempt_recorded_but_not_forwarded"] is True,
                "armed start-delivery boundary differs",
            )
            require(
                ready["container_id"] == cid
                and ready["nonce"] == nonce
                and ready["watchdog_pid"] == result["watchdog_pid"],
                "watchdog binding differs",
            )
            require(
                cleanup["reason"] == "owner_pipe_eof" and result["observer_delete_requests"] == 0,
                "automatic owner-EOF cleanup is unverified",
            )
            policy.verify_owned(document("container/before-start.json"), plan)
        else:
            require(
                not starts
                and name + "/container/watchdog-ready.json" not in files
                and name + "/container/start-intent.json" not in files,
                "pre-arm control crossed the launch boundary",
            )
            require(
                cleanup["reason"] == "explicit_creation_reconciliation"
                and result["metadata_only_reconciliation"] is True,
                "explicit original-only reconciliation differs",
            )
            observed = result["observer_operations"]
            require(
                sum(op["method"] == "DELETE" for op in observed) == 1
                and all(op["method"] in ("GET", "DELETE") for op in observed),
                "observer performed a create/start or duplicate removal",
            )
            policy.verify_owned(document("external-before-cleanup.json"), plan)
        require(raw("creator.stdout") == raw("creator.stderr") == b"", "unexpected creator output")
        results.append({"name": name, "container_id": cid, "owner_exit": exit_code})
    return {
        "schema": "utility-creation-owner-offline-verification-v1",
        "manifest_sha256": manifest_sha256,
        "verified_files": len(files),
        "controls": results,
        "created_objects": 6,
        "container_starts": 0,
        "scoring_starts": 0,
        "live_absence_checked_now": False,
        "private_scoring_qualified": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    print(policy.encode(verify(args.archive, args.manifest_sha256)).decode())
