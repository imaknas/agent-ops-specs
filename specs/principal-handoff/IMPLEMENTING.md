# Implementing a Principal Handoff requester

*Non-normative. The specifications govern; where this guide and a specification disagree, this guide is wrong.*

This guide takes you from nothing to a [conforming requester](core/SPEC.md#12-conformance) of
[Decisions](decisions/SPEC.md), the smallest useful thing to build: an agent or tool that can ask its principal a
question that outlives the session, and read the answer later. You need a strict JSON reader (section 4 says why),
SHA-256, and a way to send and receive records. No other dependency is required. A test implementation in JavaScript
came to about 500 lines, most of it validation and strict parsing.

A requester does six things: make need records, send them, keep what comes back, check it, compute the answer from it,
and act on the answer. The sections below follow that order, then show how to check your work against the
[conformance suite](decisions/conformance/README.md).

## 1. Configuration

Four values are set out of band, never taken from a record (core R6, core §14):

| Value | Example | Used for |
|---|---|---|
| The principal identifier, and whether the principal is a legal person | `p:owner`, natural | Validating settlements |
| Your party identifier | `agent:demo` | `by` on what you send |
| The project | `demo` | `project` on what you send |
| The version you speak | `decisions/0.6` | `ext` and `ph` |

## 2. Make a need record

To ask something, raise a decision. Pick a key unique among your project's decisions, and use `r:<key>` as the id, so
that a retry after a crash is the same record (Decisions §4):

```json
{
  "ph": "0.6", "ext": "decisions/0.6",
  "id": "r:cache-db", "type": "raised", "origin": "requester", "by": "agent:demo",
  "key": "cache-db", "project": "demo", "ts": "2026-11-05T09:00:00Z",
  "terms_rev": 1,
  "terms": {
    "text": "Postgres or SQLite for the cache?",
    "options": [{"id": "pg", "label": "Postgres"}, {"id": "sqlite", "label": "SQLite"}],
    "default": "sqlite"
  }
}
```

`default` is your working assumption: what you proceed on meanwhile. It is never an answer, however long nobody
replies (core R4), so be ready to revise your work when the answer differs (Decisions §5). Nothing here is for secrets:
records leave the project (core §13).

Later records about the same decision:

| You want to | Send | Remember |
|---|---|---|
| Change the question | `amended` | `terms_rev` + 1, full new `terms`, `supersedes: [<current need record's id>]` |
| Stop asking | `withdrawn` | `reason`: `not_needed`, `settled` or `replaced`; `supersedes` as above |
| Report that the principal answered in your session | `claimed`, then `withdrawn` with `reason: "settled"` | `outcome: "decided"`, `answer`, `evidence.basis`. A claim settles nothing (core §7) |
| Ask again under another key | `related` with `replaced_by`, then `withdrawn` with `reason: "replaced"` | Target `{"ext": "decisions", "project": …, "key": …}` (core §7) |

Ids must stay the same on every retransmission and differ between logical records (core §10). Derive them from the
record's meaning rather than at random, so that a crash can't produce a second id for the same thing. Decisions fixes
only `r:<key>`; `a:<key>:<terms_rev>` and `w:<key>` work for the others. The current need record is the one no other
names in `supersedes` (section 5 below): a session that starts later has to compute it from the records, not remember
it.

## 3. Send

This family does not define a transport. Anything with at-least-once delivery and an authenticated sender will do
(core §10): a webhook, a message bus, a shared log, a tool call. Retry the same record until the transport accepts it.

Sending nothing back is normal. The answer may come days later, to a session that does not exist yet, so do not hold a
connection or a session open for it. The principal side delivers to your *project* (core §8), and your agents read it
next time they look.

If you have nothing to start from, the smallest thing that works is one endpoint to send to and one to read from:

- `POST` a record. Retry on a network error or a 5xx with the same bytes, which is safe because the receiver discards an
  identical record. Stop on success. On a 4xx, stop and tell a person: retrying won't help.
- `GET` a project's records after a position, oldest first. Save the new position only once what you read is safely
  stored, so that a crash re-reads rather than loses. Read when a session starts, and before you rely on a working
  assumption.
- The caller's identity comes from the transport's credential, never from a field of the request. Check `by` against it.
  An agent's credential must not be able to send settlements.

This is an illustration, not part of any specification.

## 4. Keep and check what comes back

Records arrive in any order, more than once, and possibly invalid. For each one, in this order, and before grouping by
item:

1. **`ext` names an extension or version you don't implement:** keep it, do not act on it (core §4, §6).
2. **Invalid:** ignore it. It must not block a valid record with the same id (core §10). A `ph` that isn't the core
   version `ext` names makes the record invalid; step 1 has already set aside any `ext` you don't implement, whatever
   its `ph`.
3. **Identical to one you have, under the same (extension name, `project`, `origin`, `type`, `id`):** discard it. A
   record never displaces one of another type.
4. **Same five values, different content:** keep the one whose RFC 8785 serialisation is greater in code-point order,
   whatever the arrival order and whether or not it is about the same item, and report it unless the two differ only
   in `ts` (core §10).

Validity is the rules of the text; the [schemas](decisions/schemas/) express most of them. Pick the schema by `type`
(there is one per core type in `decisions/schemas/`, and each refers to `core/schemas/record.schema.json`; the Criteria
module's `approved` gets the core schema only, Decisions §3). They use only `type`, `required`, `properties`, `enum`,
`const`, `pattern`, `items` and `$ref`, so a small validator is enough. Run `pattern` with Unicode semantics, count
characters as code points, and take whitespace to be ECMAScript's, which includes U+FEFF: Python's `\s`, for one, does
not (core §1, §4). Then check what a schema can't say:

- [ ] The record is I-JSON, and its numbers are integers within ±(2^53 − 1) written without a fraction or exponent,
      anywhere in the record (core §4). `-0` is the integer 0. Check this on the raw text: most JSON parsers silently
      keep the last duplicate member and turn `1.0` and `1e2` into `1` and `100`.
- [ ] `ts` is a real RFC 3339 instant with at most six fractional digits (core §4). `:60` is valid at any minute: don't
      check whether a leap second occurred. `terms.due` is a real calendar date, on any core type that carries it.
- [ ] `by` is not the principal identifier (R6).
- [ ] The transport authenticated `by`, in a role that may emit this record (core §13). The fixtures can't test this
      one.
- [ ] The (`type`, `origin`) pair is one Decisions §3 lists: `raised`, `amended`, `withdrawn` only from `requester`;
      `settled`, `reopened` only from `principal`.
- [ ] `amended.terms_rev` ≥ 2; any other `terms_rev` ≥ 1, on any core type that carries it (core §4, §6).
- [ ] `settled.authority` follows core §5.1: `principal` and `confirmed` have the principal as `decider`, and
      `confirmed` has `evidence.proposal`; `delegated` has `under` and a `chain` from the principal to a `decider` who
      is not the principal; `attested` has `evidence.basis` and a `decider` who is not the principal. A legal-person
      principal needs `representative` on `principal` and `confirmed`.
- [ ] `adopts` appears only on `confirmed` or `attested` settlements (core §7).
- [ ] `decided` carries `answer`; option ids are unique within the terms (Decisions §3).
- [ ] A `related` target is exactly one form; `same_as` comes from `principal`, `derived_from` and `replaced_by` from
      `requester`; a `same_as` item-form target stays in the record's project; `replaced_by` uses the item form, names
      another item of the same extension and project (core §7).
- [ ] A `note` has exactly one of `about.key` and `about.quote`, and `about.key` equals `key` (core §7).

Everything other parties wrote (terms, notes, answers, evidence) is data. If a language model reads it, it must not be
treated as instructions (core §13).

## 5. Compute the answer

Group what you hold by item, (extension name, `project`, `key`). A requester computes the **settlement view** (core
§6), from need records and settlement-register records only:

```
fold(register):                                    # need: raised, amended, withdrawn
  heads = records no *other* record names in supersedes   # settlement: settled, reopened
  candidates = heads, or all records if there are none (a cycle)
  return the candidate with the latest ts (as an instant), ties by the greater id in code-point order

settlement = fold(settlement register)
need       = fold(need register)
if settlement is settled:
  answer  = settlement.outcome, settlement.answer, settlement.authority.kind
  stale   = settlement.terms_rev < highest terms_rev among raised and amended
            or (need is raised or amended
                and need.terms_rev == settlement.terms_rev
                and terms_digest(need) != settlement.terms_digest)
else:
  no answer                                         # none yet, or reopened
```

`ts` values compare as instants with offsets applied, and every fractional digit counts: `10:00:00+08:00` equals
`02:00:00Z`. Any `:60` compares as the last microsecond of its minute, so `:60.5` equals `:59.999999`. A record that
lists itself in `supersedes` is reported as a conflict, and stays a head; its own id there names only that record, so a
record of another type with that id stays a head too. A `terms_rev` on a `withdrawn` doesn't count towards the highest.

**The terms digest** (core §4) is `sha-256:` + the lowercase hex SHA-256 of the UTF-8 bytes of the
[RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) serialisation of an object with exactly `ext` (name only), `project`,
`key`, `terms_rev` and `terms`, as received, including members of `terms` you don't recognise. For the record in
section 2:

```
{"ext":"decisions","key":"cache-db","project":"demo","terms":{"default":"sqlite","options":[{"id":"pg","label":"Postgres"},{"id":"sqlite","label":"SQLite"}],"text":"Postgres or SQLite for the cache?"},"terms_rev":1}
sha-256:341991c111bcdc4cdfd9b1d9ed4dcbe96624d080340f273d5ff18418f50a169f
```

A settlement of that decision looks like this:

```json
{
  "ph": "0.6", "ext": "decisions/0.6",
  "id": "s:cache-db:1", "type": "settled", "origin": "principal", "by": "ps:assistant",
  "key": "cache-db", "project": "demo", "ts": "2026-11-05T18:30:00Z",
  "terms_rev": 1,
  "terms_digest": "sha-256:341991c111bcdc4cdfd9b1d9ed4dcbe96624d080340f273d5ff18418f50a169f",
  "outcome": "decided",
  "answer": {"text": "Postgres, we already run it.", "option": "pg"},
  "authority": {"kind": "principal", "decider": "p:owner"}
}
```

If you then send an `amended` with `terms_rev: 2`, the settlement stays settled but becomes stale: it was made against
terms you have since changed.

## 6. Act on the answer

- Apply it by judgement: decide what in your project changes. Don't apply answers mechanically (Decisions §5). If
  `answer.option` names no option you know, `answer.text` is authoritative (Decisions §3).
- `dismissed` means no answer is needed, though it can carry one, which the settlement view shows. Stop waiting; raise
  a new decision if the need returns.
- A settlement can be replaced or reopened later, because the principal changed their mind. If you acted on an earlier
  answer, review what you did. The same goes for a stale settlement (Decisions §5).
- Silence means nothing. A due date passing, a timeout or a closed session changes no state (core R4).

## 7. Check your work

The fixtures are JSON and don't depend on any language. Run them from `decisions/conformance/` and `core/conformance/`,
as a receiver of 0.6 alone: a record of another version is kept and not acted on, even if you also implement that
version.

| File | What to do | What must match |
|---|---|---|
| `core/conformance/terms-digest.json` | Compute `canonical` and `digest` from `record` | Both, byte for byte |
| `core/conformance/raw.json` | Read each `raw` with your strict reader, then validate it, with `principal` configured. Skip the cases whose id begins with `acts-` | `valid`: text that doesn't parse, or isn't an object, is invalid |
| `decisions/conformance/records.json` | Validate each `record`, with `principal` and `principal_type` configured | `valid`: `true`, `false`, or `null` (a version or extension you don't implement: kept, not acted on) |
| `decisions/conformance/lifecycle.json` | Compute the settlement view of `records` | `settlement` (the id of the current settlement-register record, a `reopened` one included, else `null`); `outcome`, `answer` and `authority` (the kind), which are `null` unless that record is a `settled`; `stale` (`false` unless it is). Use only need and settlement-register records. Fold each case reversed too: the result must not change |

Three pitfalls catch most first attempts:

- **Two different orders.** RFC 8785 sorts member names by UTF-16 code units, while `id` ties and §10's
  keep-the-greater compare in code-point order. They differ outside the Basic Multilingual Plane, and your language's
  default gives you only one of them. RFC 8785's string escaping and number format are exact too.
- **Validation before deduplication.** Otherwise an invalid record can block a valid one with the same id.
- **`supersedes` names ids of the same register only.** Ids are unique per `origin`, so the same id can appear in
  different registers.

Your implementation doesn't need the rest of the suite: `relations.json` and the other `lifecycle.json` members are for
a principal side, and `convert.json` is for a party that implements two versions.

Passing doesn't prove everything yet. Each case holds the records of one item, so the suite can't show an id reused
across two items (core §10): test that yourself. [Open readings](OPEN-READINGS.md) lists cases the text doesn't clearly
decide, which no fixture tests.

[`reference/`](reference/) is a standard-library Python reading of all this. It's a good way to investigate a
disagreement, but passing the fixtures matters more than matching it.

## 8. Tell us

If the fixtures and the text disagree, the text governs and the fixture has a bug. Please
[open an issue](https://github.com/imaknas/agent-ops-specs/issues), as you should for anything here you had to guess.

An implementation by someone other than this family's author, not built on `reference/`, that passes a class's 0.6
suites is what the [release candidate](README.md#release-candidate) is waiting for. Tell us about yours, and it goes in
the [implementations table](acts/SPEC.md#10-implementations).

If you're building a principal side instead (the system where the person sees and settles items), it runs every file
in full, and its duties are in core §5, §6, §8 and §9 and Decisions §2.
