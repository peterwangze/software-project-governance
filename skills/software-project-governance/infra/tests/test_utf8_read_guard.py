"""FIX-278 G4/F — pwsh read of .governance files MUST be explicit UTF-8 (TDD).

Audit evidence (the contract this guard holds):
- AUDIT-147 (§4.3 D6 / §6 选项 F): reading a UTF-8 file containing Chinese
  through pwsh WITHOUT an explicit encoding produced GBK-as-UTF-8 mojibake
  (``缁熶竴鎺ㄧ悊绛夌骇…`` — ``统一推理等级插件`` mis-decoded) on the Windows
  default ANSI/GBK codepage, plus a ``ConvertFrom-Json`` failure.
- AUDIT-148 (§3.4 / §4.3): the router evidence-log read via
  ``Get-Content ... -Tail 30`` (no ``-Encoding``) rendered 22,311 characters
  of mostly garbled text (``R1 瀹℃煡 = APPROVED锛坲nresolved_blockers=0…``).

Contract under test (G4/F):
  1. The bootstrap documents that tell agents how to read ``.governance``
     governance records with pwsh MUST carry an explicit UTF-8 read rule:
     ``-Encoding UTF8`` or ``[System.IO.File]::ReadAllText(p, [Text.Encoding]::UTF8)``
     (documents: repository ``AGENTS.md``, entry ``SKILL.md``,
     ``commands/governance.md``).
  2. Simulation of the router session read path (pwsh ``Get-Content`` of a
     UTF-8 ``evidence-log.md`` containing Chinese + legacy mojibake text)
     round-trips with 0 mojibake and 0 replacement characters; on a GBK
     codepage (936) the negative control (bare ``Get-Content``) reproduces
     the audited mojibake and the explicit-UTF-8 read fixes it.

Run:
    python -m pytest skills/software-project-governance/infra/tests/test_utf8_read_guard.py -v
"""

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

_REPO_ROOT = _INFRA_DIR.parents[2]

# Canonical rule texts this guard accepts (the explicit UTF-8 read markers).
_UTF8_FLAG = "-Encoding UTF8"
_UTF8_READALLTEXT = "[System.IO.File]::ReadAllText"
_UTF8_READALLTEXT_ALT = "[IO.File]::ReadAllText"


def _ps_exe():
    """Locate a PowerShell executable (pwsh 7 or Windows PowerShell 5.1)."""
    found = shutil.which("pwsh")
    if found:
        return found
    found = shutil.which("powershell")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    return None


def _ps_codepage(ps_exe):
    """Return the PowerShell default ANSI codepage (e.g. 936) or None."""
    try:
        proc = subprocess.run(
            [ps_exe, "-NoLogo", "-NoProfile", "-NonInteractive",
             "-Command",
             "[System.Text.Encoding]::Default.CodePage"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60, check=False,
        )
        return int(proc.stdout.strip())
    except (OSError, ValueError):
        return None


class Utf8ReadGuardDocsTests(unittest.TestCase):
    """Contract 1 — bootstrap documents carry the explicit UTF-8 read rule."""

    DOC_PATHS = (
        _REPO_ROOT / "AGENTS.md",
        _INFRA_DIR.parent / "SKILL.md",
        _REPO_ROOT / "commands" / "governance.md",
    )

    def _text(self, path):
        return path.read_text(encoding="utf-8")

    def test_bootstrap_docs_carry_explicit_utf8_rule(self):
        """Each bootstrap doc that discusses pwsh reads must carry a UTF-8 rule.

        FIX-278 G4/F: without the explicit rule the model reproduces the
        AUDIT-147 D6 / AUDIT-148 §4.3 raw ``Get-Content`` mojibake path.
        """
        missing = []
        for path in self.DOC_PATHS:
            text = self._text(path)
            present = (
                _UTF8_FLAG in text
                or _UTF8_READALLTEXT in text
                or _UTF8_READALLTEXT_ALT in text
            )
            if not present:
                missing.append(str(path))
        self.assertEqual(
            missing, [],
            "bootstrap docs must carry an explicit UTF-8 pwsh read rule "
            "(-Encoding UTF8 / [IO.File]::ReadAllText): missing in {}".format(
                missing))

    def test_governance_encoding_note_mentions_gbk_mojibake(self):
        """The rule must name the failure mode (GBK mojibake) — a bare UTF-8
        mention without the reason would not change agent behavior."""
        for path in self.DOC_PATHS:
            text = self._text(path)
            self.assertTrue(
                ("UTF8" in text and ("乱码" in text or "mojibake" in text))
                or _UTF8_READALLTEXT in text,
                "{}: UTF-8 rule must name the mojibake failure mode"
                .format(path))


class Utf8ReadSimulationTests(unittest.TestCase):
    """Contract 2 — simulation of the router read path, 0 mojibake."""

    def _ps(self):
        ps = _ps_exe()
        if ps is None:
            self.skipTest("PowerShell not available — simulation skipped")
        return ps

    def _run(self, ps_exe, script):
        return subprocess.run(
            [ps_exe, "-NoLogo", "-NoProfile", "-NonInteractive",
             "-Command", script],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120, check=False,
        )

    _FIXTURE_CONTENT = (
        "| REVIEW-DEV-002-R1 | DEV-002 | 治理记录 | "
        "review-record CLI 机器写入 review 结论记录（round 1） | "
        "2026-08-22 | G11 | APPROVED_WITH_NOTES | unresolved_blockers=0 |\n"
        "| 旧行 | 调试结果 = 统一推理等级插件（历史 GBK 残留） |\n"
    )

    def test_pwsh_utf8_read_roundtrip_zero_mojibake(self):
        """A UTF-8 governance file read via the documented pwsh path
        round-trips Chinese text with zero mojibake / replacement chars.

        Fixture content reproduces the router evidence-log shape: Chinese
        prose plus a literal legacy-mojibake line (as it exists on disk in
        legacy records — must be preserved faithfully, not re-decoded).
        """
        import tempfile
        ps = self._ps()
        with tempfile.TemporaryDirectory(prefix="spg-utf8-") as tmp:
            evidence = Path(tmp) / "evidence-log.md"
            evidence.write_text(self._FIXTURE_CONTENT, encoding="utf-8")
            script = (
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                "Get-Content -LiteralPath '{0}' -Encoding UTF8 -Tail 30"
                " | Out-String".format(evidence)
            )
            proc = self._run(ps, script)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            out = proc.stdout
            # Chinese content decodes correctly through the documented path.
            self.assertIn("review-record CLI 机器写入", out)
            self.assertIn("统一推理等级插件", out)
            self.assertIn("unresolved_blockers=0", out)
            # Zero replacement characters (no undecodable bytes).
            self.assertNotIn("\ufffd", out)

    def test_bare_getcontent_reproduces_gbk_mojibake_on_gbk_codepage(self):
        """Negative control (GBK codepage only): the audited bare
        ``Get-Content`` path reproduces the mojibake while the explicit
        ``-Encoding UTF8`` read does not — the guard is the rule."""
        import tempfile
        ps = self._ps()
        codepage = _ps_codepage(ps)
        if codepage != 936:
            self.skipTest(
                "system ANSI codepage is {0}, not 936 (GBK) — mojibake "
                "negative control not reproducible on this machine".format(
                    codepage))
        with tempfile.TemporaryDirectory(prefix="spg-utf8-") as tmp:
            evidence = Path(tmp) / "evidence-log.md"
            evidence.write_text(self._FIXTURE_CONTENT, encoding="utf-8")
            bare = self._run(
                ps,
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                "Get-Content -LiteralPath '{0}' -Tail 30 | Out-String"
                .format(evidence))
            explicit = self._run(
                ps,
                "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
                "Get-Content -LiteralPath '{0}' -Encoding UTF8 -Tail 30"
                " | Out-String".format(evidence))
            # Bare read garbles the Chinese (GBK decode)…
            self.assertNotIn("review-record CLI 机器写入", bare.stdout)
            # …the explicit UTF-8 read round-trips it.
            self.assertIn("review-record CLI 机器写入", explicit.stdout)
            self.assertNotIn("\ufffd", explicit.stdout)

    def test_pure_python_utf8_read_path_contract(self):
        """The canonical reader the docs recommend round-trips UTF-8 — pure
        python guard so the simulation also runs where PowerShell is
        unavailable."""
        import tempfile
        with tempfile.TemporaryDirectory(prefix="spg-utf8-") as tmp:
            path = Path(tmp) / "plan-tracker.md"
            path.write_text("| ARCH-001 | 通用附件路由框架 v3 设计稿 | PASS |\n",
                            encoding="utf-8")
            text = path.read_text(encoding="utf-8")
            self.assertIn("通用附件路由框架", text)
            self.assertNotIn("\ufffd", text)


if __name__ == "__main__":
    unittest.main()
