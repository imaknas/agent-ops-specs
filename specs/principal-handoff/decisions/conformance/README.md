# Principal Handoff Decisions 0.4 conformance suite

JSON fixtures that any implementation of [Principal Handoff Decisions](../SPEC.md) can run. The reference runner is
[`../../reference/test_decisions.py`](../../reference/test_decisions.py) (`cd ../../reference && python3 -m unittest`).

Both files are `{"suite": "decisions/0.4", "principal": …, "description": …, "cases": [ … ]}`; `principal` is the
configured principal identifier (core R6).

- `records.json` (SPEC §3, core §4–§5): `{id, record, valid, schema, principal_type?}`, with a top-level
  `principal_type` (`natural` or `legal`, core R6) that a case may override. Valid records name the schema they validate
  against; invalid ones fail the schema or a validity rule: ownership (core R1–R3, R6), authority (core §5.1), verifiable
  entries and results (core §5.2), approvals (core §5.3), criteria (SPEC §2.1), settlements under an approval (SPEC
  §3), and that `decided` carries an `answer`.
- `lifecycle.json` (core §6, SPEC §2 and §4): `{id, spec, records, expect}`; `records` are all the records one receiver
  holds for one decision, in arrival order (duplicates, revisions, forks, reopening, withdrawal, stale terms, claims,
  invalid records, approvals granted, lapsed, retracted and used, settlements under approvals, audits). `expect` is
  `{state, outcome, settlement, authority, answer, stale, withdrawn, terms_rev, conflict, approval, claims,
  ignored}`; `approval` is the id of the approval in force (core §6), or `null`. A withdrawn decision has state `withdrawn` unless a settlement is current. `expect` does not
  depend on arrival order: the reference runner also folds each case reversed.
