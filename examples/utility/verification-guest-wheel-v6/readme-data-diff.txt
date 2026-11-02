--- v5/examples/utility/README.md
+++ current/examples/utility/README.md
@@ -265,3 +265,39 @@
 [prepared package](prepared-inference-environment-v1/README.md) for its exact hashes,
 size, proposed resource bounds and unresolved image/guest/boundary requirements.
 This is an administrative preparation tool; it does not register a private runtime.
+
+
+[guest_image.py](guest_image.py) prepares a source-matched, pinned image recipe
+without fetching or running it. See the [candidate image package](prepared-guest-image-v1/README.md)
+for payload bounds, immutable public metadata, unrun qualification cases and
+missing execution prerequisites. This does not admit an inference runtime.
+
+
+[guest_image_context.py](guest_image_context.py) materializes a reviewed recipe from
+already-present pinned files and verifies its relocated closure. It does not fetch
+or build anything. See the [context verification](verification-guest-image-context-v1/README.md)
+for authored test scope and the missing production inputs.
+
+
+[guest_archive_download.py](guest_archive_download.py) prepares and executes pinned
+archive-only requests with no automatic retries, installation or image execution.
+[Actual acquisition evidence](verification-guest-archive-download-v1/README.md)
+records the verified local archive cache and materialized production context.
+
+
+[guest_image_build.py](guest_image_build.py) prepares a pinned local candidate-image
+job. [The prepared request](prepared-guest-build-v1/README.md) requires separate
+approval for base-image acquisition and image assembly. It does not run scientific
+confirmation or admit the runtime.
+
+
+The bundled authored source CSV example runs without models or source acquisition:
+
+```sh
+pixi run python -m examples.utility.solar_csv_demo --output outputs/solar-csv-demo
+```
+
+Use a new output directory. The example exercises explicit source/clock/quality
+policies and separated preparation. Its public authored values do not establish
+site semantics or independent confirmation. See
+[installed evidence](verification-solar-csv-installed-v1/README.md).
