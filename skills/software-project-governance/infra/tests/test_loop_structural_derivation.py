"""Unit tests for loop_migration.py's structure-anchored derivation — FEAT-071.

DEC-254 (arch 混合方案 A 后手) landed the structure-anchored shadow pipeline:
``derive_structural_units_shadow`` derives task→unit candidates from THREE
machine-recorded evidence sources (change-triage ``files``, agent-locks
``files``/``target_files``, plan-tracker task-row path tokens) mapped onto a
FILESYSTEM-derived structural universe, applies the ADR-019 §2.6 uniqueness
check, and compares the result against the human approval manifest — with
ZERO side effects and NO authority flip. These tests guard:

  - **Structural evidence collection** — each source feeds candidates; the
    union is attributed per task with its source set.
  - **§2.6 uniqueness discipline** — exactly one candidate → auto-derivable
    anchor candidate; multiple → escalation (never auto-anchored); zero
    structural evidence → fail-closed (never prose-guessed).
  - **Prose degradation** — prose descriptions are DISPLAY-LAYER ONLY: a
    host full of "chrys adapter" prose but with no machine evidence
    produces ZERO anchoring candidates (the legacy prose face is reported
    as a count only).
  - **Shadow zero-side-effect** — a whole-.governance byte snapshot is
    identical before/after; no runtime is created; the manifest digest
    surface (SHA-256) is unchanged; repeated runs are byte-identical
    (deterministic / idempotent).
  - **Unified storage via the PUBLIC API** — the shadow consumes the
    manifest through ``load_approval_manifest`` (FEAT-070-R0 P3-5), and a
    corrupt manifest fails closed (not_comparable rows, never partial
    consumption).
  - **Comparison semantics** — agreement attribution per row, including the
    DIVERGENCE rows that must be flagged loudly and never auto-resolved,
    and NFC+casefold name normalization (display variance is not anchoring
    signal: ``adapter.Chrys`` joins structural ``adapters/chrys``).
  - **FEAT-070-R0 P2-2** — the dry-run manifest face reports
    ``status="indeterminate"`` and ``ambiguity_count=None`` when plan
    derivation fails (no misleading zero).
  - **FEAT-070-R0 P2-1** — CLI record-flag mutual exclusion (record×record
    and record×migration-mode combinations exit 2; record-only companion
    flags without a record flag exit 2); the pre-existing rollback>apply
    precedence is pinned UNCHANGED.

ALL tests use ``tempfile.TemporaryDirectory`` — the real ``.governance/`` is
NEVER touched. Assertions are content-based; no wall-clock magnitude is ever
asserted (timing is measured and reported by the verification document, not
judged here).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_structural_derivation.py -v
"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, _INFRA_DIR.as_posix())

import loop_migration as lm  # noqa: E402

# ─── Fixture helpers (self-contained mini host with real structure) ──────────

CLASSIC_TRACKER = (
    "# Plan Tracker — demo-host\n"
    "## 项目配置\n"
    "- workflow_model: classic-phase-gate\n"
    "## Gate 状态跟踪\n"
    "| Gate | 阶段转换 | 状态 |\n"
    "| --- | --- | --- |\n"
    "| G11 | next | passed |\n"
)

# Tracker WITH an active-task table whose rows carry structural path tokens:
#   FEAT-903 row: a slash path into adapters/opencode + a UNIQUE bare filename
#   FEAT-904 row: an AMBIGUOUS bare filename (dup.txt exists twice)
# The prose line names Chrys/opencode/alpha/beta so the legacy planner derives
# those units — the ONLY ids the record chain accepts (fixture parity with the
# real repo, where the manifest decisions were recorded against prose-derived
# ids).
TASK_ROW_TRACKER = (
    "# Plan Tracker — demo-host\n"
    "## 项目配置\n"
    "- workflow_model: classic-phase-gate\n"
    "the Chrys adapter and the opencode adapter and the alpha skill\n"
    "## 当前活跃事项\n"
    "| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |\n"
    "|--------|----|------|------|---------|---------|------|\n"
    "| **P2** | FEAT-903 | wire the opencode surface, see "
    "adapters/opencode/launch.py and delta_helper.py | none | 1.0 | "
    "verify | new |\n"
    "| **P3** | FEAT-904 | touch dup.txt only | none | 1.0 | "
    "verify | new |\n"
    "## Gate 状态跟踪\n"
    "| Gate | 阶段转换 | 状态 |\n"
    "| --- | --- | --- |\n"
    "| G11 | next | passed |\n"
)

# Tracker whose prose derives EXACTLY the units the decision fixtures need
# (Chrys in display case → the name-normalization arm is exercisable).
DECISION_TRACKER = (
    "# Plan Tracker — demo-host\n"
    "## 项目配置\n"
    "- workflow_model: classic-phase-gate\n"
    "the Chrys adapter and the opencode adapter and the loading adapter "
    "and the alpha skill and the beta skill\n"
    "## Gate 状态跟踪\n"
    "| Gate | 阶段转换 | 状态 |\n"
    "| --- | --- | --- |\n"
    "| G11 | next | passed |\n"
)

# Prose-rich tracker with NO structural evidence anywhere: the legacy prose
# derivation would emit three units, but the shadow pipeline must emit ZERO.
PROSE_ONLY_TRACKER = (
    "# Plan Tracker — demo-host\n"
    "## 项目配置\n"
    "- workflow_model: classic-phase-gate\n"
    "the chrys adapter and the alpha skill and the review skill\n"
    "## Gate 状态跟踪\n"
    "| Gate | 阶段转换 | 状态 |\n"
    "| --- | --- | --- |\n"
    "| G11 | next | passed |\n"
)

EVIDENCE_LOG = (
    "| 编号 | 事项 | 说明 |\n"
    "| --- | --- | --- |\n"
    "| EVD-001 | init | seeded evidence log |\n"
)


def _write_basic_host(root, tracker=CLASSIC_TRACKER):
    """Seed a minimal classic .governance/ (plan + evidence)."""
    gov = root / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "plan-tracker.md").write_text(tracker, encoding="utf-8")
    (gov / "evidence-log.md").write_text(EVIDENCE_LOG, encoding="utf-8")
    return gov


def _add_structure(root):
    """Filesystem-derived structural universe:
    adapters/{chrys,opencode} + skills/{alpha,beta} (+ gamma WITHOUT
    SKILL.md — must be excluded) + one plugin manifest surface."""
    (root / "adapters" / "chrys").mkdir(parents=True, exist_ok=True)
    (root / "adapters" / "chrys" / "chrys_main.py").write_text(
        "x = 1\n", encoding="utf-8")
    (root / "adapters" / "chrys" / "adapter-manifest.json").write_text(
        "{}\n", encoding="utf-8")
    (root / "adapters" / "chrys" / "dup.txt").write_text(
        "c\n", encoding="utf-8")
    (root / "adapters" / "opencode").mkdir(parents=True, exist_ok=True)
    (root / "adapters" / "opencode" / "launch.py").write_text(
        "y = 2\n", encoding="utf-8")
    (root / "skills" / "alpha").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\n---\n", encoding="utf-8")
    (root / "skills" / "alpha" / "dup.txt").write_text(
        "a\n", encoding="utf-8")
    (root / "skills" / "beta").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "beta" / "SKILL.md").write_text(
        "---\nname: beta\n---\n", encoding="utf-8")
    (root / "skills" / "gamma").mkdir(parents=True, exist_ok=True)
    (root / "skills" / "gamma" / "README.md").write_text(
        "no SKILL.md here\n", encoding="utf-8")
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / "plugin.json").write_text(
        "{}\n", encoding="utf-8")
    # bare filename resolving to exactly one live path (root file)
    (root / "delta_helper.py").write_text("d = 3\n", encoding="utf-8")


def _write_triage(root, task_id, files):
    ct = root / ".governance" / "change-triage"
    ct.mkdir(parents=True, exist_ok=True)
    (ct / (task_id + ".json")).write_text(
        json.dumps({
            "schema_version": 1, "task_id": task_id,
            "title": "fixture task", "files": files,
        }, ensure_ascii=False),
        encoding="utf-8")


def _write_agent_locks(root, task_id, files=None, target_files=None):
    spec = {"agent_role": "Developer", "spawned_at": "2026-01-01T00:00:00"}
    if files is not None:
        spec["files"] = files
    if target_files is not None:
        spec["target_files"] = target_files
    gov = root / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "agent-locks.json").write_text(
        json.dumps({"active_tasks": {task_id: spec}, "file_locks": {}},
                   ensure_ascii=False),
        encoding="utf-8")


def _manifest_path(root):
    return root / ".governance" / lm.APPROVAL_MANIFEST_FILENAME


def _derived_id(root, suffix):
    """The planner-derived unit id whose tail matches ``suffix``.

    The project prefix is derived from the temp directory's basename, so
    tests address units by their stable tail (e.g. "adapter.Chrys").
    """
    ids = lm.build_migration_plan(str(root)).unit_ids
    matches = [i for i in ids if i == suffix or i.endswith("." + suffix)]
    if len(matches) != 1:
        raise AssertionError(
            "expected exactly one derived id with tail {0!r}, got {1}".format(
                suffix, sorted(ids)))
    return matches[0]


def _record(root, unit_id, task_id="adapters/chrys"):
    return lm.record_unit_approval(
        target_root=str(root), flow_unit_id=unit_id, task_id=task_id,
        confirmation_evidence="structural fact: the unit directory exists",
        reviewer="test-reviewer", repo_version="1.0.0")


def _block(root, unit_id, reason="prose fragment — no structural unit"):
    return lm.record_unit_block(
        target_root=str(root), flow_unit_id=unit_id, reason=reason,
        recorded_by="test-reviewer", repo_version="1.0.0")


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_tree(root):
    """Map of relative-path → (kind, size-or-sha) for EVERYTHING under root."""
    snapshot = {}
    for p in sorted(Path(root).rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_dir():
            snapshot[rel] = ("dir", None)
        else:
            snapshot[rel] = ("file", _sha256(p))
    return snapshot


def _shadow(root, **kwargs):
    return lm.derive_structural_units_shadow(target_root=str(root), **kwargs)


def _row_by_unit(result, unit_id_suffix):
    for row in result["comparison"]["rows"]:
        if row["manifest_unit_id"].endswith(unit_id_suffix):
            return row
    raise AssertionError("no comparison row for " + unit_id_suffix)


# ═══════════════════════════════════════════════════════════════════════════
# Evidence collection — the three machine-recorded sources
# ═══════════════════════════════════════════════════════════════════════════


class TestEvidenceCollection(unittest.TestCase):

    def test_change_triage_files_field_yields_unique_candidate(self):
        """S1: a triage record whose files all live under one adapter yields
        EXACTLY that unit as a unique (auto-derivable) candidate."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            _add_structure(root)
            _write_triage(root, "FEAT-900", [
                "adapters/chrys/chrys_main.py",
                "adapters/chrys/adapter-manifest.json",  # facet → parent unit
            ])

            result = _shadow(root)

            self.assertTrue(result["shadow_derived"])
            self.assertTrue(
                result["evidence_sources"]["change_triage_files"]["available"])
            rows = {r["task_id"]: r for r in result["task_candidates"]}
            self.assertEqual(rows["FEAT-900"]["verdict"], "unique")
            self.assertEqual(rows["FEAT-900"]["candidate_units"],
                             ["adapter.chrys"])
            self.assertEqual(rows["FEAT-900"]["evidence_sources"],
                             ["change_triage_files"])
            self.assertEqual(len(result["anchor_candidates"]), 1)
            self.assertEqual(result["anchor_candidates"][0]["task_id"],
                             "FEAT-900")

    def test_agent_lock_files_and_target_files_are_unioned(self):
        """S2: agent-locks ``files`` AND ``target_files`` both feed evidence."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            _add_structure(root)
            _write_agent_locks(root, "FEAT-902",
                               files=["skills/beta/SKILL.md"],
                               target_files=["adapters/opencode/launch.py"])

            result = _shadow(root)

            rows = {r["task_id"]: r for r in result["task_candidates"]}
            self.assertEqual(rows["FEAT-902"]["verdict"], "multi")
            self.assertEqual(rows["FEAT-902"]["candidate_units"],
                             ["adapter.opencode", "skill.beta"])
            self.assertIn("agent_lock_files",
                          rows["FEAT-902"]["evidence_sources"])

    def test_task_row_slash_path_and_unique_bare_filename_resolve(self):
        """S3: a task-row slash path anchors its unit; a bare filename with
        EXACTLY ONE live hit resolves to that path."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root, tracker=TASK_ROW_TRACKER)
            _add_structure(root)

            result = _shadow(root)

            self.assertTrue(
                result["evidence_sources"]["task_row_paths"]["available"])
            self.assertEqual(
                result["evidence_sources"]["task_row_paths"]["task_rows_scanned"], 2)
            rows = {r["task_id"]: r for r in result["task_candidates"]}
            self.assertEqual(rows["FEAT-903"]["verdict"], "unique")
            self.assertEqual(rows["FEAT-903"]["candidate_units"],
                             ["adapter.opencode"])
            self.assertIn("delta_helper.py", rows["FEAT-903"]["evidence_files"])
            self.assertEqual(rows["FEAT-904"]["verdict"], "none")

    def test_ambiguous_bare_filename_recorded_never_anchored(self):
        """A bare filename hitting MULTIPLE live paths is recorded as
        ambiguous and contributes NO evidence (§2.6: never guess)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root, tracker=TASK_ROW_TRACKER)
            _add_structure(root)

            result = _shadow(root)

            rows = {r["task_id"]: r for r in result["task_candidates"]}
            self.assertEqual(rows["FEAT-904"]["verdict"], "none")
            self.assertEqual(rows["FEAT-904"]["candidate_units"], [])
            ambiguous = dict(rows["FEAT-904"]["ambiguous_basenames"])
            self.assertIn("dup.txt", ambiguous)
            self.assertEqual(len(ambiguous["dup.txt"]), 2)
            for hit in ambiguous["dup.txt"]:
                self.assertNotIn(hit, rows["FEAT-904"]["evidence_files"])


# ═══════════════════════════════════════════════════════════════════════════
# §2.6 uniqueness discipline + prose degradation
# ═══════════════════════════════════════════════════════════════════════════


class TestUniquenessAndProseDegradation(unittest.TestCase):

    def test_multi_candidate_task_never_auto_anchored(self):
        """A task whose evidence maps to two units is 'multi' — it must NOT
        appear in anchor_candidates (escalation is human, §2.6)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            _add_structure(root)
            _write_triage(root, "FEAT-901", [
                "adapters/chrys/chrys_main.py", "skills/alpha/SKILL.md"])

            result = _shadow(root)

            rows = {r["task_id"]: r for r in result["task_candidates"]}
            self.assertEqual(rows["FEAT-901"]["verdict"], "multi")
            anchor_tasks = [r["task_id"] for r in result["anchor_candidates"]]
            self.assertNotIn("FEAT-901", anchor_tasks)

    def test_cross_cutting_only_task_is_fail_closed_none(self):
        """Evidence that never touches a unit-bearing surface (docs/,
        .governance/, root files) yields verdict 'none' — no unit is
        invented (fail-closed, zero candidates)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            _add_structure(root)
            (root / "docs").mkdir(exist_ok=True)
            (root / "docs" / "notes.md").write_text("n\n", encoding="utf-8")
            _write_triage(root, "FEAT-905", [
                "docs/notes.md", ".governance/evidence-log.md"])

            result = _shadow(root)

            rows = {r["task_id"]: r for r in result["task_candidates"]}
            self.assertEqual(rows["FEAT-905"]["verdict"], "none")
            self.assertEqual(rows["FEAT-905"]["candidate_units"], [])
            self.assertEqual(rows["FEAT-905"]["evidence_files"],
                             [".governance/evidence-log.md", "docs/notes.md"])

    def test_prose_never_produces_candidates_display_layer_only(self):
        """DEC-254 A core discipline: a prose-rich tracker (the legacy
        derivation would emit 3 units) with ZERO machine evidence produces
        ZERO structural candidates. The prose face is reported for display
        only — it is not an anchoring input."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root, tracker=PROSE_ONLY_TRACKER)
            _add_structure(root)

            result = _shadow(root)

            # The prose face WOULD have anchored three units (display only):
            self.assertEqual(
                result["prose_face_display_only"]["derived_unit_count"], 3)
            self.assertTrue(
                result["prose_face_display_only"]["note"].startswith(
                    "legacy prose-token derivation"))
            # The structural pipeline anchors NOTHING from that prose:
            self.assertEqual(result["task_candidates"], [])
            self.assertEqual(result["anchor_candidates"], [])
            for source in result["evidence_sources"].values():
                self.assertFalse(source["available"])

    def test_uniqueness_exactly_one_hit_anchors(self):
        """The §2.6 uniqueness boundary itself: one candidate → unique,
        two → multi (the escalation boundary is pinned from both sides)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            _add_structure(root)
            _write_triage(root, "FEAT-910", ["skills/beta/SKILL.md"])
            _write_triage(root, "FEAT-911",
                          ["skills/beta/SKILL.md", "skills/alpha/dup.txt"])

            result = _shadow(root)

            rows = {r["task_id"]: r for r in result["task_candidates"]}
            self.assertEqual(rows["FEAT-910"]["verdict"], "unique")
            self.assertEqual(rows["FEAT-911"]["verdict"], "multi")


# ═══════════════════════════════════════════════════════════════════════════
# Structural universe
# ═══════════════════════════════════════════════════════════════════════════


class TestStructuralUniverse(unittest.TestCase):

    def test_universe_counts_and_skill_requires_skill_md(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            _add_structure(root)

            result = _shadow(root)

            universe = result["structural_universe"]
            self.assertEqual(universe["adapter_count"], 2)
            self.assertEqual(universe["adapters"], ["chrys", "opencode"])
            self.assertEqual(universe["skill_count"], 2)
            self.assertEqual(universe["skills"], ["alpha", "beta"],
                             "gamma has no SKILL.md — excluded")
            # Manifest-surface FILES are inventoried…
            self.assertIn(".claude-plugin/plugin.json",
                          universe["manifest_surfaces"])
            # …but NO manifest unit is ever generated from them (§2.6).
            self.assertIn("no structural unit rule",
                          universe["manifest_unit_rule"])
            for row in result["task_candidates"]:
                for unit in row["candidate_units"]:
                    self.assertFalse(unit.startswith("manifest."))

    def test_structural_units_without_human_decision_normalizes_names(self):
        """The switch-input membership uses the SAME NFC+casefold join as the
        comparison: the human decision on adapter.Chrys covers the
        structural adapter.chrys (project prefix + display case are not
        identity)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root, tracker=DECISION_TRACKER)
            _add_structure(root)
            self.assertTrue(
                _record(root, _derived_id(root, "adapter.Chrys"),
                        task_id="adapters/chrys")["recorded"])

            result = _shadow(root)

            without = result["switch_judgment_inputs"][
                "structural_units_without_human_decision"]
            self.assertNotIn("adapter.chrys", without)
            self.assertIn("adapter.opencode", without)
            self.assertIn("skill.alpha", without)
            self.assertIn("skill.beta", without)
            self.assertNotIn("skill.gamma", without,
                             "gamma is not a structural unit at all")


# ═══════════════════════════════════════════════════════════════════════════
# Comparison vs the human manifest — agreement attribution
# ═══════════════════════════════════════════════════════════════════════════


class TestShadowComparison(unittest.TestCase):

    def _host_with_decisions(self, root):
        _write_basic_host(root, tracker=DECISION_TRACKER)
        _add_structure(root)
        _write_triage(root, "FEAT-900", ["adapters/chrys/chrys_main.py"])
        _write_triage(root, "FEAT-902", ["skills/beta/SKILL.md"])
        # Human decisions (via the sanctioned record chain — the ids are the
        # planner-derived ones): confirm Chrys (display case) + opencode;
        # block a prose artifact (no structural unit) AND a structural unit
        # the pipeline CAN uniquely anchor (skill.beta → DIVERGENCE arm).
        self.assertTrue(
            _record(root, _derived_id(root, "adapter.Chrys"),
                    task_id="adapters/chrys")["recorded"])
        self.assertTrue(
            _record(root, _derived_id(root, "adapter.opencode"),
                    task_id="adapters/opencode")["recorded"])
        self.assertTrue(_block(root, _derived_id(root, "adapter.loading"))["recorded"])
        self.assertTrue(_block(root, _derived_id(root, "skill.beta"),
                               reason="blocked by human")["recorded"])

    def test_row_count_and_agreement_classes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._host_with_decisions(root)

            result = _shadow(root)

            comparison = result["comparison"]
            self.assertEqual(comparison["row_count"], 4)
            self.assertEqual(
                comparison["agreement_counts"],
                {"consistent_reproduction": 1,      # adapter.Chrys + FEAT-900
                 "consistent_no_evidence": 1,       # adapter.opencode
                 "consistent_absence": 1,           # adapter.loading
                 "DIVERGENCE": 1})                  # skill.beta
            self.assertEqual(
                result["switch_judgment_inputs"]["divergence_count"], 1)
            self.assertEqual(
                result["switch_judgment_inputs"][
                    "confirmed_units_reproduced_by_structure"], 1)

    def test_confirmed_row_reproduced_with_name_normalization(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._host_with_decisions(root)

            result = _shadow(root)

            row = _row_by_unit(result, "adapter.Chrys")
            self.assertEqual(row["structural_unit"]["name"], "chrys")
            self.assertTrue(row["name_normalization_applied"])
            self.assertEqual(row["pipeline_verdict"], "reproducible")
            self.assertEqual(row["unique_anchor_tasks"], ["FEAT-900"])
            self.assertEqual(row["agreement"], "consistent_reproduction")

    def test_confirmed_without_evidence_keeps_human_authority(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._host_with_decisions(root)

            result = _shadow(root)

            row = _row_by_unit(result, "adapter.opencode")
            self.assertEqual(row["pipeline_verdict"],
                             "structural_match_no_evidence")
            self.assertEqual(row["agreement"], "consistent_no_evidence")
            self.assertIn("human entry stands", row["agreement_note"])

    def test_prose_artifact_absent_from_structure_agrees(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._host_with_decisions(root)

            result = _shadow(root)

            row = _row_by_unit(result, "adapter.loading")
            self.assertIsNone(row["structural_unit"])
            self.assertEqual(row["pipeline_verdict"], "no_structural_unit")
            self.assertEqual(row["agreement"], "consistent_absence")
            self.assertIn("never enters anchoring", row["agreement_note"])

    def test_divergence_row_flagged_never_auto_resolved(self):
        """The pipeline uniquely anchors a unit the human BLOCKED — the row
        must be flagged DIVERGENCE (loud), and the shadow must NOT flip
        anything (the manifest still says blocked; zero writes are pinned
        elsewhere)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._host_with_decisions(root)

            result = _shadow(root)

            row = _row_by_unit(result, "skill.beta")
            self.assertEqual(row["human_decision"], "blocked")
            self.assertEqual(row["pipeline_verdict"], "reproducible")
            self.assertEqual(row["unique_anchor_tasks"], ["FEAT-902"])
            self.assertEqual(row["agreement"], "DIVERGENCE")
            self.assertIn("never auto-flip", row["agreement_note"])
            # The authority did NOT move: the manifest still blocks it.
            state, data, _ = lm.load_approval_manifest(root)
            self.assertEqual(state, "valid")
            blocked_ids = [b["flow_unit_id"] for b in data["blocked"]]
            self.assertTrue(
                any(i.endswith("skill.beta") for i in blocked_ids))

    def test_corrupt_manifest_rows_not_comparable_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._host_with_decisions(root)
            manifest = json.loads(_manifest_path(root).read_text(
                encoding="utf-8"))
            manifest["entries"][0]["task_id"] = "tampered/task"
            _manifest_path(root).write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")

            result = _shadow(root)

            self.assertTrue(result["shadow_derived"])
            self.assertEqual(result["manifest_face"]["state"], "corrupt")
            self.assertTrue(result["manifest_face"]["issues"])
            # Fail-closed comparison: a corrupt manifest is NEVER partially
            # consumed, so there are NO rows to compare — not a degraded
            # partial table.
            self.assertEqual(result["comparison"]["row_count"], 0)
            self.assertEqual(result["comparison"]["rows"], [])
            self.assertEqual(result["comparison"]["agreement_counts"], {})
            self.assertEqual(
                result["switch_judgment_inputs"]["divergence_count"], 0)


# ═══════════════════════════════════════════════════════════════════════════
# Shadow zero-side-effect + determinism (the hard constraint)
# ═══════════════════════════════════════════════════════════════════════════


class TestZeroSideEffectAndDeterminism(unittest.TestCase):

    def test_zero_side_effect_full_tree_snapshot(self):
        """A whole-host byte snapshot is IDENTICAL before/after the shadow
        run: no manifest write, no runtime, no evidence row, no archive, no
        temp file — nothing."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root, tracker=TASK_ROW_TRACKER)
            _add_structure(root)
            _write_triage(root, "FEAT-900", ["adapters/chrys/chrys_main.py"])
            self.assertTrue(
                _record(root, _derived_id(root, "adapter.Chrys"),
                        task_id="adapters/chrys")["recorded"])
            before = _snapshot_tree(root)
            manifest_sha_before = _sha256(_manifest_path(root))

            _shadow(root)
            _shadow(root)  # twice — the second run must be as inert

            after = _snapshot_tree(root)
            self.assertEqual(after, before,
                             "the shadow run wrote/removed/changed files")
            self.assertEqual(_sha256(_manifest_path(root)),
                             manifest_sha_before,
                             "manifest bytes must be untouched (SHA-256)")
            self.assertFalse(
                (root / ".governance" / "flow-unit-runtime.json").is_file())
            self.assertFalse((root / ".governance" / "archive").is_dir())

    def test_shadow_output_deterministic_idempotent(self):
        """No wall-clock in the result: two runs serialize to identical
        JSON (idempotency pin)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root, tracker=TASK_ROW_TRACKER)
            _add_structure(root)
            _write_triage(root, "FEAT-900", ["adapters/chrys/chrys_main.py"])

            first = json.dumps(_shadow(root), ensure_ascii=False, sort_keys=True)
            second = json.dumps(_shadow(root), ensure_ascii=False, sort_keys=True)

            self.assertEqual(first, second)

    def test_zero_side_effect_field_declares_no_writes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            _add_structure(root)

            result = _shadow(root)

            self.assertEqual(result["zero_side_effect"]["write_operations"], 0)

    def test_unresolvable_target_fails_closed(self):
        result = lm.derive_structural_units_shadow(
            target_root=str(Path(tempfile.gettempdir()) / "no-such-host-feat071"))
        self.assertFalse(result["shadow_derived"])
        self.assertIn("unresolvable", result["aborted_reason"])


# ═══════════════════════════════════════════════════════════════════════════
# Public manifest consumption API (FEAT-070-R0 P3-5)
# ═══════════════════════════════════════════════════════════════════════════


class TestPublicManifestConsumptionApi(unittest.TestCase):

    def test_public_api_states_and_contract_docstring(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root, tracker=DECISION_TRACKER)
            _add_structure(root)

            # absent
            state, data, issues = lm.load_approval_manifest(root)
            self.assertEqual((state, data, issues), ("absent", None, []))

            # valid — via the record chain (the sanctioned writer)
            self.assertTrue(
                _record(root, _derived_id(root, "adapter.Chrys"))["recorded"])
            state, data, issues = lm.load_approval_manifest(root)
            self.assertEqual(state, "valid")
            self.assertEqual(issues, [])
            self.assertEqual(data["revision"], 1)

            # corrupt — never partially consumed
            manifest = json.loads(_manifest_path(root).read_text(
                encoding="utf-8"))
            manifest["entries"][0]["task_id"] = "tampered/task"
            _manifest_path(root).write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
            state, data, issues = lm.load_approval_manifest(root)
            self.assertEqual(state, "corrupt")
            self.assertIsNone(data)
            self.assertTrue(issues)

        # The consumption contract is declared on the public name itself.
        self.assertIn("contract", lm.load_approval_manifest.__doc__.lower())
        self.assertIn("read-only", lm.load_approval_manifest.__doc__.lower())

    def test_public_api_matches_private_loader(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root, tracker=DECISION_TRACKER)
            _add_structure(root)
            self.assertTrue(
                _record(root, _derived_id(root, "adapter.Chrys"))["recorded"])
            self.assertEqual(lm.load_approval_manifest(root),
                             lm._load_approval_manifest(root))


# ═══════════════════════════════════════════════════════════════════════════
# FEAT-070-R0 P2-2 — face "indeterminate"/None on plan-derivation failure
# ═══════════════════════════════════════════════════════════════════════════


class TestUnitFaceIndeterminateOnPlanFailure(unittest.TestCase):

    def test_valid_manifest_plus_plan_failure_is_indeterminate_none(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            unit_id = lm.build_migration_plan(str(root)).unit_ids[0]
            self.assertTrue(
                _record(root, unit_id, task_id="task/whole")["recorded"])

            patches = [mock.patch.object(lm, "build_migration_plan",
                                         side_effect=ValueError("boom"))]
            try:
                for p in patches:
                    p.start()
                preview = lm.preview_migration(target_root=str(root))
            finally:
                for p in reversed(patches):
                    p.stop()

            face = preview["unit_manifest"]
            self.assertEqual(face["status"], "indeterminate")
            self.assertIsNone(face["ambiguity_count"],
                              "not measured — never a misleading zero")
            self.assertIsNone(preview["unit_manifest_ambiguity_count"])
            self.assertTrue(any("comparison skipped" in i
                                for i in face["issues"]))
            self.assertIn("plan_derivation_error", preview)


# ═══════════════════════════════════════════════════════════════════════════
# CLI — --shadow-derive flag + FEAT-070-R0 P2-1 flag mutex
# ═══════════════════════════════════════════════════════════════════════════


def _run_cli(*argv):
    return subprocess.run(
        [sys.executable, str(Path(lm.__file__))] + list(argv),
        capture_output=True, text=True, encoding="utf-8", check=False,
    )


class TestCliShadowDerive(unittest.TestCase):

    def test_cli_shadow_derive_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            _add_structure(root)
            _write_triage(root, "FEAT-900", ["adapters/chrys/chrys_main.py"])

            completed = _run_cli("--target", str(root), "--shadow-derive")

            self.assertEqual(completed.returncode, 0,
                             completed.stdout + completed.stderr)
            output = json.loads(completed.stdout)
            self.assertEqual(output["mode"], "shadow-derive")
            self.assertTrue(output["shadow_derived"])
            self.assertEqual(output["zero_side_effect"]["write_operations"], 0)
            self.assertEqual(output["comparison"]["row_count"], 0)
            self.assertEqual(len(output["anchor_candidates"]), 1)

    def test_cli_shadow_derive_unresolvable_target_exits_nonzero(self):
        completed = _run_cli(
            "--target",
            str(Path(tempfile.gettempdir()) / "no-such-host-feat071-cli"),
            "--shadow-derive")
        self.assertEqual(completed.returncode, 1)
        output = json.loads(completed.stdout)
        self.assertFalse(output["shadow_derived"])


class TestCliFlagMutex(unittest.TestCase):
    """FEAT-070-R0 P2-1: impossible flag combinations fail LOUDLY (exit 2)
    instead of silently honoring one intent and dropping the other."""

    def test_both_record_flags_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            completed = _run_cli(
                "--target", str(root),
                "--record-unit-approval", "--record-unit-block")
            self.assertEqual(completed.returncode, 2)
            self.assertIn("mutually exclusive", completed.stderr)

    def test_record_with_apply_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            completed = _run_cli("--target", str(root), "--record-unit-approval",
                                 "--apply")
            self.assertEqual(completed.returncode, 2)
            self.assertIn("mutually exclusive", completed.stderr)
            self.assertFalse(
                (root / ".governance" / "flow-unit-runtime.json").is_file(),
                "the mutex must fire before ANY migration work")

    def test_record_with_rollback_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            completed = _run_cli("--target", str(root), "--record-unit-block",
                                 "--rollback")
            self.assertEqual(completed.returncode, 2)
            self.assertIn("mutually exclusive", completed.stderr)

    def test_record_with_dry_run_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            completed = _run_cli("--target", str(root), "--record-unit-approval",
                                 "--dry-run")
            self.assertEqual(completed.returncode, 2)
            self.assertIn("mutually exclusive", completed.stderr)

    def test_record_with_shadow_derive_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            completed = _run_cli("--target", str(root), "--record-unit-approval",
                                 "--shadow-derive")
            self.assertEqual(completed.returncode, 2)
            self.assertIn("mutually exclusive", completed.stderr)

    def test_record_only_companion_without_record_flag_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            for companion in ("--approve-task", "--approve-evidence",
                              "--approve-reviewer", "--block-reason",
                              "--repo-version"):
                completed = _run_cli("--target", str(root), companion, "x")
                self.assertEqual(completed.returncode, 2, companion)
                self.assertIn("only valid together with --record-unit",
                              completed.stderr)

    def test_record_only_companion_with_record_flag_still_works(self):
        """Guard against over-blocking: companions WITH a record flag are
        still legal (exit 1 for the missing-argument refusal, NOT 2)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            completed = _run_cli(
                "--target", str(root), "--record-unit-approval",
                "--approve-unit", "demo-host.script.whole",
                "--approve-task", "task/whole",
                "--repo-version", "1.0.0")
            self.assertEqual(completed.returncode, 1,
                             "record refusal (missing evidence/reviewer) is "
                             "the expected outcome here, not a flag error")
            self.assertNotIn("mutually exclusive", completed.stderr)

    def test_legacy_apply_rollback_precedence_preserved(self):
        """Backward-compatibility pin: the pre-existing rollback>apply
        precedence is NOT part of the P2-1 mutex — the pair must NOT hit the
        new exit-2 validation."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_basic_host(root)
            completed = _run_cli("--target", str(root), "--apply", "--rollback")
            self.assertNotEqual(completed.returncode, 2,
                                completed.stderr)
            self.assertNotIn("mutually exclusive", completed.stderr)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
