"""FEAT-088 (F-A3) — committed regression tests for the exploration-channel guard.

The guard (``check_exploration_channels``, FEAT-088 / F-A3) closes the
REVIEW-FEAT-086-DESIGN-R0 F-A3 gap: the dsh ``exploration_channels`` native
declarations were backed by live-session self-attestation while the sibling
adapters anchor their channel evidence to dated E2E records. These tests
follow the QuoteSyncGuardTests sandbox form (FIX-432 F-1): the guard's
canonical surfaces (six adapter manifests + the dated evidence document the
dsh anchors cite) are copied from the real repo into a throwaway temp ROOT,
mutated per case, and removed afterwards — the real repo is never touched.
Pinned contract:

- positive: an unmutated surface set yields zero issues (no-false-positive
  baseline over the current repo shape; the clock-relative staleness
  advisory is pinned structurally — none while fresh, EXP-03-only once old);
- F-A3 negative (anchor missing): an enrolled (dsh) native channel losing
  both its structured ``verified_on`` and every inline date in the evidence
  prose flags exactly one issue naming that manifest and channel, and the
  issue carries the honest-degradation advice (EXP-03);
- F-A3 negative (malformed date / dangling evidence_ref / uncorroborated
  date / prose-structured drift): each flags its own issue;
- scoping (no retroactive FAIL): a non-enrolled adapter's native channel
  without any anchor stays silent, while a voluntarily-carried malformed
  anchor is still validated (forward-compatible generalization);
- convention compatibility: an inline prose date alone (the dated-E2E
  form codex/gemini use) satisfies the anchor requirement;
- structure: a missing channel declaration, an unknown status and an extra
  channel key are issues for any adapter;
- advisories: anchor staleness beyond the threshold is a WARN-only advisory
  (never an issue) with the EXP-03 degradation suggestion.
"""

from __future__ import annotations

import contextlib
import json
import shutil
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

_INFRA_DIR = Path(__file__).resolve().parent.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import verify_workflow as vw  # noqa: E402

_DSH_REL = "adapters/dsh/adapter-manifest.json"
_REVIEW_REL = "docs/reviews/review-FEAT-086-DESIGN-R0.md"


@contextlib.contextmanager
def _governance_temp_dir(prefix="feat088-guard-"):
    # Same FIX-404 sandbox-safe temp dir the sibling suites use (a 0o700
    # mkdtemp denies writes from this very process under the UAC-filtered
    # token of the DSH sandbox).
    import tempfile
    import uuid

    path = Path(tempfile.gettempdir()) / (prefix + uuid.uuid4().hex[:12])
    path.mkdir()
    try:
        yield str(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


class ExplorationChannelGuardTests(unittest.TestCase):
    """FEAT-088 F-A3 — sandboxed positive/negative pins for the guard."""

    maxDiff = None

    def _materialize_surfaces(self, root):
        """Copy the guard's canonical surfaces from the real repo into the
        isolated ROOT (real files are only ever read)."""
        rels = tuple(vw.QUOTE_SYNC_ADAPTER_MANIFESTS) + (_REVIEW_REL,)
        for rel in rels:
            dst = Path(root) / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(vw.ROOT / rel, dst)

    def _run_guard(self, root):
        with patch.object(vw, "ROOT", Path(root)):
            return vw.check_exploration_channels()

    def _read(self, root, rel):
        return (Path(root) / rel).read_text(encoding="utf-8")

    def _write_payload(self, root, rel, payload):
        (Path(root) / rel).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8")

    def _payload(self, root, rel=_DSH_REL):
        return json.loads(self._read(root, rel))

    # ── positive baseline ────────────────────────────────────────────────

    def test_no_drift_yields_zero_issues(self):
        # The shipped repo (dsh anchored 2026-10-04, corroborated by the
        # cited review document) must not trip the guard's FAIL face. The
        # advisory face is clock-relative (the anchor ages), so it is pinned
        # structurally: either no advisories while fresh, or — once the
        # anchor is older than the threshold — only EXP-03 advisories.
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            result = self._run_guard(td)
        self.assertEqual(result["issues"], [], result["issues"])
        self.assertTrue(result["pass"])
        self.assertEqual(result["dated_anchor_adapters"], ["dsh"])
        age = result["adapters"]["dsh"]["native_anchored"]["discover"]["age_days"]
        if age <= vw.CHANNEL_EVIDENCE_STALE_DAYS:
            self.assertEqual(result["advisories"], [])
        else:
            self.assertTrue(result["advisories"])
            self.assertTrue(all("EXP-03" in advisory
                                for advisory in result["advisories"]))

    # ── F-A3 negatives: the anchor requirement ───────────────────────────

    def test_enrolled_native_channel_without_any_anchor_is_flagged(self):
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            payload = self._payload(td)
            discover = payload["exploration_channels"]["channels"]["discover"]
            del discover["verified_on"]
            del discover["evidence_ref"]
            discover["evidence"] = "dsh ships a native web_search tool; used by live sessions."
            self._write_payload(td, _DSH_REL, payload)
            result = self._run_guard(td)
        self.assertEqual(len(result["issues"]), 1, result["issues"])
        issue = result["issues"][0]
        self.assertIn("adapters/dsh/adapter-manifest.json", issue)
        self.assertIn("discover", issue)
        self.assertIn("dated evidence anchor", issue)
        self.assertIn("EXP-03", issue)  # the honest-degradation advice rides along

    def test_malformed_verified_on_is_flagged(self):
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            payload = self._payload(td)
            discover = payload["exploration_channels"]["channels"]["discover"]
            discover["verified_on"] = "2026-02-31"  # real form, not a real date
            # Strip the prose date too: with an inline date present the
            # anchor requirement is legitimately satisfied through prose and
            # only the malformed-structured-field issue fires — pinned by the
            # next case; this one pins the no-fallback-anywhere shape.
            discover["evidence"] = "dsh ships a native web_search tool; used by live sessions."
            self._write_payload(td, _DSH_REL, payload)
            result = self._run_guard(td)
        self.assertEqual(len(result["issues"]), 2, result["issues"])
        self.assertTrue(any("not a valid YYYY-MM-DD" in issue
                            for issue in result["issues"]))
        self.assertTrue(any("dated evidence anchor" in issue
                            for issue in result["issues"]))

    def test_malformed_structured_date_with_prose_date_flags_only_the_form(self):
        # A malformed verified_on is an issue even when the prose date could
        # have carried the anchor: two forms of one fact, one of them broken.
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            payload = self._payload(td)
            payload["exploration_channels"]["channels"]["discover"]["verified_on"] = "2026-13-01"
            self._write_payload(td, _DSH_REL, payload)
            result = self._run_guard(td)
        self.assertEqual(result["issues"], [
            "exploration channels: adapters/dsh/adapter-manifest.json "
            "channels.discover.verified_on='2026-13-01' is not a valid "
            "YYYY-MM-DD calendar date"], result["issues"])

    def test_dangling_evidence_ref_is_flagged(self):
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            payload = self._payload(td)
            payload["exploration_channels"]["channels"]["inspect"]["evidence_ref"] = \
                "docs/reviews/does-not-exist.md"
            self._write_payload(td, _DSH_REL, payload)
            result = self._run_guard(td)
        self.assertEqual(len(result["issues"]), 1, result["issues"])
        self.assertIn("dangling dated anchor", result["issues"][0])
        self.assertIn("does-not-exist.md", result["issues"][0])

    def test_uncorroborated_anchor_date_is_flagged(self):
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            payload = self._payload(td)
            consult = payload["exploration_channels"]["channels"]["consult"]
            # A real calendar date that the cited review document does not
            # carry: the dated claim is not corroborated by its own source.
            consult["verified_on"] = "2026-01-01"
            consult["evidence"] = consult["evidence"].replace("2026-10-04", "2026-01-01")
            self._write_payload(td, _DSH_REL, payload)
            result = self._run_guard(td)
        self.assertEqual(len(result["issues"]), 1, result["issues"])
        self.assertIn("not corroborated", result["issues"][0])
        self.assertIn("2026-01-01", result["issues"][0])

    def test_prose_structured_date_drift_is_flagged(self):
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            payload = self._payload(td)
            validate = payload["exploration_channels"]["channels"]["validate"]
            validate["evidence"] = validate["evidence"].replace(
                "2026-10-04", "2026-03-03")
            self._write_payload(td, _DSH_REL, payload)
            result = self._run_guard(td)
        self.assertEqual(len(result["issues"]), 1, result["issues"])
        self.assertIn("must not drift", result["issues"][0])
        self.assertIn("2026-03-03", result["issues"][0])

    # ── scoping: no retroactive FAIL on the not-yet-enrolled five ────────

    def test_non_enrolled_native_channel_without_anchor_stays_silent(self):
        claude_rel = "adapters/claude/adapter-manifest.json"
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            result = self._run_guard(td)
            claude_face = result["adapters"]["claude"]
            self.assertFalse(claude_face["dated_anchor_required"])
            self.assertEqual(result["issues"], [])
            # And the guard's own enrollment list is the declared scope.
            self.assertNotIn("claude", result["dated_anchor_adapters"])
            _ = claude_rel  # the claude manifest exists unmutated in the sandbox

    def test_voluntarily_carried_malformed_anchor_is_still_validated(self):
        claude_rel = "adapters/claude/adapter-manifest.json"
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            payload = self._payload(td, claude_rel)
            payload["exploration_channels"]["channels"]["inspect"]["verified_on"] = "yesterday"
            self._write_payload(td, claude_rel, payload)
            result = self._run_guard(td)
        self.assertEqual(len(result["issues"]), 1, result["issues"])
        self.assertIn("adapters/claude/adapter-manifest.json", result["issues"][0])
        self.assertIn("not a valid YYYY-MM-DD", result["issues"][0])

    def test_inline_prose_date_alone_satisfies_the_anchor(self):
        # The dated-E2E convention codex/gemini use (dates in prose, no
        # structured field) is an accepted anchor form.
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            payload = self._payload(td)
            discover = payload["exploration_channels"]["channels"]["discover"]
            del discover["verified_on"]
            del discover["evidence_ref"]
            discover["evidence"] = (
                "dsh ships a native web_search tool; verified in a live "
                "session on 2026-10-04.")
            self._write_payload(td, _DSH_REL, payload)
            result = self._run_guard(td)
        self.assertEqual(result["issues"], [], result["issues"])
        face = result["adapters"]["dsh"]["native_anchored"]["discover"]
        self.assertTrue(face["inline_date_only"])

    # ── structure rules (all six adapters) ───────────────────────────────

    def test_missing_channel_declaration_is_flagged(self):
        gemini_rel = "adapters/gemini/adapter-manifest.json"
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            payload = self._payload(td, gemini_rel)
            del payload["exploration_channels"]["channels"]["validate"]
            self._write_payload(td, gemini_rel, payload)
            result = self._run_guard(td)
        self.assertEqual(len(result["issues"]), 1, result["issues"])
        self.assertIn("missing channel", result["issues"][0])
        self.assertIn("validate", result["issues"][0])

    def test_unknown_status_vocabulary_is_flagged(self):
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            payload = self._payload(td)
            payload["exploration_channels"]["channels"]["inspect"]["status"] = "super"
            self._write_payload(td, _DSH_REL, payload)
            result = self._run_guard(td)
        self.assertTrue(any("outside the M10.3 vocabulary" in issue
                            for issue in result["issues"]), result["issues"])

    def test_extra_channel_key_is_flagged(self):
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            payload = self._payload(td)
            payload["exploration_channels"]["channels"]["ruminate"] = {
                "status": "native", "mapping": "x", "evidence": "y",
                "verified_on": "2026-10-04",
                "evidence_ref": _REVIEW_REL,
            }
            self._write_payload(td, _DSH_REL, payload)
            result = self._run_guard(td)
        self.assertTrue(any("unknown to M10.3" in issue and "ruminate" in issue
                            for issue in result["issues"]), result["issues"])

    def test_unreadable_manifest_fails_closed(self):
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            (Path(td) / _DSH_REL).write_text("{ not json", encoding="utf-8")
            result = self._run_guard(td)
        self.assertTrue(any("unreadable or invalid JSON" in issue
                            for issue in result["issues"]), result["issues"])

    # ── advisories: staleness is WARN-only, with the EXP-03 advice ───────

    def test_stale_anchor_is_an_advisory_never_an_issue(self):
        old = (date.today() - timedelta(days=vw.CHANNEL_EVIDENCE_STALE_DAYS + 40))
        old_text = old.strftime("%Y-%m-%d")
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            # The sandbox review doc must corroborate the old date for the
            # corroboration probe to stay quiet (a dated claim and its cited
            # source move together, as they would in a real re-dating).
            review = Path(td) / _REVIEW_REL
            review.write_text(
                review.read_text(encoding="utf-8") + f"\nanchor-corroboration {old_text}\n",
                encoding="utf-8")
            payload = self._payload(td)
            for name, channel in payload["exploration_channels"]["channels"].items():
                channel["verified_on"] = old_text
                channel["evidence"] = channel["evidence"].replace("2026-10-04", old_text)
            self._write_payload(td, _DSH_REL, payload)
            result = self._run_guard(td)
        self.assertEqual(result["issues"], [], result["issues"])
        self.assertTrue(result["advisories"], "a >threshold-old anchor must advise")
        self.assertTrue(all("EXP-03" in advisory for advisory in result["advisories"]))
        self.assertTrue(result["pass"], "staleness alone must not fail the guard")

    def test_anchor_face_books_the_age_it_advises_on(self):
        # The positive baseline already pins issue-freedom; this case pins
        # the per-channel bookkeeping the advisory machinery reads from.
        with _governance_temp_dir() as td:
            self._materialize_surfaces(td)
            result = self._run_guard(td)
        face = result["adapters"]["dsh"]["native_anchored"]["discover"]
        self.assertEqual(face["verified_on"], "2026-10-04")
        self.assertFalse(face["inline_date_only"])
        self.assertIsInstance(face["age_days"], int)
        self.assertEqual(face["age_days"],
                         (date.today() - date(2026, 10, 4)).days)


class CheckCrossReferencesCarrierTests(unittest.TestCase):
    """The guard rides the check-cross-references surface (FEAT-088 wiring)."""

    def test_cross_references_result_carries_the_channel_face(self):
        with _governance_temp_dir() as td:
            self.assertTrue(hasattr(vw, "check_exploration_channels"))
            with patch.object(vw, "ROOT", Path(td)):
                result = vw.check_cross_references()
        self.assertIn("exploration_channels", result)
        face = result["exploration_channels"]
        self.assertIn("issues", face)
        self.assertIn("advisories", face)
        self.assertIn("probe_layering", face)
        # Sandbox root has no manifests: fail-closed issues, disclosed under
        # the guard's own key (never smeared into the dangling/cycle faces).
        self.assertTrue(face["issues"])
        self.assertTrue(all("exploration channels:" in issue
                            for issue in face["issues"]))
        self.assertTrue(all("exploration channels:" not in issue
                            for issue in result.get("quote_sync", [])))

    def test_probe_layering_discloses_the_not_probeable_boundary(self):
        result = vw.check_exploration_channels()
        layering = result["probe_layering"]
        self.assertIn("web_search / route_agent", layering["not_probeable"])
        self.assertIn("NOT probed", layering["not_probeable"])
        self.assertIn("read-only", layering["feasible_probe"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
