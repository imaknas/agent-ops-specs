"""Reference reading of Principal Handoff Decisions 0.5 (decisions/SPEC.md sections 2 to 4), on ph_core.

  validate(record, config)        -> (type or None, [errors])
  fold(records, config)           -> the decision's state (core section 6; a withdrawn need: no longer presented)
  settlement_view(records, config) -> what a requester computes (core section 12)
"""
from __future__ import annotations

import ph_core
from ph_core import Config  # noqa: F401  (re-exported for callers)


def _check(r: dict) -> list[str]:
    t, out = r.get("type"), []
    if t == "settled" and r.get("outcome") == "decided" and "answer" not in r:
        out.append("decided needs answer")
    if t in ("raised", "amended") and isinstance(r.get("terms"), dict):
        ids = [o.get("id") for o in r["terms"].get("options") or [] if isinstance(o, dict)]
        if len(ids) != len(set(ids)):
            out.append("option ids are unique within the terms")
    return out


# section 3: approved is a pair of the Criteria module, which only receivers implementing it act on
EXT = ph_core.ext("decisions/0.5", "stop", _check, modules={"approved": {"principal"}})


def validate(r: dict, cfg: ph_core.Config) -> tuple[str | None, list[str]]:
    return ph_core.validate(r, EXT, cfg)


def fold(records: list[dict], cfg: ph_core.Config) -> dict:
    return ph_core.fold(records, EXT, cfg)


def settlement_view(records: list[dict], cfg: ph_core.Config) -> dict:
    return ph_core.settlement_view(records, EXT, cfg)
