"""Unit tests for the DeepSeek Harness adapter assets — DSH-ADAPTER-001.

Enforcement mapping for the dsh projection itself (ADR-001 / ADR-017):
the adapter must not rely on prose alone — its installable artifacts are
machine-checked here so a drifted template, an unknown token, a broken
command shim, or a launcher/template mismatch fails the suite.

Covers:

  - Token contract: every ``__GOVERNANCE_*__`` token in the composition
    template is exactly one the renderers substitute, and vice versa.
  - Render determinism: ``launch.py --install`` output equals pure token
    substitution — no hidden drift.
  - Render parity: the Python renderer (``launch.render_composition``) and the
    JavaScript renderer (``lib/index.js`` ``renderComposition``) produce the
    SAME text for the same package root, so ``dsh plugin add`` and
    ``--install`` cannot write different presets.
  - Structural row contract: persona + skill-filesystem customSkillDirs
    (repo skills/ + adapters/dsh/skill-shims/) + tool-skill + delegation rows
    are present so the rendered preset remains a full coding agent.
  - Zero-intrusion bundle patch contract (DEC-187): the repo-root
    cordis.patch.yml is ONE ``- insert:`` row naming only this package — no
    UPDATE of any host row, no ``!!js`` self-location, no ``trust: system``
    preset root.
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
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
_REPO_ROOT = _INFRA_DIR.parents[2]
_ADAPTER_DIR = _REPO_ROOT / "adapters" / "dsh"
_HOOKS_DIR = _INFRA_DIR / "hooks"

# FIX-310: the composition template and the preset metadata are the payload
# of the preset they render, not adapter-side siblings.
_PACKAGE_PRESET = _REPO_ROOT / "agent-presets" / "governance"
_TEMPLATE_PATH = _PACKAGE_PRESET / "agent.cordis.yml.template"
_PRESET_METADATA_PATH = _PACKAGE_PRESET / "preset.yml"
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


# FIX-313 (design §6.1 V10): the catch/cleanup path of `ensurePreset()`.
#
# The review root was that cleanup matched directories by NAME (every entry of
# the preset root starting with `<presetId>.staging-`) and deleted them without
# any predicate proving the row had created them. A name prefix is not proof of
# ownership, so these tests fix the observable contract of the cleanup path:
# a directory this attempt did not create is never removed, and the staging
# directory this attempt DID create is still cleaned up.
_ROGUE_STAGING_NAME = "governance.staging-personal-scratch"

# The row's live catch entry point. `lib/index.js` writes the whole staging tree
# BEFORE it reads the payload metadata, so an unreadable `preset.yml` reproduces
# exactly the case the cleanup exists for: "the rename did not happen but the
# staging tree WAS written". A directory in the metadata's place is listed by
# `readdirSync` (so `payloadIncomplete` stays false — the row takes its normal
# path and not an early return) and then fails `readFileSync` with EISDIR.
_LIB_CATCH_PROBE = (
    "import { pathToFileURL } from 'node:url';\n"
    "// argv[1] is this script itself (node file mode), so the row is argv[2].\n"
    "try {\n"
    "const { ensurePreset } = await import(pathToFileURL(process.argv[2]).href);\n"
    "const warns = [];\n"
    "const outcome = ensurePreset({ logger: { warn: (m) => warns.push(String(m)),"
    " info: () => {} } });\n"
    "process.stdout.write(JSON.stringify({ outcome, warns }));\n"
    "} catch (error) {\n"
    "process.stderr.write('PROBE-FAILURE: ' + (error && error.stack ? error.stack : String(error)));\n"
    "process.exitCode = 3;\n"
    "}\n"
)


def _catching_package_copy(root: Path) -> Path:
    """Package copy whose payload metadata is a directory (readable listing,
    unreadable file) — puts the row's catch block on the reachable path."""
    pkg = root / "pkg"
    (pkg / "lib").mkdir(parents=True)
    shutil.copyfile(_REPO_ROOT / "lib" / "index.js", pkg / "lib" / "index.js")
    (pkg / "adapters" / "dsh").mkdir(parents=True)
    shutil.copyfile(
        _REPO_ROOT / "adapters" / "dsh" / "host-contract.json",
        pkg / "adapters" / "dsh" / "host-contract.json",
    )
    shutil.copytree(_PACKAGE_PRESET, pkg / "agent-presets" / "governance")
    (pkg / "agent-presets" / "governance" / "preset.yml").unlink()
    (pkg / "agent-presets" / "governance" / "preset.yml").mkdir()
    (pkg / "package.json").write_text(
        '{"name":"fake","version":"9.9.9","type":"module","main":"lib/index.js"}\n',
        encoding="utf-8",
    )
    return pkg


def _run_catch_probe(lib_path: Path, cwd: Path, dsh_home: Path, home: Path):
    """Run the row in a throwaway process; all home vars redirected."""
    node = shutil.which("node")
    if not node:
        return None
    script = cwd / "probe.mjs"
    script.write_text(_LIB_CATCH_PROBE, encoding="utf-8")
    env = os.environ.copy()
    env["DSH_HOME"] = str(dsh_home)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    return subprocess.run(
        [node, str(script), str(lib_path.resolve())],
        cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )


# FIX-325 (REVIEW-FIX-313-CODE-R0 F1/F2/F3): the collision side of the V10
# staging loop. `Date.now` and `Math.random` are PINNED for the row under test,
# so the staging name is a fixed, predictable string — which lets the fixture
# pre-create a directory at exactly that name and put the EEXIST rename-retry,
# the 8-attempt circuit breaker and its warning path on the reachable path.
# This is the machine guard for V10 acceptance ①/G-04 the review found missing
# (mutation M5 passed the whole suite while the CWD misdeletion survived).
_COLLISION_PROBE = (
    "import { existsSync, mkdirSync, readdirSync, writeFileSync } from 'node:fs';\n"
    "import { join } from 'node:path';\n"
    "import { pathToFileURL } from 'node:url';\n"
    "// argv: 2 = lib/index.js copy, 3 = pinned Math.random sequence (JSON),\n"
    "//      4 = DSH_HOME (forwarded to the row through the environment).\n"
    "const FIXED_TS = 1700000000000;\n"
    "const pinned = JSON.parse(process.argv[3]);\n"
    "let randCalls = 0;\n"
    "Date.now = () => FIXED_TS;\n"
    "Math.random = () => pinned[Math.min(randCalls++, pinned.length - 1)];\n"
    "const dshHome = process.argv[4];\n"
    "const presetRoot = join(dshHome, '.agent-presets');\n"
    "const colliding = join(presetRoot,\n"
    "  `governance.staging-${FIXED_TS}-${pinned[0].toString(36).slice(2, 8)}`);\n"
    "mkdirSync(presetRoot, { recursive: true });\n"
    "mkdirSync(colliding);\n"
    "writeFileSync(join(colliding, 'NOTES.md'), 'my own scratch dir\\n', 'utf8');\n"
    "const before = readdirSync(presetRoot).sort();\n"
    "const warns = [];\n"
    "const { ensurePreset } = await import(pathToFileURL(process.argv[2]).href);\n"
    "const outcome = ensurePreset({ logger: { warn: (m) => warns.push(String(m)),"
    " info: () => {} } });\n"
    "const after = readdirSync(presetRoot).sort();\n"
    "process.stdout.write(JSON.stringify({ outcome, warns, before, after,\n"
    "  collidingSurvived: existsSync(join(colliding, 'NOTES.md')) }));\n"
)


# FIX-325 / F1 — the CWD-degradation inverse. When `resolveDshHome()` THROWS,
# `outcome.dir` stays '' and the pre-V10 catch enumerated `dirname('.')` — the
# PROCESS CWD — deleting every `governance.staging-*` entry there (review
# scenario S2). On Windows the throw cannot be produced by clearing environment
# variables (`os.homedir()` still resolves), so the fixture faults the row's
# own `homedir` import binding via the SYNCHRONOUS ESM `registerHooks` — which
# needs Node >= 22.15. The repo declares engines >= 20: on older runtimes this
# guard is NOT_RUN (skip), never a failure — the FIX-325 skip/NOT_RUN policy.
_CWD_FAULT_PROBE = (
    "import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';\n"
    "import { join } from 'node:path';\n"
    "import { registerHooks } from 'node:module';\n"
    "import { pathToFileURL } from 'node:url';\n"
    "// argv: 2 = lib/index.js copy, 3 = decoy directory name for the CWD.\n"
    "const target = pathToFileURL(process.argv[2]).href;\n"
    "registerHooks({\n"
    "  load(url, context, nextLoad) {\n"
    "    if (url === target) {\n"
    "      const source = readFileSync(new URL(url), 'utf8').replace(\n"
    "        \"import { homedir } from 'node:os'\",\n"
    "        \"const homedir = () => { throw new Error('injected: homedir unavailable') }\");\n"
    "      return { format: 'module', source, shortCircuit: true };\n"
    "    }\n"
    "    return nextLoad(url, context);\n"
    "  },\n"
    "});\n"
    "const decoy = process.argv[3];\n"
    "mkdirSync(decoy);\n"
    "writeFileSync(join(decoy, 'NOTES.md'), 'my own scratch dir\\n', 'utf8');\n"
    "const warns = [];\n"
    "let outcome = null;\n"
    "let threw = null;\n"
    "try {\n"
    "  const { ensurePreset } = await import(target);\n"
    "  outcome = ensurePreset({ logger: { warn: (m) => warns.push(String(m)),"
    " info: () => {} } });\n"
    "} catch (error) {\n"
    "  threw = String(error);\n"
    "}\n"
    "process.stdout.write(JSON.stringify({ outcome, warns, threw,\n"
    "  decoySurvived: existsSync(join(decoy, 'NOTES.md')) }));\n"
)


def _complete_package_copy(root: Path) -> Path:
    """Package copy with a COMPLETE payload — the row's happy path is reachable,
    so the collision fixture can reach the EEXIST retry loop and the successful
    rename after it (unlike `_catching_package_copy`, which breaks `preset.yml`
    on purpose)."""
    pkg = root / "pkg"
    (pkg / "lib").mkdir(parents=True)
    shutil.copyfile(_REPO_ROOT / "lib" / "index.js", pkg / "lib" / "index.js")
    (pkg / "adapters" / "dsh").mkdir(parents=True)
    shutil.copyfile(
        _REPO_ROOT / "adapters" / "dsh" / "host-contract.json",
        pkg / "adapters" / "dsh" / "host-contract.json",
    )
    shutil.copytree(_PACKAGE_PRESET, pkg / "agent-presets" / "governance")
    (pkg / "package.json").write_text(
        '{"name":"fake","version":"9.9.9","type":"module","main":"lib/index.js"}\n',
        encoding="utf-8",
    )
    return pkg


def _run_collision_probe(pkg: Path, dsh_home: Path, home: Path, cwd: Path,
                         pinned_random):
    """Run the row with `Date.now`/`Math.random` pinned; all home vars
    redirected. The probe seeds a directory at the exact colliding staging name
    before `ensurePreset()` runs and reports the preset-root listing before and
    after, so the assertions cover creation as well as deletion."""
    node = shutil.which("node")
    if not node:
        return None
    script = cwd / "collision-probe.mjs"
    script.write_text(_COLLISION_PROBE, encoding="utf-8")
    env = os.environ.copy()
    env["DSH_HOME"] = str(dsh_home)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    return subprocess.run(
        [node, str(script), str((pkg / "lib" / "index.js").resolve()),
         json.dumps(pinned_random), str(dsh_home.resolve())],
        cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )


def _node_version_tuple():
    """The runtime's `(major, minor, patch)`, or None when node is unusable."""
    node = shutil.which("node")
    if not node:
        return None
    try:
        out = subprocess.run([node, "--version"], capture_output=True,
                             text=True, encoding="utf-8", timeout=30)
    except OSError:
        return None
    match = re.match(r"^v(\d+)\.(\d+)\.(\d+)", (out.stdout or "").strip())
    return tuple(int(part) for part in match.groups()) if match else None


def _node_register_hooks_available():
    """FIX-325 skip/NOT_RUN policy: the CWD fault injection needs the
    synchronous `module.registerHooks` (Node >= 22.15); the repo declares
    engines >= 20, so older runtimes skip the guard instead of failing."""
    version = _node_version_tuple()
    return version is not None and version >= (22, 15, 0)


def _run_cwd_fault_probe(lib_path: Path, cwd: Path, home: Path,
                         decoy_name: str):
    """Run the row with `homedir` faulted to throw; DSH_HOME is deliberately
    UNSET so `resolveDshHome()` actually reaches its `homedir()` fallback (with
    DSH_HOME set, `homedir()` is never consulted and the fault never fires).
    `DSH_HOME`/`HOME`/`USERPROFILE` are removed or redirected — the real home
    is never read through the row under test."""
    node = shutil.which("node")
    if not node:
        return None
    script = cwd / "cwd-fault-probe.mjs"
    script.write_text(_CWD_FAULT_PROBE, encoding="utf-8")
    env = os.environ.copy()
    env.pop("DSH_HOME", None)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    return subprocess.run(
        [node, str(script), str(lib_path.resolve()), decoy_name],
        cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )


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

    def test_launch_render_is_pure_substitution(self):
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            exit_code = launch.install_preset()
            self.assertEqual(exit_code, 0)
            preset_dir = Path(td) / ".agent-presets" / "governance"
            generated = (preset_dir / "agent.cordis.yml").read_text(encoding="utf-8")
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
        # No residue of the retired self-locating form, and no token may
        # survive into a mounted composition.
        self.assertNotIn("baseUrl", generated)
        for token in _TOKENS:
            self.assertNotIn(token, generated, token)

    def test_install_writes_only_the_rendered_preset(self):
        # FIX-310: the package's shared core (skills/, commands/, agents/) is
        # referenced ABSOLUTELY — nothing may be copied into the preset dir,
        # otherwise the repo would carry a second source of the same files.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            self.assertEqual(launch.install_preset(), 0)
            preset_dir = Path(td) / ".agent-presets" / "governance"
            entries = sorted(item.name for item in preset_dir.iterdir())
            self.assertEqual(
                entries,
                [".dsh-bundle-version", "agent.cordis.yml", "preset.yml",
                 "skill-root.txt"],
                entries,
            )
            composition = (preset_dir / "agent.cordis.yml").read_text(encoding="utf-8")
        for copied in ("skills/", "skill-shims/", "commands/", "agents/"):
            self.assertFalse((preset_dir / copied).exists(), copied)
        roots = launch._custom_skill_dir_entries(composition)
        self.assertEqual(len(roots), 2, roots)
        for entry in roots:
            form, path, issue = launch._resolve_skill_entry(entry, preset_dir)
            self.assertIsNone(issue, entry)
            self.assertEqual(form, "absolute", entry)
            self.assertTrue(path.is_dir(), entry)
            self.assertTrue(str(path).startswith(str(_REPO_ROOT.resolve())), entry)

    def test_install_writes_skill_root_marker(self):
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            self.assertEqual(launch.install_preset(), 0)
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
            self.assertEqual(launch.install_preset(dry_run=True), 0)
            self.assertEqual(launch.install_preset(dry_run=True), 0)
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
            self.assertIn("composition tpl", result.stdout)
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
            self.assertEqual(launch.install_preset(), 0)
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
            self.assertEqual(launch.install_preset(), 0)
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

    def test_rendered_composition_carries_absolute_existing_skill_roots(self):
        # FIX-290 round 2 (live regression, twice) + FIX-310: preset sessions do
        # NOT inherit the host-plane customSkillDirs, and a literal relative
        # entry resolves against the dsh PROCESS CWD
        # (dsh-skill-filesystem `map((root) => resolve(root))`) — either way the
        # session catalog silently empties and `/governance` disappears. The
        # render model makes every entry an ABSOLUTE path into this package, so
        # the guard is: (1) the render source carries customSkillDirs;
        # (2) rendering it yields exactly 2 entries; (3) every entry is
        # absolute (no literal relative string, no `../` escape, no `baseUrl`
        # self-location residue); (4) every entry exists and resolves inside
        # the package.
        template = _TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("- id: skill-filesystem", template)
        launch = _load_launch_module()
        rendered = launch.render_composition()
        self.assertTrue(rendered, "the shipped payload must render")
        entries = launch._custom_skill_dir_entries(rendered)
        self.assertEqual(len(entries), 2, entries)
        for entry in entries:
            form, path, issue = launch._resolve_skill_entry(
                entry, _PACKAGE_PRESET)
            self.assertIsNone(issue, entry)
            self.assertEqual(form, "absolute", entry)
            self.assertNotIn("..", str(path), entry)
            self.assertTrue(path.is_dir(), entry)
            self.assertTrue(
                str(path).startswith(str(_REPO_ROOT.resolve())), entry)

    def test_rendered_skill_roots_are_pack_whitelisted(self):
        # FIX-310 companion guard: rendering produces absolute paths into the
        # REPO, but `file:`/`github:` installs receive a package packed per
        # package.json `files` — a root that exists in the repo yet falls
        # outside the whitelist silently disappears from installed copies (the
        # same empty-catalog failure class). Every root the renderer produces
        # must be covered by a `files` entry, and the render source itself must
        # be packed too.
        launch = _load_launch_module()
        rendered = launch.render_composition()
        resolved_roots = []
        for entry in launch._custom_skill_dir_entries(rendered):
            _form, path, issue = launch._resolve_skill_entry(entry, _PACKAGE_PRESET)
            self.assertIsNone(issue, entry)
            resolved_roots.append(
                path.resolve().relative_to(_REPO_ROOT.resolve()).as_posix())
        pkg = json.loads((_REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        whitelist = [
            str(item).rstrip("/").replace("\\", "/")
            for item in pkg.get("files", [])
            if not str(item).startswith("!")
        ]
        for resolved in resolved_roots + ["agent-presets/governance/agent.cordis.yml.template",
                                          "agent-presets/governance/preset.yml",
                                          "lib/index.js"]:
            covered = any(
                resolved == entry or resolved.startswith(entry + "/")
                for entry in whitelist
            )
            self.assertTrue(
                covered,
                f"required path '{resolved}' is not covered by package.json "
                f"files whitelist {whitelist} — installed file:/github: copies "
                "would lack it",
            )

    def test_bundle_patch_is_zero_intrusion(self):
        # DEC-187 I-1/I-2/I-3 (user ruling, 2026-09-12): this bundle may not
        # modify host behaviour. The machine criterion the ruling names is that
        # the composed entry list differs from the unpatched one by exactly the
        # bundle's OWN inserted row — so the patch is one `- insert:` row naming
        # this package, plus comments. Guard (regex/string, not YAML: the file
        # is a loader patch list, not a document):
        #   (1) exactly one top-level `- insert:` and ZERO top-level `- id:`
        #       UPDATE rows (an id-targeted entry would REPLACE a host row's
        #       whole config);
        #   (2) no `!!js` expression at all — in particular none parsing
        #       `process.argv` or scanning `$DSH_HOME/profiles` to self-locate;
        #   (3) no `trust: system` preset-root declaration;
        #   (4) the inserted row names this package and nothing under
        #       `@deepseek-ai/`.
        patch_text = (_REPO_ROOT / "cordis.patch.yml").read_text(encoding="utf-8")
        code_lines = [
            line for line in patch_text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        code_text = "\n".join(code_lines)
        inserts = [line for line in code_lines if re.match(r"^- insert:\s*$", line)]
        self.assertEqual(len(inserts), 1, code_lines)
        top_level_ids = [line for line in code_lines if re.match(r"^- id:", line)]
        self.assertEqual(
            top_level_ids, [],
            "an `- id:`-targeted patch entry REPLACES a host row's config — "
            "DEC-187 forbids it; only `- insert:` is allowed",
        )
        # Comments explain the ban, so the scan is over CODE lines only.
        self.assertNotIn("!!js", code_text)
        for forbidden in ("process.argv", "profiles", "dshHomePath", "trust:"):
            self.assertNotIn(forbidden, code_text, forbidden)
        self.assertNotIn("@deepseek-ai/", code_text)
        inserted_names = re.findall(r"(?m)^\s+name:\s*'?([^'\s]+)'?\s*$", code_text)
        self.assertEqual(
            inserted_names, ["@peterwangze/software-project-governance-plugin"],
            inserted_names,
        )
        inserted_ids = re.findall(r"(?m)^\s+- id:\s*'?([^'\s]+)'?\s*$", code_text)
        self.assertEqual(inserted_ids, ["governance"], inserted_ids)
        # The inserted row must be resolvable as a module: package.json main.
        pkg = json.loads((_REPO_ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["dsh"]["bundle"]["patch"], "./cordis.patch.yml")
        self.assertNotIn("skills", pkg["dsh"], "dsh.skills is dead metadata")
        self.assertEqual(pkg["main"], "lib/index.js")
        self.assertEqual(pkg["type"], "module")

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
            ("agent-presets/governance/agent.cordis.yml.template",
             f"治理工作流（v{version}）"),
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

            persona = root / "agent-presets/governance/agent.cordis.yml.template"
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
        # Negative path 3c-i: the skill root resolves to a directory without
        # the catalog skill → the gate names it.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            self.assertEqual(launch.install_preset(), 0)
            preset = Path(td) / ".agent-presets" / "governance"
            empty_root = Path(td) / "empty-skills"
            empty_root.mkdir()
            composition = (preset / "agent.cordis.yml").read_text(encoding="utf-8")
            (preset / "agent.cordis.yml").write_text(
                composition.replace(
                    str((_REPO_ROOT / "skills").resolve()).replace("\\", "/"),
                    empty_root.as_posix(),
                ),
                encoding="utf-8",
            )
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
        # Negative path 3c-ii: the shims root exists but carries no
        # /governance projection.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"DSH_HOME": td}, clear=False
        ):
            self.assertEqual(launch.install_preset(), 0)
            preset = Path(td) / ".agent-presets" / "governance"
            empty_shims = Path(td) / "empty-shims"
            empty_shims.mkdir()
            composition = (preset / "agent.cordis.yml").read_text(encoding="utf-8")
            (preset / "agent.cordis.yml").write_text(
                composition.replace(
                    str((_ADAPTER_DIR / "skill-shims").resolve()).replace("\\", "/"),
                    empty_shims.as_posix(),
                ),
                encoding="utf-8",
            )
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

    def test_verify_preset_loading_carries_the_row_schema_gate(self):
        # The 0.1.5 regression class: the row carried `text` while the installed
        # @deepseek-ai/dsh-persona declares `prefix: z.string().required()`, and
        # the loader rejected the WHOLE preset mount. This verifier — the repo's
        # own "preset loading" gate on the --smoke path — used to read the
        # composition only for customSkillDirs and never parsed a row.
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td:
            preset = Path(td) / "preset"
            preset.mkdir()
            (preset / "agent.cordis.yml").write_text(
                "- id: persona\n"
                "  name: '@deepseek-ai/dsh-persona'\n"
                "  config:\n"
                "    text: 'the pre-fix key'\n",
                encoding="utf-8",
            )
            result = launch.verify_preset_loading(preset)
        row_validation = result.get("row_validation")
        self.assertIsNotNone(row_validation, result)
        if row_validation["verdict"] == "NOT_RUN":
            # No node and/or no discoverable dsh install: the row check is
            # NOT_RUN by policy (never a silent PASS, never a FAIL).
            self.skipTest("installed-schema oracle unavailable: "
                          f"{row_validation['reason']}")
        self.assertEqual(row_validation["verdict"], "FAIL", row_validation)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertTrue(
            any("persona" in issue and "prefix" in issue
                for issue in result["issues"]),
            result["issues"],
        )

    def test_verify_preset_loading_accepts_a_contract_shaped_persona_row(self):
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td:
            preset = Path(td) / "preset"
            preset.mkdir()
            (preset / "agent.cordis.yml").write_text(
                "- id: persona\n"
                "  name: '@deepseek-ai/dsh-persona'\n"
                "  config:\n"
                "    prefix: 'the post-fix key'\n",
                encoding="utf-8",
            )
            result = launch.verify_preset_loading(preset)
        self.assertNotEqual(
            (result.get("row_validation") or {}).get("verdict"), "FAIL",
            result.get("row_validation"),
        )
        self.assertFalse(
            [issue for issue in result["issues"] if "row/config" in issue],
            result["issues"],
        )

    def test_real_home_witness_scope_ignores_host_activity(self):
        # The witness must be a DETERMINISTIC oracle under a live host: host
        # activity inside its own subtrees (measured 2026-09-09:
        # dsh-agent-router/stats/*) may not flip it, while any change to the
        # adapter's own write surface must.
        #
        # D-54 (design §3.3 row 11) rewrote the top-level half of this contract:
        # the witness compares top-level NAMES only — a host rewrite of
        # `settings.yaml` moves size and mtime but is not evidence that this
        # adapter wrote anything. Cases 3/4 below are the C-23 expected rewrite
        # of this test's pre-D-54 assertions ("top-level size/mtime change IS
        # detected"), which asserted exactly the behaviour D-54 removes.
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

            # 2b. …and the verdict function agrees, with no resampling grace
            self.assertEqual(
                launch.witness_verdict((baseline, launch._real_home_witness(home))
                                       )["verdict"],
                "FAIL",
            )

            # 3. D-54: top-level file MODIFICATION is NOT a failure. The host
            # rewrites settings.yaml on its own schedule; size/mtime are no
            # longer witness inputs at all, so the samples stay identical.
            home = fresh_home(td, "top-level-file")
            baseline = launch._real_home_witness(home)
            settings = home / "settings.yaml"
            stamp = settings.stat().st_mtime_ns
            settings.write_text("a: 22\n" + "y" * 4096, encoding="utf-8")
            os.utime(settings, ns=(stamp + 10 ** 9, stamp + 10 ** 9))
            after = launch._real_home_witness(home)
            self.assertEqual(
                baseline, after,
                "top-level size/mtime must not be witness inputs any more",
            )
            self.assertEqual(launch.witness_verdict((baseline, after))["verdict"],
                             "PASS")

            # 4. D-54: a NEW top-level entry is still noticed, but a single
            # appearance is a host race → advisory; only a reproduced change
            # (present again on the immediate resample) fails the gate.
            home = fresh_home(td, "top-level-entry")
            baseline = launch._real_home_witness(home)
            transient = home / ".credentials.yaml"
            transient.write_text("x: y\n", encoding="utf-8")
            first = launch._real_home_witness(home)
            self.assertNotEqual(baseline, first)
            race = launch.witness_verdict((baseline, first), resample=lambda: (
                transient.unlink(), launch._real_home_witness(home))[1])
            self.assertEqual(race["verdict"], "PASS", race)
            self.assertTrue(race["advisories"], race)

            home = fresh_home(td, "top-level-entry-settled")
            baseline = launch._real_home_witness(home)
            (home / ".credentials.yaml").write_text("x: y\n", encoding="utf-8")
            first = launch._real_home_witness(home)
            settled = launch.witness_verdict(
                (baseline, first),
                resample=lambda: launch._real_home_witness(home),
            )
            self.assertEqual(settled["verdict"], "FAIL", settled)

    def test_fx_witness_01_fixture_reproduces_the_d54_judgments(self):
        # D-54 acceptance ⑤: the fixture registered for this judgment must be
        # machine-checkable. It is emitted here and executed against this
        # launcher, so the four judgments are verified by running them rather
        # than by asserting that a file exists.
        if str(_INFRA_DIR) not in sys.path:
            sys.path.insert(0, str(_INFRA_DIR))
        sys.path.insert(0, str(_INFRA_DIR / "tests"))
        import dsh_fixtures

        with tempfile.TemporaryDirectory() as td:
            path = dsh_fixtures.emit_fixture("FX-WITNESS-01", Path(td))
            proc = subprocess.run(
                [sys.executable, str(path), str(_LAUNCH_PATH)],
                cwd=str(_REPO_ROOT), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=300,
            )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        self.assertEqual(report["verdict"], "PASS", report)

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

    # ── FIX-310: single-source payload + two-renderer parity ───────────────

    def test_package_preset_payload_has_no_duplicated_core(self):
        # FIX-310 / DEC-187: this repository is one shared core (skills/,
        # commands/, agents/) consumed by six adapters. The preset payload must
        # stay a two-file payload — the composition template + its metadata —
        # because a copied core inside one adapter's preset is a second source
        # of the same files (and a 2x package). Guard the shape, not the prose.
        entries = sorted(item.name for item in _PACKAGE_PRESET.iterdir())
        self.assertEqual(
            entries,
            ["agent.cordis.yml.template", "preset.yml"],
            f"preset payload must carry exactly the composition template and "
            f"its metadata, found {entries}",
        )
        for leaked in ("skills", "commands", "agents", "skill-shims"):
            self.assertFalse(
                (_PACKAGE_PRESET / leaked).exists(),
                f"the shared core directory '{leaked}' must not be duplicated "
                "into the preset payload (single-source violation)",
            )

    def test_js_and_python_renderers_agree(self):
        # Two renderers write the same user-root composition: `lib/index.js`
        # `ensurePreset()` on bundle boot and `launch.py --install` on the
        # manual path. They share a token contract but no code, so parity is a
        # machine fact, not an intention: a divergence would install a
        # different preset depending on which path ran.
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable (JS renderer cannot be exercised)")
        launch = _load_launch_module()
        lib_uri = (_REPO_ROOT / "lib" / "index.js").resolve().as_uri()
        script = (
            f"import {{ renderComposition }} from {json.dumps(lib_uri)};"
            "import { readFileSync } from 'node:fs';"
            "const t = readFileSync(process.argv[1], 'utf8');"
            "process.stdout.write(JSON.stringify(renderComposition(t, process.argv[2])));"
        )
        result = subprocess.run(
            [node, "--input-type=module", "-e", script,
             str(_TEMPLATE_PATH),
             str(_REPO_ROOT.resolve()).replace("\\", "/")],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["leftovers"], [], payload)
        self.assertEqual(
            payload["text"], launch.render_composition(),
            "the JS and Python renderers produced different compositions",
        )

    def test_isolated_cr_template_renders_identically(self):
        # FIX-313(a) / D-66: the shared line-ending contract of the two
        # renderers is "fold `\r\n` to `\n`, leave an isolated `\r` alone".
        # `test_js_and_python_renderers_agree` reads the SHIPPED template,
        # which contains no isolated CR, so the lone-CR half of the contract
        # is invisible to it (inventory D-67: the parity test "不注入 `\r` ⇒
        # 抓不到 D-66"). This fixture injects exactly one isolated CR and
        # requires the two delivery paths — `launch.render_composition()`
        # (the `--install` path) and `renderComposition()` (the bundle-boot
        # path), both against the same package root — to produce the
        # identical byte string, with the CR SURVIVING on both sides (the
        # direction FIX-316 pinned when it closed D-66). Either regression
        # direction is caught: a renderer that folds the lone CR alone breaks
        # parity, and a silent both-sides fold breaks the survival pins.
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable (JS renderer cannot be exercised)")
        launch = _load_launch_module()
        with tempfile.TemporaryDirectory() as td:
            fixture = (
                _TEMPLATE_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
                + "\n# FIX-313 isolated-CR probe: X\rY\n"
            )
            self.assertEqual(fixture.count("\r"), 1,
                             "fixture must carry exactly one lone CR")
            fixture_path = Path(td) / "isolated-cr.template"
            # `newline=""` keeps the writer from translating the probe CR
            # back into the platform's text convention.
            fixture_path.write_text(fixture, encoding="utf-8", newline="")

            original_template = launch._composition_template
            launch._composition_template = lambda: Path(fixture_path)
            try:
                with redirect_stdout(io.StringIO()), \
                        redirect_stderr(io.StringIO()):
                    rendered = launch.render_composition()
            finally:
                launch._composition_template = original_template
            self.assertTrue(rendered, "the lone-CR fixture must still render")

            lib_uri = (_REPO_ROOT / "lib" / "index.js").resolve().as_uri()
            script = (
                f"import {{ renderComposition }} from {json.dumps(lib_uri)};"
                "import { readFileSync } from 'node:fs';"
                "const t = readFileSync(process.argv[1], 'utf8');"
                "process.stdout.write(JSON.stringify(renderComposition(t, process.argv[2])));"
            )
            result = subprocess.run(
                [node, "--input-type=module", "-e", script,
                 str(fixture_path),
                 str(_REPO_ROOT.resolve()).replace("\\", "/")],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["leftovers"], [], payload)
            # Parity: byte-identical compositions from the two delivery paths
            # (string equality — the same fact a sha256 comparison would show).
            self.assertEqual(
                payload["text"], rendered,
                "the JS and Python renderers disagree on the isolated-CR template",
            )
            self.assertEqual(rendered.count("\r"), 1,
                             "lone CR must survive the Python path")
            self.assertEqual(payload["text"].count("\r"), 1,
                             "lone CR must survive the JS path")

    def test_lib_ensure_preset_renders_the_user_root_idempotently(self):
        # Acceptance path of the DEC-187 design: the inserted host row alone
        # must deliver a mountable preset into the USER preset root (which is
        # what makes it a custom, deletable preset in the settings page), and
        # a second boot must not rewrite it. The row is exercised against a
        # redirected DSH_HOME only — the real ~/.dsh is never touched.
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable (host row cannot be exercised)")
        launch = _load_launch_module()
        lib_uri = (_REPO_ROOT / "lib" / "index.js").resolve().as_uri()
        script = (
            f"import {{ apply }} from {json.dumps(lib_uri)};"
            "const warns = [];"
            "const ctx = { logger: { warn: (m) => warns.push(String(m)), info: () => {} } };"
            "apply(ctx);"
            "process.stdout.write(JSON.stringify(warns));"
        )
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env["DSH_HOME"] = td
            preset = Path(td) / ".agent-presets" / "governance"

            def run():
                return subprocess.run(
                    [node, "--input-type=module", "-e", script],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", env=env,
                )

            first = run()
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(json.loads(first.stdout), [])
            for name in ("agent.cordis.yml", "preset.yml",
                         ".dsh-bundle-version", "skill-root.txt"):
                self.assertTrue((preset / name).is_file(), name)
            composition = (preset / "agent.cordis.yml").read_text(encoding="utf-8")
            # The synced composition is the same text --install writes, with
            # absolute package roots and no token/baseUrl residue.
            self.assertEqual(composition, launch.render_composition())
            self.assertEqual(
                sorted(item.name for item in preset.iterdir()),
                [".dsh-bundle-version", "agent.cordis.yml", "preset.yml",
                 "skill-root.txt"],
            )
            before = (preset / "agent.cordis.yml").stat().st_mtime_ns

            second = run()
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(second.stdout), [])
            self.assertEqual(
                (preset / "agent.cordis.yml").stat().st_mtime_ns, before,
                "a version-matching boot must not rewrite the preset",
            )

    def test_lib_ensure_preset_warns_and_never_throws_without_payload(self):
        # Failure policy (module header): a broken payload must NOT throw out
        # of apply() — a throwing row breaks the whole dsh boot, which is far
        # worse than a missing preset. The row warns and returns.
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable (host row cannot be exercised)")
        lib_uri = (_REPO_ROOT / "lib" / "index.js").resolve().as_uri()
        with tempfile.TemporaryDirectory() as td:
            # A package copy whose preset payload is absent. V2 (FEAT-030): the
            # payload's location comes from the host contract — the row holds no
            # inlined copy of it (J-4) — so the copy carries the contract and is
            # still missing only the payload. Without that contract the failure
            # under test would be "contract unreadable", a different guard.
            fake_pkg = Path(td) / "pkg"
            (fake_pkg / "lib").mkdir(parents=True)
            (fake_pkg / "adapters" / "dsh").mkdir(parents=True)
            (fake_pkg / "lib" / "index.js").write_text(
                (_REPO_ROOT / "lib" / "index.js").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            shutil.copyfile(
                _REPO_ROOT / "adapters" / "dsh" / "host-contract.json",
                fake_pkg / "adapters" / "dsh" / "host-contract.json",
            )
            (fake_pkg / "package.json").write_text(
                '{"name":"fake","version":"9.9.9","type":"module",'
                '"main":"lib/index.js"}\n',
                encoding="utf-8",
            )
            dsh_home = Path(td) / "home"
            script = (
                f"import {{ apply }} from {json.dumps((fake_pkg / 'lib' / 'index.js').as_uri())};"
                "const warns = [];"
                "const ctx = { logger: { warn: (m) => warns.push(String(m)), info: () => {} } };"
                "apply(ctx);"
                "process.stdout.write(JSON.stringify(warns));"
            )
            env = os.environ.copy()
            env["DSH_HOME"] = str(dsh_home)
            result = subprocess.run(
                [node, "--input-type=module", "-e", script],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            warns = json.loads(result.stdout)
            self.assertTrue(
                any("payload incomplete" in warning for warning in warns), warns)
            self.assertFalse(
                (dsh_home / ".agent-presets" / "governance").exists(),
                "a failed render must leave no preset behind",
            )

    def test_lib_cleanup_never_deletes_a_directory_it_did_not_create(self):
        # FIX-313 (design §6.1 V10 / AUDIT-153). RED before the fix: the catch
        # block enumerated the preset root and deleted every entry whose name
        # started with `governance.staging-`, so this user directory (which the
        # row never created) was removed together with the real staging tree.
        # GREEN after: the cleanup addresses only the staging directory THIS
        # attempt proved it created, and the undecidable name is left alone.
        if not shutil.which("node"):
            self.skipTest("node unavailable (host row cannot be exercised)")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = _catching_package_copy(root)
            cwd = root / "cwd"
            home = root / "home"
            dsh_home = root / "dshhome"
            for path in (cwd, home, dsh_home):
                path.mkdir(parents=True)
            preset_root = dsh_home / ".agent-presets"
            preset_root.mkdir(parents=True)
            rogue = preset_root / _ROGUE_STAGING_NAME
            rogue.mkdir()
            (rogue / "NOTES.md").write_text("my own scratch dir\n", encoding="utf-8")

            result = _run_catch_probe(pkg / "lib" / "index.js", cwd, dsh_home, home)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["outcome"]["synced"], payload)
            self.assertTrue(
                any("preset sync failed" in warning for warning in payload["warns"]),
                payload,
            )
            # The fix's core claim: an unprovable target is never removed.
            self.assertTrue(
                rogue.is_dir(),
                "cleanup deleted a directory the row never created "
                "(name prefix is not proof of ownership)",
            )
            self.assertTrue(
                (rogue / "NOTES.md").is_file(),
                "cleanup emptied a directory it never created",
            )

    def test_lib_cleanup_still_removes_its_own_staging_directory(self):
        # Positive control for the V10 predicate: proving ownership must not be
        # bought by refusing to clean up at all. The same failure that leaves a
        # foreign directory alone must still remove the staging directory the
        # attempt created — otherwise every failed sync would leak a full
        # rendered preset next to the user's preset root forever.
        if not shutil.which("node"):
            self.skipTest("node unavailable (host row cannot be exercised)")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = _catching_package_copy(root)
            cwd = root / "cwd"
            home = root / "home"
            dsh_home = root / "dshhome"
            for path in (cwd, home, dsh_home):
                path.mkdir(parents=True)
            preset_root = dsh_home / ".agent-presets"
            preset_root.mkdir(parents=True)
            rogue = preset_root / _ROGUE_STAGING_NAME
            rogue.mkdir()

            result = _run_catch_probe(pkg / "lib" / "index.js", cwd, dsh_home, home)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["outcome"]["dir"], result.stdout)
            survivors = sorted(path.name for path in preset_root.iterdir())
            self.assertEqual(
                survivors,
                [_ROGUE_STAGING_NAME],
                "the staging directory this attempt created must be cleaned up, "
                "and nothing else may be touched",
            )
            self.assertFalse(
                (dsh_home / ".agent-presets" / "governance").exists(),
                "a failed sync must not leave a preset directory behind",
            )

    def test_lib_eexist_collision_breaker_keeps_every_directory_and_warns(self):
        # FIX-325 / F3 (REVIEW-FIX-313-CODE-R0): the EEXIST rename-retry loop,
        # its 8-attempt circuit breaker and its warning path had zero coverage
        # (mutation M4 passed all three V10 tests). `Date.now` and
        # `Math.random` are pinned so EVERY attempt derives the SAME staging
        # name, and that name pre-exists as a directory the row never created.
        # RED under the pre-V10 shape (`rmSync` + recursive `mkdirSync`: the
        # foreign directory is adopted and destroyed); GREEN requires the
        # breaker: eight losing attempts, zero deletions, one actionable
        # warning naming the parent — and it replaces the self-justifying
        # replay the review graded as zero-capture (F2), so this one test
        # closes F1's fixture gap, F2's rewrite and F3's coverage at once.
        if not shutil.which("node"):
            self.skipTest("node unavailable (host row cannot be exercised)")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = _complete_package_copy(root)
            cwd = root / "cwd"
            home = root / "home"
            dsh_home = root / "dshhome"
            for path in (cwd, home, dsh_home):
                path.mkdir(parents=True)

            result = _run_collision_probe(pkg, dsh_home, home, cwd, [0.5])
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["outcome"]["synced"], payload)
            breaker = [warning for warning in payload["warns"]
                       if "could not create a fresh staging" in warning]
            self.assertTrue(breaker, payload["warns"])
            self.assertIn("no existing directory was removed", breaker[0])
            # The pre-existing directory carrying the colliding name — with
            # its user file — is untouched after eight collisions.
            self.assertTrue(
                payload["collidingSurvived"],
                "the breaker deleted or emptied a directory the row never "
                f"created (name collision is not ownership): {payload}",
            )
            # Zero residue: the losing attempts created nothing and removed
            # nothing — the preset root holds exactly the seeded directory.
            self.assertEqual(payload["after"], payload["before"], payload)

    def test_lib_eexist_collision_retry_syncs_and_keeps_the_foreign_dir(self):
        # The OTHER half of F3: the first pinned draw collides, the second is
        # fresh. The loop must retry — and the retry must complete the whole
        # sync WITHOUT touching the directory the first attempt lost to (the
        # pre-V10 shape deleted it right before adopting its name).
        if not shutil.which("node"):
            self.skipTest("node unavailable (host row cannot be exercised)")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = _complete_package_copy(root)
            cwd = root / "cwd"
            home = root / "home"
            dsh_home = root / "dshhome"
            for path in (cwd, home, dsh_home):
                path.mkdir(parents=True)

            result = _run_collision_probe(pkg, dsh_home, home, cwd, [0.1, 0.9])
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["outcome"]["synced"], payload)
            self.assertTrue(
                payload["collidingSurvived"],
                "the winning retry destroyed the directory the losing first "
                f"attempt collided with: {payload}",
            )
            # The sync really landed: the user preset holds the four payload
            # files, and no staging residue survives the rename.
            user_dir = dsh_home / ".agent-presets" / "governance"
            names = sorted(entry.name for entry in user_dir.iterdir())
            self.assertEqual(len(names), 4, names)
            self.assertIn("agent.cordis.yml", names, names)
            self.assertIn("preset.yml", names, names)
            preset_root = dsh_home / ".agent-presets"
            # The ONLY new entry in the preset root is the synced preset
            # itself: no staging residue survives the rename.
            self.assertEqual(
                sorted(entry.name for entry in preset_root.iterdir()),
                sorted(payload["before"] + ["governance"]),
                payload,
            )

    def test_lib_cwd_degradation_never_deletes_a_cwd_staging_directory(self):
        # FIX-325 / F1 — V10 acceptance ① (G-04 CWD degradation inverse), the
        # machine guard the review found MISSING (mutation M5 restored the old
        # CWD sweep and the whole suite stayed green while the CWD misdeletion
        # survived). When `resolveDshHome()` THROWS, `outcome.dir` stays '' and
        # the pre-V10 catch enumerated `dirname('.')` — the PROCESS CWD —
        # deleting every `governance.staging-*` entry there. The fixture seeds
        # such a directory in the CWD and faults the row's `homedir` import via
        # the synchronous ESM `registerHooks` (Node >= 22.15; repo engines
        # >= 20 — older runtimes NOT_RUN this guard, per the FIX-325 policy).
        if not shutil.which("node"):
            self.skipTest("node unavailable (host row cannot be exercised)")
        if not _node_register_hooks_available():
            self.skipTest(
                "Node >= 22.15 required for the ESM registerHooks fault "
                "injection (repo declares engines >= 20) — NOT_RUN per the "
                "FIX-325 skip/NOT_RUN policy")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg = _complete_package_copy(root)
            cwd = root / "cwd"
            home = root / "home"
            for path in (cwd, home):
                path.mkdir(parents=True)

            result = _run_cwd_fault_probe(pkg / "lib" / "index.js", cwd, home,
                                          _ROGUE_STAGING_NAME)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            # The row failed BEFORE a staging directory existed, said so, and
            # — the core claim — the CWD decoy survived.
            self.assertIsNone(payload["threw"], payload)
            self.assertFalse(payload["outcome"]["synced"], payload)
            self.assertFalse(payload["outcome"]["dir"], payload)
            self.assertTrue(
                any("nothing was removed" in warning
                    for warning in payload["warns"]),
                payload,
            )
            self.assertTrue(
                payload["decoySurvived"],
                "cleanup swept the process CWD for staging-prefixed names and "
                f"deleted a directory the row never created: {payload}",
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
