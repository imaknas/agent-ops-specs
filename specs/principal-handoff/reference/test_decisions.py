"""Runs the Principal Handoff Decisions 0.6 conformance suite against the reference implementation.

    cd specs/principal-handoff/reference && python3 -m unittest -v
"""
from __future__ import annotations

import json
import pathlib
import unittest

import ph_core
import ph_decisions as decisions
from ph_core import VIEW, Config

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
                if c["valid"] is None:  # an extension or version not implemented: kept, not acted on (core sections 4, 6)
                    self.assertFalse(ph_core.implemented(c["record"], decisions.EXT))
                elif c["valid"]:
                    # a module pair has no schema of its own (section 3, core section 4)
                    self.assertEqual((None if name in decisions.EXT.modules else name, errs), (c["schema"], []))
                    self.assertTrue(ph_core.implemented(c["record"], decisions.EXT))
                else:
                    self.assertTrue(errs, f"expected invalid, validated against {name}")

    def test_relations(self):
        s = suite("relations.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                for records in (c["records"], list(reversed(c["records"]))):
                    self.assertEqual(ph_core.relations(records, decisions.EXT, Config(s["principal"])),
                                     c["expect"]["relations"])
                    self.assertEqual(ph_core.replacement(records, decisions.EXT, Config(s["principal"])),
                                     c["expect"]["replacement"])

    def test_lifecycle(self):
        s = suite("lifecycle.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                self.assertEqual(decisions.fold(c["records"], Config(s["principal"])), c["expect"])

    def test_requester_settlement_view(self):
        """core section 12: a requester computes the settlement view from need records and principal-side records."""
        s = suite("lifecycle.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                self.assertEqual(decisions.settlement_view(c["records"], Config(s["principal"])),
                                 {k: c["expect"][k] for k in VIEW})

    def test_lifecycle_does_not_depend_on_arrival_order(self):
        s = suite("lifecycle.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                self.assertEqual(decisions.fold(list(reversed(c["records"])), Config(s["principal"])), c["expect"])


if __name__ == "__main__":
    unittest.main()
