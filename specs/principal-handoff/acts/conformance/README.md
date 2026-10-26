# Principal Handoff Acts 0.3 conformance suite

JSON fixtures that any implementation of [Principal Handoff Acts](../SPEC.md) can run. The reference runner is
[`../../reference/test_acts.py`](../../reference/test_acts.py) (`cd ../../reference && python3 -m unittest`).

## Common conventions

- Every file except `profiles.json` is `{"suite": "acts/0.3", "description": …, "cases": [ … ]}`; `records.json` and
  `lifecycle.json` also carry `principal`, the configured principal identifier (core R6). Every case has a unique `id`.
- `profile` names an entry of `profiles.json`. The `zh-hant` profile has a parameter `principal_tag`, which the
  fixtures set to `Owner`. An implementation configured with another tag substitutes it for `Owner` in documents,
  texts and expected outputs before running the cases.
- `document` is an array of lines; the text is the lines joined with `\n` plus a final `\n`. Line numbers are 0-based.
- Documents are **compared** as their sequences of non-blank lines with trailing whitespace removed.
- Keys like `task-demo-aaaaaaaaaa` are arbitrary opaque keys, except in `keys.json` and in `register.json`'s `raised`.

## Files

- `profiles.json`: `{"profiles": {<name>: {heading, label_open, label_close, label_separator, labels: {principal,
  agent, undecided}, placeholder, marker_render, marker_pattern, parameters?}}}`.
- `parse.json` (SPEC §5.2–§5.4): `{id, profile, document, expect: {section, tasks, problems}}`; `tasks` are
  `{line, assignee, text, key}` in document order, `problems` the line numbers of malformed checkbox lines.
- `keys.json` (SPEC §6.2, example recipe only): `{id, project, text, key}`.
- `register.json` (SPEC §4 step 2): `{id, profile, project, document, expect: {raised, document}}`; `raised` is
  `[{key, text}]`, the items to send `raised` for, in document order.
- `amend.json` (SPEC §4 step 3): `{id, profile, document, latest, expect}`; `latest` maps keys to the item's latest
  terms text, `expect` is `[{key, text}]` for keyed lines whose normalised text differs.
- `apply.json` (SPEC §4 step 1, I2): `{id, profile, document, record, expect: {changed, document}}`. Only a
  principal-side `settled` (strike) or `reopened` with `restore_text` (re-add) changes the document.
- `reconcile.json` (SPEC §4 step 4): `{id, profile, document, open, expect}`; `open` maps raised, unsettled keys to
  their latest terms text; `expect` is `[{key, action}]` for keys missing from the document, `action` being `claim`
  or `warn` (a line looks like a rewrite).
- `records.json` (SPEC §3, core §4–§5): `{id, record, valid, schema}`. Valid records name the schema they validate
  against; invalid ones fail the schema, the ownership rules (core R1–R3, R6) or the authority rules (core §5).
- `lifecycle.json` (core §6, SPEC §2): `{id, spec, records, expect}`; `records` are all the records one receiver holds
  for one act, in arrival order. `expect` is `{state, outcome, settlement, authority, answer, stale, withdrawn,
  terms_rev, conflict, claims, ignored}` and does not depend on arrival order.
