"""Reference reading of the Principal Handoff Evidence 0.6 module (evidence/SPEC.md section 2), on ph_core.

  breaches(record) -> [errors]   the structural rules a record's verifiable and verified break
  usable(record)   -> evidence   the record's evidence as a verifier uses it: verifiable and verified removed when the
                                 record breaks a structural rule (core section 11), otherwise unchanged

Neither changes whether a record is valid or what state an item is in; that is ph_core's alone.
"""
from __future__ import annotations

import json
import pathlib

import ph_core
import schema_subset

SCHEMAS = pathlib.Path(__file__).resolve().parent.parent / "evidence" / "schemas"
MEMBERS = ("verifiable", "verified")


def breaches(r: dict) -> list[str]:
    ev = r.get("evidence")
    if not isinstance(ev, dict) or not ev.keys() & set(MEMBERS):
        return []
    t, out = r.get("type"), []
    out += schema_subset.errors(ev, json.loads((SCHEMAS / "evidence.schema.json").read_text()), SCHEMAS, "$.evidence")
    if out:  # the schema's required lists and types guarantee what the rules below read
        return out
    entries = ev.get("verifiable")
    if "verifiable" in ev:
        if t not in ("claimed", "note", "settled"):
            out.append("verifiable only on claims, notes and settlements")
        if "terms_rev" not in r:
            out.append("a record with verifiable entries carries terms_rev")
    if isinstance(entries, list):
        ids = [x.get("id") for x in entries if isinstance(x, dict)]
        if len(ids) != len(set(ids)):
            out.append("verifiable entry ids are unique within the record")
        if any(isinstance(x, dict) and ("proof" in x) == ("proof_ref" in x) for x in entries):
            out.append("a verifiable entry carries exactly one of proof and proof_ref")
    if "verified" in ev and not (t == "settled" or (t == "note" and r.get("origin") == "principal")):
        out.append("verified only on settlements and principal-side notes")
    results = ev.get("verified")
    if isinstance(results, list) and any(isinstance(v, dict) and isinstance(v.get("at"), str)
                                         and ph_core._instant(v["at"]) is None for v in results):
        out.append("a verification time that is not an RFC 3339 date-time")
    return out


def usable(r: dict) -> dict:
    ev = r.get("evidence") if isinstance(r.get("evidence"), dict) else {}
    if breaches(r):
        return {k: v for k, v in ev.items() if k not in MEMBERS}
    return ev
