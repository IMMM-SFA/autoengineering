"""Render saved four-family diagnostics, preserving all route rows in CSV exports."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLORS = ("#8C5E3C", "#3B6B57", "#496D8C", "#92704D", "#685E80", "#60877F", "#8B4F50")
ROUTES = (
    "baseline",
    "conventional",
    "single_agent",
    "multi_agent",
    "no_investigator",
    "no_implementer",
    "no_reviewer",
)


def groups(frame, columns, order):
    """Collapse exact plotted duplicates only; keep their route membership explicit."""
    result = {}
    for route in ROUTES:
        table = frame[frame.route == route].sort_values(order)
        assert len(table)
        key = hashlib.sha256(table[columns].to_numpy(dtype=float).tobytes()).hexdigest()
        if key not in result:
            result[key] = {"table": table, "routes": []}
        result[key]["routes"].append(route)
    return list(result.values())


def label(routes):
    if routes == ["baseline"]:
        return "Baseline"
    if set(routes) == set(ROUTES[1:]):
        return "Six selection routes"
    if set(routes) == set(ROUTES):
        return "All seven routes"
    return ", ".join(r.replace("_", " ") for r in routes)


def segmented(dates, values):
    # Gaps in scored support remain gaps. No nighttime or missing data are imputed.
    x = pd.to_datetime(dates, utc=True)
    t = x.astype("int64").to_numpy()
    step = np.median(np.diff(t))
    xx, yy = [], []
    for i, (date, value) in enumerate(zip(x, values)):
        if i and t[i] - t[i - 1] > step * 1.5:
            xx.append(date)
            yy.append(np.nan)
        xx.append(date)
        yy.append(value)
    return xx, yy


def run(root: Path, width: float):
    summary = json.loads((root / "summary.json").read_text())
    for name, expected in summary["tables"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected
    predictions = pd.read_csv(root / "predictions.csv")
    scenarios = pd.read_csv(root / "scenarios.csv")
    checks = pd.read_csv(root / "checks.csv")
    layouts = pd.read_csv(root / "layouts.csv")
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelcolor": "#303030",
            "text.color": "#303030",
            "svg.fonttype": "none",
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )
    membership = {}
    fig, axes = plt.subplots(2, 2, figsize=(width, width * 0.68), layout="constrained")
    for row, (task, title) in enumerate((("leaf", "Leaf River"), ("solar", "Measured-POA solar"))):
        frame = predictions[predictions.task == task]
        grouped = groups(frame, ["observed", "prediction"], "date")
        membership[task] = [g["routes"] for g in grouped]
        base = grouped[0]["table"]
        units = base.units.iloc[0]
        axis, residual = axes[row]
        axis.plot(
            *segmented(base.date, base.observed),
            color="#303030",
            lw=1.2,
            label="Observed",
            zorder=4,
        )
        for i, group in enumerate(grouped):
            table = group["table"]
            name = label(group["routes"])
            axis.plot(
                *segmented(table.date, table.prediction), color=COLORS[i], lw=1.25, label=name
            )
            residual.scatter(
                pd.to_datetime(table.date, utc=True),
                table.residual,
                s=7,
                color=COLORS[i],
                alpha=0.65,
                label=name,
                rasterized=True,
            )
        residual.axhline(0, color="#777777", lw=0.7, ls="--")
        axis.set(
            title=f"{'a' if row == 0 else 'c'}. {title}: comparison support",
            ylabel=f"Prediction ({units})",
        )
        residual.set(
            title=f"{'b' if row == 0 else 'd'}. Prediction minus observation",
            ylabel=f"Residual ({units})",
        )
        for ax in (axis, residual):
            if task == "solar":
                ax.xaxis.set_major_locator(mdates.DayLocator())
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d", tz=timezone.utc))
            else:
                locator = mdates.AutoDateLocator(minticks=3, maxticks=5)
                ax.xaxis.set_major_locator(locator)
                ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
            ax.set_xlabel("Date (UTC)" if task == "solar" else "Date")
            ax.grid(axis="y", color="#dedbd5", lw=0.5)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncols=3, frameon=False, fontsize=8)
    fig.suptitle("Saved prediction diagnostics | exposed development only", fontsize=11)
    suffix = "" if width == 11 else "-narrow"
    for extension in ("png", "svg"):
        fig.savefig(root / f"prediction-diagnostics{suffix}.{extension}", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(width, width * 0.66), layout="constrained")
    circuit = scenarios[scenarios.task == "circuit"].copy()
    circuit["ground_V"] = circuit.forcing.map(lambda s: json.loads(s)["ground_voltage"])
    voltage = checks[(checks.task == "circuit") & (checks.check == "node_voltage")].copy()
    scenario_ground = circuit.set_index("scenario").ground_V.to_dict()
    voltage["ground_V"] = voltage.scenario.map(scenario_ground)
    for axis, frame, title, ylabel in (
        (axes[0, 0], circuit, "a. Circuit source power", "Source power (W)"),
        (axes[0, 1], voltage, "b. Circuit voltage requirement", "Node 2 voltage (V)"),
    ):
        grouped = groups(frame, ["ground_V", "value"], "ground_V")
        for i, group in enumerate(grouped):
            table = group["table"]
            axis.plot(
                table.ground_V,
                table.value,
                marker="o",
                ms=4,
                lw=1.2,
                color=COLORS[i],
                label=label(group["routes"]),
            )
        axis.set(title=title, xlabel="Ground potential (V)", ylabel=ylabel)
        axis.legend(frameon=False, fontsize=8)
        axis.grid(axis="y", color="#dedbd5", lw=0.5)
    assert voltage.threshold.nunique() == 1
    lower = float(voltage.threshold.iloc[0])
    axes[0, 1].axhline(
        lower, color="#777777", lw=0.8, ls="--", label=f"Required minimum: {lower:g} V"
    )
    axes[0, 1].legend(frameon=False, fontsize=8, loc="upper left")
    axes[0, 0].set_ylim(bottom=0)
    layout_groups = groups(layouts, ["turbine", "x_m", "y_m"], "turbine")
    membership["wind_layout"] = [g["routes"] for g in layout_groups]
    x0, y0 = layouts.x_m.min(), layouts.y_m.min()
    axis = axes[1, 0]
    for i, group in enumerate(layout_groups):
        table = group["table"]
        axis.scatter(
            table.x_m - x0, table.y_m - y0, color=COLORS[i], s=40, label=label(group["routes"])
        )
        for r in table.itertuples():
            axis.annotate(
                str(r.turbine),
                (r.x_m - x0, r.y_m - y0),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8,
            )
    axis.set(
        title="c. Saved four-turbine wind layout",
        xlabel=f"East offset from {x0:.0f} m (m)",
        ylabel=f"North offset from {y0:.0f} m (m)",
    )
    axis.set_aspect("equal", adjustable="datalim")
    axis.margins(0.16)
    axis.legend(frameon=False, fontsize=8)
    spacing = (
        checks[(checks.task == "wind") & (checks.check == "wind_spacing")]
        .set_index("route")
        .loc[list(ROUTES)]
    )
    axis = axes[1, 1]
    axis.scatter(np.arange(7), spacing.value, color=COLORS[1], s=30)
    assert spacing.threshold.nunique() == 1
    minimum = float(spacing.threshold.iloc[0])
    axis.axhline(minimum, color="#777777", ls="--", lw=0.8, label=f"Required: {minimum:g} m")
    axis.set_xticks(
        np.arange(7),
        ["Base", "Conv", "Single", "Multi", "No inv.", "No impl.", "No rev."],
        rotation=30,
        ha="right",
    )
    axis.set(
        title="d. Spacing in the bundled wind case",
        ylabel="Minimum turbine spacing (m)",
        ylim=(0, spacing.value.max() * 1.18),
    )
    axis.legend(frameon=False, fontsize=8)
    axis.grid(axis="y", color="#dedbd5", lw=0.5)
    fig.suptitle("Saved engineering diagnostics | modeled scenarios only", fontsize=11)
    for extension in ("png", "svg"):
        fig.savefig(root / f"engineering-diagnostics{suffix}.{extension}", dpi=170)
    plt.close(fig)
    if not suffix:
        caption = (
            "# Exposed development diagnostics\n\n"
            f"Prediction panels show {len(predictions[predictions.task == 'leaf']) // 7} scored Leaf River dates and "
            f"{len(predictions[predictions.task == 'solar']) // 7} scored solar timestamps for all seven routes. "
            "Only comparison support is shown. Gaps remain gaps. Residuals are prediction minus observation. "
            "Exact overlapping curves are grouped as baseline and six selection routes. "
            "The six routes are conventional, single agent, multi agent and the three role removals.\n\n"
            "Engineering panels preserve three circuit ground-potential scenarios and the single bundled wind distribution. "
            "All selected circuit designs satisfy the recorded voltage requirement. All seven wind routes have the same saved layout. "
            "Spacing is shown separately from energy and prediction errors. The direction discretization is not new weather. "
            "These are one exposed scripted repetition, with no independent confirmation or evidence of a general utility or role benefit.\n\n"
            "CSV files retain every route, scenario and check, including finite checks with no numeric value. "
            "summary.json binds source artifacts and tables. rendering.json binds rendered files and exact plotted overlap groups.\n"
        )
        (root / "README.md").write_text(caption)
        result = {
            "rendered_at_utc": datetime.now(timezone.utc).isoformat(),
            "width_inches": width,
            "plot_groups": membership,
            "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "files": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.iterdir()
                if p.suffix in (".png", ".svg", ".csv")
            },
            "scope": summary["scope"],
        }
        (root / "rendering.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"width_inches": width, "groups": membership}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--width", type=float, default=11)
    args = parser.parse_args()
    run(args.root, args.width)
