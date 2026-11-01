"""Runs the Principal Handoff Core 0.5 conformance vectors and checks every schema stays within the core section 4
keyword subset.

    cd specs/principal-handoff/reference && python3 -m unittest -v
"""
from __future__ import annotations

import json
import pathlib
import unittest

import ph_core

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONF = ROOT / "core" / "conformance"
SCHEMAS = [ROOT / d / "schemas" for d in ("core", "acts", "decisions", "evidence", "criteria")]
ALLOWED = {"$schema", "$id", "$ref", "title", "description", "type", "required", "properties", "enum", "const",
           "pattern", "items"}


class Core(unittest.TestCase):
    def test_terms_digest(self):
        for c in json.loads((CONF / "terms-digest.json").read_text())["cases"]:
            with self.subTest(c["id"]):
                self.assertEqual(ph_core._canon(ph_core.digest_input(c["record"])), c["canonical"])
                self.assertEqual(ph_core.terms_digest(c["record"]), c["digest"])

    def test_convert(self):
        for c in json.loads((CONF / "convert.json").read_text())["cases"]:
            with self.subTest(c["id"]):
                self.assertEqual(ph_core.convert(c["record"], c["to"], c["held"]), c["expect"])

    def test_schemas_use_only_the_subset(self):
        def walk(x, where):
            self.assertLessEqual(set(x) - ALLOWED, set(), where)
            for k, sub in x.get("properties", {}).items():
                walk(sub, f"{where}.{k}")
            if "items" in x:
                walk(x["items"], f"{where}[]")

        for d in SCHEMAS:
            for f in sorted(d.glob("*.json")):
                walk(json.loads(f.read_text()), f.name)


if __name__ == "__main__":
    unittest.main()
