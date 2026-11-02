# Raw WIND direction source review

The [pinned exporter trace](../../examples/utility/verification-wind-upstream-source-v1/README.md)
now supports an angle-preserving raw-to-SAM path at an existing height in the
reviewed rex version. SAM's documented wind-from angles therefore support the
development interpretation as an inference. This does not prove the original
raw production history, qualify the 2014 version change or establish untouched
data. The production admission flag remains false. The earlier untraced review
below is preserved as historical evidence.

The raw HDF5 direction convention remains unresolved. No acquisition, model,
selection, scoring or protocol change followed this review.

The [provider's dataset description](https://nrel.sitefinity.cloud/hpc/wind-dataset)
identifies the height fields, instantaneous hourly support, integer storage and
annual HDF5 layout. It separates 2007-2013 CONUS from the 2014 WRF/PBL update.
The reviewed page does not state the direction origin, rotation or from/to meaning.

The [meteorological validation report](https://docs.nlr.gov/docs/fy15osti/61740.pdf)
lists direction in degrees, heights and UTC support. The bounded direction-text
review did not establish the raw HDF5 encoding. Validation plots are background
evidence, not confirmation observations for the proposed offshore point.

The [SAM CSV guide](https://samrepo.nlr.gov/help/weather_format_csv_wind.html)
defines a wind-from convention for a related interface. The review has not traced
a versioned export path proving angle-preserving conversion from the exact raw
HDF5 product to that interface. The development assumption therefore stays explicit.
Web-extracted pages were reviewed; full source bytes were not acquired or hashed.
No source independence or absence of prior personal exposure is inferred.

A useful next source check is an upstream raw-to-SAM export contract or a pinned
conversion implementation tied to this HDF5 product. Additional development model
runs cannot establish the provider's convention.
