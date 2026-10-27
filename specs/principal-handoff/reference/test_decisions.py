"""Runs the Principal Handoff Decisions 0.3 conformance suite against the reference implementation.

    cd specs/principal-handoff/reference && python3 -m unittest -v
"""
from __future__ import annotations

import json
import pathlib
import unittest

import ph_decisions as decisions
from ph_core import Config

CONF = pathlib.Path(__file__).resolve().parent.parent / "decisions" / "conformance"


def suite(name: str) -> dict:
    return json.loads((CONF / name).read_text())


class Conformance(unittest.TestCase):
    def test_records(self):
        s = suite("records.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                cfg = Config(s["principal"], c.get("principal_type", s.get("principal_type")) == "legal")
                name, errs = decisions.validate(c["record"], cfg)
                if c["valid"]:
                    self.assertEqual((name, errs), (c["schema"], []))
                else:
                    self.assertTrue(errs, f"expected invalid, validated against {name}")

    def test_lifecycle(self):
        s = suite("lifecycle.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                self.assertEqual(decisions.fold(c["records"], Config(s["principal"])), c["expect"])

    def test_lifecycle_does_not_depend_on_arrival_order(self):
        s = suite("lifecycle.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                self.assertEqual(decisions.fold(list(reversed(c["records"])), Config(s["principal"])), c["expect"])


if __name__ == "__main__":
    unittest.main()
