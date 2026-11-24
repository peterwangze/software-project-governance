"""Exercise model-facing material discovery through a real isolated host."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

INFRA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(INFRA))
from loop_materials import lookup
from loop_workflow import start
from review_record import write_review_record


class MaterialLookupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.gov = self.root / ".governance"
        start(self.root, unit_id="receipt", task="FIX-001", tier="inner", goal="Compare totals",
              acceptance="The exported total can be checked.")
        self.log = self.gov / "evidence-log.md"
        self.log.write_text("# Evidence\n", encoding="utf-8")

    def cli(self, *args, ok=True):
        proc = subprocess.run([sys.executable, "-X", "utf8", str(INFRA / "verify_workflow.py"),
                               "--project-root", str(self.root), *args], cwd=self.root, capture_output=True,
                              encoding="utf-8")
        self.assertEqual(ok, proc.returncode == 0, proc.stdout + proc.stderr)
        if args[:2] == ("loop", "materials"):
            self.assertLessEqual(len(proc.stdout.encode("utf-8")), 4096)
        return json.loads(proc.stdout)

    def read(self, *args, unit="receipt"):
        return self.cli("loop", "materials", "--unit", unit, *args)

    def append(self, description, artifacts, refs=None):
        self.cli("evidence-append", "--task", "FIX-001", "--type", "EVD", "--description",
                         "目标对齐：核对导出的任务材料，保证从本轮工作单元逐步定位到登记时保留的原件。" + description,
                         "--basis", "PRIVATE_BASIS", "--artifacts", artifacts,
                         *(("--refs", refs) if refs else ()), "--conclusion", "observed")

    def test_noise_archive_and_exact_task_scoping(self):
        (self.root / "对账.myformat").write_bytes(b"PRIVATE_ORIGINAL")
        self.append("对账核销", "对账.myformat", "repo_file:对账.myformat")
        first = self.read("--query", "核销")
        self.assertEqual(first["items"][0]["ref"], "EVD-1")
        self.assertNotIn("PRIVATE", str(first))
        row = self.log.read_text(encoding="utf-8").splitlines()[-1]
        archive = self.gov / "archive/evidence"
        archive.mkdir(parents=True)
        (archive / "batch.md").write_text(row + "\n", encoding="utf-8")
        self.log.write_text("\n".join(
            f"| EVD-{index+10} | FIX-001 | EVD | unrelated {index} | PRIVATE | unrelated.log | QA | 2026 | — | seen |"
            for index in range(1000)) + "\n" + row.replace("FIX-001", "FIX-0010").replace("EVD-1 ", "EVD-9999 "),
            encoding="utf-8")
        self.assertEqual(self.read("--query", "核销"), first)
        self.assertEqual(self.read("--ref", "EVD-9999")["state"], "empty")
        self.assertEqual(self.read("--query", "对账.myformat")["items"][0]["ref"], "EVD-1")
        detail = self.read("--ref", "EVD-1")["items"][0]
        self.assertEqual(detail["scope"], "task")
        self.assertIn("archive/evidence/batch.md", detail["source"])
        self.assertEqual(detail["locations"], [{"role": "repo_file", "target": "对账.myformat", "availability": "present"}])
        (self.root / "对账.myformat").unlink()
        self.assertEqual(self.read("--ref", "EVD-1")["items"][0]["locations"][0]["availability"], "missing")
        with patch.object(Path, "rglob", side_effect=AssertionError("recursive scan")), \
                patch("loop_materials._evidence_records", side_effect=AssertionError("opened the ledger")):
            self.assertEqual(lookup(self.root, "receipt")["state"], "empty")

    def test_learning_scope(self):
        (self.root / "audio.cue").write_bytes(b"PRIVATE_AUDIO")
        self.cli("loop", "learn", "--unit", "receipt", "--id", "trace", "--kind", "note",
                 "--observation", "发现响铃误差", "--action", "核对时间戳", "--validation", "原件可比较",
                 "--evidence", "audio.cue")
        self.assertEqual(self.read()["items"], [])
        self.assertEqual(self.read("--query", "时间戳")["items"][0]["scope"], "unit")
        view = self.read("--ref", "learn:trace")["items"][0]
        self.assertEqual(view["locations"][0]["target"], "audio.cue")
        self.assertIn("recorded_sha256", view["locations"][0])
        start(self.root, unit_id="other", task="FIX-001", tier="inner", goal="Another result", acceptance="Can inspect")
        self.assertEqual(self.read("--ref", "learn:trace", unit="other")["items"], [])
        self.assertEqual(self.read("--ref", "../../audio.cue")["state"], "empty")

    def test_unrelated_observations_do_not_displace_a_decision(self):
        (self.root / "sample.csv").write_text("3,7", encoding="utf-8")
        args = ["loop", "learn", "--unit", "receipt", "--action", "rerun", "--validation", "compare totals",
                "--evidence", "sample.csv"]
        self.cli(*args, "--id", "route", "--kind", "decision", "--observation", "receipt total")
        before = self.read()
        self.cli(*args, "--id", "scratch", "--kind", "note", "--observation", "unrelated")
        runtime = self.gov / "flow-unit-runtime.json"
        data = json.loads(runtime.read_bytes())
        records = data["flow_units"][0]["learning"]
        note = records[-1]
        records.extend(dict(note, id=f"scratch-{index}") for index in range(1000))
        runtime.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(before, self.read())
        self.assertEqual(before["items"][0]["ref"], "learn:route")
        self.log.write_text("| EVD-1 | FIX-001 | EVD | receipt total | evidence | file | reviewer | date | — | done |",
                            encoding="utf-8")
        self.assertEqual(self.read("--query", "receipt total")["items"][0]["ref"], "learn:route")

    def test_gate_receipt_to_original_report_and_missing_receipt(self):
        (self.root / "original.md").write_text("**审查结论**: **APPROVED**", encoding="utf-8")
        receipt = write_review_record(task_id="FIX-001", round_n=0, result="APPROVED", reviewer="Reviewer",
                                      report_path="original.md", root=self.root, unit_id="receipt", require_loop=True)
        self.assertNotIn("error", receipt, receipt)
        ref = self.read()["items"][0]["ref"]
        item = self.read("--ref", ref)["items"][0]
        self.assertEqual(item["locations"][-1]["target"], "original.md")
        self.assertEqual(self.read("--ref", "REVIEW-FIX-001-R0")["items"], [item])
        mirror = self.root / item["locations"][0]["target"]
        mirror.write_text("\n".join(line for line in mirror.read_text(encoding="utf-8").splitlines()
                                    if not line.startswith("- report_sha256:")), encoding="utf-8")
        (self.root / "original.md").write_text("changed", encoding="utf-8")
        damaged = self.read("--ref", ref)["items"][0]["locations"]
        self.assertEqual(damaged[0]["availability"], "binding_unconfirmed")
        self.assertEqual(damaged[1], item["locations"][1])
        mirror.unlink()
        self.assertEqual(self.read("--ref", ref)["items"][0]["locations"][0]["availability"], "missing")

    def test_record_only_report_and_delta_are_scoped_observations(self):
        start(self.root, unit_id="other", task="FIX-001", tier="inner", goal="Another result", acceptance="Can inspect")
        for name in ("report.md", "earlier.md"):
            (self.root / name).write_text("**APPROVED**\nPRIVATE_REPORT", encoding="utf-8")
        receipt = write_review_record(task_id="FIX-001", round_n=0, result="APPROVED", reviewer="Reviewer",
                                      report_path="report.md", root=self.root, record_only=True,
                                      unit_id="receipt", scope="delta", delta_base="earlier.md")
        self.assertNotIn("error", receipt, receipt)
        reply = self.read("--ref", "REVIEW-FIX-001-R0")
        item = reply["items"][0]
        self.assertEqual(item["status"], "observation")
        self.assertEqual([p["role"] for p in item["locations"]], ["receipt", "report", "delta_base"])
        self.assertNotIn("PRIVATE_REPORT", str(reply))
        self.assertEqual(self.read()["state"], "empty")
        self.assertEqual(self.read("--ref", item["ref"], unit="other")["items"], [])
        self.assertEqual(self.read("--query", "复审")["items"][0]["ref"], item["ref"])
        (self.root / "earlier.md").unlink()
        self.assertEqual(self.read("--ref", item["ref"])["items"][0]["locations"][-1]["availability"], "missing")
        self.cli("review-record", "--task", "FIX-001", "--round", "1", "--result", "APPROVED",
                 "--reviewer", "Reviewer", "--unit", "receipt", "--record-only", "--scope", "delta",
                 "--report", "report.md", "--delta-base", "HEAD~1..HEAD")
        delta = self.read("--ref", "REVIEW-FIX-001-R1")["items"][0]["locations"][-1]
        self.assertEqual(delta, {"role": "delta_base", "kind": "git_range", "target": "HEAD~1..HEAD",
                                 "availability": "not_checked"})

    def test_scoped_revision_and_replaced_decision(self):
        (self.root / "measure.json").write_text("{}", encoding="utf-8")
        (self.root / "candidate.txt").write_text("sample", encoding="utf-8")
        common = ["loop", "learn", "--unit", "receipt", "--kind", "decision", "--action", "compare",
                  "--validation", "equal", "--evidence", "measure.json", "--candidate", "candidate.txt",
                  "--criterion", "acceptance"]
        self.cli(*common, "--id", "first", "--observation", "previous totals")
        self.cli(*common, "--id", "second", "--observation", "actual totals", "--supersedes", "first")
        self.assertEqual(self.read("--ref", "learn:first")["items"][0]["status"], "superseded")
        self.assertEqual(self.read("--ref", "learn:second")["items"][0]["supersedes"], "learn:first")
        rev = {"id": "sum-changed", "kind": "counterevidence", "unit": "receipt", "base_revision": 0,
               "actor": "QA", "reason": "sum differs", "criteria": {"acceptance": "The exported total can be checked."}}
        (self.root / "revision.json").write_text(json.dumps(rev), encoding="utf-8")
        self.cli("loop", "revise", "--unit", "receipt", "--evidence", "revision.json")
        item = self.read("--query", "反证")["items"][0]
        self.assertEqual(item["status"], "counterevidence")
        self.assertEqual(self.read("--ref", item["ref"])["items"][0]["locations"][0]["target"], "revision.json")

    def test_archived_only_identity_is_rejected_before_writes_and_explicit_successor_is_allowed(self):
        (self.root / "approval.md").write_text("**审查结论**: **APPROVED**", encoding="utf-8")
        record = write_review_record(task_id="FIX-001", round_n=0, result="APPROVED", reviewer="Reviewer",
                                     report_path="approval.md", root=self.root, unit_id="receipt", require_loop=True)
        self.assertNotIn("error", record)
        archive = self.gov / "archive/evidence"
        archive.mkdir(parents=True)
        (archive / "past.md").write_text(
            "| EVD-9 | FIX-777, FIX-001 | EVD | old work | basis | old.log | QA | day | — | done |\n",
            encoding="utf-8")
        inputs = ["loop", "start", "--unit", "FIX-777", "--tier", "inner", "--goal", "Different work",
                  "--acceptance", "Different evidence"]
        def contents():
            return {p.relative_to(self.root): p.read_bytes() for p in self.gov.rglob("*") if p.is_file()}
        before = contents()
        self.assertIn("archive", self.cli(*inputs, ok=False)["error"])
        self.assertEqual(contents(), before)
        self.cli("loop", "start", "--unit", "new-round", "--task", "FIX-001", "--after", "receipt", "--tier", "inner")

    def test_bounded_locations_free_text_and_invalid_input(self):
        ledger = "\n".join([
            "| EVD-1 | FIX-001 | EVD | red | basis | 现场复核结果见本行，合计 42.00 元 | QA | day | — | done |",
            "| EVD-2 | FIX-001 | EVD | red | basis | a.wav; b.png; missing.txt; another.csv | QA | day | — | done |",
            "| EVD-3 | FIX-001 | EVD | red | basis | refs[repo_file:../outside.txt=resolvable] | QA | day | — | done |",
            "| EVD-4 | FIX-001 | EVD | red | basis | " + "长" * 5000 + ".txt | QA | day | — | done |",
        ])
        self.log.write_text(ledger, encoding="utf-8")
        self.assertEqual(self.read("--ref", "EVD-1")["items"][0]["locations"], [])
        page = self.read("--ref", "EVD-2")
        detail = page["items"][0]
        self.assertEqual(len(detail["locations"]), 3)
        self.assertTrue(detail["locations_omitted"])
        self.assertEqual(self.read("--query", "another.csv")["items"][0]["ref"], "EVD-2")
        end = self.read("--ref", "EVD-2", "--offset", str(page["next_offset"]))
        self.assertEqual(end["items"][0]["locations"][0]["target"], "another.csv")
        self.assertNotIn("next_offset", end)
        self.assertEqual(self.read("--ref", "EVD-3")["items"][0]["locations"][0]["availability"], "unverifiable")
        long_target = self.read("--ref", "EVD-4")["items"][0]
        self.assertTrue(long_target["locations_omitted"])
        self.assertEqual(long_target["locations"], [])
        search = self.read("--query", "red")
        self.assertEqual(len(search["items"]), 3)
        self.assertTrue(search["more_matches"])
        invalid = self.cli("loop", "materials", "--unit", "unknown", ok=False)
        self.assertEqual(invalid["state"], "invalid")

    def test_free_text_counts_and_dates_do_not_become_missing_paths(self):
        relative = "核查 记录/结果 12.csv"
        original = self.root / relative
        original.parent.mkdir()
        original.write_bytes(b"12")
        ledger = [
            "现场复核结果见本行，通过 12/12 项",
            "2026/11/24 计数通过12/12项",
            "检查 12 / 12 项",
            relative,
            "refs[repo_file:12/12=resolvable]",
        ]
        self.log.write_text("\n".join(
            f"| EVD-{number} | FIX-001 | EVD | totals | basis | {entry} | QA | day | — | done |"
            for number, entry in enumerate(ledger, 1)), encoding="utf-8")
        for number in range(1, 4):
            self.assertEqual(self.read("--ref", f"EVD-{number}")["items"][0]["locations"], [])
        actual = self.read("--ref", "EVD-4")["items"][0]["locations"]
        self.assertEqual(actual, [{"role": "artifact", "target": relative, "availability": "present"}])
        missing = self.read("--ref", "EVD-5")["items"][0]["locations"]
        self.assertEqual(missing, [{"role": "repo_file", "target": "12/12", "availability": "missing"}])


if __name__ == "__main__":
    unittest.main()
