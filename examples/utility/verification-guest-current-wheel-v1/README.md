# Current guest wheel and offline readers

The copied-input offline build contains the current 224 core Python files and
314 packaged Python sources. All core wheel source bytes match the checkout.
The 355 build input hashes are retained in `wheel-source-pins.json`.

`build-inputs.py.txt` calls the existing setuptools backend on copied files in a
fresh temporary directory. It performs no dependency resolution or installation.
The wheel SHA-256 is
`2bcd32d9f0488aa85ec6e89e3bf243266380ba4b69daebc26347ce7eb58af44a`.

`replay-wheel.py.txt` extracts that wheel outside the checkout, starts isolated
interpreters and checks that package imports come from the extraction. The
original cleanup reader, guest composite score/cost reader and CLI help all exit
zero. The two original readers enforce their process/network/model/clock/array
and file-access guards. Existing interpreter dependencies remain available.
This is extracted-wheel evidence, not an installed-package qualification.

The successor prepared input manifest is
`../prepared-inference-environment-v4/manifest.json`, digest
`503d6d86b3ec113853ab5a64cc7a4ea8f6df277087639462e73a2a4f5702b808`.
All three earlier prepared manifests still verify. The same 49 locked Linux
archives total 265,399,717 compressed bytes. They were not acquired or installed.
Uncompressed size, compatibility and dependency constraints remain unqualified.
No image was built and no runtime was exercised. `starts_authorized` and
`runtime_qualified` remain false.

Actual installation, macOS/Linux execution qualification, runtime/privacy,
second-host checks, independent task admission, approved thresholds and the
frozen scientific comparison remain open. The full default tests were not rerun.
Part 5 remains incomplete.
