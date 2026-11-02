"""Pinned, serial Optuna TPE with verified reconstruction from the scientific ledger.

Sessions are disposable and in memory. No external database owns actions or
results. The controller commits pending actions and verifies them on recovery.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
import hashlib
from pathlib import Path
import platform
import sys

from .backend import SearchSpaceExhausted, _BaselineBackend, _canonical_config
from .records import BackendDiagnostics, EvaluationStatus
from .space import CategoricalParameter, ContinuousParameter, IntegerParameter


class OptunaBackend(_BaselineBackend):
    name = "optuna"

    def __init__(self, spec, space, *, min_initial=4, candidate_retry_limit=64):
        super().__init__(spec, space)
        try:
            installed = version("optuna")
        except PackageNotFoundError as error:
            raise ImportError("Optuna policy requires autoengineering[optuna]") from error
        if installed != "4.5.0":
            raise ValueError("Optuna policy requires pinned version 4.5.0")
        for value in (min_initial, candidate_retry_limit):
            if type(value) is not int or value < 1:
                raise ValueError("Optuna options must be positive integers")
        for p in space.parameters:
            if isinstance(p, CategoricalParameter) and any(
                left == right and type(left) is not type(right)
                for i, left in enumerate(p.categories)
                for right in p.categories[i + 1 :]
            ):
                raise ValueError("Optuna categorical equality conflates distinct types")
        self.sampler_seed = spec.seed
        if spec.seed > 2**32 - 1:
            import numpy as np

            self.sampler_seed = int(
                np.random.SeedSequence(spec.seed).generate_state(1, dtype=np.uint32)[0]
            )
        self.min_initial = min_initial
        self.candidate_retry_limit = candidate_retry_limit
        self.environment = {name: version(name) for name in ("optuna", "numpy", "scipy")}
        self.environment.update(python=sys.version, platform=platform.platform())

    def identity_dict(self):
        identity = {
            "schema_version": "1.0",
            "name": self.name,
            "constructor": {
                "framework_version": "4.5.0",
                "sampler": "TPESampler",
                "min_initial": self.min_initial,
                "candidate_retry_limit": self.candidate_retry_limit,
                "storage": "disposable_in_memory",
                "pruning": "disabled",
                "conditional_mapping": "active_parameters_v1",
                "recovery": "verified_ledger_replay_v3",
                "environment": self.environment,
                "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "dependency_sources": self._dependency_sources(),
            },
        }
        if self.sampler_seed != self.spec.seed:
            identity["constructor"]["seed_mapping"] = {
                "version": "numpy-seedsequence-u32-v1",
                "sampler_seed": self.sampler_seed,
            }
        return identity

    def _dependency_sources(self):
        root = Path(__file__).resolve().parents[1]
        paths = (
            "optimization/backend.py",
            "optimization/space.py",
            "optimization/controller.py",
            "optimization/ledger.py",
            "optimization/records.py",
            "optimization/spec.py",
            "optimization/provenance.py",
            "integrations/contracts.py",
        )
        return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths}

    def _experiment_id(self):
        from .provenance import sha256_json

        return "optuna-" + sha256_json(
            {
                "backend": self.identity_dict(),
                "study": self.spec.to_dict(),
                "space": self.space.to_dict(),
            }
        )

    def _proposal(self, intent, action, trial_id):
        from .provenance import sha256_json

        return {
            "intent_sha256": sha256_json(intent),
            "action": action.to_dict(),
            "external_experiment_id": self._experiment_id(),
            "external_trial_id": str(trial_id),
        }

    def _evidence_directory(self, directory):
        from autoengineering.campaign.store import checked_directory

        root = Path(directory) / "optimizer-proposals"
        root.mkdir(mode=0o700, exist_ok=True)
        return checked_directory(root)

    def _evidence(self, root, name, document, *, create):
        from autoengineering.campaign.artifacts import confined_file
        from autoengineering.campaign.store import durable_write
        from .provenance import canonical_json

        expected = canonical_json(document).encode()
        path = root / name
        if path.exists() or path.is_symlink():
            path = confined_file(root, name)
            if path.stat().st_size > 1048576 or path.read_bytes() != expected:
                raise ValueError("Optuna proposal evidence differs; reconciliation required")
        elif create:
            durable_write(path, expected)
        else:
            raise ValueError("Optuna proposal evidence missing; reconciliation required")

    def _intent(self, index, prefix):
        return {
            "schema_version": 1,
            "action_id": f"eval-{index:06d}",
            "ledger_prefix_sha256": hashlib.sha256(prefix).hexdigest(),
            "backend": self.identity_dict(),
            "study": self.spec.to_dict(),
            "space": self.space.to_dict(),
        }

    def prepare_suggestion(self, ledger, directory):
        """Persist intent before any in-memory ask and verify committed evidence."""
        from .ledger import ObservationLedger

        root = self._evidence_directory(directory)
        session = self._new_session()
        replayed = set()
        prefix = b""
        for index, (action, result) in enumerate(ledger.entries()):
            intent = self._intent(index, prefix)
            self._evidence(root, f"{action.id}-intent.json", intent, create=False)
            trial = self._replay_action(session, replayed, action)
            self._evidence(
                root,
                f"{action.id}-proposal.json",
                self._proposal(intent, action, trial.number),
                create=False,
            )
            self._tell(session, trial, result)
            prefix += ObservationLedger.record_bytes(action, result)
        entries, actual = ledger.snapshot()
        if prefix != actual:
            raise ValueError("Optuna ledger snapshot differs from verified history")
        index, _ = self._next_index_and_observed(ledger)
        self._evidence(
            root, f"eval-{index:06d}-intent.json", self._intent(index, actual), create=True
        )

    def record_suggestion(self, ledger, directory, action):
        """Save exact action bytes before the controller admits physical work."""
        index, _ = self._next_index_and_observed(ledger)
        _, prefix = ledger.snapshot()
        intent = self._intent(index, prefix)
        root = self._evidence_directory(directory)
        self._evidence(root, f"{action.id}-intent.json", intent, create=False)
        trial = self._next_trial(ledger, action)
        self._evidence(
            root,
            f"{action.id}-proposal.json",
            self._proposal(intent, action, trial.number),
            create=True,
        )

    def verify_saved_suggestion(self, ledger, directory, action):
        """Pending recovery must not silently recreate missing proposal state."""
        index, _ = self._next_index_and_observed(ledger)
        _, prefix = ledger.snapshot()
        intent = self._intent(index, prefix)
        root = self._evidence_directory(directory)
        self._evidence(root, f"{action.id}-intent.json", intent, create=False)
        trial = self._next_trial(ledger, action)
        self._evidence(
            root,
            f"{action.id}-proposal.json",
            self._proposal(intent, action, trial.number),
            create=False,
        )

    def state_dict(self):
        return {
            **self.identity_dict(),
            "study_seed": self.spec.seed,
            "sequence_state": "verified_from_committed_ledger",
        }

    def diagnostics(self, ledger):
        return BackendDiagnostics(
            backend=self.name,
            fit_state="ledger_replay_tpe",
            fallback_reasons=(),
            details={
                "ledger_entries": len(ledger.entries()),
                "framework_version": "4.5.0",
                "pruning": False,
                "framework_retries": 0,
            },
        )

    def _new_session(self):
        import optuna

        return optuna.create_study(
            study_name=self._experiment_id(),
            direction=self.spec.objective.direction,
            sampler=optuna.samplers.TPESampler(
                seed=self.sampler_seed, n_startup_trials=self.min_initial
            ),
            pruner=optuna.pruners.NopPruner(),
        )

    def _ask_distinct(self, session, observed):
        for _ in range(self.candidate_retry_limit):
            trial = session.ask()
            config = {}
            for p in self.space.parameters:
                if not isinstance(p, CategoricalParameter) and not self.space._is_active(p, config):
                    continue
                if isinstance(p, CategoricalParameter):
                    config[p.name] = trial.suggest_categorical(p.name, p.categories)
                elif isinstance(p, IntegerParameter):
                    config[p.name] = trial.suggest_int(
                        p.name, p.lower, p.upper, log=p.scale == "log"
                    )
                elif isinstance(p, ContinuousParameter):
                    config[p.name] = trial.suggest_float(
                        p.name, p.lower, p.upper, log=p.scale == "log"
                    )
            self.space.encode(config)
            if _canonical_config(config) not in observed:
                return trial, config
            # A duplicate causes no model start and no invented failed outcome.
            # Its in-memory trial stays incomplete while sampling continues.
        raise RuntimeError("Optuna distinct-candidate sampling limit reached; no dispatch")

    def _objective(self, result):
        required = (self.spec.objective.outcome,) + tuple(c.outcome for c in self.spec.constraints)
        feasible = (
            result.status is EvaluationStatus.SUCCESS
            and all(name in result.outcomes for name in required)
            and all(
                result.outcomes[c.outcome] <= c.threshold
                if c.operator == "<="
                else result.outcomes[c.outcome] >= c.threshold
                for c in self.spec.constraints
            )
        )
        return result.outcomes[self.spec.objective.outcome] if feasible else None

    def _tell(self, session, trial, result):
        import optuna

        objective = self._objective(result)
        if objective is None:
            session.tell(trial, state=optuna.trial.TrialState.FAIL)
        else:
            session.tell(trial, objective)

    def _replay_action(self, session, replayed, action):
        trial, config = self._ask_distinct(session, replayed)
        if self._action(len(replayed), config) != action:
            raise ValueError("Optuna replay differs from committed action; reconciliation required")
        replayed.add(_canonical_config(config))
        return trial

    def _restore(self, ledger):
        session = self._new_session()
        replayed = set()
        for action, result in ledger.entries():
            trial = self._replay_action(session, replayed, action)
            self._tell(session, trial, result)
        return session, replayed

    def _next_trial(self, ledger, action):
        session, replayed = self._restore(ledger)
        return self._replay_action(session, replayed, action)

    def synchronize_results(self, ledger, directory, *, allow_action_id, links):
        """Verify trial IDs and project only committed results into disposable sessions.

        Only an exact controller pending-result transition can create missing tell
        records. A committed manifest with missing records fails reconciliation.
        """
        from dataclasses import replace
        from autoengineering.integrations.contracts import CommittedTrialLink
        from .ledger import ObservationLedger
        from .provenance import sha256_json

        root = self._evidence_directory(directory)
        session = self._new_session()
        replayed = set()
        prefix = b""
        for index, (action, result) in enumerate(ledger.entries()):
            intent = self._intent(index, prefix)
            trial = self._replay_action(session, replayed, action)
            proposal = self._proposal(intent, action, trial.number)
            self._evidence(root, f"{action.id}-intent.json", intent, create=False)
            self._evidence(root, f"{action.id}-proposal.json", proposal, create=False)
            context = (
                links(action)
                if links is not None
                else {
                    "campaign_id": None,
                    "study_id": "study-" + self._experiment_id().removeprefix("optuna-"),
                    "attempt_ids": (),
                }
            )
            receipt = CommittedTrialLink(
                schema_version=1,
                integration_digest=sha256_json(self.identity_dict()),
                action_id=action.id,
                external_experiment_id=self._experiment_id(),
                external_trial_id=str(trial.number),
                proposal_digest=sha256_json(proposal),
                observation_digest=sha256_json(result.to_dict()),
                ledger_prefix_digest=hashlib.sha256(prefix).hexdigest(),
                result_status=result.status.value,
                projected_objective=self._objective(result),
                synchronization="tell_intent",
                **context,
            )
            create = action.id == allow_action_id
            self._evidence(root, f"{action.id}-tell-intent.json", receipt.to_dict(), create=create)
            self._tell(session, trial, result)
            self._evidence(
                root,
                f"{action.id}-synchronized.json",
                replace(receipt, synchronization="synchronized").to_dict(),
                create=create,
            )
            prefix += ObservationLedger.record_bytes(action, result)

    def suggest(self, ledger, n=1):
        if type(n) is not int or n != 1:
            raise ValueError("Optuna supports exactly one outstanding action")
        next_index, observed = self._next_index_and_observed(ledger)
        if self.finite_space_exhausted(ledger):
            raise SearchSpaceExhausted("finite search space exhausted")
        session, _ = self._restore(ledger)
        _, config = self._ask_distinct(session, observed)
        return (self._action(next_index, config),)
