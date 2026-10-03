"""Regression guard for the C-10 evidence-binding drift face (FEAT-069).

FEAT-068 Code Review R0 finding F-1: ``check_evidence_binding_drift`` and its
renderer (``checks/evidence_domain.py`` C-10 enforcement logic) shipped with
ZERO pytest coverage — only a %TEMP% manual smoke existed. This file closes
that gap with the eight-branch matrix the review mandated. Every test method
carries an ``R0 F-1 #N`` anchor comment naming the branch it guards.

Also guards, in the same batch (FEAT-069):
  - R0 F-2 — the MIGRATION version-prefix boundary tightening
    (``MIGRATION-<ver>`` must anchor its FOLLOWING delimiter; a strict prefix
    of a longer row version must never bind — the old ``\\b`` tail false-bound
    across version segments, a fail-open direction).
  - E-6 compatibility surface — the C-10 evidence binding is stamp-agnostic
    (a runtime binds the ``MIGRATION-<its own stamp>`` row) and the evidence
    row prefix regex accepts the bumped ``MIGRATION_VERSION`` stamp.
  - ADR-RB-2 two-face goal-layer contract gate (factory WARN form): face ①
    host-activation precondition + face ② sensitive-action gate judge.
    FIX-431: 发布间隙态（无活跃 P0/P1 unit）→ 两 face 判 N/A 不发 WARN；
    有活跃 unit 的运行期判定链（PASS/WARN/BLOCK）零变化——正负用例同册守护。

ALL tests use ``tempfile.TemporaryDirectory`` — the real ``.governance/`` is
NEVER touched. Assertions are content-based only (no wall-clock; RISK-048).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_evidence_binding_drift.py -v
or:
    python -m unittest skills.software-project-governance.infra.tests.test_evidence_binding_drift -v
"""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402
import checks.evidence_domain as ed  # noqa: E402
import loop_migration as lm  # noqa: E402
from loop_migration_plan import (  # noqa: E402
    build_migration_plan,
    confirm_decomposition,
    plan_to_payload,
)


# ─── Shared fixtures ─────────────────────────────────────────────────────────

# A known-good product_success_contract (same shape the Check 18d tests in
# test_verify_workflow.py use — it passes _validate_product_success_contract).
VALID_CONTRACT = {
    "user": "AI-assisted product owner using the governance workflow for release planning",
    "job_to_be_done": "Keep AI coding work tied to explicit user outcomes before implementation starts",
    "non_goals": [
        "Do not expand the task into unrelated release automation changes",
        "Do not treat evidence-log updates as a substitute for user-visible quality",
    ],
    "success_metrics": [
        "User-visible acceptance scenario is captured for the active task before code changes continue",
        "Runnable E2E validation command passes and proves the acceptance scenario is still satisfied",
    ],
    "competitive_baseline": "Mature software teams require explicit acceptance criteria and validation before implementation closure",
    "done_definition": [
        "Product success evidence is recorded with concrete facts",
        "Independent review confirms the user outcome is not replaced by process completion",
    ],
}

_DEMO_TASK_ID = "FIX-099"

_MIGRATION_STAMP = lm.MIGRATION_VERSION  # E-6: stamp-agnostic fixtures


def _plan_tracker_text(goal_face=True, with_active_task=True):
    """Minimal host plan-tracker: goal face + one active P1 task row."""
    lines = [
        "# Plan Tracker — demo-host",
        "## 项目配置",
        "- workflow_model: classic-phase-gate",
    ]
    if goal_face:
        lines += [
            "## 项目总览",
            "",
            "| 项目 | 当前阶段 |",
            "| --- | --- |",
            "| demo-host | 维护与演进 |",
        ]
    if with_active_task:
        lines += [
            "## 当前活跃事项",
            "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |",
            "|--------|----|------|------|---------|---------|------|",
            "| **P1** | {0} | Demo unit for RB-2 gate fixtures | - | 0.90.0 "
            "| fixture | 📋 待启动 |".format(_DEMO_TASK_ID),
        ]
    return "\n".join(lines) + "\n"


def _evidence_log_text(with_migration_row=True, migration_row=None):
    """Minimal evidence-log; the MIGRATION row mirrors loop_migration's shape."""
    lines = [
        "| 编号 | 事项 | 说明 |",
        "| --- | --- | --- |",
        "| EVD-001 | init | seeded evidence log |",
    ]
    if with_migration_row:
        if migration_row is None:
            migration_row = (
                "| MIGRATION-{0} | FX-191 | migrated classic-phase-gate -> "
                "loop-engineering | backup=migration-{0}-test |".format(
                    _MIGRATION_STAMP))
        lines.append(migration_row)
    return "\n".join(lines) + "\n"


def _seed_gov(gov_dir, plan_text=None, evidence_text=None):
    """Create the .governance dir and write the plan/evidence faces."""
    gov_dir.mkdir(parents=True, exist_ok=True)
    (gov_dir / "plan-tracker.md").write_text(
        plan_text if plan_text is not None else _plan_tracker_text(),
        encoding="utf-8")
    (gov_dir / "evidence-log.md").write_text(
        evidence_text if evidence_text is not None else _evidence_log_text(),
        encoding="utf-8")
    return gov_dir


def _build_valid_runtime(gov_dir, migration_version=_MIGRATION_STAMP,
                         flatten_dependencies=False):
    """Build a contract-valid v2 runtime payload via the REAL planner.

    Same chain apply uses: build_migration_plan → confirm_decomposition →
    plan_to_payload. Fully content-deterministic for a fixed fixture text.
    Seeds the plan/evidence faces first so the planner can read them.
    """
    _seed_gov(gov_dir)
    host_root = str(gov_dir.parent)
    plan_text = (gov_dir / "plan-tracker.md").read_text(encoding="utf-8")
    plan = build_migration_plan(host_root, None, plan_tracker_text=plan_text)
    confirmed = confirm_decomposition(plan)
    payload = plan_to_payload(
        confirmed, migration_version=migration_version,
        migration_timestamp="2026-09-27T00:00:00Z",
    )
    if flatten_dependencies:
        for unit in payload["flow_units"]:
            unit["dependencies"] = []
    return payload


class _HostFixture:
    """A temp host with a .governance/ dir; patches the vw faces on enter."""

    def __init__(self, tmp, plan_text=None, plan_bytes=None,
                 evidence_text=None, runtime=None, packets=None):
        self.root = Path(tmp)
        self.gov = self.root / ".governance"
        _seed_gov(self.gov,
                  plan_text=plan_text, evidence_text=evidence_text)
        if plan_bytes is not None:
            (self.gov / "plan-tracker.md").write_bytes(plan_bytes)
        if runtime is not None:
            (self.gov / "flow-unit-runtime.json").write_text(
                json.dumps(runtime, ensure_ascii=False, indent=2),
                encoding="utf-8")
        if packets is not None:
            (self.gov / "execution-packets.json").write_text(
                json.dumps({"version": 1, "packets": packets},
                           ensure_ascii=False),
                encoding="utf-8")

    def __enter__(self):
        self._patches = [
            mock.patch.object(vw, "GOVERNANCE_DIR", self.gov),
            mock.patch.object(vw, "SAMPLE_PATH",
                              self.gov / "plan-tracker.md"),
            mock.patch.object(vw, "EXECUTION_PACKET_PATH",
                              self.gov / "execution-packets.json"),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc_info):
        for p in reversed(self._patches):
            p.stop()
        return False


def _fail_types(block):
    return [issue["type"] for issue in block.get("fail", [])]


def _warn_types(block):
    return [issue["type"] for issue in block.get("warn", [])]


# ═══════════════════════════════════════════════════════════════════════════
# The eight C-10 branches (R0 F-1) + renderer
# ═══════════════════════════════════════════════════════════════════════════


class TestEvidenceBindingDriftEightBranches(unittest.TestCase):
    """check_evidence_binding_drift — the R0 F-1 eight-branch matrix."""

    def test_branch1_not_applicable_when_runtime_absent(self):
        # R0 F-1 #1 (not-applicable): no flow-unit-runtime.json → the machine
        # face is absent (pre-switch host) → applicable=False, zero issues.
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(td, runtime=None):
                block = ed.check_evidence_binding_drift()
        self.assertFalse(block["applicable"])
        self.assertTrue(block["pass"])
        self.assertEqual(block["fail"], [])
        self.assertEqual(block["warn"], [])
        self.assertIsNone(block["runtime_path"])

    def test_branch2_valid_runtime_passes_clean(self):
        # R0 F-1 #2 (有效 PASS): valid runtime + its MIGRATION row + plan
        # re-derivation in sync → applicable=True, zero fail, zero warn.
        with tempfile.TemporaryDirectory() as td:
            runtime = _build_valid_runtime(Path(td) / ".governance")
            with _HostFixture(td, runtime=runtime):
                block = ed.check_evidence_binding_drift()
        self.assertTrue(block["applicable"])
        self.assertTrue(block["pass"])
        self.assertEqual(block["fail"], [],
                         "unexpected fails: {0}".format(block["fail"]))
        self.assertEqual(block["warn"], [],
                         "unexpected warns: {0}".format(block["warn"]))

    def test_branch3_missing_migration_row_fails(self):
        # R0 F-1 #3 (缺 MIGRATION 行 FAIL): runtime claims its stamp but the
        # evidence face carries no MIGRATION row → evidence_binding_missing.
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            runtime = _build_valid_runtime(gov)
            with _HostFixture(td, runtime=runtime,
                              evidence_text=_evidence_log_text(
                                  with_migration_row=False)):
                block = ed.check_evidence_binding_drift()
        self.assertFalse(block["pass"])
        self.assertIn("evidence_binding_missing", _fail_types(block))

    def test_branch4_bad_plan_hash_fails(self):
        # R0 F-1 #4 (坏 hash FAIL): migration_plan_hash not 64-hex →
        # runtime_face_missing_machine_credential (产物版本绑定缺失).
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            runtime = _build_valid_runtime(gov)
            runtime["migration_plan_hash"] = "deadbeef"
            with _HostFixture(td, runtime=runtime):
                block = ed.check_evidence_binding_drift()
        self.assertFalse(block["pass"])
        self.assertIn("runtime_face_missing_machine_credential",
                      _fail_types(block))
        hash_fails = [issue for issue in block["fail"]
                      if "migration_plan_hash" in issue.get("detail", "")]
        self.assertTrue(hash_fails,
                        "hash detail missing: {0}".format(block["fail"]))

    def test_branch5_dangling_dependency_fails(self):
        # R0 F-1 #5 (悬空依赖 FAIL): a dependency outside the unit set →
        # runtime_unit_corrupt with the 悬空依赖 detail.
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            runtime = _build_valid_runtime(gov, flatten_dependencies=True)
            runtime["flow_units"][0]["dependencies"] = ["ghost-unit"]
            with _HostFixture(td, runtime=runtime):
                block = ed.check_evidence_binding_drift()
        self.assertFalse(block["pass"])
        self.assertIn("runtime_unit_corrupt", _fail_types(block))
        dangling = [issue for issue in block["fail"]
                    if "悬空依赖" in issue.get("detail", "")]
        self.assertTrue(dangling,
                        "dangling-dep detail missing: {0}".format(
                            block["fail"]))

    def test_branch6_gate_schema_none_guard_suppresses_drift_warn(self):
        # R0 F-1 #6 (gate_schema None-guard): the real v2 payload does NOT
        # persist a top-level gate_schema — the None-guard must suppress the
        # gate_schema_drift WARN (策略版本经 plan hash 传递绑定). Contrast arm:
        # a present-but-stale gate_schema DOES warn, proving the suppression
        # is the None-guard and not a dead branch.
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            runtime = _build_valid_runtime(gov)
            self.assertNotIn("gate_schema", runtime)  # real payload shape
            with _HostFixture(td, runtime=runtime):
                block = ed.check_evidence_binding_drift()
            self.assertNotIn("gate_schema_drift", _warn_types(block))
            # Contrast: a stale top-level gate_schema warns.
            runtime_stale = json.loads(json.dumps(runtime))
            runtime_stale["gate_schema"] = "loop-gate-schema-v1@stale0000"
            with _HostFixture(td, runtime=runtime_stale):
                block_stale = ed.check_evidence_binding_drift()
        self.assertIn("gate_schema_drift", _warn_types(block_stale))

    def test_branch7_unit_set_drift_warns_without_fail(self):
        # R0 F-1 #7 (unit_set_drift WARN): runtime unit set differs from the
        # re-derived plan (legal plan-tracker evolution, runtime not re-synced)
        # → WARN-grade drift, pass stays True.
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            runtime = _build_valid_runtime(gov, flatten_dependencies=True)
            self.assertGreaterEqual(len(runtime["flow_units"]), 1)
            runtime["flow_units"][0]["flow_unit_id"] = "renamed-away-unit"
            with _HostFixture(td, runtime=runtime):
                block = ed.check_evidence_binding_drift()
        self.assertTrue(block["pass"])
        self.assertIn("unit_set_drift", _warn_types(block))
        self.assertNotIn("runtime_unit_corrupt", _fail_types(block))

    def test_branch8_plan_read_failure_warns(self):
        # R0 F-1 #8 (plan 读取失败 WARN): the plan face is unreadable → the
        # drift comparison degrades to a WARN (计划面重派生失败), never a FAIL.
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            runtime = _build_valid_runtime(gov)
            with _HostFixture(td, plan_bytes=b"\xff\xfe-not-valid-utf8-\xff",
                              runtime=runtime):
                block = ed.check_evidence_binding_drift()
        self.assertTrue(block["pass"])
        drift_warns = [issue for issue in block.get("warn", [])
                       if "计划面重派生失败" in issue.get("detail", "")]
        self.assertTrue(drift_warns,
                        "plan-read-failure warn missing: {0}".format(
                            block["warn"]))


class TestEvidenceBindingDriftRenderer(unittest.TestCase):
    """F-1 covers 检查+渲染器 — the Check 3b renderer face is guarded too."""

    def test_renderer_pass_shape_and_zero_count(self):
        with tempfile.TemporaryDirectory() as td:
            runtime = _build_valid_runtime(Path(td) / ".governance")
            with _HostFixture(td, runtime=runtime):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    count = ed.render_evidence_binding_drift_block(7)
        self.assertEqual(count, 7)  # PASS adds no issues
        self.assertIn("[PASS] Machine-maintained faces match legal "
                      "writers (C-10).", buf.getvalue())

    def test_renderer_counts_fail_and_renders_warn_without_count(self):
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            runtime = _build_valid_runtime(gov, flatten_dependencies=True)
            runtime["migration_plan_hash"] = "deadbeef"  # FAIL face
            runtime["flow_units"][0]["flow_unit_id"] = "renamed-away-unit"
            with _HostFixture(td, runtime=runtime):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    count = ed.render_evidence_binding_drift_block(1)
        self.assertEqual(count, 2)  # +1 FAIL (bad hash); the WARN adds none
        self.assertIn("[FAIL] runtime_face_missing_machine_credential",
                      buf.getvalue())
        self.assertIn("[WARN] unit_set_drift", buf.getvalue())


# ═══════════════════════════════════════════════════════════════════════════
# R0 F-2 — MIGRATION version-prefix boundary
# ═══════════════════════════════════════════════════════════════════════════


class TestF2MigrationPrefixBoundary(unittest.TestCase):
    """R0 F-2: ``MIGRATION-<ver>\\b`` could false-bind ACROSS version
    segments (runtime ver "0.65" vs row MIGRATION-0.65.0 → the old regex
    matched and silently skipped the evidence_binding_missing FAIL — a
    fail-open direction). The tightened anchor requires a FOLLOWING
    delimiter (table pipe / whitespace / end-of-line)."""

    def _block_for(self, runtime_version, migration_row):
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            runtime = _build_valid_runtime(gov)
            runtime["migration_version"] = runtime_version
            with _HostFixture(
                    td, runtime=runtime,
                    evidence_text=_evidence_log_text(
                        with_migration_row=True, migration_row=migration_row)):
                return ed.check_evidence_binding_drift()

    def test_f2_version_prefix_of_longer_row_does_not_bind(self):
        # Positive tightening case: a version PREFIX of the row version must
        # NOT satisfy the evidence binding (the old \\b false-bound here).
        block = self._block_for(
            "0.65",
            "| MIGRATION-0.65.0 | FX-191 | migrated classic-phase-gate -> "
            "loop-engineering | backup=migration-0.65.0-test |")
        self.assertIn("evidence_binding_missing", _fail_types(block))

    def test_f2_exact_version_row_still_binds(self):
        # Negative (regression) case: the legitimate exact-version bind must
        # keep working after the tightening.
        block = self._block_for(
            "0.65.0",
            "| MIGRATION-0.65.0 | FX-191 | migrated classic-phase-gate -> "
            "loop-engineering | backup=migration-0.65.0-test |")
        self.assertNotIn("evidence_binding_missing", _fail_types(block))

    def test_f2_overrun_segment_does_not_bind(self):
        # A row carrying a LONGER version (0.65.01) never satisfies a 0.65.0
        # runtime — segment overrun is rejected, not truncated.
        block = self._block_for(
            "0.65.0",
            "| MIGRATION-0.65.01 | FX-191 | migrated classic-phase-gate -> "
            "loop-engineering | backup=x |")
        self.assertIn("evidence_binding_missing", _fail_types(block))

    def test_f2_row_at_end_of_line_still_binds(self):
        # A MIGRATION row with no trailing pipe (bare end-of-line) still
        # binds — the delimiter class includes end-of-line.
        block = self._block_for("0.65.0", "| MIGRATION-0.65.0")
        self.assertNotIn("evidence_binding_missing", _fail_types(block))


# ═══════════════════════════════════════════════════════════════════════════
# E-6 — MIGRATION_VERSION stamp compatibility surface
# ═══════════════════════════════════════════════════════════════════════════


class TestE6MigrationStampCompatibility(unittest.TestCase):
    """E-6 (fullchain §7): the semantic stamp may be bumped (0.65.0 →
    0.90.0). These guards pin the compatibility surface the bump relies on —
    stamp-agnostic binding, row-shape acceptance, and rollback stamping from
    the backup dir (not from the constant)."""

    def test_e6_c10_binding_is_stamp_agnostic(self):
        # A runtime binds the MIGRATION-<its own stamp> row, whatever the
        # constant currently is — old stamped runtimes keep binding.
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            runtime = _build_valid_runtime(gov, migration_version="9.9.9")
            with _HostFixture(
                    td, runtime=runtime,
                    evidence_text=_evidence_log_text(
                        with_migration_row=True,
                        migration_row="| MIGRATION-9.9.9 | FX-191 | migrated "
                                      "classic-phase-gate -> loop-engineering "
                                      "| backup=b |")):
                block = ed.check_evidence_binding_drift()
        self.assertNotIn("evidence_binding_missing", _fail_types(block))

    def test_e6_evidence_row_prefix_regex_accepts_current_stamp(self):
        # loop_migration._EVIDENCE_ROW_PREFIX_RE must keep accepting the
        # MIGRATION/ROLLBACK rows for the CURRENT stamp (bump-safe). The
        # regex is applied to the extracted FIRST CELL of the markdown row
        # (mirror of _count_evidence_rows' consumption shape).
        def _first_cell(row_line):
            stripped = row_line.strip()
            if stripped.startswith("|"):
                cells = [c.strip() for c in stripped.split("|")]
                return next((c for c in cells if c), "")
            return stripped

        migration_row = "| MIGRATION-{0} | FX-191 | migrated | backup=b |".format(
            lm.MIGRATION_VERSION)
        self.assertIsNotNone(
            lm._EVIDENCE_ROW_PREFIX_RE.match(_first_cell(migration_row)),
            migration_row)
        rollback_row = ("| ROLLBACK-{0} | FX-191 | rolled back | "
                        "restored_from=b |").format(lm.MIGRATION_VERSION)
        self.assertIsNotNone(
            lm._EVIDENCE_ROW_PREFIX_RE.match(_first_cell(rollback_row)),
            rollback_row)

    def test_e6_rollback_row_stamps_from_backup_dir_not_constant(self):
        # Source-level compatibility anchor: rollback stamps ROLLBACK-<version>
        # from the selected backup dir entry (backup_version), so pre-bump
        # backups roll back with their original stamp even after a bump.
        source = Path(lm.__file__).read_text(encoding="utf-8")
        self.assertIn("ver=backup_version", source)


# ═══════════════════════════════════════════════════════════════════════════
# ADR-RB-2 — two-face goal-layer contract gate (factory WARN form)
# ═══════════════════════════════════════════════════════════════════════════


class TestRB2ActivationPrecondition(unittest.TestCase):
    """Face ① — host-activation precondition (ADR-019 §4 RB-2 mitigation):
    at least one unit's product_success_contract is non-TO_BE_DEFINED AND
    traceable to the plan-tracker goal face. Factory form: WARN-grade."""

    def _packets(self, contract):
        return {
            _DEMO_TASK_ID: {
                "task_id": _DEMO_TASK_ID,
                "product_success_contract": contract,
            },
        }

    def test_precondition_met_on_filled_contract(self):
        # Positive sample: filled contract + goal face → precondition met,
        # zero WARN (the real repo must render exactly this shape).
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets=self._packets(VALID_CONTRACT)):
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertTrue(readiness["plan_tracker_goal_face"])
        self.assertEqual(readiness["contract_ready_units"], [_DEMO_TASK_ID])
        self.assertTrue(readiness["precondition_met"])
        self.assertEqual(readiness["warn"], [])

    def test_precondition_rejects_placeholder_contract_host(self):
        # Negative sample: the REAL TO_BE_DEFINED template (via
        # build_execution_packet) must NOT satisfy the precondition.
        template = vw.build_execution_packet({
            "task_id": _DEMO_TASK_ID,
            "title": "Demo unit",
            "priority": "P1",
            "status": "📋 待启动",
        })["product_success_contract"]
        self.assertIn("TO_BE_DEFINED", template["user"])  # template sanity
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets=self._packets(template)):
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertFalse(readiness["precondition_met"])  # the 拒绝/WARN 判据
        self.assertFalse(readiness["contract_ready_units"])
        self.assertTrue(readiness["warn"])
        self.assertTrue(any("占位" in w or "TO_BE_DEFINED" in w
                            for w in readiness["warn"]),
                        readiness["warn"])

    def test_precondition_warns_when_goal_face_missing(self):
        # Traceability half: no goal face in the plan-tracker → the contract
        # cannot be traced to plan-tracker success criteria → WARN.
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=False),
                    packets=self._packets(VALID_CONTRACT)):
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertFalse(readiness["plan_tracker_goal_face"])
        self.assertFalse(readiness["precondition_met"])
        self.assertTrue(any("成功标准" in w for w in readiness["warn"]),
                        readiness["warn"])

    def test_precondition_gap_state_judges_na_without_warn(self):
        # FIX-431 正例: 发布间隙态（无活跃 P0/P1 unit——任务表全完成）无判定
        # 对象 → face① 判 N/A，不发「无活跃 P0/P1 unit」WARN（旧实现在此发
        # WARN 且计入渲染块三条之一）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(with_active_task=False),
                    packets={}):
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertFalse(readiness["active_units"])
        self.assertFalse(readiness["precondition_met"])
        self.assertEqual(readiness["warn"], [])  # 间隙态零 WARN

    def test_precondition_gap_state_na_even_without_goal_face(self):
        # 间隙态无判定对象优先于 goal_face 追溯检查——goal_face 缺失 WARN
        # 只在有活跃 unit 的运行期有意义（运行期形态由
        # test_precondition_warns_when_goal_face_missing 守护，零变化）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(
                        goal_face=False, with_active_task=False),
                    packets={}):
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertFalse(readiness["active_units"])
        self.assertFalse(readiness["precondition_met"])
        self.assertEqual(readiness["warn"], [])

    def test_precondition_gap_state_still_discloses_unreadable_packets(self):
        # 间隙态改判 N/A 不吞评估完整性异常：execution packets 不可读仍 WARN
        # （fail-open 披露保持——FIX-431 只重判「无活跃 unit」的判定结论，
        # 不隐藏异常；安全语义不回退）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(with_active_task=False),
                    packets=None):  # 不写 packets 文件 → load_error
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertFalse(readiness["active_units"])
        self.assertFalse(readiness["precondition_met"])
        self.assertTrue(any("不可读" in w for w in readiness["warn"]),
                        readiness["warn"])

    def test_precondition_active_unit_without_contract_still_warns(self):
        # FIX-431 负例: 有活跃 P0/P1 unit 但无 contract → 现行为 WARN 全保持
        # （间隙态 N/A 不得外溢到运行期判定链）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets={}):  # 活跃任务存在、无对应 packet
                readiness = ed.check_goal_layer_contract_readiness()
        self.assertTrue(readiness["active_units"])
        self.assertFalse(readiness["precondition_met"])
        self.assertTrue(any("穿透" in w or "TO_BE_DEFINED" in w
                            for w in readiness["warn"]),
                        readiness["warn"])


class TestRB2SensitiveActionGate(unittest.TestCase):
    """Face ② — contract-missing gate judge: missing → WARN, sensitive
    action (发布/翻转类) → BLOCK judge. Factory: BLOCK is demoted to WARN
    (enforcement off — 真阻断属授权票域, B-12/B-13 precedent)."""

    def test_judge_factory_demotes_block_to_warn_but_keeps_judge(self):
        readiness = {"precondition_met": False}
        j = ed.judge_rb2_contract_gate("release 0.90.0 (发布)", readiness)
        self.assertTrue(j["sensitive"])
        self.assertEqual(j["raw_verdict"], "BLOCK")   # 阻断判据可观测
        self.assertEqual(j["verdict"], "WARN")        # factory 不拦截
        self.assertIn("warn-only", j["enforcement"])

    def test_judge_enforced_flip_blocks_sensitive_action(self):
        readiness = {"precondition_met": False}
        with mock.patch.object(ed, "RB2_SENSITIVE_BLOCK_ENFORCED", True):
            j = ed.judge_rb2_contract_gate("授权票翻转 authorization-flip",
                                           readiness)
        self.assertEqual(j["raw_verdict"], "BLOCK")
        self.assertEqual(j["verdict"], "BLOCK")       # 授权票翻转后真阻断
        self.assertEqual(j["enforcement"], "enforced")

    def test_judge_nonsensitive_contract_missing_warns_not_blocks(self):
        readiness = {"precondition_met": False}
        j = ed.judge_rb2_contract_gate("check-governance", readiness)
        self.assertFalse(j["sensitive"])
        self.assertEqual(j["raw_verdict"], "WARN")
        self.assertEqual(j["verdict"], "WARN")        # 非敏感→WARN 不阻断

    def test_judge_ready_contract_passes_sensitive_action(self):
        readiness = {"precondition_met": True}
        j = ed.judge_rb2_contract_gate("release 0.90.0", readiness)
        self.assertTrue(j["sensitive"])
        self.assertEqual(j["verdict"], "PASS")        # 契约在→放行

    def test_judge_defaults_to_live_host_readiness(self):
        # No readiness passed → the judge consults the REAL host faces.
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True)):
                j = ed.judge_rb2_contract_gate("release 0.90.0")
        # No packets file → contract readiness unmet → would-block family.
        self.assertFalse(j["contract_ready"])

    def test_judge_gap_state_na_for_sensitive_and_nonsensitive(self):
        # FIX-431 正例: 间隙态（无活跃 P0/P1 unit）无判定语境——demo 契约缺
        # 失 WARN/BLOCK 只在有活跃 unit 的运行期才有意义 → sensitive 与
        # non-sensitive 都判 N/A（verdict 与 raw_verdict 同值，不发 WARN）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(with_active_task=False),
                    packets={}):
                readiness = ed.check_goal_layer_contract_readiness()
                j_sensitive = ed.judge_rb2_contract_gate(
                    "release 0.90.0 (发布)", readiness)
                j_plain = ed.judge_rb2_contract_gate(
                    "check-governance", readiness)
        self.assertTrue(j_sensitive["sensitive"])
        self.assertFalse(j_plain["sensitive"])
        for j in (j_sensitive, j_plain):
            self.assertEqual(j["raw_verdict"], "N/A")
            self.assertEqual(j["verdict"], "N/A")

    def test_judge_gap_state_na_survives_enforced_flip(self):
        # 边界守护: enforcement 翻转机制（B-12/B-13 授权票域）零触碰——间隙
        # 态无判定对象，翻转后 sensitive action 仍判 N/A 而非 BLOCK。
        readiness = {"precondition_met": False, "active_units": False}
        with mock.patch.object(ed, "RB2_SENSITIVE_BLOCK_ENFORCED", True):
            j = ed.judge_rb2_contract_gate("授权票翻转 authorization-flip",
                                           readiness)
        self.assertEqual(j["raw_verdict"], "N/A")
        self.assertEqual(j["verdict"], "N/A")
        self.assertEqual(j["enforcement"], "enforced")

    def test_judge_handbuilt_readiness_keeps_runtime_semantics(self):
        # 向后兼容: 直接调用方 hand-built readiness（缺 active_units 键）按
        # 运行期处理——WARN/BLOCK 判定链零变化（既有契约，FIX-431 不外溢）。
        readiness = {"precondition_met": False}
        j = ed.judge_rb2_contract_gate("release 0.90.0 (发布)", readiness)
        self.assertEqual(j["raw_verdict"], "BLOCK")
        self.assertEqual(j["verdict"], "WARN")


class TestRB2RendererBlock(unittest.TestCase):
    """The renderer wiring face — WARN-grade output, never [FAIL]."""

    def test_renderer_positive_host_shows_pass(self):
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets={_DEMO_TASK_ID: {
                        "task_id": _DEMO_TASK_ID,
                        "product_success_contract": VALID_CONTRACT,
                    }}):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    ed.render_rb2_goal_contract_block()
        out = buf.getvalue()
        self.assertIn("Activation precondition: [PASS]", out)
        self.assertIn("gate open", out)
        self.assertNotIn("[FAIL]", out)  # factory WARN-only discipline

    def test_renderer_placeholder_host_shows_warn_and_block_judge(self):
        template = vw.build_execution_packet({
            "task_id": _DEMO_TASK_ID,
            "title": "Demo unit",
            "priority": "P1",
            "status": "📋 待启动",
        })["product_success_contract"]
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets={_DEMO_TASK_ID: {
                        "task_id": _DEMO_TASK_ID,
                        "product_success_contract": template,
                    }}):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    ed.render_rb2_goal_contract_block()
        out = buf.getvalue()
        self.assertIn("Activation precondition: [WARN]", out)
        self.assertIn("(judge=BLOCK)", out)   # 阻断判据可观测
        self.assertIn("enforcement=warn-only", out)
        self.assertNotIn("[FAIL]", out)

    def test_renderer_gap_state_shows_na_no_warn(self):
        # FIX-431 正例: 间隙态（无活跃 P0/P1）→ face① N/A + demo faces N/A，
        # 全块零 [WARN] 行（旧实现发三条 WARN：face① 一条 + demo 两条）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(with_active_task=False),
                    packets={}):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    ed.render_rb2_goal_contract_block()
        out = buf.getvalue()
        self.assertIn("Activation precondition: [N/A]", out)
        self.assertEqual(out.count("[N/A]"), 3)  # face① + 两条 demo
        self.assertNotIn("[WARN]", out)
        self.assertNotIn("[FAIL]", out)

    def test_renderer_active_unit_without_contract_keeps_warn(self):
        # FIX-431 负例: 有活跃 P0/P1 但无 contract → 现行为渲染零变化
        # （face① WARN + demo judge=BLOCK/WARN 全保持）。
        with tempfile.TemporaryDirectory() as td:
            with _HostFixture(
                    td, plan_text=_plan_tracker_text(goal_face=True),
                    packets={}):  # 活跃任务存在、无对应 packet
                buf = io.StringIO()
                with redirect_stdout(buf):
                    ed.render_rb2_goal_contract_block()
        out = buf.getvalue()
        self.assertIn("Activation precondition: [WARN]", out)
        self.assertIn("(judge=BLOCK)", out)
        self.assertIn("contract missing → WARN", out)
        self.assertNotIn("[N/A]", out)


if __name__ == "__main__":  # pragma: no cover - direct-run convenience
    unittest.main()
