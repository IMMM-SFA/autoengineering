"""Experimental Ax public Client replay policy; not a promoted backend."""
from __future__ import annotations

from importlib.metadata import version

from autoengineering.integrations.replay import Observation, Proposal
from autoengineering.optimization.space import CategoricalParameter, SearchSpace


class AxReplayPolicy:
    def __init__(self, space: SearchSpace, *, seed: int, direction: str, initial_points=()):
        from ax.api.client import Client
        from ax.api.configs import ChoiceParameterConfig, RangeParameterConfig

        if version("ax-platform") != "1.1.2":
            raise ValueError("prototype requires pinned Ax 1.1.2")
        if direction not in ("minimize", "maximize"):
            raise ValueError("invalid objective direction")
        parameters = []
        for p in space.parameters:
            if len(getattr(p, "active_when", {})) > 1:
                raise ValueError("Ax prototype supports one selector per conditional parameter")
            if isinstance(p, CategoricalParameter):
                types = {type(value).__name__ for value in p.categories}
                if len(types) != 1:
                    raise ValueError("Ax prototype requires homogeneous categorical types")
                dependents = {
                    value: [q.name for q in space.parameters
                            if any(type(value) is type(choice) and value == choice
                                   for choice in getattr(q, "active_when", {}).get(p.name, ()))]
                    for value in p.categories
                }
                parameters.append(ChoiceParameterConfig(
                    name=p.name, values=list(p.categories), parameter_type=next(iter(types)),
                    is_ordered=False,
                    dependent_parameters={k: v for k, v in dependents.items() if v} or None,
                ))
            else:
                parameters.append(RangeParameterConfig(
                    name=p.name, bounds=(p.lower, p.upper),
                    parameter_type="int" if type(p.lower) is int else "float",
                    scaling=p.scale,
                ))
        self.client = Client(random_seed=seed)
        self.client.configure_experiment(parameters=parameters)
        self.client.configure_optimization(objective="-objective" if direction == "minimize"
                                           else "objective")
        self.client.configure_generation_strategy(
            method="fast", initialization_budget=4, initialization_random_seed=seed,
            initialize_with_center=False, torch_device="cpu",
        )
        self.initial_points = tuple(dict(point) for point in initial_points)
        self.position = 0
        for point in self.initial_points:
            space.encode(point)

    def ask(self) -> Proposal:
        if self.position < len(self.initial_points):
            config = self.initial_points[self.position]
            self.position += 1
            return Proposal(str(self.client.attach_trial(parameters=config)), config)
        trials = self.client.get_next_trials(max_trials=1)
        if len(trials) != 1:
            raise RuntimeError("Ax did not produce exactly one trial")
        number, config = next(iter(trials.items()))
        return Proposal(str(number), config)

    def tell(self, proposal: Proposal, observation: Observation) -> None:
        number = int(proposal.external_id)
        if observation.status == "success" and observation.feasible:
            self.client.complete_trial(number, raw_data={"objective": observation.objective})
        else:
            self.client.mark_trial_failed(number)
