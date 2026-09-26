"""FIX-395 — Check 28c hot fact-source terminal judgment aligned to FIX-393.

Background (TRIAGE-FIX-395; census 2026-09-26, 28c cluster = 20 live issues):
``check_hot_fact_source_consistency`` judged task terminal states with the
standalone legacy word-form read (``_status_cell_is_delivered``: a
✅/已交付/已完成 literal anywhere in the cell). The governed writer's ONLY
terminal state writes ``committed … 〔op-<32hex>〕`` (FIX-393 criterion) —
none of those literals — so the writer-committed 0.88.0 release chain
(REL-087/088/089) was judged NOT delivered → ``released_face=False`` →

  1. the 0.88.0 roadmap row's honest 已发布 claim FAILed
     ("must not claim 已发布 before its release task is delivered") and the
     hot sections FAILed "overstate 0.88.0 as released" (2 issues);
  2. with the face down, the roadmap enumeration demand fired for EVERY
     task associated with 0.88.0 but absent from the row text — 18
     "missing active task" pseudo-FAILs (delivered FIX-373~389 tickets, the
     writer-committed REL-087/088/089 themselves, and the 0.89-target
     REL-091 swept in by FIX-339's any-cell recall via its bump-source
     narrative 「0.88.0→0.89.0」).

FIX-395: the 28c task-terminal judgment consumes the FIX-393 writer-terminal
predicate BY IDENTITY (``_status_is_writer_committed_cell`` — the governed
writer's own chain ``task_row_update._STATE_MARKER_CHAIN`` + ops receipt
anchor; no fourth mirror) ON TOP of the legacy word forms — S_new ⊇ S_old
for the 28c face. Guarded directions preserved byte-for-byte:

  - active dev/triaged cells stay open EVEN when writer-anchored (every
    writer write carries an anchor; the chain FIRST-HIT must be
    ``committed`` — a triaged-anchored cell is not terminal);
  - hand-written 「committed」 without the ops anchor (B-1 hand-edit class)
    and unknown tokens are never guessed terminal (未知不猜);
  - Check 18/18b's narrower FIX-390 three-state exemption face
    (``_hot_status_completion_state``) is untouched (组合恒等).

Version-row mapping semantics (deliverable ③, documented — NOT changed):
the V+1-target-task-swept-into-V recall is existing FIX-339 semantics
(F-01/F-05 recall-first tradeoff, pinned below); it can only FAIL the V
roadmap enumeration while V is UNRELEASED — with the released face repaired
the enumeration loop is skipped entirely.

Live-shape fidelity: the fixtures reuse the real cell shapes and the real
ops receipt anchors of the 0.88.0-era release chain (REL-087/088/089) and
REL-091 (plan-tracker 2026-09-25/26); judgment keys on the shapes, not the
prose. R1 (review-FIX-395-CODE-R0 P0-1): fixture VERSIONS are derived
(``_ACTIVE_VERSION`` via ``resolve_entry.read_active_version()`` — the
DEC-213③/FIX-352/353 shape), never pinned literally; after the next bump
the fixtures self-adapt with zero exemption-ledger rows. All tests use
in-memory fixture strings; the real ``.governance/`` is never touched.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_fix395_hot_fact_source_writer_terminal.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import resolve_entry  # noqa: E402
import verify_workflow as vw  # noqa: E402


# FIX-395 R1 (review-FIX-395-CODE-R0 P0-1): the fixtures speak the ACTIVE
# version by DERIVATION, never by literal pin (DEC-213③ / FIX-352/353 shape,
# test_bootstrap_aggregate precedent). After the next bump the fixtures
# self-adapt with zero re-anchoring and zero exemption-ledger rows.
_ACTIVE_VERSION = resolve_entry.read_active_version() or "0.0.0"


def _next_minor_version(version):
    """The next minor of ``version`` — the derived V+1 bump-source token for
    the swept-target fixture row (the live REL-091 shape)."""
    major, minor, patch = version.split(".")
    return f"{major}.{int(minor) + 1}.{patch}"


_NEXT_VERSION = _next_minor_version(_ACTIVE_VERSION)


# ── Live anchors (plan-tracker 2026-09-25/26) ───────────────────────────────

ANCHOR_REL087 = "op-d1a17f83c33e459189de17a4f1752a3e"
ANCHOR_REL088 = "op-1e4093d7f4ed48f0ade584986e40c592"
ANCHOR_REL089 = "op-6c138c33f635447c9e2cc18226e91bfc"
ANCHOR_REL091 = "op-fb75a7295c2d45289a0d549c87913b53"
ANCHOR_FIX382 = "op-6a0ba7d101e146ba8c606a310d39c9f2"

# Live status-cell shapes.
ST_WRITER_COMMITTED = "committed (2026-09-25——static-pin 套件全过) 〔" + ANCHOR_REL087 + "〕"
ST_WRITER_COMMITTED_TRAILING_GROUP = (
    "committed 已 lock 待派发 (2026-09-23——0.88 阶段 C1) 〔" + ANCHOR_REL088
    + "〕〔R0 NEEDS_CHANGE/2→R1 APPROVED_WITH_NOTES/0；commit 61618a5〕"
)
ST_LEGACY_CHECK = "✅ 完成 (2026-09-23——REVIEW-R0 APPROVED_WITH_NOTES/0)"
ST_LEGACY_DELIVERED = "✅ 已交付 (2026-09-20——数据勘正回填)"
# Guarded shapes (未知不猜 — never terminal).
ST_TRIAGED_ANCHORED = "🆕 已 triage 待排期 (2026-09-26——0.89 M-1 启动：DEC-245 执行授权) 〔" + ANCHOR_REL091 + "〕"
ST_DEV_ANCHORED = "🆕 🔄 进行中 待排期 (2026-09-26——派发开发) 〔" + ANCHOR_REL091 + "〕"
ST_HAND_COMMITTED_NO_ANCHOR = "committed 审查中 (2026-09-26——审查派发中)"
ST_UNKNOWN_TOKEN = "🧪 未知token形态 (2026-09-26)"


def _plan_content(
    *,
    plan_version=None,
    roadmap_status="已发布",
    fix087_status="✅ 已完成 (2026-05-28)",
    rel013_status="✅ 已完成 (2026-05-28)",
    req074_status="✅ 已交付",
    dependency_line=None,
    overview_tail=None,
    extra_task_rows=(),
    extra_roadmap_rows="",
):
    """Hot-section scaffold in the HotFactSourceConsistencyTests shape,
    defaulted to a RELEASED-face active version (derived ``_ACTIVE_VERSION``)."""
    plan_version = plan_version or _ACTIVE_VERSION
    dependency_line = dependency_line or (
        "0.38.0 FIX-082~087 + REL-013 全部闭环，RISK-033 已关闭\n"
        f"{_ACTIVE_VERSION} FIX-373~389 + REL-086 发布链闭环，RISK-033 已关闭"
    )
    overview_tail = overview_tail or f"RISK-033 已关闭，{_ACTIVE_VERSION} 已发布（REL-086 发布链闭环）"
    project_stage = f"维护与演进 — {_ACTIVE_VERSION} 已发布，{_NEXT_VERSION} 推进中"
    overview_stage = f"维护（{_ACTIVE_VERSION} 已发布，{_NEXT_VERSION} 推进中）"
    active_items_intro = f"{_ACTIVE_VERSION} 发布闭环完成，{_NEXT_VERSION} 批次推进中。"
    plan_version_line = f"- **工作流版本**: {plan_version}\n\n" if plan_version else ""
    rows = [
        "| **P0** | FIX-082 | Runtime capability contract | AUDIT-102 | 0.38.0 | done | ✅ 已完成 (2026-05-23) |",
        "| **P0** | FIX-083 | Structured evidence schema | AUDIT-102 | 0.38.0 | done | ✅ 已完成 (2026-05-23) |",
        "| **P0** | FIX-084 | AI execution packet | AUDIT-102 | 0.38.0 | done | ✅ 已完成 (2026-05-23) |",
        "| **P0** | FIX-085 | Agent Team degraded mode | AUDIT-102 | 0.38.0 | done | ✅ 已完成 (2026-05-25) |",
        "| **P1** | FIX-086 | Projection sync guard | AUDIT-102 | 0.38.0 | done | ✅ 已完成 (2026-05-25) |",
        f"| **P1** | FIX-087 | Hot fact-source consistency guard | AUDIT-102 | 0.38.0 | pending | {fix087_status} |",
        f"| **P0** | REL-013 | Release 0.38.0 | FIX-082~087 | 0.38.0 | pending | {rel013_status} |",
    ]
    rows.extend(extra_task_rows)
    return (
        "# 当前项目样例\n\n"
        "## 项目配置\n\n"
        f"- **当前阶段**: {project_stage}\n\n"
        f"{plan_version_line}"
        "## 项目总览\n\n"
        "| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        f"| 项目管理工作流插件 | {overview_stage} | 204 | 190 | 0 | 1 | {overview_tail} | 2026-05-26 |\n\n"
        "## 当前活跃事项\n\n"
        f"{active_items_intro}\n\n"
        "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        + "\n".join(rows)
        + "\n\n"
        "### 1.0.0 依赖链\n\n"
        "```\n"
        "0.37.0 FIX-080~081 + REL-012 全部闭环，RISK-032 已关闭\n"
        "    │\n"
        "    ▼\n"
        f"{dependency_line}\n"
        "    │\n"
        "    ▼\n"
        "1.0.0 正式发布\n"
        "```\n\n"
        "## 版本规划\n\n"
        "| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| **0.37.0** | **已发布** | **2026-05-22** | **事实依据看护** | **FIX-080(P0), FIX-081(P0), REL-012(P0)** | **tag v0.37.0** |\n"
        "| **0.38.0** | **已发布** | **2026-05-23** | **AI 执行底座** | **AUDIT-102(P0), FIX-082~085(P0), FIX-086~087(P1), REL-013(P0)** | **能力契约、结构化证据、执行包、降级模式、投影同步、热区事实源一致性** |\n"
        f"{extra_roadmap_rows}"
        "| **1.0.0** | **预留** | **—** | **首次正式发布标签** | **—** | **不得绕过 AI 执行底座收口** |\n\n"
        "## 需求跟踪矩阵\n\n"
        "| 需求ID | 需求描述 | 来源 | 优先级 | 关联任务 | 当前状态 | 验证方式 |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n"
        "| REQ-070 | 真实运行时能力 | AUDIT-102 | P0 | FIX-082, FIX-085 | ✅ 已交付 | 0.38.0 |\n"
        "| REQ-071 | 结构化证据 | AUDIT-102 | P0 | FIX-083 | ✅ 已交付 | 0.38.0 |\n"
        "| REQ-072 | AI execution packet | AUDIT-102 | P0 | FIX-084 | ✅ 已交付 | 0.38.0 |\n"
        "| REQ-073 | projection sync | AUDIT-102 | P1 | FIX-086 | ✅ 已交付 | 0.38.0 |\n"
        f"| REQ-074 | hot fact-source consistency | AUDIT-102 | P1 | FIX-087 | {req074_status} | 0.38.0 |\n"
    )


# The active-version roadmap row enumerates ONLY the FIX-373~382 range —
# exactly the live post-FIX-394 shape: REL-087/088/089 and the swept REL-091
# are absent from the row text, so the pre-fix face-down run produced
# missing-task pseudo-FAILs for all of them.
ROADMAP_088_ROW = (
    f"| **{_ACTIVE_VERSION}** | **已发布** | **2026-09-25** | **执法硬化批** | **FIX-373~382(P1)** | **tag {_ACTIVE_VERSION}** |\n"
)

RELEASED_088_TASK_ROWS = (
    # The writer-committed active-version release chain (live anchors) — the
    # cluster's root cause: legacy read judged these NOT delivered.
    f"| **P1** | REL-087 | {_ACTIVE_VERSION} M-1 版本 bump 票：0.87.0→{_ACTIVE_VERSION} 全仓锚 | — | {_ACTIVE_VERSION} | done | {ST_WRITER_COMMITTED} |",
    f"| **P1** | REL-088 | {_ACTIVE_VERSION} M-1R 四件套票 | — | {_ACTIVE_VERSION} | done | {ST_WRITER_COMMITTED_TRAILING_GROUP} |",
    f"| **P1** | REL-089 | {_ACTIVE_VERSION} M-3 前置补强票 | — | {_ACTIVE_VERSION} | done | committed (2026-09-25——rollback §8 落位) 〔{ANCHOR_REL089}〕 |",
    # Delivered task tickets in both eras.
    f"| **P1** | FIX-373 | B-3 契约卫生首票 | DEC-229 | {_ACTIVE_VERSION} | done | {ST_LEGACY_CHECK} |",
    f"| **P1** | FIX-382 | write-guard WARN 披露面 | DEC-229 | {_ACTIVE_VERSION} | done | committed——REVIEW-FIX-382-R0 APPROVED_WITH_NOTES/0 〔{ANCHOR_FIX382}〕 |",
    # The V+1-target task swept into the active-version set by any-cell recall
    # (bump-source narrative 「V→V+1」) — triaged-anchored = ACTIVE.
    f"| **P1** | REL-091 | {_NEXT_VERSION} M-1 版本 bump 票：{_ACTIVE_VERSION}→{_NEXT_VERSION} 全仓锚 | REL-086 | {_NEXT_VERSION} | pending | {ST_TRIAGED_ANCHORED} |",
)


class Fix395WriterCommittedReleasedFaceTests(unittest.TestCase):
    """The live pseudo-FAIL cluster: a writer-committed release chain must
    lift the released face and silence the roadmap enumeration demand."""

    def _write_plan(self, root, content):
        path = Path(root) / "plan-tracker.md"
        path.write_text(content, encoding="utf-8")
        return path

    def test_writer_committed_release_chain_lifts_face_and_silences_cluster(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                _plan_content(
                    extra_task_rows=RELEASED_088_TASK_ROWS,
                    extra_roadmap_rows=ROADMAP_088_ROW,
                ),
            )
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertEqual(
                issues,
                [],
                "released face must lift on the writer-committed release chain; "
                f"residual issues={issues}",
            )

    def test_hot_task_ids_for_version_release_delivered_consumes_writer_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                _plan_content(
                    extra_task_rows=RELEASED_088_TASK_ROWS,
                    extra_roadmap_rows=ROADMAP_088_ROW,
                ),
            )
            content = path.read_text(encoding="utf-8")
            ids, release_delivered, release_declared = vw._hot_task_ids_for_version(
                content, _ACTIVE_VERSION
            )
            self.assertTrue(
                release_delivered,
                f"release_delivered must recognize the writer-committed REL rows; ids={ids}",
            )
            self.assertTrue(release_declared)
            # Recognition recall pinned (FIX-339 any-cell): the writer-committed
            # REL rows AND the bump-source REL-091 all join the version set.
            for task_id in ("REL-087", "REL-088", "REL-089", "FIX-373", "FIX-382", "REL-091"):
                self.assertIn(task_id, ids)

    def test_hot_task_is_delivered_recognizes_writer_committed_cells(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                _plan_content(
                    extra_task_rows=(
                        f"| **P1** | REL-087 | bump 票 | — | {_ACTIVE_VERSION} | done | {ST_WRITER_COMMITTED} |",
                        f"| **P1** | REL-088 | 四件套票 | — | {_ACTIVE_VERSION} | done | {ST_WRITER_COMMITTED_TRAILING_GROUP} |",
                    ),
                    extra_roadmap_rows=ROADMAP_088_ROW,
                ),
            )
            content = path.read_text(encoding="utf-8")
            self.assertTrue(
                vw._hot_task_is_delivered(content, "REL-087", version=None),
                "plain writer-committed cell must be delivered",
            )
            self.assertTrue(
                vw._hot_task_is_delivered(content, "REL-088", version=None),
                "writer-committed cell with a FEAT-061 trailing narrative group "
                "after the anchor must still be delivered (search-anywhere anchor)",
            )
            self.assertFalse(
                vw._hot_task_is_open(content, "REL-087", version=None),
                "writer-committed terminal must not count open",
            )


class Fix395GuardedDirectionsTests(unittest.TestCase):
    """未知不猜 + 活体守护：non-terminal cells never flip, the true-positive
    protections stay byte-for-byte (组合②③互不回归)."""

    def _write_plan(self, root, content):
        path = Path(root) / "plan-tracker.md"
        path.write_text(content, encoding="utf-8")
        return path

    def test_active_dev_and_triaged_cells_stay_open_and_demanded(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                _plan_content(
                    plan_version="0.38.0",
                    roadmap_status="进行中",
                    fix087_status="📋 待启动",
                    rel013_status="📋 待启动",
                    req074_status="📋 待实施",
                    dependency_line="0.38.0 FIX-082~086 已闭环，RISK-033 关闭前不得打 1.0.0\nFIX-087 + REL-013 待闭环",
                    overview_tail="RISK-033 继续由 FIX-087 承载",
                    extra_task_rows=(
                        "| **P2** | FIX-099 | 未来票甲 | — | 0.38.0 | pending | " + ST_TRIAGED_ANCHORED + " |",
                        "| **P2** | FIX-098 | 未来票乙 | — | 0.38.0 | pending | " + ST_DEV_ANCHORED + " |",
                    ),
                ),
            )
            content = path.read_text(encoding="utf-8")
            # Unit face: writer-anchored NON-terminal cells stay open — every
            # writer write carries an anchor, the chain first-hit decides.
            self.assertFalse(vw._hot_task_is_delivered(content, "FIX-099", version=None))
            self.assertTrue(vw._hot_task_is_open(content, "FIX-099", version=None))
            self.assertFalse(vw._hot_task_is_delivered(content, "FIX-098", version=None))
            self.assertTrue(vw._hot_task_is_open(content, "FIX-098", version=None))
            # Check face: active tasks absent from the unreleased roadmap row
            # are still demanded (the true-positive direction is preserved).
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertTrue(
                any("0.38.0 roadmap row missing active task FIX-099" in issue for issue in issues),
                f"triaged-anchored active task must stay demanded: {issues}",
            )
            self.assertTrue(
                any("0.38.0 roadmap row missing active task FIX-098" in issue for issue in issues),
                f"dev-anchored active task must stay demanded: {issues}",
            )

    def test_anchorless_hand_committed_release_row_never_lifts_face(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                _plan_content(
                    extra_task_rows=(
                        f"| **P1** | REL-087 | bump 票 | — | {_ACTIVE_VERSION} | done | {ST_HAND_COMMITTED_NO_ANCHOR} |",
                    ),
                    extra_roadmap_rows=ROADMAP_088_ROW,
                ),
            )
            content = path.read_text(encoding="utf-8")
            self.assertFalse(
                vw._hot_task_is_delivered(content, "REL-087", version=None),
                "hand-written 「committed」 without the ops anchor (B-1 class) "
                "must never be guessed terminal",
            )
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertTrue(
                any(f"{_ACTIVE_VERSION} roadmap row must not claim 已发布" in issue for issue in issues),
                f"released-claim protection must stay with an anchor-less row: {issues}",
            )

    def test_unknown_token_cell_never_terminal(self):
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                _plan_content(
                    extra_task_rows=(
                        f"| **P1** | FIX-382 | 披露面 | — | {_ACTIVE_VERSION} | done | {ST_UNKNOWN_TOKEN} |",
                    ),
                    extra_roadmap_rows=ROADMAP_088_ROW,
                ),
            )
            content = path.read_text(encoding="utf-8")
            self.assertFalse(vw._hot_task_is_delivered(content, "FIX-382", version=None))
            self.assertTrue(vw._hot_task_is_open(content, "FIX-382", version=None))

    def test_legacy_delivered_semantics_superset_invariant(self):
        """S_new ⊇ S_old: every legacy-delivered cell form stays delivered."""
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                _plan_content(
                    extra_task_rows=(
                        f"| **P1** | REL-087 | 甲 | — | {_ACTIVE_VERSION} | done | {ST_LEGACY_CHECK} |",
                        f"| **P1** | REL-088 | 乙 | — | {_ACTIVE_VERSION} | done | {ST_LEGACY_DELIVERED} |",
                        f"| **P1** | REL-089 | 丙 | — | {_ACTIVE_VERSION} | done | 🔄 已 lock 待派发 (2026-09-23) → ✅ 完成 (2026-09-24——R1 APPROVED/0) |",
                    ),
                    extra_roadmap_rows=ROADMAP_088_ROW,
                ),
            )
            content = path.read_text(encoding="utf-8")
            for task_id in ("REL-087", "REL-088", "REL-089"):
                self.assertTrue(
                    vw._hot_task_is_delivered(content, task_id, version=None),
                    f"legacy form must stay delivered ({task_id})",
                )


class Fix395VersionRowMappingSemanticsTests(unittest.TestCase):
    """Deliverable ③ — the mapping semantics pinned as DECIDED existing
    behavior (FIX-339 any-cell recall), documented in
    ``_hot_task_ids_for_version``."""

    def _write_plan(self, root, content):
        path = Path(root) / "plan-tracker.md"
        path.write_text(content, encoding="utf-8")
        return path

    def test_bump_source_row_joins_previous_version_set_by_recall(self):
        """A V+1-target task whose narrative mentions V (the bump-source
        「V→V+1」 form) joins V's task set — existing recall-first semantics.
        With the released face lifted it must NOT FAIL the V roadmap
        enumeration."""
        with tempfile.TemporaryDirectory() as td:
            path = self._write_plan(
                td,
                _plan_content(
                    extra_task_rows=RELEASED_088_TASK_ROWS,
                    extra_roadmap_rows=ROADMAP_088_ROW,
                ),
            )
            content = path.read_text(encoding="utf-8")
            ids, _release_delivered, _release_declared = vw._hot_task_ids_for_version(
                content, _ACTIVE_VERSION
            )
            self.assertIn(
                "REL-091",
                ids,
                "bump-source narrative must keep any-cell recall membership",
            )
            issues = vw.check_hot_fact_source_consistency(path)
            self.assertFalse(
                any("missing active task REL-091" in issue for issue in issues),
                "a swept V+1-target task must not FAIL the released V roadmap "
                f"row (enumeration demand only bites pre-release): {issues}",
            )


if __name__ == "__main__":
    unittest.main()
