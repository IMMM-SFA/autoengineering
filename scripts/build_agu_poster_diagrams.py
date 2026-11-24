#!/usr/bin/env python3
"""Compile and verify the two AGU poster TikZ flowcharts (Figures 1 & 2) at 450 DPI on white."""

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
  card/.style={text width=4.68cm, minimum height=1.82cm, align=center}
]
  % Stage I: Map the Coupled Model Chain & Telemetry
  \node[iobox, card] (s1_mid) {\textbf{1b. Sub-Component Graph}\\(\code{system.yaml}: breaks macro-models\\into internal process modules)};
  \node[storebox, card, left=1.1cm of s1_mid] (s1_left) {\textbf{1a. Observations \& Costs}\\(1,190 USGS stream gauges,\\NERSC node-hrs, physical bounds)};
  \node[iobox, card, right=1.1cm of s1_mid] (s1_right) {\textbf{1c. Candidate Process Pool}\\(\code{candidates.yaml}: alternative\\physics, bug fixes \& surrogates)};
  \coordinate (g1_pad) at ([yshift=0.38cm]s1_left.north);

  \draw[flow] (s1_left.east) -- (s1_mid.west);
  \draw[flow] (s1_right.west) -- (s1_mid.east);

  \begin{scope}[on background layer]
    \node[group, fit=(s1_left)(s1_mid)(s1_right)(g1_pad), inner sep=11pt] (G1) {};
  \end{scope}
  \node[grouptitle] at (G1.north west) {Stage I. Map the Coupled Model Chain, Internal Process Modules \& Compute Costs};

  % Stage II: Cost vs. Sensitivity Triage
  \node[rulebox, card, below=1.95cm of s1_mid] (s2_mid) {\textbf{2b. Cost vs. Sensitivity Matrix}\\(Compares \% HPC cost against\\downstream impact \& break-even $N^*$)};
  \node[procbox, card, left=1.1cm of s2_mid] (s2_left) {\textbf{2a. Perturbation Sensitivity}\\(Perturbs each module's output\\by $\pm 10\%$ through the chain)};
  \node[condbox, card, right=1.1cm of s2_mid] (s2_right) {\textbf{2c. Triage Recommendation}\\(\textbf{Fix Process Physics} vs. \textbf{Emulate}\\vs. \textbf{Deprioritize Low-ROI})};
  \coordinate (g2_pad) at ([yshift=0.38cm]s2_left.north);

  \draw[flow] (s2_left.east) -- (s2_mid.west);
  \draw[flow] (s2_mid.east) -- (s2_right.west);

  \begin{scope}[on background layer]
    \node[group, fit=(s2_left)(s2_mid)(s2_right)(g2_pad), inner sep=11pt] (G2) {};
  \end{scope}
  \node[grouptitle] at (G2.north west) {Stage II. Coupled Bottleneck Triage: Where Is Compute Spent vs. Where Do Errors Originate?};

  % Stage III: Physics-Guarded Sub-Component Testing
  \node[condbox, card, below=1.95cm of s2_mid] (s3_mid) {\textbf{3b. Hard Physical Guardrails}\\(Checks mass balance, non-negative\\baseflow $Q_{\text{DRAI}}\ge 0$, drought bias)};
  \node[stagebox, card, left=1.1cm of s3_mid] (s3_left) {\textbf{3a. Sub-Component Trial Swap}\\(Tests one internal process fix\\or targeted surrogate at a time)};
  \node[rulebox, card, right=1.1cm of s3_mid] (s3_right) {\textbf{3c. Transparent Disposition}\\(\textbf{KEPT $\checkmark$} / \textbf{REVERTED $\times$}\\or \textbf{VETOED $\oslash$} if unphysical)};
  \coordinate (g3_pad) at ([yshift=0.38cm]s3_left.north);

  \draw[flow] (s3_left.east) -- (s3_mid.west);
  \draw[flow] (s3_mid.east) -- (s3_right.west);

  \begin{scope}[on background layer]
    \node[group, fit=(s3_left)(s3_mid)(s3_right)(g3_pad), inner sep=11pt] (G3) {};
  \end{scope}
  \node[grouptitle] at (G3.north west) {Stage III. Physics-Guarded Attribution Loop: Test Process Fixes \& Vetoes Unphysical Surrogates};

  % Stage IV: Multi-Dimensional Stakeholder Assessment Report
  \node[juncbox, card, below=1.95cm of s3_mid] (s4_mid) {\textbf{4b. For Project PIs}\\(Cross-model error attribution \&\\UQ ensemble capacity per 10k hrs)};
  \node[juncbox, card, left=1.1cm of s4_mid] (s4_left) {\textbf{4a. For Domain Modelers}\\(Specific parameterization fixes,\\data bugs \& physical veto logs)};
  \node[juncbox, card, right=1.1cm of s4_mid] (s4_right) {\textbf{4c. For Program Managers}\\(HPC node-hr savings, Pareto knee\\\& where \emph{not} to spend effort)};
  \coordinate (g4_pad) at ([yshift=0.38cm]s4_left.north);

  \draw[flow] (s4_left.east) -- (s4_mid.west);
  \draw[flow] (s4_right.west) -- (s4_mid.east);

  \begin{scope}[on background layer]
    \node[group, fit=(s4_left)(s4_mid)(s4_right)(g4_pad), inner sep=11pt] (G4) {};
  \end{scope}
  \node[grouptitle] at (G4.north west) {Stage IV. Actionable Assessment Report for Modelers, Project PIs \& Program Managers};

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
  mcard/.style={text width=4.68cm, minimum height=2.16cm, align=center}
]
  % Row 1: CLM5 / ELMv3 Land Surface Hydrology (240.0h = 98.6% HPC)
  \node[stagebox, mcard] (lsm2) {\textbf{2. Surface Infiltration}\\(\code{52.0h = 21.4\% HPC}, Sens $=2.6$)\\Uncalibrated ELMv3 \textbf{VETOED $\oslash$}\\($+40\%$ drought bias); Calibrated \textbf{KEPT $\checkmark$}};
  \node[stagebox, mcard, left=1.05cm of lsm2] (lsm1) {\textbf{1. Canopy, Snow \& ET}\\(\code{68.0h = 28.0\% HPC}, Sens $=6.7$)\\Satellite phenology \textbf{REVERTED $\times$};\\ELMv3 crop/snow physics \textbf{KEPT $\checkmark$}};
  \node[rulebox, mcard, right=1.05cm of lsm2] (lsm3) {\textbf{3. Deep Soil \& Baseflow}\\(\code{120.0h = 49.3\% HPC}, Sens $=4.2$)\\Fixes negative baseflow \textbf{KEPT $\checkmark$};\\\textbf{\#1 Sub-Emulator Target} ($-54\%$ HPC)};
  \coordinate (glsm_pad) at ([yshift=0.38cm]lsm1.north);

  \draw[flow] (lsm1.east) -- (lsm2.west);
  \draw[flow] (lsm2.east) -- (lsm3.west);

  \begin{scope}[on background layer]
    \node[group, fit=(lsm1)(lsm2)(lsm3)(glsm_pad), inner sep=11pt] (GLSM) {};
  \end{scope}
  \node[grouptitle] at (GLSM.north west) {Model 1: CLM5 / ELMv3 Land Surface Model (240.0 NERSC Node-Hrs/Run = 98.6\% of Compute)};

  % Row 2: Tethys Sectoral Water-Demand Downscaling (0.8h = 0.3% HPC)
  \node[procbox, mcard, below=1.95cm of lsm2] (tet2) {\textbf{5. Power-Plant \& Ind. Water}\\(\code{0.20h = 0.08\% HPC}, Sens $=37.8$)\\Separates once-through cooling\\return water from towers \textbf{KEPT $\checkmark$}};
  \node[procbox, mcard, left=1.05cm of tet2] (tet1) {\textbf{4. Agricultural Irrigation}\\(\code{0.45h = 0.18\% HPC}, Sens $=22.4$)\\Adds $0.83$ canal efficiency \&\\USGS groundwater shares \textbf{KEPT $\checkmark$}};
  \node[condbox, mcard, right=1.05cm of tet2] (tet3) {\textbf{6. Municipal \& Domestic}\\(\code{0.15h = 0.06\% HPC}, Sens $=31.2$)\\$<3\%$ of river flow ($\Delta\text{KGE}=0$);\\\textbf{REVERTED $\times$ (Low-ROI Warning)}};
  \coordinate (gtet_pad) at ([yshift=0.38cm]tet1.north);

  \draw[flow] (tet1.east) -- (tet2.west);
  \draw[flow] (tet2.east) -- (tet3.west);

  \begin{scope}[on background layer]
    \node[group, fit=(tet1)(tet2)(tet3)(gtet_pad), inner sep=11pt] (GTET) {};
  \end{scope}
  \node[grouptitle] at (GTET.north west) {Model 2: Tethys Sectoral Water-Demand Downscaling (0.8 Node-Hrs/Run = 0.3\% of Compute)};

  % Row 3: mosartwmpy River Routing & Water Management (2.5h = 1.0% HPC)
  \node[procbox, mcard, below=1.95cm of tet2] (mos2) {\textbf{8. Main Channel Network}\\(\code{0.90h = 0.37\% HPC}, Sens $=6.7$)\\Fixes $0.125^\circ$ grid area mismatch\\in small basins: \textbf{$+2,600\%$ KGE $\checkmark$}};
  \node[procbox, mcard, left=1.05cm of mos2] (mos1) {\textbf{7. Hillslope \& Tributaries}\\(\code{0.70h = 0.29\% HPC}, Sens $=6.7$)\\Repairs 1,690 missing (\code{NaN})\\grid slope cells \textbf{KEPT $\checkmark$}};
  \node[rulebox, mcard, right=1.05cm of mos2] (mos3) {\textbf{9. Reservoir \& Demand Mgmt}\\(\code{0.90h = 0.37\% HPC}, \textbf{Sens $=73.9$})\\Fixes 1,847 negative dam floors +\\returns unconsumed water: \textbf{$+202\%$ KGE $\checkmark$}};
  \coordinate (gmos_pad) at ([yshift=0.38cm]mos1.north);

  \draw[flow] (mos1.east) -- (mos2.west);
  \draw[flow] (mos2.east) -- (mos3.west);

  \begin{scope}[on background layer]
    \node[group, fit=(mos1)(mos2)(mos3)(gmos_pad), inner sep=11pt] (GMOS) {};
  \end{scope}
  \node[grouptitle] at (GMOS.north west) {Model 3: mosartwmpy River Routing \& Water Management (2.5 Node-Hrs/Run = 1.0\% of Compute)};

  % Row 4: Multi-Dimensional Assessment Outcomes Across 1,190 CONUS Gauges
  \node[juncbox, mcard, below=1.95cm of mos2] (out2) {\textbf{Water-Scarcity Accuracy}\\CONUS KGE: \textbf{0.847 $\rightarrow$ 0.909}\\False Deficit Cut: \textbf{$-86.2\%$} ($5.97\text{ km}^3$/yr)};
  \node[juncbox, mcard, left=1.05cm of out2] (out1) {\textbf{Physical Regimes Repaired}\\Small Headwaters: \textbf{0.013 $\rightarrow$ 0.337}\\Regulated Dams: \textbf{0.168 $\rightarrow$ 0.507}};
  \node[juncbox, mcard, right=1.05cm of out2] (out3) {\textbf{Compute \& UQ Ensemble Gain}\\Vadose Sub-Emu: \textbf{$-54.2\%$ HPC} ($2.2\times$ UQ)\\Whole-LSM (Last Resort): \textbf{$-98.5\%$ HPC}};
  \coordinate (gout_pad) at ([yshift=0.38cm]out1.north);

  \draw[flow] (out1.east) -- (out2.west);
  \draw[flow] (out3.west) -- (out2.east);

  \begin{scope}[on background layer]
    \node[group, fit=(out1)(out2)(out3)(gout_pad), inner sep=11pt] (GOUT) {};
  \end{scope}
  \node[grouptitle] at (GOUT.north west) {Assessment Outcome Across 1,190 USGS Stream Gauges (1981--2015: 672 Natural + 518 Regulated)};

  % Vertical connectors anchored to center column X
  \draw[flow] (lsm2.center |- GLSM.south) -- (tet2.center |- GTET.north);
  \draw[flow] (tet2.center |- GTET.south) -- (mos2.center |- GMOS.north);
  \draw[flow] (mos2.center |- GMOS.south) -- (out2.center |- GOUT.north);
\end{tikzpicture}
"""


def compile_tikz_pdf_and_png(raw_tikz: str, out_stem: Path) -> None:
    """Compile a TikZ block using print Earth-Tone palette to PDF, SVG, and 450-DPI white PNG."""
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
