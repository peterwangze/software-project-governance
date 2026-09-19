"""FEAT-050 (0.85.0, DEC-211③) — the resident injection budget is a HARD gate.

The slice-A relaxed window (review-FEAT-039 P3-8, accepted by DEC-210) shipped
the resident tier as ADVISORY because the standard/strict entry templates
exceeded 6K tokens. FEAT-041 slimmed them under it (EVD-1104 baseline:
lightweight 4,216 / standard 5,694 / strict 5,966 — all ≤ 6,000), so FEAT-050
flips the resident gate posture to ``hard``: an over-budget resident set is
now an issue + FAIL, and any future growth fails closed instead of rebounding
silently (AUDIT-154 §5: "预算不守护则瘦身必然回弹").

This suite pins the FLIP and its four contracted consequences:

1. an over-budget resident set moves the verdict to FAIL — exercised by
   lowering ``budget_tokens`` against the real tree (the derived-threshold
   pattern test_verify_workflow.py already uses; no template is rewritten),
   with an advisory-posture counterfactual proving the verdict motion is
   caused by the gate posture alone;
2. all three live profiles still PASS at the default budget (zero-breakage
   regression: the tree carries zero over-budget surfaces; the strict
   profile's 34-token margin is guarded by the hard gate itself);
3. the skill/command tiers stay report-only (FEAT-050 does NOT fold the ⑧
   ticket's separate budget face into the resident gate);
4. the advisory→hard posture flip has a negative guard — a revert to
   ``advisory`` reddens the suite;

plus review-FEAT-039-CODE-R1 P3-3 (deferred there as untested, landed here by
the DEC-211③ same-commit discipline): ``injection_budget_tier_gate`` fails
closed to ``hard`` for any tier missing from the policy table.

FEAT-052 (batch 2.4 ⑧, 0.85.0 — ``Feat052SkillTierBudgetTests`` below) adds
the skill tier's OWN budget face: a 16,000-token ``budget_tokens`` field on
the explicit ``report-only`` policy row (measured baseline 14,456 — the
deliberate growth of FEAT-041's progressive-disclosure migration). The
posture stays report-only and the row stays data; flipping it to ``hard`` is
a 0.86.0+ candidate to be carried via FEAT-047's BaselineMetadata. Review
cleanup carried in the same batch (review-FEAT-050-CODE-R0 F-2): the stale
``test_budget_tier_is_not_a_hard_fail_while_advisory`` in
test_verify_workflow.py was REMOVED — its FAIL-motion face lives in
``test_report_separates_gated_from_report_only_over_budget`` (same file) and
in this suite's #6/#7, its posture face in this suite's #1/#2; F-3's stale
docstring on ``test_live_resident_baseline_is_within_budget`` was refreshed.
"""

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

from checks import injection_budget as ib


class Feat050ResidentHardGateTests(unittest.TestCase):
    """FEAT-050: resident over-budget is a verdict-moving FAIL, not advisory."""

    # ── ④ posture flip — negative guard (防回退) ────────────────────────────

    def test_resident_tier_gate_is_hard(self):
        """The posture flip itself: resident must be ``hard``.

        The gate posture is data (``BUDGET_TIER_POLICY``), so a silent revert
        to ``advisory`` — the slice-A stance — would re-open the gate and let
        over-budget growth be reported instead of blocking. This assertion is
        the tripwire for DEC-211③'s fail-closed promise.
        """
        self.assertEqual(ib.BUDGET_TIER_POLICY["resident"]["gate"], "hard")
        self.assertEqual(ib.injection_budget_tier_gate("resident"), "hard")

    def test_advisory_gone_from_the_policy_table(self):
        """No tier may carry the advisory posture anymore (slice-A closed).

        An ``advisory`` row would silently downgrade a tier's over-budget
        condition back to a reportable note; if a future tier genuinely needs
        the posture it must be added deliberately — with this test updated in
        the same commit — not by leaving a stale advisory row behind.
        """
        gates = {name: row["gate"]
                 for name, row in ib.BUDGET_TIER_POLICY.items()}
        self.assertNotIn("advisory", gates.values(),
                         f"advisory posture must stay retired, got {gates}")

    def test_unknown_tier_gate_defaults_hard_p3_3(self):
        """P3-3 (review-FEAT-039-CODE-R1 §二 — deferred there, landed here):
        a tier missing from ``BUDGET_TIER_POLICY`` must default to ``hard``
        (fail-closed), so an undeclared tier can never silently measure-only.
        R0 proposed exactly this assertion; R1 recorded it as unfixed with no
        tracking face (F-3); DEC-211③ carries it into the hard-flip commit.
        """
        self.assertEqual(ib.injection_budget_tier_gate("unknown"), "hard")
        self.assertEqual(ib.injection_budget_tier_gate(""), "hard")
        self.assertEqual(ib.injection_budget_tier_gate("not-a-tier"), "hard")

    # ── ③ ⑧-ticket boundary — skill/command stay report-only ───────────────

    def test_skill_and_command_stay_report_only(self):
        """FEAT-050 scope boundary (triage reason): the skill tier — whose
        entry-skill surface is the largest single surface — and the command
        tier must NOT be folded into the resident hard gate; their budget
        face is a separate scheduled task. Flipping either to ``hard`` would
        FAIL the gate on surfaces this task never scoped."""
        self.assertEqual(ib.BUDGET_TIER_POLICY["skill"]["gate"], "report-only")
        self.assertEqual(ib.BUDGET_TIER_POLICY["command"]["gate"],
                         "report-only")
        self.assertEqual(ib.injection_budget_tier_gate("skill"), "report-only")
        self.assertEqual(ib.injection_budget_tier_gate("command"),
                         "report-only")

    def test_skill_and_command_overrun_never_becomes_an_issue(self):
        """③ Behavior face of report-only: with every tier driven over budget
        at once, the issues may name the resident tier (hard) but never the
        skill/command surfaces — a measurement overrun stays out of the
        verdict path (AUDIT-154 §8 keeps the static budget separate).
        FEAT-052 rebase: the skill tier now verdicts against its OWN 16,000
        line, so the overrun is reproduced by lowering that policy line for
        the duration of the call (try/finally restore)."""
        skill_policy = ib.BUDGET_TIER_POLICY["skill"]
        saved_skill_budget = skill_policy["budget_tokens"]
        skill_policy["budget_tokens"] = 1000
        try:
            result = ib.check_injection_budget(profile="lightweight",
                                               budget_tokens=1)
        finally:
            skill_policy["budget_tokens"] = saved_skill_budget
        self.assertIn("skill", result["over_budget_tiers"])
        self.assertIn("command", result["over_budget_tiers"])
        self.assertNotIn("skill", result["gated_over_budget_tiers"])
        self.assertNotIn("command", result["gated_over_budget_tiers"])
        joined = " ".join(result["issues"])
        self.assertIn("'resident' tier over budget", joined)
        self.assertNotIn("entry-skill", joined)
        self.assertNotIn("command-doc", joined)
        self.assertEqual(result["verdict"], "FAIL")

    # ── ① over-budget fixture → FAIL verdict 动位 ──────────────────────────

    def test_over_budget_resident_moves_verdict_to_fail(self):
        """① The hard-gate consequence: an over-budget resident set yields an
        explicit ``hard gate`` issue + FAIL. The over-budget condition is
        produced by lowering ``budget_tokens`` one token below the real
        resident price (derived-threshold pattern — no template rewritten)."""
        baseline = ib.check_injection_budget(profile="lightweight")
        resident_tokens = baseline["tiers"]["resident"]["tokens"]
        derived = ib.check_injection_budget(profile="lightweight",
                                            budget_tokens=resident_tokens - 1)
        self.assertIn("resident", derived["over_budget_tiers"])
        self.assertIn("resident", derived["gated_over_budget_tiers"])
        self.assertTrue(derived["issues"])
        self.assertIn("hard gate", " ".join(derived["issues"]))
        self.assertEqual(derived["verdict"], "FAIL")

    def test_verdict_motion_is_caused_by_the_gate_posture_alone(self):
        """① Counterfactual: the SAME over-budget condition under the retired
        advisory posture yields ADVISORY with zero issues — proving the FAIL
        comes from the posture flip (FEAT-050), not from the measurement."""
        baseline = ib.check_injection_budget(profile="lightweight")
        resident_tokens = baseline["tiers"]["resident"]["tokens"]
        policy = ib.BUDGET_TIER_POLICY["resident"]
        saved = policy["gate"]
        policy["gate"] = "advisory"
        try:
            counterfactual = ib.check_injection_budget(
                profile="lightweight", budget_tokens=resident_tokens - 1)
            self.assertIn("resident", counterfactual["over_budget_tiers"])
            self.assertIn("resident",
                          counterfactual["gated_over_budget_tiers"])
            self.assertEqual(counterfactual["issues"], [])
            self.assertEqual(counterfactual["verdict"], "ADVISORY")
        finally:
            policy["gate"] = saved
        self.assertEqual(policy["gate"], "hard")

    def test_cli_prints_failed_and_exits_1_for_over_budget_resident(self):
        """① CLI face: the over-budget resident set prints ``FAILED`` with the
        ``hard gate`` issue, and ``--fail-on-issues`` turns it into exit 1 —
        the CI-wirable form of the hard gate (advisory used to stay exit-0)."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ib.cmd_check_injection_budget(SimpleNamespace(
                budget_tokens=1,
                profile=ib.INJECTION_BUDGET_DEFAULT_PROFILE,
                format="text", fail_on_issues=False))
        out = buf.getvalue()
        self.assertIn("Result: FAILED", out)
        self.assertIn("hard gate", out)
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(io.StringIO()):
                ib.cmd_check_injection_budget(SimpleNamespace(
                    budget_tokens=1,
                    profile=ib.INJECTION_BUDGET_DEFAULT_PROFILE,
                    format="text", fail_on_issues=True))
        self.assertEqual(ctx.exception.code, 1)

    # ── ② real-tree regression — three profiles PASSED under the hard gate ─

    def test_all_three_profiles_pass_at_default_budget(self):
        """② Zero-breakage regression: the live tree carries zero over-budget
        surfaces (EVD-1104: 4,216 / 5,694 / 5,966 — post-FEAT-041 baseline),
        so flipping the resident gate to ``hard`` keeps every profile at a
        plain PASS. The strict profile's 34-token margin now sits behind the
        hard gate: any growth beyond it fails closed."""
        for profile in ib.INJECTION_BUDGET_PROFILES:
            with self.subTest(profile=profile):
                result = ib.check_injection_budget(profile=profile)
                self.assertLessEqual(result["tokens"],
                                     ib.INJECTION_BUDGET_TOKENS)
                self.assertEqual(result["issues"], [])
                self.assertEqual(result["gated_over_budget_tiers"], [])
                self.assertEqual(result["verdict"], "PASS")


class Feat052SkillTierBudgetTests(unittest.TestCase):
    """FEAT-052: the skill tier's own 16,000-token budget line — report-only.

    Complementary to (not a repeat of) the ③ pins above: #4 pins the POSTURE
    (gate == report-only), #5 pins skill staying out of the issue path while
    the RESIDENT tier simultaneously fails at a global budget=1. These two
    pin the INDEPENDENT LINE itself: its value, its per-tier verdicting, and
    the pure-PASS behavior when ONLY the skill line is crossed.
    """

    def test_skill_tier_carries_its_own_16000_budget_line(self):
        """The independent line exists as data: 16,000 tokens on the explicit
        ``report-only`` row (FEAT-052; measured baseline 14,456 — FEAT-041's
        progressive-disclosure growth), and the per-tier verdict actually
        uses it — the live skill tier (14,456) is within ITS OWN budget even
        though it exceeds the resident 6K, so the tier neither over-budgets
        nor prints an overrun note. Flipping the posture stays a 0.86.0+
        candidate via FEAT-047's BaselineMetadata, NOT this row."""
        self.assertEqual(ib.BUDGET_TIER_POLICY["skill"]["budget_tokens"],
                         16000)
        self.assertEqual(ib.BUDGET_TIER_POLICY["skill"]["gate"],
                         "report-only")
        result = ib.check_injection_budget(profile="lightweight")
        skill = result["tiers"]["skill"]
        self.assertEqual(skill["budget_tokens"], 16000)
        self.assertFalse(skill["over_budget"])
        self.assertNotIn("note", skill)
        self.assertNotIn("skill", result["over_budget_tiers"])
        skill_row = next(s for s in result["surfaces"]
                         if s["name"] == "entry-skill")
        self.assertEqual(skill_row["budget_tokens"], 16000)
        self.assertEqual(skill_row["status"], "ok")
        self.assertEqual(result["verdict"], "PASS")

    def test_skill_overrun_stays_out_of_the_verdict_path_at_its_own_line(self):
        """Behavior face of the independent line: when ONLY the skill line is
        crossed (derived-threshold pattern — the policy line lowered one
        token below the measured 14,456; no template rewritten), the overrun
        is measured and rendered as report-only but produces NO issue and
        does NOT move the verdict — the resident set is within budget, so
        the gate stays a plain PASS. This is the pure-skill counterpart of
        #5 (where the resident tier fails simultaneously): the issue channel
        and the verdict channel are both closed to a report-only overrun."""
        baseline = ib.check_injection_budget(profile="lightweight")
        skill_tokens = baseline["tiers"]["skill"]["tokens"]
        skill_policy = ib.BUDGET_TIER_POLICY["skill"]
        saved = skill_policy["budget_tokens"]
        skill_policy["budget_tokens"] = skill_tokens - 1
        try:
            result = ib.check_injection_budget(profile="lightweight")
        finally:
            skill_policy["budget_tokens"] = saved
        self.assertEqual(skill_policy["budget_tokens"], 16000)
        self.assertIn("skill", result["over_budget_tiers"])
        self.assertNotIn("skill", result["gated_over_budget_tiers"])
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["verdict"], "PASS")


if __name__ == "__main__":
    unittest.main()
