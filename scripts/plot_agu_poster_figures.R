#!/usr/bin/env Rscript
# =============================================================================
# Complete AGU Poster Data Figure Suite (Figures 3, 4, 5, 6, and 7)
# Combines all visual diagnostics from the initial conference deck into
# high-resolution 200-DPI Cairo PNGs in the Waterology Earth-Tone Palette.
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

# Remove older 5-figure filenames if present so directory stays clean
unlink(file.path(fig_dir, c(
  "fig3_poster_triage_and_process_attribution.png",
  "fig4_poster_physical_process_diagnostics.png",
  "fig5_poster_practical_savings_and_uq_capacity.png"
)))

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

# =============================================================================
# Figure 3: Triage Decoupling & The 12-Step Sub-Component Progression Waterfall
# =============================================================================
png(file.path(fig_dir, "fig3_triage_and_stepwise_progression.png"),
    width = 3300, height = 1320, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

# Panel (a): 9 Sub-Components Ordered by Compute Share [Sort Key]
par(mar = c(5.2, 16.8, 3.8, 2.0))
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
  xlab = "Share of Total Compute Budget (%)  /  Downstream Sensitivity (|dKGE| x 100)",
  main = "(a) Sub-Component Triage: Compute Cost [Sort Key] vs. Sensitivity",
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
       labels = sprintf("%.1f", sens_scaled[i]),
       pos = 4, cex = 0.70, col = ET_OCHRE_B, font = 1, xpd = TRUE)
}
legend(x = 18, y = 16.0,
       legend = c("HPC Compute Share (% of 243.3 Node-Hrs) [Sort Key]",
                  "Downstream Streamflow Sensitivity (|dKGE| x 100)"),
       fill = c(ET_SLATE, ET_OCHRE),
       border = c(ET_SLATE_B, ET_OCHRE_B),
       bg = "white", box.col = "#dcd7cd", cex = 0.74)

# Panel (b): Step-by-Step 12-Stage Progression (Horizontal Bar Waterfall from Initial Figure 2)
par(mar = c(5.2, 16.5, 3.8, 2.2))
st <- d$stages
n_st <- nrow(st)
st_rev <- rev(seq_len(n_st))

friendly_stage <- c(
  "0. Baseline (CLM5 + Tethys 2.1 + MOSART)",
  "1. Satellite Phenology ET (CLM5-SP)",
  "2. ELMv3 Crop LULCC & Snowmelt ET",
  "3. Uncalibrated ELMv3 Infiltration",
  "4. Calibrated Frozen-Soil Infiltration",
  "5. Non-Negative Power-Law Baseflow",
  "6. Unconstrained Neural Vadose Surrogate",
  "7. Tethys 2.2 Canal Loss & GW Shares",
  "8. Power-Plant Cooling Return Ratios",
  "9. Municipal Urban Expansion (<3% Flow)",
  "10. Repair 1,690 Missing Slope Cells",
  "11. Small-Basin Sub-Grid Area Filter",
  "12. Broman Dam Rules & Return Flows"
)[st_rev]

kge_raw <- st$conus_kge[st_rev]
kge_plt <- pmax(kge_raw, 0.04)
st_stat <- st$status[st_rev]
bar_cols <- ifelse(st_stat == "kept", ET_PINE,
            ifelse(st_stat == "vetoed", ET_TERRA,
            ifelse(st_stat == "reverted", ET_OCHRE, ET_SLATE)))
bar_bords <- ifelse(st_stat == "kept", ET_PINE_B,
             ifelse(st_stat == "vetoed", ET_TERRA_B,
             ifelse(st_stat == "reverted", ET_OCHRE_B, ET_SLATE_B)))

bp3b <- barplot(
  kge_plt,
  horiz = TRUE,
  names.arg = friendly_stage,
  las = 1,
  col = bar_cols,
  border = bar_bords,
  xlim = c(0, 1.88),
  ylim = c(-2.6, 15.8),
  xlab = "Pooled CONUS Streamflow Skill (KGE) & Regime Summary",
  main = "(b) 12-Candidate Progression & Physical Guardrail Vetoes",
  cex.names = 0.76,
  cex.axis = 0.88,
  cex.lab = 0.90,
  cex.main = 0.95
)
grid(nx = NULL, ny = NA, col = "#dcd7cd", lty = "dotted")
segments(st$conus_kge[1], 0, st$conus_kge[1], 15.6, col = ET_SLATE_B, lty = 3, lwd = 1.4)

for (i in seq_len(n_st)) {
  idx_orig <- st_rev[i]
  st_row <- st[idx_orig, ]
  badge <- if (st_row$status == "kept") "KEPT"
           else if (st_row$status == "vetoed") "VETOED"
           else if (st_row$status == "reverted") "REVERTED"
           else "BASE"
  detail <- if (idx_orig == 4) {
    sprintf("KGE=%.3f [%s: Drought Q10=+40.0%% > 25%%]", st_row$conus_kge, badge)
  } else if (idx_orig == 7) {
    sprintf("KGE=%.2f [%s: Negative Baseflow -19.8 m3/s]", st_row$conus_kge, badge)
  } else {
    sprintf("KGE=%.4f [%s] | Small=%.3f | Dam=%.3f",
            st_row$conus_kge, badge,
            st_row$median_gauge_kge_small_basins,
            st_row$median_gauge_kge_regulated)
  }
  text(kge_plt[i] + 0.02, bp3b[i], labels = detail, pos = 4, cex = 0.64,
       col = bar_bords[i],
       font = if (st_row$status %in% c("vetoed", "kept") && idx_orig %in% c(4, 7, 12, 13)) 2 else 1,
       xpd = TRUE)
}
legend("bottomright",
       legend = c("KEPT Improvement (8/12)   ",
                  "REVERTED Low-ROI Swap (2/12)   ",
                  "VETOED by Physical Guardrail (2/12)",
                  "Unfixed Baseline Reference"),
       fill = c(ET_PINE, ET_OCHRE, ET_TERRA, ET_SLATE),
       border = c(ET_PINE_B, ET_OCHRE_B, ET_TERRA_B, ET_SLATE_B),
       ncol = 2, bg = "white", box.col = "#dcd7cd", cex = 0.68)
dev.off()

# =============================================================================
# Figure 4: Side-by-Side CONUS Spatial Maps (Baseline Skill vs. Skill Gain dKGE)
# =============================================================================
png(file.path(fig_dir, "fig4_conus_spatial_baseline_vs_gain.png"),
    width = 3300, height = 1240, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

sg <- d$spatial_gauges
pt_pch <- ifelse(sg$cohort == "regulated", 17, 19)

# Panel (a): Baseline KGE Spatial Map Across 1,190 USGS Gauges
par(mar = c(5.2, 4.8, 3.8, 1.5))
kb <- sg$kge_base
cols_base <- ifelse(kb < 0.00, ET_TERRA_B,
             ifelse(kb < 0.25, ET_OCHRE,
             ifelse(kb < 0.50, ET_GOLD,
             ifelse(kb < 0.70, ET_SAGE, ET_SLATE_B))))

plot(sg$lon, sg$lat, type = "n", xlim = c(-125.5, -66.5), ylim = c(25.0, 49.8),
     xlab = "Longitude (deg W)", ylab = "Latitude (deg N)",
     main = "(a) Baseline Streamflow Skill Across 1,190 Gauges (Small Med=0.013, Dam Med=0.168)",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.95)
rect(par("usr")[1], par("usr")[3], par("usr")[2], par("usr")[4], col = "white", border = ET_STONE)
grid(nx = 6, ny = 5, col = "#dcd7cd", lty = "dotted")
points(sg$lon, sg$lat, col = adjustcolor(cols_base, alpha.f = 0.85), pch = pt_pch, cex = 0.95)

legend("bottomleft",
       legend = c("KGE < 0.00 (Severe Error: Western Dams & Headwaters)",
                  "0.00 <= KGE < 0.25 (Poor Skill)",
                  "0.25 <= KGE < 0.50 (Moderate Skill)",
                  "0.50 <= KGE < 0.70 (Good Skill)",
                  "KGE >= 0.70 (High Skill: Large Humid Rivers)",
                  "Circles = 672 Natural Gauges | Triangles = 518 Regulated Dams"),
       col = c(ET_TERRA_B, ET_OCHRE, ET_GOLD, ET_SAGE, ET_SLATE_B, ET_CHARCOAL),
       pch = c(15, 15, 15, 15, 15, 17),
       bg = "white", box.col = "#dcd7cd", cex = 0.70)

# Panel (b): Streamflow Skill Gain (dKGE = Repaired 9-Module Chain - Baseline)
par(mar = c(5.2, 4.8, 3.8, 1.8))
dk <- sg$delta_kge
cols_gain <- ifelse(dk >= 0.25, ET_PINE_B,
             ifelse(dk >= 0.08, ET_PINE,
             ifelse(dk >= 0.00, ET_SAGE,
             ifelse(dk >= -0.03, ET_STONE, ET_TERRA))))

plot(sg$lon, sg$lat, type = "n", xlim = c(-125.5, -66.5), ylim = c(25.0, 49.8),
     xlab = "Longitude (deg W)", ylab = "Latitude (deg N)",
     main = "(b) Streamflow Skill Gain dKGE After Internal Repairs (82.8% All, 96.5% Dams Improved)",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.95)
rect(par("usr")[1], par("usr")[3], par("usr")[2], par("usr")[4], col = "white", border = ET_STONE)
grid(nx = 6, ny = 5, col = "#dcd7cd", lty = "dotted")
points(sg$lon, sg$lat, col = adjustcolor(cols_gain, alpha.f = 0.86), pch = pt_pch, cex = 0.95)

legend("bottomleft",
       legend = c("dKGE >= +0.25 (Large Gain: Western Dams & Headwaters)",
                  "+0.08 <= dKGE < +0.25 (Moderate Gain)",
                  "0.00 <= dKGE < +0.08 (Slight Gain)",
                  "dKGE < 0.00 (17.2% of Gauges)",
                  "Small Headwaters (<=4 Cells, n=446): Med KGE 0.013 -> 0.337 (+2,600%)",
                  "Regulated Dam Gauges (n=518): Med KGE 0.168 -> 0.507 (+202%)"),
       col = c(ET_PINE_B, ET_PINE, ET_SAGE, ET_TERRA, ET_CHARCOAL, ET_CHARCOAL),
       pch = c(15, 15, 15, 15, 19, 17),
       bg = "white", box.col = "#dcd7cd", cex = 0.70)
dev.off()

# =============================================================================
# Figure 5: Headwater Grid-Quantization Bins & Regulated Seasonal Hydrograph
# =============================================================================
png(file.path(fig_dir, "fig5_headwater_grid_and_regulated_hydrograph.png"),
    width = 3300, height = 1240, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

# Panel (a): Natural Streamflow Skill by Basin Grid-Cell Count (672 HCDN Gauges)
par(mar = c(5.8, 4.8, 3.8, 1.5))
bins <- d$basin_size_bins
mat_bins <- rbind(bins$base_kge_median, bins$final_kge_median)
short_bins <- c("1 Cell\n(<150 km2\nn=146)",
                "2 Cells\n(150-300\nn=140)",
                "3-4 Cells\n(300-600\nn=160)",
                "5-8 Cells\n(600-1.2k\nn=115)",
                "9-15 Cells\n(1.2k-2.5k\nn=61)",
                ">15 Cells\n(>2.5k km2\nn=50)")
bp5a <- barplot(
  mat_bins,
  beside = TRUE,
  names.arg = short_bins,
  col = c(ET_STONE, ET_SLATE),
  border = c(ET_CHARCOAL, ET_SLATE_B),
  ylim = c(-0.15, 0.72),
  ylab = "Median Natural Gauge KGE (with 75th Percentile Whisker)",
  main = "(a) Why Small Headwaters Fail: 0.125-Deg Grid Area Rounding by Cell Count",
  cex.names = 0.76,
  cex.axis = 0.88,
  cex.lab = 0.94,
  cex.main = 0.96
)
grid(nx = NA, ny = NULL, col = "#dcd7cd", lty = "dotted")
abline(h = 0, col = ET_CHARCOAL, lty = 2)

arrows(bp5a[1, ], pmax(bins$base_kge_median, 0), bp5a[1, ], bins$base_kge_q75,
       angle = 90, code = 2, length = 0.04, col = ET_CHARCOAL, lwd = 1.4)
arrows(bp5a[2, ], pmax(bins$final_kge_median, 0), bp5a[2, ], bins$final_kge_q75,
       angle = 90, code = 2, length = 0.04, col = ET_SLATE_B, lwd = 1.6)

for (i in seq_len(nrow(bins))) {
  yb <- bins$base_kge_q75[i] + 0.025
  yf <- bins$final_kge_q75[i] + 0.025
  text(bp5a[1, i], yb, labels = sprintf("%.2f", bins$base_kge_median[i]),
       cex = 0.68, col = ET_CHARCOAL)
  text(bp5a[2, i], yf, labels = sprintf("%.2f", bins$final_kge_median[i]),
       cex = 0.72, col = ET_SLATE_B, font = 2)
}
legend("topright",
       legend = c("Unfixed Gridded MOSART + CLM5 (<=4-Cell Med KGE = 0.0125)",
                  "Sub-Grid Area-Filtered Routing + ELMv3 (<=4-Cell Med KGE = 0.3374, +2,600%)"),
       fill = c(ET_STONE, ET_SLATE),
       border = c(ET_CHARCOAL, ET_SLATE_B),
       bg = "white", box.col = "#dcd7cd", cex = 0.74)

# Panel (b): Regulated Dam 12-Month Discharge Climatology + Veto Canary
par(mar = c(5.8, 4.8, 3.8, 1.8))
clim <- d$regulated_monthly_climatology
m_x <- clim$month_index

plot(m_x, clim$obs_median_m3s, type = "n", ylim = c(-78, 178), xlim = c(1, 12),
     xaxt = "n", xlab = "Calendar Month (1981-2015 Climatology Across 518 Regulated Dam Gauges)",
     ylab = "Regulated River Discharge / Subsurface Flux (m3/s)",
     main = "(b) Regulated Dam Seasonal Hydrograph & Non-Negative Physical Veto Zone",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.96)
rect(par("usr")[1], -78, par("usr")[2], 0, col = adjustcolor(ET_TERRA, alpha.f = 0.16), border = NA)
grid(nx = NULL, ny = NULL, col = "#dcd7cd", lty = "dotted")
abline(h = 0, col = ET_TERRA_B, lty = 2, lwd = 2)
axis(1, at = 1:12, labels = clim$month, cex.axis = 0.86)

lines(m_x, clim$obs_median_m3s,         col = ET_CHARCOAL, lwd = 3.2, type = "b", pch = 19)
lines(m_x, clim$final_median_m3s,       col = ET_PINE,     lwd = 3.0, type = "b", pch = 17)
lines(m_x, clim$base_median_m3s,        col = ET_OCHRE,    lwd = 2.5, type = "b", pch = 15, lty = 2)
lines(m_x, clim$veto_drought_p15_m3s,   col = ET_TERRA,    lwd = 2.6, type = "b", pch = 13, lty = 3)

text(6.5, -16,
     labels = "PHYSICAL VETO ZONE (Q < 0 m3/s): Unconstrained Neural Surrogate Predicts Upward Suction (-66.2 m3/s in Sep)",
     col = ET_TERRA_B, font = 2, cex = 0.72)

legend("topleft",
       legend = c("USGS Observed Regulated Flow (518 Pre-1980 Dam Gauges)",
                  "Repaired 9-Module Chain (Broman Rules + Return Flow, Med KGE = 0.5072)",
                  "Unfixed Baseline Chain (Corrupted Dam Floors + No Return Flow, Med KGE = 0.1680)",
                  "Vetoed Unconstrained Neural Vadose Surrogate (15th Pct Drought Flux < 0)"),
       col = c(ET_CHARCOAL, ET_PINE, ET_OCHRE, ET_TERRA),
       lwd = c(3.2, 3.0, 2.5, 2.6),
       pch = c(19, 17, 15, 13),
       lty = c(1, 1, 2, 3),
       bg = "white", box.col = "#dcd7cd", cex = 0.72)
dev.off()

# =============================================================================
# Figure 6: Inside Tethys Sectoral Return Flows & 35-Year Water-Scarcity Deficit
# =============================================================================
png(file.path(fig_dir, "fig6_sectoral_return_flows_and_water_scarcity.png"),
    width = 3300, height = 1260, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

# Panel (a): Sectoral Consumed Water vs. Returned Water (Stacked Horizontal Bar Chart from Initial Figure 5)
par(mar = c(5.5, 14.2, 3.8, 2.0))
swb <- d$sectoral_water_balance
swb_rev <- rev(seq_len(nrow(swb)))
sec_labels <- swb$short_label[swb_rev]
mat_sec <- rbind(swb$consumed_km3_yr[swb_rev], swb$returned_km3_yr[swb_rev])

bp6a <- barplot(
  mat_sec,
  beside = FALSE,
  horiz = TRUE,
  names.arg = sec_labels,
  las = 1,
  col = c(ET_SLATE_B, ET_SAGE),
  border = c(ET_CHARCOAL, ET_PINE_B),
  xlim = c(0, 240),
  ylim = c(-1.1, 5.4),
  xlab = "Mean Annual Basin Water Volume (km3/yr: Consumed vs. Returned to River)",
  main = "(a) Tethys Sectoral Water Balance: Consumed vs. Returned Flow",
  cex.names = 0.78,
  cex.axis = 0.88,
  cex.lab = 0.90,
  cex.main = 0.96
)
grid(nx = NULL, ny = NA, col = "#dcd7cd", lty = "dotted")

for (i in seq_len(length(bp6a))) {
  idx_o <- swb_rev[i]
  r_row <- swb[idx_o, ]
  tot_w <- r_row$withdrawal_km3_yr
  lbl <- if (idx_o == 1) {
    sprintf("WD: %.1f km3/yr\n(%.1f Consumed | %.1f Returned, %.0f%%)",
            tot_w, r_row$consumed_km3_yr, r_row$returned_km3_yr, r_row$return_fraction_pct)
  } else {
    sprintf("WD: %.1f | Consumed: %.1f | Returned: %.1f km3/yr (%.0f%% Return)",
            tot_w, r_row$consumed_km3_yr, r_row$returned_km3_yr, r_row$return_fraction_pct)
  }
  text(tot_w + 2.5, bp6a[i], labels = lbl, pos = 4, cex = 0.66,
       col = ET_CHARCOAL, font = if (idx_o %in% c(1, 3)) 2 else 1, xpd = TRUE)
}

# Inset Audit Banner for GRanD Reservoir release_min (Issue I-22) at bottom of Panel (a)
rect(2, -0.95, 232, -0.05, col = "#fdf2f0", border = ET_TERRA, lwd = 1.4)
text(5, -0.32,
     labels = "GRanD Dam Audit: 1,847 / 1,863 baseline dams had NEGATIVE release_min (down to -7.9 m3/s).",
     pos = 4, cex = 0.62, col = ET_TERRA_B, font = 2, xpd = TRUE)
text(5, -0.70,
     labels = "Repaired Broman 9505v4 enforces release_min >= 0.0 m3/s across all 1,863 dams (0 negative).",
     pos = 4, cex = 0.62, col = ET_PINE_B, font = 2, xpd = TRUE)

legend("topright",
       legend = c("Consumed Water (Evaporated / Transpired: Permanently Removed)",
                  "Returned Water (Withdrawal - Consumption: Re-Enters River Reach)"),
       fill = c(ET_SLATE_B, ET_SAGE),
       border = c(ET_CHARCOAL, ET_PINE_B),
       bg = "white", box.col = "#dcd7cd", cex = 0.72)

# Panel (b): 35-Year Annual CONUS Unmet Water Demand Reduction (1981-2015)
par(mar = c(5.5, 4.8, 3.8, 1.8))
ud <- d$annual_unmet_demand
yrs <- ud$year

plot(yrs, ud$baseline_km3_yr, type = "n", ylim = c(0, 86), xlim = c(1981, 2015),
     xlab = "Simulation Year (1981-2015 Historical Evaluation Window)",
     ylab = "CONUS Annual Unmet Water Demand Deficit (km3/yr)",
     main = "(b) 35-Year CONUS Unmet Water Demand: -86.2% False Scarcity Removed",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.96)
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
       legend = c(sprintf("Unfixed Baseline (Tethys 2.1 + No Return Flow): Mean = %.2f km3/yr", mean(ud$baseline_km3_yr)),
                  sprintf("Step 1: Tethys 2.2 Canal Efficiency (0.83) Fix Only: Mean = %.2f km3/yr (-23.9%%)", mean(ud$tethys_m2_canal_fix_km3_yr)),
                  sprintf("Step 2: + Return Flows & Non-Negative Dam Releases: Mean = %.2f km3/yr (-86.2%%)", mean(ud$retained_9subcomponent_km3_yr))),
       col = c(ET_TERRA, ET_SLATE, ET_PINE),
       lwd = c(2.8, 2.4, 3.0),
       lty = c(1, 2, 1),
       bg = "white", box.col = "#dcd7cd", cex = 0.73)
dev.off()

# =============================================================================
# Figure 7: Pareto Cost-Accuracy Frontier & Cumulative Campaign / UQ Capacity
# =============================================================================
png(file.path(fig_dir, "fig7_emulator_comparison_pareto_and_uq_savings.png"),
    width = 3300, height = 1240, res = 200, type = "cairo")
par(mfrow = c(1, 2), bg = "white", col.axis = ET_CHARCOAL, col.lab = ET_CHARCOAL,
    col.main = ET_CHARCOAL, family = "sans")

# Panel (a): HPC Cost vs Regulated Dam Skill & Retained Physical Process Modules
par(mar = c(5.2, 4.8, 3.8, 1.5))
cf <- d$cross_family_comparison
plot(c(0, 265), c(0.06, 0.56), type = "n",
     xlab = "Single-Run Computational Cost (NERSC HPC Node-Hours per 35-Yr CONUS Run)",
     ylab = "Regulated Dam Streamflow Skill (Median KGE Across 518 Gauges)",
     main = "(a) Cost-Accuracy Pareto Frontier: Process Fixes vs. Targeted & Whole Emulators",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.96)
grid(nx = NULL, ny = NULL, col = "#dcd7cd", lty = "dotted")

rect(0, 0.07, 128, 0.155, col = adjustcolor(ET_TERRA, alpha.f = 0.15), border = ET_TERRA)
text(64, 0.134, labels = "Fast but Scientifically Broken Trap", col = ET_TERRA_B, font = 2, cex = 0.75)

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
     labels = "Blind Whole-LSM Emulator (3.3h, Reg KGE=0.106, Small=0.004)", pos = 4, cex = 0.72, col = ET_TERRA_B, font = 2)
text(cf$hpc_node_hours[7] - 4,  cf$regulated_kge[7] - 0.032,
     labels = "0. Unfixed Baseline (243.3h, 9/9 Phys, Reg=0.168)", pos = 2, cex = 0.72, col = ET_CHARCOAL)
text(cf$hpc_node_hours[6] + 6,  cf$regulated_kge[6] - 0.018,
     labels = "Last-Resort Whole-LSM Emulator After Fixes (3.3h, 6/9 Phys, Reg=0.387)",
     pos = 4, cex = 0.72, col = ET_SLATE_B, font = 2)
text(cf$hpc_node_hours[5] - 18, cf$regulated_kge[5] + 0.028,
     labels = "Targeted Vadose Sub-Emulator (111.3h, 8/9 Phys, Reg=0.456)",
     cex = 0.74, col = ET_TEAL, font = 2)
text(cf$hpc_node_hours[4] - 5,  cf$regulated_kge[4] + 0.025,
     labels = "Full 9-Module Repaired Physics (216.3h, 9/9 Phys, Reg=0.507)",
     pos = 2, cex = 0.75, col = ET_PINE_B, font = 2)

# Panel (b): Cumulative Campaign HPC Cost Across Ensemble Size (N = 1..50 Runs) & UQ Capacity
par(mar = c(5.2, 4.8, 3.8, 1.8))
cb <- d$campaign_breakeven
n_seq <- 1:50
c_base_seq <- 243.3 * n_seq
c_phys_seq <- 216.3 * n_seq
c_vad_seq  <- 8.0 + 111.3 * n_seq
c_last_seq <- 15.0 + 3.3 * n_seq

plot(n_seq, c_base_seq / 1000.0, type = "n", ylim = c(0, 13.4), xlim = c(1, 50),
     xlab = "Number of 35-Year IM3 Scenario / UQ Ensemble Evaluations (N)",
     ylab = "Cumulative Campaign Compute Cost (Thousand NERSC Node-Hours)",
     main = "(b) Multi-Scenario Campaign Cost (N = 1..50) & UQ Capacity per 10k Node-Hrs",
     cex.axis = 0.88, cex.lab = 0.94, cex.main = 0.96)
grid(nx = NULL, ny = NULL, col = "#dcd7cd", lty = "dotted")

lines(n_seq, c_base_seq / 1000.0, col = ET_STONE, lwd = 2.5, lty = 2)
lines(n_seq, c_phys_seq / 1000.0, col = ET_PINE,  lwd = 3.0)
lines(n_seq, c_vad_seq  / 1000.0, col = ET_TEAL,  lwd = 3.0)
lines(n_seq, c_last_seq / 1000.0, col = ET_SLATE, lwd = 3.0)

points(cb$n_runs, cb$retained_physics_hpc_hours / 1000.0, col = ET_PINE,  pch = 19, cex = 1.0)
points(cb$n_runs, cb$targeted_vadose_emulator_hpc_hours / 1000.0, col = ET_TEAL, pch = 17, cex = 1.0)
points(cb$n_runs, cb$last_resort_whole_lsm_emulator_hpc_hours / 1000.0, col = ET_SLATE, pch = 15, cex = 1.0)

# Callout annotations at N=50 right edge
text(49, 11.4, labels = "-1,350h Saved", col = ET_PINE_B, font = 2, cex = 0.72, pos = 2)
text(49, 6.2,  labels = "-6,592h Saved (2.2x UQ Runs)", col = ET_TEAL, font = 2, cex = 0.74, pos = 2)
text(49, 0.85, labels = "-11,985h Saved (72.7x UQ Runs)", col = ET_SLATE_B, font = 2, cex = 0.74, pos = 2)

legend("topleft",
       legend = c("Unfixed Baseline (243.3h/run): 12,165h at N=50  |  41 UQ Runs per 10k Node-Hrs",
                  "Repaired 9-Module Physics (216.3h/run): 10,815h at N=50 (-11.1%)  |  46 UQ Runs per 10k Hrs",
                  "Targeted Vadose Sub-Emulator (8h + 111.3h/run): 5,573h at N=50 (-54.2%)  |  89 UQ Runs (2.2x)",
                  "Last-Resort Whole-LSM Emulator (15h + 3.3h/run): 180h at N=50 (-98.5%)  |  2,980 UQ Runs (72.7x)"),
       col = c(ET_STONE, ET_PINE, ET_TEAL, ET_SLATE),
       lwd = c(2.5, 3.0, 3.0, 3.0),
       lty = c(2, 1, 1, 1),
       pch = c(NA, 19, 17, 15),
       bg = "white", box.col = "#dcd7cd", cex = 0.71)
dev.off()

cat("Generated complete 5-data-figure AGU poster suite (Figures 3..7) in", fig_dir, "\n")
