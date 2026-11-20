#!/usr/bin/env python3
"""Compile and verify the two AGU poster TikZ flowcharts (Figures 1 & 2) to SVG and 300-DPI PNG."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = Path("/Users/cam/.gemini/config/skills/diagrams")
STY_PATH = SKILLS_DIR / "resources" / "flowchart-tikz.sty"
sys.path.insert(0, str(SKILLS_DIR / "scripts"))

from check_tikz_svg import check_tikz_svg_overlaps, compile_tikz_to_svg  # noqa: E402

POSTER_DIR = REPO_ROOT / "reports" / "agu-poster-im3-assessment-2026-11-20"
FIG_DIR = POSTER_DIR / "figures"

# ---------------------------------------------------------------------------
# Figure 1: High-Level Autoengineering Assessment Workflow Flowchart
# ---------------------------------------------------------------------------
TIKZ_FIG1 = r"""
% caption: Autoengineering four-stage assessment workflow for coupled Earth-system model chains.
\begin{tikzpicture}[
  node distance=1.4cm and 1.8cm,
  card/.style={text width=4.65cm, minimum height=1.78cm, align=center}
]
  % Stage I: Declarative Sub-Component Graph & Telemetry
  \node[iobox, card] (s1_mid) {\textbf{1b. Sub-Component DAG}\\(\code{system.yaml}: typed ports,\\internal modules, couplings)};
  \node[storebox, card, left=1.1cm of s1_mid] (s1_left) {\textbf{1a. Benchmark \& Telemetry}\\(1,190 USGS gauges, NERSC\\node-hrs, physical bounds)};
  \node[iobox, card, right=1.1cm of s1_mid] (s1_right) {\textbf{1c. Candidate Process Pool}\\(\code{candidates.yaml}: process\\parameterizations \& surrogates)};
  \coordinate (g1_pad) at ([yshift=0.38cm]s1_left.north);

  \draw[flow] (s1_left.east) -- (s1_mid.west);
  \draw[flow] (s1_right.west) -- (s1_mid.east);

  \begin{scope}[on background layer]
    \node[group, fit=(s1_left)(s1_mid)(s1_right)(g1_pad), inner sep=11pt] (G1) {};
  \end{scope}
  \node[grouptitle] at (G1.north west) {I. Declarative Sub-Component Decomposition \& Telemetry Ingestion};

  % Stage II: Coupled Triage & Sensitivity Engine
  \node[rulebox, card, below=1.95cm of s1_mid] (s2_mid) {\textbf{2b. Decoupling Matrix}\\(Compute share $C_i/C_{\text{tot}}$ vs.\\sensitivity $S_i$; break-even $N_i^*$)};
  \node[procbox, card, left=1.1cm of s2_mid] (s2_left) {\textbf{2a. Port Perturbation Probe}\\($\pm 10\%$ flux perturbation\\across topological order)};
  \node[condbox, card, right=1.1cm of s2_mid] (s2_right) {\textbf{2c. Prioritization Triage}\\(\code{fix\_physics} vs. \code{sub\_emulate}\\vs. \code{deprioritize})};
  \coordinate (g2_pad) at ([yshift=0.38cm]s2_left.north);

  \draw[flow] (s2_left.east) -- (s2_mid.west);
  \draw[flow] (s2_mid.east) -- (s2_right.west);

  \begin{scope}[on background layer]
    \node[group, fit=(s2_left)(s2_mid)(s2_right)(g2_pad), inner sep=11pt] (G2) {};
  \end{scope}
  \node[grouptitle] at (G2.north west) {II. Coupled Bottleneck Triage \& Sensitivity Assessment (\code{autoengineering triage})};

  % Stage III: Physics-Guarded Sub-Component Probe & Attribution Loop
  \node[condbox, card, below=1.95cm of s2_mid] (s3_mid) {\textbf{3b. Hard Physical Guardrails}\\(\code{PhysicalCheck}: $Q_{\text{DRAI}} \ge 0$,\\$|Q_{10}\text{ PBIAS}| \le 25\%$, mass balance)};
  \node[stagebox, card, left=1.1cm of s3_mid] (s3_left) {\textbf{3a. Sub-Component Swap}\\(Trial DAG execution across\\process \& surrogate variants)};
  \node[rulebox, card, right=1.1cm of s3_mid] (s3_right) {\textbf{3c. Attribution Disposition}\\(\textbf{KEPT $\checkmark$} / \textbf{REVERTED $\times$}\\or \textbf{VETOED $\oslash$} + provenance)};
  \coordinate (g3_pad) at ([yshift=0.38cm]s3_left.north);

  \draw[flow] (s3_left.east) -- (s3_mid.west);
  \draw[flow] (s3_mid.east) -- (s3_right.west);

  \begin{scope}[on background layer]
    \node[group, fit=(s3_left)(s3_mid)(s3_right)(g3_pad), inner sep=11pt] (G3) {};
  \end{scope}
  \node[grouptitle] at (G3.north west) {III. Physics-Guarded Sub-Component Attribution Loop (\code{autoengineering improve})};

  % Stage IV: Multi-Dimensional Stakeholder Assessment Report
  \node[juncbox, card, below=1.95cm of s3_mid] (s4_mid) {\textbf{4b. For Project PIs}\\(Cross-model error attribution,\\UQ ensemble capacity $N_{\text{UQ}}$)};
  \node[juncbox, card, left=1.1cm of s4_mid] (s4_left) {\textbf{4a. For Domain Modelers}\\(Process parameterization fixes,\\physical vetoes \& defect audit)};
  \node[juncbox, card, right=1.1cm of s4_mid] (s4_right) {\textbf{4c. For Program Managers}\\(HPC node-hr ROI, Pareto knee,\\where \emph{not} to invest effort)};
  \coordinate (g4_pad) at ([yshift=0.38cm]s4_left.north);

  \draw[flow] (s4_left.east) -- (s4_mid.west);
  \draw[flow] (s4_right.west) -- (s4_mid.east);

  \begin{scope}[on background layer]
    \node[group, fit=(s4_left)(s4_mid)(s4_right)(g4_pad), inner sep=11pt] (G4) {};
  \end{scope}
  \node[grouptitle] at (G4.north west) {IV. Multi-Dimensional Stakeholder Assessment Deliverable (Portable Report Bundle)};

  % Vertical group-to-group connectors anchored to center column X
  \draw[flow] (s1_mid.center |- G1.south) -- (s2_mid.center |- G2.north);
  \draw[flow] (s2_mid.center |- G2.south) -- (s3_mid.center |- G3.north);
  \draw[flow] (s3_mid.center |- G3.south) -- (s4_mid.center |- G4.north);
\end{tikzpicture}
"""

# ---------------------------------------------------------------------------
# Figure 2: DOE IM3 Water-Scarcity 9-Subcomponent Application Flowchart
# ---------------------------------------------------------------------------
TIKZ_FIG2 = r"""
% caption: Sub-component assessment architecture for the DOE IM3 CONUS water-scarcity modeling chain.
\begin{tikzpicture}[
  node distance=1.35cm and 1.6cm,
  mcard/.style={text width=4.68cm, minimum height=2.12cm, align=center}
]
  % Row 1: CLM5 / ELMv3 Land Surface Hydrology (240.0h = 98.6% HPC)
  \node[stagebox, mcard] (lsm2) {\textbf{2. Surface Infiltration}\\(\code{52.0h = 21.4\% HPC}, $S=2.63$)\\Uncalibrated ELMv3 \textbf{VETOED $\oslash$}\\($Q_{10}=+40\%$); \code{fover} \textbf{KEPT $\checkmark$}};
  \node[stagebox, mcard, left=1.05cm of lsm2] (lsm1) {\textbf{1. Canopy / Snow / ET}\\(\code{68.0h = 28.0\% HPC}, $S=6.70$)\\CLM5-SP \textbf{REVERTED $\times$};\\ELMv3 Demeter \textbf{KEPT $\checkmark$}};
  \node[rulebox, mcard, right=1.05cm of lsm2] (lsm3) {\textbf{3. Subsurface Vadose}\\(\code{120.0h = 49.3\% HPC}, $S=4.24$)\\Fixes 124 neg $Q_{\text{DRAI}}$ (\code{I-25}) \textbf{KEPT $\checkmark$};\\\textbf{\#1 Sub-Emulator Target} ($N^*=1$)};
  \coordinate (glsm_pad) at ([yshift=0.38cm]lsm1.north);

  \draw[flow] (lsm1.east) -- (lsm2.west);
  \draw[flow] (lsm2.east) -- (lsm3.west);

  \begin{scope}[on background layer]
    \node[group, fit=(lsm1)(lsm2)(lsm3)(glsm_pad), inner sep=11pt] (GLSM) {};
  \end{scope}
  \node[grouptitle] at (GLSM.north west) {Macro-Model 1: CLM5 / ELMv3 Land Surface Hydrology (240.0 NERSC Node-Hrs/Run = 98.6\% of Compute)};

  % Row 2: Tethys Sectoral Water-Demand Downscaling (0.8h = 0.3% HPC)
  \node[procbox, mcard, below=1.95cm of lsm2] (tet2) {\textbf{5. Thermoelectric \& Ind.}\\(\code{0.20h = 0.08\% HPC}, $S=37.80$)\\0-LMP CERF cooling return\\ratios (\code{I-08/I-09}) \textbf{KEPT $\checkmark$}};
  \node[procbox, mcard, left=1.05cm of tet2] (tet1) {\textbf{4. Irrigation Downscaler}\\(\code{0.45h = 0.18\% HPC}, $S=22.36$)\\0.829937 canal efficiency (\code{I-07})\\\& USGS Method 2 \textbf{KEPT $\checkmark$}};
  \node[condbox, mcard, right=1.05cm of tet2] (tet3) {\textbf{6. Municipal / Domestic}\\(\code{0.15h = 0.06\% HPC}, $S=31.25$)\\$<3\%$ of basin flow ($\Delta\text{KGE}=0$);\\\textbf{REVERTED $\times$ (Low-ROI Warning)}};
  \coordinate (gtet_pad) at ([yshift=0.38cm]tet1.north);

  \draw[flow] (tet1.east) -- (tet2.west);
  \draw[flow] (tet2.east) -- (tet3.west);

  \begin{scope}[on background layer]
    \node[group, fit=(tet1)(tet2)(tet3)(gtet_pad), inner sep=11pt] (GTET) {};
  \end{scope}
  \node[grouptitle] at (GTET.north west) {Macro-Model 2: Tethys Spatiotemporal Sectoral Demand Downscaling (0.8 Node-Hrs/Run = 0.3\% of Compute)};

  % Row 3: mosartwmpy River Routing & Water Management (2.5h = 1.0% HPC)
  \node[procbox, mcard, below=1.95cm of tet2] (mos2) {\textbf{8. Channel Network Routing}\\(\code{0.90h = 0.37\% HPC}, $S=6.69$)\\Sub-grid area filter (\code{\#129}, $\le 4$c):\\\textbf{$+2,600\%$ Small-Basin KGE $\checkmark$}};
  \node[procbox, mcard, left=1.05cm of mos2] (mos1) {\textbf{7. Hillslope \& Tributary}\\(\code{0.70h = 0.29\% HPC}, $S=6.70$)\\Repairs 1,690 \code{hslp/rslp=NaN}\\land cells (\code{I-23}) \textbf{KEPT $\checkmark$}};
  \node[rulebox, mcard, right=1.05cm of mos2] (mos3) {\textbf{9. Reservoir \& Demand WM}\\(\code{0.90h = 0.37\% HPC}, \textbf{$S=73.89$})\\Broman \code{9505v4} + $\text{release\_min}\ge 0$\\+ return flows: \textbf{$+202\%$ Reg KGE $\checkmark$}};
  \coordinate (gmos_pad) at ([yshift=0.38cm]mos1.north);

  \draw[flow] (mos1.east) -- (mos2.west);
  \draw[flow] (mos2.east) -- (mos3.west);

  \begin{scope}[on background layer]
    \node[group, fit=(mos1)(mos2)(mos3)(gmos_pad), inner sep=11pt] (GMOS) {};
  \end{scope}
  \node[grouptitle] at (GMOS.north west) {Macro-Model 3: mosartwmpy River Routing \& Water Management (2.5 Node-Hrs/Run = 1.0\% of Compute)};

  % Row 4: Multi-Dimensional Assessment Outcomes Across 1,190 CONUS Gauges
  \node[juncbox, mcard, below=1.95cm of mos2] (out2) {\textbf{Process Fidelity \& Deficit}\\CONUS KGE: \textbf{0.847 $\rightarrow$ 0.909}\\Unmet Demand: \textbf{$-86.2\%$} (5.97 $\text{km}^3$/yr)};
  \node[juncbox, mcard, left=1.05cm of out2] (out1) {\textbf{Regime Bottlenecks Solved}\\Small-Basin ($\le 4$c): \textbf{0.013 $\rightarrow$ 0.337}\\Regulated Dams: \textbf{0.168 $\rightarrow$ 0.507}};
  \node[juncbox, mcard, right=1.05cm of out2] (out3) {\textbf{HPC \& UQ Capacity ROI}\\Vadose Sub-Emu: \textbf{$-54.2\%$ HPC} ($2.2\times$ UQ)\\Whole-LSM (Last Resort): \textbf{$-98.5\%$ HPC}};
  \coordinate (gout_pad) at ([yshift=0.38cm]out1.north);

  \draw[flow] (out1.east) -- (out2.west);
  \draw[flow] (out3.west) -- (out2.east);

  \begin{scope}[on background layer]
    \node[group, fit=(out1)(out2)(out3)(gout_pad), inner sep=11pt] (GOUT) {};
  \end{scope}
  \node[grouptitle] at (GOUT.north west) {Assessment Summary Across 1,190 USGS 70/70 CONUS Gauges (1981--2015, 672 Natural + 518 Regulated)};

  % Vertical connectors anchored to center column X
  \draw[flow] (lsm2.center |- GLSM.south) -- (tet2.center |- GTET.north);
  \draw[flow] (tet2.center |- GTET.south) -- (mos2.center |- GMOS.north);
  \draw[flow] (mos2.center |- GMOS.south) -- (out2.center |- GOUT.north);
\end{tikzpicture}
"""


def compile_tikz_pdf_and_png(raw_tikz: str, out_stem: Path) -> None:
    """Compile a TikZ block using print Earth-Tone palette to PDF, SVG, and 300-DPI PNG."""
    _ = compile_tikz_to_svg(raw_tikz, STY_PATH, context_label=out_stem.name)

    lines = [
        line
        for line in raw_tikz.strip().splitlines()
        if not line.strip().lower().startswith("% caption:")
    ]
    body = "\n".join(lines)
    tex_doc = (
        "\\documentclass[tikz,border=10pt]{standalone}\n"
        "\\usepackage{flowchart-tikz}\n"
        "\\definecolor{clusterfill}{HTML}{FFFFFF}\n"
        "\\pagecolor{white}\n"
        "\\begin{document}\n"
        f"{body}\n"
        "\\end{document}\n"
    )
    env = os.environ.copy()
    for extra_bin in ("/opt/homebrew/bin", "/usr/local/bin", "/Library/TeX/texbin"):
        if Path(extra_bin).is_dir() and extra_bin not in env.get("PATH", ""):
            env["PATH"] = extra_bin + ":" + env.get("PATH", "")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        shutil.copyfile(STY_PATH, tmp / STY_PATH.name)
        (tmp / "diagram.tex").write_text(tex_doc, encoding="utf-8")
        subprocess.run(
            ["latex", "-interaction=nonstopmode", "diagram.tex"],
            cwd=tmp,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        subprocess.run(
            ["dvisvgm", "--no-fonts", "--zoom=1.35", "-o", "diagram.svg", "diagram.dvi"],
            cwd=tmp,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        svg_str = (tmp / "diagram.svg").read_text(encoding="utf-8")
        check_tikz_svg_overlaps(svg_str, context_label=f"{out_stem.name} (print SVG)")
        # Ensure standalone SVG has an explicit white background rect for poster printing
        svg_white = svg_str.replace(
            "<g id='page1'>",
            "<g id='page1'>\n<rect x='-10000' y='-10000' width='20000' height='20000' fill='#ffffff'/>",
            1,
        )
        out_stem.with_suffix(".svg").write_text(svg_white, encoding="utf-8")

        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "diagram.tex"],
            cwd=tmp,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        shutil.copyfile(tmp / "diagram.pdf", out_stem.with_suffix(".pdf"))
        subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-r",
                "450",
                "-singlefile",
                str(tmp / "diagram.pdf"),
                str(out_stem),
            ],
            cwd=tmp,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    print(f"Verified and exported 450-DPI white-background {out_stem.name} (.svg, .pdf, .png)")


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    compile_tikz_pdf_and_png(TIKZ_FIG1, FIG_DIR / "fig1_autoengineering_workflow_flowchart")
    compile_tikz_pdf_and_png(TIKZ_FIG2, FIG_DIR / "fig2_im3_subcomponent_chain_flowchart")


if __name__ == "__main__":
    main()
