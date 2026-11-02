"""Read original supervised scenario costs without executing supplied code."""

from __future__ import annotations

import hashlib
from pathlib import Path

from autoengineering.agents.process import ProcessResult
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.execution import ProcessIdentity
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.campaign.store import StoreError
from .contracts import sha256
from .costs import CostRecord
from .engineering_process import EngineeringScenarioJob, decode_scenario


def _metadata(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 4 * 1024 * 1024:
        raise StoreError("scenario cost metadata exceeds bound")
    return path.read_bytes()


def _verified(batch, reservation, observation, document):
    relative = f"cases/{reservation.case_id}/engineering-processes"
    root = batch.root / relative / reservation.invocation_digest
    job = EngineeringScenarioJob.from_json(_metadata(root, "scenario.json").decode())
    binding = unique_json(_metadata(batch.root, relative + "/execution.json").decode())
    spec = job.execution
    original = Path(job.scratch_path)
    suffix = (*Path(relative).parts, reservation.invocation_digest)
    if (
        job.digest != document["job_digest"]
        or job.binding_digest != digest(binding)
        or binding["execution"] != spec.to_dict()
        or binding["source_root"] != job.source_root
        or document["execution_digest"] != spec.digest
        or document["process_directory"]
        != relative + "/" + reservation.invocation_digest + "/process"
        or not original.is_absolute()
        or ".." in original.parts
        or original.parts[-len(suffix) :] != suffix
        or reservation.id != "science-" + reservation.invocation_digest[:32]
        or reservation.timeout_seconds != spec.timeout_seconds + 5.0
        or not observation.stop_verified
        or len(observation.evidence) != 1
        or not document["stop_verified"]
    ):
        raise StoreError("scenario cost binding differs from original reservation")
    completion = unique_json(_metadata(root, "process/completion.json").decode())
    raw_job = _metadata(root, "process/job.json")
    process_job = unique_json(raw_job.decode())
    identity = completion["identity"]
    if (
        hashlib.sha256(raw_job).hexdigest() != completion["job_sha256"]
        or process_job["command"]
        != [
            binding["python"],
            "-I",
            "-B",
            "-m",
            "autoengineering.utility.engineering_worker",
            str(original / "scenario.json"),
        ]
        or process_job["cwd"] != str(original)
        or process_job["environment"] != {}
        or process_job.get("keep_group_leader") is not True
        or process_job.get("owner_lease") != "pipe-eof-v1"
        or identity != document["process_identity"]
        or (
            identity is not None
            and identity["nonce"] != "engineering-" + reservation.invocation_digest[:32]
        )
        or not completion["stopped"]
        or completion["status"] != document["process_status"]
        or completion["elapsed_seconds"] != observation.elapsed_seconds
    ):
        raise StoreError("scenario cost completion differs from original process")
    output = read_bytes(
        root,
        ArtifactRef(
            "process/stdout.bin",
            completion["stdout_sha256"],
            completion["stdout_bytes"],
            "application/json",
            "original-supervisor",
            {},
        ),
        max_bytes=spec.output_bytes,
    )
    process = ProcessResult(
        completion["status"],
        ProcessIdentity(**identity) if identity else None,
        completion["returncode"],
        output,
        b"",
        completion["elapsed_seconds"],
        completion["stopped"],
        completion["truncated"],
    )
    status, result = decode_scenario(job, process)
    if (
        status != document["status"]
        or status != observation.status
        or (result.to_dict() if result else None) != document["result"]
    ):
        raise StoreError("scenario cost result differs from original output")
    return process, result


def join_scenario_costs(batch, case_cells):
    """Project starts and declared counters, preserving unknown failed work.

    These starts are a subset of batch science permissions. Lifecycle seconds
    overlap process durations. Diagnostic names retain their supplied meaning.
    Neither quantity can be added to its enclosing total as extra work.
    """
    if set(case_cells) != {c.id for c in batch.spec.cases} or len(set(case_cells.values())) != len(
        case_cells
    ):
        raise ValueError("scenario cost mapping must cover unique child cases exactly")
    for cell in case_cells.values():
        sha256(cell)
    state = batch.replay()
    records = []
    for observation in state.observations.values():
        reservation = state.reservations[observation.reservation_id]
        if reservation.resource != "science":
            continue
        for ref in observation.evidence:
            if ref.media_type != "application/json":
                continue
            document = unique_json(read_bytes(batch.root, ref, max_bytes=65536).decode())
            if (
                not isinstance(document, dict)
                or document.get("profile") != "supervised-engineering-v1"
            ):
                continue
            try:
                process, result = _verified(batch, reservation, observation, document)
            except (KeyError, TypeError) as error:
                raise StoreError("scenario cost receipt is malformed") from error
            quantities = [
                ("scenario_process_starts", "count", 1.0 if process.identity else None),
                ("scenario_lifecycle_duration", "s", result.lifecycle_seconds if result else None),
            ]
            names = {"solver_iterations", "component_calls", "derivative_calls"}
            if result:
                names.update(k for k, units in result.solver_units.items() if units == "count")
            for name in sorted(names):
                quantity = (
                    result.solver_work.get(name)
                    if result and result.solver_units.get(name) == "count"
                    else None
                )
                quantities.append(("scenario_diagnostic_" + name, "count", quantity))
            source = digest(document)
            records.extend(
                CostRecord(
                    "scenario-cost-" + digest({"source": source, "resource": name})[:48],
                    source,
                    "selection",
                    name,
                    units,
                    quantity,
                    (case_cells[reservation.case_id],),
                    (1.0,),
                )
                for name, units, quantity in quantities
            )
    return tuple(records)
