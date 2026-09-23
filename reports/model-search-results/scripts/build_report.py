"""Verify RESULTS.md aggregates, then build interactive figures and static SVGs."""

from __future__ import annotations

import ast
import csv
import hashlib
import html
import json
from pathlib import Path
from statistics import mean, median

import matplotlib

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import get_plotlyjs

REPORT = Path(__file__).resolve().parents[1]
REPO = REPORT.parents[1]
matplotlib.use("Agg")

DATA = REPO / "examples/complex_models/results"
CHAINS = REPO / "examples/open_chains/results"
METHODS = ["random", "sobol", "bo"]
COLORS = {"random": "#A96C2B", "sobol": "#237F79", "bo": "#85506E"}
METHOD_NAMES = {"random": "Random", "sobol": "Sobol", "bo": "BO"}
DOMAINS = ["hydro", "solar", "copper", "hymod", "solar_diode"]
NAMES = {
    "hydro": "Simple hydrology",
    "solar": "Simple solar",
    "copper": "Copper",
    "hymod": "HYMOD",
    "solar_diode": "Single-diode solar",
}
UNITS = {
    "hydro": "mm/day",
    "hymod": "mm/day",
    "solar": "kW",
    "solar_diode": "kW",
    "copper": "source units",
}
CHECKPOINTS = [12, 24, 48, 96]
INPUTS = {}
FIGURES = []
EXPORTS = {}
plt.rcParams.update(
    {
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.labelcolor": "#333333",
        "text.color": "#333333",
        "svg.fonttype": "none",
        "svg.hashsalt": "model-search-results",
        "figure.facecolor": "white",
        "axes.prop_cycle": plt.cycler(color=list(COLORS.values())),
    }
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source(path: Path):
    INPUTS[str(path.relative_to(REPO))] = digest(path)
    return json.loads(path.read_text())


def markdown_tables(text: str) -> dict:
    tables = {}
    lines = text.splitlines()
    for i, line in enumerate(lines[:-1]):
        if line.startswith("| ") and lines[i + 1].startswith("| ---"):
            header = tuple(x.strip() for x in line.strip("|").split("|"))
            rows = []
            for other in lines[i + 2 :]:
                if not other.startswith("| "):
                    break
                rows.append([x.strip() for x in other.strip("|").split("|")])
            tables[header] = rows
    return tables


def validate_matrix(name: str) -> list:
    directory = DATA / name
    rows = source(directory / "results.json")["runs"]
    manifest = source(directory / "manifest.json")
    audit = source(DATA / f"{name}-audit.json")
    assert audit["results_sha256"] == digest(directory / "results.json")
    assert audit["source_sha256"] == digest(REPO / "scripts/audit_complex_models.py")
    expected = {(d, m, s) for d in DOMAINS for m in METHODS for s in manifest["seeds"]}
    assert len(rows) == len(expected)
    assert {(r["domain"], r["method"], r["seed"]) for r in rows} == expected
    assert audit["attempts"] == sum(r["evaluations"] for r in rows)
    assert not audit["failures"], "This report expects the audited zero-failure matrix"
    ledger_hashes = {}
    for r in rows:
        key = f"{r['domain']}-{r['method']}-{r['seed']}"
        assert r["cap"] == manifest["cap"] and r["evaluations"] <= r["cap"]
        ledger = directory / key / "observations.jsonl"
        ledger_hashes[key] = digest(ledger)
        assert source(directory / key / "application-result.json") == r
        assert source(directory / key / "frozen-recommendation.json") == r["recommendation"]
    assert audit["ledger_sha256"] == ledger_hashes
    INPUTS.update(
        {
            str((directory / k / "observations.jsonl").relative_to(REPO)): v
            for k, v in ledger_hashes.items()
        }
    )
    return rows


def group(rows: list, domain: str, method: str) -> list:
    return sorted(
        [r for r in rows if r["domain"] == domain and r["method"] == method],
        key=lambda r: r["seed"],
    )


def verify_markdown(fixed: list, target: list, chains: dict) -> int:
    path = DATA / "RESULTS.md"
    INPUTS[str(path.relative_to(REPO))] = digest(path)
    tables = markdown_tables(path.read_text())
    checked = 0
    for header, rows in tables.items():
        for cells in rows:
            expected = None
            if header[:3] == ("Model", "Method", "Test at 12"):
                g = group(fixed, *cells[:2])
                expected = cells[:2] + [
                    f"{median(r['checkpoints'][i]['test']['rmse'] for r in g):.4f}"
                    for i in range(4)
                ]
                expected += [
                    f"{median(r['recommendation']['outcomes']['rmse'] for r in g):.4f}",
                    f"{median(r['study_seconds'] for r in g):.2f}",
                ]
            elif header[:3] == ("Model", "Method", "Validation at 12"):
                g = group(fixed, *cells[:2])
                expected = cells[:2] + [
                    f"{median(r['checkpoints'][i]['recommendation']['outcomes']['rmse'] for r in g):.4f}"
                    for i in range(4)
                ]
            elif header[:3] == ("Model", "Target", "Method"):
                g = group(target, cells[0], cells[2])
                hits = [r for r in g if r["target_reached"]]
                calls = ", ".join(
                    str(r["evaluations"]) if r["target_reached"] else f">{r['cap']}" for r in g
                )
                expected = [
                    cells[0],
                    f"{g[0]['target']:.4f}",
                    cells[2],
                    f"{len(hits)}/{len(g)}",
                    calls,
                    str(median(r["evaluations"] for r in hits)) if hits else "NA",
                    f"{mean(r['evaluations'] for r in g):.1f}",
                    f"{median(r['study_seconds'] for r in g):.3f}",
                    f"{median(r['test']['rmse'] for r in g):.4f}",
                ]
            elif header[:3] == ("Experiment", "Model", "Method"):
                g = group(fixed if cells[0] == "fixed" else target, cells[1], cells[2])
                # Action classifications were verified by the canonical summary. Recheck timing here.
                assert cells[3:5] == [
                    f"{median(r['model_seconds'] for r in g):.3f}",
                    f"{median(r['controller_and_optimizer_seconds'] for r in g):.3f}",
                ]
                checked += 1
            elif header[:2] == ("Chain", "Selection objective (minimize)"):
                s, trials = chains[cells[0]]
                expected = [
                    cells[0],
                    s["objective"],
                    f"{s['baseline']:.6g}",
                    f"{s['selected_value']:.6g}",
                    f"{s['gain']:.6g}",
                    str(len(trials)),
                    f"{sum(r['seconds'] for r in trials):.3f}",
                ]
            elif header[:3] == ("Chain", "Candidate", "Status"):
                trials = chains[cells[0]][1]
                assert next(t for t in trials if t["id"] == cells[1])["status"] == cells[2]
                checked += 1
            if expected is not None:
                assert cells == expected, (header, cells, expected)
                checked += 1
    assert checked == 88, f"Unexpected Markdown table coverage: {checked}"
    return checked


def style(fig: go.Figure, height: int = 500, legend: bool = True) -> go.Figure:
    fig.update_layout(
        template="none",
        title=None,
        height=height,
        autosize=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=13, color="#333333"),
        margin=dict(t=35, r=25, b=160 if legend else 85, l=75),
        legend=dict(orientation="h", x=0, y=-0.2, xanchor="left", yanchor="top"),
        showlegend=legend,
        hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(automargin=True, title_standoff=12, gridcolor="#dddddd", zeroline=False)
    fig.update_yaxes(automargin=True, title_standoff=12, gridcolor="#dddddd", zeroline=False)
    return fig


def save_svg(fig, name: str) -> str:
    filename = f"figures/{name}.svg"
    fig.savefig(REPORT / filename, bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)
    return filename


def register(identifier: str, title: str, caption: str, variants: list, default: int = 0) -> None:
    """Every variant stores its Plotly spec and an independently rendered static fallback."""
    for variant in variants:
        variant["figure"] = json.loads(variant["figure"].to_json())
        (REPORT / "figures" / f"{identifier}-{variant['key']}.json").write_text(
            json.dumps(variant["figure"], indent=2) + "\n"
        )
    FIGURES.append(
        dict(id=identifier, title=title, caption=caption, variants=variants, default=default)
    )


def calls_figure(target: list) -> None:
    fig = make_subplots(
        rows=len(DOMAINS),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.055,
        subplot_titles=[NAMES[d] for d in DOMAINS],
    )
    sf, axes = plt.subplots(5, 1, figsize=(9, 10), sharex=True, layout="constrained")
    exported = []
    for row, (d, ax) in enumerate(zip(DOMAINS, axes), 1):
        for j, m in enumerate(METHODS):
            g = group(target, d, m)
            x = [r["evaluations"] for r in g]
            y = [j + (i - (len(g) - 1) / 2) * 0.085 for i in range(len(g))]
            symbols = ["circle" if r["target_reached"] else "triangle-right-open" for r in g]
            custom = [
                [r["seed"], r["stop_reason"], r["target"], r["recommendation"]["outcomes"]["rmse"]]
                for r in g
            ]
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    mode="markers",
                    name=METHOD_NAMES[m],
                    marker=dict(color=COLORS[m], size=10, symbol=symbols, line_width=1.5),
                    customdata=custom,
                    showlegend=False,
                    hovertemplate=METHOD_NAMES[m]
                    + " seed %{customdata[0]}<br>%{x} calls<br>%{customdata[1]}<br>Target %{customdata[2]:.4f}<br>Validation %{customdata[3]:.4f}<extra></extra>",
                ),
                row=row,
                col=1,
            )
            for value, pos, r in zip(x, y, g):
                ax.scatter(
                    value,
                    pos,
                    color=COLORS[m] if r["target_reached"] else "none",
                    edgecolors=COLORS[m],
                    marker="o" if r["target_reached"] else ">",
                    s=40,
                )
                exported.append(
                    {
                        k: r[k]
                        for k in [
                            "domain",
                            "method",
                            "seed",
                            "evaluations",
                            "target_reached",
                            "stop_reason",
                            "target",
                        ]
                    }
                )
        cap = g[0]["cap"]
        fig.add_vline(x=cap, line_dash="dot", line_color="#888888", row=row, col=1)
        fig.update_yaxes(
            tickvals=[0, 1, 2],
            ticktext=["Random", "Sobol", "BO"],
            range=[-0.4, 2.4],
            row=row,
            col=1,
        )
        ax.set(
            yticks=[0, 1, 2],
            yticklabels=["Random", "Sobol", "BO"],
            ylim=(-0.4, 2.4),
            title=NAMES[d],
            xscale="log",
            xlim=(0.8, 3100),
        )
        ax.axvline(cap, color="#888888", ls=":", lw=1)
        ax.grid(axis="x", alpha=0.2)
    fig.update_xaxes(
        type="log",
        range=[np.log10(0.8), np.log10(3100)],
        tickmode="array",
        tickvals=[1, 10, 100, 1000, 2000],
        minorloglabels="none",
    )
    fig.update_xaxes(title_text="Model calls (log scale)", row=5, col=1)
    axes[-1].set_xlabel("Model calls (log scale)")
    style(fig, 1030, False)
    register(
        "target-calls",
        "Target attainment differs across problems",
        "Each point is one seed. Filled circles reached the frozen validation target; open right-facing triangles exhausted the cap and remain censored. Small vertical offsets separate seeds. The dotted line marks the cap. Easy cases often finish during Sobol initialization, before BO makes an adaptive suggestion.",
        [dict(key="all", label="All models", figure=fig, svg=save_svg(sf, "target-calls"))],
    )
    EXPORTS["target-calls"] = exported


def progress_figure(fixed: list) -> None:
    variants, exported = [], []
    for d in DOMAINS:
        fig = make_subplots(
            rows=2,
            cols=1,
            vertical_spacing=0.20,
            subplot_titles=["Validation: used for selection", "Test: revealed after selection"],
        )
        sf, axes = plt.subplots(2, 1, figsize=(8, 7), layout="constrained")
        for panel, kind in enumerate(["validation", "test"], 1):
            for m in METHODS:
                g = group(fixed, d, m)
                values = [
                    [
                        s["test"]["rmse"]
                        if kind == "test"
                        else s["recommendation"]["outcomes"]["rmse"]
                        for s in r["checkpoints"]
                    ]
                    for r in g
                ]
                for r, ys in zip(g, values):
                    fig.add_trace(
                        go.Scatter(
                            x=CHECKPOINTS,
                            y=ys,
                            mode="lines+markers",
                            line=dict(color=COLORS[m], width=1),
                            marker=dict(size=4),
                            opacity=0.35,
                            name=f"{METHOD_NAMES[m]}, seed {r['seed']}",
                            showlegend=False,
                            hovertemplate=f"{METHOD_NAMES[m]} seed {r['seed']}<br>Calls %{{x}}<br>RMSE %{{y:.4f}}<extra></extra>",
                        ),
                        row=panel,
                        col=1,
                    )
                    axes[panel - 1].plot(
                        CHECKPOINTS, ys, "o-", color=COLORS[m], alpha=0.28, lw=0.8, ms=3
                    )
                    exported.extend(
                        dict(domain=d, method=m, seed=r["seed"], metric=kind, calls=n, rmse=v)
                        for n, v in zip(CHECKPOINTS, ys)
                    )
                med = np.median(values, axis=0)
                fig.add_trace(
                    go.Scatter(
                        x=CHECKPOINTS,
                        y=med,
                        mode="lines+markers",
                        line=dict(color=COLORS[m], width=3),
                        marker=dict(size=7),
                        name=METHOD_NAMES[m],
                        showlegend=panel == 1,
                        hovertemplate=METHOD_NAMES[m]
                        + " median<br>Calls %{x}<br>RMSE %{y:.4f}<extra></extra>",
                    ),
                    row=panel,
                    col=1,
                )
                axes[panel - 1].plot(
                    CHECKPOINTS, med, "o-", color=COLORS[m], lw=2, label=METHOD_NAMES[m]
                )
            fig.update_xaxes(tickvals=CHECKPOINTS, title_text="Model calls", row=panel, col=1)
            fig.update_yaxes(title_text=f"RMSE ({UNITS[d]})", row=panel, col=1)
            axes[panel - 1].set(
                title=["Validation", "Held-out test"][panel - 1],
                xlabel="Model calls",
                ylabel=f"RMSE ({UNITS[d]})",
                xticks=CHECKPOINTS,
            )
            axes[panel - 1].grid(alpha=0.2)
        axes[0].legend(ncol=3, frameon=False)
        variants.append(
            dict(key=d, label=NAMES[d], figure=style(fig, 760), svg=save_svg(sf, f"progress-{d}"))
        )
    register(
        "fixed-progress",
        "Validation gains do not guarantee better test prediction",
        "Bold lines show medians across the fixed-study seeds; faint lines show every seed. Checkpoints belong to the same trajectories and are not independent replications. Lower RMSE is better. The panels have separate vertical scales; no confidence intervals are shown.",
        variants,
        default=DOMAINS.index("hymod"),
    )
    EXPORTS["fixed-progress"] = exported


def time_figure(fixed: list, target: list) -> None:
    variants, exported = [], []
    for experiment, rows in [("fixed", fixed), ("target", target)]:
        for d in DOMAINS:
            fig = go.Figure()
            sf, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
            for field, label, color, offset in [
                ("model_seconds", "Model", "#7895AC", -0.18),
                ("controller_and_optimizer_seconds", "Optimizer + controller", "#C0B9AD", 0.18),
            ]:
                values = [median(r[field] for r in group(rows, d, m)) for m in METHODS]
                fig.add_trace(
                    go.Bar(
                        x=[METHOD_NAMES[m] for m in METHODS],
                        y=values,
                        name=label,
                        marker_color=color,
                        hovertemplate=label + "<br>%{x}<br>%{y:.3f} seconds<extra></extra>",
                    )
                )
                ax.bar(np.arange(3) + offset, values, width=0.34, color=color, label=label)
            totals = [median(r["study_seconds"] for r in group(rows, d, m)) for m in METHODS]
            fig.add_trace(
                go.Scatter(
                    x=[METHOD_NAMES[m] for m in METHODS],
                    y=totals,
                    mode="markers",
                    name="Median total",
                    marker=dict(symbol="diamond", size=10, color="#946842"),
                )
            )
            ax.scatter(
                np.arange(3), totals, marker="D", color="#946842", label="Median total", zorder=4
            )
            for m in METHODS:
                for r in group(rows, d, m):
                    exported.append(
                        dict(
                            experiment=experiment,
                            domain=d,
                            method=m,
                            seed=r["seed"],
                            calls=r["evaluations"],
                            target_reached=r["target_reached"],
                            **{
                                k: r[k]
                                for k in [
                                    "model_seconds",
                                    "controller_and_optimizer_seconds",
                                    "study_seconds",
                                ]
                            },
                        )
                    )
            fig.update_layout(barmode="group")
            fig.update_yaxes(title_text="Elapsed time (seconds)", rangemode="tozero")
            ax.set(
                xticks=range(3),
                xticklabels=[METHOD_NAMES[m] for m in METHODS],
                ylabel="Elapsed time (seconds)",
            )
            ax.legend(frameon=False, ncol=1)
            label = f"{NAMES[d]} - {'fixed calls' if experiment == 'fixed' else 'target or cap'}"
            variants.append(
                dict(
                    key=f"{experiment}-{d}",
                    label=label,
                    figure=style(fig, 510),
                    svg=save_svg(sf, f"time-{experiment}-{d}"),
                )
            )
    register(
        "runtime",
        "Bookkeeping and optimization can dominate model time",
        "Bars show the median of each time component separately; diamonds show median total study time. Medians need not add, so the bars are not stacked. Fixed studies have equal call budgets. Target-study times end at different targets or caps and must be interpreted with the attainment figure. Imports and held-out scoring are excluded. Cached target timings and uncached fixed timings are separate experiments; background tests overlapped some target runs.",
        variants,
        default=3,
    )
    EXPORTS["runtime"] = exported


def dimensions() -> dict:
    result = {}
    for filename in ["examples/local_models/kernels.py", "examples/complex_models/models.py"]:
        path = REPO / filename
        INPUTS[filename] = digest(path)
        fn = next(
            n
            for n in ast.parse(path.read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == "search_space"
        )
        for node in fn.body:
            if (
                isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare)
                and isinstance(node.test.comparators[0], ast.Constant)
            ):
                name = node.test.comparators[0].value
                returns = [n for n in node.body if isinstance(n, ast.Return)]
            elif isinstance(node, ast.Return) and filename.endswith("complex_models/models.py"):
                name, returns = "solar_diode", [node]
            else:
                continue
            if (
                returns
                and isinstance(returns[0].value, ast.Call)
                and isinstance(returns[0].value.func, ast.Name)
                and returns[0].value.func.id == "SearchSpace"
            ):
                result[name] = len(returns[0].value.args[0].elts)
    assert set(result) == set(DOMAINS)
    return result


def complexity_figure(fixed: list) -> None:
    dims = dimensions()
    values = [
        median(r["model_seconds"] / r["evaluations"] * 1000 for r in fixed if r["domain"] == d)
        for d in DOMAINS
    ]
    fig = go.Figure(
        go.Scatter(
            x=[dims[d] for d in DOMAINS],
            y=values,
            mode="markers",
            marker=dict(size=12, color="#4B737A"),
            customdata=[NAMES[d] for d in DOMAINS],
            hovertemplate="%{customdata}<br>%{x} parameters<br>%{y:.2f} ms/call<extra></extra>",
        )
    )
    sf, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    for d, v in zip(DOMAINS, values):
        shift = -20 if d == "solar" else 12
        fig.add_annotation(
            x=dims[d],
            y=np.log10(v),
            text=NAMES[d],
            showarrow=False,
            xanchor="left",
            xshift=12,
            yshift=shift,
        )
        ax.scatter(dims[d], v, s=45, color="#4B737A")
        ax.annotate(NAMES[d], (dims[d], v), xytext=(8, shift), textcoords="offset points")
    fig.update_xaxes(
        title_text="Nominal search parameters",
        range=[1, 10],
        tickvals=sorted(set(dims.values())),
    )
    fig.update_yaxes(
        title_text="Model time (ms/call, log scale)",
        type="log",
        range=[np.log10(5), np.log10(300)],
        tickmode="array",
        tickvals=[5, 10, 20, 50, 100, 200],
        minorloglabels="none",
    )
    ax.set(
        xlim=(1, 10),
        ylim=(5, 300),
        yscale="log",
        xlabel="Nominal search parameters",
        ylabel="Model time (ms/call, log scale)",
        xticks=sorted(set(dims.values())),
    )
    ax.grid(alpha=0.2)
    register(
        "complexity",
        "Parameter count and model cost measure different things",
        "Parameter counts are read from the declared search spaces; a categorical choice counts as one parameter. Cost is the median, across fixed studies, of each study's model time divided by calls. These are implementation- and dataset-specific timings, not an intrinsic complexity score. Effective dimension and interaction strength have not been estimated here.",
        [
            dict(
                key="all",
                label="All models",
                figure=style(fig, 430, False),
                svg=save_svg(sf, "complexity"),
            )
        ],
    )
    EXPORTS["complexity"] = [
        dict(domain=d, nominal_parameters=dims[d], model_ms_per_call=v)
        for d, v in zip(DOMAINS, values)
    ]


def chain_figures(chains: dict) -> None:
    s = chains["solar"][0]
    pairs = [
        ("Selection year", s["baseline"], s["selected_value"]),
        ("Test year", s["test"]["baseline_rmse_kw"], s["test"]["selected_rmse_kw"]),
    ]
    fig = go.Figure()
    sf, ax = plt.subplots(figsize=(8, 3.6), layout="constrained")
    for j, (label, a, b) in enumerate(pairs):
        fig.add_trace(
            go.Scatter(
                x=[a, b],
                y=[label, label],
                mode="lines",
                line=dict(color="#A8A59B"),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        ax.plot([a, b], [j, j], color="#A8A59B")
    for index, label, color in [(1, "Baseline", "#77766D"), (2, "Selected", "#237F79")]:
        fig.add_trace(
            go.Scatter(
                x=[p[index] for p in pairs],
                y=[p[0] for p in pairs],
                mode="markers",
                name=label,
                marker=dict(color=color, size=12),
                hovertemplate=label + "<br>%{y}<br>%{x:.4f} kW<extra></extra>",
            )
        )
        ax.scatter([p[index] for p in pairs], range(2), label=label, color=color, s=45)
    fig.update_xaxes(title_text="AC power RMSE (kW; lower is better)")
    ax.set(
        yticks=range(2),
        yticklabels=[p[0] for p in pairs],
        xlabel="AC power RMSE (kW; lower is better)",
    )
    ax.legend(frameon=False)
    register(
        "solar-chain",
        "Solar: a small improvement survives the temporal split",
        "Baseline and selected thermal components are scored on the same rows within each year. Selection uses 2018; the final comparison uses 2019. This is conditional on measured plane-of-array irradiance, not an irradiance forecasting test. The temporal holdout was inspected during development and is not blind external validation. Implausible module-temperature observations invalidate that diagnostic, while the AC objective is retained.",
        [
            dict(
                key="all",
                label="Solar chain",
                figure=style(fig, 410),
                svg=save_svg(sf, "solar-chain"),
            )
        ],
    )
    EXPORTS["solar-chain"] = [
        dict(period=p[0], baseline_rmse_kw=p[1], selected_rmse_kw=p[2], gain_kw=p[1] - p[2])
        for p in pairs
    ]
    s = chains["wind"][0]
    labels = ["Selection grid", "Finer direction grid"]
    vals = [s["gain"], s["test"]["gain_gwh"]]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=vals,
            marker_color=["#7895AC", "#237F79"],
            text=[f"{v:.4f}" for v in vals],
            textposition="outside",
            hovertemplate="%{x}<br>%{y:.6f} GWh<extra></extra>",
        )
    )
    fig.update_yaxes(
        title_text="Selected minus baseline annual energy (GWh)", range=[0, max(vals) * 1.25]
    )
    sf, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    ax.bar(labels, vals, color=["#7895AC", "#237F79"])
    for j, v in enumerate(vals):
        ax.text(j, v, f"{v:.4f}", ha="center", va="bottom")
    ax.set(ylabel="Annual energy gain (GWh)", ylim=(0, max(vals) * 1.25))
    register(
        "wind-chain",
        "Wind: the apparent gain depends strongly on the direction grid",
        "Both comparisons use the same NOJ wake model. The finer grid is a sensitivity check, not observed plant validation. TOPFARM reached its iteration limits without convergence; the layouts are feasible bounded iterates. The smaller gain on the finer grid limits the design claim.",
        [
            dict(
                key="all",
                label="Wind chain",
                figure=style(fig, 440, False),
                svg=save_svg(sf, "wind-chain"),
            )
        ],
    )
    EXPORTS["wind-chain"] = [dict(grid=label, gain_gwh=v) for label, v in zip(labels, vals)]
    trials = chains["hybrid"][1]
    baseline = trials[0]["metrics"]["revenue_usd"]
    labels = ["Baseline", "CBC: rejected", "CBC: SOC buffer"]
    colors = ["#77766D", "#A34F38", "#237F79"]
    gains = [(t["metrics"]["revenue_usd"] - baseline) / 1000 for t in trials]
    maxima = [t["metrics"]["maximum_soc_percent"] for t in trials]
    fig = make_subplots(
        rows=2,
        cols=1,
        vertical_spacing=0.24,
        subplot_titles=["Annual gross revenue gain", "Maximum simulated state of charge"],
    )
    fig.add_trace(
        go.Bar(
            x=labels,
            y=gains,
            marker_color=colors,
            marker_pattern_shape=["", "x", ""],
            showlegend=False,
            customdata=[t["status"] for t in trials],
            hovertemplate="%{x}<br>%{y:.3f} thousand USD<br>%{customdata}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=labels,
            y=maxima,
            mode="markers+text",
            text=[f"{v:.3f}%" for v in maxima],
            textposition="top center",
            marker=dict(color=colors, size=11),
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    fig.add_hline(y=91, line_color="#A34F38", line_dash="dot", row=2, col=1)
    fig.add_hline(y=90, line_color="#77766D", line_dash="dash", row=2, col=1)
    fig.update_yaxes(title_text="Gain (thousand USD)", rangemode="tozero", row=1, col=1)
    fig.update_yaxes(title_text="Maximum SOC (%)", range=[84, 94], row=2, col=1)
    sf, axes = plt.subplots(2, 1, figsize=(8, 7), layout="constrained")
    axes[0].bar(labels, gains, color=colors)
    axes[0].patches[1].set_hatch("xx")
    axes[0].set_ylabel("Gross revenue gain (thousand USD)")
    axes[1].scatter(labels, maxima, color=colors, s=50)
    for j, v in enumerate(maxima):
        axes[1].annotate(
            f"{v:.3f}%", (j, v), xytext=(0, 8), textcoords="offset points", ha="center"
        )
    axes[1].axhline(91, color="#A34F38", ls=":", label="Screen upper limit")
    axes[1].axhline(90, color="#77766D", ls="--", label="Nominal operating upper limit")
    axes[1].set(ylabel="Maximum SOC (%)", ylim=(84, 94))
    axes[1].legend(frameon=False, loc="lower left")
    register(
        "hybrid-chain",
        "Hybrid: the highest-revenue candidate fails the SOC screen",
        "Hatching marks the excluded CBC policy. The buffered policy is selected from candidates that pass the unchanged screens. The dotted line is the 91% screening upper limit; the dashed line is the nominal 90% operating upper limit. The screen includes numerical tolerance and is not strict operating-limit certification. Revenue assumes perfect 24-hour foresight, a separate price-year scenario, and omits capital, degradation and terminal SOC value. It is neither forecast skill nor realized income.",
        [
            dict(
                key="all",
                label="Hybrid chain",
                figure=style(fig, 740, False),
                svg=save_svg(sf, "hybrid-chain"),
            )
        ],
    )
    EXPORTS["hybrid-chain"] = [
        dict(
            candidate=t["id"],
            status=t["status"],
            revenue_usd=t["metrics"]["revenue_usd"],
            gain_usd=t["metrics"]["revenue_usd"] - baseline,
            maximum_soc_percent=t["metrics"]["maximum_soc_percent"],
            final_soc_percent=t["metrics"]["final_soc_percent"],
        )
        for t in trials
    ]


def write_assets() -> None:
    (REPORT / "assets/plotly.min.js").write_text(get_plotlyjs())
    fragments = []
    for item in FIGURES:
        identifier = item["id"]
        default = item["default"]
        fragments += [
            f"## {item['title']}",
            "",
            "```{=html}",
            f'<section class="figure-block" id="{identifier}">',
        ]
        if len(item["variants"]) > 1:
            fragments += [
                f'<label class="plot-control" for="select-{identifier}">View: <select id="select-{identifier}" aria-label="Choose view for {html.escape(item["title"])}">'
            ]
            fragments += [
                f'<option value="{i}" {"selected" if i == default else ""}>{html.escape(v["label"])}</option>'
                for i, v in enumerate(item["variants"])
            ]
            fragments += ["</select></label>"]
        fragments += [
            f'<div class="interactive-plot" id="plot-{identifier}" role="img" aria-label="{html.escape(item["title"])}"></div>'
        ]
        fragments += [
            f'<img class="print-fallback" src="{v["svg"]}" alt="{html.escape(item["title"] + ": " + v["label"])}" {"hidden" if i != default else ""}>'
            for i, v in enumerate(item["variants"])
        ]
        payload = json.dumps(
            dict(default=default, variants=[v["figure"] for v in item["variants"]])
        ).replace("</", "<\\/")
        fragments += [
            f'<script type="application/json" id="data-{identifier}">{payload}</script>',
            "</section>",
            "```",
            "",
            item["caption"],
            "",
        ]
    (REPORT / "figures.qmd").write_text("\n".join(fragments) + "\n")
    for name, rows in EXPORTS.items():
        with (REPORT / "figures" / f"{name}.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def main() -> None:
    fixed, target = validate_matrix("fixed"), validate_matrix("target-2000")
    chains = {}
    for name in ["solar", "wind", "hybrid"]:
        hashes = source(CHAINS / name / "artifact-sha256.json")
        for filename, expected in hashes.items():
            path = CHAINS / name / filename
            assert digest(path) == expected, path
            INPUTS[str(path.relative_to(REPO))] = expected
        chains[name] = (
            source(CHAINS / name / "summary.json"),
            source(CHAINS / name / "trials.json"),
        )
    checked = verify_markdown(fixed, target, chains)
    print(f"Verified {checked} Markdown data rows against audited records", flush=True)
    for function, args in [
        (calls_figure, (target,)),
        (progress_figure, (fixed,)),
        (time_figure, (fixed, target)),
        (complexity_figure, (fixed,)),
        (chain_figures, (chains,)),
    ]:
        function(*args)
        print(f"Built {function.__name__}", flush=True)
    write_assets()
    cap = target[0]["cap"]
    hits = sum(r["target_reached"] for r in target)
    projected = [r for r in target if "projection" in r]
    excluded = sum(r["projection"]["discarded_from_analysis"] for r in projected)
    bo = group(target, "hymod", "bo")
    random = group(target, "hymod", "random")
    sobol = group(target, "hymod", "sobol")
    summary = f"""The benchmark contains {len(fixed)} fixed-budget studies and {len(target)} target studies.
The target analysis retains {sum(r["evaluations"] for r in target):,} calls under a {cap:,}-call ceiling:
{hits} studies reached their target and {len(target) - hits} were capped. The separate component-swap
examples exercise solar, wind and hybrid energy chains. Figures retain unsuccessful
runs and separate calibration gains from test performance.

HYMOD illustrates the distinction: BO reached the validation target in {sum(r["target_reached"] for r in bo)}/{len(bo)} runs,
with a median of {median(r["evaluations"] for r in bo)} calls. Random and Sobol each reached it in
{sum(r["target_reached"] for r in random)}/{len(random)} and {sum(r["target_reached"] for r in sobol)}/{len(sobol)} runs, respectively.
Yet median test RMSE was {median(r["test"]["rmse"] for r in bo):.4f} mm/day for BO, compared with
{median(r["test"]["rmse"] for r in random):.4f} for random and {median(r["test"]["rmse"] for r in sobol):.4f} for Sobol.
This supports a distinction between target attainment and prediction, rather than a universal winner.
"""
    (REPORT / "summary.qmd").write_text(summary)
    provenance = f"""The cap was reduced retrospectively during the original extended run.
{len(projected)} studies are exact prefixes ending at their first target hit or the new cap;
{excluded:,} later observations remain archived and are excluded from the analysis.
The other {len(target) - len(projected)} studies ran with the reduced cap. Timings of projected runs
end at the retained call. The target values, seeds and data splits were unchanged.

The numeric audit recalculated all {sum(r["evaluations"] for r in target):,} retained target objectives and
all {len(target)} final recommendations. The source report also verifies historical prefixes,
fixed checkpoints and component artifacts. This report cross-checks {checked} Markdown
rows against the underlying records and freezes the input and figure hashes in
`provenance.json`. Numeric plot data are exported as CSV, Plotly specifications as
JSON, and print fallbacks as SVG.
"""
    (REPORT / "provenance.qmd").write_text(provenance)
    outputs = {
        str(p.relative_to(REPORT)): digest(p) for p in (REPORT / "figures").iterdir() if p.is_file()
    }
    outputs.update(
        {n: digest(REPORT / n) for n in ["figures.qmd", "summary.qmd", "provenance.qmd"]}
    )
    report_sources = {
        name: digest(REPORT / name)
        for name in [
            "report.qmd",
            "references.bib",
            "pixi.toml",
            "pixi.lock",
            "assets/head.html",
            "assets/interactive.html",
            "scripts/build_report.py",
            "scripts/verify_report.py",
            "scripts/test_report.py",
        ]
    }
    result = dict(
        inputs=INPUTS,
        report_sources=report_sources,
        outputs=outputs,
        build_script_sha256=digest(Path(__file__)),
        fixed_studies=len(fixed),
        target_studies=len(target),
        retained_target_calls=sum(r["evaluations"] for r in target),
        target_hits=hits,
        capped=len(target) - hits,
        markdown_rows_verified=checked,
        figure_count=len(FIGURES),
        plotly_version=__import__("plotly").__version__,
        matplotlib_version=matplotlib.__version__,
    )
    (REPORT / "provenance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {len(FIGURES)} interactive figures with CSV, JSON and SVG artifacts", flush=True)


if __name__ == "__main__":
    main()
