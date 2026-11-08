# DOE IM3 CONUS Water-Scarcity Chain (`CLM5/ELMv3 + Tethys -> mosartwmpy`)

Flagship systems-engineering demonstration of **Autoengineering 2.0** across **1,190 USGS 70/70 monthly stream gauges** (`1981–2015`, 420 months = **672 Natural HCDN gauges** + **518 Regulated Pre-1980 GRanD Dam gauges**).

## 1. Decomposing the 3 IM3 Macro-Models into 9 Internal Physical Sub-Components

Rather than treating `CLM5/ELMv3`, `Tethys`, and `mosartwmpy` as monolithic black boxes, [`system.yaml`](system.yaml) decomposes them into **9 connected internal sub-components**:

1. **`CLM5 / ELMv3` Land Surface Hydrology (`240.0` NERSC node-hours/run):**
   - `lsm_canopy_snow_et` (`68.0h`): Canopy interception, multilayer snowpack melt & evapotranspiration partitioning (`LUH2` vs `CLM5-SP` MODIS satellite phenology vs `ELMv3 Demeter` crop LULCC + `f_wet`/`n_melt_coef`).
   - `lsm_surface_infiltration` (`52.0h`): Saturation-excess & infiltration-excess overland flow (`QOVER + QH2OSFC`; TOPMODEL `fover` decay & modified frozen-soil infiltration).
   - `lsm_subsurface_drainage` (`120.0h`): 20-layer nonlinear Richards vadose solver, perched water table & unconfined aquifer baseflow (`QDRAI + QDRAI_PERCH`; `I-25` negative drainage fix & LHS-1500 calibration).
2. **`Tethys` Spatiotemporal Sectoral Water-Demand Downscaling (`0.8` NERSC node-hours/run):**
   - `tethys_irrigation_downscaler` (`0.45h`): Agricultural crop-grid downscaling, canal conveyance efficiency (`0.829937`, `I-07`/`I-10`), 6-year populated share interpolation (`I-11`), and USGS Method 2 (`I-13`) surface/groundwater partitioning.
   - `tethys_thermoelectric_industrial_downscaler` (`0.20h`): Power-plant cooling (`0-LMP` CERF `I-08`/`I-09` once-through vs recirculating return-flow ratios) & industrial (`mfg`/`min`/`liv`) demands.
   - `tethys_municipal_domestic_downscaler` (`0.15h`): Urban/rural population masks (`I-30`) & seasonal outdoor municipal water consumption.
3. **`mosartwmpy` River Routing & Water Management (`2.5` NERSC node-hours/run):**
   - `mosart_hillslope_tributary_routing` (`0.70h`): Hillslope overland kinematic wave & tributary sub-network routing (repairing 987 land cells with `hslp=NaN` and 703 with `rslp=NaN`, Issue `I-23`).
   - `mosart_channel_network_routing` (`0.90h`): `0.125°` NLDAS2 main-channel routing + sub-grid headwater drainage-area reconciliation (`IM3 Hybrid` selector for basins $\le 4$ cells + `#129` `a69c2a7` aggregation fix `I-01`).
   - `mosart_reservoir_demand_wm` (`0.90h`): GRanD 9505 reservoir storage/release rule curves (`20230629` vs Broman `9505v4`), non-negative release floor (`I-22`), `wmpy_irrigation_first_mask` (`I-21`), coordinate-aligned reservoir demand reference (`I-17`), and return-flow routing (`I-20`).

## 2. Running the Workflow

```sh
# 1. Inspect the 9-subcomponent graph
pixi run autoengineering describe examples/im3_water_scarcity/system.yaml

# 2. Run CLI triage across the 9 internal sub-components
pixi run autoengineering triage examples/im3_water_scarcity/system.yaml

# 3. Execute the full sub-component triage, guarded improvement loop, and emulator comparisons
pixi run python examples/im3_water_scarcity/run_workflow.py
```
