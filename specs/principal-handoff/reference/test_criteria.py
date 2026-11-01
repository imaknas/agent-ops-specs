"""Runs the Principal Handoff Criteria 0.5 conformance suite against the reference implementation.

    cd specs/principal-handoff/reference && python3 -m unittest -v
"""
from __future__ import annotations

import json
import pathlib
import unittest

import ph_criteria
import ph_decisions
from ph_core import Config

CONF = pathlib.Path(__file__).resolve().parent.parent / "criteria" / "conformance"


def suite(name: str) -> dict:
    return json.loads((CONF / name).read_text())


class Conformance(unittest.TestCase):
    def test_records(self):
        s = suite("records.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                cfg = Config(s["principal"], c.get("principal_type", s.get("principal_type")) == "legal")
                name, errs = ph_decisions.validate(c["record"], cfg)
                self.assertEqual((name if not errs else None, not errs), (c.get("schema"), c["valid"]), errs)
                self.assertEqual("ignored" if ph_criteria.breaches(c["record"], cfg) else "used", c["criteria"])

    def test_lifecycle(self):
        s = suite("lifecycle.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                self.assertEqual(ph_criteria.fold(c["records"], Config(s["principal"])), c["expect"])
                self.assertEqual(ph_criteria.fold(list(reversed(c["records"])), Config(s["principal"])), c["expect"])

    def test_state_does_not_depend_on_the_module(self):
        """core section 11: the decision's state is the same with and without this module's records."""
        s = suite("lifecycle.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                core = [r for r in c["records"] if r.get("type") != "approved"]
                state = {k: v for k, v in c["expect"].items() if k not in ("approval", "ignored")}
                self.assertEqual({k: v for k, v in ph_decisions.fold(core, Config(s["principal"])).items()
                                  if k != "ignored"}, state)


if __name__ == "__main__":
    unittest.main()
