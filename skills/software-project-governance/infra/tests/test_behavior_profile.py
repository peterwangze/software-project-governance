"""FEAT-040 — gray-release switch: behaviour + safety-boundary guards.

The switch exists to give a user a way back from the slice-A protocol changes
without weakening anything that protects them. So the guard net has three
layers, and each one can actually fail:

1. **Resolution** — precedence (env > plan-tracker > default), and the
   fail-closed treatment of a value outside the vocabulary ("legacyy" must not
   be read as legacy, and must not be silently read as modern either).
2. **Boundary** — ``revert_contract_issues()`` is exercised against INJECTED
   violations (a safety entry smuggled into the revert table, a duplicate
   surface, a markerless invariant, an unexplained exemption). Asserting "the
   real table is clean" alone would not prove the checker works.
3. **Non-interference** — with the SAME host tree, the ``governance-bootstrap``
   payload is identical under both profiles except for the declared faces
   (``behavior`` + the switch's own next-action). That is the machine statement
   of "legacy rolls back performance, not safety": health stays ``deferred``
   (no borrowed green light), the resolve envelope — the fail-closed authority
   — is untouched, and no governance face is dropped. It runs over **BOTH
   arms** (env and plan-tracker) against a FIXTURE plan-tracker rather than the
   live one: the project-level arm is documented user surface, so it carries
   the same non-interference evidence as the session-level arm, and a guard
   must not flip red merely because the live tree enabled that arm (R0 P1-1 /
   P2-2).

Plus the publication guard: every surface that ships the protocol must carry
the switch marker, and every safety invariant's marker must appear in the
published boundary — a rewrite that drops the switch, or that keeps the switch
but loses the boundary, reddens here.
"""

from __future__ import annotations

import ast
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

INFRA = Path(__file__).resolve().parents[1]
if str(INFRA) not in sys.path:
    sys.path.insert(0, str(INFRA))

import behavior_profile as bp  # noqa: E402
import bootstrap_aggregate as ba  # noqa: E402
import resolve_entry  # noqa: E402
import verify_workflow as vw  # noqa: E402

ROOT = INFRA.parents[2]


def _plan_tracker_text(value):
    return "\n".join([
        "## 项目配置",
        "",
        "- **项目名称**: demo",
        "- **当前阶段**: 维护与演进",
        "- **工作流版本**: 0.83.0",
        ("- **behavior_profile**: %s" % value) if value is not None else "",
        "",
        "## Gate 状态跟踪",
        "",
        "- **behavior_profile**: not-here (section-bounded read must ignore it)",
    ])


#: A well-formed plan-tracker the AGGREGATE can be built from — deliberately
#: NOT the live file (R0 P2-2): a guard test must not flip red because someone
#: enabled the very project-level arm it guards on the live dogfood tree.
_FIXTURE_PLAN_SECTIONS = (
    "## 项目总览",
    "",
    "| 项目 | 当前版本 | 任务总数 | 已完成 | 阻塞中 | 风险数 |",
    "|------|---------|---------|--------|--------|--------|",
    "| demo | 0.83.0 | 5 | 2 | 0 | 0 |",
    "",
    "## Gate 状态跟踪",
    "",
    "| Gate | 名称 | 状态 |",
    "|------|------|------|",
    "| G1 | 立项 | passed |",
    "| G2 | 调研 | pending |",
    "",
    "| **P1** | FIX-900 | 合成任务（臂无关） | DEC-000 | 0.83.0 | pending |",
    "| **P2** | FIX-901 | 合成任务（臂无关） | DEC-000 | 0.83.0 | pending |",
)


def _fixture_plan_text(behavior_profile=None):
    """Host-independent plan-tracker text for the aggregate tests."""
    head = ["## 项目配置", "",
            "- **项目名称**: demo",
            "- **当前阶段**: 维护与演进",
            "- **工作流版本**: 0.83.0",
            "- **触发模式**: always-on",
            "- **操作权限模式**: default-confirm"]
    if behavior_profile is not None:
        head.append("- **behavior_profile**: %s" % behavior_profile)
    return "\n".join(head + [""] + list(_FIXTURE_PLAN_SECTIONS) + [""])


class ResolutionTests(unittest.TestCase):
    """Layer 1 — precedence and the fail-closed vocabulary."""

    def test_default_is_modern(self):
        result = bp.resolve_behavior_profile(env={}, plan_tracker_text="")
        self.assertEqual(result["profile"], "modern")
        self.assertEqual(result["source"], "default")
        self.assertFalse(result["is_legacy"])
        self.assertEqual(result["revert_ids"], [])

    def test_env_arm_wins(self):
        result = bp.resolve_behavior_profile(
            env={bp.ENV_VAR: "1"},
            plan_tracker_text=_plan_tracker_text("modern"))
        self.assertEqual(result["profile"], "legacy")
        self.assertEqual(result["source"], "env")

    def test_plan_tracker_arm(self):
        result = bp.resolve_behavior_profile(
            env={}, plan_tracker_text=_plan_tracker_text("legacy"))
        self.assertEqual(result["profile"], "legacy")
        self.assertEqual(result["source"], "plan-tracker")

    def test_vocabulary_is_symmetric_and_case_insensitive(self):
        for token in ("1", "true", "TRUE", " yes ", "on", "legacy", "Legacy"):
            with self.subTest(token=token):
                profile, status = bp.classify_token(token)
                self.assertEqual((profile, status), ("legacy", "set"))
        for token in ("0", "false", "NO", " off ", "modern"):
            with self.subTest(token=token):
                profile, status = bp.classify_token(token)
                self.assertEqual((profile, status), ("modern", "set"))

    def test_invalid_value_is_reported_and_never_guessed(self):
        """`legacyy` must not enable legacy — and must not be swallowed."""
        result = bp.resolve_behavior_profile(
            env={bp.ENV_VAR: "legacyy"},
            plan_tracker_text=_plan_tracker_text("legacy"))
        # not guessed as legacy …
        self.assertEqual(result["profile"], "legacy")
        self.assertEqual(result["source"], "plan-tracker")  # fell through
        # … and the bad value is on the record.
        self.assertEqual(len(result["invalid"]), 1)
        self.assertEqual(result["invalid"][0]["arm"], bp.SOURCE_ENV)
        self.assertEqual(result["invalid"][0]["value"], "legacyy")

    def test_echoed_invalid_value_is_bounded(self):
        """P2-3: the echoed raw value is a token, not a payload."""
        result = bp.resolve_behavior_profile(
            env={bp.ENV_VAR: "y" * 300}, plan_tracker_text="")
        value = result["invalid"][0]["value"]
        self.assertEqual(len(value), bp.INVALID_VALUE_LIMIT + 1)
        self.assertTrue(value.endswith("…"), value)
        # short values pass through untouched (the clip discloses, it never
        # rewrites what the user actually typed)
        self.assertEqual(bp.resolve_behavior_profile(
            env={bp.ENV_VAR: "legacyy"}, plan_tracker_text="")["invalid"][0],
            {"arm": "env", "name": bp.ENV_VAR, "value": "legacyy"})

    def test_whitespace_and_empty_are_unset(self):
        for raw in (None, "", "   "):
            with self.subTest(raw=raw):
                profile, status = bp.classify_token(raw)
                self.assertIsNone(profile)
                self.assertEqual(status, "unset")

    def test_plan_tracker_read_is_section_bounded(self):
        """The `## 项目配置` read must not pick up a later section's key."""
        text = "\n".join([
            "## 项目总览", "", "- **behavior_profile**: legacy", "",
            "## 项目配置", "", "- **项目名称**: demo", "",
        ])
        self.assertIsNone(bp.plan_tracker_value(text))
        self.assertEqual(bp.resolve_behavior_profile(env={}, plan_tracker_text=text)
                         ["profile"], "modern")

    def test_reverted_list_is_empty_when_modern_and_full_when_legacy(self):
        modern = bp.resolve_behavior_profile(env={}, plan_tracker_text="")
        legacy = bp.resolve_behavior_profile(env={bp.ENV_VAR: "1"},
                                             plan_tracker_text="")
        self.assertEqual(modern["revert_ids"], [])
        self.assertEqual(len(legacy["revert_ids"]), len(bp.LEGACY_REVERTS))
        # the invariant list is profile-INDEPENDENT: it is the boundary, not a
        # consequence of the switch
        self.assertEqual(modern["invariant_ids"], legacy["invariant_ids"])


class BoundaryContractTests(unittest.TestCase):
    """Layer 2 — the boundary checker is exercised, not just asserted clean."""

    def test_real_table_is_clean(self):
        self.assertEqual(bp.revert_contract_issues(), [])

    def test_feat035_is_not_revertible(self):
        feats = {item["feat"] for item in bp.LEGACY_REVERTS}
        self.assertNotIn("FEAT-035", feats,
                         "FEAT-035 carries safety semantics (upgrade "
                         "confirmation gate) — it MUST NOT appear in the "
                         "revert table")
        invariant_feats = {item["feat"] for item in bp.SAFETY_INVARIANTS}
        self.assertIn("FEAT-035", invariant_feats)

    def test_revert_classes_are_performance_only(self):
        for item in bp.LEGACY_REVERTS:
            self.assertEqual(item["class"], bp.REVERT_CLASS_PERFORMANCE)
        self.assertEqual(bp.ALLOWED_REVERT_CLASSES,
                         frozenset((bp.REVERT_CLASS_PERFORMANCE,)))

    def test_checker_catches_a_smuggled_safety_revert(self):
        smuggled = bp.LEGACY_REVERTS + ({
            "feat": "FEAT-035",
            "surface": "升级确认门",
            "modern": "ask 确认后写",
            "legacy": "静默写（不回退）",
            "class": "safety",
        },)
        with patch.object(bp, "LEGACY_REVERTS", smuggled):
            issues = bp.revert_contract_issues()
        self.assertTrue(any("outside" in issue for issue in issues), issues)
        self.assertTrue(any("BOTH" in issue for issue in issues), issues)

    def test_checker_catches_duplicate_surface_and_markerless_invariant(self):
        with patch.object(bp, "LEGACY_REVERTS", bp.LEGACY_REVERTS + (
                dict(bp.LEGACY_REVERTS[0]),)):
            self.assertTrue(any("duplicate revert surface" in issue
                                for issue in bp.revert_contract_issues()))
        markerless = tuple(dict(item, marker="") if index == 0 else item
                           for index, item in enumerate(bp.SAFETY_INVARIANTS))
        with patch.object(bp, "SAFETY_INVARIANTS", markerless):
            self.assertTrue(any("no protocol marker" in issue
                                for issue in bp.revert_contract_issues()))

    def test_safety_invariant_markers_are_published(self):
        """Each invariant's marker must appear wherever the switch is published."""
        surfaces = _published_surfaces()
        for item in bp.SAFETY_INVARIANTS:
            hits = [name for name, text in surfaces.items()
                    if item["marker"] in text]
            self.assertTrue(
                hits,
                f"safety invariant {item['id']!r} marker "
                f"{item['marker']!r} is not published on any surface — the "
                "boundary text drifted away from the boundary table")
        # and the two richest surfaces must carry the FULL boundary, so no
        # single-file rewrite can silently narrow it
        for rich in ("skills/software-project-governance/SKILL.md",
                     "commands/governance/bootstrap.md"):
            text = surfaces[rich]
            for item in bp.SAFETY_INVARIANTS:
                self.assertIn(item["marker"], text,
                              f"{rich} lost safety invariant "
                              f"{item['id']!r} ({item['marker']!r})")


def _published_surfaces():
    out = {}
    for rel in bp.PROTOCOL_SURFACES:
        path = ROOT / rel
        if path.is_file():
            out[rel] = path.read_text(encoding="utf-8")
    return out


class PublicationTests(unittest.TestCase):
    """Every shipping surface publishes the switch, and it still works."""

    def test_every_protocol_surface_exists(self):
        for rel in bp.PROTOCOL_SURFACES:
            self.assertTrue((ROOT / rel).is_file(), f"{rel} is missing")

    def test_every_protocol_surface_carries_the_marker(self):
        surfaces = _published_surfaces()
        for rel in bp.PROTOCOL_SURFACES:
            self.assertIn(bp.PROTOCOL_MARKER, surfaces[rel],
                          f"{rel} does not publish the gray-release switch "
                          f"({bp.PROTOCOL_MARKER!r})")

    def test_entry_templates_carry_the_switch_and_the_boundary(self):
        """All four Step 7 templates are generated from one canonical source."""
        from sync_entry_projection import extract_canonical_templates
        templates = extract_canonical_templates(
            (ROOT / "commands/governance-init.md").read_text(encoding="utf-8"))
        for profile in ("lightweight", "standard", "strict", "secondary-thin"):
            with self.subTest(profile=profile):
                text = templates[profile]
                for token in (bp.ENV_VAR, bp.PLAN_TRACKER_KEY,
                              "安全语义不回退"):
                    self.assertIn(token, text, f"{profile} template lost {token}")

    def test_dsh_thin_pointer_dialect_carries_the_switch(self):
        """FEAT-037 P3-6: the second thin-pointer dialect is guarded too."""
        from sync_entry_projection import (check_dsh_thin_pointer,
                                           validate_dsh_thin_pointer)
        report = check_dsh_thin_pointer(ROOT)
        self.assertEqual(report["issues"], [], report["issues"])
        self.assertTrue(report["bytes"] > 0)
        text = (ROOT / report["path"]).read_text(encoding="utf-8")
        self.assertEqual(validate_dsh_thin_pointer(text), [])

    def test_router_layer_stays_within_budget_with_the_switch(self):
        """FEAT-040 text must not push the router past its 12KB envelope."""
        router = ROOT / "commands/governance.md"
        self.assertLessEqual(router.stat().st_size, 12288)

    def test_protocol_documents_render_the_boundary_table(self):
        rendered = bp.render_boundary_table(
            bp.resolve_behavior_profile(env={}, plan_tracker_text=""))
        for item in bp.LEGACY_REVERTS:
            self.assertIn(item["surface"], rendered)
        for item in bp.SAFETY_INVARIANTS:
            self.assertIn(item["id"], rendered)


class AggregateFaceTests(unittest.TestCase):
    """Layer 3 — the switch is observable, and it changes nothing else.

    Both the resolve envelope and the host root stay REAL (so the fail-closed
    authority and every governance face are exercised); only the plan-tracker
    text is a fixture, so no test here reads a live ``behavior_profile`` cell.
    """

    @classmethod
    def setUpClass(cls):
        cls.host_root = Path(resolve_entry.resolve_host_root(str(ROOT)))
        cls.envelope = resolve_entry.resolve(cls.host_root)

    def _payload(self, env, plan_text=None):
        plan_text = _fixture_plan_text() if plan_text is None else plan_text
        with patch.dict(os.environ, env, clear=False):
            if not env:
                os.environ.pop(bp.ENV_VAR, None)
            with patch.object(ba, "_read_text", return_value=plan_text):
                return ba._build_payload(self.host_root, self.envelope, 3000,
                                         "standard", time.monotonic())

    def test_face_is_present_and_modern_by_default(self):
        os.environ.pop(bp.ENV_VAR, None)
        face = self._payload({})["behavior"]
        self.assertEqual(face["profile"], "modern")
        self.assertEqual(face["reverted"], [])
        self.assertEqual(face["invariants"],
                         [item["id"] for item in bp.SAFETY_INVARIANTS])

    def test_legacy_face_reports_the_reverted_surfaces(self):
        face = self._payload({bp.ENV_VAR: "1"})["behavior"]
        self.assertEqual(face["profile"], "legacy")
        self.assertEqual(face["source"], "env")
        self.assertEqual(len(face["reverted"]), len(bp.LEGACY_REVERTS))

    def test_rollback_action_is_first_when_legacy(self):
        payload = self._payload({bp.ENV_VAR: "1"})
        actions = payload["next_actions"]
        self.assertTrue(actions)
        self.assertIn("灰度回退生效", actions[0],
                      "the rollback hint must be FIRST — the 5-item cap could "
                      "otherwise drop it (FEAT-040)")

    def test_no_rollback_action_when_modern(self):
        payload = self._payload({})
        self.assertFalse(any("灰度回退生效" in action
                             for action in payload["next_actions"]))

    def test_next_action_line_contract(self):
        """The aggregate's rollback line is driven by the face (the real API)."""
        face = self._payload({}, _fixture_plan_text("legacy"))["behavior"]
        line = bp.next_action_line(face)
        self.assertIn("灰度回退生效", line)
        self.assertIn("plan-tracker", line)
        self.assertIsNone(bp.next_action_line(
            self._payload({})["behavior"]))
        self.assertIsNone(bp.next_action_line(None))

    def test_legacy_changes_only_the_declared_faces(self):
        """The machine statement of "performance rollback, not safety".

        Runs once per arm: the env arm and the project-level (plan-tracker) arm
        both resolve to the same declared difference, so the documented
        "project-level rollback channel" carries the same non-interference
        evidence as the session-level one (R0 P1-1). The plan-tracker text is a
        fixture — never the live file (R0 P2-2).
        """
        baseline = self._payload({}, _fixture_plan_text())
        # the premise: with neither arm engaged the default decides (otherwise
        # the comparison below is not a comparison of the switch at all)
        self.assertEqual(baseline["behavior"]["profile"], "modern")
        self.assertEqual(baseline["behavior"]["source"], "default")
        # per arm: (engaged env, engaged plan-tracker text, the MODERN control
        # for the same arm) — for the env arm the control differs only by the
        # variable; for the project arm only by the `behavior_profile` cell.
        arms = {
            "env": ({bp.ENV_VAR: "1"}, _fixture_plan_text(),
                    _fixture_plan_text()),
            "plan-tracker": ({}, _fixture_plan_text("legacy"),
                             _fixture_plan_text()),
        }
        for arm, (env, plan_text, modern_text) in arms.items():
            with self.subTest(arm=arm):
                modern = self._payload({}, modern_text)
                legacy = self._payload(env, plan_text)
                self.assertEqual(modern["behavior"]["source"], "default",
                                 "the modern leg must not be overridden by "
                                 "either arm")
                self.assertEqual(legacy["behavior"]["source"], arm)
                self.assertEqual(legacy["behavior"]["profile"], "legacy")
                # the declared difference
                self.assertNotEqual(modern["behavior"], legacy["behavior"])
                self.assertNotEqual(modern["next_actions"],
                                    legacy["next_actions"])
                # everything else is byte-equal: health stays deferred (no
                # borrowed green light), the resolve envelope (the fail-closed
                # authority) is untouched, and no governance face is dropped.
                for face in ("resolve", "health", "project", "gates", "tasks",
                             "risks", "migration", "candidates", "recent"):
                    self.assertEqual(modern.get(face), legacy.get(face),
                                     f"legacy ({arm} arm) changed {face}")
                self.assertEqual(modern["health"]["state"], "deferred")
                self.assertEqual(legacy["health"]["state"], "deferred")

    def test_plan_tracker_arm_reaches_the_aggregate_face(self):
        """R0 P1-1: the project-level arm is the DOCUMENTED rollback channel.

        The env arm works on its own (a user can roll back a session without
        touching a governance file); the plan-tracker arm is what a project
        sets when the old shape is needed beyond one session. Nothing else
        guards the single wiring point that reads it
        (``_build_payload`` → ``behavior_face(plan_tracker_text=...)``), so
        losing that argument would silently disable the channel while the CLI
        still reported ``modern``.
        """
        payload = self._payload({}, _fixture_plan_text("legacy"))
        face = payload["behavior"]
        self.assertEqual(face["profile"], "legacy")
        self.assertEqual(face["source"], "plan-tracker")
        self.assertEqual(len(face["reverted"]), len(bp.LEGACY_REVERTS))
        self.assertTrue(payload["next_actions"])
        self.assertIn("灰度回退生效", payload["next_actions"][0])

    def test_plan_tracker_arm_reports_an_invalid_project_value(self):
        """Same "never guessed" rule, project-level spelling."""
        payload = self._payload({}, _fixture_plan_text("legacyy"))
        face = payload["behavior"]
        self.assertEqual(face["profile"], "modern")
        self.assertEqual(face["source"], "default")
        self.assertEqual(len(face["invalid"]), 1)
        self.assertEqual(face["invalid"][0]["arm"], "plan-tracker")

    def test_text_face_renders_the_behavior_line(self):
        payload = self._payload({bp.ENV_VAR: "1"})
        text = ba.format_text(payload)
        self.assertIn("behavior: legacy (source env)", text)

    def test_text_face_discloses_the_plan_tracker_arm(self):
        text = ba.format_text(self._payload({}, _fixture_plan_text("legacy")))
        self.assertIn("behavior: legacy (source plan-tracker)", text)

    def test_invalid_env_value_is_disclosed_in_the_face(self):
        face = self._payload({bp.ENV_VAR: "legacyy"})["behavior"]
        self.assertEqual(face["profile"], "modern")
        self.assertEqual(len(face["invalid"]), 1)

    def test_invalid_env_value_also_reaches_next_actions(self):
        """R0 P1-2: the JSON fast path must carry the action signal.

        The wrong-value case has no ``behavior``-face consumer by default (the
        documented fast path reads ``next_actions``), whereas the legacy-engaged
        case has always shipped a first-class action line. Without this the
        user who typed ``legacyy`` would see nothing happen and nothing said.
        """
        payload = self._payload({bp.ENV_VAR: "legacyy"})
        self.assertEqual(payload["behavior"]["profile"], "modern")
        hints = [index for index, action in enumerate(payload["next_actions"])
                 if action == bp.INVALID_VALUE_ACTION]
        self.assertTrue(
            hints,
            "the invalid switch value must be actionable — next_actions="
            f"{payload['next_actions']}")
        self.assertEqual(hints[0], 0,
                         "with no rollback hint present the invalid-value hint "
                         "is the most urgent one")
        text = ba.format_text(payload)
        self.assertIn("行为开关取值非法已被忽略", text)

    def test_rollback_and_invalid_hints_coexist_under_both_arms(self):
        """Both signals at once: env=legacy engaged, plan-tracker = garbage."""
        payload = self._payload({bp.ENV_VAR: "1"},
                                _fixture_plan_text("legacyy"))
        face = payload["behavior"]
        self.assertEqual(face["profile"], "legacy")
        self.assertEqual(face["source"], "env")
        self.assertEqual([item["arm"] for item in face["invalid"]],
                         ["plan-tracker"])
        actions = payload["next_actions"]
        self.assertIn("灰度回退生效", actions[0])
        self.assertEqual(actions[1], bp.INVALID_VALUE_ACTION)
        self.assertLessEqual(len(actions), 5)

    def test_echoed_invalid_value_is_clipped(self):
        """P2-3: an over-long env value cannot ride into the agent context."""
        payload = self._payload({bp.ENV_VAR: "x" * 200})
        value = payload["behavior"]["invalid"][0]["value"]
        self.assertEqual(len(value), bp.INVALID_VALUE_LIMIT + 1)
        self.assertTrue(value.endswith("…"), value)

    def test_face_fits_the_aggregate_output_budget(self):
        payload = ba._enforce_projection_budget(self._payload({}))
        self.assertLessEqual(ba._payload_bytes(payload), ba.MAX_JSON_BYTES)

    def test_face_with_both_hints_still_fits_the_output_budget(self):
        payload = ba._enforce_projection_budget(self._payload(
            {bp.ENV_VAR: "legacyy"}, _fixture_plan_text("legacy")))
        self.assertLessEqual(ba._payload_bytes(payload), ba.MAX_JSON_BYTES)


class CliSmokeTests(unittest.TestCase):
    """The documented one-click verification really runs."""

    def _run(self, env=None):
        import subprocess
        full_env = dict(os.environ)
        full_env.pop(bp.ENV_VAR, None)
        full_env.update(env or {})
        proc = subprocess.run(
            [sys.executable, str(INFRA / "verify_workflow.py"),
             "--project-root", str(ROOT),
             "governance-bootstrap", "--format", "json"],
            capture_output=True, timeout=180, env=full_env)
        out = proc.stdout.decode("utf-8", "replace")
        return proc.returncode, out

    def test_cli_reports_modern_by_default(self):
        code, out = self._run(None)
        self.assertEqual(code, 0, out[-800:])
        payload = json.loads(out[out.index("{"):])
        self.assertEqual(payload["behavior"]["profile"], "modern")

    def test_cli_reports_legacy_under_the_env_var(self):
        code, out = self._run({bp.ENV_VAR: "1"})
        self.assertEqual(code, 0, out[-800:])
        payload = json.loads(out[out.index("{"):])
        self.assertEqual(payload["behavior"]["profile"], "legacy")
        self.assertIn("灰度回退生效", payload["next_actions"][0])


class FailClosedUnaffectedTests(unittest.TestCase):
    """The switch cannot reach the fail-closed authority (structural guard).

    ``behavior_profile`` is a pure read-only resolver: it must not import the
    engine, must not touch the filesystem, and must not expose anything that
    could disable ``resolved_root_ok``. This test pins that shape, so a later
    "legacy bypass" cannot be added without reddening here.
    """

    def test_module_is_stdlib_only_and_never_mutates(self):
        """AST guard — not a source-text scan (the docstring may name things)."""
        tree = ast.parse((INFRA / "behavior_profile.py").read_text(
            encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        self.assertLessEqual(
            imported, {"os", "re", "__future__"},
            "behavior_profile must stay a stdlib-only leaf (ArchGuard R2/R6): "
            f"imports={sorted(imported)}")

        mutators = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = getattr(func, "attr", None) or getattr(func, "id", None)
                if name in {"write_text", "write_bytes", "remove", "unlink",
                            "rmtree", "rename", "replace", "open", "system",
                            "run", "Popen", "chmod", "mkdir", "touch"}:
                    mutators.add(name)
        self.assertEqual(mutators, set(),
                         "the rollback switch must be a pure read-only "
                         f"resolver — found mutating calls: {sorted(mutators)}")

    def test_resolver_is_total_for_ordinary_shapes(self):
        """Only a broken env MAPPING raises (caller error); values never do."""
        for env in ({}, {bp.ENV_VAR: ""}, {bp.ENV_VAR: "junk"},
                    {bp.ENV_VAR: "1"}, {bp.ENV_VAR: "0"}):
            with self.subTest(env=env):
                result = bp.resolve_behavior_profile(env=env,
                                                     plan_tracker_text=None)
                self.assertIn(result["profile"], bp.PROFILE_VALUES)

    def test_resolver_does_not_swallow_a_broken_env_mapping(self):
        class _BadEnv:
            def get(self, _key):
                raise RuntimeError("hostile mapping")

        with self.assertRaises(RuntimeError):
            bp.resolve_behavior_profile(env=_BadEnv(), plan_tracker_text="")

    def test_engine_exports_the_surface_census_used_by_guards(self):
        """The FEAT-039 census stays importable from the engine (guard input)."""
        self.assertTrue(vw.INJECTION_BUDGET_SURFACES)
        paths = {item["path"] for item in vw.INJECTION_BUDGET_SURFACES}
        self.assertIn("commands/governance.md", paths)


if __name__ == "__main__":
    unittest.main()
