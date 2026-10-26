"""Minimal JSON Schema (draft 2020-12) validator for the keyword subset the Principal Handoff schemas use:
type, required, properties, enum, const, pattern, items, $ref (a relative path to another schema file). Standard library only.

Other keywords (title, description, $id, $schema) are annotations and ignored. Properties not listed under
`properties` are allowed, as in JSON Schema.
"""
from __future__ import annotations

import json
import pathlib
import re

TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "null": lambda v: v is None,
}


def _same(a, b) -> bool:
    return type(a) is type(b) and a == b


def errors(instance, schema: dict, base: pathlib.Path, path: str = "$") -> list[str]:
    out = []
    if "$ref" in schema:
        target = base / schema["$ref"]
        out += errors(instance, json.loads(target.read_text()), target.parent, path)
    if "type" in schema and not TYPES[schema["type"]](instance):
        return out + [f"{path}: not {schema['type']}"]
    if "const" in schema and not _same(instance, schema["const"]):
        out.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and not any(_same(instance, v) for v in schema["enum"]):
        out.append(f"{path}: not one of {schema['enum']}")
    if "pattern" in schema and isinstance(instance, str) and not re.search(schema["pattern"], instance):
        out.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(instance, dict):
        out += [f"{path}: missing {k}" for k in schema.get("required", []) if k not in instance]
        for k, sub in schema.get("properties", {}).items():
            if k in instance:
                out += errors(instance[k], sub, base, f"{path}.{k}")
    if isinstance(instance, list) and "items" in schema:
        for i, v in enumerate(instance):
            out += errors(v, schema["items"], base, f"{path}[{i}]")
    return out
