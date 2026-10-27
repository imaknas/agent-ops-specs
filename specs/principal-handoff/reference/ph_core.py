"""Reference reading of Principal Handoff Core 0.3 (core/SPEC.md sections 3 to 7).

Standard library only, Python >= 3.10. Extensions plug in through an Ext description:

  Ext(name, schemas_dir, withdrawn_policy, check)   withdrawn_policy is "keep" (Acts) or "stop" (Decisions);
                                                   check(record) -> [errors] adds the extension's own rules
  Config(principal, legal=False)                   the configured principal (core R6)
  validate(record, ext, config)                    -> (schema name or None, [errors])
  fold(records, ext, config)                       -> the item's state, independent of arrival order
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

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
    check: Callable[[dict], list[str]] = field(default=lambda r: [])


@dataclass(frozen=True)
class Config:
    principal: str          # the principal identifier, configured out of band (core R6)
    legal: bool = False     # the principal is a legal person (core section 5: representative)


def ext(name: str, policy: str, check: Callable[[dict], list[str]] | None = None) -> Ext:
    return Ext(name, ROOT / name.split("/")[0] / "schemas", policy, check or (lambda r: []))


def validate(r: dict, e: Ext, cfg: Config) -> tuple[str | None, list[str]]:
    """Schema by (type, origin) as the extension lists it, then the rules a schema cannot state."""
    t = r.get("type")
    path = e.schemas / f"{t}.schema.json"
    if not isinstance(t, str) or not path.exists():
        return None, ["no schema for this type"]
    errs = schema_subset.errors(r, json.loads(path.read_text()), e.schemas)
    if t in OWNER and r.get("origin") not in OWNER[t]:  # R1, R2
        errs.append(f"origin {r.get('origin')!r} may not emit {t}")
    if r.get("by") == cfg.principal:  # R6: the principal never emits records itself
        errs.append("the principal identifier cannot emit records")
    if t == "amended" and isinstance(r.get("terms_rev"), int) and r["terms_rev"] < 2:  # core section 6
        errs.append("amended terms_rev must be at least 2")
    if t == "settled" and isinstance(r.get("terms_rev"), int) and r["terms_rev"] < 1:
        errs.append("settled terms_rev must be at least 1")
    if t == "claimed" and r.get("origin") == "principal":  # R3: the owner records, it does not claim
        errs.append("the principal side settles; it does not claim")
    if t == "related":
        rel = r.get("relation") or {}
        want = {"same_as": "principal", "derived_from": "requester"}.get(rel.get("kind"))
        if want and r.get("origin") != want:
            errs.append(f"{rel.get('kind')} is emitted by {want}")
        tg = rel.get("target") or {}
        item = all(k in tg for k in ("ext", "project", "key"))
        if item == ("uri" in tg) or (not item and tg.keys() - {"uri"}):  # core section 7: exactly one form
            errs.append("relation target must be an item {ext, project, key} or a {uri}")
    if t == "settled":
        errs += _authority(r, cfg)
    if r.get("adopts") and (r.get("authority") or {}).get("kind") not in ("confirmed", "attested"):
        errs.append("adopts only on confirmed or attested settlements")
    errs += e.check(r)
    if t == "note" and not (r.get("about") or {}).keys() & {"key", "quote"}:
        errs.append("about needs key or quote")
    return t, errs


def _authority(r: dict, cfg: Config) -> list[str]:
    """core section 5."""
    a, ev = r.get("authority") or {}, r.get("evidence") or {}
    kind, decider = a.get("kind"), a.get("decider")
    out = []
    if kind in ("principal", "confirmed"):
        if decider != cfg.principal:
            out.append(f"{kind} needs the principal as decider")
        if cfg.legal and "representative" not in a:
            out.append("a legal-person principal needs a representative")
    if kind == "confirmed" and "proposal" not in ev:
        out.append("confirmed needs evidence.proposal")
    if kind in ("delegated", "attested") and decider == cfg.principal:
        out.append(f"{kind} decider cannot be the principal")
    if kind == "delegated":
        chain = a.get("chain")
        if "under" not in a or not chain:
            out.append("delegated needs under and chain")
        elif chain[0] != cfg.principal or chain[-1] != decider:
            out.append("chain runs from the principal to the decider")
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


def _canon(r: dict) -> str:
    """RFC 8785 for these records (strings, integers, booleans, arrays, objects): sorted keys, no whitespace."""
    return json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fold(records: list[dict], e: Ext, cfg: Config) -> dict:
    """State of one item from all the records a receiver holds for it, in any order. Invalid records are ignored and
    listed, and never block a valid record with the same id; an id reused with different valid content keeps the
    greater canonical form (core section 10)."""
    seen: dict[str, dict] = {}
    ignored: set[str] = set()
    for r in records:
        if validate(r, e, cfg)[1]:
            if r.get("id") is not None:
                ignored.add(r["id"])
            continue
        old = seen.get(r["id"])
        if old is None or _canon(r) > _canon(old):
            seen[r["id"]] = r
    ignored -= seen.keys()
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
