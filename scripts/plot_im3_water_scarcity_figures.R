#!/usr/bin/env Rscript
# =============================================================================
# Waterology Earth-Tone Publication Figure Generator for the DOE IM3 Report
# Usage: Rscript scripts/plot_im3_water_scarcity_figures.R [results.json] [figures_dir]
# =============================================================================

suppressPackageStartupMessages({
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
json_path <- if (length(args) >= 1) args[1] else "reports/im3-water-scarcity-2026-11-20/im3_water_scarcity_results.json"
fig_dir   <- if (length(args) >= 2) args[2] else "reports/im3-water-scarcity-2026-11-20/figures"
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

d <- fromJSON(json_path, simplifyDataFrame = TRUE)

# Cohesive Waterology Earth-Tone Publication Palette
ET_PINE     <- "#2e6b4e"
ET_SLATE    <- "#3d6b82"
ET_OCHRE    <- "#c4842d"
ET_TERRA    <- "#b84a39"
ET_SAGE     <- "#6b9080"
ET_PLUM     <- "#7a5177"
ET_CHARCOAL <- "#2b2b2b"
ET_STONE    <- "#8c857b"
ET_SAND     <- "#f4f1ea"
ET_GOLD     <- "#d4a038"
ET_TEAL     <- "#2a7b88"

ET_PINE_B   <- "#1f4d37"
ET_SLATE_B  <- "#284b5c"
ET_OCHRE_B  <- "#8f5d19"
ET_TERRA_B  <- "#853023"
ET_SAGE_B   <- "#49695b"
ET_PLUM_B   <- "#543452"

add_bar_labels <- function(bp, vals_plot, vals_raw = vals_plot, cex = 0.72,
                           offset = 0.032, digits = 2, bold_rows = NULL) {
  nr <- nrow(vals_plot)
  nc <- ncol(vals_plot)
  for (r in seq_len(nr)) {
    for (c in seq_len(nc)) {
      v_raw <- vals_raw[r, c]
      v_plt <- vals_plot[r, c]
      if (is.finite(v_raw)) {
        lbl <- sprintf(paste0("%.", digits, "f"), v_raw)
        fnt <- if (!is.null(bold_rows) && (r %in% bold_rows)) 2 else 1
        text(bp[r, c], max(v_plt, 0) + offset, labels = lbl,
             cex = cex, col = ET_CHARCOAL, font = fnt, xpd = TRUE)
      }
    }
  }
}

# =============================================================================
# Figure 1: Ecosystem Triage (Sorted by HPC Share) & Physical Verification Gates
# =============================================================================
png(file.path(fig_dir, "fig1_triage_and_verification_gates.png"),
    width = 3250, height = 1260, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

# Panel (a): 9 Sub-Components Ordered by Compute Share [Sort Key]
par(mar = c(5.2, 16.8, 3.8, 2.2))
tc <- d$triage_components_sorted
idx_rev <- rev(seq_len(nrow(tc)))
comp_names <- tc$component[idx_rev]
cost_share_pct <- tc$compute_share[idx_rev] * 100.0
sens_scaled <- tc$downstream_sensitivity[idx_rev] * 100.0

mat_fig1a <- rbind(cost_share_pct, sens_scaled)
bp1a <- barplot(
  mat_fig1a,
  beside = TRUE,
  horiz = TRUE,
  names.arg = comp_names,
  las = 1,
  col = c(ET_SLATE, ET_OCHRE),
  border = c(ET_SLATE_B, ET_OCHRE_B),
  xlim = c(0, 92),
  ylim = c(0, 29.5),
  xlab = "Share of Total HPC Node-Hours (%)  /  Downstream Sensitivity (|dKGE| x 100)",
  main = "(a) 9-Subcomponent Triage (Sorted by HPC Share [Sort Key])",
  cex.names = 0.80,
  cex.axis = 0.88,
  cex.lab = 0.90,
  cex.main = 0.96
)
grid(nx = NULL, ny = NA, col = "#dcd7cd", lty = "dotted")
for (i in seq_len(ncol(bp1a))) {
  text(cost_share_pct[i] + 0.9, bp1a[1, i],
       labels = sprintf("%.1f%%", cost_share_pct[i]),
       pos = 4, cex = 0.72, col = ET_SLATE_B, font = 2, xpd = TRUE)
  text(sens_scaled[i] + 0.9, bp1a[2, i],
       labels = sprintf("%.2f", sens_scaled[i]),
       pos = 4, cex = 0.70, col = ET_OCHRE_B, font = 1, xpd = TRUE)
}
legend(x = 18, y = 16.0,
       legend = c("HPC Compute Share (% of 243.3h) [Sort Key]",
                  "Downstream Sensitivity (|dKGE| x 100)"),
       fill = c(ET_SLATE, ET_OCHRE),
       border = c(ET_SLATE_B, ET_OCHRE_B),
       bg = "white", box.col = "#dcd7cd", cex = 0.74)

# Panel (b): Mandatory Physical Verification Gate Scorecard
par(mar = c(5.2, 14.5, 3.8, 3.2))
vg <- d$verification_gates
vg_rev <- rev(seq_len(nrow(vg)))
gate_labels <- paste0(vg$gate_id[vg_rev], ": ",
                      c("Sub-Grid Area Filter (#129)",
                        "Tethys 6-Yr Canal Shares",
                        "MOSART Finite Slope Mask",
                        "GRanD Release Floor >= 0",
                        "Low-Flow Q10 PBIAS <= 25%",
                        "Vadose Baseflow QDRAI >= 0"))
base_compliance <- c(3.7, 50.0, 42.0, 0.9, 13.1, 45.0)
eng_compliance  <- c(100.0, 100.0, 100.0, 100.0, 100.0, 100.0)
mat_fig1b <- rbind(base_compliance, eng_compliance)

bp1b <- barplot(
  mat_fig1b,
  beside = TRUE,
  horiz = TRUE,
  names.arg = gate_labels,
  las = 1,
  col = c(ET_TERRA, ET_PINE),
  border = c(ET_TERRA_B, ET_PINE_B),
  xlim = c(0, 132),
  ylim = c(-2.2, 19.5),
  xlab = "Physical & Structural Gate Compliance Score (%)",
  main = "(b) Mandatory Physical Verification Gate & Audit Scorecard",
  cex.names = 0.84,
  cex.axis = 0.88,
  cex.lab = 0.94,
  cex.main = 1.00
)
abline(v = 100, col = ET_PINE_B, lty = 2, lwd = 1.5)
ans_txt <- c("0.0125 -> 0.3374 PASS",
             "3 missing -> 0 PASS",
             "1690 NaN -> 0 PASS",
             "1847 neg -> 0 PASS",
             "+21.7% -> +15.1% PASS",
             "124 neg -> 0 PASS")
for (i in seq_len(ncol(bp1b))) {
  text(eng_compliance[i] + 1.5, bp1b[2, i],
       labels = ans_txt[i],
       pos = 4, cex = 0.72, col = ET_PINE_B, font = 2, xpd = TRUE)
}
legend("bottomright",
       legend = c("Unfixed Baseline Chain (Pre-Audit)",
                  "Retained 9-Subcomponent Engineered Chain (All 6 Gates PASS)"),
       fill = c(ET_TERRA, ET_PINE),
       border = c(ET_TERRA_B, ET_PINE_B),
       bg = "white", box.col = "#dcd7cd", cex = 0.78)
dev.off()

# =============================================================================
# Figure 2: Cross-Family Strategy Comparison (Split Peak at Vertical Red Line)
# =============================================================================
png(file.path(fig_dir, "fig2_cross_family_strategy_comparison.png"),
    width = 3250, height = 1260, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

# Panel (a): Cross-family comparison ordered Asc Left / Desc Right of Red Divider Line
par(mar = c(8.6, 4.8, 3.8, 1.5))
cf <- d$cross_family_comparison
mat_cf <- rbind(cf$regulated_kge, cf$small_basin_kge, cf$conus_kge)
bp2a <- barplot(
  mat_cf,
  beside = TRUE,
  col = c(ET_PINE, ET_SLATE, ET_OCHRE),
  border = c(ET_PINE_B, ET_SLATE_B, ET_OCHRE_B),
  ylim = c(0, 1.24),
  ylab = "Streamflow Skill (Kling-Gupta Efficiency, KGE)",
  main = "(a) Cross-Family Comparison (Asc Left / Desc Right of Red Line [Sort Key: Reg KGE])",
  names.arg = rep("", nrow(cf)),
  cex.axis = 0.88,
  cex.lab = 0.94,
  cex.main = 0.96
)
grid(nx = NA, ny = NULL, col = "#dcd7cd", lty = "dotted")
add_bar_labels(bp2a, mat_cf, mat_cf, cex = 0.62, offset = 0.025, digits = 3, bold_rows = 1)

# Vertical Red Dashed Divider Line between Left Family (cols 1..4) and Right Family (cols 5..8)
x_red <- mean(c(max(bp2a[, 4]), min(bp2a[, 5])))
segments(x_red, 0, x_red, 1.08, col = "#c0392b", lty = 2, lwd = 2.8)
text(mean(bp2a[2, 1:4]), 1.03,
     labels = "Internal Sub-Component Physics (Asc -> Peak)",
     col = ET_PINE_B, font = 2, cex = 0.80, xpd = TRUE)
text(mean(bp2a[2, 5:8]), 1.03,
     labels = "AI Emulators & Unfixed Baselines (Peak -> Desc)",
     col = ET_TERRA_B, font = 2, cex = 0.80, xpd = TRUE)

text(x = bp2a[2, ], y = -0.04, labels = cf$short_label,
     srt = 28, adj = 1, xpd = TRUE, cex = 0.78, font = c(1, 1, 1, 2, 2, 1, 1, 1))
legend("top",
       legend = c("Regulated Dam Med KGE [Sort Key]",
                  "Small Headwater (<=4c) Med KGE",
                  "Pooled CONUS KGE"),
       fill = c(ET_PINE, ET_SLATE, ET_OCHRE),
       border = c(ET_PINE_B, ET_SLATE_B, ET_OCHRE_B),
       horiz = TRUE, bty = "n", cex = 0.78)

# Panel (b): Multi-Cohort Regime Profile Across the 5 Core Architectures
par(mar = c(8.6, 4.8, 3.8, 1.8))
cohorts_x <- 1:5
cohort_labels <- c("Pooled CONUS\n(1,190 Gauges)",
                   "All Natural HCDN\n(672 Gauges)",
                   "Large Natural >4c\n(226 Gauges)",
                   "Small Headwaters <=4c\n(446 Gauges)",
                   "Regulated Dams\n(518 Gauges)")
get_prof <- function(row_idx) {
  r <- cf[row_idx, ]
  c(r$conus_kge, r$natural_kge, r$large_natural_kge, r$small_basin_kge, r$regulated_kge)
}
p_full   <- get_prof(4)
p_vadose <- get_prof(5)
p_last   <- get_prof(6)
p_base   <- get_prof(7)
p_blind  <- get_prof(8)

plot(cohorts_x, p_full, type = "n", ylim = c(-0.06, 1.18), xlim = c(0.85, 5.15),
     xaxt = "n", xlab = "", ylab = "Median / Pooled Streamflow KGE",
     main = "(b) Streamflow Skill Profile Across Hydrologic & Regulation Regimes",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.96)
grid(nx = NULL, ny = NULL, col = "#dcd7cd", lty = "dotted")
axis(1, at = cohorts_x, labels = cohort_labels, cex.axis = 0.78, padj = 0.45)

lines(cohorts_x, p_full,   col = ET_PINE,  lwd = 3.2, type = "b", pch = 19, cex = 1.3)
lines(cohorts_x, p_vadose, col = ET_TEAL,  lwd = 2.6, type = "b", pch = 17, cex = 1.2, lty = 2)
lines(cohorts_x, p_last,   col = ET_SLATE, lwd = 2.4, type = "b", pch = 15, cex = 1.1, lty = 3)
lines(cohorts_x, p_base,   col = ET_STONE, lwd = 2.4, type = "b", pch = 18, cex = 1.2, lty = 4)
lines(cohorts_x, p_blind,  col = ET_TERRA, lwd = 2.6, type = "b", pch = 4,  cex = 1.2, lty = 2)

text(cohorts_x, p_full + 0.052, labels = sprintf("%.3f", p_full),
     col = ET_PINE_B, font = 2, cex = 0.76)
text(cohorts_x, p_blind - 0.055, labels = sprintf("%.3f", p_blind),
     col = ET_TERRA_B, font = 1, cex = 0.72)

legend("topright",
       legend = c("Full 9-Subcomponent Physics (216.3h, Best Across All Regimes)",
                  "Targeted Vadose Sub-Emulator After Fixes (111.3h, -54% HPC)",
                  "Last-Resort Whole-LSM Emulator After Fixes (3.3h, -98.5% HPC)",
                  "Unfixed Baseline IM3 Chain (243.3h)",
                  "Blind Whole-LSM Emulator Without Downstream Fixes (3.3h)"),
       col = c(ET_PINE, ET_TEAL, ET_SLATE, ET_STONE, ET_TERRA),
       lwd = c(3.2, 2.6, 2.4, 2.4, 2.6),
       pch = c(19, 17, 15, 18, 4),
       lty = c(1, 2, 3, 4, 2),
       bg = "white", box.col = "#dcd7cd", cex = 0.76)
dev.off()

# =============================================================================
# Figure 3: 12-Stage Sub-Component Progression & PhysicalCheck Vetoes
# =============================================================================
png(file.path(fig_dir, "fig3_subcomponent_progression_and_vetoes.png"),
    width = 3250, height = 1260, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

st <- d$stages
n_st <- nrow(st)
x_st <- seq_len(n_st) - 1
short_st <- c("0.Base", "1.CLM-SP", "2.Demeter", "3.UncalInf",
              "4.CalInf", "5.CalBase", "6.NN-Vad", "7.TethM2",
              "8.CERF", "9.Muni", "10.HSlp", "11.SubGrid", "12.Broman")
status_cols <- ifelse(st$status == "kept", ET_PINE,
               ifelse(st$status == "vetoed", ET_TERRA,
               ifelse(st$status == "reverted", ET_OCHRE, ET_SLATE)))
status_pch  <- ifelse(st$status == "kept", 19,
               ifelse(st$status == "vetoed", 13,
               ifelse(st$status == "reverted", 4, 15)))

# Panel (a): 12-Stage Skill Trajectory Across Regimes
par(mar = c(6.8, 4.8, 3.8, 1.5))
kge_c_clip <- pmax(st$conus_kge, -0.18)

plot(x_st, kge_c_clip, type = "n", ylim = c(-0.24, 1.05),
     xaxt = "n", xlab = "", ylab = "Streamflow Skill (KGE)",
     main = "(a) 12-Stage Sub-Component Progression Inside CLM/ELM, Tethys & mosartwmpy",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.98)
grid(nx = NULL, ny = NULL, col = "#dcd7cd", lty = "dotted")
abline(h = 0, col = ET_STONE, lty = 3)
axis(1, at = x_st, labels = short_st, las = 2, cex.axis = 0.78)

kept_idx <- which(st$status %in% c("baseline", "kept"))
lines(x_st[kept_idx], st$conus_kge[kept_idx], col = ET_PINE, lwd = 2.8)
lines(x_st[kept_idx], st$median_gauge_kge_regulated[kept_idx], col = ET_PLUM, lwd = 2.5, lty = 2)
lines(x_st[kept_idx], st$median_gauge_kge_small_basins[kept_idx], col = ET_SLATE, lwd = 2.5, lty = 3)

points(x_st, kge_c_clip, col = status_cols, pch = status_pch, cex = 1.5, lwd = 2)
points(x_st[kept_idx], st$median_gauge_kge_regulated[kept_idx], col = ET_PLUM, pch = 17, cex = 1.1)
points(x_st[kept_idx], st$median_gauge_kge_small_basins[kept_idx], col = ET_SLATE, pch = 15, cex = 1.1)

text(x_st[3 + 1], kge_c_clip[3 + 1] - 0.075, labels = "VETOED\n(Q10 > 25%)", col = ET_TERRA_B, cex = 0.68, font = 2)
text(x_st[6 + 1] + 0.2, kge_c_clip[6 + 1] + 0.08, labels = "VETOED (Stage 6)\n(QDRAI = -19.8 < 0)", col = ET_TERRA_B, cex = 0.68, font = 2)
text(x_st[11 + 1] - 0.5, st$median_gauge_kge_small_basins[11 + 1] + 0.06,
     labels = "+2,600% Small-Basin", col = ET_SLATE_B, cex = 0.72, font = 2)
text(x_st[12 + 1] - 0.9, st$median_gauge_kge_regulated[12 + 1] + 0.06,
     labels = "+202% Reg Dam", col = ET_PLUM_B, cex = 0.72, font = 2)

legend(x = 0.0, y = 0.63,
       legend = c("Pooled CONUS KGE (Kept Trajectory: 0.8471 -> 0.9094)",
                  "Regulated Dam Med KGE (Kept Trajectory: 0.1680 -> 0.5072)",
                  "Small-Basin <=4c Med KGE (Kept Trajectory: 0.0125 -> 0.3374)",
                  "KEPT Candidate (8/12)", "REVERTED Candidate (2/12)", "VETOED by PhysicalCheck (2/12)"),
       col = c(ET_PINE, ET_PLUM, ET_SLATE, ET_PINE, ET_OCHRE, ET_TERRA),
       lwd = c(2.8, 2.5, 2.5, NA, NA, NA),
       lty = c(1, 2, 3, NA, NA, NA),
       pch = c(19, 17, 15, 19, 4, 13),
       bg = "white", box.col = "#dcd7cd", cex = 0.72)

# Panel (b): Physical Guardrail Audit Across the 12 Candidates (Low-Flow Q10 PBIAS %)
par(mar = c(6.8, 4.8, 3.8, 1.8))
q10_vals <- st$conus_low_flow_q10_pbias
q10_plot <- pmax(pmin(q10_vals, 46), -35)

bp3b <- barplot(
  q10_plot,
  names.arg = short_st,
  las = 2,
  col = status_cols,
  border = ET_CHARCOAL,
  ylim = c(-44, 54),
  ylab = "Low-Flow Drought Bias: Q10 PBIAS (%)",
  main = "(b) Physical Guardrail Audit: Drought Low-Flow Q10 Bias & Baseflow Veto Gate",
  cex.names = 0.78,
  cex.axis = 0.88,
  cex.lab = 0.94,
  cex.main = 0.98
)
rect(par("usr")[1], 25, par("usr")[2], 54, col = adjustcolor(ET_TERRA, alpha.f = 0.14), border = NA)
rect(par("usr")[1], -44, par("usr")[2], -25, col = adjustcolor(ET_TERRA, alpha.f = 0.14), border = NA)
abline(h = c(-25, 25), col = ET_TERRA_B, lty = 2, lwd = 2)
abline(h = 0, col = ET_CHARCOAL, lwd = 1)
text(mean(bp3b), 48.5, labels = "PHYSICAL VETO ZONE: |Q10 PBIAS| > 25.0% OR QDRAI < -0.05 m3/s",
     col = ET_TERRA_B, font = 2, cex = 0.78)

for (i in seq_len(n_st)) {
  v_raw <- q10_vals[i]
  v_plt <- q10_plot[i]
  y_pos <- if (v_plt >= 0) v_plt + 2.5 else v_plt - 3.2
  lbl <- if (i == 7) "-205% (QDRAI=-19.8)" else sprintf("%+.1f%%", v_raw)
  text(bp3b[i], y_pos, labels = lbl, cex = 0.65,
       col = if (st$status[i] == "vetoed") ET_TERRA_B else ET_CHARCOAL,
       font = if (st$status[i] == "vetoed" || i == n_st) 2 else 1, xpd = TRUE)
}
dev.off()

# =============================================================================
# Figure 4: CONUS Spatial Skill Gain Map & Small-Basin Grid-Quantization Bins
# =============================================================================
png(file.path(fig_dir, "fig4_conus_spatial_skill_and_headwater_quantization.png"),
    width = 3250, height = 1240, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

# Panel (a): CONUS Spatial Map of Per-Gauge Skill Gain (dKGE)
par(mar = c(5.2, 4.8, 3.8, 1.5))
sg <- d$spatial_gauges
dk <- sg$delta_kge
pt_cols <- ifelse(dk >= 0.25, ET_PINE_B,
           ifelse(dk >= 0.08, ET_PINE,
           ifelse(dk >= 0.00, ET_SAGE,
           ifelse(dk >= -0.03, ET_STONE, ET_TERRA))))
pt_pch  <- ifelse(sg$cohort == "regulated", 17, 19)

plot(sg$lon, sg$lat, type = "n", xlim = c(-125.5, -66.5), ylim = c(25.0, 49.8),
     xlab = "Longitude (deg W)", ylab = "Latitude (deg N)",
     main = "(a) CONUS Spatial Skill Gain dKGE Across 1,190 USGS Gauges (82.8% Improved)",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.98)
rect(par("usr")[1], par("usr")[3], par("usr")[2], par("usr")[4], col = "#faf8f4", border = ET_STONE)
grid(nx = 6, ny = 5, col = "#dcd7cd", lty = "dotted")
points(sg$lon, sg$lat, col = adjustcolor(pt_cols, alpha.f = 0.85), pch = pt_pch, cex = 0.95)

legend("bottomleft",
       legend = c("dKGE >= +0.25 (Large Gain)",
                  "+0.08 <= dKGE < +0.25 (Moderate Gain)",
                  "0.00 <= dKGE < +0.08 (Slight Gain)",
                  "dKGE < 0.00 (17.2% of Gauges)",
                  "Natural HCDN Gauge (n=672, 71.5% <=4c Improved)",
                  "Regulated GRanD Dam Gauge (n=518, 96.5% Improved)"),
       col = c(ET_PINE_B, ET_PINE, ET_SAGE, ET_TERRA, ET_CHARCOAL, ET_CHARCOAL),
       pch = c(15, 15, 15, 15, 19, 17),
       bg = "white", cex = 0.72)

# Panel (b): Natural Streamflow Skill by Basin Grid-Cell Count (672 HCDN Gauges)
par(mar = c(5.8, 4.8, 3.8, 1.8))
bins <- d$basin_size_bins
mat_bins <- rbind(bins$base_kge_median, bins$final_kge_median)
short_bins <- c("1 Cell\n(<150 km2\nn=146)",
                "2 Cells\n(150-300\nn=140)",
                "3-4 Cells\n(300-600\nn=160)",
                "5-8 Cells\n(600-1.2k\nn=115)",
                "9-15 Cells\n(1.2k-2.5k\nn=61)",
                ">15 Cells\n(>2.5k km2\nn=50)")
bp4b <- barplot(
  mat_bins,
  beside = TRUE,
  names.arg = short_bins,
  col = c(ET_STONE, ET_SLATE),
  border = c(ET_CHARCOAL, ET_SLATE_B),
  ylim = c(-0.15, 0.72),
  ylab = "Median Natural Gauge KGE (with 75th Percentile Whisker)",
  main = "(b) Headwater Grid-Quantization Bottleneck by NLDAS2 0.125-Deg Cell Count",
  cex.names = 0.76,
  cex.axis = 0.88,
  cex.lab = 0.94,
  cex.main = 0.98
)
grid(nx = NA, ny = NULL, col = "#dcd7cd", lty = "dotted")
abline(h = 0, col = ET_CHARCOAL, lty = 2)

# Add Q75 upper whiskers and value labels ABOVE the whisker tips
arrows(bp4b[1, ], pmax(bins$base_kge_median, 0), bp4b[1, ], bins$base_kge_q75,
       angle = 90, code = 2, length = 0.04, col = ET_CHARCOAL, lwd = 1.4)
arrows(bp4b[2, ], pmax(bins$final_kge_median, 0), bp4b[2, ], bins$final_kge_q75,
       angle = 90, code = 2, length = 0.04, col = ET_SLATE_B, lwd = 1.6)

for (i in seq_len(nrow(bins))) {
  yb <- bins$base_kge_q75[i] + 0.025
  yf <- bins$final_kge_q75[i] + 0.025
  text(bp4b[1, i], yb, labels = sprintf("%.2f", bins$base_kge_median[i]),
       cex = 0.68, col = ET_CHARCOAL)
  text(bp4b[2, i], yf, labels = sprintf("%.2f", bins$final_kge_median[i]),
       cex = 0.72, col = ET_SLATE_B, font = 2)
}
legend("topright",
       legend = c("Baseline Gridded MOSART + CLM5 (Med KGE <=4c = 0.0125)",
                  "Sub-Grid Area-Filtered Routing #129 + ELMv3 (Med KGE <=4c = 0.3374, +2,600%)"),
       fill = c(ET_STONE, ET_SLATE),
       border = c(ET_CHARCOAL, ET_SLATE_B),
       bg = "white", box.col = "#dcd7cd", cex = 0.75)
dev.off()

# =============================================================================
# Figure 5: Regulated Dam Seasonal Climatology & 35-Year Unmet Water Demand
# =============================================================================
png(file.path(fig_dir, "fig5_regulated_climatology_and_sectoral_water_balance.png"),
    width = 3250, height = 1240, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

# Panel (a): Regulated Dam 12-Month Discharge Climatology + Veto Canary
par(mar = c(5.2, 4.8, 3.8, 1.5))
clim <- d$regulated_monthly_climatology
m_x <- clim$month_index

plot(m_x, clim$obs_median_m3s, type = "n", ylim = c(-78, 178), xlim = c(1, 12),
     xaxt = "n", xlab = "Calendar Month (1981-2015 Climatology Across 518 Regulated Dam Gauges)",
     ylab = "Regulated River Discharge / Subsurface Flux (m3/s)",
     main = "(a) Regulated Dam Seasonal Climatology & Non-Negative Physical Veto Canary",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.98)
rect(par("usr")[1], -78, par("usr")[2], 0, col = adjustcolor(ET_TERRA, alpha.f = 0.16), border = NA)
grid(nx = NULL, ny = NULL, col = "#dcd7cd", lty = "dotted")
abline(h = 0, col = ET_TERRA_B, lty = 2, lwd = 2)
axis(1, at = 1:12, labels = clim$month, cex.axis = 0.86)

lines(m_x, clim$obs_median_m3s,         col = ET_CHARCOAL, lwd = 3.2, type = "b", pch = 19)
lines(m_x, clim$final_median_m3s,       col = ET_PINE,     lwd = 3.0, type = "b", pch = 17)
lines(m_x, clim$base_median_m3s,        col = ET_OCHRE,    lwd = 2.5, type = "b", pch = 15, lty = 2)
lines(m_x, clim$veto_drought_p15_m3s,   col = ET_TERRA,    lwd = 2.6, type = "b", pch = 13, lty = 3)

text(6.5, -16,
     labels = "PHYSICAL VETO ZONE (Q < 0 m3/s): Unconstrained Neural Vadose Surrogate Suction (-66.2 m3/s in Sep)",
     col = ET_TERRA_B, font = 2, cex = 0.74)

legend("topleft",
       legend = c("USGS Observed Regulated Discharge (518 Pre-1980 GRanD Dam Gauges)",
                  "Retained 9-Subcomponent Chain (Broman 9505v4 + Return Flow, Med KGE = 0.5072)",
                  "Baseline IM3 Chain (20230629 Rules + Total Withdrawal, Med KGE = 0.1680)",
                  "Vetoed Unconstrained Neural Vadose Surrogate (15th Pct Drought Flux < 0)"),
       col = c(ET_CHARCOAL, ET_PINE, ET_OCHRE, ET_TERRA),
       lwd = c(3.2, 3.0, 2.5, 2.6),
       pch = c(19, 17, 15, 13),
       lty = c(1, 1, 2, 3),
       bg = "white", box.col = "#dcd7cd", cex = 0.74)

# Panel (b): 35-Year Annual CONUS Unmet Water Demand Time Series (1981-2015)
par(mar = c(5.2, 4.8, 3.8, 1.8))
ud <- d$annual_unmet_demand
yrs <- ud$year

plot(yrs, ud$baseline_km3_yr, type = "n", ylim = c(0, 86), xlim = c(1981, 2015),
     xlab = "Simulation Year (1981-2015 Historical Evaluation Window)",
     ylab = "CONUS Annual Unmet Water Demand Deficit (km3/yr)",
     main = "(b) 35-Year CONUS Annual Unmet Water Demand Reduction (-86.2% Artificial Deficit)",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.98)
grid(nx = NULL, ny = NULL, col = "#dcd7cd", lty = "dotted")

polygon(c(yrs, rev(yrs)), c(ud$baseline_km3_yr, rev(ud$retained_9subcomponent_km3_yr)),
        col = adjustcolor(ET_SAGE, alpha.f = 0.22), border = NA)

lines(yrs, ud$baseline_km3_yr,               col = ET_TERRA, lwd = 2.8, type = "l")
lines(yrs, ud$tethys_m2_canal_fix_km3_yr,    col = ET_SLATE, lwd = 2.4, lty = 2)
lines(yrs, ud$retained_9subcomponent_km3_yr, col = ET_PINE,  lwd = 3.0, type = "l")

idx_2002 <- which(yrs == 2002)
idx_2012 <- which(yrs == 2012)
points(c(2002, 2012), ud$baseline_km3_yr[c(idx_2002, idx_2012)], col = ET_TERRA_B, pch = 19, cex = 1.2)
text(2002, ud$baseline_km3_yr[idx_2002] + 3.8,
     labels = sprintf("2002 Drought\n(%.1f km3/yr)", ud$baseline_km3_yr[idx_2002]),
     cex = 0.72, col = ET_TERRA_B, font = 2)
text(2012, ud$baseline_km3_yr[idx_2012] + 3.8,
     labels = sprintf("2012 Drought\n(%.1f km3/yr)", ud$baseline_km3_yr[idx_2012]),
     cex = 0.72, col = ET_TERRA_B, font = 2)

legend("topleft",
       legend = c(sprintf("Baseline Chain (Tethys 2.1.0 + No Return Flow): Mean = %.2f km3/yr", mean(ud$baseline_km3_yr)),
                  sprintf("After Tethys 2.2.0 M2 + 0.829937 Canal Loss Fix: Mean = %.2f km3/yr (-23.9%%)", mean(ud$tethys_m2_canal_fix_km3_yr)),
                  sprintf("Retained 9-Subcomponent Chain (+ Return Flow & 9505v4): Mean = %.2f km3/yr (-86.2%%)", mean(ud$retained_9subcomponent_km3_yr))),
       col = c(ET_TERRA, ET_SLATE, ET_PINE),
       lwd = c(2.8, 2.4, 3.0),
       lty = c(1, 2, 1),
       bg = "white", box.col = "#dcd7cd", cex = 0.74)
dev.off()

# =============================================================================
# Figure 6: Multi-Objective Cost-Accuracy Pareto Frontier & Campaign Break-Even
# =============================================================================
png(file.path(fig_dir, "fig6_pareto_frontier_and_campaign_breakeven.png"),
    width = 3250, height = 1240, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

# Panel (a): HPC Cost vs Regulated Dam Skill Pareto Frontier
par(mar = c(5.2, 4.8, 3.8, 1.5))
plot(c(0, 265), c(0.06, 0.56), type = "n",
     xlab = "Single-Run Computational Cost (NERSC HPC Node-Hours per 35-Yr CONUS Run)",
     ylab = "Regulated Dam Streamflow Skill (Median KGE Across 518 Gauges)",
     main = "(a) Cost-Accuracy Pareto Frontier: Internal Physics vs. Targeted & Whole Emulators",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.98)
grid(nx = NULL, ny = NULL, col = "#dcd7cd", lty = "dotted")

rect(0, 0.07, 132, 0.155, col = adjustcolor(ET_TERRA, alpha.f = 0.15), border = ET_TERRA)
text(66, 0.134, labels = "Fast but Scientifically Broken Trap", col = ET_TERRA_B, font = 2, cex = 0.78)

st_kept <- st[st$status %in% c("baseline", "kept"), ]
lines(st_kept$hpc_node_hours, st_kept$median_gauge_kge_regulated,
      col = ET_SAGE, lwd = 2.4, lty = 2, type = "b", pch = 19)

pf_x <- c(cf$hpc_node_hours[6], cf$hpc_node_hours[5], cf$hpc_node_hours[4])
pf_y <- c(cf$regulated_kge[6],  cf$regulated_kge[5],  cf$regulated_kge[4])
lines(pf_x, pf_y, col = ET_PINE, lwd = 3.2)

points(cf$hpc_node_hours[8], cf$regulated_kge[8], col = ET_TERRA, pch = 13, cex = 1.7, lwd = 2.2)
points(cf$hpc_node_hours[7], cf$regulated_kge[7], col = ET_STONE, pch = 18, cex = 1.7)
points(cf$hpc_node_hours[6], cf$regulated_kge[6], col = ET_SLATE, pch = 15, cex = 1.6)
points(cf$hpc_node_hours[5], cf$regulated_kge[5], col = ET_TEAL,  pch = 17, cex = 1.7)
points(cf$hpc_node_hours[4], cf$regulated_kge[4], col = ET_PINE,  pch = 19, cex = 1.8)

text(cf$hpc_node_hours[8] + 6,  cf$regulated_kge[8] - 0.015,
     labels = "Blind Whole-LSM Emulator (3.3h, Reg KGE=0.106)", pos = 4, cex = 0.74, col = ET_TERRA_B, font = 2)
text(cf$hpc_node_hours[7] - 4,  cf$regulated_kge[7] - 0.032,
     labels = "0. Baseline Chain (243.3h, Reg KGE=0.168)", pos = 2, cex = 0.74, col = ET_CHARCOAL)
text(cf$hpc_node_hours[6] + 6,  cf$regulated_kge[6] - 0.018,
     labels = "Last-Resort Whole-LSM Emulator After Fixes (3.3h, Reg KGE=0.387, CONUS=0.900)",
     pos = 4, cex = 0.74, col = ET_SLATE_B, font = 2)
text(cf$hpc_node_hours[5] - 18, cf$regulated_kge[5] + 0.028,
     labels = "Targeted Vadose Sub-Emulator (111.3h, Reg KGE=0.456, CONUS=0.907)",
     cex = 0.74, col = ET_TEAL, font = 2)
text(cf$hpc_node_hours[4] - 5,  cf$regulated_kge[4] + 0.025,
     labels = "Retained 9-Subcomponent Physics (216.3h, Reg KGE=0.507, CONUS=0.909)",
     pos = 2, cex = 0.76, col = ET_PINE_B, font = 2)

# Panel (b): Cumulative Campaign HPC Cost vs. Number of Ensemble Runs (N = 1..50)
par(mar = c(5.2, 4.8, 3.8, 1.8))
cb <- d$campaign_breakeven
n_seq <- 1:50
c_base_seq <- 243.3 * n_seq
c_phys_seq <- 216.3 * n_seq
c_vad_seq  <- 8.0 + 111.3 * n_seq
c_last_seq <- 15.0 + 3.3 * n_seq

plot(n_seq, c_base_seq / 1000.0, type = "n", ylim = c(0, 13.0), xlim = c(1, 50),
     xlab = "Number of 35-Year IM3 Scenario / Ensemble Evaluations (N)",
     ylab = "Cumulative Campaign Compute Cost (Thousand NERSC Node-Hours)",
     main = "(b) Cumulative Multi-Scenario Campaign Cost & Emulator Break-Even (N* = 1 Run)",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.98)
grid(nx = NULL, ny = NULL, col = "#dcd7cd", lty = "dotted")

lines(n_seq, c_base_seq / 1000.0, col = ET_STONE, lwd = 2.5, lty = 2)
lines(n_seq, c_phys_seq / 1000.0, col = ET_PINE,  lwd = 3.0)
lines(n_seq, c_vad_seq  / 1000.0, col = ET_TEAL,  lwd = 3.0)
lines(n_seq, c_last_seq / 1000.0, col = ET_SLATE, lwd = 3.0)

points(cb$n_runs, cb$retained_physics_hpc_hours / 1000.0, col = ET_PINE,  pch = 19, cex = 1.0)
points(cb$n_runs, cb$targeted_vadose_emulator_hpc_hours / 1000.0, col = ET_TEAL, pch = 17, cex = 1.0)
points(cb$n_runs, cb$last_resort_whole_lsm_emulator_hpc_hours / 1000.0, col = ET_SLATE, pch = 15, cex = 1.0)

legend("topleft",
       legend = c("Unfixed Baseline Chain: 243.3h/run -> 12,165 Node-Hrs at N=50",
                  "Retained 9-Subcomponent Physics: 216.3h/run -> 10,815 Node-Hrs at N=50 (-11.1%, Best Skill)",
                  "Targeted Vadose Sub-Emulator: 8h train + 111.3h/run -> 5,573 Node-Hrs at N=50 (-54.2% HPC)",
                  "Last-Resort Whole-LSM Emulator: 15h train + 3.3h/run -> 180 Node-Hrs at N=50 (-98.5% HPC)"),
       col = c(ET_STONE, ET_PINE, ET_TEAL, ET_SLATE),
       lwd = c(2.5, 3.0, 3.0, 3.0),
       lty = c(2, 1, 1, 1),
       pch = c(NA, 19, 17, 15),
       bg = "white", box.col = "#dcd7cd", cex = 0.74)
dev.off()

cat("Generated all 6 Cairo PNG figures in", fig_dir, "\n")
