"""Confirmation CLI uses trusted registrations and the original service journal."""

from dataclasses import replace
import json

from click.testing import CliRunner
import pytest

from autoengineering.cli import cli
from autoengineering.utility.store import SuiteStore
from test_utility_confirmation_recovery import SavedScorer, pending
from test_utility_scoring import H, setup


def command_for(store, grant, scorer, contract, **changes):
    from autoengineering.utility.confirmation_command import (
        ConfirmationRegistration,
        build_confirmation_command,
    )

    scorer.identity = H
    registration = ConfirmationRegistration(
        "authored-fixture",
        store.spec.digest,
        grant.partition_digest,
        H,
        "2" * 64,
        contract,
        scorer,
        True,
    )
    return build_confirmation_command((replace(registration, **changes),))


def invoke(command, store, grant, tmp_path, *extra):
    path = tmp_path / "grant.json"
    path.write_text(grant.to_json())
    return CliRunner().invoke(
        command, [str(store.root), str(path), "--registration", "authored-fixture", *extra]
    )


def test_default_cli_has_confirmation_command_without_admitted_scorers(tmp_path):
    scorer = SavedScorer()
    store, grant, _, _ = setup(tmp_path, scorer)
    path = tmp_path / "grant.json"
    path.write_text(grant.to_json())
    result = CliRunner().invoke(
        cli,
        [
            "utility",
            "confirm",
            str(store.root),
            str(path),
            "--registration",
            "unqualified-container",
        ],
    )
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] == "confirmation_not_admitted_or_invalid"
    assert scorer.calls == 0 and not store.replay()["confirmation_accesses"]


def test_registered_cli_confirms_once_and_replays_without_scorer(tmp_path):
    scorer = SavedScorer()
    store, grant, _, contract = setup(tmp_path, scorer)
    command = command_for(store, grant, scorer, contract)
    result = invoke(command, store, grant, tmp_path)
    assert result.exit_code == 0, result.output
    document = json.loads(result.output)
    assert document["receipt"]["score"]["value"] == 3.0
    assert document["qualification_digest"] == "2" * 64
    before = store.replay()
    replay = invoke(command, store, grant, tmp_path)
    assert replay.exit_code == 0 and scorer.calls == 1
    assert json.loads(replay.output)["receipt"] == document["receipt"]
    assert store.replay()["head"] == before["head"]


def test_cli_recovers_original_charge_and_access(tmp_path):
    store, grant, _, scorer, contract = pending(tmp_path)
    before = store.replay()
    result = invoke(
        command_for(store, grant, scorer, contract), store, grant, tmp_path, "--recover"
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["receipt"]["recovery"] is not None
    after = store.replay()
    assert after["used"] == before["used"] and after["phase_used"] == before["phase_used"]
    assert after["confirmation_accesses"] == before["confirmation_accesses"]
    assert scorer.calls == scorer.recoveries == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"admitted": False},
        {"suite_digest": "3" * 64},
        {"partition_digest": "3" * 64},
        {"scorer_digest": "3" * 64},
    ],
)
def test_unadmitted_or_mismatched_registration_starts_nothing(tmp_path, changes):
    scorer = SavedScorer()
    store, grant, _, contract = setup(tmp_path, scorer)
    before = store.replay()["head"]
    result = invoke(command_for(store, grant, scorer, contract, **changes), store, grant, tmp_path)
    assert result.exit_code == 2
    assert scorer.calls == 0 and store.replay()["head"] == before


def test_uncertain_attempt_never_automatically_retries(tmp_path):
    store, grant, _, scorer, contract = pending(tmp_path)
    before = store.replay()["head"]
    result = invoke(command_for(store, grant, scorer, contract), store, grant, tmp_path)
    assert result.exit_code == 2 and scorer.calls == 1 and scorer.recoveries == 0
    assert store.replay()["head"] == before


def test_recover_cannot_authorize_first_score(tmp_path):
    scorer = SavedScorer()
    store, grant, _, contract = setup(tmp_path, scorer)
    result = invoke(
        command_for(store, grant, scorer, contract), store, grant, tmp_path, "--recover"
    )
    assert result.exit_code == 2 and scorer.calls == scorer.recoveries == 0
    assert not SuiteStore(store.root).replay()["confirmation_accesses"]


def test_changed_qualification_pin_cannot_reuse_original_grant(tmp_path):
    scorer = SavedScorer()
    store, grant, _, contract = setup(tmp_path, scorer)
    command = command_for(store, grant, scorer, contract)
    assert invoke(command, store, grant, tmp_path).exit_code == 0
    before = store.replay()["head"]
    changed = command_for(store, grant, scorer, contract, qualification_digest="4" * 64)
    assert invoke(changed, store, grant, tmp_path).exit_code == 2
    assert scorer.calls == 1 and store.replay()["head"] == before


def test_changed_registered_identity_starts_nothing(tmp_path):
    scorer = SavedScorer()
    store, grant, _, contract = setup(tmp_path, scorer)
    before = store.replay()["head"]
    command = command_for(store, grant, scorer, contract)
    scorer.identity = "PRIVATE-IDENTITY-CANARY"
    result = invoke(command, store, grant, tmp_path)
    assert result.exit_code == 2 and "PRIVATE-IDENTITY-CANARY" not in result.output
    assert scorer.calls == 0 and store.replay()["head"] == before


def test_selection_barrier_is_checked_before_registration_pin(tmp_path):
    scorer = SavedScorer()
    store, grant, _, contract = setup(tmp_path, scorer)
    empty = SuiteStore.create(tmp_path / "unsealed", store.spec)
    result = invoke(command_for(empty, grant, scorer, contract), empty, grant, tmp_path)
    assert result.exit_code == 2 and scorer.calls == 0
    assert not (empty.root / "control/confirmation-registrations").exists()


def test_private_scorer_exception_is_sanitized_and_keeps_charge(tmp_path):
    class PrivateFailure(SavedScorer):
        def __call__(self, *_):
            self.calls += 1
            raise RuntimeError("PRIVATE-SCORE-CANARY /private/path")

    scorer = PrivateFailure()
    store, grant, _, contract = setup(tmp_path, scorer)
    command = command_for(store, grant, scorer, contract)
    result = invoke(command, store, grant, tmp_path)
    assert result.exit_code == 2 and "PRIVATE-SCORE-CANARY" not in result.output
    assert len(store.replay()["confirmation_accesses"]) == 1
    assert invoke(command, store, grant, tmp_path).exit_code == 2
    assert scorer.calls == 1


def test_symlinked_grant_never_reaches_scorer(tmp_path):
    scorer = SavedScorer()
    store, grant, _, contract = setup(tmp_path, scorer)
    before = store.replay()["head"]
    original = tmp_path / "original.json"
    original.write_text(grant.to_json())
    link = tmp_path / "link.json"
    link.symlink_to(original)
    result = CliRunner().invoke(
        command_for(store, grant, scorer, contract),
        [
            str(store.root),
            str(link),
            "--registration",
            "authored-fixture",
        ],
    )
    assert result.exit_code == 2 and scorer.calls == 0
    assert store.replay()["head"] == before


def test_duplicate_and_unknown_grant_fields_are_rejected(tmp_path):
    scorer = SavedScorer()
    store, grant, _, contract = setup(tmp_path, scorer)
    before = store.replay()["head"]
    command = command_for(store, grant, scorer, contract)
    for raw in (
        grant.to_json()[:-1] + ',"private":"DO-NOT-PRINT"}',
        '{"suite_digest":"DO-NOT-PRINT",' + grant.to_json()[1:],
    ):
        path = tmp_path / "invalid.json"
        path.write_text(raw)
        result = CliRunner().invoke(
            command, [str(store.root), str(path), "--registration", "authored-fixture"]
        )
        assert result.exit_code == 2 and "DO-NOT-PRINT" not in result.output
    assert scorer.calls == 0 and store.replay()["head"] == before


def test_duplicate_registration_ids_are_rejected(tmp_path):
    from autoengineering.utility.confirmation_command import (
        ConfirmationRegistration,
        build_confirmation_command,
    )

    scorer = SavedScorer()
    store, grant, _, contract = setup(tmp_path, scorer)
    registration = ConfirmationRegistration(
        "fixture", store.spec.digest, grant.partition_digest, H, "2" * 64, contract, scorer, True
    )
    with pytest.raises(ValueError, match="duplicate"):
        build_confirmation_command((registration, registration))


def test_recovery_still_settles_cancelled_suite_without_new_work(tmp_path):
    store, grant, _, scorer, contract = pending(tmp_path)
    with store.writer():
        store.append(
            request_id="cancel-cli-fixture",
            operation="cancel",
            cell_digest=grant.cell_digest,
            attempt_id="suite-cancel",
            child_digest=grant.digest,
        )
    before = store.replay()
    result = invoke(
        command_for(store, grant, scorer, contract), store, grant, tmp_path, "--recover"
    )
    assert result.exit_code == 0
    after = store.replay()
    assert after["cancelled"] is True and after["used"] == before["used"]
    assert scorer.calls == scorer.recoveries == 1
