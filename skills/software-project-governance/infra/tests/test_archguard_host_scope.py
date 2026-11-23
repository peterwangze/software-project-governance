"""Consumer-facing architecture checks must distinguish installed rules from host sources."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


INFRA = Path(__file__).resolve().parents[1]
CLI = INFRA / "verify_workflow.py"
PLUGIN = INFRA.parents[2]
SCHEMA = Path("skills/software-project-governance/core/architecture-health.json")
if str(INFRA) not in sys.path:
    sys.path.insert(0, str(INFRA))
from checks.architecture_health import host_architecture_health


class HostScopeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.host = Path(temp.name).resolve()

    def write(self, relative, text):
        path = self.host / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def cli(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(CLI), *map(str, args)],
            cwd=cwd or self.host, capture_output=True, encoding="utf-8", timeout=90,
        )

    def test_default_policy_scans_product_in_project_wrapper(self):
        self.write("project/src/server.ts", "export {};\n" * 2000)
        self.write("node_modules/a/lib.js", "unused\n" * 5000)
        self.write(".governance/history/old.py", "old\n" * 5000)
        self.write("tests/test_copy.py", "old\n" * 5000)
        # A host copy at the plugin's internal path has no implicit authority.
        self.write(SCHEMA, "invalid shadow")
        run = self.cli("check-architecture-health", "--scope", "host", "--fail-on-issues")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("files scanned (.py, .js, .ts): 1", run.stdout)
        self.assertIn("module_size: project/src/server.ts", run.stdout.replace("\\", "/"))
        self.assertIn("lines=2000", run.stdout)
        self.assertIn("advisory", run.stdout)

    def test_explicit_override_resolves_from_host_and_respects_fatal_setting(self):
        self.write("src/source.py", "VALUE = 1\nVALUE = 2\n")
        self.write("ignored/copy.js", "x\n" * 100)
        self.write("rules/host.json", json.dumps({
            "module_size": {"warn_lines": 1, "error_lines": 2, "exclusions": ["ignored/**"]},
            "gate_integration": {"fatal_on_error": True},
        }))
        args = ("check-architecture-health", "--scope", "host", "--policy", "rules/host.json",
                "--project-root", self.host)
        inspection = self.cli(*args, cwd=PLUGIN)
        self.assertEqual(inspection.returncode, 0, inspection.stderr)
        gate = self.cli(*args, "--fail-on-issues", cwd=PLUGIN)
        self.assertEqual(gate.returncode, 1, gate.stderr)
        self.assertIn("2 ERROR, 0 WARN", gate.stdout)
        self.assertIn("duplicate_constant", gate.stdout)
        self.assertIn("files scanned (.py, .js, .ts): 1", gate.stdout)

    def test_explicit_plugin_matches_legacy_with_external_project_root(self):
        self.write("source.ts", "external\n" * 5000)
        args = ("--project-root", self.host, "check-architecture-health", "--fail-on-issues")
        implicit = self.cli(*args)
        explicit = self.cli(*args, "--scope", "plugin")
        installed = self.cli("check-architecture-health", "--fail-on-issues", cwd=PLUGIN)
        host = self.cli(*args, "--scope", "host")
        for run in (implicit, explicit, installed, host):
            self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Architecture Health Check (ArchGuard)", installed.stdout)
        self.assertEqual(implicit.stdout, explicit.stdout)
        self.assertEqual(explicit.stdout, installed.stdout)
        self.assertNotIn("source.ts", explicit.stdout)
        self.assertIn("module_size: source.ts", host.stdout)

    def test_policy_and_empty_input_errors_are_not_advisory_success(self):
        command = ("check-architecture-health", "--scope", "host")
        for args, message in (
            (command, "No eligible host source"),
            ((*command, "--policy", "missing.json"), "cannot load architecture policy"),
            (("check-architecture-health", "--policy", "policy.json"), "requires --scope host"),
            ((*command, "--project-root", self.host / "missing"), "invalid-project-root"),
        ):
            with self.subTest(args=args):
                run = self.cli(*args)
                self.assertEqual(run.returncode, 2, run.stdout)
                self.assertIn(message, run.stderr)
        for payload in ("invalid", "[]", "{}", '{"module_size":{"warn_lines":true}}',
                        '{"module_size":{"warn_lines":5001}}', '{"module_size":{"exclusions":[{}]}}',
                        '{"function_size":{"warn_line":5}}', '{"gate_integration":{"fatal_on_error":"no"}}'):
            with self.subTest(payload=payload):
                path = self.write("policy.json", payload)
                with self.assertRaises(ValueError):
                    host_architecture_health(self.host, PLUGIN, PLUGIN / SCHEMA, path)

    def test_nested_installed_plugin_is_outside_host_input(self):
        nested = self.host / "package"
        rules = self.write(Path("package") / SCHEMA, (PLUGIN / SCHEMA).read_text(encoding="utf-8"))
        self.write("package/internal.js", "x\n" * 5000)
        self.write("src/small.ts", "export {};\n")
        result = host_architecture_health(self.host, nested, rules, None)
        self.assertEqual(result["files_scanned"], 1)
        self.assertEqual(result["findings"], [])
        for missing_or_broken in [rules.with_name("absent.json"), self.write("broken.json", "{}")]:
            with self.subTest(default_policy=missing_or_broken), self.assertRaises(ValueError):
                host_architecture_health(self.host, nested, missing_or_broken, None)
