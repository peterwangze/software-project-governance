# FIX-486 Code Review — R0 (2026-11-15)

- Reviewer: Code Reviewer subagent fix486-rev (read-only; ran sandbox suite 7/7 + rc.3 harness)
- Subject: uncommitted diff — lib/dsh-native/overlay.js (+31/−3, sole git file); sandbox test .governance/sandboxes/fix486-impl/tests/t-js-expr-skill-dirs.mjs (7 cases, gitignored); evidence .governance/incidents/fix486-evidence/
- Verdict: **NEEDS_CHANGE** — the overlay.js diff itself is correct and approved as-is; the sole required change is giving the regression test a tracked home. Do not touch overlay.js.

## Findings

1. MUST-FIX (test placement, not the diff): the only guard for the expr face is gitignored; add one expr-node case to the existing tracked embedded-node probe `_PATH_IDENTITY_PROBE` in skills/software-project-governance/infra/tests/test_dsh_native_bridge.py:341 (its customSkillDirs is string-only, :359) — zero new infra, matches the repo's existing JS-face pattern.
2. Note: sandbox test lacks a weird-proto case (`Object.create({__jsExpr:'x'})` / class instance) for overlay.js:61; add alongside finding 1.
3. Note overlay.js:173: `'__jsExpr' in dir` also matches inherited props — message-wording only, same refusal code, acceptable.
4. Note: an expression that later evaluates to a path equal to an appended root yields a duplicate dir at child activation — benign vs. refusing the preset; no action.

## Seven points

1. PASS isJsExprNode — rejects null/non-object/array; proto must be Object.prototype/null; exactly one own enumerable key `__jsExpr` with string value; `{__js__}`, multi-key, `{__jsExpr:42}` all refuse; input is post-structuredClone so getters are already flattened — no slip-through found.
2. PASS dedup — sole samePath call (overlay.js:181) short-circuits `typeof dir === 'string' &&`; expr nodes never compared; that guard also stops the old object→`.replace` crash mode.
3. PASS no weakening — PERSONA_PREFIX_UNSUPPORTED (:128-137) and BASE_NOT_CLONEABLE (:104-110) untouched; all refusal codes intact; prefix-refusal asymmetry sound (prefix needs text append; dirs stay opaque).
4. PASS order — declaredDirs.slice() (:167) preserves base entries verbatim incl. expr nodes, roots appended after; asserted by R1/R5.
5. PASS tests — all 7 required cases covered and green (7/7, 131 ms); only gap = proto-branch (finding 2).
6. NEEDS_TRACKED_HOME — ruling: tracked home needed NOW; the only tracked deriveDefinition probes use string-only customSkillDirs and the harness lives in Temp, so on a fresh clone the exact rc.3 outage face has zero guard; one expr-node case in the existing tracked probe closes it (P4).
7. PASS scope — git status = single file; docs (:12-16, :51-58) name only `{__jsExpr: string}`, never `__js__` as acceptable.

## Evidence

git diff/status = single file (+31/−3); node --test 7/7 pass; harness vs rc.3 real rows: `deriveDefinition: ok baseRows=23`.

## Rework history (pre-R0, Coordinator-caught)

First delivery accepted BOTH `__js__` and `__jsExpr` single-key forms — the `__js__` form was a harness-fixture artifact (Coordinator's Python yaml converter invented the key), not a host fact; the real composed tree's only form is `{__jsExpr}` (loader config/utils.ts isJsExpr). Narrowed to `__jsExpr`-only; fixture renamed (4 sites); `__js__` became a refusal case. R1b red-first re-established after the narrowing.

## R1 delta review (same Reviewer, post-rework)

Verdict: **APPROVED**.

1. ① PASS — declared-side/clone-side split sound: `skillIndexes` runs on the clone but structuredClone preserves position/`name`, so `rows[skillIndexes[0]]` is the true declared row (overlay.js:171); emitted entries are only clone-stable forms (string / plain single-key `{__jsExpr: string}`); refused shapes are never emitted; getter/throwing boundaries die at BASE_NOT_CLONEABLE — declared-pass ⊆ clone-safe holds; the R7b laundering hole is genuinely closed; comments (overlay.js:167-170) match behavior; clone-side array-nature refusal (:159-165) and null/array guards (:172-173) retained.
2. ② PASS — tracked test guards the real rc.3 face: node deepEqual-verified verbatim at index 1, appended tail all-strings after the node with `/pkg/skills` fold-distinct under both folding regimes; native/posix inputs byte-identical; existing cases untouched (purely additive).
3. ③ PASS — R7 (`Object.create({__jsExpr})` → zero own keys → refused) and R7b (class own-key instance → refused, laundering rationale documented) assert `ok:false` + SKILL_DIRS_UNSUPPORTED; message branch unasserted — cosmetic, no action.
4. Micro-note (no action): a pathological non-deterministic customSkillDirs accessor would be read twice (clone read vs declared read) — unreachable from YAML-parsed host data and already fail-closed under BASE_NOT_CLONEABLE.
5. Verified locally: test_dsh_native_bridge 13 OK; sandbox 9/9 pass.
6. Scope: exactly 2 modified files matching findings 1-2; untracked docs/reviews/review-FIX-486-CODE-R0.md is the R0 review record (non-product), acceptable.
