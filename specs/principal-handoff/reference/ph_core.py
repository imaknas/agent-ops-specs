"""Reference reading of Principal Handoff Core 0.6 (core/SPEC.md sections 3 to 7, 10, 11 and 14).

Standard library only, Python >= 3.11. Extensions plug in through an Ext description:

  Ext(name, schemas_dir, withdrawn_policy, check, modules)
                                                   withdrawn_policy is "keep" (Acts) or "stop" (Decisions);
                                                   check(record) -> [errors] adds the extension's own rules;
                                                   modules maps a module record type to the origins that may emit it
  Config(principal, legal=False)                   the configured principal (core R6)
  parse(text)                                      -> (record or None, [errors]): the strict reading of a record's text
  validate(record, ext, config)                    -> (type or None, [errors])
  fold(records, ext, config)                       -> the item's state, independent of arrival order
  settlement_view(records, ext, config)            -> the part of the state a requester computes (core section 12)
  terms_digest(need_record)                        -> "sha-256:<hex>" over the item and its terms (core section 4)
  relations(records, ext, config)                  -> the item's active relations (section 7)
  replacement(records, ext, config)                -> the target of its single active replaced_by, or None
  convert(record, version)                         -> the record in the other version of its extension, or None
                                                      if it has no form there (section 14, 0.5 <-> 0.6)
  converting_held(records, ext, config)            -> what a party configured for 0.6 that also implements 0.5
                                                      holds (sections 6 and 14)
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from dataclasses import dataclass, field
from datetime import date
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
    name: str               # "acts/0.6"
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


def parse(text: str) -> tuple[dict | None, list[str]]:
    """core section 4: a record is an I-JSON object. This reads what a parsed value can no longer show: a duplicate
    member name and an unpaired surrogate. A fraction, an exponent or an out-of-range integer survives parsing, as a
    float or a large int, and validate() rejects it. NaN and Infinity, which Python's reader takes, are not JSON. The
    caller supplies the text."""
    def members(pairs: list) -> dict:
        if len({k for k, _ in pairs}) != len(pairs):
            raise ValueError("duplicate member name")
        return dict(pairs)

    def constant(name: str) -> None:
        raise ValueError(f"{name} is not JSON")

    try:
        v = json.loads(text, object_pairs_hook=members, parse_constant=constant)
    except (ValueError, RecursionError) as x:
        return None, [str(x)]
    if not isinstance(v, dict):
        return None, ["a record is an object"]
    return (None, ["unpaired surrogate"]) if _unpaired(v) else (v, [])


def _unpaired(v) -> bool:
    """json.loads joins paired escapes, so any surrogate left in a string is unpaired."""
    if isinstance(v, str):
        return any("\ud800" <= c <= "\udfff" for c in v)
    if isinstance(v, dict):
        return any(_unpaired(k) or _unpaired(x) for k, x in v.items())
    return isinstance(v, list) and any(_unpaired(x) for x in v)


def validate(r: dict, e: Ext, cfg: Config) -> tuple[str | None, list[str]]:
    """Schema by (type, origin) as the extension lists it, then the rules a schema cannot state, which read what the
    schema has established. A module record (core section 11) gets the core checks only; its own schema and rules
    belong to the module."""
    t = r.get("type")
    if isinstance(t, str) and t in e.modules:
        errs = schema_subset.errors(r, schema_subset.load(RECORD_SCHEMA), RECORD_SCHEMA.parent)
        if errs:
            return t, errs
        # from here on the schemas' required lists and types guarantee the members read as r[...]
        if r["ext"] != e.name:
            errs.append(f"ext is not {e.name}")
        if r["origin"] not in e.modules[t]:
            errs.append(f"origin {r['origin']!r} may not emit {t}")
        return t, errs + _common(r, cfg)
    if t not in TYPES:
        return None, ["no schema for this type"]
    errs = schema_subset.errors(r, schema_subset.load(e.schemas / f"{t}.schema.json"), e.schemas)
    if errs:
        return t, errs
    # from here on the schemas' required lists and types guarantee the members read as r[...]
    errs = _common(r, cfg)
    if "due" in r.get("terms", {}) and not _calendar_date(r["terms"]["due"]):
        errs.append("terms.due is not a calendar date")
    if t in OWNER and r["origin"] not in OWNER[t]:  # R1, R2
        errs.append(f"origin {r['origin']!r} may not emit {t}")
    rev = r.get("terms_rev")
    if t == "amended" and rev < 2:  # core section 6
        errs.append("amended terms_rev must be at least 2")
    if rev is not None and rev < 1:  # core section 4
        errs.append(f"{t} terms_rev must be at least 1")
    if t == "claimed" and r["origin"] == "principal":  # R3: the owner records, it does not claim
        errs.append("the principal side settles; it does not claim")
    if t == "related":
        errs += _relation(r)
    if t == "settled":
        errs += _authority(r, cfg)
    if "adopts" in r and (t != "settled" or r["authority"]["kind"] not in ("confirmed", "attested")):
        errs.append("adopts only on confirmed or attested settlements")
    errs += e.check(r)
    if t == "note" and len(r["about"].keys() & {"key", "quote"}) != 1:
        errs.append("about has exactly one of key and quote")
    if t == "note" and "key" in r["about"] and r["about"]["key"] != r["key"]:
        errs.append("a note about a key carries that key")
    return t, errs


def _common(r: dict, cfg: Config) -> list[str]:
    """Checks every record gets, module records included (core sections 4, 11 and R6). The core record schema's required
    list guarantees ts."""
    errs = []
    if not _bounded(r):
        errs.append("numbers are integers within 2^53 - 1")
    if _instant(r["ts"]) is None:
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
    """core section 7. The schemas' required lists guarantee relation, its kind and target, origin and project."""
    out, rel = [], r["relation"]
    want, tg = RELATION_ORIGIN[rel["kind"]], rel["target"]
    if r["origin"] != want:
        out.append(f"{rel['kind']} is emitted by {want}")
    item = all(k in tg for k in ("ext", "project", "key"))
    if item == ("uri" in tg) or (not item and tg.keys() & {"ext", "project", "key"}):  # exactly one form
        out.append("relation target must be an item {ext, project, key} or a {uri}")
    if r["origin"] == "principal" and item and tg["project"] != r["project"]:
        out.append("the principal side names another project's item only by uri")
    # naming another deployment's item by uri (R5) is a duty, not a validity rule
    if rel["kind"] == "replaced_by" and not (
            item and tg["ext"] == _name(r) and tg["project"] == r["project"] and tg["key"] != r["key"]):
        out.append("replaced_by targets another item of the same extension and project, in the item form")
    return out


def implemented(r: dict, e: Ext) -> bool:
    """core section 4: whether the record names the extension and version e implements; one that does not is kept
    and not acted on (core section 6)."""
    return r.get("ext") == e.name and r.get("ph") == e.name.split("/")[1]


def _name(r: dict) -> str | None:
    """core section 4: the extension's name is the part of ext before the /."""
    return r["ext"].split("/")[0] if isinstance(r.get("ext"), str) else None


def _authority(r: dict, cfg: Config) -> list[str]:
    """core section 5.1. The schemas' required lists guarantee authority, its kind and its decider."""
    a, ev = r["authority"], r.get("evidence", {})
    kind, decider = a["kind"], a["decider"]
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


def _day(y: int, mo: int, d: int) -> int | None:
    """The day number of a date of the proleptic Gregorian calendar, or None. RFC 3339 years run from 0000; date has no
    year 0, and the calendar repeats every 400 years."""
    try:
        return date(y, mo, d).toordinal() if y else date(400, mo, d).toordinal() - 146097
    except ValueError:
        return None


def _calendar_date(due: str) -> bool:
    """core section 4: terms.due, which the schema has shown to be YYYY-MM-DD, is a real date."""
    return _day(*(int(x) for x in due.split("-"))) is not None


def _instant(ts: str) -> int | None:
    """core section 4: the instant in microseconds, offsets applied, every fractional digit kept; a leap second (:60)
    compares as the last microsecond of its minute. None if ts is not an RFC 3339 date-time."""
    m = TS.fullmatch(ts)
    if not m:
        return None
    y, mo, d, h, mi, sec = (int(x) for x in m.groups()[:6])
    oh, om = int(m.group(10) or 0), int(m.group(11) or 0)
    day = _day(y, mo, d)
    if day is None or h > 23 or mi > 59 or sec > 60 or oh > 23 or om > 59:
        return None
    frac = int((m.group(7) or "0").ljust(6, "0"))
    if sec == 60:
        sec, frac = 59, 999999
    off = (oh * 3600 + om * 60) * (-1 if m.group(9) == "-" else 1)
    return (day * 86400 + h * 3600 + mi * 60 + sec - off) * 1000000 + frac


def _when(ts: str) -> int:
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
    ignored = {r["id"] for r in records if isinstance(r.get("id"), str) and validate(r, e, cfg)[1]}
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


def relations(records: list[dict], e: Ext, cfg: Config) -> list[dict]:
    """core section 7: each relation of the item is identified by its kind and the target's extension name, project
    and key, or by its kind and uri (an exact string); the latest held `related` decides whether it is active. Returns
    the active ones as {kind, target}, sorted. A same_as or derived_from naming the record's own item has no effect."""
    latest: dict[tuple, dict] = {}
    for r in held(records, e, cfg):
        if r["type"] != "related":
            continue
        rel, tg = r["relation"], r["relation"]["target"]
        k = (rel["kind"], "uri", tg["uri"]) if "uri" in tg else (rel["kind"], tg["ext"], tg["project"], tg["key"])
        if k not in latest or (_when(r["ts"]), r["id"]) > (_when(latest[k]["ts"]), latest[k]["id"]):
            latest[k] = r
    out = []
    for k in sorted(latest):
        r = latest[k]
        tg = {m: v for m, v in r["relation"]["target"].items() if m in ("uri", "ext", "project", "key")}
        if r["relation"]["active"] and tg != {"ext": _name(r), "project": r["project"], "key": r["key"]}:
            out.append({"kind": k[0], "target": tg})
    return out


def replacement(records: list[dict], e: Ext, cfg: Config) -> dict | None:
    """core section 7: the target of the item's single active replaced_by; an item with more than one has none."""
    active = [r["target"] for r in relations(records, e, cfg) if r["kind"] == "replaced_by"]
    return active[0] if len(active) == 1 else None


# --- mixed versions (core section 14; the 0.5 <-> 0.6 conversion of core section 14, Acts section 6, Decisions
# section 6 and Criteria section 10)

NAME = re.compile(r"[a-z][a-z0-9-]*")
PROJECT = re.compile(f"[^{schema_subset.WS}]{{1,128}}")  # core section 1: whitespace as ECMAScript defines it


def convert(r: dict, version: str) -> dict | None:
    """r converted to `version` ("0.5" or "0.6") of its extension, from the record alone; None if it has no form in
    that version (core section 14: a 0.5 relation whose target does not convert)."""
    out = {k: v for k, v in r.items()}
    out["ph"], out["ext"] = version, f"{_name(r)}/{version}"
    ev = {k: v for k, v in (r.get("evidence") or {}).items() if k != "proof"}
    if "evidence" in r:
        if ev:
            out["evidence"] = ev
        else:
            del out["evidence"]
    tg = (r.get("relation") or {}).get("target") if r.get("type") == "related" else None
    if isinstance(tg, dict) and isinstance(tg.get("ext"), str):
        t = dict(tg)
        if version == "0.6":
            t["ext"] = tg["ext"].split("/")[0]
            if not NAME.fullmatch(t["ext"]) or not (isinstance(t.get("project"), str)
                                                    and PROJECT.fullmatch(t["project"])):
                return None
        else:
            t["ext"] = f"{tg['ext']}/0.5"
        out["relation"] = {**r["relation"], "target": t}
    return out


def _errors_0_5(r: dict, e: Ext, cfg: Config) -> list[str]:
    """0.5 validity, read as the 0.6 validity of the converted form plus the 0.5 rule that 0.6 relaxes: a
    replaced_by's target.ext was the record's whole ext. A record with no 0.6 form is not held whatever its 0.5
    validity, so that is not decided here."""
    ok = r.get("ph") == "0.5" and isinstance(r.get("ext"), str) and r["ext"] == f"{_name(r)}/0.5"
    n = convert(r, "0.6") if ok else None
    if n is None:
        return ["not a 0.5 record with a 0.6 form"]
    errs = validate(n, e, cfg)[1]
    rel = r.get("relation") or {}
    tg = rel.get("target") or {}
    if r.get("type") == "related" and "ext" in tg and rel.get("kind") == "replaced_by" and tg.get("ext") != r.get("ext"):
        errs.append("0.5: replaced_by targets an item of the same ext")
    return errs


def converting_held(records: list[dict], e: Ext, cfg: Config) -> list[dict]:
    """What a party configured for 0.6 that also implements 0.5 holds (core sections 6 and 14): a record received in
    0.5 counts only if it is valid in 0.5 and has a 0.6 form, and section 10 compares the 0.6 forms."""
    forms = []
    for r in records:
        if r.get("ph") == "0.5":
            if not _errors_0_5(r, e, cfg):
                forms.append(convert(r, "0.6"))
        else:
            forms.append(r)
    return held(forms, e, cfg)
