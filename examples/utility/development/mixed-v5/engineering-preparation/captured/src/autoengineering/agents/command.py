"""Experimental worker CLI. Read-only commands import no host or scientific controller."""

from __future__ import annotations

from functools import wraps
from pathlib import Path

import click

from autoengineering.campaign.serialization import canonical_json, unique_json

from .records import AgentRunSpec
from .report import evidence_report, render_report
from .store import WorkerStore


def errors(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except (ValueError, TypeError, OSError) as error:
            click.echo(canonical_json({"status": "error", "error": str(error)}))
            raise click.exceptions.Exit(2) from None

    return wrapped


def _binding(spec, campaign):
    from autoengineering.campaign.artifacts import confined_file
    from autoengineering.campaign.spec import CampaignSpec

    original = CampaignSpec.from_yaml(confined_file(campaign, "campaign.yaml"))
    identity = unique_json(confined_file(campaign, "identity.json").read_text())
    if original.digest != identity["spec_digest"]:
        raise ValueError("scientific campaign manifest identity mismatch")
    if (spec.campaign_id, spec.campaign_identity) != (
        original.name,
        identity["scientific_identity"],
    ):
        raise ValueError("worker and scientific campaign identities differ")
    allowed = {value for item in original.interventions for value in item.implementation_ids}
    if not set(spec.permitted_interventions) <= allowed:
        raise ValueError("worker run expands scientific interventions")


def _host(spec, host_config=None, *, campaign, workdir=None):
    if spec.host.kind == "fake":
        if host_config is not None:
            raise ValueError("--host-config requires a codex subscription run")
        from .hosts.scripted import scripted_host

        return scripted_host(spec.workflow_route), None
    if host_config is None:
        raise ValueError("codex subscription runs require explicit --host-config")
    from .host_configuration import HostConfiguration

    configuration = HostConfiguration.from_file(host_config)
    configuration.check_scope(campaign, *((workdir,) if workdir is not None else ()))
    return configuration.build(spec), configuration


def _bind_host_configuration(store, host, configuration):
    if configuration is None:
        return
    from .records import HostConfigurationBinding

    expected = HostConfigurationBinding(
        "1.0", store.spec.id, configuration.digest, host.capabilities()
    )
    with store.operation(), store.writer():
        projection = store.replay()
        if projection.host_configuration is not None:
            if projection.host_configuration != expected:
                raise ValueError("host configuration changed during the worker run")
        elif len(projection.events) == 1:
            store.commit(expected)
        else:
            raise ValueError("existing worker activity has no original host configuration binding")


def _recover_preparations(broker, qualification_root):
    """Reconcile fixed source checks before permitting another host/scientific action."""
    from autoengineering.campaign.artifacts import read_bytes
    from .preparation import PreparationSpec, SourcePreparation

    pending = broker.store.replay().pending_preparations
    if pending and qualification_root is None:
        raise ValueError(
            "pending source checks require --qualification-root; their stored digest cannot change"
        )
    for value in pending:
        config = PreparationSpec.from_json(
            read_bytes(broker.store.root, value.configuration).decode()
        )
        manager = SourcePreparation(broker, qualification_root, config.qualification_digest)
        manager.check(value.id)


def _execute(store, campaign, max_new_evaluations, qualification_root=None, *, host=None):
    from autoengineering.campaign.controller import CampaignController
    from .broker import workflow_broker, WorkflowStopped
    from .scheduler import SerialScheduler
    from .deadline import DeadlineForwardingError

    has_preparation = bool(store.replay().preparations)
    controller = CampaignController.open(
        campaign, max_new_evaluations=max_new_evaluations, inspect_only=has_preparation
    )
    if host is None:
        host, _ = _host(store.spec, campaign=campaign, workdir=store.root)
    broker = workflow_broker(controller, SerialScheduler(store, host))
    stopped = None
    try:
        if has_preparation:
            # Preparation is an explicit branch of a generated run. Completion
            # awaits trusted admission/forking, never another parent evaluation.
            try:
                _recover_preparations(broker, qualification_root)
            except (ValueError, OSError, TypeError) as error:
                stopped = str(error)
        else:
            broker.advance()
    except (WorkflowStopped, DeadlineForwardingError) as error:
        stopped = str(error)
    result = evidence_report(store)
    if stopped:
        result["workflow_stop"] = stopped
    click.echo(canonical_json(result))
    if stopped or result["status"] in ("reconciliation_required", "stopped", "cancel_queued"):
        raise click.exceptions.Exit(4)


@click.group()
def agents():
    """Bounded worker workflows with fake or explicitly configured Codex hosts."""


@agents.command("validate")
@click.argument("specification", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--campaign", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    "--host-config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Explicit native profile and prepared-lease metadata TOML. No credential discovery.",
)
@errors
def validate_command(specification, campaign, host_config):
    """Validate worker identity and campaign binding without starting a host."""
    from .scheduler import validate_run_spec

    spec = AgentRunSpec.from_file(specification)
    validate_run_spec(spec)
    _binding(spec, campaign)
    _host(spec, host_config, campaign=campaign)
    click.echo(canonical_json({"status": "ok", "run_digest": spec.digest}))


@agents.command("run")
@click.argument("specification", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--campaign", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option("--workdir", required=True, type=click.Path(file_okay=False, path_type=Path))
@click.option("--max-new-evaluations", type=click.IntRange(min=0))
@click.option(
    "--host-config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Explicit native profile and prepared-lease metadata TOML.",
)
@errors
def run_command(specification, campaign, workdir, max_new_evaluations, host_config):
    """Start a fresh worker run over an explicitly selected scientific campaign."""
    from .scheduler import validate_run_spec

    spec = AgentRunSpec.from_file(specification)
    validate_run_spec(spec)
    _binding(spec, campaign)
    host, configuration = _host(spec, host_config, campaign=campaign, workdir=workdir)
    store = WorkerStore.create(workdir, spec)
    _bind_host_configuration(store, host, configuration)
    click.echo(f"Worker run {spec.id}: starting", err=True)
    _execute(store, campaign, max_new_evaluations, host=host)


@agents.command("resume")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--campaign", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option("--max-new-evaluations", type=click.IntRange(min=0))
@click.option(
    "--qualification-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Existing source-check qualification. Its digest is taken from the stored preparation.",
)
@click.option(
    "--host-config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Original native profile and prepared-lease metadata. Changes are rejected.",
)
@errors
def resume_command(workdir, campaign, max_new_evaluations, qualification_root, host_config):
    """Resume with stored identities, permissions and original worker limits."""
    store = WorkerStore(workdir)
    _binding(store.spec, campaign)
    if qualification_root is not None and store.spec.execution_mode != "generated":
        raise ValueError("--qualification-root applies only to generated source preparation")
    host, configuration = _host(store.spec, host_config, campaign=campaign, workdir=store.root)
    _bind_host_configuration(store, host, configuration)
    click.echo(f"Worker run {store.spec.id}: resuming", err=True)
    _execute(store, campaign, max_new_evaluations, qualification_root, host=host)


@agents.command("status")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@errors
def status_command(workdir):
    """Inspect verified worker evidence without host or campaign access."""
    report = evidence_report(WorkerStore(workdir))
    click.echo(
        canonical_json(
            {
                key: report[key]
                for key in (
                    "run_id",
                    "status",
                    "allowances",
                    "pending_invocations",
                    "pending_campaign_actions",
                    "pending_source_preparations",
                    "campaign_outcome",
                    "worker_stop",
                    "scientific_stop",
                    "deadline_notices",
                )
            }
        )
    )


@agents.command("report")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--format", "format_", type=click.Choice(("json", "markdown")), default="json")
@errors
def report_command(workdir, format_):
    """Reconstruct raw/normalized evidence links without executing work."""
    report = evidence_report(WorkerStore(workdir))
    click.echo(canonical_json(report) if format_ == "json" else render_report(report))


@agents.command("batch-prepare")
@click.argument("specification", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--workdir", required=True, type=click.Path(file_okay=False, path_type=Path))
@errors
def batch_prepare_command(specification, workdir):
    """Freeze shared batch allowances. Does not launch work or grant live authority."""
    from .batch import BatchSpec, BatchStore

    batch = BatchStore.create(workdir, BatchSpec.from_file(specification))
    click.echo(canonical_json(batch.report()))


@agents.command("batch-status")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--expected-digest", help="Optional reviewed batch manifest pin for read-only inspection."
)
@errors
def batch_status_command(workdir, expected_digest):
    """Reconstruct a batch journal without loading a host or scientific controller."""
    from .batch import BatchStore

    click.echo(canonical_json(BatchStore(workdir, expected_digest=expected_digest).report()))


@agents.command("conformance-prepare")
@click.argument("specification", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--campaign", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    "--host-config", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option("--output", required=True, type=click.Path(file_okay=False, path_type=Path))
@click.option("--runtime-root", required=True, type=click.Path(file_okay=False, path_type=Path))
@errors
def conformance_prepare_command(specification, campaign, host_config, output, runtime_root):
    """Capture review inputs without credentials, execution or a running batch clock."""
    from .conformance import prepare_conformance, inspect_conformance
    from .host_configuration import HostConfiguration

    configuration = HostConfiguration.from_file(host_config)
    plan = prepare_conformance(
        AgentRunSpec.from_file(specification), campaign, configuration, output, runtime_root
    )
    click.echo(
        canonical_json(
            inspect_conformance(output, expected_digest=plan.digest, configuration=configuration)
        )
    )


@agents.command("conformance-inspect")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--expected-digest", required=True)
@click.option("--host-config", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@errors
def conformance_inspect_command(workdir, expected_digest, host_config):
    """Verify pinned preparation and report unfinished execution handlers."""
    from .conformance import inspect_conformance
    from .host_configuration import HostConfiguration

    configuration = HostConfiguration.from_file(host_config) if host_config is not None else None
    click.echo(
        canonical_json(
            inspect_conformance(
                workdir, expected_digest=expected_digest, configuration=configuration
            )
        )
    )


def _conformance_execution(
    preparation, expected_digest, host_config, max_new_cases, runtime_digest=None
):
    from .conformance_runtime import ConformanceRuntime
    from .host_configuration import HostConfiguration

    configuration = HostConfiguration.from_file(host_config)
    if runtime_digest is None:
        runtime = ConformanceRuntime.create(
            preparation,
            expected_digest=expected_digest,
            configuration=configuration,
        )
    else:
        runtime = ConformanceRuntime.open(
            preparation,
            expected_digest=expected_digest,
            configuration=configuration,
            runtime_digest=runtime_digest,
        )
    click.echo(
        canonical_json(
            {
                "event": "conformance_runtime_created"
                if runtime_digest is None
                else "conformance_runtime_opened",
                "preparation_digest": expected_digest,
                "runtime_digest": runtime.batch.digest,
                "runtime_root": str(runtime.batch.root),
            }
        ),
        err=True,
    )
    report = runtime.advance(max_new_cases=max_new_cases)
    click.echo(canonical_json(report))
    if report["status"] == "failed":
        raise click.exceptions.Exit(4)
    if report["status"] == "reconciliation_required":
        raise click.exceptions.Exit(3)


@agents.command("conformance-run")
@click.argument("preparation", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--expected-digest", required=True)
@click.option(
    "--host-config", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option("--max-new-cases", type=click.IntRange(min=0))
@errors
def conformance_run_command(preparation, expected_digest, host_config, max_new_cases):
    """Execute the pinned preparation in its absent runtime root. Requires live authority."""
    _conformance_execution(preparation, expected_digest, host_config, max_new_cases)


@agents.command("conformance-resume")
@click.argument("preparation", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--expected-digest", required=True)
@click.option("--runtime-digest", required=True)
@click.option(
    "--host-config", required=True, type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option("--max-new-cases", type=click.IntRange(min=0))
@errors
def conformance_resume_command(
    preparation, expected_digest, runtime_digest, host_config, max_new_cases
):
    """Recover the original pinned runtime and continue within its existing allowances."""
    _conformance_execution(preparation, expected_digest, host_config, max_new_cases, runtime_digest)


@agents.command("conformance-status")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--expected-digest", required=True)
@errors
def conformance_status_command(workdir, expected_digest):
    """Read saved case proofs without importing physical execution implementations."""
    from .conformance_report import read_report

    click.echo(canonical_json(read_report(workdir, expected_digest=expected_digest)))


@agents.command("cancel")
@click.argument("workdir", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--campaign", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@errors
def cancel_command(workdir, campaign):
    """Queue independent worker and scientific cancellation intents."""
    from autoengineering.campaign.execution import cancellation_intent
    from .broker import action_id

    store = WorkerStore(workdir)
    _binding(store.spec, campaign)
    worker = store.request_cancel()
    science = cancellation_intent(
        campaign, action_id("cancel", store.spec.id), campaign_id=store.spec.campaign_id
    )
    click.echo(
        canonical_json(
            {
                "worker_intent": worker,
                "scientific_intent": science,
                "worker_stop": "queued",
                "scientific_stop": "queued",
            }
        )
    )
