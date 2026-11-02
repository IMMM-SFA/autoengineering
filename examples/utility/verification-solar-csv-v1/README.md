# Source CSV to separated solar preparation

The new parser binds exact source bytes, a complete CSV header, an AC metadata
review and explicit sensor semantics before normalization. It passes normalized
averages and samples into the existing interval alignment and partition preparation.
The existing public and reserved readers remain unchanged. All results stay
`not_admitted`.

The profile accepts UTF-8 comma-separated input with bounded bytes, columns, fields
and rows. Values use finite decimal/scientific notation. Blank measurements and
explicit missing tokens remain missing. Quality flags use separate declared good
and bad token sets. Blank quality is rejected unless explicitly classified as bad.
Absent quality flags remain unqualified rather than establishing source quality.
Negative AC standby is preserved. Conversions occur in the existing alignment,
not while interpreting source numeric values.

Every channel declares its timestamp column, source units, average/sample support,
availability delay and clock policy. Averages require an explicit constant duration
or duration column. Adjacent timestamps do not supply missing durations. Mixed
supported durations and gaps remain distinct. Samples stay instantaneous until the
existing causal-hold alignment. Datetime strings require explicit offsets unless a
fixed offset is expressly supplied. No named-zone/DST rule is inferred from metadata.
An explicit offset can disambiguate repeated wall times. Units and clock conventions
still need actual source review.

The source callback is invoked only after both existing role claims have committed.
Its errors and malformed source cells produce generic messages without exception
cause or context. A consumed or failed preparation cannot reopen the source. This
is trusted Python preparation, not an OS privacy boundary. Native callers still own
their process and traceback frames.

Thirty-nine parser tests cover source identities, mixed support, gaps, causal delays,
DST offsets, units, missingness, quality, malformed input, bounds and custody ordering.
The broader solar regression passed 93 tests. The authored end-to-end case produces
12 development intervals and four reserved intervals. The source and reserved
artifacts stay in the test's trusted temporary scopes. Only its public normalized
bundle and metadata are copied here. No actual PVDAQ observation file was accessed.
The first fixture failed because strict records reject empty string tokens. Explicit
blank-value and blank-quality policies fixed that representation without relaxing
the shared serializer.

A fresh guarded reader initialized checkout modules, checked parser/CSV-plan pins,
then reconstructed the public bundle with outside reads, writes, new imports,
processes, network and clocks denied. It verified four fitting and four selection
score rows without reading raw CSV or reserved artifacts. This is a checkout reader,
not installed-package or fresh-environment qualification.

Site 2107 still lacks qualified timestamp support, availability, equipment joins,
string topology and physical parameters. This parser does not resolve those facts,
exposure, rights, scientific-model admission or protected execution. No model,
fitting, scoring, provider, data acquisition, reserved-period observation or dependency
installation ran. All 224 core and 315 frozen guest Python sources remain unchanged.
No task dossier, independent partition or absolute useful-gain margin was admitted.
