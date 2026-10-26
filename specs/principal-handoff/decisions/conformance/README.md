# Principal Handoff Decisions 0.3 conformance suite

JSON fixtures that any implementation of [Principal Handoff Decisions](../SPEC.md) can run. The reference runner is
[`../../reference/test_decisions.py`](../../reference/test_decisions.py) (`cd ../../reference && python3 -m unittest`).

Both files are `{"suite": "decisions/0.3", "principal": …, "description": …, "cases": [ … ]}`; `principal` is the
configured principal identifier (core R6).

- `records.json` (SPEC §3, core §4–§5): `{id, record, valid, schema}`. Valid records name the schema they validate
  against; invalid ones fail the schema, the ownership rules (core R1–R3, R6), the authority rules (core §5), or the
  rule that `decided` carries an `answer`.
- `lifecycle.json` (core §6, SPEC §2 and §4): `{id, spec, records, expect}`; `records` are all the records one receiver
  holds for one decision, in arrival order (duplicates, revisions, forks, reopening, withdrawal, stale terms, claims,
  invalid records). `expect` is `{state, outcome, settlement, authority, answer, stale, withdrawn, terms_rev, conflict,
  claims, ignored}`. A withdrawn decision has state `withdrawn` unless a settlement is current. `expect` does not
  depend on arrival order: the reference runner also folds each case reversed.
