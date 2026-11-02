# Pinned runtime archive acquisition and production context

The archive-only tool request completed 50 GETs for 49 locked packages and one
micromamba installer archive. Each file passed its exact length and SHA-256 pin.
The transfer read 272,387,807 application payload bytes in 8.871 seconds. It had
no redirects or retries. Tool approval review allowed this bounded archive-only
action. No installer, image, daemon, container or scientific model ran.

Request pin:
`cccaecc7393ece16742fb30b1ba0c702e29ff16cc87456cf348b4e61431cc2f0`.
Completed-cache pin:
`cd89e6cb04b26261960045de4ee6d7e807f50f10a77c77e9aa3ccef21cc3b0d8`.

The local cache is `outputs/guest-runtime-archives-v1` from the repository root.
The production context at `outputs/guest-build-context-v1` copies 275,243,466
pinned file bytes, including its metadata proof. Its pin is
`0e523c9b2dd0cc9bbc01bea14b185db87f14e982a495f5960b1c082804df2cce`.
Both directories are private and ignored by Git. Dependency locks and historical
results were preserved. Completion metadata is retained here without copying the
large archives into the review artifact.

## Verification

The final archive/context/image/environment check passed 85 cases in 3.12 seconds.
It covers framing, truncation, hashes, lost responses, interruption, original
expiry, exact evidence closure, source/scope identity and completed-cache replay.
Unit HTTP streams are authored and do not contact the public service.

A fresh isolated administrative reader verified copied real archives and the real
context outside the checkout. After code initialization, an audit guard denied
file reads outside the relocated scope and all writes. Processes, sockets, clocks,
array loads and source probes were denied. Original directories were retained for
later build preparation but could not be read through the guard. This is source
reader evidence, not installed-helper or runtime qualification.

Installer tar headers identify one regular `bin/micromamba` member of 18,292,808
bytes among 58 members and 18,553,507 declared uncompressed bytes. This meets the
recipe's extraction envelope. No file was extracted or executed. The whole
environment's unpacked size and compatibility remain unknown.

## Bounds and remaining work

The downloader fixes its target scope/source and persists request/GET intents
before HTTP work. A consumed cache cannot be resumed or retried automatically.
It accepts only the pinned public HTTPS origin, identity encoding and exact
Content-Length framing. No redirect or fallback origin is permitted. Completed
bytes are committed only after hash verification. Partial files and original
failure evidence are retained. A lost final acknowledgement replays the original
completion instead of issuing more GETs.

The request has a 1,200-second deadline checked at request, read and publication
boundaries and a 30-second socket timeout. These do not establish a hard bound on
synchronous filesystem calls. Payload-byte counts exclude HTTP/TLS/DNS overhead.
No authority for installation, base-image acquisition, build or execution follows
from this archive request. Existing image-plan authority fields remain unchanged.

A bounded build runner, cached base-image validation/acquisition authority, actual
daemon handlers and diagnostic profiles remain required. Installed/platform/host,
runtime/privacy and independent scientific qualification remain open. The new
host helpers are outside the preceding 315-source wheel scope. The full default
suite was not rerun. Part 5 remains incomplete.
