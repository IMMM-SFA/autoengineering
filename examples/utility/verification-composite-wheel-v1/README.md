# Extracted composite wheel reader check

The wheel contains 211 core Python files with exact source parity. Its 340 copied
build inputs are pinned in source-pins.json. No package or dependency was installed.
The build frontend was unavailable; the existing setuptools backend built the wheel
without isolation or network access. Both build attempts are preserved.

The authored public fixture supports cold composite replay, cost reconstruction
and the actual utility report/verify CLI. Guards reject model/optional imports,
array loads, optimizer/process/network calls, private/original scope reads and
public writes. All 329 public files retain their hashes. Report verification keeps
complete cost evidence false. Authored execution metadata is not a container or
OS privacy attestation.

The transported check used a fresh temporary directory. It extracted the wheel
into unpacked, extracted authored-public-suite.tar.gz into public-suite, and copied
cold-cli.py.txt alongside those directories. It then ran Python 3.12 with -I on
that copied script using the existing base dependencies. The script is saved with
its exact executed bytes; its extension does not affect Python execution.

Verify the file hashes in summary.json before extracting these trusted artifacts.
Use safe tar extraction. Then restore owner-private modes on the new fixture:
0700 for its root and every directory, 0600 for its files. Safe tar extraction
omits directory modes, which caused the first transported attempt to refuse before
verification. The corrected attempt passed without relaxing the store guard.
Keep all extraction in a fresh owner-private directory.

This check covers an extracted wheel reader on macOS ARM64 with inherited base
dependencies. Package installation, preparation/development/resume from the wheel,
optional scientific environments, Linux and another host remain outside its scope.
No independent labels, new image, provider or remote execution was used.

See [summary](summary.json), [transported output](transported-private-fixture.log)
and the [current requirement audit](../../../docs/reviews/part-5-completion-audit.md).
