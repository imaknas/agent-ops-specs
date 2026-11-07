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
| A member defined for other types, on a core type that doesn't list it: `answer` or `restore_text` on a `note`; an extension's or core §5's and §7's rules on a type they don't name, such as a `note` whose `authority.decider` breaks core §5.1, a `target` with both `uri` and `key`, or an `outcome` the extension doesn't define. The core record schema, `terms_rev` and `terms.due` are not open: they hold on every core type (core §4) | Ignored as an unknown member | Held to its definition | Ignored, except Acts' single-line `terms.text` | Not asked | Ignored | Ignored |
| A byte order mark at the start of the text (RFC 8259 "MAY ignore") | Rejected | Ignored | Rejected | Rejected | Rejected in text, ignored in bytes | Rejected |

On the `ext` case neither reading acts on the record, so no state differs.

## State

- Two records of one register with the same id, different types and equal `ts`: `raised` and `withdrawn`, or `settled`
  and `reopened`. Core §6 breaks a tie by the greater id, which can't separate them, though it promises a result
  independent of arrival order. The result depends on arrival order in the reference, brunna and Muninn alike: `settled`
  and `reopened` give settled or open. Core §10 already tells a sender not to use one id for two records, so this takes a
  sender's breach, and settling it changes state.
- An Acts `settled` carrying `answer`: the reference, brunna and Muninn all show it in the settlement view, though core
  §6 limits the view to members the extension defines, and Acts defines none.

## Holding records

- Core §6's records a party "emitted" carry no validity condition, unlike those it has kept. Brunna still validates its
  own.
- Core §14 leaves out records older than N−1. Both brunna and Muninn still hold and read them, and open items depend on
  them; a party can't learn a counterpart's version before sending.
- The readings recorded in 0.6.2 are stated for 0.6. Whether a converting party applies them to 0.5 records (a non-date
  `terms.due` on a `note`) wasn't fully compared; the reference and Muninn do.

## Suite format

These affect how a case is read, not what a receiver does.

- `expect.claims` can list one id twice, when two origins use it.
- For an id with both an invalid and a valid record, `expect.ignored` omits it for core records and lists it for module
  records.
