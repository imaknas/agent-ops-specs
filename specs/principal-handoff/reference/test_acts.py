"""Runs the Principal Handoff Acts 0.3 conformance suite against the reference implementation.

    cd specs/principal-handoff/reference && python3 -m unittest -v
"""
from __future__ import annotations

import json
import pathlib
import unittest

import ph_acts as acts
from ph_core import Config

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONF = ROOT / "acts" / "conformance"
SCHEMAS = [ROOT / "acts" / "schemas", ROOT / "core" / "schemas"]
PROFILES = json.loads((CONF / "profiles.json").read_text())["profiles"]
ALLOWED = {"$schema", "$id", "$ref", "title", "description", "type", "required", "properties", "enum", "const",
           "pattern", "items"}


def suite(name: str) -> dict:
    return json.loads((CONF / name).read_text())


def cases(name: str) -> list[dict]:
    return suite(name)["cases"]


def doc(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def nonblank(text: str) -> list[str]:
    """Conformance compares documents as their sequence of non-blank lines, trailing whitespace removed."""
    return [l.rstrip() for l in text.split("\n") if l.strip()]


def profile(name: str) -> acts.Profile:
    return acts.Profile.from_json(PROFILES[name])


class Binding(unittest.TestCase):
    def test_parse(self):
        for c in cases("parse.json"):
            with self.subTest(c["id"]):
                self.assertEqual(acts.parse(doc(c["document"]), profile(c["profile"])), c["expect"])

    def test_keys(self):
        for c in cases("keys.json"):
            with self.subTest(c["id"]):
                self.assertEqual(acts.recipe_key(c["project"], c["text"]), c["key"])

    def test_register(self):
        for c in cases("register.json"):
            with self.subTest(c["id"]):
                out, raised = acts.register(doc(c["document"]), c["project"], profile(c["profile"]))
                self.assertEqual(raised, c["expect"]["raised"])
                self.assertEqual(nonblank(out), nonblank(doc(c["expect"]["document"])))

    def test_register_is_idempotent(self):
        for c in cases("register.json"):
            with self.subTest(c["id"]):
                p = profile(c["profile"])
                once, _ = acts.register(doc(c["document"]), c["project"], p)
                self.assertEqual(acts.register(once, c["project"], p), (once, []))

    def test_relink(self):
        for c in cases("relink.json"):
            with self.subTest(c["id"]):
                out, relinked = acts.relink(doc(c["document"]), c["vanished"], profile(c["profile"]))
                self.assertEqual(relinked, c["expect"]["relinked"])
                self.assertEqual(nonblank(out), nonblank(doc(c["expect"]["document"])))

    def test_amend(self):
        for c in cases("amend.json"):
            with self.subTest(c["id"]):
                self.assertEqual(acts.amend(doc(c["document"]), c["latest"], profile(c["profile"])), c["expect"])

    def test_apply(self):
        for c in cases("apply.json"):
            with self.subTest(c["id"]):
                out, changed = acts.apply(doc(c["document"]), c["record"], profile(c["profile"]))
                self.assertEqual(changed, c["expect"]["changed"])
                self.assertEqual(nonblank(out), nonblank(doc(c["expect"]["document"])))

    def test_apply_records_are_valid(self):
        for c in cases("apply.json"):
            with self.subTest(c["id"]):
                self.assertEqual(acts.validate(c["record"], Config("p:owner"))[1], [])

    def test_reconcile(self):
        for c in cases("reconcile.json"):
            with self.subTest(c["id"]):
                self.assertEqual(acts.reconcile(doc(c["document"]), c["open"], profile(c["profile"])), c["expect"])


class Records(unittest.TestCase):
    def test_records(self):
        s = suite("records.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                cfg = Config(s["principal"], c.get("principal_type", s.get("principal_type")) == "legal")
                name, errs = acts.validate(c["record"], cfg)
                if c["valid"]:
                    self.assertEqual((name, errs), (c["schema"], []))
                else:
                    self.assertTrue(errs, f"expected invalid, validated against {name}")

    def test_lifecycle(self):
        s = suite("lifecycle.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                self.assertEqual(acts.fold(c["records"], Config(s["principal"])), c["expect"])

    def test_lifecycle_does_not_depend_on_arrival_order(self):
        s = suite("lifecycle.json")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                self.assertEqual(acts.fold(list(reversed(c["records"])), Config(s["principal"])), c["expect"])

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
