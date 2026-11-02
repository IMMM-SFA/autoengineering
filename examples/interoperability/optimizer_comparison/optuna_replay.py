"""Experimental Optuna public-API replay policy; not a promoted backend."""
from __future__ import annotations

from autoengineering.integrations.replay import Observation, Proposal
from autoengineering.optimization.space import (
    CategoricalParameter, ContinuousParameter, IntegerParameter, SearchSpace,
)
from .branches import active


class OptunaReplayPolicy:
    def __init__(self, space: SearchSpace, *, seed: int, direction: str, initial_points=()):
        import optuna

        if optuna.__version__ != "4.5.0":
            raise ValueError("prototype requires pinned Optuna 4.5.0")
        # Optuna categorical equality can conflate bool/int. Reject ambiguous
        # choices rather than silently altering the scientific parameter type.
        for p in space.parameters:
            if isinstance(p, CategoricalParameter) and any(
                left == right and type(left) is not type(right)
                for i, left in enumerate(p.categories) for right in p.categories[i + 1:]
            ):
                raise ValueError("Optuna categories conflate distinct scientific types")
        self.space = space
        self.study = optuna.create_study(
            direction=direction,
            sampler=optuna.samplers.TPESampler(seed=seed, n_startup_trials=4),
            pruner=optuna.pruners.NopPruner(),
        )
        for point in initial_points:
            space.encode(point)
            self.study.enqueue_trial(dict(point))

    def ask(self) -> Proposal:
        trial = self.study.ask()
        config = {}
        for p in self.space.parameters:
            if not active(p, config):
                continue
            if isinstance(p, CategoricalParameter):
                config[p.name] = trial.suggest_categorical(p.name, p.categories)
            elif isinstance(p, IntegerParameter):
                config[p.name] = trial.suggest_int(p.name, p.lower, p.upper, log=p.scale == "log")
            elif isinstance(p, ContinuousParameter):
                config[p.name] = trial.suggest_float(p.name, p.lower, p.upper, log=p.scale == "log")
            else:
                raise ValueError("unsupported parameter")
        return Proposal(str(trial.number), config)

    def tell(self, proposal: Proposal, observation: Observation) -> None:
        import optuna

        number = int(proposal.external_id)
        if observation.status == "success" and observation.feasible:
            self.study.tell(number, observation.objective)
        else:
            # Full reason remains in the transcript. No invented objective.
            self.study.tell(number, state=optuna.trial.TrialState.FAIL)
