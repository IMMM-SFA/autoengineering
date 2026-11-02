"""Offline paused-workload control verification; no daemon or model execution.

The caller must supply a separately retained manifest digest. Saved evidence is
checked for consistency, not independently attested or admitted for private use.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re

from autoengineering.utility import private_container_runtime as policy
from verify_utility_creation_owner_archive import load
from verify_utility_local_runtime_archive import decode, require


def verify(root, manifest_sha256, *, execution_timeout_only=False):
    files = load(root, manifest_sha256)
    ids = set()
    nonces = set()
    controls = []
    faults = (
        ("cancel", -15),
        ("owner-loss", -9),
        ("lost-start-ack", 0),
        ("deadline", 0),
    )
    if execution_timeout_only:
        faults = (("runtime-timeout", 0),)
    for fault, exit_code in faults:

        def raw(name):
            return files[fault + "/" + name]

        def document(name):
            return decode(raw(name))

        result = document("control-result.json")
        settings = document("control.json")
        plan = document("container/plan.json")
        pending = document("container/creation-pending.json")
        config = document("container/create-intent.json")
        cid, nonce = plan["container_id"], plan["nonce"]
        require(
            bool(re.fullmatch(r"[0-9a-f]{64}", cid)) and cid not in ids and nonce not in nonces,
            "invalid or reused original running identity",
        )
        ids.add(cid)
        nonces.add(nonce)
        require(plan == {**pending, "container_id": cid}, "original acknowledged plan differs")
        require(
            config == policy.configuration(nonce, "score", Path(plan["stage"]))
            and plan["configuration_sha256"] == policy.sha(policy.encode(config)),
            "original running configuration differs",
        )
        runtime_sha = policy.sha(raw("container/runtime.py"))
        identity = policy.sha(
            policy.encode(
                {
                    "profile": policy.PURPOSE,
                    "socket": settings["endpoint"],
                    "server": settings["server_sha256"],
                    "image": policy.IMAGE,
                    "runtime": runtime_sha,
                    "wrapper": policy.sha(raw("container/stage/private_container_worker.py")),
                    "worker": policy.sha(raw("container/stage/private_score_worker.py")),
                    "memory": policy.MEMORY,
                    "output": policy.OUTPUT,
                    "watchdog_seconds": 10,
                }
            )
        )
        require(
            plan["runtime_sha256"] == runtime_sha
            and plan["runtime_identity"] == identity
            and settings["runtime_identity"] == identity,
            "executed running source identity differs",
        )
        require(
            plan["socket_path"] == settings["endpoint"]
            and plan["api_version"] == settings["api_version"]
            and plan["job_sha256"] == settings["job_sha256"]
            and plan["labels_sha256"] == settings["labels_sha256"],
            "running control inputs differ",
        )
        before = document("running-before-pause.json")
        paused = document("paused-running.json")
        cleanup_before = document("container/cleanup-before.json")
        for observed in (before, paused, cleanup_before):
            policy.verify_owned(observed, plan)
            require(
                observed["State"]["Running"] is True
                and observed["State"]["Pid"] > 0
                and observed["RestartCount"] == 0,
                "original workload was not running once",
            )
        require(
            before["State"]["Paused"] is False
            and paused["State"]["Paused"] is True
            and cleanup_before["State"]["Paused"] is True
            and before["State"]["Pid"] == paused["State"]["Pid"] == cleanup_before["State"]["Pid"],
            "pause-induced hang evidence differs",
        )
        intent = document("running-fault-intent.json")
        require(
            intent
            == {
                "fault": fault,
                "owner_pid": result["owner_pid"],
                "container_id": cid,
                "nonce": nonce,
                "transport_start_status": 204,
                "paused": True,
            },
            "original start/fault witness differs",
        )
        reason = "deadline" if fault == "deadline" else "owner_pipe_eof"
        cleanup = document("container/cleanup.json")
        require(
            cleanup["container_id"] == cid
            and cleanup["nonce"] == nonce
            and cleanup["reason"] == reason
            and cleanup["removed"] is True,
            "automatic running cleanup differs",
        )
        require(
            result["fault"] == settings["fault"] == fault
            and result["owner_exit"] == exit_code
            and type(result["owner_pid"]) is int
            and result["owner_pid"] > 0,
            "running owner outcome differs",
        )
        require(
            result["container_id"] == cid
            and result["nonce"] == nonce
            and result["created_objects"] == result["container_starts"] == 1
            and result["scoring_child_starts"] is None
            and result["replacement_attempts"] == result["observer_delete_requests"] == 0
            and result["accepted_scientific_result"] is False
            and result["automatic_original_removal"] is True
            and result["cleanup_reason"] == reason
            and result["live_absence_confirmed"] is True,
            "running control result differs",
        )
        require(
            result["all_authored_input_copies_deleted"] is True
            and fault + "/container/result.json" not in files,
            "interrupted scoring supplied a result or retained input copies",
        )
        operations = [decode(line) for line in raw("creator-requests.jsonl").splitlines()]
        posts = [op["path"] for op in operations if op["method"] == "POST"]
        require(
            posts
            == [
                "/containers/create?name=ae-private-rmse-" + nonce,
                "/containers/" + cid + "/start",
                "/containers/" + cid + "/pause",
            ]
            and all(op["method"] in ("POST", "GET") for op in operations),
            "creator retried or performed cleanup instead of its watchdog",
        )
        if fault in ("deadline", "lost-start-ack", "runtime-timeout"):
            refused = document("expected-controller-refusal.json")
            require(
                refused
                == {
                    "fault": fault,
                    "type": "TimeoutError" if fault == "lost-start-ack" else "Refused",
                },
                "original uncertainty was not preserved",
            )
        require(
            raw("creator.stdout") == raw("creator.stderr") == b"",
            "unexpected running creator output",
        )
        controls.append(
            {"fault": fault, "container_id": cid, "owner_exit": exit_code, "cleanup_reason": reason}
        )
    return {
        "schema": "utility-running-container-offline-verification-v1",
        "manifest_sha256": manifest_sha256,
        "verified_files": len(files),
        "controls": controls,
        "container_starts": len(controls),
        "scoring_child_starts": None,
        "accepted_scientific_results": 0,
        "live_absence_checked_now": False,
        "private_scoring_qualified": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--execution-timeout-only", action="store_true")
    args = parser.parse_args()
    print(
        policy.encode(
            verify(
                args.archive,
                args.manifest_sha256,
                execution_timeout_only=args.execution_timeout_only,
            )
        ).decode()
    )
