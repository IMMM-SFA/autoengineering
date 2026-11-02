"""Inspect saved native Claude loopback evidence without contacting any runtime.

Authentication match is a trusted peer attestation. Synthetic reported token and
cost fields are fixture data, not measured provider work or actual billing.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex

from autoengineering.agents.hosts.claude import parse_result
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import unique_json
if __package__:
    from .verify_claude_policy_archive import MAX_BYTES, MAX_FILES, VERSION, digest
else:
    from verify_claude_policy_archive import MAX_BYTES, MAX_FILES, VERSION, digest


def inspect(root: Path, index_sha256: str) -> dict:
    index_path = confined_file(root, "archive.json")
    if index_path.stat().st_size > 1024 * 1024:
        raise ValueError("archive index exceeds bound")
    raw = index_path.read_bytes()
    if digest(raw) != index_sha256:
        raise ValueError("archive index digest mismatch")
    index = unique_json(raw.decode())
    entries = index.get("files")
    if (
        index.get("version") != VERSION or index.get("production_admission") is not False
        or not isinstance(entries, dict) or not 1 <= len(entries) <= MAX_FILES
    ):
        raise ValueError("unsupported bounded archive")
    refs = {name: ArtifactRef.from_dict(value) for name, value in entries.items()}
    total = sum(ref.size_bytes for ref in refs.values())
    if total > MAX_BYTES or total != index.get("total_bytes"):
        raise ValueError("archive size mismatch")
    if any(ref.path != name for name, ref in refs.items()):
        raise ValueError("archive reference name mismatch")
    data = {name: read_bytes(root, ref, max_bytes=MAX_BYTES) for name, ref in refs.items()}

    def obj(name):
        if name not in data:
            raise ValueError("missing pinned evidence")
        result = unique_json(data[name].decode())
        if not isinstance(result, dict):
            raise ValueError("evidence must be an object")
        return result

    report = obj("report.json")
    if (
        report.get("version") != "claude-controlled-peer-probe-1.1"
        or report.get("production_admission") is not False
        or type(report.get("provider_calls")) is not int or report["provider_calls"] != 0
        or type(report.get("scientific_calls")) is not int or report["scientific_calls"] != 0
        or report.get("native_helper_observed") is not True
        or report.get("transport_error") is not None
        or report.get("process_status") != "completed"
        or type(report.get("returncode")) is not int or report["returncode"] != 0
        or report.get("stopped") is not True
    ):
        raise ValueError("saved native roundtrip did not complete within its limited scope")
    completion = obj("native/completion.json")
    identity = obj("native/process.json")
    watchdog = obj("native/watchdog-job.json")
    stop = obj("native/watchdog-result.json")
    if (
        completion.get("schema_version") != "1.0" or completion.get("status") != "completed"
        or type(completion.get("returncode")) is not int or completion["returncode"] != 0
        or completion.get("stopped") is not True or completion.get("truncated") is not False
        or completion.get("identity") != identity
        or identity.get("nonce") != "claude-controlled-peer"
        or obj("native/intent.json") != {"nonce": "claude-controlled-peer"}
        or watchdog.get("target") != identity or stop.get("nonce") != watchdog.get("nonce")
        or stop.get("job_sha256") != digest(data["native/watchdog-job.json"])
        or stop.get("stopped") is not True or stop.get("reason") != "group_stopped"
    ):
        raise ValueError("inconsistent saved process/stop evidence")
    for name, suffix in (("job", ".json"), ("stdin", ".bin"), ("stdout", ".bin"), ("stderr", ".bin")):
        value = data["native/" + name + suffix]
        if completion.get(name + "_sha256") != digest(value):
            raise ValueError("saved process digest mismatch")
        if name in ("stdout", "stderr") and completion.get(name + "_bytes") != len(value):
            raise ValueError("saved process size mismatch")
    if report.get("job_sha256") != digest(data["native/job.json"]):
        raise ValueError("report/job digest mismatch")
    original = index["original_root"]
    spec = report["policy_specification"]
    job = obj("native/job.json")
    command = job.get("command")
    if (
        not isinstance(command, list)
        or command[:4] != ["/usr/bin/sandbox-exec", "-f", original + "/client.sb",
                           report["inventory"]["executable"]]
        or job.get("keep_group_leader") is not True or job.get("owner_lease") != "pipe-eof-v1"
        or job.get("environment") != {
            "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": spec["home"],
            "TMPDIR": spec["home"], "CLAUDE_CODE_TMPDIR": spec["home"],
        }
        or data.get("home/helper-observed") != b"synthetic helper executed"
    ):
        raise ValueError("native command/home/helper evidence mismatch")
    requests = report.get("requests")
    if not isinstance(requests, list) or len(requests) != 1:
        raise ValueError("probe did not retain exactly one authored-peer request")
    observed = requests[0]
    model = "claude-sonnet-4-6"
    try:
        settings = unique_json(command[command.index("--settings") + 1])
        helper = shlex.split(settings["apiKeyHelper"])
        port = spec["endpoints"][0]["port"]
        expected_settings = {
            "apiKeyHelper": settings["apiKeyHelper"], "disableAllHooks": True,
            "env": {"ANTHROPIC_BASE_URL": f"http://127.0.0.1:{port}"},
        }
        if (
            settings != expected_settings or len(helper) != 7
            or helper[:4] != [spec["python"], "-I", "-S", "-c"]
            or helper[-2:] != [spec["helper"], digest(data["auth/helper"])]
            or command[command.index("--model") + 1] != model
            or "--tools=" not in command or "--setting-sources=" not in command
            or "--bare" not in command or "--no-session-persistence" not in command
        ):
            raise ValueError("native fixed configuration mismatch")
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("incomplete native fixed configuration") from error
    request = obj("request-1.json")
    if (
        observed.get("sha256") != digest(data["request-1.json"])
        or observed.get("bytes") != len(data["request-1.json"])
        or observed.get("synthetic_auth_matched") is not True
        or observed.get("path") != "/v1/messages?beta=true"
        or observed.get("requested_model") != model or request.get("model") != model
        or observed.get("stream") is not True or request.get("stream") is not True
        or observed.get("tools") != request.get("tools")
        or [tool.get("name") for tool in request.get("tools", [])] != ["StructuredOutput"]
    ):
        raise ValueError("request/peer attestation mismatch")
    parsed = parse_result(data["native/stdout.bin"])
    if (
        parsed.rejection is not None or parsed.reported_models != (model,)
        or parsed.text != report.get("structured_output")
        or unique_json(parsed.text) != {"handoff_json": "synthetic controlled peer"}
    ):
        raise ValueError("native structured output mismatch")
    return {
        "status": "verified_saved_synthetic_roundtrip", "index_sha256": index_sha256,
        "source_identity": report["source_identity"], "native_helper_observed": True,
        "auth_match_basis": "trusted authored-peer attestation", "requests": 1,
        "structured_output": parsed.text, "saved_stop_verified": True,
        "live_process_state_checked": False, "production_admission": False,
        "provider_calls": 0, "scientific_calls": 0,
        "usage_and_estimated_cost_basis": "authored fixture; not measured provider work",
        "billed_cost_usd": None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--index-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.root, args.index_sha256), sort_keys=True))
