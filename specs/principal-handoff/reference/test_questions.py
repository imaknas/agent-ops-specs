"""Runs the Principal Handoff Questions 0.1 conformance suite against the reference implementation.

    cd specs/principal-handoff/reference && python3 -m unittest -v
"""
from __future__ import annotations

import json
import pathlib
import unittest

import ph_questions as questions

CONF = pathlib.Path(__file__).resolve().parent.parent / "questions" / "conformance"


def cases(name: str) -> list[dict]:
    return json.loads((CONF / name).read_text())["cases"]


class Conformance(unittest.TestCase):
    def test_events(self):
        for c in cases("events.json"):
            with self.subTest(c["id"]):
                name, errs = questions.validate(c["event"])
                if c["valid"]:
                    self.assertEqual((name, errs), (c["schema"], []))
                else:
                    self.assertTrue(errs, f"expected invalid, validated against {name}")

    def test_lifecycle(self):
        for c in cases("lifecycle.json"):
            with self.subTest(c["id"]):
                self.assertEqual(questions.fold(c["events"]), c["expect"])

    def test_lifecycle_does_not_depend_on_arrival_order(self):
        for c in cases("lifecycle.json"):
            with self.subTest(c["id"]):
                self.assertEqual(questions.fold(list(reversed(c["events"]))), c["expect"])

    def test_schemas_use_only_the_subset(self):
        allowed = {"$schema", "$id", "$ref", "title", "description", "type", "required", "properties", "enum",
                   "const", "pattern", "items"}

        def walk(s, where):
            self.assertLessEqual(set(s) - allowed, set(), where)
            for k, sub in s.get("properties", {}).items():
                walk(sub, f"{where}.{k}")
            if "items" in s:
                walk(s["items"], f"{where}[]")

        for f in sorted(questions.SCHEMAS.glob("*.json")):
            walk(json.loads(f.read_text()), f.name)


if __name__ == "__main__":
    unittest.main()
