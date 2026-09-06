"""Check rendered figures against saved specs and verify standalone resources."""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1]


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []
        self.tables = 0
        self.payloads = {}
        self.active = None
        self.ids = set()
        self.anchors = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "table":
            self.tables += 1
        if tag in ["script", "img", "iframe", "source"] and a.get("src"):
            self.resources.append(a["src"])
        if tag == "link" and a.get("rel") == "stylesheet":
            self.resources.append(a["href"])
        if tag == "a" and a.get("href", "").startswith("#") and a["href"] != "#":
            self.anchors.append(a["href"][1:])
        if (
            tag == "script"
            and a.get("type") == "application/json"
            and a.get("id", "").startswith("data-")
        ):
            self.active = a["id"][5:]
            self.payloads[self.active] = ""

    def handle_endtag(self, tag):
        if tag == "script":
            self.active = None

    def handle_data(self, data):
        if self.active:
            self.payloads[self.active] += data


def verify(path: Path = REPORT / "report.html") -> dict:
    document = path.read_text()
    parser = ReportParser()
    parser.feed(document)
    assert parser.tables == 0, "The report should use figures instead of data tables"
    assert len(parser.payloads) == 7
    assert all(r.startswith("data:") for r in parser.resources), parser.resources
    assert set(parser.anchors) <= parser.ids, set(parser.anchors) - parser.ids
    assert {"ref-frazier2018", "ref-bergstra2012"} <= parser.ids
    saved = {p.name: json.loads(p.read_text()) for p in (REPORT / "figures").glob("*.json")}
    embedded_count = 0
    for name, text in parser.payloads.items():
        payload = json.loads(text)
        specs = [value for key, value in saved.items() if key.startswith(name + "-")]
        assert len(specs) == len(payload["variants"]), name
        assert 0 <= payload["default"] < len(specs)
        for figure in payload["variants"]:
            assert figure in specs, f"Embedded figure differs from saved JSON: {name}"
            embedded_count += 1
    assert embedded_count == len(saved)
    provenance = json.loads((REPORT / "provenance.json").read_text())
    for name, expected in provenance["report_sources"].items():
        assert hashlib.sha256((REPORT / name).read_bytes()).hexdigest() == expected, name
    for name, expected in provenance["outputs"].items():
        assert hashlib.sha256((REPORT / name).read_bytes()).hexdigest() == expected, name
    return {
        "html_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "figures": len(parser.payloads),
        "embedded_plotly_specs": embedded_count,
        "embedded_resource_count": len(parser.resources),
        "external_required_resources": 0,
        "data_tables": parser.tables,
        "internal_links_resolve": True,
        "saved_specs_match_embedded": True,
        "figure_hashes_verified": True,
    }


if __name__ == "__main__":
    result = verify()
    (REPORT / "html-check.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
