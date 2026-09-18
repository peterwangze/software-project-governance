"""Unit tests for bootstrap_aggregate.py — FEAT-033 (AUDIT-154 slice A-2).

Read-only bootstrap aggregate: one command that joins the resolve_entry
envelope, a lean status projection (project config / gate summary / task
stats / active risks / recent activity), the task-priority light candidate
path, the v1-deferred health face, and the migration flag — under a wall
clock budget with fail-safe ``deferred`` disclosure.

Fixtures are small SYNTHETIC ``.governance/`` trees built in temporary
directories — the host project's live governance data is never written and
only read by the explicit end-to-end wiring smoke (read-only). Idempotency
asserts byte-stability of the fixture tree across runs and equality of two
aggregate payloads modulo the declared volatile fields (``generated_at``,
``duration_ms``).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py -q
    python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_bootstrap_aggregate.py" -v
"""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import bootstrap_aggregate as ba  # noqa: E402

_ENGINE = _INFRA_DIR / "verify_workflow.py"

VOLATILE_KEYS = ("generated_at", "duration_ms")

PLAN_TRACKER = """# 项目计划跟踪

## 项目配置

- **项目名称**: 聚合命令夹具项目
- **Profile**: standard
- **触发模式**: always-on
- **操作权限模式**: default-confirm
- **工作流版本**: 0.83.0
- **当前阶段**: 维护（maintenance）

## 项目总览

| 项目 | 当前阶段 | 总任务 | 已完成 | 阻塞中 | 关键风险 | 最近 Gate | 最近复盘 |
|------|---------|--------|--------|--------|---------|----------|---------|
| 聚合命令夹具项目 | 维护（maintenance） | 4 | 1 | 1 | 1 | G11 passed | 2026-09-01 |

## Gate 状态跟踪

| Gate | 迁移条件 | 状态 | 日期 | 证据 |
|------|---------|------|------|------|
| G1 | 立项完成 | passed | 2026-08-01 | EVD-001 |
| G2 | 需求定义 | pending | — | — |
| G3 | 技术选型 | failed | 2026-08-02 | EVD-002 |

## 0.84.0 task 表

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| P0 | FEAT-101 | 已完成的任务 | — | 0.84.0 | tests | ✅ 完成 (2026-09-10) |
| P0 | FEAT-102 | 进行中无阻塞 | FEAT-101 | 0.84.0 | tests | 🔄 进行中 |
| P1 | FEAT-103 | 未开始无阻塞 | — | 0.84.0 | tests | ⏳ 待执行 |
| P2 | FEAT-104 | 被阻塞的任务 | FEAT-105 | 0.85.0 | tests | ⏳ 待执行 |
"""

PLAN_TRACKER_UPGRADED = PLAN_TRACKER.replace("**工作流版本**: 0.83.0",
                                              "**工作流版本**: 0.99.0")

RISK_LOG = """# 风险记录

## 活跃风险

| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 | 严重级别 | Owner | 当前状态 | 缓解动作 | 截止日期 | 关联任务 | 备注 |
|------|------|--------------|---------|---------|------|---------|-------|---------|---------|---------|---------|------|
| RISK-901 | 2026-09-01 | 已过期升级线 | 维护 | x | y | 高 | Claude | 打开 | 观察 | 2026-09-05 | FEAT-102 | 过期 |
| RISK-902 | 2026-09-14 | 远期升级线 | 维护 | x | y | 中 | Claude | 打开 | 观察 | 2099-09-20 | FEAT-103 | 远期 |
| RISK-903 | 2026-09-01 | 已关闭风险 | 维护 | x | y | 低 | Claude | 已关闭 | 完成 | 2026-09-02 | — | 关闭 |
"""

DECISION_LOG = """# 决策记录

## 决策

| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 | 选择原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |
|------|------|------|------|---------|---------|---------|---------|--------|---------|---------|
| DEC-901 | 2026-09-12 | 夹具决策一 | bg | content | alt | why | scope | Claude | FEAT-102 | next |
| DEC-900 | 2026-09-01 | 夹具决策二 | bg | content | alt | why | scope | Claude | — | next |
"""

# R0 P0-1 fixture: the LIVE risk-log shape — ONE table whose rows are split
# into segments by blank lines (live dogfood inserts them between sub-groups).
# The pre-R1 scanner dropped every segment after the first blank line; the
# engine tolerates the blanks and keeps all rows. RISK-914/915 only exist in
# the post-cut segments — losing them is the exact P0-1 failure mode.
RISK_LOG_SEGMENTED = """# 风险记录

## 活跃风险

| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 | 严重级别 | Owner | 当前状态 | 缓解动作 | 截止日期 | 关联任务 | 备注 |
|------|------|--------------|---------|---------|------|---------|-------|---------|---------|---------|---------|------|
| RISK-911 | 2026-09-01 | 段一已过期风险 | 维护 | x | y | 高 | Claude | 打开 | 观察 | 2026-09-05 | FEAT-102 | 过期 |
| RISK-912 | 2026-09-14 | 段一远期风险 | 维护 | x | y | 中 | Claude | 打开 | 观察 | 2099-09-20 | FEAT-103 | 远期 |
| RISK-913 | 2026-09-01 | 段一已关闭风险 | 维护 | x | y | 低 | Claude | 已关闭 | 完成 | 2026-09-02 | — | 关闭 |

| RISK-914 | 2026-09-02 | 段二风险（一个空行切段之后） | 维护 | x | y | 高 | Claude | 打开 | 观察 | 2026-09-04 | FEAT-102 | 过期段二 |

| RISK-915 | 2026-09-03 | 段三风险（两个空行切段之后） | 维护 | x | y | 中 | Claude | 打开 | 观察 | 2099-01-01 | FEAT-103 | 远期段三 |

## 下一节

| 编号 | 日期 | 主题 |
|------|------|------|
| DEC-950 | 2026-09-12 | 分段夹具尾部真表 |
"""

# Ghost block: `|` rows AFTER the preceding table was ended by a non-`|`
# line, carrying NO separator row anywhere. Neither row may mint a table
# (no ghost headers / no phantom counts) — engine semantics skip them.
GHOST_BLOCK_COMBINED = RISK_LOG_SEGMENTED + """
非表行分隔（结束上一张表）

| RISK-990 | 2026-09-01 | 幽灵段数据行（无分隔行） | 维护 | x | y | 高 | Claude | 打开 | 观察 | 2026-09-01 | FEAT-102 | 不得计数 |
| RISK-991 | 2026-09-02 | 幽灵段续行（无分隔行） | 维护 | x | y | 低 | Claude | 打开 | 观察 | 2026-09-02 | FEAT-103 | 不得计数 |
"""

# R0 P1-1 fixture: EVERY task dependency-blocked (unknown root dep) — the
# only shape that exercises the REQ-110 structured empty-recommendation
# path (_candidate_empty's empty_reason / unblock_recommendation branches),
# which the original 26 tests never executed (their fixture always had
# unblocked tasks).
PLAN_TRACKER_ALL_BLOCKED = """# 项目计划跟踪

## 项目配置

- **项目名称**: 全阻塞夹具项目
- **Profile**: standard
- **触发模式**: always-on
- **操作权限模式**: default-confirm
- **工作流版本**: 0.83.0
- **当前阶段**: 维护（maintenance）

## 0.84.0 task 表

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| P0 | FEAT-201 | 链中阻塞任务 | FEAT-998 | 0.84.0 | tests | ⏳ 待执行 |
| P1 | FEAT-202 | 链尾阻塞任务 | FEAT-201 | 0.84.0 | tests | ⏳ 待执行 |
"""

# R0 P0-1 recent half: the LIVE decision-log shape — blank lines cut the
# decision table into segments (live file lines 8-11 do exactly this);
# every row after the cuts must survive in BOTH readers.
DECISION_LOG_SEGMENTED = """# 决策记录

## 决策

| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 | 选择原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |
|------|------|------|------|---------|---------|---------|---------|--------|---------|---------|
| DEC-901 | 2026-09-12 | 夹具决策一 | bg | content | alt | why | scope | Claude | FEAT-102 | next |

| DEC-900 | 2026-09-01 | 夹具决策二 | bg | content | alt | why | scope | Claude | — | next |
"""

DECISION_LOG_SEGMENTED_GHOST = DECISION_LOG_SEGMENTED + """
非表行分隔（结束上一张表）

| DEC-989 | 2026-09-30 | 幽灵段决策（无分隔行） | bg | content | alt | why | scope | Claude | — | next |
"""


def _write_gov(root, name, content):
    gov = Path(root) / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    path = gov / name
    path.write_text(content, encoding="utf-8")
    return path


def _make_fixture(root):
    """Build the synthetic .governance tree used by most tests."""
    _write_gov(root, "plan-tracker.md", PLAN_TRACKER)
    _write_gov(root, "evidence-log.md", "# 证据记录\n\n（夹具）\n")
    _write_gov(root, "risk-log.md", RISK_LOG)
    _write_gov(root, "decision-log.md", DECISION_LOG)


def _make_skill_home(root, version="9.9.9"):
    """A minimal PLUGIN_HOME stand-in with a controlled frontmatter version."""
    skill_home = Path(root) / "skill-home" / "software-project-governance"
    skill_home.mkdir(parents=True, exist_ok=True)
    (skill_home / "SKILL.md").write_text(
        "---\nname: fixture\nversion: %s\n---\n\n# fixture\n" % version,
        encoding="utf-8")
    return skill_home


def _run_aggregate(root, extra_args=()):
    """Invoke cmd_governance_bootstrap against a fixture root; return payload."""
    args = ba.build_arg_parser().parse_args(
        ["--project-root", str(root), "--format", "json", *extra_args])
    buf = io.StringIO()
    with redirect_stdout(buf):
        ba.cmd_governance_bootstrap(args)
    return json.loads(buf.getvalue())


def _strip_volatile(payload):
    cleaned = dict(payload)
    for key in VOLATILE_KEYS:
        cleaned.pop(key, None)
    return cleaned


def _import_engine(testcase):
    """In-process engine import for the mirror differentials (R0 P0-1).

    Skipped — disclosed, not failed — when this environment cannot cold-
    import the engine (same discipline as the subprocess probe below).
    """
    try:
        import verify_workflow as vw  # noqa: E402
        return vw
    except Exception as exc:  # pragma: no cover — environment-dependent
        testcase.skipTest("engine import unavailable here: %s"
                          % str(exc)[-200:])
        return None


def _tree_digest(root):
    """sha256 over sorted (relpath, bytes) of every file under root."""
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            digest.update(rel.encode("utf-8"))
            digest.update(b"\x00")
            digest.update(path.read_bytes())
            digest.update(b"\x00")
    return digest.hexdigest()


class ResolveMigrationTests(unittest.TestCase):
    """The migration flag: version comparison ONLY — never an execution."""

    def test_upgrade_available_when_plan_version_older(self):
        flag = ba.migration_flag("0.83.0", "0.84.0")
        self.assertTrue(flag["required"])
        self.assertEqual(flag["plan_version"], "0.83.0")
        self.assertEqual(flag["active_version"], "0.84.0")
        self.assertEqual(flag["status"], "upgrade_available")

    def test_no_migration_when_versions_equal(self):
        flag = ba.migration_flag("0.84.0", "0.84.0")
        self.assertFalse(flag["required"])
        self.assertEqual(flag["status"], "up_to_date")

    def test_no_migration_when_plan_newer(self):
        flag = ba.migration_flag("0.99.0", "0.84.0")
        self.assertFalse(flag["required"])
        self.assertEqual(flag["status"], "plan_ahead")

    def test_unknown_when_either_version_unparseable(self):
        flag = ba.migration_flag("", "0.84.0")
        self.assertFalse(flag["required"])
        self.assertEqual(flag["status"], "unknown")
        flag = ba.migration_flag(None, None)
        self.assertEqual(flag["status"], "unknown")


class AggregateFieldCompletenessTests(unittest.TestCase):
    """One invocation emits every contracted aggregate section."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        _make_fixture(root)
        cls.payload = _run_aggregate(root)
        cls.root = root

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_schema_and_budget_faces(self):
        self.assertEqual(self.payload["schema"], "governance-bootstrap/1")
        self.assertEqual(self.payload["task"], "FEAT-033")
        self.assertEqual(self.payload["budget_ms"], ba.DEFAULT_BUDGET_MS)
        self.assertEqual(self.payload["deferred"], [])

    def test_resolve_face_reuses_resolve_entry_envelope(self):
        resolve = self.payload["resolve"]
        self.assertTrue(resolve["resolved_root_ok"])
        self.assertEqual(resolve["scenario_hint"], "F")
        self.assertTrue(resolve["plugin_home"])
        self.assertIn("active_version", resolve)

    def test_migration_face_matches_fixture_versions(self):
        # resolve() reads the ACTIVE version from PLUGIN_HOME at call time —
        # the documented test seam (resolve_entry docstring). Pin it to a
        # fixture skill home so the flag is deterministic.
        skill_home = _make_skill_home(self.root, version="9.9.9")
        with unittest.mock.patch.object(ba.resolve_entry, "PLUGIN_HOME",
                                        skill_home):
            payload = _run_aggregate(self.root)
        migration = payload["migration"]
        self.assertEqual(migration["status"], "upgrade_available")
        self.assertTrue(migration["required"])
        self.assertEqual(migration["plan_version"], "0.83.0")
        self.assertEqual(migration["active_version"], "9.9.9")

    def test_project_face(self):
        project = self.payload["project"]
        self.assertEqual(project["name"], "聚合命令夹具项目")
        self.assertEqual(project["profile"], "standard")
        self.assertEqual(project["trigger_mode"], "always-on")
        self.assertEqual(project["permission_mode"], "default-confirm")
        self.assertEqual(project["workflow_version"], "0.83.0")
        self.assertIn("维护", project["stage"])

    def test_gate_summary_counts(self):
        gates = self.payload["gates"]
        self.assertEqual(gates["total"], 3)
        self.assertEqual(gates["passed"], 1)
        self.assertEqual(gates["pending"], 1)
        self.assertEqual(gates["failed"], 1)
        self.assertEqual(gates["next_gate"], "G2")

    def test_task_stats_from_light_parse(self):
        tasks = self.payload["tasks"]
        self.assertEqual(tasks["total"], 4)
        self.assertEqual(tasks["completed"], 1)
        self.assertEqual(tasks["unblocked"], 2)   # FEAT-102 + FEAT-103
        self.assertEqual(tasks["blocked"], 1)     # FEAT-104 (unknown dep)
        self.assertEqual(tasks["p0_pending"], 1)
        self.assertEqual(tasks["in_progress"], 1)

    def test_risk_summary_counts(self):
        risks = self.payload["risks"]
        self.assertEqual(risks["open"], 2)
        self.assertEqual(risks["escalation_overdue"], 1)
        # Engine caliber: soon = deadline ≤3d INCLUDING the overdue row;
        # the far-future row (2099) counts in neither bucket.
        self.assertEqual(risks["escalation_soon"], 1)
        self.assertIn("RISK-901", risks["overdue_ids"])

    def test_recent_activity_capped(self):
        recent = self.payload["recent"]
        self.assertEqual(len(recent["decisions"]), 2)
        self.assertEqual(recent["decisions"][0]["id"], "DEC-901")

    def test_candidates_light_path(self):
        candidates = self.payload["candidates"]
        self.assertEqual(candidates["source"],
                         "task-priority-analysis(light)")
        ids = [c["task_id"] for c in candidates["items"]]
        # FEAT-104 depends on the unknown FEAT-105 (fail-closed block);
        # FEAT-101 is completed — only 102/103 are dependency-free.
        self.assertEqual(sorted(ids), ["FEAT-102", "FEAT-103"])
        # P0 in-progress sorts before P1 pending.
        self.assertEqual(ids[0], "FEAT-102")
        for item in candidates["items"]:
            self.assertTrue(item["deps_satisfied"])
            self.assertTrue(item["reason"])

    def test_health_face_is_deferred_not_fake(self):
        health = self.payload["health"]
        self.assertEqual(health["state"], "deferred")
        self.assertIn("check-governance", health["pending_checks"])
        self.assertIn("check-governance", health["next_action"])

    def test_next_actions_present(self):
        self.assertTrue(self.payload["next_actions"])
        for action in self.payload["next_actions"]:
            self.assertIsInstance(action, str)
            self.assertTrue(action)

    def test_json_bytes_within_projection_budget(self):
        raw = json.dumps(self.payload, ensure_ascii=False)
        self.assertLessEqual(
            len(raw.encode("utf-8")), ba.MAX_JSON_BYTES,
            "aggregate JSON exceeded the ≤8KB projection budget")


class ProfileDetailTests(unittest.TestCase):
    """--profile lite|standard|strict only changes projection detail."""

    def test_lite_drops_recent_and_caps_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_fixture(tmp)
            lite = _run_aggregate(tmp, ["--profile", "lite"])
            strict = _run_aggregate(tmp, ["--profile", "strict"])
        self.assertNotIn("recent", lite)
        self.assertLessEqual(len(lite["candidates"]["items"]), 1)
        self.assertLessEqual(len(strict["candidates"]["items"]), 5)


class BudgetFailSafeTests(unittest.TestCase):
    """--budget-ms exhaustion returns the finished part + deferred disclosure."""

    def test_zero_budget_defers_status_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_fixture(tmp)
            payload = _run_aggregate(tmp, ["--budget-ms", "0"])
        self.assertTrue(payload["deferred"])
        for entry in payload["deferred"]:
            self.assertIn("section", entry)
            self.assertIn("reason", entry)
            self.assertEqual(entry["reason"], "budget_exhausted")
        # Fail-safe honesty: sections that never ran are absent, not guessed.
        self.assertNotIn("gates", payload)
        self.assertNotIn("candidates", payload)
        # But the envelope itself (resolve face) is still present.
        self.assertTrue(payload["resolve"]["resolved_root_ok"])

    def test_health_deferred_state_is_not_a_budget_defer(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_fixture(tmp)
            payload = _run_aggregate(tmp)
        deferred_sections = {d["section"] for d in payload["deferred"]}
        self.assertNotIn("health", deferred_sections)
        self.assertEqual(payload["health"]["state"], "deferred")


class ReadOnlyIdempotencyTests(unittest.TestCase):
    """Two consecutive runs: identical output (modulo volatile fields) and
    a byte-identical .governance tree — zero writes, zero side effects."""

    def test_double_run_is_output_stable_and_tree_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_fixture(tmp)
            digest_before = _tree_digest(tmp)
            first = _run_aggregate(tmp)
            digest_mid = _tree_digest(tmp)
            second = _run_aggregate(tmp)
            digest_after = _tree_digest(tmp)
        self.assertEqual(digest_before, digest_mid)
        self.assertEqual(digest_mid, digest_after)
        self.assertEqual(_strip_volatile(first), _strip_volatile(second))

    def test_engine_cli_double_run_is_read_only(self):
        """End-to-end wiring smoke through the engine dispatch (read-only).

        Runs the real CLI against a fixture root twice and asserts the
        fixture tree digest is unchanged and the payloads agree modulo
        volatile fields. Skipped when the engine cannot cold-import in this
        environment (disclosed, not failed).
        """
        with tempfile.TemporaryDirectory() as tmp:
            _make_fixture(tmp)
            probe = subprocess.run(
                [sys.executable, "-I", "-B", "-c",
                 "import sys; sys.path.insert(0, %r); import verify_workflow"
                 % str(_INFRA_DIR)],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=180, check=False)
            if probe.returncode != 0:
                self.skipTest("engine cold-import unavailable in this "
                              "environment: %s" % probe.stderr[-300:])
            digest_before = _tree_digest(tmp)
            outputs = []
            for _ in range(2):
                completed = subprocess.run(
                    [sys.executable, str(_ENGINE), "--project-root", tmp,
                     "governance-bootstrap", "--format", "json"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", timeout=180, check=False,
                    cwd=str(_HERE))
                self.assertEqual(completed.returncode, 0,
                                 completed.stderr[-500:])
                outputs.append(json.loads(completed.stdout))
            self.assertEqual(digest_before, _tree_digest(tmp))
        self.assertEqual(_strip_volatile(outputs[0]),
                         _strip_volatile(outputs[1]))


class TextFormatTests(unittest.TestCase):
    """--format text renders a ≤40-line summary."""

    def test_text_summary_line_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_fixture(tmp)
            args = ba.build_arg_parser().parse_args(
                ["--project-root", tmp, "--format", "text"])
            buf = io.StringIO()
            with redirect_stdout(buf):
                ba.cmd_governance_bootstrap(args)
        lines = buf.getvalue().rstrip("\n").split("\n")
        self.assertLessEqual(len(lines), 40)
        self.assertTrue(any("governance-bootstrap" in ln for ln in lines))


class SegmentedTableMirrorTests(unittest.TestCase):
    """R0 P0-1: blank-line-segmented tables — the mirror keeps every data
    row, mints no ghost headers, and matches the engine stream exactly
    (bidirectional differential: mirror↔engine on identical inputs)."""

    #: Clock-free deadline design: overdue rows (911/914) pinned around
    #: 2026-09-10; far rows (912/915) at 2099 so open counts stay
    #: clock-independent.
    _TODAY = date(2026, 9, 10)

    def test_stream_matches_engine_on_every_fixture(self):
        vw = _import_engine(self)
        for text in (PLAN_TRACKER, RISK_LOG, DECISION_LOG,
                     RISK_LOG_SEGMENTED, DECISION_LOG_SEGMENTED_GHOST,
                     GHOST_BLOCK_COMBINED):
            self.assertEqual(
                list(ba._iter_positional_tables(text)),
                list(vw._status_table_stream(text)),
                "mirror drift vs engine _status_table_stream")

    def test_blank_line_segments_keep_all_data_rows(self):
        # Live risk-log shape: blank lines INSIDE the active table split it
        # into segments; blank lines are tolerance, not terminators.
        summary = ba.parse_risk_summary(RISK_LOG_SEGMENTED, today=self._TODAY)
        # 911+912 (segment 1) + 914 (after one cut) + 915 (after two) — the
        # pre-R1 scanner silently dropped 914/915 (open would be 2).
        self.assertEqual(summary["open"], 4)
        self.assertEqual(summary["escalation_overdue"], 2)
        self.assertEqual(summary["overdue_ids"], ["RISK-911", "RISK-914"])
        self.assertEqual(summary["escalation_soon"], 2)

    def test_segment_data_rows_never_become_ghost_headers(self):
        tables = list(ba._iter_positional_tables(GHOST_BLOCK_COMBINED))
        self.assertEqual(len(tables), 2)  # risk table + topic table only
        for header, _ in tables:
            self.assertFalse(
                ba._ID_TOKEN_RE.match((header or [""])[0] or ""),
                "a data row leaked in as a table header: %r" % (header,))
        # Ghost rows (990/991, no separator anywhere) add nothing.
        summary = ba.parse_risk_summary(GHOST_BLOCK_COMBINED,
                                        today=self._TODAY)
        self.assertEqual(summary["open"], 4)

    def test_risk_open_count_equals_engine_on_segmented_shape(self):
        vw = _import_engine(self)
        engine_rows = vw.parse_active_risks(RISK_LOG_SEGMENTED)
        self.assertEqual(
            ba.parse_risk_summary(RISK_LOG_SEGMENTED,
                                  today=date.today())["open"],
            len(engine_rows))
        self.assertEqual(sorted(r["id"] for r in engine_rows),
                         ["RISK-911", "RISK-912", "RISK-914", "RISK-915"])

    def test_recent_matches_engine_on_segmented_shape(self):
        # Decision-DOMAIN text (the only input parse_recent_decisions ever
        # receives): blank-line cuts + a separator-less ghost block. The
        # engine's recent reader accepts any 编号-table (risk-shaped tables
        # would leak in with empty topics); the bootstrap keeps the R0-era
        # 主题/决策内容 domain gate — on real decision-log shapes the two
        # agree, which is the parity this face owes.
        vw = _import_engine(self)
        text = DECISION_LOG_SEGMENTED_GHOST
        mine = ba.parse_recent_decisions(text, limit=5)
        engine = vw.parse_recent_decisions(n=5, decision_content=text)
        self.assertEqual([d["id"] for d in mine], [d["id"] for d in engine])
        # Blank-line cuts lost NO row (pre-R1 scanner saw only DEC-901).
        self.assertEqual([d["id"] for d in mine], ["DEC-901", "DEC-900"])
        self.assertNotIn("DEC-989", [d["id"] for d in mine])
        for mine_row, engine_row in zip(mine, engine):
            # Bootstrap discloses the cut past 60 chars; both agree below it.
            self.assertEqual(mine_row["topic"][:60],
                             engine_row["topic"][:60])


class EmptyRecommendationTests(unittest.TestCase):
    """R0 P1-1: REQ-110 structured empty-recommendation face — the
    _candidate_empty branches the original 26 tests never executed."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        root = Path(cls._tmp.name)
        _write_gov(root, "plan-tracker.md", PLAN_TRACKER_ALL_BLOCKED)
        _write_gov(root, "evidence-log.md", "# 证据记录\n\n（夹具）\n")
        _write_gov(root, "risk-log.md", RISK_LOG)
        _write_gov(root, "decision-log.md", DECISION_LOG)
        cls.payload = _run_aggregate(root)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_candidates_carry_structured_empty_reason(self):
        face = self.payload["candidates"]
        self.assertEqual(face["items"], [])
        self.assertEqual(face["source"], "task-priority-analysis(light)")
        reason = face["empty_reason"]
        self.assertEqual(reason["kind"], "all_blocked")
        self.assertEqual(reason["total"], 2)
        self.assertEqual(reason["completed"], 0)
        self.assertEqual(reason["blocked"], 2)
        self.assertEqual(reason["non_executable"], 0)
        self.assertTrue(reason["message"])
        self.assertTrue(reason["nearest_action"])
        self.assertIn("FEAT-998", reason["nearest_action"])

    def test_candidates_carry_unblock_recommendation(self):
        rec = self.payload["candidates"]["unblock_recommendation"]
        self.assertEqual(rec["root_task_id"], "FEAT-998")
        self.assertEqual(rec["root_kind"], "unknown_dependency")
        self.assertEqual(rec["downstream_count"], 2)
        self.assertTrue(rec["reason"])

    def test_task_stats_and_next_actions_reflect_all_blocked(self):
        self.assertEqual(self.payload["tasks"]["blocked"], 2)
        self.assertEqual(self.payload["tasks"]["unblocked"], 0)
        self.assertTrue(any("无就绪候选" in action
                            for action in self.payload["next_actions"]))


class RecentTopicFallbackTests(unittest.TestCase):
    """R0 P2-1: per-row 主题→决策内容 fallback + DISCLOSED 60-char clip."""

    DECISIONS = (
        "# 决策记录\n\n## 决策\n\n"
        "| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 | 选择原因 |"
        " 影响范围 | 决策人 | 关联任务 | 后续动作 |\n"
        "|------|------|------|------|---------|---------|---------|"
        "---------|--------|---------|---------|\n"
        "| DEC-801 | 2026-09-12 | %s | bg | 兜底内容一 | alt | why | scope"
        " | Claude | FEAT-102 | next |\n"
        "| DEC-802 | 2026-09-11 | | bg | 主题空回退到决策内容 | alt | why"
        " | scope | Claude | — | next |\n"
    ) % ("主" * 80)

    def test_long_topic_is_clipped_with_disclosure_marker(self):
        rows = ba.parse_recent_decisions(self.DECISIONS, limit=3)
        self.assertEqual(rows[0]["id"], "DEC-801")
        self.assertEqual(rows[0]["topic"], "主" * 60 + "…")
        self.assertEqual(len(rows[0]["topic"]), 61)

    def test_empty_topic_falls_back_to_decision_content(self):
        rows = ba.parse_recent_decisions(self.DECISIONS, limit=3)
        self.assertEqual(rows[1]["id"], "DEC-802")
        self.assertEqual(rows[1]["topic"], "主题空回退到决策内容")

    def test_ids_and_dates_still_match_engine(self):
        vw = _import_engine(self)
        mine = ba.parse_recent_decisions(self.DECISIONS, limit=3)
        engine = vw.parse_recent_decisions(n=3,
                                           decision_content=self.DECISIONS)
        self.assertEqual([d["id"] for d in mine], [d["id"] for d in engine])
        self.assertEqual([d["date"] for d in mine],
                         [d["date"] for d in engine])


class GateBucketContractTests(unittest.TestCase):
    """R0 P2-2: closed word-form vocabulary — domain forms keep their
    buckets; superset word forms can no longer mis-bucket via substrings."""

    def test_domain_word_forms_keep_their_buckets(self):
        cases = {
            "passed": "passed", "pass": "passed",
            "passed-on-entry": "passed",
            "passed-with-conditions": "passed",
            "`passed-on-entry`": "passed", "**passed**": "passed",
            "pending": "pending",
            "failed": "failed", "fail": "failed",
        }
        for cell, bucket in cases.items():
            self.assertEqual(ba._gate_bucket(cell), bucket, cell)

    def test_superset_word_forms_cannot_mis_bucket(self):
        # The R0 vector: substring scans bucket these WRONG ("passed" in
        # "unpassed"); the closed vocabulary sends them to "other", where a
        # live anomaly stays visible instead of being silently absorbed.
        for cell in ("unpassed", "pending-review", "failed-pending",
                     "passed (见 DEC-1)"):
            self.assertEqual(ba._gate_bucket(cell), "other", cell)


class ProjectionClampTests(unittest.TestCase):
    """R0 P2-3: the ≤8KB projection promise gets a hard output-side clamp
    with disclosed trims — deterministic across runs, idempotent."""

    OVERSIZE_ROW = (
        "| 聚合命令夹具项目 | 维护（maintenance） | 4 | 1 | 1 | 1 |"
        " G11 passed | 2026-09-01 |")

    @classmethod
    def _oversize_tracker(cls):
        prose = "冗" * 12000  # KB-sized live-like overview cell prose
        return PLAN_TRACKER.replace(
            cls.OVERSIZE_ROW,
            "| 聚合命令夹具项目 | %s | 4 | 1 | 1 | 1 | G11 passed |"
            " 2026-09-01 |" % prose)

    @classmethod
    def _oversize_fixture(cls, root):
        _write_gov(root, "plan-tracker.md", cls._oversize_tracker())
        _write_gov(root, "evidence-log.md", "# 证据记录\n\n（夹具）\n")
        _write_gov(root, "risk-log.md", RISK_LOG)
        _write_gov(root, "decision-log.md", DECISION_LOG)

    def test_oversize_face_clamped_under_budget_with_disclosure(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._oversize_fixture(tmp)
            payload = _run_aggregate(tmp)
        raw = json.dumps(payload, ensure_ascii=False)
        self.assertLessEqual(len(raw.encode("utf-8")), ba.MAX_JSON_BYTES)
        self.assertNotIn("overview", payload.get("project") or {})
        self.assertTrue(any("projection clamp" in note
                            for note in payload.get("notes") or []))
        # A clamp is NOT a budget defer; the core faces stay intact.
        self.assertEqual(payload["deferred"], [])
        self.assertEqual(payload["project"]["name"], "聚合命令夹具项目")
        self.assertIn("gates", payload)

    def test_clamp_is_deterministic_across_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._oversize_fixture(tmp)
            first = _run_aggregate(tmp)
            second = _run_aggregate(tmp)
        self.assertEqual(_strip_volatile(first), _strip_volatile(second))

    def test_under_budget_payload_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_fixture(tmp)
            payload = _run_aggregate(tmp)
        self.assertNotIn("notes", payload)
        self.assertIn("overview", payload["project"])


class FailClosedRootTests(unittest.TestCase):
    """resolved_root_ok=false → refuse governance state (DEC-080)."""

    def test_missing_project_root_fails_closed(self):
        args = ba.build_arg_parser().parse_args(
            ["--project-root", str(_HERE / "no-such-dir-xyz"),
             "--format", "json"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                ba.cmd_governance_bootstrap(args)
        self.assertEqual(ctx.exception.code, 1)
        payload = json.loads(buf.getvalue())
        self.assertFalse(payload["resolve"]["resolved_root_ok"])
        self.assertTrue(payload["resolve"]["diagnostic"])


class ModuleDisciplineTests(unittest.TestCase):
    """Structural red lines: read-only, engine-free, stdlib-only imports."""

    def test_module_never_imports_the_engine(self):
        source = (_INFRA_DIR / "bootstrap_aggregate.py").read_text(
            encoding="utf-8")
        self.assertNotIn("import verify_workflow", source)
        self.assertNotIn("from verify_workflow", source)

    def test_module_never_spawns_subprocesses_or_writes(self):
        source = (_INFRA_DIR / "bootstrap_aggregate.py").read_text(
            encoding="utf-8")
        # Usage patterns, not bare words (the docstring legitimately names
        # the boundary it enforces).
        for forbidden in ("import subprocess", "os.system", "popen(",
                          "write_text(", "open(", "mkdir(", "shutil",
                          "os.remove", "os.unlink"):
            self.assertNotIn(forbidden, source,
                             "read-only red line: %s must not appear"
                             % forbidden)

    def test_registry_declares_the_aggregate_command(self):
        import registry as reg
        spec = reg.command_spec("governance-bootstrap")
        self.assertEqual(spec.handler,
                         "bootstrap_aggregate.cmd_governance_bootstrap")


if __name__ == "__main__":
    unittest.main()
