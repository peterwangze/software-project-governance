"""FEAT-047 — BaselineMetadata provenance tests (version-plan-0.86.0 §2 批 1).

TDD order: this file was written and run RED (module absent) BEFORE
``infra/baseline_metadata.py`` existed. Red-phase matrix (task acceptance):

  1. registration refuses any metadata missing one of the seven provenance
    要素 (arch round-2 §4) — 14 required fields, each negative-controlled;
  2. an expired baseline evaluates ``not_evaluable`` and the continuation
     axis splits by ``policy_class`` (release/safety/data_integrity → block;
     trend/pilot → advisory + re-measure action);
  3. fresh-but-different-caliber observations evaluate ``not_evaluable``
     (never ``pass``) — arch round-2 §4: 新鲜但口径不同的数字同样不能比较;
  4. a deterministically detectable contradiction (threshold below the
     frozen floor of the caliber — the EVD-1100 "85% 数学不可达" shape)
     reports a gate-configuration-error diagnostic, not a user failure;
  5. replay idempotency: registering identical metadata twice writes once.

Guard tests (机录写入器 DoD 0/3/4/7, architecture-evolution §4): untrusted
input type bounds, explicit UTF-8 round trip (FIX-278 caliber), atomic
replace + write-after-read self-check, tampered scope digest refused,
unknown schema version refused, CLI exit-code face pinned.

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_baseline_metadata.py" -v
"""

import argparse
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest import mock

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import baseline_metadata as bm  # noqa: E402
import contracts as c  # noqa: E402


def _valid_kwargs(**overrides):
    """A fully valid BaselineMetadata kwargs set (injection-budget stock row).

    The payload is the stock registration the task pins: injection-budget
    6,000 gate, baseline EVD-1104 (4,216 / 5,694 / 5,966, measured 2026-09-19,
    threshold basis DEC-210/211, expiry = SKILL version bump or any of the
    six template surfaces' SHA change).
    """
    kwargs = dict(
        gate_id="injection-budget",
        value=4216,
        unit="tokens",
        measured_at="2026-09-19",
        measurement_command=(
            "verify_workflow.py check-injection-budget --profile lightweight"),
        instrument_version="check-injection-budget@0.85.0",
        target_commit_digest="b717835",
        scope=("resident 注入模板集（INJECTION_BUDGET_SURFACES 六面清单锚，"
               "canonical 模板口径）"),
        numerator=("resident 注入 token 实测：lightweight 4,216 / "
                   "standard 5,694 / strict 5,966（EVD-1104 canonical 重测）"),
        denominator="INJECTION_BUDGET_TOKENS=6000 tokens（resident 硬门上限）",
        exclusions=("tool-return 预算面（bootstrap_aggregate."
                    "MAX_JSON_BYTES=8192B）单列；报告输出等非注入文本不计"),
        threshold_basis="DEC-210/211（≤6,000 出货姿态 + 批 2.3 翻 hard）",
        expiry_condition=("SKILL.md active_version bump 或模板六面"
                          "（INJECTION_BUDGET_SURFACES 锚）任一 SHA 变更"),
        source_evd="EVD-1104",
    )
    kwargs.update(overrides)
    return kwargs


@contextmanager
def _tmp_registry():
    """A fresh registry path in a per-test temp dir (never the repo's)."""
    with tempfile.TemporaryDirectory(prefix="feat047-") as name:
        yield Path(name) / "baselines.json"


@contextmanager
def _capture_stdio():
    buf_out, buf_err = io.StringIO(), io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = buf_out, buf_err
    try:
        yield buf_out, buf_err
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class BaselineMetadataConstructionTests(unittest.TestCase):
    """Red-phase 1: missing any required provenance element is refused."""

    def test_valid_construction_returns_all_fields(self):
        meta = bm.BaselineMetadata(**_valid_kwargs())
        self.assertEqual(meta.gate_id, "injection-budget")
        self.assertEqual(meta.value, 4216)
        self.assertEqual(meta.measured_at, "2026-09-19")
        self.assertIsNone(meta.max_age_days)

    def test_all_fourteen_required_fields_are_declared(self):
        self.assertEqual(
            len(bm.BASELINE_FIELDS), 14,
            "the provenance schema declares exactly the 14 task fields")
        seven = {
            "measured_at": "测量时间",
            "instrument_version": "测量器版本",
            "measurement_command": "来源命令",
            "target_commit_digest": "测量对象 commit/内容摘要",
            "scope": "范围", "numerator": "分子口径",
            "denominator": "分母口径", "exclusions": "排除规则",
            "threshold_basis": "阈值依据", "expiry_condition": "失效条件",
        }
        for field, label in seven.items():
            self.assertIn(field, bm.BASELINE_FIELDS,
                          f"provenance 要素缺失: {label}")

    def test_missing_each_required_field_is_refused(self):
        for field in bm.BASELINE_FIELDS:
            with self.subTest(field=field):
                kwargs = _valid_kwargs()
                del kwargs[field]
                with self.assertRaises(c.ContractViolation):
                    bm.BaselineMetadata(**kwargs)

    def test_blank_string_field_is_refused(self):
        for field in ("scope", "numerator", "denominator", "exclusions",
                      "threshold_basis", "expiry_condition", "source_evd"):
            with self.subTest(field=field):
                with self.assertRaises(c.ContractViolation):
                    bm.BaselineMetadata(**_valid_kwargs(**{field: "   "}))

    def test_untrusted_value_types_are_refused(self):
        for bad in (True, False, "4216", float("nan"), float("inf"),
                    float("-inf"), None):
            with self.subTest(value=bad):
                with self.assertRaises(c.ContractViolation):
                    bm.BaselineMetadata(**_valid_kwargs(value=bad))

    def test_bad_gate_id_form_is_refused(self):
        for bad in ("", "has space", "a/b", "a\\b", "-lead", None):
            with self.subTest(gate_id=bad):
                with self.assertRaises(c.ContractViolation):
                    bm.BaselineMetadata(**_valid_kwargs(gate_id=bad))

    def test_bad_commit_digest_is_refused(self):
        for bad in ("", "XYZabc1", "b71783", "b" * 65, "B717835"):
            with self.subTest(digest=bad):
                with self.assertRaises(c.ContractViolation):
                    bm.BaselineMetadata(**_valid_kwargs(
                        target_commit_digest=bad))

    def test_bad_measured_at_is_refused(self):
        for bad in ("", "not-a-date", "2026-13-40", "2026/09/19"):
            with self.subTest(measured_at=bad):
                with self.assertRaises(c.ContractViolation):
                    bm.BaselineMetadata(**_valid_kwargs(measured_at=bad))

    def test_bad_max_age_days_is_refused(self):
        for bad in (0, -1, True, float("nan"), "30", float("inf")):
            with self.subTest(max_age_days=bad):
                with self.assertRaises(c.ContractViolation):
                    bm.BaselineMetadata(**_valid_kwargs(max_age_days=bad))


class CaliberAndPolicyAxisTests(unittest.TestCase):
    """Scope fingerprint determinism + the policy_class → continuation axis."""

    def test_caliber_digest_is_deterministic_64hex(self):
        first = bm.caliber_digest("tokens", "n", "d", "none")
        second = bm.caliber_digest("tokens", "n", "d", "none")
        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{64}$")

    def test_caliber_digest_is_field_sensitive(self):
        base = bm.caliber_digest("tokens", "n", "d", "none")
        self.assertNotEqual(base, bm.caliber_digest("bytes", "n", "d", "none"))
        self.assertNotEqual(
            base, bm.caliber_digest("tokens", "n2", "d", "none"))
        self.assertNotEqual(
            base, bm.caliber_digest("tokens", "n", "d2", "none"))
        self.assertNotEqual(base, bm.caliber_digest("tokens", "n", "d", "x"))

    def test_policy_class_axis_splits_block_from_advisory(self):
        for policy in ("release", "safety", "data_integrity"):
            self.assertEqual(bm.continuation_for(policy), "block", policy)
        for policy in ("trend", "pilot"):
            self.assertEqual(bm.continuation_for(policy), "advisory", policy)

    def test_unknown_policy_class_fails_closed(self):
        with self.assertRaises(c.ContractViolation):
            bm.continuation_for("unknown")
        with self.assertRaises(c.ContractViolation):
            bm.continuation_for("")


class RegistrationStorageTests(unittest.TestCase):
    """Red-phase 5 + DoD 3/4: atomic write, replay idempotency, self-check."""

    def setUp(self):
        cm = _tmp_registry()
        self.registry = cm.__enter__()
        self.addCleanup(lambda: cm.__exit__(None, None, None))

    def test_first_register_writes_schema_version_one(self):
        result = bm.register(bm.BaselineMetadata(**_valid_kwargs()),
                             self.registry)
        self.assertEqual(result.status, "registered")
        raw = json.loads(self.registry.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], bm.REGISTRY_SCHEMA_VERSION)
        self.assertIn("injection-budget", raw["baselines"])
        self.assertEqual(
            raw["baselines"]["injection-budget"]["source_evd"], "EVD-1104")

    def test_replay_identical_metadata_writes_once(self):
        meta = bm.BaselineMetadata(**_valid_kwargs())
        bm.register(meta, self.registry)
        before = self.registry.read_bytes()
        stat_before = self.registry.stat().st_mtime_ns
        result = bm.register(meta, self.registry)
        self.assertEqual(result.status, "replay")
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertEqual(self.registry.stat().st_mtime_ns, stat_before)

    def test_same_gate_different_payload_is_conflict(self):
        bm.register(bm.BaselineMetadata(**_valid_kwargs()), self.registry)
        with self.assertRaises(bm.BaselineConflict):
            bm.register(bm.BaselineMetadata(**_valid_kwargs(value=9999)),
                        self.registry)

    def test_dry_run_writes_nothing(self):
        result = bm.register(bm.BaselineMetadata(**_valid_kwargs()),
                             self.registry, dry_run=True)
        self.assertTrue(result.dry_run)
        self.assertFalse(self.registry.exists())

    def test_utf8_chinese_round_trip_is_lossless(self):
        bm.register(bm.BaselineMetadata(**_valid_kwargs()), self.registry)
        raw = self.registry.read_text(encoding="utf-8")
        self.assertIn("注入模板集", raw)
        loaded = bm.load_registry(self.registry)
        row = loaded["baselines"]["injection-budget"]
        self.assertEqual(row["scope"], _valid_kwargs()["scope"])

    def test_corrupted_json_is_refused_not_swallowed(self):
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        self.registry.write_text("{broken", encoding="utf-8")
        with self.assertRaises(bm.BaselineMetadataError):
            bm.load_registry(self.registry)

    def test_tampered_scope_digest_is_refused(self):
        bm.register(bm.BaselineMetadata(**_valid_kwargs()), self.registry)
        raw = json.loads(self.registry.read_text(encoding="utf-8"))
        raw["baselines"]["injection-budget"]["scope_digest"] = "f" * 64
        self.registry.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        with self.assertRaises(bm.BaselineMetadataError):
            bm.load_registry(self.registry)

    def test_tampered_caliber_field_invalidates_stored_digest(self):
        # A hand-edited caliber without recomputing scope_digest = corrupted
        # storage (write-after-read self-check must refuse, never compare).
        bm.register(bm.BaselineMetadata(**_valid_kwargs()), self.registry)
        raw = json.loads(self.registry.read_text(encoding="utf-8"))
        raw["baselines"]["injection-budget"]["denominator"] = "edited"
        self.registry.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        with self.assertRaises(bm.BaselineMetadataError):
            bm.load_registry(self.registry)

    def test_unknown_schema_version_is_refused(self):
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        self.registry.write_text(
            json.dumps({"schema_version": 99, "baselines": {}}),
            encoding="utf-8")
        with self.assertRaises(bm.BaselineMetadataError) as ctx:
            bm.load_registry(self.registry)
        self.assertIn("schema_version", str(ctx.exception))

    def test_missing_registry_reads_as_empty(self):
        loaded = bm.load_registry(self.registry)
        self.assertEqual(loaded["schema_version"], 1)
        self.assertEqual(loaded["baselines"], {})


class EvaluationAxisTests(unittest.TestCase):
    """Red-phase 2/3/4: expiry, caliber mismatch, config contradiction."""

    def setUp(self):
        cm = _tmp_registry()
        self.registry = cm.__enter__()
        self.addCleanup(lambda: cm.__exit__(None, None, None))
        self.scope_digest = bm.caliber_digest(
            "tokens", _valid_kwargs()["numerator"],
            _valid_kwargs()["denominator"], _valid_kwargs()["exclusions"])
        bm.register(bm.BaselineMetadata(**_valid_kwargs()), self.registry)

    def _evaluate(self, **overrides):
        # Defaults describe a FRESH observation: caliber matches and the
        # event-based expiry observations equal the registered baseline, so
        # each test only overrides the axis it is pinning.
        kwargs = dict(
            gate_id="injection-budget",
            observed_value=5000,
            policy_class="release",
            threshold=6000,
            direction="upper",
            observed_unit="tokens",
            observed_scope_digest=self.scope_digest,
            current_instrument_version="check-injection-budget@0.85.0",
            current_target_digest="b717835",
            registry=self.registry,
            now=datetime(2026, 9, 20),
        )
        kwargs.update(overrides)
        return bm.evaluate(**kwargs)

    def _registry_with_age(self, max_age_days):
        """A second registry carrying the same row with a time-based expiry."""
        cm = _tmp_registry()
        registry = cm.__enter__()
        self.addCleanup(lambda: cm.__exit__(None, None, None))
        bm.register(
            bm.BaselineMetadata(**_valid_kwargs(max_age_days=max_age_days)),
            registry)
        return registry

    # ── red-phase 2: expired → not_evaluable, continuation splits ─────────

    def test_time_expired_baseline_is_not_evaluable(self):
        registry = self._registry_with_age(30)
        outcome = bm.evaluate(
            gate_id="injection-budget",
            observed_value=5000,
            policy_class="release",
            threshold=6000,
            direction="upper",
            observed_unit="tokens",
            observed_scope_digest=self.scope_digest,
            registry=registry,
            now=datetime(2027, 9, 30),  # measured 2026-09-19 + 30d ≪ now
        )
        self.assertEqual(outcome.evaluation, "not_evaluable")
        self.assertEqual(outcome.diagnostic.kind, "baseline_expired")

    def test_expired_release_gate_blocks_and_trend_gate_advises(self):
        registry = self._registry_with_age(30)
        common = dict(
            gate_id="injection-budget", threshold=6000, direction="upper",
            observed_unit="tokens", observed_scope_digest=self.scope_digest,
            registry=registry, now=datetime(2027, 9, 30))
        blocked = bm.evaluate(
            observed_value=5000, policy_class="release", **common)
        self.assertEqual(blocked.evaluation, "not_evaluable")
        self.assertEqual(blocked.continuation, "block")
        self.assertIn("waiver", blocked.diagnostic.action)

        advised = bm.evaluate(
            observed_value=5000, policy_class="trend", **common)
        self.assertEqual(advised.evaluation, "not_evaluable")
        self.assertEqual(advised.continuation, "advisory")
        self.assertIn("re-measure", advised.diagnostic.action)

    def test_fresh_within_age_is_evaluable(self):
        registry = self._registry_with_age(400)
        outcome = bm.evaluate(
            gate_id="injection-budget", observed_value=5000,
            policy_class="release", threshold=6000, direction="upper",
            observed_unit="tokens", observed_scope_digest=self.scope_digest,
            registry=registry, now=datetime(2026, 10, 10))
        self.assertEqual(outcome.evaluation, "pass")

    def test_instrument_version_change_is_not_evaluable(self):
        outcome = self._evaluate(
            current_instrument_version="check-injection-budget@0.86.0")
        self.assertEqual(outcome.evaluation, "not_evaluable")
        self.assertEqual(outcome.diagnostic.kind, "instrument_changed")

    def test_target_digest_change_is_not_evaluable(self):
        outcome = self._evaluate(current_target_digest="deadbeef")
        self.assertEqual(outcome.evaluation, "not_evaluable")
        self.assertEqual(outcome.diagnostic.kind, "target_changed")

    def test_matching_current_observation_keeps_baseline_live(self):
        outcome = self._evaluate(
            current_target_digest="b717835",
            current_instrument_version="check-injection-budget@0.85.0")
        self.assertEqual(outcome.evaluation, "pass")

    # ── red-phase 3: fresh but different caliber is never a pass ──────────

    def test_unit_mismatch_is_not_evaluable_not_pass(self):
        outcome = self._evaluate(observed_unit="bytes")
        self.assertEqual(outcome.evaluation, "not_evaluable")
        self.assertEqual(outcome.diagnostic.kind, "caliber_mismatch")

    def test_scope_digest_mismatch_is_not_evaluable_not_pass(self):
        outcome = self._evaluate(observed_scope_digest="a" * 64)
        self.assertEqual(outcome.evaluation, "not_evaluable")
        self.assertEqual(outcome.diagnostic.kind, "caliber_mismatch")

    def test_missing_baseline_is_not_evaluable(self):
        outcome = self._evaluate(gate_id="no-such-gate")
        self.assertEqual(outcome.evaluation, "not_evaluable")
        self.assertEqual(outcome.diagnostic.kind, "baseline_missing")

    # ── P1-1 ①: comparison-side caliber is required, never silently skipped

    def test_omitted_observed_unit_is_caller_bug(self):
        with self.assertRaises(c.ContractViolation):
            self._evaluate(observed_unit=None)

    def test_omitted_scope_digest_is_caller_bug(self):
        with self.assertRaises(c.ContractViolation):
            self._evaluate(observed_scope_digest=None)

    def test_baseline_missing_still_reports_before_required_observations(
            self):
        # Layering order: a missing baseline is the earlier diagnostic; the
        # required-observation rule applies once a baseline is present.
        outcome = self._evaluate(gate_id="no-such-gate",
                                 observed_unit=None,
                                 observed_scope_digest=None)
        self.assertEqual(outcome.evaluation, "not_evaluable")
        self.assertEqual(outcome.diagnostic.kind, "baseline_missing")

    # ── P1-1 ②: event-based expiry with missing observation → fail-visible

    def test_event_based_missing_instrument_is_not_evaluable(self):
        outcome = self._evaluate(current_instrument_version=None)
        self.assertEqual(outcome.evaluation, "not_evaluable")
        self.assertEqual(outcome.diagnostic.kind, "instrument_missing")

    def test_event_based_missing_target_is_not_evaluable(self):
        outcome = self._evaluate(current_target_digest=None)
        self.assertEqual(outcome.evaluation, "not_evaluable")
        self.assertEqual(outcome.diagnostic.kind, "target_missing")

    def test_missing_expiry_observation_splits_by_policy_axis(self):
        blocked = self._evaluate(policy_class="release",
                                 current_instrument_version=None)
        self.assertEqual(blocked.continuation, "block")
        self.assertIn("waiver", blocked.diagnostic.action)
        advised = self._evaluate(policy_class="trend",
                                 current_instrument_version=None)
        self.assertEqual(advised.continuation, "advisory")
        self.assertIn("re-measure", advised.diagnostic.action)

    def test_time_based_baseline_keeps_event_observations_optional(self):
        # A max_age_days baseline carries its expiry in the TTL; the event
        # observations are optional (supplied → compared, absent → TTL).
        registry = self._registry_with_age(400)
        outcome = bm.evaluate(
            gate_id="injection-budget", observed_value=5000,
            policy_class="release", threshold=6000, direction="upper",
            observed_unit="tokens", observed_scope_digest=self.scope_digest,
            registry=registry, now=datetime(2026, 10, 10))
        self.assertEqual(outcome.evaluation, "pass")

    # ── P2-3: floor on a lower-bound gate is refused at the entrance ──────

    def test_floor_with_lower_direction_is_refused(self):
        with self.assertRaises(c.ContractViolation):
            self._evaluate(threshold=85, direction="lower", floor_value=70)

    # ── red-phase 4: deterministic contradiction → config error ───────────

    def test_threshold_below_floor_is_gate_configuration_error(self):
        # EVD-1100 shape: the 85% line implied a ≤414-token budget while the
        # frozen safety floor is 720 tokens — mathematically unreachable, a
        # gate configuration error, never a user failure.
        outcome = self._evaluate(threshold=414, floor_value=720)
        self.assertEqual(outcome.evaluation, "not_evaluable")
        self.assertEqual(outcome.diagnostic.kind, "gate_configuration_error")
        self.assertIn("414", outcome.diagnostic.message)
        self.assertIn("720", outcome.diagnostic.message)

    def test_config_error_precedes_baseline_state(self):
        # A broken gate configuration is reported even when the baseline is
        # missing — the configuration contradiction is the more fundamental
        # defect and must not be masked by baseline_missing.
        outcome = self._evaluate(gate_id="no-such-gate",
                                 threshold=414, floor_value=720)
        self.assertEqual(outcome.diagnostic.kind, "gate_configuration_error")

    def test_non_finite_threshold_is_gate_configuration_error(self):
        outcome = self._evaluate(threshold=float("nan"))
        self.assertEqual(outcome.diagnostic.kind, "gate_configuration_error")

    def test_non_finite_floor_is_gate_configuration_error(self):
        outcome = self._evaluate(floor_value=float("inf"))
        self.assertEqual(outcome.diagnostic.kind, "gate_configuration_error")

    def test_bad_direction_is_caller_bug_not_config_error(self):
        with self.assertRaises(c.ContractViolation):
            self._evaluate(direction="sideways")

    def test_unknown_policy_class_is_caller_bug(self):
        with self.assertRaises(c.ContractViolation):
            self._evaluate(policy_class="hope")

    def test_non_finite_observed_value_is_refused(self):
        with self.assertRaises(c.ContractViolation):
            self._evaluate(observed_value=float("inf"))

    # ── the three evaluation values themselves ────────────────────────────

    def test_fresh_matching_under_budget_passes(self):
        outcome = self._evaluate(observed_value=4216)
        self.assertEqual(outcome.evaluation, "pass")
        self.assertEqual(outcome.continuation, "block")  # release 轴姿态
        self.assertEqual(outcome.diagnostic.kind, "ok")

    def test_fresh_matching_over_budget_fails(self):
        outcome = self._evaluate(observed_value=6100)
        self.assertEqual(outcome.evaluation, "fail")
        self.assertEqual(outcome.diagnostic.kind, "objective_missed")

    def test_fail_on_trend_gate_stays_advisory(self):
        outcome = self._evaluate(observed_value=6100, policy_class="trend")
        self.assertEqual(outcome.evaluation, "fail")
        self.assertEqual(outcome.continuation, "advisory")

    def test_fail_on_release_gate_blocks(self):
        outcome = self._evaluate(observed_value=6100, policy_class="release")
        self.assertEqual(outcome.evaluation, "fail")
        self.assertEqual(outcome.continuation, "block")

    def test_lower_direction_gate(self):
        outcome = self._evaluate(
            observed_value=90, threshold=85, direction="lower")
        self.assertEqual(outcome.evaluation, "pass")
        outcome = self._evaluate(
            observed_value=70, threshold=85, direction="lower")
        self.assertEqual(outcome.evaluation, "fail")

    def test_evaluation_is_pure_replay(self):
        first = self._evaluate(observed_value=6100)
        second = self._evaluate(observed_value=6100)
        self.assertEqual(first, second)


class CommandLineTests(unittest.TestCase):
    """DoD 5/9: dry-run + structured output; pinned exit-code face."""

    def setUp(self):
        cm = _tmp_registry()
        self.registry = cm.__enter__()
        self.addCleanup(lambda: cm.__exit__(None, None, None))
        self.base_args = [
            "baseline-register",
            "--gate", "injection-budget",
            "--value", "4216",
            "--unit", "tokens",
            "--measured-at", "2026-09-19",
            "--measurement-command",
            "verify_workflow.py check-injection-budget --profile lightweight",
            "--instrument-version", "check-injection-budget@0.85.0",
            "--target-commit-digest", "b717835",
            "--scope", "resident injection template set",
            "--numerator", "resident tokens measured",
            "--denominator", "INJECTION_BUDGET_TOKENS=6000",
            "--exclusions", "tool-return budget face",
            "--threshold-basis", "DEC-210/211",
            "--expiry-condition", "SKILL version bump or surface SHA change",
            "--source-evd", "EVD-1104",
            "--registry", str(self.registry),
        ]

    def _run(self, argv):
        with _capture_stdio() as (buf_out, buf_err):
            code = bm.main(argv)
        return code, buf_out.getvalue(), buf_err.getvalue()

    def test_register_via_cli_writes_file(self):
        code, out, _ = self._run(self.base_args)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["status"], "registered")
        self.assertTrue(self.registry.exists())

    def test_register_replay_via_cli_is_idempotent(self):
        self._run(self.base_args)
        code, out, _ = self._run(self.base_args)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["status"], "replay")

    def test_register_dry_run_outputs_seven_elements_without_writing(self):
        code, out, _ = self._run(self.base_args + ["--dry-run"])
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(self.registry.exists())
        preview = payload["would_write"]
        for field in ("measured_at", "instrument_version",
                      "measurement_command", "target_commit_digest",
                      "scope", "numerator", "denominator", "exclusions",
                      "threshold_basis", "expiry_condition", "source_evd"):
            self.assertTrue(preview[field], field)

    def test_evaluate_exit_code_face(self):
        self._run(self.base_args)
        scope_digest = bm.caliber_digest(
            "tokens", "resident tokens measured",
            "INJECTION_BUDGET_TOKENS=6000", "tool-return budget face")
        evaluate_args = [
            "baseline-evaluate",
            "--gate", "injection-budget",
            "--policy-class", "release",
            "--observed-value", "5966",
            "--threshold", "6000",
            "--direction", "upper",
            "--observed-unit", "tokens",
            "--observed-scope-digest", scope_digest,
            "--current-instrument-version", "check-injection-budget@0.85.0",
            "--current-target-digest", "b717835",
            "--registry", str(self.registry),
        ]
        code, out, _ = self._run(evaluate_args)
        self.assertEqual(code, 0)  # pass
        self.assertEqual(json.loads(out)["evaluation"], "pass")

        code, out, _ = self._run(
            evaluate_args[:5] + ["--observed-value", "6100"]
            + evaluate_args[7:])
        self.assertEqual(code, 1)  # fail
        self.assertEqual(json.loads(out)["evaluation"], "fail")

        code, out, _ = self._run(
            ["baseline-evaluate", "--gate", "no-such-gate",
             "--policy-class", "release", "--observed-value", "5",
             "--threshold", "6000", "--direction", "upper",
             "--registry", str(self.registry)])
        self.assertEqual(code, 2)  # not_evaluable
        self.assertEqual(json.loads(out)["evaluation"], "not_evaluable")

    def test_cli_invalid_now_exits_three_not_fail(self):
        # P0-1: an unparsable --now is a usage error (exit 3) — the bare
        # ValueError must never pierce the except face and exit 1, wearing
        # a FAIL verdict for a command mistake.
        self._run(self.base_args)
        code, _, err = self._run(
            ["baseline-evaluate", "--gate", "injection-budget",
             "--policy-class", "release", "--observed-value", "5966",
             "--threshold", "6000", "--direction", "upper",
             "--now", "not-a-date",
             "--registry", str(self.registry)])
        self.assertEqual(code, 3)
        self.assertIn("ERROR", err)

    def test_cli_omitted_observed_unit_exits_three(self):
        # P1-1 ①: with a baseline present, omitting the comparison-side
        # caliber is a caller bug (exit 3), never a silent skip to pass.
        self._run(self.base_args)
        code, _, err = self._run(
            ["baseline-evaluate", "--gate", "injection-budget",
             "--policy-class", "release", "--observed-value", "5966",
             "--threshold", "6000", "--direction", "upper",
             "--observed-scope-digest", "a" * 64,
             "--registry", str(self.registry)])
        self.assertEqual(code, 3)
        self.assertIn("observed_unit", err)

    def test_cli_event_based_missing_expiry_observation_not_evaluable(
            self):
        # P1-1 ②: the stock row's expiry is event-based; without the
        # current instrument/target observations the verdict degrades to
        # not_evaluable (exit 2) — fail-visible, never "check skipped".
        self._run(self.base_args)
        code, out, _ = self._run(
            ["baseline-evaluate", "--gate", "injection-budget",
             "--policy-class", "release", "--observed-value", "5966",
             "--threshold", "6000", "--direction", "upper",
             "--observed-unit", "tokens",
             "--observed-scope-digest",
             bm.caliber_digest("tokens", "resident tokens measured",
                               "INJECTION_BUDGET_TOKENS=6000",
                               "tool-return budget face"),
             "--registry", str(self.registry)])
        self.assertEqual(code, 2)
        payload = json.loads(out)
        self.assertEqual(payload["evaluation"], "not_evaluable")
        self.assertIn(payload["diagnostic"]["kind"],
                      ("instrument_missing", "target_missing"))

    def test_cli_usage_error_exits_three(self):
        code, _, err = self._run(["baseline-evaluate", "--nope"])
        self.assertEqual(code, 3)
        self.assertTrue(err.strip())

    def test_cli_rejects_unknown_policy_class(self):
        self._run(self.base_args)
        code, _, _ = self._run(
            ["baseline-evaluate", "--gate", "injection-budget",
             "--policy-class", "hope", "--observed-value", "5",
             "--threshold", "6000", "--direction", "upper",
             "--registry", str(self.registry)])
        self.assertEqual(code, 3)


class StockBaselineProvenanceTests(unittest.TestCase):
    """存量登记演示面：injection-budget 6,000 门（EVD-1104）dry-run 素材。"""

    def test_stock_row_carries_all_seven_provenance_elements(self):
        meta = bm.BaselineMetadata(**_valid_kwargs())
        self.assertEqual(meta.measured_at, "2026-09-19")        # 测量时间
        self.assertTrue(meta.instrument_version)                # 测量器版本
        self.assertTrue(meta.measurement_command)               # 来源命令
        self.assertEqual(meta.target_commit_digest, "b717835")  # 对象摘要
        self.assertTrue(meta.scope and meta.numerator
                        and meta.denominator and meta.exclusions)  # 口径
        self.assertIn("DEC-210", meta.threshold_basis)          # 阈值依据
        self.assertIn("SHA", meta.expiry_condition)             # 失效条件
        self.assertEqual(meta.source_evd, "EVD-1104")

    def test_stock_row_evaluates_within_6000_budget(self):
        with _tmp_registry() as registry:
            bm.register(bm.BaselineMetadata(**_valid_kwargs()), registry)
            digest = bm.caliber_digest(
                "tokens", _valid_kwargs()["numerator"],
                _valid_kwargs()["denominator"], _valid_kwargs()["exclusions"])
            outcome = bm.evaluate(
                gate_id="injection-budget",
                observed_value=5966,
                policy_class="release",
                threshold=6000,
                direction="upper",
                observed_unit="tokens",
                observed_scope_digest=digest,
                registry=registry,
                now=datetime(2026, 9, 20),
                current_target_digest="b717835",
                current_instrument_version="check-injection-budget@0.85.0",
            )
        self.assertEqual(outcome.evaluation, "pass")


class DispatchFaceTests(unittest.TestCase):
    """P3-5 + P2-1 (review-FEAT-047, batch-2.0 FEAT-055): the engine
    dispatch face gets its own guards — the ``cmd_*`` handlers consume a
    Namespace built by the SAME option fact source (``add_*_arguments``) the
    engine subparser uses, and there is exactly one option definition per
    flag (the former Namespace→argv→main re-parse and its hand-maintained
    option maps are gone).
    """

    # instrument-version is DERIVED from the stock row (never a literal
    # version pin — the static-pin scan stays clean by construction)
    INSTRUMENT_VERSION = _valid_kwargs()["instrument_version"]

    BASE_ARGS = [
        "baseline-register",
        "--gate", "injection-budget",
        "--value", "4216",
        "--unit", "tokens",
        "--measured-at", "2026-09-19",
        "--measurement-command",
        "verify_workflow.py check-injection-budget --profile lightweight",
        "--instrument-version", INSTRUMENT_VERSION,
        "--target-commit-digest", "b717835",
        "--scope", "resident injection template set",
        "--numerator", "resident tokens measured",
        "--denominator", "INJECTION_BUDGET_TOKENS=6000",
        "--exclusions", "tool-return budget face",
        "--threshold-basis", "DEC-210/211",
        "--expiry-condition", "SKILL version bump or surface SHA change",
        "--source-evd", "EVD-1104",
    ]

    def test_cmd_register_handler_consumes_engine_namespace(self):
        with _tmp_registry() as registry:
            parser = bm.build_parser()
            args = parser.parse_args(self.BASE_ARGS
                                     + ["--registry", str(registry)])
            with _capture_stdio() as (buf_out, _):
                code = bm.cmd_baseline_register(args)
            self.assertEqual(code, 0)
            payload = json.loads(buf_out.getvalue())
            self.assertEqual(payload["status"], "registered")
            self.assertTrue(registry.exists())

    def test_cmd_evaluate_handler_consumes_engine_namespace(self):
        with _tmp_registry() as registry:
            bm.register(bm.BaselineMetadata(**_valid_kwargs()), registry)
            scope_digest = bm.caliber_digest(
                "tokens", _valid_kwargs()["numerator"],
                _valid_kwargs()["denominator"], _valid_kwargs()["exclusions"])
            parser = bm.build_parser()
            args = parser.parse_args([
                "baseline-evaluate", "--gate", "injection-budget",
                "--policy-class", "release", "--observed-value", "5966",
                "--threshold", "6000", "--direction", "upper",
                "--observed-unit", "tokens",
                "--observed-scope-digest", scope_digest,
                "--current-instrument-version", self.INSTRUMENT_VERSION,
                "--current-target-digest", "b717835",
                "--registry", str(registry)])
            with _capture_stdio() as (buf_out, _):
                code = bm.cmd_baseline_evaluate(args)
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(buf_out.getvalue())["evaluation"],
                             "pass")

    def test_add_arguments_is_the_single_option_fact_source(self):
        """The exported add_*_arguments faces define EXACTLY the option set
        of build_parser's own subparsers (same dests, requireds, choices) —
        proving the engine subparser and the module CLI cannot drift."""
        for add_face, command in ((bm.add_register_arguments,
                                   "baseline-register"),
                                  (bm.add_evaluate_arguments,
                                   "baseline-evaluate")):
            canonical = bm.build_parser()
            engine_side = argparse.ArgumentParser()
            sub = engine_side.add_subparsers(dest="command")
            face_parser = sub.add_parser(command)
            add_face(face_parser)
            canonical_sub = next(a for a in canonical._subparsers._group_actions
                                 if a.dest == "command")
            canonical_opts = {
                a.dest: (a.required, getattr(a, "option_strings", []))
                for a in canonical_sub.choices[command]._actions
                if a.dest != "help"}
            face_opts = {
                a.dest: (a.required, getattr(a, "option_strings", []))
                for a in face_parser._actions if a.dest != "help"}
            self.assertEqual(canonical_opts, face_opts, command)

    def test_namespace_handlers_no_longer_route_through_argv(self):
        """P2-1 structural pin: the argv-rebuild helpers are gone — a
        regression that reintroduces the double fact source fails here."""
        for gone in ("_namespace_to_argv", "_register_option_map",
                     "_evaluate_option_map"):
            self.assertFalse(hasattr(bm, gone), gone)


class RegistryNegativeControlTests(unittest.TestCase):
    """P2-2 (b)/(c)/(d) (review-FEAT-047, batch-2.0 FEAT-055): the
    fail-closed reader and the crash-safe writer get their direct negative
    controls."""

    def test_key_row_gate_id_mismatch_refused(self):
        with _tmp_registry() as registry:
            bm.register(bm.BaselineMetadata(**_valid_kwargs()), registry)
            payload = json.loads(registry.read_text(encoding="utf-8"))
            row = payload["baselines"]["injection-budget"]
            row["gate_id"] = "injection-budget-spoofed"
            payload["baselines"]["injection-budget"] = row
            registry.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8")
            with self.assertRaises(bm.BaselineMetadataError) as caught:
                bm.load_registry(registry)
            self.assertIn("keys and rows must agree", str(caught.exception))

    def test_non_utf8_bytes_refused(self):
        with _tmp_registry() as registry:
            registry.write_bytes(
                '{"baselines": "中文通道"}'.encode("gbk"))
            with self.assertRaises(bm.BaselineMetadataError) as caught:
                bm.load_registry(registry)
            self.assertIn("not valid UTF-8", str(caught.exception))

    def test_crash_during_replace_keeps_old_file_and_leaves_no_temp(self):
        with _tmp_registry() as registry:
            bm.register(bm.BaselineMetadata(**_valid_kwargs()), registry)
            before = registry.read_bytes()
            parent = registry.parent
            crashed = bm.BaselineMetadata(
                **_valid_kwargs(gate_id="crash-gate"))

            def exploding_replace(src, dst):
                raise OSError(13, "simulated crash mid-replace")

            with mock.patch.object(bm.os, "replace", exploding_replace):
                with self.assertRaises(OSError):
                    bm.register(crashed, registry)
            self.assertEqual(registry.read_bytes(), before)
            leftovers = [p.name for p in parent.iterdir()
                         if p.name.startswith(".baselines-")]
            self.assertEqual(leftovers, [],
                             "crash-point temp files must be cleaned up")


class ConcurrentRegisterWindowTests(unittest.TestCase):
    """P2-2(a) — the TOCTOU negative control (review-FEAT-047 DoD-7 ruling,
    batch-2.0 obligation FEAT-055): ``register`` is an UNLOCKED
    load→mutate→os.replace whole-file write, so two interleaved registers of
    DIFFERENT gates can lost-update each other.  This test reproduces the
    window with a controlled interleave (no thread-scheduling assumptions)
    to pin the documented single-writer constraint; a cross-process lock
    face landing MUST flip it with that deliberate change."""

    def test_concurrent_register_lost_update_window_is_documented(self):
        with _tmp_registry() as registry:
            meta_a = bm.BaselineMetadata(**_valid_kwargs(gate_id="gate-a"))
            meta_b = bm.BaselineMetadata(**_valid_kwargs(gate_id="gate-b"))
            original_load = bm.load_registry
            state = {"b_done": False}

            def interleaved_load(path):
                # Writer A's register loads the (empty) registry; while A
                # holds that stale view, writer B completes a FULL register.
                result = original_load(path)
                if not state["b_done"]:
                    state["b_done"] = True
                    bm.register(meta_b, registry)
                return result

            with mock.patch.object(bm, "load_registry", interleaved_load):
                bm.register(meta_a, registry)

            final = bm.load_registry(registry)
            self.assertIn("gate-a", final["baselines"])
            # THE WINDOW: B's row is silently gone — A wrote its stale view
            # over B's completed registration without any refusal.
            self.assertNotIn("gate-b", final["baselines"],
                             "if a lock face landed, flip this test: the "
                             "lost update must now be refused")


if __name__ == "__main__":
    unittest.main()
