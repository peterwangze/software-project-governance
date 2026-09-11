"""FEAT-025 Slice-1 tests — quick-scan 检查段事实源注册表（70 段）。

Bidirectional machine checks (正/负对照) for the five Slice-1 acceptance items
of ``docs/requirements/quickscan-evaluation-0.79.0.md`` §6 (FX-195 §250):

  ① 70/70 coverage — registry segment set ≡ FEAT-020 frozen snapshot Check ids
     (``git show c92bf5d --stat`` → infra/contract_matrix/snapshots.json
     ``faces.check_segments``), via ``reconcile_snapshot``.
  ② completeness guard — an engine segment absent from the table warns and
     fails closed back to ``full`` (missing-segment fixture).
  ③ table schema ⊂ CheckSpec field set (§3.6 of
     ``docs/requirements/architecture-evolution-0.80.0.md``) — Phase-2
     translation claim.
  ④ C3 four segments (28g / 28j / 28l / 29) adjudicated per segment with
     code-level evidence, default-retain quick face (fail-safe).
  ⑤ carrier discipline — the registry is an independent data module: the
     monolith ``verify_workflow.py`` neither imports nor references it
     (zero-modification red line, FX-195 §255).

Negative controls operate on synthetic id fixtures held in memory; the real
engine, the real FEAT-020 snapshot and the real governance data are read-only.

Run:
    python -m unittest skills/software-project-governance/infra.tests.test_quickscan_registry -v
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_SKILL_ROOT = _INFRA_DIR.parent
_REPO_ROOT = _SKILL_ROOT.parents[1]
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import quickscan_registry as qr  # noqa: E402

ENGINE = _INFRA_DIR / "verify_workflow.py"
SNAPSHOT = _INFRA_DIR / "contract_matrix" / "snapshots.json"
ARCH_DOC = _REPO_ROOT / "docs" / "requirements" / "architecture-evolution-0.80.0.md"
EVAL_DOC = _REPO_ROOT / "docs" / "requirements" / "quickscan-evaluation-0.79.0.md"

# FEAT-020 freeze commit (authoritative snapshot provenance).
FREEZE_COMMIT = "c92bf5d"

# quickscan-evaluation §3.1 C1（25 段排除）/ C2（41 段保留）/ C3（4 段待判定）
EVAL_C1_EXCLUDED = (
    "7", "10", "11", "12", "15", "24", "28b", "28d", "28e", "28f", "28h",
    "28i", "28k", "28m", "28n", "28o", "28p", "28q", "28r", "28t", "28u",
    "30b", "31", "33", "40",
)
EVAL_C3_SEGMENTS = ("28g", "28j", "28l", "29")

# Box-drawing dashes used by the engine's ``# ── <id>. `` section markers.
_DASH = "\u2500"


def _write_snapshot(directory, count, ids):
    """Synthetic FEAT-020-shaped snapshot fixture (never the real one)."""
    path = directory / "snapshots.json"
    path.write_text(
        json.dumps({"faces": {"check_segments": {"count": count, "ids": ids}}}),
        encoding="utf-8",
    )
    return path


def _write_engine_fixture(directory, extra_segments=()):
    """Synthetic engine source whose segment census mirrors the real one."""
    lines = ["def _run_full_engine_checks(args):"]
    for check_id in tuple(_engine_ids_for_fixture()) + tuple(extra_segments):
        lines.append(f"    # {_DASH}{_DASH} {check_id}. Fixture segment {_DASH}{_DASH}")
    lines.append("    return 0")
    lines.append("")
    lines.append("def _after():")
    lines.append("    pass")
    path = directory / "verify_workflow_fixture.py"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _engine_ids_for_fixture():
    return qr.registry_ids()


def _snapshot_ids():
    data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    return tuple(data["faces"]["check_segments"]["ids"])


def _engine_source():
    return ENGINE.read_text(encoding="utf-8")


class Acceptance1CoverageTests(unittest.TestCase):
    """① 70/70 coverage against the FEAT-020 frozen snapshot (machine identity)."""

    def test_registry_declares_exactly_the_frozen_segment_ids(self):
        self.assertEqual(len(qr.registry_ids()), 70)
        self.assertEqual(set(qr.registry_ids()), set(_snapshot_ids()))

    def test_registry_order_follows_the_frozen_snapshot_order(self):
        # Declaring rows in snapshot order keeps the human-readable review diff
        # aligned with the frozen contract face (no hidden re-ordering).
        self.assertEqual(tuple(qr.registry_ids()), tuple(_snapshot_ids()))

    def test_snapshot_count_field_matches_ids_and_the_freeze_provenance(self):
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        face = data["faces"]["check_segments"]
        self.assertEqual(face["count"], 70)
        self.assertEqual(face["count"], len(face["ids"]))
        # Snapshot provenance is FEAT-020 (freeze commit c92bf5d).
        self.assertEqual(data["freeze_point"]["task"], "FEAT-020")
        self.assertEqual(data["task"], "FEAT-020")
        self.assertEqual(len(FREEZE_COMMIT), 7)

    def test_reconcile_snapshot_reports_identity_on_the_real_tree(self):
        report = qr.reconcile_snapshot()
        self.assertTrue(report.ok, report.lines())
        self.assertEqual(report.missing, ())
        self.assertEqual(report.extra, ())
        self.assertEqual(len(report.expected), 70)
        self.assertEqual(len(report.actual), 70)

    def test_reconcile_snapshot_negative_control_missing_and_extra(self):
        """Negative control: a drifted registry MUST be reported, never silent."""
        drifted = tuple(i for i in _snapshot_ids() if i != "28o") + ("41",)
        report = qr.reconcile_snapshot(actual_ids=drifted)
        self.assertFalse(report.ok)
        self.assertEqual(report.missing, ("28o",))
        self.assertEqual(report.extra, ("41",))
        self.assertTrue(any("28o" in line for line in report.lines()))

    def test_engine_discovery_yields_the_same_70_segments(self):
        """The live engine's own segment list must equal the frozen snapshot."""
        observed = qr.discover_engine_segment_ids()
        self.assertEqual(len(observed), 70)
        self.assertEqual(set(observed), set(_snapshot_ids()))

    def test_engine_discovery_ignores_non_segment_sections(self):
        """Discovery is scoped to the engine function body, not the whole file."""
        source = _engine_source()
        whole_file_hits = len(
            re.findall(r"^\s*#\s*\u2500\u2500\s*([0-9][A-Za-z0-9]*)\.\s", source, re.M)
        )
        in_body_hits = len(qr.discover_engine_segment_ids())
        self.assertGreater(whole_file_hits, in_body_hits)  # scoping is load-bearing
        self.assertEqual(in_body_hits, 70)


class Acceptance2CompletenessGuardTests(unittest.TestCase):
    """② 完整性守卫：新段未入表 → 告警 + fail-closed 回退 full。"""

    def test_guard_passes_and_keeps_quick_when_coverage_is_complete(self):
        report = qr.guard_completeness()
        self.assertTrue(report.ok, report.lines())
        self.assertEqual(report.undeclared, ())
        self.assertEqual(report.stale, ())
        self.assertFalse(report.fail_closed)
        self.assertEqual(report.fallback_mode, qr.MODE_FULL_FALLBACK)

    def test_guard_warns_and_fails_closed_on_a_new_engine_segment(self):
        """Missing-segment fixture: engine grew a Check 41 the table never saw."""
        fixture = tuple(_snapshot_ids()) + ("41",)
        report = qr.guard_completeness(observed_ids=fixture)
        self.assertFalse(report.ok)
        self.assertEqual(report.undeclared, ("41",))
        self.assertTrue(report.fail_closed)
        self.assertEqual(report.fallback_mode, qr.MODE_FULL_FALLBACK)
        self.assertTrue(report.warnings, "guard MUST emit a warning line")
        self.assertTrue(any("41" in w for w in report.warnings))

    def test_guard_warning_names_the_fail_closed_reason_code(self):
        report = qr.guard_completeness(observed_ids=tuple(_snapshot_ids()) + ("41",))
        joined = "\n".join(report.warnings)
        self.assertIn(qr.REASON_UNDECLARED_SEGMENT, joined)
        self.assertIn("full", joined)

    def test_guard_reports_stale_rows_without_failing_closed(self):
        """A removed engine segment is registry drift: warn only (no coverage loss)."""
        report = qr.guard_completeness(observed_ids=tuple(i for i in _snapshot_ids() if i != "20"))
        self.assertEqual(report.stale, ("20",))
        self.assertEqual(report.undeclared, ())
        self.assertFalse(report.fail_closed)
        self.assertEqual(report.fallback_mode, qr.MODE_FULL_FALLBACK)
        self.assertTrue(report.warnings)

    def test_missing_declared_row_alone_disables_quick(self):
        """Dropping one row from the table must fail closed even if the engine is stable."""
        declared = tuple(i for i in _snapshot_ids() if i != "29")
        report = qr.guard_completeness(declared_ids=declared)
        self.assertEqual(report.undeclared, ("29",))
        self.assertTrue(report.fail_closed)

    def test_guard_uses_live_engine_discovery_by_default(self):
        self.assertEqual(qr.guard_completeness().observed, qr.discover_engine_segment_ids())


class Acceptance3SchemaTests(unittest.TestCase):
    """③ 表 schema ⊂ CheckSpec 字段集（§3.6）——Phase-2 平移性声明。"""

    def test_row_fields_are_a_subset_of_the_checkspec_field_set(self):
        self.assertTrue(qr.SEGMENT_SPEC_FIELDS)
        self.assertLessEqual(set(qr.SEGMENT_SPEC_FIELDS), set(qr.CHECKSPEC_FIELDS))

    def test_checkspec_field_names_match_architecture_evolution_section_3_6(self):
        doc = ARCH_DOC.read_text(encoding="utf-8")
        block = doc.split("class CheckSpec:")[1]
        fields = re.findall(r"^\s{4}([a-z_]+):", block, re.M)
        self.assertEqual(
            tuple(fields),
            ("check_id", "domain", "loader", "input_deps", "severity_floor", "modes"),
        )
        self.assertEqual(tuple(qr.CHECKSPEC_FIELDS), tuple(fields))

    def test_every_row_carries_the_slice1_declared_columns(self):
        for spec in qr.all_segments():
            data = spec.as_dict()
            self.assertEqual(set(data), set(qr.SEGMENT_SPEC_FIELDS))
            self.assertTrue(data["check_id"])
            self.assertTrue(data["domain"])
            self.assertTrue(data["input_deps"])

    def test_declared_columns_are_the_documented_slice1_columns(self):
        # CheckID → 模式政策面 + 事实源根 + 输入路径清单 + 排除原因代码
        self.assertEqual(
            set(qr.SEGMENT_SPEC_FIELDS),
            {"check_id", "domain", "input_deps", "modes"},
        )

    def test_frozen_spec_is_immutable(self):
        spec = qr.segment("1")
        with self.assertRaises(AttributeError):
            spec.check_id = "99"  # frozen dataclass — Phase-2 must re-declare


class Acceptance4FactSourceRootTests(unittest.TestCase):
    """事实源根派生 + 输入路径清单语法（70 段逐行可机判）。"""

    def test_every_input_dep_uses_the_root_tagged_grammar(self):
        for spec in qr.all_segments():
            for dep in spec.input_deps:
                parts = dep.split(":", 2)
                self.assertEqual(len(parts), 3, dep)
                root, kind, target = parts
                self.assertIn(root, qr.DEP_ROOTS, dep)
                self.assertIn(kind, qr.DEP_KINDS[root], dep)
                self.assertTrue(target.strip(), dep)

    def test_fact_source_root_is_derived_from_the_declared_deps(self):
        self.assertEqual(qr.fact_source_root("1"), qr.FACT_SOURCE_HOST)
        self.assertEqual(qr.fact_source_root("11"), qr.FACT_SOURCE_PLUGIN)
        self.assertEqual(qr.fact_source_root("28g"), qr.FACT_SOURCE_MIXED)

    def test_fact_source_root_is_unknown_for_an_undeclared_segment(self):
        """Fail-closed: an unknown segment can never be reported as covered."""
        self.assertEqual(qr.fact_source_root("41"), qr.FACT_SOURCE_UNKNOWN)
        self.assertIn(qr.REASON_UNKNOWN_INPUT, qr.FALLBACK_REASON_CODES)

    def test_every_segment_has_a_known_root(self):
        unknown = [s.check_id for s in qr.all_segments() if s.fact_source_root == qr.FACT_SOURCE_UNKNOWN]
        self.assertEqual(unknown, [])

    def test_host_face_segments_only_declare_host_governance_or_host_git(self):
        for spec in qr.all_segments():
            if spec.fact_source_root != qr.FACT_SOURCE_HOST:
                continue
            for dep in spec.input_deps:
                self.assertTrue(dep.startswith("host:"), f"{spec.check_id}: {dep}")


class Acceptance5C3AdjudicationTests(unittest.TestCase):
    """④ C3 四段逐段裁决：代码级依据 + 默认保留 quick 面（fail-safe）。"""

    def test_the_four_c3_segments_are_adjudicated(self):
        self.assertEqual(tuple(qr.C3_ADJUDICATED_SEGMENTS), EVAL_C3_SEGMENTS)
        for check_id in EVAL_C3_SEGMENTS:
            self.assertIn(check_id, qr.C3_ADJUDICATION, check_id)

    def test_c3_segments_keep_the_quick_face(self):
        """§3.1 C3：默认保留 quick 面（fail-safe to more checks）。"""
        for check_id in EVAL_C3_SEGMENTS:
            spec = qr.segment(check_id)
            self.assertIn(qr.MODE_QUICK, spec.modes, check_id)
            self.assertIsNone(qr.exclusion_reason_code(check_id), check_id)
            self.assertEqual(qr.C3_ADJUDICATION[check_id]["verdict"], qr.C3_VERDICT_RETAIN)

    def test_c3_verdicts_carry_code_level_evidence_backing_the_declared_deps(self):
        for check_id in EVAL_C3_SEGMENTS:
            basis = qr.C3_ADJUDICATION[check_id]["basis"]
            self.assertTrue(basis, check_id)
            joined = " | ".join(basis)
            for dep in qr.segment(check_id).input_deps:
                target = dep.split(":", 2)[2]
                self.assertIn(target, joined, f"{check_id}: {dep} not backed by evidence")

    def test_c3_g_governance_context_reads_host_hot_files_and_plugin_command_docs(self):
        spec = qr.segment("28g")
        self.assertEqual(spec.fact_source_root, qr.FACT_SOURCE_MIXED)
        self.assertIn("host:governance:.governance/plan-tracker.md", spec.input_deps)
        self.assertIn("plugin:asset:commands/governance.md", spec.input_deps)

    def test_c3_j_and_l_capability_context_are_plugin_face_and_not_product_gated(self):
        """Code evidence: both read plugin assets only — and FIX-270 does not gate them."""
        for check_id in ("28j", "28l"):
            spec = qr.segment(check_id)
            self.assertEqual(spec.fact_source_root, qr.FACT_SOURCE_PLUGIN, check_id)
            self.assertIn("skills/software-project-governance/infra/TOOLS.md", " ".join(spec.input_deps))
            self.assertNotIn(check_id, EVAL_C1_EXCLUDED)

    def test_c3_29_m5_runtime_triggers_is_host_face(self):
        spec = qr.segment("29")
        self.assertEqual(spec.fact_source_root, qr.FACT_SOURCE_HOST)
        self.assertEqual(spec.input_deps, ("host:governance:.governance/evidence-log.md",))

    def test_review_recorded_c3_verdicts_are_not_silently_reclassified(self):
        for check_id in EVAL_C3_SEGMENTS:
            self.assertEqual(qr.C3_ADJUDICATION[check_id]["review"], "FX-195 §136 C3 行 + 代码核验")


class QuickFacePolicyTests(unittest.TestCase):
    """模式政策面：排除集 = FIX-270 机判 product-gate 集（§3.1 C1）。"""

    def test_excluded_set_equals_the_engine_product_gate_declaration(self):
        self.assertEqual(set(qr.excluded_ids()), set(qr.discover_product_gate_ids()))

    def test_excluded_set_equals_the_evaluation_c1_list(self):
        self.assertEqual(set(qr.excluded_ids()), set(EVAL_C1_EXCLUDED))
        self.assertEqual(len(qr.excluded_ids()), 25)

    def test_engine_product_gate_parse_matches_the_live_constant(self):
        import verify_workflow as vw  # heavy import confined to this assertion

        live = {raw.replace("Check ", "").strip() for raw in vw._PLUGIN_PRODUCT_CHECK_IDS}
        self.assertEqual(set(qr.discover_product_gate_ids()), live)

    def test_quick_face_is_the_complement_of_the_exclusion_set(self):
        quick = set(qr.quick_face_ids())
        excluded = set(qr.excluded_ids())
        self.assertEqual(len(quick), 45)
        self.assertEqual(quick | excluded, set(_snapshot_ids()))
        self.assertEqual(quick & excluded, set())
        for spec in qr.all_segments():
            self.assertEqual(qr.MODE_QUICK in spec.modes, spec.check_id in quick)

    def test_every_excluded_segment_carries_a_reason_code(self):
        for check_id in qr.excluded_ids():
            code = qr.exclusion_reason_code(check_id)
            self.assertIn(code, qr.EXCLUSION_REASON_CODES, check_id)

    def test_reason_codes_follow_the_fix_270_fact_source_groupings(self):
        expected = {
            "7": "PLUGIN_GIT_FACT_SOURCE",
            "15": "PLUGIN_GIT_FACT_SOURCE",
            "31": "PLUGIN_CLAIM_ATTESTATION",
            "28o": "PLUGIN_TREE_SCAN",
            "28p": "PLUGIN_TREE_SCAN",
            "28q": "PLUGIN_TREE_SCAN",
            "28r": "PLUGIN_TREE_SCAN",
            "30b": "PLUGIN_TREE_SCAN",
            "11": "PLUGIN_PACKAGE_ASSET",
            "40": "PLUGIN_PACKAGE_ASSET",
        }
        for check_id, code in expected.items():
            self.assertEqual(qr.exclusion_reason_code(check_id), code, check_id)

    def test_retained_segments_carry_no_reason_code(self):
        for check_id in qr.quick_face_ids():
            self.assertIsNone(qr.exclusion_reason_code(check_id), check_id)

    def test_mode_tokens_are_legal_and_always_include_full(self):
        for spec in qr.all_segments():
            self.assertIn(qr.MODE_FULL, spec.modes, spec.check_id)
            for mode in spec.modes:
                if mode.startswith(qr.NOT_QUICK_PREFIX):
                    code = mode.split(":", 1)[1]
                    self.assertIn(code, qr.EXCLUSION_REASON_CODES, spec.check_id)
                else:
                    self.assertIn(mode, (qr.MODE_FULL, qr.MODE_QUICK), spec.check_id)

    def test_exclusion_reason_code_table_is_a_frozen_constant_table(self):
        self.assertEqual(
            set(qr.EXCLUSION_REASON_CODES),
            {
                "PLUGIN_GIT_FACT_SOURCE",
                "PLUGIN_PACKAGE_ASSET",
                "PLUGIN_TREE_SCAN",
                "PLUGIN_CLAIM_ATTESTATION",
            },
        )
        for code, text in qr.EXCLUSION_REASON_CODES.items():
            self.assertTrue(text.strip(), code)


class DiscoveryDisclosureTests(unittest.TestCase):
    """实现期新发现：插件面但未经 product-gate 登记的段 + 双根披露。"""

    def test_plugin_face_segments_absent_from_the_product_gate_are_retained(self):
        discovered = qr.plugin_face_not_product_gated()
        self.assertIn("18h", discovered)
        self.assertIn("28", discovered)
        for check_id in discovered:
            self.assertIn(qr.MODE_QUICK, qr.segment(check_id).modes, check_id)

    def test_discovered_plugin_face_segments_are_not_in_the_evaluation_c1_list(self):
        for check_id in qr.plugin_face_not_product_gated():
            self.assertNotIn(check_id, EVAL_C1_EXCLUDED, check_id)

    def test_dual_root_disclosure_lists_excluded_segments_touching_host_facts(self):
        """24 and 31 are dual-root by design, yet both sit in the exclusion set.

        24 reads plugin version assets *and* the host plan-tracker version
        projection (``check_version_consistency`` passes ``GOVERNANCE_DIR.parent``
        alongside ``ROOT``); 31 declares ``product_root`` + ``host_root`` with an
        ``installed_host`` scan mode. Both stay excluded (FIX-270 + §3.1 C1) and
        are disclosed here instead of being silently flattened to "plugin face".

        ArchGuard 28o only *appears* to touch host paths in dogfood (its tree
        anchor is ROOT and dogfood roots coincide) — it must stay plugin-only so
        that Phase-2 closure never selects it for a governance-data change.
        """
        disclosed = qr.dual_root_disclosures()
        self.assertEqual(disclosed, ("24", "31"))
        self.assertTrue(all(qr.exclusion_reason_code(c) for c in disclosed))
        self.assertTrue(all(qr.fact_source_root(c) == qr.FACT_SOURCE_MIXED for c in disclosed))
        self.assertEqual(qr.fact_source_root("28o"), qr.FACT_SOURCE_PLUGIN)
        self.assertEqual(qr.fact_source_root("24"), qr.FACT_SOURCE_MIXED)
        self.assertEqual(qr.fact_source_root("31"), qr.FACT_SOURCE_MIXED)


class CarrierDisciplineTests(unittest.TestCase):
    """⑤ 载体禁写入巨石编排体（FX-195 §255）：注册表为独立数据模块。"""

    def test_engine_never_references_the_registry_module(self):
        source = _engine_source()
        self.assertNotIn("quickscan_registry", source)
        self.assertNotIn("quickscan", source)

    def test_registry_module_does_not_import_the_engine(self):
        """A data module must not import the 24k-line orchestration body."""
        source = (_INFRA_DIR / "quickscan_registry.py").read_text(encoding="utf-8")
        self.assertNotIn("import verify_workflow", source)
        self.assertNotIn("from verify_workflow", source)
        self.assertNotIn("import subprocess", source)

    def test_registry_module_declares_no_cli_surface(self):
        """No CLI surface in this slice — quick orchestration belongs to Slice-2.

        The module docstring names argparse only to forbid it, so the scan runs
        over the code body (everything after the closing docstring delimiter).
        """
        source = (_INFRA_DIR / "quickscan_registry.py").read_text(encoding="utf-8")
        body = source.split('"""', 2)[-1]
        self.assertNotIn("argparse", body)
        self.assertNotIn("add_parser", body)
        self.assertNotIn("set_defaults", body)

    def test_engine_segment_census_is_unchanged_by_this_slice(self):
        """The 70-segment census and the CLI key census still hold (no engine edit)."""
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        self.assertEqual(len(qr.discover_engine_segment_ids()), 70)
        self.assertEqual(data["faces"]["check_segments"]["count"], 70)
        self.assertEqual(data["faces"]["cli_dispatch"]["key_count"], len(data["faces"]["cli_dispatch"]["keys"]))

    def test_registry_declares_no_module_level_file_io(self):
        """Importing the table alone must be pure declaration (no reads, no drift)."""
        source = (_INFRA_DIR / "quickscan_registry.py").read_text(encoding="utf-8")
        module_level = source.split("\ndef ", 1)[0]
        for token in ("read_text(", "read_bytes(", "json.load(", "open(", "Path(__file__)"):
            self.assertNotIn(token, module_level, token)


class DesignTraceabilityTests(unittest.TestCase):
    """Slice-1 规格可溯：本注册表与 FX-195 §6 / §250 / §255 的锚定。"""

    def test_module_docstring_anchors_the_slice_spec(self):
        doc = qr.__doc__ or ""
        for token in (
            "quickscan-evaluation-0.79.0.md",
            "architecture-evolution-0.80.0.md",
            "FEAT-020",
            "c92bf5d",
            "FX-195",
            "Slice-1",
        ):
            self.assertIn(token, doc, token)

    def test_evaluation_doc_still_lists_the_four_c3_segments(self):
        doc = EVAL_DOC.read_text(encoding="utf-8")
        row = next(line for line in doc.split("\n") if line.startswith("| **C3 待判定"))
        for check_id in EVAL_C3_SEGMENTS:
            self.assertIn(check_id, row, check_id)

    def test_unknown_segment_lookup_fails_closed(self):
        with self.assertRaises(KeyError):
            qr.segment("41")
        with self.assertRaises(KeyError):
            qr.exclusion_reason_code("41")


class FailClosedBranchTests(unittest.TestCase):
    """Every fail-closed guard gets a negative control (no silent passthrough)."""

    def test_unknown_exclusion_reason_code_is_rejected(self):
        with self.assertRaises(KeyError):
            qr._excluded("NOT_A_REASON_CODE")

    def test_excluded_row_without_a_reason_token_yields_no_code(self):
        spec = qr.SegmentSpec("x", "d", ("plugin:asset:a.md",), (qr.MODE_FULL,))
        self.assertTrue(spec.excluded_from_quick)
        self.assertIsNone(spec.exclusion_reason_code)

    def test_empty_input_deps_derive_unknown_root(self):
        spec = qr.SegmentSpec("x", "d", (), (qr.MODE_FULL, qr.MODE_QUICK))
        self.assertEqual(spec.fact_source_root, qr.FACT_SOURCE_UNKNOWN)

    def test_engine_discovery_fails_closed_without_the_entry_function(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verify_workflow.py"
            path.write_text("def something_else():\n    pass\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                qr.discover_engine_segment_ids(path)

    def test_product_gate_discovery_fails_closed_without_the_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verify_workflow.py"
            path.write_text("x = 1\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                qr.discover_product_gate_ids(path)

    def test_snapshot_loader_fails_closed_on_count_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_snapshot(Path(tmp), count=2, ids=["1"])
            with self.assertRaises(ValueError):
                qr.load_frozen_snapshot_ids(path)


class FixtureDrivenGuardTests(unittest.TestCase):
    """② 完整性守卫端到端负对照：引擎源码 fixture 长出新段（不碰真引擎）。"""

    def test_guard_discovers_a_new_segment_from_a_fixture_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _write_engine_fixture(Path(tmp), extra_segments=("41",))
            report = qr.guard_completeness(engine_path=fixture)
            self.assertEqual(report.undeclared, ("41",))
            self.assertTrue(report.fail_closed)
            self.assertEqual(report.fallback_mode, qr.MODE_FULL_FALLBACK)
            self.assertTrue(
                any("41" in w and qr.REASON_UNDECLARED_SEGMENT in w for w in report.warnings)
            )
            self.assertEqual(len(report.observed), 71)

    def test_guard_stays_green_on_a_fixture_engine_without_new_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _write_engine_fixture(Path(tmp))
            report = qr.guard_completeness(engine_path=fixture)
            self.assertTrue(report.ok)
            self.assertFalse(report.fail_closed)
            self.assertEqual(report.warnings, ())
            self.assertIn("fallback=full", report.lines()[0])

    def test_guard_ignores_non_segment_sections_in_a_fixture_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "verify_workflow.py"
            path.write_text(
                "def _run_full_engine_checks(args):\n"
                "    # " + _DASH + _DASH + " Summary " + _DASH + _DASH + "\n"
                "    pass\n",
                encoding="utf-8",
            )
            self.assertEqual(qr.guard_completeness(engine_path=path).observed, ())

    def test_count_mismatch_guard_accepts_a_matching_fixture_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = _write_snapshot(Path(tmp), count=70, ids=list(_snapshot_ids()))
            self.assertEqual(qr.load_frozen_snapshot_ids(fixture), tuple(_snapshot_ids()))
            self.assertTrue(
                qr.reconcile_snapshot(snapshot_ids=tuple(_snapshot_ids())).ok
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
