"""Install registry selection through the public plugin freshness command."""

import io
import json
import os
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verify_workflow


class PluginFreshnessTests(unittest.TestCase):
    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        base = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        home = base / "isolated user home"
        package = base / "plugin"
        self.skill = package / "skills/software-project-governance/SKILL.md"
        home_registry = home / ".claude"
        plugin_registry = package / ".claude-plugin"
        home_registry.mkdir(parents=True)
        plugin_registry.mkdir(parents=True)
        self.local = plugin_registry / "installed_plugins.json"
        self.global_registry = home_registry / "installed_plugins.json"
        (plugin_registry / "marketplace.json").write_text(self.registry("2.0"), encoding="utf-8")
        stack.enter_context(patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}))
        stack.enter_context(patch.object(verify_workflow, "ROOT", package))

    @staticmethod
    def registry(version):
        return json.dumps({"plugins": [{"name": "software-project-governance", "version": version}]})

    def check_command(self, installed, status, expected_exit=0, source="2.0"):
        output = io.StringIO()
        with redirect_stdout(output):
            try:
                verify_workflow.main(["check-plugin-freshness"])
            except SystemExit as error:
                code = error.code
            else:
                code = 0
        self.assertEqual(code, expected_exit)
        self.assertIn(f"Installed: {installed} (", output.getvalue())
        self.assertIn(f"Source:    {source} (", output.getvalue())
        self.assertIn(f"Status:    {status}", output.getvalue())

    def test_absent_installation_is_reported(self):
        self.check_command("unknown", "UNKNOWN (plugin not installed via marketplace?)")
        self.assertFalse(self.global_registry.exists())

    def test_home_installation_can_be_current(self):
        self.global_registry.write_text(self.registry("2.0"), encoding="utf-8")
        self.check_command("2.0", "UP TO DATE")

    def test_package_installation_wins_over_home(self):
        self.global_registry.write_text(self.registry("2.0"), encoding="utf-8")
        self.local.write_text(self.registry("1.0"), encoding="utf-8")
        self.check_command("1.0", "OUTDATED", expected_exit=1)

    def test_invalid_package_record_keeps_existing_unknown_result(self):
        self.global_registry.write_text(self.registry("2.0"), encoding="utf-8")
        self.local.write_text("{", encoding="utf-8")
        self.check_command("unknown", "UNKNOWN (plugin not installed via marketplace?)")

    def test_invalid_home_record_is_reported(self):
        self.global_registry.write_text("{", encoding="utf-8")
        self.check_command("unknown", "UNKNOWN (plugin not installed via marketplace?)")

    def test_skill_is_authoritative_over_a_stale_marketplace_projection(self):
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text("---\nmetadata:\n  version: 2.1.0\n---\n", encoding="utf-8")
        self.local.write_text(self.registry("2.1.0"), encoding="utf-8")
        self.check_command("2.1.0", "UP TO DATE", source="2.1.0")
        self.skill.write_text("---\nmetadata:\n  version: broken\n---\n", encoding="utf-8")
        self.check_command("2.1.0", "UNKNOWN (source version unavailable)", source="unknown")

    def test_missing_or_invalid_source_cannot_establish_a_mismatch(self):
        marketplace = self.local.with_name("marketplace.json")
        self.local.write_text(self.registry("2.0"), encoding="utf-8")
        for text in (None, "{", "[]", self.registry(None), self.registry("bad")):
            with self.subTest(text=text):
                if text is None:
                    marketplace.unlink()
                else:
                    marketplace.write_text(text, encoding="utf-8")
                self.check_command("2.0", "UNKNOWN (source version unavailable)", source="unknown")

    def test_non_version_installation_values_remain_unknown(self):
        for value in (None, 2, {}, "", "unknown", "latest", "2..0"):
            with self.subTest(value=value):
                self.local.write_text(self.registry(value), encoding="utf-8")
                self.check_command("unknown", "UNKNOWN (plugin not installed via marketplace?)")

    def test_two_missing_versions_do_not_establish_freshness(self):
        self.local.with_name("marketplace.json").unlink()
        self.check_command("unknown", "UNKNOWN (plugin not installed via marketplace?)", source="unknown")

    def test_list_registry_skips_unrelated_rows_and_tolerates_bad_optional_fields(self):
        entries = [None, {"name": "another", "version": "1.0"},
                   {"name": "software-project-governance", "version": "2.0",
                    "gitCommitSha": 123, "installedAt": {}}]
        self.global_registry.write_text(json.dumps(entries), encoding="utf-8")
        self.check_command("2.0", "UP TO DATE")


class PackedPluginFreshnessTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("npm"), "npm is required to build the distribution")
    def test_packaged_cli_classifies_five_installation_states(self):
        root = Path(__file__).resolve().parents[4]
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            home = work / "isolated user home"
            user_registry = home / ".claude" / "installed_plugins.json"
            user_registry.parent.mkdir(parents=True)
            env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
                       npm_config_cache=str(work / "npm-cache"), PYTHONDONTWRITEBYTECODE="1")
            packed = subprocess.run(
                [shutil.which("npm"), "pack", "--offline", "--ignore-scripts", "--json",
                 "--pack-destination", str(work)], cwd=root, env=env, capture_output=True,
                encoding="utf-8", check=True)
            archive = work / json.loads(packed.stdout)[0]["filename"]
            with tarfile.open(archive, mode="r:gz") as bundle:
                bundle.extractall(work, filter="data")
            package = work / "package"
            local_registry = package / ".claude-plugin" / "installed_plugins.json"
            self.assertFalse(local_registry.with_name("marketplace.json").exists())
            local_registry.parent.mkdir(exist_ok=True)
            version = json.loads((package / "package.json").read_text(encoding="utf-8"))["version"]
            old_version = "0.0.1"
            self.assertNotEqual(old_version, version)
            registry = PluginFreshnessTests.registry
            cli = package / "skills/software-project-governance/infra/verify_workflow.py"
            cases = [
                (None, None, "unknown", "UNKNOWN", 0),
                (None, registry(version), version, "UP TO DATE", 0),
                (registry(old_version), registry(version), old_version, "OUTDATED", 1),
                ("{", registry(version), "unknown", "UNKNOWN", 0),
                (None, "{", "unknown", "UNKNOWN", 0),
            ]
            for local, user, installed, status, exit_code in cases:
                with self.subTest(installed=installed, status=status, user=user):
                    for path, text in ((local_registry, local), (user_registry, user)):
                        if text is None:
                            path.unlink(missing_ok=True)
                        else:
                            path.write_text(text, encoding="utf-8")
                    before = {p: p.read_bytes() for p in home.rglob("*") if p.is_file()}
                    command = subprocess.run([sys.executable, "-B", str(cli), "check-plugin-freshness"],
                                             cwd=package, env=env, capture_output=True, encoding="utf-8")
                    self.assertEqual(command.returncode, exit_code, command.stderr)
                    self.assertIn(f"Installed: {installed} (", command.stdout)
                    self.assertIn(f"Source:    {version} (", command.stdout)
                    self.assertIn(f"Status:    {status}", command.stdout)
                    self.assertEqual({p: p.read_bytes() for p in home.rglob("*") if p.is_file()}, before)
