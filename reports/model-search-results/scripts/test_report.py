"""Reject altered aggregate values, uncensored caps and relabeled infeasible policies."""

from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import build_report as build
from verify_report import verify


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixed = build.source(build.DATA / "fixed/results.json")["runs"]
        cls.target = build.source(build.DATA / "target-2000/results.json")["runs"]
        cls.chains = {
            name: (
                build.source(build.CHAINS / name / "summary.json"),
                build.source(build.CHAINS / name / "trials.json"),
            )
            for name in ["solar", "wind", "hybrid"]
        }
        cls.original = (build.DATA / "RESULTS.md").read_text()

    def check_text(self, text):
        with tempfile.TemporaryDirectory(dir=build.REPORT / ".quarto") as directory:
            path = Path(directory)
            (path / "RESULTS.md").write_text(text)
            with patch.object(build, "DATA", path):
                return build.verify_markdown(self.fixed, self.target, self.chains)

    def test_original_aggregates_match(self):
        self.assertEqual(self.check_text(self.original), 88)

    def test_changed_rmse_is_rejected(self):
        altered = re.sub(
            r"(\| hydro \| random \| )([0-9.]+)", r"\g<1>99999", self.original, count=1
        )
        self.assertNotEqual(altered, self.original)
        with self.assertRaises(AssertionError):
            self.check_text(altered)

    def test_censored_call_is_not_an_exact_target_hit(self):
        altered = self.original.replace(">2000", "2000", 1)
        self.assertNotEqual(altered, self.original)
        with self.assertRaises(AssertionError):
            self.check_text(altered)

    def test_infeasible_candidate_cannot_be_relabelled(self):
        altered = self.original.replace(
            "| hybrid | cbc_dispatch | infeasible |", "| hybrid | cbc_dispatch | evaluated |"
        )
        self.assertNotEqual(altered, self.original)
        with self.assertRaises(AssertionError):
            self.check_text(altered)

    def test_dimension_extraction_matches_declared_examples(self):
        self.assertEqual(
            build.dimensions(), {"hydro": 3, "solar": 3, "copper": 2, "hymod": 7, "solar_diode": 7}
        )

    def test_html_embeds_the_actual_figures_and_resources(self):
        self.assertEqual(verify()["embedded_plotly_specs"], 20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
