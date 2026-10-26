"""Reference reading of Principal Handoff Decisions 0.3 (decisions/SPEC.md sections 2 to 4), on ph_core.

  validate(record, principal=None) -> (schema name or None, [errors])
  fold(records, principal=None)    -> the decision's state (core section 6, withdrawn need: no longer presented)
"""
from __future__ import annotations

import ph_core

EXT = ph_core.ext("decisions/0.3", "stop")


def validate(r: dict, principal: str | None = None) -> tuple[str | None, list[str]]:
    name, errs = ph_core.validate(r, EXT, principal)
    if r.get("type") == "settled" and r.get("outcome") == "decided" and "answer" not in r:
        errs.append("decided needs answer")
    return name, errs


def fold(records: list[dict], principal: str | None = None) -> dict:
    """Records that fail this extension's own rules are ignored like any invalid record."""
    ok = [r for r in records if not validate(r, principal)[1]]
    bad = sorted({r.get("id") for r in records if validate(r, principal)[1] and r.get("id") is not None})
    out = ph_core.fold(ok, EXT, principal)
    out["ignored"] = bad
    return out
