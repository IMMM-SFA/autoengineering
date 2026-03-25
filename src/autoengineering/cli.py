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


if __name__ == "__main__":
    cli()
