# Principal Handoff Criteria 0.6 conformance suite

JSON fixtures for the [Criteria module](../SPEC.md). The reference runner is
[`../../reference/test_criteria.py`](../../reference/test_criteria.py) (`cd ../../reference && python3 -m unittest`).

Both files are `{"suite": "criteria/0.6", "principal": …, "description": …, "cases": [ … ]}`.

- `records.json` (SPEC §2, §7, core §11): `{id, record, valid, schema?, criteria, principal_type?}`. `valid` is
  whether the record is valid under the core and Decisions, the same for every receiver whether or not it implements
  this module (an `approved` record gets the core checks only, core §11), and `schema` the type it validates as when
  it is valid; `criteria` is `used` when this module uses the record's module content (SPEC §7) and `ignored` when the
  record breaks a structural rule.
- `lifecycle.json` (SPEC §4, core §6): `{id, spec, records, expect}`; `records` are the records a principal side holds
  for one decision (grants, lapses, retractions, settlements under approvals, audits), in arrival order. `expect` is
  the Decisions state (as in [`../../decisions/conformance/`](../../decisions/conformance/)) plus `approval`, the id
  of the approval in force or `null`. Only a principal side computes `approval`. The runner also checks that the state
  is the same without the `approved` records (core §11) and that `expect` does not depend on arrival order.
