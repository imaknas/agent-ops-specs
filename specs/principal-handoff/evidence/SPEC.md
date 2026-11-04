# Principal Handoff: Evidence 0.6

| | |
|---|---|
| Status | Experimental ([release candidate](../README.md#release-candidate)) |
| Version | 0.6 (2026-11-04); 0.5 (2026-11-01); in core 0.4 as §5.2 |
| Module | of [Principal Handoff Core 0.6](../core/SPEC.md), for every extension (`acts/0.6`, `decisions/0.6`) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) |
| Conformance suite | [`conformance/`](conformance/) |
| Reference | [`../reference/`](../reference/) |

## Abstract

Records can carry evidence. The core records who decided and what they were shown; this module lets a record carry
**proofs of facts** that a third party can check without trusting whoever reported them (a web proof that an invoice
was paid, a signed test attestation), and lets the principal side record what it checked. Proofs are borrowed from
the systems that define them; this module records what was proven, by what format, and with what result. Like every
module (core §11), it never changes whether a record is valid or what state an item is in.

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [Members](#2-members)
3. [Verification](#3-verification)
4. [Proofs about the principal](#4-proofs-about-the-principal)
5. [Use by the extensions](#5-use-by-the-extensions)
6. [Conformance](#6-conformance)
7. [Security considerations](#7-security-considerations)
8. [Changes from 0.5](#8-changes-from-05)
9. [Relation to other specifications](#9-relation-to-other-specifications)

## 1. Conventions and terminology

The key words in this document are to be interpreted as in the [core](../core/SPEC.md#1-conventions-and-terminology),
which also defines *principal*, *principal side*, *requester*, *item*, *record*, *claim* and *note*. This module adds:

**Verifiable entry**
: A proof of a fact that a third party can check without trusting whoever reported it, carried in a record's
`evidence.verifiable` (§2).

**Verification result**
: What a verifier found when it checked one verifiable entry, carried in `evidence.verified` (§2).

**Trust policy**
: The principal side's own list, per proof format, of the signers, notaries and issuers whose proofs it accepts, and
of the freshness bounds it applies (§3).

**Trust root**
: A signer, notary or issuer whose proofs a trust policy accepts for a format, named as that format names it (§3).

**Verifier**
: A component of the principal side that checks verifiable entries against its trust policy. A verifier that settles
an item does so as a delegate (core §5).

## 2. Members

This module defines two members of `evidence` (core §5.2):

| Member | On | Meaning |
|---|---|---|
| `verifiable` | `claimed`, `note`, `settled` | Proofs of **what** is true: an array of verifiable entries. |
| `verified` | `settled`, and `note` with `origin: "principal"` | What the principal side checked: an array of verification results. |

A **verifiable entry** is an object:

| Member | Req. | Meaning |
|---|---|---|
| `id` | yes | Unique within the record; matches `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`. |
| `format` | yes | The proof system, as that system names itself and its version (for example `tlsnotary`, `vc+sd-jwt`, `in-toto`); 1–128 characters, no whitespace. Formats are defined by their own systems, not by this family. |
| `statement` | yes | What the proof establishes, in plain words for a person. |
| `proof` | one of the two | The proof by value, as a string in the format's own serialisation (base64url where the format is binary). |
| `proof_ref` | one of the two | `{"uri", "digest"}`: where the proof can be fetched, and the digest (`sha-256:` + lowercase hex) of its exact bytes. |

A **verification result** is an object:

| Member | Req. | Meaning |
|---|---|---|
| `of` | yes | `{"record", "entry", "origin"?}`: the id of a record about the same item (same `ext` name, `project` and `key`), the `id` of the verifiable entry in it that was checked, and the record's `origin`. The record may be the one carrying the result, or one the principal side keeps and never sends (§4). Without `origin`, `of.record` names every record about the item with that id (core §10). |
| `verifier` | yes | Party identifier of the verifier. |
| `result` | yes | `valid`, `invalid` or `unsupported` (V3). |
| `at` | yes | RFC 3339 time of the check. |

**Structural rules** (core §11): `evidence.verifiable` and `evidence.verified` validate against
[`schemas/evidence.schema.json`](schemas/evidence.schema.json) and appear only on the records the table above lists;
each entry carries exactly one of `proof` and `proof_ref`; entry ids are unique within the record; a record that
carries entries carries `terms_rev`, the terms version the evidence was produced against; every `at` is a valid
RFC 3339 date-time. A receiver that implements this module and finds a record that breaks one of them ignores that
record's `verifiable` and `verified` and SHOULD report it. The record stays valid, and the item's state stays as the
core computes it.

## 3. Verification

The core's V1 holds: no result changes whether a record is valid or what state an item is in. The rules below say what
a result means and what the principal side does with it.

- **V2 — A proof establishes only its statement.** That a proven statement concerns this item (that this payment was
  for this act) is the emitter's judgement, except where binding is required (V4). Receivers MUST NOT present a valid
  proof as establishing more than its `statement`, and SHOULD show the statement together with the result.
- **V3 — Valid means valid against the principal side's trust policy.** A verifier reports `valid` only when all of
  these hold: (a) the proof verifies in its format; (b) its verified content establishes, in machine-readable form,
  every condition the rule relying on it pins (a check's pass condition, an identifier the item names), the
  `statement` text itself counting for nothing; (c) its signer, notary or issuer is a trust root that the principal
  side's trust policy accepts for that format; (d) it is within the freshness bound that policy sets for the format,
  at the time the result is relied on; (e) it is bound to the item where V4 requires. Trust roots are strings in the
  format's own identifier form (a key fingerprint, an issuer URL, a DID), compared exactly. A root is acceptable only
  if the requester cannot choose what it attests: a notary or builder that attests what it itself observed or ran, an
  issuer independent of the requester, or the principal side's own runs. `unsupported` means only that the verifier
  does not implement the format, has no trust policy for it, or could not complete the check (its own infrastructure
  failed, or the `proof_ref` could not be fetched); a proof whose content does not let it read (b), or whose fetched
  bytes do not match `proof_ref.digest`, is `invalid`, like everything else that fails.
- **V4 — Binding and reuse.** Emitters SHOULD produce proofs whose proven content names the item (its `key`, its terms
  digest, core §4, or an identifier the terms name, such as an invoice number) wherever the format allows. Where a
  rule relying on the proof requires such binding, a proof without it is `invalid`. The principal side SHOULD report
  to the principal, never to a project, a proof offered as evidence for two different items (the same `proof`, the
  same `proof_ref.digest`, or, where the format exposes one, the same underlying fact such as a transaction id), and
  MUST NOT settle a second item on it without the principal, unless a module layered on this one allows it. "First"
  means the item first settled on the proof. Where the reuse is not allowed, the proof fails (e) for the second item;
  what is recorded for that item never names the other. Only proofs offered by parties holding a role in an item's
  project count as offered for it.
- **V5 — Results are recorded.** The principal side records every result it computes for an item, `valid` or not. A
  settlement carries the results it was made on; every other result goes on a `note` about the item from the
  principal side, with `terms_rev`, so that a failed or unsupported check stays on record and reaches the requester
  (core §8).

## 4. Proofs about the principal

A record the principal side sends to a project MUST NOT disclose, in `evidence.verifiable` (the `proof`, the
`statement` or the `proof_ref.uri`) or in any other text, anything about the principal that the project may not know
(core §13). Such proofs stay with the principal side, in principal-side `note` records it keeps and never sends (core
§8 lets notes be kept unsent where a module says so); results about them refer to them through `of`. Because a sent
record never changes (core §10), this applies when the record is made. (`evidence.proof`, the signature made with the
principal's own credential, is not such a proof.)

An agent able to produce a web proof over the principal's own account must hold that account's session, that is, the
principal's credentials, which agents should not hold (core §13). Proofs about the principal's accounts (their bank,
their mailbox) are therefore made by the principal side, on a surface the principal controls; agents offer proofs
about their own work, the other party's side, and public facts.

## 5. Use by the extensions

**Acts: settling on proofs.** A claim of `done` MAY carry verifiable entries, for example a web proof from the payee's
invoice portal that invoice 2026-114 was paid. A principal side that implements this module MAY adopt such a claim as
`attested` (core §7) with the results in `verified`, only for the outcomes `done` and `already_done`, and only if each
entry it relies on is `valid` and bound to the act: its verified content contains the act's `key`, its terms digest,
or an identifier (an invoice number, an order or payment reference) named in terms of the act that the principal has
been shown, since later terms are the requester's alone (V4). The settlement's `terms_rev` is the claim's. Where the
format exposes the underlying fact (a transaction id), the principal side MUST NOT settle a second act on the same
fact without the principal (V4). A proof never settles an act `dropped`. Proofs over the principal's own accounts come
only from the principal side (§4).

**Decisions: attested answers.** When the evidence independent of the claimant that Decisions §2 requires for an
`attested` settlement is verifiable entries, their verified content MUST establish that the principal decided this
decision at these terms: for example a message signed with the principal's credential that names the terms digest
(core §4) and the answer. A key alone does not suffice, since it survives amendments.

**Criteria** ([Criteria](../criteria/SPEC.md)) uses entries for check results (submissions) and results on the
settlements a verifier makes.

## 6. Conformance

- A **conforming verifier** is a principal side that implements this module: it applies the structural rules of §2,
  reports and records results as V2–V5 say, keeps proofs about the principal as §4 says, and settles from proofs only
  as §5 allows.

Every other role ignores this module's members, as core §11 says. What this module asks of emitters (V4's binding) is
not part of any conformance class here; a module that uses entries (Criteria's submissions) says what its emitters
follow. The suite tests the structural rules of §2 only: V2–V5 are duties no fixture can check.

[`conformance/records.json`](conformance/records.json) holds the suite: `{id, record, valid, evidence}`, where `valid`
is whether the record is valid under the core and its extension (the same for every receiver) and `evidence` is `used`
or `ignored`: whether a verifier keeps the record's `verifiable` and `verified` or ignores them under §2.

## 7. Security considerations

- **Verification moves trust; it does not remove it.** Verifiable entries let a principal side settle more than a
  person can review, but every `valid` result rests on the trust roots being honest and independent of the requester,
  and the verifier being correct. A proof establishes only its statement (V2). The principal side's own trust policy
  (V3) is what keeps a requester from naming its own signer as a trust root.
- **Running what the requester supplies.** `proof_ref` URIs, and in Criteria check implementations and subjects, come
  from the requester. A verifier that runs or fetches them MUST do so isolated from the principal side's own state,
  credentials and proofs about the principal, and SHOULD fetch through a channel that tells the requester nothing
  about the principal.
- **Replayed and stale proofs.** A proof made for one item can be offered for another, and an old proof can be offered
  after the fact changed. Binding the proven statement to the item, freshness bounds per format, and reporting reuse
  (V3, V4) are the defences.
- **Proofs about the principal.** Selective-disclosure credentials (SD-JWT, BBS) and web proofs (zkTLS, TLSNotary) can
  disclose facts about the principal: their identity, accounts and payments. §4 keeps them with the principal side.
- **Proofs of payment** can disclose the principal's accounts and spending; §5 limits who makes them and what they may
  settle.

## 8. Changes from 0.5

None. The members and their meaning are unchanged, and the terms digest is computed as in 0.5 (core §4), so a record
converts between 0.5 and 0.6 as its extension says (Acts §6, Decisions §6); no 0.5 record lacks a 0.6 form because
of this module's members. In 0.4 this module was core §5.2 and §13.

## 9. Relation to other specifications

*Non-normative; see [RELATED-WORK.md](../RELATED-WORK.md) §7.1.*

This module borrows its proof systems instead of defining any: web proofs over TLS (TLSNotary, DECO and other "zkTLS"
systems), selective-disclosure credentials (SD-JWT, RFC 9901; BBS signatures), and signed build and test attestations
(in-toto, SLSA). `format` names them; this module records what was proven and what was checked.

## References

- Principal Handoff Core 0.6, [`../core/SPEC.md`](../core/SPEC.md).
- [RFC 3339] Klyne, G. and C. Newman, "Date and Time on the Internet: Timestamps", RFC 3339, July 2002.
- [RFC 9901] Fett, D., Yasuda, K., and B. Campbell, "Selective Disclosure for JSON Web Tokens", RFC 9901, November
  2025.
