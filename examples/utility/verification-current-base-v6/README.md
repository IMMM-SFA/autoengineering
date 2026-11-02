# Current default regression checkpoint

The full source-pinned run finished with 4,047 passed, 122 skipped and one failure
in 3,063.46 seconds of pytest time. Its original exit code is 1. Every one of
11,997 pinned files remained unchanged. The current source sets contain 225 core
and 287 test Python files.

The failure is `TestRunComponent.test_command_kind_npz_contract`. Its shell command
invokes bare `python`. The launch used an absolute pytest interpreter without
putting that interpreter's directory on child PATH. The captured error is
`/bin/sh: python: command not found`, exit 127.

Exactly that case passed in a fresh temporary scope after placing the project
interpreter on child PATH. A fresh bytecode lookup prefix was used. No test or
production source changed. The first recheck wrapper stopped before starting a
test because it misparsed the JUnit class name; its source and refusal are saved.
The corrected wrapper and terminal records remain separate.

[Verified summary](verified-summary.json) reconciles 4,048 unique non-skipped cases
with passing evidence and 122 skips across the original run and one-case recheck.
This is not a single clean full-suite pass. The original log, failed JUnit,
completion, source pins and recheck outputs are retained. Future full runs should
activate Pixi or explicitly configure child PATH. Do not rerun either consumed
scope or overwrite these records.

This checkpoint tests software on local authored fixtures and available optional
profiles. It does not admit independent data, qualify an updated guest image or
complete Part 5. No frozen research benchmark matrix was rerun.
