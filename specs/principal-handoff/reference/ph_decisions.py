"""Reference reading of Principal Handoff Decisions 0.4 (decisions/SPEC.md sections 2 to 4), on ph_core.

  validate(record, config) -> (schema name or None, [errors])
  fold(records, config)    -> the decision's state (core section 6; a withdrawn need: no longer presented)
"""
from __future__ import annotations

import ph_core
from ph_core import Config  # noqa: F401  (re-exported for callers)


def _criteria(terms: dict) -> list[str]:
    """decisions section 2.1: rules on criteria a schema cannot state."""
    c = terms.get("criteria")
    if not isinstance(c, dict):
        return []
    out, checks = [], [x for x in c.get("checks") or [] if isinstance(x, dict)]
    ids = [x.get("id") for x in checks]
    if not ids:
        out.append("criteria need at least one check")
    if len(ids) != len(set(ids)):
        out.append("check ids are unique within the criteria")
    if any(not x.get("trust") for x in checks):
        out.append("every check names at least one trust root")
    option = (c.get("answer") or {}).get("option")
    if option is not None and option not in {o.get("id") for o in terms.get("options") or []}:
        out.append("criteria.answer.option must be one of the options")
    return out


def _check(r: dict) -> list[str]:
    t, out = r.get("type"), []
    if t == "settled" and r.get("outcome") == "decided" and "answer" not in r:
        out.append("decided needs answer")
    if t in ("raised", "amended") and isinstance(r.get("terms"), dict):
        ids = [o.get("id") for o in r["terms"].get("options") or [] if isinstance(o, dict)]
        if len(ids) != len(set(ids)):
            out.append("option ids are unique within the terms")
        out += _criteria(r["terms"])
    if t == "settled" and str((r.get("authority") or {}).get("under", "")).startswith(ph_core.APPROVAL_PREFIX):
        verified = (r.get("evidence") or {}).get("verified") or []
        if r.get("outcome") != "decided":
            out.append("a settlement under an approval records the approved answer")
        if not verified or any(v.get("result") != "valid" for v in verified if isinstance(v, dict)):
            out.append("a settlement under an approval carries only valid verification results")
    return out


EXT = ph_core.ext("decisions/0.4", "stop", _check, approvable=lambda terms: "criteria" in terms)


def validate(r: dict, cfg: ph_core.Config) -> tuple[str | None, list[str]]:
    return ph_core.validate(r, EXT, cfg)


def fold(records: list[dict], cfg: ph_core.Config) -> dict:
    return ph_core.fold(records, EXT, cfg)
