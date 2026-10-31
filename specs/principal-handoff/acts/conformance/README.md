# Principal Handoff Acts 0.4 conformance suite

JSON fixtures that any implementation of [Principal Handoff Acts](../SPEC.md) can run. The reference runner is
[`../../reference/test_acts.py`](../../reference/test_acts.py) (`cd ../../reference && python3 -m unittest`).

## Common conventions

- Every file except `profiles.json` is `{"suite": "acts/0.4", "description": …, "cases": [ … ]}`; `records.json` and
  `lifecycle.json` also carry `principal`, the configured principal identifier (core R6). Every case has a unique `id`.
- `profile` names an entry of `profiles.json`. The `zh-hant` profile has a parameter `principal_tag`, which the
  fixtures set to `Owner`. An implementation configured with another tag substitutes it for `Owner` in documents,
  texts and expected outputs before running the cases.
- `document` is an array of lines; the text is the lines joined with `\n` plus a final `\n`. Line numbers are 0-based.
- A line in `document` may end with `\r`, so that the joined text has CR LF line endings (SPEC §5.2).
- Documents are **compared** as their sequences of non-blank lines with trailing whitespace removed.
- Keys like `task-demo-aaaaaaaaaa` are arbitrary opaque keys, except in `keys.json` and in `register.json`'s `raised`.

## Files

- `profiles.json`: `{"description", "profiles": {<name>: {title, heading, label_open, label_close, label_separator,
  labels: {principal, agent, undecided}, placeholder, marker_render, marker_pattern, parameters?}}}`.
- `parse.json` (SPEC §5.2–§5.4): `{id, profile, document, expect: {sections, tasks, problems, unclosed}}`; `sections`
  are the line numbers of the tasks headings, `tasks` are `{line, assignee, text, key}` in document order,
  `problems` the lines a reader reports (malformed checkbox lines, task-like lines, every tasks heading after the
  first), and `unclosed` the line where an unclosed fence or comment opens, or `null`.
- `keys.json` (SPEC §6.2, example recipe only): `{id, project, text, key}`.
- `relink.json` (SPEC §4 step 2): `{id, profile, document, active, bound?, expect: {relinked, document}}`; `active`
  maps active keys to their latest terms text; the function itself finds which have vanished.
- `register.json` (SPEC §4 step 3): `{id, profile, project, document, bound?, expect: {raised, reported, document}}`;
  `raised` is `[{key, text}]`, the items to send `raised` for, in document order, with normalised text; `reported`
  the lines not raised and reported.
- `amend.json` (SPEC §4 step 4): `{id, profile, document, latest, expect: {amended, warn}}`; `latest` maps active keys
  to their latest terms text; `amended` is `[{key, text}]`, `warn` the keys whose holding lines disagree.
- `apply.json` (SPEC §4 step 1, I2, §5.5.2–§5.5.3): `{id, profile, document, record, latest?, expect: {changed,
  document}}`; `latest` is the registrar's `{text, terms_rev, terms_digest?}` for the key, absent when it holds no
  terms for it (a key it did not raise, or one whose stored terms it lost). Only a principal-side `settled` (strike)
  or `reopened` (re-add) changes the document; a settlement that is stale against `latest`, or whose holding lines
  differ from it, strikes nothing.
- `reconcile.json` (SPEC §4 step 5): `{id, profile, document, open, bound?, expect}`; `open` maps active keys to their
  latest terms text; `expect` is `[{key, action}]` with `action` one of `ticked` (claim done: a ticked principal box),
  `displaced` (marker still present elsewhere: note, no claim), `warn` (vanished, a line looks like a rewrite),
  `claim` (vanished: claim done), and, after those, `closed` for principal task lines carrying a bound key that is not
  active. Whether a vanished key is `warn` or `claim` depends on the similarity measure, which the SPEC leaves to the
  implementation beyond equal normalised texts; `zh-vanished` and `en-vanished-no-section` assume the reference's
  (a `difflib` ratio of at least 0.6 counts as a rewrite).
- A case without `bound` treats every key it names as bound (SPEC §4); `bound: []` means none is.
- `records.json` (SPEC §3, core §4–§5): `{id, record, valid, schema, principal_type?}`, with a top-level
  `principal_type` (`natural` or `legal`, core R6) that a case may override. Valid records name the schema they validate
  against; invalid ones fail the schema or a validity rule of core §4–§7 or SPEC §3.
- `lifecycle.json` (core §6, SPEC §2): `{id, spec, records, expect}`; `records` are all the records one receiver holds
  for one act, in arrival order. `expect` is `{state, outcome, settlement, authority, answer, stale, withdrawn,
  terms_rev, conflict, approval, claims, ignored}` and does not depend on arrival order.
- The core's [terms-digest vectors](../../core/conformance/terms-digest.json) apply to every implementation.
