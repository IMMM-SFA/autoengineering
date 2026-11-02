"""One bounded comparison cell. The parent enforces process resource limits."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import resource
import platform
import sys
import time

from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import durable_write
from autoengineering.integrations.contracts import IntegrationSpec
from autoengineering.integrations.replay import Observation, Proposal, ReplayJournal
from .cases import case, evaluate
from .branches import project_sobol


def run(root, framework, case_name, seed):
    from scipy.stats import qmc

    branch = case(case_name)
    points = tuple(project_sobol(branch.space, row) for row in qmc.Sobol(
        branch.space.encoded_dimension, scramble=True, seed=seed,
    ).random_base2(4))
    initial = points[:4]
    started = time.perf_counter()
    if framework == "ax":
        from .ax_replay import AxReplayPolicy
        cls = AxReplayPolicy
        package = "ax-platform"
    elif framework == "optuna":
        import optuna
        optuna.logging.set_verbosity(optuna.logging.ERROR)
        from .optuna_replay import OptunaReplayPolicy
        cls = OptunaReplayPolicy
        package = "optuna"
    else:
        package = "scipy"

        class Sobol:
            def __init__(self, *args, **kwargs):
                self.position = 0

            def ask(self):
                index = self.position
                self.position += 1
                return Proposal(str(index), points[index])

            def tell(self, *args):
                pass

        cls = Sobol
    import_seconds = time.perf_counter() - started

    def factory():
        return cls(branch.space, seed=seed, direction="minimize", initial_points=initial)

    # All identity material must exist before the first analytic model start.
    config = {"space": branch.space.to_dict(), "defaults": dict(branch.inactive_defaults),
              "initial": initial, "seed": seed, "framework": framework,
              "case": case_name, "limit": 12, "failure_ordinal": 1}
    versions = {p: importlib.metadata.version(p) for p in (package, "autoengineering", "numpy")}
    versions.update(python=sys.version, platform=platform.platform())
    source_root = Path(__file__).resolve().parent
    sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_root.glob("*.py")}
    repository = source_root.parents[2]
    sources.update({str(p.relative_to(repository)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (repository / "src").rglob("*.py")})
    identity = IntegrationSpec(1, framework, versions[package], "comparison-v1", "policy",
                               digest(config), digest(versions), digest(sources),
                               ("serial", "in_memory_replay"), seed, "transcript-json-v1")
    durable_write(root / "manifest.json", json.dumps({"configuration": config,
                  "versions": versions, "sources": sources,
                  "identity": identity.to_dict()}, sort_keys=True).encode())
    journal_root = root / "journal"
    journal_root.mkdir(mode=0o700)
    journal = ReplayJournal(journal_root, identity)
    seen, history = set(), []
    stop = "evaluation_ceiling"
    for index in range(12):
        action = f"eval-{index:06d}"
        prefix = digest(history)
        before = time.perf_counter()
        proposal = journal.propose(action, prefix, factory)
        suggest_seconds = time.perf_counter() - before
        scientific = branch.scientific(proposal.configuration)
        key = branch.configuration_digest(scientific)
        if key in seen:
            # No fake failure or extra physical attempt for a duplicate.
            stop = "duplicate_proposal_no_dispatch"
            break
        seen.add(key)
        before = time.perf_counter()
        result = evaluate(scientific, index)
        evaluation_seconds = time.perf_counter() - before
        result_data = {"action_id": action, "configuration": scientific, "result": result}
        result_digest = digest(result_data)
        result_path = root / f"result-{index:06d}.json"
        durable_write(result_path, json.dumps(result_data, sort_keys=True).encode())
        observation = Observation(result_digest, result["status"], result["feasible"],
                                  result["objective"])

        def committed(action_id, claimed_digest):
            saved = json.loads(result_path.read_text())
            return saved["action_id"] == action_id and digest(saved) == claimed_digest

        before = time.perf_counter()
        journal.observe(action, observation, factory, committed_result=committed)
        tell_seconds = time.perf_counter() - before
        # Lost acknowledgment and fresh-process reconstruction use identical APIs.
        reopened = ReplayJournal(journal_root, identity)
        if reopened.propose(action, prefix, factory) != proposal:
            raise ValueError("resume proposal differs")
        reopened.observe(action, observation, factory, committed_result=committed)
        history.append({**result_data, "suggest_seconds": suggest_seconds,
                        "tell_seconds": tell_seconds, "evaluation_seconds": evaluation_seconds})
        durable_write(root / f"history-{index:06d}.json", json.dumps(history[-1]).encode())
    summary = {"framework": framework, "case": case_name, "seed": seed,
               "physical_starts": len(history), "stop": stop, "history": history,
               "import_seconds": import_seconds,
               "total_seconds": time.perf_counter() - started,
               "peak_rss_native_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    durable_write(root / "summary.json", json.dumps(summary, sort_keys=True).encode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("framework", choices=("ax", "optuna", "sobol"))
    parser.add_argument("case", choices=("continuous", "mixed", "conditional"))
    parser.add_argument("seed", type=int)
    args = parser.parse_args()
    run(args.root, args.framework, args.case, args.seed)
