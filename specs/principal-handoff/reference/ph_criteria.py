"""Reference reading of the Principal Handoff Criteria 0.5 module (criteria/SPEC.md sections 2, 4 and 7), on
ph_decisions and ph_evidence.

  breaches(record, config) -> [errors]       the structural rules of section 7 the record breaks (its module content)
  fold(records, config)    -> the decision's state (ph_decisions.fold) plus "approval": the approval in force (section 4)

Neither changes whether a record is valid or what state a decision is in; that is ph_decisions'.
"""
from __future__ import annotations

import json
import pathlib

import ph_core
import ph_decisions
import ph_evidence
import schema_subset

SCHEMAS = pathlib.Path(__file__).resolve().parent.parent / "criteria" / "schemas"
PREFIX = "approval:"  # the authority.under prefix this module reserves (core section 11)


def _criteria(terms: dict) -> list[str]:
    """section 2."""
    c = terms.get("criteria")
    if c is None:
        return []
    out = schema_subset.errors(c, json.loads((SCHEMAS / "criteria.schema.json").read_text()), SCHEMAS,
                               "$.terms.criteria")
    if out or not isinstance(c, dict):
        return out
    checks = [x for x in c.get("checks") or [] if isinstance(x, dict)]
    ids = [x.get("id") for x in checks]
    if not ids:
        out.append("criteria need at least one check")
    if len(ids) != len(set(ids)):
        out.append("check ids are unique within the criteria")
    if any(not x.get("trust") for x in checks):
        out.append("every check names at least one trust root")
    option = (c.get("answer") or {}).get("option")
    if option is not None and option not in {o.get("id") for o in terms.get("options") or [] if isinstance(o, dict)}:
        out.append("criteria.answer.option must be one of the options")
    return out


def _approved(r: dict, cfg: ph_core.Config) -> list[str]:
    """section 7: an approved record's own rules, beyond the core checks."""
    out = schema_subset.errors(r, json.loads((SCHEMAS / "approved.schema.json").read_text()), SCHEMAS)
    ap = r.get("approval") if isinstance(r.get("approval"), dict) else {}
    if not ap.get("active", True):
        out += [] if r.get("supersedes") else ["a retraction lists the approval it retracts in supersedes"]
        return out + (["terms_digest and after only on a grant"] if ap.keys() & {"terms_digest", "after"} else [])
    out += ["a grant needs terms_rev"] if "terms_rev" not in r else []
    out += ["a grant needs approval.terms_digest"] if "terms_digest" not in ap else []
    out += ["a grant never adopts a claim"] if "adopts" in r else []
    a = r.get("authority")
    if not isinstance(a, dict):
        return out + ["a grant needs authority"]
    out += ph_core._authority(r, cfg)
    if a.get("kind") not in ("principal", "confirmed"):
        out.append("an approval comes from the principal: kind principal or confirmed")
    if "presented" not in (r.get("evidence") or {}):
        out.append("a grant needs evidence.presented")
    return out


def _under(r: dict) -> str | None:
    under = (r.get("authority") or {}).get("under")
    return under[len(PREFIX):] if isinstance(under, str) and under.startswith(PREFIX) else None


def breaches(r: dict, cfg: ph_core.Config) -> list[str]:
    """section 7. Evidence's structural rules apply first: verified results it ignores do not count here."""
    t = r.get("type")
    if t == "approved":
        return _approved(r, cfg)
    if t in ("raised", "amended") and isinstance(r.get("terms"), dict):
        return _criteria(r["terms"])
    if t == "settled" and _under(r) is not None:
        out = []
        if not _under(r):
            out.append("approval: names no record")
        if (r.get("authority") or {}).get("kind") != "delegated":
            out.append("a settlement under an approval is delegated")
        if r.get("outcome") != "decided":
            out.append("a settlement under an approval records the approved answer")
        verified = ph_evidence.usable(r).get("verified") or []
        if not verified or any(v.get("result") != "valid" for v in verified if isinstance(v, dict)):
            out.append("a settlement under an approval carries only valid verification results")
        return out
    return []


def _approval_in_force(records: list[dict], cfg: ph_core.Config) -> dict | None:
    """section 4: the approval in force, as only the principal side computes it."""
    valid = ph_core.held(records, ph_decisions.EXT, cfg)
    needs = [r for r in valid if r["type"] in ph_core.NEED]
    need, conflict = ph_core._register(needs)
    if need is None or conflict or need["type"] == "withdrawn" or "criteria" not in need["terms"] or breaches(need, cfg):
        return None
    rev = need["terms_rev"]
    if rev != max(n["terms_rev"] for n in needs if n["type"] != "withdrawn"):
        return None
    digest = ph_core.terms_digest(need)
    if any(ph_core.terms_digest(n) != digest for n in needs if n["type"] != "withdrawn" and n["terms_rev"] == rev):
        return None
    settlements = {r["id"]: r for r in valid if r["type"] in ph_core.SETTLEMENT}
    approvals = {}
    for r in records:  # this module's valid records, deduplicated among themselves (core section 10), and only then
        if r.get("type") == "approved" and not ph_decisions.validate(r, cfg)[1]:  # checked against section 7
            old = approvals.get(r["id"])
            if old is None or ph_core._canon(r) > ph_core._canon(old):
                approvals[r["id"]] = r
    approvals = {i: r for i, r in approvals.items() if not breaches(r, cfg)}
    retracted = {s for r in approvals.values() for s in r.get("supersedes", [])}

    def made_over(after: str | None) -> bool:  # condition 4: every held settlement record is `after` or before it
        covered, stack = set(), [after] if after else []
        while stack:
            i = stack.pop()
            if i in covered or i not in settlements:
                continue
            covered.add(i)
            stack += settlements[i].get("supersedes", [])
        return set(settlements) <= covered

    used = {_under(r) for r in settlements.values() if r["type"] == "settled"}
    live = [r for r in approvals.values() if r["approval"]["active"] and r["id"] not in retracted | used
            and r["terms_rev"] == rev and r["approval"]["terms_digest"] == digest
            and made_over(r["approval"].get("after"))]
    return ph_core._latest(live) if live else None


def fold(records: list[dict], cfg: ph_core.Config) -> dict:
    approval = _approval_in_force(records, cfg)
    return {**ph_decisions.fold(records, cfg), "approval": approval["id"] if approval else None}
