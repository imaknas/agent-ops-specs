"""Runs the Principal Handoff Core 0.6 conformance vectors and checks every schema stays within the core section 4
keyword subset.

    cd specs/principal-handoff/reference && python3 -m unittest -v
"""
from __future__ import annotations

import json
import pathlib
import unittest

import ph_acts
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
                self.assertEqual(ph_core.convert(c["record"], c["to"]), c["expect"])

    def test_converting_party_holds_converted_forms(self):
        s = json.loads((CONF / "convert.json").read_text())
        cfg = ph_core.Config(s["principal"])
        for c in s["held"]:
            with self.subTest(c["id"]):
                held = ph_core.converting_held(c["records"], ph_acts.EXT, cfg)
                self.assertEqual(sorted(r["id"] for r in held), c["expect"]["held"])
                self.assertEqual(ph_core.relations(held, ph_acts.EXT, cfg), c["expect"]["relations"])
                again = ph_core.converting_held(list(reversed(c["records"])), ph_acts.EXT, cfg)
                self.assertEqual(sorted(again, key=lambda r: r["id"]), sorted(held, key=lambda r: r["id"]))

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
