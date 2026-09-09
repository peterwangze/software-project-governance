"""Unit tests for the DeepSeek Harness adapter assets — DSH-ADAPTER-001.

Enforcement mapping for the dsh projection itself (ADR-001 / ADR-017):
the adapter must not rely on prose alone — its installable artifacts are
machine-checked here so a drifted template, an unknown token, a broken
command shim, or a launcher/template mismatch fails the suite.

Covers:

  - Token contract: every ``__GOVERNANCE_*__`` token in the composition
    template is exactly one the launcher substitutes, and vice versa.
  - Generation determinism: ``launch.py --install`` (link and copy modes)
    output equals pure token substitution — no hidden drift.
  - Structural row contract: persona + skill-filesystem customSkillDirs
    (repo skills/ + skill-shims/) + tool-skill + delegation rows are
    present so the generated preset remains a full coding agent.
  - Command shim contract: each ``adapters/dsh/skill-shims/<name>.md``
    carries DSH frontmatter (``name`` == filename, non-empty
    ``description``) and a thin pointer to ``commands/<name>.md`` — this
    is what makes the dsh ``/name`` gesture load the shared command.
  - Bootstrap template contract: the project AGENTS.md template carries
    the version marker and points at the shared skill without duplicating
    workflow rules.
  - Preset metadata contract: ``preset.yml`` has name + description.
  - Optional YAML validity (skipped when PyYAML is unavailable, matching
    the repo's NOT_RUN policy for optional tooling).

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_dsh_adapter.py" -v
"""

import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_REPO_ROOT = _INFRA_DIR.parents[2]
_ADAPTER_DIR = _REPO_ROOT / "adapters" / "dsh"
_HOOKS_DIR = _INFRA_DIR / "hooks"

_TEMPLATE_PATH = _ADAPTER_DIR / "agent.cordis.yml.template"
_PRESET_METADATA_PATH = _ADAPTER_DIR / "preset.yml"
_BOOTSTRAP_TEMPLATE_PATH = _ADAPTER_DIR / "AGENTS.md.template"
_SHIMS_DIR = _ADAPTER_DIR / "skill-shims"
_MANIFEST_PATH = _ADAPTER_DIR / "adapter-manifest.json"
_LAUNCH_PATH = _ADAPTER_DIR / "launch.py"

_TOKENS = (
    "__GOVERNANCE_SKILLS_ROOT__",
    "__GOVERNANCE_SHIMS_ROOT__",
    "__GOVERNANCE_REPO_ROOT__",
)


def _load_launch_module():
    spec = importlib.util.spec_from_file_location("dsh_launch_under_test", _LAUNCH_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fingerprint_tree(root: Path):
    """Independent (test-local) read-only fingerprint: rel/size/mtime_ns.

    Deliberately NOT the launcher's own helper: the FEAT-015 zero-real-home-write
    evidence must be produced by an oracle the code under test cannot influence.
    """
    if not root.exists():
        return ("absent",)
    entries = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        for name in sorted(dirnames) + sorted(filenames):
            path = Path(dirpath) / name
            try:
                stat = path.lstat()
            except OSError:
                continue
            entries.append(
                (path.relative_to(root).as_posix(), stat.st_size, stat.st_mtime_ns)
            )
    return tuple(entries)


def _real_home_witness_oracle(home: Path):
    """Test-local zero-write oracle: home top level + <home>/.agent-presets.

    Deliberately independent of the launcher's own witness (an oracle the code
    under test cannot influence). Scope mirrors the claim under test: the
    adapter's only real-home write surface is ``<home>/.agent-presets``; the
    host-owned subtrees (sessions/, storages/, dsh-agent-router/, …) are
    excluded because a live session mutates them concurrently.
    """
    top = []
    if home.is_dir():
        for path in sorted(home.iterdir()):
            stat = path.lstat()
            if path.is_dir():
                top.append((path.name, "d"))
            else:
                top.append((path.name, "f", stat.st_size, stat.st_mtime_ns))
    return (tuple(top), _fingerprint_tree(home / ".agent-presets"))


def _decoy_home_env(decoy: Path):
    """Env for a smoke CLI run whose 'user home' is a throwaway decoy.

    M7.7: the refusal paths are exercised against a decoy home so the real
    ~/.dsh is never inside the blast radius of a guard regression.
    """
    env = os.environ.copy()
    env.pop("DSH_HOME", None)
    env["HOME"] = str(decoy)
    env["USERPROFILE"] = str(decoy)
    return env


def _run_smoke_cli(env, *extra):
    return subprocess.run(
        [sys.executable, str(_LAUNCH_PATH), "--smoke", *extra],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def _bash():
    for candidate in (
        Path(os.environ.get("ProgramFiles", "")) / "Git" / "bin" / "bash.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Git" / "bin" / "bash.exe",
    ):
        if candidate.exists():
            return str(candidate)
    return shutil.which("bash") or "bash"


class DshAdapterTests(unittest.TestCase):
    """Machine checks over the dsh adapter's installable artifacts."""

    maxDiff = None

    def _template_text(self):
        return _TEMPLATE_PATH.read_text(encoding="utf-8")

    def test_template_uses_only_known_tokens(self):
        text = self._template_text()
        stray = sorted(set(re.findall(r"__[A-Z0-9_]+__", text)) - set(_TOKENS))
        self.assertEqual(stray, [])

    def test_template_contains_every_launcher_token(self):
        text = self._template_text()
        missing = [token for token in _TOKENS if token not in text]
        self.assertEqual(missing, [])

    def test_template_required_rows(self):
        text = self._template_text()
        for marker in (
            "- id: persona",
            "name: '@deepseek-ai/dsh-persona'",
            "software-project-governance",
            "resolve_entry.py",
            "ask_user_question",
            # FIX-253/REQ-112: the persona must carry the compressed
            # behavior contract (关键行为契约) unconditionally.
            "关键行为契约",
            "复审必达",
            "完成必推荐",
            "task-priority-analysis",
            "- id: skill-filesystem",
            "customSkillDirs:",
            "- id: tool-skill",
            "- id: tool-subagent",
            "provider: spawn",
            "- id: tool-subagent-fork",
            "provider: fork",
            "- id: tool-ask-user",
            "- id: tool-goal",
        ):
            self.assertIn(marker, text)

    def test_launch_link_generation_is_pure_substitution(self):
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            exit_code = launch.install_preset("link")
            self.assertEqual(exit_code, 0)
            generated = (
                Path(td) / ".agent-presets" / "governance" / "agent.cordis.yml"
            ).read_text(encoding="utf-8")
        skills = str((_REPO_ROOT / "skills").resolve()).replace("\\", "/")
        shims = str((_ADAPTER_DIR / "skill-shims").resolve()).replace("\\", "/")
        repo = str(_REPO_ROOT.resolve()).replace("\\", "/")
        expected = (
            _TEMPLATE_PATH.read_text(encoding="utf-8")
            .replace("__GOVERNANCE_SKILLS_ROOT__", skills)
            .replace("__GOVERNANCE_SHIMS_ROOT__", shims)
            .replace("__GOVERNANCE_REPO_ROOT__", repo)
        )
        self.assertEqual(generated, expected)

    def test_launch_copy_generation_snapshots_roots(self):
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            exit_code = launch.install_preset("copy")
            self.assertEqual(exit_code, 0)
            preset_dir = Path(td) / ".agent-presets" / "governance"
            self.assertTrue((preset_dir / "skills" / "software-project-governance" / "SKILL.md").is_file())
            self.assertTrue((preset_dir / "skill-shims" / "governance.md").is_file())
            composition = (preset_dir / "agent.cordis.yml").read_text(encoding="utf-8")
            self.assertTrue((preset_dir / "preset.yml").is_file())
        self.assertIn(str(preset_dir).replace("\\", "/") + "/skills", composition)
        self.assertIn(str(preset_dir).replace("\\", "/") + "/skill-shims", composition)

    def test_install_writes_skill_root_marker(self):
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            self.assertEqual(launch.install_preset("link"), 0)
            marker = (
                Path(td) / ".agent-presets" / "governance" / "skill-root.txt"
            ).read_text(encoding="utf-8")
        self.assertEqual(
            marker.strip(),
            str(_REPO_ROOT.resolve()).replace("\\", "/"),
        )

    def test_install_dry_run_writes_nothing(self):
        # FEAT-010 incident / DEC-158 R1: the safe verification path must be
        # side-effect free — --dry-run may not create even the preset root.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            self.assertEqual(launch.install_preset("link", dry_run=True), 0)
            self.assertEqual(launch.install_preset("copy", dry_run=True), 0)
            self.assertFalse((Path(td) / ".agent-presets").exists())

    def test_cli_install_dry_run_flag_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env["DSH_HOME"] = td
            result = subprocess.run(
                [sys.executable, str(_LAUNCH_PATH), "--install", "--dry-run"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("[DRY-RUN]", result.stdout)
            self.assertIn("dsh home", result.stdout)
            self.assertFalse((Path(td) / ".agent-presets").exists())

    def test_bootstrap_dry_run_writes_nothing(self):
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "project"
            project.mkdir()
            self.assertEqual(
                launch.write_bootstrap(project, force=False, dry_run=True), 0
            )
            self.assertFalse((project / "AGENTS.md").exists())

    def test_uninstall_removes_only_governance_preset(self):
        # Lifecycle symmetry: install must have an official uninstall that
        # deletes exactly the governance preset dir — never siblings.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            self.assertEqual(launch.install_preset("link"), 0)
            sibling = Path(td) / ".agent-presets" / "other-agent"
            sibling.mkdir(parents=True)
            (sibling / "preset.yml").write_text("name: other\n", encoding="utf-8")
            self.assertEqual(launch.uninstall_preset(), 0)
            self.assertFalse((Path(td) / ".agent-presets" / "governance").exists())
            self.assertTrue((sibling / "preset.yml").is_file())
            # idempotent: uninstalling an absent preset is a clean no-op
            self.assertEqual(launch.uninstall_preset(), 0)

    def test_uninstall_dry_run_deletes_nothing(self):
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            self.assertEqual(launch.install_preset("link"), 0)
            self.assertEqual(launch.uninstall_preset(dry_run=True), 0)
            self.assertTrue(
                (Path(td) / ".agent-presets" / "governance" / "preset.yml").is_file()
            )

    def test_cli_uninstall_flag_removes_preset(self):
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env["DSH_HOME"] = td
            install = subprocess.run(
                [sys.executable, str(_LAUNCH_PATH), "--install"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            uninstall = subprocess.run(
                [sys.executable, str(_LAUNCH_PATH), "--uninstall"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            self.assertEqual(
                uninstall.returncode, 0, uninstall.stdout + uninstall.stderr
            )
            self.assertIn("preset removed", uninstall.stdout)
            self.assertFalse((Path(td) / ".agent-presets" / "governance").exists())

    def test_shipped_preset_skill_dirs_are_baseurl_selflocated(self):
        # FIX-290 round 2 (live regression, twice): preset sessions do NOT
        # inherit the host-plane customSkillDirs, and literal relative
        # entries resolve against the dsh PROCESS CWD
        # (dsh-skill-filesystem `map((root) => resolve(root))`) — either way
        # the session catalog silently empties and `/governance` disappears.
        # The only sanctioned form here is `!!js` resolved from `baseUrl`
        # (this composition's own directory; the pattern proven by the
        # shipped dsh-novel-writing preset). Guard: (1) the shipped preset
        # carries customSkillDirs entries; (2) every entry is a !!js baseUrl
        # self-location expression; (3) no literal relative entries; (4) the
        # URL math of each expression, evaluated against the preset file's
        # real location, yields an existing directory.
        shipped_path = _REPO_ROOT / "presets" / "governance" / "agent.cordis.yml"
        shipped = shipped_path.read_text(encoding="utf-8")
        self.assertIn("- id: skill-filesystem", shipped)
        entries = re.findall(
            r"(?m)^\s*-\s*!!js\s+\"([^\"]*baseUrl[^\"]*)\"\s*$", shipped
        )
        self.assertGreaterEqual(
            len(entries), 2, "expected 2 baseUrl self-located customSkillDirs"
        )
        # no literal relative customSkillDirs entries (cwd-resolved trap)
        self.assertIsNone(
            re.search(r"(?m)^\s*-\s*['\"]\.\.?/", shipped),
            "literal relative skill roots are forbidden (process-cwd resolved)",
        )
        # semantic evaluation: URL math against the preset's real location
        from urllib.parse import urljoin, urlparse
        import urllib.request

        preset_dir_uri = shipped_path.parent.resolve().as_uri() + "/"
        for expr in entries:
            m = re.search(r"new URL\('([^']+)',\s*baseUrl\)", expr)
            self.assertIsNotNone(m, f"entry not baseUrl-anchored: {expr}")
            resolved = urljoin(preset_dir_uri, m.group(1))
            local = urllib.request.url2pathname(urlparse(resolved).path)
            self.assertTrue(
                Path(local).is_dir(),
                f"customSkillDirs entry resolves to missing dir: {local}",
            )

    def test_shipped_preset_skill_roots_are_pack_whitelisted(self):
        # FIX-290 round 2 companion guard: the semantic URL-math test above
        # validates the REPO layout, but `file:`/`github:` installs receive
        # a package packed per package.json `files` — a root that exists in
        # the repo yet falls outside the whitelist silently disappears from
        # installed copies (same failure class: empty session catalog). Every
        # directory the preset's customSkillDirs expressions resolve to must
        # be covered by a `files` entry.
        shipped_path = _REPO_ROOT / "presets" / "governance" / "agent.cordis.yml"
        shipped = shipped_path.read_text(encoding="utf-8")
        # anchor on real `- !!js "..."` config entries (comment examples in
        # the preset header use a `'<rel>'` placeholder and must not match)
        exprs = re.findall(
            r"(?m)^\s*-\s*!!js\s+\"([^\"]*baseUrl[^\"]*)\"\s*$", shipped
        )
        rels = [
            m.group(1)
            for m in (
                re.search(r"new URL\('([^']+)',\s*baseUrl\)", expr)
                for expr in exprs
            )
            if m
        ]
        self.assertGreaterEqual(len(rels), 2)
        pkg = json.loads((_REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        whitelist = [
            str(item).rstrip("/").replace("\\", "/")
            for item in pkg.get("files", [])
            if not str(item).startswith("!")
        ]
        for rel in rels:
            # resolve `../../skills/` against presets/governance/ → repo-relative
            parts = ["presets", "governance"]
            for segment in rel.split("/"):
                if segment == "..":
                    parts.pop()
                elif segment:
                    parts.append(segment)
            resolved = "/".join(parts)
            covered = any(
                resolved == entry or resolved.startswith(entry + "/")
                for entry in whitelist
            )
            self.assertTrue(
                covered,
                f"customSkillDirs root '{resolved}' is not covered by "
                f"package.json files whitelist {whitelist} — installed "
                "file:/github: copies would lack it",
            )

    def _init_target_repo(self, root: Path) -> None:
        root.mkdir()
        subprocess.run(
            ["git", "init"], cwd=root, check=True, capture_output=True, text=True
        )
        gov = root / ".governance"
        gov.mkdir(parents=True)
        (gov / "plan-tracker.md").write_text(
            "## 项目配置\n- **工作流版本**: 0.50.2\n", encoding="utf-8"
        )

    def _write_source_home(self, source_home: Path) -> Path:
        source_hooks = source_home / "infra" / "hooks"
        source_hooks.mkdir(parents=True)
        (source_home / "SKILL.md").write_text(
            "---\nversion: 0.50.2\n---\n", encoding="utf-8"
        )
        shutil.copyfile(_HOOKS_DIR / "pre-commit", source_hooks / "pre-commit")
        return source_hooks / "pre-commit"

    def _run_stale_hook(self, root: Path, installed_hook: Path, env) -> subprocess.CompletedProcess:
        shutil.copyfile(_HOOKS_DIR / "pre-commit", installed_hook)
        installed_hook.write_text(
            installed_hook.read_text(encoding="utf-8") + "\n# stale dsh-discovered copy\n",
            encoding="utf-8",
        )
        return subprocess.run(
            [_bash(), installed_hook.as_posix()],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def _clean_hook_env(self, td: str) -> dict:
        env = os.environ.copy()
        env.pop("SOFTWARE_PROJECT_GOVERNANCE_HOME", None)
        env.pop("SPG_HOME", None)
        env.pop("XDG_CACHE_HOME", None)
        env["HOME"] = str(Path(td) / "plain-home")
        return env

    @unittest.skipUnless(
        shutil.which("bash") or Path(os.environ.get("ProgramFiles", ""), "Git", "bin", "bash.exe").exists(),
        "bash unavailable (hook self-upgrade checks are bash-hosted)",
    )
    def test_hook_discovers_dsh_link_mode_marker(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "target"
            self._init_target_repo(root)

            repo_home = Path(td) / "installed"
            source_hook = self._write_source_home(
                repo_home / "skills" / "software-project-governance"
            )

            dsh_home = Path(td) / "dsh-home"
            preset_dir = dsh_home / ".agent-presets" / "governance"
            preset_dir.mkdir(parents=True)
            (preset_dir / "skill-root.txt").write_text(
                repo_home.resolve().as_posix() + "\n", encoding="utf-8"
            )

            installed_hook = root / ".git" / "hooks" / "pre-commit"
            env = self._clean_hook_env(td)
            env["DSH_HOME"] = dsh_home.as_posix()
            result = self._run_stale_hook(root, installed_hook, env)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("self-upgraded", result.stdout)
            self.assertEqual(
                installed_hook.read_text(encoding="utf-8"),
                source_hook.read_text(encoding="utf-8"),
            )

    @unittest.skipUnless(
        shutil.which("bash") or Path(os.environ.get("ProgramFiles", ""), "Git", "bin", "bash.exe").exists(),
        "bash unavailable (hook self-upgrade checks are bash-hosted)",
    )
    def test_hook_discovers_dsh_copy_mode_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "target"
            self._init_target_repo(root)

            dsh_home = Path(td) / "dsh-home"
            source_home = (
                dsh_home / ".agent-presets" / "governance" / "skills" / "software-project-governance"
            )
            source_hook = self._write_source_home(source_home)

            installed_hook = root / ".git" / "hooks" / "pre-commit"
            env = self._clean_hook_env(td)
            env["DSH_HOME"] = dsh_home.as_posix()
            result = self._run_stale_hook(root, installed_hook, env)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("self-upgraded", result.stdout)
            self.assertEqual(
                installed_hook.read_text(encoding="utf-8"),
                source_hook.read_text(encoding="utf-8"),
            )

    def test_hooks_carry_dsh_discovery_candidates(self):
        for hook_name in ("pre-commit", "commit-msg", "post-commit"):
            text = (_HOOKS_DIR / hook_name).read_text(encoding="utf-8")
            self.assertIn("dsh_preset_root", text, hook_name)
            self.assertIn("skill-root.txt", text, hook_name)
            self.assertIn("DSH_HOME", text, hook_name)

    def test_workflow_registries_know_dsh(self):
        """FIX-168 doc-sync discipline: the loading machinery must cover dsh."""
        if str(_INFRA_DIR) not in sys.path:
            sys.path.insert(0, str(_INFRA_DIR))
        import verify_workflow as vw

        self.assertIn("dsh", vw.MAINSTREAM_AGENT_ADAPTERS)
        self.assertIn("dsh", vw.RUNTIME_MATRIX_AGENT_IDS)
        self.assertIn("dsh", vw.ADAPTER_RUNTIME_CAPABILITY_POLICY)
        self.assertIn("adapters/dsh/README.md", vw.MAINSTREAM_AGENT_LOADING_REQUIRED_DOCS)
        self.assertIn("DeepSeek Harness", vw.MAINSTREAM_AGENT_LOADING_TIER1)
        self.assertIn("dsh", vw.MAINSTREAM_AGENT_LOADING_ADAPTERS)
        self.assertEqual(
            vw.MAINSTREAM_AGENT_LOADING_ADAPTERS["dsh"]["display"], "DeepSeek Harness"
        )
        # Deliberate absence: dsh has no headless CLI, so the live-session E2E
        # path (Chrys style) is used instead of the agent-runtime-e2e matrix.
        self.assertNotIn("dsh", vw.AGENT_RUNTIME_E2E_PLATFORMS)

    def test_supported_agents_and_loading_docs_include_dsh(self):
        manifest_md = (
            _REPO_ROOT / "skills" / "software-project-governance" / "core" / "manifest.md"
        ).read_text(encoding="utf-8")
        self.assertIn("DeepSeek Harness", manifest_md)

        loading_doc = (
            _REPO_ROOT
            / "docs"
            / "requirements"
            / "mainstream-agent-loading-0.47.0.md"
        ).read_text(encoding="utf-8")
        self.assertIn("DeepSeek Harness", loading_doc)
        # The Official Surface Findings row must carry a citation URL (FIX-122).
        findings_section = loading_doc.split("## Official Surface Findings")[1]
        dsh_row = next(
            line
            for line in findings_section.splitlines()
            if line.startswith("| DeepSeek Harness")
        )
        self.assertIn("https://", dsh_row)

    def test_skill_shim_frontmatter_contract(self):
        shims = sorted(_SHIMS_DIR.glob("*.md"))
        self.assertGreaterEqual(len(shims), 9)
        for shim in shims:
            name = shim.stem
            text = shim.read_text(encoding="utf-8")
            self.assertTrue(
                text.startswith("---"),
                f"{shim.name}: missing YAML frontmatter fence",
            )
            self.assertIn(f"name: {name}\n", text, f"{shim.name}: frontmatter name mismatch")
            description = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
            self.assertIsNotNone(description, f"{shim.name}: missing description")
            self.assertTrue(description.group(1).strip(), f"{shim.name}: empty description")
            self.assertIn(f"commands/{name}.md", text, f"{shim.name}: must point at the shared command")
            self.assertIn("薄投影", text, f"{shim.name}: must declare itself a thin pointer")

    def test_bootstrap_template_contract(self):
        text = _BOOTSTRAP_TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertEqual(text.count("__GOVERNANCE_REPO_ROOT__"), 1)
        self.assertIn("# Governance Bootstrap", text)
        # FIX-253 (§6.6.2): dynamic version assertion — read the authority
        # version from the SKILL frontmatter instead of a hardcoded literal,
        # so releases no longer need a manual test-literal sync (the FIX-250
        # sibling drift channel for @bootstrap-version is closed by the
        # dsh-agents-bootstrap-version projection + this test).
        if str(_INFRA_DIR) not in sys.path:
            sys.path.insert(0, str(_INFRA_DIR))
        from checks.version import extract_skill_version

        version = extract_skill_version(
            _REPO_ROOT / "skills" / "software-project-governance" / "SKILL.md"
        )
        self.assertTrue(version, "SKILL.md frontmatter version is missing")
        self.assertIn(f"@bootstrap-version: {version}", text)
        self.assertIn("software-project-governance", text)
        self.assertIn("resolve_entry.py", text)
        self.assertIn("ask_user_question", text)
        self.assertIn("subagent", text)
        self.assertIn("关键行为契约", text)  # FIX-253 anchor (§6.6.2)

    def test_dsh_version_projections_are_satisfied(self):
        """FIX-253 (§6.6.3): persona/AGENTS version strings track the SKILL frontmatter.

        build_projection_plan validates both new transformed_text projections
        (dsh-persona-version / dsh-agents-bootstrap-version) hit their pattern
        exactly once; comparing the planned writes against the current file
        bytes asserts the projection-achieved state (no drift).
        """
        if str(_INFRA_DIR) not in sys.path:
            sys.path.insert(0, str(_INFRA_DIR))
        from release.projection import build_projection_plan

        version, plan = build_projection_plan(_REPO_ROOT)
        planned = {write.relative_path: write.content for write in plan}
        for relative, marker in (
            ("adapters/dsh/agent.cordis.yml.template", f"治理工作流（v{version}）"),
            ("adapters/dsh/AGENTS.md.template", f"@bootstrap-version: {version}"),
        ):
            self.assertIn(relative, planned, relative)
            current = (_REPO_ROOT / relative).read_bytes()
            self.assertEqual(
                current.replace(b"\r\n", b"\n"),
                planned[relative].replace(b"\r\n", b"\n"),
                f"{relative}: projection drift",
            )
            self.assertIn(marker.encode("utf-8"), current, relative)

    def test_injection_contract_check_flags_missing_anchor(self):
        """FIX-253 (S6 guard): deleting an anchor must FAIL check-injection-contract.

        Copies the three injection surfaces into a temp root, removes one
        anchor keyword from the persona copy, and asserts the checker reports
        it (the "manually delete anchor → FAIL" scenario, unit-covered).
        """
        if str(_INFRA_DIR) not in sys.path:
            sys.path.insert(0, str(_INFRA_DIR))
        import verify_workflow as vw

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for relative in vw.INJECTION_CONTRACT_ANCHORS:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(_REPO_ROOT / relative, target)

            baseline = vw.check_injection_contract(root)
            self.assertEqual(baseline["issues"], [])
            self.assertEqual(baseline["files_checked"], len(vw.INJECTION_CONTRACT_ANCHORS))

            persona = root / "adapters/dsh/agent.cordis.yml.template"
            persona.write_text(
                persona.read_text(encoding="utf-8").replace("复审必达", "复审必须达成"),
                encoding="utf-8",
            )
            result = vw.check_injection_contract(root)
            self.assertTrue(
                any("复审必达" in issue for issue in result["issues"]),
                result["issues"],
            )

    def test_preset_metadata_contract(self):
        text = _PRESET_METADATA_PATH.read_text(encoding="utf-8")
        self.assertIn("name:", text)
        self.assertIn("description:", text)

    def test_manifest_required_contract(self):
        manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest["adapter_id"], "dsh")
        self.assertEqual(manifest["workflow_id"], "software-project-governance")
        self.assertEqual(manifest["launcher"], "adapters/dsh/launch.py")
        self.assertEqual(manifest["runtime_e2e"]["version_command"], "dsh --version")
        capabilities = manifest["runtime_capabilities"]
        for key in ("ask_user_question", "sub_agent", "tool_calling", "git_hooks"):
            self.assertEqual(capabilities[key]["status"], "native", key)
        for key in ("browser", "mcp"):
            self.assertEqual(capabilities[key]["status"], "degraded", key)
        closure = capabilities["workflow_closure"]
        self.assertEqual(closure["status"], "degraded")
        self.assertEqual(closure["degraded_capabilities"], ["browser", "mcp"])

    # ── FEAT-015 / RISK-049 ②: isolated preset-session smoke gate ──────────
    # M7.7 protection baseline (a) — isolation: every preset/session operation
    # runs under a redirected DSH_HOME; the real ~/.dsh is only FINGERPRINTED
    # (metadata: rel path + size + mtime_ns — file contents such as
    # credentials.yaml are never read), never written.

    def test_home_fingerprint_detects_metadata_change(self):
        # Metadata-only by design (the real home holds credentials that must
        # not be read). Detection is therefore size/mtime based: a same-size
        # rewrite inside one filesystem timer tick is not distinguishable —
        # the structural isolation guard is the primary protection and this
        # fingerprint is the detection net.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "home"
            home.mkdir()
            (home / "settings.yaml").write_text("a: 1\n", encoding="utf-8")
            before = launch._home_fingerprint(home)
            self.assertEqual(before["state"], "present")
            self.assertEqual(len(before["entries"]), 1)
            (home / "settings.yaml").write_text("a: 22\n", encoding="utf-8")
            after = launch._home_fingerprint(home)
            self.assertNotEqual(before["entries"], after["entries"])
            (home / "added.yaml").write_text("b: 1\n", encoding="utf-8")
            self.assertEqual(len(launch._home_fingerprint(home)["entries"]), 2)
            self.assertEqual(launch._home_fingerprint(home / "nope")["state"], "absent")

    def test_smoke_cli_passes_in_isolated_home(self):
        # Acceptance (1)+(2): one command under DSH_HOME=<tempdir> yields a
        # verdict, and the real ~/.dsh witness is identical after.
        real_home = Path.home() / ".dsh"
        before = _real_home_witness_oracle(real_home)
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env["DSH_HOME"] = td
            result = _run_smoke_cli(env)
            preset = Path(td) / ".agent-presets" / "governance"
            self.assertTrue((preset / "agent.cordis.yml").is_file())
            self.assertTrue((preset / "preset.yml").is_file())
            self.assertTrue((preset / "skill-root.txt").is_file())
        after = _real_home_witness_oracle(real_home)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[SMOKE] Result: PASS", result.stdout)
        # skill 目录加载: the catalog root resolves and carries the skill
        self.assertIn("software-project-governance/SKILL.md", result.stdout)
        # /governance 手势: the projection shim resolves to its shared command
        self.assertIn("governance.md", result.stdout)
        self.assertIn("commands/governance.md", result.stdout)
        # acceptance (2): real ~/.dsh zero writes — independent test-side oracle
        self.assertEqual(before, after)

    def test_smoke_cli_refuses_unredirected_dsh_home(self):
        # Negative path 3a: DSH_HOME unset. The guard must refuse BEFORE any
        # write; the decoy home keeps the real ~/.dsh out of scope entirely.
        with tempfile.TemporaryDirectory() as td:
            decoy = Path(td) / "decoy-home"
            decoy.mkdir()
            result = _run_smoke_cli(_decoy_home_env(decoy))
            self.assertNotEqual(result.returncode, 0)
            out = result.stdout + result.stderr
            self.assertIn("DSH_HOME", out)
            self.assertIn("refus", out.lower())
            self.assertFalse((decoy / ".dsh").exists())

    def test_smoke_cli_refuses_dsh_home_at_user_home(self):
        # Negative path 3b: DSH_HOME == <home>/.dsh — the "误打真实 home"
        # shape, exercised against a decoy home (zero real-home exposure).
        with tempfile.TemporaryDirectory() as td:
            decoy = Path(td) / "decoy-home"
            decoy.mkdir()
            env = _decoy_home_env(decoy)
            env["DSH_HOME"] = str(decoy / ".dsh")
            result = _run_smoke_cli(env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refus", (result.stdout + result.stderr).lower())
            self.assertFalse((decoy / ".dsh" / ".agent-presets").exists())

    def test_smoke_refuses_in_process_when_dsh_home_is_real_home(self):
        # Same guard, unit level: the real home is patched to a temp dir, so a
        # regression can never reach the actual ~/.dsh through this test.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td:
            fake_real = Path(td) / "real-home"
            fake_real.mkdir()
            with patch.dict(os.environ, {"DSH_HOME": str(fake_real)}, clear=False), \
                    patch.object(launch, "real_dsh_home", return_value=fake_real):
                exit_code = launch.smoke_preset()
            self.assertNotEqual(exit_code, 0)
            self.assertFalse((fake_real / ".agent-presets").exists())

    def test_smoke_verifier_fails_when_skill_catalog_root_missing(self):
        # Negative path 3c-i: the skill directory is absent → the gate names it.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            self.assertEqual(launch.install_preset("copy"), 0)
            preset = Path(td) / ".agent-presets" / "governance"
            shutil.rmtree(preset / "skills")
            result = launch.verify_preset_loading(preset)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertTrue(
            any("SKILL.md" in issue for issue in result["issues"]),
            result["issues"],
        )
        self.assertTrue(
            any("skill" in issue.lower() for issue in result["issues"]),
            result["issues"],
        )

    def test_smoke_verifier_fails_when_governance_gesture_missing(self):
        # Negative path 3c-ii: the /governance projection shim is absent.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            self.assertEqual(launch.install_preset("copy"), 0)
            preset = Path(td) / ".agent-presets" / "governance"
            (preset / "skill-shims" / "governance.md").unlink()
            result = launch.verify_preset_loading(preset)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertTrue(
            any("/governance" in issue for issue in result["issues"]),
            result["issues"],
        )

    def test_smoke_verifier_rejects_literal_relative_skill_dir(self):
        # FIX-290 defect class at the gate level: a literal relative
        # customSkillDirs entry resolves against the dsh process CWD and
        # silently empties the catalog — the gate must name it, not pass.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td:
            preset = Path(td) / "preset"
            preset.mkdir()
            (preset / "agent.cordis.yml").write_text(
                "- id: skill-filesystem\n"
                "  name: '@deepseek-ai/dsh-skill-filesystem'\n"
                "  config:\n"
                "    customSkillDirs:\n"
                "      - '../../skills'\n",
                encoding="utf-8",
            )
            result = launch.verify_preset_loading(preset)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertTrue(
            any("relative" in issue.lower() for issue in result["issues"]),
            result["issues"],
        )

    def test_real_home_witness_scope_ignores_host_activity(self):
        # The witness must be a DETERMINISTIC oracle under a live host: host
        # activity inside its own subtrees (measured 2026-09-09:
        # dsh-agent-router/stats/*) may not flip it, while any change to the
        # adapter's write surface or to the home's top level must.
        launch = _load_launch_module()

        def fresh_home(td, name):
            home = Path(td) / name
            (home / ".agent-presets" / "governance").mkdir(parents=True)
            (home / ".agent-presets" / "governance" / "preset.yml").write_text(
                "name: governance\n", encoding="utf-8"
            )
            (home / "settings.yaml").write_text("a: 1\n", encoding="utf-8")
            (home / "sessions").mkdir()
            return home

        with tempfile.TemporaryDirectory() as td:
            # 1. host-owned subtree activity is tolerated
            home = fresh_home(td, "host-activity")
            baseline = launch._real_home_witness(home)
            (home / "sessions" / "session-1.jsonl").write_text(
                "{}\n", encoding="utf-8"
            )
            self.assertEqual(baseline, launch._real_home_witness(home))

            # 2. adapter write surface change is detected
            home = fresh_home(td, "write-surface")
            baseline = launch._real_home_witness(home)
            (home / ".agent-presets" / "governance" / "agent.cordis.yml").write_text(
                "- id: persona\n", encoding="utf-8"
            )
            self.assertNotEqual(baseline, launch._real_home_witness(home))

            # 3. top-level file modification is detected
            home = fresh_home(td, "top-level-file")
            baseline = launch._real_home_witness(home)
            (home / "settings.yaml").write_text("a: 22\n", encoding="utf-8")
            self.assertNotEqual(baseline, launch._real_home_witness(home))

            # 4. new top-level entry is detected
            home = fresh_home(td, "top-level-entry")
            baseline = launch._real_home_witness(home)
            (home / ".credentials.yaml").write_text("x: y\n", encoding="utf-8")
            self.assertNotEqual(baseline, launch._real_home_witness(home))

    def test_smoke_fails_when_real_home_witness_changes(self):
        # Defence in depth: if any code path mutated the real home, the
        # before/after witness comparison must FAIL the gate.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td:
            isolated = Path(td) / "isolated"
            fake_real = Path(td) / "real-home"
            fake_real.mkdir()
            baseline = launch._real_home_witness(fake_real)
            mutated = dict(baseline)
            mutated["write_surface"] = list(baseline["write_surface"]) + [
                "f:governance/preset.yml:1:1"
            ]
            sequence = [baseline, mutated]
            with patch.dict(os.environ, {"DSH_HOME": str(isolated)}, clear=False), \
                    patch.object(launch, "real_dsh_home", return_value=fake_real), \
                    patch.object(
                        launch, "_real_home_witness",
                        side_effect=lambda home: sequence.pop(0),
                    ):
                exit_code = launch.smoke_preset()
            self.assertNotEqual(exit_code, 0)
            self.assertEqual(sequence, [], "expected exactly two witnesses")

    def test_smoke_reports_absent_dsh_cli_without_false_live_claim(self):
        # Quality budget (reliability): a missing dsh CLI must be reported
        # explicitly as NOT_RUN for the live-session面 — never a silent pass
        # that implies session behavior was verified.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ), patch.object(launch.shutil, "which", return_value=None):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = launch.smoke_preset()
        output = buffer.getvalue()
        self.assertEqual(exit_code, 0, output)
        self.assertIn("dsh CLI", output)
        self.assertIn("absent", output)
        self.assertIn("NOT_RUN", output)

    def test_check_dsh_preset_smoke_passes_and_cleans_temp_home(self):
        if str(_INFRA_DIR) not in sys.path:
            sys.path.insert(0, str(_INFRA_DIR))
        import verify_workflow as vw

        result = vw.check_dsh_preset_smoke()
        self.assertEqual(result["verdict"], "PASS", result)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["isolation"]["real_home_writes"], 0)
        self.assertFalse(
            Path(result["isolation"]["temp_home"]).exists(),
            "the isolated temp DSH_HOME must be removed after the run",
        )

    def test_check_dsh_preset_smoke_reports_failure_not_false_pass(self):
        # Fail-closed: a broken launcher must surface as FAIL with its
        # diagnostic — the check may never degrade to a silent PASS.
        if str(_INFRA_DIR) not in sys.path:
            sys.path.insert(0, str(_INFRA_DIR))
        import verify_workflow as vw

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            adapter = root / "adapters" / "dsh"
            adapter.mkdir(parents=True)
            (adapter / "launch.py").write_text(
                "import sys\n"
                "print('[SMOKE] FAIL: skill catalog root missing')\n"
                "sys.exit(1)\n",
                encoding="utf-8",
            )
            result = vw.check_dsh_preset_smoke(root=root)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(result["exit_code"], 1)
        self.assertTrue(
            any("skill catalog root missing" in detail for detail in result["details"]),
            result["details"],
        )

    @unittest.skipUnless(
        importlib.util.find_spec("yaml") is not None,
        "PyYAML unavailable (optional progressive check, NOT_RUN)",
    )
    def test_template_is_valid_yaml(self):
        import yaml

        class JsTolerantLoader(yaml.SafeLoader):
            """Accept the composition's `!!js` tag as an opaque scalar."""

        def _js_constructor(loader, tag_suffix, node):
            return loader.construct_scalar(node)

        JsTolerantLoader.add_multi_constructor("tag:yaml.org,2002:js", _js_constructor)

        text = self._template_text()
        # The header comments survive a plain parse; the loader dialect is
        # what dsh actually uses, so this is a structural sanity floor only.
        doc = yaml.load(text, Loader=JsTolerantLoader)
        self.assertIsInstance(doc, list)
        ids = [row.get("id") for row in doc if isinstance(row, dict)]
        self.assertIn("persona", ids)
        self.assertIn("skill-filesystem", ids)
        self.assertIn("tool-skill", ids)
        self.assertIn("delegation", ids)


if __name__ == "__main__":
    unittest.main()
