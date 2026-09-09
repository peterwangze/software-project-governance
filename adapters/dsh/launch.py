#!/usr/bin/env python3
"""DeepSeek Harness adapter launcher for software-project-governance.

Unlike the other adapters, whose launchers only print the manifest,
dsh has a real install surface: an agent preset is a plain directory under
``${DSH_HOME}/.agent-presets/<id>/`` holding ``agent.cordis.yml`` +
``preset.yml``. This launcher generates the ``governance`` preset from the
template in this directory and, optionally, writes the DSH project bootstrap
(``AGENTS.md``) into a governed project root.

Modes:
  --check              Print the adapter manifest summary (default action).
  --install / --sync   (Re)write the preset into ${DSH_HOME}/.agent-presets/governance.
                       --sync is the post-`git pull` refresh path.
  --uninstall          Remove the governance preset — deletes exactly
                       ${DSH_HOME}/.agent-presets/governance/ and nothing else
                       (sibling presets and every other file under DSH_HOME
                       untouched; path-escape guard built in). Idempotent: a
                       missing preset is a clean no-op. This is the official
                       preset-side uninstall path — `dsh plugin remove` manages
                       the profile's pnpm bundle layer, never the user preset
                       root, so it cannot remove this preset.
  --dry-run            Safety mode (FEAT-010 incident / DEC-158 R1 protocol):
                       print the resolved ${DSH_HOME} and every planned write
                       without touching the filesystem. Verify the adapter this
                       way, or against a redirected DSH_HOME — never by
                       installing into the real ~/.dsh.
  --smoke              Isolated preset-session smoke gate (FEAT-015 /
                       RISK-049 ②): generate the preset under a REDIRECTED
                       DSH_HOME and prove the session loading surface — the
                       skill catalog root (skills/software-project-governance/
                       SKILL.md) and the /governance gesture projection
                       (skill-shims/governance.md → commands/governance.md) —
                       for both the installed and the shipped in-package
                       preset. Exit 0 = PASS, 1 = FAIL, 2 = REFUSED. The
                       guard refuses to run when DSH_HOME is unset or resolves
                       to (or around) the real ${HOME}/.dsh, and the real home
                       is fingerprinted before/after (metadata only) so a
                       write would be detected. Resolution-level only: it
                       never claims LLM session behavior (printed as NOT_RUN).
  --mode link|copy     link (default): the preset registers the repo's own
                       skills/ + adapters/dsh/skill-shims/ directories as
                       custom skill roots — repo edits are picked up live by
                       the dsh skill watcher. copy: snapshot those two trees
                       into the preset directory so the preset stays valid if
                       the repo moves. Also selects the --smoke generation mode.
  --bootstrap-project DIR [--force]
                       Write the DSH AGENTS.md bootstrap into DIR (thin
                       pointer; it must not duplicate workflow rules). Refuses
                       to overwrite an existing different AGENTS.md without
                       --force.

The generated composition never needs the file sandbox: it only reads skills
and points agents at scripts under this repository. It registers no services,
so the dsh mount audit accepts it from any user preset root.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[2]
ADAPTER_DIR = ROOT / "adapters" / "dsh"
MANIFEST_PATH = ADAPTER_DIR / "adapter-manifest.json"
COMPOSITION_TEMPLATE = ADAPTER_DIR / "agent.cordis.yml.template"
PRESET_METADATA = ADAPTER_DIR / "preset.yml"
BOOTSTRAP_TEMPLATE = ADAPTER_DIR / "AGENTS.md.template"

SKILLS_TOKEN = "__GOVERNANCE_SKILLS_ROOT__"
SHIMS_TOKEN = "__GOVERNANCE_SHIMS_ROOT__"
REPO_TOKEN = "__GOVERNANCE_REPO_ROOT__"

PRESET_ID = "governance"


def dsh_home() -> Path:
    env = os.environ.get("DSH_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".dsh"


def preset_dir() -> Path:
    return dsh_home() / ".agent-presets" / PRESET_ID


def print_manifest(manifest: dict) -> None:
    print("== DeepSeek Harness Adapter Launcher ==")
    print(f"workflow: {manifest['workflow_id']}")
    print(f"entry_type: {manifest['entry_type']}")
    print(f"support_status: {manifest['support_status']}")
    print("trigger:")
    for item in manifest["trigger"]:
        print(f" - {item}")
    print("read_order:")
    for index, item in enumerate(manifest["inputs"], start=1):
        print(f" {index}. {item}")
    print("outputs:")
    for item in manifest["outputs"]:
        print(f" - {item}")
    print("native_entry:")
    for key in sorted(manifest["native_entry"]):
        print(f" - {key}: {manifest['native_entry'][key]}")
    print("runtime_e2e:")
    runtime_e2e = manifest["runtime_e2e"]
    print(f" - e2e_level: {runtime_e2e['e2e_level']}")
    print(f" - command: {runtime_e2e['command']}")
    print(f" - version_command: {runtime_e2e['version_command']}")
    print(f" - full_e2e_verified: {runtime_e2e.get('full_e2e_verified')}")
    print("validation:")
    print(f" - command: {manifest['validation']['command']}")


def install_preset(mode: str, dry_run: bool = False) -> int:
    target = preset_dir()
    if dry_run:
        print(f"[DRY-RUN] dsh home     : {dsh_home()}")
        print(f"[DRY-RUN] preset dir   : {target}")
        if mode == "copy":
            print(f"[DRY-RUN] snapshot     : {target / 'skills'} , {target / 'skill-shims'}")
        else:
            print(f"[DRY-RUN] skill roots  : {ROOT / 'skills'}")
            print(f"[DRY-RUN] command roots: {ADAPTER_DIR / 'skill-shims'}")
        planned = "agent.cordis.yml, preset.yml, skill-root.txt"
        if mode == "copy":
            planned += " (+ skills/ and skill-shims/ snapshots)"
        print(f"[DRY-RUN] planned write: {planned}")
        print("[DRY-RUN] nothing written — re-run without --dry-run to install")
        return 0
    target.mkdir(parents=True, exist_ok=True)

    if mode == "copy":
        skills_root = target / "skills"
        shims_root = target / "skill-shims"
        if skills_root.exists():
            shutil.rmtree(skills_root)
        if shims_root.exists():
            shutil.rmtree(shims_root)
        shutil.copytree(ROOT / "skills", skills_root)
        shutil.copytree(ADAPTER_DIR / "skill-shims", shims_root)
        print(f"snapshot copied: {skills_root}")
        print(f"snapshot copied: {shims_root}")
    else:  # link
        skills_root = ROOT / "skills"
        shims_root = ADAPTER_DIR / "skill-shims"

    template = COMPOSITION_TEMPLATE.read_text(encoding="utf-8")
    composition = (
        template.replace(SKILLS_TOKEN, str(skills_root.resolve()).replace("\\", "/"))
        .replace(SHIMS_TOKEN, str(shims_root.resolve()).replace("\\", "/"))
        .replace(REPO_TOKEN, str(ROOT.resolve()).replace("\\", "/"))
    )
    for token in (SKILLS_TOKEN, SHIMS_TOKEN, REPO_TOKEN):
        if token in composition:
            print(f"ERROR: template token {token} not substituted", file=sys.stderr)
            return 1

    (target / "agent.cordis.yml").write_text(composition, encoding="utf-8")
    shutil.copyfile(PRESET_METADATA, target / "preset.yml")
    # Hook discovery marker: the repo hooks' find_spg_home reads this file to
    # resolve the workflow home under dsh (link mode), so installed project
    # hooks keep self-upgrading after `git pull` + `--sync`.
    (target / "skill-root.txt").write_text(
        str(ROOT.resolve()).replace("\\", "/") + "\n", encoding="utf-8"
    )
    print(f"preset written: {target}")
    print(f"  composition : {target / 'agent.cordis.yml'}")
    print(f"  metadata    : {target / 'preset.yml'}")
    print(f"  skill-root  : {target / 'skill-root.txt'}")
    print(f"  skill roots : {skills_root}")
    print(f"  command root: {shims_root}")
    print(
        "Next: start a dsh session and select the '治理协调器' (governance) "
        "preset, or run `python adapters/dsh/launch.py --bootstrap-project "
        "<project>` to bootstrap an existing project."
    )
    return 0


def uninstall_preset(dry_run: bool = False) -> int:
    """Remove the governance preset from ${DSH_HOME}/.agent-presets/governance.

    Deletes exactly that one preset directory; sibling presets and every
    other file under ${DSH_HOME} are never touched. Idempotent: a missing
    preset is a clean no-op (exit 0), not an error.
    """
    target = preset_dir()
    # Path-escape guard: the resolved target must sit directly under an
    # `.agent-presets` parent before anything is deleted.
    if target.parent.name != ".agent-presets" or target.name != PRESET_ID:
        print(
            f"ERROR: refusing to uninstall unexpected path: {target}",
            file=sys.stderr,
        )
        return 1
    if not target.exists():
        print(f"not installed: {target} (nothing to do)")
        return 0
    entries = sorted(p.name for p in target.iterdir())
    if dry_run:
        print(f"[DRY-RUN] dsh home      : {dsh_home()}")
        print(f"[DRY-RUN] preset dir    : {target}")
        print(
            f"[DRY-RUN] planned delete: {target} "
            f"({len(entries)} entr{'y' if len(entries) == 1 else 'ies'}: "
            f"{', '.join(entries)})"
        )
        print("[DRY-RUN] nothing deleted — re-run without --dry-run to uninstall")
        return 0
    shutil.rmtree(target)
    print(f"preset removed: {target}")
    print(f"  deleted entries: {', '.join(entries)}")
    print("  sibling presets and all other DSH_HOME content untouched")
    return 0


# ── isolated preset-session smoke gate (FEAT-015 / RISK-049 ②) ──────────────
#
# RISK-049 closure standard (2): "安装后 preset 会话可用" must become a
# repeatable machine gate instead of reasoning. The smoke generates the preset
# under a REDIRECTED DSH_HOME (M7.7 protection baseline (a) — isolation) and
# resolves the two loading surfaces a session needs:
#   1. the skill catalog root (skills/software-project-governance/SKILL.md),
#   2. the /governance gesture projection (skill-shims/governance.md → the
#      shared commands/governance.md it points at).
# Both surfaces are checked for the INSTALLED preset (generated into the
# redirected home) and for the SHIPPED in-package preset (baseUrl
# self-location — the FIX-290 regression surface).
#
# Isolation is structural, not advisory: the guard REFUSES to run unless
# DSH_HOME is redirected away from the real home (unset, or resolving to /
# above / inside ${HOME}/.dsh is rejected before any write), and the real home
# is fingerprinted before/after (metadata only — no file content is read, so
# credentials are never touched) so any write would be detected and FAIL.
#
# Resolution-level by design: this proves the composition a session mounts
# carries the catalog and the gesture. It does NOT run an LLM session and
# prints that boundary as NOT_RUN instead of implying it.

SMOKE_CATALOG_SKILL = ("software-project-governance", "SKILL.md")
SMOKE_GESTURE_NAME = "governance"
SMOKE_GESTURE_TARGET = ("commands", "governance.md")

SMOKE_EXIT_PASS = 0
SMOKE_EXIT_FAIL = 1
SMOKE_EXIT_REFUSED = 2


def real_dsh_home() -> Path:
    """The REAL user DSH home — derived from the user profile, never from env.

    The isolation guard compares the ambient ``DSH_HOME`` against this path, so
    an env override can never disguise the real home as "redirected".
    """
    return Path.home() / ".dsh"


def _normcase_path(path: Path) -> str:
    try:
        resolved = path.expanduser().resolve()
    except OSError:  # pragma: no cover - unresolvable path
        resolved = path.expanduser().absolute()
    return os.path.normcase(str(resolved))


def _is_within(child: Path, parent: Path) -> bool:
    """True when ``child`` equals ``parent`` or sits underneath it."""
    child_n = _normcase_path(child)
    parent_n = _normcase_path(parent)
    if child_n == parent_n:
        return True
    return child_n.startswith(parent_n.rstrip("\\/") + os.sep)


def _home_fingerprint(home: Path) -> dict:
    """Read-only metadata fingerprint of a DSH home (no file content read).

    Returns ``{"state": "absent"|"present", "entries": [kind:rel:size:mtime_ns]}``.
    Only ``lstat`` metadata is collected — file contents (e.g.
    ``credentials.yaml``) are never opened or printed.
    """
    if not home.exists():
        return {"state": "absent", "entries": []}
    entries = []
    for dirpath, dirnames, filenames in os.walk(home, followlinks=False):
        dirnames.sort()
        for name in sorted(dirnames) + sorted(filenames):
            path = Path(dirpath) / name
            try:
                stat = path.lstat()
            except OSError:  # pragma: no cover - transient/racy entry
                continue
            kind = "d" if (stat.st_mode & 0o170000) == 0o040000 else "f"
            entries.append(
                f"{kind}:{path.relative_to(home).as_posix()}:"
                f"{stat.st_size}:{stat.st_mtime_ns}"
            )
    return {"state": "present", "entries": entries}


def _real_home_witness(home: Path) -> dict:
    """Deterministic zero-write witness for the real DSH home.

    Two components, both stable while a live host session runs:

    1. ``write_surface`` — recursive fingerprint of ``<home>/.agent-presets``,
       the ONLY path this adapter ever writes under a DSH home
       (``preset_dir()``). Byte-identical means no adapter write happened.
    2. ``top_level`` — names of ``<home>`` plus size/mtime_ns of its top-level
       FILES (settings.yaml, credentials.yaml, …). Directory mtimes are
       excluded: host activity inside a subtree bumps them.

    A whole-home comparison is deliberately NOT used: measured 2026-09-09,
    two full-home reads 3 s apart differ (a live session appends
    ``dsh-agent-router/stats/*``) while ``.agent-presets`` stays identical, so
    a whole-home oracle would fail for host activity, not for this gate.
    Subtrees owned by the live host (sessions/, storages/, profiles/,
    dsh-agent-router/, attachments/) are out of scope and never written by
    this launcher.
    """
    top_level = []
    if home.is_dir():
        for path in sorted(home.iterdir()):
            try:
                stat = path.lstat()
            except OSError:  # pragma: no cover - transient/racy entry
                continue
            if (stat.st_mode & 0o170000) == 0o040000:
                top_level.append(f"d:{path.name}")
            else:
                top_level.append(f"f:{path.name}:{stat.st_size}:{stat.st_mtime_ns}")
    return {
        "state": "present" if home.exists() else "absent",
        "write_surface": _home_fingerprint(home / ".agent-presets")["entries"],
        "top_level": top_level,
    }


def _custom_skill_dir_entries(composition: str) -> list:
    """Raw ``customSkillDirs`` entries of a composition text, in order."""
    entries = []
    block_indent = None
    for line in composition.splitlines():
        stripped = line.strip()
        if block_indent is None:
            if stripped.startswith("customSkillDirs:"):
                block_indent = len(line) - len(line.lstrip())
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if len(line) - len(line.lstrip()) <= block_indent:
            break
        match = re.match(r"^-\s+(.*)$", stripped)
        if not match:
            break
        entries.append(match.group(1).strip())
    return entries


def _resolve_skill_entry(entry: str, preset_dir: Path):
    """Resolve one ``customSkillDirs`` entry → ``(form, path, issue)``.

    Handles both sanctioned forms: the launcher's substituted absolute paths
    and the shipped preset's ``!!js`` ``baseUrl`` self-location (evaluated with
    the same URL math dsh applies, against the composition file's directory).
    A literal relative entry is reported as an issue — it resolves against the
    dsh process CWD and silently empties the session catalog (FIX-290).
    """
    raw = entry.strip()
    if raw.startswith("!!js"):
        body = raw[len("!!js"):].strip().strip('"').strip("'")
        match = re.search(r"new URL\(\s*'([^']+)'\s*,\s*baseUrl\s*\)", body)
        if not match:
            return "baseUrl", None, (
                f"customSkillDirs entry is a !!js expression that does not "
                f"resolve against baseUrl: {raw}")
        preset_uri = preset_dir.resolve().as_uri() + "/"
        resolved = urljoin(preset_uri, match.group(1))
        local = urllib.request.url2pathname(urlparse(resolved).path)
        return "baseUrl", Path(local), None
    raw = raw.strip("'\"")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        return "relative", candidate, (
            f"customSkillDirs entry is a literal relative path ({raw!r}) — it "
            "resolves against the dsh process CWD (FIX-290) and silently "
            "empties the session catalog")
    return "absolute", candidate, None


def _repo_root_for_preset(preset_dir: Path, catalog_root):
    """Repo root of a preset: the skill-root marker, else the catalog parent."""
    marker = preset_dir / "skill-root.txt"
    if marker.is_file():
        try:
            text = marker.read_text(encoding="utf-8").strip()
        except OSError:  # pragma: no cover - unreadable marker
            text = ""
        if text:
            return Path(text)
    if catalog_root is not None:
        return catalog_root.parent
    return None


def verify_preset_loading(preset_dir: Path, repo_root=None) -> dict:
    """Resolve a preset's skill roots + the ``/governance`` gesture (read-only).

    Pure verification over an installed or shipped preset directory. Returns
    ``{"verdict": "PASS"|"FAIL", "issues": [...], "skill_roots": [...],
    "skill_catalog", "gesture_shim", "gesture_target", "repo_root"}`` with
    POSIX-form paths (the report and assertions compare them literally).
    """
    preset_dir = Path(preset_dir)
    result = {
        "verdict": "PASS",
        "issues": [],
        "skill_roots": [],
        "skill_catalog": None,
        "gesture_shim": None,
        "gesture_target": None,
        "repo_root": None,
    }
    composition_path = preset_dir / "agent.cordis.yml"
    if not composition_path.is_file():
        result["issues"].append(
            f"preset composition missing: {composition_path.as_posix()}")
        result["verdict"] = "FAIL"
        return result
    composition = composition_path.read_text(encoding="utf-8")
    entries = _custom_skill_dir_entries(composition)
    if not entries:
        result["issues"].append(
            "preset declares no customSkillDirs — the session skill catalog "
            "would be empty and /governance would not load")
    resolved_roots = []
    for entry in entries:
        form, path, issue = _resolve_skill_entry(entry, preset_dir)
        if issue:
            result["issues"].append(issue)
        exists = bool(path is not None and path.is_dir())
        result["skill_roots"].append({
            "entry": entry,
            "form": form,
            "path": path.as_posix() if path is not None else None,
            "exists": exists,
        })
        if path is not None and exists:
            resolved_roots.append(path)
        elif path is not None and not issue:
            result["issues"].append(
                f"customSkillDirs root does not exist: {path.as_posix()}")

    catalog_root = None
    for root in resolved_roots:
        candidate = root.joinpath(*SMOKE_CATALOG_SKILL)
        if candidate.is_file():
            catalog_root = root
            result["skill_catalog"] = candidate.as_posix()
            break
    if result["skill_catalog"] is None:
        result["issues"].append(
            "skill directory not loaded: no customSkillDirs root contains "
            f"{'/'.join(SMOKE_CATALOG_SKILL)}")

    shim_path = None
    for root in resolved_roots:
        candidate = root / f"{SMOKE_GESTURE_NAME}.md"
        if candidate.is_file():
            shim_path = candidate
            result["gesture_shim"] = candidate.as_posix()
            break
    if shim_path is None:
        result["issues"].append(
            f"/{SMOKE_GESTURE_NAME} projection skill missing: no "
            f"customSkillDirs root contains {SMOKE_GESTURE_NAME}.md (the "
            f"/{SMOKE_GESTURE_NAME} gesture would not load)")
    else:
        shim_text = shim_path.read_text(encoding="utf-8", errors="replace")
        if not shim_text.startswith("---") \
                or f"name: {SMOKE_GESTURE_NAME}\n" not in shim_text \
                or not re.search(r"^description:\s*\S", shim_text, re.MULTILINE):
            result["issues"].append(
                f"/{SMOKE_GESTURE_NAME} projection skill is not a loadable dsh "
                f"skill (frontmatter name/description): {shim_path.as_posix()}")

    root = Path(repo_root) if repo_root is not None else \
        _repo_root_for_preset(preset_dir, catalog_root)
    result["repo_root"] = root.as_posix() if root is not None else None
    if root is None:
        result["issues"].append(
            f"/{SMOKE_GESTURE_NAME} projection target unresolved: no "
            "skill-root.txt marker and no skill catalog parent to derive the "
            "repo root from")
    else:
        target = root.joinpath(*SMOKE_GESTURE_TARGET)
        if target.is_file():
            result["gesture_target"] = target.as_posix()
        else:
            result["issues"].append(
                f"/{SMOKE_GESTURE_NAME} projection target missing: "
                f"{target.as_posix()} (the shim is a thin pointer to it)")

    if result["issues"]:
        result["verdict"] = "FAIL"
    return result


def _print_surface_report(label, surface):
    print(f"[SMOKE] surface          : {label}")
    print(f"[SMOKE]   skill roots    : {len(surface['skill_roots'])}")
    for root in surface["skill_roots"]:
        mark = "ok" if root["exists"] else "MISSING"
        print(f"[SMOKE]     - [{root['form']}] {root['path']} ({mark})")
    print(f"[SMOKE]   skill catalog  : "
          f"{surface['skill_catalog'] or 'MISSING'}")
    print(f"[SMOKE]   gesture shim   : {surface['gesture_shim'] or 'MISSING'}")
    print(f"[SMOKE]   gesture target : "
          f"{surface['gesture_target'] or 'UNRESOLVED'}")
    print(f"[SMOKE]   verdict        : {surface['verdict']}")
    for issue in surface["issues"]:
        print(f"[SMOKE]   [FAIL] {issue}")


def smoke_preset(mode: str = "link") -> int:
    """Isolated preset-session smoke gate (FEAT-015 / RISK-049 ②).

    Exit codes: 0 = PASS, 1 = FAIL (a loading surface is missing), 2 =
    REFUSED (isolation guard). The isolated DSH_HOME is caller-owned and left
    in place (re-runs are idempotent); the gate's own callers create/remove it.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):  # pragma: no cover - non-tty stdout
        pass
    print("== DSH preset session smoke (FEAT-015 / RISK-049 ②) ==")
    home = real_dsh_home()
    env_home = (os.environ.get("DSH_HOME") or "").strip()
    if not env_home:
        message = (
            f"[SMOKE] [REFUSED] DSH_HOME is not set — refusing to run the "
            f"smoke (M7.7: it must be redirected to a temporary directory; "
            f"the real home {home} is never a target)")
        print(message)
        print(message, file=sys.stderr)
        print(f"[SMOKE] Result: REFUSED (exit {SMOKE_EXIT_REFUSED})")
        return SMOKE_EXIT_REFUSED
    isolated = Path(env_home).expanduser()
    if _is_within(isolated, home) or _is_within(home, isolated):
        message = (
            f"[SMOKE] [REFUSED] DSH_HOME resolves to the real DSH home "
            f"({home}) — refusing to run (M7.7: never write the real home)")
        print(message)
        print(message, file=sys.stderr)
        print(f"[SMOKE] Result: REFUSED (exit {SMOKE_EXIT_REFUSED})")
        return SMOKE_EXIT_REFUSED

    print(f"[SMOKE] isolated DSH_HOME: {isolated}")
    print(f"[SMOKE] real DSH home    : {home}")
    before = _real_home_witness(home)
    print(f"[SMOKE] real home before : state={before['state']} "
          f"write_surface={len(before['write_surface'])} entry(ies), "
          f"top_level={len(before['top_level'])} (metadata only)")
    isolated.mkdir(parents=True, exist_ok=True)

    issues = []
    saved_home = os.environ.get("DSH_HOME")
    try:
        os.environ["DSH_HOME"] = str(isolated)
        if install_preset(mode) != 0:
            issues.append("preset installation failed in the isolated home")
    finally:
        if saved_home is None:
            os.environ.pop("DSH_HOME", None)
        else:
            os.environ["DSH_HOME"] = saved_home

    surfaces = (
        ("installed preset (generated in the isolated DSH_HOME)",
         isolated / ".agent-presets" / PRESET_ID),
        ("shipped in-package preset (baseUrl self-location)",
         ROOT / "presets" / PRESET_ID),
    )
    for label, directory in surfaces:
        surface = verify_preset_loading(directory)
        _print_surface_report(label, surface)
        issues.extend(f"{label}: {issue}" for issue in surface["issues"])

    after = _real_home_witness(home)
    unchanged = before == after
    print(f"[SMOKE] real-home writes : {0 if unchanged else 1} "
          f"({'witness unchanged — top level + .agent-presets recursive' if unchanged else 'WITNESS CHANGED'})")
    if not unchanged:
        issues.append(
            f"real DSH home witness changed during the smoke: {home} — the "
            "isolation guarantee is broken (top-level entries and/or "
            ".agent-presets write surface)")

    dsh_cli = shutil.which("dsh") or shutil.which("dsh.cmd") \
        or shutil.which("dsh.ps1")
    print(f"[SMOKE] dsh CLI          : {dsh_cli or 'absent'}")
    print("[SMOKE] live session面   : NOT_RUN — this gate verifies the loading "
          "surface only (preset generation + skill catalog + /governance "
          "gesture resolution); no LLM session is executed and no session "
          "behavior is claimed" + ("" if dsh_cli else " (dsh CLI absent)"))

    if issues:
        print(f"[SMOKE] Result: FAIL (exit {SMOKE_EXIT_FAIL}) — "
              f"{len(issues)} issue(s)")
        for issue in issues:
            print(f"[SMOKE]   [FAIL] {issue}", file=sys.stderr)
        return SMOKE_EXIT_FAIL
    print(f"[SMOKE] Result: PASS (isolated loading surface verified; "
          f"real home untouched)")
    return SMOKE_EXIT_PASS


def write_bootstrap(project: Path, force: bool, dry_run: bool = False) -> int:
    project = project.expanduser().resolve()
    if not project.is_dir():
        print(f"ERROR: project root is not a directory: {project}", file=sys.stderr)
        return 1
    target = project / "AGENTS.md"
    rendered = BOOTSTRAP_TEMPLATE.read_text(encoding="utf-8").replace(
        REPO_TOKEN, str(ROOT.resolve()).replace("\\", "/")
    )
    if REPO_TOKEN in rendered:
        print(f"ERROR: template token {REPO_TOKEN} not substituted", file=sys.stderr)
        return 1
    if target.exists() and not force:
        existing = target.read_text(encoding="utf-8", errors="replace")
        if "Governance Bootstrap" not in existing:
            print(
                f"ERROR: {target} exists without a Governance Bootstrap section; "
                "re-run with --force to overwrite",
                file=sys.stderr,
            )
            return 1
    if dry_run:
        print(f"[DRY-RUN] bootstrap target: {target}")
        print("[DRY-RUN] planned write  : AGENTS.md (thin governance pointer)")
        print("[DRY-RUN] nothing written — re-run without --dry-run to write")
        return 0
    target.write_text(rendered, encoding="utf-8")
    print(f"bootstrap written: {target}")
    return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(
        description="DeepSeek Harness adapter launcher for software-project-governance."
    )
    parser.add_argument(
        "--check", action="store_true", help="print the adapter manifest summary"
    )
    parser.add_argument(
        "--install",
        "--sync",
        dest="install",
        action="store_true",
        help="(re)write the governance preset into ${DSH_HOME}/.agent-presets/governance",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="remove the governance preset (deletes exactly "
        "${DSH_HOME}/.agent-presets/governance; sibling presets untouched)",
    )
    parser.add_argument(
        "--mode",
        choices=["link", "copy"],
        default="link",
        help="link = register the repo's own skill roots (default); "
        "copy = snapshot them into the preset directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the resolved ${DSH_HOME} and planned writes without "
        "touching the filesystem (safe verification; DEC-158 R1)",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="isolated preset-session smoke gate (FEAT-015 / RISK-049 ②): "
        "generate the preset under a redirected DSH_HOME and verify the skill "
        "catalog + /governance gesture resolve (exit 0 PASS / 1 FAIL / "
        "2 REFUSED — refuses an unredirected DSH_HOME)",
    )
    parser.add_argument(
        "--bootstrap-project",
        metavar="DIR",
        default=None,
        help="write the DSH AGENTS.md bootstrap into a project root",
    )
    parser.add_argument(
        "--force", action="store_true", help="allow --bootstrap-project to overwrite"
    )
    args = parser.parse_args(argv)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    acted = False
    exit_code = 0

    if args.install and args.uninstall:
        parser.error("--install and --uninstall are mutually exclusive")

    if args.smoke and (args.install or args.uninstall or args.bootstrap_project
                       or args.dry_run):
        parser.error(
            "--smoke is a standalone isolated verification; do not combine it "
            "with --install / --uninstall / --bootstrap-project / --dry-run")

    if args.smoke:
        acted = True
        exit_code = smoke_preset(args.mode) or exit_code
    if args.install:
        acted = True
        exit_code = install_preset(args.mode, dry_run=args.dry_run) or exit_code
    if args.uninstall:
        acted = True
        exit_code = uninstall_preset(dry_run=args.dry_run) or exit_code
    if args.bootstrap_project:
        acted = True
        exit_code = (
            write_bootstrap(
                Path(args.bootstrap_project), args.force, dry_run=args.dry_run
            )
            or exit_code
        )

    if not acted or args.check:
        print_manifest(manifest)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
