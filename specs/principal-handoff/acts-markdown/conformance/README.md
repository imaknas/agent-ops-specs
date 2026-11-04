# Principal Handoff Acts Markdown binding 0.6 conformance suite

JSON fixtures that any implementation of the [Acts Markdown binding](../SPEC.md) can run. The reference runner is
[`../../reference/test_acts.py`](../../reference/test_acts.py) (`cd ../../reference && python3 -m unittest`). A
registrar also runs the [Acts suite](../../acts/conformance/) as a requester (SPEC §7.1).

## Common conventions

- Every file except `profiles.json` is `{"suite": "acts/0.6", "description": …, "cases": [ … ]}`: the binding has no
  `ext` value of its own and is versioned with Acts. Every case has a unique `id`.
- `profile` names an entry of `profiles.json`. Both profiles have a parameter `principal_tag`, whose value for the
  fixtures is under the profile's `parameters` (`owner` for `en`, `Owner` for `zh-hant`). A case MAY carry
  `parameters`, which override the profile's for that case; such cases exercise other tags.
- `document` is an array of lines; the text is the lines joined with `\n` plus a final `\n`. Line numbers are 0-based.
- A line in `document` may end with `\r`, so that the joined text has CR LF line endings (SPEC §3.2).
- Documents are **compared** as their sequences of non-blank lines with trailing whitespace removed.
- Keys like `task-demo-aaaaaaaaaa` are arbitrary opaque keys, except in `keys.json` and in `register.json`'s `raised`.

## Files

- `profiles.json`: `{"description", "profiles": {<name>: {title, heading, label_open, label_close, label_separator,
  labels: {principal, agent, undecided}, placeholder, marker_render, marker_pattern, parameters?}}}`.
- `parse.json` (SPEC §3.2–§3.4): `{id, profile, document, expect: {sections, tasks, problems, unclosed}}`; `sections`
  are the line numbers of the tasks headings, `tasks` are `{line, assignee, text, key}` in document order,
  `problems` the lines a reader reports (malformed checkbox lines, task-like lines, every tasks heading after the
  first), and `unclosed` the line where an unclosed fence or comment opens, or `null`.
- `keys.json` (SPEC §4.2, example recipe only): `{id, project, text, key}`.
- `relink.json` (SPEC §2 step 2): `{id, profile, document, active, bound?, known?, expect: {relinked, document}}`;
  `active` maps active keys to their latest terms text; the function itself finds which have vanished.
- `register.json` (SPEC §2 step 3): `{id, profile, project, document, bound?, known?, expect: {raised, reported,
  document}}`;
  `raised` is `[{key, text}]`, the items to send `raised` for, in document order, with normalised text; `reported`
  the lines not raised and reported.
- `amend.json` (SPEC §2 step 4): `{id, profile, document, latest, expect: {amended, warn}}`; `latest` maps active keys
  to their latest terms text; `amended` is `[{key, text}]`, `warn` the keys whose holding lines disagree.
- `apply.json` (SPEC §2 step 1, I2, §3.5.2–§3.5.3): `{id, profile, document, record, latest?, bound?, expect:
  {changed, document}}`; `latest` is the registrar's `{text, terms_rev, terms_digest?}` for the key (bound or known),
  absent when it holds no terms for it (a bound key whose stored terms it lost, or a key it neither raised nor
  knows). A `reopened` re-adds a line only for a bound key. Only a principal-side `settled` (strike)
  or `reopened` (re-add) changes the document; a settlement that is stale against `latest`, or whose holding lines
  differ from it, strikes nothing.
- `reconcile.json` (SPEC §2 step 5): `{id, profile, document, open, bound?, expect}`; `open` maps active keys to their
  latest terms text; `expect` is `[{key, action}]` with `action` one of `ticked` (claim done: a ticked principal box),
  `displaced` (marker still present elsewhere: note, no claim), `warn` (vanished, a line looks like a rewrite),
  `claim` (vanished: claim done), and, after those, `closed` for principal task lines carrying a bound key that is not
  active. Whether a vanished key is `warn` or `claim` depends on the similarity measure, which the SPEC leaves to the
  implementation beyond equal normalised texts; `zh-vanished` and `en-vanished-no-section` assume the reference's
  (a `difflib` ratio of at least 0.6 counts as a rewrite).
- A case without `bound` treats every key it names as bound (SPEC §2); `bound: []` means none is. `known` lists keys
  outside the binding whose need records the registrar holds (SPEC §2 step 3); absent means none.
