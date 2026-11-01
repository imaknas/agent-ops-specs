# Principal Handoff Core 0.5 conformance vectors

JSON vectors for rules of the [core](../SPEC.md) that every extension shares. The reference runner is
[`../../reference/test_core.py`](../../reference/test_core.py) (`cd ../../reference && python3 -m unittest`). The
record, ownership, authority and state rules of the core are exercised through each extension's suite
([Acts](../../acts/conformance/), [Decisions](../../decisions/conformance/)); module rules through each module's
([Evidence](../../evidence/conformance/), [Criteria](../../criteria/conformance/)).

- `terms-digest.json` (SPEC §4): `{"suite": "core/0.5", "description", "cases": [{id, record, canonical, digest}]}`.
  `record` is a need record; `canonical` is the RFC 8785 serialisation of the object with exactly `ext` (the
  extension's name without its version), `project`, `key`, `terms_rev` and `terms`; `digest` is `sha-256:` + the
  lowercase hex SHA-256 of `canonical`'s UTF-8 bytes. The cases cover member order, non-ASCII text, and characters
  JSON must escape (a newline, a quote, a tab, a backslash, U+001F) next to ones it must not (U+007F, `é`, and a
  character outside the Basic Multilingual Plane).
- `convert.json` (SPEC §14, Acts §6, Decisions §6, Criteria §10): `{"suite": "core/0.5", "description", "cases": [{id,
  record, to, held, expect}]}`. `record` is converted to version `to` (`"0.4"` or `"0.5"`) by a converter holding the
  records `held` about the item; `expect` is the converted record. A converter converts again at each fold, so a
  digest kept because the need record at the settlement's `terms_rev` is not held yet is replaced once it is. The
  cases cover need records and notes (only `ph` and `ext` change), settlements (the terms digest is replaced by that
  of the held need record whose old digest matches, kept when none matches, and `evidence.proof` is removed), and
  Criteria grants (cases with `"module": "criteria"`, only for parties that implement Criteria: a grant converted up
  names no `approval.after`, and `after` is removed going down).
