"""Authored archives test bounded byte membership, not source admission."""

from dataclasses import replace
import hashlib
import io
import struct
import warnings
import zipfile

import pytest

from examples.utility.hydrology_camels_archive import read_archive_rows
from examples.utility.hydrology_partitions import prepare
from test_utility_hydrology_camels import archive_source, fixture


def make_archive(tmp_path, *, entries=None, compression=zipfile.ZIP_DEFLATED, zip64=False):
    original, plan, forcing, flow = fixture()
    source = archive_source(original)
    entries = entries or [(source.forcing_member, forcing), (source.streamflow_member, flow)]
    path = tmp_path / "authored.zip"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(path, "w", compression=compression) as archive:
            for name, value in entries:
                archive.writestr(name, value)
    if zip64:
        # Authored ordinary central directory with a valid ZIP64 end/locator.
        data = path.read_bytes()
        end = struct.unpack("<4s4H2IH", data[-22:])
        record = struct.pack(
            "<4sQ2H2I4Q", b"PK\x06\x06", 44, 45, 45, 0, 0, end[3], end[4], end[5], end[6]
        )
        locator = struct.pack("<4sIQI", b"PK\x06\x07", 0, len(data) - 22, 1)
        sentinel = struct.pack(
            "<4s4H2IH", b"PK\x05\x06", 0, 0, 65535, 65535, 2**32 - 1, 2**32 - 1, 0
        )
        path.write_bytes(data[:-22] + record + locator + sentinel)
    metadata = b"authored archive metadata; not provider authentication"
    source = replace(
        source,
        archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        archive_metadata_sha256=hashlib.sha256(metadata).hexdigest(),
    )
    return source, replace(plan, declared_source_digest=source.digest), path, metadata


def run(inputs, **kwargs):
    source, plan, path, metadata = inputs
    with path.open("rb") as handle:
        return read_archive_rows(
            source, plan, handle, metadata, max_archive_bytes=path.stat().st_size, **kwargs
        )


@pytest.mark.parametrize("compression", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
@pytest.mark.parametrize("zip64", [False, True])
def test_exact_members_roundtrip_without_admission(tmp_path, compression, zip64):
    inputs = make_archive(tmp_path, compression=compression, zip64=zip64)
    progress = []
    receipt, rows = run(inputs, progress=progress.append)
    assert len(rows) == 8 and rows[-1].flow_cfs == 876543.210987
    assert receipt.archive_membership_verified is True
    assert receipt.source_authenticity_admitted is False
    assert receipt.physical_intervals_admitted is False
    assert receipt.rights_and_exposure_admitted is False
    assert receipt.protected_execution_qualified is False
    assert receipt.source_digest == inputs[0].digest
    assert progress[-1] == receipt.archive_bytes_hashed == inputs[2].stat().st_size
    assert b"876543.210987" not in receipt.to_json().encode()
    assert set(p.name for p in tmp_path.iterdir()) == {"authored.zip"}


def test_preparation_claim_precedes_archive_read(tmp_path):
    inputs = make_archive(tmp_path)
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    receipts = []

    def rows():
        assert (public / "preparation-claim.json").is_file()
        assert (private / "preparation-claim.json").is_file()
        receipt, values = run(inputs)
        receipts.append(receipt)
        yield from values

    result = prepare(inputs[1], rows(), public, private)
    assert len(receipts) == 1
    assert result["scientific_adapter_admitted"] is False
    assert b"876543.210987" not in b"".join(p.read_bytes() for p in public.iterdir())


@pytest.mark.parametrize(
    "change",
    [
        "archive",
        "metadata",
        "plan",
        "member",
        "missing",
        "duplicate",
        "symlink",
        "compression",
        "directory",
        "trailer",
        "split",
    ],
)
def test_invalid_archive_refuses_sanitized(tmp_path, change):
    original, _, forcing, flow = fixture()
    template = archive_source(original)
    entries = [(template.forcing_member, forcing), (template.streamflow_member, flow)]
    if change == "member":
        entries[1] = (entries[1][0], flow + b"PRIVATE-ERROR-CANARY")
    elif change == "missing":
        entries[0] = ("wrong/path.txt", forcing)
    elif change == "duplicate":
        entries.append(entries[0])
    elif change == "symlink":
        info = zipfile.ZipInfo(template.forcing_member)
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        entries[0] = (info, forcing)
    inputs = make_archive(
        tmp_path,
        entries=entries,
        compression=zipfile.ZIP_BZIP2 if change == "compression" else zipfile.ZIP_DEFLATED,
    )
    source, plan, path, metadata = inputs
    if change == "archive":
        path.write_bytes(path.read_bytes() + b"PRIVATE-ERROR-CANARY")
    elif change == "metadata":
        metadata += b"PRIVATE-ERROR-CANARY"
    elif change == "plan":
        plan = replace(plan, declared_source_digest="c" * 64)
    elif change in ("directory", "trailer", "split"):
        data = bytearray(path.read_bytes())
        if change == "directory":
            struct.pack_into("<I", data, len(data) - 10, 17 * 1024**2)
        elif change == "split":
            struct.pack_into("<H", data, len(data) - 18, 1)
        else:
            data += b"appended data"
        path.write_bytes(data)
        source = replace(source, archive_sha256=hashlib.sha256(data).hexdigest())
        plan = replace(plan, declared_source_digest=source.digest)
    with pytest.raises(ValueError, match="^CAMELS archive verification failed$") as error:
        run((source, plan, path, metadata))
    assert error.value.__suppress_context__
    assert "PRIVATE" not in str(error.value)


def test_archive_size_refuses_before_hash_or_zip(tmp_path, monkeypatch):
    import examples.utility.hydrology_camels_archive as module

    source, plan, path, metadata = make_archive(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("oversized archive reached directory decoding")

    monkeypatch.setattr(module, "_directory_bound", forbidden)
    with path.open("rb") as handle, pytest.raises(ValueError):
        read_archive_rows(source, plan, handle, metadata, max_archive_bytes=1)
    with pytest.raises(ValueError):
        read_archive_rows(
            source,
            plan,
            io.BytesIO(path.read_bytes()),
            metadata,
            max_archive_bytes=path.stat().st_size,
        )


def test_selected_bomb_refuses_before_decompression(tmp_path, monkeypatch):
    import examples.utility.hydrology_camels_archive as module

    original, _, _, flow = fixture()
    source = archive_source(original)
    inputs = make_archive(
        tmp_path,
        entries=[
            (source.forcing_member, b"0" * (module.MAX_BYTES + 1)),
            (source.streamflow_member, flow),
        ],
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("oversized selected member reached decompression")

    monkeypatch.setattr(zipfile.ZipFile, "open", forbidden)
    with pytest.raises(ValueError):
        run(inputs)


def test_unrelated_member_never_opened(tmp_path, monkeypatch):
    original, _, forcing, flow = fixture()
    source = archive_source(original)
    inputs = make_archive(
        tmp_path,
        entries=[
            (source.forcing_member, forcing),
            (source.streamflow_member, flow),
            ("../unrelated", b"not selected"),
        ],
    )
    opened = []
    original_open = zipfile.ZipFile.open

    def guarded(self, name, *args, **kwargs):
        opened.append(name.filename)
        assert name.filename in (source.forcing_member, source.streamflow_member)
        return original_open(self, name, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "open", guarded)
    receipt, _ = run(inputs)
    assert receipt.archive_membership_verified and len(opened) == 2


def test_changed_archive_during_hash_refuses(tmp_path):
    inputs = make_archive(tmp_path)

    def mutate(total):
        with inputs[2].open("ab") as writer:
            writer.write(b"changed")

    with pytest.raises(ValueError):
        run(inputs, progress=mutate)


def test_crc_corruption_refuses_even_with_new_archive_hash(tmp_path):
    source, plan, path, metadata = make_archive(tmp_path, compression=zipfile.ZIP_STORED)
    raw = path.read_bytes()
    assert b"876543.210987" in raw
    raw = raw.replace(b"876543.210987", b"976543.210987")
    path.write_bytes(raw)
    source = replace(source, archive_sha256=hashlib.sha256(raw).hexdigest())
    plan = replace(plan, declared_source_digest=source.digest)
    with pytest.raises(ValueError):
        run((source, plan, path, metadata))


def test_bad_archive_hash_never_opens_directory(tmp_path, monkeypatch):
    import examples.utility.hydrology_camels_archive as module

    inputs = make_archive(tmp_path)
    inputs[2].write_bytes(inputs[2].read_bytes() + b"changed")

    def forbidden(*args, **kwargs):
        raise AssertionError("checksum failure reached archive parsing")

    monkeypatch.setattr(module, "_directory_bound", forbidden)
    with pytest.raises(ValueError):
        run(inputs)


def test_receipt_roundtrip_rejects_invented_admission_and_bad_counts(tmp_path):
    from examples.utility.hydrology_camels_archive import CamelsArchiveVerification

    receipt, _ = run(make_archive(tmp_path))
    assert CamelsArchiveVerification.from_json(receipt.to_json()) == receipt
    for change in (
        {"source_authenticity_admitted": True},
        {"archive_bytes_hashed": 0},
        {"member_bytes_decompressed": -1},
        {"source_digest": "not-a-hash"},
    ):
        with pytest.raises(ValueError):
            replace(receipt, **change)
