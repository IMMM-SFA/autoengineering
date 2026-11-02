"""Candidate policy validation, not actual-host qualification."""

from dataclasses import replace
from pathlib import Path
import sys

import pytest

from autoengineering.agents.hosts.claude_policy import (
    ClaudeEgress,
    ClaudePolicy,
    VERSION,
    render_claude_policy,
    _within,
)


def fixture(tmp_path):
    tmp_path.chmod(0o700)
    for name in ("workspace", "home", "runtime", "private", "auth", "bin"):
        (tmp_path / name).mkdir(mode=0o700)
    for name in ("runtime/python", "bin/client", "auth/helper", "auth/key"):
        (tmp_path / name).write_text("synthetic fixture")
    return ClaudePolicy(
        VERSION,
        str(tmp_path / "workspace"),
        str(tmp_path / "home"),
        str(tmp_path / "bin/client"),
        str(tmp_path / "auth/helper"),
        str(tmp_path / "runtime/python"),
        str(tmp_path / "runtime"),
        (str(tmp_path / "auth/key"),),
        (ClaudeEgress("localhost", 12345),),
        (str(tmp_path / "private"),),
    )


def test_policy_is_deny_default_with_exact_endpoint_and_credential_literal(tmp_path):
    spec = fixture(tmp_path)
    if sys.platform != "darwin":
        with pytest.raises(ValueError, match="unsupported"):
            render_claude_policy(spec)
        return
    text = render_claude_policy(spec)
    assert "(deny default)" in text and "(deny process-info*)" in text
    assert '(remote ip "localhost:12345")' in text
    assert '(literal "' + spec.credential_files[0] + '")' in text
    assert '(subpath "' + str(tmp_path / "auth") + '")' not in text
    assert '(subpath "' + str(tmp_path / "private") + '")' not in text
    assert '(literal "/bin/sh")' in text
    assert '(subpath "/bin")' not in text
    assert ClaudePolicy.from_json(spec.to_json()) == spec


@pytest.mark.parametrize(
    "address,port",
    [
        ("127.0.0.1", 1),
        ("::1", 1),
        ("127.000.0.1", 1),
        ("127.0.0.1", 0),
        ("127.0.0.1", 65536),
        ("127.0.0.1", True),
    ],
)
def test_noncanonical_or_unsupported_endpoint_refuses(address, port):
    with pytest.raises(ValueError):
        ClaudeEgress(address, port)


@pytest.mark.parametrize(
    "field", ["home", "python_root", "helper", "executable", "credential_files"]
)
def test_scope_overlaps_refuse_before_render(tmp_path, field):
    spec = fixture(tmp_path)
    bad = {
        "home": spec.workspace,
        "python_root": str(tmp_path),
        "helper": spec.credential_files[0],
        "executable": spec.credential_files[0],
        "credential_files": (spec.helper,),
    }[field]
    if field in ("helper", "executable"):
        target = tmp_path / "workspace" / "injected"
        target.write_text("fixture")
        bad = str(target)
    if field == "credential_files":
        bad = (str(tmp_path / "private" / "key"),)
        Path(bad[0]).write_text("fixture")
    with pytest.raises(ValueError):
        replace(spec, **{field: bad})


def test_private_checkout_need_not_be_owner_private_to_be_denied(tmp_path):
    spec = fixture(tmp_path)
    (tmp_path / "private").chmod(0o755)
    assert replace(spec, forbidden_roots=(str(tmp_path / "private"),)) == spec


def test_render_rejects_later_symlink_retargeting(tmp_path):
    spec = fixture(tmp_path)
    target = tmp_path / "auth/key"
    target.unlink()
    target.symlink_to(tmp_path / "private/labels")
    (tmp_path / "private/labels").write_text("synthetic labels")
    if sys.platform == "darwin":
        with pytest.raises(ValueError, match="symlink"):
            render_claude_policy(spec)


def test_case_alias_cannot_hide_private_overlap(tmp_path):
    spec = fixture(tmp_path)
    alias = tmp_path / "PRIVATE"
    if not alias.exists():
        pytest.skip("filesystem is case sensitive")
    nested = tmp_path / "private/workspace"
    nested.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="overlap"):
        replace(spec, workspace=str(nested), forbidden_roots=(str(alias),))


def test_overlap_checks_allow_absent_platform_runtime_paths(tmp_path):
    # Darwin's public runtime paths need not exist when records are read on Linux.
    missing = tmp_path / "missing/runtime"
    assert not _within(missing, tmp_path / "private")
    assert _within(missing, tmp_path)
    assert not _within(tmp_path, missing)
