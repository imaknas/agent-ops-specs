"""Runs the Principal Handoff Core 0.6 conformance vectors and checks every schema stays within the core section 4
keyword subset.

    cd specs/principal-handoff/reference && python3 -m unittest -v
"""
from __future__ import annotations

import copy
import json
import pathlib
import unittest

import ph_acts
import ph_core
import ph_criteria
import ph_decisions
import ph_evidence

EXTENSIONS = {"acts": ph_acts, "decisions": ph_decisions}
ROOT = pathlib.Path(__file__).resolve().parent.parent
CONF = ROOT / "core" / "conformance"
SCHEMAS = [ROOT / d / "schemas" for d in ("core", "acts", "decisions", "evidence", "criteria")]
ALLOWED = {"$schema", "$id", "$ref", "title", "description", "type", "required", "properties", "enum", "const",
           "pattern", "items"}


JUNK = (None, True, 0, -1, 1.5, 2 ** 60, "", " ", "x", [], [None], ["x"], [[]], {}, {"x": 1})


def _paths(v, at=()):
    """The path of every member and array element in a parsed record."""
    children = v.items() if isinstance(v, dict) else enumerate(v) if isinstance(v, list) else ()
    for k, x in children:
        yield (*at, k)
        yield from _paths(x, (*at, k))


def _replaced(record: dict, path: tuple, value) -> dict:
    out = copy.deepcopy(record)
    node = out
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    return out


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

    def test_raw_text(self):
        s = json.loads((CONF / "raw.json").read_text())
        cfg = ph_core.Config(s["principal"], s["principal_type"] == "legal")
        for c in s["cases"]:
            with self.subTest(c["id"]):
                record, errs = ph_core.parse(c["raw"])
                name = None
                if not errs:
                    name, errs = EXTENSIONS.get(str(record.get("ext")).split("/")[0], ph_decisions).validate(record, cfg)
                self.assertEqual((name if not errs else None, not errs), (c["schema"], c["valid"]), errs)

    def test_parse_rejects_what_is_not_json(self):
        for text in ('{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}', '{"a":1,}', ""):
            with self.subTest(text):
                self.assertEqual(ph_core.parse(text)[0], None)

    def test_validate_never_raises(self):
        """A receiver ignores what is invalid: whatever a member holds, validate() answers (core section 10). Each kind of
        record in the suites, with each of its members replaced by each other JSON type."""
        for f in sorted(ROOT.glob("*/conformance/records.json")):
            s = json.loads(f.read_text())
            cfg = ph_core.Config(s["principal"], s.get("principal_type") == "legal")
            shapes = {}
            for c in s["cases"]:
                shapes.setdefault(str(sorted(_paths(c["record"]))), c)
            for c in shapes.values():
                module = EXTENSIONS.get(str(c["record"].get("ext")).split("/")[0], ph_decisions)
                for path in _paths(c["record"]):
                    for value in JUNK:
                        with self.subTest(f"{c['id']}: {path} = {value!r}"):
                            r = _replaced(c["record"], path, value)
                            if not module.validate(r, cfg)[1]:  # a valid record may still break a module's rules
                                ph_evidence.breaches(r)
                                ph_criteria.breaches(r, cfg)

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
