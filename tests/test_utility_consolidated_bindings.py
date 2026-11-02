"""Check concrete task identities without opening confirmation measurements."""

import copy
from pathlib import Path

import pytest

from autoengineering.campaign.serialization import digest
from autoengineering.utility.contracts import TaskSpec
from examples.utility.consolidated_bindings import build, verify

ROOT = Path(__file__).resolve().parents[1]


def test_task_specs_bind_partition_outcome_and_candidate_sources():
    bundle = build(ROOT)
    verify(ROOT, bundle)
    for name, item in bundle["tasks"].items():
        spec = TaskSpec.from_dict(item["task_spec"])
        assert spec.task_id == name
        assert spec.partition_digest == digest(item["definition"]["partition"])
        assert spec.outcome_digest == digest(item["definition"]["outcome"])
        assert not item["dispatchable"]


@pytest.mark.parametrize("field", ["partition", "outcome", "baseline", "source_bindings"])
def test_changed_definition_cannot_keep_saved_task_identity(field):
    bundle = copy.deepcopy(build(ROOT))
    bundle["tasks"]["solar"]["definition"][field] = {}
    with pytest.raises(ValueError, match="differ"):
        verify(ROOT, bundle)


def test_exposure_is_specific_to_replacement_period():
    bundle = build(ROOT)
    solar = bundle["tasks"]["solar"]["definition"]
    assert solar["site"]["system_id"] == 1278
    assert solar["partition"]["confirmation"] == ["2013-01-01", "2013-12-31"]
    assert solar["partition"]["selection"][1] < solar["partition"]["confirmation"][0]
