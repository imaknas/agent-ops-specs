# Open readings

*Non-normative. A list of cases, not rules.*

While strengthening the conformance suites, we found cases the specifications' text doesn't clearly decide. Each is
settled once implementations have reported how they read it: by a fixture and a clearer sentence in 0.6.x if they all
agree, in 0.7 if they don't (see the [release candidate](README.md#release-candidate) policy). 0.6.2 settled those on
which they agree. No fixture tests the cases below, so an implementation can pass the suites whichever way it reads them.

If your implementation meets one of these, or you find another, please
[open an issue](https://github.com/imaknas/agent-ops-specs/issues).

"Reference" is [`reference/`](reference/). "Second reading" is a requester written in another language from the documents
alone, by the same author's tools, so it is no independent implementation. Brunna and Muninn are the implementations
[Acts §10](acts/SPEC.md#10-implementations) lists, which share that author too.

## Validity

| Case | One reading | Other reading | Reference | Second reading | Brunna | Muninn |
|---|---|---|---|---|---|---|
| `ext` of `decisions/0.6.1`, or `decisions` | Invalid: not name and two-part version | Kept, not acted on | Invalid | Invalid | Kept | Kept |
| A member defined for other types, on a record that doesn't list it: `answer` or `restore_text` on a `note`, a `note` whose `authority` breaks core §5.1, an unknown `outcome` on a `note`; `terms_rev: 0` or a bad `due` on the module record `approved` | Ignored as an unknown member | Held to its definition | Ignored | Not asked | Not asked | Not asked |
| A byte order mark at the start of the text (RFC 8259 "MAY ignore") | Rejected | Ignored | Rejected | Rejected | Rejected in text, ignored in bytes | Rejected |

On the `ext` case neither reading acts on the record, so no state differs.

## Holding records

- Core §6's records a party "emitted" carry no validity condition, unlike those it has kept. Brunna still validates its
  own.
- Core §14 leaves out records older than N−1. Both brunna and Muninn still read them.

## Suite format

These affect how a case is read, not what a receiver does.

- `expect.claims` can list one id twice, when two origins use it.
- For an id with both an invalid and a valid record, `expect.ignored` omits it for core records and lists it for module
  records.
