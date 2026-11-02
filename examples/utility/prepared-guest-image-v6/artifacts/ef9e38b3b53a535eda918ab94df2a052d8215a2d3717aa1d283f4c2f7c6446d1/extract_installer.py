"""Run only inside the authorized image build after archive hash verification."""
from pathlib import Path
import tarfile
with tarfile.open('/build/installer/micromamba-2.9.0-0.tar.bz2', 'r:bz2') as archive:
    members = archive.getmembers()
    if len(members) > 1024 or sum(m.size for m in members) > 64 * 1024 * 1024:
        raise ValueError('installer archive exceeds its extraction envelope')
    selected = [m for m in members if m.name == 'bin/micromamba']
    if len(selected) != 1 or not selected[0].isfile() or selected[0].size > 32 * 1024 * 1024:
        raise ValueError('installer executable differs from reviewed archive layout')
    with archive.extractfile(selected[0]) as stream:
        content = stream.read(32 * 1024 * 1024 + 1)
    if len(content) != selected[0].size:
        raise ValueError('installer executable size differs')
path = Path('/build/micromamba')
with path.open('xb') as stream:
    stream.write(content)
path.chmod(0o555)
