"""Offline inference input package tests; no package acquisition or execution."""

from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import socket
import stat
import subprocess
import zipfile

import pytest
import yaml

from autoengineering.campaign.artifacts import reference
from examples.utility import inference_environment as module


def inputs(tmp_path):
    tmp_path.chmod(0o700)
    records = []
    for name in (*module.ROOTS, "pytest"):
        version = "3.12.99" if name == "python" else "1.0"
        records.append(
            {
                "conda": "https://conda.anaconda.org/conda-forge/linux-64/"
                + f"{name}-{version}-0.conda",
                "sha256": hashlib.sha256(name.encode()).hexdigest(),
                "size": 100,
                "license": "BSD-3-Clause",
                "depends": ["__glibc >=2.28"] if name == "python" else ["python >=3.12"],
                "constrains": [],
            }
        )
    lock = {
        "version": 7,
        "platforms": [
            {
                "name": "linux-64",
                "virtual-packages": ["__linux=4.18", "__glibc=2.28", "__archspec=0=x86_64"],
            }
        ],
        "environments": {
            "default": {
                "packages": {
                    "linux-64": [{"conda": r["conda"]} for r in records] + [{"pypi": "./"}]
                }
            }
        },
        "packages": records + [{"pypi": "./", "name": "autoengineering"}],
    }
    (tmp_path / "pixi.lock").write_text(yaml.safe_dump(lock))
    buffer = io.BytesIO()
    requirements = "\n".join("Requires-Dist: " + name for name in module.ROOTS if name != "python")
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "autoengineering-0.2.0.dist-info/METADATA",
            "Name: autoengineering\nVersion: 0.2.0\nRequires-Python: <3.13,>=3.12\n"
            + requirements
            + "\n",
        )
        archive.writestr(
            "autoengineering-0.2.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        for name in ("inference_worker", "inference_execution"):
            archive.writestr(
                f"autoengineering/utility/{name}.py",
                b"# authored metadata fixture, never imported\n",
            )
    (tmp_path / "autoengineering-0.2.0-py3-none-any.whl").write_bytes(buffer.getvalue())
    return lock, refs(tmp_path)


def refs(root):
    return {
        "lock": reference(root, "pixi.lock", media_type="text/plain", producer="author"),
        "wheel": reference(
            root,
            "autoengineering-0.2.0-py3-none-any.whl",
            media_type="application/zip",
            producer="author",
        ),
    }


def test_prepares_exact_locked_closure_offline_and_never_overwrites(tmp_path, monkeypatch):
    _, arguments = inputs(tmp_path)

    def forbidden(*_a, **_k):
        pytest.fail("preparation tried acquisition, extraction or execution")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    output = tmp_path / "package"
    result = module.prepare_inputs(tmp_path, output=output, **arguments)
    assert tuple(p.name for p in result.archives) == module.ROOTS
    assert result.compressed_archive_bytes == 800
    assert result.virtual_constraints == ("__glibc >=2.28",)
    assert not result.starts_authorized and not result.runtime_qualified
    assert not result.dependency_constraints_rechecked
    assert len(result.wheel_python_sources) == 2
    assert (
        module.InferenceEnvironmentInputs.from_json((output / "manifest.json").read_text())
        == result
    )
    review = json.loads((output / "review.json").read_text())
    assert review["image_identity"] is None and review["starts_authorized"] is False
    assert any("guest contract" in b for b in review["blockers"])
    assert module.verify_inputs(output, expected_digest=result.digest) == result
    before = {str(p.relative_to(output)): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    with pytest.raises(FileExistsError):
        module.prepare_inputs(tmp_path, output=output, **arguments)
    assert {
        str(p.relative_to(output)): p.read_bytes() for p in output.rglob("*") if p.is_file()
    } == before


@pytest.mark.parametrize(
    "problem",
    [
        "schema",
        "schema_type",
        "remote_pypi",
        "url",
        "hash",
        "size",
        "missing",
        "duplicate",
        "python",
        "architecture",
        "local_project",
        "duplicate_local",
    ],
)
def test_bad_lock_refuses_before_publication(tmp_path, problem):
    lock, _ = inputs(tmp_path)
    selected = lock["environments"]["default"]["packages"]["linux-64"]
    if problem == "schema":
        lock["version"] = 8
    elif problem == "schema_type":
        lock["version"] = 7.0
    elif problem == "remote_pypi":
        selected.append({"pypi": "https://example.invalid/package.whl"})
    elif problem == "url":
        old = lock["packages"][0]["conda"]
        new = old.replace("conda.anaconda.org", "example.invalid")
        lock["packages"][0]["conda"] = new
        selected[0]["conda"] = new
    elif problem == "hash":
        lock["packages"][0]["sha256"] = "bad"
    elif problem == "size":
        lock["packages"][0]["size"] = True
    elif problem == "missing":
        lock["packages"][0]["depends"] = ["unavailable >=1"]
    elif problem == "duplicate":
        selected.append(dict(selected[0]))
    elif problem == "architecture":
        lock["platforms"][0]["virtual-packages"][-1] = "__archspec=0=arm64"
    elif problem == "local_project":
        lock["packages"][-1]["name"] = "unexpected"
    elif problem == "duplicate_local":
        selected.append({"pypi": "./"})
    else:
        record = next(r for r in lock["packages"] if "python-3.12" in r.get("conda", ""))
        old = record["conda"]
        record["conda"] = old.replace("3.12.99", "3.13.0")
        next(r for r in selected if r.get("conda") == old)["conda"] = record["conda"]
    (tmp_path / "pixi.lock").write_text(yaml.safe_dump(lock))
    with pytest.raises(ValueError):
        module.prepare_inputs(tmp_path, output=tmp_path / "out", **refs(tmp_path))
    assert not (tmp_path / "out").exists()


def test_duplicate_yaml_and_altered_pinned_bytes_refuse(tmp_path):
    _, arguments = inputs(tmp_path)
    path = tmp_path / "pixi.lock"
    path.write_bytes(path.read_bytes() + b"\nversion: 7\n")
    with pytest.raises(ValueError):
        module.prepare_inputs(tmp_path, output=tmp_path / "out", **refs(tmp_path))
    with pytest.raises(ValueError):
        module.prepare_inputs(tmp_path, output=tmp_path / "out", **arguments)
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize(
    "problem", ["traversal", "symlink", "oversize", "requirements", "metadata"]
)
def test_bad_wheel_refuses_before_publication(tmp_path, problem):
    inputs(tmp_path)
    path = tmp_path / "autoengineering-0.2.0-py3-none-any.whl"
    if problem in ("requirements", "metadata"):
        with zipfile.ZipFile(path) as old:
            content = {n: old.read(n) for n in old.namelist()}
        name = "autoengineering-0.2.0.dist-info/METADATA"
        if problem == "requirements":
            content[name] += b"Requires-Dist: unexpected\n"
        else:
            content[name] = content[name].replace(b"Name: autoengineering", b"Name: unexpected")
        with zipfile.ZipFile(path, "w") as new:
            for name, raw in content.items():
                new.writestr(name, raw)
    else:
        with zipfile.ZipFile(path, "a") as archive:
            if problem == "symlink":
                member = zipfile.ZipInfo("autoengineering/link")
                member.create_system = 3
                member.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(member, "outside")
            elif problem == "oversize":
                archive.writestr("autoengineering/big.py", b"x" * (1024 * 1024 + 1))
            else:
                archive.writestr("../outside.py", b"bad")
    with pytest.raises(ValueError):
        module.prepare_inputs(tmp_path, output=tmp_path / "out", **refs(tmp_path))
    assert not (tmp_path / "out").exists()


def test_interrupted_package_is_not_ready_and_cannot_be_replaced(tmp_path, monkeypatch):
    _, arguments = inputs(tmp_path)
    original = module.durable_write

    def interrupt(path, raw):
        if Path(path).name == "manifest.json":
            raise RuntimeError("authored manifest loss")
        return original(path, raw)

    monkeypatch.setattr(module, "durable_write", interrupt)
    output = tmp_path / "out"
    with pytest.raises(RuntimeError):
        module.prepare_inputs(tmp_path, output=output, **arguments)
    assert not (output / "manifest.json").exists() and (output / "review.json").is_file()
    with pytest.raises(FileExistsError):
        module.prepare_inputs(tmp_path, output=output, **arguments)


def test_execution_or_qualification_claim_cannot_be_added(tmp_path):
    _, arguments = inputs(tmp_path)
    result = module.prepare_inputs(tmp_path, output=tmp_path / "out", **arguments)
    for field in ("starts_authorized", "runtime_qualified", "dependency_constraints_rechecked"):
        with pytest.raises(ValueError):
            replace(result, **{field: True})


def test_symlinked_package_parent_refuses_without_creating_target(tmp_path):
    _, arguments = inputs(tmp_path)
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    linked = tmp_path / "linked"
    linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        module.prepare_inputs(tmp_path, output=linked / "out", **arguments)
    assert not (real / "out").exists()


@pytest.mark.parametrize("problem", ["manifest", "metadata", "payload", "review", "review_types"])
def test_cold_verifier_rejects_changed_pins_and_metadata(tmp_path, problem):
    _, arguments = inputs(tmp_path)
    output = tmp_path / "out"
    result = module.prepare_inputs(tmp_path, output=output, **arguments)
    expected = result.digest
    if problem == "manifest":
        expected = "f" * 64
    elif problem == "metadata":
        altered = replace(
            result, archives=(replace(result.archives[0], sha256="f" * 64), *result.archives[1:])
        )
        (output / "manifest.json").write_text(altered.to_json())
        expected = altered.digest
    elif problem == "payload":
        path = output / result.wheel.path
        path.write_bytes(path.read_bytes() + b"altered")
    else:
        path = output / "review.json"
        value = json.loads(path.read_text())
        if problem == "review_types":
            value["candidate_limits"]["cpu_count"] = True
        else:
            value["starts_authorized"] = True
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        module.verify_inputs(output, expected_digest=expected)
