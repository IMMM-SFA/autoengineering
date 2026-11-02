"""Single-agent native transport with an actual pinned profile and authored replies.

This exercises four native CLI clients and two synthetic scientific executions.
No credential, provider or real model is used. Model names/usage in the authored
stream are fixture metadata and do not establish availability or agent utility.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from autoengineering.agents.hosts.brokered_host import BrokeredCodexHost
from autoengineering.agents.hosts.codex_brokered import inspect_brokered_codex
from autoengineering.agents.hosts.native_profile import verify_native_profile
from autoengineering.agents.hosts.scripted import single_supplied_reply
from autoengineering.agents.records import HostSelection, TaskAssignment
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import durable_write
from autoengineering.cli import cli
from examples.agent_campaign.check_brokered_scheduler_fixture import authored_stream, snapshot
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL
from examples.agent_campaign.run import prepare


def exercise(output, *, executable, qualification_root, qualification_digest):
    profile = verify_native_profile(qualification_root, expected_digest=qualification_digest)
    if profile.inventory != inspect_brokered_codex(executable) or profile.model != OFFLINE_MODEL:
        raise ValueError("single-agent fixture differs from pinned executable/model")
    output = Path(output).absolute()
    _, spec = prepare(output, workflow_route="single_agent")
    spec = replace(
        spec,
        host=HostSelection("codex", "subscription", OFFLINE_MODEL, "2.1", qualification_digest),
    )
    durable_write(output / "native-agent-run.json", spec.to_json().encode())
    config = {
        "schema_version": "1.0",
        "qualification_root": str(Path(qualification_root).absolute()),
        "qualification_digest": qualification_digest,
        "credential_path": str(output / "no-real-credential"),
        "lease_id": "offline-single-agent",
    }
    durable_write(
        output / "host.toml",
        "".join(f"{k} = {canonical_json(v)}\n" for k, v in config.items()).encode(),
    )
    calls = []

    def upstream(self, *_):
        def callback(raw):
            calls.append(raw)
            prompt = unique_json(raw.decode())["input"][0]["content"][0]["text"]
            context = unique_json(prompt[prompt.index('{"approved_evidence"') :])
            task = TaskAssignment.from_dict(context["task"])
            response = single_supplied_reply(task, prompt, context["invocation_id"])
            return authored_stream(canonical_json({"handoff_json": response.raw_output}))

        return callback

    print("Checking one-persona native transport with authored decisions", flush=True)
    args = [
        "agents",
        "run",
        str(output / "native-agent-run.json"),
        "--campaign",
        str(output / "campaign"),
        "--workdir",
        str(output / "worker"),
        "--host-config",
        str(output / "host.toml"),
    ]
    with patch.object(BrokeredCodexHost, "_upstream", new=upstream):
        result = CliRunner().invoke(cli, args)
        if result.exit_code != 0:
            raise ValueError("single-agent native CLI failed: " + result.stdout)
        report = unique_json(result.stdout)
        before = snapshot(output)
        replay = CliRunner().invoke(
            cli,
            [
                "agents",
                "resume",
                str(output / "worker"),
                "--campaign",
                str(output / "campaign"),
                "--host-config",
                str(output / "host.toml"),
            ],
        )
        status = CliRunner().invoke(cli, ["agents", "status", str(output / "worker")])
        reported = CliRunner().invoke(cli, ["agents", "report", str(output / "worker")])
        unchanged = snapshot(output) == before
    passed = (
        report["status"] == "completed"
        and report["run_digest"] == spec.digest
        and report["workflow_route"] == "single_agent"
        and report["roles_ran"] == ["single_agent"]
        and report["review_context"] == "self_review"
        and report["allowances"]["invocations_used"] == len(calls) == 4
        and report["physical_work"]["attempts"] == 2
        and not report["physical_work"]["cost_is_uncertain"]
        and report["scientific_evidence"]["selected_configuration"] == {"multiplier": 1.5}
        and report["scientific_evidence"]["objective_value"] == 0
        and replay.exit_code == status.exit_code == reported.exit_code == 0
        and unchanged
        and unique_json(replay.stdout) == unique_json(reported.stdout) == report
        and all(report[key] == value for key, value in unique_json(status.stdout).items())
        and not (output / "no-real-credential").exists()
    )
    receipt = {
        "status": "passed" if passed else "failed",
        "workflow_route": "single_agent",
        "worker_run_digest": spec.digest,
        "qualification_stubbed": False,
        "qualification_digest": qualification_digest,
        "native_clients": 4,
        "authored_callbacks": len(calls),
        "scientific_starts": 2,
        "provider_calls": 0,
        "real_credentials_used": False,
        "real_model_evidence": "not_attempted",
        "model_metadata": "authored_offline_stream",
        "review_context": "self_review",
        "replay_unchanged": unchanged,
        "independent_measured_data_confirmation": "not_attempted",
    }
    durable_write(output / "runtime-report.json", canonical_json(report).encode())
    durable_write(output / "single-agent-fixture-receipt.json", canonical_json(receipt).encode())
    print(f"Single-agent native fixture: {receipt['status']}", flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--qualification-digest", required=True)
    return 0 if exercise(**vars(parser.parse_args()))["status"] == "passed" else 4


if __name__ == "__main__":
    raise SystemExit(main())
