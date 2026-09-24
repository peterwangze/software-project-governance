"""FEAT-040 — projection-registry extension guards.

Three carry-over findings from the slice-A reviews land here, and each needs a
guard that can actually fail:

* **FEAT-036 P2-3 / FEAT-038 P2-4** — the fixture's `commands/governance.md`
  had NO deterministic sync path (it was outside `version-projections.json`,
  so the router mirror was hand-copied and left uncommitted). It is now a
  declared `byte_copy` projection; the tests below prove the registry — not a
  hand copy — produces the file that is on disk.
* **FEAT-038 P2-4 / RISK-039** — the fixture's engine copy diverges by ~34.7k
  lines and cannot be a projection. It is DECLARED a legacy snapshot, and the
  declaration is falsifiable: it reddens when the file disappears, and it
  reddens when the file converges (a converged copy must be promoted to a real
  projection instead of keeping a stale exemption).
* **FEAT-037 P3-4** — the fixture-mirror inventory registered in the manifest
  must keep matching `PROJECTION_SYNC_PATTERNS` exactly, so a pattern added
  without a manifest update fails here rather than drifting.
* **FIX-381** — the controlled-backport institution
  (`legacy_snapshot_backport_policy` + per-snapshot `approved_backports`
  ledgers) is machine-guarded: hollow policy sections, hollow ledger entries,
  stale anchors and missing patch markers each redden, and a converged
  backport-bearing snapshot names the replay-or-promote disposition.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

INFRA = Path(__file__).resolve().parents[1]
if str(INFRA) not in sys.path:
    sys.path.insert(0, str(INFRA))

from release.projection import (  # noqa: E402
    build_projection_plan, check_legacy_snapshots, check_projections)

ROOT = INFRA.parents[2]
CONFIG_REL = "skills/software-project-governance/core/version-projections.json"
MANIFEST_REL = "skills/software-project-governance/core/manifest.json"
ROUTER = "commands/governance.md"
ROUTER_FIXTURE = "project/e2e-test-project/commands/governance.md"


class RouterProjectionTests(unittest.TestCase):
    """The router mirror is registry-driven, not hand-copied."""

    def test_router_is_a_declared_byte_copy_projection(self):
        _version, plan = build_projection_plan(ROOT)
        targeted = {write.relative_path: write for write in plan}
        self.assertIn(ROUTER_FIXTURE, targeted,
                      "the fixture router MUST be a declared projection — "
                      "otherwise its mirror has no deterministic sync path "
                      "(FEAT-038 P2-4)")
        write = targeted[ROUTER_FIXTURE]
        self.assertEqual(write.kind, "byte_copy")
        self.assertEqual(write.content, (ROOT / ROUTER).read_bytes())

    def test_projection_plan_is_current_on_disk(self):
        """No drift: the shipped fixture already equals the registry output."""
        result = check_projections(ROOT).as_dict()
        self.assertEqual(result["state"], "PASS", result["issues"])
        self.assertEqual(result["issues"], [])

    def test_registry_and_manifest_contract_agree(self):
        """Adding a projection without the manifest counterpart must fail."""
        manifest = json.loads((ROOT / MANIFEST_REL).read_text(encoding="utf-8"))
        ids = manifest["release_projection_contract"]["projection_ids"]
        self.assertIn("fixture-command-governance-router", ids)
        # build_projection_plan enforces exact set equality between the two
        _version, plan = build_projection_plan(ROOT)
        targets = [write.relative_path for write in plan]
        self.assertEqual(len(targets), len(set(targets)),
                         "duplicate projection targets")

    def test_fixture_mirror_inventory_matches_the_manifest(self):
        """FEAT-037 P3-4: patterns ↔ required_members stay exact."""
        import verify_workflow as vw
        manifest = json.loads((ROOT / MANIFEST_REL).read_text(encoding="utf-8"))
        contract = manifest["release_projection_contract"]
        entry = next(item for item in contract["validation_inventories"]
                     if item["id"] == "fixture-mirror-patterns")
        self.assertEqual(entry.get("member_match"), "exact")
        self.assertEqual(set(vw.PROJECTION_SYNC_PATTERNS),
                         set(entry["required_members"]))
        for pattern in ("commands/*.md", "commands/governance/*.md"):
            self.assertIn(pattern, vw.PROJECTION_SYNC_PATTERNS)


class LegacySnapshotDeclarationTests(unittest.TestCase):
    """The declared divergences are on the record AND falsifiable."""

    def test_shipped_declarations_pass(self):
        result = check_legacy_snapshots(ROOT)
        self.assertTrue(result["pass"], result["issues"])
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["checked"], 10)
        self.assertEqual(result["converged"], [])
        self.assertEqual(result["missing"], [])
        by_path = {item["path"]: item for item in result["declared"]}
        self.assertIn(
            "project/e2e-test-project/skills/software-project-governance/"
            "infra/verify_workflow.py", by_path)

    def test_every_divergent_fixture_infra_copy_is_declared(self):
        """No silent residual INSIDE the declared scope.

        `declared_legacy_snapshot_scope` is the machine-readable boundary of
        the claim: within it, a path that diverges from its canonical file MUST
        appear either as a projection or as a declared legacy snapshot — an
        undeclared divergence is exactly the implicit parity debt FEAT-038
        P2-4 named. (Outside the scope the fixture mirror is a much wider
        legacy tree; that census is REPORTED by `check_legacy_snapshots`
        rather than silently absorbed here.)
        """
        import verify_workflow as vw
        from release.projection import FIXTURE_PREFIX
        config = json.loads((ROOT / CONFIG_REL).read_text(encoding="utf-8"))
        scopes = tuple(config["declared_legacy_snapshot_scope"])
        self.assertTrue(scopes)
        declared = {item["path"][len(FIXTURE_PREFIX):]
                    for item in config["declared_legacy_snapshots"]}
        projected = {item["target"][len(FIXTURE_PREFIX):]
                     for item in config["projections"]
                     if item.get("target", "").startswith(FIXTURE_PREFIX)}
        fixture_root = ROOT / "project/e2e-test-project"
        undeclared = []
        for rel in sorted(vw._projection_source_files(ROOT)):
            if not rel.startswith(scopes):
                continue
            fixture = fixture_root / rel
            if not fixture.is_file():
                continue  # absent copies are a different class (partial tree)
            if fixture.read_bytes() == (ROOT / rel).read_bytes():
                continue
            if rel not in declared and rel not in projected:
                undeclared.append(rel)
        self.assertEqual(
            undeclared, [],
            "these in-scope fixture files diverge from their canonical source "
            "without being declared (add a projection or a declared legacy "
            f"snapshot): {undeclared}")

    def test_out_of_scope_divergence_is_reported_not_absorbed(self):
        """The wider fixture divergence is a disclosed census, not a silence."""
        result = check_legacy_snapshots(ROOT)
        census = result["census"]
        self.assertGreater(census["divergent"], 0)
        self.assertEqual(census["declared"], len(result["declared"]))
        self.assertEqual(census["undeclared_in_scope"], [])
        # the wider tree really is wider — if it ever becomes empty the
        # disclosure should be deleted rather than kept as decoration
        self.assertTrue(census["undeclared_out_of_scope"] or
                        census["absent"] == 0)

    def test_census_is_structural_not_a_disclosed_number(self):
        """R0 P2-1: the census counts are held by IDENTITIES, not by prose.

        The disclosure in the report/docstrings names concrete counts
        (inventory 282 = identical 55 + divergent 39 + absent 177 + 11
        projected at the time of writing). Numbers copied into prose cannot be
        falsified — they just drift. So this test does not pin them; it pins
        the identities that make them true, which reddens the moment the
        fixture tree and the reported census stop agreeing, whichever side
        moves:

        * the inventory is exactly the ``PROJECTION_SYNC_PATTERNS`` mirror set
          (the same authority the manifest's ``fixture-mirror-patterns``
          inventory names);
        * every inventoried path lands in exactly one bucket — projected
          (claimed by a ``byte_copy``/``json_merge`` projection), absent,
          identical, or divergent;
        * the declared divergences are a subset of the divergent ones, and the
          in-scope undeclared list is intact (no duplicates, ≤ divergent).
        """
        import verify_workflow as vw
        from release import projection as rp
        result = check_legacy_snapshots(ROOT)
        self.assertTrue(result["pass"], result["issues"])
        census = result["census"]
        fixture_root = ROOT / rp.FIXTURE_PREFIX.rstrip("/")
        if not fixture_root.is_dir():
            self.skipTest("fixture mirror is absent (partial tree)")
        # the mirror inventory IS the engine's resolution of the same patterns
        # release.projection extracts by AST — two independent readers, one set
        self.assertEqual(census["inventory"],
                         len(vw._projection_source_files(ROOT)))
        self.assertEqual(census["inventory"], len(rp._mirror_inventory(ROOT)))
        self.assertGreater(census["inventory"], 0,
                           "an empty inventory makes the identity below "
                           "vacuous — the disclosure would be decoration")
        projected = (census["inventory"] - census["absent"]
                     - census["identical"] - census["divergent"])
        self.assertGreaterEqual(projected, 0, census)
        self.assertEqual(
            census["inventory"],
            census["absent"] + census["identical"] + census["divergent"]
            + projected, census)
        self.assertEqual(len(census["undeclared_in_scope"]),
                         len(set(census["undeclared_in_scope"])), census)
        self.assertLessEqual(len(census["undeclared_in_scope"]),
                             census["divergent"])
        self.assertLessEqual(census["declared"], census["divergent"], census)
        for key in ("inventory", "identical", "divergent", "absent",
                    "declared", "undeclared_out_of_scope"):
            with self.subTest(count=key):
                self.assertIsInstance(census[key], int)
                self.assertGreaterEqual(census[key], 0)

    def test_engine_copy_really_is_divergent(self):
        """The declaration is only honest while the divergence is real."""
        config = json.loads((ROOT / CONFIG_REL).read_text(encoding="utf-8"))
        entry = next(item for item in config["declared_legacy_snapshots"]
                     if item["id"] == "fixture-engine")
        self.assertNotEqual((ROOT / entry["path"]).read_bytes(),
                            (ROOT / entry["canonical"]).read_bytes())

    def test_check_projections_reports_the_legacy_face(self):
        facts = check_projections(ROOT).as_dict()
        self.assertIn("legacy_snapshot_check", facts)
        self.assertEqual(facts["declared_legacy_snapshots"], 10)

    # ── falsifiability: the three failure modes ─────────────────────────
    def _fixture(self, entries, files):
        """Build a temp root + config carrying `entries` and `files`."""
        tmp = tempfile.TemporaryDirectory(prefix="feat040_legacy_")
        root = Path(tmp.name)
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        config = root / "config.json"
        config.write_text(json.dumps({"declared_legacy_snapshots": entries}),
                          encoding="utf-8")
        return tmp, root, config

    def test_missing_declared_path_fails(self):
        tmp, root, config = self._fixture(
            [{"id": "gone", "path": "fixture/a.py", "canonical": "canon/a.py",
              "scope": "RISK-039", "reason": "legacy copy"}],
            {"canon/a.py": "canonical\n"})
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertEqual(result["missing"], ["fixture/a.py"])
        self.assertTrue(any("points at nothing" in issue
                            for issue in result["issues"]))

    def test_converged_declaration_fails(self):
        tmp, root, config = self._fixture(
            [{"id": "same", "path": "fixture/a.py", "canonical": "canon/a.py",
              "scope": "RISK-039", "reason": "legacy copy"}],
            {"canon/a.py": "identical\n", "fixture/a.py": "identical\n"})
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertEqual(result["converged"], ["fixture/a.py"])
        self.assertTrue(any("CONVERGED" in issue for issue in result["issues"]))

    def test_unexplained_declaration_fails(self):
        tmp, root, config = self._fixture(
            [{"id": "bare", "path": "fixture/a.py",
              "canonical": "canon/a.py"}],
            {"canon/a.py": "canonical\n", "fixture/a.py": "other\n"})
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertTrue(any("not auditable" in issue
                            for issue in result["issues"]))

    def test_empty_block_is_legitimate(self):
        tmp, root, config = self._fixture([], {})
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertTrue(result["pass"])
        self.assertEqual(result["checked"], 0)

    def test_non_list_block_fails_closed(self):
        tmp, root, config = self._fixture({}, {})
        with tmp:
            config.write_text(json.dumps(
                {"declared_legacy_snapshots": {"oops": True}}),
                encoding="utf-8")
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertTrue(any("must be a list" in issue
                            for issue in result["issues"]))

    def test_unreadable_registry_fails_closed(self):
        tmp, root, config = self._fixture([], {})
        with tmp:
            config.write_text("{not json", encoding="utf-8")
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertTrue(any("unreadable" in issue for issue in result["issues"]))


class BackportPolicyTests(unittest.TestCase):
    """FIX-381 — the controlled-backport institution is machine-guarded."""

    LEDGER_ENTRY = {
        "fix_id": "FIX-999", "source_fix": "FIX-001",
        "approved": "review-FIX-999-CODE-R0 APPROVED/0",
        "anchor_symbol": "guarded_region", "marker": "FIX-999 (backport",
        "reason": "sync the guarded region",
        "dual_run": "probe red->green on both legs",
        "coupling_reviewed": "no registry-path move; no third copy",
    }
    COPY_SOURCE = (
        "def guarded_region(line):\n"
        '    """FIX-999 (backport of the FIX-001 fix into this declared'
        " legacy snapshot).\"\"\"\n"
        "    return line\n"
    )
    POLICY = {
        "trigger": {"evaluate_when": "a canonical fix touches a declared copy"},
        "ledger": {"location": "approved_backports"},
        "dual_run_contract": {"requirement": "probe passes in both trees"},
        "coupling_check": {"when": "before approval"},
        "replay_path": {"rule": "regeneration is not a supported write"},
    }

    def _root_with(self, *, entries, files, policy="default"):
        """Build a temp root + config; `policy="default"` ships the valid one."""
        tmp = tempfile.TemporaryDirectory(prefix="fix381_backport_")
        root = Path(tmp.name)
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        config = {"declared_legacy_snapshots": entries}
        if policy == "default":
            config["legacy_snapshot_backport_policy"] = dict(self.POLICY)
        elif policy is not None:
            config["legacy_snapshot_backport_policy"] = policy
        config_path = root / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        return tmp, root, config_path

    # ── shipped registry: the institution is live, not decorative ────────
    def test_shipped_policy_and_ledger_are_live(self):
        result = check_legacy_snapshots(ROOT)
        self.assertTrue(result["pass"], result["issues"])
        face = result["backport_ledger"]
        self.assertTrue(face["policy_declared"])
        self.assertGreaterEqual(face["ledger_entries"], 1)
        self.assertEqual(face["anchors_resolved"], face["ledger_entries"])

    def test_shipped_ledger_entry_resolves_in_the_real_copy(self):
        config = json.loads((ROOT / CONFIG_REL).read_text(encoding="utf-8"))
        entry = next(item for item in config["declared_legacy_snapshots"]
                     if item["id"] == "fixture-engine")
        ledger = entry["approved_backports"]
        self.assertTrue(ledger)
        copy_text = (ROOT / entry["path"]).read_text(encoding="utf-8",
                                                     errors="replace")
        for item in ledger:
            self.assertIn(item["anchor_symbol"], copy_text,
                          f"{item['fix_id']} anchor no longer in the copy")
            self.assertIn(item["marker"], copy_text,
                          f"{item['fix_id']} patch marker no longer in the copy")

    # ── policy block falsifiability ──────────────────────────────────────
    def test_hollow_policy_block_fails(self):
        hollow = {**self.POLICY, "trigger": {}}
        tmp, root, config = self._root_with(
            entries=[], files={}, policy=hollow)
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertTrue(any("hollow" in issue and "trigger" in issue
                            for issue in result["issues"]))

    def test_policy_block_non_object_fails(self):
        tmp, root, config = self._root_with(entries=[], files={},
                                            policy="prose only")
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertTrue(any("must be an object" in issue
                            for issue in result["issues"]))

    # ── ledger entry falsifiability ──────────────────────────────────────
    def _ledger_root(self, ledger, copy_source, canon_source="canonical\n"):
        return self._root_with(
            entries=[{"id": "snap", "path": "fixture/copy.py",
                      "canonical": "canon/copy.py", "scope": "RISK-039",
                      "reason": "legacy copy",
                      "approved_backports": ledger}],
            files={"canon/copy.py": canon_source,
                   "fixture/copy.py": copy_source})

    def test_valid_ledger_passes(self):
        tmp, root, config = self._ledger_root([dict(self.LEDGER_ENTRY)],
                                              self.COPY_SOURCE)
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertTrue(result["pass"], result["issues"])
        self.assertEqual(result["backport_ledger"]["ledger_entries"], 1)
        self.assertEqual(result["backport_ledger"]["anchors_resolved"], 1)

    def test_ledger_entry_missing_fields_fails(self):
        hollow_entry = {key: value for key, value in self.LEDGER_ENTRY.items()
                        if key not in ("reason", "dual_run")}
        tmp, root, config = self._ledger_root([hollow_entry], self.COPY_SOURCE)
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertTrue(any("hollow" in issue and "reason" in issue
                            for issue in result["issues"]))

    def test_stale_anchor_fails(self):
        renamed = self.COPY_SOURCE.replace("def guarded_region(",
                                           "def renamed_region(")
        tmp, root, config = self._ledger_root([dict(self.LEDGER_ENTRY)],
                                              renamed)
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertTrue(any("no longer resolves" in issue
                            for issue in result["issues"]))

    def test_missing_marker_fails(self):
        reverted = self.COPY_SOURCE.replace("FIX-999 (backport", "FIX-001")
        tmp, root, config = self._ledger_root([dict(self.LEDGER_ENTRY)],
                                              reverted)
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertTrue(any("not present" in issue
                            for issue in result["issues"]))

    def test_non_list_ledger_fails(self):
        tmp, root, config = self._ledger_root("prose", self.COPY_SOURCE)
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertTrue(any("non-empty list" in issue
                            for issue in result["issues"]))

    # ── converged disposition refinement (semantics review landed) ──────
    def test_converged_backport_bearing_snapshot_names_replay_disposition(self):
        tmp, root, config = self._ledger_root(
            [dict(self.LEDGER_ENTRY)], "identical\n", canon_source="identical\n")
        with tmp:
            result = check_legacy_snapshots(root, config)
        self.assertFalse(result["pass"])
        self.assertEqual(result["converged"], ["fixture/copy.py"])
        replay = [issue for issue in result["issues"]
                  if "replay" in issue and "approved_backports ledger" in issue]
        self.assertTrue(replay,
                        "a converged backport-bearing snapshot must name the "
                        f"replay-or-promote disposition: {result['issues']}")


if __name__ == "__main__":
    unittest.main()
