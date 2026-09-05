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
  --mode link|copy     link (default): the preset registers the repo's own
                       skills/ + adapters/dsh/skill-shims/ directories as
                       custom skill roots — repo edits are picked up live by
                       the dsh skill watcher. copy: snapshot those two trees
                       into the preset directory so the preset stays valid if
                       the repo moves.
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
import shutil
import sys
from pathlib import Path

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
