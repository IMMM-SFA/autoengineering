# WIND point data attribution

The compact `public/point.npz` is a local extraction and decoding of public NREL
WIND Toolkit CONUS v1.0.0 data for 2007. It contains one point's raw integer inputs,
scaled speed/direction, validity masks and UTC timestamps. These are modeled weather
inputs, not measured turbine outputs. Source, ETag, source metadata and extraction
identities are in `public/request.json`; output and source range hashes are preserved.

The [AWS registry](https://registry.opendata.aws/nrel-pds-wtk/) declares
[CC BY 3.0 US](https://creativecommons.org/licenses/by/3.0/us/). Data terms remain
separate from the package code license. Cite the WIND Toolkit and recommended
reports listed by the [provider](https://nrel.sitefinity.cloud/hpc/wind-dataset),
including Draxl, Clifton, Hodge and McCaa (2015), The Wind Integration National
Dataset (WIND) Toolkit, Applied Energy 151, 355-366. The metadata archive's NOTICE
retains the original development-source attribution.

Unscaling follows the [provider's convention](https://natlabrockies.github.io/rex/misc/examples.nlr_data.html):
mask raw fill values, then divide integer values by the declared scale factor.
No directional from/to or north-reference convention is inferred from the unit name.
