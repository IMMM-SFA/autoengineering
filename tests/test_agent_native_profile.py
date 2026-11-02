"""Native profile decoder tests with authored attestations, not OS qualification."""

from dataclasses import asdict, replace
import hashlib
import json

import pytest

from autoengineering.agents.hosts import native_profile as profile
from autoengineering.agents.hosts.codex_brokered import inspect_brokered_codex
from autoengineering.agents.identity import host_source_identity
from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.serialization import canonical_json, digest
from test_agent_brokered_codex import program


def fixture(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    runtime = {**profile.native_runtime(), "platform": "darwin", "machine": "arm64"}
    monkeypatch.setattr(profile, "native_runtime", lambda: runtime)
    inventory = inspect_brokered_codex(program(tmp_path))
    (tmp_path / "artifacts").mkdir(mode=0o700)
    limits = {"max_worker_seconds": 30, "max_output_bytes": 65536, "max_workspace_bytes": 65536}
    bindings = {
        "source_identity": host_source_identity(),
        "runtime_identity": digest(runtime),
        "inventory_identity": digest(asdict(inventory)),
        "boundary_source_identity": profile.boundary_source_identity(),
        "limits": limits,
    }
    checks = {}
    raw_indexed = put_bytes(
        tmp_path,
        b"authored decoder evidence only",
        name="index-raw.txt",
        media_type="text/plain",
        producer="unit-test",
    )
    index = replace(
        put_bytes(
            tmp_path,
            canonical_json(
                {
                    "version": profile.INDEX_VERSION,
                    "bindings": bindings,
                    "files": [raw_indexed.to_dict()],
                    "total_bytes": raw_indexed.size_bytes,
                }
            ).encode(),
            name="evidence-index.json",
            media_type="application/json",
            producer="unit-test",
        ),
        metadata={"kind": profile.INDEX_VERSION},
    )
    for name, observed in profile.OBSERVATIONS.items():
        raw = put_bytes(
            tmp_path,
            b"authored decoder evidence only",
            name=f"{name}-raw.txt",
            media_type="text/plain",
            producer="unit-test",
        )
        report = {
            "version": profile.VERSION,
            "name": name,
            "status": "passed",
            "bindings": bindings,
            "observed": observed,
            "evidence": [raw.to_dict(), index.to_dict()],
        }
        checks[name] = put_bytes(
            tmp_path,
            canonical_json(report).encode(),
            name=f"{name}.json",
            media_type="application/json",
            producer="unit-test",
        ).to_dict()
    value = {
        "version": profile.VERSION,
        "status": "qualified",
        "source_identity": host_source_identity(),
        "runtime": runtime,
        "boundary_source_identity": profile.boundary_source_identity(),
        "inventory": asdict(inventory),
        "model": "authored-only-model",
        "limits": limits,
        "checks": checks,
        "provider_calls": 0,
        "scientific_calls": 0,
    }
    return value


@pytest.mark.parametrize(
    "problem",
    [
        None,
        "pin",
        "candidate",
        "source",
        "runtime",
        "boundary",
        "checks",
        "preferences",
        "artifact",
        "limit",
        "unknown",
    ],
)
def test_profile_reader_requires_every_pinned_binding_and_artifact(tmp_path, monkeypatch, problem):
    value = fixture(tmp_path, monkeypatch)
    if problem == "candidate":
        value["status"] = "candidate"
    elif problem == "source":
        value["source_identity"] = "0" * 64
    elif problem == "runtime":
        value["runtime"] = {**value["runtime"], "tls_library": "changed TLS"}
    elif problem == "boundary":
        value["boundary_source_identity"] = "0" * 64
    elif problem == "checks":
        value["checks"].pop("credentials")
    elif problem == "preferences":
        value["checks"].pop("preferences")
    elif problem == "limit":
        value["limits"] = {**value["limits"], "max_output_bytes": True}
    elif problem == "unknown":
        value["extra"] = True
    elif problem == "artifact":
        ref = value["checks"]["tools"]
        (tmp_path / ref["path"]).write_bytes(b"changed")
    raw = canonical_json(value).encode()
    (tmp_path / "qualification.json").write_bytes(raw)
    pin = hashlib.sha256(raw).hexdigest() if problem != "pin" else "0" * 64
    if problem is None:
        # Decoder acceptance of this synthetic test object proves no OS fact.
        checked = profile.verify_native_profile(tmp_path, expected_digest=pin)
        assert checked.receipt_digest == pin and checked.max_output_bytes == 65536
    else:
        with pytest.raises(ValueError):
            profile.verify_native_profile(tmp_path, expected_digest=pin)


def test_profile_rejects_boolean_substitution_for_execution_counter(tmp_path, monkeypatch):
    value = fixture(tmp_path, monkeypatch)
    ref = value["checks"]["tools"]
    path = tmp_path / ref["path"]
    report = json.loads(path.read_text())
    report["observed"]["native_tool_executions"] = False
    value["checks"]["tools"] = put_bytes(
        tmp_path,
        canonical_json(report).encode(),
        name="changed-tools.json",
        media_type="application/json",
        producer="unit-test",
    ).to_dict()
    raw = canonical_json(value).encode()
    (tmp_path / "qualification.json").write_bytes(raw)
    with pytest.raises(ValueError, match="failed"):
        profile.verify_native_profile(tmp_path, expected_digest=hashlib.sha256(raw).hexdigest())


def test_catalog_bytes_are_bound_to_profile_and_selected_model(tmp_path, monkeypatch):
    value = fixture(tmp_path, monkeypatch)
    catalog = b'{"models":[{"slug":"authored-only-model"}]}'
    ref = put_bytes(
        tmp_path, catalog, name="catalog.json", media_type="application/json", producer="unit-test"
    )
    value["model_catalog"] = ref.to_dict()
    raw = canonical_json(value).encode()
    (tmp_path / "qualification.json").write_bytes(raw)
    pin = hashlib.sha256(raw).hexdigest()
    assert profile.verify_native_profile(tmp_path, expected_digest=pin).model_catalog == catalog
    (tmp_path / ref.path).write_bytes(catalog.replace(b"authored-only-model", b"different-model"))
    with pytest.raises(ValueError):
        profile.verify_native_profile(tmp_path, expected_digest=pin)


@pytest.mark.parametrize(
    "problem",
    ["missing", "duplicate", "object", "binding", "total", "boolean", "paths", "raw"],
)
def test_profile_requires_bounded_digest_bound_raw_index(tmp_path, monkeypatch, problem):
    value = fixture(tmp_path, monkeypatch)
    ref = value["checks"]["credentials"]
    report = json.loads((tmp_path / ref["path"]).read_text())
    index_ref = report["evidence"][1]
    index = json.loads((tmp_path / index_ref["path"]).read_text())
    if problem == "missing":
        report["evidence"].pop()
    elif problem == "duplicate":
        report["evidence"].append(index_ref)
    elif problem == "raw":
        (tmp_path / index["files"][0]["path"]).write_bytes(b"altered raw evidence")
    else:
        if problem == "object":
            index = []
        elif problem == "binding":
            index["bindings"]["source_identity"] = "0" * 64
        elif problem == "total":
            index["total_bytes"] += 1
        elif problem == "boolean":
            index["total_bytes"] = True
        elif problem == "paths":
            index["files"] *= 2
            index["total_bytes"] *= 2
        report["evidence"][1] = replace(
            put_bytes(
                tmp_path,
                canonical_json(index).encode(),
                name="changed-index.json",
                media_type="application/json",
                producer="unit-test",
            ),
            metadata={"kind": profile.INDEX_VERSION},
        ).to_dict()
    value["checks"]["credentials"] = put_bytes(
        tmp_path,
        canonical_json(report).encode(),
        name="changed-credentials.json",
        media_type="application/json",
        producer="unit-test",
    ).to_dict()
    raw = canonical_json(value).encode()
    (tmp_path / "qualification.json").write_bytes(raw)
    with pytest.raises(ValueError):
        profile.verify_native_profile(tmp_path, expected_digest=hashlib.sha256(raw).hexdigest())
