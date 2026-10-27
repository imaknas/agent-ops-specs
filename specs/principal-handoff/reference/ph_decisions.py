"""Reference reading of Principal Handoff Decisions 0.3 (decisions/SPEC.md sections 2 to 4), on ph_core.

  validate(record, config) -> (schema name or None, [errors])
  fold(records, config)    -> the decision's state (core section 6; a withdrawn need: no longer presented)
"""
from __future__ import annotations

import ph_core
from ph_core import Config  # noqa: F401  (re-exported for callers)


def _check(r: dict) -> list[str]:
    if r.get("type") == "settled" and r.get("outcome") == "decided" and "answer" not in r:
        return ["decided needs answer"]
    return []


EXT = ph_core.ext("decisions/0.3", "stop", _check)


def validate(r: dict, cfg: ph_core.Config) -> tuple[str | None, list[str]]:
    return ph_core.validate(r, EXT, cfg)


def fold(records: list[dict], cfg: ph_core.Config) -> dict:
    return ph_core.fold(records, EXT, cfg)
