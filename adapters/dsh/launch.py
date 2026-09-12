#!/usr/bin/env python3
"""DeepSeek Harness adapter launcher for software-project-governance.

Unlike the other adapters, whose launchers only print the manifest,
dsh has a real install surface: an agent preset is a plain directory under
``${DSH_HOME}/.agent-presets/<id>/`` holding ``agent.cordis.yml`` +
``preset.yml``. This launcher RENDERS the composition template (substituting
the ``__GOVERNANCE_*__`` tokens with absolute paths) into that directory, and,
optionally, writes the DSH project bootstrap (``AGENTS.md``) into a governed
project root.

Single source (FIX-310 / DEC-187, 2026-09-12): the package's preset payload is
``agent-presets/governance/`` and holds exactly two files — the composition
template ``agent.cordis.yml.template`` (the ONE composition source) and
``preset.yml``. Nothing is duplicated: ``skills/``, ``commands/`` and
``agents/`` stay the repository's shared core, referenced ABSOLUTELY from the
rendered file. ``lib/index.js`` ``ensurePreset()`` renders the identical
composition automatically on bundle boot; this launcher is the manual /
offline path (the reference bundle ships ``install.ps1`` / ``install.sh`` for
the same purpose). Both renderers share the same three-token contract, so they
cannot disagree; ``adapters/dsh/agent.cordis.yml.template`` used to carry that
template and now lives inside the preset payload it renders.

Modes:
  --check              Print the adapter manifest summary (default action).
  --install / --sync   (Re)write the preset into ${DSH_HOME}/.agent-presets/governance
                       by rendering ``agent-presets/governance/agent.cordis.yml.template``
                       (staging directory + rename, so a crash mid-render never
                       leaves a half-written preset). --sync is the post-`git
                       pull` refresh path.
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
                       RISK-049 ②): render the preset under a REDIRECTED
                       DSH_HOME and prove the session loading surface — the
                       skill catalog root (skills/software-project-governance/
                       SKILL.md) and the /governance gesture projection
                       (adapters/dsh/skill-shims/governance.md →
                       commands/governance.md). Exit 0 = PASS, 1 = FAIL,
                       2 = REFUSED. The guard refuses to run when DSH_HOME is
                       unset or resolves to (or around) the real ${HOME}/.dsh,
                       and the real home is fingerprinted before/after
                       (metadata only) so a write would be detected.
                       Resolution-level only: it never claims LLM session
                       behavior (printed as NOT_RUN).
  --bootstrap-project DIR [--force]
                       Write the DSH AGENTS.md bootstrap into DIR (thin
                       pointer; it must not duplicate workflow rules). Refuses
                       to overwrite an existing different AGENTS.md without
                       --force.

The rendered composition never needs the file sandbox: it only reads the
repository's shared skills tree and points agents at scripts under this
repository. It registers no services, so the dsh mount audit accepts it from
any user preset root.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[2]
ADAPTER_DIR = ROOT / "adapters" / "dsh"
MANIFEST_PATH = ADAPTER_DIR / "adapter-manifest.json"
BOOTSTRAP_TEMPLATE = ADAPTER_DIR / "AGENTS.md.template"
# The installed-schema row check lives with the rest of the governance infra
# (single implementation, shared with check-governance Check 28v).
INFRA_DIR = ROOT / "skills" / "software-project-governance" / "infra"

# dsh facts come from the single host-dependency contract (design §2.5 C-2):
# the preset id, the preset payload paths, the render token table, the user
# preset root, the `DSH_HOME` variable name and the marker file names are all
# declared there in `own.preset.*`, `own.render.tokens`, `host.home.*` and
# `host.env.*`. This launcher holds the declared symbols, never their values —
# a second copy of a value is a second source of truth, which is the defect
# class the contract exists to remove. The contract is read **lazily** (see
# `_contract()`), so importing this module never depends on the file being
# present and no inlined fallback copy is needed to keep the import working.
#
# Render contract, shared verbatim with `lib/index.js`: token → package-relative
# path, `""` meaning the package root itself. Both renderers read the same
# `own.render.tokens` map, so `dsh plugin add` and `--install` cannot write
# different presets for the same package version.
SKILLS_TOKEN = "__GOVERNANCE_SKILLS_ROOT__"
SHIMS_TOKEN = "__GOVERNANCE_SHIMS_ROOT__"
REPO_TOKEN = "__GOVERNANCE_REPO_ROOT__"

#: Declared preset facts and the contract path each one is read from. The
#: values are resolved at call time; the names are the traceability anchors the
#: contract self-check compares against (`test_dsh_contract.py`).
PRESET_ID = "governance"
PRESET_MARKER = ".dsh-bundle-version"
SKILL_ROOT_MARKER = "skill-root.txt"

CONTRACT_BINDING = {
    "PRESET_ID": "own.preset.id",
    "PRESET_MARKER": "own.preset.version_marker",
    "SKILL_ROOT_MARKER": "own.preset.skill_root_marker",
    "PACKAGE_PRESET": "own.preset.payload_dir",
    "COMPOSITION_TEMPLATE": "own.preset.template",
    "PRESET_METADATA": "own.preset.metadata",
    "COMPOSITION_FILENAME": "host.home.composition_file",
    "PRESET_DIR_NAME": "host.home.user_preset_dir",
    "HOME_VAR": "host.env.home_var",
    "HOME_FALLBACK": "host.env.write_side.fallback",
    "TOKENS": "own.render.tokens",
    "LEFTOVER_SCAN": "own.render.leftover_scan",
}

#: Memoized contract document; `None` until the first declared fact is read.
_CONTRACT: Optional[dict] = None


def _fact(name: str):
    """Value of one declared dsh fact, resolved from the contract.

    The import is deferred to the first call so this module stays importable on
    its own, and the contract is loaded once per process. A missing, unreadable,
    malformed or schema-unknown contract raises — the caller turns that into an
    actionable message and a non-zero exit; it is never absorbed by falling back
    to a built-in copy (design §2.5 C-2).
    """
    global _CONTRACT
    if str(INFRA_DIR) not in sys.path:
        sys.path.insert(0, str(INFRA_DIR))
    import dsh_contract  # noqa: PLC0415 — deliberate: lazy (see docstring)

    if _CONTRACT is None:
        _CONTRACT = dsh_contract.load_contract()
    path = CONTRACT_BINDING[name]
    value = _CONTRACT
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            raise dsh_contract.ContractMalformed(
                f"ContractMalformed: `{path}` is not declared "
                f"(needed for {name}) in contract "
                f"{dsh_contract.contract_path()}")
        value = value[key]
    return value


def _preset_payload_dir() -> Path:
    return ROOT / Path(_fact("PACKAGE_PRESET"))


def _composition_template() -> Path:
    return ROOT / Path(_fact("COMPOSITION_TEMPLATE"))


def _preset_metadata() -> Path:
    return ROOT / Path(_fact("PRESET_METADATA"))


def _composition_filename() -> str:
    return _fact("COMPOSITION_FILENAME")


def _preset_dir_name() -> str:
    return _fact("PRESET_DIR_NAME")


def _token_paths() -> dict:
    """Token → absolute target, resolved from ``own.render.tokens``.

    The contract declares each token's package-relative path (``""`` = the
    package root itself), so the render map is derived rather than restated.
    """
    return {token: (ROOT / Path(relative) if relative else ROOT)
            for token, relative in _fact("TOKENS").items()}


def _home_fallback_name() -> str:
    """Last path segment of the declared ``$DSH_HOME`` fallback (`<home>/.dsh`)."""
    declared = str(_fact("HOME_FALLBACK"))
    return declared.replace("\\", "/").rsplit("/", 1)[-1]


def dsh_home() -> Path:
    env = os.environ.get(_fact("HOME_VAR"))
    if env:
        return Path(env).expanduser()
    return Path.home() / Path(_fact("HOME_FALLBACK")).name


def preset_dir() -> Path:
    return dsh_home() / _preset_dir_name() / _fact("PRESET_ID")


def package_version() -> str:
    try:
        payload = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "0"
    version = payload.get("version")
    return version if isinstance(version, str) and version else "0"


def render_composition() -> str:
    """Render the composition template with absolute paths.

    Returns ``""`` when the template is missing or a token survives
    substitution — the caller reports it instead of installing a composition
    whose skill roots would silently resolve against the dsh process CWD. The
    ``__…__`` scan is the declared ``own.render.leftover_scan`` set, so a token
    this renderer does not know is reported too.

    Line endings are LF by construction: ``read_text`` uses universal newlines
    (CRLF → LF), which is what ``lib/index.js`` normalizes to as well, so the
    two renderers produce byte-identical text for the same package root.
    """
    try:
        template = _composition_template().read_text(encoding="utf-8")
    except OSError:
        return ""
    composition = template
    tokens = _token_paths()
    for token, path in tokens.items():
        value = str(path.resolve()).replace("\\", "/")
        composition = composition.replace(token, value)
    if re.search(_fact("LEFTOVER_SCAN"), composition):
        return ""
    return composition



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


def write_rendered_preset(destination: Path) -> bool:
    """Render the payload into ``destination`` (no atomicity — the caller owns it).

    Returns ``False`` (leaving no partial directory behind) when the template
    cannot be rendered or its metadata is missing. Shared by
    :func:`install_preset` (into a staging dir) and the smoke gate (into a
    scratch dir), so the shipped payload is verified through exactly the same
    code path that installs it.
    """
    composition = render_composition()
    if not composition or not _preset_metadata().is_file():
        return False
    destination.mkdir(parents=True, exist_ok=True)
    # newline="\n": the rendered composition is LF on every platform, matching
    # `lib/index.js` (YAML is newline-agnostic; parity is what matters).
    (destination / _composition_filename()).write_text(
        composition, encoding="utf-8", newline="\n")
    shutil.copyfile(_preset_metadata(), destination / "preset.yml")
    (destination / _fact("PRESET_MARKER")).write_text(
        package_version() + "\n", encoding="utf-8")
    # Hook discovery marker: the repo hooks' find_spg_home reads this file to
    # resolve the workflow home under dsh, so installed project hooks keep
    # self-upgrading after `git pull` + `--sync`.
    (destination / _fact("SKILL_ROOT_MARKER")).write_text(
        str(ROOT.resolve()).replace("\\", "/") + "\n", encoding="utf-8")
    return True


def install_preset(dry_run: bool = False) -> int:
    """Render the composition into ${DSH_HOME}/.agent-presets/governance.

    Staging directory + ``rename`` replace (identical atomicity contract to
    ``lib/index.js`` ``ensurePreset()``): a crash mid-render can never leave a
    half-written preset behind, which would break every governance session.
    Three files are written — the rendered ``agent.cordis.yml``, the preset
    metadata, and two markers:

      * ``.dsh-bundle-version`` — the idempotence key ``ensurePreset()`` reads;
      * ``skill-root.txt``      — the plugin-home marker the shipped git hooks
        read (``find_spg_home``) so an installed project hook self-upgrades.

    Nothing else is copied: the skill catalog, the command shims and the role
    definitions stay the repository's shared core, referenced by the absolute
    paths rendered into the composition.
    """
    target = preset_dir()
    if dry_run:
        print(f"[DRY-RUN] dsh home       : {dsh_home()}")
        print(f"[DRY-RUN] preset dir     : {target}")
        print(f"[DRY-RUN] composition tpl: {_composition_template()}")
        print(f"[DRY-RUN] render map     : "
              + ", ".join(f"{token} -> {str(path.resolve()).replace(chr(92), '/')}"
                          for token, path in _token_paths().items()))
        print(
            f"[DRY-RUN] planned write  : {_composition_filename()} (rendered), "
            f"preset.yml, {_fact('PRESET_MARKER')}, {_fact('SKILL_ROOT_MARKER')} "
            "(staging + rename replace)"
        )
        print("[DRY-RUN] nothing written — re-run without --dry-run to install")
        return 0

    composition = render_composition()
    if not composition:
        print(
            f"ERROR: cannot render the composition — missing template or an "
            f"unsubstituted token: {_composition_template()}",
            file=sys.stderr,
        )
        return 1
    if not _preset_metadata().is_file():
        print(f"ERROR: preset metadata missing: {_preset_metadata()}", file=sys.stderr)
        return 1

    version = package_version()
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(
        f"{target.name}.staging-{os.getpid()}-{int(time.time() * 1000)}"
    )
    shutil.rmtree(staging, ignore_errors=True)
    if not write_rendered_preset(staging):
        shutil.rmtree(staging, ignore_errors=True)
        print(f"ERROR: rendering the preset failed: {_composition_template()}",
              file=sys.stderr)
        return 1
    if target.exists():
        shutil.rmtree(target)
    staging.rename(target)
    print(f"preset written: {target}")
    print(f"  template    : {_composition_template()}")
    print(f"  composition : {target / _composition_filename()}")
    print(f"  metadata    : {target / 'preset.yml'}")
    targets = _token_paths()
    print(f"  skill roots : {targets[SKILLS_TOKEN]} , {targets[SHIMS_TOKEN]}")
    print(f"  version mark: {target / _fact('PRESET_MARKER')} ({version})")
    print(f"  skill-root  : {target / _fact('SKILL_ROOT_MARKER')}")
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
    if target.parent.name != _preset_dir_name() or target.name != _fact("PRESET_ID"):
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
    return Path.home() / _home_fallback_name()


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
        "write_surface": _home_fingerprint(home / _preset_dir_name())["entries"],
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


def _validate_composition_rows(composition_path: Path) -> dict:
    """Validate every enabled row against the INSTALLED dsh's own schemas.

    Thin delegation to ``skills/software-project-governance/infra/dsh_compat.py``
    — the single implementation of "parse with the loader's YAML dialect,
    interpolate ``!!js`` with the loader's ``evaluate``, run the installed
    cordis ``resolveConfig``". No schema is copied here, so this gate and
    `check-governance` Check 28v can never disagree about what a row means.

    Why it lives here: this function's caller (``--smoke``) is the repo's own
    "preset loading" verifier, yet it only resolved ``customSkillDirs`` and the
    ``/governance`` shim — it never parsed the composition into rows and never
    validated config, which is exactly why the ``text``-vs-``prefix`` defect
    (whole preset mount rejected) escaped it.

    Returns ``{"verdict", "reason", "issues", "rows_enabled", "install",
    "schema_checked"}``. An unreachable harness (no node / no discoverable dsh
    install) is ``NOT_RUN`` — never FAIL and never a silent PASS — so the smoke
    gate stays usable on a machine without dsh (FEAT-015 NOT_RUN policy).
    """
    fallback = {
        "verdict": "NOT_RUN",
        "reason": "row/config guard unavailable",
        "issues": [],
        "rows_enabled": 0,
        "install": None,
        "schema_checked": False,
    }
    try:
        if str(INFRA_DIR) not in sys.path:
            sys.path.insert(0, str(INFRA_DIR))
        import dsh_compat
    except Exception as exc:  # noqa: BLE001 — disclosure, never a crash
        fallback["reason"] = f"guard module unavailable: {type(exc).__name__}: {exc}"
        return fallback
    try:
        composition_path.resolve().relative_to(ROOT)
        probe_root = ROOT
    except (ValueError, OSError):
        probe_root = composition_path.parent
    try:
        report = dsh_compat.check_dsh_preset_compat(
            root=probe_root, compositions=[composition_path])
    except Exception as exc:  # noqa: BLE001 — disclosure, never a crash
        fallback["reason"] = f"guard raised: {type(exc).__name__}: {exc}"
        return fallback
    return {
        "verdict": report["verdict"],
        "reason": report["reason"],
        "issues": list(report["issues"]),
        "rows_enabled": report["rows_enabled"],
        "install": (report.get("install") or {}).get("node_modules"),
        "schema_checked": report["verdict"] != "NOT_RUN",
    }


def verify_preset_loading(preset_dir: Path, repo_root=None) -> dict:
    """Resolve a preset's skill roots + the ``/governance`` gesture (read-only).

    Pure verification over an installed or shipped preset directory. Returns
    ``{"verdict": "PASS"|"FAIL", "issues": [...], "skill_roots": [...],
    "skill_catalog", "gesture_shim", "gesture_target", "repo_root",
    "row_validation"}`` with POSIX-form paths (the report and assertions
    compare them literally). ``row_validation`` records the installed-schema
    row check (see :func:`_validate_composition_rows`); its findings are folded
    into ``issues`` only when it reaches FAIL.
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
        "row_validation": None,
    }
    composition_path = preset_dir / _composition_filename()
    if not composition_path.is_file():
        result["issues"].append(
            f"preset composition missing: {composition_path.as_posix()}")
        result["verdict"] = "FAIL"
        return result
    composition = composition_path.read_text(encoding="utf-8")
    result["row_validation"] = _validate_composition_rows(composition_path)
    if result["row_validation"]["verdict"] == "FAIL":
        result["issues"].extend(
            f"preset row/config rejected by the installed dsh schemas: {issue}"
            for issue in result["row_validation"]["issues"])
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
    row_validation = surface.get("row_validation") or {}
    print(f"[SMOKE]   row schemas    : "
          f"{row_validation.get('verdict', 'NOT_RUN')} "
          f"({row_validation.get('rows_enabled', 0)} enabled row(s) validated "
          f"against the installed dsh; {row_validation.get('reason', '-')})")
    print(f"[SMOKE]   verdict        : {surface['verdict']}")
    for issue in surface["issues"]:
        print(f"[SMOKE]   [FAIL] {issue}")


def smoke_preset() -> int:
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
    home_var = _fact("HOME_VAR")
    env_home = (os.environ.get(home_var) or "").strip()
    if not env_home:
        message = (
            f"[SMOKE] [REFUSED] {home_var} is not set — refusing to run the "
            f"smoke (M7.7: it must be redirected to a temporary directory; "
            f"the real home {home} is never a target)")
        print(message)
        print(message, file=sys.stderr)
        print(f"[SMOKE] Result: REFUSED (exit {SMOKE_EXIT_REFUSED})")
        return SMOKE_EXIT_REFUSED
    isolated = Path(env_home).expanduser()
    if _is_within(isolated, home) or _is_within(home, isolated):
        message = (
            f"[SMOKE] [REFUSED] {home_var} resolves to the real DSH home "
            f"({home}) — refusing to run (M7.7: never write the real home)")
        print(message)
        print(message, file=sys.stderr)
        print(f"[SMOKE] Result: REFUSED (exit {SMOKE_EXIT_REFUSED})")
        return SMOKE_EXIT_REFUSED

    print(f"[SMOKE] isolated {home_var}: {isolated}")
    print(f"[SMOKE] real DSH home    : {home}")
    before = _real_home_witness(home)
    print(f"[SMOKE] real home before : state={before['state']} "
          f"write_surface={len(before['write_surface'])} entry(ies), "
          f"top_level={len(before['top_level'])} (metadata only)")
    isolated.mkdir(parents=True, exist_ok=True)

    issues = []
    saved_home = os.environ.get(home_var)
    try:
        os.environ[home_var] = str(isolated)
        if install_preset() != 0:
            issues.append("preset installation failed in the isolated home")
    finally:
        if saved_home is None:
            os.environ.pop(home_var, None)
        else:
            os.environ[home_var] = saved_home

    # Second surface: the shipped payload rendered through the SAME code path,
    # into a scratch dir of the isolated home. This is the FIX-290 regression
    # surface — it proves the tokens substitute to absolute paths that really
    # resolve, not just that an installed copy happens to work.
    preset_id = _fact("PRESET_ID")
    payload_surface = isolated / ".preset-payload-check" / preset_id
    if not write_rendered_preset(payload_surface):
        issues.append(
            f"shipped payload failed to render: {_composition_template()}")

    surfaces = (
        (f"installed preset (rendered into the isolated {home_var})",
         isolated / _preset_dir_name() / preset_id),
        (f"shipped in-package payload (rendered from {_fact('PACKAGE_PRESET')}/"
         f"{_composition_filename()}.template)",
         payload_surface),
    )
    for label, directory in surfaces:
        surface = verify_preset_loading(directory)
        _print_surface_report(label, surface)
        issues.extend(f"{label}: {issue}" for issue in surface["issues"])

    after = _real_home_witness(home)
    unchanged = before == after
    print(f"[SMOKE] real-home writes : {0 if unchanged else 1} "
          f"({'witness unchanged — top level + preset write surface recursive' if unchanged else 'WITNESS CHANGED'})")
    if not unchanged:
        issues.append(
            f"real DSH home witness changed during the smoke: {home} — the "
            "isolation guarantee is broken (top-level entries and/or the "
            "preset write surface)")

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
    # Declared facts are read before the CLI is described, so the help text
    # names the same preset and home the code will use. A contract that cannot
    # be read is answered with an actionable error and a non-zero exit — it is
    # never papered over with built-in literals (design §2.5 C-2).
    try:
        preset_id = _fact("PRESET_ID")
        home_var = _fact("HOME_VAR")
        preset_location = f"${{{home_var}}}/{_preset_dir_name()}/{preset_id}"
    except Exception as exc:  # noqa: BLE001 — boundary: no stack may escape
        print(f"ERROR: the dsh host contract could not be read: {exc}",
              file=sys.stderr)
        print("ERROR: fix or restore the contract at "
              "adapters/dsh/host-contract.json, then re-run — the launcher "
              "carries no built-in fallback copy by design.", file=sys.stderr)
        return 1

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
        help=f"(re)write the {preset_id} preset into {preset_location}",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help=f"remove the {preset_id} preset (deletes exactly "
        f"{preset_location}; sibling presets untouched)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=f"print the resolved ${{{home_var}}} and planned writes without "
        "touching the filesystem (safe verification; DEC-158 R1)",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="isolated preset-session smoke gate (FEAT-015 / RISK-049 ②): "
        f"generate the preset under a redirected {home_var} and verify the "
        f"skill catalog + /{preset_id} gesture resolve (exit 0 PASS / 1 FAIL / "
        f"2 REFUSED — refuses an unredirected {home_var})",
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
        exit_code = smoke_preset() or exit_code
    if args.install:
        acted = True
        exit_code = install_preset(dry_run=args.dry_run) or exit_code
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
