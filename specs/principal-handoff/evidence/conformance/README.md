# Principal Handoff Evidence 0.6 conformance suite

JSON fixtures for the [Evidence module](../SPEC.md). The reference runner is
[`../../reference/test_evidence.py`](../../reference/test_evidence.py) (`cd ../../reference && python3 -m unittest`).

- `records.json` (SPEC §2, core §11): `{"suite": "evidence/0.6", "principal", "principal_type", "description",
  "cases": [{id, record, valid, schema?, evidence, principal_type?}]}`. `record` is an Acts or a Decisions record
  (its `ext` says which). `valid` is whether it is valid under the core and its extension, the same for every receiver
  whether or not it implements this module, and `schema` the type it validates as when it is valid; `evidence` is
  `used` when a verifier keeps the record's `verifiable` and `verified`, and `ignored` when the record breaks a
  structural rule of SPEC §2. A malformed entry never makes a record invalid.
