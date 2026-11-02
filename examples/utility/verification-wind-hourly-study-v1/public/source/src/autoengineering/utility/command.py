"""Local JSON CLI for implemented utility preparation and offline evidence operations."""
from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from pathlib import Path

import click

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json
from autoengineering.campaign.store import durable_write
from .confirmation_command import build_confirmation_command
from .contracts import UtilitySuiteSpec
from .exposure import ExposureRecord
from .preparation import TaskPreparation, prepare_suite
from .store import SuiteStore


@dataclass(frozen=True)
class PreparationInputs(Record):
    tasks: tuple[TaskPreparation, ...]
    register: tuple[ExposureRecord, ...]
    lock: ArtifactRef | None
    source_inventory: tuple[ArtifactRef, ...]


def load(path, kind):
    path = Path(path).absolute()
    checked = confined_file(path.parent, path.name)
    if checked.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("utility input exceeds size limit")
    return kind.from_json(checked.read_text())


def errors(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (ValueError, TypeError, OSError, KeyError):
            # Input paths or scoring payloads may contain private metadata.
            click.echo(canonical_json({"status": "error", "error": "invalid_utility_evidence"}))
            raise click.exceptions.Exit(2) from None
    return wrapped


def emit(document):
    click.echo(canonical_json(document))


@click.group()
def utility():
    """Prepare and inspect experimental utility comparisons offline."""


@utility.command("validate")
@click.argument("specification", type=click.Path(exists=True, path_type=Path))
@errors
def validate(specification):
    """Validate immutable suite records without executing a factory."""
    spec = load(specification, UtilitySuiteSpec)
    emit({"status": "valid_schema", "suite_digest": spec.digest, "cells": len(spec.cells),
          "batch_sizes": [len(batch) for batch in spec.child_batches()], "starts_authorized": False})


@utility.command()
@click.argument("specification", type=click.Path(exists=True, path_type=Path))
@click.option("--inputs", type=click.Path(exists=True, path_type=Path))
@click.option("--source-root", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True)
@click.option("--workdir", type=click.Path(path_type=Path), required=True)
@errors
def prepare(specification, inputs, source_root, workdir):
    """Verify supplied admissions and create a reviewable journal, with zero starts."""
    from autoengineering.campaign.runtime import registry
    spec = load(specification, UtilitySuiteSpec)
    admission = load(inputs, PreparationInputs) if inputs else PreparationInputs((), (), None, ())
    profiles = {"hydrology": ("daily", "stores", "fluxes", "water_balance"),
                "solar-pvlib": ("subdaily", "measured_poa", "fixed_equipment")}
    result = prepare_suite(spec, admission.tasks, source_root=source_root, adapters=registry(),
                           capabilities=profiles, register=admission.register, lock=admission.lock,
                           source_inventory=admission.source_inventory)
    store = SuiteStore.create(workdir, spec)
    with store.writer():
        durable_write(store.root / "preparation.json", (result.to_json() + "\n").encode())
    emit(result.to_dict())


@utility.command()
@click.argument("workdir", type=click.Path(exists=True, path_type=Path))
@errors
def status(workdir):
    """Read authoritative allocation state without launching work."""
    store = SuiteStore(workdir)
    state = store.replay()
    emit({"suite_digest": store.spec.digest, "assigned_cells": len(store.spec.cells),
          "attempt_states": {key: value[1] for key, value in state["attempts"].items()},
          "cancelled": state["cancelled"], "selection_manifest": state["frozen"],
          "revision": len(state["events"])})


@utility.command("freeze")
@click.argument("workdir", type=click.Path(exists=True, path_type=Path))
@click.argument("manifest", type=click.Path(exists=True, path_type=Path))
@errors
def freeze_command(workdir, manifest):
    """Seal every assigned selection without accessing confirmation data."""
    from .confirmation import SelectionManifest, freeze
    identity = freeze(SuiteStore(workdir), load(manifest, SelectionManifest))
    emit({"status": "selection_frozen", "selection_digest": identity})


@utility.command()
@click.argument("workdir", type=click.Path(exists=True, path_type=Path))
@errors
def cancel(workdir):
    """Stop new suite dispatch while retaining all reserved charges."""
    store = SuiteStore(workdir)
    with store.writer():
        store.append(request_id="suite-cancel", operation="cancel", attempt_id="suite-cancel",
                     cell_digest=store.spec.cells[0].digest, child_digest=store.spec.digest)
    emit({"status": "cancelled", "existing_work": "requires_child_reconciliation"})


@utility.command()
@click.argument("workdir", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "output_format", type=click.Choice(["json", "markdown"]), default="json")
@click.option("--inputs", "report_inputs", type=click.Path(exists=True, path_type=Path))
@click.option("--export-directory", type=click.Path(path_type=Path))
@click.option("--figures", is_flag=True, help="Render optional Matplotlib figures with the export.")
@errors
def report(workdir, output_format, report_inputs, export_directory, figures):
    """Reconstruct public accounting or comparative tables offline."""
    from .report import accounting_report, render_markdown
    store = SuiteStore(workdir)
    if figures and export_directory is None:
        raise ValueError("figures require an export directory")
    if export_directory is not None and (report_inputs is None or output_format != "json"):
        raise ValueError("export requires comparative inputs and JSON output")
    if report_inputs is not None:
        from .reporting import ReportSpec, comparative_report, export_report, render_comparative_markdown
        request = load(report_inputs, ReportSpec)
        if export_directory is not None:
            if figures:
                from .figures import export_figures
                emit(export_figures(store, request, export_directory))
                return
            emit(export_report(store, request, export_directory))
            return
        document = comparative_report(store, request)
        if output_format == "json":
            emit(document)
        else:
            click.echo(render_comparative_markdown(document))
        return
    document = accounting_report(store)
    if output_format == "json":
        emit(document)
    else:
        click.echo(render_markdown(document))


@utility.command()
@click.argument("workdir", type=click.Path(exists=True, path_type=Path))
@click.option("--inputs", "report_inputs", type=click.Path(exists=True, path_type=Path))
@click.option("--export-directory", type=click.Path(exists=True, path_type=Path))
@click.option("--rerender-figures", is_flag=True, help="Rebuild image pixels in the optional rendering environment.")
@errors
def verify(workdir, report_inputs, export_directory, rerender_figures):
    """Verify saved evidence or reconstruct a comparative export offline."""
    from .report import accounting_report
    store = SuiteStore(workdir)
    if rerender_figures and (report_inputs is None or export_directory is None):
        raise ValueError("pixel verification requires comparative inputs and an export")
    if report_inputs is not None or export_directory is not None:
        if report_inputs is None or export_directory is None:
            raise ValueError("comparative verification needs inputs and an export")
        from .reporting import ReportSpec, verify_export
        emit(verify_export(store, load(report_inputs, ReportSpec), export_directory,
                           rerender_figures=rerender_figures))
        return
    document = accounting_report(store)
    emit({"status": "invalid" if document["evidence_blockers"] else "verified_integrity",
          "suite_digest": document["suite_digest"], "blockers": document["evidence_blockers"],
          "complete_cost_evidence": document["complete_cost_evidence"],
          "utility_verdict": document["utility_verdict"]})
    if document["evidence_blockers"]:
        raise click.exceptions.Exit(2)


def _execute_scripted(workdir, execution_plan, source_root, max_new_cells, *, resume, continue_pending_scenarios=False):
    from .execution import ScriptedCoordinator, ScriptedExecutionPlan
    from .engineering_execution import ScriptedEngineeringCoordinator, ScriptedEngineeringPlan
    from .mixed_execution import ScriptedMixedCoordinator, ScriptedMixedPlan
    from autoengineering.campaign.serialization import unique_json
    raw = confined_file(Path(execution_plan).absolute().parent, Path(execution_plan).name)
    if raw.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("utility input exceeds size limit")
    document = unique_json(raw.read_text())
    if not isinstance(document, dict):
        raise ValueError("execution plan must be a record")
    mixed = document.get("schema") == "utility-scripted-mixed-v1"
    engineering = mixed or document.get("schema") == "utility-scripted-engineering-v1"
    kind = ScriptedMixedPlan if mixed else (ScriptedEngineeringPlan if engineering else ScriptedExecutionPlan)
    plan = kind.from_dict(document)
    if continue_pending_scenarios and (not resume or not engineering):
        raise ValueError("pending scenario continuation requires engineering resume")
    store = SuiteStore(workdir)
    coordinator_type = ScriptedMixedCoordinator if mixed else (ScriptedEngineeringCoordinator if engineering else ScriptedCoordinator)
    coordinator = coordinator_type(store, plan, source_root)
    pin = store.root / "control/execution-plan.json"
    with store.writer():
        if resume:
            saved = load(pin, kind)
            if saved != plan:
                raise ValueError("resume execution plan changed")
        else:
            if pin.exists() or pin.is_symlink() or store.replay()["attempts"]:
                raise ValueError("existing execution requires resume")
            durable_write(pin, (plan.to_json()+"\n").encode())
    from .studies import EngineeringReconciliationRequired
    try:
        result = (coordinator.run(max_new_cells=max_new_cells, resume_scenarios=continue_pending_scenarios)
                  if engineering else coordinator.run(max_new_cells=max_new_cells))
    except EngineeringReconciliationRequired:
        raise ValueError("original engineering work requires reconciliation") from None
    if result["finished_cells"] == result["assigned_cells"]:
        manifest = coordinator.selection_manifest()
        from autoengineering.campaign.artifacts import put_bytes
        with store.writer():
            ref = put_bytes(store.root, (manifest.to_json()+"\n").encode(), name="selection-proposal.json",
                            media_type="application/json", producer="scripted-coordinator")
        result["selection_proposal"] = ref.to_dict()
    emit(result)


@utility.command("run")
@click.argument("workdir", type=click.Path(exists=True, path_type=Path))
@click.argument("execution_plan", type=click.Path(exists=True, path_type=Path))
@click.option("--source-root", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True)
@click.option("--max-new-cells", type=click.IntRange(min=0))
@click.option("--scripted-development", is_flag=True, required=True,
              help="Use scripted hosts and exposed supplied-campaign development inputs only.")
@errors
def run_command(workdir, execution_plan, source_root, max_new_cells, scripted_development):
    """Run the frozen local scripted development plan, without confirmation."""
    if not scripted_development:
        raise ValueError("scripted development profile must be explicit")
    _execute_scripted(workdir, execution_plan, source_root, max_new_cells, resume=False)


@utility.command("resume")
@click.argument("workdir", type=click.Path(exists=True, path_type=Path))
@click.argument("execution_plan", type=click.Path(exists=True, path_type=Path))
@click.option("--source-root", type=click.Path(exists=True, file_okay=False, path_type=Path), required=True)
@click.option("--max-new-cells", type=click.IntRange(min=0))
@click.option("--scripted-development", is_flag=True, required=True)
@click.option("--continue-pending-scenarios", is_flag=True,
              help="Engineering only: continue never-reserved work in the original pending request.")
@errors
def resume_command(workdir, execution_plan, source_root, max_new_cells, scripted_development, continue_pending_scenarios):
    """Resume original scripted work; engineering continuation must be explicit."""
    if not scripted_development:
        raise ValueError("scripted development profile must be explicit")
    _execute_scripted(workdir, execution_plan, source_root, max_new_cells, resume=True,
                      continue_pending_scenarios=continue_pending_scenarios)


# Applications may construct this same command with explicitly reviewed trusted
# registrations. The distributed CLI admits no private scorer by default.
utility.add_command(build_confirmation_command())
