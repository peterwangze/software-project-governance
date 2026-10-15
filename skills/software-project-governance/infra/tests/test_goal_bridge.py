"""FEAT-097 guard tests — infra/goal_bridge.py (goal 与预算桥接).

RPG session 实测 (报告 §3.1/§3.8): goal 60 轮 6h 撞线 blocked 后静默续跑
21 轮、38h 仅 2 次 ask — the intent-break this bridge closes:

  * RUNNING→DRAINING→CHECKPOINTED→BLOCKED state mapping (data table,
    grep-able) — the bridge MAPS harness goal signals onto governance
    states, it never replaces the harness goal (non_goal);
  * multi-dimension budget danger-zone collection: 轮次/token/墙钟/成本
    ANY dimension entering its danger zone triggers 收口 (DRAINING →
    CHECKPOINTED) — the old 70%-rounds-only rule was necessary but NOT
    sufficient (it watched ONE dimension);
  * checkpoint artifact schema: 账本 (authority-ledger summary) + 义务
    (open obligations) + 修订 (revision) + 规则版本 (rules_version —
    mixed-version resume can never be SILENT) + 预算消耗 (per-dimension
    usage) — cross-session recovery is idempotent;
  * blocked 后禁未授权续跑: every unauthorized execution attempt is
    REFUSED and machine-audited — fault injection proves the count of
    unauthorized NEW executions is exactly 0; resume-direction rulings
    from CHECKPOINTED are likewise refused without authorized_by
    (symmetric authorization, P2-1 — only abort, the safe direction,
    is exempt);
  * P1-1 (review R0): all three mutating entrypoints run their
    load→mutate→save under the artifact's ``governance_store.
    _TargetLock`` — cross-process contention refuses retryable
    (lock_contention) and a racing refuse can never erase a recorded
    user ruling (serialization regression pair);
  * CHECKPOINTED presentation carries scope-ruling options (禁静默续跑:
    ambition-infeasible MUST bring the scope ruling to the user);
  * rollback switch ``GOVERNANCE_GOAL_BRIDGE=off`` restores legacy
    harness-goal behavior (passthrough gate).

All fixtures run in temp directories — the real .governance is never
touched.

Run:
    python -m unittest skills/software-project-governance/infra/tests/test_goal_bridge.py -v
"""

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import goal_bridge as gb  # noqa: E402


class GoalBridgeTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp_ctx = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp_ctx.name)
        self.gov = self.tmp / ".governance"
        self.gov.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp_ctx.cleanup()

    # ── helpers ────────────────────────────────────────────────────────

    def record(self, goal="goal-x", **kw):
        return gb.record_execution(
            goal, governance_dir=self.gov, **kw)

    def checkpoint(self, goal="goal-x", **kw):
        return gb.write_checkpoint(
            goal, governance_dir=self.gov, **kw)

    def ruling(self, goal="goal-x", **kw):
        return gb.record_ruling(goal, governance_dir=self.gov, **kw)

    def status(self, goal="goal-x", **kw):
        return gb.goal_status(goal, governance_dir=self.gov, **kw)

    def load_artifact(self, goal="goal-x"):
        path = self.gov / "goal-bridge" / ("{0}.json".format(goal))
        return json.loads(path.read_text(encoding="utf-8"))

    def assertRefused(self, result, code):
        self.assertTrue(result.get("error"), result)
        self.assertEqual(result.get("code"), code, result)


class mock_env:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self._saved = None

    def __enter__(self):
        self._saved = os.environ.get(self.name)
        os.environ[self.name] = self.value
        return self

    def __exit__(self, *exc_info):
        if self._saved is None:
            os.environ.pop(self.name, None)
        else:
            os.environ[self.name] = self._saved
        return False


# ── ② 多维权预算危险区收口 ────────────────────────────────────────────


class BudgetDangerZoneTests(GoalBridgeTestCase):
    def test_any_dimension_danger_triggers_collection(self):
        # 任一入危险区即收口: four independent fault injections — each
        # dimension ALONE in its danger zone must recommend DRAINING.
        cases = [
            dict(rounds=48, tokens=100, seconds=100, cost=1.0),   # 80% rounds
            dict(rounds=1, tokens=1_600_000, seconds=100, cost=1.0),  # 80% tok
            dict(rounds=1, tokens=100, seconds=34_000, cost=1.0),  # 1.58x clock
            dict(rounds=1, tokens=100, seconds=100, cost=180.0),   # 1.8x cost
        ]
        for usage in cases:
            judged = gb.judge_budget(**usage)
            danger_dims = [d for d, z in judged["zones"].items()
                           if z["zone"] == "danger"]
            self.assertEqual(len(danger_dims), 1, usage)
            self.assertEqual(judged["recommended_transition"],
                             ("RUNNING", "DRAINING"), usage)

    def test_rounds_warning_alone_is_not_sufficient(self):
        # 70% 轮量 = necessary but NOT sufficient (the OLD single-dimension
        # rule): rounds in the WARNING band with every other dimension
        # safe leaves the goal RUNNING.
        judged = gb.judge_budget(rounds=39, tokens=100, seconds=100,
                                 cost=1.0)  # 65% rounds = warning band
        self.assertEqual(judged["zones"]["rounds"]["zone"], "warning")
        self.assertFalse(judged["any_danger"])
        self.assertEqual(judged["recommended_transition"], None)

    def test_rounds_at_exact_danger_boundary_collects(self):
        # P2-4/P2-R1-E (review R0/R1): 42/60 = 0.70 EXACTLY — the
        # ``share >= danger_ratio`` EQUALITY position must collect (a
        # boundary round may not slip through as merely-warning).
        judged = gb.judge_budget(rounds=42, tokens=100, seconds=100,
                                 cost=1.0)
        self.assertEqual(judged["zones"]["rounds"]["share"], 0.7)
        self.assertEqual(judged["zones"]["rounds"]["zone"], "danger")
        self.assertTrue(judged["any_danger"])
        self.assertEqual(judged["recommended_transition"],
                         ("RUNNING", "DRAINING"))

    def test_two_dimensions_danger_simultaneously(self):
        # P2-4/P2-R1-E: rounds+tokens BOTH in their danger zones — the
        # collection face must name BOTH dimensions (any_danger
        # aggregates; no single-dimension shadowing).
        judged = gb.judge_budget(rounds=48, tokens=1_600_000,
                                 seconds=100, cost=1.0)
        danger = sorted(d for d, z in judged["zones"].items()
                        if z["zone"] == "danger")
        self.assertEqual(danger, ["rounds", "tokens"])
        self.assertTrue(judged["any_danger"])
        # …and the record face reports the same pair on transition:
        result = self.record(rounds=48, tokens=1_600_000, seconds=100,
                             cost=1.0)
        self.assertTrue(result["allowed"], result)
        self.assertTrue(result["collected"], result)
        self.assertEqual(result["danger_dimensions"],
                         ["rounds", "tokens"])

    def test_all_safe_dimensions_stay_running(self):
        judged = gb.judge_budget(rounds=10, tokens=500_000, seconds=5_000,
                                 cost=20.0)
        self.assertFalse(judged["any_danger"])
        self.assertTrue(all(z["zone"] == "safe"
                            for z in judged["zones"].values()))

    def test_thresholds_are_config_data_not_code_forks(self):
        # assumption_record: 映射与阈值=配置面数据（调整不动状态机）—
        # a custom threshold table changes the verdict without ANY code
        # path change.
        custom = json.loads(json.dumps(gb.DEFAULT_BUDGET_CONFIG))
        custom["rounds"]["danger_ratio"] = 0.30
        judged = gb.judge_budget(rounds=20, tokens=1, seconds=1, cost=0.0,
                                 config=custom)
        self.assertEqual(judged["zones"]["rounds"]["zone"], "danger")

    def test_threshold_table_greppable(self):
        text = gb.render_thresholds_text()
        for anchor in ("dimension=rounds", "dimension=tokens",
                       "dimension=wall_clock", "dimension=cost",
                       "danger_ratio=", "limit="):
            self.assertIn(anchor, text)


# ── ① 状态映射 ────────────────────────────────────────────────────────


class StateMappingTests(GoalBridgeTestCase):
    def test_mapping_table_is_data_and_greppable(self):
        text = gb.render_mapping_text()
        for anchor in ("RUNNING --danger_zone--> DRAINING",
                       "DRAINING --drained--> CHECKPOINTED",
                       "CHECKPOINTED --scope_ruling--> RUNNING",
                       "BLOCKED --authorized_resume--> RUNNING"):
            self.assertIn(anchor, text)

    def test_record_bootstraps_running_state_on_first_use(self):
        result = self.record(rounds=1, tokens=100, seconds=10, cost=0.0)
        self.assertFalse(result.get("error"), result)
        self.assertTrue(result["allowed"])
        artifact = self.load_artifact()
        self.assertEqual(artifact["state"], "RUNNING")

    def test_danger_on_record_auto_transitions_to_draining(self):
        result = self.record(rounds=50, tokens=100, seconds=10, cost=0.0)
        self.assertTrue(result["allowed"])  # the triggering round finishes
        artifact = self.load_artifact()
        self.assertEqual(artifact["state"], "DRAINING")
        self.assertEqual(artifact["transition_history"][-1]["trigger"],
                         "danger_zone")
        self.assertIn("rounds", artifact["transition_history"][-1]["note"])

    def test_draining_new_work_refused_in_flight_allowed(self):
        self.record(rounds=50, tokens=100, seconds=10, cost=0.0)
        new_work = self.record(rounds=51, tokens=100, seconds=10, cost=0.0)
        self.assertRefused(new_work, gb.CODE_DRAINING)
        in_flight = self.record(rounds=51, tokens=100, seconds=10,
                                cost=0.0, in_flight=True)
        self.assertTrue(in_flight["allowed"])

    def test_persistent_danger_in_draining_checkpoints(self):
        self.record(rounds=50, tokens=100, seconds=10, cost=0.0)
        result = self.record(rounds=52, tokens=100, seconds=10, cost=0.0,
                             in_flight=True)
        self.assertTrue(result["allowed"])
        artifact = self.load_artifact()
        self.assertEqual(artifact["state"], "CHECKPOINTED")

    def test_checkpoint_action_materializes_artifact(self):
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        result = self.checkpoint(task_ref="FEAT-097")
        self.assertFalse(result.get("error"), result)
        artifact = self.load_artifact()
        self.assertEqual(artifact["state"], "CHECKPOINTED")


# ── ③ checkpoint 工件 schema ──────────────────────────────────────────


class CheckpointArtifactTests(GoalBridgeTestCase):
    def test_schema_carries_all_five_faces(self):
        # 账本 + 义务 + 修订 + 规则版本 + 预算消耗 (acceptance ③).
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        # P2-3/P2-R1-D (review R0/R1): seed a REAL authority-ledger so
        # the ledger face is exercised on actual status() keys — the
        # assertions below are unconditional (no idle conditional on
        # available=False spinning empty).
        import authority_ledger as al
        writer = al.LedgerWriter(self.gov)
        seeded = writer.record_task(
            "FEAT-097",
            subject="**FEAT-097 checkpoint 账本面真键断言——测试播种**",
            status="⏳ 待执行")
        self.assertEqual(seeded["status"], "registered", seeded)
        self.checkpoint(task_ref="FEAT-097", obligations=[
            {"obligation_id": "REVIEW-FEAT-097-R1", "kind": "recheck"},
        ])
        artifact = self.load_artifact()
        self.assertEqual(artifact["schema_version"], 1)
        # 账本 (authority-ledger best-effort summary — absent ⇒ disclosed)
        self.assertIn("ledger", artifact)
        # the seeded ledger makes available=True a FACT, so the real
        # keys must carry real (non-null) values:
        self.assertIs(artifact["ledger"].get("available"), True,
                      artifact["ledger"])
        self.assertIsInstance(artifact["ledger"]["events_lines"], int)
        self.assertGreaterEqual(artifact["ledger"]["events_lines"], 1)
        self.assertIsInstance(artifact["ledger"]["last_seq"], int)
        self.assertGreaterEqual(artifact["ledger"]["last_seq"], 1)
        self.assertIs(artifact["ledger"]["integrity_ok"], True,
                      artifact["ledger"])
        # the R0 hallucinated constant-null key must not come back
        self.assertNotIn("events_total", artifact["ledger"])
        # 义务
        self.assertEqual(artifact["obligations"][0]["obligation_id"],
                         "REVIEW-FEAT-097-R1")
        # 修订 (monotone)
        self.assertGreaterEqual(artifact["revision"], 1)
        # 规则版本 (never silent on mixed versions — resolves from the
        # plugin's own SKILL.md frontmatter, never fabricated "unknown")
        self.assertTrue(artifact["rules_version"])
        self.assertNotEqual(artifact["rules_version"], "unknown")
        # 预算消耗 (per-dimension usage at checkpoint time)
        self.assertIn("rounds", artifact["budget_consumption"])
        self.assertEqual(artifact["budget_consumption"]["rounds"]["used"],
                         10)

    def test_checkpoint_recovery_idempotent(self):
        # reliability: 重复恢复状态一致 — load→write→load leaves the
        # artifact byte-stable on revision and state.
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        first = self.checkpoint(task_ref="FEAT-097")
        self.assertFalse(first.get("error"), first)
        again = self.checkpoint(task_ref="FEAT-097")
        self.assertFalse(again.get("error"), again)
        artifact = self.load_artifact()
        self.assertEqual(artifact["revision"], first["revision"])
        self.assertEqual(artifact["state"], "CHECKPOINTED")
        # the idempotent re-checkpoint added no duplicate history rows
        checkpoints_seen = [h for h in artifact["transition_history"]
                            if h["to"] == "CHECKPOINTED"]
        self.assertEqual(len(checkpoints_seen), 1)

    def test_resume_with_different_rules_version_is_loud(self):
        # 禁混合版本静默升级: a resume under a DIFFERENT rules version
        # proceeds only with an explicit disclosure + history row.
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        self.checkpoint(task_ref="FEAT-097")
        result = self.ruling(decision="continue",
                             authorized_by="user",
                             rules_version="999.0.0-future")
        self.assertFalse(result.get("error"), result)
        self.assertTrue(result.get("rules_version_changed"),
                        result)
        artifact = self.load_artifact()
        mixed = [h for h in artifact["transition_history"]
                 if h.get("rules_version_changed")]
        self.assertEqual(len(mixed), 1)

    def test_record_path_discloses_rules_version_change(self):
        # P2-2/P2-R1-C (review R0/R1): the RECORD path (cross-session
        # RUNNING resume — the path that never sees a ruling) also
        # compares the rules version on EVERY mutation: a mismatch is
        # LOUD (disclosure history row + re-pin) but never blocks
        # (DEC-330: rules changes take effect via checkpoint + a NEW
        # session).
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        with mock.patch.object(gb, "_default_rules_version",
                               return_value="999.0.0-future"):
            resumed = self.record(rounds=12, tokens=1_000, seconds=10,
                                  cost=0.0)
            self.assertFalse(resumed.get("error"), resumed)
            self.assertTrue(resumed["allowed"], resumed)  # never blocks
        artifact = self.load_artifact()
        # re-pinned to the current (mocked) version…
        self.assertEqual(artifact["rules_version"], "999.0.0-future")
        # …with exactly ONE loud disclosure row, state undisturbed:
        mixed = [h for h in artifact["transition_history"]
                 if h.get("rules_version_changed")]
        self.assertEqual(len(mixed), 1)
        self.assertEqual(mixed[0]["trigger"], "rules_version_changed")
        self.assertIn("999.0.0-future", mixed[0]["note"])
        self.assertEqual(artifact["state"], "RUNNING")
        # a second record under the SAME (now re-pinned) version adds
        # no further row — disclosure is once per actual change:
        with mock.patch.object(gb, "_default_rules_version",
                               return_value="999.0.0-future"):
            self.record(rounds=13, tokens=1_000, seconds=10, cost=0.0)
        artifact = self.load_artifact()
        self.assertEqual(
            len([h for h in artifact["transition_history"]
                 if h.get("rules_version_changed")]), 1)

    def test_checkpointed_presentation_carries_scope_ruling_options(self):
        # ux 阈值: CHECKPOINTED 呈现携带范围裁决选项 (禁静默续跑).
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        result = self.checkpoint(task_ref="FEAT-097")
        options = result["scope_ruling_options"]
        self.assertTrue(options)
        labels = {option["id"] for option in options}
        self.assertIn("reduce-scope", labels)
        self.assertIn("extend-budget", labels)
        self.assertIn("abort", labels)
        for option in options:
            self.assertTrue(option["description"].strip())
        self.assertIn("MUST", json.dumps(result["ask_contract"],
                                         ensure_ascii=False))


# ── ④ blocked 后禁未授权续跑（故障注入） ─────────────────────────────


class ResumeAuthorizationTests(GoalBridgeTestCase):
    def _drive_to_blocked(self):
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        self.checkpoint(task_ref="FEAT-097")
        blocked = self.ruling(decision="abort")
        self.assertFalse(blocked.get("error"), blocked)
        return blocked

    def _drive_to_checkpointed(self):
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        self.checkpoint(task_ref="FEAT-097")

    def test_checkpointed_unauthorized_resume_refused_and_audited(self):
        # P2-1/P2-R1-B (review R0/R1): authorization is SYMMETRIC — every
        # RESUME-direction ruling from CHECKPOINTED (continue /
        # extend-budget / reduce-scope) requires a non-empty
        # authorized_by exactly as the BLOCKED face does (the option
        # descriptions themselves promise user confirmation).  Each
        # decision drives its OWN fresh goal artifact (subTest does not
        # rebuild the fixture between iterations).
        for decision in ("continue", "extend-budget", "reduce-scope"):
            with self.subTest(decision=decision):
                goal = "cpk-unauth-{0}".format(decision.replace("-", ""))
                self.record(goal=goal, rounds=10, tokens=1_000,
                            seconds=10, cost=0.0)
                self.checkpoint(goal=goal, task_ref="FEAT-097")
                refused = self.ruling(goal=goal, decision=decision)
                self.assertRefused(refused, gb.CODE_UNAUTHORIZED_RESUME)
                artifact = self.load_artifact(goal=goal)
                # refused AND audited (kind=resume row), state unmoved:
                self.assertEqual(artifact["state"], "CHECKPOINTED")
                rows = artifact["unauthorized_attempts"]
                self.assertEqual(len(rows), 1, artifact)
                self.assertEqual(rows[0]["kind"], "resume")
                self.assertEqual(rows[0]["decision"], decision)
                self.assertEqual(rows[0]["state"], "CHECKPOINTED")

    def test_checkpointed_abort_without_authorization_is_safe_direction(self):
        # P2-1: abort is EXEMPT — terminating is the safe direction, so
        # an UNAUTHORIZED abort still lands BLOCKED (contrast: resuming
        # FROM the block still needs authorization, see the BLOCKED
        # face tests above).
        self._drive_to_checkpointed()
        result = self.ruling(decision="abort")  # no authorized_by
        self.assertFalse(result.get("error"), result)
        artifact = self.load_artifact()
        self.assertEqual(artifact["state"], "BLOCKED")
        self.assertEqual(artifact["scope_ruling"]["decision"], "abort")

    def test_blocked_unauthorized_resume_refused_and_audited(self):
        self._drive_to_blocked()
        resume = self.ruling(decision="continue")  # no authorized_by
        self.assertRefused(resume, gb.CODE_UNAUTHORIZED_RESUME)
        artifact = self.load_artifact()
        self.assertTrue(
            [a for a in artifact["unauthorized_attempts"]
             if a["kind"] == "resume"])

    def test_blocked_execution_fault_injection_zero_unauthorized(self):
        # THE acceptance-④ fault injection: hammer the gate from BLOCKED
        # with every spelling — none may execute; all must be audited.
        self._drive_to_blocked()
        attempts = [
            self.record(rounds=30, tokens=1, seconds=1, cost=0.0),
            self.record(rounds=30, tokens=1, seconds=1, cost=0.0,
                        in_flight=True),
            self.record(rounds=31, tokens=1, seconds=1, cost=0.0),
        ]
        for refused in attempts:
            self.assertRefused(refused, gb.CODE_BLOCKED)
            self.assertIsNone(refused.get("allowed"))
        artifact = self.load_artifact()
        audited = [a for a in artifact["unauthorized_attempts"]
                   if a["kind"] == "execution"]
        self.assertEqual(len(audited), len(attempts))
        # 未授权新增执行 = 0 (every attempt returned allowed=False and
        # the state never left BLOCKED).
        self.assertEqual(artifact["state"], "BLOCKED")

    def test_blocked_authorized_resume_allows_execution(self):
        self._drive_to_blocked()
        authorized = self.ruling(decision="reduce-scope",
                                 authorized_by="user",
                                 new_limits={"rounds": 80})
        self.assertFalse(authorized.get("error"), authorized)
        artifact = self.load_artifact()
        self.assertEqual(artifact["state"], "RUNNING")
        self.assertEqual(artifact["budget_config"]["rounds"]["limit"], 80)
        after = self.record(rounds=55, tokens=1, seconds=1, cost=0.0)
        self.assertTrue(after["allowed"])

    def test_checkpointed_execution_without_ruling_refused(self):
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        self.checkpoint(task_ref="FEAT-097")
        refused = self.record(rounds=11, tokens=1_000, seconds=10,
                              cost=0.0)
        self.assertRefused(refused, gb.CODE_SCOPE_RULING_REQUIRED)
        artifact = self.load_artifact()
        self.assertEqual(artifact["state"], "CHECKPOINTED")

    def test_checkpointed_with_ruling_resumes_running(self):
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        self.checkpoint(task_ref="FEAT-097")
        ruled = self.ruling(decision="extend-budget",
                            authorized_by="user",
                            new_limits={"rounds": 100})
        self.assertFalse(ruled.get("error"), ruled)
        after = self.record(rounds=65, tokens=1_000, seconds=10, cost=0.0)
        self.assertTrue(after["allowed"])
        self.assertEqual(self.load_artifact()["state"], "RUNNING")

    def test_abort_ruling_is_terminal_block(self):
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        self.checkpoint(task_ref="FEAT-097")
        result = self.ruling(decision="abort")
        self.assertFalse(result.get("error"), result)
        self.assertEqual(self.load_artifact()["state"], "BLOCKED")


# ── P1-1 (review R0/R1): artifact-lock serialization regressions ──────


class ConcurrentSerializationTests(GoalBridgeTestCase):
    """The lost-update race this pair guards (R0 P1-1 probe, now a
    permanent regression): a racing writer's load→mutate→save must be
    EXCLUDED from (or serialized after) the current writer's window —
    the user's abort ruling and the audit rows can never be erased by
    a stale-snapshot write-back, and cross-process contention refuses
    retryable instead of interleaving."""

    _HOLDER_SOURCE = """\
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from governance_store import _TargetLock  # noqa: E402
target, ready, release = (Path(p) for p in sys.argv[2:5])
with _TargetLock(target, 30.0):
    ready.write_text("held", encoding="utf-8")
    deadline = time.monotonic() + 20.0
    while not release.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
"""

    def test_cross_process_lock_contention_refused_retryable(self):
        # ① a REAL second process holds the artifact target lock → all
        # three mutating entrypoints refuse with lock_contention
        # (disposition retryable) and leave the artifact untouched.
        import subprocess
        self.record(rounds=5, tokens=100, seconds=5, cost=0.0)
        artifact_file = self.gov / "goal-bridge" / "goal-x.json"
        before = artifact_file.read_bytes()
        holder = self.tmp / "feat097_hold_lock.py"
        holder.write_text(self._HOLDER_SOURCE, encoding="utf-8")
        ready = self.tmp / "lock_ready.flag"
        release = self.tmp / "lock_release.flag"
        proc = subprocess.Popen(
            [sys.executable, str(holder), str(_INFRA_DIR),
             str(artifact_file), str(ready), str(release)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 15.0
            while not ready.exists() and time.monotonic() < deadline:
                if proc.poll() is not None:
                    self.fail("lock holder died early (rc={0})"
                              .format(proc.returncode))
                time.sleep(0.05)
            self.assertTrue(ready.exists(),
                            "lock holder never signaled ready")
            contention_calls = [
                ("record", lambda: gb.record_execution(
                    "goal-x", rounds=20, tokens=100, seconds=10,
                    cost=0.0, governance_dir=self.gov,
                    timeout_seconds=1.0)),
                ("checkpoint", lambda: gb.write_checkpoint(
                    "goal-x", task_ref="FEAT-097",
                    governance_dir=self.gov, timeout_seconds=1.0)),
                ("ruling", lambda: gb.record_ruling(
                    "goal-x", decision="continue",
                    governance_dir=self.gov, timeout_seconds=1.0)),
            ]
            for face, call in contention_calls:
                with self.subTest(face=face):
                    refused = call()
                    self.assertRefused(refused, gb.CODE_LOCK_CONTENTION)
                    self.assertEqual(refused["disposition"], "retryable")
            # refused-under-contention ops wrote NOTHING (no partial
            # state, no audit row) — bytes identical:
            self.assertEqual(artifact_file.read_bytes(), before)
        finally:
            release.write_text("go", encoding="utf-8")
            proc.wait(timeout=25)
        self.assertEqual(proc.returncode, 0)
        # the lock is freed — normal operation resumes (no wedge):
        resumed = self.record(rounds=6, tokens=100, seconds=5, cost=0.0)
        self.assertTrue(resumed["allowed"], resumed)
        self.assertEqual(self.load_artifact()["state"], "RUNNING")

    def test_racing_refuse_cannot_erase_user_abort_ruling(self):
        # ② serialization semantics (the R0 lost-update shape): while
        # the user's abort ruling is MID-WINDOW (loaded, about to
        # save), a racing refuse arrives — it must queue on the
        # artifact lock, load the POST-ruling state, and refuse per
        # the BLOCKED face; the ruling and BOTH audit trails survive.
        import threading
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        self.checkpoint(task_ref="FEAT-097")
        window_open = threading.Event()
        allow_save = threading.Event()
        rogue_done = threading.Event()
        rogue = {}
        real_save = gb._save
        calls = {"n": 0}

        def gated_save(path, artifact):
            calls["n"] += 1
            if calls["n"] == 1:
                # the abort ruling holds the artifact lock right now —
                # this is the interleave point the R0 race exploited.
                window_open.set()
                self.assertTrue(allow_save.wait(10.0),
                                "ruling save gate never released")
            return real_save(path, artifact)

        def run_ruling():
            self.ruling(decision="abort")

        def run_rogue():
            rogue["result"] = self.record(rounds=40, tokens=1,
                                          seconds=1, cost=0.0)
            rogue_done.set()

        with mock.patch.object(gb, "_save", new=gated_save):
            ruling_thread = threading.Thread(target=run_ruling)
            ruling_thread.start()
            self.assertTrue(window_open.wait(10.0),
                            "abort ruling never reached its save window")
            rogue_thread = threading.Thread(target=run_rogue)
            rogue_thread.start()   # queues on the artifact lock
            allow_save.set()       # …NOW the ruling's save may land
        ruling_thread.join(10.0)
        self.assertFalse(ruling_thread.is_alive(),
                         "abort ruling thread wedged")
        self.assertTrue(rogue_done.wait(10.0),
                        "racing refuse never completed")
        rogue_thread.join(10.0)
        # the racing refuse saw the POST-ruling state (BLOCKED face),
        # not its pre-ruling CHECKPOINTED snapshot:
        self.assertRefused(rogue["result"], gb.CODE_BLOCKED)
        self.assertIsNone(rogue["result"].get("allowed"))
        artifact = self.load_artifact()
        # the user's ruling was NOT erased by the racing write-back…
        self.assertEqual(artifact["state"], "BLOCKED")
        self.assertEqual(artifact["scope_ruling"]["decision"], "abort")
        # …and the rogue's audit row survived the ruling's save too:
        audited = [a for a in artifact["unauthorized_attempts"]
                   if a["kind"] == "execution"]
        self.assertEqual(len(audited), 1, artifact)


# ── 回退开关 + 性能 + 可检索性 ────────────────────────────────────────


class RollbackSwitchAndPerformanceTests(GoalBridgeTestCase):
    def test_disabled_switch_passthrough_legacy_behavior(self):
        # rollback_plan: 桥接开关关闭即回退既有 goal 行为（纯 harness
        # goal，无桥接门）.
        with mock_env(gb.DISABLE_ENV_VAR, "off"):
            passthrough = gb.record_execution(
                "goal-x", rounds=59, tokens=1_999_999, seconds=99_999,
                cost=999.0, governance_dir=self.gov)
        self.assertFalse(passthrough.get("error"), passthrough)
        self.assertTrue(passthrough["allowed"])
        self.assertTrue(passthrough["gate_disabled"])
        # zero bridge state was written
        self.assertFalse((self.gov / "goal-bridge").exists())

    def test_judgment_wall_clock_under_10ms(self):
        # performance: 预算信号采集与状态判定开销 ≤10ms 量级.
        samples = []
        for _ in range(9):
            t0 = time.perf_counter()
            judged = gb.judge_budget(rounds=30, tokens=900_000,
                                     seconds=15_000, cost=50.0)
            samples.append(time.perf_counter() - t0)
            self.assertFalse(judged["any_danger"])
        median = sorted(samples)[len(samples) // 2]
        self.assertLess(median, 0.010,
                        "judge_budget median {0:.4f}s blew the 10ms budget"
                        .format(median))

    def test_status_is_machine_readable_and_greppable(self):
        self.record(rounds=10, tokens=1_000, seconds=10, cost=0.0)
        status = self.status()
        self.assertFalse(status.get("error"), status)
        self.assertEqual(status["state"], "RUNNING")
        self.assertIn("zones", status)
        text = gb.render_status_text(status)
        for anchor in ("state=", "dimension=rounds", "zone="):
            self.assertIn(anchor, text)

    def test_goal_id_path_traversal_refused(self):
        bad = gb.record_execution("../escape", rounds=1, tokens=1,
                                  seconds=1, cost=0.0,
                                  governance_dir=self.gov)
        self.assertRefused(bad, gb.CODE_SCHEMA_VIOLATION)


# ── CLI face (module composition root) ────────────────────────────────


class CliFaceTests(GoalBridgeTestCase):
    def test_module_cli_roundtrip(self):
        import subprocess
        import sys as _sys
        base = [_sys.executable, str(_INFRA_DIR / "goal_bridge.py"),
                "--project-root", str(self.tmp)]
        run = lambda *extra: subprocess.run(
            list(base) + list(extra), stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        seeded = run("goal-bridge", "--action", "record", "--goal",
                     "cli-goal", "--rounds", "10", "--tokens", "1000",
                     "--seconds", "10", "--cost", "0")
        self.assertEqual(seeded.returncode, 0)
        checked = run("goal-bridge", "--action", "checkpoint", "--goal",
                      "cli-goal", "--task", "FEAT-097")
        self.assertEqual(checked.returncode, 0)
        # blocked gate via CLI: execution now refuses with exit 2
        refused = run("goal-bridge", "--action", "record", "--goal",
                      "cli-goal", "--rounds", "11", "--tokens", "1000",
                      "--seconds", "10", "--cost", "0")
        self.assertEqual(refused.returncode, 2)
        artifact = self.load_artifact("cli-goal")
        self.assertEqual(artifact["state"], "CHECKPOINTED")


if __name__ == "__main__":
    unittest.main()
