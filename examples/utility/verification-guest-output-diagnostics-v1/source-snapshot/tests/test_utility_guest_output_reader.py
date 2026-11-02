"""Saved diagnostics cannot change producer ownership, byte bounds or starts."""

from copy import deepcopy
import hashlib

import pytest

from autoengineering.campaign.serialization import digest, canonical_json
from examples.utility import guest_output_diagnostics as producer, guest_output_reader as module
from test_utility_guest_resources import authored


def saved(root):
    source = producer.worker_source()
    q = {
        "schema": "utility-guest-output-diagnostics-v1",
        "sources": producer.sources(),
        "reader_sources": producer.reader_sources(),
        "limits": module.LIMITS,
        "worker_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "cases": [],
        "runtime_qualified": False,
        "owner_loss_cleanup_qualified": False,
    }
    results = []
    (root / "worker.py.txt").write_text(source)
    (root / "controller.py.txt").write_bytes(producer.Path(producer.__file__).read_bytes())
    for i, mode in enumerate(module.MODES):
        nonce = str(i) * 32
        cid = str(i + 1) * 64
        config = producer.configuration(mode, nonce)
        case = {"mode": mode, "nonce": nonce, "configuration_digest": digest(config)}
        q["cases"].append(case)
        work = root / mode
        work.mkdir(mode=0o700)
        before, _, _ = authored("read_only_root", image_id=module.policy.DERIVATIVE_IMAGE)
        before["HostConfig"] = config.pop("HostConfig")
        before["Config"] = config
        before.update(Id=cid, Name="/ae-guest-output-" + nonce)
        before["State"].update(Status="created", Running=False, Pid=0)

        def save(name, value):
            producer.fixture.save(work, name, value)

        save(
            "create-intent.json",
            {
                "name": "ae-guest-output-" + nonce,
                "configuration_digest": case["configuration_digest"],
            },
        )
        save("created.json", {"Id": cid})
        save("before.json", before)
        save("start-intent.json", {"container_id": cid, "starts": 1})
        save(
            "start-response.json",
            {"status": 204, "body_size": 0, "body_sha256": hashlib.sha256(b"").hexdigest()},
        )
        after = deepcopy(before)
        after["State"].update(Status="exited")
        save("after-refusal.json", after)
        save("cleanup-before.json", after)
        exception, message = module.MESSAGES[mode]
        refusal = {
            "exception": exception,
            "message": message,
            "stderr_bytes_discarded": 0,
            "stdout_bytes_accepted": len(module.RESPONSE_MAGIC)
            if i == 0
            else module.MAX_STDOUT - 16,
            "stdout_bytes_declared": len(module.RESPONSE_MAGIC)
            if i == 0
            else module.MAX_STDOUT + 16,
        }
        save("refusal.json", refusal)
        save("delete-intent.json", {"container_id": cid, "nonce": nonce})
        save("delete-response.json", {"status": 204, "body_size": 0})
        save(
            "cleanup.json",
            {"container_id": cid, "absent": True, "owner_loss_cleanup_qualified": False},
        )
        result = {
            "mode": mode,
            "container_id": cid,
            "container_creations": 1,
            "container_starts": 1,
            "refusal": refusal,
            "cleanup_absent": True,
            "scientific_starts": 0,
        }
        save("complete.json", result)
        results.append(result)
    pin = digest(q)
    producer.fixture.save(root, "request.json", q)
    producer.fixture.save(
        root, "execution-intent.json", {"request_digest": pin, "limits": module.LIMITS}
    )
    done = {
        "schema": "utility-guest-output-diagnostics-completion-v1",
        "request_digest": pin,
        "cases": results,
        "container_creations": 2,
        "container_starts": 2,
        "scientific_starts": 0,
        "runtime_qualified": False,
        "owner_loss_cleanup_qualified": False,
        "automatic_retries": 0,
    }
    producer.fixture.save(root, "complete.json", done)
    return dict(
        expected_request_digest=pin,
        expected_sources=q["sources"],
        expected_reader_sources=q["reader_sources"],
    ), done


def test_reconstruction_uses_saved_sources_without_live_source_fallback(tmp_path, monkeypatch):
    args, expected = saved(tmp_path)
    monkeypatch.setattr(module.policy, "worker_source", lambda: pytest.fail("source fallback"))
    assert module.read_completion(tmp_path, **args) == expected


@pytest.mark.parametrize(
    "mode,name,change",
    [
        ("oversized_stdout", "refusal.json", lambda v: v.update(stdout_bytes_declared=100)),
        (
            "oversized_stdout",
            "refusal.json",
            lambda v: v.update(stdout_bytes_accepted=producer.MAX_STDOUT + 1),
        ),
        ("malformed_stdio", "start-intent.json", lambda v: v.update(starts=True)),
        ("malformed_stdio", "before.json", lambda v: v["Config"].update(Entrypoint=["/bin/sh"])),
        ("malformed_stdio", "cleanup.json", lambda v: v.update(absent=False)),
        (
            "malformed_stdio",
            "cleanup-before.json",
            lambda v: v["HostConfig"].update(Binds=["/host:/work"]),
        ),
    ],
)
def test_altered_saved_diagnostic_refuses(mode, name, change, tmp_path):
    args, _ = saved(tmp_path)
    path = tmp_path / mode / name
    value = producer.fixture.read(path.parent, name)
    change(value)
    path.write_text(canonical_json(value))
    with pytest.raises(ValueError):
        module.read_completion(tmp_path, **args)


def test_wrong_caller_source_pins_refuse(tmp_path):
    args, _ = saved(tmp_path)
    args["expected_reader_sources"] = {}
    with pytest.raises(ValueError):
        module.read_completion(tmp_path, **args)
