"""Trusted registration and standalone lifecycle checks with a fake container executor."""

from dataclasses import replace
import hashlib
import io
import json
import shutil
import zipfile

import numpy as np
import pytest

from autoengineering.adapters.contracts import AdapterRegistry, PrepareContext
from autoengineering.adapters.isolated import registration_entry
from autoengineering.adapters.python import run_lifecycle
from autoengineering.adapters.registration import (
    AdmissionReview,
    extract_archive,
    load_registration,
)
from autoengineering.agents.admission import register_candidate
from autoengineering.agents.interface import check_interface
from autoengineering.campaign.records import ModelSnapshot
from autoengineering.campaign.serialization import digest
from test_agent_interface import run as run


def approved(run, receipt):
    return AdmissionReview(
        "1.0",
        "response",
        run.capture.digest,
        receipt.digest,
        run.options["qualification_digest"],
        {},
        "unit-test-caller",
        "Explicit fixture approval of the exact source and checks",
        "approve",
    )


def stage(run, tmp_path, review_change=None):
    q = run.options["qualification_root"]
    q.mkdir(mode=0o700)
    (q / "manifest.json").write_text("{}")
    (q / "qualification.json").write_text("{}")
    receipt = check_interface(run.work, run.capture, run.spec, **run.options)
    review = approved(run, receipt)
    if review_change:
        review = review_change(review)
    output = tmp_path / "registration"
    reg = register_candidate(
        run.work,
        run.capture,
        run.spec,
        interface_root=run.options["output"],
        qualification_root=q,
        review=review,
        trusted_review_digest=review.digest,
        output=output,
    )
    return reg, output


def context(reg, root, tmp_path, **changes):
    _, refs = load_registration(root, expected_identity=reg.digest)
    model = ModelSnapshot(
        digest({"component": "response"}),
        {"response": reg.adapter_id},
        refs,
        digest([]),
        reg.specification.inputs,
        reg.specification.outputs,
    )
    scratch = tmp_path / "scratch"
    scratch.mkdir(mode=0o700, exist_ok=True)
    return replace(PrepareContext(model, {}, 17, str(scratch), ()), **changes)


def test_registered_entry_executes_only_captured_bytes_after_original_packet_is_gone(
    run, tmp_path, monkeypatch
):
    import autoengineering.adapters.isolated as isolated
    import autoengineering.agents.interface as interface

    reg, root = stage(run, tmp_path)
    ctx = context(reg, root, tmp_path)
    shutil.rmtree(run.work.root)
    shutil.rmtree(run.options["output"])
    shutil.rmtree(run.options["qualification_root"])
    monkeypatch.setattr(isolated, "verify_qualification", interface.verify_qualification)
    registry = AdapterRegistry((registration_entry(root, expected_identity=reg.digest),))
    registry.validate(reg.adapter_id, ctx.model, root)
    adapter = registry.create(reg.adapter_id)
    result = run_lifecycle(
        adapter, ctx, {"forcing": np.asarray(1.5)}, ctx.model.inputs, ctx.model.outputs
    )
    assert result.outputs["prediction"] == 3.0
    assert result.training.status == "not_applicable"
    assert len(run.calls) == 3
    assert adapter.last_result.stopped and adapter.last_execution.is_dir()
    assert (adapter.last_execution / "result.json").is_file()
    assert adapter._active is None


@pytest.mark.parametrize(
    "change",
    [
        lambda review: replace(review, decision="reject"),
        lambda review: replace(review, capture_digest="f" * 64),
        lambda review: replace(review, interface_digest="f" * 64),
        lambda review: replace(review, qualification_digest="f" * 64),
    ],
)
def test_unapproved_or_mismatched_evidence_cannot_create_registration(run, tmp_path, change):
    with pytest.raises(ValueError):
        stage(run, tmp_path, change)
    assert not (tmp_path / "registration").exists()


def test_failed_interface_checks_never_register(run, tmp_path):
    run.replies.append((b"{}", "success", True))
    with pytest.raises(ValueError, match="failed interface"):
        stage(run, tmp_path)
    assert not (tmp_path / "registration").exists()


def test_unknown_packet_files_are_rejected_instead_of_copied(run, tmp_path):
    q = run.options["qualification_root"]
    q.mkdir(mode=0o700)
    (q / ".env").write_text("not-candidate-evidence")
    receipt = check_interface(run.work, run.capture, run.spec, **run.options)
    review = approved(run, receipt)
    with pytest.raises(ValueError, match="undeclared file"):
        register_candidate(
            run.work,
            run.capture,
            run.spec,
            interface_root=run.options["output"],
            qualification_root=q,
            review=review,
            trusted_review_digest=review.digest,
            output=tmp_path / "registration",
        )
    assert not (tmp_path / "registration").exists()


@pytest.mark.parametrize("name", ["adapter.py", "driver.py", "evidence.zip"])
def test_changed_registered_bytes_fail_before_execution(run, tmp_path, name):
    reg, root = stage(run, tmp_path)
    (root / "generated" / name).write_bytes(b"changed")
    with pytest.raises(ValueError):
        registration_entry(root, expected_identity=reg.digest)
    assert len(run.calls) == 2


def test_changed_parameters_or_ports_fail_before_preparing_execution(run, tmp_path):
    reg, root = stage(run, tmp_path)
    registry = AdapterRegistry((registration_entry(root, expected_identity=reg.digest),))
    ctx = context(reg, root, tmp_path)
    adapter = registry.create(reg.adapter_id)
    with pytest.raises(ValueError, match="configuration"):
        adapter.prepare(replace(ctx, parameters={"unexpected": 1}))
    changed = replace(ctx.model, outputs=(replace(ctx.model.outputs[0], units="m/day"),))
    with pytest.raises(ValueError, match="configuration"):
        adapter.prepare(replace(ctx, model=changed))
    assert not list((tmp_path / "scratch").iterdir())
    assert adapter.last_execution is None


@pytest.mark.parametrize(
    "name", ["../escape", "/private/tmp/escape", "workspace/../escape", "workspace//escape"]
)
def test_unsafe_archive_members_fail_before_creating_output(tmp_path, name):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(name, b"never-written")
    output = tmp_path / "extract"
    tmp_path.chmod(0o700)
    with pytest.raises(ValueError):
        extract_archive(stream.getvalue(), output)
    assert not output.exists()


def test_symlink_archive_member_is_rejected_before_writing(tmp_path):
    import stat

    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        member = zipfile.ZipInfo("workspace/link")
        member.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(member, b"/private/labels")
    tmp_path.chmod(0o700)
    with pytest.raises(ValueError, match="unsafe"):
        extract_archive(stream.getvalue(), tmp_path / "extract")
    assert not (tmp_path / "extract").exists()


def test_resealed_registration_cannot_replace_fixed_driver(run, tmp_path):
    reg, root = stage(run, tmp_path)
    driver = b'print("unreviewed driver")'
    changed = replace(reg, driver_sha256=hashlib.sha256(driver).hexdigest())
    (root / "generated/driver.py").write_bytes(driver)
    (root / "generated/registration.json").write_text(changed.to_json())
    with pytest.raises(ValueError, match="fixed execution harness"):
        load_registration(root, expected_identity=changed.digest)


def test_review_schema_rejects_worker_claimed_authority(run):
    receipt = check_interface(run.work, run.capture, run.spec, **run.options)
    review = approved(run, receipt)
    data = json.loads(review.to_json())
    data["worker_can_register"] = True
    with pytest.raises(ValueError):
        AdmissionReview.from_json(json.dumps(data))


def test_runtime_source_change_rejects_registration_before_execution(run, tmp_path, monkeypatch):
    import autoengineering.adapters.registration as module

    reg, root = stage(run, tmp_path)
    monkeypatch.setattr(module, "execution_source_identity", lambda: "f" * 64)
    with pytest.raises(ValueError, match="execution source changed"):
        registration_entry(root, expected_identity=reg.digest)
    assert len(run.calls) == 2


def test_legacy_registration_remains_readable_but_cannot_run_unbound_sources(run, tmp_path):
    from autoengineering.adapters.registration import SourceRegistration

    reg, root = stage(run, tmp_path)
    old = replace(reg, schema_version="1.0", execution_identity=None)
    assert "execution_identity" not in old.to_dict()
    assert SourceRegistration.from_json(old.to_json()) == old
    (root / "generated/registration.json").write_text(old.to_json())
    with pytest.raises(ValueError, match="identity is unbound"):
        registration_entry(root, expected_identity=old.digest)


@pytest.mark.parametrize("kind", ["collision", "case-collision", "compressed", "count"])
def test_archive_table_rejects_collisions_compression_and_excess_members_before_writes(
    tmp_path, kind
):
    stream = io.BytesIO()
    with zipfile.ZipFile(
        stream,
        "w",
        compression=zipfile.ZIP_DEFLATED if kind == "compressed" else zipfile.ZIP_STORED,
    ) as archive:
        if kind in ("collision", "case-collision"):
            archive.writestr("workspace/file", b"first")
            archive.writestr(
                "workspace/FILE/second" if kind == "case-collision" else "workspace/file/second",
                b"never-written",
            )
        elif kind == "count":
            for number in range(513):
                archive.writestr(f"workspace/file-{number}", b"x")
        else:
            archive.writestr("workspace/manifest.json", b"compressed")
    tmp_path.chmod(0o700)
    with pytest.raises(ValueError):
        extract_archive(stream.getvalue(), tmp_path / "extract")
    assert not (tmp_path / "extract").exists()


def test_training_request_is_rejected_without_starting_container(run, tmp_path, monkeypatch):
    import autoengineering.adapters.isolated as isolated
    import autoengineering.agents.interface as interface

    reg, root = stage(run, tmp_path)
    monkeypatch.setattr(isolated, "verify_qualification", interface.verify_qualification)
    ctx = context(reg, root, tmp_path)
    adapter = registration_entry(root, expected_identity=reg.digest).factory()
    with pytest.raises(ValueError, match="do not train"):
        run_lifecycle(
            adapter,
            ctx,
            {"forcing": np.asarray(1.5)},
            ctx.model.inputs,
            ctx.model.outputs,
            fitting_data={"private-label": np.asarray(3.0)},
        )
    assert adapter.last_execution is None and adapter._active is None
    assert len(run.calls) == 2


def test_standalone_registration_does_not_activate_campaign_backend(run, tmp_path):
    from autoengineering.campaign.runtime import registry

    reg, root = stage(run, tmp_path)
    ctx = context(reg, root, tmp_path)
    with pytest.raises(ValueError, match="not registered"):
        registry().validate(reg.adapter_id, ctx.model, root)
    assert len(run.calls) == 2
