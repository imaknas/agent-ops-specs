# Principal Handoff Tasks 0.2 conformance suite

JSON fixtures that any implementation of [Principal Handoff Tasks](../SPEC.md) can run. The reference implementation's
runner is [`../../reference/test_tasks.py`](../../reference/test_tasks.py) (`cd ../../reference && python3 -m
unittest`); an adapter for another implementation can follow it closely.

## Common conventions

- Every file except `profiles.json` is `{"suite": "tasks/0.2", "description": …, "cases": [ … ]}`, and every case has a
  unique `id`.
- `profile` names an entry of `profiles.json`. The `zh-hant` profile has a parameter `principal_tag`, which the fixtures
  set to `Owner`. An implementation configured with another tag substitutes it for `Owner` in documents, texts and
  expected outputs (labels `〔Owner〕` and markers `(等 Owner:…)`) before running the cases.
- `document` is an array of lines; the document text is the lines joined with `\n` plus a final `\n`. Line numbers
  in expectations are 0-based indexes into that array.
- Documents are **compared** as their sequences of non-blank lines with trailing whitespace removed (SPEC §8.2):
  where blank lines end up is not part of conformance.
- Project names are `demo` (and `other-project`); keys like `task-demo-aaaaaaaaaa` are arbitrary opaque keys, not
  outputs of any recipe, except in `keys.json` and in the `registered` expectations of `register.json`.

## Files

### `profiles.json`

`{"profiles": {<name>: {heading, label_open, label_close, label_separator, labels: {principal, agent, undecided},
placeholder, marker_render, marker_pattern, parameters?}}}`. `{principal_tag}` inside `labels`, `marker_render` and
`marker_pattern` is a profile parameter (regex-escape it when substituting into `marker_pattern`). `marker_render`
contains `{key}`.

### `parse.json` (SPEC §5.2–§5.4)

`{id, profile, document, expect: {section, tasks, problems}}`

- `section`: whether the document has a tasks section.
- `tasks`: in document order, `{line, assignee, text, key}`, where `assignee` is `principal`, `agent` or `undecided`,
  `text` is trimmed and has the key marker removed, and `key` is `null` for an unkeyed task.
- `problems`: line numbers of malformed checkbox lines (SPEC §5.3 step 5), in order.

### `keys.json` (SPEC §7.2, example recipe only)

`{id, project, text, key}`: the key the example recipe derives. Skip this file if your registrar uses another
recipe; your own recipe must still satisfy SPEC §7.1.

### `register.json` (SPEC §4.2, §5.5.1)

`{id, profile, project, document, expect: {registered, document}}`

- `registered`: `{key, text}` for each `registered` event the registrar sends, in document order. Keys are from the
  example recipe; with another recipe, compare `text` and check that the stamped markers carry your keys.
- `document`: the document after stamping.

Running registration a second time on the expected document must send nothing and change nothing (invariant I4).

### `apply.json` (SPEC §4.3–§4.5, §5.5.2–§5.5.3)

`{id, profile, document, event, expect: {changed, document}}`: apply one event as the registrar. `event` is a full
envelope (SPEC §6). Events whose `origin` is not `principal` must leave the document unchanged (invariant I3).

### `reconcile.json` (SPEC §4.6)

`{id, profile, document, open, expect}`: `open` maps each registered key that has no principal-origin resolution yet to
the text it was registered with. `expect` lists, sorted by key, `{key, action}` for each vanished key, where `action`
is `infer_done` (send an inferred `done`) or `warn` (a task with the same normalised text exists; send nothing). Keys
still present in the document produce no entry. Cases use only clear-cut texts (identical or unrelated), so any
reasonable similarity measure gives the expected result.

### `events.json` (SPEC §6)

`{id, event, valid, schema}`: select a schema by (`type`, `origin`) as in SPEC §6 and validate. For a valid event,
`schema` is the expected schema name (`registered`, `resolution`, `reopened`, `agent-report`, `inferred-done`); for
an invalid one, `schema` is `null` and the event must either have no schema for its (`type`, `origin`) or fail
validation.
