"""Common post-selection scoring allocation, separate from selection cost matching.

This opt-in profile does not claim fixed end-to-end cost or an OS time limit.
The selection controller remains responsible for enforcing its own budget.
All inherited source grants, frozen selections and recovery checks remain active.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from autoengineering.campaign.serialization import digest
from examples.utility.wind_annual_callback import TrustedAnnualWindScorer


class CommonConfirmationWindScorer(TrustedAnnualWindScorer):
    """One common 60-second reservation and one model call per declared year.

    The reservation is accounting, not a guaranteed runtime deadline. Actual scoring
    cost stays reported separately, including unknown and unsuccessful work.
    """

    def _code_digest(self):
        return digest(
            {
                "schema": "utility-wind-common-confirmation-v1",
                "parent": super()._code_digest(),
                "source": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "cost_comparison_scope": "selection_only",
                "confirmation_active_seconds_reserved": 60,
                "end_to_end_cost_matched": False,
            }
        )

    def _selection_regime_allowed(self, regime):
        return regime in ("fixed_evaluations", "fixed_total_cost")

    def _context(self, grant, model):
        context = super()._context(grant, model)
        active = next(cap for cap in grant.resources if cap.name == "active_time")
        if active.limit != 60:
            raise ValueError("common confirmation requires the frozen 60-second reservation")
        return context
