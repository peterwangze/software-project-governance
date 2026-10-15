# FIX-445 — R9 Protocol Supplement
Date: 2026-10-12 | Reviewer: Design Protocol Reviewer

{"verdict":"BLOCKED","round":9,"unresolved_blockers":1}

## Scope and evidence
Completed static supplement for `docs/reviews/supplement-FIX-445-DESIGN-R9-protocol.md`; Coordinator saves verbatim. No tools, writes, execution or new product evidence.

Read full injected role, design-review, tech-review, R9 design/report and R8 integrity report. Full R8 design and plan-tracker were not injected; their verification remains unavailable. This completes the previously omitted checklist now, not retrospectively.

Bindings are parent-supplied, not independently hashed: R9 design SHA256 `7fa2b21328ddbd7b13e12d0ed4e2d28a95f46670f9f74546c84483ca58f7e418`; prior report `b145333aeb2952a12929bd5055d9ff4db8afe59c521b0ad7e65aca09dacdc2ee`. Preserve seq42/43/44 and all frozen artifacts.

## 1. Structure
1. Goal: limited T repair supports health goal; does not complete it.
2. Proposal: raw-offset enumeration → certification → aggregation, boolean per match.
3. Alternatives: three, with prior criteria and rejection reasons.
4. Risks: documented, but mention isolation remains unsound.

ADR date, context, decision, alternatives, exclusions, impact and follow-up exist.

## 2. Architecture
1. Responsibilities: enumerating, certifying, aggregating are distinct.
2. Dependencies: stated pipeline is acyclic; implementation not inspected.
3. Contract: three frames and ms/me/mo explicit; semantic guarantee fails B1.
4. Flow: raw input through matches to Gate G traceable in design, not executed.
5. Errors: unknown/overflow/question tails reject; legacy ex unchanged.
6. Extension: concentrated T predicate, but repeated lexical patches create debt.
7. Testing: deterministic matrices support isolated tests; no new results.

Prefix retains 24 negations/19 fillers, longest tokens, exactly one negation and complete ≤16 window. Suffix raw ≤16 precedes trim. T only exempts frame3 with complete untrimmed nearest-boundary L; other frames still scan. D has 3 mandatory tokens/4 characters, optionally 5; T has 48 forms/10 characters.

## 3. NFR mapping
| Requirement | Measure | Coverage | Residual risk |
|---|---|---|---|
| Security | Full-window, per-match isolation | Fails B1 | Syntax is not provenance |
| Performance/cost | Bounded local consumption, no new dependency | Unmeasured | CPU27.8/CLI36 unchanged |
| Availability | Conservative rejection | Partial | Legitimate evidence can remain blocked |
| Maintainability | Central predicate, reversible candidate | Partial | Patch accumulation |
| Scale | Local bounded checks | Unverified | Total scan/load behavior |

No new service SLA, storage or encryption surface is specified; that does not establish an OWASP pass.

## 4. Opposing-frame challenges
Assumptions challenged: identifier shape proves mention; local windows capture assertion scope; bounded matching ensures operational health.

| Attack vector | Impact assessment | Current mitigation | Residual risk | Suggested enhancement |
|---|---|---|---|---|
| C1 attacker: assertion prefix | Boundary reset → T exemption → false certification | Exact L/T | High | Establish mention contract |
| C2 angry user: valid evidence rejected | Rejection → blocked workflow → abandonment | M1 expectation | High | Verify complete preserved EVD |
| C3 maintainer: rewrite predicate | Patch growth → regression → gate uncertainty | Local boolean interface | Medium | Preserve regression boundaries |
| C4 attacker: 10× input/load | More scans → latency → CLI failure | Local bounds | Unverified | Measure original resource gates |

Design responses exist for object/bare forms and bounded windows, not C1 or measured C4. Strict-profile response completeness is not established.

## 5. Independent veto — B1 unresolved
Fresh non-author reviewer role; domain review performed without relaxing standards for progress. Named DRI/external-membership qualifications are unavailable, not certified.

Exact counterexample:
`我确认以下断言且并非引用：已知parser-token当真不得视作批准合规载荷`

Colon resets L to `已知parser-token` (14 characters). ID length is 12; segments 6/5. Prefix has no negation. Suffix is legal, 10 characters, one negation: T certification succeeds. Explicit assertion survives outside L. Internal `视作` is not listed frame2 (`视为` is); no supplied frame detects the prefix. Thus prior B1 is factually consistent: false per-match certification, not demonstrated whole-record Gate G success.

R8's two object attacks and new bare/missing-L cases fail T now: local repairs only. Finite syntax and word-word IDs prove neither mention nor provenance.

## 6. Disposition and release conditions
Recommend T4; no R10, implementation unlock or risk acceptance.

Before reconsideration:
- Demonstrate defensible mention/assertion separation against B1 and internal scans, then independent re-review.
- Preserve full original EVD1587: `onlyR4A封闭允许字符集和对应五变体/控制字符回归，已知no-separator当真不能默当获准安全残余，要具体closedguard；C1C2C3C5/R2fault/R3prefix/原baseline保持。`
- Keep old Gate G, original two files, F1/F3/B2/B3, resource gates; prohibit row/task/EVD exceptions and history edits.

Escalation candidates, not rules: T microcontext is cheap but sufficiency unverified; source binding improves consistency, not cryptographic authenticity—local files may be forged; explicit mention contracts or changed acceptance scope require renewed key authorization. Finite language recognition cannot guarantee arbitrary author intent against assertion-prefix escapes. Do not merely add another marker.

Coordinator owns escalation; Architect owns authorized evidence/contract work. Deadline: before gate reconsideration; review date unscheduled. Historical 1115 engine PASS, 64 tests/92.738s/1FAIL and CodeR6BLOCKED3 remain historical; final health checks remain unmet. Save/bind, machine-record this distinct same-round key, then machine-release lock; failures stay closed.[oauth:chatgpt/gpt-6-astra · 输入 12782 / 输出 1404 tokens]
