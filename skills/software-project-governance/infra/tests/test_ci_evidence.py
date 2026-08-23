"""FIX-267 / REQ-145.5 — Check 38 `check_ci_evidence` CI-evidence tests
(red→green).

Deliverable under test (design audit-145-watchdog-design-0.76.0.md §3.5,
test plan §5.4 — 8 cases, plus the FIX-267 acceptance-item extras):

1. ``check_ci_evidence(plan_content=None, repo_root=None)`` in
   ``infra/checks/ci_domain.py``: signal table C1 (claimed built, no
   carrier → FAIL) / C2 (carrier exists, no remote / git unavailable →
   WARN「CI 未真跑」) / C3 (claimed run, locally unprovable → WARN,
   fail-safe) / C4 (no declaration, no carrier → PASS); result contract
   ``{verdict, reason, violations, warnings, stats}``; verdict ∈
   PASS / WARN / FAIL / no-verdict; NEVER raises.
2. Declaration parsing (DEC-154 ③): markers 已建|已配置|已建立|已完成 CI|
   workflow 就绪 → claimed built; 已跑|已运行|已执行 → claimed run;
   negation words (未跑|未真跑|待远端|从未|...) → 「声称已建未跑」
   (built-not-run admission — still a built claim for C1); CI mention
   without an affirmative marker → no claim (no over-claim).
3. Multi-path carrier probe (DEC-154 ①): deep glob ``**/.github/workflows/*``
   (monorepo-safe), root ``.gitlab-ci.yml``, root ``Jenkinsfile`` —
   any one = carrier.
4. Fail-safe: git unavailable (no .git) → C2 WARN, never FAIL; carrier +
   remote ok → PASS even with a run claim (0.76.0 does not deep-inspect
   workflow content/runs — DEC-154 ②).
5. Facts root: repo_root=None → live HOST_PROJECT_ROOT (FIX-270 mixed-root
   semantics — never the plugin ROOT).
6. no plan text → no-verdict / never-raise.
7. Numbering (F9): Check 38 block sits between Check 37 and the summary.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_ci_evidence.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402
from checks import ci_domain as cd  # noqa: E402


# ── Fixtures ────────────────────────────────────────────────────────────

CLAIM_BUILT = "| P1 | DEV-003 | CI 已建——GitHub Actions 门禁已配置 | 已完成 |"
CLAIM_BUILT_NOTRUN = (
    "| P1 | DEV-003 | CI 已建——本仓无 remote，首次运行/成功率统计待远端"
    "仓库后补验 | 已完成 |")   # 已建 + 待远端 → 声称已建未跑
CLAIM_RUN = "| P1 | DEV-003 | CI 已跑 3 次 | 已完成 |"
NO_CLAIM_CI_TEXT = (
    "| P1 | DEV-003 | 建立基础 CI 门禁（gradle build + unit test 自动运行）| "
    "计划 2026-08-21 |")   # CI 字样、无肯定声明标记 → 不构成声明
DESCRIPTIVE_CI_TEXT = (
    "| 里程碑 | 检查 CI 是否存在 | 成功率 80% | 门禁设计 |\n"
    "| 里程碑 | 确认 CI 从未跑过的历史 | 待评估 |")  # 否定/描述 → 无声明
RULE_TEXT_CI = (
    "| REQ-145.5 | CI 实跑证据断言——plan-tracker 声称 CI 已建但 workflow "
    "不存在 → FAIL；存在但无 remote/运行记录 → WARN「CI 未真跑」 |\n"
    "| **P0** | FIX-267 | 验收：无 workflow 声称 CI → FAIL；有 workflow "
    "无 remote/运行记录 → WARN「未真跑」 |")  # 规则/验收文本 → 无声明
NO_CI_TEXT = "| P1 | DEV-003 | 建立基础门禁 | 计划 |"


def _plan(*lines):
    return "\n".join(lines)


def _mk_repo(base, workflows=(), gitlab=False, jenkins=False):
    """Recreate a minimal repo dir under ``base`` with carrier files."""
    root = Path(base)
    for rel in workflows:
        wf = root / rel
        wf.parent.mkdir(parents=True, exist_ok=True)
        wf.write_text("name: ci\non: push\n", encoding="utf-8")
    if gitlab:
        (root / ".gitlab-ci.yml").write_text("stages: [test]\n", encoding="utf-8")
    if jenkins:
        (root / "Jenkinsfile").write_text("pipeline {}\n", encoding="utf-8")
    return root


def _remote(state):
    return mock.patch.object(cd, "_git_remote_state", return_value=state)


# ── Signal table: C1 / C2 / C3 / C4 ─────────────────────────────────────

class Check38SignalTableTests(unittest.TestCase):
    """Red→green fixtures over injectable plan text + repo root."""

    def test_c1_claimed_built_no_carrier_fails(self):
        """§5.4 #1: 声称已建但 `.github/workflows` 不存在 → FAIL (C1)."""
        with tempfile.TemporaryDirectory() as td:
            r = vw.check_ci_evidence(
                plan_content=_plan(CLAIM_BUILT),
                repo_root=_mk_repo(td))
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual([v["rule"] for v in r["violations"]], ["C1"])
        self.assertIn("CI 已建", r["violations"][0]["claim"])
        self.assertEqual(r["stats"]["built_claims"], 1)
        self.assertEqual(r["stats"]["carrier_exists"], False)

    def test_c1_claimed_built_with_carrier_passes(self):
        """§5.4 #1-green: 声称已建 + 载体存在 → 不 C1 (carrier+remote → PASS)."""
        with tempfile.TemporaryDirectory() as td:
            repo = _mk_repo(td, workflows=(".github/workflows/ci.yml",))
            with _remote("ok"):
                r = vw.check_ci_evidence(
                    plan_content=_plan(CLAIM_BUILT), repo_root=repo)
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["stats"]["carrier_exists"], True)
        self.assertEqual(r["stats"]["workflow_files"], 1)

    def test_c2_carrier_without_remote_warns(self):
        """§5.4 #2: 载体存在 + 无 remote → WARN「CI 未真跑」(C2)."""
        with tempfile.TemporaryDirectory() as td:
            repo = _mk_repo(td, workflows=(".github/workflows/ci.yml",))
            with _remote("empty"):
                r = vw.check_ci_evidence(
                    plan_content=_plan(NO_CLAIM_CI_TEXT), repo_root=repo)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual([w["rule"] for w in r["warnings"]], ["C2"])
        self.assertIn("CI 未真跑", r["warnings"][0]["reason"])
        self.assertEqual(r["stats"]["remote_state"], "empty")

    def test_c3_claimed_run_locally_unprovable_warns(self):
        """§5.4 #3: 声称已跑 + 本地无法证实 → WARN (C3, fail-safe)."""
        with tempfile.TemporaryDirectory() as td:
            repo = _mk_repo(td, workflows=(".github/workflows/ci.yml",))
            with _remote("empty"):
                r = vw.check_ci_evidence(
                    plan_content=_plan(CLAIM_RUN), repo_root=repo)
        self.assertEqual(r["verdict"], "WARN")
        rules = [w["rule"] for w in r["warnings"]]
        self.assertIn("C2", rules)   # carrier + no remote
        self.assertIn("C3", rules)   # claimed run, unprovable
        self.assertEqual(r["stats"]["run_claims"], 1)

    def test_claimed_run_with_remote_passes_fail_safe(self):
        """C3 fail-safe boundary: carrier + remote ok → PASS even with a
        run claim (0.76.0 does not deep-inspect workflow runs — DEC-154 ②;
        local cannot disprove, never nag)."""
        with tempfile.TemporaryDirectory() as td:
            repo = _mk_repo(td, workflows=(".github/workflows/ci.yml",))
            with _remote("ok"):
                r = vw.check_ci_evidence(
                    plan_content=_plan(CLAIM_RUN), repo_root=repo)
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["warnings"], [])

    def test_c4_no_claim_no_carrier_passes(self):
        """§5.4 #4: 无 CI 声明且无 workflow → PASS (C4, 不过度声明)."""
        with tempfile.TemporaryDirectory() as td:
            r = vw.check_ci_evidence(
                plan_content=_plan(NO_CI_TEXT),
                repo_root=_mk_repo(td))
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])
        self.assertIn("C4", r["reason"])

    def test_negation_classified_as_built_not_run(self):
        """否定词归类（已建未跑）: 已建 + 待远端 → built_notrun claim.

        (a) carrier exists + no remote → C2 WARN (same as tv DEV-003);
        (b) without carrier → C1 FAIL (the admission still asserts
        existence — DEC-154 ③)."""
        with tempfile.TemporaryDirectory() as td:
            repo = _mk_repo(td, workflows=(".github/workflows/ci.yml",))
            with _remote("empty"):
                r = vw.check_ci_evidence(
                    plan_content=_plan(CLAIM_BUILT_NOTRUN), repo_root=repo)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["stats"]["built_notrun_claims"], 1)
        self.assertEqual(r["stats"]["built_claims"], 0)
        self.assertEqual(r["stats"]["run_claims"], 0)
        with tempfile.TemporaryDirectory() as td2:
            r2 = vw.check_ci_evidence(
                plan_content=_plan(CLAIM_BUILT_NOTRUN), repo_root=_mk_repo(td2))
        self.assertEqual(r2["verdict"], "FAIL")
        self.assertEqual(r2["violations"][0]["rule"], "C1")

    def test_warn_to_fail_progression_same_plan(self):
        """§5.4 #8: 同一计划 —— 载体被删后 C2 WARN → C1 FAIL 渐进对."""
        with tempfile.TemporaryDirectory() as td:
            repo = _mk_repo(td, workflows=(".github/workflows/ci.yml",))
            plan = _plan(CLAIM_BUILT)
            with _remote("empty"):
                r_warn = vw.check_ci_evidence(
                    plan_content=plan, repo_root=repo)
            self.assertEqual(r_warn["verdict"], "WARN")
            self.assertEqual(r_warn["warnings"][0]["rule"], "C2")
            (repo / ".github" / "workflows" / "ci.yml").unlink()
            r_fail = vw.check_ci_evidence(plan_content=plan, repo_root=repo)
            self.assertEqual(r_fail["verdict"], "FAIL")
            self.assertEqual(r_fail["violations"][0]["rule"], "C1")

    def test_c3_run_claim_without_carrier_warns(self):
        """DEC-156 (review-FIX-267-R0 P1-1): 声称已跑 + 无载体 → C3 WARN
        （称已跑但本地无法证实——无载体即不可证实；fail-safe 与 §3.5 C3
        一致，不升 FAIL）；不出现在 violations / 不走 C1 分支。"""
        with tempfile.TemporaryDirectory() as td:
            r = vw.check_ci_evidence(
                plan_content=_plan(CLAIM_RUN), repo_root=_mk_repo(td))
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])          # never C1 for run
        self.assertEqual([w["rule"] for w in r["warnings"]], ["C3"])
        self.assertIn("无法证实", r["warnings"][0]["reason"])

    def test_built_and_run_claims_without_carrier_mixed(self):
        """已建 + 已跑 + 无载体 → C1 FAIL (built) 与 C3 WARN (run) 并存. """
        with tempfile.TemporaryDirectory() as td:
            r = vw.check_ci_evidence(
                plan_content=_plan(CLAIM_BUILT, CLAIM_RUN),
                repo_root=_mk_repo(td))
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual([v["rule"] for v in r["violations"]], ["C1"])
        self.assertEqual([w["rule"] for w in r["warnings"]], ["C3"])

    def test_english_ci_substring_not_a_claim(self):
        """P2-1 词边界: ACID/SCIENCE/SPECIFIC 型英文词含 CI 子串 + 肯定
        标记（如「specific 已配置」）不得构成假 built claim —— 无载体
        → PASS (no C1)."""
        with tempfile.TemporaryDirectory() as td:
            r = vw.check_ci_evidence(
                plan_content=_plan(
                    "The specific 门禁策略 已配置 for all checks — "
                    "ACID/SCIENCE/SPECIFIC 词内均含 C-I 字母序列"),
                repo_root=_mk_repo(td))
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["built_claims"], 0)
        self.assertEqual(r["stats"]["built_notrun_claims"], 0)
        self.assertEqual(r["stats"]["run_claims"], 0)
        self.assertEqual(r["violations"], [])

    def test_run_marker_with_negation_without_built_marker(self):
        """P2-2: run 标记 + 否定词且无 built 标记的行（「CI 已跑但从未
        真跑」）→ 归「声称已建未跑」（design :343 意图——存在性隐含 +
        未跑自认），不静默丢弃 → 无载体 C1 FAIL / 有载体无 remote C2 WARN."""
        with tempfile.TemporaryDirectory() as td:
            r = vw.check_ci_evidence(
                plan_content=_plan("CI 已跑但从未真跑（本地无记录）"),
                repo_root=_mk_repo(td))
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["violations"][0]["rule"], "C1")
        self.assertEqual(r["stats"]["built_notrun_claims"], 1)
        self.assertEqual(r["stats"]["run_claims"], 0)
        with tempfile.TemporaryDirectory() as td2:
            repo = _mk_repo(td2, workflows=(".github/workflows/ci.yml",))
            with _remote("empty"):
                r2 = vw.check_ci_evidence(
                    plan_content=_plan("CI 已跑但从未真跑（本地无记录）"),
                    repo_root=repo)
        self.assertEqual(r2["verdict"], "WARN")
        self.assertEqual(r2["warnings"][0]["rule"], "C2")

    def test_deep_monorepo_glob_probe(self):
        """§5.4 #6: monorepo 深路径 `**/.github/workflows/*` → carrier 命中."""
        with tempfile.TemporaryDirectory() as td:
            repo = _mk_repo(
                td, workflows=("services/app/.github/workflows/ci.yml",))
            with _remote("ok"):
                r = vw.check_ci_evidence(
                    plan_content=_plan(NO_CI_TEXT), repo_root=repo)
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["carrier_exists"], True)
        self.assertEqual(r["stats"]["workflow_files"], 1)

    def test_gitlab_ci_probe(self):
        """§5.4 #5: `.gitlab-ci.yml` 存在 → 视为有 CI 载体."""
        with tempfile.TemporaryDirectory() as td:
            repo = _mk_repo(td, gitlab=True)
            with _remote("ok"):
                r = vw.check_ci_evidence(
                    plan_content=_plan(NO_CI_TEXT), repo_root=repo)
        self.assertEqual(r["stats"]["carrier_exists"], True)
        self.assertEqual(r["stats"]["gitlab_ci"], True)

    def test_jenkinsfile_probe(self):
        """Jenkinsfile 存在 → 视为有 CI 载体."""
        with tempfile.TemporaryDirectory() as td:
            repo = _mk_repo(td, jenkins=True)
            with _remote("ok"):
                r = vw.check_ci_evidence(
                    plan_content=_plan(NO_CI_TEXT), repo_root=repo)
        self.assertEqual(r["stats"]["carrier_exists"], True)
        self.assertEqual(r["stats"]["jenkinsfile"], True)

    def test_nested_git_repo_workflows_excluded(self):
        """嵌套 git 仓库边界: vendored/scratch 子仓库（自带 .git）的
        workflow 不属于项目 —— 不计数（router 实况:
        .inspect-vision-router / .tmp-research/dsh-codex-connect 是独立
        仓库；router 自身零 tracked workflow）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            vendor = root / "vendor" / "dep"
            vendor.mkdir(parents=True)
            (vendor / ".git").mkdir()          # nested repository marker
            wf = vendor / ".github" / "workflows" / "ci.yml"
            wf.parent.mkdir(parents=True)
            wf.write_text("name: ci\n", encoding="utf-8")
            with _remote("ok"):
                r = vw.check_ci_evidence(
                    plan_content=_plan(NO_CI_TEXT), repo_root=root)
        self.assertEqual(r["stats"]["carrier_exists"], False)
        self.assertEqual(r["stats"]["workflow_files"], 0)
        self.assertEqual(r["verdict"], "PASS")   # C4: 无声明无载体

    def test_monorepo_subdir_without_nested_git_counts(self):
        """monorepo 边界对照: 项目自身 git 树内的子目录 workflow（无嵌套
        .git）→ 计数（host project/.github/workflows 实况）。"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wf = root / "project" / ".github" / "workflows" / "check.yml"
            wf.parent.mkdir(parents=True)
            wf.write_text("name: ci\n", encoding="utf-8")
            with _remote("ok"):
                r = vw.check_ci_evidence(
                    plan_content=_plan(NO_CI_TEXT), repo_root=root)
        self.assertEqual(r["stats"]["carrier_exists"], True)
        self.assertEqual(r["stats"]["workflow_files"], 1)

    def test_git_unavailable_warns_not_fails(self):
        """§5.4 #7 / design: git 不可用（无 .git）→ remote fail-safe WARN
        不 FAIL（真实 _git_remote_state 路径，无 mock）。"""
        with tempfile.TemporaryDirectory() as td:
            repo = _mk_repo(td, workflows=(".github/workflows/ci.yml",))
            r = vw.check_ci_evidence(
                plan_content=_plan(NO_CLAIM_CI_TEXT), repo_root=repo)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["warnings"][0]["rule"], "C2")
        self.assertEqual(r["stats"]["remote_state"], "unable")
        self.assertEqual(r["violations"], [])

    def test_declaration_boundary_no_false_positive(self):
        """声明识别边界: CI 字样但无肯定声明（检查/描述/纯否定）→ 不误判
        为声明 → 无载体 → PASS (no C1)."""
        with tempfile.TemporaryDirectory() as td:
            r = vw.check_ci_evidence(
                plan_content=_plan(DESCRIPTIVE_CI_TEXT),
                repo_root=_mk_repo(td))
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["built_claims"], 0)
        self.assertEqual(r["stats"]["built_notrun_claims"], 0)
        self.assertEqual(r["stats"]["run_claims"], 0)
        self.assertEqual(r["violations"], [])

    def test_rule_text_quoting_check_semantics_not_a_claim(self):
        """声明识别边界: REQ/FIX 行引用检查自身的失败语义（→ FAIL/→ WARN）
        是规则描述，不是项目状态声明 —— 不构成 claim → 无载体 PASS
        （防「引用规则文本的项目被误 C1」；host REQ-145.5 行实况）。"""
        with tempfile.TemporaryDirectory() as td:
            r = vw.check_ci_evidence(
                plan_content=_plan(RULE_TEXT_CI),
                repo_root=_mk_repo(td))
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["built_claims"], 0)
        self.assertEqual(r["stats"]["built_notrun_claims"], 0)
        self.assertEqual(r["violations"], [])


# ── Live mode: facts root = HOST_PROJECT_ROOT (FIX-270) ─────────────────

class Check38LiveModeTests(unittest.TestCase):
    """Live plan read via SAMPLE_PATH; repo_root default = HOST_PROJECT_ROOT."""

    def test_repo_root_defaults_to_host_project_root(self):
        """repo_root=None → carrier/remote probes receive HOST_PROJECT_ROOT
        (FIX-270 mixed-root semantics — never the plugin ROOT)."""
        with mock.patch.object(cd, "_probe_workflow_carriers",
                               return_value=([], False, False)) as m_probe, \
             mock.patch.object(cd, "_git_remote_state",
                               return_value="ok") as m_remote:
            r = vw.check_ci_evidence(
                plan_content=_plan(NO_CI_TEXT), repo_root=None)
        self.assertEqual(m_probe.call_args.args[0], vw.HOST_PROJECT_ROOT)
        self.assertEqual(m_remote.call_args.args[0], vw.HOST_PROJECT_ROOT)
        self.assertEqual(r["verdict"], "PASS")

    def test_live_plan_reads_sample_path(self):
        """plan_content=None → live read of SAMPLE_PATH (host plan-tracker)."""
        with tempfile.TemporaryDirectory() as td:
            tracker = Path(td) / "plan-tracker.md"
            tracker.write_text(_plan(CLAIM_BUILT), encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(cd, "_probe_workflow_carriers",
                                   return_value=([], False, False)), \
                 _remote("ok"):
                r = vw.check_ci_evidence()   # no plan_content, no repo_root
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["violations"][0]["rule"], "C1")
        self.assertEqual(r["stats"]["plan_lines_scanned"], 1)


# ── Contract: shape, never-raise, no-plan, numbering, export ────────────

class Check38ContractTests(unittest.TestCase):
    """Result shape, never-raise contract, numbering (F9), domain export."""

    def test_result_contract_shape(self):
        r = vw.check_ci_evidence(
            plan_content=_plan(CLAIM_BUILT),
            repo_root="Z:/definitely/missing/repo")
        self.assertEqual(
            set(r.keys()),
            {"verdict", "reason", "violations", "warnings", "stats"})
        self.assertIn(r["verdict"], ("PASS", "WARN", "FAIL", "no-verdict"))
        for key in ("plan_lines_scanned", "built_claims",
                    "built_notrun_claims", "run_claims", "carrier_exists",
                    "workflow_files", "gitlab_ci", "jenkinsfile",
                    "remote_state", "warn_count", "violation_count"):
            self.assertIn(key, r["stats"], f"stats.{key} missing")

    def test_no_plan_tracker_degrades_no_verdict(self):
        """无计划 → no-verdict: missing SAMPLE_PATH live read must not
        raise (safe no-verdict)."""
        with mock.patch.object(vw, "SAMPLE_PATH",
                               Path("Z:/missing/plan-tracker.md")), \
             mock.patch.object(cd, "_probe_workflow_carriers",
                               return_value=([], False, False)), \
             mock.patch.object(cd, "_git_remote_state", return_value="ok"):
            r = vw.check_ci_evidence()
        self.assertEqual(r["verdict"], "no-verdict")
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])
        self.assertIn("plan-tracker.md not found", r["reason"])

    def test_unreadable_plan_tracker_degrades_no_verdict(self):
        """Unreadable live read (OSError) → no-verdict, never raise."""
        with tempfile.TemporaryDirectory() as td:
            tracker = Path(td) / "plan-tracker.md"
            tracker.write_text("anything", encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker), \
                 mock.patch.object(
                     Path, "read_text",
                     side_effect=OSError("boom")), \
                 mock.patch.object(cd, "_probe_workflow_carriers",
                                   return_value=([], False, False)), \
                 mock.patch.object(cd, "_git_remote_state",
                                   return_value="ok"):
                r = vw.check_ci_evidence()
        self.assertEqual(r["verdict"], "no-verdict")
        self.assertIn("unreadable", r["reason"])

    def test_never_raises_on_garbage_inputs(self):
        """Never raise: non-text plan, bad repo roots, odd shapes — every
        path returns the contract dict (P2-3: SAMPLE_PATH mocked — no
        dependence on the real host plan-tracker)."""
        with mock.patch.object(vw, "SAMPLE_PATH",
                               Path("Z:/missing/plan-tracker.md")), \
             mock.patch.object(cd, "_probe_workflow_carriers",
                               return_value=([], False, False)), \
             mock.patch.object(cd, "_git_remote_state", return_value="ok"):
            cases = [
                dict(plan_content=12345, repo_root=None),
                dict(plan_content=[], repo_root=None),
                dict(plan_content={"CI": "已建"}, repo_root=None),
                dict(plan_content="CI 已建".encode("utf-8"),
                     repo_root=None),                       # bytes
                dict(plan_content=_plan(CLAIM_BUILT), repo_root="Z:/missing"),
                dict(plan_content=_plan(CLAIM_BUILT), repo_root=12345),
                dict(plan_content=_plan(CLAIM_BUILT), repo_root=None),
                dict(plan_content="", repo_root=None),
                dict(plan_content=None, repo_root=None),
            ]
            for kwargs in cases:
                r = vw.check_ci_evidence(**kwargs)
                self.assertIn(
                    r["verdict"], ("PASS", "WARN", "FAIL", "no-verdict"),
                    f"kwargs={kwargs!r} -> {r['verdict']}")
                self.assertIsInstance(r["violations"], list)
                self.assertIsInstance(r["warnings"], list)

    def test_never_raises_repo_root_non_pathlike_unmocked(self):
        """P0-1 red→green: NON-pathlike repo_root (int) must never raise —
        exercised WITHOUT mocked probes (the mocked garbage test above
        would mask a TypeError in Path(repo_root), which the old except
        tuple (OSError/RuntimeError/ValueError) does NOT catch). The live
        guard degrades to a fail-safe no-verdict stating the invalid root."""
        with tempfile.TemporaryDirectory() as td:
            tracker = Path(td) / "plan-tracker.md"
            tracker.write_text(_plan(CLAIM_BUILT), encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", tracker):
                r = vw.check_ci_evidence(
                    plan_content=_plan(CLAIM_BUILT), repo_root=12345)
        self.assertEqual(r["verdict"], "no-verdict")
        self.assertIn("repo_root", r["reason"])
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])

    def test_check38_block_position_and_numbering(self):
        """Check 38 block exists, numbered, between Check 37 and the summary."""
        src = (_INFRA_DIR / "verify_workflow.py").read_text(encoding="utf-8")
        block38 = "┌─ Check 38: CI Evidence (FIX-267)"
        self.assertIn(block38, src)
        self.assertLess(src.index("┌─ Check 37: Gate Sequence for Release"),
                        src.index(block38))
        self.assertLess(src.index(block38),
                        src.index("┌─ Governance Health Summary"))

    def test_check35_36_37_38_no_interleaving(self):
        """Check 35 / 36 / 37 / 38 blocks appear in ascending order with no
        interleaving."""
        src = (_INFRA_DIR / "verify_workflow.py").read_text(encoding="utf-8")
        markers = ["┌─ Check 35: Snapshot Freshness",
                   "┌─ Check 36: Risk Mitigation Closure",
                   "┌─ Check 37: Gate Sequence for Release",
                   "┌─ Check 38: CI Evidence"]
        idx = [src.index(m) for m in markers]
        self.assertEqual(idx, sorted(idx), "Check 35/36/37/38 out of order")

    def test_check38_exported_and_function_lives_in_ci_domain(self):
        domain = (_INFRA_DIR / "checks" / "ci_domain.py").read_text(
            encoding="utf-8")
        self.assertIn("def check_ci_evidence", domain)
        self.assertIn("def _probe_workflow_carriers", domain)
        self.assertIn("def _git_remote_state", domain)
        self.assertTrue(hasattr(vw, "check_ci_evidence"))

    def test_check38_import_export_placed_with_domain_imports(self):
        src = (_INFRA_DIR / "verify_workflow.py").read_text(encoding="utf-8")
        self.assertIn("from checks.ci_domain import (", src)
        idx_import = src.index("from checks.ci_domain import (")
        idx_block = src.index("┌─ Check 38")
        self.assertLess(idx_import, idx_block)


if __name__ == "__main__":
    unittest.main()
