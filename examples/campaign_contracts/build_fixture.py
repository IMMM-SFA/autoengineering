"""Resolve the small schema fixture. Does not execute a model."""

from __future__ import annotations

from pathlib import Path

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import (
    DataContract,
    ModelSnapshot,
    PortContract,
    Request,
    Response,
)
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.spec import (
    AcceptanceSpec,
    BaselineSpec,
    CampaignSpec,
    CheckSpec,
    ConfirmationSpec,
    ExecutionSpec,
    InterventionSpec,
    ProvenanceSpec,
    WorkflowSpec,
)

ROOT = Path(__file__).resolve().parents[2]
HERE = "examples/campaign_contracts"


def fixture(root: Path = ROOT) -> CampaignSpec:
    source = reference(
        root, f"{HERE}/fixture_model.py", media_type="text/x-python", producer="author"
    )
    system = reference(
        root, f"{HERE}/system.yaml", media_type="application/yaml", producer="author"
    )

    def data_ref(role):
        return reference(
            root, f"{HERE}/{role}.json", media_type="application/json", producer="author"
        )

    lock = reference(root, "pixi.lock", media_type="text/plain", producer="pixi")
    sources = (
        source,
        *(
            reference(
                root, str(path.relative_to(root)), media_type="text/x-python", producer="author"
            )
            for path in sorted((root / "src/autoengineering").rglob("*.py"))
        ),
    )

    def port(name):
        return PortContract(name, (), "mm/day", "float", (), "scalar", digest([]), None)

    model = ModelSnapshot(
        system.sha256,
        {"response": "linear-v1"},
        sources,
        lock.sha256,
        (port("forcing"),),
        (port("prediction"),),
    )
    return CampaignSpec(
        "1.0",
        "contract-fixture",
        "Synthetic scalar orchestration fixture",
        17,
        "contract-fixture-v1",
        BaselineSpec(system, model, "linear", {"multiplier": 1.0}),
        (
            DataContract("forcing", data_ref("forcing"), (port("forcing"),), "forcing", "exposed"),
            DataContract(
                "fitting", data_ref("fitting"), (port("prediction"),), "fitting", "exposed"
            ),
            DataContract(
                "comparison", data_ref("comparison"), (port("prediction"),), "comparison", "exposed"
            ),
        ),
        (InterventionSpec("response", ("linear-v1", "linear-v2"), {"multiplier": (0.0, 2.0)}),),
        AcceptanceSpec(
            "rmse",
            "minimize",
            0.01,
            {},
            (CheckSpec("finite", "1", True, "outputs", {}),),
        ),
        None,
        WorkflowSpec(),
        ExecutionSpec(("linear",)),
        ConfirmationSpec("disabled"),
        ProvenanceSpec(sources, lock, model.outputs),
    )


if __name__ == "__main__":
    spec = fixture()
    spec.to_yaml(ROOT / HERE / "fixture.yaml")
    request = Request("1.0", spec.name, "state-1", 0, "state", {})
    (ROOT / HERE / "request.json").write_text(request.to_json() + "\n")

    response = Response("state-1", "ok", 0, {"state": "created"}, None, ())
    (ROOT / HERE / "response.json").write_text(response.to_json() + "\n")
