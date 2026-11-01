"""Reference reading of Principal Handoff Core 0.5 (core/SPEC.md sections 3 to 7, 10, 11 and 14).

Standard library only, Python >= 3.11. Extensions plug in through an Ext description:

  Ext(name, schemas_dir, withdrawn_policy, check, modules)
                                                   withdrawn_policy is "keep" (Acts) or "stop" (Decisions);
                                                   check(record) -> [errors] adds the extension's own rules;
                                                   modules maps a module record type to the origins that may emit it
  Config(principal, legal=False)                   the configured principal (core R6)
  validate(record, ext, config)                    -> (type or None, [errors])
  fold(records, ext, config)                       -> the item's state, independent of arrival order
  settlement_view(records, ext, config)            -> the part of the state a requester computes (core section 12)
  terms_digest(need_record)                        -> "sha-256:<hex>" over the item and its terms (core section 4)
  convert(record, version, held)                   -> the record in another version of its extension (section 14)
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Callable

import schema_subset

ROOT = pathlib.Path(__file__).resolve().parent.parent
RECORD_SCHEMA = ROOT / "core" / "schemas" / "record.schema.json"

NEED = ("raised", "amended", "withdrawn")
SETTLEMENT = ("settled", "reopened")
TYPES = NEED + SETTLEMENT + ("claimed", "related", "note")  # core section 4
# core section 4: which roles may emit each record type (extensions may only narrow this; their schemas do)
OWNER = {"raised": {"requester"}, "amended": {"requester"}, "withdrawn": {"requester"},
         "settled": {"principal"}, "reopened": {"principal"}}
# core section 7: which role emits each relation kind
RELATION_ORIGIN = {"same_as": "principal", "derived_from": "requester", "replaced_by": "requester"}
VIEW = ("settlement", "outcome", "answer", "authority", "stale")  # the settlement view (core section 6)


@dataclass(frozen=True)
class Ext:
    name: str               # "acts/0.5"
    schemas: pathlib.Path
    withdrawn_policy: str   # "keep": stays open and the principal is asked; "stop": no longer presented
    check: Callable[[dict], list[str]] = field(default=lambda r: [])
    modules: dict = field(default_factory=dict)  # module record type -> origins the extension's table lists


@dataclass(frozen=True)
class Config:
    principal: str          # the principal identifier, configured out of band (core R6)
    legal: bool = False     # the principal is a legal person (core section 5: representative)


def ext(name: str, policy: str, check: Callable[[dict], list[str]] | None = None,
        modules: dict | None = None) -> Ext:
    return Ext(name, ROOT / name.split("/")[0] / "schemas", policy, check or (lambda r: []), modules or {})


def validate(r: dict, e: Ext, cfg: Config) -> tuple[str | None, list[str]]:
    """Schema by (type, origin) as the extension lists it, then the rules a schema cannot state. A module record
    (core section 11) gets the core checks only; its own schema and rules belong to the module."""
    t = r.get("type")
    if t in e.modules:
        errs = schema_subset.errors(r, json.loads(RECORD_SCHEMA.read_text()), RECORD_SCHEMA.parent)
        if r.get("ext") != e.name:
            errs.append(f"ext is not {e.name}")
        if r.get("origin") not in e.modules[t]:
            errs.append(f"origin {r.get('origin')!r} may not emit {t}")
        return t, errs + _common(r, cfg)
    path = e.schemas / f"{t}.schema.json"
    if t not in TYPES or not path.exists():
        return None, ["no schema for this type"]
    errs = schema_subset.errors(r, json.loads(path.read_text()), e.schemas) + _common(r, cfg)
    due = (r.get("terms") or {}).get("due") if isinstance(r.get("terms"), dict) else None
    if isinstance(due, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", due):
        try:
            date.fromisoformat(due)
        except ValueError:
            errs.append("terms.due is not a calendar date")
    if t in OWNER and r.get("origin") not in OWNER[t]:  # R1, R2
        errs.append(f"origin {r.get('origin')!r} may not emit {t}")
    rev = r.get("terms_rev")
    if t == "amended" and isinstance(rev, int) and rev < 2:  # core section 6
        errs.append("amended terms_rev must be at least 2")
    if t not in ("raised", "amended") and isinstance(rev, int) and rev < 1:
        errs.append(f"{t} terms_rev must be at least 1")
    if t == "claimed" and r.get("origin") == "principal":  # R3: the owner records, it does not claim
        errs.append("the principal side settles; it does not claim")
    if t == "related":
        errs += _relation(r)
    if t == "settled":
        errs += _authority(r, cfg)
    if "adopts" in r and (t != "settled" or (r.get("authority") or {}).get("kind") not in ("confirmed", "attested")):
        errs.append("adopts only on confirmed or attested settlements")
    errs += e.check(r)
    if t == "note" and len((r.get("about") or {}).keys() & {"key", "quote"}) != 1:
        errs.append("about has exactly one of key and quote")
    if t == "note" and "key" in (r.get("about") or {}) and r["about"]["key"] != r.get("key"):
        errs.append("a note about a key carries that key")
    return t, errs


def _common(r: dict, cfg: Config) -> list[str]:
    """Checks every record gets, module records included (core sections 4, 11 and R6)."""
    errs = []
    if not _bounded(r):
        errs.append("numbers are integers within 2^53 - 1")
    if isinstance(r.get("ts"), str) and _instant(r["ts"]) is None:
        errs.append("ts is not an RFC 3339 date-time")
    if r.get("by") == cfg.principal:  # R6: the principal never emits records itself
        errs.append("the principal identifier cannot emit records")
    return errs


def _bounded(v) -> bool:
    """core section 4: every number in a record is an integer every receiver serialises alike."""
    if isinstance(v, bool) or isinstance(v, str) or v is None:
        return True
    if isinstance(v, int):
        return abs(v) <= 2 ** 53 - 1
    if isinstance(v, dict):
        return all(_bounded(x) for x in v.values())
    if isinstance(v, list):
        return all(_bounded(x) for x in v)
    return False


def _relation(r: dict) -> list[str]:
    """core section 7."""
    out, rel = [], r.get("relation") or {}
    want = RELATION_ORIGIN.get(rel.get("kind"))
    if want and r.get("origin") != want:
        out.append(f"{rel.get('kind')} is emitted by {want}")
    tg = rel.get("target") or {}
    item = all(k in tg for k in ("ext", "project", "key"))
    if item == ("uri" in tg) or (not item and tg.keys() & {"ext", "project", "key"}):  # exactly one form
        out.append("relation target must be an item {ext, project, key} or a {uri}")
    if r.get("origin") == "principal" and item and tg["project"] != r.get("project"):
        out.append("the principal side names another project's item only by uri")
    if rel.get("kind") == "replaced_by" and not (
            item and tg["ext"] == r.get("ext") and tg["project"] == r.get("project") and tg["key"] != r.get("key")):
        out.append("replaced_by targets another item of the same extension and project")
    return out


def _authority(r: dict, cfg: Config) -> list[str]:
    """core section 5.1."""
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


TS = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,6}))?"
                r"(?:([Zz])|([+-])([0-9]{2}):([0-9]{2}))")


def _instant(ts: str) -> datetime | None:
    """core section 4: an instant, offsets applied, every fractional digit kept; a leap second (:60) compares as the
    last microsecond of its minute. None if ts is not an RFC 3339 date-time."""
    m = TS.fullmatch(ts)
    if not m:
        return None
    y, mo, d, h, mi, sec = (int(x) for x in m.groups()[:6])
    frac = int((m.group(7) or "0").ljust(6, "0"))
    if sec == 60:
        sec, frac = 59, 999999
    try:
        off = timedelta(0) if m.group(8) else (1 if m.group(9) == "+" else -1) * timedelta(
            hours=int(m.group(10)), minutes=int(m.group(11)))
        return datetime(y, mo, d, h, mi, sec, frac, tzinfo=timezone(off))
    except ValueError:
        return None


def _when(ts: str) -> datetime:
    return _instant(ts)


def _latest(records: list[dict]) -> dict:
    return max(records, key=lambda r: (_when(r["ts"]), r["id"]))


def _register(records: list[dict]) -> tuple[dict | None, bool]:
    """core section 6: current record (latest head, ties by greater id) and whether there is a conflict."""
    if not records:
        return None, False
    by_id = {r["id"]: r for r in records}
    replaced = {s for r in records for s in r.get("supersedes", []) if s in by_id and s != r["id"]}  # self: still a head
    heads = [r for r in records if r["id"] not in replaced] or records
    return _latest(heads), len(heads) > 1 or _cycle(by_id)


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


def _canon(v) -> str:
    """RFC 8785 for these records (strings, integers, booleans, null, arrays, objects): member names sorted by their
    UTF-16 code units, no whitespace, strings escaped as JSON.stringify does."""
    if isinstance(v, dict):
        keys = sorted(v, key=lambda k: k.encode("utf-16-be"))
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + _canon(v[k]) for k in keys) + "}"
    if isinstance(v, list):
        return "[" + ",".join(_canon(x) for x in v) + "]"
    return json.dumps(v, ensure_ascii=False)


def digest_input(need: dict) -> dict:
    """core section 4: the object a terms digest is computed over; ext is the extension's name, without its version."""
    return {"ext": need["ext"].split("/")[0], "project": need["project"], "key": need["key"],
            "terms_rev": need["terms_rev"], "terms": need["terms"]}


def terms_digest(need: dict) -> str:
    """core section 4: the digest a settlement carries, over the item and its terms at one terms_rev."""
    return "sha-256:" + hashlib.sha256(_canon(digest_input(need)).encode("utf-8")).hexdigest()


def terms_digest_0_4(need: dict) -> str:
    """Core 0.4's terms digest, over the full ext value (version included); used only to convert 0.4 records."""
    bound = {k: need[k] for k in ("ext", "project", "key", "terms_rev", "terms")}
    return "sha-256:" + hashlib.sha256(_canon(bound).encode("utf-8")).hexdigest()


def held(records: list[dict], e: Ext, cfg: Config) -> list[dict]:
    """The valid records of the types the core folds, one per (origin, id): an invalid record never blocks a valid one
    with the same id, an id reused with different valid content keeps the greater canonical form, and a record never
    displaces one of another type, module records included (core section 10)."""
    seen: dict[tuple[str, str, str], dict] = {}
    for r in records:
        if r.get("type") not in TYPES or validate(r, e, cfg)[1]:
            continue
        k = (r["origin"], r["type"], r["id"])  # a record never displaces one of another type
        old = seen.get(k)
        if old is None or _canon(r) > _canon(old):
            seen[k] = r
    return list(seen.values())


def fold(records: list[dict], e: Ext, cfg: Config) -> dict:
    """State of one item from all the records a receiver holds for it, in any order. Invalid records are ignored and
    listed; valid module records are left to their module and not listed (core section 11)."""
    valid = held(records, e, cfg)
    ignored = {r["id"] for r in records if r.get("id") is not None and validate(r, e, cfg)[1]}
    ignored -= {r["id"] for r in valid}
    needs = [r for r in valid if r["type"] in NEED]
    need, need_conflict = _register(needs)
    settlements = [r for r in valid if r["type"] in SETTLEMENT]
    settle, settle_conflict = _register(settlements)
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
        "stale": bool(settled and (settled.get("terms_rev", 0) < terms_rev or (
            need is not None and need["type"] != "withdrawn" and need["terms_rev"] == settled["terms_rev"]
            and terms_digest(need) != settled["terms_digest"]))),
        "withdrawn": bool(need and need["type"] == "withdrawn"),
        "terms_rev": terms_rev,
        "conflict": need_conflict or settle_conflict,
        "claims": sorted(r["id"] for r in valid if r["type"] == "claimed"),
        "ignored": sorted(ignored),
    }


def settlement_view(records: list[dict], e: Ext, cfg: Config) -> dict:
    """core sections 6 and 12: what a requester computes, from its need records and the principal side's records."""
    mine = [r for r in records if r.get("type") in NEED + SETTLEMENT]
    state = fold(mine, e, cfg)
    return {k: state[k] for k in VIEW}


# --- mixed versions (core section 14; the 0.4 <-> 0.5 conversion of Acts section 8, Decisions section 6, Criteria
# section 10)

def convert(r: dict, version: str, records: list[dict]) -> dict:
    """r converted to `version` ("0.4" or "0.5") of its extension, given the records the converter holds about the item
    (in either version). A converter keeps what it received and converts again at each fold (core section 14)."""
    name = r["ext"].split("/")[0]
    out = {k: v for k, v in r.items()}
    out["ph"], out["ext"] = version, f"{name}/{version}"
    ev = {k: v for k, v in (r.get("evidence") or {}).items() if k != "proof"}
    if "evidence" in r:
        if ev:
            out["evidence"] = ev
        else:
            del out["evidence"]
    old = terms_digest_0_4 if version == "0.5" else terms_digest
    new = terms_digest if version == "0.5" else terms_digest_0_4
    needs = [{**n, "ext": f"{name}/{version}"} for n in records
             if n.get("type") in ("raised", "amended") and n.get("terms_rev") == r.get("terms_rev")]
    source = r["ext"]

    def redigest(value: str) -> str:  # the held need record whose source digest matches, else the value as it is
        match = [n for n in needs if old({**n, "ext": source}) == value]
        return new(match[0]) if match else value

    if r.get("type") == "settled":
        out["terms_digest"] = redigest(r["terms_digest"])
    if r.get("type") == "approved" and (r.get("approval") or {}).get("active"):
        # Criteria section 10: a converted grant names no `after`, so it is in force only while no settlement is held
        ap = {k: v for k, v in r["approval"].items() if k != "after"}
        ap["terms_digest"] = redigest(r["approval"].get("terms_digest", ""))
        out["approval"] = ap
    return out
