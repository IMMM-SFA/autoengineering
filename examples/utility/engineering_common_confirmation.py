"""Common post-selection scoring for the selection-only cost comparison."""

import hashlib
from pathlib import Path

from autoengineering.campaign.serialization import digest
from examples.utility.engineering_load_callback import TrustedLoadScorer


class CommonConfirmationLoadScorer(TrustedLoadScorer):
    def _code_digest(self):
        return digest(
            {
                "parent": super()._code_digest(),
                "source": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "cost_comparison_scope": "selection_only",
                "confirmation_seconds_reserved": 60,
            }
        )

    def _selection_regime_allowed(self, regime):
        return regime in ("fixed_evaluations", "fixed_total_cost")

    def _scope(self, grant, model):
        current = super()._scope(grant, model)
        if next(c.limit for c in grant.resources if c.name == "active_time") != 60:
            raise ValueError("Common confirmation needs the frozen 60-second reservation")
        return current

    def recover(self, grant, model):
        """Read the original completed score without reopening scenarios or solving."""
        import json
        from autoengineering.campaign.artifacts import confined_file
        from autoengineering.utility.scoring import PublicScore
        from examples.utility.engineering_load_callback import WORK_DIRECTORY

        self._scope(grant, model)
        state = self.store.replay()
        attempt = "confirmation-" + grant.cell_digest[:48]
        if attempt not in state["confirmation_accesses"]:
            raise ValueError("Original charged confirmation access is missing")
        public = json.loads(
            confined_file(self.store.root / WORK_DIRECTORY, grant.digest + ".json").read_text()
        )
        record = json.loads(
            confined_file(self.work_root / grant.digest, "complete.json").read_text()
        )
        if (
            public["grant_digest"] != grant.digest
            or public["scorer_digest"] != self.identity
            or public["private_result_digest"] != digest(record)
            or record["execution_digest"] != grant.digest
            or record["policy_digest"] != self.policy.digest
        ):
            raise ValueError("Original confirmation result identity differs")
        score = PublicScore.from_dict(record["score"])
        if score.digest != public["score_digest"]:
            raise ValueError("Original confirmation score changed")
        return score
