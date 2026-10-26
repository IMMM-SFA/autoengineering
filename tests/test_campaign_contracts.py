"""Discriminating schema, identity and legacy compatibility checks."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from autoengineering.campaign import CampaignSpec, Request, Response, TimeContract
from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.identity import scientific_identity
from autoengineering.campaign.records import CandidateProposal, CandidateSnapshot
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.spec import CalibrationSpec
from autoengineering.optimization import (
    BudgetSpec,
    ContinuousParameter,
    NoiseSpec,
    ObjectiveSpec,
    OptimizationRunSpec,
    SearchSpace,
    StudySpec,
)
from autoengineering.research.candidates import Candidate, load_candidates
from autoengineering.system import System
from examples.campaign_contracts.build_fixture import ROOT, fixture


def test_canonical_roundtrip_and_whitespace(tmp_path):
    spec = fixture()
    path = tmp_path / "campaign.yaml"
    spec.to_yaml(path)
    restored = CampaignSpec.from_yaml(path)
    assert restored == spec
    assert restored.to_json() == spec.to_json()
    assert restored.digest == spec.digest
    path.write_text("# changed formatting\n\n" + path.read_text())
    assert CampaignSpec.from_yaml(path).digest == spec.digest
    assert CampaignSpec.from_json(spec.to_json()) == spec
    assert CampaignSpec.from_yaml(ROOT / "examples/campaign_contracts/fixture.yaml") == spec


@pytest.mark.parametrize(
    "section,field,value",
    [
        (None, "schema_version", "2.0"),
        (None, "seed", False),
        (None, "seed", -1),
        (None, "name", "../unsafe"),
        (None, "unknown", 1),
        ("execution", "max_executions", False),
        ("execution", "timeout_seconds", float("nan")),
        ("execution", "adapter_ids", ["unregistered"]),
        ("workflow", "max_repairs", 3),
        ("workflow", "max_transport_requests", True),
        ("acceptance", "minimum_gain", float("inf")),
        ("confirmation", "mode", "automatic"),
    ],
)
def test_invalid_specifications(section, field, value):
    data = fixture().to_dict()
    (data if section is None else data[section])[field] = value
    with pytest.raises((ValueError, TypeError)):
        CampaignSpec.from_dict(data)


def test_duplicates_references_and_dates(tmp_path):
    path = tmp_path / "bad.yaml"
    text = yaml.safe_dump(fixture().to_dict())
    path.write_text(text + "schema_version: '1.0'\n")
    with pytest.raises(ValueError, match="duplicate"):
        CampaignSpec.from_yaml(path)
    data = fixture().to_dict()
    data["baseline"]["parameters"] = {"multiplier": 1.0}
    text = yaml.safe_dump(data).replace("multiplier: 1.0", "multiplier: 1.0\n    multiplier: 2.0")
    path.write_text(text)
    with pytest.raises(ValueError, match="duplicate"):
        CampaignSpec.from_yaml(path)
    for edit in ("duplicate_data", "missing_target", "confirmation_exposure", "missing_source"):
        data = fixture().to_dict()
        if edit == "duplicate_data":
            data["data"].append(data["data"][0])
        elif edit == "missing_target":
            data["interventions"][0]["target"] = "absent"
        elif edit == "confirmation_exposure":
            data["confirmation"] = {"mode": "once", "data_id": "comparison", "protocol": "v1"}
        else:
            data["baseline"]["model"]["source_bundle"][0]["sha256"] = "0" * 64
        with pytest.raises(ValueError):
            CampaignSpec.from_dict(data)
    with pytest.raises(ValueError):
        TimeContract(
            ("2019-02-30",),
            "interval_total",
            "P1D",
            "proleptic_gregorian",
            "start",
            (False,),
            (True,),
        )
    with pytest.raises(ValueError):
        TimeContract(
            ("2019-01-01", "2019-01-03"),
            "interval_total",
            "P1D",
            "proleptic_gregorian",
            "start",
            (False, False),
            (True, True),
        )


def test_nested_inputs_and_exports_cannot_mutate_snapshot():
    data = fixture().to_dict()
    spec = CampaignSpec.from_dict(data)
    original = spec.to_json()
    data["baseline"]["parameters"]["multiplier"] = 99
    data["baseline"]["model"]["implementations"]["response"] = "other"
    exported = spec.to_dict()
    exported["data"].clear()
    with pytest.raises(TypeError):
        spec.baseline.parameters["multiplier"] = 9
    with pytest.raises(FrozenInstanceError):
        spec.name = "changed"
    assert spec.to_json() == original


def test_reuses_optimizer_contract_and_preserves_parameter_order():
    spec = fixture()
    run = OptimizationRunSpec(
        StudySpec(
            "fit",
            ObjectiveSpec("rmse", "minimize"),
            (),
            BudgetSpec(16, "calls", 16),
            NoiseSpec(),
            "system",
            17,
        ),
        SearchSpace((ContinuousParameter("multiplier", 0, 2),)),
        "sobol",
        {},
        "autoengineering.campaign.studies:campaign_evaluator",
    )
    calibrated = replace(spec, calibration=CalibrationSpec(run, "fitting"))
    assert CampaignSpec.from_json(calibrated.to_json()) == calibrated
    assert calibrated.calibration.run.to_dict() == run.to_dict()
    data = calibrated.to_dict()
    data["calibration"]["fitting_data_id"] = "comparison"
    with pytest.raises(ValueError, match="fitting"):
        CampaignSpec.from_dict(data)
    data = calibrated.to_dict()
    data["calibration"]["run"]["search_space"]["parameters"][0]["upper"] = 5
    with pytest.raises(ValueError, match="bounds"):
        CampaignSpec.from_dict(data)
    assert digest(["capacity", "recession"]) != digest(["recession", "capacity"])


def test_identity_checks_declared_closure_and_refuses_changed_bytes(tmp_path):
    spec = fixture()
    for ref in (
        spec.baseline.system,
        spec.provenance.environment_lock,
        *spec.provenance.sources,
        *(item.artifact for item in spec.data),
    ):
        target = tmp_path / ref.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / ref.path).read_bytes())
    identity = scientific_identity(spec, tmp_path)
    assert identity == scientific_identity(CampaignSpec.from_json(spec.to_json()), tmp_path)
    assert identity != scientific_identity(replace(spec, seed=18), tmp_path)
    source = tmp_path / spec.provenance.sources[0].path
    source.write_text(source.read_text() + "\n# changed helper\n")
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="mismatch"):
        scientific_identity(spec, tmp_path)
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_confined_artifacts_and_bounded_reads(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data/value").write_bytes(b"test")
    ref = reference(tmp_path, "data/value", media_type="text/plain", producer="test")
    assert read_bytes(tmp_path, ref) == b"test"
    with pytest.raises(ValueError, match="size limit"):
        read_bytes(tmp_path, ref, max_bytes=3)
    (tmp_path / "alias").symlink_to(tmp_path / "data", target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        reference(tmp_path, "alias/value", media_type="text/plain", producer="test")
    for path in ("../value", "/etc/passwd", "data/../value", "data//value"):
        with pytest.raises(ValueError):
            replace(ref, path=path)


def test_requests_are_bounded_and_strict():
    request = Request("1.0", "fixture", "state-1", 0, "state", {})
    assert Request.from_json(request.to_json()) == request
    with pytest.raises(ValueError, match="duplicate"):
        Request.from_json(request.to_json().replace('"payload":{}', '"payload":{},"payload":{}'))
    with pytest.raises(ValueError):
        replace(request, expected_revision=True)
    with pytest.raises(ValueError):
        replace(request, operation="execute_python")
    with pytest.raises(ValueError, match="64 KiB"):
        Request.from_json(json.dumps(dict(request.to_dict(), payload={"data": "x" * 65536})))
    response = Response("state-1", "ok", 0, {"state": "created"}, None, ())
    assert Response.from_json(response.to_json()) == response


def test_candidate_identity_is_distinct_from_target_and_configuration():
    spec = fixture()
    proposal = CandidateProposal(
        "proposal-1", "response", "linear-v2", "Test scaling", (), "Lower error", None, ()
    )
    model = replace(spec.baseline.model, implementations={"response": "linear-v2"})
    candidate = CandidateSnapshot(proposal, model, "linear", digest([]), {"multiplier": 1.5})
    assert CandidateSnapshot.from_json(candidate.to_json()) == candidate
    assert candidate.digest != replace(candidate, fixed_parameters={"multiplier": 1.4}).digest
    with pytest.raises(ValueError, match="implementation"):
        replace(candidate, model=spec.baseline.model)


def test_legacy_yaml_and_component_copy_still_work():
    system = System.from_yaml(ROOT / "examples/leaf_river/system.yaml")
    assert system.name
    assert load_candidates(ROOT / "examples/leaf_river/candidates.yaml")
    candidate = Candidate("response", rationale="legacy", sources=["reference"])
    assert candidate.to_component().metadata["rationale"] == "legacy"
    graph = system.to_networkx()
    graph.clear()
    assert system.to_networkx().number_of_nodes() > 0


def test_base_imports_do_not_load_optional_packages():
    source = (
        "import sys; import autoengineering.campaign; import autoengineering.adapters.contracts; "
        "assert not any(name.split('.')[0] in {'torch','botorch','gpytorch','smac','bmipy'} "
        "for name in sys.modules)"
    )
    subprocess.run([sys.executable, "-c", source], check=True, cwd=Path.cwd())


def test_resolved_hydrology_profile_and_private_split_artifacts():
    from autoengineering.campaign.artifacts import read_arrays
    from autoengineering.campaign.identity import verify_dependencies
    from examples.campaign_contracts.build_profile import audit_cache

    cached = audit_cache()
    spec = CampaignSpec.from_yaml(ROOT / "examples/campaign_contracts/profile/campaign.yaml")
    verify_dependencies(spec, ROOT)
    contracts = {item.id: item for item in spec.data}
    forcing = read_arrays(ROOT, contracts["forcing"].artifact)
    assert set(forcing) == {"precip_mm", "tmean_c", "tmax_c", "tmin_c", "day_of_year"}
    assert len(forcing["precip_mm"]) == 365
    for split, length in (("fitting", 183), ("comparison", 92)):
        labels = read_arrays(ROOT, contracts[split].artifact)
        assert set(labels) == {"prediction"}
        assert len(labels["prediction"]) == length
        assert contracts[split].prior_exposure == "exposed"
    assert spec.confirmation.mode == "disabled"
    assert cached.split.value_counts().to_dict() == {
        "test": 366,
        "train": 183,
        "validation": 92,
        "warmup": 90,
    }
    assert spec.calibration.run.study.budget.max_evaluations == 16
    assert spec.calibration.run.study.seed == 17
    assert spec.execution.max_executions == 64
    assert spec.baseline.parameters == {"pet": "hamon", "capacity": 100.0, "recession": 0.7}
