"""Preparation never creates adapters or hides an incomplete task family."""
from autoengineering.adapters.contracts import AdapterRegistry
from autoengineering.utility.preparation import prepare_suite, PreparationResult
from test_utility_contracts import suite


def test_missing_tasks_block_before_factories(tmp_path):
    result = prepare_suite(suite(), (), source_root=tmp_path,
                           adapters=AdapterRegistry(()), capabilities={}, register=())
    assert result.status == "blocked"
    assert result.blockers == ("suite:missing_source_or_lock_closure",
                               "task:missing_preparation", "suite:incomplete_real_task_families")
    assert result.starts_authorized is False
    assert result.cells == tuple(c.digest for c in suite().cells)
    assert PreparationResult.from_json(result.to_json()) == result


def test_preparation_estimates_whole_matrix_without_reservation(tmp_path):
    spec = suite(35)
    result = prepare_suite(spec, (), source_root=tmp_path,
                           adapters=AdapterRegistry(()), capabilities={}, register=())
    assert result.batch_sizes == (32, 32, 6)
    assert sum(result.batch_sizes) == len(spec.cells)
    assert list(tmp_path.iterdir()) == []


def test_pinned_task_preparation_validates_without_constructing_model(tmp_path):
    from dataclasses import replace
    from autoengineering.adapters.contracts import AdapterRegistration
    from autoengineering.campaign.artifacts import reference
    from autoengineering.campaign.records import ModelSnapshot, PortContract
    from autoengineering.campaign.serialization import digest
    from autoengineering.utility.preparation import TaskPreparation
    from test_utility_exposure import exposure, manifest
    h = "1" * 64
    files = {"model.py": "# trusted fixture\n", "lock.txt": "fixture lock\n",
             "dossier.json": '{"status":"admitted"}', "outcome.json": '{"units":"W"}',
             "qualification.txt": "Authored fixture review, not real science"}
    refs = {}
    for name, content in files.items():
        (tmp_path / name).write_text(content)
        refs[name] = reference(tmp_path, name, media_type="text/plain", producer="fixture")
    model = ModelSnapshot(h, {"component": "fixture"}, [refs["model.py"]], h, [],
                          [PortContract("value", (), "W", "float", (), "scalar", h, None)])
    spec = suite()
    task = replace(spec.tasks[0], dossier_digest=digest({"status": "admitted"}),
                   partition_digest=manifest().digest, outcome_digest=digest({"units": "W"}),
                   candidate_digests=(model.digest,), required_capabilities=("scalar",))
    spec = replace(spec, tasks=(task,), exposure_digest=digest([exposure().to_dict()]),
                   lock_digest=refs["lock.txt"].sha256,
                   source_digest=digest([refs["model.py"].to_dict()]))
    prepared = TaskPreparation("task", "trusted", refs["dossier.json"], (model,), manifest(),
                               exposure(), refs["qualification.txt"], refs["outcome.json"])

    def factory():
        raise AssertionError("preparation must never create a model")

    registry = AdapterRegistry((AdapterRegistration("trusted", "1", factory, ("model.py",)),))
    kwargs = dict(source_root=tmp_path, adapters=registry, capabilities={"trusted": ("scalar",)},
                  register=(exposure(),), lock=refs["lock.txt"],
                  source_inventory=(refs["model.py"],))
    result = prepare_suite(spec, (prepared,), **kwargs)
    assert result.blockers == ("suite:incomplete_real_task_families",)
    unsupported = prepare_suite(spec, (prepared,), **(kwargs | {"capabilities": {}}))
    assert "task:unsupported_capability" in unsupported.blockers
    (tmp_path / "model.py").write_text("changed")
    altered = prepare_suite(spec, (prepared,), **kwargs)
    assert "suite:source_or_lock_identity_invalid" in altered.blockers
    assert "task:identity_source_or_custody_invalid" in altered.blockers
