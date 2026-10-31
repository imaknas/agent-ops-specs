# Principal Handoff Core 0.4

| | |
|---|---|
| Status | Draft |
| Version | 0.4 (2026-11-01) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) |
| Conformance vectors | [`conformance/`](conformance/) |
| Extensions | [Acts](../acts/SPEC.md) · [Decisions](../decisions/SPEC.md) |

## Abstract

AI agents working for someone keep reaching things only that someone may settle: work only they can do (pay, sign,
buy) and choices only they may make (which design, whether to spend). That someone is the agents' **principal**.
Principal Handoff specifies how such items leave the agents, reach the principal's own tool (the **principal side**),
and come back settled, when the items outlive every agent session.

The core defines one model for every kind of item. Each item has two **registers** with different owners: the
**need**, owned by the agent that raised it, and the **settlement**, owned by the principal side. Every change is an
append-only, attributable **record** that names who made it, under what **authority**, with what **evidence**.
Assertions by anyone else are **claims**, which change nothing until the owner of the register records something.
Records can carry independently **verifiable** proofs of facts, and the principal can **approve** an item's terms so
that a verifier may settle it without the principal reviewing the work. The **extensions** define the two kinds of
item: [Acts](../acts/SPEC.md) (work only the principal can do, with a Markdown binding for a project's state document)
and [Decisions](../decisions/SPEC.md) (answers and choices only the principal may make).

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
11. [Extensions](#11-extensions)
12. [Conformance](#12-conformance)
13. [Security and privacy considerations](#13-security-and-privacy-considerations)
14. [Versioning](#14-versioning)
15. [Scope](#15-scope)
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
: The role of the agents acting for a project, including a registrar acting on their behalf (Acts). Any party the
deployment authenticates as holding a project's requester role may emit need records for that project's items (§3).
Which parties hold which roles is configured per deployment, like the principal identifier.

**Delegate**
: Any agent or system that decides on the principal's behalf without the principal deciding or confirming,
including the principal side itself and agents further up a delegation chain. A delegate is never the principal.

**Decider**
: The party a settlement record names as having made the settlement (§5).

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

**Verifiable entry**
: A proof of a fact that a third party can check without trusting whoever reported it, carried in a record's
`evidence` (§5.2).

**Trust policy**
: The principal side's own list, per proof format, of the signers, notaries and issuers whose proofs it accepts, and
of the freshness bounds it applies (§5.2).

**Verifier**
: A component of the principal side that checks verifiable entries against its trust policy. A verifier that settles
an item does so as a delegate (§5.3).

**Mandate**
: An authorisation, given by the principal or further up a delegation chain, for a delegate to settle items without
the principal deciding each one; a standing instruction is a mandate. Mandates are defined by their own systems (§15),
except approvals (§5.3).

**Trust root**
: A signer, notary or issuer whose proofs a trust policy accepts for a format, named as that format names it (§5.2).

**Approval**
: The principal's approval of an item's terms exactly as they stand at one `terms_rev`, recorded by the principal side
in an `approved` record (§5.3). It is the only mandate this family defines.

## 2. Model

```
                     need register (owner: requester)          settlement register (owner: principal side)
                     ─────────────────────────────────          ───────────────────────────────────────────
  requester ──────▶  raised · amended(terms_rev) · withdrawn    settled(outcome, authority, evidence) · reopened  ◀── principal side
                                    │                                               ▲
                                    └──── terms the settlement saw (terms_rev) ─────┘
  anyone but the principal side ──▶ claim;   anyone ──▶ note   (change no register; may carry verifiable proofs)
  principal side ──▶  approval (terms_rev, terms digest) · relation (same_as)   (change no register)
       requester ──▶  relation (derived_from, replaced_by)
```

Each item has two registers because the two questions they answer have different owners:

- The **need** register says whether the requester still asks, and what it asks. Only the requester changes it.
- The **settlement** register says whether, how, by whom and under what authority the item was settled. Only the
  principal side changes it.

An item's **current state** (§6) is computed from both registers. Neither register can overwrite the other: a late
answer does not undo a withdrawal, and a withdrawal does not settle anything. Approvals (§5.3) are kept beside the
registers: they authorise a settlement but are not one.

## 3. Ownership

These rules replace any notion that an item is "resolved" by whoever last spoke.

- **R1 — The need belongs to the requester.** Only the requester emits `raised`, `amended` and `withdrawn` for its
  item.
- **R2 — The settlement belongs to the principal side.** Only the principal side emits `settled` and `reopened`. Every
  `settled` carries a decider and an authority kind (§5). Only the principal side emits `approved` (§5.3).
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
- **R6 — The principal is configured, not asserted.** The principal identifier, whether the principal is a natural or
  a legal person, and optionally the keys that verify the principal's own `evidence.proof` (§5.2), are configured out
  of band by whoever operates the deployment, on the principal side and
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
| `ph` | string | yes | Core version; `"0.4"` for this document. |
| `ext` | string | yes | Extension name and version, e.g. `"acts/0.4"`, `"decisions/0.4"`. |
| `id` | string | yes | Record id, no whitespace, 1–256 characters (§10). |
| `type` | string | yes | One of the record types below. |
| `origin` | string | yes | The role that emitted it: `requester`, `principal` (the principal side), `agent` (any other agent), or a role the extension defines. |
| `by` | string | yes | Party identifier of the emitter. |
| `key` | string | yes | Key of the item. |
| `project` | string | yes | Project of the item. |
| `ts` | string | yes | RFC 3339 date-time at which the record was created, with at most six fractional digits; a value that is not a valid date-time makes the record invalid. Receivers compare `ts` values as instants, offsets applied, using every fractional digit given; a leap second (`:60`) compares as the last microsecond of its minute. Senders SHOULD use UTC (`Z`). |
| `supersedes` | array of strings | no | Ids of records in the same register that this one replaces (§6); on `approved`, ids of approvals (§5.3). |
| `terms` | object | on `raised`, `amended` | The item's terms; the members are defined by the extension. `text` is always present. |
| `terms_rev` | integer ≥ 1 | on `raised`, `amended`, `settled`, a granting `approved`, and any record carrying `evidence.verifiable` | On need records, the terms version (1 on `raised`, increasing by one on each `amended`). On a settlement or approval, the terms version it was made against. On a claim or note (optional unless it carries verifiable entries), the terms version it refers to. |
| `outcome` | string | on `settled`, `claimed` | What the settlement says or the claim asserts; values defined by the extension. |
| `terms_digest` | string | on `settled` | The terms digest (§5.3) of the need record the settlement was made against, so that a settlement cannot be carried over to other terms at the same `terms_rev` (§6). |
| `authority` | object | on `settled` and a granting `approved` | §5. |
| `evidence` | object | no | §5. |
| `relation` | object | on `related` | §7. |
| `approval` | object | on `approved` | §5.3. |
| `reason` | string | on `withdrawn` | Why the requester withdrew; values defined by the extension. |
| `adopts` | array of strings | no | On `settled`: ids of claims this settlement accepts (§7). |
| `about` | object | on `note` | §7. |
| `note` | string | no | Free text from the emitter (§8). |
| `context` | string | no | Free-form tag for why the record was sent, e.g. `bulk-import`. |

Receivers MUST ignore members they do not recognise. Senders MAY add members; names beginning with `x_` are reserved
for private extensions. Every number in a record MUST be an integer between −(2^53 − 1) and 2^53 − 1, written
without a fraction or an exponent, so that every receiver serialises it alike (§5.3, §10). `terms.due`, where an
extension defines it, MUST be a calendar date.

Every rule that §4–§7 state about the content of a single record (the type table, the authority rules of §5.1, the
rules on verifiable entries and results in §5.2, approvals in §5.3, claims, relations and notes in §7), and every
rule an extension's records section lists, is a validity rule: a record that breaks one is invalid (§10), whether or
not a schema in the subset below can express it. Rules that need other records (that a superseded id exists, that an
approval was in force) are never validity rules; they are duties of the emitter, and receivers that can check them
SHOULD report a breach.

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
| `approved` | (approval, §5.3) | `principal` |
| `claimed` | (claim) | any origin except `principal` |
| `related` | (relation) | per relation kind (§7) |
| `note` | (note) | any origin the extension's table lists |

Extensions MAY restrict this table further, and MUST NOT widen it. A receiver selects the schema by `ext` and the
(`type`, `origin`) pair as the extension's table lists, and MUST reject a record whose pair is not listed. A receiver
that does not implement the extension or version named in `ext` MUST NOT act on the record; it SHOULD consume it
without error and MAY report it. The schemas use JSON Schema draft 2020-12 restricted to `type`, `required`,
`properties`, `enum`, `const`, `pattern` (an ECMAScript regular expression, in which `$` matches only at the end of
the string), `items` and `$ref` (a relative path), plus the annotations `$schema`, `$id` (the schema's path from the
family's root, against which `$ref` resolves), `title` and `description`, so that a small validator suffices.

## 5. Authority and evidence

### 5.1 Authority

Every `settled` record, and every `approved` record that grants an approval (§5.3), carries `authority`:

| Member | Req. | Meaning |
|---|---|---|
| `kind` | yes | `principal`, `confirmed`, `delegated` or `attested`. |
| `decider` | yes | Party identifier of whoever made the settlement or approval. |
| `under` | for `delegated` | Reference to the mandate or standing instruction relied on. The prefix `approval:` is reserved: a value beginning with it names an approval of this family (§5.3). Any other value is an opaque reference to a mandate of another system (§15), which the principal side MUST be able to produce. |
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

When the principal is a legal person, a settlement or approval of kind `principal` or `confirmed` MUST carry
`representative`, naming the natural person who acted for it, and `evidence.proof` SHOULD include evidence of their
power to represent it.

### 5.2 Evidence

`evidence`, when present, is an object:

| Member | Meaning |
|---|---|
| `presented` | Digest (`sha-256:` + lowercase hex), opaque to receivers, of exactly what was shown to the person who decided or confirmed: the terms at `terms_rev` and any options or consequences the principal side displayed (§9). |
| `proposal` | For `confirmed`: id of the record, or digest of the content, that was confirmed. |
| `basis` | For `attested`, and on claims: what the evidence was, in words. |
| `proof` | An independently verifiable proof of **who** made the record, such as a detached JWS or a verifiable credential, over the record with `evidence.proof` removed (and `evidence` too, if it is then empty), serialised with the JSON Canonicalization Scheme [RFC 8785]. |
| `verifiable` | Proofs of **what** is true: an array of verifiable entries (below). Only on `claimed`, `note` and `settled`. |
| `verified` | What the principal side checked: an array of verification results (below). Only on `settled`, and on `note` with `origin: "principal"`. |

A settlement or approval of kind `principal` or `confirmed` SHOULD carry `evidence.proof` made with the principal's
own credential on a surface no agent controls. A **verifiable** principal side (§12) MUST. In a deployment configured
with the principal's verification keys (R6), every role verifies `evidence.proof` on such records, and a record whose
proof is missing or does not verify is invalid.

A **verifiable entry** is an object:

| Member | Req. | Meaning |
|---|---|---|
| `id` | yes | Unique within the record; matches `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`. |
| `format` | yes | The proof system, as that system names itself and its version (for example `tlsnotary`, `vc+sd-jwt`, `in-toto`); 1–128 characters, no whitespace. Formats are defined by their own systems, not by this family. |
| `statement` | yes | What the proof establishes, in plain words for a person. |
| `proof` | one of the two | The proof by value, as a string in the format's own serialisation (base64url where the format is binary). |
| `proof_ref` | one of the two | `{"uri", "digest"}`: where the proof can be fetched, and the digest (`sha-256:` + lowercase hex) of its exact bytes. |

Each entry MUST carry exactly one of `proof` and `proof_ref`. A record that carries verifiable entries MUST carry
`terms_rev`: the terms version the evidence was produced against.

A **verification result** is an object:

| Member | Req. | Meaning |
|---|---|---|
| `of` | yes | `{"record", "entry"}`: the id of a record about the same item (same `ext` name, `project` and `key`), and the `id` of the verifiable entry in it that was checked. The record may be the one carrying the result, or one the principal side keeps and never sends (a proof about the principal, below). Receivers do not resolve `of` to decide validity or state. |
| `verifier` | yes | Party identifier of the verifier. |
| `result` | yes | `valid`, `invalid` or `unsupported` (V3). |
| `at` | yes | RFC 3339 time of the check. |

These rules, and the ones below that no schema in the §4 subset can express (exactly one of two members, unique ids),
are validity rules: a record that breaks them is invalid.

- **V1 — Validity and state never depend on checking a proof.** Whether a record is valid (§4, §5) and an item's state
  and approval in force (§6) are computed from the records' own content; they never depend on anyone verifying a
  verifiable entry. A receiver that cannot check a format, or checks nothing, computes the same state from the same
  records. Structural rules an extension states over a record's own `verified` (for example, that every result is
  `valid`) are part of validity like any other member rule.
- **V2 — A proof establishes only its statement.** That a proven statement concerns this item (that this payment was
  for this act) is the emitter's judgement, except where an extension requires binding (V4). Receivers MUST NOT
  present a valid proof as establishing more than its `statement`, and SHOULD show the statement together with the
  result.
- **V3 — Valid means valid against the principal side's trust policy.** A verifier reports `valid` only when all of
  these hold: (a) the proof verifies in its format; (b) its verified content establishes, in machine-readable form,
  every condition the extension pins (a check's pass condition, an identifier the item names), the `statement` text
  itself counting for nothing; (c) its signer, notary or issuer is a trust root that the principal side's trust policy
  accepts for that format; (d) it is within the freshness bound that policy sets for the format, at the time the
  result is relied on; (e) it is bound to the item where V4 requires. Trust roots are strings in the format's own
  identifier form (a key fingerprint, an issuer URL, a DID), compared exactly. A root is acceptable only if the
  requester cannot choose what it attests: a notary or builder that attests what it itself observed or ran, an issuer
  independent of the requester, or the principal side's own runs. `unsupported` means only that the verifier does not
  implement the format, has no trust policy for it, or could not complete the check (its own infrastructure failed, or
  the `proof_ref` could not be fetched); a proof whose content does not let it read (b), or whose fetched bytes do not
  match `proof_ref.digest`, is `invalid`, like everything else that fails.
- **V4 — Binding and reuse.** Emitters SHOULD produce proofs whose proven content names the item (its `key`, the terms
  digest of §5.3, or an identifier the terms name, such as an invoice number) wherever the format allows. Where an
  extension requires such binding, a proof without it is `invalid`. The principal side SHOULD report to the principal,
  never to a project, a proof offered as evidence for two different items (the same `proof`, the same
  `proof_ref.digest`, or, where the format exposes one, the same underlying fact such as a transaction id), and MUST
  NOT settle a second item on it without the principal, except as an extension allows (Decisions §4.1). "First" means
  the item first settled on the proof. Where the extension does not allow the reuse, the proof fails (e) for the
  second item; what is recorded for that item never names the other. Only proofs offered by parties holding a role in
  an item's project count as offered for it.
- **V5 — Results are recorded.** The principal side records every result it computes for an item, `valid` or not. A
  settlement carries the results it was made on; every other result goes on a `note` about the item from the
  principal side, so that a failed or unsupported check stays on record and reaches the requester.

**Proofs about the principal.** A record the principal side sends to a project MUST NOT disclose, in
`evidence.verifiable` (the `proof`, the `statement` or the `proof_ref.uri`) or in any other text, anything about the
principal that the project may not know (§13). Such proofs stay with the principal side, in records it keeps and does
not send; results about them refer to them through `of`. Because a sent record never changes (§10), this applies when
the record is made. (`evidence.proof`, the signature made with the principal's own credential, is not such a proof.)

### 5.3 Approvals

An **approval** is the principal's approval of an item's terms exactly as they stand at one `terms_rev`. It
authorises at most one settlement of that item, of the kind and on the conditions the item's extension defines (in
Decisions, by a verifier when the approved criteria hold, Decisions §4.1), and nothing else. An extension whose table
(§4) does not list `approved` has no approvals, and in it a settlement whose `under` begins with `approval:` is
invalid. An approval is not a settlement and not an answer: requesters MUST NOT proceed on one as if the item were
settled.

**Recording.** The principal side records an approval as an `approved` record about the item:

| Member | Req. | Meaning |
|---|---|---|
| `approval` | yes | `{"active", "terms_digest"?}`. `active`: `true` grants an approval; `false` retracts the approvals listed in `supersedes`. `terms_digest`: REQUIRED when granting, and only then: the terms digest (below) of the need record at `terms_rev`. |
| `terms_rev` | when granting | The terms version approved. |
| `authority` | when granting | §5.1, of kind `principal` (the person approved the terms as presented) or `confirmed` (the person confirmed a delegate's recommendation to approve; `evidence.proposal` identifies it). Never `delegated` or `attested`. |
| `evidence` | when granting | `presented` is REQUIRED and covers the terms at `terms_rev` with everything the extension puts in them; `proof` as §5.2 says. |
| `supersedes` | when retracting | The approvals retracted. |

A grant MUST NOT carry `adopts`: an approval never comes from a claim. §9 applies to it. It approves the terms as they
stand, without conditions: if the person attaches any condition, reservation or limit, the principal side MUST NOT
record an approval; it MAY send a `note` asking the requester to amend the terms so that they carry it. A `note` on an
`approved` record is never part of what was approved. A new grant for a `terms_rev` that already has a grant MUST
list the earlier grants in `supersedes`.

A retraction (`active: false`) needs no `authority`: the principal side may always narrow what it has authorised, at
any time (for example once `terms.due` has passed). `supersedes` on an `approved` takes effect only on `approved`
records of the same item; other ids in it are ignored and SHOULD be reported. A retracted approval is never in force
again: re-approving is a new grant.

**Terms digest.** The terms digest of a need record (`raised` or `amended`) is `sha-256:` followed by the lowercase
hexadecimal SHA-256 of the UTF-8 bytes of the RFC 8785 serialisation of the JSON object whose members are exactly
`ext` (its full value, such as `decisions/0.4`), `project`, `key`, `terms_rev` and `terms`, copied from that record as
received, including members of `terms` the receiver does not recognise. Receivers keep `terms` as received. Because
records are I-JSON and numbers in terms are bounded integers (§4), every receiver computes the same digest. The
principal side MUST NOT approve terms containing members it does not show the person. Because the digest includes the
item's identity, extension version and terms version, it alone binds the item (settlements and approvals stay bound to
the extension version they were made under; a later version says how to carry them over, §14), and it can be quoted
inside a proven statement (V4). [`conformance/terms-digest.json`](conformance/terms-digest.json) holds vectors.

**Binding.** An approval binds (`ext`, `project`, `key`, `terms_rev`, terms digest). It authorises nothing for any
other item, project or terms version, and nothing transfers it: no relation (§7), claim, note or record of another
item.

**In force.** Whether an approval is in force is computed from the records held, as §6 defines. In short: it lapses
when the terms change in any way, when it is retracted, once a settlement names it, and once the item has any
settlement record made after it (whether under the approval or not, and whether later reopened or not), so that an
approval is used at most once and a principal who has settled or reopened the item by hand is never overridden by it.
For "after" to mean what happened, the principal side MUST give each `settled`, `reopened` and `approved` it makes
about an item a `ts` later than that of every settlement-register record and approval of the item it holds.

**Settling under an approval.** A settlement made under an approval carries `authority.kind: "delegated"`, `decider`
the verifier or other delegate that applied it, `chain` from the principal to that decider, and `under` equal to
`approval:` followed by the `id` of the `approved` record (everything after the prefix is the id, looked up among the
principal side's records of the settlement's own `ext` name and `project`), and `terms_digest` equal to the
approval's. The `by` of such a settlement is still the principal side. A settlement whose `under` begins with
`approval:` MUST be of kind `delegated`, and the id after the prefix MUST NOT be empty. The principal side MUST NOT
send such a settlement unless the named record is a grant about the same item, in force over the records the principal
side held when it settled, at the settlement's `terms_rev`, and the extension's conditions held. That duty is the
principal side's: receivers do not make the settlement's validity depend on the other records they hold (V1), but a
receiver that holds them MAY check and SHOULD report a settlement that fails it.

**One approval store.** Where more than one implementation acts as the principal side (for example a personal
assistant and a platform's built-in owner view), they MUST either share one store of approvals, retractions and
settlements, in which using an approval is one atomic check-and-mark (so that two of them cannot both use it), or
leave approvals to one of them alone. Either way, every implementation delivers its settlements of an item to the one
that holds approvals before that one relies on an approval, and all of them follow the `ts` rule above.

**After a retraction.** A retraction, or a lapse, never changes a settlement already made: state is computed from the
registers (§6). When an approval is retracted, the principal side MUST present every current settlement made under it
to the principal, who either confirms it (a `settled` that supersedes it, kind `confirmed`, `evidence.proposal` its
id) or replaces or reopens it (§6). A lapse through amendment needs nothing further: the settlement is stale (§6).

## 6. Current state

Each register is folded separately, over all its records a receiver holds, regardless of arrival order:

- A **head** is a record in the register that no other held record of the same register names in `supersedes`.
- The **current** record is the head with the latest `ts` (compared as instants, §4). Equal `ts` are broken by the
  greater `id` in Unicode code-point order. If there is no head (`supersedes` links form a cycle), the same rule
  applies to all records of the register.
- There is a **conflict** in the register when there is more than one head, or a cycle (a record that lists itself
  in `supersedes` is a cycle). Receivers MUST use the current
  record and SHOULD report the conflict to a person.

A requester's `amended` and `withdrawn` MUST list the item's current need record in `supersedes`, and every
principal-side `settled` or `reopened` made while the settlement register holds records MUST list its current record.
A receiver that nonetheless holds several heads uses the rule above and reports the conflict.

From the two current records, the item's state is:

| Settlement (current) | Need (current) | State |
|---|---|---|
| `settled` | any, or none | **settled**, with its `outcome`. It is **stale** if its `terms_rev` is lower than the highest `terms_rev` held in the need register, or if the current need record has the same `terms_rev` but a terms digest other than its `terms_digest`. |
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

**Approvals** (§5.3) are folded apart from both registers and never change the state above. A grant (an `approved`
with `approval.active: true`) is **in force** when all of these hold over the records a receiver holds:

1. no held `approved` record about the item lists it in `supersedes`;
2. the need register has no conflict, and its current record is a `raised` or `amended` (not `withdrawn`) whose
   `terms_rev` equals the grant's `terms_rev`, is the highest `terms_rev` held, and whose terms digest (§5.3) equals
   `approval.terms_digest`;
3. no other held `raised` or `amended` with that `terms_rev` has a different terms digest;
4. no held `settled` about the item names it in `authority.under`, and no held `settled` or `reopened` about the item
   has a `ts` equal to or later than the grant's.

If several grants are in force, the item's approval is the one with the latest `ts`, equal `ts` broken by the greater
`id`. The item reports its approval in force, or none. Like the state, this depends only on the records held, not on
their order or on anything checked outside them. An extension MAY narrow which terms an approval can be in force for
(Decisions: only terms with criteria).

## 7. Claims, relations and notes

**Claims.** A `claimed` record asserts an `outcome` that the claimant has no authority to record: an agent that heard
the principal say "I paid it", or a registrar that saw a declared line disappear. It SHOULD carry `evidence.basis`. A
claim changes no register. The principal side MAY accept it by recording a settlement that lists the claim's id in
`adopts`, with kind `confirmed` if the principal confirmed it, or `attested` if evidence independent of the claimant
shows the outcome (the claimant's own word, `evidence.basis` included, is never enough for `attested`); `adopts` MUST
NOT appear on a settlement of any other kind, nor on any other record. An id in `adopts` adopts every held claim about
the item with that id; an id in `verified.of` likewise names every record about the item with that id. A claim never
removes an item from the principal's view. A claim MAY carry `terms_rev`, the terms version it refers to, and MAY
carry verifiable entries (§5.2); a principal side that adopts a claim on the strength of its verifiable entries
records the results in `verified` (V5) and settles `attested` only if every entry it relies on is `valid`. Extensions
narrow what such entries may establish (Acts §2, Decisions §2).

**Relations.** A `related` record carries `relation`:

| Member | Meaning |
|---|---|
| `kind` | `same_as`, `derived_from` or `replaced_by`. |
| `target` | The other item: `{"ext", "project", "key"}` (all three) for an item of this family, or `{"uri"}` for anything else (an A2A task, a bus message, an issue). Exactly one of the two forms MUST be used. |
| `active` | `true`, or `false` to retract the relation. For each (`kind`, `target`) of an item, the relation record with the latest `ts` (equal `ts`: greater `id`) decides whether the relation is active. |

- `same_as` is emitted by the principal side (`origin: "principal"`) when it treats two items as one, for example the
  same request raised by two projects, or a request repeating one already settled. Relations never change any item's
  state (§6): when the principal side settles a group of related items, it MUST emit a `settled` for each item, so
  that every requester computes the same state. A settlement under an approval (§5.3) covers only its own item: the
  others stay open until they are settled on their own authority. One requester withdrawing leaves the other items
  open. A relation the principal side sends to a project names an item of another project only by a `uri` that the
  principal side alone can resolve, never by that project's `ext`, `project` and `key` (§13).
  A requester that disagrees sends a `note` about its item saying why the two differ; the principal side SHOULD then
  retract the relation.
- `derived_from` is emitted by the requester when its item arises from another item, inside or outside this family
  (§3 R5; a question asked while answering an inquiry from the principal; a task that an answer created).
- `replaced_by` is emitted by the requester when it replaces its item with another of its own items: the same need,
  raised again under another key. Its target MUST be an item with the same `ext` and `project` as the record, and not
  the item itself: an item of another kind would fall under another withdrawal policy (§11). A requester that replaces
  an item sends `replaced_by` and then withdraws the item with the extension's replacement reason. An item with more
  than one active `replaced_by` has no replacement; the principal side SHOULD report it. How the principal side
  presents a replaced item is the extension's policy (§11). A requester's re-sent list that simply omits the old item
  replaces nothing (R4), and no relation moves a settlement or an approval from one item to another.

**Notes.** A `note` record carries information that changes no register: progress, a fact the principal mentioned, a
premise that changed. It carries `about`, either `{"key": …}` for a keyed item or `{"quote": …}` with text in the
recipient's own words for something that was never keyed (exactly one of the two); such a note carries, as its `key`,
one the sender chooses that names no item. A note whose `about` has `key` MUST carry the same `key` (a validity rule).
A note never settles anything. In particular, a note from the principal side saying a premise changed (a moved date)
is not an amendment: the requester decides whether to amend its terms. A note MAY carry `terms_rev`, the terms version
it refers to; it MUST when it carries verifiable entries (§5.2). A principal-side note MAY carry `verified`, which is
how a verification that settled nothing is recorded (V5).

## 8. Delivery and application

- The principal side MUST deliver every settlement, approval, relation it emits, and note it addresses to a project to
  that project, where its agents will read it next (an inbox, notes, a decision log), not only to a session that may
  no longer exist.
- **Mechanical versus judgement.** Only an extension's binding applies records mechanically, and only to keyed items
  (for example, striking a line in a state document). Everything else, including every note and every `quote`, is
  applied by judgement: the recipient decides what changes. Implementations MUST NOT apply a `quote` reference
  mechanically.
- A `note` on any record is for the other party: on need records and claims, for the principal side, which SHOULD show
  it with the item; on settlements, approvals and notes from the principal side, for the project.
- What the principal side sends a project carries only what that project may know (§13), and its verification results
  rather than proof bodies about the principal (§5.2).

## 9. When a person decides

These rules apply to every settlement and every approval (§5.3) of kind `principal` or `confirmed`, that is, whenever
a natural person decides or confirms, whether the principal or an organisation's representative.

- The principal side MUST present the terms at the `terms_rev` it records, and SHOULD record `evidence.presented`. If
  the terms change before the person decides, the principal side MUST present them again.
- The principal side SHOULD show the requester's working assumption as such, and SHOULD NOT pre-select it.
- The principal side SHOULD show, or flag, members of the terms it does not recognise: a requester must not rely on
  terms the person was never shown.
- Before an approval, the principal side MUST make clear what it authorises: that a verifier may settle the item
  without the person seeing the result, on what conditions, and for these terms only.
- The principal side SHOULD batch and rate-limit items per project and SHOULD NOT present an item it can settle under
  an existing mandate. A person's attention is the scarce resource this family protects.
- *Note (informative):* a person who confirms everything they are shown is deciding only in name. Recording
  `presented`, the authority kind and the decider makes that visible, and is a precondition for the human oversight
  that rules such as the EU AI Act Article 14 require of high-risk systems. Approvals (§5.3) exist so that a person
  can decide what counts as done instead of reviewing more work than they can read; they do not make the review
  unnecessary, they move it (§13).

## 10. Identifiers, deduplication and ordering

- A record id MUST be unique per logical record within its (`ext` name, `project`, `origin`), and MUST be the same on
  every retransmission. Extensions say how ids are derived when a sender must re-create them after a crash. A sender
  MUST NOT reuse an id for a different record. Ids are scoped by `origin` so that no party can displace another
  role's record by reusing its id; every reference to an id (`supersedes`, `adopts`, `under`, `verified.of`) names a
  record of the origin that reference implies (the register's owner, a claimant, the principal side).
- Receivers MUST discard a record identical to one they have already processed with the same (`ext` name, `project`,
  `origin`, `id`). A record that fails validation, or names a version the receiver does not implement (§4), is not
  processed: it is ignored, and does not block a valid record with the same id. A receiver that sees an id reused
  with different valid content keeps the one whose RFC 8785 serialisation is greater in code-point order, whatever
  the arrival order, and SHOULD report it unless the two differ only in `ts` (a record re-created after a crash). A
  need record replaced this way changes the terms at its `terms_rev`; settlements made on the other content become
  stale through their `terms_digest` (§6).
- Senders MUST retry until the transport accepts the record (at-least-once delivery). Ordering is not guaranteed;
  §6 makes the current state independent of arrival order.
- A record that was never sent MAY be retracted by its sender without trace (for example, a settlement held for an
  undo window). Once sent, a record is changed only by a later record that supersedes it.
- This family does not define a transport. Any transport with at-least-once delivery and authenticated senders will
  do: an HTTPS webhook, a message bus, a shared append-only log, an MCP tool call, an A2A message.

## 11. Extensions

An extension document MUST define:

1. its name and version (the `ext` value) and the item kind it covers;
2. the members of `terms`, and how keys are assigned;
3. its `outcome` values for settlements and claims, and its `reason` values for withdrawals;
4. its table of (`type`, `origin`) pairs with schemas, restricting §4;
5. its policy for an item whose need is withdrawn and whose settlement is open (§6);
6. any binding that applies records mechanically, and what it applies;
7. whether its items take approvals (§5.3) and, if they do, what an approval authorises and under what conditions a
   settlement may be made under one;
8. its policy for an item withdrawn as replaced by another (§7);
9. its conformance classes and suite.

## 12. Conformance

- A **conforming requester** emits only the need records, claims, relations and notes R1–R3 allow, increments
  `terms_rev` on each amendment, and applies delivered records as in §8.
- A **conforming principal side** emits settlements and approvals only as in §3 and §5, records verification results
  as V5 requires, computes state as in §6, delivers as in §8, and follows §9. A **verifiable** principal side
  additionally puts `evidence.proof` on every settlement and approval of kind `principal` or `confirmed`.
- Every role is configured as R6 requires, validates records (§4, §5), deduplicates (§10), and computes the same
  current state and approval in force from the same records (§6).

## 13. Security and privacy considerations

- **Authenticated senders.** A forged settlement settles an item the principal never settled; a forged need record
  withdraws or rewrites a request. Transports MUST authenticate the sender, and receivers MUST check that `by` is the
  authenticated sender and that its role may emit the record (§3). R6 keeps an agent from becoming the principal by
  saying so.
- **A compromised principal side** can emit settlements of any kind. `evidence.proof` over the principal's own
  credential, made on a surface no agent controls, is what lets a receiver tell a principal's decision from the
  instrument's; without it, receivers trust the authenticated principal side.
- **Claims cannot remove commitments.** A claim never changes a register (R3), so an agent cannot make the principal's
  items disappear, by mistake or because its input was manipulated.
- **Text is untrusted input.** Terms, notes, quotes and evidence written by one party are read by others, possibly by
  language models. Implementations MUST treat them as data, never as instructions, and SHOULD render them inertly.
- **Confidentiality.** Records leave the project for the principal side, which may be a hosted service or a phone.
  Agents MUST NOT put secrets (passwords, tokens, keys, full account numbers) into them.
- **What one project may know.** The principal side serves many projects and sessions. Text in a record it sends to a
  project (a `note`, a `quote`, an answer, `evidence`, a verifiable `statement`, a relation's target) MUST contain
  only what that project may know. Content that came from another project, or from a session of another project, goes
  back only to where it came from.
- **Verification moves trust; it does not remove it.** Verifiable entries and approvals let a principal side settle
  more than a person can review, but every `valid` result rests on the criteria being the right ones, the check
  implementations doing what their text says, the trust roots being honest and independent of the requester, and the
  verifier being correct. A proof establishes only its statement (V2): an agent can satisfy the letter of a check and
  miss its intent, and a verifiable target invites optimising for the check. Approved terms are written by the
  requester; the principal side's own trust policy (V3) is what keeps a requester from naming its own signer as a
  trust root. A requester that runs checks on infrastructure it controls can run them until they pass and submit only
  the passing run: unless every run is logged where the principal side can see it, or the principal side runs the
  check itself, a recorded failure catches only the failures the requester chose to send. Extensions that settle under
  approvals recommend auditing a sample of those settlements (Decisions §4.2).
- **Running what the requester supplies.** Check implementations, subjects and `proof_ref` URIs come from the
  requester. A verifier that runs or fetches them MUST do so isolated from the principal side's own state, credentials
  and proofs about the principal, and SHOULD fetch through a channel that tells the requester nothing about the
  principal.
- **Replayed and stale proofs.** A proof made for one item can be offered for another, and an old proof can be offered
  after the fact changed. Binding the proven statement to the item, freshness bounds per format, and reporting reuse
  (V3, V4) are the defences.
- **Proofs about the principal.** Selective-disclosure credentials (SD-JWT, BBS) and web proofs (zkTLS, TLSNotary) can
  disclose facts about the principal: their identity, accounts and payments. Such proofs stay with the principal side
  (§5.2). An agent able to produce a web proof over the principal's own account must hold that account's session, that
  is, the principal's credentials; agents SHOULD NOT hold them (work an agent can do with the principal's credentials
  is not something only the principal can do, and those credentials are secrets, above). Proofs about the principal's
  accounts are therefore made by the principal side, on a surface the principal controls; agents offer proofs about
  their own work and about public facts.
- **Approvals are authority.** A forged or replayed approval lets a verifier settle without the principal. Approvals
  are bound to one item and one terms version, authorise one settlement (§5.3), and `evidence.proof` on them is what
  lets a receiver tell the principal's approval from the instrument's. An approved item whose requester never submits
  stays unsettled; the principal side SHOULD present it to the principal again at its due date, or after a period it
  tells the principal, rather than keep it out of view (§9).
- **Resource limits.** Receivers SHOULD bound record size, text length and record rate per project.

## 14. Versioning

- `ph` carries the core version; `ext` carries each extension's name and version.
- Before 1.0, every version is its own contract: senders and receivers support exactly the versions they claim. From
  1.0 on, adding optional members, record types or outcome values will be a minor change; removing or renaming a
  member, or changing the meaning of one, will require a new major version.
- A version leaves draft status only once two independent implementations pass the same conformance suite.
  *Open issue:* whether two implementations that play different roles (for example a requester and registrar on one
  side, a principal side on the other) count as two independent implementations is not yet decided.

**Change log.** 0.4 (2026-11-01): verifiable entries (`evidence.verifiable`) and verification results
(`evidence.verified`) with rules V1–V5; approvals, a new `approved` record and the one mandate this family defines,
bound to an item's terms by the terms digest and referenced as `under: "approval:<id>"` (§5.3, §15); the approval in
force is folded beside the registers (§6); the `replaced_by` relation; `terms_rev` on claims and notes; R4 covers a
requester's listing that omits an item; §13 covers text sent to a project, proofs and approvals. Every extension is
re-pinned to core 0.4. 0.3 (2026-10-27): the event model of 0.2 is replaced by two registers with owners, claims,
relations and notes; resolutions carry an authority kind, a decider and evidence; the principal is defined
structurally and configured (R6); Tasks and Questions become the Acts and Decisions extensions. A mapping from every
0.2 event to 0.3 records is in each extension. 0.2 (2026-10-27): split from Human Task Handoff 0.1.

## 15. Scope

Out of scope, deliberately:

- **Mandate formats and lifecycle, except approvals.** Issuing, scoping, revoking and verifying mandates belong to
  their own systems (§16); for those this family only records the reference (`under`) and the chain. The one exception
  is the approval (§5.3), a deliberately narrow mandate defined here: it is granted by a person, covers one item's
  terms at one `terms_rev` and nothing else, cannot be transferred, lapses when the terms change, and authorises only
  what the item's extension says. An `under` beginning with `approval:` refers to one; every other `under` stays an
  opaque reference to another system. Standing instructions that span items ("pay any invoice under 50 euros") remain
  out of scope.
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
  matters for accountability, not only the current actor. AP2's Trusted Surface is the model for `evidence.proof`.
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
- **Verifiable evidence** borrows its proof systems instead of defining any: web proofs over TLS (TLSNotary, DECO and
  other "zkTLS" systems), selective-disclosure credentials (SD-JWT, RFC 9901; BBS signatures), and signed build and
  test attestations (in-toto, SLSA). `format` names them; this family records what was proven and what was checked.
- **Approvals** apply an idea from scalable-oversight research: when a person cannot check the work, they decide what
  a cheap, trusted check must establish, as in proof-carrying code (the consumer sets a safety policy and checks a
  proof instead of the code), AI safety via debate and prover-verifier games. As there, the check is only as good as
  the policy and the verifier (§13).

## References

- [RFC 2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.
- [RFC 8174] Leiba, B., "Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words", BCP 14, RFC 8174, May 2017.
- [RFC 3339] Klyne, G. and C. Newman, "Date and Time on the Internet: Timestamps", RFC 3339, July 2002.
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
- [RFC 9901] Fett, D., Yasuda, K., and B. Campbell, "Selective Disclosure for JSON Web Tokens", RFC 9901, November
  2025.
- Necula, G. C., "Proof-Carrying Code", POPL 1997.
- Irving, G., Christiano, P., and D. Amodei, "AI safety via debate", arXiv:1805.00899, 2018.
- Kirchner, J. H., et al., "Prover-Verifier Games improve legibility of LLM outputs", arXiv:2407.13692, 2024.
