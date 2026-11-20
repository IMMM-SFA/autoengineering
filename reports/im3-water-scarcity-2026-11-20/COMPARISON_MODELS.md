# Mathematical and Architectural Reference: DOE IM3 Sub-Components and Emulator Benchmarks (`COMPARISON_MODELS.md`)

**Companion to:** [`IM3_WATER_SCARCITY_REPORT.md`](./IM3_WATER_SCARCITY_REPORT.md) (`im3-water-scarcity-2026-11-20`)  
**Implementation Source:** [`../../examples/im3_water_scarcity/run_workflow.py`](../../examples/im3_water_scarcity/run_workflow.py), [`../../examples/im3_water_scarcity/system.yaml`](../../examples/im3_water_scarcity/system.yaml), and [`../../examples/im3_water_scarcity/candidates.yaml`](../../examples/im3_water_scarcity/candidates.yaml)

---

## 1. Decomposing the 3 IM3 Macro-Models into 9 Internal Physical Sub-Components

Rather than treating `CLM5/ELMv3`, `Tethys`, and `mosartwmpy` as monolithic black boxes, the Autoengineering 2.0 DAG decomposes the CONUS water-scarcity chain into **9 connected internal sub-components** evaluated across **1,190 USGS 70/70 monthly stream gauges** (`1981-01` to `2015-12`, $T = 420$ months; $N_{\text{nat}} = 672$ HCDN natural gauges and $N_{\text{reg}} = 518$ regulated pre-1980 `GRanD` dam gauges).

### 1.1 `CLM5 / ELMv3` Land Surface Hydrology (`240.0` NERSC Node-Hours/Run)

1. **`lsm_canopy_snow_et` (`68.0` Node-Hours/Run, 28.0% of Total HPC):**
   - **Baseline (`clm5_bgc_crop_luh2_canopy_snow`):** `CLM5-BGC-Crop` prognostic leaf area index (LAI) with `LUH2` land-use forcing, default leaf-wetted fraction $f_{\text{wet}}$, and snowpack shape factor $n_{\text{melt\_coef}}$.
   - **Candidate 1 (`clmsp_satellite_phenology_et`, 24.0h, Reverted):** Prescribed MODIS satellite phenology (`CLM5-SP` `dMAE`), which bypasses prognostic carbon/nitrogen allocation (`-44.0` node-hours/run) but suppresses interannual drought canopy shedding in western snowmelt headwaters.
   - **Candidate 2 (`elm_demeter_canopy_snow_et`, 62.0h, Kept):** `ELMv3-BGC-Crop` forced by GCAM-Demeter crop LULCC with Latin Hypercube Sample (`LHS-1500`) calibrated leaf-wetted fraction $f_{\text{wet}}$, sublimation resistance, and snowmelt shape factor $n_{\text{melt\_coef}}$ (calibrated on `1981-1999`, validated on `2000-2015`).

2. **`lsm_surface_infiltration` (`52.0` Node-Hours/Run, 21.4% of Total HPC):**
   - **Baseline (`clm5_default_fover_infiltration`):** Saturation-excess (TOPMODEL $f_{\text{over}} = 0.5\text{ m}^{-1}$) and infiltration-excess overland flow ($Q_{\text{OVER}} + Q_{\text{H2OSFC}}$).
   - **Candidate 3 (`elmv3_uncalibrated_infiltration`, 46.0h, Vetoed):** Out-of-the-box `ELMv3` surface infiltration (`20260831` default `clm_params_c251006.nc`), which increases CONUS mean $Q_{\text{OVER}}$ by $+35\%$ ($0.190 \rightarrow 0.256\text{ mm/d}$) and pushes low-flow drought bias to $\text{Q10\_PBIAS} = +39.96\% > 25.0\%$.
   - **Candidate 4 (`modified_infil_fover_calibrated`, 46.0h, Kept):** `ELMv3` modified frozen-soil ice-impedance infiltration (`modified_infil_True`) paired with `LHS-1500` calibrated TOPMODEL decay $f_{\text{over}}$ and micro-topographic surface water storage $d_{\text{max}}$.

3. **`lsm_subsurface_drainage` (`120.0` Node-Hours/Run, 49.3% of Total HPC):**
   - **Baseline (`clm5_richards_linear_baseflow`):** 20-layer nonlinear Richards vadose moisture solver coupled to perched water table drainage ($Q_{\text{DRAI\_PERCH}}$) and unconfined aquifer baseflow ($Q_{\text{DRAI}}$). Exhibits **124 negative $Q_{\text{DRAI}}$ cell-months** (minimum $-1.94\times 10^{-5}\text{ mm/s}$, Issue `I-25`) where the bottom aquifer boundary extracts upward suction during drought.
   - **Candidate 5 (`calibrated_nonlinear_baseflow_aquifer`, 105.0h, Kept):** `ELMv3` non-negative power-law aquifer drainage ($Q_{\text{DRAI}} = K_{\text{bf}} S^{\,N_{\text{bf}}} \ge 0$) with `LHS-1500` calibrated $K_{\text{bf}}$, $N_{\text{bf}}$, specific yield $S_y$, and hydraulic conductivity scale factor $\text{hksat\_sf}$, eliminating all 124 negative drainage anomalies.
   - **Candidate 6 (`unconstrained_neural_vadose_emulator`, 0.05h, Vetoed):** Unconstrained multi-layer perceptron trained on monthly total moisture without a non-negativity output activation; predicts negative baseflow ($Q_{\text{DRAI}} = -19.8\text{ m}^3/\text{s}$ across drought basins) and is vetoed by `PhysicalCheck("nonnegative_runoff_and_baseflow")`.

---

### 1.2 `Tethys` Sectoral Water-Demand Downscaling (`0.8` NERSC Node-Hours/Run)

4. **`tethys_irrigation_downscaler` (`0.45` Node-Hours/Run, 0.2% of Total HPC):**
   - **Baseline (`tethys_v210_unadjusted_irrigation`):** `Tethys 2.1.0` agricultural irrigation withdrawal and consumption downscaler (`demand_optimized_gw_shares.nc`), which omitted the `0.829937` canal conveyance efficiency factor (Issue `I-07`/`I-10`, causing $+17.0\%$ irrigation over-withdrawal) and left 1985, 1995, and 2000 share matrices unpopulated (Issue `I-11`).
   - **Candidate 7 (`tethys_m2_usgs_canal_loss`, 0.45h, Kept):** `Tethys 2.2.0` irrigation downscaler (`demand_kazi_clean_2026.nc`) incorporating the `0.829937` canal conveyance factor (`I-07`), all 6 populated USGS benchmark years (`1985-2010`, `I-11`), and Method 2 USGS surface-water vs. groundwater source shares (`I-13`).

5. **`tethys_thermoelectric_industrial_downscaler` (`0.20` Node-Hours/Run, 0.1% of Total HPC):**
   - **Baseline (`tethys_v210_thermoelectric_ind`):** `Tethys 2.1.0` power-plant cooling and industrial (`mfg`, `min`, `liv`) demand downscaler prior to `0-LMP` CERF cooling-technology siting reconciliation.
   - **Candidate 8 (`cerf_0lmp_thermoelectric_downscaler`, 0.20h, Kept):** Rebuilt `Tethys 2.2.0` thermoelectric and industrial downscaler aligned with `0-LMP` CERF power-plant cooling technology mixes (separating high-withdrawal/high-return once-through cooling from high-consumption recirculating towers, Issues `I-08`/`I-09`).

6. **`tethys_municipal_domestic_downscaler` (`0.15` Node-Hours/Run, 0.1% of Total HPC):**
   - **Baseline (`tethys_v210_static_municipal`):** Static urban/rural population density downscaling for domestic and municipal water deliveries.
   - **Candidate 9 (`transient_urban_municipal_downscaler`, 0.15h, Reverted):** Transient decadal urban population expansion mask (`I-30`) with temperature-modulated seasonal lawn consumption. Reverted (`✗`) by `auto_improve` because municipal withdrawals represent $<3\%$ of total basin flow ($\Delta\text{KGE} = 0.0000$), illustrating how the workflow identifies low-ROI sub-components where engineering resources should *not* be spent.

---

### 1.3 `mosartwmpy` River Routing and Water Management (`2.5` NERSC Node-Hours/Run)

7. **`mosart_hillslope_tributary_routing` (`0.70` Node-Hours/Run, 0.3% of Total HPC):**
   - **Baseline (`mosart_default_grid_hillslope`):** Kinematic-wave overland hillslope routing ($Q_{\text{OVER}}$) and sub-grid tributary routing ($Q_{\text{DRAI}}$) on `mosart_conus_nldas_grid.nc`, which contains **987 land cells with `hslp = NaN`** and **703 land cells with `rslp = NaN`** (Issue `I-23`).
   - **Candidate 10 (`slope_repaired_hillslope_routing`, 0.70h, Kept):** Imputes a physical minimum topographic slope floor ($\max(\text{hslp}, 10^{-4})$, $\max(\text{rslp}, 10^{-4})$) across all 1,690 NaN-slope land cells and reconciles sub-network travel times.

8. **`mosart_channel_network_routing` (`0.90` Node-Hours/Run, 0.4% of Total HPC):**
   - **Baseline (`mosart_gridded_0125deg_channel`):** Standard $0.125^\circ$ NLDAS2 8-direction mainstem kinematic/diffusion-wave channel routing without sub-grid drainage-area reconciliation or the `#129` (`a69c2a7`) monthly discharge aggregation patch (Issue `I-01`). In headwater catchments spanning $\le 4$ grid cells ($<600\text{ km}^2$, $n = 446$ natural gauges), $0.125^\circ$ grid-cell quantization introduces $\pm 50\text{--}200\%$ drainage-area mismatch or snaps gauges onto adjacent mainstem reaches (`Med KGE = 0.0125`).
   - **Candidate 11 (`subgrid_area_filtered_channel_routing`, 0.90h, Kept):** Sub-grid area-ratio reconciliation (`IM3 Hybrid` selector routing headwater gauges $\le 4$ cells via exact polygon-area-weighted catchment flux while routing multi-cell mainstems $>4$ cells through the `#129`-patched channel solver), lifting small-basin median KGE by **$+2,600\%$** (`0.0125 -> 0.3374`).

9. **`mosart_reservoir_demand_wm` (`0.90` Node-Hours/Run, 0.4% of Total HPC):**
   - **Baseline (`wm_20230629_withdrawal_extraction`):** `mosartwmpy` water management parameterized with `grand_reservoir_parameters_20230629.nc` (where **1,847 of 1,863 CONUS dams have negative `release_min`** down to $-7.89\text{ m}^3/\text{s}$, Issue `I-22`), extracting $100\%$ of total withdrawal (`irrigation_withdrawal + nonirrigation_withdrawal`) without crediting non-consumptive return flows (Issue `I-20`).
   - **Candidate 12 (`broman_rules_plus_return_flow_wm`, 0.90h, Kept):** Combines (i) Broman observed-storage rule curves (`grand_reservoir_parameters_hybrid_9505v4.nc`), (ii) a hard non-negative minimum release floor ($\text{release\_min} \ge 0$, `I-22`), (iii) the `wmpy_irrigation_first_mask.nc` priority rule (`I-21`), and (iv) return-flow routing ($R_t = W_t - C_t$, `I-20`), lifting regulated dam median KGE by **$+202\%$** (`0.1680 -> 0.5072`) and cutting CONUS unmet water demand by **$-86.2\%$** (`43.16 -> 5.97 km3/yr`).

---

## 2. AI Emulator Comparison Points and Last-Resort Architectures

1. **Benchmark A - Blind Whole-LSM Emulator Without Downstream Fixes (`3.3` Node-Hours/Run):**
   - Replaces all 3 `CLM5/ELMv3` sub-components (`240.0` node-hours $\rightarrow 0.05$ node-hours) with a truncated-SVD + Fourier-harmonic ridge surrogate ($\log(1 + Q)$ space, trained on `1981-1999`), but feeds the emulated runoff into **unfixed** `Tethys 2.1.0` and **unfixed** `mosartwmpy`.
   - **Scientific Takeaway:** Achieves a $73\times$ compute speedup (`243.3h -> 3.3h`), yet regulated dam skill collapses (`Med KGE = 0.1059`) and small-basin headwater skill remains near zero (`Med KGE = 0.0044`). Upstream black-box emulation cannot fix downstream structural bugs.
2. **Benchmark B - Targeted Vadose Sub-Component Emulator After Internal Fixes (`111.3` Node-Hours/Run):**
   - Emulates **only** the 20-layer nonlinear Richards vadose solver (`lsm_subsurface_drainage`: `120.0h -> 0.05h`, $8.0\text{h}$ training overhead) using a strictly non-negative $\log(1 + Q_{\text{DRAI}})$ surrogate, while keeping `lsm_canopy_snow_et` (`62.0h`), `lsm_surface_infiltration` (`46.0h`), `Tethys 2.2.0` (`0.8h`), and `mosartwmpy` (`2.5h`) **100% physical**.
   - **Scientific Takeaway:** Preserves $99.7\%$ of full physical CONUS skill (`KGE = 0.9067` vs. `0.9094`) and $90.0\%$ of regulated dam skill (`Med KGE = 0.4561` vs. `0.5072`) while cutting total chain compute by **$-54.2\%$** (`243.3h -> 111.3h`).
3. **Benchmark C - Last-Resort Whole-LSM Emulator After Internal Fixes (`3.3` Node-Hours/Run):**
   - Replaces all 3 `CLM5/ELMv3` sub-components (`240.0h -> 0.05h`, $15.0\text{h}$ training overhead) **after** all internal `Tethys 2.2.0` and `mosartwmpy` (`#129` + Broman `9505v4` + return flow) fixes are in place.
   - **Scientific Takeaway:** Provides a $73\times$ speedup (`3.3h/run`, $-98.5\%$ HPC at $N = 50$ runs) while retaining `CONUS KGE = 0.8997`, `Small-Basin Med KGE = 0.2731`, and `Regulated Dam Med KGE = 0.3865` for large 1,000-member GCAM-WRF scenario ensembles.
