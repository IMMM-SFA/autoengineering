"""Candidate edits cannot change baselines, dependencies or immutable capture bytes."""

from dataclasses import replace

import pytest

from autoengineering.agents.workspaces import CandidateWorkspace, WorkspacePolicy, inspect_source
from autoengineering.campaign.artifacts import read_bytes

BASE = b'def predict(inputs):\n    return {"prediction": inputs["forcing"]}\n'
EDIT = b'def predict(inputs):\n    return {"prediction": [1.5*x for x in inputs["forcing"]]}\n'


def workspace(tmp_path, *, max_bytes=65536):
    tmp_path.chmod(0o700)
    return CandidateWorkspace.create(
        tmp_path / "workspace",
        run_id="worker",
        task_id="implement",
        baseline={"adapter.py": BASE},
        policy=WorkspacePolicy("1.0", max_bytes=max_bytes),
    )


def test_valid_source_capture_is_immutable_and_baseline_is_unchanged(tmp_path):
    work = workspace(tmp_path)
    (work.candidate / "adapter.py").write_bytes(EDIT)
    capture = work.capture()
    assert not capture.issues
    assert capture.base_snapshot == work.manifest.digest
    assert read_bytes(work.root, work.manifest.base_sources["adapter.py"]) == BASE
    assert read_bytes(work.root, capture.sources["adapter.py"]) == EDIT
    assert b"+    return" in read_bytes(work.root, capture.patch)
    work.verify_capture(capture)
    (work.candidate / "adapter.py").write_bytes(b"changed after qualification")
    assert read_bytes(work.root, capture.sources["adapter.py"]) == EDIT
    work.verify_capture(capture)  # Only the immutable snapshot is verified.
    assert work.capture().source_digest != capture.source_digest
    (work.root / capture.sources["adapter.py"].path).write_bytes(b"tampered stored snapshot")
    with pytest.raises(ValueError, match="mismatch"):
        work.verify_capture(capture)


@pytest.mark.parametrize(
    "raw,reason",
    [
        (b"import os\ndef predict(inputs):\n return os.environ\n", "undeclared_import"),
        (b'def predict(inputs):\n return open("evaluator-labels").read()\n', "undeclared_call"),
        (
            b"import math\nmath.pi=42\ndef predict(inputs):\n return inputs\n",
            "undeclared_module_initialization",
        ),
        (
            b'print("module code")\ndef predict(inputs):\n return inputs\n',
            "undeclared_module_initialization",
        ),
        (b"def predict(other):\n return other\n", "predict_interface_changed"),
        (b"\x00\xffbinary", "invalid_python_source"),
    ],
)
def test_invalid_source_still_has_patch_and_immutable_bytes(tmp_path, raw, reason):
    work = workspace(tmp_path)
    (work.candidate / "adapter.py").write_bytes(raw)
    capture = work.capture()
    assert any(issue.startswith(reason) for issue in capture.issues)
    assert read_bytes(work.root, capture.sources["adapter.py"]) == raw
    assert capture.patch.size_bytes > 0
    work.verify_capture(capture)  # Integrity is distinct from eligibility.


def test_dependencies_undeclared_files_and_source_size_are_visible_failures(tmp_path):
    work = workspace(tmp_path, max_bytes=128)
    (work.candidate / "requirements.txt").write_text("arbitrary-new-package\n")
    (work.candidate / "huge.bin").write_bytes(b"x" * 129)
    capture = work.capture()
    assert "undeclared_file:requirements.txt" in capture.issues
    assert "source_limit:huge.bin" in capture.issues
    assert "adapter.py" in capture.sources
    with pytest.raises(ValueError):
        replace(work.manifest.policy, dependencies=("math",))
    assert capture.patch is not None


def test_symlinks_and_nested_directories_are_not_followed(tmp_path):
    work = workspace(tmp_path)
    secret = tmp_path / "private-labels"
    secret.write_bytes(b"not-worker-readable")
    (work.candidate / "adapter.py").unlink()
    (work.candidate / "adapter.py").symlink_to(secret)
    (work.candidate / "nested").mkdir()
    capture = work.capture()
    assert "nonregular_entry:adapter.py" in capture.issues
    assert "nonregular_entry:nested" in capture.issues
    assert not capture.sources
    assert b"not-worker-readable" not in read_bytes(work.root, capture.patch)


def test_workspace_manifest_and_snapshot_identities_cannot_be_rebased(tmp_path):
    work = workspace(tmp_path)
    capture = work.capture()
    with pytest.raises(ValueError, match="different workspace"):
        work.verify_capture(replace(capture, base_snapshot="0" * 64))
    (work.root / "manifest.json").write_text(replace(work.manifest, task_id="different").to_json())
    with pytest.raises(ValueError, match="manifest changed"):
        work.capture()


def test_initial_policy_allows_math_but_never_executes_imports():
    assert not inspect_source(
        b'import math\ndef predict(inputs):\n return {"prediction":math.fabs(inputs["x"])}\n'
    )
    assert "undeclared_runtime_access" in inspect_source(
        b"def predict(inputs):\n return inputs.__class__\n"
    )
    with pytest.raises(ValueError):
        WorkspacePolicy("1.0", allowed_files=("../evaluator.py",))
    with pytest.raises(ValueError):
        WorkspacePolicy("1.0", max_bytes=True)


def test_source_parser_recursion_is_a_captured_policy_failure(tmp_path, monkeypatch):
    import ast

    work = workspace(tmp_path)

    def fail(*_):
        raise RecursionError("bounded malformed source")

    monkeypatch.setattr(ast, "parse", fail)
    capture = work.capture()
    assert "invalid_python_source:adapter.py" in capture.issues
    assert read_bytes(work.root, capture.sources["adapter.py"]) == BASE
    assert capture.patch is not None
