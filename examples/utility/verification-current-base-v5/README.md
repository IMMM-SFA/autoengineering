# Current default verification

The complete default suite passed with 3,415 passed and 120 skipped in
3,143.14 seconds. JUnit records 3,535 entries with zero failures and zero errors.
The entries include seven module-level skips beyond the 3,528 collected tests.

[Verified summary](verified-summary.json) records the counts, source checks,
artifact hashes and limits. All 603 pinned files matched. The 224 core and 243
test Python files had no additions or removals. All 12 cases that failed or
errored in v4 passed in this complete unchanged-source run.

[Launch arguments](launch.json), [source pins](source-pins.json),
[pytest output](pytest.log), [JUnit](junit.xml) and
[completion](completion.json) retain the run evidence. A PID-scoped idle-sleep
inhibitor ran from launch until pytest exited. Both processes subsequently
exited. Host observations record no newer kernel wake at the sampled time.
This supports a timing hypothesis for the earlier failures without proving
their individual causes. The v4 logs, JUnit, observations and reproductions
remain available; its original temporary fixture directory is absent.

This check covers the recorded macOS ARM64 default environment. It does not
qualify optional environments, package installation, Linux execution, a private
runtime, live providers or independent scientific confirmation. No image build
or frozen benchmark matrix ran. The prepared image-build request remains pending.
