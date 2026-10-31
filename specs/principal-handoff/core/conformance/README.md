# Principal Handoff Core 0.4 conformance vectors

JSON vectors for rules of the [core](../SPEC.md) that every extension shares. The reference runner is
[`../../reference/test_core.py`](../../reference/test_core.py) (`cd ../../reference && python3 -m unittest`). The
record, ownership, authority, evidence and state rules of the core are exercised through each extension's suite
([Acts](../../acts/conformance/), [Decisions](../../decisions/conformance/)).

- `terms-digest.json` (SPEC §5.3): `{"suite": "core/0.4", "description", "cases": [{id, record, canonical, digest}]}`.
  `record` is a need record; `canonical` is the RFC 8785 serialisation of the object with exactly its `ext`,
  `project`, `key`, `terms_rev` and `terms`; `digest` is `sha-256:` + the lowercase hex SHA-256 of `canonical`'s UTF-8
  bytes. The cases cover member order, non-ASCII text, and characters JSON must escape (a newline, a quote, a tab, a
  backslash, U+001F) next to ones it must not (U+007F, `é`, and a character outside the Basic Multilingual Plane).
