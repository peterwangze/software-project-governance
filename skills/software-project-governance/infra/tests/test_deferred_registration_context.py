"""Per-occurrence deferral decisions in evidence and plan rows."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checks import loop_gate_processor as gate


class DeferredContextTests(unittest.TestCase):
    def assert_hits(self, row, expected):
        hits = gate.scan_deferred_hits(row)
        self.assertEqual([(hit["word"], not hit["negative_context_hit"]) for hit in hits],
                         expected)
        for hit in hits:
            self.assertEqual(row[hit["start"]:hit["end"]], hit["word"])

    def test_archived_evidence_phrases(self):
        # Source excerpts retain the grammar of the three observed rows.
        self.assert_hits("过时残留当场勘正非登记待办）。用户影响: 获得=自动生效",
                         [("登记待", False)])
        self.assert_hits("全部 committed 退出候选池；无就绪候选",
                         [("候选池", False)])
        self.assert_hits("无 --no-verify）= P2 遗留待安排（需宿主插件安装面更新）。",
                         [("留待", True)])

    def test_quotes_and_assignments_in_the_same_row(self):
        row = "规则写明「登记待以后」=违规；状态=登记待以后；另项「留待复核」视为违规"
        self.assert_hits(row, [("登记待", False), ("待以后", False), ("登记待", True),
                               ("待以后", True), ("留待", False)])
        self.assert_hits("优先级＝P2 待以后；后续处理违规事项",
                         [("待以后", True), ("后续处理", True)])

    def test_cited_records_and_numbered_items(self):
        for phrase in ("勘正口径=引候选池行为准（闭环链一键化已由其他票承载）",
                       "详见候选池记录所示", "批 2 首票（候选池 #1 P1 优先——聚焦集）",
                       "批 2 收官（候选池 #3 清账——第七票闭环）", "据候选池 #28）",
                       "来源（候选池 ＃26 P2）", "候选池 #12 已办结"):
            with self.subTest(phrase=phrase):
                self.assert_hits(phrase, [("候选池", False)])
        for phrase in ("引入候选池", "引用候选池行为规范", "放入候选池 #1",
                       "首票（候选池 #1 放入待开发项）", "来源（候选池 #2 P1 转入下版）",
                       "候选池 #3 待清账", "尚未收官（候选池 #3 清账）"):
            with self.subTest(phrase=phrase):
                self.assert_hits(phrase, [("候选池", True)])

    def test_citations_and_actual_deferrals_produce_distinct_observation_entries(self):
        text = "勘正口径=引候选池行为准；接着转入候选池 #7 | 收官（候选池 #2 清账）"
        result = gate.judge_deferred_row("evidence-log.md", "EVD-99", text)
        entries = [gate.build_ledger_entry("2026-11-24", "evidence-log.md", result["family"],
                                           result["row_key"], 4, hit["word"], hit["negative_context_hit"])
                   for hit in result["hits"]]
        self.assertEqual([entry["fired"] for entry in entries], [False, True, False])
        self.assertEqual(gate.deferred_events_from_entries(entries, "2026-11-24"),
                         [{"id": "EVD-99", "kind": "deferred_registration"}])
        self.assertEqual(gate.deferred_events_from_entries([entries[0], entries[2]], "2026-11-24"), [])

    def test_source_notes_display_and_planning_outcomes(self):
        for phrase in ("来源项；候选池 #3（FEAT-056 缺口）", "登记义务 + 上会话候选池「卫生登记类」",
                       "体验变化=0.99 候选池经完成必推荐机出呈现", "使候选池规划获得确定锚点",
                       "摘要展示候选池", "补账，防「登记待以后」", "候选池 12 项盘点去重",
                       "快照 0.96 候选池线索", "候选池为空"):
            with self.subTest(phrase=phrase):
                result = gate.scan_deferred_hits(phrase)
                self.assertTrue(result)
                self.assertTrue(all(hit["negative_context_hit"] for hit in result))
        for phrase in ("入 0.99 候选池；旧版曾展示", "存入上会话候选池「旧名单」",
                       "候选池经评审转入列表展示", "登记 0.100.0 候选池规划获得锚点",
                       "需求来源是候选池 #3 转入排期", "项目存入候选池 #3（REQ-44）",
                       "防止重新登记，但后续处理"):
            with self.subTest(phrase=phrase):
                self.assertTrue(any(not hit["negative_context_hit"] for hit in gate.scan_deferred_hits(phrase)))
        self.assert_hits("登记来源；候选池 #25（TASK-16）| 缺陷转入候选池，留待下轮",
                         [("候选池", False), ("候选池", True), ("留待", True)])

    def test_pool_members_and_visible_results_have_no_deferred_action(self):
        self.assert_hits("候选池=FEAT-093~098 六任务全部 unblocked；候选池与推荐排序一次可见",
                         [("候选池", False), ("候选池", False)])
        self.assert_hits("候选池＝REQ-12~15 四项均就绪；记录转入候选池，下轮复评",
                         [("候选池", False), ("候选池", True)])
        self.assert_hits("规划（候选池 BUG-12/13 + 版本清单）；候选池全部在账可查",
                         [("候选池", False), ("候选池", False)])
        self.assert_hits("快照候选池叙述；session-snapshot carry-over 候选池；原缺口留待下轮",
                         [("候选池", False), ("候选池", False), ("留待", True)])
        for phrase in ("候选池=BUG-12 等待移交", "候选池=FIX-12/13 均拟下轮处理",
                       "将当前问题转入候选池与清单同时可见", "规划（候选池 BUG-12/13 转入下版）",
                       "实际转入 session-snapshot carry-over 候选池"):
            with self.subTest(phrase=phrase):
                self.assert_hits(phrase, [("候选池", True)])

    def test_a_settled_numbered_note_preserves_a_second_pending_action(self):
        self.assert_hits("目标已收口（先例；候选池 #8 清账）——运行正常；登记待开发席写回",
                         [("候选池", False), ("登记待", True)])
        for phrase in ("候选池 #8 待清账）", "计划（候选池 #8 清账）", "候选池 #13 清账后转入下轮",
                       "候选池 #8 清账", "须转入候选池 #8 清账）"):
            with self.subTest(phrase=phrase):
                self.assert_hits(phrase, [("候选池", True)])

    def test_repaired_rule_gap_and_actual_task_action(self):
        self.assert_hits("制度『登记待以后』登记缺口已修复；真实事项仍后续处理",
                         [("登记待", False), ("待以后", False), ("后续处理", True)])
        self.assert_hits("ADR-007(2)「留待」制度缺口已补齐", [("留待", False)])
        for phrase in ("规则「登记待以后」缺口仍待修复", "规则「登记待以后」缺口修复计划",
                       "规则「登记待以后」作为下一步",
                       "记录「登记待以后」为本次处理决定", "规则「登记待以后」| 缺口已修复"):
            with self.subTest(phrase=phrase):
                self.assert_hits(phrase, [("登记待", True), ("待以后", True)])

    def test_a_judgement_on_another_quotation_does_not_exempt_the_hit(self):
        self.assert_hits("「原项」后续处理「其它」=违规", [("后续处理", True)])
        self.assert_hits("'原项'后续处理'其它'=违规", [("后续处理", True)])
        self.assert_hits("取消禁止后续处理", [("后续处理", True)])

    def test_pool_exit_and_pending_exit(self):
        for phrase in ("已移出候选池", "从候选池中移除", "候选池已清空", "候选池内任务均已完成"):
            with self.subTest(phrase=phrase):
                self.assert_hits(phrase, [("候选池", False)])
        for phrase in ("计划退出候选池", "尚未将其移出候选池", "不能从候选池中移除",
                       "仍在候选池", "加入候选池已完成"):
            with self.subTest(phrase=phrase):
                self.assert_hits(phrase, [("候选池", True)])
        self.assert_hits("已退出 0.95 池，改入 0.96池",
                         [("0.95 池", False), ("0.96池", True)])

    def test_scope_stops_at_another_action_clause_or_cell(self):
        for boundary in ("；", "，", "。", "|", "\n"):
            with self.subTest(boundary=boundary):
                self.assert_hits("不得留待" + boundary + "下版处理",
                                 [("留待", False), ("下版处理", True)])
                self.assert_hits("留待" + boundary + "=违规", [("留待", True)])
        self.assert_hits("禁止修改配置但下版处理；不能后续处理",
                         [("下版处理", True), ("后续处理", False)])

    def test_families_and_observation_posture(self):
        text = "非登记待办 | 已退出候选池 | = P2 遗留待安排"
        for surface, key, family in (("evidence-log.md", "EVD-99", "evidence"),
                                     ("plan-tracker.md", "FIX-99", "task_status")):
            result = gate.judge_deferred_row(surface, key, text)
            self.assertEqual(result["family"], family)
            self.assertEqual(result["fired_words"], ["留待"])
        self.assertIsNone(gate.judge_deferred_row("decision-log.md", "DEC-99", text))
        self.assertEqual(gate.DEFERRED_REGISTRATION_POSTURE, "warn")
