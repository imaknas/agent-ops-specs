"""Runs the Principal Handoff Core 0.4 conformance vectors and checks every schema stays within the core section 4
keyword subset.

    cd specs/principal-handoff/reference && python3 -m unittest -v
"""
from __future__ import annotations

import json
import pathlib
import unittest

import ph_core

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMAS = [ROOT / d / "schemas" for d in ("core", "acts", "decisions")]
ALLOWED = {"$schema", "$id", "$ref", "title", "description", "type", "required", "properties", "enum", "const",
           "pattern", "items"}


class Core(unittest.TestCase):
    def test_terms_digest(self):
        for c in json.loads((ROOT / "core" / "conformance" / "terms-digest.json").read_text())["cases"]:
            with self.subTest(c["id"]):
                r = c["record"]
                bound = {k: r[k] for k in ("ext", "project", "key", "terms_rev", "terms")}
                self.assertEqual(ph_core._canon(bound), c["canonical"])
                self.assertEqual(ph_core.terms_digest(r), c["digest"])

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
