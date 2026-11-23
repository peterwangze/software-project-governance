"""Regression coverage for the profile read boundary on compatibility probes."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

INFRA = Path(__file__).resolve().parents[1]
if str(INFRA) not in sys.path:
    sys.path.insert(0, str(INFRA))

import dsh_compat
import dsh_contract
import dsh_plane


class IsolatedProfileTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name).resolve()
        self.assigned = self.root / "assigned"
        self.assigned.mkdir()
        self.other = self.root / "other"
        self.other.mkdir()
        self.sentinel = self.other / "unchanged"
        self.sentinel.write_bytes(b"private fixture")
        self.original_hash = hashlib.sha256(self.sentinel.read_bytes()).digest()
        self.home_key = dsh_contract.get("host.env.home_var")
        self.profile_key = dsh_contract.get("host.planes.env.profile_dir")
        self.composition = self.root / "agent.cordis.yml"
        self.composition.write_text("[]", encoding="utf-8")
        # Every test uses an invented user profile and no ancestor-process discovery.
        self.enter_patch(mock.patch.object(Path, "home", return_value=self.root / "user"))
        self.enter_patch(mock.patch.object(dsh_plane, "RealProcesses", return_value=None))

    def enter_patch(self, patcher):
        value = patcher.start()
        self.addCleanup(patcher.stop)
        return value

    def check(self, **kwargs):
        return dsh_compat.check_dsh_preset_compat(
            root=self.root, compositions=[self.composition],
            which=lambda name: "fixture-node" if name == "node" else None,
            **kwargs)

    def test_wrong_assigned_home_refuses_before_any_discovery_or_subprocess(self):
        discovery = self.enter_patch(mock.patch.object(dsh_compat, "locate_dsh_install"))
        runner = self.enter_patch(mock.patch.object(subprocess, "run"))
        profile = self.root / "user"
        for misplaced in (self.other, profile, profile / ".dsh"):
            with self.subTest(misplaced=misplaced):
                report = self.check(env={self.home_key: str(misplaced)}, isolated_home=self.assigned)
                self.assertEqual(report["verdict"], "FAIL", report)
                self.assertIn("differs", report["reason"])
        discovery.assert_not_called()
        runner.assert_not_called()
        self.assertEqual(hashlib.sha256(self.sentinel.read_bytes()).digest(), self.original_hash)

    def test_user_directories_relative_and_nonexistent_assignments_refuse(self):
        discovery = self.enter_patch(mock.patch.object(dsh_compat, "locate_dsh_install"))
        for invalid in (Path("relative"), self.root / "user", self.root / "user/.dsh",
                        self.root / "user/.dsh/data", self.root / "missing"):
            with self.subTest(invalid=invalid):
                report = self.check(env={}, isolated_home=invalid)
                self.assertEqual(report["verdict"], "FAIL", report)
        discovery.assert_not_called()

    def test_automatic_check_requires_explicit_host_profile_consent(self):
        inherited = {self.home_key: str(self.other)}
        discovery = self.enter_patch(mock.patch.object(
            dsh_compat, "locate_dsh_install", return_value={"status": "NOT_RUN", "reason": "fixture"}))
        with mock.patch.dict(os.environ, inherited, clear=True):
            report = self.check()
            self.assertEqual(report["verdict"], "NOT_RUN", report)
            self.assertIn("--use-host-profile", report["reason"])
            discovery.assert_not_called()
            self.check(use_host_profile=True)
            self.assertEqual(discovery.call_args.kwargs["env"][self.home_key], str(self.other))

    def test_allowed_profile_used_for_discovery_and_both_children_get_fresh_homes(self):
        plane = self.assigned / "profiles" / "node_modules"
        name = dsh_compat.ORACLE_PACKAGES[0]
        package = plane / name
        package.mkdir(parents=True)
        (package / "package.json").write_text(json.dumps({"name": name, "version": "1.0.0"}), encoding="utf-8")
        child_homes = []
        def run(argv, *, env, **kwargs):
            fresh = Path(env[self.home_key])
            self.assertTrue(fresh.is_dir())
            self.assertNotIn(fresh, (self.assigned, self.other))
            self.assertNotIn(self.profile_key, env)
            self.assertEqual(list(fresh.iterdir()), [])
            child_homes.append(fresh)
            if "--version" in argv:
                return subprocess.CompletedProcess(argv, 0, "v1.0\n", "")
            req = json.loads(kwargs["input"])
            Path(req["output"]).write_text(json.dumps({"ok": True, "files": []}), encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, "", "")

        inherited = {self.home_key: str(self.other), self.profile_key: str(self.other)}
        with mock.patch.dict(os.environ, inherited, clear=True), mock.patch.object(subprocess, "run", run):
            for env in ({self.profile_key: str(self.other)},
                        {self.home_key: str(self.assigned), self.profile_key: str(self.other)}):
                report = self.check(env=env, isolated_home=self.assigned)
                self.assertEqual(Path(report["install"]["node_modules"]), plane)
                self.assertEqual(report["install"]["node_version"], "v1.0")
                self.assertEqual(report["isolation"]["home_writes"], 0)
        self.assertEqual(len(set(child_homes)), 4)
        self.assertTrue(all(not path.exists() for path in child_homes))
        self.assertEqual(hashlib.sha256(self.sentinel.read_bytes()).digest(), self.original_hash)


if __name__ == "__main__":
    unittest.main()
