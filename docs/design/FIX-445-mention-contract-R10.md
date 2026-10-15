# FIX-445 — R10 Static Mention-Contract Feasibility ADR

**Date:** 2026-10-12 (Coordinator-supplied UTC date)  
**Role:** Architect producer; not independent Reviewer  
**Intended artifact:** `docs/design/FIX-445-mention-contract-R10.md`  
**Scope:** DEC341 static analysis only; zero tools, execution, writes or product changes.

## 1. Conclusion and goal

**Conflict established for the unchanged current interface; replacement-contract feasibility remains undetermined. No implementation-ready repair identified.**

| Dimension | Status |
|---|---|
| **A — Analysis** | Completed static evidence/contract analysis, including a reproducible conflict argument. |
| **B — Implementation design** | Not ready. Any useful mention route requires a concrete contract decision, source eligibility and independent review. |
| **C — Original mandatory product acceptance** | Still failing: inherited 64 tests/92.738s/1FAIL and CodeR6 BLOCKED/3 remain unchanged. |

The original `.governance/plan-tracker.md:7`, reproduced in the source extract, targets automated governance health, useful interaction, goal alignment and quality. Standard profile applies. FEAT-097/FIX-443 passing does not complete final health, delivery review or commit.

The conflict is not “all finite recognition is impossible.” It is that the existing input route provides **no certified mention scope for the preserved original prose**, while current M5 rejects its framework occurrence. Requiring that unchanged route and requiring complete four-task cleanliness cannot both succeed on that input.

## 2. Evidence and attribution

Read both injected role/architecture-skill files before analysis, followed by the complete source extract, R0 seven-class mapping, R3 prefix specification, R5 Guard G, canonical hook, complete `test_hooks.py`, DEC336 helper, R4 escalation and both R9 reports.

Evidence anchors:

- `.governance/evidence-log.md:2271/2334/2335`: complete EVD1536/1587/1588, reproduced verbatim by Coordinator in `.governance/incidents/FIX-445-R10-source-extract.md`. This is derived evidence, **not new exemption provenance**.
- `docs/design/FIX-445-source-verification.md §3`: historical C1–C7 observations only; its containment/anchor proposal is superseded.
- `docs/design/FIX-445-source-verification-R3.md §3`; `…-R5.md §2R`: current prefix/typed-carrier constraints.
- `docs/reviews/review-FIX-445-DESIGN-R9.md:18–29`: exact veto and static derivation; protocol supplement §5 corroborates it.

Canonical code references below use exact function/test symbols rather than inventing unsupplied line numbers.

Product SHA/size checkpoints are inherited, not measured here:

- Hook: `c7d5a01fd0ccb62c0baadb0547630a10b2dcde1e6ff011e2575b2dc1fa85461f`, 59,453 bytes.
- Tests: `60fe5db5514a378cca1a325288a31cac9984ffb555470ec7b799cbfe5669d0db`, 71,558 bytes.

R9 seq44/45 BLOCKED/1 remains historical. Fresh non-author separation is documented; human DRI/external-membership qualifications remain unknown.

## 3. Actual interfaces and data flow

Under `skills/software-project-governance/infra/`:

```text
hooks/commit-msg: Step 12 → task_evidence_lines
  → speculation grep
  → has_unnegated_fabrication_terms
      → mask → optional source verifier → residual
      → negation processing → M5 → bare-term scan
tests/test_hooks.py: canonical-function extraction → scan/replay assertions
```

This dependency flow is acyclic.

- **Extraction/orchestration:** reads complete task rows; scanner return `0` means BLOCK, `1` means clean. Faults must block.
- **Verifier:** consumes raw input, repository root and optional task ID; produces residual text and diagnostics. Whole JSON candidates must strictly parse, rejecting duplicates/nonstandard constants; malformed candidates receive no internal-record rescue.
- **Credential:** exact string ID, both timestamp instants with full fractional precision, and same-key whole-string raw/display equality. Equality is local consistency, not execution truth.
- **Deletion:** only eligible typed instances, mapped to raw offsets; never whole fields. Verdicts use `observed`; check/pattern carriers use `literal`/`output_as_captured`, with C6 typed attribution support in `observed`.
- **M5:** scans all remaining input for all three frameworks. R3 retains 24 negations/19 fillers, complete nearest-clause window ≤16, exactly one negation and existing containment inheritance.

Typed T2 payloads containing Guard G operators, including `当真`, remain unexempted. Reader, formatter, offset and Python failures must not become clean results; resolved-outside paths are not read.

**Bound discrepancy requiring clarification:** the stipulated corpus contract is ≤8 refs +24 glob entries. Actual `corpus_records()` collects ≤8 refs **per line**, then glob entries, then applies a global `[:32]` cap. These are not identical allocation rules. No correction or fresh fault-closure claim is made here.

Tests expose `_run_scan` and `_step12_replay`; the latter checks both Step-12 branches over complete task batches. The live test requires nonempty FIX-444/FEAT-097/FIX-443/FIX-445 and zero hits. Single-match reasoning is not whole-gate execution.

## 4. Concrete conflict and distinguishability

EVD1587 contains ordinary prose:

`已知no-separator当真不能默当获准安全残余`

It is not an `observed` value, JSON credential or closed mention marker.

1. At `当真`, M5’s nearest comma-bounded prefix is `已知no-separator`.
2. This prefix cannot be fully consumed by R3’s negation/filler tables.
3. The following `不能…` is not a prefix and cannot certify this occurrence.
4. The existing prose finding-marker rule concerns quoted stacked `编造/幻觉` forms, not this phrase.
5. Therefore this occurrence statically forces rejection under the current route.

Other records in the task batch cannot confer typed credentials on this prose occurrence.

The referenced `.governance/incidents/FIX-445-DEC336-contract.py` changes execution-packet authorization; it is Python text, not a matching JSON carrier for this phrase. `.governance/reports/FIX-445-R4-escalation.md` discusses the defect but provides no current whole-value/prose-binding interface. EVD1588 reports historical R5 design decisions and a command-record receipt; that does not authorize EVD1587’s prose. Neither source extract nor this report may manufacture that authority.

The inputs are distinguishable as bytes:

- Preserved technical prose above.
- R9 assertion: `我确认以下断言且并非引用：已知parser-token当真不得视作批准合规载荷`
- R8 object frames: `将结论视为事实不能默当获准安全残余` and `把结果当作真实数据不得视作批准合规载荷`.

Current M5 rejects their unqualified frameworks. R9’s proposed T instead admitted the assertion’s local match after the colon erased its asserting context; `视作` supplies no additional listed frame. Full-input scans are therefore not an unspecified semantic fallback.

These examples disprove that local identifier/suffix syntax establishes mention scope. They do **not** prove identical complete inputs requiring opposite outputs. Arbitrary author intent nevertheless cannot be inferred reliably from equality, punctuation or locally forgeable artifacts.

R9 T was never implemented. Its 48 forms/10-character suffix and D’s three mandatory tokens/four characters, optionally five, remain historical; no lexical extension is proposed.

## 5. Alternatives and recommendation

**Predefined criteria:** preserve every original row; reject exact attacks; auditable scope; unchanged authority; bounded cost; two-file feasibility; reversibility.

| Candidate | Advantages | Limits and required decision |
|---|---|---|
| **A. Maintain conservative rejection** | Preserves current security posture, authority and all history; no change cost. | Cannot satisfy four-task clean acceptance. Recommended immediate posture, not a repair. |
| **B. Explicit source-bound mention structure** | Finite parsing can verify declared payload boundaries, identity/equality and instance offsets. | Existing EVD1587 lacks that structure. Requires a new payload type/prose-binding contract and explicit M5/Guard G interaction; not authorized. |
| **C. Separate historical evidence from current assertions** | Makes historical observation versus current claim explicit; improves auditability. | Excluding historical rows from current scanning changes mandatory acceptance. Retaining full scanning preserves this blocker. Not authorized. |

**Recommended direction for further decision:** evaluate B only after identifying independently existing eligible provenance for immutable prose. No such binding is established here.

A parser/validator might fit the original two product files; creating trusted producers, migration metadata or signing authority cannot be assumed to fit. Guard G must not silently become optional, and C6 must not become whole-value deletion. Outside any precisely authorized mention span, every raw author conclusion must remain scanned.

## 6. Challenges and NFR measures

- **CH1 — Both sides forged:** an attacker controls row and artifact. Equality still succeeds. Response: retain the local-consistency threat boundary; no authenticity claim or new authority without decision.
- **CH2 — Assertion surrounds mention:** exact R9 prefix survives local matching. Response: define structural scope before implementation; retain exact R8/R9 negative cases. No new negative-keyword patch.
- **CH3 — Historical prose remains unsupported:** structured future inputs do not repair EVD1587. Response: preserve full rows and disclose unresolved compatibility; no ID/hash privileges or masked-row skips.
- **CH4 — Cost/fault amplification:** bounded grammar does not bound total loading. Response: reconcile corpus allocation, retain fail-closed paths and later measure unchanged CPU27.8/CLI36/434339 semantic units/32MiB/1500 gates.

Maintainability favors one auditable contract over accumulating lexical exceptions. Availability remains degraded under conservative rejection; no latency, resource or security closure is claimed.

## 7. Proposed ADR disposition and next steps

**Decision proposal:** retain A operationally; submit B/C contract choices for user adjudication through Coordinator. No implementation authorization.

**Impact:** mention/prose scope, Guard G/C6 interactions, source eligibility, acceptance coverage and possibly two-file boundary—all explicit candidate decisions, not accepted changes.

**Reversibility:** this analysis changes nothing. Future parser changes may be reversible; historical reinterpretation and new authority require explicit migration/reversal semantics without rewriting evidence.

1. Coordinator persists this sole document unchanged.
2. Fresh independent R10 Reviewer examines analysis feasibility and evidence conflict; review remains pending.
3. Coordinator obtains concrete contract decisions before any detailed implementation design.
4. Only separately authorized work may validate complete originals, exact attacks, individual B2 assertions, protected B2/B3 faults, canonical module/four-task checks and independent Code review.

No unsafe historical script execution, automatic R11, G5 completion, risk acceptance or delivery approval follows from this report.[oauth:chatgpt/gpt-6-astra · 输入 63689 / 输出 2540 tokens]
