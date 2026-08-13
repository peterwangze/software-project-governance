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


def install_preset(mode: str) -> int:
    target = preset_dir()
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
    print(f"preset written: {target}")
    print(f"  composition : {target / 'agent.cordis.yml'}")
    print(f"  metadata    : {target / 'preset.yml'}")
    print(f"  skill roots : {skills_root}")
    print(f"  command root: {shims_root}")
    print(
        "Next: start a dsh session and select the '治理协调器' (governance) "
        "preset, or run `python adapters/dsh/launch.py --bootstrap-project "
        "<project>` to bootstrap an existing project."
    )
    return 0


def write_bootstrap(project: Path, force: bool) -> int:
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
        "--mode",
        choices=["link", "copy"],
        default="link",
        help="link = register the repo's own skill roots (default); "
        "copy = snapshot them into the preset directory",
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

    if args.install:
        acted = True
        exit_code = install_preset(args.mode) or exit_code
    if args.bootstrap_project:
        acted = True
        exit_code = (
            write_bootstrap(Path(args.bootstrap_project), args.force) or exit_code
        )

    if not acted or args.check:
        print_manifest(manifest)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
