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
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
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
