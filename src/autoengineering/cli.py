"""CLI for the autoengineering package."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.markdown import Markdown

from autoengineering.system.graph import System

console = Console()


@click.group()
@click.version_option(package_name="autoengineering")
def cli():
    """Autoengineering: AI-assisted systems engineering for complex model chains."""
    pass


@cli.command()
@click.argument("system_file", type=click.Path(exists=True))
def describe(system_file):
    """Print a description of the system."""
    system = System.from_yaml(system_file)
    console.print(Markdown(system.describe()))


@cli.command()
@click.argument("system_file", type=click.Path(exists=True))
def graph(system_file):
    """Print the system as a Mermaid diagram."""
    system = System.from_yaml(system_file)
    click.echo(system.to_mermaid())


@cli.command()
@click.argument("system_file", type=click.Path(exists=True))
@click.option("--component", "-c", required=True, help="Component name to validate.")
@click.option("--baseline", "-b", required=True, type=click.Path(exists=True), help="Path to baseline data (CSV).")
@click.option("--simulated", "-s", required=True, type=click.Path(exists=True), help="Path to simulated data (CSV).")
@click.option("--metrics", "-m", multiple=True, default=None, help="Metrics to compute (default: all).")
@click.option("--format", "fmt", type=click.Choice(["text", "json"]), default="text")
def validate(system_file, component, baseline, simulated, metrics, fmt):
    """Validate a component against baseline data."""
    import numpy as np
    import pandas as pd

    from autoengineering.validate.compare import validate_arrays

    system = System.from_yaml(system_file)
    system.get_component(component)  # verify it exists

    # Load data
    baseline_data = pd.read_csv(baseline)
    simulated_data = pd.read_csv(simulated)

    # Use the first numeric column if multiple exist
    obs = baseline_data.select_dtypes(include=[np.number]).iloc[:, 0].values
    sim = simulated_data.select_dtypes(include=[np.number]).iloc[:, 0].values

    metric_list = list(metrics) if metrics else None
    results = validate_arrays(component, obs, sim, metrics=metric_list)

    if fmt == "json":
        click.echo(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        for r in results:
            click.echo(r.to_markdown())


@cli.command()
@click.argument("system_file", type=click.Path(exists=True))
@click.option("--results", "-r", required=True, type=click.Path(exists=True), help="Path to validation results JSON.")
@click.option("--format", "fmt", type=click.Choice(["markdown", "json"]), default="markdown")
def report(system_file, results, fmt):
    """Generate an analysis report from validation results."""
    from autoengineering.analyze.report import generate_report
    from autoengineering.validate.compare import ValidationResult

    system = System.from_yaml(system_file)

    with open(results) as f:
        raw = json.load(f)

    validation_results = [
        ValidationResult(**r) for r in raw
    ]

    output = generate_report(system, validation_results, format=fmt)

    if fmt == "markdown":
        console.print(Markdown(output))
    else:
        click.echo(output)


@cli.command()
@click.argument("system_file", type=click.Path(exists=True))
def components(system_file):
    """List all components in the system."""
    system = System.from_yaml(system_file)
    for name in system.component_names:
        comp = system.get_component(name)
        click.echo(f"  {name} ({comp.model_type})" if comp.model_type else f"  {name}")


@cli.command()
@click.argument("system_file", type=click.Path(exists=True))
@click.option("--component", "-c", required=True, help="Component to research replacements for.")
@click.option("--output", "-o", type=click.Path(), default=None, help="Write the scaffold to this file.")
def candidates(system_file, component, output):
    """Scaffold a candidates YAML for a component (fill in via deep research)."""
    from autoengineering.research.candidates import candidate_template

    system = System.from_yaml(system_file)
    comp = system.get_component(component)  # raises if missing
    template = candidate_template(comp)

    if output:
        with open(output, "w") as f:
            f.write(template)
        click.echo(f"Wrote candidate scaffold for '{component}' to {output}")
    else:
        click.echo(template)


@cli.command()
@click.argument("system_file", type=click.Path(exists=True))
@click.option("--candidates", "-C", "candidates_file", required=True, type=click.Path(exists=True), help="Candidates YAML from deep research.")
@click.option("--chain", required=True, help="run_chain factory as 'module:callable'; called with the system to get {output: array}.")
@click.option("--observed", "-b", required=True, type=click.Path(exists=True), help="Observed data (CSV, first numeric column).")
@click.option("--output", "-O", "validate_output", required=True, help="Which run_chain output key to score.")
@click.option("--metrics", "-m", multiple=True, default=None, help="Metrics to compute (default: rmse bias nse kge).")
@click.option("--target", "-t", multiple=True, help="Satisficing target as metric=value (e.g. nse=0.5). Repeatable.")
@click.option("--max-iter", type=int, default=20, help="Maximum candidates to evaluate.")
@click.option("--workdir", type=click.Path(), default="outputs", help="Where to write artifacts.")
@click.option("--slug", default="auto-improve", help="Artifact name slug.")
def improve(system_file, candidates_file, chain, observed, validate_output, metrics, target, max_iter, workdir, slug):
    """Run the bounded auto-research loop over candidate replacements."""
    import numpy as np
    import pandas as pd

    from autoengineering.research.candidates import load_candidates
    from autoengineering.research.loop import auto_improve
    from autoengineering.research.provenance import write_report
    from autoengineering.research.runner import _load_callable

    system = System.from_yaml(system_file)
    cands = load_candidates(candidates_file)

    # The --chain entry is a factory that, given the system, returns run_chain.
    chain_factory = _load_callable(chain)
    run_chain = chain_factory(system)

    obs_df = pd.read_csv(observed)
    obs = obs_df.select_dtypes(include=[np.number]).iloc[:, 0].values

    target_dict = {}
    for t in target:
        key, _, val = t.partition("=")
        target_dict[key.strip()] = float(val)

    tree = auto_improve(
        system,
        run_chain,
        obs,
        validate_output=validate_output,
        candidates=cands,
        metrics=list(metrics) or None,
        target=target_dict or None,
        max_iterations=max_iter,
        workdir=workdir,
        slug=slug,
    )

    report_path, prov_path = write_report(tree, system, slug, workdir)
    click.echo(tree.to_markdown())  # pre-formatted tree; echo verbatim to keep indentation
    click.echo(f"\nReport:     {report_path}")
    click.echo(f"Provenance: {prov_path}")


@cli.command()
@click.argument("tree_file", type=click.Path(exists=True))
def experiments(tree_file):
    """Render a saved experiment tree (autoresearch.jsonl)."""
    from autoengineering.research.experiment import ExperimentTree

    tree = ExperimentTree.from_jsonl(tree_file)
    click.echo(tree.to_markdown())  # pre-formatted tree; echo verbatim to keep indentation


if __name__ == "__main__":
    cli()
