#!/usr/bin/env Rscript
# =============================================================================
# AGU Poster Data Figure Generator (Figures 3, 4, and 5)
# Usage: Rscript scripts/plot_agu_poster_figures.R
# =============================================================================

suppressPackageStartupMessages({
  library(jsonlite)
})

json_src <- "reports/im3-water-scarcity-2026-11-20/im3_water_scarcity_results.json"
poster_dir <- "reports/agu-poster-im3-assessment-2026-11-20"
fig_dir <- file.path(poster_dir, "figures")
dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)
file.copy(json_src, file.path(poster_dir, "im3_water_scarcity_results.json"), overwrite = TRUE)

d <- fromJSON(json_src, simplifyDataFrame = TRUE)

# Waterology Earth-Tone Publication Palette
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
# Figure 3 (Poster Data Figure 1): Triage Decoupling & Process vs. Emulation
# =============================================================================
png(file.path(fig_dir, "fig3_poster_triage_and_process_attribution.png"),
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

mat_fig3a <- rbind(cost_share_pct, sens_scaled)
bp3a <- barplot(
  mat_fig3a,
  beside = TRUE,
  horiz = TRUE,
  names.arg = comp_names,
  las = 1,
  col = c(ET_SLATE, ET_OCHRE),
  border = c(ET_SLATE_B, ET_OCHRE_B),
  xlim = c(0, 96),
  ylim = c(0, 29.5),
  xlab = "Share of Total HPC Node-Hours (%)  /  Downstream Sensitivity (|dKGE| x 100)",
  main = "(a) Sub-Component Triage: Compute Share [Sort Key] vs. Sensitivity",
  cex.names = 0.80,
  cex.axis = 0.88,
  cex.lab = 0.90,
  cex.main = 0.96
)
grid(nx = NULL, ny = NA, col = "#dcd7cd", lty = "dotted")
for (i in seq_len(ncol(bp3a))) {
  text(cost_share_pct[i] + 0.9, bp3a[1, i],
       labels = sprintf("%.1f%%", cost_share_pct[i]),
       pos = 4, cex = 0.72, col = ET_SLATE_B, font = 2, xpd = TRUE)
  text(sens_scaled[i] + 0.9, bp3a[2, i],
       labels = sprintf("%.2f", sens_scaled[i]),
       pos = 4, cex = 0.70, col = ET_OCHRE_B, font = 1, xpd = TRUE)
}
legend(x = 18, y = 16.0,
       legend = c("HPC Compute Share (% of 243.3h) [Sort Key]",
                  "Downstream Sensitivity (|dKGE| x 100)"),
       fill = c(ET_SLATE, ET_OCHRE),
       border = c(ET_SLATE_B, ET_OCHRE_B),
       bg = "white", box.col = "#dcd7cd", cex = 0.74)

# Panel (b): Cross-Family Process Repairs vs. Emulators (Asc Left / Desc Right of Red Line)
par(mar = c(8.6, 4.8, 3.8, 1.5))
cf <- d$cross_family_comparison
mat_cf <- rbind(cf$regulated_kge, cf$small_basin_kge, cf$conus_kge)
bp3b <- barplot(
  mat_cf,
  beside = TRUE,
  col = c(ET_PINE, ET_SLATE, ET_OCHRE),
  border = c(ET_PINE_B, ET_SLATE_B, ET_OCHRE_B),
  ylim = c(0, 1.24),
  ylab = "Streamflow Skill (Kling-Gupta Efficiency, KGE)",
  main = "(b) Process Engineering vs. Emulation (Asc Left / Desc Right [Sort Key: Reg KGE])",
  names.arg = rep("", nrow(cf)),
  cex.axis = 0.88,
  cex.lab = 0.94,
  cex.main = 0.96
)
grid(nx = NA, ny = NULL, col = "#dcd7cd", lty = "dotted")
add_bar_labels(bp3b, mat_cf, mat_cf, cex = 0.62, offset = 0.025, digits = 3, bold_rows = 1)

x_red <- mean(c(max(bp3b[, 4]), min(bp3b[, 5])))
segments(x_red, 0, x_red, 1.08, col = "#c0392b", lty = 2, lwd = 2.8)
text(mean(bp3b[2, 1:4]), 1.03,
     labels = "Internal Physics (Asc -> Peak)",
     col = ET_PINE_B, font = 2, cex = 0.80, xpd = TRUE)
text(mean(bp3b[2, 5:8]), 1.03,
     labels = "Emulators & Baselines (Peak -> Desc)",
     col = ET_TERRA_B, font = 2, cex = 0.80, xpd = TRUE)

text(x = bp3b[2, ], y = -0.04, labels = cf$short_label,
     srt = 28, adj = 1, xpd = TRUE, cex = 0.78, font = c(1, 1, 1, 2, 2, 1, 1, 1))
legend("top",
       legend = c("Regulated Dam Med KGE [Sort Key]",
                  "Small Headwater (<=4c) KGE",
                  "Pooled CONUS KGE"),
       fill = c(ET_PINE, ET_SLATE, ET_OCHRE),
       border = c(ET_PINE_B, ET_SLATE_B, ET_OCHRE_B),
       horiz = TRUE, bty = "n", cex = 0.76)
dev.off()

# =============================================================================
# Figure 4 (Poster Data Figure 2): Physical Process Diagnostics Across CONUS
# =============================================================================
png(file.path(fig_dir, "fig4_poster_physical_process_diagnostics.png"),
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
     main = "(a) CONUS Spatial Process Gain dKGE Across 1,190 Gauges (82.8% Improved)",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.98)
rect(par("usr")[1], par("usr")[3], par("usr")[2], par("usr")[4], col = "white", border = ET_STONE)
grid(nx = 6, ny = 5, col = "#dcd7cd", lty = "dotted")
points(sg$lon, sg$lat, col = adjustcolor(pt_cols, alpha.f = 0.85), pch = pt_pch, cex = 0.95)

legend("bottomleft",
       legend = c("dKGE >= +0.25 (Large Process Gain)",
                  "+0.08 <= dKGE < +0.25 (Moderate Gain)",
                  "0.00 <= dKGE < +0.08 (Slight Gain)",
                  "dKGE < 0.00 (17.2% of Gauges)",
                  "Natural HCDN Gauge (n=672; <=4c Med KGE: 0.013 -> 0.337, +2,600%)",
                  "Regulated GRanD Dam Gauge (n=518; 96.5% Improved, Med KGE: 0.168 -> 0.507)"),
       col = c(ET_PINE_B, ET_PINE, ET_SAGE, ET_TERRA, ET_CHARCOAL, ET_CHARCOAL),
       pch = c(15, 15, 15, 15, 19, 17),
       bg = "white", cex = 0.71)

# Panel (b): 35-Year Annual CONUS Unmet Water Demand Reduction (1981-2015)
par(mar = c(5.2, 4.8, 3.8, 1.8))
ud <- d$annual_unmet_demand
yrs <- ud$year

plot(yrs, ud$baseline_km3_yr, type = "n", ylim = c(0, 86), xlim = c(1981, 2015),
     xlab = "Simulation Year (1981-2015 Historical Evaluation Window)",
     ylab = "CONUS Annual Unmet Water Demand Deficit (km3/yr)",
     main = "(b) Water-Scarcity Process Attribution: -86.2% Artificial Deficit Removed",
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
     labels = sprintf("2002 Drought\n(%.1f -> %.1f km3/yr)",
                      ud$baseline_km3_yr[idx_2002], ud$retained_9subcomponent_km3_yr[idx_2002]),
     cex = 0.72, col = ET_TERRA_B, font = 2)
text(2012, ud$baseline_km3_yr[idx_2012] + 3.8,
     labels = sprintf("2012 Drought\n(%.1f -> %.1f km3/yr)",
                      ud$baseline_km3_yr[idx_2012], ud$retained_9subcomponent_km3_yr[idx_2012]),
     cex = 0.72, col = ET_TERRA_B, font = 2)

legend("topleft",
       legend = c(sprintf("Baseline Chain (Tethys 2.1.0 + No Return Flow): Mean = %.2f km3/yr", mean(ud$baseline_km3_yr)),
                  sprintf("Step 1: Tethys 2.2.0 M2 + 0.829937 Canal Efficiency: Mean = %.2f km3/yr (-23.9%%)", mean(ud$tethys_m2_canal_fix_km3_yr)),
                  sprintf("Step 2: + mosartwmpy Return Flows & Broman 9505v4 Floor: Mean = %.2f km3/yr (-86.2%%)", mean(ud$retained_9subcomponent_km3_yr))),
       col = c(ET_TERRA, ET_SLATE, ET_PINE),
       lwd = c(2.8, 2.4, 3.0),
       lty = c(1, 2, 1),
       bg = "white", box.col = "#dcd7cd", cex = 0.74)
dev.off()

# =============================================================================
# Figure 5 (Poster Data Figure 3): Practical Savings & UQ Ensemble Capacity
# =============================================================================
png(file.path(fig_dir, "fig5_poster_practical_savings_and_uq_capacity.png"),
    width = 3250, height = 1240, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

# Panel (a): HPC Cost vs Regulated Dam Skill & Retained Physical Process Modules
par(mar = c(5.2, 4.8, 3.8, 1.5))
st <- d$stages
plot(c(0, 265), c(0.06, 0.56), type = "n",
     xlab = "Single-Run Computational Cost (NERSC HPC Node-Hours per 35-Yr CONUS Run)",
     ylab = "Regulated Dam Streamflow Skill (Median KGE Across 518 Gauges)",
     main = "(a) Multi-Objective Pareto Frontier: Compute Cost vs. Process Fidelity",
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
     labels = "0. Baseline Chain (243.3h, 9/9 Phys, Reg=0.168)", pos = 2, cex = 0.74, col = ET_CHARCOAL)
text(cf$hpc_node_hours[6] + 6,  cf$regulated_kge[6] - 0.018,
     labels = "Last-Resort Whole-LSM Emulator (3.3h, 6/9 Phys, Reg=0.387)",
     pos = 4, cex = 0.74, col = ET_SLATE_B, font = 2)
text(cf$hpc_node_hours[5] - 18, cf$regulated_kge[5] + 0.028,
     labels = "Targeted Vadose Sub-Emulator (111.3h, 8/9 Phys, Reg=0.456)",
     cex = 0.74, col = ET_TEAL, font = 2)
text(cf$hpc_node_hours[4] - 5,  cf$regulated_kge[4] + 0.025,
     labels = "Retained 9-Subcomponent Physics (216.3h, 9/9 Phys, Reg=0.507)",
     pos = 2, cex = 0.76, col = ET_PINE_B, font = 2)

# Panel (b): Practical Savings & UQ Ensemble Capacity Breakdown (Sorted by UQ Capacity [Sort Key])
par(mar = c(6.4, 4.8, 3.8, 1.8))
strat_names <- c("1. Unfixed Baseline\n(243.3h | 41 UQ Runs)",
                 "2. Retained Physics\n(216.3h | 46 UQ Runs)",
                 "3. Vadose Sub-Emu\n(111.3h | 89 UQ Runs)",
                 "4. Whole-LSM Emu\n(3.3h | 2,980 UQ Runs)")
hpc_saved_pct <- c(0.0, 11.1, 54.2, 98.5)
conus_kge_pct <- c(84.7, 90.9, 90.7, 90.0)
reg_skill_pct <- c(0.1680 / 0.5072 * 100.0, 100.0, 0.4561 / 0.5072 * 100.0, 0.3865 / 0.5072 * 100.0)

mat_5b <- rbind(hpc_saved_pct, conus_kge_pct, reg_skill_pct)
bp5b <- barplot(
  mat_5b,
  beside = TRUE,
  names.arg = strat_names,
  padj = 0.45,
  col = c(ET_SLATE, ET_PINE, ET_OCHRE),
  border = c(ET_SLATE_B, ET_PINE_B, ET_OCHRE_B),
  ylim = c(0, 125),
  ylab = "Practical Performance & Savings Index (%)",
  main = "(b) Practical Savings & UQ Capacity (Sorted by HPC Saved [Sort Key])",
  cex.names = 0.78,
  cex.axis = 0.88,
  cex.lab = 0.94,
  cex.main = 0.96
)
grid(nx = NA, ny = NULL, col = "#dcd7cd", lty = "dotted")

for (i in 1:4) {
  text(bp5b[1, i], hpc_saved_pct[i] + 3.4, labels = sprintf("%.1f%%", hpc_saved_pct[i]),
       cex = 0.68, col = ET_SLATE_B, font = 2, xpd = TRUE)
  text(bp5b[2, i], conus_kge_pct[i] + 3.4, labels = sprintf("%.1f%%", conus_kge_pct[i]),
       cex = 0.68, col = ET_PINE_B, font = 2, xpd = TRUE)
  text(bp5b[3, i], reg_skill_pct[i] + 3.4, labels = sprintf("%.1f%%", reg_skill_pct[i]),
       cex = 0.68, col = ET_OCHRE_B, font = 1, xpd = TRUE)
}

legend("topleft",
       legend = c("50-Run HPC Cost Savings (%) & Feasible UQ Runs per 10k Node-Hrs [Sort Key]",
                  "CONUS Streamflow Fidelity (Pooled KGE x 100%)",
                  "Regulated Dam Skill Retention (% of Full 9-Module Physical KGE = 0.5072)"),
       fill = c(ET_SLATE, ET_PINE, ET_OCHRE),
       border = c(ET_SLATE_B, ET_PINE_B, ET_OCHRE_B),
       bg = "white", box.col = "#dcd7cd", cex = 0.74)
dev.off()

cat("Generated AGU poster data figures (Figures 3, 4, and 5) in", fig_dir, "\n")
