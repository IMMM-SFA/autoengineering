"""Fixed source catalogue rejects substitutions before any model import."""

from hashlib import sha256
import json

import pytest

from examples.utility import engineering_load_entrypoint as entry


def fixture(tmp_path):
    files = {}
    for name in entry.FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# authored source fixture\n")
        files[name] = sha256(path.read_bytes()).hexdigest()
    own = b"# authored entrypoint fixture\n"
    manifest = {
        "schema": "utility-coupled-entrypoint-source-v1",
        "entrypoint_sha256": sha256(own).hexdigest(),
        "files": files,
    }
    return own, manifest


def test_exact_source_bytes_and_entrypoint_required(tmp_path):
    own, manifest = fixture(tmp_path)
    result = entry.verify_sources(tmp_path, json.dumps(manifest).encode(), own)
    assert set(result) == set(entry.FILES)
    with pytest.raises(ValueError):
        entry.verify_sources(tmp_path, json.dumps(manifest).encode(), own + b"# changed")
    path = tmp_path / entry.FILES[0]
    path.write_bytes(path.read_bytes() + b"# substituted")
    with pytest.raises(ValueError):
        entry.verify_sources(tmp_path, json.dumps(manifest).encode(), own)


@pytest.mark.parametrize("change", ["extra", "missing", "unknown_schema", "duplicate"])
def test_manifest_cannot_select_extra_executable_paths(tmp_path, change):
    own, manifest = fixture(tmp_path)
    if change == "extra":
        manifest["files"]["../../private"] = "1" * 64
    elif change == "missing":
        del manifest["files"][entry.FILES[0]]
    elif change == "unknown_schema":
        manifest["schema"] = "untrusted"
    raw = json.dumps(manifest).encode()
    if change == "duplicate":
        raw = raw[:-1] + b',"files":{}}'
    with pytest.raises(ValueError):
        entry.verify_sources(tmp_path, raw, own)


@pytest.mark.parametrize("kind", ["symlink", "parent_symlink", "oversize", "directory"])
def test_source_files_must_be_regular_bounded_and_not_symlinked(tmp_path, kind):
    own, manifest = fixture(tmp_path)
    path = tmp_path / entry.FILES[0]
    if kind == "parent_symlink":
        actual = path.parent.with_name("saved-utility")
        path.parent.rename(actual)
        path.parent.symlink_to(actual, target_is_directory=True)
    else:
        path.unlink()
        if kind == "symlink":
            target = tmp_path / "replacement.py"
            target.write_bytes(b"# authored source fixture\n")
            path.symlink_to(target)
        elif kind == "oversize":
            path.write_bytes(b"x" * 131073)
        else:
            path.mkdir()
    with pytest.raises((ValueError, OSError)):
        entry.verify_sources(tmp_path, json.dumps(manifest).encode(), own)


def test_fixed_error_response_has_no_exception_or_private_path(monkeypatch, capsys):
    def fail(_):
        raise ValueError("PRIVATE-CANARY-/private/label.json")

    monkeypatch.setattr(entry, "execute", fail)
    assert entry.main(["1" * 64]) == 70
    assert json.loads(capsys.readouterr().out) == {
        "status": "refused",
        "private_boundary_qualified": False,
    }
