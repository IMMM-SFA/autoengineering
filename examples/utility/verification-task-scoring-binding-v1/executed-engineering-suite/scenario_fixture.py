
import time
from pathlib import Path
from autoengineering.utility.engineering_process import EngineeringScenarioResult, SupervisedEngineeringExecutor
from autoengineering.utility.outcomes import ScenarioScore
from autoengineering.campaign.records import CheckResult

def execute(job):
    if job.configuration.get("x") == 1.:
        raise RuntimeError("PRIVATE-DIAGNOSTIC-CANARY")
    if job.scenario_id == "scenario-0" and job.configuration.get("x") == 0.:
        time.sleep(60)
    score = ScenarioScore(job.scenario_id, SupervisedEngineeringExecutor._forcing_digest(
        next(s for s in job.execution.scenarios if s.scenario_id == job.scenario_id)),
        {"power":10.-job.configuration["x"], "revenue":5.},
        (CheckResult("physics","1","pass",True,"scenario",None,None,"Authored supplied check",()),))
    return EngineeringScenarioResult("utility-engineering-result-v1",job.digest,score,{"solves":1.},.01, {"solves":"count"})

def native(job):
    from autoengineering.utility.engineering_native import NativeDriverResult, NativeSolveRecord, NativeSolverState
    import time
    if job.specification.max_iterations == 1:
        time.sleep(60)
    if job.specification.max_iterations == 2:
        raise RuntimeError("PRIVATE-NATIVE-CANARY")
    work = NativeSolverState(True,0.,1e-10,"A",2,5,1)
    records = (NativeSolveRecord("driver",None,"shared_problem_snapshot",work),)*2
    records += tuple(NativeSolveRecord("scenario",s.scenario_id,"independent_problem",work) for s in job.specification.execution.scenarios)
    return NativeDriverResult("utility-native-result-v2",job.digest,{"x":.9},job.specification.max_iterations != 3,records,work)
