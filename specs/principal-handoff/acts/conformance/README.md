# Principal Handoff Acts 0.5 conformance suite

JSON fixtures that any implementation of [Principal Handoff Acts](../SPEC.md) can run. The reference runner is
[`../../reference/test_acts.py`](../../reference/test_acts.py) (`cd ../../reference && python3 -m unittest`). The
fixtures of the [Acts Markdown binding](../../acts-markdown/SPEC.md) are in
[`../../acts-markdown/conformance/`](../../acts-markdown/conformance/).

## Common conventions

- Every file is `{"suite": "acts/0.5", "description": …, "principal": …, "cases": [ … ]}`, where `principal` is the
  configured principal identifier (core R6). Every case has a unique `id`.

## Files

- `records.json` (SPEC §3, core §4–§5): `{id, record, valid, schema, principal_type?}`, with a top-level
  `principal_type` (`natural` or `legal`, core R6) that a case may override. Valid records name the schema they
  validate against; invalid ones fail the schema or a validity rule of core §4–§7 or SPEC §3. Records with Evidence
  content are in the [Evidence suite](../../evidence/conformance/).
- `lifecycle.json` (core §6, SPEC §2): `{id, spec, records, expect}`; `records` are all the records one receiver holds
  for one act, in arrival order. `expect` is `{state, outcome, settlement, authority, answer, stale, withdrawn,
  terms_rev, conflict, claims, ignored}`, as the Decisions suite defines them, and does not depend on arrival order. A
  requester (core §12) compares only `settlement`, `outcome`, `answer`, `authority` and `stale`, computed from the
  need records and the principal side's records alone.
- The core's [terms-digest](../../core/conformance/terms-digest.json) and
  [conversion](../../core/conformance/convert.json) vectors apply to every implementation.
