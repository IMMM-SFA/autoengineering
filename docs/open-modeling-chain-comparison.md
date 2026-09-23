# Open modeling chains for autoengineering

Search date: 2026-09-05. Recommendation: adopt pvlib's OEDI System 9068 example first. Use PyWake/TOPFARM for a later design optimization demonstration, and HOPP when a broader energy system is needed.

This assessment uses the current repository README, concept.md, and docs/bayesian-optimization-status.md. It distinguishes component replacement from whole-system optimization. No models were installed or executed during the search. Runtime and memory requirements below are feasibility judgments, not benchmarks.

## Comparison

| Existing chain | Evidence and replaceable components | Local execution | Caveat | Confidence |
| --- | --- | --- | --- | --- |
| [pvlib OEDI 9068](https://pvlib-python.readthedocs.io/en/v0.15.2/gallery/system-models/oedi_9068.html) | Existing solar-plant chain covering tracking, shading, irradiance, temperature, DC conversion and inverter output. | Python scientific stack. Download weather and observations once, then use cached files. CPU execution appears practical. | Some equipment and geometry values are inferred. Installation and full data access remain untested. | High workflow fit; medium readiness. |
| [PyWake Horns Rev](https://topfarm.pages.windenergy.dtu.dk/PyWake/notebooks/Quickstart.html) with [TOPFARM](https://topfarm.pages.windenergy.dtu.dk/TopFarm2/) | Wind resource, wake interactions, turbine power and annual energy. TOPFARM adds layout optimization and electrical network integration. | Python; the quickstart includes site/turbine inputs and a 16-turbine calculation. Larger layout searches provide substantial local work. | Built-in site inputs do not establish access to raw plant observations. Larger predicted energy from a different wake model does not establish improved accuracy. | High documented execution fit; medium validation fit. |
| [HOPP dispatchable solar case](https://hopp.readthedocs.io/en/v3.1/examples/dispatchable_solar_case_study.html) | PV and concentrating solar generation, storage, dispatch and financial outputs. | Local Python and mathematical programming solvers; documented case uses CBC. Full dispatch and repeated design evaluations are the heavier option. | This is a modeled design case, not an observed plant-validation dataset. Initial adapters and solver setup are more involved. | High chain relevance; medium readiness. |

The projects agree on exposing modular physical calculations. They serve different objectives: pvlib offers a direct accuracy demonstration, TOPFARM optimizes wind-farm design, and HOPP evaluates hybrid plant design and operation. Their simulated improvements are not interchangeable evidence.

## Recommended example

OEDI 9068 is a 4.7 MW tracking CdTe plant in Colorado. The [pvlib gallery example](https://pvlib-python.readthedocs.io/en/v0.15.2/gallery/system-models/oedi_9068.html) includes comparison with inverter measurements. It already includes Faiman temperature with Prilliman thermal transience. Preserve that upstream implementation as a reference; call any deliberately simplified version an ablation.

The [SETO webinar tutorial](https://pv-tutorials.github.io/2024_Modeling_Webinar/pvlib-tutorial.html) provides a concrete component experiment using the same plant: compare Faiman, SAPM, PVsyst, and Faiman plus Prilliman against temperature measurements. It identifies thermal lag during changing weather. That is evidence for a useful hypothesis, not proof that electrical output improves on unseen periods.

Proposed demonstration question: which component replacement reduces held-out electrical prediction error, and does the component's own error explain that gain?

1. Preserve the upstream reference and expose existing calculations through autoengineering adapters. Verify adapter output parity before searching.
2. Establish a common temperature contract. Back-of-module sensor temperature and modeled cell temperature must not be equated without an explicit mapping. Use the same observation channels and valid timestamps for every candidate.
3. Compare temperature alternatives with irradiance and equipment assumptions fixed. Then test compatible irradiance/shading alternatives separately. Preserve legitimate physical configurations.
4. Rank components, run bounded replacements, and retain unsuccessful attempts. Record component error, final power error, integrated energy bias, evaluation time and total search overhead.
5. Freeze chronological fitting, selection and test periods after inspecting coverage. Require a full seasonal test cycle if data permit. Use selection data for search decisions and access the final test only after freezing the choice.
6. Compare automated search against the unchanged upstream chain, fixed candidate order and equal-budget random search. Add Sobol/SMAC/BoTorch comparisons only when the corresponding repository interfaces are ready. Do not claim function-network optimization from intermediate diagnostics alone.

A temperature improvement with no power improvement is an informative result. Do not promise a positive headline or weaken the upstream baseline to obtain one.

## Adoption gates

- Data: the [PVDAQ catalog](https://data.openei.org/submissions/4568) exposes the Solar Data Prize collection with anonymous S3 access. Target only `pvdaq/2023-solar-data-prize/9068_OEDI/`, not the entire collection. The webinar names metadata, irradiance, environment and AC-power files. Check their existence, sizes, coverage and reuse terms before downloading or redistributing a subset. The exact object listing was not retrieved in this search.
- Software: [pvlib's license](https://github.com/pvlib/pvlib-python/blob/main/LICENSE) is BSD-3-Clause. [PyWake](https://topfarm.pages.windenergy.dtu.dk/PyWake/) is MIT; [HOPP](https://github.com/NatLabRockies/HOPP) is BSD-3-Clause. Data and bundled dependencies need their own attribution records.
- Weather: the current gallery code uses `get_nsrdb_psm4_conus`, although surrounding prose still mentions PSM3. [Release notes](https://pvlib-python.readthedocs.io/en/v0.15.2/whatsnew.html) document removal of the old PSM3 interface. Use a pinned current implementation and cache the actual response. Do not assume the example's demo credential can fetch the required slice.
- Observations: predeclare treatment of outages, clipping, shading, tracker stalls, missing values, timestamp conventions and sensor disagreement. Report exclusions and coverage. Integrate power with actual time intervals rather than silently filling missing periods.
- Local feasibility: create a separate Pixi environment and first time a contiguous month, including transient-model warmup. Then run a year and report peak memory and wall time. Set the search budget from that measurement. There is no reason to add artificial computation merely to make optimization appear useful.
- Stop conditions: pause adoption if required files or rights cannot be established, parity fails, or independent evaluation coverage is inadequate. Keep those states explicit.

HOPP remains a useful second example if expensive evaluation is the priority. Its [repository instructions](https://github.com/NatLabRockies/HOPP) specify Python 3.11+, CBC/GLPK and credentials for resource downloads. Local resource files are supported by the case study. Native dependency compatibility on this Mac still needs verification.

## Sources

- pvlib plant example: https://pvlib-python.readthedocs.io/en/v0.15.2/gallery/system-models/oedi_9068.html
- Temperature comparison tutorial: https://pv-tutorials.github.io/2024_Modeling_Webinar/pvlib-tutorial.html
- PVDAQ data catalog: https://data.openei.org/submissions/4568
- pvlib license: https://github.com/pvlib/pvlib-python/blob/main/LICENSE
- pvlib release notes: https://pvlib-python.readthedocs.io/en/v0.15.2/whatsnew.html
- PyWake project and license: https://topfarm.pages.windenergy.dtu.dk/PyWake/
- Horns Rev quickstart: https://topfarm.pages.windenergy.dtu.dk/PyWake/notebooks/Quickstart.html
- TOPFARM: https://topfarm.pages.windenergy.dtu.dk/TopFarm2/
- HOPP repository and installation: https://github.com/NatLabRockies/HOPP
- HOPP dispatchable solar example: https://hopp.readthedocs.io/en/v3.1/examples/dispatchable_solar_case_study.html
