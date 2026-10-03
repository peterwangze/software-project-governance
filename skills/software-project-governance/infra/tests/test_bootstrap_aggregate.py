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

# ── Fixture version pin — DEC-096 authoritative derivation (FIX-353) ──────
# resolve_entry.detect_scenario routes `host_v < active_version` to scenario
# "C" (upgrade), so a literal pin in the fixture head rots the suite on every
# plugin bump (FIX-352 §6 root cause; REL-080: fixture head 0.83.0 vs active
# 0.84.0 ⇒ scenario 'C' != expected 'F'). Derive the version through the SAME
# reader resolve() uses — resolve_entry.read_active_version() over
# PLUGIN_HOME/SKILL.md leading frontmatter — so `fixture plan version ==
# active_version` holds by construction for every future bump.
_ACTIVE_VERSION = ba.resolve_entry.read_active_version()
if not _ACTIVE_VERSION:  # pragma: no cover — plugin tree corruption
    raise RuntimeError(
        "active_version underivable from %s/SKILL.md frontmatter — the "
        "fixture plan version cannot be pinned (fail-closed)"
        % ba.resolve_entry.PLUGIN_HOME)

#: Replaced by ``_ACTIVE_VERSION`` in every fixture plan-tracker head.
_VERSION_TOKEN = "@@ACTIVE_VERSION@@"


def _pin_active_version(text):
    """Bind a fixture plan-tracker head to the derived active version.

    Fail-closed on a token-less template: a fixture head re-pinned to a
    literal would silently rot again (the FIX-352 §6 failure mode).
    """
    pinned = text.replace(_VERSION_TOKEN, _ACTIVE_VERSION)
    if pinned == text:  # pragma: no cover — template lost its token
        raise RuntimeError(
            "fixture plan-tracker template carries no %s token — its head "
            "version would silently rot against the active version"
            % _VERSION_TOKEN)
    return pinned


def _version_header(version):
    """The fixture plan-tracker config line carrying ``version``."""
    return "- **工作流版本**: %s" % version


def _next_minor(version):
    """``version`` + one minor — strictly greater (upgrade-scenario shape)."""
    major, minor = version.split(".")[:2]
    return "%d.%d.0" % (int(major), int(minor) + 1)


_PLAN_TRACKER_TEMPLATE = """# 项目计划跟踪

## 项目配置

- **项目名称**: 聚合命令夹具项目
- **Profile**: standard
- **触发模式**: always-on
- **操作权限模式**: default-confirm
- **工作流版本**: @@ACTIVE_VERSION@@
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

PLAN_TRACKER = _pin_active_version(_PLAN_TRACKER_TEMPLATE)

# Upgrade fixture: same body, version bumped ONE minor above the derived
# active version — no literal, so it can never equal (or fall behind) the
# head it derives from, and it stays "plan ahead of active" for any bump.
PLAN_TRACKER_UPGRADED = PLAN_TRACKER.replace(
    _version_header(_ACTIVE_VERSION),
    _version_header(_next_minor(_ACTIVE_VERSION)))
if PLAN_TRACKER_UPGRADED == PLAN_TRACKER:  # pragma: no cover — silent no-op
    raise RuntimeError(
        "PLAN_TRACKER_UPGRADED no longer bumps the fixture version — the "
        "upgrade-scenario fixture would silently equal PLAN_TRACKER")

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
_PLAN_TRACKER_ALL_BLOCKED_TEMPLATE = """# 项目计划跟踪

## 项目配置

- **项目名称**: 全阻塞夹具项目
- **Profile**: standard
- **触发模式**: always-on
- **操作权限模式**: default-confirm
- **工作流版本**: @@ACTIVE_VERSION@@
- **当前阶段**: 维护（maintenance）

## 0.84.0 task 表

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|------|
| P0 | FEAT-201 | 链中阻塞任务 | FEAT-998 | 0.84.0 | tests | ⏳ 待执行 |
| P1 | FEAT-202 | 链尾阻塞任务 | FEAT-201 | 0.84.0 | tests | ⏳ 待执行 |
"""

PLAN_TRACKER_ALL_BLOCKED = _pin_active_version(
    _PLAN_TRACKER_ALL_BLOCKED_TEMPLATE)

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
        # The fixture head carries the DERIVED active version (FIX-353).
        self.assertEqual(migration["plan_version"], _ACTIVE_VERSION)
        self.assertEqual(migration["active_version"], "9.9.9")

    def test_project_face(self):
        project = self.payload["project"]
        self.assertEqual(project["name"], "聚合命令夹具项目")
        self.assertEqual(project["profile"], "standard")
        self.assertEqual(project["trigger_mode"], "always-on")
        self.assertEqual(project["permission_mode"], "default-confirm")
        self.assertEqual(project["workflow_version"], _ACTIVE_VERSION)
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
        # FEAT-082: the closure judgment caliber rides FUNCTION-LOCAL
        # imports of the pure check-domain leaves (same ArchGuard R6
        # discipline as _behavior's behavior_profile import) — the
        # MODULE-LEVEL import face must stay stdlib + the two peer leaves.
        for line in source.split("\n"):
            if line.startswith(("import ", "from ")):
                self.assertNotIn("checks.", line,
                                 "checks.* import must stay function-local "
                                 "(R6 cold-import budget): %s" % line)

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


# ── FEAT-082 (ADR-021 §3.2.3 B4′): session-closure metric fixtures ─────────
#
# Column shapes mirror the LIVE evidence-log/risk-log headers so the
# collection caliber is exercised on faithful shapes: evidence cells[1]=
# row id / cells[2]=task / cells[8]=提交日期 / cells[10]=备注；risk
# cells[1]=RISK id / cells[2]=日期 / terminal tail = cells[9]+cells[13].
_CLOSURE_TODAY = "2026-10-02"

_EVIDENCE_HEADER = (
    "# 证据记录\n\n## 证据\n\n"
    "| 编号 | 对应任务 ID | 阶段 | 证据类型 | 证据说明 | 证据位置 | 提交人 |"
    " 提交日期 | 关联 Gate | 备注 |\n"
    "|------|-----------|------|---------|---------|---------|--------|"
    "---------|----------|------|\n")

#: 1 problem (REVIEW NEEDS_CHANGE FEAT-102) + 1 closure (APPROVED same
#: task) + 1 extra closure (EVD ✅ FEAT-103) + one OUT-OF-WINDOW row
#: (2026-10-01) proving the date filter.
EVIDENCE_FULL_CLOSURE = _EVIDENCE_HEADER + (
    "| REVIEW-901 | FEAT-102 | 开发 | 审查 | R0 审查 | p | Claude |"
    " 2026-10-02 | G8 | NEEDS_CHANGE |\n"
    "| REVIEW-902 | FEAT-102 | 开发 | 审查 | R1 复审 | p | Claude |"
    " 2026-10-02 | G8 | APPROVED |\n"
    "| EVD-901 | FEAT-103 | 开发 | 交付 | 任务收口 | p | Claude |"
    " 2026-10-02 | G8 | ✅ 完成 |\n"
    "| REVIEW-903 | FEAT-105 | 开发 | 审查 | 窗口外他日行 | p | Claude |"
    " 2026-10-01 | G8 | NEEDS_CHANGE |\n")

#: 2 problems, 1 closed — the <100% WARN shape.
EVIDENCE_PARTIAL_CLOSURE = _EVIDENCE_HEADER + (
    "| REVIEW-901 | FEAT-102 | 开发 | 审查 | R0 审查 | p | Claude |"
    " 2026-10-02 | G8 | NEEDS_CHANGE |\n"
    "| REVIEW-902 | FEAT-102 | 开发 | 审查 | R1 复审 | p | Claude |"
    " 2026-10-02 | G8 | APPROVED |\n"
    "| REVIEW-904 | FEAT-104 | 开发 | 审查 | 未复审 | p | Claude |"
    " 2026-10-02 | G8 | NEEDS_CHANGE |\n")

#: A today-dated RISK row closed the same day (terminal word in the
#: 备注 tail) + an out-of-window row.
RISK_LOG_CLOSURE_TERMINAL = """# 风险记录

## 活跃风险

| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 | 严重级别 | Owner | 当前状态 | 缓解动作 | 截止日期 | 关联任务 | 备注 |
|------|------|--------------|---------|---------|------|---------|-------|---------|---------|---------|---------|------|
| RISK-910 | 2026-10-02 | 当日风险同日终局 | 维护 | x | y | 中 | Claude | 打开 | 观察 | 2026-10-05 | — | 已关闭（同日终局） |
| RISK-911 | 2026-10-01 | 窗口外他日风险 | 维护 | x | y | 中 | Claude | 打开 | 观察 | 2026-10-05 | — | 无 |
"""


def _ledger_line(date_str=_CLOSURE_TODAY, row_key="EVD-950",
                 negative_context_hit=False):
    """One M2 observation-ledger line, built by the SHAPE SOURCE itself
    (checks.loop_gate_processor.build_ledger_entry) — the JSONL contract
    never gets a second fixture-side re-implementation."""
    from checks import loop_gate_processor as lgp
    entry = lgp.build_ledger_entry(
        date_str, "evidence-log.md", "evidence", row_key, 42,
        "待以后", negative_context_hit)
    return json.dumps(entry, ensure_ascii=False)


LEDGER_FIRED = _ledger_line() + "\n"
LEDGER_EXEMPT = _ledger_line(row_key="EVD-951",
                             negative_context_hit=True) + "\n"
LEDGER_MALFORMED = "{ not-json \n"

SNAPSHOT_WITH_TODAY = "# 会话快照\n\n- 日期：2026-10-02\n- 状态：进行中\n"
SNAPSHOT_WITHOUT_TODAY = "# 会话快照\n\n- 日期：2026-09-30\n"


def _make_closure_fixture(root, evidence=EVIDENCE_FULL_CLOSURE,
                          risk=RISK_LOG_CLOSURE_TERMINAL, ledger=None,
                          snapshot=None):
    """A synthetic .governance tree for the closure-metric faces."""
    # FEAT-083: the ledger filename is single-sourced from the shared
    # collection leaf (the bootstrap mirror constant is retired).
    from checks.provenance_domain import CLOSURE_LEDGER_FILENAME
    _write_gov(root, "plan-tracker.md", PLAN_TRACKER)
    _write_gov(root, "evidence-log.md", evidence)
    _write_gov(root, "risk-log.md", risk)
    _write_gov(root, "decision-log.md", DECISION_LOG)
    if ledger is not None:
        _write_gov(root, CLOSURE_LEDGER_FILENAME, ledger)
    if snapshot is not None:
        _write_gov(root, "session-snapshot.md", snapshot)


class SessionClosureFaceTests(unittest.TestCase):
    """FEAT-082 (ADR-021 §3.2.3 B4′): the behavior-face closure metric —
    Check 42's judgment caliber (SKIP 分态 / 降级标注 / deferred>0 恒不
    SKIP / 违规前置归零), single-sourced through the imported domain
    functions."""

    def _face(self, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            _make_closure_fixture(tmp, **kwargs)
            return ba.session_closure_face(
                Path(tmp) / ".governance", today=_CLOSURE_TODAY)

    def test_full_closure_rate_is_1_and_compliant(self):
        face = self._face()
        self.assertEqual(face["session_closure_rate"], 1.0)
        self.assertEqual(face["deferred_detections"], 0)
        self.assertEqual(face["problems_raised"], 2)   # REVIEW-901 + RISK-910
        self.assertEqual(face["closed"], 2)
        self.assertTrue(face["compliant"])
        self.assertIsNone(face["skip_kind"])

    def test_partial_closure_below_1_judges_not_skips(self):
        face = self._face(evidence=EVIDENCE_PARTIAL_CLOSURE, risk=RISK_LOG)
        self.assertEqual(face["session_closure_rate"], 0.5)
        self.assertEqual(face["problems_raised"], 2)
        self.assertEqual(face["closed"], 1)
        self.assertFalse(face["compliant"])
        # problems_raised > 0 → no SKIP available (live judging face).
        self.assertIsNone(face["skip_kind"])

    def test_deferred_detection_zeroes_rate_and_never_skips(self):
        face = self._face(ledger=LEDGER_FIRED)
        self.assertEqual(face["deferred_detections"], 1)
        # 违规前置（ADR §3.2.3）: deferred > 0 → rate 0.0 even though
        # every raised problem closed.
        self.assertEqual(face["session_closure_rate"], 0.0)
        self.assertFalse(face["compliant"])
        # deferred > 0 恒不 SKIP.
        self.assertIsNone(face["skip_kind"])

    def test_exempted_ledger_hit_is_not_a_detection(self):
        face = self._face(ledger=LEDGER_EXEMPT)
        self.assertEqual(face["deferred_detections"], 0)
        self.assertEqual(face["session_closure_rate"], 1.0)

    def test_vacuum_skip_kind_when_nothing_to_observe(self):
        face = self._face(evidence="# 证据记录\n", risk="# 风险记录\n")
        self.assertEqual(face["skip_kind"], "vacuum")
        self.assertIn("无观测义务", face["skip_reason"])
        # Trivially compliant vacuum (rate 1.0, deferred 0) still computed
        # by the single-source function — presented, not guessed.
        self.assertEqual(face["session_closure_rate"], 1.0)
        self.assertTrue(face["compliant"])

    def test_orchestration_fallback_nulls_metrics_and_discloses(self):
        face = self._face(ledger=LEDGER_MALFORMED)
        self.assertEqual(face["skip_kind"], "orchestration_fallback")
        # CR-R1-2: numbers off a partial/broken read must not masquerade
        # as measured — Check 42's fallback branch prints no rate either.
        self.assertIsNone(face["session_closure_rate"])
        self.assertIsNone(face["deferred_detections"])
        self.assertIsNone(face["problems_raised"])
        self.assertIsNone(face["closed"])
        self.assertIsNone(face["compliant"])
        self.assertEqual(face["anomaly"]["kind"], "ledger_parse")

    def test_window_session_when_snapshot_carries_today(self):
        face = self._face(snapshot=SNAPSHOT_WITH_TODAY)
        self.assertEqual(face["window"], "session")
        self.assertIn("window=session", face["window_note"])
        self.assertIn("会话身份关联", face["window_note"])

    def test_window_daily_aggregate_degradation_is_disclosed(self):
        face = self._face(snapshot=SNAPSHOT_WITHOUT_TODAY)
        self.assertEqual(face["window"], "daily-aggregate")
        # 禁止无标注的静默降级 (ADR §3.2.3 / §2.4 L4).
        self.assertIn("按日聚合", face["window_note"])
        self.assertIn("精度降级", face["window_note"])
        # F-P3-3 (review-FEAT-082-CODE-R0 §五): the dedicated wider clip
        # (160) keeps the FULL degradation note — the ADR anchor no
        # longer truncates mid-citation.
        self.assertIn("禁止无标注的静默降级", face["window_note"])
        self.assertIn("ADR-021 §3.2.3 / §2.4 L4", face["window_note"])


class SessionClosureAggregateTests(unittest.TestCase):
    """End-to-end wiring: the behavior face gains the closure sub-face
    (ONE new key; every existing key unchanged), the text face renders
    the line, budget exhaustion defers the section, and the metric never
    pretends the health check ran."""

    @staticmethod
    def _today_fixture_kwargs():
        today = date.today().isoformat()
        return {
            "evidence": EVIDENCE_FULL_CLOSURE.replace(_CLOSURE_TODAY, today),
            "ledger": LEDGER_FIRED.replace(_CLOSURE_TODAY, today),
        }

    def test_behavior_face_gains_closure_subface(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_closure_fixture(tmp, **self._today_fixture_kwargs())
            payload = _run_aggregate(tmp)
        behavior = payload["behavior"]
        # 向后兼容 + FEAT-082「新增键 only」的严格形态（F-P3-2b：存在性
        # 断言升级为键集合相等——behavior 平键集 = FEAT-040 冻结面，恰 1
        # 个新增嵌套子面）.
        self.assertEqual(
            set(behavior),
            {"profile", "source", "env_var", "plan_tracker_key",
             "reverted", "invariants", "invalid", "session_closure"})
        closure = behavior["session_closure"]
        self.assertEqual(closure["deferred_detections"], 1)
        self.assertEqual(closure["session_closure_rate"], 0.0)
        self.assertIsNone(closure["skip_kind"])
        # 指标呈现 ≠ 健康检查已跑（FEAT-082 验收 2）.
        self.assertEqual(payload["health"]["state"], "deferred")
        self.assertIn("check-governance",
                      payload["health"]["pending_checks"])

    def test_text_face_renders_the_closure_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_closure_fixture(tmp, **self._today_fixture_kwargs())
            args = ba.build_arg_parser().parse_args(
                ["--project-root", tmp, "--format", "text"])
            buf = io.StringIO()
            with redirect_stdout(buf):
                ba.cmd_governance_bootstrap(args)
        lines = buf.getvalue().rstrip("\n").split("\n")
        self.assertLessEqual(len(lines), 40)
        closure_lines = [ln for ln in lines
                         if ln.startswith("session-closure:")]
        self.assertEqual(len(closure_lines), 1)
        self.assertIn("deferred 1", closure_lines[0])
        self.assertIn("rate 0%", closure_lines[0])

    def test_zero_budget_defers_the_closure_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_closure_fixture(tmp, **self._today_fixture_kwargs())
            payload = _run_aggregate(tmp, ["--budget-ms", "0"])
        sections = {d["section"] for d in payload["deferred"]}
        self.assertIn("behavior.session_closure", sections)
        for entry in payload["deferred"]:
            self.assertEqual(entry["reason"], "budget_exhausted")
        # Fail-safe honesty: the section that never ran is absent.
        self.assertNotIn("session_closure", payload["behavior"])


class SessionClosureSingleSourceTests(unittest.TestCase):
    """FEAT-083: the FEAT-082 disclosed mirror is RETIRED — engine
    (Check 42's thin delegation) and bootstrap (the behavior sub-face)
    both consume checks.provenance_domain's collector, so the
    bidirectional differential is converted to INTERFACE-EQUIVALENCE +
    SINGLE-SOURCE assertions (review-FEAT-082-CODE-R0 §6.3). The two
    read-failure arms the old differential never pinned (F-P3-2a) are
    added on the ONE shared implementation — non-UTF-8 bytes trigger a
    REAL read failure (same construction as the engine-side
    Check42DeferredSignalTests), no permission tricks, stable
    cross-platform."""

    _VARIANTS = {
        "full": dict(),
        "partial": dict(evidence=EVIDENCE_PARTIAL_CLOSURE, risk=RISK_LOG),
        "deferred": dict(ledger=LEDGER_FIRED + LEDGER_EXEMPT),
        "malformed": dict(ledger=LEDGER_MALFORMED),
        "snapshot-session": dict(snapshot=SNAPSHOT_WITH_TODAY),
        "snapshot-stale": dict(snapshot=SNAPSHOT_WITHOUT_TODAY),
        "vacuum": dict(evidence="# 证据记录\n", risk="# 风险记录\n"),
    }

    def test_engine_symbol_equals_shared_collector_on_every_fixture(self):
        # Interface equivalence: the legacy engine symbol (now a thin
        # delegation, signature unchanged) and a direct call to the
        # shared leaf return the identical triple on every fixture tree.
        vw = _import_engine(self)
        from checks import provenance_domain as pd
        for name, kwargs in self._VARIANTS.items():
            with tempfile.TemporaryDirectory() as tmp:
                _make_closure_fixture(tmp, **kwargs)
                gov = Path(tmp) / ".governance"
                via_engine = vw._collect_session_closure_events(
                    governance_dir=gov, today=_CLOSURE_TODAY)
                direct = pd.collect_session_closure_events(
                    gov, today=_CLOSURE_TODAY)
            self.assertEqual(
                via_engine, direct,
                "engine delegation != shared leaf (%s)" % name)

    def test_mirror_is_fully_retired(self):
        # Zero second implementation, pinned on the sources: every
        # bootstrap mirror symbol is gone, and the engine keeps ONLY the
        # thin delegation symbol (its own collection body is gone).
        ba_source = (_INFRA_DIR / "bootstrap_aggregate.py").read_text(
            encoding="utf-8")
        for symbol in ("def _collect_session_closure_events",
                       "_closure_evidence_events", "_closure_risk_events",
                       "_closure_ledger_events", "_RISK_TERMINAL_WORDS",
                       "_CLOSURE_LEDGER_FILENAME"):
            self.assertNotIn(symbol, ba_source,
                             "retired mirror symbol still present: %s"
                             % symbol)
        vw_source = (_INFRA_DIR / "verify_workflow.py").read_text(
            encoding="utf-8")
        self.assertNotIn("_read_deferred_ledger_events", vw_source,
                         "engine collection body still present")
        self.assertNotIn("_RISK_TERMINAL_WORDS", vw_source,
                         "engine word-set constant still present")
        # The shared leaf owns the vocabulary; the storage contract the
        # engine's write-guard face keeps (its own alias) is pinned
        # equal to the leaf's reader constant.
        from checks import provenance_domain as pd
        self.assertEqual(pd.RISK_TERMINAL_WORDS, ("关闭", "收窄", "升级"))
        vw = _import_engine(self)
        self.assertEqual(pd.CLOSURE_LEDGER_FILENAME,
                         vw._DEFERRED_LEDGER_FILENAME)

    def test_ledger_read_failure_is_disclosed_not_silent(self):
        # F-P3-2a arm 1: the ledger exists but is unreadable → the
        # ledger_read anomaly (orchestration_fallback face), never a
        # silent vacuum. The engine delegation stays equivalent under
        # the same failure.
        vw = _import_engine(self)
        from checks import provenance_domain as pd
        with tempfile.TemporaryDirectory() as tmp:
            _make_closure_fixture(tmp)
            gov = Path(tmp) / ".governance"
            (gov / pd.CLOSURE_LEDGER_FILENAME).write_bytes(
                b"\xff\xfe not utf8")
            direct = pd.collect_session_closure_events(
                gov, today=_CLOSURE_TODAY)
            via_engine = vw._collect_session_closure_events(
                governance_dir=gov, today=_CLOSURE_TODAY)
        self.assertEqual(direct, via_engine)
        self.assertEqual(direct[2]["anomaly"]["kind"], "ledger_read")

    def test_row_read_failure_is_disclosed_not_silent(self):
        # F-P3-2a arm 2: evidence-log.md unreadable → the row_read
        # anomaly; the OTHER arms keep collecting (fail-closed
        # disclosure, not a standing-down of the whole face). The engine
        # delegation stays equivalent under the same failure.
        vw = _import_engine(self)
        from checks import provenance_domain as pd
        with tempfile.TemporaryDirectory() as tmp:
            _make_closure_fixture(tmp)
            gov = Path(tmp) / ".governance"
            (gov / "evidence-log.md").write_bytes(b"\xff\xfe not utf8")
            direct = pd.collect_session_closure_events(
                gov, today=_CLOSURE_TODAY)
            via_engine = vw._collect_session_closure_events(
                governance_dir=gov, today=_CLOSURE_TODAY)
        self.assertEqual(direct, via_engine)
        anomaly = direct[2]["anomaly"]
        self.assertEqual(anomaly["kind"], "row_read")
        self.assertIn("evidence-log.md unreadable", anomaly["reason"])
        kinds = {(e["id"], e["kind"]) for e in direct[0]}
        self.assertIn(("RISK-910", "problem"), kinds)
        self.assertIn(("RISK-910", "closure"), kinds)

    def test_face_numbers_equal_check42_judgment_on_same_tree(self):
        vw = _import_engine(self)
        from checks.provenance_domain import session_closure_rate
        from checks.loop_gate_processor import classify_observation_face
        for name, kwargs in self._VARIANTS.items():
            with tempfile.TemporaryDirectory() as tmp:
                _make_closure_fixture(tmp, **kwargs)
                gov = Path(tmp) / ".governance"
                face = ba.session_closure_face(gov, _CLOSURE_TODAY)
                events, _note, state = vw._collect_session_closure_events(
                    governance_dir=gov, today=_CLOSURE_TODAY)
            rate = session_closure_rate(events)
            skip = classify_observation_face(
                rate["problems_raised"], rate["deferred_detections"],
                state["anomaly"])
            expected_skip = skip["skip_kind"] if skip else None
            self.assertEqual(face["skip_kind"], expected_skip, name)
            if expected_skip == "orchestration_fallback":
                continue  # nulled metrics — disclosed, not compared
            self.assertEqual(
                face["session_closure_rate"],
                rate["session_closure_rate"], name)
            self.assertEqual(
                face["deferred_detections"],
                rate["deferred_detections"], name)
            self.assertEqual(face["problems_raised"],
                             rate["problems_raised"], name)
            self.assertEqual(face["closed"], rate["closed"], name)
            self.assertEqual(face["compliant"], rate["compliant"], name)


if __name__ == "__main__":
    unittest.main()
