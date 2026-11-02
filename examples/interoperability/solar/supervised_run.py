"""The trusted solar workflow run inside the common resource supervisor."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoengineering.campaign.controller import CampaignController
from .campaign import prepare


def run(cache, output):
    output.mkdir(mode=0o700)
    prepared = output / "prepared"
    prepare(cache, prepared)
    controller = CampaignController.create(prepared / "campaign.yaml", prepared / "source",
                                           output / "campaign", max_new_evaluations=3)
    controller.advance()
    controller = CampaignController.open(output / "campaign")
    controller.advance()
    state = controller.state()
    report = {"outcome": state.outcome, "physical_starts": len(state.budget.attempts),
              "confirmed_attempts": state.budget.confirmed_attempts,
              "unresolved_attempts": state.budget.unresolved_attempts,
              "confirmation": "not_attempted"}
    (output / "report.json").write_text(json.dumps(report, indent=2))
    if state.outcome not in ("accepted_candidate", "retain_baseline") or state.budget.unresolved_attempts:
        raise RuntimeError("solar workflow did not complete with a scientific recommendation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.cache, args.output)
