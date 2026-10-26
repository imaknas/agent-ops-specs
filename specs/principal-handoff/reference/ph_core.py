"""Reference reading of Principal Handoff Core 0.3 (core/SPEC.md sections 3 to 7).

Standard library only, Python >= 3.10. Extensions plug in through an Ext description:

  Ext(name, schemas_dir, withdrawn_policy)   withdrawn_policy is "keep" (Acts) or "stop" (Decisions)
  validate(record, ext, principal=None)      -> (schema name or None, [errors])   schema + ownership + authority
  fold(records, ext, principal=None)         -> the item's state, independent of arrival order
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from datetime import datetime

import schema_subset

ROOT = pathlib.Path(__file__).resolve().parent.parent

NEED = ("raised", "amended", "withdrawn")
SETTLEMENT = ("settled", "reopened")
# core section 4: which roles may emit each record type (extensions may only narrow this; their schemas do)
OWNER = {"raised": {"requester"}, "amended": {"requester"}, "withdrawn": {"requester"},
         "settled": {"principal"}, "reopened": {"principal"}}


@dataclass(frozen=True)
class Ext:
    name: str               # "acts/0.3"
    schemas: pathlib.Path
    withdrawn_policy: str   # "keep": stays open and the principal is asked; "stop": no longer presented


def ext(name: str, policy: str) -> Ext:
    return Ext(name, ROOT / name.split("/")[0] / "schemas", policy)


def validate(r: dict, e: Ext, principal: str | None = None) -> tuple[str | None, list[str]]:
    """Schema by (type, origin) as the extension lists it, then the rules a schema cannot state."""
    t = r.get("type")
    path = e.schemas / f"{t}.schema.json"
    if not isinstance(t, str) or not path.exists():
        return None, ["no schema for this type"]
    errs = schema_subset.errors(r, json.loads(path.read_text()), e.schemas)
    if t in OWNER and r.get("origin") not in OWNER[t]:  # R1, R2
        errs.append(f"origin {r.get('origin')!r} may not emit {t}")
    if principal is not None and r.get("by") == principal:  # R6: the principal is never a participant
        errs.append("the principal identifier cannot emit records")
    if t == "claimed" and r.get("origin") == "principal":  # R3: the owner records, it does not claim
        errs.append("the principal side settles; it does not claim")
    if t == "related":
        rel = r.get("relation") or {}
        want = {"same_as": "principal", "derived_from": "requester"}.get(rel.get("kind"))
        if want and r.get("origin") != want:
            errs.append(f"{rel.get('kind')} is emitted by {want}")
    if t == "settled":
        errs += _authority(r, principal)
    if t == "note" and not (r.get("about") or {}).keys() & {"key", "quote"}:
        errs.append("about needs key or quote")
    return t, errs


def _authority(r: dict, principal: str | None) -> list[str]:
    """core section 5."""
    a, ev = r.get("authority") or {}, r.get("evidence") or {}
    kind, decider = a.get("kind"), a.get("decider")
    out = []
    if kind in ("principal", "confirmed") and principal is not None and decider != principal:
        out.append(f"{kind} needs the principal as decider")
    if kind == "confirmed" and "proposal" not in ev:
        out.append("confirmed needs evidence.proposal")
    if kind == "delegated":
        if "under" not in a or "chain" not in a:
            out.append("delegated needs under and chain")
        if principal is not None and decider == principal:
            out.append("delegated decider cannot be the principal")
    if kind == "attested" and "basis" not in ev:
        out.append("attested needs evidence.basis")
    return out


def _when(r: dict) -> datetime:
    return datetime.fromisoformat(r["ts"].replace("Z", "+00:00").replace("z", "+00:00"))


def _register(records: list[dict]) -> tuple[dict | None, bool]:
    """core section 6: current record (latest head, ties by greater id) and whether there is a conflict."""
    if not records:
        return None, False
    by_id = {r["id"]: r for r in records}
    replaced = {s for r in records for s in r.get("supersedes", []) if s in by_id}
    heads = [r for r in records if r["id"] not in replaced] or records
    current = max(heads, key=lambda r: (_when(r), r["id"]))
    return current, len(heads) > 1 or _cycle(by_id)


def _cycle(by_id: dict) -> bool:
    for start in by_id.values():
        seen, stack = set(), [start]
        while stack:
            r = stack.pop()
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            for s in r.get("supersedes", []):
                if s == start["id"]:
                    return True
                if s in by_id:
                    stack.append(by_id[s])
    return False


def fold(records: list[dict], e: Ext, principal: str | None = None) -> dict:
    """State of one item from all the records a receiver holds for it, in any order. Invalid records are ignored and
    listed; an id counts once (core section 10)."""
    seen: dict[str, dict] = {}
    ignored: set[str] = set()
    for r in records:
        if r.get("id") in seen:
            continue
        if validate(r, e, principal)[1]:
            if r.get("id") is not None:
                ignored.add(r["id"])
            continue
        seen[r["id"]] = r
    valid = list(seen.values())
    need, need_conflict = _register([r for r in valid if r["type"] in NEED])
    settle, settle_conflict = _register([r for r in valid if r["type"] in SETTLEMENT])
    terms_rev = max((r.get("terms_rev", 0) for r in valid if r["type"] in ("raised", "amended")), default=0)
    if settle and settle["type"] == "settled":
        state = "settled"
    elif need and need["type"] == "withdrawn":
        state = "open" if e.withdrawn_policy == "keep" else "withdrawn"
    elif need:
        state = "open"
    else:
        state = "unknown"
    settled = settle if settle and settle["type"] == "settled" else None
    return {
        "state": state,
        "outcome": settled["outcome"] if settled else None,
        "settlement": settle["id"] if settle else None,
        "authority": settled["authority"]["kind"] if settled else None,
        "answer": settled.get("answer") if settled else None,
        "stale": bool(settled and settled.get("terms_rev", 0) < terms_rev),
        "withdrawn": bool(need and need["type"] == "withdrawn"),
        "terms_rev": terms_rev,
        "conflict": need_conflict or settle_conflict,
        "claims": sorted(r["id"] for r in valid if r["type"] == "claimed"),
        "ignored": sorted(ignored),
    }
