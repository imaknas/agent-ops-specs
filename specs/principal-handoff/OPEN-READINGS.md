# Open readings

*Non-normative. A list of cases, not rules.*

While strengthening the conformance suites, we found cases the specifications' text doesn't clearly decide. No fixture
tests them, so an implementation can pass the suites whichever way it reads them, and we don't yet know that two
implementations agree. Each will be settled once implementations have reported how they read it: by a fixture and a
clearer sentence in 0.6.x if they all agree, in 0.7 if they don't (see the [release candidate](README.md#release-candidate)
policy).

If your implementation meets one of these, or you find another, please
[open an issue](https://github.com/imaknas/agent-ops-specs/issues).

"Reference" is [`reference/`](reference/). "Second reading" is a requester written in another language from the documents
alone, by the same author's tools, so it is no independent implementation. A dash means it was not compared.

## Validity

| Case | One reading | Other reading | Reference | Second reading |
|---|---|---|---|---|
| `decisions/0.5` with `ph: "0.6"` | Invalid: `ph` is not the core version `ext` names | Kept, not acted on: a version the receiver doesn't implement (core §4 states both, without an order) | Invalid | Kept |
| `ext` of `decisions/0.6.1`, or `decisions` | Invalid: not name and two-part version | Kept, not acted on | Invalid | Invalid |
| `note` with a non-date `terms.due`; more widely, a member on a type that doesn't list it | Validated | Ignored as an unknown member | Invalid | Valid |
| `option.label: 1` | Invalid: Decisions §3 assigns the terms schema | Valid: the text states no type, and core §4 calls a schema constraint the text doesn't state an error in the schema | Invalid | Invalid |
| `terms_rev: 0` on `withdrawn`, `reopened` or `related` | Invalid: `terms_rev` is at least 1 | Ignored: the member isn't defined on these types | Invalid | Invalid |
| `evidence.presented` off-pattern or not a string | Invalid: the form core §5.2 states | Valid: "opaque to receivers" | Invalid | Invalid |
| Malformed `terms_digest` | Invalid: the form core §4 defines | Valid and stale: it matches nothing | Invalid | Invalid |
| An id containing whitespace in `supersedes` or `adopts` | Invalid: not an id | Valid: a string that names nothing | Invalid | Invalid |
| `-0` | Valid: an integer without a fraction | Invalid: core §4 doesn't address it | Valid | Valid |
| `dismissed` carrying `answer` | Valid, and the settlement view shows it | Null or invalid: "no answer is needed" | Valid | Valid |
| `reopened` with `supersedes: []` | Valid: the member is present | Invalid: it must name what it reopens | Valid | Valid |
| `:60` at a minute other than 23:59 UTC, or on a day with no leap second | Valid: RFC 3339's grammar | Invalid: RFC 3339 §5.7 | Valid | Valid |
| A byte order mark at the start of the text (RFC 8259 "MAY ignore") | Rejected | Ignored | Rejected | Rejected |
| U+2028 in Acts `terms.text`, which is a single line | Allowed | Invalid | Allowed | — |

## State

| Case | One reading | Other reading |
|---|---|---|
| A `withdrawn` with `terms_rev: 9` over a settlement at 1 | Not stale: only "held `raised` and `amended`" count | Stale: core §6's "compared by `terms_rev`" |
| `:60.5` against `:59.999999` | Equal: a leap second compares as the last microsecond | Later: every fractional digit counts |
| A record listing itself in `supersedes`, when a record of another type has the same id | It names only itself | It also names the other record |
| A record of an older version in a `lifecycle.json` case | Not acted on | Acted on by a receiver that implements that version: the format doesn't say which versions the receiver implements |

## Suite format

These affect how a case is read, not what a receiver does.

- `expect.claims` can list one id twice, when two origins use it.
- For an id with both an invalid and a valid record, `expect.ignored` omits it for core records and lists it for module
  records.
