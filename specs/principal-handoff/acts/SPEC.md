# Principal Handoff: Acts 0.6

| | |
|---|---|
| Status | Draft, release candidate (core §14) |
| Version | 0.6 (2026-11-04); 0.5 (2026-11-01); 0.4 (2026-11-01); 0.3 (2026-10-27); formerly Tasks 0.2 and Human Task Handoff (HTH) 0.1 |
| Extension | `acts/0.6`, an extension of [Principal Handoff Core 0.6](../core/SPEC.md) |
| Binding | [Acts Markdown](../acts-markdown/SPEC.md) |
| Modules | [Evidence](../evidence/SPEC.md) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) (record schema in [`../core/schemas/`](../core/schemas/)) |
| Conformance suite | [`conformance/`](conformance/) |
| Reference | [`../reference/`](../reference/) |

## Abstract

Agents working for someone often find work only that someone can do: pay an invoice, sign a contract, buy a part,
renew a domain. This extension of Principal Handoff covers such **acts**. It defines their terms and outcomes on top
of the [core](../core/SPEC.md) registers. The [Acts Markdown binding](../acts-markdown/SPEC.md), a document of its own,
lets agents declare acts as lines in a project's state document, the document they already read and write, where a
**registrar** turns those lines into records and applies the principal side's settlements back to the document.

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [Model](#2-model)
3. [Records](#3-records)
4. [Record ids](#4-record-ids)
5. [Markdown binding](#5-markdown-binding)
6. [Mapping from 0.2 and changes from 0.5](#6-mapping-from-02-and-changes-from-05)
7. [Conformance](#7-conformance)
8. [Security considerations](#8-security-considerations)
9. [Open issues](#9-open-issues)
10. [Implementations](#10-implementations)

Appendix A: [Mapping notes for the reference deployment](#appendix-a-mapping-notes-for-the-reference-deployment)

## 1. Conventions and terminology

The key words in this document are to be interpreted as in the [core](../core/SPEC.md#1-conventions-and-terminology),
which also defines *principal*, *principal side*, *requester*, *delegate*, *item*, *key*, *terms*, *record*, *claim*,
*relation* and *note*. This extension adds:

**Act**
: An item of kind `act`: work only the principal can do, because it needs their identity, credentials, money, legal
capacity or physical presence, or because they reserved it. Agents SHOULD NOT declare acts for work an agent could do
with the access it has.

**Registrar**
: The component the [Acts Markdown binding](../acts-markdown/SPEC.md#1-conventions-and-terminology) defines (§5).

## 2. Model

- **Terms:** `{"text": …, "due"?: "YYYY-MM-DD"}`. `text` is a single line.
- **Settlement outcomes:** `done` (the principal did it), `dropped` (it will not be done), `already_done` (it had
  been done before it was raised, or repeats an item already settled; the settlement SHOULD be accompanied by a
  `same_as` relation to that item).
- **Claim outcomes:** `done`, `dropped`.
- **Withdrawal reasons:** `not_needed`, and `replaced` (the requester raised the same act again under another key and
  sent `replaced_by` to it, core §7).
- **Withdrawn need, open settlement:** an act may be a commitment the principal has made to someone else, so a
  withdrawal never ends it. The principal side MUST keep the item open and SHOULD ask the principal whether to drop
  it; it ends only with a settlement. (Core §6.)
- **Replaced acts:** an act withdrawn as `replaced` follows the keep policy like any withdrawn act; only its
  presentation differs. While the target of its single active `replaced_by` (core §7) is an act the principal side
  holds open (raised, not settled, not withdrawn), the principal side SHOULD show the replaced act with that target
  and ask about both together, not about the replaced act alone; once the target is settled or withdrawn, or is no
  longer the single active target, it asks about the replaced act on its own, without pre-selecting an outcome (core
  §9). A replaced act is settled only by the principal (kind `principal` or `confirmed`), never from the replacement's
  settlement.
- **Settling on proofs:** a principal side that implements the [Evidence](../evidence/SPEC.md) module may settle an
  act from a claim that carries proofs, only as Evidence §5 says.
- **Claims from the registrar** (Acts Markdown §2 step 5: a vanished line, a ticked box) are never adopted as
  `attested` on that basis alone: what happened to a line is not evidence that the work was done (core R4). The
  principal side settles such an act with the principal (kind `principal` or `confirmed`), or `attested` on
  independent evidence.
- **Keys** are assigned by the registrar (Acts Markdown §4) or, outside the binding, by the requester. A
  deployment that runs a registrar fixes a prefix for the keys it derives and tells its requesters. Keys a requester
  assigns outside the binding MUST NOT begin with it, so that they never collide with a registrar's keys.

## 3. Records

Records use the [core record](../core/SPEC.md#4-records) with `ext: "acts/0.6"`.

| `type` | `origin` | Emitted by | Schema | Additional requirements |
|---|---|---|---|---|
| `raised` | `requester` | the requester, or the registrar on its behalf | [`raised`](schemas/raised.schema.json) | `terms.text`, `terms_rev: 1` |
| `amended` | `requester` | as above | [`amended`](schemas/amended.schema.json) | `terms`, `terms_rev` |
| `withdrawn` | `requester` | as above | [`withdrawn`](schemas/withdrawn.schema.json) | `reason` |
| `settled` | `principal` | the principal side | [`settled`](schemas/settled.schema.json) | `outcome` of §2, `authority`, `terms_rev`, `terms_digest` |
| `reopened` | `principal` | the principal side | [`reopened`](schemas/reopened.schema.json) | `supersedes`, `restore_text` |
| `claimed` | `agent`, `registrar`, `requester` | anyone else | [`claimed`](schemas/claimed.schema.json) | `outcome` of §2; `evidence.basis` |
| `related` | `principal` (`same_as`), `requester` (`derived_from`, `replaced_by`) | | [`related`](schemas/related.schema.json) | `relation` |
| `note` | `requester`, `registrar`, `principal`, `agent` | | [`note`](schemas/note.schema.json) | `about` |

`restore_text` on `reopened` is a copy of the item's current terms text, so that a registrar that has lost its stored
terms can still re-add the line. It is not an amendment. Validity rule beyond the schemas (core §4): `terms.text` is a
single line. As core §6 says, `amended` and `withdrawn` MUST list the item's current need record in `supersedes` (a
duty of the requester, not a validity rule).

## 4. Record ids

Ids carry a type prefix and a colon, which keys cannot contain (core §1), so ids of different records never collide.

- `raised`: `r:<key>`, so that a sender re-creating it after a crash re-sends the same id (core §10).
- `amended`: `a:<key>:<terms_rev>`.
- A registrar's `claimed` and `note`: as the binding says (Acts Markdown §5).
- Other records: any id unique per core §10.

## 5. Markdown binding

The [Acts Markdown binding](../acts-markdown/SPEC.md) is the binding of this extension that applies records
mechanically (core §8, §11): its registrar strikes the lines of a project's state document that carry an act's key
when the principal side settles the act, and re-adds the line of an act it raised when the principal side reopens it
(Acts Markdown §2 step 1, §3.5). That document also defines the registrar, the derivation of the keys it assigns, the
ids of its claims and notes, and the records a deployment that runs a registrar delivers to it. Requesters and
principal sides that do not use a state document need not implement it.

## 6. Mapping from 0.2 and changes from 0.5

| Tasks 0.2 event | Acts 0.6 record |
|---|---|
| `registered` (registrar), id = key | `raised`, origin `requester`, sent by the registrar, id `r:<key>`, `terms_rev: 1` |
| `done`, `dropped`, `already_done` (principal) | `settled` with that `outcome`; `authority.kind` `principal`, or, where 0.2 had `decided_by: assistant`, `attested` with `evidence.basis` naming the 0.2 event (`delegated` only where the mandate is known, with `under` and `chain`) |
| `reopened` (principal) | `reopened` superseding the settlement; 0.2's `text` becomes `restore_text` |
| `done`, `dropped` (agent) | `claimed` with that `outcome` |
| inferred `done` (registrar), id `done-<key>` | `claimed`, origin `registrar`, `outcome: "done"`, `evidence.basis`, id `c:<key>:r0` |
| a resolution's `note` | the settlement's `note`, delivered to the project |

Changes from 0.5: records carry `ph: "0.6"` and `ext: "acts/0.6"`, and a relation names an act by the extension name
`acts` (core §7).

**Conversion** (core §14), with vectors in [`../core/conformance/convert.json`](../core/conformance/convert.json):
both ways, change `ph` and `ext` (`"acts/0.5"` ↔ `"acts/0.6"`), remove `evidence.proof`, and convert a relation's
`target.ext` as core §14 says. The only 0.5 records with no 0.6 form are the relations core §14 lists. The 0.4 to 0.5
conversion was: change `ph` and `ext`, remove `evidence.proof`, and replace a settlement's `terms_digest` as core 0.5
§14 said.

## 7. Conformance

### 7.1 Conformance classes

- A **conforming requester** follows core §12; it runs `records.json` and is compared on the settlement view in
  `lifecycle.json`.
- A **conforming principal side** for acts follows core §12 and §2: the withdrawn-need and replaced-act policies, and
  the limit on settling from registrar claims.

The reader and registrar classes are the binding's (Acts Markdown §7).

### 7.2 Conformance suite

[`conformance/`](conformance/) holds JSON fixtures; its [README](conformance/README.md) documents the formats. The
binding's fixtures are in [`../acts-markdown/conformance/`](../acts-markdown/conformance/).

| File | Exercises |
|---|---|
| `records.json` | §3: record → schema it validates against, or invalid |
| `lifecycle.json` | core §6 and §2's keep policy: the records one receiver holds for one act → its state; a requester is compared on the settlement view only (core §12) |

## 8. Security considerations

The [core considerations](../core/SPEC.md#13-security-and-privacy-considerations) apply, and those of the binding
(Acts Markdown §8) to deployments that use it.

## 9. Open issues

- **Transport bindings.** No binding to a specific transport (HTTPS webhooks, A2A, MCP) is defined yet.

The binding's open issues are in Acts Markdown §9.

## 10. Implementations

*Non-normative.*

| Implementation | Roles | Profiles | Status |
|---|---|---|---|
| [`../reference/`](../reference/) in this repository | reader, registrar logic, record validation and state, the Evidence and Criteria modules (no transport) | `en`, `zh-hant` | passes the 0.5 conformance suites of every document |
| [brunna](https://github.com/imaknas/brunna) | registrar and requesters for Acts; requesters for Decisions | `zh-hant`, `en` | the reference deployment this document is generalised from; implements Acts 0.5 and Decisions 0.5, and passes the binding fixtures, `records`, `lifecycle` (settlement view), the terms-digest vectors and `convert` (without the Criteria cases) |
| Muninn, with brunna's built-in owner side | principal side | | implements the principal side of 0.5; passes `records`, `lifecycle`, the terms-digest vectors and `convert` (without the Criteria cases) |

The reference code, brunna and Muninn share an author, so under core §14 they are not independent: no class of this
document or of the binding has two independent implementations yet.

The reference deployment has two implementations acting as its principal side; each delivers its settlements to the
other (core §6). Neither records approvals ([Criteria](../criteria/SPEC.md)) or checks proofs
([Evidence](../evidence/SPEC.md)).

## Appendix A: Mapping notes for the reference deployment

*Non-normative.* The reference deployment uses its own message names on an internal event bus:

| Reference deployment | Acts 0.6 |
|---|---|
| message type `task` sent to the principal, with a fixed id equal to the key | `raised` (`id` = `r:<key>`) |
| principal-side handoff with `effect` `done` / `dropped` / `already_done` | `settled` with that `outcome` |
| principal-side handoff with `effect` `reopened` | `reopened` |
| handoff field `reply_to` | `key` |
| handoff field `item` | `restore_text` on `reopened`, otherwise the project's own wording in a `note` |
| agent message `done` / `drop` with a task key | `claimed` with `outcome` `done` / `dropped` |
| `done` with `inferred: true`, id `done-<key>` | registrar `claimed`, id `c:<key>:r0` |
| handoff `effect` `resolves` / `changes` / `relevant` on an unkeyed to-do | `note` with `about.quote` |
| `context: migration` on the first run | `context` |
