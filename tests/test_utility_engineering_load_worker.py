"""Packet tampering, private-output canaries and shared descriptor limits."""

from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from examples.utility import engineering_load_worker as worker

H = "1" * 64


def packet():
    return {
        "schema": "utility-coupled-load-packet-v1",
        "execution_digest": H,
        "source_binding_digest": "2" * 64,
        "model_digest": "3" * 64,
        "kernel_digest": "4" * 64,
        "source_current_A": 0.05,
        "minimum_node2_voltage_V": 0.62,
        "cases": [
            {
                "scenario_id": f"authored-{i}",
                "weight": 1 / 24,
                "forcing": {
                    "ground_voltage": 0.025,
                    "resistor1_ohm": 110.0,
                    "resistor2_ohm": 8000.0,
                },
            }
            for i in range(24)
        ],
    }


def encoded(value):
    raw = json.dumps(value, allow_nan=False).encode()
    return raw, sha256(raw).hexdigest()


def test_packet_pins_exact_bytes_and_rejects_new_entrypoints():
    value = packet()
    raw, pin = encoded(value)
    assert worker.parse_packet(raw, expected_sha256=pin) == value
    with pytest.raises(ValueError):
        worker.parse_packet(raw + b" ", expected_sha256=pin)
    value["entrypoint"] = "untrusted:run"
    raw, pin = encoded(value)
    with pytest.raises(ValueError):
        worker.parse_packet(raw, expected_sha256=pin)


@pytest.mark.parametrize(
    "change",
    [
        lambda p: p.update(source_current_A=True),
        lambda p: p.update(source_current_A=0.101),
        lambda p: p.update(source_current_A=10**400),
        lambda p: p.update(minimum_node2_voltage_V=False),
        lambda p: p.update(execution_digest="UPPERCASE"),
        lambda p: p["cases"].pop(),
        lambda p: p["cases"].append(deepcopy(p["cases"][0])),
        lambda p: p["cases"][1].update(scenario_id="authored-0"),
        lambda p: p["cases"][0].update(scenario_id="../../PRIVATE"),
        lambda p: p["cases"][0].update(weight=True),
        lambda p: p["cases"][0]["forcing"].update(resistor1_ohm=0),
        lambda p: p["cases"][0]["forcing"].update(resistor2_ohm=-1),
        lambda p: p["cases"][0]["forcing"].update(ground_voltage=True),
        lambda p: p["cases"][0]["forcing"].update(extra=1),
    ],
)
def test_packet_refuses_malformed_scientific_inputs(change):
    value = packet()
    change(value)
    raw, pin = encoded(value)
    with pytest.raises(ValueError):
        worker.parse_packet(raw, expected_sha256=pin)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"schema":1,"schema":2}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'"' + b"x" * worker.PACKET_BYTES + b'"',
        b"\xff",
        b"[]",
    ],
)
def test_packet_refuses_duplicate_nonfinite_oversized_and_non_object_json(raw):
    with pytest.raises(ValueError):
        worker.parse_packet(raw, expected_sha256=sha256(raw).hexdigest())


def receipt(failed=False):
    return {
        "execution_digest": H,
        "attempted_model_starts": 3 if failed else 24,
        "completed_model_starts": 2 if failed else 24,
        "known_completed_inner_work" if failed else "inner_work": {
            "solver_iterations": 96,
            "component_calls": 480,
            "derivative_calls": 0,
        },
        "PRIVATE-CANARY": {"scenario_id": "PRIVATE-ID", "forcing": [123456.789]},
    }


@pytest.mark.parametrize("failed", [False, True])
def test_bridge_calls_only_fixed_kernel_and_exports_no_private_receipt(
    tmp_path, monkeypatch, failed
):
    from examples.utility import engineering_load_scoring as kernel

    value = packet()
    value["kernel_digest"] = kernel.source_identity()
    raw, pin = encoded(value)
    calls = []

    def run(current, cases, root, source_root, *, policy, execution_digest):
        calls.append((current, cases, root, source_root, policy, execution_digest))
        (root / ("failed.json" if failed else "complete.json")).write_text(
            json.dumps(receipt(failed))
        )
        return SimpleNamespace(
            status="model_failure" if failed else "success",
            outcome="mean_source_power",
            units="W",
            value=None if failed else 0.25,
            feasible=None if failed else True,
        )

    monkeypatch.setattr(kernel, "score_loads", run)
    result = worker.score_packet(
        raw, expected_sha256=pin, source_root=tmp_path, private_work=tmp_path
    )
    assert len(calls) == 1 and calls[0][0] == 0.05 and len(calls[0][1]) == 24
    assert calls[0][4].expected_model_digest == value["model_digest"]
    assert result["last_attempt_inner_work_unknown"] is failed
    assert result["attempted_model_starts"] == (3 if failed else 24)
    assert "PRIVATE" not in json.dumps(result)
    assert not result["private_boundary_qualified"]


@pytest.mark.parametrize("kind", ["symlink", "oversize", "fifo", "execution"])
def test_receipt_replacement_cannot_export_a_score(tmp_path, monkeypatch, kind):
    from examples.utility import engineering_load_scoring as kernel

    def run(*args, **kwargs):
        path = tmp_path / "complete.json"
        if kind == "symlink":
            target = tmp_path / "PRIVATE.json"
            target.write_text(json.dumps(receipt()))
            path.symlink_to(target)
        elif kind == "fifo":
            os.mkfifo(path)
        elif kind == "oversize":
            path.write_bytes(b"x" * (worker.OUTPUT_BYTES + 1))
        else:
            changed = receipt()
            changed["execution_digest"] = "5" * 64
            path.write_text(json.dumps(changed))
        return SimpleNamespace(
            status="success", outcome="mean_source_power", units="W", value=0.25, feasible=True
        )

    monkeypatch.setattr(kernel, "score_loads", run)
    raw, pin = encoded(packet())
    with pytest.raises((ValueError, OSError)):
        worker.score_packet(raw, expected_sha256=pin, source_root=tmp_path, private_work=tmp_path)


@pytest.mark.parametrize("change", ["negative", "wrong_outcome", "work", "uncompleted"])
def test_invalid_score_or_work_receipt_is_not_public_success(change):
    score = SimpleNamespace(
        status="success", outcome="mean_source_power", units="W", value=0.25, feasible=True
    )
    work = receipt()
    if change == "negative":
        score.value = -1.0
    elif change == "wrong_outcome":
        score.outcome = "PRIVATE-CANARY"
    elif change == "work":
        work["inner_work"]["solver_iterations"] = True
    else:
        work["completed_model_starts"] = 23
    with pytest.raises(ValueError):
        worker._public_result(score, work, failed=False)


@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX output boundary")
def test_shared_stdout_stderr_hard_limit_never_exports_partial_output(tmp_path):
    small = worker.capture(
        b"", expected_sha256=H, source_root=tmp_path, private_work=tmp_path, mode="output-small"
    )
    assert small["captured_bytes"] == 4096 and not small["output_limited"]
    large = worker.capture(
        b"", expected_sha256=H, source_root=tmp_path, private_work=tmp_path, mode="output-overrun"
    )
    assert large["captured_bytes"] == worker.OUTPUT_BYTES
    assert large["output_limited"] and large["result"] is None
    assert small["result"] is None


@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX output boundary")
def test_child_keeps_only_fixed_single_thread_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVATE-ENVIRONMENT-CANARY", "must-not-survive")

    def run(*args, **kwargs):
        assert dict(os.environ) == worker.CHILD_ENVIRONMENT
        score = SimpleNamespace(
            status="success", outcome="mean_source_power", units="W", value=0.25, feasible=True
        )
        return worker._public_result(score, receipt(), failed=False)

    monkeypatch.setattr(worker, "score_packet", run)
    raw, pin = encoded(packet())
    result = worker.capture(raw, expected_sha256=pin, source_root=tmp_path, private_work=tmp_path)
    assert result["result"]["score"]["status"] == "success"


@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX output boundary")
@pytest.mark.parametrize("failure", ["exception", "print", "extra", "typed"])
def test_private_child_errors_and_unapproved_json_never_escape(tmp_path, monkeypatch, failure):
    def run(*args, **kwargs):
        if failure == "exception":
            raise ValueError("PRIVATE-EXCEPTION-CANARY")
        if failure == "print":
            os.write(2, b"PRIVATE-NATIVE-STDERR-CANARY")
        score = SimpleNamespace(
            status="success", outcome="mean_source_power", units="W", value=0.25, feasible=True
        )
        result = worker._public_result(score, receipt(), failed=False)
        if failure == "extra":
            result["PRIVATE-CANARY"] = 1234
        if failure == "typed":
            result["private_boundary_qualified"] = 0
        return result

    monkeypatch.setattr(worker, "score_packet", run)
    raw, pin = encoded(packet())
    result = worker.capture(raw, expected_sha256=pin, source_root=tmp_path, private_work=tmp_path)
    assert result["result"] is None and "PRIVATE" not in json.dumps(result)


@pytest.mark.skipif(importlib.util.find_spec("openmdao") is None, reason="optional OpenMDAO")
@pytest.mark.skipif(not hasattr(os, "fork"), reason="POSIX output boundary")
def test_real_authored_coupled_packet_without_scenario_output(tmp_path):
    from examples.utility import engineering_load as load
    from examples.utility import engineering_load_scoring as kernel

    source_root = Path(__file__).resolve().parents[1]
    value = packet()
    value["model_digest"] = load.context(0.05, tmp_path, source_root=source_root).model.digest
    value["kernel_digest"] = kernel.source_identity()
    raw, pin = encoded(value)
    result = worker.capture(
        raw, expected_sha256=pin, source_root=source_root, private_work=tmp_path
    )
    assert result["child_exit_code"] == 0
    assert result["result"]["score"]["status"] == "success"
    assert result["result"]["completed_model_starts"] == 24
    assert "authored-" not in json.dumps(result)
    assert len(list(tmp_path.glob("??-result.json"))) == 24
    (tmp_path / "public-worker-output.json").write_text(json.dumps(result, sort_keys=True))
