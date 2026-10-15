# FIX-445 — Independent Design Review R10

## Disposition and scope

```json
{"verdict":"BLOCKED","round":10,"unresolved_blockers":1,"review_scope":"static_contract_analysis","implementation_authorized":false}
```

**Completion:** Static review completed against available injected materials; mandatory evidence verification remains incomplete.  
**Intended artifact:** `docs/reviews/review-FIX-445-DESIGN-R10.md`  
**Target:** `docs/design/FIX-445-mention-contract-R10.md`, supplied 135-line analysis.  
**Binding:** Parent-reported SHA256 `4cb201c24ef220a8b60941d1db3ad117f4a7b9568c198dff234a15c12fd29c8a`; not independently measured.

| Decision dimension | Result |
|---|---|
| Analysis quality | Central conflict argument is supported; one mandatory evidence-completeness blocker prevents approval. |
| Implementation readiness | **Not ready or authorized.** No replacement contract is established. |
| Original product acceptance | Unchanged: inherited 64 tests / 92.738s / 1FAIL; CodeR6 BLOCKED/3. |

This veto is **not** because the product remains unrepaired or because future alternatives need authorization.

## 1. Evidence and independence

Read the complete injected role, design-review and tech-review skills first, then the supplied target, source extract, canonical hook, R2/R3/R5 specifications and both R9 reports. No tools, commands, probes, writes, network requests or bootstrap execution occurred.

The source extract supplies complete EVD1536/1587/1588 at original lines 2271/2334/2335 and the original goal at plan-tracker line 7. It is derived evidence, not exemption authority. The goal supports useful automated governance without sacrificing quality; this analysis does not complete health or delivery.

Fresh non-author reviewer context is supplied. Human external membership, DRI exclusion and independently certified qualifications remain unknown. Standard-profile opposing-frame review was performed; no human panel is invented.

**Missing from the actual injection:** full `test_hooks.py`, historical `FIX-445-source-verification.md` C1–C7 mapping, `FIX-445-DEC336-contract.py`, and `FIX-445-R4-escalation.md`. Their mention in the extract or author’s reading declaration is not their contents.

## 2. Six-dimension assessment and hard gates

| Dimension | Assessment |
|---|---|
| Completeness / structure | Goal, proposal, alternatives and risks present. ADR date, context, proposed decision, exclusions, impact and follow-up present. Date is Coordinator-supplied, not a measured clock. |
| Architecture / dependencies | Acyclic: task extraction → orchestration → optional verifier → residual → M5/term scan. Tests depend on canonical implementation; no reverse dependency shown. Responsibilities are distinct. |
| Interfaces | Current scanner contract and credential boundaries are materially accurate. Future B is deliberately unspecified, not implementation-ready. |
| NFR / evolution | Security, resource cost, availability and maintainability addressed without claiming fresh validation; see mapping below. |
| Blue team | Four author challenges plus independent challenges below satisfy the numerical threshold. |
| Independent review | Fresh non-author review performed; required source corroboration incomplete. |

Hard gates: alternatives **3 ≥ 2**; ADR fields present; identified challenges **4 ≥ 3**; no cycle in the inspected flow. Evidence gate fails **B1**. No additional analysis defect is established.

## 3. Independently checked technical findings

### Current-interface conflict: supported

EVD1587’s preserved ordinary prose contains:

`已知no-separator当真不能默当获准安全残余`

In `endorsement_frame_check`, `当真` creates a framework match. Its nearest comma-bounded prefix is `已知no-separator`, which cannot be consumed by the 24-negation/19-filler tables. The following `不能` is outside the prefix. No quoted stacked-term substitution in `has_unnegated_fabrication_terms` removes this phrase.

The engine processes credentials and deletions within parsed records and typed fields. A JSON record elsewhere in the batch cannot credential this prose occurrence. Thus the unchanged route rejects this occurrence, conflicting with unchanged full-four-task cleanliness.

This is a static derivation, not executed whole-gate evidence, and not proof that every finite grammar or source-binding contract is impossible.

### Credential and guard boundaries: supported

`strict_obj`, `_nodup`, `_noconst` and `regions` support whole-candidate parsing, duplicate/nonstandard-constant rejection and no malformed-inner-record rescue. `credential` requires string identity, both timestamp instants with full fractional comparison, and same-key whole-value raw/display equality.

`field_candidates`, `top_string_fields` and `main` constrain deletion to eligible typed instances mapped to raw offsets. C6 retains `observed` typed attribution, not whole-value deletion. `GUARD_TOKENS` includes `把/将/当作/当成/视为/作为/当真`; guarded T2 candidates remain unexempted. Equality demonstrates local consistency, not cryptographic authenticity.

A future prose-mention type requiring different M5/Guard G behavior needs explicit authorization.

### R9/R8 reconciliation: supported within supplied historical evidence

Both R9 reports preserve the exact assertion:

`我确认以下断言且并非引用：已知parser-token当真不得视作批准合规载荷`

The colon resets the historical proposed T context to 14-character `已知parser-token`; the ID comprises 6/5-character segments plus hyphen. Its legal suffix has five tokens, ten characters and one negation. `视作` is not the listed `视为` framework. This explains false **per-match** certification, not actual whole-Gate-G passage.

R8 object examples remain rejected by current outer frameworks: `ms=mo` at `将/把`, not the inner `mid`. Residual scanning is not an arbitrary polarity classifier. R9 T was never implemented; its 48 forms and historical D’s three mandatory tokens/four characters, optionally five, are not new contracts.

The examples have distinct bytes; no identical-input/opposite-output impossibility proof is established.

## 4. Findings

### B1 — BLOCKING: mandatory original-source corroboration unavailable

**Scope:** Review evidence completeness, not a demonstrated false central conclusion.

Target §§2/4 relies on historical mapping, helper and escalation contents; §3 invokes test interfaces. Those files were not supplied here. The hook independently establishes the absence of a current ordinary-prose binding route, but it cannot establish the exact contents or historical classifications of absent artifacts.

**Closure:** Coordinator must obtain explicit next-step authorization under T4 and supply these frozen files verbatim for the required corroboration. Preserve this report and target unchanged. No probe, replacement design or automatic R11 is requested. Reviewer reconsideration date is unscheduled.

### W1 — WARNING: corpus allocation discrepancy needs a concrete decision

R2 line 50 says exactly: **“行内 refs ≤8 + taskglob ≤24，总≤32”**. Target §3’s shorthand must not be interpreted as a batch-wide eight-reference promise.

At hook lines 478–497, `got` resets per line; unique references accumulate across lines; sorted glob entries have no separate 24-entry cap; `files[:32]` caps the combined list.

Static examples, **not probes**:

- With zero refs and 32 eligible glob files, selection can contain 32 glob entries, violating the explicit 24-glob limit.
- Four lines with eight distinct refs each can consume all 32 positions before any glob entry.
- With 16 refs, at most 16 additional entries survive; batch allocation priority is ambiguous.

The total-32 bound remains intact. Lines 498–555 still resolve paths and drop outside-repository targets before opening them. No outside-read breach or performance failure is inferred.

**Priority:** Resolve before implementation reopening. This is an existing allocation-contract defect/ambiguity, potentially affecting legitimate credential availability, not grounds to reject an analysis that disclosed it.

**Immediate closure proposal:** Coordinator’s decision packet must specify per-line versus batch pooling, separate glob cap, deduplication and truncation priority. Attach these three static cases and expected selections. Any product correction requires separate authorization and focused tests; do not silently rewrite R2 or the frozen analysis.

## 5. NFR mapping and opposing-frame challenges

| Requirement | Measure / coverage | Remaining limit |
|---|---|---|
| Security | Strict credentials, typed offsets, Guard G, residual scan | No general natural-language or authenticity guarantee; no OWASP certification |
| Reliability | R2 distinguishes malformed content, outside paths and I/O failures | Reader/formatter/offset/Python fault claims are design/source evidence, not fresh fault tests |
| Performance / cost | Local bounds and retained total-32 selection | CPU27.8 / CLI36 / 434339 / 32MiB / 1500 unchanged; no measured closure |
| Availability / scale | Conservative rejection | Legitimate prose stays blocked; 10× load behavior unmeasured |
| Maintainability | One auditable contract preferred over lexical patches | Future migration/versioning and two-file feasibility unresolved |

Opposing assumptions: local syntax proves mention; bounded matching guarantees health; repository artifacts establish authenticity.

| Attack vector | Impact assessment | Current mitigation | Residual risk | Suggested enhancement |
|---|---|---|---|---|
| CH1 attacker forges both sides | Matching artifact → credential → unwarranted trust | Local-consistency disclaimer | High | Define eligible independent provenance |
| CH2 angry user retains original prose | Rejection → blocked health → unusable workflow | Honest conservative A | High | Require exact immutable-EVD compatibility evidence |
| CH3 dependency fault / 10× load | Read failure or extra work → blocking/latency → disruption | Fail-closed intent, caps | Unverified | Authorized fault and resource validation |
| CH4 maintainer rewrites predicate | Patch growth → regression → uncertain gate | Central interface, immutable history | Medium | Version scope and preserve negative regressions |

## 6. Recommendation and next actions

Retain **A** now: no repair claim. Evaluate **B** only with an existing eligible provenance binding, exact preserved-EVD mapping, explicit Guard G decision and adversarial scope evidence. **C** requires explicit acceptance-change authorization; it cannot be presumed permissible.

Coordinator owns B1/W1 escalation before gate reconsideration; dates remain unassigned. Persist/bind this exact report, machine-record the actual scoped verdict, then machine-release the lock.

Round 10 exceeds the fuse: **T4, no NEEDS_CHANGE and no automatic R11**. F1/F3/B2/B3 remain unchanged. Future authorized work still requires full product/source checks, 12 individual B2 assertions, protected fault validation and independent Code review. Product, implementation, health and delivery gates remain closed.[oauth:chatgpt/gpt-6-astra · 输入 41507 / 输出 2399 tokens]
