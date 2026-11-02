"""Missing receipts and shared work retain their physical meaning."""
import pytest

from autoengineering.utility.costs import CostRecord, reconcile

H = "1" * 64


def receipt(quantity=2):
    return CostRecord("physical-one", H, "preparation", "active_time", "s",
                      quantity, [H, "2" * 64], [.25, .75])


def test_shared_receipt_counted_once():
    result = reconcile((receipt(),), ("physical-one",))
    assert result["complete"]
    assert result["known_totals"] == [
        {"resource": "active_time", "units": "s", "quantity": 2.}]
    with pytest.raises(ValueError, match="duplicate"):
        reconcile((receipt(), receipt()), ("physical-one",))


def test_missing_and_unknown_are_not_zero():
    result = reconcile((receipt(None),), ("physical-one", "physical-two"))
    assert not result["complete"]
    assert result["known_totals"] == []
    assert result["unknown"] == ["physical-one"]
    assert result["missing"] == ["physical-two"]


@pytest.mark.parametrize("fractions", [[1, 1], [-1, 2], [.5], [float("nan"), .5]])
def test_invalid_allocation(fractions):
    data = receipt().to_dict()
    data["allocation"] = fractions
    with pytest.raises(ValueError):
        CostRecord.from_dict(data)


def test_same_evidence_can_support_distinct_resource_quantities():
    from dataclasses import replace
    first = receipt()
    second = replace(first, receipt_id="other-metric", resource="cpu_time", units="CPU-s")
    result = reconcile((first, second), (first.receipt_id, second.receipt_id))
    assert len(result["known_totals"]) == 2
    with pytest.raises(ValueError, match="duplicate"):
        reconcile((first, replace(first, receipt_id="duplicate")),
                  (first.receipt_id, "duplicate"))


def test_batch_join_preserves_missing_usage_and_does_not_invent_starts(tmp_path):
    from autoengineering.utility.costs import join_batch_costs
    from test_agent_batch import initialized, reservation, observed
    child = initialized(tmp_path)
    mapping = {"first": H, "second": "2" * 64}
    r = reservation()
    child.reserve(r)
    records = join_batch_costs(child, mapping)
    values = {record.resource: record.quantity for record in records}
    assert values["host_reservations"] == 1
    assert values["host_starts"] is None
    assert values["host_duration"] is None
    child.observe(observed(child, r, usage={"input_tokens": 123}))
    records = join_batch_costs(child, mapping)
    values = {record.resource: record.quantity for record in records}
    assert values["provider_input_tokens"] == 123
    assert values["provider_output_tokens"] is None
    assert values["provider_spend"] is None
    assert values["host_starts"] is None
    assert not reconcile(records, tuple(r.receipt_id for r in records))["complete"]


def test_batch_join_rejects_modified_observation_evidence(tmp_path):
    from autoengineering.utility.costs import join_batch_costs
    from test_agent_batch import initialized, reservation, observed
    child = initialized(tmp_path)
    r = reservation()
    child.reserve(r)
    observation = observed(child, r)
    child.observe(observation)
    (child.root / observation.evidence[0].path).write_text("altered")
    with pytest.raises(ValueError):
        join_batch_costs(child, {"first": H, "second": "2" * 64})
