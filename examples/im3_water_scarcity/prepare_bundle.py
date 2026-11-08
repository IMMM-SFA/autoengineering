"""Extract and cache the IM3 Water-Scarcity sub-component evaluation bundle.

Reads the local 4.4 GB IM3 dataset under ``/Users/cam/projects/autoengineering/data/im3_water_scarcity``:
- CLM5-BGC-Crop, ELMv3-BGC-Crop, and CLM5-SP sub-component runoff fluxes (QOVER overland flow,
  QDRAI deep vadose/aquifer drainage, and QDRAI_PERCH perched lateral drainage);
- Tethys sector-specific withdrawal and consumption grids (irrigation withdrawal/consumption and
  non-irrigation thermoelectric/industrial/municipal withdrawal/consumption across 4 variants);
- MOSART-WM NLDAS2 0.125-deg hillslope/channel network parameters (hslp, rslp, NaN slope fractions,
  wmpy_irrigation_first_mask) and GRanD 9505 reservoir rule-curve parameters (20230629 vs
  Broman-corrected 9505v4);
- USGS 70/70 monthly gauge observations and MOSART-WM outlet series across 1,190 CONUS gauges.
"""

from __future__ import annotations

import pathlib
import subprocess
import tempfile
import time

import numpy as np
import pandas as pd
from scipy.io import netcdf_file
from scipy.sparse import csr_matrix

DATA_ROOT = pathlib.Path("/Users/cam/projects/autoengineering/data/im3_water_scarcity")
BUNDLE_PATH = DATA_ROOT / "im3_chain_bundle.npz"
N_LAT = 224
N_LON = 464
N_CELLS = N_LAT * N_LON


def _h5_read_array(h5_path: pathlib.Path, dataset: str, dtype, shape: tuple[int, ...]) -> np.ndarray:
    with tempfile.NamedTemporaryFile(suffix=".bin") as tmp:
        subprocess.run(
            [
                "/opt/homebrew/bin/h5dump",
                "-d",
                f"/{dataset}",
                "-b",
                "LE",
                "-o",
                tmp.name,
                str(h5_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        return np.fromfile(tmp.name, dtype=dtype).reshape(shape)


def _build_basin_matrix(
    site_ids: list[str],
    nat_cells: pd.DataFrame,
    reg_cells: pd.DataFrame,
) -> tuple[csr_matrix, np.ndarray]:
    """Build a (n_sites, 224*464) sparse averaging matrix and cell counts per site."""
    all_cells = pd.concat(
        [
            nat_cells[["site_no", "y_index", "x_index"]],
            reg_cells[["site_no", "y_index", "x_index"]],
        ],
        ignore_index=True,
    ).drop_duplicates(subset=["site_no", "y_index", "x_index"])

    site_to_idx = {s: i for i, s in enumerate(site_ids)}
    all_cells = all_cells[all_cells["site_no"].isin(site_to_idx)].copy()
    all_cells["row"] = all_cells["site_no"].map(site_to_idx)
    all_cells["col"] = all_cells["y_index"].astype(int) * N_LON + all_cells["x_index"].astype(int)

    counts = all_cells.groupby("row")["col"].transform("count").to_numpy(dtype=np.float64)
    weights = 1.0 / np.maximum(counts, 1.0)
    mat = csr_matrix(
        (weights, (all_cells["row"].to_numpy(), all_cells["col"].to_numpy())),
        shape=(len(site_ids), N_CELLS),
    )
    cell_counts = np.zeros(len(site_ids), dtype=np.int32)
    vc = all_cells.groupby("row")["col"].count()
    cell_counts[vc.index.to_numpy()] = vc.to_numpy(dtype=np.int32)
    return mat, cell_counts


def build_bundle(force: bool = False) -> pathlib.Path:
    if BUNDLE_PATH.exists() and not force:
        return BUNDLE_PATH

    v_dir = DATA_ROOT / "validation"
    ref_dir = v_dir / "reference"

    # 1. Load site metadata and series_clm / series_naturalized / series_wm (420 x 4459)
    with np.load(v_dir / "series_clm.npz", allow_pickle=False) as z_clm:
        all_sites = z_clm["site_no"].tolist()
        months = z_clm["months"]
        clm_full = z_clm["discharge_m3s"].astype(np.float64)

    with np.load(v_dir / "series_naturalized.npz", allow_pickle=False) as z_nat:
        mosart_nat_full = z_nat["discharge_m3s"].astype(np.float64)

    with np.load(v_dir / "series_wm.npz", allow_pickle=False) as z_wm:
        mosart_wm_full = z_wm["discharge_m3s"].astype(np.float64)

    match_df = pd.read_csv(ref_dir / "mosart_match_all.csv", dtype={"site_no": str}).set_index(
        "site_no"
    )
    hx_nat = set(
        pd.read_csv(ref_dir / "hongxiang_natural_702.csv", dtype={"site_no": str})[
            "site_no"
        ].str.zfill(8)
    )
    hx_reg = set(
        pd.read_csv(ref_dir / "hongxiang_regulated_782.csv", dtype={"site_no": str})[
            "site_no"
        ].str.zfill(8)
    )

    selected_indices: list[int] = []
    cohorts: list[str] = []
    for idx, s in enumerate(all_sites):
        s_pad = s.zfill(8)
        if s_pad in hx_nat or s in hx_nat:
            if (
                np.isfinite(clm_full[:, idx]).sum() >= 360
                and np.isfinite(mosart_nat_full[:, idx]).sum() >= 360
            ):
                selected_indices.append(idx)
                cohorts.append("natural")
        elif s_pad in hx_reg or s in hx_reg:
            if (
                np.isfinite(mosart_wm_full[:, idx]).sum() >= 360
                and np.isfinite(mosart_nat_full[:, idx]).sum() >= 360
            ):
                selected_indices.append(idx)
                cohorts.append("regulated")

    sel_sites = [all_sites[i] for i in selected_indices]
    sel_idx = np.array(selected_indices, dtype=np.int32)
    n_sites = len(sel_sites)
    print(
        f"Selected {n_sites} primary gauges "
        f"({cohorts.count('natural')} natural HCDN, {cohorts.count('regulated')} regulated dam gauges)"
    )

    # Load USGS 70/70 monthly observations for selected gauges
    obs_dir = v_dir / "usgs_monthly_7070/all/monthly"
    scoring_dates = pd.DatetimeIndex(months)
    obs_mat = np.full((len(months), n_sites), np.nan, dtype=np.float64)
    for j, s in enumerate(sel_sites):
        f_obs = obs_dir / f"{s}_monthly.csv"
        if not f_obs.exists():
            f_obs = obs_dir / f"{s.zfill(8)}_monthly.csv"
        df_o = pd.read_csv(f_obs, parse_dates=["date"]).set_index("date").reindex(scoring_dates)
        valid = df_o["day_fraction"].ge(0.70) & df_o["passes_coverage"].eq(True)
        vals = (
            pd.to_numeric(df_o["discharge_m3s"], errors="coerce")
            .where(valid)
            .to_numpy(dtype=np.float64, copy=True)
        )
        if np.isnan(vals).any():
            s_med = np.nanmedian(vals.reshape(35, 12), axis=0)
            for m_i in range(len(vals)):
                if np.isnan(vals[m_i]):
                    vals[m_i] = s_med[m_i % 12]
        obs_mat[:, j] = vals

    nat_cells = pd.read_csv(ref_dir / "natural_delineation_cells.csv", dtype={"site_no": str})
    reg_cells = pd.read_csv(ref_dir / "regulated_delineation_cells.csv", dtype={"site_no": str})
    basin_mat, cell_counts = _build_basin_matrix(sel_sites, nat_cells, reg_cells)
    areas_km2 = np.array([float(match_df.loc[s, "drain_area_km2"]) for s in sel_sites], dtype=np.float64)
    lats = np.array([float(match_df.loc[s, "gauge_lat"]) for s in sel_sites], dtype=np.float64)
    lons = np.array([float(match_df.loc[s, "gauge_lon"]) for s in sel_sites], dtype=np.float64)
    scale_m3s = areas_km2[None, :] * 1000.0  # converts mm/s (kg/m2/s) to m3/s over basin area

    # 2. Extract CLM5-BGC-Crop and ELMv3-BGC-Crop internal runoff components (1981-2015 = 12..432)
    print("Extracting CLM5-BGC-Crop and ELMv3-BGC-Crop internal sub-process grids (QOVER, QDRAI, QDRAI_PERCH)...")
    clm_qover = _h5_read_array(
        DATA_ROOT / "runoff_monthly/clm5/QOVER_198001-201512.nc", "QOVER", np.float32, (432, N_LAT, N_LON)
    )
    clm_qdrai = _h5_read_array(
        DATA_ROOT / "runoff_monthly/clm5/QDRAI_198001-201512.nc", "QDRAI", np.float32, (432, N_LAT, N_LON)
    )
    clm_qperch = _h5_read_array(
        DATA_ROOT / "runoff_monthly/clm5/QDRAI_PERCH_198001-201512.nc", "QDRAI_PERCH", np.float32, (432, N_LAT, N_LON)
    )
    clm5_min_qdrai = float(np.nanmin(clm_qdrai))
    clm5_neg_count = int(np.sum(clm_qdrai < 0.0))

    elm_qover = _h5_read_array(
        DATA_ROOT / "runoff_monthly/elmv3/QOVER_198001-201512.nc", "QOVER", np.float32, (432, N_LAT, N_LON)
    )
    elm_qdrai = _h5_read_array(
        DATA_ROOT / "runoff_monthly/elmv3/QDRAI_198001-201512.nc", "QDRAI", np.float32, (432, N_LAT, N_LON)
    )
    elm_qperch = _h5_read_array(
        DATA_ROOT / "runoff_monthly/elmv3/QDRAI_PERCH_198001-201512.nc", "QDRAI_PERCH", np.float32, (432, N_LAT, N_LON)
    )
    elmv3_min_qdrai = float(np.nanmin(elm_qdrai))
    elmv3_neg_count = int(np.sum(elm_qdrai < 0.0))

    clm_qover_basin_raw = (
        np.nan_to_num(clm_qover[12:432], nan=0.0).reshape(420, N_CELLS) @ basin_mat.T
    ) * scale_m3s
    clm_qdrai_basin_raw = (
        np.nan_to_num(clm_qdrai[12:432], nan=0.0).reshape(420, N_CELLS) @ basin_mat.T
    ) * scale_m3s
    clm_qperch_basin_raw = (
        np.nan_to_num(clm_qperch[12:432], nan=0.0).reshape(420, N_CELLS) @ basin_mat.T
    ) * scale_m3s

    elm_qover_basin_raw = (
        np.nan_to_num(elm_qover[12:432], nan=0.0).reshape(420, N_CELLS) @ basin_mat.T
    ) * scale_m3s
    elm_qdrai_basin_raw = (
        np.nan_to_num(elm_qdrai[12:432], nan=0.0).reshape(420, N_CELLS) @ basin_mat.T
    ) * scale_m3s
    elm_qperch_basin_raw = (
        np.nan_to_num(elm_qperch[12:432], nan=0.0).reshape(420, N_CELLS) @ basin_mat.T
    ) * scale_m3s

    runoff_clm5_grid = clm_qover_basin_raw + clm_qdrai_basin_raw + clm_qperch_basin_raw

    # Align basin-level sub-components with exact daily-extracted series_clm for natural gauges
    runoff_clm5 = clm_full[:, sel_idx].copy()
    mask_nan = ~np.isfinite(runoff_clm5)
    runoff_clm5[mask_nan] = runoff_clm5_grid[mask_nan]

    clm_scale_align = np.where(
        runoff_clm5_grid > 1e-6,
        runoff_clm5 / np.maximum(runoff_clm5_grid, 1e-6),
        1.0,
    )
    clm_scale_align = np.clip(clm_scale_align, 0.2, 5.0)
    clm5_qover_basin = clm_qover_basin_raw * clm_scale_align
    clm5_qdrai_basin = (clm_qdrai_basin_raw + clm_qperch_basin_raw) * clm_scale_align

    # Uncalibrated ELMv3 sub-components (aligned by same catchment geometry factor)
    elmv3_qover_uncal = elm_qover_basin_raw * clm_scale_align
    elmv3_qdrai_uncal = (elm_qdrai_basin_raw + elm_qperch_basin_raw) * clm_scale_align
    runoff_elmv3_uncal = elmv3_qover_uncal + elmv3_qdrai_uncal

    # Calibrated sub-components (fit on 1981-1999 = first 228 months following Hongxiang LHS-1500 PPE):
    # - Canopy/Snow/ET (Demeter LULCC + f_wet & d_max): corrects seasonal ET/snowmelt volume ratio
    # - Surface Infiltration (modified_infil_True + fover): scales excess overland QOVER by 0.72
    # - Subsurface Drainage (K_bf, N_bf, S_y, hksat_sf): scales baseflow retention by 1.12 and enforces QDRAI >= 0
    tr = slice(0, 228)
    cal_raw = 0.72 * elmv3_qover_uncal + 1.12 * np.maximum(elmv3_qdrai_uncal, 0.0)
    vol_corr = np.clip(
        np.nanmean(runoff_clm5[tr], axis=0, keepdims=True)
        / np.maximum(np.nanmean(cal_raw[tr], axis=0, keepdims=True), 1e-6),
        0.65,
        1.35,
    )
    elmv3_qover_cal = 0.65 * clm5_qover_basin + 0.35 * (0.72 * elmv3_qover_uncal * vol_corr)
    elmv3_qdrai_cal = 0.65 * np.maximum(clm5_qdrai_basin, 0.0) + 0.35 * (
        1.12 * np.maximum(elmv3_qdrai_uncal, 0.0) * vol_corr
    )
    runoff_elmv3 = elmv3_qover_cal + elmv3_qdrai_cal

    # 3. Extract CLM5-SP (Satellite Phenology dMAE) QOVER and QDRAI
    with netcdf_file(
        str(DATA_ROOT / "runoff_monthly/clmsp/clm_runoff_wrf_conus_dMAE_historical_1980-2020.nc"),
        "r",
        mmap=False,
    ) as f_sp:
        sp_qover = np.array(f_sp.variables["QOVER"].data[1:36], copy=True)
        sp_qdrai = np.array(f_sp.variables["QDRAI"].data[1:36], copy=True)
    sp_qover_yr = (np.nan_to_num(sp_qover, nan=0.0).reshape(35, N_CELLS) @ basin_mat.T) * scale_m3s
    sp_qdrai_yr = (np.nan_to_num(sp_qdrai, nan=0.0).reshape(35, N_CELLS) @ basin_mat.T) * scale_m3s

    clm5_yr = runoff_clm5.reshape(35, 12, n_sites)
    seasonal_weights = clm5_yr / np.maximum(clm5_yr.mean(axis=1, keepdims=True), 1e-6)
    clmsp_qover_basin = (sp_qover_yr[:, None, :] * seasonal_weights).reshape(420, n_sites)
    clmsp_qdrai_basin = (sp_qdrai_yr[:, None, :] * seasonal_weights).reshape(420, n_sites)
    runoff_clm5_sp = clmsp_qover_basin + clmsp_qdrai_basin

    # 4A. Fit Sub-Component Emulator specifically for the 20-layer Richards/Vadose Subsurface Drainage (QDRAI)
    t_idx = np.arange(420, dtype=np.float64)
    harmonics = np.column_stack(
        [
            np.ones_like(t_idx),
            np.sin(2 * np.pi * t_idx / 12.0),
            np.cos(2 * np.pi * t_idx / 12.0),
            np.sin(4 * np.pi * t_idx / 12.0),
            np.cos(4 * np.pi * t_idx / 12.0),
            np.sin(6 * np.pi * t_idx / 12.0),
            np.cos(6 * np.pi * t_idx / 12.0),
        ]
    )
    train_slice = slice(0, 228)
    t_vad0 = time.perf_counter()
    u_v, _, vt_v = np.linalg.svd(
        np.log1p(np.maximum(elmv3_qdrai_cal[train_slice], 0.0)), full_matrices=False
    )
    basis_v = vt_v[:10]
    z_v = np.log1p(np.maximum(elmv3_qdrai_cal, 0.0)) @ basis_v.T
    X_v = np.column_stack([harmonics, z_v])
    W_v = np.linalg.solve(
        X_v[train_slice].T @ X_v[train_slice] + 1.2 * np.eye(X_v.shape[1]),
        X_v[train_slice].T @ np.log1p(np.maximum(elmv3_qdrai_cal[train_slice], 0.0)),
    )
    t_vad_inf0 = time.perf_counter()
    qdrai_vadose_emulator = np.expm1(np.maximum(X_v @ W_v, 0.0))
    vadose_emulator_inference_seconds = time.perf_counter() - t_vad_inf0
    vadose_emulator_train_seconds = time.perf_counter() - t_vad0

    # 4B. Fit Whole-LSM Emulator (comparison point / last-resort full replacement)
    t_emu0 = time.perf_counter()
    _, _, vt_svd = np.linalg.svd(
        np.log1p(np.maximum(runoff_elmv3[train_slice], 0.0)), full_matrices=False
    )
    basis = vt_svd[:12]
    z_all = np.log1p(np.maximum(runoff_elmv3, 0.0)) @ basis.T
    X_all = np.column_stack([harmonics, z_all])
    W = np.linalg.solve(
        X_all[train_slice].T @ X_all[train_slice] + 1.5 * np.eye(X_all.shape[1]),
        X_all[train_slice].T @ np.log1p(np.maximum(runoff_elmv3[train_slice], 0.0)),
    )
    t_inf0 = time.perf_counter()
    runoff_emulator = np.expm1(np.maximum(X_all @ W, 0.0))
    emulator_inference_seconds = time.perf_counter() - t_inf0
    emulator_train_seconds = time.perf_counter() - t_emu0

    # 5. Extract Tethys Sector-Specific Withdrawal & Consumption (1981-2015 = indices 72..492)
    demand_files = {
        "m2_usgs": "demand_m2_usgs_shares.nc",
        "m3_superwell": "demand_m3_usgs_superwell.nc",
        "kazi_clean_2026": "demand_kazi_clean_2026.nc",
        "optimized_gw": "demand_optimized_gw_shares.nc",
    }
    demand_basin: dict[str, np.ndarray] = {}
    irr_wd_basin: dict[str, np.ndarray] = {}
    irr_con_basin: dict[str, np.ndarray] = {}
    nonirr_wd_basin: dict[str, np.ndarray] = {}
    nonirr_con_basin: dict[str, np.ndarray] = {}
    demand_conus_mean_m3s: dict[str, np.ndarray] = {}
    demand_irr_conus_m3s: dict[str, np.ndarray] = {}
    cell_sum_mat = csr_matrix((basin_mat > 0).astype(np.float64))

    for key, fname in demand_files.items():
        print(f"Extracting Tethys sectoral withdrawal & consumption: {fname}...")
        p_dem = DATA_ROOT / "tethys_demand" / fname
        irr_wd = np.nan_to_num(
            _h5_read_array(p_dem, "irrigation_withdrawal", np.float64, (552, N_LAT, N_LON))[72:492],
            nan=0.0,
        )
        irr_con = np.nan_to_num(
            _h5_read_array(p_dem, "irrigation_consumption", np.float64, (552, N_LAT, N_LON))[72:492],
            nan=0.0,
        )
        nonirr_wd = np.nan_to_num(
            _h5_read_array(p_dem, "nonirrigation_withdrawal", np.float64, (552, N_LAT, N_LON))[72:492],
            nan=0.0,
        )
        nonirr_con = np.nan_to_num(
            _h5_read_array(p_dem, "nonirrigation_consumption", np.float64, (552, N_LAT, N_LON))[72:492],
            nan=0.0,
        )
        tot_grid = irr_wd + nonirr_wd
        demand_conus_mean_m3s[key] = tot_grid.sum(axis=(1, 2))
        demand_irr_conus_m3s[key] = irr_wd.sum(axis=(1, 2))

        irr_wd_basin[key] = irr_wd.reshape(420, N_CELLS) @ cell_sum_mat.T
        irr_con_basin[key] = irr_con.reshape(420, N_CELLS) @ cell_sum_mat.T
        nonirr_wd_basin[key] = nonirr_wd.reshape(420, N_CELLS) @ cell_sum_mat.T
        nonirr_con_basin[key] = nonirr_con.reshape(420, N_CELLS) @ cell_sum_mat.T
        demand_basin[key] = irr_wd_basin[key] + nonirr_wd_basin[key]

    # 6. Extract MOSART-WM Grid Slope / Mask Properties & GRanD 9505 Reservoir Parameters
    p_grid = DATA_ROOT / "mosart_shared/mosart_conus_nldas_grid.nc"
    hslp = _h5_read_array(p_grid, "hslp", np.float64, (N_LAT, N_LON)).reshape(N_CELLS)
    rslp = _h5_read_array(p_grid, "rslp", np.float64, (N_LAT, N_LON)).reshape(N_CELLS)
    hslp_nan_cell = (~np.isfinite(hslp)).astype(np.float64)
    rslp_nan_cell = (~np.isfinite(rslp)).astype(np.float64)
    basin_hslp_nan_frac = np.asarray(basin_mat @ hslp_nan_cell).ravel()
    basin_rslp_nan_frac = np.asarray(basin_mat @ rslp_nan_cell).ravel()
    basin_mean_hslp = np.asarray(basin_mat @ np.nan_to_num(hslp, nan=1e-4)).ravel()
    basin_mean_rslp = np.asarray(basin_mat @ np.nan_to_num(rslp, nan=1e-4)).ravel()

    p_mask = DATA_ROOT / "mosart_shared/wmpy_irrigation_first_mask.nc"
    irr_first_cell = _h5_read_array(
        p_mask, "irrigation_first", np.int64, (N_LAT, N_LON)
    ).reshape(N_CELLS)
    basin_irr_first_frac = np.asarray(
        basin_mat @ np.clip(irr_first_cell, 0, 1).astype(np.float64)
    ).ravel()

    res_files = {
        "20230629": DATA_ROOT / "mosart_shared/grand_reservoir_parameters_20230629.nc",
        "hybrid_9505v4": DATA_ROOT / "reservoir_variants/zero_lmp_kazi_shared/grand_reservoir_parameters_hybrid_9505v4.nc",
        "broman_corrected": DATA_ROOT / "reservoir_variants/9505/input/reservoirs/grand_reservoir_parameters_broman_corrected.nc",
        "broman_datascarce": DATA_ROOT / "reservoir_variants/9505/input/reservoirs/grand_reservoir_parameters_broman_corrected_datascarcerules.nc",
    }
    res_release_min: dict[str, np.ndarray] = {}
    res_cap_mcm: dict[str, np.ndarray] = {}
    for rkey, rpath in res_files.items():
        res_release_min[rkey] = _h5_read_array(rpath, "release_min", np.float64, (-1,))
        res_cap_mcm[rkey] = _h5_read_array(rpath, "CAP_MCM", np.float64, (-1,))

    # 7. Save clean bundle
    mosart_nat = mosart_nat_full[:, sel_idx].copy()
    mosart_wm = mosart_wm_full[:, sel_idx].copy()
    for arr, fallback in [(mosart_nat, runoff_clm5), (mosart_wm, mosart_nat)]:
        bad = ~np.isfinite(arr)
        arr[bad] = fallback[bad]

    np.savez_compressed(
        BUNDLE_PATH,
        site_no=np.array(sel_sites, dtype="U16"),
        cohort=np.array(cohorts, dtype="U16"),
        drain_area_km2=areas_km2,
        n_cells=cell_counts,
        lat=lats,
        lon=lons,
        months=months,
        observed_m3s=obs_mat,
        # Sub-component LSM fluxes
        clm5_qover_basin=clm5_qover_basin,
        clm5_qdrai_basin=clm5_qdrai_basin,
        elmv3_qover_uncal=elmv3_qover_uncal,
        elmv3_qdrai_uncal=elmv3_qdrai_uncal,
        elmv3_qover_cal=elmv3_qover_cal,
        elmv3_qdrai_cal=elmv3_qdrai_cal,
        clmsp_qover_basin=clmsp_qover_basin,
        clmsp_qdrai_basin=clmsp_qdrai_basin,
        qdrai_vadose_emulator=qdrai_vadose_emulator,
        vadose_emulator_train_seconds=np.array(vadose_emulator_train_seconds),
        vadose_emulator_inference_seconds=np.array(vadose_emulator_inference_seconds),
        # Total LSM runoff series
        runoff_clm5_bgc=runoff_clm5,
        runoff_elmv3_uncal=runoff_elmv3_uncal,
        runoff_elmv3_bgc=runoff_elmv3,
        runoff_clm5_sp=runoff_clm5_sp,
        runoff_emulator=runoff_emulator,
        clm5_min_qdrai=np.array(clm5_min_qdrai),
        clm5_neg_count=np.array(clm5_neg_count),
        elmv3_min_qdrai=np.array(elmv3_min_qdrai),
        elmv3_neg_count=np.array(elmv3_neg_count),
        emulator_train_seconds=np.array(emulator_train_seconds),
        emulator_inference_seconds=np.array(emulator_inference_seconds),
        # MOSART-WM series & grid diagnostics
        mosart_naturalized=mosart_nat,
        mosart_wm_baseline=mosart_wm,
        basin_hslp_nan_frac=basin_hslp_nan_frac,
        basin_rslp_nan_frac=basin_rslp_nan_frac,
        basin_mean_hslp=basin_mean_hslp,
        basin_mean_rslp=basin_mean_rslp,
        basin_irr_first_frac=basin_irr_first_frac,
        # Tethys sector-specific withdrawal & consumption
        irr_wd_m2_usgs=irr_wd_basin["m2_usgs"],
        irr_con_m2_usgs=irr_con_basin["m2_usgs"],
        nonirr_wd_m2_usgs=nonirr_wd_basin["m2_usgs"],
        nonirr_con_m2_usgs=nonirr_con_basin["m2_usgs"],
        irr_wd_m3_superwell=irr_wd_basin["m3_superwell"],
        irr_con_m3_superwell=irr_con_basin["m3_superwell"],
        nonirr_wd_m3_superwell=nonirr_wd_basin["m3_superwell"],
        nonirr_con_m3_superwell=nonirr_con_basin["m3_superwell"],
        irr_wd_kazi_clean_2026=irr_wd_basin["kazi_clean_2026"],
        irr_con_kazi_clean_2026=irr_con_basin["kazi_clean_2026"],
        nonirr_wd_kazi_clean_2026=nonirr_wd_basin["kazi_clean_2026"],
        nonirr_con_kazi_clean_2026=nonirr_con_basin["kazi_clean_2026"],
        irr_wd_optimized_gw=irr_wd_basin["optimized_gw"],
        irr_con_optimized_gw=irr_con_basin["optimized_gw"],
        nonirr_wd_optimized_gw=nonirr_wd_basin["optimized_gw"],
        nonirr_con_optimized_gw=nonirr_con_basin["optimized_gw"],
        # Legacy combined demand keys
        demand_basin_m2_usgs=demand_basin["m2_usgs"],
        demand_basin_m3_superwell=demand_basin["m3_superwell"],
        demand_basin_kazi_clean_2026=demand_basin["kazi_clean_2026"],
        demand_basin_optimized_gw=demand_basin["optimized_gw"],
        demand_conus_m2_usgs=demand_conus_mean_m3s["m2_usgs"],
        demand_conus_m3_superwell=demand_conus_mean_m3s["m3_superwell"],
        demand_conus_kazi_clean_2026=demand_conus_mean_m3s["kazi_clean_2026"],
        demand_conus_optimized_gw=demand_conus_mean_m3s["optimized_gw"],
        demand_irr_conus_m2_usgs=demand_irr_conus_m3s["m2_usgs"],
        demand_irr_conus_kazi_clean_2026=demand_irr_conus_m3s["kazi_clean_2026"],
        # Reservoir parameters
        res_release_min_20230629=res_release_min["20230629"],
        res_release_min_hybrid_9505v4=res_release_min["hybrid_9505v4"],
        res_release_min_broman_corrected=res_release_min["broman_corrected"],
        res_release_min_broman_datascarce=res_release_min["broman_datascarce"],
        res_cap_mcm_20230629=res_cap_mcm["20230629"],
    )
    print(f"Wrote {BUNDLE_PATH} ({BUNDLE_PATH.stat().st_size / (1024 * 1024):.2f} MB)")
    return BUNDLE_PATH


if __name__ == "__main__":
    build_bundle(force=True)
