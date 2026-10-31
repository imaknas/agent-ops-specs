# Principal Handoff: Decisions 0.4

| | |
|---|---|
| Status | Draft |
| Version | 0.4 (2026-11-01); 0.3 (2026-10-27); formerly Questions 0.1 |
| Extension | `decisions/0.4`, an extension of [Principal Handoff Core 0.4](../core/SPEC.md) |
| License | Apache-2.0 |
| Schemas | [`schemas/`](schemas/) (record schema in [`../core/schemas/`](../core/schemas/)) |
| Conformance suite | [`conformance/`](conformance/) |
| Reference | [`../reference/`](../reference/) |

## Abstract

Agents working for someone often reach a choice only that someone may make: which of two designs, whether to spend
money, what a customer was promised. The agent's session may end long before the answer comes. This extension of
Principal Handoff covers such **decisions**: how an agent raises one with options and a working assumption, how the
principal side records the principal's answer (or that no answer is needed) with the authority it was made under, how
an answer is revised, and how the answer reaches the project rather than a session that may be gone. When agents
produce more than the principal can review, a decision can also carry **acceptance criteria**: machine-checkable
checks on a pinned result. The principal approves the criteria, and a verifier on the principal side settles the
decision when every check is proven to pass, without the principal reviewing the work itself. It builds on the
[core](../core/SPEC.md) registers; work only the principal can do is the [Acts](../acts/SPEC.md) extension.

## Table of contents

1. [Conventions and terminology](#1-conventions-and-terminology)
2. [Model](#2-model)
3. [Records](#3-records)
4. [Lifecycle](#4-lifecycle)
5. [Receiving decisions](#5-receiving-decisions)
6. [Mapping from Questions 0.1 and changes from 0.3](#6-mapping-from-questions-01-and-changes-from-03)
7. [Conformance](#7-conformance)
8. [Security considerations](#8-security-considerations)
9. [Relation to the Acts extension and other
   specifications](#9-relation-to-the-acts-extension-and-other-specifications)
10. [Open issues](#10-open-issues)

## 1. Conventions and terminology

The key words in this document are to be interpreted as in the [core](../core/SPEC.md#1-conventions-and-terminology),
which also defines *principal*, *principal side*, *requester*, *delegate*, *item*, *key*, *terms*, *record*, *claim*,
*relation* and *note*. This extension adds:

**Decision**
: An item of kind `decide`: an answer or choice only the principal may make.

**Answer**
: `{"text": …, "option"?: …}`: free text, and the chosen option's id if the decision has options.

**Working assumption**
: What the requester proceeds on while the decision is open (`terms.default`). It is never an answer (core R4).

**Criteria**
: Acceptance criteria in a decision's terms (`terms.criteria`, §2.1): a pinned subject, the checks it must pass, and
the answer to record when it passes them all.

**Submission**
: A requester's note carrying verifiable entries that prove the checks' outcomes (§2.2).

## 2. Model

- **Terms:** `{"text": …, "options"?: [{"id", "label"}], "default"?: …, "due"?: "YYYY-MM-DD", "criteria"?: …}`.
  Option ids are unique within the decision. `default` is an option id or text; if it equals an option's id, it is
  that option. `criteria` is §2.1.
- **Keys** are assigned by the requester, unique among the decisions its project raises. They are not derived from
  the text: raising the same text again is a new decision.
- **Settlement outcomes:** `decided` (carries `answer`) and `dismissed` (no answer is needed; the `note` SHOULD say
  why).
- **Claim outcomes:** `decided` (carries `answer`): someone heard the principal decide, for example in the
  requester's own session.
  A submission of check results (§2.2) is never a claim: it asserts results, not that the principal decided.
- **Attested settlements:** the principal side MUST NOT settle a decision `attested` (including by adopting a claim,
  core §7) on the claimant's word alone; it uses `confirmed` once the principal has confirmed, or `attested` on
  evidence independent of the claimant. When that evidence is verifiable entries, their verified content MUST
  establish that the principal decided this decision at these terms: for example a message signed with the
  principal's credential that names the terms digest (core §5.3) and the answer. A key alone does not suffice, since
  it survives amendments. Check results never establish a decision; they authorise a settlement only through an
  approval (§4.1).
- **Withdrawal reasons:** `settled` (the decision was made where it was asked), `not_needed`, and `replaced` (the
  requester raised the same decision again under another key and sent `replaced_by` to it, core §7).
- **Withdrawn need, open settlement:** the need belongs to the requester, so the principal side MUST stop presenting
  the decision as waiting. It MAY still record a settlement (for example to keep what the principal said); such a
  settlement is delivered (§5), and the requester MAY ignore it. (Core §6.) It MUST NOT settle a withdrawn decision
  under an approval.
- **Replaced decisions:** a decision withdrawn as `replaced` is presented, if at all, together with its replacement.
  Approvals, answers and check results of the old decision do not carry over: the replacement has its own terms.
- **Approvals:** decisions take approvals (core §5.3) only of terms that carry `criteria`. Such an approval authorises
  one settlement of the decision with `criteria.answer`, made by a verifier when §4.1's conditions hold, and nothing
  else. The principal side MUST NOT record an approval of terms without criteria; one that exists is never in force
  (core §6). An approval is not an answer: the requester MUST NOT proceed on `criteria.answer` before the decision is
  settled.

### 2.1 Criteria

`terms.criteria` is an object:

| Member | Req. | Meaning |
|---|---|---|
| `subject` | yes | `{"uri", "digest"}`: what is checked (a commit, a build artefact, a document), pinned by the `sha-256:` digest of its exact content. |
| `checks` | yes | One or more checks (below), with ids unique within the criteria. |
| `answer` | yes | The answer (`{"text", "option"?}`) recorded when every check passes. If `option` is present it MUST be one of the options of these terms. As in every answer, `text` is what counts (§3); the principal side MUST show it, not only the option's label. |

A **check** is an object:

| Member | Req. | Meaning |
|---|---|---|
| `id` | yes | Unique within the criteria; same syntax as a verifiable entry's `id` (core §5.2). |
| `text` | yes | What the check establishes, in plain words for the person who approves. |
| `format` | yes | The proof format a result must come in (core §5.2). |
| `implementation` | yes | `{"uri", "digest"}`: the check's code or procedure, pinned by digest. |
| `trust` | yes | One or more trust roots (signers, notaries, issuers, in the format's own terms) whose proofs are accepted for this check. |

A check **passes** when its pinned `implementation`, run on the pinned `subject`, reports success; a proof establishes
that only if its verified content (core V3) names both digests and carries that outcome in machine-readable form.

The requester writes the criteria, as it writes all terms; the principal approves or does not. Because the terms are
the requester's:

- Before it records an approval, the principal side MUST show every result it has recorded, at any `terms_rev`, for
  this decision or any other decision of the project, including replaced ones, for a check with the same subject
  digest and implementation digest, failures in particular.
- `trust` only narrows what the principal side accepts: a result is `valid` only under a root that is both listed in
  the check and acceptable under the principal side's own trust policy (core V3), with one exception: the principal
  side's own runs (§4.1), which a check's `trust` need not list.
- The principal side's trust policy MAY list implementations it has reviewed. Before an approval, the principal side
  MUST show, for each check, whether its implementation is on that list, and which of its roots the policy accepts. If
  an implementation is not on the list, it MUST say plainly that the check means whatever the requester's code does,
  and record the approval only if the person accepts that.

Criteria change only by amendment, which lapses any approval (core §5.3).

### 2.2 Submissions

A requester submits check results with a `note` (`origin: "requester"`, from a party holding the project's requester
role) about the decision (`about.key`) that carries `terms_rev`, the terms version whose criteria it answers, and
`evidence.verifiable`, one entry per check it answers:

- the entry's `id` is the check's `id`, and its `format` is the check's `format`;
- the proof's verified content MUST name the subject's digest and the check's implementation digest and show that the
  check passed; a proof that does not is `invalid` for the check. It SHOULD also name the terms digest (core §5.3),
  but a proof that does not is not `invalid` for that reason.

Submissions are notes, not claims: they change no register and assert no outcome. Only notes from the project's
requester role are submissions; the verifier never checks verifiable entries in other parties' notes against the
criteria (its own runs, §4.1, are not submissions). A
requester MAY send several; a later one does not erase an earlier one, and every result the principal side computes
stays on record (core V5).

## 3. Records

Records use the [core record](../core/SPEC.md#4-records) with `ext: "decisions/0.4"`.

| `type` | `origin` | Schema | Additional requirements |
|---|---|---|---|
| `raised` | `requester` | [`raised`](schemas/raised.schema.json) | `terms.text`, `terms_rev: 1`; terms per [`terms`](schemas/terms.schema.json) and §2.1 |
| `amended` | `requester` | [`amended`](schemas/amended.schema.json) | `terms`, `terms_rev`; terms as for `raised` |
| `withdrawn` | `requester` | [`withdrawn`](schemas/withdrawn.schema.json) | `reason` |
| `settled` | `principal` | [`settled`](schemas/settled.schema.json) | `outcome`; `answer` when `decided`; `authority`; `terms_rev`; `terms_digest`; under an approval, §4.1 |
| `reopened` | `principal` | [`reopened`](schemas/reopened.schema.json) | `supersedes` |
| `approved` | `principal` | [`approved`](schemas/approved.schema.json) | `approval`; when granting, `terms_rev`, `authority` and `evidence.presented`; when retracting, `supersedes` (core §5.3) |
| `claimed` | `agent`, `requester` | [`claimed`](schemas/claimed.schema.json) | `outcome: "decided"`, `answer`, `evidence.basis` |
| `related` | `principal` (`same_as`), `requester` (`derived_from`, `replaced_by`) | [`related`](schemas/related.schema.json) | `relation` |
| `note` | `requester`, `principal`, `agent` | [`note`](schemas/note.schema.json) | `about`; a submission (§2.2) also `terms_rev` and `evidence.verifiable` |

Validity rules beyond the schemas: option ids are unique within the terms; criteria hold at least one check, check
ids are unique and every `trust` is non-empty, and `criteria.answer.option`, if present, is one of the options (§2.1);
`decided` carries `answer`. A settlement whose `authority.under` begins with `approval:` MUST have
`outcome: "decided"`, `terms_digest`, and `evidence.verified` with at least one result, every one `valid`; receivers
reject it otherwise. Whether these results cover every
check, whether the answer is `criteria.answer`, and whether the approval was in force are the principal side's duty
(§4.1), not conditions of validity (core V1). A receiver that holds the terms and the approval SHOULD check them and
report a mismatch, and a principal side that receives such a report presents the decision to the principal.

If `answer.option` is present, the principal side MUST make it one of the options at the `terms_rev` it records. A
receiver that finds it is not, or cannot check because it never saw the terms, MUST still accept the settlement, treat
`answer.text` as authoritative, and SHOULD report the mismatch: the principal's answer must not be lost to a
validation error.

## 4. Lifecycle

1. **Raising.** The requester sends `raised` with id `r:<key>`, so that a repeated `raised` is a duplicate of the
   first (core §10). A second `raised` for the same key under another id is a need-register conflict (core §6), which
   the principal side SHOULD report. Other record ids are any ids unique per core §10.
2. **Amending.** The requester changes the question, its options or its working assumption with `amended`, listing
   its current need record in `supersedes` and increasing `terms_rev` by one. A settlement made against older terms is
   stale (core §6).
3. **Deciding.** The principal side records `settled` with `outcome: "decided"` and an `answer`, naming the decider
   and authority kind (core §5):
   - `principal`: the principal answered.
   - `confirmed`: the principal confirmed an answer the assistant proposed.
   - `delegated`: the assistant answered under a standing instruction or mandate (`under`), without the principal,
     or a verifier settled under an approval of the decision's criteria (§4.1).
   - `attested`: the answer is taken from evidence, for example something the principal wrote elsewhere.
4. **Dismissing.** `settled` with `outcome: "dismissed"`: the principal decided no answer is needed. The requester
   MUST NOT keep waiting and SHOULD raise a new decision if the need returns.
5. **Revising.** The principal side MAY replace an earlier settlement (the principal changed their mind, or answers a
   decision they had dismissed) with a new `settled` that lists it in `supersedes`, or reopen it with `reopened`.
   Which settlement is current is defined by core §6.
6. **Withdrawing.** The requester sends `withdrawn` when it no longer needs an answer. If the principal answered in
   the requester's own session, the requester SHOULD first send a `claimed` with that answer and `evidence.basis`, so
   that the principal side can record who decided, and then withdraw with `reason: "settled"`. The principal side MAY
   adopt the claim (core §7); until it has, it SHOULD present the claim to the principal once for confirmation, even
   though the decision itself is no longer presented as waiting. A requester that replaces the decision with another
   sends `replaced_by` (core §7) and then withdraws with `reason: "replaced"`.

### 4.1 Settling by criteria

The flow for a decision with criteria:

1. The requester raises (or amends) the decision with `criteria` pinned to its result.
2. The principal side presents the terms, criteria included, and what an approval would authorise (core §9). If the
   principal approves them without conditions, it records an `approved` (core §5.3). The principal may instead answer
   the decision directly, as any other: criteria never stop the principal deciding.
3. The requester sends submissions (§2.2).
4. A verifier of the principal side checks them, and the principal side either settles under the approval or records
   the results and presents the decision to the principal.

The principal side MAY settle a decision under an approval only when all of these hold over the records it holds:

1. the approval is in force (core §6), so that the terms have not changed, nothing has retracted it, and the decision
   has had no settlement since it was granted; its `terms_rev` is the settlement's `terms_rev`, and those terms carry
   `criteria`;
2. no held claim about the decision carries an answer other than `criteria.answer` (answers are equal when their
   `text` strings are identical and their `option`s are identical or both absent), unless the principal side showed
   that claim to the principal before the approval was granted: someone may have heard the principal decide
   otherwise;
3. the verifier has checked every submission it holds at the approval's `terms_rev`, and for every check has
   obtained a `valid` result (core V3) for an entry with the
   check's `id`, in the check's `format`, in a submission (§2.2) or its own run whose `terms_rev` is the approval's,
   whose verified content names the subject's digest and the check's implementation digest and shows that the check
   passed, under a root acceptable for the check (§2.1), and fresh under its trust policy when it settles;
4. no `invalid` result has been recorded for any check of the criteria at that `terms_rev`, nor, at any `terms_rev`
   and in any decision of the project, for a check with the same subject digest and implementation digest: one
   submitted failure sends the decision to the principal, so that a requester cannot re-run a flaky check until it
   passes, nor start again by amending the terms, renaming the check or replacing the decision. Failures the requester
   never submits are not caught (core §13). (An `unsupported` result does not block: it says the verifier could not
   check, not that the check failed.)

A proof that has served another decision does not stop this one (core V4) when both decisions' approved criteria pin
the same subject and implementation for that check.

The settlement then has `outcome: "decided"`; `answer` equal to `criteria.answer`; `terms_rev` and `terms_digest`
of the approval; `authority` of kind
`delegated` with `decider` the verifier, `chain` from the principal to the verifier, and `under` as core §5.3 says;
and `evidence.verified` with exactly the `valid` results it was made on, one for every check. It carries no proof
bodies about the principal (core §5.2). Every other result the verifier computed goes on a principal-side `note` (core
V5).

Otherwise the principal side MUST NOT settle under the approval. It records every result it computed in a
principal-side `note` about the decision with `terms_rev` and `evidence.verified` (core V5), which reaches the
project, and presents the decision to the principal with the check texts, the statements and the results. If no
submission arrives, it presents the decision again as core §13 says.

The verifier is a component of the principal side. It MAY run a check's implementation itself on the subject,
isolated as core §13 requires and in an environment the requester cannot write to. It records the run as a verifiable
entry, with the check's `id`, in its own note or settlement, and refers to it in `verified`.

### 4.2 Audits

A verifier settles on what the checks establish, which may be less than what the principal wanted (core §13). The
principal side SHOULD present to the principal, for full review, a sample of the decisions it settled under
approvals, chosen so that no requester can predict which (for example drawn with a secret random source after
settling), at a rate it tells the principal and that is not zero. (The rate and the draw cannot be checked from
records; the recorded reviews can.) It records each review:

- if the principal agrees, as a `settled` that supersedes the audited one, kind `confirmed`, `evidence.proposal` the
  audited settlement's id, with the same answer and the audited settlement's `terms_rev`; if the terms have changed
  since, the principal decides on the current terms instead;
- if not, as a `reopened`, or a `settled` with the principal's own answer, superseding it.

Either way the approval stays used: it never settles the decision again (core §5.3). The principal side SHOULD raise
the sampling rate for a project whose audits find wrong settlements, and MAY stop settling that project's decisions
under approvals. A requester that receives a superseding settlement with the same answer has nothing to redo.

## 5. Receiving decisions

- The principal side MUST deliver every settlement to the requester's **project** (core §8), not only to the session
  that asked, which may no longer exist.
- The requester applies a decision by judgement: it decides what in the project changes. Implementations MUST NOT
  apply answers mechanically to documents.
- When a settlement supersedes one the project already acted on, or is stale, the project SHOULD review what it did on
  the earlier answer.
- A settlement under an approval may be reopened by an audit (§4.2). Requesters SHOULD keep work that rests on one
  revisable until the decision is confirmed or the project has accepted that risk.
- While a decision is open, the requester MAY proceed on its working assumption, and MUST be ready to revise its work
  when the answer differs.
- An answer that requires work only the principal can do becomes an act under the Acts extension: the requester
  raises it with a `derived_from` relation to the decision.

## 6. Mapping from Questions 0.1 and changes from 0.3

| Questions 0.1 event | Decisions 0.4 record |
|---|---|
| `asked` | `raised`, `terms` from `text`, `options`, `default`, `due`; `terms_rev: 1` |
| `answered`, `decided_by: principal` | `settled`, `outcome: "decided"`, `authority.kind: "principal"` |
| `answered`, `decided_by: assistant` | `settled`, `outcome: "decided"`, `authority.kind: "attested"` with `evidence.basis` naming the 0.1 event, unless the mandate is known, then `"delegated"` with `under` and `chain` |
| `dismissed` | `settled`, `outcome: "dismissed"`, with the authority kind of the 0.1 event as above |
| `supersedes` (one id) | `supersedes` (array) |
| `withdrawn`, `reason: settled` | `claimed` with the answer, then `withdrawn`, `reason: "settled"` |
| `withdrawn`, `reason: not_needed` | `withdrawn`, `reason: "not_needed"` |

Changes from 0.3: `ext` is `decisions/0.4` and records carry `ph: "0.4"`; settlements carry `terms_digest`; terms may
carry `criteria` (§2.1); the `approved` record (core §5.3) and settlement under an approval (§4.1) with audits (§4.2);
submissions (§2.2); the withdrawal reason `replaced`. A 0.3 record is converted by changing `ph` and `ext` and, on
`settled`, adding `terms_digest` computed over the converted need record at the settlement's `terms_rev`; nothing else
changes meaning.

## 7. Conformance

### 7.1 Conformance classes

- A **conforming requester** follows core §12, assigns keys unique within its project, submits check results only as
  §2.2 says, and applies settlements as in §5.
- A **conforming principal side** follows core §12, §3's option rule, the withdrawn-need, attested-settlement and
  approval rules of §2, §2.1's duties before an approval, and §4.1 for every settlement under an approval; it SHOULD
  audit as §4.2 says.

### 7.2 Conformance suite

[`conformance/`](conformance/) holds JSON fixtures; its [README](conformance/README.md) documents the formats.

| File | Exercises |
|---|---|
| `records.json` | §2.1, §3 and core §4–§5: record → schema it validates against, or invalid |
| `lifecycle.json` | core §6 and §4 here: the records one receiver holds for one decision (with duplicates, reordering, revisions, forks, ties, cycles, withdrawals, stale terms, approvals granted, lapsed and retracted, settlements under approvals, audits and invalid records) → the decision's state and approval in force |

The core's [terms-digest vectors](../core/conformance/terms-digest.json) apply to every implementation that records
or checks approvals.

## 8. Security considerations

The [core considerations](../core/SPEC.md#13-security-and-privacy-considerations) apply. In addition:

- **Answers steer work.** A forged settlement steers a project. Receivers MUST accept settlements only from the
  principal side.
- **Answers by an assistant** (`delegated`, `attested`) let routine decisions be made without interrupting the
  principal. Requesters SHOULD treat them as revisable and MAY raise a new decision when the stakes are high.
- **Options and working assumptions are untrusted text** like the question itself, and MUST be rendered inertly.
- **Criteria are written by the requester.** An approval is only as good as what the person approved: a check whose
  `text` promises more than its `implementation` does, a subject that is not what the person thinks, or a trust root
  the requester controls. The principal side SHOULD show, next to each check, which of its trust roots it accepts, and
  SHOULD warn when a check's roots are unknown to its trust policy. Settling under an approval moves trust to the
  criteria, the check implementations, the trust roots and the verifier; it does not remove it (core §13), which is
  why §4.2 audits a sample.
- **Gaming the checks.** A requester can pass every check and still miss what the principal meant. Checks that are
  cheap to satisfy without doing the work are the risk; audits (§4.2) are the measure of how often it happens.

## 9. Relation to the Acts extension and other specifications

*Non-normative.*

- **Acts** settle mechanically through a document and are reopened when they were not really done; decisions are
  applied by judgement and revised when the principal changes their mind. A withdrawn act stays open until the
  principal settles it; a withdrawn decision stops being presented. An Acts `undecided` line is a decision nobody has
  raised yet.
- **MCP elicitation** asks the client's user inside one request; its `default` only pre-fills a form, which matches
  the working assumption here. A principal side can expose "ask the principal" as an MCP tool that sends `raised`.
- **CHAP's whisper** profile applies `default_if_lapsed` when no answer arrives. This extension deliberately does not:
  a working assumption never becomes an answer (core R4).
- **A2A `input-required`** pauses one task until its client answers, and does not record who answered. A decision
  raised while answering an inquiry from the principal (core §15) carries `derived_from` with the inquiry's `uri`.
- **Proof-carrying code, debate and prover-verifier games** are the research lineage of §4.1: the person sets the
  policy, a cheap checker checks a proof, and the result is only as good as the policy (see
  [RELATED-WORK.md](../RELATED-WORK.md) §7).

## 10. Open issues

- **Markdown binding.** Decisions are records only; some deployments also list open decisions in the state document.
  A binding for that is not specified.
- **Rich answers.** `answer` is text plus an option id. Structured answers (numbers, dates, files) are not specified.
- **Transport bindings** are not defined yet (core §10).
- **Approvals across decisions.** An approval covers one decision's terms at one `terms_rev`. Approving one set of
  criteria for a series of decisions (for example every release of a project) would be a standing mandate, which this
  family leaves to other systems (core §15).

## References

- Principal Handoff Core 0.4, [`../core/SPEC.md`](../core/SPEC.md).
