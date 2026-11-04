# Principal Handoff Core 0.6

| | |
|---|---|
| Status | Draft ([release candidate](../README.md#release-candidate)) |
| Version | 0.6 (2026-11-04) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) |
| Conformance vectors | [`conformance/`](conformance/) |
| Extensions | [Acts](../acts/SPEC.md) · [Decisions](../decisions/SPEC.md) |
| Bindings | [Acts Markdown](../acts-markdown/SPEC.md) |
| Modules | [Evidence](../evidence/SPEC.md) · [Criteria](../criteria/SPEC.md) |

## Abstract

AI agents working for someone keep reaching things only that someone may settle: work only they can do (pay, sign,
buy) and choices only they may make (which design, whether to spend). That someone is the agents' **principal**.
Principal Handoff specifies how such items leave the agents, reach the principal's own tool (the **principal side**),
and come back settled, when the items outlive every agent session.

The core defines one model for every kind of item. Each item has two **registers** with different owners: the
**need**, owned by the agent that raised it, and the **settlement**, owned by the principal side. Every change is an
append-only, attributable **record** that names who made it, under what **authority**, with what **evidence**.
Assertions by anyone else are **claims**, which change nothing until the owner of the register records something. The
**extensions** define the two kinds of item: [Acts](../acts/SPEC.md) (work only the principal can do, with a [Markdown
binding](../acts-markdown/SPEC.md) for a project's state document) and [Decisions](../decisions/SPEC.md) (answers and
choices only the principal may make). Optional **modules** add features that never change an item's state:
[Evidence](../evidence/SPEC.md) (independently verifiable proofs of facts) and [Criteria](../criteria/SPEC.md) (the
principal's approval of a decision's acceptance criteria, so that a verifier may settle it).

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [Model](#2-model)
3. [Ownership](#3-ownership)
4. [Records](#4-records)
5. [Authority and evidence](#5-authority-and-evidence)
6. [Current state](#6-current-state)
7. [Claims, relations and notes](#7-claims-relations-and-notes)
8. [Delivery and application](#8-delivery-and-application)
9. [When a person decides](#9-when-a-person-decides)
10. [Identifiers, deduplication and ordering](#10-identifiers-deduplication-and-ordering)
11. [Extensions and modules](#11-extensions-and-modules)
12. [Conformance](#12-conformance)
13. [Security and privacy considerations](#13-security-and-privacy-considerations)
14. [Versioning](#14-versioning)
15. [Scope and open issues](#15-scope-and-open-issues)
16. [Relation to other specifications](#16-relation-to-other-specifications)

## 1. Conventions and terminology

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT
RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC 2119]
[RFC 8174] when, and only when, they appear in all capitals, as shown here. Sections marked *non-normative*, examples
and notes are informative.

**Party identifier**
: A string that identifies one party (a person, an organisation, an agent, a system) within a deployment, no
whitespace, 1–256 characters. This family does not define how parties are authenticated (§13).

**Principal**
: The single party at the root of every delegation chain in a deployment, on whose behalf its agents and delegates
act. The principal is identified by the **principal identifier**, which is configured as in §3 (R6). The principal
MUST be a natural person, or a legal person or public body that a natural person is able to act for. A deployment
MUST NOT designate a software agent or system as the principal, whatever legal form wraps it.
*Note (informative): in practice the principal is the party that bears responsibility, under the law or rules that
apply, for what is decided in its name. This specification does not determine who that is; §15 says how a future
version may revisit the type constraint.*

**Principal side**
: The system through which the principal sees and settles items: a personal assistant, a to-do app, an issue
tracker. It is an instrument, not a party with authority of its own: when it settles without the principal it does so
as a delegate (§5). It is configured with exactly one principal identifier.

**Requester**
: The role of the agents acting for a project, including a registrar acting on their behalf (Acts Markdown). Any
party the deployment authenticates as holding a project's requester role may emit need records for that project's
items (§3). Which parties hold which roles is configured per deployment, like the principal identifier.

**Delegate**
: Any agent or system that decides on the principal's behalf without the principal deciding or confirming,
including the principal side itself and agents further up a delegation chain. A delegate is never the principal.

**Decider**
: The party a settlement record names as having made the settlement (§5).

**Mandate**
: An authorisation, given by the principal or further up a delegation chain, for a delegate to settle items without
the principal deciding each one; a standing instruction is a mandate. Mandates are defined by their own systems (§15)
or by a module (§11).

**Project**
: A unit of work the agents work on, identified by a project name unique within one deployment (1–128 characters, no
whitespace).

**Item**
: One thing only the principal may settle. An item has a **kind** (defined by an extension: `act` or `decide`), a
**key**, a project, terms, and two registers.

**Key**
: The opaque identifier of an item within its project and extension, matching `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`. An
item is identified by the triple (extension name, `project`, `key`). Extensions say who assigns keys and how.

**Terms**
: What the item asks: its text, and as the extension defines, a due date, options and a working assumption.

**Register**
: One of an item's two sequences of records: the **need** register and the **settlement** register (§2).

**Record**
: An append-only, attributable JSON message about one item (§4).

**Claim**
: A record asserting something about an item's settlement by a party that does not own the settlement register (§7).

**Relation**
: A record linking an item to another item, inside or outside this family (§7).

**Note**
: A record that carries information without changing any register (§7).

**Extension**, **module**
: An extension defines a kind of item (§11). A module adds optional members, record types and rules to one or more
extensions, and never changes an item's state (§11).

## 2. Model

```
                     need register (owner: requester)          settlement register (owner: principal side)
                     ─────────────────────────────────          ───────────────────────────────────────────
  requester ──────▶  raised · amended(terms_rev) · withdrawn    settled(outcome, authority, evidence) · reopened  ◀── principal side
                                    │                                               ▲
                                    └──── terms the settlement saw (terms_rev, terms_digest)
  anyone but the principal side ──▶ claim;   anyone ──▶ note        (change no register)
  principal side ──▶  relation (same_as)        requester ──▶ relation (derived_from, replaced_by)
```

Each item has two registers because the two questions they answer have different owners:

- The **need** register says whether the requester still asks, and what it asks. Only the requester changes it.
- The **settlement** register says whether, how, by whom and under what authority the item was settled. Only the
  principal side changes it.

An item's **current state** (§6) is computed from both registers. Neither register can overwrite the other: a late
answer does not undo a withdrawal, and a withdrawal does not settle anything.

## 3. Ownership

These rules replace any notion that an item is "resolved" by whoever last spoke.

- **R1 — The need belongs to the requester.** Only the requester emits `raised`, `amended` and `withdrawn` for its
  item.
- **R2 — The settlement belongs to the principal side.** Only the principal side emits `settled` and `reopened`. Every
  `settled` carries a decider and an authority kind (§5).
- **R3 — Everything else is a claim or a note.** A record by any other party that asserts a settlement is a claim
  (§7). It changes no register, and receivers MUST NOT treat it as a settlement.
- **R4 — Silence never settles.** No timeout, due date, default or working assumption produces a settlement. If the
  principal side cannot reach the principal, the item stays open and visible; the principal side MUST NOT settle it
  except as a delegate within a mandate (§5). A requester that stops mentioning an item (a handoff, summary or list
  that no longer includes it) is silent about it too: the principal side MUST NOT settle an item, or treat it as
  withdrawn, because a requester's listing left it out. Only a need record, or a record the principal side makes,
  changes anything.
- **R5 — Authority never grows down a chain.** A delegate MUST NOT settle an item that needs authority it does not
  hold. It raises its own item upstream, `derived_from` the first (§7), and settles the first only from that item's
  settlement. To raise it, the delegate acts as a requester of the upstream deployment, in a project it holds the
  requester role for there; it settles the first item `delegated`, with `under` a URI naming the upstream item's
  settlement.
- **R6 — The principal is configured, not asserted.** The principal identifier, and whether the principal is a
  natural or a legal person, are configured out of band by whoever operates the deployment, on the principal side and
  on every other role that validates records. No record, claim, relation or mandate establishes or changes them, and
  receivers MUST reject any that tries. The principal identifier MUST NOT equal the party identifier of any agent,
  delegate or principal side, and the principal never emits records itself: its decisions are recorded by the
  principal side, so a record whose `by` is the principal identifier is invalid.

## 4. Records

Every record is an I-JSON object (RFC 7493: no duplicate member names, no unpaired surrogates, numbers that are exact
IEEE 754 doubles) that validates against
[`schemas/record.schema.json`](schemas/record.schema.json) and against the schema its extension assigns to its
(`type`, `origin`) pair.

| Member | Type | Req. | Meaning |
|---|---|---|---|
| `ph` | string | yes | Core version; `"0.6"` for this document. |
| `ext` | string | yes | Extension name and version, e.g. `"acts/0.6"`, `"decisions/0.6"`. |
| `id` | string | yes | Record id, no whitespace, 1–256 characters (§10). |
| `type` | string | yes | One of the record types below, or a module record type the extension's table lists (§11). |
| `origin` | string | yes | The role that emitted it: `requester`, `principal` (the principal side), `agent` (any other agent), or a role the extension defines. |
| `by` | string | yes | Party identifier of the emitter. |
| `key` | string | yes | Key of the item. |
| `project` | string | yes | Project of the item. |
| `ts` | string | yes | RFC 3339 date-time at which the record was created, with at most six fractional digits; a value that is not a valid date-time makes the record invalid. Receivers compare `ts` values as instants, offsets applied, using every fractional digit given; a leap second (`:60`) compares as the last microsecond of its minute. Senders SHOULD use UTC (`Z`). |
| `supersedes` | array of strings | no | Ids of records in the same register that this one replaces (§6), or of the records a module says. |
| `terms` | object | on `raised`, `amended` | The item's terms; the members are defined by the extension and its modules. `text` is always present. |
| `terms_rev` | integer ≥ 1 | on `raised`, `amended`, `settled` | On need records, the terms version (1 on `raised`, increasing by one on each `amended`). On a settlement, the terms version it was made against. On a claim or note (optional), the terms version it refers to. |
| `terms_digest` | string | on `settled` | The terms digest (below) of the need record the settlement was made against, so that a settlement cannot be carried over to other terms at the same `terms_rev` (§6). |
| `outcome` | string | on `settled`, `claimed` | What the settlement says or the claim asserts; values defined by the extension. |
| `authority` | object | on `settled` | §5. |
| `evidence` | object | no | §5. |
| `relation` | object | on `related` | §7. |
| `reason` | string | on `withdrawn` | Why the requester withdrew; values defined by the extension. |
| `adopts` | array of strings | no | On `settled`: ids of claims this settlement accepts (§7). |
| `about` | object | on `note` | §7. |
| `note` | string | no | Free text from the emitter (§8). |
| `context` | string | no | Free-form tag for why the record was sent, e.g. `bulk-import`. |

Receivers MUST ignore members they do not recognise. Senders MAY add members; names beginning with `x_` are reserved
for private extensions. Every number in a record MUST be an integer between −(2^53 − 1) and 2^53 − 1, written
without a fraction or an exponent, so that every receiver serialises it alike (§10). `terms.due`, where an extension
defines it, MUST be a calendar date.

**Terms digest.** The terms digest of a need record (`raised` or `amended`) is `sha-256:` followed by the lowercase
hexadecimal SHA-256 of the UTF-8 bytes of the RFC 8785 serialisation of the JSON object whose members are exactly
`ext`, with its `/` and version removed (`decisions`, not `decisions/0.6`), and `project`, `key`, `terms_rev` and
`terms`, copied from that record as received, including members of `terms` the receiver does not recognise. Receivers
keep `terms` as received. Because records are I-JSON and numbers are bounded integers, every receiver computes the
same digest. The digest binds the item and its terms at one `terms_rev`, not the version of the extension: a version
whose conversion changes the meaning of a member of `terms` keeps the old digests, so that settlements made before it
read as stale (§14). [`conformance/terms-digest.json`](conformance/terms-digest.json) holds vectors.

Every rule that §4–§7 state about the content of a single record (the type table, the authority rules of §5, claims,
relations and notes in §7), and every rule an extension's records section lists, is a validity rule: a record that
breaks one is invalid (§10), whether or not a schema in the subset below can express it. Rules that need other
records (that a superseded id exists, that a mandate was in force) are never validity rules; they are duties of the
emitter, and receivers that can check them SHOULD report a breach.

Each `origin` stands for a role the deployment configures (§1): `requester` and an extension's requester-side
origins (Acts' `registrar`, which the deployment configures as a role of its own) for a party holding that role in
the record's project; `principal` for the principal side; `agent` for any other party the deployment authorises to
write about the record's project. Receivers check `origin` against the sender's configured role (§13), so no party
writes claims or notes about a project it holds no role in.

| `type` | Register | Allowed `origin` |
|---|---|---|
| `raised` | need | `requester` |
| `amended` | need | `requester` |
| `withdrawn` | need | `requester` |
| `settled` | settlement | `principal` |
| `reopened` | settlement | `principal` |
| `claimed` | (claim) | any origin except `principal` |
| `related` | (relation) | per relation kind (§7) |
| `note` | (note) | any origin the extension's table lists |

Extensions MAY restrict this table further, and MUST NOT widen it, except that an extension's table MAY also list
(`type`, `origin`) pairs that a module layered on it defines (§11); no other type is valid. The core record schema
therefore leaves `type` open, and the extension's table decides which types are valid. A receiver selects the schema
by `ext` and the (`type`, `origin`) pair as the extension's table lists, and MUST reject a record whose pair is not
listed. For a module pair the extension assigns no schema of its own: receivers apply the core record schema, and the
module's schema is one of its structural rules (§11). A record whose `ph` is not the core version its `ext` names is
invalid. A receiver that does not implement the extension or version named in `ext` MUST NOT act on the record; it
SHOULD consume it without error and MAY report it. The schemas use JSON Schema draft 2020-12 restricted to `type`,
`required`, `properties`, `enum`, `const`, `pattern` (an ECMAScript regular expression, in which `$` matches only at
the end of the string), `items` and `$ref` (a relative path), plus the annotations `$schema`, `$id` (the schema's path
from the family's root, against which `$ref` resolves), `title` and `description`, so that a small validator suffices.
Where this text and a schema or a conformance fixture disagree, the text governs.

## 5. Authority and evidence

### 5.1 Authority

Every `settled` record carries `authority`:

| Member | Req. | Meaning |
|---|---|---|
| `kind` | yes | `principal`, `confirmed`, `delegated` or `attested`. |
| `decider` | yes | Party identifier of whoever made the settlement. |
| `under` | for `delegated` | Reference to the mandate or standing instruction relied on, which the principal side MUST be able to produce. It is opaque to receivers, except that a module MAY define a prefix naming a mandate recorded in this family (§11); the principal side MUST NOT begin any other reference with such a prefix (a duty, not a validity rule). |
| `chain` | for `delegated` | Party identifiers from the principal to the decider, in order. |
| `representative` | no | For an organisation principal: the natural person who acted for it, as a party identifier the principal side can resolve (it need not reveal the person's name to projects). |

The four kinds:

- **`principal`**: the principal decided. `decider` MUST be the principal identifier.
- **`confirmed`**: the principal confirmed a proposal made by a delegate. `decider` MUST be the principal identifier.
  `evidence.proposal`, identifying what was confirmed, is REQUIRED.
- **`delegated`**: a delegate decided under a mandate, without the principal deciding or confirming. `decider` MUST
  NOT be the principal identifier, and `chain` MUST begin with the principal identifier and end with `decider`. A
  settlement whose mandate the principal side cannot produce MUST NOT be sent.
- **`attested`**: the principal side or a delegate settled from evidence that the item was done or decided (for
  example a payment record), without the principal confirming. `decider` MUST NOT be the principal identifier, and
  `evidence.basis` is REQUIRED.

When the principal is a legal person, a settlement of kind `principal` or `confirmed` MUST carry `representative`,
naming the natural person who acted for it; this is a validity rule, evaluated under the configured principal (R6).

### 5.2 Evidence

`evidence`, when present, is an object:

| Member | Meaning |
|---|---|
| `presented` | Digest (`sha-256:` + lowercase hex), opaque to receivers, of exactly what was shown to the person who decided or confirmed: the terms at `terms_rev` and any options or consequences the principal side displayed (§9). |
| `proposal` | For `confirmed`: id of the record, or digest of the content, that was confirmed. |
| `basis` | For `attested`, and on claims: what the evidence was, in words. |

Other members of `evidence` are defined by modules (the [Evidence](../evidence/SPEC.md) module defines proofs of
**what** is true); receivers that do not implement them ignore them (§4). The member `proof` is reserved for a proof
of **who** made a record, made with the principal's own credential on a surface no agent controls, which a deployment
profile is still to specify (§15). Until one does, senders MUST NOT emit it and receivers ignore it.

- **V1 — Validity and state never depend on checking evidence.** Whether a record is valid (§4, §5) and an item's
  state (§6) are computed from the records' own content; they never depend on anyone checking a proof, or anything
  else that `evidence` refers to. A receiver that checks nothing computes the same state from the same records.

## 6. Current state

The records a party **holds** about an item are the records about it that it emitted, or received in a version it
implemented when it received them, that are valid in that version, and that §10 does not displace. A party that
converts, or has retired N−1, holds the N forms of those received in N−1 instead (§14). Every rule of this family
about held records, in modules too, uses this definition.

Each register is folded separately, over all its records a receiver holds, regardless of arrival order:

- A **head** is a record in the register that no other held record of the same register names in `supersedes`.
- The **current** record is the head with the latest `ts` (compared as instants, §4). Equal `ts` are broken by the
  greater `id` in Unicode code-point order. If there is no head (`supersedes` links form a cycle), the same rule
  applies to all records of the register.
- There is a **conflict** in the register when there is more than one head, or a cycle (a record that lists itself
  in `supersedes` is a cycle). Receivers MUST use the current record and SHOULD report the conflict to a person.

A requester's `amended` and `withdrawn` MUST list the item's current need record in `supersedes`, and every
principal-side `settled` or `reopened` made while the settlement register holds records MUST list its current record.
The principal side MUST give each `settled` and `reopened` it makes a `ts` later than that of every
settlement-register record of the item it holds, so that "later" means what happened. Where more than one
implementation acts as the principal side (for example a personal assistant and a platform's built-in owner view),
each SHOULD deliver every settlement-register record it makes to the others (the transport accepting it, §10) before
it reports the record to the person as made, so that they do not fork the register. A receiver that nonetheless
holds several heads uses the
rule above and reports the conflict.

From the two current records, the item's state is:

| Settlement (current) | Need (current) | State |
|---|---|---|
| `settled` | any, or none | **settled**, with its `outcome`. It is **stale** if its `terms_rev` is lower than the highest `terms_rev` among the held `raised` and `amended`, or if the current need record is a `raised` or `amended` with the same `terms_rev` and a terms digest other than its `terms_digest` (a current `withdrawn` is compared by `terms_rev` only). |
| none, or `reopened` | `raised` or `amended` | **open** |
| none, or `reopened` | `withdrawn` | by the extension's policy (§11): **open** under the *keep* policy (the principal side keeps presenting it and asks the principal), **withdrawn** under the *stop* policy (it is no longer presented) |
| none, or `reopened` | none | **unknown**: no need record is held yet |

In every state the item also reports whether its current need is `withdrawn`, so that a principal side under the
keep policy knows to ask.

Receivers MUST reject an `amended` whose `terms_rev` is lower than 2 and a `settled` whose `terms_rev` is lower than
1. Because records may be missing or late, a receiver MUST accept a skipped `terms_rev`, and a settlement whose
`terms_rev` is higher than any need record it holds (it is not stale). The current terms are those of the current
need record.

A stale settlement stays settled. The principal side SHOULD present it to the principal again, and the requester
SHOULD treat it as made against outdated terms.

The **settlement view** of an item is the part of this state a requester needs (§12): the current settlement-register
record, and, if it is a `settled`, its outcome, authority kind, the members the extension defines on it (Decisions:
`answer`) and whether it is stale, exactly as the table above says. It leaves out the state open, withdrawn or
unknown, whether the need is withdrawn, the claims held, and reporting conflicts.

## 7. Claims, relations and notes

**Claims.** A `claimed` record asserts an `outcome` that the claimant has no authority to record: an agent that heard
the principal say "I paid it", or a registrar that saw a declared line disappear. It SHOULD carry `evidence.basis`. A
claim changes no register. The principal side MAY accept it by recording a settlement that lists the claim's id in
`adopts`, with kind `confirmed` if the principal confirmed it, or `attested` if evidence independent of the claimant
shows the outcome (the claimant's own word, `evidence.basis` included, is never enough for `attested`); `adopts` MUST
NOT appear on a settlement of any other kind, nor on any other record of the types this section and §6 define
(modules say the rest, §11). Evidence the principal side does not check,
including members of modules it does not implement, counts as the claimant's word. An id in `adopts` adopts every held
claim about the item with that id. A claim never removes an item from the principal's view. A claim MAY carry
`terms_rev`, the terms version it refers to.

**Relations.** A `related` record carries `relation`:

| Member | Meaning |
|---|---|
| `kind` | `same_as`, `derived_from` or `replaced_by`. |
| `target` | The other item: `{"ext", "project", "key"}` (all three) for an item of this family in the same deployment, or `{"uri"}` for anything else (an A2A task, a bus message, an issue). `ext` is the extension's name only, matching `^[a-z][a-z0-9-]*$` (`decisions`, not `decisions/0.6`), so that a target names the same item in every version; `project` and `key` take the patterns of the record's `project` and `key`. The members present decide the form: a `target` with `uri` and any of `ext`, `project` and `key`, or with neither `uri` nor all three, makes the record invalid. An item outside this family, or in another deployment (an upstream item, §3 R5), MUST be named by `uri` (a duty of the emitter, not a validity rule: receivers cannot check it). |
| `active` | `true`, or `false` to retract the relation. For each relation of an item, identified by (`kind`, `target.ext`, `target.project`, `target.key`) or by (`kind`, `target.uri`), the relation record with the latest `ts` (equal `ts`: greater `id`) decides whether the relation is active. The two forms never identify the same relation, and `uri` values are compared as exact strings, without normalisation. |

- `same_as` is emitted by the principal side (`origin: "principal"`) when it treats two items as one, for example the
  same request raised by two projects, or a request repeating one already settled. Relations never change any item's
  state (§6): when the principal side settles a group of related items, it MUST emit a `settled` for each item, on
  that item's own authority, so that every requester computes the same state. One requester withdrawing leaves the
  other items open. A relation the principal side sends to a project names an item of another project only by a `uri`
  that the principal side alone can resolve, never by that project's `ext`, `project` and `key` (§13). A requester
  that disagrees sends a `note` about its item saying why the two differ; the principal side SHOULD then retract the
  relation.
- `derived_from` is emitted by the requester when its item arises from another item, inside or outside this family
  (§3 R5; a question asked while answering an inquiry from the principal; a task that an answer created).
- `replaced_by` is emitted by the requester when it replaces its item with another of its own items: the same need,
  raised again under another key. Its target MUST be an item of the same extension (its `target.ext` is the name in
  the record's `ext`) and `project` as the record, and not the item itself: an item of another kind would fall under
  another withdrawal policy (§11). A requester that replaces an item sends `replaced_by` and then withdraws the item
  with the extension's replacement reason. An item with more than one active `replaced_by` has no replacement; the
  principal side SHOULD report it. How the principal side presents a replaced item is the extension's policy (§11). A
  requester's re-sent list that simply omits the old item replaces nothing (R4), and no relation moves a settlement,
  or anything a module binds to an item, from one item to another.

**Notes.** A `note` record carries information that changes no register: progress, a fact the principal mentioned, a
premise that changed. It carries `about`, either `{"key": …}` for a keyed item or `{"quote": …}` with text in the
recipient's own words for something that was never keyed (exactly one of the two); such a note carries, as its `key`,
one the sender chooses that names no item. A note whose `about` has `key` MUST carry the same `key` (a validity rule).
A note never settles anything. In particular, a note from the principal side saying a premise changed (a moved date)
is not an amendment: the requester decides whether to amend its terms. A note MAY carry `terms_rev`, the terms version
it refers to.

## 8. Delivery and application

- The principal side MUST deliver every settlement-register record and relation it emits, every note it addresses to
  a project, and every record a module tells it to deliver, to that project, where its agents will read it next (an
  inbox, notes, a decision log), not only to a session that may no longer exist. Of the records it emits and does not
  retract (§10), only notes may be kept unsent, where a module says so ([Evidence](../evidence/SPEC.md)).
- **Mechanical versus judgement.** Only an extension's binding applies records mechanically, and only to keyed items
  (for example, striking a line in a state document). Everything else, including every note and every `quote`, is
  applied by judgement: the recipient decides what changes. Implementations MUST NOT apply a `quote` reference
  mechanically.
- A `note` on any record is for the other party: on need records and claims, for the principal side, which SHOULD show
  it with the item; on records from the principal side, for the project.
- What the principal side sends a project carries only what that project may know (§13).

## 9. When a person decides

These rules apply to every settlement of kind `principal` or `confirmed`, that is, whenever a natural person decides
or confirms, whether the principal or an organisation's representative, and to whatever else a module says a person
decides.

- The principal side MUST present the terms at the `terms_rev` it records, and SHOULD record `evidence.presented`. If
  the terms change before the person decides, the principal side MUST present them again.
- The principal side SHOULD show the requester's working assumption as such, and SHOULD NOT pre-select it.
- The principal side SHOULD show, or flag, members of the terms it does not recognise: a requester must not rely on
  terms the person was never shown.
- The principal side SHOULD batch and rate-limit items per project and SHOULD NOT present an item it can settle under
  an existing mandate. A person's attention is the scarce resource this family protects.
- *Note (informative):* a person who confirms everything they are shown is deciding only in name. Recording
  `presented`, the authority kind and the decider makes that visible, and is a precondition for the human oversight
  that rules such as the EU AI Act Article 14 require of high-risk systems.

## 10. Identifiers, deduplication and ordering

- A record id MUST be unique per logical record within its (`ext` name, `project`, `origin`), whatever its type, and
  MUST be the same on every retransmission. Extensions say how ids are derived when a sender must re-create them after
  a crash. A sender MUST NOT reuse an id for a different record. Ids are scoped by `origin` so that no party can
  displace another role's record by reusing its id; every reference to an id (`supersedes`, `adopts`, and those a
  module defines) names a record of the origin that reference implies (the register's owner, a claimant, the
  principal side), or of the origin it states.
- Receivers MUST discard a record identical to one they have already processed with the same (`ext` name, `project`,
  `origin`, `id`). A record that fails validation, or names a version the receiver does not implement (§4), is not
  processed: it is ignored, and does not block a valid record with the same id. A receiver that sees an id reused
  with different valid content, about the same item or not, keeps the one whose RFC 8785 serialisation is greater in
  code-point order, whatever the arrival order, and SHOULD report it unless the two differ only in `ts` (a record
  re-created after a crash). A need record replaced this way changes the terms at its `terms_rev`; settlements made
  on the other content become stale through their `terms_digest` (§6). A record never displaces a record of another
  type, and every reference to an id names records of the types it implies (`supersedes`: the same register;
  `adopts`: claims).
- Senders MUST retry until the transport accepts the record (at-least-once delivery). Ordering is not guaranteed;
  §6 makes the current state independent of arrival order.
- A record that was never sent MAY be retracted by its sender without trace (for example, a settlement held for an
  undo window). Once sent, a record is changed only by a later record that supersedes it.
- This family does not define a transport. Any transport with at-least-once delivery and authenticated senders will
  do: an HTTPS webhook, a message bus, a shared append-only log, an MCP tool call, an A2A message.

## 11. Extensions and modules

An extension document MUST define:

1. its name and version (the `ext` value) and the item kind it covers;
2. the members of `terms`, and how keys are assigned;
3. its `outcome` values for settlements and claims, and its `reason` values for withdrawals;
4. its table of (`type`, `origin`) pairs with schemas, restricting §4;
5. its policy for an item whose need is withdrawn and whose settlement is open (§6);
6. its policy for an item withdrawn as replaced by another (§7);
7. any binding that applies records mechanically, and what it applies;
8. its conformance classes and suite.

An extension's binding MAY be a document of its own. Such a document has no `ext` value; it MUST name the
extension it binds, define what it applies mechanically and to what, and define its conformance classes and suite.

A **module** adds optional members, record types and rules to the extensions it names. It has no `ext` value: it is
versioned with what it layers on, so a record's `ph` and `ext` also fix the version of every module whose content it
carries. A module record type changes no register; it is valid only in an extension whose table lists its (`type`,
`origin`) pair (§4).

- **A module never changes validity or state.** Whether a record is valid under the core and its extension, and every
  item's state (§6), are the same for a receiver that implements a module as for one that does not. For a module
  record, validity is the rules of §4 that hold for every record (I-JSON, integer bounds, `ph` agreeing with `ext`,
  `ts`, the core record schema, the pair the extension lists), R6 and the sender's role (§13); the rules of §5 and §7
  are for the core types. A module record that fails one of these is invalid; the module's own schema and rules are
  for receivers that implement it. A module states two kinds of rules: **structural rules** on its **module content**
  (the members it defines, its record types, and what it reads into core members, as the module says), and **duties**
  of the party that emits. A receiver that implements the module and finds a record that breaks a structural rule
  ignores that record's module content and SHOULD report it; one that finds a duty broken SHOULD report it. A module
  built on another applies its rules to what the other leaves after its own. A receiver that does not implement a
  module consumes that module's records without acting on them, and ignores its members.
- **Reserved prefixes.** A module MAY define a prefix of `authority.under` that names a mandate recorded in this
  family. The prefixes so defined are reserved: `approval:` ([Criteria](../criteria/SPEC.md)). To a receiver that does
  not implement the module, such an `under` is opaque, like any other.
- **Modules are configured.** Which modules each party implements is configured per deployment, like roles. A party
  MUST NOT rely on a module its counterpart is not configured for. Where the principal side does not implement a
  module, items are presented to the principal as any other (R4): nothing waits on a module that is absent.

A module document MUST define: the documents it layers on and those it requires; the members and record types it
adds, and the (`type`, `origin`) pairs extensions list for it; its structural rules and what they make it ignore; the
duties it places on each party; any `under` prefix it reserves; its conversion between versions (§14); and its
conformance classes and suite.

## 12. Conformance

- A **conforming requester** emits only the need records, claims, relations and notes R1–R3 and §7 allow, with ids
  as §10 says, increments `terms_rev` on each amendment, validates the records it receives (§4, §5), deduplicates
  (§10), computes for each of its items the settlement view (§6), and applies delivered records as in §8.
- A **conforming principal side** emits settlements only as in §3 and §5, validates and deduplicates, computes state
  as in §6, follows §6's duties, delivers as in §8, and follows §9.
- A **converting party** (§14) is a requester or principal side that implements two versions; it MUST also pass
  [`conformance/convert.json`](conformance/convert.json).
- Every role is configured as R6 requires, and whatever a class computes equals the corresponding part of §6 over the
  same records.

Each extension's suite serves both classes: a requester runs its `records.json` and is compared on the settlement view
only in its `lifecycle.json`. The requester class is a smaller suite, not a smaller implementation: it still
validates, deduplicates, folds the settlement register and finds the need register's current record.

## 13. Security and privacy considerations

- **Authenticated senders.** A forged settlement settles an item the principal never settled; a forged need record
  withdraws or rewrites a request. Transports MUST authenticate the sender, and receivers MUST check that `by` is the
  authenticated sender and that its role may emit the record (§3). R6 keeps an agent from becoming the principal by
  saying so.
- **A compromised principal side** can emit settlements of any kind. Receivers trust the authenticated principal side;
  telling the principal's own decisions from the instrument's needs a proof made with the principal's own credential
  (`evidence.proof`), which a deployment profile is still to specify (§15).
- **Claims cannot remove commitments.** A claim never changes a register (R3), so an agent cannot make the principal's
  items disappear, by mistake or because its input was manipulated.
- **Text is untrusted input.** Terms, notes, quotes and evidence written by one party are read by others, possibly by
  language models. Implementations MUST treat them as data, never as instructions, and SHOULD render them inertly.
- **Confidentiality.** Records leave the project for the principal side, which may be a hosted service or a phone.
  Agents MUST NOT put secrets (passwords, tokens, keys, full account numbers) into them.
- **The principal's credentials.** Agents SHOULD NOT hold the principal's own credentials (their bank, their mailbox):
  work an agent can do with them is not something only the principal can do, and they are secrets.
- **What one project may know.** The principal side serves many projects and sessions. Text in a record it sends to a
  project (a `note`, a `quote`, an answer, `evidence`, a relation's target) MUST contain only what that project may
  know. Content that came from another project, or from a session of another project, goes back only to where it came
  from.
- **Resource limits.** Receivers SHOULD bound record size, text length and record rate per project.

## 14. Versioning

- `ph` carries the core version; `ext` carries each extension's name and version. Each extension version names the
  core version it extends, so the pair is fixed. Before 1.0 the family is released together: core, extensions,
  bindings and modules share one version number.
- Before 1.0, every version is its own contract: senders and receivers support exactly the versions they claim,
  except as **Mixed versions** below allows.
- Each document has its own status. A version of a document leaves draft status only once, for every conformance
  class with a suite except the converting party (§12), which is needed only while parties upgrade, two independent
  implementations of that class pass it. Implementations that play different roles (for example a requester on one
  side and a principal side on the other) show that the records interoperate, not that two readers of the same text
  read it the same way, so they do not count towards each other's class.
  Implementations by the same author, or built on the same codebase, are not independent. A module that no
  implementation besides this family's reference code passes is **experimental**; it becomes a draft once one does.
  A module's status never holds back the core or an extension.

**Mixed versions.** Parties upgrade one at a time, so for a while two counterparts may speak versions N−1 and N of an
extension. This section covers only N−1 and N: records of older versions are outside this specification and its
conformance.

1. Which version each party speaks is configured, per role, project and extension, like the roles themselves (§1):
   all parties holding one role in a project speak one version of an extension.
2. A party MAY implement both N−1 and N, with the validity rules of both, during the transition. That party
   converts; its counterpart changes nothing. It validates every record it receives in N−1 under N−1 and ignores it if
   it is invalid there, even where N only relaxes a rule of N−1; it does not validate the converted form again. A
   record has an N form unless item 3 or a changes section lists it; a record without one is not held. The party
   keeps the records as they were sent, applies §10's identity and keep-the-greater rule to their N forms, and holds
   those (§6); since conversion depends on the record alone, the result does not depend on arrival order. It thus
   computes what an N receiver computes over the converted records, not necessarily what a receiver of N−1 alone
   computes: receivers compute the same results from the same records when they speak the same version. The
   converted form is never passed on as the counterpart's record. It converts every record it sends to an N−1
   counterpart to N−1. Two parties that both speak N use N.
3. From 0.5 to 0.6 on, conversion between consecutive versions MUST be a function of the record alone, never of
   other records held. It keeps `id` (§10) and removes `evidence.proof`. Each extension, and each module with records
   of its own, states the rest of its conversion in both directions in its "changes" section, with the records valid
   in N−1 that have no N form. A version whose conversion changes the meaning of a member of `terms` without changing
   its bytes MUST say so, and its conversion then keeps a settlement's `terms_digest` as it is, so that the settlement
   reads as stale (§4). [`conformance/convert.json`](conformance/convert.json) holds the vectors for 0.5 and 0.6.

   *0.5 to 0.6:* the core changes `ph`, and a relation's `target.ext` becomes its part before the first `/` (0.6 to
   0.5: `/0.5` is appended); a `uri` target is unchanged. A 0.5 `related` whose `target.ext`, up to the first `/`,
   does not match `^[a-z][a-z0-9-]*$`, or whose `target.project` does not match the project pattern, has no 0.6 form.
   A 0.5 item-form target could name an item in another deployment (§3 R5), which now reads as one of the receiver's
   own; a converting party SHOULD report an item-form `derived_from` whose target it cannot place. Every 0.6 record
   has a 0.5 form.
4. A party that implements both versions MUST NOT make, about an item whose counterpart speaks N−1, a record that has
   no valid N−1 form.
5. A party stops speaking N−1 to a role in a project, for an extension, only once no party holding that role there is
   configured for N−1, whether it converted until then or spoke N−1 alone. It then replaces each record it holds as
   received in N−1 with that record's N form, and discards those that have none. Once a party is configured to speak
   N in a role, project and extension, it sends every record there in N, including retransmissions of records first
   sent in N−1.

**Change log.** 0.6 (2026-11-04): a stabilizing release. A relation's `target.ext` names the extension without its
version, and `target.project` follows the project pattern (§7), so 0.5 targets that differed only in the extension
version, or only in members of `target` that 0.6 does not define, now identify one relation. The records a party
holds are defined (§6). Mixed versions covers only N−1 and N; conversion is a function of the record alone; a
converting party deduplicates and holds the converted forms; retiring N−1 and sending in N are defined. The
converting party no longer holds back leaving draft; the promise about minor changes after 1.0 is withdrawn (§15).
Where this text and a schema disagree, the text governs (§4).

0.5 (2026-11-01): a restructuring release. Verifiable entries and verification results (0.4 §5.2,
V2–V5) move to the [Evidence](../evidence/SPEC.md) module; approvals (0.4 §5.3 and the approval fold of §6) move to
the [Criteria](../criteria/SPEC.md) module, layered on Decisions; modules never change validity or state (§11); the
terms digest is defined in §4 and computed over the extension name without its version; the principal side's `ts`
duty, in 0.4 a rule of approvals, binds every principal side, and implementations that share the principal side
deliver their settlement-register records to each other (§6, new); the requester class computes only
the settlement view (§6, §12); mixed versions (§14). Rules of 0.4 that 0.5 relaxes, so that records invalid in 0.4
may be valid in 0.5:

- malformed `evidence.verifiable` or `evidence.verified`, and verifiable entries without `terms_rev`, no longer make a
  record invalid (a receiver implementing Evidence ignores them);
- malformed `terms.criteria` no longer makes a need record invalid (Criteria ignores the criteria);
- the shape of a settlement under an approval, and of an `approved` record beyond the core checks, is no longer a
  validity rule (Criteria ignores it and reports it); an `under` beginning with `approval:` in Acts is no longer
  invalid (the prefix is reserved, the value opaque);
- a deployment can no longer make a settlement without a verifying `evidence.proof` invalid by configuring the
  principal's keys, and the *verifiable* principal side is gone (§15);
- the approval in force is no longer computed by every role;
- the terms digest no longer covers the extension version;
- records of different types with the same id (a module record and a core record, but also, say, a `raised` and an
  `amended`) no longer displace each other (§10);
- `evidence.proof` is only reserved: 0.4's SHOULD on settlements of kind `principal` or `confirmed`, its SHOULD on
  evidence of a representative's power, and its definition over the record's JCS form wait for the deployment profile
  (§15).

0.4 (2026-11-01): verifiable entries and verification results with rules V1–V5; approvals, a new `approved` record
bound to an item's terms by the terms digest; the `replaced_by` relation; `terms_rev` on claims and notes; R4 covers
a requester's listing that omits an item; §13 covers text sent to a project; leaving draft needs two independent
implementations per conformance class (§14). 0.3 (2026-10-27): the event model of 0.2 is replaced by two registers
with owners, claims, relations and notes; resolutions carry an authority kind, a decider and evidence; the principal
is defined structurally and configured (R6); Tasks and Questions become the Acts and Decisions extensions. A mapping
from every 0.2 event to 0.3 records is in each extension. 0.2 (2026-10-27): split from Human Task Handoff 0.1.

## 15. Scope and open issues

Out of scope, deliberately:

- **Mandate formats and lifecycle.** Issuing, scoping, revoking and verifying mandates belong to their own systems
  (§16); this family records the reference (`under`) and the chain. A module may define a narrow mandate recorded in
  this family ([Criteria](../criteria/SPEC.md)'s approvals); standing instructions that span items ("pay any invoice
  under 50 euros") remain out of scope.
- **Group decision procedures.** An organisation or body may be the principal if it presents one principal side; how
  its members decide (quorum, separation of duties) is internal to that side. Settlements name the representative who
  acted (§5).
- **Inquiries from the principal to a project** ("how far has this got?"). These are requests the project answers, so
  this family's rules about who may settle do not apply to them. They travel on the deployment's transport (for
  example as an A2A task or a message); an item a project raises while answering one carries `derived_from` with the
  inquiry's `uri`.
- **Transport and authentication.**
- **Software agents as principals.** The type constraint in §1 reflects that no legal regime gives software agents
  the standing and oversight a principal implies. A future version MAY revisit it if such a regime exists, together
  with whatever oversight it brings; the rest of this model does not depend on the principal being a person.

Open issues, to be specified later:

- **Resync and completeness.** A receiver cannot yet ask for every record about an item, nor tell that it holds them
  all; §6 makes the state independent of order, not of loss.
- **A signed-principal deployment profile.** A proof format for `evidence.proof`, how receivers are configured with
  the principal's verification keys, whether a record whose proof does not verify is then invalid, and a *verifiable*
  principal side that signs every decision a person makes (0.4 §5.2 and §12 had a first version).
- **Minor versions.** How 1.x versions add record types, outcome values and members so that older receivers can
  handle them is to be designed for 1.0.

## 16. Relation to other specifications

*Non-normative. The detailed comparison is in [RELATED-WORK.md](../RELATED-WORK.md).*

Existing protocols that involve a person place the request inside a live unit of work (a call, a task an agent
server runs, a run on a thread), and the system that created the unit decides when it is complete. Principal Handoff
covers items that outlive every agent run and that only the principal side settles. It is meant to be carried by
those protocols and to reference their mandates, not to replace them.

- **ACP** connects a client to a coding agent's sessions; a principal's assistant borrowing a project's session uses
  ACP for the session. **MCP** connects agents to tools and data; a principal side can be exposed as an MCP server.
  **A2A** carries delegation between agents, including inquiries from the principal's assistant to a project (§15).
- **AP2, OAuth (RFC 8693 token exchange, RAR) and UCAN** define mandates and delegation. `under` references their
  mandates; `chain` records the actors in the way RFC 8693's nested `act` claims do, except that here the whole chain
  matters for accountability, not only the current actor. AP2's Trusted Surface is the model for `evidence.proof`
  (§15).
- **W3C PROV** supplies the vocabulary this model follows: attribution (`by`, `decider`), acting on behalf of
  (`chain`, `under`), revision (`supersedes`) and derivation (`derived_from`).
- **CHAP** specifies a coordinator-hosted workspace in which several people and agents assign, review and override
  work. Principal Handoff has no coordinator, a single principal per deployment, and owner-based registers.
- **AG-UI** and agent SDK interrupts pause one run for a person's answer; AG-UI's "omission is not abandonment" is the
  same principle as R4.
- **iCalendar VTODO, JSCalendar and JMAP Tasks** model tasks assigned to people; a principal side MAY store items as
  them.
- **EU AI Act Article 14** requires that high-risk systems can be effectively overseen by natural persons; §9's
  records are what such oversight needs to be checkable.
- **AGENTS.md** tells agents how to work in a repository; a project using this family SHOULD say so there.

## References

- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- [RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.
- [RFC 3339] Klyne, G. and C. Newman, "Date and Time on the Internet: Timestamps", RFC 3339, July 2002.
- [RFC 7493] Bray, T., Ed., "The I-JSON Message Format", RFC 7493, March 2015.
- [RFC 8259] Bray, T., Ed., "The JavaScript Object Notation (JSON) Data Interchange Format", RFC 8259, December 2017.
- [RFC 8693] Jones, M., et al., "OAuth 2.0 Token Exchange", RFC 8693, January 2020.
- [RFC 8785] Rundgren, A., Jordan, B., and S. Erdtman, "JSON Canonicalization Scheme (JCS)", RFC 8785, June 2020.
- JSON Schema: A Media Type for Describing JSON Documents, draft 2020-12.
- W3C PROV-O: The PROV Ontology, <https://www.w3.org/TR/prov-o/>.
- Agent Payments Protocol (AP2), <https://ap2-protocol.org>.
- Agent Client Protocol, <https://agentclientprotocol.com>; Model Context Protocol, <https://modelcontextprotocol.io>;
  Agent2Agent (A2A) Protocol, <https://a2a-protocol.org>; AG-UI, <https://docs.ag-ui.com>.
- Collaborative Human-Agent Protocol (CHAP), <https://github.com/BrightbeamAI/chap>.
- Regulation (EU) 2024/1689 (AI Act), Article 14.
- AGENTS.md, <https://agents.md>.
