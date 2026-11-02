"""Physical fake executables are gated by durable worker ownership records."""

import json
import sys
import threading
import time

import pytest

from autoengineering.agents.hosts.executable_fake import ExecutableFakeHost
from autoengineering.agents.scheduler import SerialScheduler
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.execution import ProcessIdentity, identity_matches, live_members
from autoengineering.campaign.store import StoreError
from test_agent_scheduler import setup


def program(tmp_path, *, sleep=False, empty=False):
    path = tmp_path / "trusted-worker"
    # Parse the resolved fixture prompt, not any executable candidate text.
    source = f"""#!{sys.executable}
import json,sys,time
from pathlib import Path
prompt=sys.stdin.read()
context=json.loads(prompt[prompt.index('{{"approved_evidence"'):])
Path({str(tmp_path / "started")!r}).touch()
"""
    if sleep:
        source += "time.sleep(20)\n"
    elif not empty:
        source += """
task=context['task']
evidence=context['approved_evidence'][0]['id']
record={'schema_version':'1.0','id':'fixture-handoff','task_id':task['id'],
 'invocation_id':context['invocation_id'],'role':'investigator','campaign_revision':task['campaign_revision'],
 'status':'complete','output':{'candidate_id':'candidate-1','target':'routing',
 'implementation_id':'linear','hypothesis':'Test supplied implementation',
 'expected_tradeoffs':'Measure the declared objective','evidence_ids':[evidence],'eligibility_gaps':[]},
 'supporting_artifact_ids':[evidence],'unresolved_issues':[],'proposed_next_action':'propose', 'supersedes':None}
print(json.dumps(record))
print('private fake executable diagnostic',file=sys.stderr)
"""
    path.write_text(source)
    path.chmod(0o700)
    return path


def scheduler(tmp_path, **kwargs):
    store, _, task, _ = setup(tmp_path)
    host = ExecutableFakeHost(program(tmp_path, **kwargs))
    return SerialScheduler(store, host, clock=lambda: 100), task


def test_running_receipt_and_separate_channels_are_digest_bound(tmp_path):
    worker, task = scheduler(tmp_path)
    result = worker.dispatch(task, campaign_revision=3)
    assert result.state == "completed" and result.schema_version == "1.2"
    assert (
        result.process_receipt
        and result.raw_response
        and result.final_response
        and result.stderr_response
    )
    identity = ProcessIdentity(**json.loads(read_bytes(worker.store.root, result.process_receipt)))
    assert identity.nonce == result.launch_nonce
    assert not live_members(identity.pgid)
    assert (
        read_bytes(worker.store.root, result.stderr_response)
        == b"private fake executable diagnostic\n"
    )
    assert worker.handoff(result).task_id == task.id
    assert any(
        getattr(event.record, "state", None) == "running" for event in worker.store.replay().events
    )
    assert worker.dispatch(task, campaign_revision=3) == result
    assert worker.host.cancel(result.id)
    reopened = WorkerStore(worker.store.root)
    assert reopened.replay().invocations[result.id] == result


def test_empty_physical_output_is_retained_as_invalid_output(tmp_path):
    worker, task = scheduler(tmp_path, empty=True)
    result = worker.dispatch(task, campaign_revision=3)
    assert result.state == "invalid_output"
    assert result.raw_response.size_bytes == 0
    assert read_bytes(worker.store.root, result.raw_response) == b""
    assert result.parse_failure is not None


def test_lost_launch_commit_ack_retains_ownership_and_cannot_start_executable(tmp_path):
    worker, task = scheduler(tmp_path)

    def fail(stage):
        if (
            stage == "after_event_commit"
            and getattr(worker.store.replay().events[-1].record, "state", None) == "running"
        ):
            raise RuntimeError("launch acknowledgment lost")

    worker.store.fault = fail
    result = worker.dispatch(task, campaign_revision=3)
    assert result.state == "reconciliation_required"
    assert result.process_receipt is not None
    assert not (tmp_path / "started").exists()
    identity = ProcessIdentity(**json.loads(read_bytes(worker.store.root, result.process_receipt)))
    assert not live_members(identity.pgid)
    with pytest.raises(StoreError, match="reconciliation"):
        SerialScheduler(WorkerStore(worker.store.root), worker.host, clock=lambda: 101).dispatch(
            task, campaign_revision=3
        )


def test_independent_cancel_inbox_stops_the_owned_executable(tmp_path):
    worker, task = scheduler(tmp_path, sleep=True)
    results = []
    errors = []

    def dispatch():
        try:
            results.append(worker.dispatch(task, campaign_revision=3))
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=dispatch)
    thread.start()
    deadline = time.monotonic() + 5
    while not (tmp_path / "started").exists() and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert (tmp_path / "started").exists()
    pending = WorkerStore(worker.store.root).replay().pending[0]
    identity = ProcessIdentity(**json.loads(read_bytes(worker.store.root, pending.process_receipt)))
    assert identity_matches(identity)
    from autoengineering.campaign.store import WriterBusy

    other = WorkerStore(worker.store.root)
    with other.writer():
        assert other.replay().pending[0].id == pending.id
    competing = SerialScheduler(other, worker.host, clock=lambda: 101)
    with pytest.raises(WriterBusy, match="operation"):
        competing.recover_invocation(pending.id, campaign_revision=3, stop_owned=True)
    assert identity_matches(identity)
    WorkerStore(worker.store.root).request_cancel()
    thread.join(timeout=5)
    assert not thread.is_alive() and not errors
    assert results[0].state == "cancelled"
    assert not live_members(identity.pgid)
    receipt = json.loads(read_bytes(worker.store.root, results[0].completion_receipt))
    assert receipt["stop_verified"] is True
    assert not results[0].usage


def test_lost_process_return_recovers_checksummed_output_without_rerun(tmp_path):
    worker, task = scheduler(tmp_path)
    invoke = worker.host.invoke_supervised

    def lose(*args):
        invoke(*args)
        raise RuntimeError("process return lost")

    worker.host.invoke_supervised = lose
    pending = worker.dispatch(task, campaign_revision=3)
    assert pending.state == "reconciliation_required" and pending.raw_response is None
    before = (tmp_path / "started").stat().st_mtime_ns
    worker.host.invoke_supervised = lambda *_: pytest.fail("duplicate physical start")
    recovered = worker.recover_invocation(pending.id, campaign_revision=3)
    assert recovered.state == "completed"
    assert recovered.recovery_receipt is not None
    assert recovered.completion_receipt == pending.completion_receipt
    assert (tmp_path / "started").stat().st_mtime_ns == before
    assert len(worker.store.replay().invocations) == 1
    assert worker.handoff(recovered).task_id == task.id


def test_corrupt_physical_output_cannot_be_recovered_as_a_handoff(tmp_path):
    worker, task = scheduler(tmp_path)
    invoke = worker.host.invoke_supervised

    def lose(*args):
        invoke(*args)
        raise RuntimeError("process return lost")

    worker.host.invoke_supervised = lose
    pending = worker.dispatch(task, campaign_revision=3)
    physical = worker.store.root / "processes" / pending.id
    (physical / "stdout.bin").write_bytes(b"changed")
    with pytest.raises(ValueError, match="mismatch"):
        worker.recover_invocation(pending.id, campaign_revision=3)
    assert worker.store.replay().pending[0].id == pending.id


def test_recovered_result_cannot_override_stale_scientific_revision(tmp_path):
    worker, task = scheduler(tmp_path)
    invoke = worker.host.invoke_supervised

    def lose(*args):
        invoke(*args)
        raise RuntimeError("process return lost")

    worker.host.invoke_supervised = lose
    pending = worker.dispatch(task, campaign_revision=3)
    recovered = worker.recover_invocation(pending.id, campaign_revision=4)
    assert recovered.state == "invalid_output"
    assert recovered.normalized_output is None and recovered.raw_response is not None
    assert recovered.parse_failure is not None
