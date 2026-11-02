"""Verify two declared CAMELS members in an existing seekable archive.

Trusted preparation only. No acquisition, extraction to disk, scientific admission
or execution boundary is supplied. The caller owns the open regular-file handle
and must keep it separate from workers and holdout-visible diagnostics.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import stat
import struct
from typing import BinaryIO, Callable, Literal
import zipfile

from autoengineering.campaign.serialization import Record
from autoengineering.utility.contracts import sha256
from examples.utility.hydrology_camels import CamelsArchiveDaymetSource, MAX_BYTES, iter_rows
from examples.utility.hydrology_partitions import DailyHydrologyPlan, DailyHydrologyRow

MAX_ARCHIVE_BYTES = 32 * 1024**3
MAX_DIRECTORY_BYTES = 16 * 1024**2
MAX_MEMBERS = 20000
MAX_METADATA_BYTES = 1024**2
CHUNK_BYTES = 1024**2


@dataclass(frozen=True)
class CamelsArchiveVerification(Record):
    schema: Literal["utility-camels-archive-membership-v1"]
    source_digest: str
    archive_sha256: str
    archive_metadata_sha256: str
    archive_bytes_hashed: int
    forcing_sha256: str
    streamflow_sha256: str
    member_bytes_decompressed: int
    archive_membership_verified: Literal[True] = True
    source_authenticity_admitted: Literal[False] = False
    physical_intervals_admitted: Literal[False] = False
    rights_and_exposure_admitted: Literal[False] = False
    protected_execution_qualified: Literal[False] = False

    def _validate(self):
        for value in (
            self.source_digest,
            self.archive_sha256,
            self.archive_metadata_sha256,
            self.forcing_sha256,
            self.streamflow_sha256,
        ):
            sha256(value)
        if not 0 < self.archive_bytes_hashed <= MAX_ARCHIVE_BYTES:
            raise ValueError("archive byte count bound")
        if not 0 < self.member_bytes_decompressed <= 2 * MAX_BYTES:
            raise ValueError("selected member byte count bound")


def _identity(handle):
    value = os.fstat(handle.fileno())
    if not stat.S_ISREG(value.st_mode):
        raise ValueError("regular archive required")
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


def _read_at(handle, offset, length):
    if offset < 0:
        raise ValueError("invalid archive offset")
    handle.seek(offset)
    value = handle.read(length)
    if len(value) != length:
        raise ValueError("incomplete archive structure")
    return value


def _directory_bound(handle, size):
    """Bound ZipFile's central-directory allocation before constructing it.

    Accept ordinary and ZIP64 single-volume archives, including comments. Refuse
    appended data, split volumes and a ZIP64 extensible data sector over 4 KiB.
    """
    length = min(size, 22 + 65535)
    tail = _read_at(handle, size - length, length)
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0 or len(tail) - offset < 22:
        raise ValueError("missing end record")
    end = struct.unpack("<4s4H2IH", tail[offset : offset + 22])
    if offset + 22 + end[7] != len(tail) or end[1:3] != (0, 0):
        raise ValueError("unsupported archive trailer")
    count, directory_size, directory_offset = end[4:7]
    boundary = size - length + offset
    if boundary >= 20 and _read_at(handle, boundary - 20, 4) == b"PK\x06\x07":
        locator = struct.unpack("<4sIQI", _read_at(handle, boundary - 20, 20))
        if locator[1] != 0 or locator[3] != 1:
            raise ValueError("split ZIP64 archive")
        record = struct.unpack("<4sQ2H2I4Q", _read_at(handle, locator[2], 56))
        if (
            record[0] != b"PK\x06\x06"
            or not 44 <= record[1] <= 4096
            or locator[2] + 12 + record[1] != boundary - 20
            or record[4:6] != (0, 0)
            or record[6] != record[7]
        ):
            raise ValueError("invalid ZIP64 directory")
        for old, new, sentinel in zip(end[3:7], record[6:10], (65535, 65535, 2**32 - 1, 2**32 - 1)):
            if old not in (sentinel, new):
                raise ValueError("inconsistent ZIP64 counts")
        count, directory_size, directory_offset = record[7:10]
        boundary = locator[2]
    elif end[3] != count or 65535 in end[3:5] or 2**32 - 1 in end[5:7]:
        raise ValueError("missing or split ZIP64 directory")
    if (
        not 2 <= count <= MAX_MEMBERS
        or not 0 < directory_size <= MAX_DIRECTORY_BYTES
        or directory_offset + directory_size != boundary
    ):
        raise ValueError("archive directory bound")
    return count


def _member(archive, name):
    info = archive.getinfo(name)
    mode = info.external_attr >> 16
    if (
        info.is_dir()
        or stat.S_ISLNK(mode)
        or (stat.S_IFMT(mode) and not stat.S_ISREG(mode))
        or info.flag_bits & 1
        or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
        or not 0 < info.file_size <= MAX_BYTES
        or not 0 <= info.compress_size <= MAX_BYTES + 65536
    ):
        raise ValueError("unsupported selected member")
    with archive.open(info) as reader:
        value = reader.read(MAX_BYTES + 1)
    if len(value) != info.file_size:
        raise ValueError("member length differs")
    return value


def read_archive_rows(
    source: CamelsArchiveDaymetSource,
    plan: DailyHydrologyPlan,
    handle: BinaryIO,
    metadata: bytes,
    *,
    max_archive_bytes: int,
    progress: Callable[[int], None] | None = None,
) -> tuple[CamelsArchiveVerification, tuple[DailyHydrologyRow, ...]]:
    """Hash a complete local archive, then parse only the two exact member names.

    Freeze the byte cap and source/metadata digests before opening observations.
    Progress reports cumulative archive bytes hashed, never rows or member names.
    Returned rows include labels and belong only in trusted preparation. Use the
    existing partition preparer to seal roles. A receipt proves local byte
    membership, not provider authenticity, timing, rights, exposure or custody.
    Archive hashing is metered here; other I/O, CPU and RSS are not total costs.
    """
    try:
        if not isinstance(source, CamelsArchiveDaymetSource) or not isinstance(
            plan, DailyHydrologyPlan
        ):
            raise ValueError("versioned source and plan required")
        if (
            plan.declared_source_digest != source.digest
            or plan.site_id != f"usgs-{source.gauge_id}"
        ):
            raise ValueError("source and plan differ")
        if (
            type(max_archive_bytes) is not int
            or not 0 < max_archive_bytes <= MAX_ARCHIVE_BYTES
            or type(metadata) is not bytes
            or not 0 < len(metadata) <= MAX_METADATA_BYTES
            or hashlib.sha256(metadata).hexdigest() != source.archive_metadata_sha256
        ):
            raise ValueError("archive or metadata bound")
        before = _identity(handle)
        size = before[2]
        if not 0 < size <= max_archive_bytes:
            raise ValueError("archive size bound")
        handle.seek(0)
        digest = hashlib.sha256()
        total = 0
        while total < size:
            chunk = handle.read(min(CHUNK_BYTES, size - total))
            if not chunk:
                raise ValueError("incomplete archive")
            digest.update(chunk)
            total += len(chunk)
            if progress is not None:
                progress(total)
        if digest.hexdigest() != source.archive_sha256 or _identity(handle) != before:
            raise ValueError("archive identity differs")
        count = _directory_bound(handle, size)
        with zipfile.ZipFile(handle) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(infos) != count or len(set(names)) != len(names):
                raise ValueError("duplicate or inconsistent members")
            forcing = _member(archive, source.forcing_member)
            flow = _member(archive, source.streamflow_member)
        rows = tuple(iter_rows(source, plan, forcing, flow))
        if _identity(handle) != before:
            raise ValueError("archive changed during parsing")
        receipt = CamelsArchiveVerification(
            "utility-camels-archive-membership-v1",
            source.digest,
            source.archive_sha256,
            source.archive_metadata_sha256,
            total,
            source.forcing_sha256,
            source.streamflow_sha256,
            len(forcing) + len(flow),
        )
        return receipt, rows
    except Exception:
        raise ValueError("CAMELS archive verification failed") from None
