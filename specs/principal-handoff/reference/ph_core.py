"""Reference reading of Principal Handoff Core 0.4 (core/SPEC.md sections 3 to 7).

Standard library only, Python >= 3.11. Extensions plug in through an Ext description:

  Ext(name, schemas_dir, withdrawn_policy, check)   withdrawn_policy is "keep" (Acts) or "stop" (Decisions);
                                                   check(record) -> [errors] adds the extension's own rules
  Config(principal, legal=False)                   the configured principal (core R6)
  validate(record, ext, config)                    -> (schema name or None, [errors])
  fold(records, ext, config)                       -> the item's state, independent of arrival order
  terms_digest(need_record)                        -> "sha-256:<hex>" over the item binding (core section 5.3)
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

NEED = ("raised", "amended", "withdrawn")
SETTLEMENT = ("settled", "reopened")
TYPES = NEED + SETTLEMENT + ("approved", "claimed", "related", "note")  # core section 4
# core section 4: which roles may emit each record type (extensions may only narrow this; their schemas do)
OWNER = {"raised": {"requester"}, "amended": {"requester"}, "withdrawn": {"requester"},
         "settled": {"principal"}, "reopened": {"principal"}, "approved": {"principal"}}
# core section 7: which role emits each relation kind
RELATION_ORIGIN = {"same_as": "principal", "derived_from": "requester", "replaced_by": "requester"}
APPROVAL_PREFIX = "approval:"  # core section 5.3: authority.under naming an approval record of the same item


@dataclass(frozen=True)
class Ext:
    name: str               # "acts/0.4"
    schemas: pathlib.Path
    withdrawn_policy: str   # "keep": stays open and the principal is asked; "stop": no longer presented
    check: Callable[[dict], list[str]] = field(default=lambda r: [])
    approvable: Callable[[dict], bool] = field(default=lambda terms: True)  # terms an approval can be in force for


@dataclass(frozen=True)
class Config:
    principal: str          # the principal identifier, configured out of band (core R6)
    legal: bool = False     # the principal is a legal person (core section 5: representative)


def ext(name: str, policy: str, check: Callable[[dict], list[str]] | None = None,
        approvable: Callable[[dict], bool] | None = None) -> Ext:
    return Ext(name, ROOT / name.split("/")[0] / "schemas", policy, check or (lambda r: []),
               approvable or (lambda terms: True))


def validate(r: dict, e: Ext, cfg: Config) -> tuple[str | None, list[str]]:
    """Schema by (type, origin) as the extension lists it, then the rules a schema cannot state."""
    t = r.get("type")
    path = e.schemas / f"{t}.schema.json"
    if t not in TYPES or not path.exists():
        return None, ["no schema for this type"]
    errs = schema_subset.errors(r, json.loads(path.read_text()), e.schemas)
    if not _bounded(r):
        errs.append("numbers are integers within 2^53 - 1")
    times = [r.get("ts")] + [v.get("at") for v in ((r.get("evidence") or {}).get("verified") or [])
                             if isinstance(v, dict)]
    if any(isinstance(x, str) and _instant(x) is None for x in times):
        errs.append("a time that is not an RFC 3339 date-time")
    due = (r.get("terms") or {}).get("due") if isinstance(r.get("terms"), dict) else None
    if isinstance(due, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", due):
        try:
            date.fromisoformat(due)
        except ValueError:
            errs.append("terms.due is not a calendar date")
    if t in OWNER and r.get("origin") not in OWNER[t]:  # R1, R2
        errs.append(f"origin {r.get('origin')!r} may not emit {t}")
    if r.get("by") == cfg.principal:  # R6: the principal never emits records itself
        errs.append("the principal identifier cannot emit records")
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
        under = (r.get("authority") or {}).get("under", "")
        if under.startswith(APPROVAL_PREFIX) and r["authority"].get("kind") != "delegated":
            errs.append("a settlement under an approval is delegated")
        if under.startswith(APPROVAL_PREFIX) and not (e.schemas / "approved.schema.json").exists():
            errs.append("this extension has no approvals")
        if under == APPROVAL_PREFIX:
            errs.append("approval: names no record")
    if t == "approved":
        errs += _approval(r, cfg)
    if r.get("adopts") and (t != "settled" or (r.get("authority") or {}).get("kind") not in ("confirmed", "attested")):
        errs.append("adopts only on confirmed or attested settlements")
    errs += _evidence(r)
    errs += e.check(r)
    if t == "note" and len((r.get("about") or {}).keys() & {"key", "quote"}) != 1:
        errs.append("about has exactly one of key and quote")
    if t == "note" and "key" in (r.get("about") or {}) and r["about"]["key"] != r.get("key"):
        errs.append("a note about a key carries that key")
    return t, errs


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
    if item == ("uri" in tg) or (not item and tg.keys() - {"uri"}):  # exactly one form
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


def _approval(r: dict, cfg: Config) -> list[str]:
    """core section 5.3: an approval in force comes from a person; a retraction only narrows."""
    ap = r.get("approval") or {}
    if not ap.get("active", True):
        out = [] if r.get("supersedes") else ["a retraction lists the approval it retracts in supersedes"]
        return out + (["terms_digest only on a grant"] if "terms_digest" in ap else [])
    out = [f"a grant needs {m}" for m in ("terms_rev",) if m not in r]
    out += ["a grant needs approval.terms_digest"] if "terms_digest" not in ap else []
    a = r.get("authority")
    if not isinstance(a, dict):
        return out + ["an approval needs authority"]
    out += _authority(r, cfg)
    if a.get("kind") not in ("principal", "confirmed"):
        out.append("an approval comes from the principal: kind principal or confirmed")
    if "presented" not in (r.get("evidence") or {}):
        out.append("an approval needs evidence.presented")
    return out


def _evidence(r: dict) -> list[str]:
    """core section 5.2: verifiable entries and verification results."""
    ev, t, out = r.get("evidence") or {}, r.get("type"), []
    if not isinstance(ev, dict):
        return out
    entries = ev.get("verifiable")
    if isinstance(entries, list):
        if t not in ("claimed", "note", "settled"):
            out.append("verifiable only on claims, notes and settlements")
        if "terms_rev" not in r:
            out.append("a record with verifiable entries carries terms_rev")
        ids = [x.get("id") for x in entries if isinstance(x, dict)]
        if len(ids) != len(set(ids)):
            out.append("verifiable entry ids are unique within the record")
        if any(isinstance(x, dict) and ("proof" in x) == ("proof_ref" in x) for x in entries):
            out.append("a verifiable entry carries exactly one of proof and proof_ref")
    if "verified" in ev and not (t == "settled" or (t == "note" and r.get("origin") == "principal")):
        out.append("verified only on settlements and principal-side notes")
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
    replaced = {s for r in records for s in r.get("supersedes", []) if s in by_id}
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


def terms_digest(need: dict) -> str:
    """core section 5.3: the digest an approval binds, over the item and its terms at one terms_rev."""
    bound = {k: need[k] for k in ("ext", "project", "key", "terms_rev", "terms")}
    return "sha-256:" + hashlib.sha256(_canon(bound).encode("utf-8")).hexdigest()


def _approval_in_force(approvals: list[dict], needs: list[dict], need: dict | None, conflict: bool,
                       settlements: list[dict], e: Ext) -> dict | None:
    """core section 6: the approval in force, if any."""
    if need is None or conflict or need["type"] == "withdrawn" or not e.approvable(need["terms"]):
        return None
    rev = need["terms_rev"]
    if rev != max(n["terms_rev"] for n in needs if n["type"] != "withdrawn"):
        return None
    digest = terms_digest(need)
    if any(terms_digest(n) != digest for n in needs if n["type"] != "withdrawn" and n["terms_rev"] == rev):
        return None
    replaced = {s for r in approvals for s in r.get("supersedes", [])}
    used = {r["authority"]["under"][len(APPROVAL_PREFIX):] for r in settlements
            if r["type"] == "settled" and r["authority"].get("under", "").startswith(APPROVAL_PREFIX)}
    live = [r for r in approvals if r["approval"]["active"] and r["id"] not in replaced and r["id"] not in used
            and r["terms_rev"] == rev and r["approval"]["terms_digest"] == digest
            and not any(_when(s["ts"]) >= _when(r["ts"]) for s in settlements)]
    return _latest(live) if live else None


def fold(records: list[dict], e: Ext, cfg: Config) -> dict:
    """State of one item from all the records a receiver holds for it, in any order. Invalid records are ignored and
    listed, and never block a valid record with the same id; an id reused with different valid content keeps the
    greater canonical form (core section 10)."""
    seen: dict[tuple[str, str], dict] = {}  # ids are scoped by origin (core section 10)
    ignored: set[str] = set()
    for r in records:
        if validate(r, e, cfg)[1]:
            if r.get("id") is not None:
                ignored.add(r["id"])
            continue
        old = seen.get((r["origin"], r["id"]))
        if old is None or _canon(r) > _canon(old):
            seen[(r["origin"], r["id"])] = r
    ignored -= {i for _, i in seen}
    valid = list(seen.values())
    needs = [r for r in valid if r["type"] in NEED]
    need, need_conflict = _register(needs)
    settlements = [r for r in valid if r["type"] in SETTLEMENT]
    settle, settle_conflict = _register(settlements)
    terms_rev = max((r.get("terms_rev", 0) for r in valid if r["type"] in ("raised", "amended")), default=0)
    approval = _approval_in_force([r for r in valid if r["type"] == "approved"], needs, need, need_conflict,
                                  settlements, e)
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
        "approval": approval["id"] if approval else None,
        "claims": sorted(r["id"] for r in valid if r["type"] == "claimed"),
        "ignored": sorted(ignored),
    }
