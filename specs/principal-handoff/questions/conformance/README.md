# Principal Handoff Questions 0.1 conformance suite

JSON fixtures that any implementation of [Principal Handoff Questions](../SPEC.md) can run. The reference
implementation's runner is [`../../reference/test_questions.py`](../../reference/test_questions.py)
(`cd ../../reference && python3 -m unittest`).

## Common conventions

- Every file is `{"suite": "questions/0.1", "description": …, "cases": [ … ]}`, and every case has a unique `id`.
- Events are full envelopes ([core §3](../../core/SPEC.md#3-event-envelope)). The project is `demo` and question keys
  look like `q-demo-1`; keys are opaque and assigned by the asker.

## Files

### `events.json` (SPEC §4)

`{id, event, valid, schema}`: select a schema by (`type`, `origin`) as in SPEC §4 and validate. For a valid event,
`schema` names the schema it must validate against. For an invalid one, `schema` is `null`: the pair has no schema,
or the event fails the schema it selects.

### `lifecycle.json` (SPEC §3–§4)

`{id, spec, events, expect}`: `events` are all the events one receiver holds for one question, in arrival order.
They may contain duplicates, revisions in any order, forks, ties, cycles and invalid events. `expect` is the question's state as
SPEC §3–§4 defines it:

- `state`: `open`, `answered`, `dismissed`, `withdrawn`, or `unknown` (no valid event at all);
- `current`: id of the current resolution (SPEC §4, Ordering), or `null`;
- `answer`: the current resolution's `answer` if it is an `answered`, otherwise `null`;
- `decided_by`: the current resolution's `decided_by`, or `null`;
- `conflict`: `true` when there is more than one head or a `supersedes` cycle (SPEC §4, Ordering);
- `ignored`: ids of invalid events, sorted in code-point order. An event that fails validation is not a question event and has
  no effect (Q1, core §3).

`expect` does not depend on arrival order. The reference runner checks this by also folding each case reversed.
