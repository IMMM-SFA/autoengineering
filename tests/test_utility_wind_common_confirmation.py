"""The selection-cost amendment keeps original confirmation accounting and replay."""

import pytest
from examples.utility import wind_annual_source, wind_annual_callback
from examples.utility.wind_common_confirmation import CommonConfirmationWindScorer
from test_utility_wind_annual_callback import setup, lose_score_publication


def test_cost_selection_uses_common_confirmation_without_rescoring(tmp_path, monkeypatch):
    context = setup(
        tmp_path, monkeypatch, change="regime", scorer_class=CommonConfirmationWindScorer
    )
    receipt = context["service"].confirm(context["grant"])
    assert receipt.score.status == "success"
    assert len(context["calls"]) == len(context["reads"]) == 3
    assert context["service"].confirm(context["grant"]) == receipt
    assert len(context["calls"]) == len(context["reads"]) == 3


def test_cost_selection_recovers_original_score_without_weather(tmp_path, monkeypatch):
    context = setup(
        tmp_path, monkeypatch, change="regime", scorer_class=CommonConfirmationWindScorer
    )
    lose_score_publication(context)

    def denied(*args, **kwargs):
        pytest.fail("recovery attempted new source or model work")

    monkeypatch.setattr(wind_annual_source, "open_for_confirmation", denied)
    monkeypatch.setattr(wind_annual_callback.kernel, "score_annual", denied)
    receipt = context["service"].recover(context["grant"])
    assert receipt.score.status == "success"
    assert len(context["calls"]) == len(context["reads"]) == 3
