"""FIX-265 / REQ-145.3 — Check 36 risk-mitigation-closure tests (red→green).

Deliverable under test (design audit-145-watchdog-design-0.76.0.md §3.3,
test plan §5.2 — 12 cases, plus acceptance-item extras):

1. ``check_risk_mitigation_closure(risk_content=None, task_status_map=None)``
   in ``infra/checks/risk_domain.py``: WARN/FAIL progressive semantics
   R1 start-WARN / R2 FAIL (deadline passed OR high severity) / R3 WARN
   (cross-entity/archived ref) / R4 WARN (no machine-resolvable task ref
   and no exemption marker) / R5 skip (closed / exempted / ragged /
   undecidable).
2. Parser lock (F6): raw ``line.split("|")`` parts[9]=当前状态 /
   parts[10]=缓解动作 / parts[11]=截止日期 / parts[12]=关联任务 — same
   index set as Check 2/8; ``_governance_table_cells`` is NOT used.
3. Task status map rebuilt from ``task_priority.PriorityReport`` buckets
   (F11 — ``compute_unblocked_tasks`` exposes no status map); parse
   failure / missing plan-tracker → fail-safe WARN, never FAIL.
4. Numbering (F9): Check 36 block in ``cmd_check_governance`` co-exists
   with Check 35 (snapshot freshness, FIX-268) — 35 before 36, consecutive.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_risk_mitigation_closure.py -v
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


# ── Fixtures ────────────────────────────────────────────────────────────

_CANONICAL_HEADER = (
    "# 风险记录\n\n"
    "| 编号 | 日期 | 风险/阻塞描述 | 所属阶段 | 触发条件 | 影响 | 严重级别 | Owner | "
    "当前状态 | 缓解动作 | 截止日期 | 关联任务 | 备注 |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
)

# Canonical 13-content-column row template (raw parts: 1=编号, 2=日期, 7=严重级别,
# 8=Owner, 9=当前状态, 10=缓解动作, 11=截止日期, 12=关联任务, 13=备注).
def _risk_row(rid="RISK-001", created="2026-08-19", desc="风险描述", stage="开发 (6)",
              trigger="触发条件", impact="影响", severity="高", owner="Developer",
              status="打开", mitigation="缓解动作", deadline="2099-01-01",
              refs="FIX-300", note="—"):
    return (f"| {rid} | {created} | {desc} | {stage} | {trigger} | {impact} | "
            f"{severity} | {owner} | {status} | {mitigation} | {deadline} | "
            f"{refs} | {note} |")


def _risk_content(*rows):
    return _CANONICAL_HEADER + "\n" + "\n".join(rows) + "\n"


DONE = {"FIX-300": "✅ 完成 (2026-08-22)"}
OPEN = {"FIX-300": "⏳ 进行中"}


# ── R1-R5 rule fixtures ────────────────────────────────────────────────

class Check36RuleTests(unittest.TestCase):
    """Rule table fixtures over injectable rows + task_status_map."""

    def test_r1_default_active_status_is_not_completed_therefore_closed_state(self):
        """Design: closure == 已完成 only; WARN start when the referenced
        task is not completed (R1). Middle severity + future deadline so
        the R2 escalation signals stay off (R2 = R1 + 截止过 OR 高危)."""
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(
                _risk_row(severity="中", refs="FIX-300")),
            task_status_map=OPEN)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        w = [x for x in r["warnings"] if x["rule"] == "R1"]
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0]["risk_id"], "RISK-001")
        self.assertEqual(w[0]["task_refs"], ["FIX-300"])
        self.assertEqual(r["stats"]["warn_count"], 1)

    def test_r1_intermediate_status_not_closed(self):
        """缓解中/缓解完成 are NOT 已关闭 → still in flight (AUDIT-145 cases
        router RISK-003 / tv RISK-001 that Check 2/8 only sees as '打开')."""
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(
                _risk_row(status="缓解完成", severity="中", refs="FIX-300")),
            task_status_map=OPEN)
        self.assertEqual(r["verdict"], "WARN")
        self.assertIn("R1", {w["rule"] for w in r["warnings"]})

    def test_r2_fail_deadline_passed(self):
        """R1 + deadline parts[11] < today → FAIL (R2)."""
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(
                _risk_row(severity="中", deadline="2020-01-01", refs="FIX-300")),
            task_status_map=OPEN)
        self.assertEqual(r["verdict"], "FAIL")
        v = [x for x in r["violations"] if x["rule"] == "R2"]
        self.assertEqual(len(v), 1)
        self.assertEqual(v[0]["deadline"], "2020-01-01")
        self.assertEqual(r["stats"]["violation_count"], 1)

    def test_r2_fail_high_severity_future_deadline(self):
        """R1 + severity 高/严重 (deadline still in future) → FAIL (R2)."""
        for sev in ("高", "严重"):
            r = vw.check_risk_mitigation_closure(
                risk_content=_risk_content(
                    _risk_row(severity=sev, deadline="2099-01-01", refs="FIX-300")),
                task_status_map=OPEN)
            self.assertEqual(r["verdict"], "FAIL", f"severity={sev}")
            self.assertEqual([x["rule"] for x in r["violations"]], ["R2"])
            self.assertEqual(r["violations"][0]["severity"], sev)

    def test_pass_all_referenced_tasks_completed(self):
        """Completed task reference → closure satisfied (PASS, zero noise)."""
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(_risk_row(refs="FIX-300")),
            task_status_map=DONE)
        self.assertEqual(r["violations"], [])
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["stats"]["pass"], 1)

    def test_r3_warn_unknown_reference_never_fails(self):
        """Cross-entity / archived ref absent from the map → R3 WARN, even
        with deadline passed + high severity (design: never upgraded)."""
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(
                _risk_row(severity="严重", deadline="2020-01-01", refs="FIX-999")),
            task_status_map=DONE)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        w = [x for x in r["warnings"] if x["rule"] == "R3"]
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0]["task_refs"], ["FIX-999"])

    def test_r4_warn_no_reference_no_exemption(self):
        """Non-closed risk, no resolvable task ref, no exemption marker →
        content-level WARN disclosure (router RISK-003 pattern; never a
        silent no-verdict)."""
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(
                _risk_row(refs="", mitigation="依赖测试看护/接口奇偶回归/症状知识库")),
            task_status_map=DONE)
        self.assertEqual(r["verdict"], "WARN")
        w = [x for x in r["warnings"] if x["rule"] == "R4"]
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0]["risk_id"], "RISK-001")

    def test_r5_exemption_marker_skipped(self):
        """[无任务引用] / [跨实体] / [流程动作] → skip (R5, no WARN)."""
        for marker in ("[无任务引用]", "[跨实体]", "[流程动作]"):
            r = vw.check_risk_mitigation_closure(
                risk_content=_risk_content(_risk_row(refs="", note=marker)),
                task_status_map=DONE)
            self.assertEqual(r["warnings"], [], f"marker={marker}")
            self.assertEqual(r["verdict"], "no-verdict", f"marker={marker}")
            self.assertEqual(r["stats"]["exempted_skipped"], 1, f"marker={marker}")

    def test_r5_closed_risk_skipped(self):
        """已关闭 → skip (R5)."""
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(_risk_row(status="已关闭", refs="FIX-300")),
            task_status_map=OPEN)
        self.assertEqual(r["verdict"], "no-verdict")
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["stats"]["closed_skipped"], 1)

    def test_r5_ragged_row_skipped_neighbors_judged(self):
        """ragged/短列行 fail-safe 不判；相邻规范行不受影响."""
        ragged = "| RISK-900 | 2026-08-19 | 短行（列不足） |"
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(
                ragged,
                _risk_row(rid="RISK-001", refs="FIX-300")),
            task_status_map=DONE)
        self.assertEqual(r["stats"]["ragged_skipped"], 1)
        self.assertEqual(r["stats"]["pass"], 1)
        self.assertEqual(r["verdict"], "PASS")  # ragged row never pollutes verdict

    def test_r5_missing_status_skipped(self):
        """状态缺失（parts[9] 空）→ 该行不判（R5），不计入 judged."""
        row = _risk_row().replace("| Developer | 打开 |", "| Developer |  |", 1)
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(row),
            task_status_map=DONE)
        self.assertEqual(r["stats"]["ragged_skipped"], 1)
        self.assertEqual(r["stats"]["judged"], 0)
        self.assertEqual(r["verdict"], "no-verdict")

    def test_prose_fallback_when_ref_cell_placeholder(self):
        """关联任务列 empty → 次要源 缓解动作列 parts[10] 命中 FIX-xxx."""
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(
                _risk_row(severity="中", refs="—",
                          mitigation="缓解动作见 FIX-300 实施")),
            task_status_map=OPEN)
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual([w["rule"] for w in r["warnings"]], ["R1"])
        self.assertEqual(r["warnings"][0]["task_refs"], ["FIX-300"])

    def test_refs_union_deduped_single_warning(self):
        """同一 task 多来源/重复命中 → 只计一次（并集去重）."""
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(
                _risk_row(severity="中", refs="FIX-300, FIX-301",
                          mitigation="缓解见 FIX-300 与 FIX-300")),
            task_status_map={"FIX-300": "✅ 完成", "FIX-301": "⏳ 进行中"})
        self.assertEqual(len(r["warnings"]), 1)
        self.assertEqual(r["warnings"][0]["task_refs"], ["FIX-300", "FIX-301"])

    def test_prose_duplicate_refs_deduped(self):
        """prose 中同一 id 重复 → 只计一次（set 去重）."""
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(
                _risk_row(severity="中", refs="",
                          mitigation="见 FIX-300；FIX-300 依赖")),
            task_status_map=OPEN)
        self.assertEqual(len(r["warnings"]), 1)
        self.assertEqual(r["warnings"][0]["task_refs"], ["FIX-300"])


# ── F6 parser lock / off-by-one guard ──────────────────────────────────

class Check36ParserLockTests(unittest.TestCase):
    """raw split index lock: parts[9]/[10]/[11]/[12], never table-cells."""

    def test_mixes_cells_index_gets_wrong_column(self):
        """A row with an EMPTY trailing 备注 (what _governance_table_cells
        strips) proves raw-parts indexing: the mitigation task id lives at
        raw parts[10]; a cells[10]-style read would pick the deadline cell
        ('2099-01-01') and miss it — F6 off-by-one guard."""
        row = _risk_row(refs="", mitigation="缓解动作引 FIX-300",
                        deadline="2099-01-01", note="")
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(row),
            task_status_map=DONE)
        # Raw parts[10] = '缓解动作引 FIX-300' → FIX-300 found → closure
        # satisfied → PASS. A cells[10] (= deadline) read would emit R4 WARN.
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["verdict"], "PASS")

    def test_columns_map_to_canonical_template_positions(self):
        """Independent column mapping proof: each canonical cell lands at
        the raw parts index Check 2/8 use (parts 9/11) and the new check's
        ref sources (10/12)."""
        row = _risk_row(status="打开", severity="高", deadline="2099-01-01",
                        refs="FIX-300")
        parts = [p.strip() for p in row.split("|")]
        self.assertEqual(parts[9], "打开")      # 当前状态
        self.assertEqual(parts[10], "缓解动作")  # 缓解动作
        self.assertEqual(parts[11], "2099-01-01")  # 截止日期
        self.assertEqual(parts[12], "FIX-300")  # 关联任务
        self.assertGreaterEqual(len(parts), 13)

    def test_check2_8_same_raw_parts_index(self):
        """Check 2/8 (check_risk_staleness/escalation) read status/deadline
        from the same raw parts[9]/[11] — the new check must agree."""
        with tempfile.TemporaryDirectory() as td:
            risk_path = Path(td) / "risk-log.md"
            risk_path.write_text(
                _risk_content(
                    _risk_row(rid="RISK-001", status="打开", deadline="2099-01-01"),
                    _risk_row(rid="RISK-002", status="已关闭", deadline="2020-01-01")),
                encoding="utf-8")
            with mock.patch.object(vw, "RISK_PATH", risk_path):
                staleness = vw.check_risk_staleness()
                escalation = vw.check_risk_escalation()
            self.assertEqual(staleness["total_open"], 1)
            self.assertEqual(escalation["total_open"], 1)
            self.assertEqual(escalation["escalated"], [])
            # Same fixture through the closure check: RISK-001 judged,
            # RISK-002 (已关闭) skipped — parts[9] index consistency.
            r = vw.check_risk_mitigation_closure(
                risk_content=risk_path.read_text(encoding="utf-8"),
                task_status_map=DONE)
            self.assertEqual(r["stats"]["risks_scanned"], 2)
            self.assertEqual(r["stats"]["closed_skipped"], 1)
            self.assertEqual(r["stats"]["pass"], 1)


# ── task_priority integration (F11 rebuild + fail-safe) ────────────────

class Check36TaskPriorityTests(unittest.TestCase):
    """F11: status map rebuilt from PriorityReport buckets; fail-safe WARN."""

    def test_default_map_built_from_priority_report(self):
        """Live build: plan-tracker fixture → PriorityReport → {id: status}
        rebuild; the referenced task resolves from the rebuild."""
        plan = (
            "### 优先级一览\n"
            "| 优先级 | ID | 任务 | 依赖 | 目标版本 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| P0 | FIX-300 | 任务 | — | 0.76.0 | ⏳ 进行中 |\n"
        )
        with tempfile.TemporaryDirectory() as td:
            plan_path = Path(td) / "plan-tracker.md"
            plan_path.write_text(plan, encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", plan_path):
                r = vw.check_risk_mitigation_closure(
                    risk_content=_risk_content(
                        _risk_row(severity="中", refs="FIX-300")))
            self.assertEqual(r["verdict"], "WARN")
            self.assertEqual([w["rule"] for w in r["warnings"]], ["R1"])

    def test_task_priority_unavailable_failsafe_warn(self):
        """task-priority parse failure / missing plan-tracker → the risk
        fails-safe to WARN, never FAIL (even with passed deadline)."""
        with mock.patch.object(vw, "SAMPLE_PATH",
                               Path("Z:/definitely-missing/plan-tracker.md")):
            r = vw.check_risk_mitigation_closure(
                risk_content=_risk_content(
                    _risk_row(severity="严重", deadline="2020-01-01",
                              refs="FIX-300")))
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["violations"], [])
        self.assertIn("无法验证", r["warnings"][0]["reason"])

    def test_live_mode_reads_patched_paths(self):
        """Live mode (no fixtures) reads RISK_PATH + rebuilds from patched
        SAMPLE_PATH — completed ref → PASS."""
        plan = (
            "### 优先级一览\n"
            "| 优先级 | ID | 任务 | 依赖 | 目标版本 | 状态 |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| P0 | FIX-300 | 任务 | — | 0.76.0 | ✅ 完成 (2026-08-22) |\n"
        )
        with tempfile.TemporaryDirectory() as td:
            gov = Path(td) / ".governance"
            gov.mkdir()
            (gov / "plan-tracker.md").write_text(plan, encoding="utf-8")
            (gov / "risk-log.md").write_text(
                _risk_content(_risk_row(refs="FIX-300")), encoding="utf-8")
            with mock.patch.object(vw, "SAMPLE_PATH", gov / "plan-tracker.md"), \
                 mock.patch.object(vw, "RISK_PATH", gov / "risk-log.md"):
                r = vw.check_risk_mitigation_closure()
            self.assertEqual(r["verdict"], "PASS")
            self.assertEqual(r["stats"]["pass"], 1)


# ── Result contract + numbering ────────────────────────────────────────

class Check36ContractTests(unittest.TestCase):
    """Result shape + Check numbering (F9: Check 36 with Check 35 before it)."""

    def test_result_contract_shape(self):
        r = vw.check_risk_mitigation_closure(
            risk_content=_risk_content(_risk_row(refs="FIX-300")),
            task_status_map=DONE)
        self.assertEqual(set(r.keys()),
                         {"verdict", "reason", "violations", "warnings", "stats"})
        self.assertIn(r["verdict"], ("PASS", "WARN", "FAIL", "no-verdict"))

    def test_empty_content_no_verdict(self):
        r = vw.check_risk_mitigation_closure(risk_content="", task_status_map=DONE)
        self.assertEqual(r["verdict"], "no-verdict")
        self.assertEqual(r["warnings"], [])
        self.assertEqual(r["violations"], [])

    def test_check35_and_check36_blocks_coexist(self):
        """F9: Check 35 (FIX-268) landed BEFORE Check 36 (FIX-265) — both
        blocks must exist in cmd_check_governance, consecutive, 35 → 36."""
        src = (_INFRA_DIR / "verify_workflow.py").read_text(encoding="utf-8")
        check35 = "┌─ Check 35: Snapshot Freshness (FIX-268)"
        check36 = "┌─ Check 36: Risk Mitigation Closure (FIX-265)"
        self.assertIn(check35, src)
        self.assertIn(check36, src)
        # Consecutive block order: Check 35 strictly before Check 36, and
        # neither overlaps the other's section header.
        self.assertLess(src.index(check35), src.index(check36))

    def test_check36_exported_and_function_lives_in_risk_domain(self):
        domain = (_INFRA_DIR / "checks" / "risk_domain.py").read_text(
            encoding="utf-8")
        self.assertIn("def check_risk_mitigation_closure", domain)
        # Parser lock (F6): raw split only, never the cells helper. The
        # function body is the text after the docstring (which documents
        # the lock and therefore mentions the helper by name).
        body = domain.split("def check_risk_mitigation_closure")[1]
        body = body.split('"""')[2]
        self.assertNotIn("_governance_table_cells", body)
        self.assertIn('line.split("|")', body)
        self.assertIn("parts[9]", body)
        self.assertTrue(hasattr(vw, "check_risk_mitigation_closure"))


if __name__ == "__main__":
    unittest.main()
