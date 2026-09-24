"""FEAT-061 — independent verifier guard tests (Layer 6).

Runs the verifier as a SUBPROCESS (the independence-faithful invocation)
and proves:

  * the negative injection suite: all seven injected faults REJECTED
    (ARCH-04 负向验收);
  * verify PASS on a consistent shadow world, with the proof-pack minimum
    sections + a real independence declaration (ARCH-10);
  * verify FAIL when the shadow store smuggles a content change (历史勘正
    不得混入格式转换);
  * verify FAIL on unresolved lines (ARCH-05 解析不明行阻断);
  * reverse-check PASS on a faithful rollback export (ARCH-07);
  * the forbidden-import environment gate fires when a new-implementation
    module is importable (independence rule ②, negative case ⑦).

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_decision_migration_verify.py -v
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

VERIFY_SCRIPT = _INFRA_DIR / "decision_migration_verify.py"

LEGACY_HEADER = ("| 编号 | 日期 | 主题 | 背景 | 决策内容 | 备选方案 "
                 "| 选择原因 | 影响范围 | 决策人 | 关联任务 | 后续动作 |\n")
SEPARATOR = ("| --- | --- | --- | --- | --- | --- | --- | --- | --- "
             "| --- | --- |\n")


def _seed_md() -> str:
    return (
        "# 当前项目决策记录\n\n"
        + LEGACY_HEADER + SEPARATOR
        + "| DEC-147 | 2026-08-22 | 旧 11 列行样本 | 背景 | 决策内容 | 备选"
          " | 原因 | 范围 | Coordinator | FIX-1 | 动作 |\n"
        + "| DEC-237 | 2026-09-25 | Coordinator | FEAT-061 arch 复核结论"
          " | version-plan C1（机器写入：governance-store decision-append "
          "op-b13202de；schema v1） |\n")


def _verifier(args):
    proc = subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT)] + args,
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120)
    return proc.returncode, json.loads(proc.stdout)


def _make_world(tmp: Path, *, md_text=None, shadow_records_patch=None,
                ledger=None):
    gov = tmp / ".governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "decision-log.md").write_bytes(
        (md_text if md_text is not None else _seed_md()).encode("utf-8"))
    if ledger is not None:
        (gov / "governance-store-ops.json").write_bytes(
            json.dumps(ledger, ensure_ascii=False).encode("utf-8"))
    migration_id = "M-V"
    migration_root = tmp / ".decision-migration"
    code, payload = _verifier([
        "sample", "--gov-dir", str(gov), "--migration-id", migration_id,
        "--migration-root", str(migration_root)])
    assert code == 0, payload
    # Shadow conversion is performed INSIDE the test with the verifier's
    # own legacy parser (data-level fixture; the point of these tests is
    # the verifier's gates, not the controller).
    sys.path.insert(0, str(_INFRA_DIR))
    import decision_migration_verify as vmod
    items = vmod.classify_lines_legacy(
        (gov / "decision-log.md").read_bytes().decode("utf-8"))
    records = []
    for item in items:
        if item["kind"] == "record":
            records.append({
                "id": item["id"],
                "shape": ("live5" if len(item["cells"]) == 5 else
                          ("legacy11" if len(item["cells"]) == 11
                           else "variant")),
                "cells": item["cells"], "row_raw": item["row_raw"],
                "source_line": item["line_no"], "provenance": None,
            })
    if shadow_records_patch:
        records = shadow_records_patch(records)
    store = {
        "format": "decision-store", "schema_version": 1,
        "records": records,
        "items": [{"kind": i["kind"], "id": i.get("id"),
                   "text": i.get("text")} for i in items],
    }
    shadow_dir = migration_root / migration_id / "shadow"
    shadow_dir.mkdir(parents=True, exist_ok=True)
    (shadow_dir / "decision-store.json").write_bytes(
        (json.dumps(store, ensure_ascii=False, indent=2)
         + "\n").encode("utf-8"))
    return gov, migration_id, migration_root


class TestIndependentVerifier(unittest.TestCase):

    def test_negative_suite_all_rejected(self):
        code, payload = _verifier(["negative-suite"])
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["verdict"], "PASS")
        self.assertTrue(all(r["rejected"] for r in payload["results"]))
        self.assertEqual(len(payload["results"]), 7)

    def test_verify_pass_and_proof_pack_sections(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="feat061-v-"))
        gov, migration_id, migration_root = _make_world(tmp)
        code, report = _verifier([
            "verify", "--gov-dir", str(gov), "--migration-id", migration_id,
            "--migration-root", str(migration_root)])
        self.assertEqual(code, 0, report)
        self.assertEqual(report["verdict"], "PASS")
        for section in ("input_snapshot_identity", "origin_manifest",
                        "tool_and_dependency_identity",
                        "normalization_rules", "line_coverage_report",
                        "per_id_field_diffs", "ops_reconciliation",
                        "independence_declaration"):
            self.assertIn(section, report, section)
        declaration = report["independence_declaration"]
        self.assertTrue(declaration["shared_dependencies"])
        self.assertTrue(declaration["residual_risks"])
        self.assertNotEqual(declaration["declaration"].strip().lower(),
                            "独立：是")
        # Coverage classified every line; zero unresolved.
        self.assertEqual(
            report["line_coverage_report"]["unresolved_lines"], [])

    def test_verify_fails_on_smuggled_content_change(self):
        import tempfile

        def patch(records):
            for record in records:
                if record["id"] == "DEC-237":
                    record["cells"] = list(record["cells"])
                    record["cells"][3] += "（被偷换的内容）"
            return records

        tmp = Path(tempfile.mkdtemp(prefix="feat061-v-"))
        gov, migration_id, migration_root = _make_world(
            tmp, shadow_records_patch=patch)
        code, report = _verifier([
            "verify", "--gov-dir", str(gov), "--migration-id", migration_id,
            "--migration-root", str(migration_root)])
        self.assertEqual(code, 1)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(report["per_id_field_diffs"]["diffs"])

    def test_verify_fails_on_unresolved_line(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="feat061-v-"))
        gov, migration_id, migration_root = _make_world(
            tmp, md_text=_seed_md() + "| 无锚点手写行 |\n")
        code, report = _verifier([
            "verify", "--gov-dir", str(gov), "--migration-id", migration_id,
            "--migration-root", str(migration_root)])
        self.assertEqual(code, 1)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertTrue(
            report["line_coverage_report"]["unresolved_lines"])

    def test_verify_fails_on_dangling_op(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="feat061-v-"))
        gov, migration_id, migration_root = _make_world(tmp, ledger={
            "operations": {"op-ghost": {
                "command": "decision-append", "status": "ok",
                "input_fingerprint": "x"}}})
        code, report = _verifier([
            "verify", "--gov-dir", str(gov), "--migration-id", migration_id,
            "--migration-root", str(migration_root)])
        self.assertEqual(code, 1)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(report["ops_reconciliation"]["ops_missing_in_world"],
                         ["op-ghost"])

    def test_reverse_check_passes_on_faithful_export(self):
        import tempfile
        sys.path.insert(0, str(_INFRA_DIR))
        import decision_migration_verify as vmod
        import decision_repository as drepo
        tmp = Path(tempfile.mkdtemp(prefix="feat061-v-"))
        gov, migration_id, migration_root = _make_world(tmp)
        store = json.loads(
            (migration_root / migration_id / "shadow"
             / "decision-store.json").read_bytes().decode("utf-8"))
        export = migration_root / migration_id / "rollback-export.md"
        # The fixture export is rendered by the repository codec (fixture
        # construction only — the VERDICT still comes from the verifier
        # subprocess and its own legacy parser).
        export.write_bytes(drepo.render_markdown(store).encode("utf-8"))
        code, report = _verifier([
            "reverse-check", "--gov-dir", str(gov), "--migration-id",
            migration_id, "--migration-root", str(migration_root)])
        self.assertEqual(code, 0, report)
        self.assertEqual(report["verdict"], "PASS")

    def test_environment_gate_fires_on_forbidden_import(self):
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="feat061-v-"))
        sys.path.insert(0, str(_INFRA_DIR))
        import decision_migration_verify as vmod
        saved = dict(sys.modules)
        try:
            sys.modules["governance_store"] = type(sys)("governance_store")
            report = vmod.environment_report(tmp)
            issues = vmod._env_gate(report)
        finally:
            sys.modules.clear()
            sys.modules.update(saved)
        self.assertTrue(issues)
        self.assertIn("self-signed", issues[0])


if __name__ == "__main__":
    unittest.main()
