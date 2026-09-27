"""Unit tests for loop_migration.py's unit approval manifest — FEAT-070.

DEC-254 (arch 混合方案 B 先手) landed the §2.6 human confirmation path:
``record_unit_approval`` / ``record_unit_block`` are the ONLY sanctioned
writers of ``.governance/flow-unit-approval-manifest.json``, and the dry-run
consumes that manifest instead of prose-token anchoring. These tests guard:

  - **Versioned storage** — the manifest carries a manifest-level
    schema_version and every entry carries the DEC-254 four-element record
    (task/unit stable identifiers, confirmation evidence, repo version,
    reviewer).
  - **Idempotency** — re-confirming the SAME unit never forks a second
    entry (in-place refresh; digest + revision stay consistent).
  - **Fail-closed corruption detection** — an unreadable/tampered manifest
    is never partially consumed, and the approval chain refuses to write
    on top of a corrupt manifest.
  - **Bypass detection** — an out-of-chain (hand) edit of entries/blocked
    breaks the recorded entries_digest and is rejected; a hand-written
    manifest that maintains the digest but violates the schema is rejected
    by the schema checks.
  - **Blocked-path trace** — a §2.6 block is recorded with reason/recorder,
    a confirmed unit cannot be blocked, and approving a previously blocked
    unit supersedes the block with the trace preserved.
  - **Dry-run consumption** — units without a confirmed entry stay §2.6
    fail-closed (missing/blocked are reported, never guessed);
    a complete manifest yields ambiguity_count = 0; stale entries
    (derivation drift) are surfaced.

ALL tests use ``tempfile.TemporaryDirectory`` — the real ``.governance/`` is
NEVER touched, and no test asserts on wall-clock values (content criteria
only; ``elapsed_ms`` is asserted for presence/type, never magnitude).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_loop_unit_manifest.py -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import loop_migration as lm  # noqa: E402
from loop_migration_plan import build_migration_plan  # noqa: E402

# A minimal classic plan-tracker with NO decomposable prose → the derivation
# yields exactly ONE fallback unit ({project_id}.script.whole).
MINIMAL_TRACKER = (
    "# Plan Tracker — demo-host\n"
    "## 项目配置\n"
    "- workflow_model: classic-phase-gate\n"
    "## Gate 状态跟踪\n"
    "| Gate | 阶段转换 | 状态 |\n"
    "| --- | --- | --- |\n"
    "| G11 | next | passed |\n"
)

# A tracker with exactly two prose-derivable phrases (probe-verified):
# "chrys adapter" and "review skill" → two deterministic units.
PROSE_TRACKER = (
    "# Plan Tracker — demo-host\n"
    "## 项目配置\n"
    "- workflow_model: classic-phase-gate\n"
    "the chrys adapter and the review skill\n"
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


def _write_host(root, tracker=MINIMAL_TRACKER):
    """Write a minimal classic .governance/ into root (no manifest, no runtime)."""
    gov = root / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "plan-tracker.md").write_text(tracker, encoding="utf-8")
    (gov / "evidence-log.md").write_text(EVIDENCE_LOG, encoding="utf-8")


def _derived_ids(root):
    """The derived candidate unit ids for a fixture root (the real planner)."""
    plan = build_migration_plan(str(root))
    return list(plan.unit_ids)


def _manifest_path(root):
    return root / ".governance" / lm.APPROVAL_MANIFEST_FILENAME


def _read_manifest(root):
    return json.loads(_manifest_path(root).read_text(encoding="utf-8"))


def _write_manifest(root, manifest):
    _manifest_path(root).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _approve(root, unit_id, task_id="adapters/chrys",
             evidence="structural fact: adapters/chrys/ exists",
             reviewer="test-reviewer", repo_version="1.2.3"):
    return lm.record_unit_approval(
        target_root=str(root), flow_unit_id=unit_id, task_id=task_id,
        confirmation_evidence=evidence, reviewer=reviewer,
        repo_version=repo_version,
    )


def _block(root, unit_id, reason="ambiguity: multiple candidates",
           recorder="test-reviewer", repo_version="1.2.3"):
    return lm.record_unit_block(
        target_root=str(root), flow_unit_id=unit_id, reason=reason,
        recorded_by=recorder, repo_version=repo_version,
    )


# ═══════════════════════════════════════════════════════════════════════════
# record_unit_approval — the §2.6 confirmation writer
# ═══════════════════════════════════════════════════════════════════════════


class TestRecordUnitApproval(unittest.TestCase):
    """FEAT-070 confirm chain: versioned storage + idempotency + refusals."""

    def test_first_approval_creates_versioned_manifest(self):
        """Branch: manifest absent → create. The entry carries the DEC-254
        four-element record and the manifest carries a schema_version."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]

            result = _approve(root, unit_id)

            self.assertTrue(result["recorded"], f"approval refused: {result}")
            self.assertEqual(result["manifest_revision"], 1)
            self.assertEqual(
                Path(result["manifest_path"]).name, lm.APPROVAL_MANIFEST_FILENAME
            )
            self.assertTrue(Path(result["manifest_path"]).is_file())
            manifest = _read_manifest(root)
            # Manifest-level version fields.
            self.assertEqual(
                manifest["schema_version"], lm.APPROVAL_MANIFEST_SCHEMA_VERSION
            )
            self.assertEqual(manifest["manifest_id"], lm.APPROVAL_MANIFEST_ID)
            self.assertEqual(manifest["revision"], 1)
            # Entry: four-element record (+ writer-stamped instant).
            self.assertEqual(len(manifest["entries"]), 1)
            entry = manifest["entries"][0]
            for field in lm._MANIFEST_ENTRY_REQUIRED_FIELDS:
                self.assertIn(field, entry)
                self.assertIsInstance(entry[field], str)
                self.assertTrue(entry[field].strip(), f"{field} must be non-empty")
            self.assertEqual(entry["flow_unit_id"], unit_id)
            self.assertEqual(entry["task_id"], "adapters/chrys")
            self.assertEqual(entry["repo_version"], "1.2.3")
            self.assertEqual(entry["reviewer"], "test-reviewer")
            # Digest present and consistent (reload validates it).
            self.assertTrue(manifest["entries_digest"])
            state, _, issues = lm._load_approval_manifest(root)
            self.assertEqual(state, "valid")
            self.assertEqual(issues, [])

    def test_repeat_approval_same_unit_no_fork(self):
        """Branch: entries hit + same task → in-place refresh. Re-confirming
        the SAME unit must NOT fork a second entry (idempotency)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]

            first = _approve(root, unit_id, evidence="evidence v1")
            self.assertTrue(first["recorded"])
            second = _approve(root, unit_id, evidence="evidence v2 (refreshed)")
            self.assertTrue(second["recorded"], f"re-approval refused: {second}")

            manifest = _read_manifest(root)
            self.assertEqual(len(manifest["entries"]), 1,
                             "same-unit re-confirmation must not fork entries")
            self.assertEqual(manifest["entries"][0]["confirmation_evidence"],
                             "evidence v2 (refreshed)")
            # Revision advanced, digest still valid after the refresh.
            self.assertEqual(manifest["revision"], 2)
            state, _, issues = lm._load_approval_manifest(root)
            self.assertEqual(state, "valid")
            self.assertEqual(issues, [])
            self.assertEqual(second["manifest_revision"], 2)

    def test_conflicting_task_for_same_unit_refused(self):
        """Branch: entries hit + DIFFERENT task → refused, manifest bytes
        unchanged (no silent re-mapping)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]

            first = _approve(root, unit_id, task_id="adapters/chrys")
            self.assertTrue(first["recorded"])
            before = _manifest_path(root).read_bytes()

            conflict = _approve(root, unit_id, task_id="skills/review")
            self.assertFalse(conflict["recorded"])
            self.assertIn("conflicting mapping", conflict["refused_reason"])
            self.assertEqual(_manifest_path(root).read_bytes(), before,
                             "a refused record must leave the manifest untouched")

    def test_unknown_unit_refused(self):
        """Branch: unit not in the derived candidate set → refused (an operator
        cannot approve a unit the planner never derived)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)

            result = _approve(root, "project-management-workflow.adapter.ghost")

            self.assertFalse(result["recorded"])
            self.assertIn("unknown flow_unit_id", result["refused_reason"])
            self.assertFalse(_manifest_path(root).is_file(),
                             "a refused first record must not create a manifest")

    def test_empty_field_refused(self):
        """Branch: input validation — every four-element field is required."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]

            result = _approve(root, unit_id, evidence="   ")

            self.assertFalse(result["recorded"])
            self.assertIn("confirmation_evidence", result["refused_reason"])
            self.assertFalse(_manifest_path(root).is_file())

    def test_approval_overturns_blocked_unit(self):
        """Branch: unit in blocked list → the approval is the §2.6 adjudication
        outcome: the block is lifted and the trace is kept on the entry."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]

            blocked = _block(root, unit_id, reason="prose anchor ambiguous")
            self.assertTrue(blocked["recorded"])
            approved = _approve(root, unit_id)
            self.assertTrue(approved["recorded"], f"adjudication refused: {approved}")

            manifest = _read_manifest(root)
            self.assertEqual(len(manifest["entries"]), 1)
            self.assertEqual(manifest["blocked"], [],
                             "adjudicated approval must lift the block")
            self.assertEqual(manifest["entries"][0].get("supersedes_block_reason"),
                             "prose anchor ambiguous")
            state, _, _ = lm._load_approval_manifest(root)
            self.assertEqual(state, "valid")


# ═══════════════════════════════════════════════════════════════════════════
# record_unit_block — the §2.6 fail-closed trace
# ═══════════════════════════════════════════════════════════════════════════


class TestRecordUnitBlock(unittest.TestCase):
    """FEAT-070 block chain: trace fields + refusal on confirmed units."""

    def test_block_creates_trace_entry(self):
        """Branch: manifest absent → create with the blocked entry carrying
        reason/recorder/version/instant (阻塞路径留痕)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]

            result = _block(root, unit_id, reason="no unique structural match")

            self.assertTrue(result["recorded"], f"block refused: {result}")
            manifest = _read_manifest(root)
            self.assertEqual(manifest["entries"], [])
            self.assertEqual(len(manifest["blocked"]), 1)
            item = manifest["blocked"][0]
            for field in lm._MANIFEST_BLOCKED_REQUIRED_FIELDS:
                self.assertIn(field, item)
                self.assertTrue(str(item[field]).strip())
            self.assertEqual(item["flow_unit_id"], unit_id)
            self.assertEqual(item["reason"], "no unique structural match")
            self.assertEqual(item["recorded_by"], "test-reviewer")
            state, _, issues = lm._load_approval_manifest(root)
            self.assertEqual(state, "valid")
            self.assertEqual(issues, [])

    def test_block_confirmed_unit_refused(self):
        """Branch: unit already confirmed → block recorder refuses (overturning
        a confirmation is an adjudication decision, not a block)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]

            approved = _approve(root, unit_id)
            self.assertTrue(approved["recorded"])
            before = _manifest_path(root).read_bytes()

            result = _block(root, unit_id, reason="second thoughts")
            self.assertFalse(result["recorded"])
            self.assertIn("already CONFIRMED", result["refused_reason"])
            self.assertEqual(_manifest_path(root).read_bytes(), before)

    def test_repeat_block_refreshes_no_fork(self):
        """Branch: blocked hit → in-place refresh of the SAME blocked entry."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]

            first = _block(root, unit_id, reason="reason v1")
            second = _block(root, unit_id, reason="reason v2 (adjudication pending)")
            self.assertTrue(first["recorded"] and second["recorded"])

            manifest = _read_manifest(root)
            self.assertEqual(len(manifest["blocked"]), 1,
                             "re-blocking the same unit must not fork entries")
            self.assertEqual(manifest["blocked"][0]["reason"],
                             "reason v2 (adjudication pending)")
            state, _, _ = lm._load_approval_manifest(root)
            self.assertEqual(state, "valid")


# ═══════════════════════════════════════════════════════════════════════════
# Corruption detection — fail-closed, never partially consumed
# ═══════════════════════════════════════════════════════════════════════════


class TestManifestCorruptionDetection(unittest.TestCase):
    """FEAT-070 consumer/writer fail-closed faces on a damaged manifest."""

    def test_unreadable_json_detected(self):
        """Branch: invalid UTF-8/JSON on disk → state corrupt with issue."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            _manifest_path(root).write_text("{ this is not json,,,", encoding="utf-8")

            state, data, issues = lm._load_approval_manifest(root)

            self.assertEqual(state, "corrupt")
            self.assertIsNone(data, "a corrupt manifest must not be consumable")
            self.assertTrue(issues)
            self.assertTrue(all(i.startswith("unit_manifest_corrupt") for i in issues))

    def test_out_of_chain_edit_detected_via_digest(self):
        """Branch: a VALID manifest is hand-edited on disk (bypass write) →
        the recorded entries_digest no longer matches → corrupt."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]
            self.assertTrue(_approve(root, unit_id)["recorded"])

            # Bypass write: flip a field directly on disk, keeping valid JSON.
            manifest = _read_manifest(root)
            manifest["entries"][0]["reviewer"] = "hand-editor"
            _write_manifest(root, manifest)

            state, data, issues = lm._load_approval_manifest(root)
            self.assertEqual(state, "corrupt")
            self.assertIsNone(data)
            self.assertTrue(
                any("entries_digest mismatch" in i for i in issues),
                f"expected a digest-mismatch issue, got {issues}",
            )

    def test_unknown_schema_version_detected(self):
        """Branch: schema_version the consumer does not support → refused
        (not guessed forward)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]
            self.assertTrue(_approve(root, unit_id)["recorded"])

            manifest = _read_manifest(root)
            manifest["schema_version"] = "999.0"
            # Maintain the digest so ONLY the schema check fires.
            manifest["entries_digest"] = lm._manifest_entries_digest(
                manifest["entries"], manifest["blocked"]
            )
            _write_manifest(root, manifest)

            state, _, issues = lm._load_approval_manifest(root)
            self.assertEqual(state, "corrupt")
            self.assertTrue(any("schema_version" in i for i in issues))

    def test_missing_required_entry_field_detected(self):
        """Branch: a self-consistent (digest-maintained) hand-written manifest
        violating the entry schema → rejected by the schema checks."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]
            self.assertTrue(_approve(root, unit_id)["recorded"])

            manifest = _read_manifest(root)
            # Drop the confirmation evidence — a hand writer that maintains
            # the digest but skips the four-element record.
            del manifest["entries"][0]["confirmation_evidence"]
            manifest["entries_digest"] = lm._manifest_entries_digest(
                manifest["entries"], manifest["blocked"]
            )
            _write_manifest(root, manifest)

            state, _, issues = lm._load_approval_manifest(root)
            self.assertEqual(state, "corrupt")
            self.assertTrue(
                any("confirmation_evidence" in i for i in issues),
                f"expected a missing-field issue, got {issues}",
            )

    def test_duplicate_entry_detected(self):
        """Branch: duplicate confirmed flow_unit_id → corrupt."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]
            self.assertTrue(_approve(root, unit_id)["recorded"])

            manifest = _read_manifest(root)
            forked = dict(manifest["entries"][0])
            forked["confirmed_at"] = "2000-01-01T00:00:00Z"  # simulate a fork
            manifest["entries"].append(forked)
            manifest["entries_digest"] = lm._manifest_entries_digest(
                manifest["entries"], manifest["blocked"]
            )
            _write_manifest(root, manifest)

            state, _, issues = lm._load_approval_manifest(root)
            self.assertEqual(state, "corrupt")
            self.assertTrue(any("duplicate confirmed" in i for i in issues))

    def test_corrupt_manifest_blocks_further_writes(self):
        """Branch: the WRITER refuses to record on top of a corrupt manifest
        (a tampered manifest is never silently overwritten)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]
            self.assertTrue(_approve(root, unit_id)["recorded"])

            manifest = _read_manifest(root)
            manifest["entries"][0]["task_id"] = "tampered/task"
            _write_manifest(root, manifest)  # digest now stale

            result = _approve(root, unit_id)
            self.assertFalse(result["recorded"])
            self.assertIn("corrupt", result["refused_reason"])
            self.assertTrue(result.get("validation_issues"))
            # The tampered bytes are preserved for human inspection.
            self.assertEqual(_read_manifest(root)["entries"][0]["task_id"],
                             "tampered/task")


# ═══════════════════════════════════════════════════════════════════════════
# Dry-run consumption — prefer the manifest, fail-closed on gaps
# ═══════════════════════════════════════════════════════════════════════════


class TestDryRunManifestConsumption(unittest.TestCase):
    """FEAT-070 preview_migration manifest face (read-only consumption)."""

    def test_preview_without_manifest_reports_all_units_missing(self):
        """Branch: manifest absent → every derived unit is §2.6 fail-closed
        (missing); the ambiguity count equals the derived unit count."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            expected = len(_derived_ids(root))

            preview = lm.preview_migration(target_root=str(root))
            face = preview["unit_manifest"]

            self.assertEqual(face["status"], "absent")
            self.assertEqual(face["derived_unit_count"], expected)
            self.assertEqual(face["ambiguity_count"], expected)
            self.assertEqual(face["confirmed_count"], 0)
            self.assertEqual(
                [u["state"] for u in face["unconfirmed_units"]],
                ["missing"] * expected,
            )
            self.assertEqual(
                preview["unit_manifest_ambiguity_count"], expected
            )

    def test_preview_with_full_manifest_zero_ambiguity(self):
        """Branch: every derived unit confirmed → consumed, ambiguity 0."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            ids = _derived_ids(root)
            for uid in ids:
                self.assertTrue(_approve(root, uid, task_id="task/" + uid)["recorded"])

            preview = lm.preview_migration(target_root=str(root))
            face = preview["unit_manifest"]

            self.assertEqual(face["status"], "consumed")
            self.assertEqual(face["confirmed_count"], len(ids))
            self.assertEqual(face["ambiguity_count"], 0,
                             "a complete manifest must yield zero anchoring ambiguity")
            self.assertEqual(preview["unit_manifest_ambiguity_count"], 0)
            self.assertEqual(face["unconfirmed_units"], [])
            self.assertEqual(face["stale_manifest_entries"], [])
            self.assertEqual(face["issues"], [])

    def test_preview_with_partial_manifest_reports_missing_units(self):
        """Branch: only some units confirmed → the rest stay §2.6 fail-closed
        missing (never guessed from prose)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root, tracker=PROSE_TRACKER)
            ids = _derived_ids(root)
            self.assertEqual(len(ids), 2, "probe fixture invariant")
            self.assertTrue(_approve(root, ids[0], task_id="adapters/chrys")["recorded"])

            preview = lm.preview_migration(target_root=str(root))
            face = preview["unit_manifest"]

            self.assertEqual(face["status"], "consumed")
            self.assertEqual(face["confirmed_count"], 1)
            self.assertEqual(face["confirmed_units"], [ids[0]])
            self.assertEqual(face["missing_count"], 1)
            self.assertEqual(face["ambiguity_count"], 1)
            self.assertEqual(face["unconfirmed_units"][0]["flow_unit_id"], ids[1])
            self.assertEqual(face["unconfirmed_units"][0]["state"], "missing")

    def test_preview_reports_blocked_units_with_reason(self):
        """Branch: blocked entries surface as §2.6-blocked unconfirmed units
        carrying the recorded reason."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root, tracker=PROSE_TRACKER)
            ids = _derived_ids(root)
            self.assertTrue(
                _block(root, ids[1], reason="name is a release-theme fragment")["recorded"]
            )

            preview = lm.preview_migration(target_root=str(root))
            face = preview["unit_manifest"]

            self.assertEqual(face["status"], "consumed")
            self.assertEqual(face["blocked_count"], 1)
            unconfirmed = {u["flow_unit_id"]: u for u in face["unconfirmed_units"]}
            self.assertEqual(unconfirmed[ids[1]]["state"], "blocked")
            self.assertEqual(unconfirmed[ids[1]]["detail"],
                             "name is a release-theme fragment")
            self.assertEqual(face["ambiguity_count"], 2,
                             "blocked units are NOT resolved anchoring")

    def test_preview_detects_stale_entries_after_derivation_change(self):
        """Branch: the derivation changes under a recorded manifest → the
        entries referencing non-derived ids are reported stale + issue."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)  # minimal tracker → fallback unit
            fallback_id = _derived_ids(root)[0]
            self.assertTrue(_approve(root, fallback_id, task_id="task/whole")["recorded"])

            # Derivation drift: rewrite the tracker so the planner now derives
            # DIFFERENT units (prose units replace the fallback).
            _write_host(root, tracker=PROSE_TRACKER)

            preview = lm.preview_migration(target_root=str(root))
            face = preview["unit_manifest"]

            self.assertEqual(face["status"], "consumed")
            self.assertIn(fallback_id, face["stale_manifest_entries"])
            self.assertTrue(
                any("unit_manifest_stale_entries" in i for i in face["issues"]),
                f"expected a stale-entry issue, got {face['issues']}",
            )
            self.assertEqual(face["confirmed_count"], 0,
                             "stale entries must not count as confirmed anchoring")

    def test_preview_read_only_with_manifest(self):
        """Regression: consuming the manifest performs NO writes (no runtime,
        no archive, evidence untouched, manifest bytes untouched)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root, tracker=PROSE_TRACKER)
            ids = _derived_ids(root)
            self.assertTrue(_approve(root, ids[0], task_id="adapters/chrys")["recorded"])
            manifest_before = _manifest_path(root).read_bytes()
            evidence_before = (root / ".governance" / "evidence-log.md").read_bytes()

            lm.preview_migration(target_root=str(root))

            self.assertFalse((root / ".governance" / "flow-unit-runtime.json").is_file())
            self.assertFalse((root / ".governance" / "archive").is_dir())
            self.assertEqual(
                (root / ".governance" / "evidence-log.md").read_bytes(), evidence_before
            )
            self.assertEqual(_manifest_path(root).read_bytes(), manifest_before)

    def test_preview_legacy_shape_preserved(self):
        """Regression: the legacy preview keys survive alongside the FEAT-070
        face (backward compatibility of the dry-run contract)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)

            preview = lm.preview_migration(target_root=str(root))

            for key in ("command", "mode", "dry_run", "write_operations",
                        "validation_issues", "no_overclaim_boundaries",
                        "migration_plan", "plan_hash", "v2_validation_issues"):
                self.assertIn(key, preview)
            self.assertIn("unit_manifest", preview)
            self.assertIn("unit_manifest_ambiguity_count", preview)


# ═══════════════════════════════════════════════════════════════════════════
# CLI surface — record actions (flag family extension)
# ═══════════════════════════════════════════════════════════════════════════


class TestCliRecordSurface(unittest.TestCase):
    """FEAT-070 CLI: --record-unit-approval / --record-unit-block dispatch."""

    def test_cli_record_approval_roundtrip(self):
        """Branch: CLI approval → exit 0, recorded true, manifest on disk."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]

            completed = subprocess.run(
                [sys.executable, str(Path(lm.__file__)),
                 "--target", str(root),
                 "--record-unit-approval",
                 "--approve-unit", unit_id,
                 "--approve-task", "adapters/chrys",
                 "--approve-evidence", "structural fact: adapters/chrys/ exists",
                 "--approve-reviewer", "cli-reviewer",
                 "--repo-version", "1.2.3"],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(completed.returncode, 0,
                             completed.stdout + completed.stderr)
            output = json.loads(completed.stdout)
            self.assertTrue(output["recorded"])
            self.assertEqual(output["manifest_revision"], 1)
            self.assertTrue(_manifest_path(root).is_file())
            # Content checks (not wall-clock): elapsed_ms present + numeric.
            self.assertIsInstance(output.get("elapsed_ms"), int)

    def test_cli_record_block_roundtrip_and_missing_args_refusal(self):
        """Branches: CLI block records; missing required flag → exit 1 with a
        refused_reason naming the missing field."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root)
            unit_id = _derived_ids(root)[0]

            ok = subprocess.run(
                [sys.executable, str(Path(lm.__file__)),
                 "--target", str(root),
                 "--record-unit-block",
                 "--approve-unit", unit_id,
                 "--block-reason", "ambiguous: multiple candidates",
                 "--approve-reviewer", "cli-reviewer",
                 "--repo-version", "1.2.3"],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            self.assertTrue(json.loads(ok.stdout)["recorded"])

            bad = subprocess.run(
                [sys.executable, str(Path(lm.__file__)),
                 "--target", str(root),
                 "--record-unit-block",
                 "--approve-unit", unit_id,
                 "--block-reason", "missing repo version",
                 "--approve-reviewer", "cli-reviewer"],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(bad.returncode, 1)
            output = json.loads(bad.stdout)
            self.assertFalse(output["recorded"])
            self.assertIn("repo_version", output["refused_reason"])

    def test_cli_record_multi_unit_refused(self):
        """Branch: record mode takes EXACTLY ONE --approve-unit (逐条
        confirmation) — a multi-unit record attempt exits 1."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_host(root, tracker=PROSE_TRACKER)
            ids = _derived_ids(root)
            self.assertEqual(len(ids), 2, "probe fixture invariant")

            completed = subprocess.run(
                [sys.executable, str(Path(lm.__file__)),
                 "--target", str(root),
                 "--record-unit-approval",
                 "--approve-unit", ids[0],
                 "--approve-unit", ids[1],
                 "--approve-task", "t",
                 "--approve-evidence", "e",
                 "--approve-reviewer", "r",
                 "--repo-version", "1.2.3"],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(completed.returncode, 1)
            output = json.loads(completed.stdout)
            self.assertFalse(output["recorded"])
            self.assertIn("exactly ONE unit", output["refused_reason"])
            self.assertFalse(_manifest_path(root).is_file(),
                             "a multi-unit refusal must not create a manifest")


if __name__ == "__main__":
    unittest.main()
