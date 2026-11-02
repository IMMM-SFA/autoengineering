# CAMELS local archive membership

[The archive verifier](../../examples/utility/hydrology_camels_archive.py) now
checks that the two exact declared basin members occur in an existing local
archive whose complete SHA-256 matches the version-2 source descriptor. It does
not acquire or authenticate provider data. No real archive or observations were
opened for this increment.

Trusted preparation supplies an open regular binary file, exact metadata bytes,
a bound source/plan and a prospective archive-byte cap. The verifier checks
metadata identity and file size before hashing. It checks archive identity before
constructing `ZipFile`, then bounds the central directory to 16 MiB and 20,000
entries. The caller's archive cap cannot exceed 32 GiB. These are supported
implementation limits, not measured source sizes or approved scientific budgets.
A progress callback receives cumulative bytes hashed.

Ordinary and ZIP64 single-volume archives with stored or deflated selected
members are supported. Selected members have a 4 MiB decompressed limit each.
Duplicate names, split volumes, unsupported selected compression, encrypted or
nonregular selected entries, appended bytes and inconsistent directory records
are refused. Only the two exact source paths are decompressed. Unrelated entries
are not opened or written to disk. An unrelated traversal name cannot choose an
output path because the verifier never extracts files. The member reader checks
CRC and the existing parser checks member hashes, dates, units and frozen axis.
File identity is checked again after parsing to detect ordinary concurrent changes.
This is trusted local preparation, not protection against an adversary controlling
the same file handle or host.

The tested preparation pattern defers archive reads until the existing preparer
has committed its claims:

```python
receipts = []


def rows():
    receipt, private_rows = read_archive_rows(
        source,
        plan,
        archive_handle,
        metadata_bytes,
        max_archive_bytes=frozen_archive_cap,
        progress=report_archive_bytes,
    )
    receipts.append(receipt)
    yield from private_rows


manifest = prepare(plan, rows(), public_directory, private_directory)
```

The caller must preserve the receipt in its own authorized preparation record.
The verifier does not choose a destination or write logs containing private rows.
Returned rows include observations and must remain in trusted preparation.
The receipt contains source/member hashes and counts, with no labels or dates.
It records local membership as verified while provider authenticity, physical
intervals, rights/exposure and protected execution remain unadmitted. The
original source descriptor and plan identity do not change.

Cost fields count complete-archive bytes hashed and selected bytes decompressed.
They do not measure total I/O, CPU, peak RSS, network transfer or failed-attempt
work. Repeating a read is additional work. This helper supplies no retry,
confirmation authorization or OS boundary and does not produce a scientific score.
The real source still requires the rights, timing, quality and exposure evidence
listed in the [current admission decision](part-5-current-admission.md).

The authored regression includes ordinary/ZIP64 parity, claim-before-read
preparation, label separation, changed archive/metadata/member checks, missing and
duplicate members, symlink entries, unsupported compression, oversized directory
and compressed member declarations, CRC corruption, concurrent mutation and
receipt reconstruction. This is software evidence only. The local membership
path has not yet been exercised on an acquired CAMELS archive.

The [saved verification](../../examples/utility/verification-camels-archive-v1/README.md)
records 112 passing focused tests, 19 final documentation checks and passing lint.
The four task dossiers, proposal and all 239 prior core-wheel input pins are
unchanged. The full default suite was not rerun for this example-only increment.
