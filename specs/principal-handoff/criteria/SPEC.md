# Principal Handoff: Criteria 0.6

| | |
|---|---|
| Status | Experimental (no implementation besides the reference code); wire content frozen in the release candidate (core §14) |
| Version | 0.6 (2026-11-04); 0.5 (2026-11-01); in core 0.4 §5.3 and Decisions 0.4 §2.1–§4.2 |
| Module | of [Principal Handoff: Decisions 0.6](../decisions/SPEC.md) (`decisions/0.6`); requires [Evidence 0.6](../evidence/SPEC.md) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) (record schema in [`../core/schemas/`](../core/schemas/)) |
| Conformance suite | [`conformance/`](conformance/) |
| Reference | [`../reference/`](../reference/) |

## Abstract

When agents produce more than the principal can review, a decision can carry **acceptance criteria**:
machine-checkable checks on a pinned result. The principal approves the criteria, and a verifier on the principal
side settles the decision when every check is proven to pass, without the principal reviewing the work itself. This
module defines the criteria, the requester's **submissions** of check results, the principal's **approval**, the only
mandate this family records, and when a verifier may settle under it. Like every module (core §11), it never changes
whether a record is valid or what state an item is in: to a receiver that does not implement it, the `under` of a
settlement made under an approval is opaque, like any other mandate reference.

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [Criteria](#2-criteria)
3. [Submissions](#3-submissions)
4. [Approvals](#4-approvals)
5. [Settling by criteria](#5-settling-by-criteria)
6. [Audits](#6-audits)
7. [Records](#7-records)
8. [Conformance](#8-conformance)
9. [Security considerations](#9-security-considerations)
10. [Changes from 0.5](#10-changes-from-05)
11. [Relation to other specifications](#11-relation-to-other-specifications)
12. [Open issues](#12-open-issues)

## 1. Conventions and terminology

The key words in this document are to be interpreted as in the [core](../core/SPEC.md#1-conventions-and-terminology).
Terms of the core, of [Decisions](../decisions/SPEC.md) (*decision*, *answer*) and of
[Evidence](../evidence/SPEC.md) (*verifiable entry*, *verification result*, *trust policy*, *trust root*, *verifier*)
apply. This module adds:

**Criteria**
: Acceptance criteria in a decision's terms (`terms.criteria`, §2): a pinned subject, the checks it must pass, and the
answer to record when it passes them all.

**Submission**
: A requester's note carrying verifiable entries that prove the checks' outcomes (§3).

**Approval**
: The principal's approval of a decision's terms exactly as they stand at one `terms_rev`, recorded by the principal
side in an `approved` record (§4). It is a mandate (core §1) for one settlement of that decision.

## 2. Criteria

`terms.criteria` is an object ([`schemas/criteria.schema.json`](schemas/criteria.schema.json)):

| Member | Req. | Meaning |
|---|---|---|
| `subject` | yes | `{"uri", "digest"}`: what is checked (a commit, a build artefact, a document), pinned by the `sha-256:` digest of its exact content. |
| `checks` | yes | One or more checks (below), with ids unique within the criteria. |
| `answer` | yes | The answer (`{"text", "option"?}`) recorded when every check passes. If `option` is present it MUST be one of the options of these terms. As in every answer, `text` is what counts (Decisions §3); the principal side MUST show it, not only the option's label. |

A **check** is an object:

| Member | Req. | Meaning |
|---|---|---|
| `id` | yes | Unique within the criteria; same syntax as a verifiable entry's `id`. |
| `text` | yes | What the check establishes, in plain words for the person who approves. |
| `format` | yes | The proof format a result must come in. |
| `implementation` | yes | `{"uri", "digest"}`: the check's code or procedure, pinned by digest. |
| `trust` | yes | One or more trust roots (signers, notaries, issuers, in the format's own terms) whose proofs are accepted for this check. |

A check **passes** when its pinned `implementation`, run on the pinned `subject`, reports success; a proof establishes
that only if its verified content (Evidence V3) names both digests and carries that outcome in machine-readable form.

**Structural rules** (core §11): `terms.criteria` validates against the schema; it holds at least one check; check ids
are unique; every `trust` is non-empty; `answer.option`, if present, is one of the options of these terms. Criteria
that break one are not criteria to this module: no approval of such terms is ever in force (§4). The decision itself,
and its terms digest (core §4), are unaffected: `criteria` is a member of the terms like any other.

The requester writes the criteria, as it writes all terms; the principal approves or does not. Because the terms are
the requester's, the principal side has these duties:

- Before it records an approval, the principal side MUST show every result it has recorded, at any `terms_rev`, for
  this decision or any other decision of the project, including replaced ones, for a check with the same subject
  digest and implementation digest, failures in particular.
- `trust` only narrows what the principal side accepts: a result is `valid` only under a root that is both listed in
  the check and acceptable under the principal side's own trust policy (Evidence V3), with one exception: the
  principal side's own runs (§5), which a check's `trust` need not list.
- The principal side's trust policy MAY list implementations it has reviewed. Before an approval, the principal side
  MUST show, for each check, whether its implementation is on that list, and which of its roots the policy accepts. If
  an implementation is not on the list, it MUST say plainly that the check means whatever the requester's code does,
  and record the approval only if the person accepts that.

Criteria change only by amendment, which lapses any approval (§4).

## 3. Submissions

A requester submits check results with a `note` (`origin: "requester"`, from a party holding the project's requester
role) about the decision (`about.key`) that carries `terms_rev`, the terms version whose criteria it answers, and
`evidence.verifiable`, one entry per check it answers:

- the entry's `id` is the check's `id`, and its `format` is the check's `format`;
- the proof's verified content MUST name the subject's digest and the check's implementation digest and show that the
  check passed; a proof that does not is `invalid` for the check. It SHOULD also name the terms digest (core §4), but
  a proof that does not is not `invalid` for that reason.

Submissions are notes, not claims: they change no register and assert no outcome. Only notes from the project's
requester role are submissions; the verifier never checks verifiable entries in other parties' notes against the
criteria (its own runs, §5, are not submissions). A requester MAY send several; a later one does not erase an earlier
one, and every result the principal side computes stays on record (Evidence V5). A principal side that does not
implement this module reads a submission as any other note (core §11).

## 4. Approvals

An approval authorises at most one settlement of the decision, with `criteria.answer`, made by a verifier when §5's
conditions hold, and nothing else. It is not a settlement and not an answer: the requester MUST NOT proceed on
`criteria.answer` before the decision is settled.

**Recording.** The principal side records an approval as an `approved` record about the decision:

| Member | Req. | Meaning |
|---|---|---|
| `approval` | yes | `{"active", "terms_digest"?, "after"?}`. `active`: `true` grants an approval; `false` retracts the approvals listed in `supersedes`. `terms_digest`: REQUIRED when granting, and only then: the terms digest (core §4) of the need record at `terms_rev`. `after`: on a grant, the id of the current settlement-register record of the decision when the grant was made; absent if the principal side held none. |
| `terms_rev` | when granting | The terms version approved. |
| `authority` | when granting | Core §5.1, of kind `principal` (the person approved the terms as presented) or `confirmed` (the person confirmed a delegate's recommendation to approve; `evidence.proposal` identifies it). Never `delegated` or `attested`. |
| `evidence` | when granting | `presented` is REQUIRED and covers the terms at `terms_rev` with everything in them, criteria included. |
| `supersedes` | when retracting | The approvals retracted. |

A grant MUST NOT carry `adopts`. The principal side MUST NOT record a grant for terms without criteria that follow §2,
nor while the decision's settlement register has a conflict (core §6). Core §9 applies to it, and before an
approval the principal side MUST also make clear what it authorises: that a verifier may settle the decision without
the person seeing the result, on what conditions, and for these terms only. The principal side MUST NOT approve terms
containing members it does not show the person. It approves the terms as they stand, without conditions: if the person
attaches any condition, reservation or limit, the principal side MUST NOT record an approval; it MAY send a `note`
asking the requester to amend the terms so that they carry it. A `note` on an `approved` record is never part of what
was approved. A new grant for a `terms_rev` that already has a grant MUST list the earlier grants in `supersedes`.

A retraction (`active: false`) needs no `authority`: the principal side may always narrow what it has authorised, at
any time (for example once `terms.due` has passed). `supersedes` on an `approved` takes effect only on `approved`
records of the same decision; other ids in it are ignored and SHOULD be reported. A retracted approval is never in
force again: re-approving is a new grant.

**Binding.** An approval binds (`ext` name, `project`, `key`, `terms_rev`, terms digest). It authorises nothing for
any other item, project or terms version, and nothing transfers it: no relation (core §7), claim, note or record of
another item. In particular, a decision replaced by another (`replaced_by`) passes on neither its approvals nor its
check results.

**In force.** Only the principal side computes which approval is in force; no other role needs to. Over the records
it holds (core §6), a grant (an `approved` with `approval.active: true` that follows this module's structural rules)
is **in force** when all of these hold:

1. no held `approved` record about the decision lists it in `supersedes`;
2. the need register has no conflict, and its current record is a `raised` or `amended` (not `withdrawn`) whose
   `terms_rev` equals the grant's `terms_rev`, is the highest `terms_rev` held, whose terms digest equals
   `approval.terms_digest`, and whose terms carry criteria that follow §2;
3. no other held `raised` or `amended` with that `terms_rev` has a different terms digest;
4. no held `settled` about the decision names it in `authority.under`; and, where A is the set made of the `settled`
   or `reopened` that `approval.after` names, if it is held, and of every settlement-register record reached from it
   by following `supersedes` again and again (A is empty without `after`), every held `settled` or `reopened` about
   the decision is in A. Both parts count every such record, whether or not it follows this module's rules.

If several grants are in force, the decision's approval is the one with the latest `ts`, equal `ts` broken by the
greater `id`. Like the state, this depends only on the records held, not on their order, their clocks or anything
checked outside them. In short, an approval lapses when the terms change in any way, when it is retracted, and once
the decision has any settlement-register record the grant was not made over (a settlement under the approval, or one
the principal or another principal-side implementation made by hand, later reopened or not), so that it is used at
most once and a principal who has settled or reopened the decision by hand is never overridden by it once the
implementation that holds approvals has received that settlement or reopening.

**One approval store.** Where more than one implementation acts as the principal side, they MUST either share one
store of approvals, retractions and settlements, in which using an approval is one atomic check-and-mark (so that two
of them cannot both use it), or leave approvals to one of them alone. In the second case the deployment MUST have
every other implementation deliver each settlement-register record it makes to the one that holds approvals (the
transport accepting it, core §10) before it reports the record to the person as made; this is what core §6 recommends
for every deployment, made a condition of using approvals.

**Delivery.** The principal side MUST deliver every `approved` record to the decision's project (core §8), so that a
requester can see what was approved and check the settlement made under it.

**After a retraction.** A retraction, or a lapse, never changes a settlement already made: state is computed from the
registers (core §6). When an approval is retracted, the principal side MUST present every current settlement made
under it to the principal, who either confirms it (a `settled` that supersedes it, kind `confirmed`,
`evidence.proposal` its id) or replaces or reopens it. A lapse through amendment needs nothing further: the settlement
is stale (core §6).

## 5. Settling by criteria

The flow for a decision with criteria:

1. The requester raises (or amends) the decision with `criteria` pinned to its result.
2. The principal side presents the terms, criteria included, and what an approval would authorise (§4). If the
   principal approves them without conditions, it records an `approved`. The principal may instead answer the
   decision directly, as any other: criteria never stop the principal deciding.
3. The requester sends submissions (§3).
4. A verifier of the principal side checks them, and the principal side either settles under the approval or records
   the results and presents the decision to the principal.

The principal side MAY settle a decision under an approval only when all of these hold over the records it holds:

1. the approval is in force (§4); its `terms_rev` is the settlement's `terms_rev`;
2. no held claim about the decision carries an answer other than `criteria.answer` (answers are equal when their
   `text` strings are identical and their `option`s are identical or both absent), unless the principal side showed
   that claim to the principal before the approval was granted: someone may have heard the principal decide
   otherwise;
3. the verifier has checked every submission it holds at the approval's `terms_rev`, and for every check has obtained
   a `valid` result (Evidence V3) for an entry with the check's `id`, in the check's `format`, in a submission (§3) or
   its own run whose `terms_rev` is the approval's, whose verified content names the subject's digest and the check's
   implementation digest and shows that the check passed, under a root acceptable for the check (§2), and fresh under
   its trust policy when it settles;
4. no `invalid` result has been recorded for any check of the criteria at that `terms_rev`, nor, at any `terms_rev`
   and in any decision of the project, for a check with the same subject digest and implementation digest: one
   submitted failure sends the decision to the principal, so that a requester cannot re-run a flaky check until it
   passes, nor start again by amending the terms, renaming the check or replacing the decision. Failures the requester
   never submits are not caught (§9). (An `unsupported` result does not block: it says the verifier could not check,
   not that the check failed.)

A proof that has served another decision does not stop this one (the exception Evidence V4 allows) when both
decisions' approved criteria pin the same subject and implementation for that check.

The settlement then has `outcome: "decided"`; `answer` equal to `criteria.answer`; the approval's `terms_rev` and
`terms_digest`; `authority` of kind `delegated` with `decider` the verifier, `chain` from the principal to the
verifier, and `under` equal to `approval:` followed by the `id` of the `approved` record (everything after the prefix
is the id, looked up among the principal side's `approved` records of the settlement's own `ext` name and
`project`); and
`evidence.verified` with exactly the `valid` results it was made on, one for every check. The `by` of such a
settlement is still the principal side. It carries no proof bodies about the principal (Evidence §4). Every other
result the verifier computed goes on a principal-side `note` (Evidence V5).

Otherwise the principal side MUST NOT settle under the approval. It records every result it computed in a
principal-side `note` about the decision with `terms_rev` and `evidence.verified` (Evidence V5), which reaches the
project, and presents the decision to the principal with the check texts, the statements and the results. An approved
decision whose requester never submits stays unsettled; the principal side SHOULD present it to the principal again at
its due date, or after a period it tells the principal, rather than keep it out of view.

The verifier is a component of the principal side. It MAY run a check's implementation itself on the subject,
isolated as Evidence §7 requires and in an environment the requester cannot write to. It records the run as a
verifiable entry, with the check's `id`, in its own note or settlement, and refers to it in `verified`.

A settlement under an approval covers only its own decision; decisions related to it by `same_as` stay open until
they are settled on their own authority (core §7).

## 6. Audits

A verifier settles on what the checks establish, which may be less than what the principal wanted (§9). The principal
side SHOULD present to the principal, for full review, a sample of the decisions it settled under approvals, chosen so
that no requester can predict which (for example drawn with a secret random source after settling), at a rate it tells
the principal and that is not zero. (The rate and the draw cannot be checked from records; the recorded reviews can.)
It records each review:

- if the principal agrees, as a `settled` that supersedes the audited one, kind `confirmed`, `evidence.proposal` the
  audited settlement's id, with the same answer and the audited settlement's `terms_rev`; if the terms have changed
  since, the principal decides on the current terms instead;
- if not, as a `reopened`, or a `settled` with the principal's own answer, superseding it.

Either way the approval stays used: it never settles the decision again (§4). The principal side SHOULD raise the
sampling rate for a project whose audits find wrong settlements, and MAY stop settling that project's decisions under
approvals. A requester that receives a superseding settlement with the same answer has nothing to redo; requesters
SHOULD keep work that rests on a settlement under an approval revisable until the decision is confirmed or the project
has accepted that risk.

## 7. Records

| Record | Module content | Structural rules |
|---|---|---|
| `approved` (`origin: "principal"`, schema [`approved`](schemas/approved.schema.json)) | the whole record | `approval`; when granting, `terms_rev`, `approval.terms_digest`, `authority` of kind `principal` or `confirmed` that follows core §5.1 as a settlement's would, and `evidence.presented`, no `adopts`; when retracting, `supersedes` and neither `approval.terms_digest` nor `approval.after` |
| `settled` whose `authority.under` begins with `approval:` | its reading as a settlement made under the approval the id after the prefix names | the id after the prefix is not empty; `authority.kind` is `delegated`; `outcome` is `decided`; `evidence.verified`, as Evidence leaves it (Evidence §2), holds at least one result and every one is `valid` |
| `raised`, `amended` | `terms.criteria` | §2 |

Decisions §3 lists `approved` as a pair of this module. Core checks (the record schema, the pair, `ts`, R6, the
sender's role) apply to it as to any record; an `approved` that fails one is invalid. A record that passes them but
breaks a structural rule above keeps its validity (Decisions §3 decides it) and the decision's state is what core §6
says; this module ignores its module content and a receiver that implements the module SHOULD report it. A settlement
whose reading is ignored this way is not a settlement under the approval, but it still counts for §4's condition 4,
like any settlement-register record. A requester reports a breach with a `note` about the decision; a principal side
that receives a report of such a settlement presents the
decision to the principal. Whether a settlement's results cover every check, whether its answer is `criteria.answer`
and whether the approval was in force are the principal side's duties (§4, §5), not structural rules: a receiver that
holds the terms and the approval MAY check them and SHOULD report a mismatch.

## 8. Conformance

- A **conforming requester** for this module writes criteria as §2 says, sends submissions only as §3 says, does not
  proceed on an approval (§4), and applies settlements as Decisions §5 and §6 of this module say. It computes nothing
  about approvals; it MAY check settlements that name an approval against §7 and report a breach.
- A **conforming principal side** for this module implements [Evidence](../evidence/SPEC.md) as a verifier, records
  approvals as §4 says, computes the approval in force, settles under an approval only as §5 says, and SHOULD audit as
  §6 says.

[`conformance/`](conformance/) holds the suite; its [README](conformance/README.md) documents the formats.

| File | Exercises |
|---|---|
| `records.json` | §2, §7: record → whether it is valid under the core and Decisions (the same for every receiver), and whether this module uses its content or ignores and reports it |
| `lifecycle.json` | §4: the records a principal side holds for one decision (grants, lapses, retractions, settlements under approvals, audits) → the decision's state and the approval in force |

## 9. Security considerations

The [core](../core/SPEC.md#13-security-and-privacy-considerations) and
[Evidence](../evidence/SPEC.md#7-security-considerations) considerations apply. In addition:

- **Approvals are authority.** A forged or replayed approval lets a verifier settle without the principal. Approvals
  are bound to one decision and one terms version and authorise one settlement (§4). Until a deployment profile
  specifies `evidence.proof` (core §15), an approval is as trustworthy as the authenticated principal side that
  records it.
- **Criteria are written by the requester.** An approval is only as good as what the person approved: a check whose
  `text` promises more than its `implementation` does, a subject that is not what the person thinks, or a trust root
  the requester controls. The principal side SHOULD show, next to each check, which of its trust roots it accepts, and
  SHOULD warn when a check's roots are unknown to its trust policy.
- **Checked is not reviewed.** Beyond what Evidence §7 says of verification, a verifiable target invites optimising
  for the check: a
  requester can pass every check and still miss what the principal meant, and checks that are cheap to satisfy
  without doing the work are the risk. A requester that runs checks on infrastructure it controls can run them until
  they pass and submit only the passing run: unless every run is logged where the principal side can see it, or the
  principal side runs the check itself, a recorded failure catches only the failures the requester chose to send.
  Audits (§6) are the measure of how often it happens.

## 10. Changes from 0.5

None to the rules; "held" (§4) has core §6's definition. Conversion between 0.5 and 0.6 changes `ph` and `ext` as
Decisions §6 says and nothing else: the terms digest is computed as in 0.5 (core §4), so `approval.terms_digest` is
kept. In 0.4 this module was core §5.3, the approval fold of core §6, and Decisions §2.1–§2.2 and §4.1–§4.2.

## 11. Relation to other specifications

*Non-normative; see [RELATED-WORK.md](../RELATED-WORK.md) §7.2.*

Approvals apply an idea from scalable-oversight research: when a person cannot check the work, they decide what a
cheap, trusted check must establish, as in proof-carrying code (the consumer sets a safety policy and checks a proof
instead of the code), AI safety via debate and prover-verifier games. As there, the check is only as good as the
policy and the verifier (§9).

## 12. Open issues

- **Approvals across decisions.** An approval covers one decision's terms at one `terms_rev`. Approving one set of
  criteria for a series of decisions (for example every release of a project) would be a standing mandate, which this
  family leaves to other systems (core §15); it would reduce how often the principal is asked, not only how deeply.
- **Expiry.** An approval stays in force until it lapses or is retracted (§4); it has no expiry of its own. The
  principal side can retract at any time, for example once `terms.due` has passed.

## References

- Principal Handoff Core 0.6, [`../core/SPEC.md`](../core/SPEC.md); Decisions 0.6,
  [`../decisions/SPEC.md`](../decisions/SPEC.md); Evidence 0.6, [`../evidence/SPEC.md`](../evidence/SPEC.md).
- Necula, G. C., "Proof-Carrying Code", POPL 1997.
- Irving, G., Christiano, P., and D. Amodei, "AI safety via debate", arXiv:1805.00899, 2018.
- Kirchner, J. H., et al., "Prover-Verifier Games improve legibility of LLM outputs", arXiv:2407.13692, 2024.
