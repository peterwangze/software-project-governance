"""Exercise the capability checks consumed by health checks in an npm installation."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[4]
REQUIREMENT = Path("docs/requirements/capability-discovery-orchestration-0.45.0.md")


class PackagedCapabilityContextTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("npm"), "npm is required to test the distributed package")
    def test_packaged_checks_accept_the_contract_and_detect_damaged_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            env = dict(os.environ, npm_config_cache=str(work / "npm-cache"))
            packed = subprocess.run(
                [shutil.which("npm"), "pack", "--offline", "--ignore-scripts", "--json",
                 "--pack-destination", str(work)],
                cwd=ROOT, env=env, capture_output=True, encoding="utf-8", check=True,
            )
            archive = work / json.loads(packed.stdout)[0]["filename"]
            with tarfile.open(archive) as bundle:
                bundle.extractall(work, filter="data")

            package = work / "package"
            entry = package / "skills/software-project-governance/infra/verify_workflow.py"
            contract = package / REQUIREMENT
            self.assertTrue(contract.is_file(), REQUIREMENT)
            self.assertEqual(contract.read_bytes(), (ROOT / REQUIREMENT).read_bytes())
            for damaged in (False, True):
                if damaged:
                    contract.write_text("# Incomplete capability contract\n", encoding="utf-8")
                for command, issue in (
                    ("capability-context", "missing capability context token"),
                    ("check-host-capability-context", "missing FIX-117 token"),
                ):
                    with self.subTest(command=command, damaged=damaged):
                        result = subprocess.run(
                            [sys.executable, "-B", str(entry), command, "--fail-on-issues"],
                            cwd=work, capture_output=True, encoding="utf-8",
                        )
                        self.assertEqual(result.returncode, 1 if damaged else 0,
                                         result.stdout + result.stderr)
                        if damaged:
                            self.assertIn(issue, result.stdout)
