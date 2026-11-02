# Offline inference inputs with candidate stdio bootstrap

This package pins the current lock and pure project wheel, including the fixed
stdin/stdout guest bootstrap. Its identity is
`9402879f689a26da4dcb07573e3f007efbc7cd4fa3451f6e0c41ae40667f0966`.
The wheel contains 217 core Python files and 307 Python sources overall. All core
files match the copied build inputs exactly. The 49 Linux x86-64 archive pins are
unchanged from the two preserved packages, totaling 265,399,717 compressed bytes.

Preparation reconstructed metadata offline. It fetched, installed and extracted
no dependency archive, built no image, started no container and accessed no
independent data. Dependency constraints were not independently re-solved or
rechecked. `starts_authorized` and `runtime_qualified` remain false. The older
packages remain unchanged and still verify against their original identities.

The candidate stdin policy uses the fixed bootstrap to load inputs into its own
workspace and return results before exit. Actual daemon attach/start, framing,
deadlines, watchdog cleanup and OS/privacy/resource enforcement still require
qualification. No default executor or confirmation service activates this path.
The extracted-wheel cold-reader check used inherited host dependencies; it does
not establish an installed or Linux environment.

Build inputs, raw logs, preserved/successor identities and source snapshots are in
[bootstrap verification](../verification-guest-bootstrap-v1/README.md).
