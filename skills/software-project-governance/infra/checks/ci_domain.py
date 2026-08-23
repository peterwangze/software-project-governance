"""CI-evidence check — extracted for FIX-267 in 0.76.0.

Scope (design audit-145-watchdog-design-0.76.0.md §3.5 / REQ-145.5): the
CI-evidence watchdog (`check_ci_evidence`, Check 38). The AUDIT-145 blind
spot this closes (G9/D4-gap): a governed project can CLAIM CI is built
(gates G5/G7 recorded, task rows mark 已完成) while the carrier file does
not exist (router) or the workflow exists but was never truly run (tv —
DEV-003 "本仓无 remote——首次运行/成功率统计待远端仓库后补验").

Declaration source (`DEC-154 ③` — only "claimed built" declarations
trigger C1; no declaration → no judgement):
  * plan-tracker 全文扫描；肯定声明 = 含「CI」+（已建|已配置|已建立|
    已完成 CI|workflow 就绪）→ 声称已建；含（已跑|已运行|已执行）→
    声称已跑。
  * 否定词（未跑|未真跑|待远端|从未|未运行|未执行）→ 「声称已建未跑」
    (built-but-not-run admission — 归类为已建声明, DEC-154 ③) — the
    claim still asserts EXISTENCE, so a missing carrier is still C1. A
    run marker + negation with NO built marker (「CI 已跑但从未真跑」)
    also classifies as 声称已建未跑 — never silently dropped (design
    :343 intent, P2-2).
  * 无「CI」字样的文本 / CI 字样但无肯定声明 → 不构成声明（不误判）。
  * 词边界（P2-1）：「CI」必须是词边界 token —— ACID/SCIENCE/SPECIFIC
    内的 "CI" 子串不算（「specific 已配置」不得成假 built claim）。
  * 规则/验收文本（含 ``→ FAIL`` / ``→ WARN`` 规则箭头——如 REQ-145.5
    / FIX-267 行引用本检查语义）→ 描述规则而非项目状态，不构成声明
    （声明识别边界：spec prose 不得触发 C1）。

Judgement (verdict ∈ PASS / WARN / FAIL / no-verdict; never raises):
  C1  FAIL — 声称已建 (incl. 已建未跑, DEC-154 ③) but NO carrier found
      (multi-path probe: ``**/.github/workflows/*`` deep walk over the
      project's OWN git tree — nested git repos (vendor/scratch clones)
      excluded — plus root ``.gitlab-ci.yml`` / ``Jenkinsfile``).
      Run claims DO NOT enter C1 (DEC-156 — see C3).
  C2  WARN — carrier exists but ``git remote -v`` is empty or git is
      unavailable ("CI 未真跑"; fail-safe — never FAIL; R-D4c).
  C3  WARN — a 声称已跑 claim that is locally unprovable: no remote /
      git unavailable (carrier present, fail-safe) OR no carrier at all
      (DEC-156: claimed run without a carrier is unprovable — fail-safe,
      never escalated to FAIL).
  C4  PASS — no declaration AND no carrier (no over-claim).
  PASS — carrier + remote confirmed (existence + remote only, `DEC-154
      ②`: 0.76.0 does NOT deep-inspect workflow contents/jobs/runs).
  no-verdict — no plan-tracker to read (missing/unreadable), non-text
      plan content, or a NON-pathlike ``repo_root`` (P0-1 guard — the
      TypeError never reaches Path()).

Facts root: ``repo_root`` defaults to ``HOST_PROJECT_ROOT`` (FIX-270
mixed-root semantics — the git facts root, never the plugin ROOT).

This module owns the CI check domain. Shared helpers and constants still
defined in verify_workflow.py (``HOST_PROJECT_ROOT``, ``SAMPLE_PATH``) are
reached through a deferred module reference rather than a top-level
import, so verify_workflow.py can import this module at module load time
without an import cycle — the same deferred ``_vw()`` pattern as
checks.risk_domain / checks.snapshot_domain / checks.gate_domain.

Orthogonality: this check does NOT replace Check 30/30c/34 (review-record
validity), Check 28 family (CI-file syntax / manifest), or the G-gate
check set — it adds one new content dimension (CLAIM vs CARRIER vs
REMOTE facts). WARN and FAIL both count into all_issues (Check-36/37
convention).
"""

import os
import re
import subprocess
from pathlib import Path

# ── Shared-helper access (deferred to avoid import cycle) ──────────
# Same deferred-_vw() pattern as checks.risk_domain (Phase 5b). The shared
# names are resolved lazily on the first call into this module (after
# verify_workflow has finished loading) and cached in this module's globals,
# so moved function bodies can reference them by bare name unchanged.

_VW_CACHE = None


def _vw():
    """Return the verify_workflow module (imported lazily, cached)."""
    global _VW_CACHE
    if _VW_CACHE is None:
        import verify_workflow  # noqa: WPS433 (deferred import on purpose)
        _VW_CACHE = verify_workflow
    return _VW_CACHE


# Shared names this domain reaches back into verify_workflow for. Refreshed
# on every call into `_resolve_shared()` (NOT cached) so test-time monkey-
# patching of verify_workflow attributes propagates (and the --project-root
# override rebinding is captured).
_SHARED_NAMES = (
    "HOST_PROJECT_ROOT",  # git facts root (FIX-270 mixed-root fix — never ROOT)
    "SAMPLE_PATH",        # plan-tracker (live declaration source)
)


def _resolve_shared():
    """Refresh this module's globals with shared names from verify_workflow."""
    vw = _vw()
    g = globals()
    for _name in _SHARED_NAMES:
        g[_name] = getattr(vw, _name)


# ── Domain constants ────────────────────────────────────────────────

_GIT_TIMEOUT = 15  # mirrors snapshot_domain / checks.projection (15s)

# Affirmative "claimed built" markers (design §3.5 / DEC-154 ③). A line
# must contain the literal 「CI」 AND one of these to be a built claim.
# Strict markers only — "CI 配置"/"CI 存在" WITHOUT 已- prefix are NOT a
# declaration (no-over-claim: descriptive text must not trigger C1).
_CI_BUILT_MARKERS = (
    "已建",
    "已配置",
    "已建立",
    "已完成 CI",
    "workflow 就绪",
)

# Affirmative "claimed run" markers.
_CI_RUN_MARKERS = (
    "已跑",
    "已运行",
    "已执行",
)

# Negation words (design §3.5 / DEC-154 ③): a claim line carrying one of
# these is an ADMISSION "已建未真跑" — classified as 声称已建未跑, NOT as
# a run claim.
_NEGATION_MARKERS = (
    "未跑",
    "未真跑",
    "待远端",
    "从未",
    "未运行",
    "未执行",
    "未建",
    "未配置",
    "未建立",
)

# Rule/spec text signatures (声明识别边界): plan-tracker rows that QUOTE
# the check's own semantics — e.g. REQ-145.5 "声称 CI 已建但 workflow
# 不存在 → FAIL；存在但无 remote → WARN「CI 未真跑」" and the FIX-267
# acceptance cell "无 workflow 声称 CI → FAIL；有 workflow 无 remote →
# WARN「未真跑」" — describe the RULE, not the project's CI status. A line
# carrying a rule arrow (→ FAIL / → WARN) is spec prose, never a claim
# (no-over-claim: rule text must not trigger C1).
_RULE_TEXT_SIGNATURES = (
    "→ FAIL",
    "→ WARN",
    "-> FAIL",
    "-> WARN",
)

_REMOTE_OK = "ok"
_REMOTE_EMPTY = "empty"
_REMOTE_UNABLE = "unable"

# Word-boundary CI token (P2-1): the declaration source must contain a
# WORD-BOUNDARY 「CI」 — the bare substring "CI" also occurs inside English
# words (ACID / SCIENCE / SPECIFIC), so "Product specific 已配置" would
# otherwise become a false built claim. Negative lookarounds exclude
# letters before/after; Chinese/space/punctuation delimiters keep the
# real "CI 已建" / "CI/CD" shapes matching.
_CI_WORD_RE = re.compile(r"(?<![A-Za-z])CI(?![A-Za-z])")


def _is_pathlike(value):
    """True iff ``value`` is a ``str`` or ``os.PathLike`` (P0-1 guard)."""
    return isinstance(value, (str, os.PathLike))


# ── Declaration parsing ─────────────────────────────────────────────

def _negated(line):
    """True iff ``line`` carries a negation admission marker."""
    return any(marker in line for marker in _NEGATION_MARKERS)


def _parse_ci_claims(plan_text):
    """Return ``{"built", "built_notrun", "run", "lines"}`` from plan text.

    Scans every line: a line that contains the literal 「CI」 and one of the
    affirmative markers becomes a claim. Lines with a negation marker are
    classified as built-not-run admissions (they still assert existence —
    DEC-154 ③). A non-``str`` input degrades to an empty claim set (the
    caller already guards the no-plan / no-text path). Never raises.

    Boundary (声明识别边界): a line that carries a RULE-TEXT signature
    (``→ FAIL`` / ``→ WARN`` — the severity arrow used by requirement and
    acceptance cells) describes the check's semantics, not the project's
    CI status — such lines are NEVER claims (spec prose must not trigger
    C1; the host REQ-145.5 / FIX-267 rows are the live example).
    """
    claims = {"built": [], "built_notrun": [], "run": [], "lines": 0}
    if not isinstance(plan_text, str):
        return claims
    for line in plan_text.splitlines():
        claims["lines"] += 1
        if not _CI_WORD_RE.search(line):
            continue  # word-boundary CI only (ACID/SCIENCE/SPECIFIC exclusion)
        has_built = any(m in line for m in _CI_BUILT_MARKERS)
        has_run = any(m in line for m in _CI_RUN_MARKERS)
        if not has_built and not has_run:
            continue  # CI mention without an affirmative marker — no claim
        if any(sig in line for sig in _RULE_TEXT_SIGNATURES):
            continue  # rule/spec text quoting the check semantics — no claim
        negated = _negated(line)
        if has_built:
            bucket = "built_notrun" if negated else "built"
            claims[bucket].append(line.strip()[:160])
        if has_run and not negated:
            claims["run"].append(line.strip()[:160])
        elif has_run and not has_built:
            # run marker + negation, no built marker ("CI 已跑但从未真跑"):
            # the run reference implies existence and the negation admits
            # non-run — classify as 声称已建未跑 (design :343 intent),
            # never silently dropped.
            claims["built_notrun"].append(line.strip()[:160])
    return claims


# ── Carrier + remote probes (multi-path, DEC-154 ①) ─────────────────

def _probe_workflow_carriers(repo_root):
    """Return ``([relpath, ...], gitlab_ci, jenkinsfile)`` — never raises.

    Multi-path probe (design §3.5 / DEC-154 ①): a CI CARRIER exists when
    ANY of the following is found:
      * ``**/.github/workflows/*`` — deep walk, MONOREPO-safe: a workflow
        in any subdirectory of the project's OWN git tree counts (e.g.
        the host ``project/.github/workflows/``). Nested-repo boundary:
        a directory that contains its own ``.git`` (vendor checkouts /
        scratch clones) and its whole subtree is NOT the project — its
        workflows are excluded (router live case:
        ``.inspect-vision-router/`` and ``.tmp-research/dsh-codex-connect/``
        are separate git repos; the router project itself has zero
        tracked workflows).
      * ``.gitlab-ci.yml``            (root of the repo),
      * ``Jenkinsfile``               (root of the repo).
    Any probe failure (missing root / permission / walk error) degrades
    to "nothing found" — a failed probe must never raise, and the caller's
    fail-safe path decides the verdict.
    """
    try:
        if not _is_pathlike(repo_root):
            return [], False, False   # P0-1: non-pathlike → no evidence
        root = Path(repo_root)
        if not root.is_dir():
            return [], False, False
        found = []
        try:
            root_str = str(root)
            for dirpath, dirnames, _filenames in os.walk(root_str, topdown=True):
                # Nested-repo boundary: any subdirectory carrying its own
                # .git is a separate repository — prune the whole subtree.
                if dirpath != root_str and os.path.exists(
                        os.path.join(dirpath, ".git")):
                    dirnames[:] = []
                    continue
                # Never descend into git metadata, deps, or caches (a
                # workflow there is a dependency's, not the project's).
                dirnames[:] = [d for d in dirnames
                               if d not in (".git", "node_modules",
                                            "__pycache__")]
                if (Path(dirpath).name == "workflows"
                        and Path(dirpath).parent.name == ".github"):
                    for name in _filenames:
                        fixture = Path(dirpath) / name
                        try:
                            found.append(str(fixture.relative_to(root)))
                        except ValueError:
                            found.append(str(fixture))
        except (OSError, RuntimeError, ValueError):
            pass  # walk degraded — fail-safe: no .github evidence
        gitlab = (root / ".gitlab-ci.yml").is_file()
        jenkins = (root / "Jenkinsfile").is_file()
        return sorted(set(found)), gitlab, jenkins
    except (OSError, RuntimeError, ValueError):
        return [], False, False


def _git_remote_state(repo_root):
    """Return ``"ok"`` | ``"empty"`` | ``"unable"`` — never raises.

    ``git -C <repo_root> remote -v``: non-empty stdout → ``"ok"``; empty
    stdout (well-formed repo, no remote) → ``"empty"``; no ``.git`` /
    git failure / timeout / bad root → ``"unable"`` (fail-safe state — the
    caller degrades to C2 WARN, never FAIL; design §3.5).
    """
    try:
        if not _is_pathlike(repo_root):
            return _REMOTE_UNABLE      # P0-1: non-pathlike → unable (fail-safe)
        root = Path(repo_root)
        if not (root / ".git").exists():
            return _REMOTE_UNABLE
        out = subprocess.run(
            ["git", "-C", str(root), "remote", "-v"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False, timeout=_GIT_TIMEOUT,
        )
        if out.returncode != 0:
            return _REMOTE_UNABLE
        return _REMOTE_OK if out.stdout.strip() else _REMOTE_EMPTY
    except (OSError, subprocess.SubprocessError, ValueError):
        return _REMOTE_UNABLE


def _set_verdict(result, verdict, reason):
    result["stats"]["warn_count"] = len(result["warnings"])
    result["stats"]["violation_count"] = len(result["violations"])
    result["verdict"] = verdict
    result["reason"] = reason
    return result


# ── Check 38 ───────────────────────────────────────────────────────

def check_ci_evidence(plan_content=None, repo_root=None):
    """FIX-267 / REQ-145.5 (design audit-145-watchdog-design §3.5): Check 38.

    CI-evidence watchdog: a plan-tracker claim that CI is built/run must be
    corroborated by a CI carrier AND a git remote; a carrier that cannot
    have run ("CI 未真跑") is disclosed, never escalated (fail-safe).

    Signals (verdict ∈ PASS / WARN / FAIL / no-verdict; never raises):
      C1  FAIL — 声称已建 (incl. 已建未跑) exists but NO carrier found.
          Run claims do NOT enter C1 (DEC-156 — see C3).
      C2  WARN — carrier exists but ``git remote -v`` is empty or git is
          unavailable ("CI 未真跑" — fail-safe, never FAIL).
      C3  WARN — 声称已跑 claim locally unprovable: no remote / git
          unavailable, OR no carrier at all (DEC-156 — fail-safe, never
          escalated to FAIL).
      C4  PASS — no declaration AND no carrier (no over-claim).
      PASS — carrier + remote confirmed (existence + remote only —
          DEC-154 ②; no deep workflow/job inspection in 0.76.0).
      no-verdict — no plan-tracker to read (missing/unreadable), or
          non-text plan content, or a NON-pathlike ``repo_root`` (P0-1
          guard): nothing to judge.

    Injection surface (all optional; default = live read):
      ``plan_content``  plan-tracker text; ``None`` → live read of
          ``SAMPLE_PATH`` (the host ``.governance/plan-tracker.md``).
      ``repo_root``     repo to probe for carrier files + git remote;
          ``None`` → live ``HOST_PROJECT_ROOT`` (FIX-270 mixed-root
          semantics: the host facts root, NEVER the plugin ROOT).

    Returns ``{verdict, reason, violations, warnings, stats}``.
    """
    result = {
        "verdict": "no-verdict",
        "reason": "",
        "violations": [],
        "warnings": [],
        "stats": {
            "plan_lines_scanned": 0,
            "built_claims": 0,
            "built_notrun_claims": 0,
            "run_claims": 0,
            "carrier_exists": False,
            "workflow_files": 0,
            "gitlab_ci": False,
            "jenkinsfile": False,
            "remote_state": None,   # "ok" | "empty" | "unable" | None
            "warn_count": 0,
            "violation_count": 0,
        },
    }
    _resolve_shared()

    # ── Plan text (live read guarded — never raise) ──
    text = plan_content
    if text is None:
        if not SAMPLE_PATH.is_file():
            return _set_verdict(
                result, "no-verdict",
                "plan-tracker.md not found — no CI declaration source to "
                "judge (fail-safe no-verdict)")
        try:
            text = SAMPLE_PATH.read_text(encoding="utf-8", errors="replace")
        except (IOError, OSError, UnicodeError):
            return _set_verdict(
                result, "no-verdict",
                "plan-tracker.md unreadable — no CI declaration source to "
                "judge (fail-safe no-verdict)")
    if not isinstance(text, str):
        return _set_verdict(
            result, "no-verdict",
            "plan content is not text — no CI declarations to judge "
            "(fail-safe no-verdict)")

    claims = _parse_ci_claims(text)
    result["stats"]["plan_lines_scanned"] = claims["lines"]
    result["stats"]["built_claims"] = len(claims["built"])
    result["stats"]["built_notrun_claims"] = len(claims["built_notrun"])
    result["stats"]["run_claims"] = len(claims["run"])

    # ── Carrier + remote facts (facts root = repo_root or host root) ──
    # P0-1: a NON-pathlike repo_root (int, list, ...) must never reach
    # Path() — TypeError is not caught by the (OSError, RuntimeError,
    # ValueError) guard. The entry guard degrades to a fail-safe
    # no-verdict stating the invalid root.
    if repo_root is not None and not _is_pathlike(repo_root):
        return _set_verdict(
            result, "no-verdict",
            "repo_root is not a str/os.PathLike — CI facts unprobeable "
            "(fail-safe no-verdict, P0-1)")
    root = repo_root
    if root is None:
        root = HOST_PROJECT_ROOT  # FIX-270: never ROOT (plugin root)
    found, gitlab, jenkins = _probe_workflow_carriers(root)
    remote = _git_remote_state(root)
    carrier = bool(found) or gitlab or jenkins
    result["stats"]["carrier_exists"] = carrier
    result["stats"]["workflow_files"] = len(found)
    result["stats"]["gitlab_ci"] = gitlab
    result["stats"]["jenkinsfile"] = jenkins
    result["stats"]["remote_state"] = remote

    claimed_built = bool(claims["built"] or claims["built_notrun"])
    claimed_run = bool(claims["run"])

    # ── Judgement ──
    if carrier:
        if remote in (_REMOTE_EMPTY, _REMOTE_UNABLE):
            no_remote_part = ("remote 为空" if remote == _REMOTE_EMPTY
                              else "git 不可用/无法确认 remote")
            carrier_name = (found[0] if found
                            else (".gitlab-ci.yml" if gitlab else "Jenkinsfile"))
            result["warnings"].append({
                "rule": "C2",
                "carrier": carrier_name,
                "reason": (
                    "CI 载体存在（{0}）但 {1}——CI 未真跑（无远端仓库无法 "
                    "运行；fail-safe WARN，不升 FAIL；R-D4c）".format(
                        carrier_name, no_remote_part)),
            })
            if claimed_run:
                result["warnings"].append({
                    "rule": "C3",
                    "reason": (
                        "plan-tracker 声称 CI 已跑但本地无法证实（{0}）— "
                        "fail-safe WARN，不升 FAIL".format(no_remote_part)),
                })
            return _set_verdict(
                result, "WARN",
                "CI 载体存在但 {0}——CI 未真跑（fail-safe WARN）"
                .format(no_remote_part))
        return _set_verdict(
            result, "PASS",
            "CI 载体存在且 git remote 可确认——存在性 + remote 满足 "
            "(DEC-154 ②：0.76.0 不深究 workflow 内容/job 校验)")

    # No carrier. Built claims (incl. built-not-run admissions, DEC-154 ③)
    # are falsified by the missing carrier → C1 FAIL. Run claims (DEC-156)
    # are C3 WARN — "claimed run" without a carrier is locally unprovable,
    # and the fail-safe C3 semantics (never escalation to FAIL) wins over
    # the C1 branch.
    if claimed_built:
        for claim in claims["built"] + claims["built_notrun"]:
            result["violations"].append({
                "rule": "C1",
                "claim": claim,
                "reason": (
                    "plan-tracker 声称 CI 已建（{0}）但未找到 CI 载体 "
                    "（**/.github/workflows/**, .gitlab-ci.yml, "
                    "Jenkinsfile 均不存在）".format(claim)),
            })
    if claimed_run:
        for claim in claims["run"]:
            result["warnings"].append({
                "rule": "C3",
                "claim": claim,
                "reason": (
                    "plan-tracker 声称 CI 已跑（{0}）但无 CI 载体——已跑"
                    "无法证实（fail-safe WARN，不升 FAIL；DEC-156）"
                    .format(claim)),
            })
    if result["violations"]:
        return _set_verdict(
            result, "FAIL",
            "声称 CI 已建但无 CI 载体（workflow 文件不存在）")
    if result["warnings"]:
        return _set_verdict(
            result, "WARN",
            "声称 CI 已跑但无 CI 载体——已跑无法证实（fail-safe WARN，"
            "DEC-156）")
    return _set_verdict(
        result, "PASS",
        "无 CI 声明且无 CI 载体——不过度声明（C4）")
