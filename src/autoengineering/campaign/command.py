"""Local Click/JSON interface. Progress uses stderr and stdout stays machine readable."""

from __future__ import annotations

from functools import wraps
from pathlib import Path
import sys

import click

from .controller import CampaignController
from .identity import verify_dependencies
from .report import render_report
from .runtime import registry
from .serialization import canonical_json
from .service import CampaignError
from .spec import CampaignSpec
from .store import StoreError


def _source_root(specification: Path, declared: Path | None) -> Path:
    if declared is not None:
        return declared.absolute()
    for parent in specification.absolute().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src/autoengineering").is_dir():
            return parent
    raise ValueError("source bundle root is unavailable; supply --source-root")


def errors(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (ValueError, TypeError, OSError, StoreError) as error:
            code = error.code if isinstance(error, CampaignError) else "schema_error"
            click.echo(canonical_json({"status": "error", "error": code}))
            raise click.exceptions.Exit(3 if code == "identity_mismatch" else 2) from None

    return wrapped


def summary(controller):
    projection = controller.store.replay()
    state = controller.state(projection)
    return {
        "campaign_id": controller.spec.name,
        "state": projection.state,
        "revision": projection.revision,
        "outcome": state.outcome,
        "physical_attempts": len(state.budget.attempts),
        "unresolved_attempts": state.budget.unresolved_attempts,
        "confirmation": state.confirmation,
    }


def _finish(controller):
    controller.advance()
    result = summary(controller)
    click.echo(canonical_json(result))
    if result["state"] == "reconciliation_required":
        raise click.exceptions.Exit(4)
    if result["outcome"] == "failed_execution":
        raise click.exceptions.Exit(5)


@click.group()
def campaign():
    """Run deterministic campaigns with supplied trusted adapters (experimental)."""


@campaign.command("validate")
@click.argument("specification", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--source-root", type=click.Path(file_okay=False, path_type=Path))
@errors
def validate_command(specification, source_root):
    """Validate schema and declared dependencies without importing a scientific model."""
    spec = CampaignSpec.from_yaml(specification)
    root = _source_root(specification, source_root)
    verify_dependencies(spec, root)
    for adapter in spec.execution.adapter_ids:
        registry(spec=spec, root=root).validate(adapter, spec.baseline.model, root)
    click.echo(
        canonical_json({"status": "ok", "campaign_id": spec.name, "spec_digest": spec.digest})
    )


@campaign.command("run")
@click.argument("specification", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--source-root", type=click.Path(file_okay=False, path_type=Path))
@click.option("--workdir", required=True, type=click.Path(file_okay=False, path_type=Path))
@click.option("--max-new-evaluations", type=click.IntRange(min=0))
@errors
def run_command(specification, source_root, workdir, max_new_evaluations):
    """Create a campaign in a fresh directory and run within the invocation limit."""
    controller = CampaignController.create(
        specification,
        _source_root(specification, source_root),
        workdir,
        max_new_evaluations=max_new_evaluations,
    )
    click.echo(f"Campaign {controller.spec.name}: starting", err=True)
    _finish(controller)


@campaign.command("resume")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--max-new-evaluations", type=click.IntRange(min=0))
@errors
def resume_command(workdir, max_new_evaluations):
    """Resume an unchanged scientific contract after verifying its original dependencies."""
    controller = CampaignController.open(workdir, max_new_evaluations=max_new_evaluations)
    click.echo(f"Campaign {controller.spec.name}: resuming", err=True)
    _finish(controller)


@campaign.command("status")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--format", "format_", type=click.Choice(("text", "json")), default="text")
@errors
def status_command(workdir, format_):
    """Inspect committed state without running models or reading private observation data."""
    controller = CampaignController.open(workdir, inspect_only=True)
    result = summary(controller)
    click.echo(
        canonical_json(result)
        if format_ == "json"
        else "\n".join(f"{key}: {value}" for key, value in result.items())
    )


@campaign.command("cancel")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--request-id", required=True)
@errors
def cancel_command(workdir, request_id):
    """Deposit a cancellation intent without waiting for the active journal writer."""
    controller = CampaignController.open(workdir, inspect_only=True)
    intent = controller.cancel(request_id)
    click.echo(canonical_json(dict(intent, status="queued")))


@campaign.command("request")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@errors
def request_command(workdir):
    """Read one bounded JSON envelope from stdin and return one JSON response."""
    raw = sys.stdin.buffer.read(65537)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = "invalid UTF-8 transport"
    from .records import Request, Response

    try:
        request = Request.from_json(text)
    except ValueError:
        request = None
    controller = CampaignController.open(
        workdir,
        inspect_only=request is not None and request.operation in ("state", "report", "cancel"),
    )
    response = Response.from_json(controller.service.request_bytes(raw))
    click.echo(response.to_json())
    if response.status == "error":
        raise click.exceptions.Exit(2)


@campaign.command("report")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--format", "format_", type=click.Choice(("markdown", "json")), default="markdown")
@errors
def report_command(workdir, format_):
    """Regenerate an evidence report without scientific execution or observation access."""
    controller = CampaignController.open(workdir, inspect_only=True)
    state = controller.state()
    click.echo(
        canonical_json(
            {
                "campaign_id": controller.spec.name,
                "spec_digest": controller.spec.digest,
                "records": state.to_dict(),
            }
        )
        if format_ == "json"
        else render_report(controller.spec, state)
    )
