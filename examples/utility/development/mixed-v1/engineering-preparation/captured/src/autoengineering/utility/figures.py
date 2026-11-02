"""Optional Matplotlib figures and offline reconstruction of their numeric data.

Rendering never opens private arrays or invokes a model. Base readers verify the
numeric source and image integrity separately; pixel rerendering is optional.
"""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import textwrap

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.serialization import canonical_json, unique_json, digest
from autoengineering.campaign.store import StoreError, durable_write
from .analysis import DependentAnalysisPlan, read_analysis_plan, uncertainty_split
from .reporting import comparative_report, report_files


def figure_data(document, plan):
    if plan.digest != document["analysis"]["analysis_digest"]:
        raise ValueError("figure policy differs from report analysis")
    contrasts = []
    family = len(plan.contrasts)*len({row["regime"] for row in document["analysis"]["contrasts"]})
    for row in document["analysis"]["contrasts"]:
        policy = next(c for c in plan.contrasts if (c.task_id, c.route_id, c.comparator_id) == (
            row["task_id"], row["route_id"], row["comparator_id"]))
        contrasts.append({name: row[name] for name in ("task_id", "regime", "route_id", "comparator_id",
            "outcome", "units", "assigned_pairs", "valid_pairs", "pairs", "mean_gain", "interval",
            "verdict", "dependence_complete", "dependence_evidence", "scientific_claim_scope")}
            | {"minimum_gain": policy.minimum_gain, "interval_method": policy.interval,
               "repetition_confidence": 1-(1-policy.confidence)/(family*(
                   uncertainty_split(plan) if isinstance(plan, DependentAnalysisPlan) else 1))})
    groups = {}
    for row in document["cells"]:
        key = (row["task_id"], row["regime"])
        routes = groups.setdefault(key, {})
        counts = routes.setdefault(row["route_id"], {})
        status = row["confirmation_status"]
        if status == "success":
            status = "successful_feasible" if row["feasible"] is True else "infeasible_score"
        counts[status] = counts.get(status, 0)+1
    return {"schema": "utility-figure-data-v1", "suite_digest": document["suite_digest"],
            "source_head": document["source_head"], "report_spec_digest": document["report_spec_digest"],
            "contrasts": contrasts, "dependence_policy": document["analysis"].get("dependence_policy"),
            "reliability": [{"task_id": task, "regime": regime, "routes": routes}
                            for (task, regime), routes in sorted(groups.items())],
            "total_cost_comparison": {"status": "blocked", "reason": "complete total cost evidence unavailable"},
            "claim_limits": document["claim_limits"]}


def _data(store, request):
    document = comparative_report(store, request)
    raw = read_bytes(store.root, request.analysis).decode()
    return document, figure_data(document, read_analysis_plan(raw))


def _profile(width):
    if type(width) not in (int, float) or not 4.5 <= width <= 12:
        raise ValueError("figure width must be between 4.5 and 12 inches")
    try:
        import matplotlib
        from matplotlib import ft2font
    except ImportError:
        raise ValueError("figure rendering requires optional Matplotlib") from None
    return {"schema": "utility-matplotlib-v1", "width_inches": float(width), "dpi": 160,
            "matplotlib": matplotlib.__version__, "freetype": ft2font.__freetype_version__,
            "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def render(data, *, width=8.):
    """Return standard vector/raster figures, using no interactive backend."""
    profile = _profile(width)
    import matplotlib as mpl
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.ticker import MaxNLocator

    files = {}
    wrap = max(28, int(width*9))
    style = {"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
             "axes.spines.right": False, "svg.hashsalt": "utility-figures-v1",
             "svg.fonttype": "none", "figure.facecolor": "white", "axes.facecolor": "white"}

    def save(fig, name):
        FigureCanvasAgg(fig)
        fig.canvas.draw()
        for extension in ("svg", "png"):
            buffer = io.BytesIO()
            metadata = {"Date": None} if extension == "svg" else {"Software": "autoengineering utility figures"}
            fig.savefig(buffer, format=extension, dpi=profile["dpi"], bbox_inches="tight", metadata=metadata)
            files[f"{name}.{extension}"] = buffer.getvalue()
        fig.clear()

    def label(ax, title, note):
        ax.set_title(textwrap.fill(title, wrap), loc="left", pad=15)
        ax.text(0, -0.40, textwrap.fill(note, wrap), transform=ax.transAxes,
                fontsize=9, va="top", color="#4b4b47")

    with mpl.rc_context():
        mpl.rcdefaults()
        mpl.rcParams.update(style)
        for index, row in enumerate(data["contrasts"], 1):
            fig = Figure(figsize=(width, 3.3), layout="constrained")
            ax = fig.subplots()
            gains = [pair["gain"] for pair in row["pairs"]]
            if gains:
                ax.scatter(gains, [0.08*((i % 5)-2) for i in range(len(gains))],
                           color="#476b55", alpha=.7, s=28)
                ax.plot([row["mean_gain"]], [1], marker="o", color="#9c613b", markersize=6)
                if row["interval"]:
                    ax.plot(row["interval"], [1, 1], color="#9c613b", linewidth=2)
                ax.set_yticks([0, 1], ["Paired gains", "Repetition mean"])
            else:
                ax.text(.5, .5, "No valid paired outcomes", transform=ax.transAxes, ha="center")
                ax.set_yticks([])
            ax.axvline(0, color="#6a6a63", linewidth=.8)
            ax.axvline(row["minimum_gain"], color="#9c613b", linestyle=":", linewidth=1)
            ax.set_ylim(-.5, 1.5)
            ax.set_xlabel(textwrap.fill(f"Gain in {row['outcome']} ({row['units']}); positive favors {row['route_id']}", wrap))
            note = (f"{row['valid_pairs']} of {row['assigned_pairs']} assigned pairs. "
                    f"{100*row['repetition_confidence']:.3g}% {row['interval_method'].replace('_', ' ')} interval. "
                    f"Dotted line: minimum useful gain. Verdict: {row['verdict']}. "
                    "Observation/scenario uncertainty is separate.")
            label(ax, f"{row['task_id']}: {row['route_id']} versus {row['comparator_id']} ({row['regime']})", note)
            save(fig, f"paired-effects-{index:03d}")
            if any(item is not None for item in row["dependence_evidence"]):
                items = row["dependence_evidence"]
                fig = Figure(figsize=(width, min(12., 3.+.2*len(items))), layout="constrained")
                ax = fig.subplots()
                for pair_index, item in enumerate(items):
                    if item is None or item["gain"] is None:
                        ax.text(.03, pair_index, "Unavailable", transform=ax.get_yaxis_transform(), fontsize=8)
                        continue
                    ax.plot([item["gain"]], [pair_index], "o", color="#476b55", markersize=4)
                    if item["interval"] is not None:
                        ax.plot(item["interval"], [pair_index, pair_index], color="#476b55", linewidth=1.5)
                    if item["status"] == "insufficient_data":
                        ax.text(.98, pair_index, "Insufficient data", ha="right", fontsize=8,
                                transform=ax.get_yaxis_transform())
                ax.axvline(0, color="#6a6a63", linewidth=.8)
                ax.axvline(row["minimum_gain"], color="#9c613b", linestyle=":", linewidth=1)
                ax.set_ylim(len(items)-.5, -.5)
                ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
                ax.set_ylabel("Valid pair index (zero based)")
                ax.set_xlabel(f"Gain in {row['outcome']} ({row['units']})")
                policies = data["dependence_policy"]
                policy_digest = next(item["policy_digest"] for item in items if item is not None)
                policy = next(policy for policy in (*policies["tasks"], *policies["scenarios"])
                              if digest(policy) == policy_digest)
                interval_label = ("Fixed scenario census." if policy["method"] == "fixed_scenario_census" else
                                  f"{100*policy['confidence']:.3g}% {policy['method'].replace('_', ' ')} intervals.")
                label(ax, f"{row['task_id']}: observation/scenario uncertainty",
                    interval_label+" Frozen task policy is recorded in figure-data.json. "
                    "Fixed scenario censuses have points only and no population interval. "
                    "These intervals do not describe algorithm repetition variation.")
                save(fig, f"dependence-{index:03d}")
        statuses = sorted({status for group in data["reliability"] for counts in group["routes"].values() for status in counts})
        colors = ["#476b55", "#b17c46", "#6c8190", "#9e6d71", "#a79c70", "#77718b", "#9a9388"]
        palette = {status: ("#476b55" if status == "successful_feasible" else colors[(i+1) % len(colors)])
                   for i, status in enumerate(statuses)}
        for index, group in enumerate(data["reliability"], 1):
            routes = list(group["routes"])
            fig = Figure(figsize=(width, 3.3+.35*len(routes)+.2*len(statuses)), layout="constrained")
            ax = fig.subplots()
            left = [0]*len(routes)
            for i, status in enumerate(statuses):
                counts = [group["routes"][route].get(status, 0) for route in routes]
                if not any(counts):
                    continue
                ax.barh(range(len(routes)), counts, left=left, color=palette[status],
                        hatch=("", "/", "\\", ".")[i % 4], label=status.replace("_", " "))
                left = [a+b for a, b in zip(left, counts)]
            ax.set_yticks(range(len(routes)), [textwrap.fill(route, 20) for route in routes])
            ax.invert_yaxis()
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_xlabel("Assigned cells (count)")
            ax.legend(loc="upper left", bbox_to_anchor=(0, -.25), ncols=1 if width < 6 else 2,
                      frameon=False, fontsize=9)
            ax.set_title(textwrap.fill(f"{group['task_id']}: confirmation evidence ({group['regime']})", wrap), loc="left", pad=15)
            save(fig, f"assigned-outcomes-{index:03d}")
    return profile, files


def export_figures(store, request, destination, *, width=8.):
    document, data = _data(store, request)
    profile, images = render(data, width=width)
    files = report_files(document) | {"figure-data.json": (canonical_json(data)+"\n").encode()} | images
    root = Path(destination).absolute()
    if root.exists() or any(part.is_symlink() for part in (root, *root.parents)):
        raise StoreError("figure export requires an absent path without symlinks")
    root.mkdir(mode=0o700, parents=True)
    manifest = {"schema": "utility-figure-export-v1", "suite_digest": store.spec.digest,
                "source_head": document["source_head"], "report_spec_digest": request.digest,
                "rendering_profile": profile,
                "files": {name: {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
                          for name, raw in sorted(files.items())}}
    for name, raw in files.items():
        durable_write(root / name, raw)
    durable_write(root / "manifest.json", (canonical_json(manifest)+"\n").encode())
    return manifest


def verify_figures(store, request, destination, *, rerender=False):
    root = Path(destination).absolute()
    manifest = unique_json(confined_file(root, "manifest.json").read_text())
    document, data = _data(store, request)
    base = report_files(document) | {"figure-data.json": (canonical_json(data)+"\n").encode()}
    image_names = {f"{prefix}-{i:03d}.{extension}" for prefix, count in (
        ("paired-effects", len(data["contrasts"])), ("assigned-outcomes", len(data["reliability"])))
        for i in range(1, count+1) for extension in ("svg", "png")}
    image_names |= {f"dependence-{i:03d}.{extension}" for i, row in enumerate(data["contrasts"], 1)
                    if any(item is not None for item in row["dependence_evidence"])
                    for extension in ("svg", "png")}
    if not isinstance(manifest, dict) or not isinstance(manifest.get("rendering_profile"), dict):
        raise StoreError("invalid figure export manifest")
    profile = manifest["rendering_profile"]
    expected_keys = {"schema", "suite_digest", "source_head", "report_spec_digest", "rendering_profile", "files"}
    if (set(manifest) != expected_keys or manifest["schema"] != "utility-figure-export-v1"
            or manifest["suite_digest"] != store.spec.digest or manifest["source_head"] != document["source_head"]
            or manifest["report_spec_digest"] != request.digest
            or set(profile) != {"schema", "width_inches", "dpi", "matplotlib", "freetype", "renderer_sha256"}
            or profile["schema"] != "utility-matplotlib-v1" or profile["dpi"] != 160
            or type(profile["width_inches"]) not in (float, int) or not 4.5 <= profile["width_inches"] <= 12
            or not isinstance(profile["matplotlib"], str) or not isinstance(profile["freetype"], str)
            or profile["renderer_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            or set(manifest["files"]) != {*base, *image_names}
            or {p.name for p in root.iterdir()} != {*base, *image_names, "manifest.json"}):
        raise StoreError("figure export differs from frozen reconstruction")
    if rerender:
        current, images = render(data, width=profile["width_inches"])
        if current != profile:
            raise StoreError("rendering environment differs from saved figure profile")
        base |= images
    for name, metadata in manifest["files"].items():
        raw = confined_file(root, name).read_bytes()
        if metadata != {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}:
            raise StoreError("figure export integrity mismatch")
        if name in base and raw != base[name]:
            raise StoreError("figure data or pixels differ from authoritative reconstruction")
    return {"status": "verified_numeric_reconstruction", "suite_digest": store.spec.digest,
            "figure_data": "reconstructed", "image_integrity": "internally_consistent",
            "image_rendering": "reconstructed" if rerender else "not_repeated", "files": len(manifest["files"])}
