# Principal Handoff Decisions 0.5 conformance suite

JSON fixtures that any implementation of [Principal Handoff Decisions](../SPEC.md) can run. The reference runner is
[`../../reference/test_decisions.py`](../../reference/test_decisions.py) (`cd ../../reference && python3 -m
unittest`).

Both files are `{"suite": "decisions/0.5", "principal": …, "description": …, "cases": [ … ]}`; `principal` is the
configured principal identifier (core R6).

- `records.json` (SPEC §3, core §4–§5): `{id, record, valid, schema, principal_type?}`, with a top-level
  `principal_type` (`natural` or `legal`, core R6) that a case may override. Valid records name the schema they
  validate against; invalid ones fail the schema or a validity rule: ownership (core R1–R3, R6), authority (core
  §5.1), the record rules of core §4 and §7, and that `decided` carries an `answer`. Records with module content are
  in the [Evidence](../../evidence/conformance/) and [Criteria](../../criteria/conformance/) suites.
- `lifecycle.json` (core §6, SPEC §2 and §4): `{id, spec, records, expect}`; `records` are all the records one
  receiver holds for one decision, in arrival order (duplicates, revisions, forks, reopening, withdrawal, stale terms,
  claims, invalid records). `expect` is `{state, outcome, settlement, authority, answer, stale, withdrawn, terms_rev,
  conflict, claims, ignored}`. A withdrawn decision has state `withdrawn` unless a settlement is current. `terms_rev`
  is the highest `terms_rev` among the held `raised` and `amended` (0 when none is held); `claims` lists the ids of
  the valid claims held, sorted; `ignored` lists the ids of the invalid records, module records included, sorted
  (valid module records are left to their module and not listed). `expect` does not depend on arrival order: the
  reference runner also folds each case reversed.

A principal side runs both files in full. A requester (core §12) runs `records.json` and compares `lifecycle.json`
only on `settlement`, `outcome`, `answer`, `authority` and `stale`, computed from the need records and the principal
side's records alone. The core's [terms-digest](../../core/conformance/terms-digest.json) and
[conversion](../../core/conformance/convert.json) vectors apply to every implementation.
