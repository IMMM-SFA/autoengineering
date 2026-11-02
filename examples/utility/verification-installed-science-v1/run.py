"""Exercise installed wind science using an exported digest-bound input bundle."""

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
import sys

import autoengineering
from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.records import HostSelection, ResourceLimits
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.serialization import digest
from autoengineering.optimization import EvaluationAction
from autoengineering.utility.callback_native import SupervisedCallbackDriver
from autoengineering.utility.engineering_native import verify_native_report
from autoengineering.utility.engineering_process import (
    SupervisedEngineeringExecutor,
    execution_identity,
)
from autoengineering.utility.mixed_execution import ScriptedMixedPlan

parser = argparse.ArgumentParser()
parser.add_argument("root", type=Path)
args = parser.parse_args()
root = args.root.resolve()
forbidden = Path("/Users/cam/projects/autoengineering")
assert Path(autoengineering.__file__).resolve().is_relative_to(Path(sys.prefix))
assert "sitecustomize" in sys.modules
try:
    (forbidden / "pyproject.toml").read_bytes()
except PermissionError:
    pass
else:
    raise AssertionError("original checkout read was not denied")
try:
    socket.socket()
except PermissionError:
    pass
else:
    raise AssertionError("network socket was not denied")
plan = ScriptedMixedPlan.from_json((root / "execution-plan.json").read_text())
campaign = next(t.campaign for t in plan.campaigns if t.task_id == "wind")
execution = campaign.execution
source = root / "captured"
policy = reference(
    source, "runtime-policy.py", media_type="text/plain", producer="installed-qualification"
)
assert (
    hashlib.sha256(Path(sys.modules["sitecustomize"].__file__).read_bytes()).hexdigest()
    == policy.sha256
)
refs = (*execution.sources, policy)
identity = execution_identity(
    execution.entrypoint,
    refs,
    execution.lock,
    execution.scenarios,
    execution.timeout_seconds,
    execution.output_bytes,
    profile="supervised-engineering-v2",
)
execution = replace(
    execution, sources=refs, study=replace(execution.study, source_identity=identity)
)
spec = replace(campaign.native, execution=execution)
profile = BatchSpec(
    "1.0",
    "installed-wind-science",
    host_source_identity(),
    host_environment_identity(),
    HostSelection("fake", "none", "unused", "1.0"),
    FakeHost(()).capabilities(),
    digest({"spec": spec.digest}),
    ResourceLimits(1, 1, 0, 0, 180.0, 10.0, 8388608, 1048576),
    2,
    (BatchCase("wind", "comparison", spec.digest, 0, 2),),
)
batch = BatchStore.create(root / "batch", profile)
batch.start_case("wind", spec.digest)
executor = SupervisedEngineeringExecutor(execution, batch, "wind", source)
driver = SupervisedCallbackDriver(spec, executor)
print("Installed science: bounded native wind process", flush=True)
report = driver.run()
assert report.status == "success" and report.result.configuration is not None
verify_native_report(batch, "wind", spec, report)
print("Installed science: separately reserved fresh scenario", flush=True)
action = EvaluationAction.system(
    "installed-native-fresh",
    report.result.configuration,
    seed=17,
    suggested_by="installed-qualification",
)
fresh = executor(action)
assert fresh.evaluation.eligible and fresh.evaluation.status == "success"
proof = batch.evidence({"native": report.to_dict(), "fresh": fresh.to_dict()})
batch.finish_case("wind", "passed", (proof,))
assert driver.run(recover_only=True) == report
assert executor.recover_completed(action) == fresh
state = batch.replay()
assert len(state.reservations) == len(state.observations) == 2 and not state.pending
assert all(o.stop_verified for o in state.observations.values())
for module in sys.modules.values():
    path = getattr(module, "__file__", None)
    if path:
        assert not Path(path).resolve().is_relative_to(forbidden)
summary = {
    "status": "passed",
    "installed_module": autoengineering.__file__,
    "input_scope": "exported bound source/data bundle; not installed preparation from scratch",
    "reservations": 2,
    "observed_stops": 2,
    "completed_replay_added_reservations": 0,
    "native_status": report.result.native_status,
    "callback_entries": len(report.result.calls),
    "fresh_modelled_energy_GWh": fresh.evaluation.metrics["annual_energy"],
    "source_files_bound": len(refs) + 1,
    "runtime_policy_sha256": policy.sha256,
    "original_checkout_python_access": "denied",
    "network_sockets": "denied",
    "boundary_limit": "Python audit policy; not an OS private-data boundary",
    "confirmation": "not_attempted",
    "utility_verdict": "not_attempted",
}
(root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary), flush=True)
