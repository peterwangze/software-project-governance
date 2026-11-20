"""Subprocess contracts for the Claude and Codex adapter launchers."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ADAPTERS = Path(__file__).resolve().parents[4] / "adapters"


class AdapterReportTests(unittest.TestCase):
    def test_isolated_launch_uses_its_own_manifest(self):
        with tempfile.TemporaryDirectory() as host:
            for platform in ("Claude", "Codex"):
                with self.subTest(platform=platform):
                    adapter = ADAPTERS / platform.lower()
                    manifest = json.loads((adapter / "adapter-manifest.json").read_text(encoding="utf-8"))
                    result = subprocess.run(
                        [sys.executable, "-I", str(adapter / "launch.py")],
                        cwd=host, capture_output=True, text=True, timeout=15,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    lines = result.stdout.splitlines()
                    self.assertEqual(lines[0], f"== {platform} Adapter Launcher ==")
                    self.assertEqual(lines[-1], f" - command: {manifest['validation']['command']}")

    def test_late_validation_failure_preserves_partial_report(self):
        with tempfile.TemporaryDirectory() as host:
            adapters = Path(host) / "plugin tree" / "adapters"
            adapter = adapters / "codex"
            adapter.mkdir(parents=True)
            shutil.copy2(ADAPTERS / "manifest_report.py", adapters)
            shutil.copy2(ADAPTERS / "codex/launch.py", adapter)
            manifest = json.loads((ADAPTERS / "codex/adapter-manifest.json").read_text(encoding="utf-8"))
            manifest["native_entry"] = {"z": "last", "a": "first"}
            manifest["runtime_e2e"] = {}
            (adapter / "adapter-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "-I", str(adapter / "launch.py")],
                cwd=host, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                result.stdout.splitlines()[-4:],
                ["native_entry:", " - a: first", " - z: last", "runtime_e2e:"],
            )
            self.assertEqual(
                result.stderr.splitlines()[-1],
                "ValueError: adapter manifest must define a non-empty runtime_e2e object",
            )
