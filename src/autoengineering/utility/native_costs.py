"""Offline joins for original native reports, without factory/model execution."""

from __future__ import annotations

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.serialization import unique_json
from autoengineering.campaign.store import StoreError
from .contracts import sha256


def _job(batch, case_id, report):
    path = confined_file(
        batch.root, f"cases/{case_id}/native-drivers/{report.specification_digest}/job.json"
    )
    if path.stat().st_size > 4 * 1024 * 1024:
        raise StoreError("native cost job metadata exceeds bound")
    return unique_json(path.read_text())


def join_native_costs(batch, case_cells):
    """Join typed, verified native diagnostics only to their reserved cell.

    Unknown science reservations remain covered by generic batch records. Native
    process starts are subsets of those reservations, not extra scientific starts.
    Callback entries are not inner solves; shared driver snapshots are not summed.
    """
    if set(case_cells) != {c.id for c in batch.spec.cases} or len(set(case_cells.values())) != len(
        case_cells
    ):
        raise ValueError("native cost mapping must cover unique child cases exactly")
    for cell in case_cells.values():
        sha256(cell)
    schemas = {
        "utility-native-report-v1",
        "utility-callback-report-v1",
        "utility-wind-driver-report-v1",
    }
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
            if not isinstance(document, dict) or document.get("schema") not in schemas:
                continue
            case, cell = reservation.case_id, case_cells[reservation.case_id]
            schema = document["schema"]
            if schema == "utility-native-report-v1":
                from .engineering_native import (
                    NativeDriverReport,
                    NativeDriverJob,
                    verify_native_report,
                    native_cost_records,
                )

                report = NativeDriverReport.from_dict(document)
                job = NativeDriverJob.from_dict(_job(batch, case, report))
                verifier, project = verify_native_report, native_cost_records
            elif schema == "utility-callback-report-v1":
                from .callback_native import (
                    CallbackDriverReport,
                    CallbackDriverJob,
                    verify_callback_report,
                    callback_cost_records,
                )

                report = CallbackDriverReport.from_dict(document)
                job = CallbackDriverJob.from_dict(_job(batch, case, report))
                verifier = verify_callback_report

                def project(report, cell):
                    return callback_cost_records(
                        report, cell, callback_kinds=job.specification.callback_limits
                    )
            else:
                from examples.utility.wind_process import (
                    WindDriverReport,
                    WindDriverJob,
                    verify_report,
                    cost_records,
                )

                report = WindDriverReport.from_dict(document)
                job = WindDriverJob.from_dict(_job(batch, case, report))
                verifier, project = verify_report, cost_records
            if (
                report.reservation_id != reservation.id
                or report.job_digest != reservation.invocation_digest
            ):
                raise StoreError("native cost report belongs to another physical reservation")
            verifier(batch, case, job.specification, report)
            records.extend(project(report, cell))
    return tuple(records)
