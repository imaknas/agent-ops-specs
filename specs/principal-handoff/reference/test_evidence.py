"""Runs the Principal Handoff Evidence 0.6 conformance suite against the reference implementation.

    cd specs/principal-handoff/reference && python3 -m unittest -v
"""
from __future__ import annotations

import json
import pathlib
import unittest

import ph_acts
import ph_decisions
import ph_evidence
from ph_core import Config

CONF = pathlib.Path(__file__).resolve().parent.parent / "evidence" / "conformance"
EXTENSIONS = {"acts": ph_acts, "decisions": ph_decisions}


class Conformance(unittest.TestCase):
    def test_records(self):
        s = json.loads((CONF / "records.json").read_text())
        for c in s["cases"]:
            with self.subTest(c["id"]):
                cfg = Config(s["principal"], c.get("principal_type", s.get("principal_type")) == "legal")
                name, errs = EXTENSIONS[c["record"]["ext"].split("/")[0]].validate(c["record"], cfg)
                self.assertEqual((name if not errs else None, not errs), (c.get("schema"), c["valid"]), errs)
                self.assertEqual("ignored" if ph_evidence.breaches(c["record"]) else "used", c["evidence"])


if __name__ == "__main__":
    unittest.main()
