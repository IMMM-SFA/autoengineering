# Historical release inputs

The content-addressed files in `source-sha256/` preserve the exact 0.1.0 package
initializer and Pixi manifest recorded in the original open-chain results.
They were copied from commit `d2fe5b4` before the 0.2.0 version bump.

Verification checks each snapshot against the unchanged result manifest hash.
Only the version assignment may differ in the current file. Any other source,
dependency, or artifact difference still fails verification. This verifies the
historical run and metadata-only release transition, not a new model execution.
