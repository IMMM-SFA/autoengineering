"""Prepare the bundled authored CSV example without observations or model execution."""

from __future__ import annotations

import argparse
from importlib.resources import files
from pathlib import Path

from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from examples.utility.solar_csv import SolarCsvPlan, prepare_csv
from examples.utility.solar_metadata import SolarMetadataReview
from examples.utility.solar_partitions import SolarPartitionPlan

PLAN_RESOURCE = "fixtures/solar-csv-plan-v1.json"
SOURCE_RESOURCE = "fixtures/solar-csv-rows-v1.json"


def resource(name):
    content = files("examples.utility").joinpath(name).read_bytes()
    if len(content) > 1024**2:
        raise ValueError("authored solar CSV resource exceeds cap")
    return unique_json(content.decode())


def prepare_demo(output):
    root = Path(output).absolute()
    if (
        root.exists()
        or root.is_symlink()
        or ".." in root.parts
        or any(p.is_symlink() for p in root.parents)
    ):
        raise ValueError("authored solar demo requires an absent output without symlink traversal")
    saved = resource(PLAN_RESOURCE)
    if (
        saved["schema"] != "utility-authored-solar-csv-plan-v1"
        or saved["source_resource"] != SOURCE_RESOURCE
    ):
        raise ValueError("authored solar CSV resource identity differs")
    plan = SolarCsvPlan.from_dict(saved["csv_plan"])
    partitions = SolarPartitionPlan.from_dict(saved["partition_plan"])
    metadata = SolarMetadataReview.from_dict(saved["metadata_review"])
    root.mkdir(mode=0o700)
    public, private = root / "public", root / "reserved"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)

    def source():
        # The source asset is opened only after prepare_csv commits both role claims.
        if (
            not (public / "preparation-claim.json").exists()
            or not (private / "preparation-claim.json").exists()
        ):
            raise ValueError("authored source opened before custody claims")
        value = resource(SOURCE_RESOURCE)
        if value["schema"] != "utility-authored-solar-csv-rows-v1" or not isinstance(
            value["csv_utf8"], str
        ):
            raise ValueError("authored solar CSV source differs")
        return value["csv_utf8"].encode("utf-8")

    return prepare_csv(partitions, plan, source, metadata, public, private)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = prepare_demo(args.output)
    print(
        canonical_json(
            {
                "status": "prepared_authored_only",
                "manifest_digest": digest(manifest),
                "task_admitted": False,
                "model_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    main()
