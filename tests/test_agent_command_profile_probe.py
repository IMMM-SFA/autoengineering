"""A sandbox startup failure must never be counted as a successful privacy denial."""

from types import SimpleNamespace

from examples.agent_campaign.probe_command_profile import command_passed


def result(stderr, *, stdout=b"", stopped=True, truncated=False, returncode=1):
    return SimpleNamespace(
        stderr=stderr, stdout=stdout, stopped=stopped, truncated=truncated, returncode=returncode
    )


def test_setup_failure_is_distinct_from_an_actual_file_access_denial():
    command = ("/bin/cat", "/private/canary")
    options = dict(readable=False, public=b"approved-marker", secret=b"secret-marker")
    assert not command_passed(
        result(b"sandbox-exec: sandbox_apply: Operation not permitted\n"), command, **options
    )
    assert not command_passed(
        result(b"cat: /different/path: Operation not permitted\n"), command, **options
    )
    assert command_passed(
        result(b"cat: /private/canary: Operation not permitted\n"), command, **options
    )


def test_privacy_probe_rejects_leaks_unstopped_processes_and_truncated_output():
    command = ("/bin/cat", "/private/canary")
    options = dict(readable=False, public=b"approved-marker", secret=b"secret-marker")
    denial = b"cat: /private/canary: Operation not permitted\n"
    assert not command_passed(result(denial, stdout=b"secret-marker"), command, **options)
    assert not command_passed(result(denial + b"secret-marker"), command, **options)
    assert not command_passed(result(denial, stopped=False), command, **options)
    assert not command_passed(result(denial, truncated=True), command, **options)
    assert command_passed(
        result(b"", stdout=b"approved-marker", returncode=0),
        command,
        readable=True,
        public=b"approved-marker",
        secret=b"secret-marker",
    )
