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


def _cycle(resolutions: list[dict]) -> bool:
    """True when supersedes links among the held resolutions loop back on themselves."""
    by_id = {e["id"]: e for e in resolutions}
    for start in resolutions:
        seen, e = set(), start
        while e is not None and "supersedes" in e:
            if e["id"] in seen:
                return True
            seen.add(e["id"])
            e = by_id.get(e["supersedes"])
    return False


def fold(events: list[dict]) -> dict:
    """State of one question (SPEC section 3, and Ordering in section 4). Invalid events are ignored and listed;
    an id counts once (core section 4)."""
    seen: dict[str, dict] = {}
    ignored: set[str] = set()
    for e in events:
        if e.get("id") in seen:
            continue
        if validate(e)[1]:
            ignored.add(e.get("id"))
            continue
        seen[e["id"]] = e
    valid = list(seen.values())
    resolutions = [e for e in valid if e["type"] in RESOLUTIONS]
    replaced = {e["supersedes"] for e in resolutions if "supersedes" in e}
    heads = [e for e in resolutions if e["id"] not in replaced] or resolutions
    current = max(heads, key=lambda e: (_when(e), e["id"])) if heads else None
    conflict = len(heads) > 1 or _cycle(resolutions)
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
        "ignored": sorted(i for i in ignored if i is not None),
    }
