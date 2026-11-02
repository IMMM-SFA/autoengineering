"""Bounded prepared inputs and status without execution imports."""

from dataclasses import replace
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.identity import scientific_identity
from autoengineering.campaign.spec import CampaignSpec
from examples.agent_campaign import comparison as comp
from examples.agent_campaign import synthetic_comparison as synthetic
from test_agent_comparison import prepared as prepared, fork


def altered_arrays(root, plan, problem):
    source = root / "captured_source"
    path = source / "inputs/forcing.npz"
    values = synthetic.arrays()["forcing"]
    if problem == "object":
        np.savez(path, **{k: v.astype(object) for k, v in values.items()})
    elif problem == "member_size":
        np.savez_compressed(path, huge=np.zeros(8192))
    elif problem == "members":
        np.savez(path, **values, extra=np.zeros(1))
    elif problem == "compressed_size":
        path.write_bytes(path.read_bytes() + b"\0" * 65536)
    elif problem == "unsafe_name":
        content = io.BytesIO()
        np.save(content, np.ones(1))
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("../forcing.npy", content.getvalue())
    elif problem == "truncated":
        path.write_bytes(b"not a zip file")
    elif problem == "complex":
        np.savez(path, **{k: v.astype(np.complex64) for k, v in values.items()})
    else:
        raise AssertionError(problem)
    changed = reference(
        source,
        "inputs/forcing.npz",
        media_type="application/x-npz",
        producer="synthetic-comparison-author",
    )
    specs = []
    for case in plan.cases:
        original = CampaignSpec.from_yaml(root / case.scientific.path)
        specs.append(
            replace(
                original,
                data=tuple(
                    replace(d, artifact=changed) if d.id == "forcing" else d for d in original.data
                ),
            )
        )
    return specs


@pytest.mark.parametrize(
    "problem", ["object", "member_size", "members", "compressed_size", "unsafe_name", "truncated"]
)
def test_bad_archive_fails_before_numpy_allocation(prepared, tmp_path, monkeypatch, problem):
    root, plan = fork(prepared, tmp_path)
    specs = altered_arrays(root, plan, problem)
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("unsafe archive reached NumPy allocation")

    monkeypatch.setattr(np, "load", forbidden)
    with pytest.raises(ValueError):
        synthetic.verify(root, plan, specs)
    assert not calls and not Path(plan.runtime_root).exists()


def test_complex_values_cannot_pass_as_real_synthetic_inputs(prepared, tmp_path):
    root, plan = fork(prepared, tmp_path)
    specs = altered_arrays(root, plan, "complex")
    with pytest.raises(ValueError, match="real numeric"):
        synthetic.verify(root, plan, specs)
    assert not Path(plan.runtime_root).exists()


def test_repinning_malicious_input_does_not_start_a_clock(prepared, tmp_path):
    root, plan = fork(prepared, tmp_path)
    specs = altered_arrays(root, plan, "object")
    source = root / "captured_source"
    cases = []
    for case, spec in zip(plan.cases, specs):
        spec.to_yaml(root / case.scientific.path)
        worker = replace(case.worker, campaign_identity=scientific_identity(spec, source))
        cases.append(
            replace(
                case,
                worker=worker,
                scientific=reference(
                    root,
                    case.scientific.path,
                    media_type="application/yaml",
                    producer="comparison-preparation",
                ),
            )
        )
    input_path = "captured_source/inputs/forcing.npz"
    ref = reference(
        root, input_path, media_type="application/x-npz", producer="comparison-preparation"
    )
    plan = replace(
        plan,
        cases=tuple(cases),
        inputs=tuple(ref if r.path == input_path else r for r in plan.inputs),
        batch=replace(plan.batch, cases=comp.batch_cases(cases)),
    )
    (root / "comparison.json").write_text(plan.to_json())
    with pytest.raises(ValueError, match="object arrays"):
        comp.Runtime.create(root, expected_digest=plan.digest)
    assert not Path(plan.runtime_root).exists()


def test_status_cli_does_not_import_host_or_scientific_execution(prepared, tmp_path):
    root, plan = fork(prepared, tmp_path)
    runtime = comp.Runtime.create(root, expected_digest=plan.digest)
    program = """
import contextlib,io,json,runpy,sys
sys.argv = ['comparison','status','--runtime',sys.argv[1],'--runtime-digest',sys.argv[2]]
output = io.StringIO()
with contextlib.redirect_stdout(output):
    try:
        runpy.run_module('examples.agent_campaign.comparison', run_name='__main__')
    except SystemExit as error:
        assert error.code == 0, error.code
value = json.loads(output.getvalue())
assert value['status'] == 'ready' and value['scientific_reservations_charged'] == 0
for prefix in ('autoengineering.campaign.controller','autoengineering.campaign.runtime',
               'autoengineering.agents.hosts','autoengineering.agents.scheduler',
               'autoengineering.agents.broker','autoengineering.agents.batch_science',
               'examples.agent_campaign.comparison_runtime',
               'examples.agent_campaign.synthetic_comparison',
               'examples.campaign_contracts','examples.leaf_river.models','torch','openai'):
    assert not any(n == prefix or n.startswith(prefix + '.') for n in sys.modules), prefix
"""
    repo = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-P", "-c", program, str(runtime.batch.root), runtime.batch.digest],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": os.pathsep.join((str(repo / "src"), str(repo)))},
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_status_rejects_foreign_origin_and_does_not_open_preparation(
    prepared, tmp_path, monkeypatch
):
    root, plan = fork(prepared, tmp_path)
    runtime = comp.Runtime.create(root, expected_digest=plan.digest)

    def forbidden(*args, **kwargs):
        raise AssertionError("status tried to load arrays or its preparation")

    monkeypatch.setattr(np, "load", forbidden)
    monkeypatch.setattr(synthetic, "verify", forbidden)
    from examples.agent_campaign.comparison_status import read_report

    assert (
        read_report(runtime.batch.root, expected_digest=runtime.batch.digest)["status"] == "ready"
    )
    origin = runtime.batch.root / "origin.json"
    value = json.loads(origin.read_text())
    value["version"] = "conformance-runtime-1.0"
    origin.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="origin or kind"):
        read_report(runtime.batch.root, expected_digest=runtime.batch.digest)
