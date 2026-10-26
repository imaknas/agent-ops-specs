"""Reference reading of Principal Handoff Questions 0.1 (questions/SPEC.md sections 3 and 4).

Standard library only, Python >= 3.10.

  validate(event)  -> (schema name or None, [errors])     dispatch on (type, origin) and validate
  fold(events)     -> {"state", "current", "answer", "decided_by", "conflict", "ignored"}
                      the state of one question from its events, in any order, with duplicates
"""
from __future__ import annotations

import json
import pathlib
from datetime import datetime

import schema_subset

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "questions" / "schemas"
EXT = "questions/0.1"

# questions/SPEC.md section 4: which schema an event must validate against, by (type, origin)
DISPATCH = {
    ("asked", "agent"): "asked",
    ("answered", "principal"): "answered",
    ("dismissed", "principal"): "dismissed",
    ("withdrawn", "agent"): "withdrawn",
}
RESOLUTIONS = ("answered", "dismissed")


def validate(event: dict) -> tuple[str | None, list[str]]:
    name = DISPATCH.get((event.get("type"), event.get("origin")))
    if name is None:
        return None, ["no schema for this type and origin"]
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text())
    return name, schema_subset.errors(event, schema, SCHEMAS)


def _when(event: dict) -> datetime:
    return datetime.fromisoformat(event["ts"].replace("Z", "+00:00").replace("z", "+00:00"))


def fold(events: list[dict]) -> dict:
    """State of one question. Invalid events are ignored (their ids listed); duplicates count once (Q5)."""
    seen: dict[str, dict] = {}
    ignored: list[str] = []
    for e in events:
        if e.get("id") in seen:
            continue
        if validate(e)[1]:
            if e.get("id") not in ignored:
                ignored.append(e.get("id"))
            continue
        seen[e["id"]] = e
    valid = list(seen.values())
    resolutions = [e for e in valid if e["type"] in RESOLUTIONS]
    replaced = {e["supersedes"] for e in resolutions if "supersedes" in e}
    heads = [e for e in resolutions if e["id"] not in replaced]
    current, conflict = None, False
    if heads:
        current = max(heads, key=_when)
        conflict = len(heads) > 1
    elif resolutions:  # every resolution is replaced by another: a cycle, which only a person can sort out
        current, conflict = max(resolutions, key=_when), True
    if any(e["type"] == "withdrawn" for e in valid):
        state = "withdrawn"
    elif current:
        state = current["type"]
    elif any(e["type"] == "asked" for e in valid):
        state = "open"
    else:
        state = "unknown"
    return {
        "state": state,
        "current": current["id"] if current else None,
        "answer": current.get("answer") if current and current["type"] == "answered" else None,
        "decided_by": current.get("decided_by") if current else None,
        "conflict": conflict,
        "ignored": ignored,
    }
