from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECK = Path(__file__).resolve().parents[3] / "release-checklist/scripts/check_mainline.py"


class ReleaseMainlineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "local"
        self.repo.mkdir()
        self.remote = Path(tmp.name) / "upstream.git"
        self.git("init", "--bare", str(self.remote))
        self.git("init", "-b", "master")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("commit", "--allow-empty", "-m", "release base")
        self.git("push", "origin", "master")
        self.git("switch", "-c", "development")
        self.git("commit", "--allow-empty", "-m", "development")

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.org",
             "-c", "commit.gpgSign=false", "-c", "core.hooksPath=unused-hooks", *args],
            cwd=self.repo, text=True, stderr=subprocess.PIPE,
        ).strip()

    def check_mainline(self, *args):
        return subprocess.run([sys.executable, str(CHECK), "master", *args], cwd=self.repo,
                              text=True, capture_output=True)

    def test_live_remote_wins_over_head_and_stale_tracking_ref(self):
        base = self.git("rev-parse", "master")
        tip = self.git("rev-parse", "HEAD")
        result = self.check_mainline()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count(base), 2)

        # Pushing by URL advances the remote without refreshing origin/master.
        self.git("push", str(self.remote), "HEAD:refs/heads/master")
        self.assertEqual(self.git("rev-parse", "origin/master"), base)
        stale = self.check_mainline()
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn(f"local refs/heads/master {base}", stale.stdout)
        self.assertIn(f"origin refs/heads/master {tip}", stale.stdout)
        self.assertEqual(self.git("rev-parse", "master"), base)

        self.git("fetch", "origin", "refs/heads/master:refs/heads/master")
        self.assertEqual(self.check_mainline().returncode, 0)
        self.assertEqual(self.git("branch", "--show-current"), "development")

    def test_unavailable_remote_and_missing_local_branch_block_closeout(self):
        self.git("remote", "rename", "origin", "upstream")
        self.assertNotEqual(self.check_mainline().returncode, 0)
        self.assertEqual(self.check_mainline("--remote", "upstream").returncode, 0)
        self.git("remote", "set-url", "upstream", str(self.remote.with_name("missing.git")))
        self.assertNotEqual(self.check_mainline("--remote", "upstream").returncode, 0)
        self.git("remote", "set-url", "upstream", str(self.remote))
        self.git("branch", "-d", "master")
        self.assertNotEqual(self.check_mainline("--remote", "upstream").returncode, 0)
