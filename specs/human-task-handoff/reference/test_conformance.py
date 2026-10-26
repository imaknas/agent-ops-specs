"""Runs the HTH v0.1 conformance suite against the reference implementation.

    cd specs/human-task-handoff/reference && python3 -m unittest -v
"""
from __future__ import annotations

import json
import pathlib
import unittest

import hth
import schema_subset

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"
CONF = ROOT / "conformance"
PROFILES = json.loads((CONF / "profiles.json").read_text())["profiles"]

# SPEC.md 6.2: which schema an event must validate against, by (type, origin)
DISPATCH = {
    ("registered", "registrar"): "registered",
    ("done", "owner"): "resolution",
    ("dropped", "owner"): "resolution",
    ("already_done", "owner"): "resolution",
    ("reopened", "owner"): "reopened",
    ("done", "agent"): "agent-report",
    ("dropped", "agent"): "agent-report",
    ("done", "registrar"): "inferred-done",
}


def cases(name: str) -> list[dict]:
    return json.loads((CONF / name).read_text())["cases"]


def doc(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def nonblank(text: str) -> list[str]:
    """Conformance compares documents as their sequence of non-blank lines, trailing whitespace removed."""
    return [l.rstrip() for l in text.split("\n") if l.strip()]


def profile(name: str) -> hth.Profile:
    return hth.Profile.from_json(PROFILES[name])


def validate(event: dict) -> tuple[str | None, list[str]]:
    name = DISPATCH.get((event.get("type"), event.get("origin")))
    if name is None:
        return None, ["no schema for this type and origin"]
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text())
    return name, schema_subset.errors(event, schema, SCHEMAS)


class Conformance(unittest.TestCase):
    def test_parse(self):
        for c in cases("parse.json"):
            with self.subTest(c["id"]):
                self.assertEqual(hth.parse(doc(c["document"]), profile(c["profile"])), c["expect"])

    def test_keys(self):
        for c in cases("keys.json"):
            with self.subTest(c["id"]):
                self.assertEqual(hth.recipe_key(c["project"], c["text"]), c["key"])

    def test_register(self):
        for c in cases("register.json"):
            with self.subTest(c["id"]):
                out, events = hth.register(doc(c["document"]), c["project"], profile(c["profile"]))
                self.assertEqual(events, c["expect"]["registered"])
                self.assertEqual(nonblank(out), nonblank(doc(c["expect"]["document"])))

    def test_register_is_idempotent(self):
        for c in cases("register.json"):
            with self.subTest(c["id"]):
                p = profile(c["profile"])
                once, _ = hth.register(doc(c["document"]), c["project"], p)
                self.assertEqual(hth.register(once, c["project"], p), (once, []))

    def test_apply(self):
        for c in cases("apply.json"):
            with self.subTest(c["id"]):
                out, changed = hth.apply(doc(c["document"]), c["event"], profile(c["profile"]))
                self.assertEqual(changed, c["expect"]["changed"])
                self.assertEqual(nonblank(out), nonblank(doc(c["expect"]["document"])))

    def test_apply_events_are_valid(self):
        for c in cases("apply.json"):
            with self.subTest(c["id"]):
                self.assertEqual(validate(c["event"])[1], [])

    def test_reconcile(self):
        for c in cases("reconcile.json"):
            with self.subTest(c["id"]):
                self.assertEqual(hth.reconcile(doc(c["document"]), c["open"], profile(c["profile"])), c["expect"])

    def test_events(self):
        for c in cases("events.json"):
            with self.subTest(c["id"]):
                name, errs = validate(c["event"])
                if c["valid"]:
                    self.assertEqual((name, errs), (c["schema"], []))
                else:
                    self.assertTrue(errs, f"expected invalid, validated against {name}")

    def test_schemas_use_only_the_subset(self):
        allowed = {"$schema", "$id", "$ref", "title", "description", "type", "required", "properties", "enum",
                   "const", "pattern", "items"}

        def walk(s, where):
            self.assertLessEqual(set(s) - allowed, set(), where)
            for k, sub in s.get("properties", {}).items():
                walk(sub, f"{where}.{k}")
            if "items" in s:
                walk(s["items"], f"{where}[]")

        for f in sorted(SCHEMAS.glob("*.json")):
            walk(json.loads(f.read_text()), f.name)


if __name__ == "__main__":
    unittest.main()
