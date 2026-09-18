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
the same purpose). Both renderers share the same declared token contract, so
they cannot disagree; ``adapters/dsh/agent.cordis.yml.template`` used to carry
that template and now lives inside the preset payload it renders.

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
from pathlib import Path
from typing import Optional

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
# `_fact()`), so importing this module never depends on the file being present
# and no inlined fallback copy is needed to keep the import working.
#
# Render contract, shared verbatim with `lib/index.js`: token → package-relative
# path, `""` meaning the package root itself. Both renderers read the same
# `own.render.tokens` map, so `dsh plugin add` and `--install` cannot write
# different presets for the same package version.
#
# These three are **traceability anchors, not runtime values** (F-14): nothing
# in this module reads them to decide anything — the render map's keys come from
# `own.render.tokens`, and the repo-root token is found by its declared *target*
# (`_substitute_repo_root`). Their job is to keep the three declared token
# spellings greppable next to the code that uses them, which is what the
# K-2 outside-contract scan and `test_dsh_contract.py` judge. Do not delete them
# as "unused"; do not start reading them either.
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
    "NEWLINE_POLICY": "own.render.newline_policy",
    "CUSTOM_SKILL_DIRS_SHAPE": "own.render.custom_skill_dirs_shape",
}

#: (label, contract token) for the render map's two skill roots — the two
#: ``customSkillDirs`` the preset declares. The token spellings above are the
#: traceability anchors ``test_dsh_contract.py`` compares against
#: ``own.render.tokens``; every runtime lookup goes through the contract-derived
#: map, so a renamed token cannot leave a stale spelling in force.
REPORTED_TOKEN_BINDINGS = (
    ("skill roots", SKILLS_TOKEN),
    ("shim roots", SHIMS_TOKEN),
)

#: Memoized contract document; `None` until the first declared fact is read.
_CONTRACT: Optional[dict] = None


class CompositionUnreadable(Exception):
    """A file the caller consumes as content is not decodable UTF-8.

    The text-mode reader cannot produce text for such a file, so the failure is
    surfaced as this structured error instead of a bare ``UnicodeDecodeError``:
    every entry point then answers with an actionable message (file name +
    offset + offending byte), a stable exit code and no traceback (G-10).

    ``errors="replace"`` is deliberately NOT used for these files: the decoded
    text *is* the product here (it is rendered into the user's preset and
    parsed for verification), so replacement characters would silently write
    mojibake into a preset — a worse outcome than a refused render.

    Attributes:
        path: the file that could not be read.
        offset: byte offset of the first undecodable byte.
        byte: the offending byte value, or ``None`` when unavailable.
        reason: the codec's own message, for the diagnostic.
    """

    def __init__(self, path, offset=None, byte=None, reason=""):
        self.path = Path(path)
        self.offset = offset
        self.byte = byte
        self.reason = reason
        super().__init__(self.diagnostic())

    def diagnostic(self) -> str:
        """One actionable line: what failed, where, and how to fix it."""
        parts = [f"{self.path} is not valid UTF-8"]
        if self.offset is not None:
            parts.append(f"at byte offset {self.offset}")
        if self.byte is not None:
            parts.append(f"(0x{self.byte:02x})")
        if self.reason:
            parts.append(f"— {self.reason}")
        return " ".join(parts) + "; fix the file's encoding (it is consumed as text)"


class PackageIdentityUnreadable(Exception):
    """This package's own ``package.json`` cannot be read or decoded.

    Distinct from "the version field is absent" on purpose (F-2). The install
    path stamps ``package.json``'s version into ``.dsh-bundle-version``, the
    idempotence key ``lib/index.js`` compares on every boot. Writing the
    placeholder ``"0"`` there would make that key permanently unequal to
    ``packageVersion()``'s real answer, so **every** boot would rebuild the
    preset — the opposite of the declared idempotence. An unreadable identity
    file is therefore a refused install with an actionable message, not a
    silently degraded one.
    """

    def __init__(self, path, cause):
        self.path = Path(path)
        self.cause = cause
        if isinstance(cause, CompositionUnreadable):
            detail = cause.diagnostic()
        else:
            detail = f"{type(cause).__name__}: {cause}"
        super().__init__(
            f"package identity unreadable ({detail}); the preset's idempotence "
            f"marker cannot be stamped from it")


def _read_text(path: Path) -> str:
    """Read ``path`` as UTF-8 text, or raise :class:`CompositionUnreadable`.

    The three entry points that consume a file as content (render, preset
    verification, bootstrap) all read through here, so their failure semantics
    are identical and machine-checkable rather than three different answers to
    the same condition (the same-file inconsistency G-10 found: two call sites
    raised a bare ``UnicodeDecodeError`` while two others silently replaced).
    """
    path = Path(path)
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise CompositionUnreadable(
            path,
            offset=exc.start,
            byte=exc.object[exc.start] if exc.object else None,
            reason=exc.reason,
        ) from exc


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


def _reported_token_bindings() -> list:
    """(label, resolved path) for the two declared ``customSkillDirs`` roots."""
    targets = _token_paths()
    return [(label, targets[token]) for label, token in REPORTED_TOKEN_BINDINGS]


def leftovers(composition: str) -> list:
    """Unresolved ``__…__`` tokens in a rendered composition, deduplicated.

    The scan expression is the declared ``own.render.leftover_scan`` pattern —
    never a fixed list of "known" tokens. A token this renderer does not
    substitute (a misspelling such as ``__GOVERNANCE_SKILLS_ROOTS__``, or the
    mixed-case ``__Governance_Repo_Root__`` a ``[A-Z0-9_]+`` list cannot see)
    is therefore reported here, not silently written into the preset. Returns
    the matched strings in first-appearance order.
    """
    pattern = _fact("LEFTOVER_SCAN")
    if not pattern:
        # An empty scan would report every render as clean — fail closed with
        # the same exception class the contract loader uses for a malformed
        # declaration (the contract is malformed, not the input file).
        raise _contract_error(
            "own.render.leftover_scan", "an empty scan cannot report leftovers")
    return list(dict.fromkeys(re.findall(pattern, composition)))


def _contract_error(declared: str, detail: str) -> Exception:
    """``ContractMalformed`` for one undeclared/unusable contract field."""
    if str(INFRA_DIR) not in sys.path:
        sys.path.insert(0, str(INFRA_DIR))
    import dsh_contract  # noqa: PLC0415 — deliberate: lazy, as in `_fact`
    return dsh_contract.ContractMalformed(
        f"ContractMalformed: `{declared}` {detail} in contract "
        f"{dsh_contract.contract_path()}")


def _env_value(env, key: str) -> str:
    """One environment value as stripped text; ``""`` for unset or blank."""
    value = env.get(key)
    return "" if value is None else str(value).strip()


def _home_from_env(raw: str) -> Path:
    """Resolve one already-decided ``$DSH_HOME`` value to a path.

    Tilde expansion is applied here (``~`` / ``~/`` / ``~\\`` — the three forms
    ``host.env.write_side.tilde_expansion`` declares). Everything else is taken
    verbatim and handed to the platform's path parser, which is what
    ``trim_policy = "verbatim-then-platform-resolve"`` means: the value decides
    *what* is resolved, the platform decides how. A relative value therefore
    resolves against the process CWD — exactly as ``lib/index.js``
    ``resolveDshHome()`` does; leaving it relative here was the one case where
    the two writers disagreed (measured: ``fix316h/x`` → ``fix316h/x`` vs
    ``<cwd>/fix316h/x``).
    """
    if raw == "~":
        return Path.home().resolve()
    if raw[:2] in ("~/", "~\\"):
        return (Path.home() / raw[2:]).resolve()
    return Path(raw).resolve()


def _home_fallback() -> Path:
    return (Path.home() / _home_fallback_name()).resolve()


def dsh_home() -> Path:
    """Resolve the harness home — the write-side rule of ``host.env.write_side``.

    One case rule, shared with ``lib/index.js`` ``resolveDshHome()``:

    * unset, ``""`` **or whitespace-only** ⇒ the declared fallback
      ``<home>/.dsh`` (``blank_policy = "trimmed-empty-means-unset"``);
    * otherwise the trimmed value, then the platform's path parser
      (``trim_policy = "verbatim-then-platform-resolve"``), with the three
      declared tilde forms expanded.

    The previous ``if env:`` test treated ``"   "`` as a real path and produced
    the literal ``"   \\.agent-presets\\governance"`` (G-06), which is why the
    blank decision is made on the *trimmed* value here. This is the write side
    only: the read/probe side (``dsh_compat.py``) deliberately keeps its
    fail-closed "explicit ``$DSH_HOME`` or nothing" rule and must not be
    converged onto this fallback (design §4.4.4 G06-b').
    """
    raw = _env_value(os.environ, _fact("HOME_VAR"))
    if not raw:
        return _home_fallback()
    return _home_from_env(raw)


def preset_dir() -> Path:
    return dsh_home() / _preset_dir_name() / _fact("PRESET_ID")


def package_version() -> str:
    """This package's version, or raise :class:`PackageIdentityUnreadable`.

    **Strict by design (N-8).** The value is stamped into the preset's
    idempotence marker, where "unknown" is not an acceptable answer: the
    placeholder ``"0"`` can never equal `lib/index.js`'s `packageVersion()`, so
    a marker holding it makes **every** boot rebuild the preset — the opposite
    of the declared idempotence.

    There is deliberately no lenient spelling of *this* read to reach for: a
    second, degrade-quietly variant is how the strict check gets bypassed by the
    next caller (the previous shape had exactly that pair, with the strict one
    guarding only one of two call sites). The genuine "no identity at all" case
    is handled once, in :func:`marker_version`, rather than by a second reader.
    """
    try:
        payload = json.loads(_read_text(ROOT / "package.json"))
    except (OSError, CompositionUnreadable, json.JSONDecodeError) as exc:
        raise PackageIdentityUnreadable(ROOT / "package.json", exc) from exc
    version = payload.get("version")
    if not isinstance(version, str) or not version:
        raise PackageIdentityUnreadable(
            ROOT / "package.json",
            ValueError("the `version` field is absent or empty"))
    return version


def marker_version() -> str:
    """The value to stamp into ``.dsh-bundle-version``.

    Strict whenever this package's ``package.json`` **exists** (N-8): a
    present-but-unreadable identity is a defect, and the ``"0"`` placeholder
    would make the marker permanently unequal to `lib/index.js`'s
    `packageVersion()`, so every boot would rebuild the preset.

    The one permitted placeholder case is the file being **absent entirely** —
    a repository copy shipped without it (the mutation-test copies keep only
    `lib/`, `adapters/` and `agent-presets/`). There, ``"0"`` matches the
    pre-existing behaviour and nothing could have supplied a real version.
    """
    if not (ROOT / "package.json").is_file():
        return "0"
    return package_version()


def render_composition() -> str:
    """Render the composition template with absolute paths.

    Returns ``""`` when the template is missing, cannot be decoded as UTF-8, or
    leaves a ``__…__`` token behind — the caller reports it instead of
    installing a composition whose skill roots would silently resolve against
    the dsh process CWD. The scan is the declared ``own.render.leftover_scan``
    pattern, so a token this renderer does not know (a misspelling) is refused
    too, not just the tokens it does know.

    Line endings are LF by construction and by *explicit* normalization:
    ``newline=""`` disables the text layer's universal-newline translation, so
    ``"\\r\\n"`` is then folded to ``"\\n"`` here and an isolated ``"\\r"`` is
    left alone — which is exactly what ``lib/index.js`` does
    (``replace(/\\r\\n/g, '\\n')``). Relying on the text layer instead made the
    two renderers disagree by every isolated CR in the template (D-66), and the
    declared ``own.render.newline_policy`` is ``"lf"`` for both of them.
    """
    try:
        template = _read_text_with_newline_mode(_composition_template())
    except CompositionUnreadable as exc:
        print(f"ERROR: {exc.diagnostic()}", file=sys.stderr)
        return ""
    except OSError:
        return ""
    composition = template.replace("\r\n", "\n")
    tokens = _token_paths()
    for token, path in tokens.items():
        value = str(path.resolve()).replace("\\", "/")
        composition = composition.replace(token, value)
    if leftovers(composition):
        return ""
    return composition


def _read_text_with_newline_mode(path: Path) -> str:
    """:func:`_read_text` with universal-newline translation disabled.

    Only the render source needs this: it is the file whose line endings are
    *compared* between the two renderers, so the reading mode is part of the
    contract rather than an accident of the platform's text layer.
    """
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except UnicodeDecodeError as exc:
        raise CompositionUnreadable(
            path,
            offset=exc.start,
            byte=exc.object[exc.start] if exc.object else None,
            reason=exc.reason,
        ) from exc


def require_lf_newline_policy() -> str:
    """The declared newline policy, asserted to be the one this code implements.

    ``own.render.newline_policy`` is a *load-bearing* declaration: every write
    in :func:`write_rendered_preset` normalizes to LF, and the JS row does the
    same. Reading it here — and refusing to write a preset under any other
    policy — is what makes a contract change to ``"crlf"`` visible instead of
    silently ignored (F-7: the binding used to exist with no reader at all, so
    the declaration carried no weight).

    Returns the policy string; raises :class:`PackageIdentityUnreadable`-style
    :class:`ContractMalformed` (via ``_contract_error``) when it is not ``"lf"``.
    """
    policy = _fact("NEWLINE_POLICY")
    if policy != "lf":
        raise _contract_error(
            "own.render.newline_policy",
            f"is {policy!r} but this launcher only normalizes to 'lf'")
    return policy



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


def write_rendered_preset(destination: Path, version: Optional[str] = None) -> bool:
    """Render the payload into ``destination`` (no atomicity — the caller owns it).

    Returns ``False`` (leaving no partial directory behind) when the template
    cannot be rendered, its metadata cannot be read, or this package's version
    cannot be established.

    **Never raises for an unreadable input, and never leaves a partial tree**
    (F-4): the metadata read happens *before* ``destination`` is created, and
    any failure after that point removes what this call created. The
    ``False`` return is therefore the only failure signal the caller needs —
    the previous shape raised ``CompositionUnreadable`` from *inside* the
    already-created staging directory, which made the caller's
    ``if not write_rendered_preset(...)`` cleanup branch unreachable and left
    ``governance.staging-<pid>-…`` behind forever (each retry picks a fresh
    name, so nothing ever reclaimed it).

    ``version`` is the value stamped into the idempotence marker. Callers that
    already hold it (``install_preset`` reads it **strictly**, before any
    staging directory exists) pass it in. When omitted, this resolves it with
    :func:`marker_version` — strict whenever ``package.json`` exists, and the
    ``"0"`` placeholder only when it is absent (N-8).

    **Callers MUST gate on** :func:`write_side_refusal` first: this function
    writes wherever it is pointed, including a real DSH home.
    """
    composition = render_composition()
    if not composition or not _preset_metadata().is_file():
        return False
    try:
        metadata = _read_text(_preset_metadata())
    except (OSError, CompositionUnreadable) as exc:
        print(f"ERROR: preset metadata unreadable: {exc}", file=sys.stderr)
        return False
    if version is None:
        try:
            version = marker_version()
        except PackageIdentityUnreadable as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return False
    try:
        destination.mkdir(parents=True, exist_ok=True)
        # Every file is written as explicit BYTES with LF terminators. The
        # declared `own.render.newline_policy` is "lf", and text mode does not
        # honour it on every platform: `write_text("\n", newline="\n")` still
        # produced CRLF for the marker files on Windows, so a preset could
        # carry four files with two different line-ending conventions
        # depending on where it was written (measured: 379 B LF payload vs
        # 381 B CRLF). Bytes make it a property of this function instead of
        # the platform.
        (destination / _composition_filename()).write_bytes(
            composition.replace("\r\n", "\n").encode("utf-8"))
        # The metadata is copied as *text* through the same LF normalization
        # rather than as raw bytes (`shutil.copyfile`), which would make its
        # line endings depend on the checkout (`git archive`/`core.autocrlf`)
        # rather than on the declared policy.
        (destination / "preset.yml").write_bytes(
            metadata.replace("\r\n", "\n").encode("utf-8"))
        (destination / _fact("PRESET_MARKER")).write_bytes(
            (version + "\n").encode("utf-8"))
        # Hook discovery marker: the repo hooks' find_spg_home reads this file
        # to resolve the workflow home under dsh, so installed project hooks
        # keep self-upgrading after `git pull` + `--sync`.
        (destination / _fact("SKILL_ROOT_MARKER")).write_bytes(
            (str(ROOT.resolve()).replace("\\", "/") + "\n").encode("utf-8"))
    except OSError as exc:
        print(f"ERROR: writing the preset failed: {exc}", file=sys.stderr)
        shutil.rmtree(destination, ignore_errors=True)
        return False
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

    # The symmetric half of `smoke_preset()`'s guard: a real install must be
    # redirected just as a smoke run must be. Without this, a mis-set (or
    # forgotten) DSH_HOME silently rewrites the user's real preset — which is
    # what happened once during this very task, hence the guard is stated here
    # and reused by both paths rather than left to the caller's discipline.
    refusal = write_side_refusal(target, operation="install into the real preset root")
    if refusal is not None:
        return _refuse_write(refusal)

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
    # Read (and decode) the metadata BEFORE anything is created: this is the
    # read point that used to raise inside the staging directory, leaving it
    # behind for good (F-4). The diagnostic names the file, the failing byte
    # and its offset, so the operator can fix the encoding (G10-b/F-2).
    try:
        _read_text(_preset_metadata())
    except CompositionUnreadable as exc:
        print(f"ERROR: {exc.diagnostic()}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: preset metadata unreadable: {exc}", file=sys.stderr)
        return 1
    try:
        require_lf_newline_policy()
    except Exception as exc:  # noqa: BLE001 — boundary: actionable, no stack
        print(f"ERROR: cannot write a preset: {exc}", file=sys.stderr)
        return 1
    try:
        version = package_version()
    except PackageIdentityUnreadable as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_name(
        f"{target.name}.staging-{os.getpid()}-{int(time.time() * 1000)}"
    )
    shutil.rmtree(staging, ignore_errors=True)
    try:
        written = write_rendered_preset(staging, version)
    except Exception as exc:  # noqa: BLE001 — boundary: clean up, then report
        written = False
        print(f"ERROR: writing the preset failed: {type(exc).__name__}: {exc}",
              file=sys.stderr)
    if not written:
        # Belt and braces (F-4): whatever failed, the staging tree this call
        # created is removed before returning, so a failed install can never
        # leave `governance.staging-<pid>-…` in the user's DSH home.
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
    for label, path in _reported_token_bindings():
        print(f"  {label:<12s}: {path}")
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

    ``dry_run`` is the read-only preview: it reports the resolved target and
    the entries it would delete, and **touches nothing** — no directory, no
    staging tree, no removal. It is reached **before** the write-side guard,
    which is the same order :func:`install_preset` uses: a preview that writes
    nothing is not a mutation of the real preset root, so refusing it would
    break the documented "inspect before you delete" path (R0 F-1/R2 microfix:
    the guard used to sit first, so `--dry-run` was refused while `--install
    --dry-run` was allowed).

    The guard still gates the **real** removal, unchanged: an unset or
    real-home `$DSH_HOME` is refused with exit 2 before anything is deleted.
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
    if dry_run:
        exists = target.is_dir()
        entries = sorted(p.name for p in target.iterdir()) if exists else []
        print(f"[DRY-RUN] dsh home      : {dsh_home()}")
        print(f"[DRY-RUN] preset dir    : {target}")
        if exists:
            print(
                f"[DRY-RUN] planned delete: {target} "
                f"({len(entries)} entr{'y' if len(entries) == 1 else 'ies'}: "
                f"{', '.join(entries)})"
            )
        else:
            print("[DRY-RUN] planned delete: nothing — preset not installed")
        print("[DRY-RUN] nothing deleted — re-run without --dry-run to uninstall")
        return 0
    # Same write-side rule as install: a removal is a mutation of the real
    # preset root and must be as deliberate as a write (an unset DSH_HOME means
    # "the real ~/.dsh", which is the last place a refusal-free delete belongs).
    # Reached only on the real (non-dry-run) path, so the preview above stays
    # available for a real home while the deletion itself does not.
    refusal = write_side_refusal(target, operation="remove the real preset")
    if refusal is not None:
        return _refuse_write(refusal)
    if not target.exists():
        print(f"not installed: {target} (nothing to do)")
        return 0
    entries = sorted(p.name for p in target.iterdir())
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


def write_side_refusal(target: Path, *, operation: str):
    """Why a *write* operation must refuse, or ``None`` when it may proceed.

    The install/sync and uninstall paths mutate a user's real preset root, so
    they are guarded by the same rule the smoke gate applies — expressed once,
    in one place, so the two cannot drift apart:

      * ``$DSH_HOME`` must be **explicitly set** (an unset variable silently
        means "the real ``~/.dsh``", which is exactly the accidental target the
        guard exists to prevent); and
      * it must not be, contain, or sit inside the real DSH home.

    ``target`` is the path the caller would actually touch, reported in the
    message so the refusal names the consequence, not just the variable.
    A temporary directory *anywhere else* — including under the user profile's
    ``AppData\\Local\\Temp`` — is allowed: this guard protects the DSH home, not
    "everything under $HOME" (the latter would refuse the isolated runs the
    rest of this repository depends on).

    Returns a one-line reason string, or ``None`` when the operation is safe.
    The message distinguishes the three refusal shapes, because they need
    different fixes: **unset** (nothing to clear, set the variable), **set but
    blank** (a value that resolves to "unset" by policy — F-13), and **profile
    unresolvable** (N-1).
    """
    home_var = _fact("HOME_VAR")
    raw = os.environ.get(home_var)
    if raw is None:
        return (f"{home_var} is not set — refusing to {operation} (an unset "
                f"variable means the real DSH home; set {home_var} to a "
                f"temporary directory to run this deliberately)")
    if not raw.strip():
        return (f"{home_var} is set but blank ({raw!r}) — refusing to "
                f"{operation} (a blank value means the real DSH home by the "
                f"declared `trimmed-empty-means-unset` policy; set {home_var} "
                f"to a temporary directory to run this deliberately)")
    # N-1: the guard's whole job is to decide whether `raw` could be the real
    # DSH home, and that decision needs `Path.home()`. When the OS profile is
    # unreadable (`USERPROFILE`/`HOME`/`HOMEDRIVE`/`HOMEPATH` all unset or
    # unparsable) `Path.home()` raises — which used to escape `main()` as a
    # traceback. A guard must never be the thing that crashes, so an
    # unresolvable profile is a **fail-closed refusal**: without a home to
    # compare against, this function cannot prove the target is safe, and
    # "cannot prove" is exactly what a safety check turns into a refusal.
    # (`lib/index.js:408-415` treats the same condition as a real failure mode
    # — node's `uv_os_homedir` ENOENT — so it is not a hypothetical.)
    try:
        real_home = real_dsh_home()
    except (RuntimeError, OSError) as exc:  # RuntimeError: node-style ENOENT
        return (f"{home_var} is set ({raw!r}) but the user profile cannot be "
                f"resolved ({type(exc).__name__}: {exc}) — refusing to "
                f"{operation}: without a resolvable home this guard cannot "
                f"prove the target is not the real DSH home. Set USERPROFILE "
                f"/ HOME (or run under a profile this process can read) and "
                f"re-run.")
    isolated = Path(raw).expanduser()
    if _is_within(isolated, real_home) or _is_within(real_home, isolated):
        return (f"{home_var} resolves to (or contains) the real DSH home "
                f"{real_home} — refusing to {operation}; the target would be "
                f"{target}")
    return None

def _refuse_write(reason: str) -> int:
    """Print a refusal on both streams and return the REFUSED exit code."""
    for stream in (sys.stdout, sys.stderr):
        print(f"[REFUSED] {reason}", file=stream)
    print(f"Result: REFUSED (exit {SMOKE_EXIT_REFUSED})")
    return SMOKE_EXIT_REFUSED


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
    2. ``top_level`` — the **names** of ``<home>``'s top-level entries, and
       nothing else. Size and mtime used to be compared too, which made the
       gate fire on host activity that has nothing to do with this adapter
       (D-54: the host rewrites ``settings.yaml`` for its own reasons, and
       "settings.yaml changed" is not evidence that *we* wrote anything). A
       name appearing or disappearing is still compared, because that is the
       one top-level change a preset write could plausibly cause.

    A whole-home comparison is deliberately NOT used: measured 2026-09-09,
    two full-home reads 3 s apart differ (a live session appends
    ``dsh-agent-router/stats/*``) while ``.agent-presets`` stays identical.
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
            kind = "d" if (stat.st_mode & 0o170000) == 0o040000 else "f"
            top_level.append(f"{kind}:{path.name}")
    return {
        "state": "present" if home.exists() else "absent",
        "write_surface": _home_fingerprint(home / _preset_dir_name())["entries"],
        "top_level": top_level,
    }


def witness_deltas(before: dict, after: dict) -> dict:
    """Compare two witness samples → ``{"write_surface", "top_level"}`` deltas.

    The comparison式 is the one design §3.3 (row 11, D-54) fixes, and the two
    components are deliberately **not** symmetric:

    * ``write_surface`` — the adapter's ONLY write face, so a difference is a
      finding on the first comparison; no race is tolerated there.
    * ``top_level`` — only the **name set** is compared. A size/mtime change is
      not even visible here any more (the witness no longer records them), so
      host activity on ``settings.yaml`` cannot produce a delta at all.
    """
    return {
        "write_surface": [entry for entry in before["write_surface"]
                          if entry not in after["write_surface"]]
                         + [entry for entry in after["write_surface"]
                            if entry not in before["write_surface"]],
        "top_level": [name for name in before["top_level"]
                      if name not in after["top_level"]]
                     + [name for name in after["top_level"]
                        if name not in before["top_level"]],
    }


def witness_verdict(samples, *, resample=None) -> dict:
    """D-54 comparison: ``{"failures", "advisories", "verdict"}``.

    ``samples`` is ``(before, after_first)``. Design §3.3's sampling definition:
    a *suspected* top-level change (one seen in the first post-sample but not
    reproducing on a second) is a host race → **advisory, not FAIL**; the write
    surface has no such tolerance.

    ``resample`` — when given, it is called at most once to take the second
    post-sample **only if** a top-level delta was suspected (the sampling
    moment is "immediately after the first post-sample, interval 0"); the delta
    then has to reproduce for the gate to fail. **Without a resampler a
    top-level delta is a failure**: the caller is asserting a single sample, so
    there is nothing that could downgrade it to a race.

    Reproduced-ness is judged **against the baseline**, not against the first
    post-sample (N-5). Design §3.3 fixes both outcomes — "seen once = advisory,
    reproduced = FAIL" — and only the baseline comparison yields both: comparing
    the two post-samples would invert each (a persistent write would look like
    a one-shot race, and a one-shot race would look like a persistent write).
    The trade-off is deliberately the fail-closed side: a *different* top-level
    change present at the resample (not the same entry) still counts as
    reproduced, because "some top-level change survives a resample" is the
    signal this gate acts on. Marked here rather than left to be inferred.
    """
    before, after_first = samples
    deltas = witness_deltas(before, after_first)
    failures = []
    advisories = []
    if deltas["write_surface"]:
        # The adapter's own write face: never a race, always a real write.
        failures.append(
            "real DSH home preset write surface changed: "
            + ", ".join(deltas["write_surface"]))
    if deltas["top_level"]:
        reproduced = True
        if resample is not None:
            # "复现同样变化" = a top-level change is still present relative to the
            # BASELINE (not relative to the first post-sample): a real write
            # persists, a host race is gone by the second sample. See the
            # fail-closed note above (N-5).
            after_second = resample()
            reproduced = bool(witness_deltas(before, after_second)["top_level"])
        if reproduced:
            failures.append(
                "real DSH home top level changed: "
                + ", ".join(deltas["top_level"]))
        else:
            advisories.append(
                "real DSH home top level changed once and did not reproduce "
                "on resample (host activity, not an adapter write): "
                + ", ".join(deltas["top_level"]))
    return {
        "failures": failures,
        "advisories": advisories,
        "verdict": "FAIL" if failures else "PASS",
    }


def _custom_skill_dir_entries(composition: str) -> list:
    """Raw ``customSkillDirs`` entries of a composition text, in order.

    The block's end is decided by indentation, and the rule is ``<`` the key's
    indent — **not** ``<=``: a YAML block sequence may sit at the *same*
    indentation as its key, so an ``<=`` early break made the scanner miss a
    legal block sequence entirely (G-05: ``customSkillDirs:`` followed by
    same-indent ``- /one`` / ``- /two`` matched 0 entries, which then surfaced
    as the misleading "preset declares no customSkillDirs" report).

    A sequence item must also be *a* sequence item: a sibling key at the key's
    own indent ends the block instead of being mistaken for an entry.
    """
    entries = []
    key_indent = None
    item_indent = None
    for line in composition.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if key_indent is None:
            if stripped.startswith("customSkillDirs:"):
                key_indent = indent
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if indent < key_indent:
            break
        match = re.match(r"^-\s+(.*)$", stripped)
        if not match:
            # A non-item line at (or left of) the key's indent is a sibling
            # key: the block is over. Deeper non-item lines are skipped.
            if indent <= key_indent:
                break
            continue
        if item_indent is None:
            item_indent = indent
        elif indent != item_indent:
            break
        entries.append(match.group(1).strip())
    return entries


def declared_custom_skill_dirs_shape() -> dict:
    """The declared ``own.render.custom_skill_dirs_shape`` block."""
    return _fact("CUSTOM_SKILL_DIRS_SHAPE")


def _shape_violations(composition: str, stage: str = "rendered") -> list:
    """Where a composition text departs from the declared block shape.

    ``own.render.custom_skill_dirs_shape`` declares the indentation, list style,
    entry count and entry form of the ``customSkillDirs`` block (``key_indent``
    / ``item_indent`` / ``list_style`` / ``entry_count`` / ``entry_form`` /
    ``renders_to``). Asserting it keeps that declaration load-bearing while the
    scanner above stays tolerant of every legal YAML spelling: the *shipped*
    payload is held to the one declared form.

    ``stage`` selects the form the entries must match, because the declaration
    describes two ends of one substitution:

      * ``"template"`` — the render source, whose entries are declared tokens
        (``entry_form``);
      * ``"rendered"`` — the mounted composition, whose entries are either the
        substituted absolute paths (``renders_to``) or the loader's own
        ``!!js new URL(<rel>, baseUrl)`` self-location — the *other* form
        :func:`_resolve_skill_entry` accepts. Both are legitimate; a
        composition using the loader form must not be reported as a
        "relative path" violation while the resolver calls it valid (F-6: the
        two judgments about one line contradicted each other).

    A drift is reported instead of silently verifying a shape nobody declared.

    ``list_style`` is handled differently from the four dimensions above, and
    deliberately (N-3): only ``block-sequence`` is implemented here, so a
    declaration of anything else is a **contract defect**, not a violation of
    the document under inspection. Emitting it as a per-document violation made
    the branch look like a document judgment while being provably unreachable
    for a valid contract — an unremovable, untestable branch. It is asserted at
    entry instead, so a contract that declares an unimplemented style fails
    loudly with the contract named.
    """
    shape = declared_custom_skill_dirs_shape()
    if shape["list_style"] != "block-sequence":
        raise _contract_error(
            "own.render.custom_skill_dirs_shape.list_style",
            f"declares {shape['list_style']!r}, which this scanner does not "
            f"implement (only 'block-sequence')")
    violations = []
    key_indent = None
    item_indents = []
    item_forms = []
    for line in composition.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if key_indent is None:
            if stripped.startswith("customSkillDirs:"):
                key_indent = indent
                if indent != shape["key_indent"]:
                    violations.append(
                        f"customSkillDirs key is indented {indent}, declared "
                        f"{shape['key_indent']}")
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if indent < key_indent:
            break
        match = re.match(r"^-\s+(.*)$", stripped)
        if not match:
            if indent <= key_indent:
                break
            continue
        entry = match.group(1).strip().strip("'\"")
        item_indents.append(indent)
        if not entry:
            item_forms.append("empty")
        elif re.fullmatch(r"__[A-Za-z0-9_]+__", entry):
            item_forms.append("token")
        elif entry.startswith("!!js"):
            # The loader's own self-location form, accepted by
            # `_resolve_skill_entry`; judge it the same way here (F-6).
            item_forms.append("baseUrl")
        elif Path(entry).expanduser().is_absolute():
            item_forms.append(shape["renders_to"])
        else:
            item_forms.append("relative")
    if key_indent is None:
        violations.append("customSkillDirs key is absent")
        return violations
    expected_count = shape["entry_count"]
    if len(item_indents) != expected_count:
        violations.append(
            f"customSkillDirs declares {len(item_indents)} "
            f"{'entry' if len(item_indents) == 1 else 'entries'}, "
            f"declared {expected_count}")
    for index, indent in enumerate(item_indents):
        if indent != shape["item_indent"]:
            violations.append(
                f"customSkillDirs item {index + 1} is indented {indent}, "
                f"declared {shape['item_indent']}")
    if stage == "template":
        allowed_forms = tuple(shape["entry_form"])
    else:
        allowed_forms = (shape["renders_to"], "baseUrl")
    for index, form in enumerate(item_forms):
        if form not in allowed_forms:
            violations.append(
                f"customSkillDirs item {index + 1} has form {form!r}, declared "
                f"{list(allowed_forms)} for the {stage} stage")
    return violations


def _resolve_skill_entry(entry: str, preset_dir: Path):
    """Resolve one ``customSkillDirs`` entry → ``(form, path, issue)``.

    Two entry forms are resolved: an absolute path (what both renderers
    substitute into the shipped template) and the loader's own
    ``!!js new URL(<rel>, baseUrl)`` self-location, evaluated with the URL math
    dsh applies against the composition file's directory. A literal relative
    entry is reported as an issue — it resolves against the dsh process CWD and
    silently empties the session catalog (FIX-290).

    The relocated form used to be detected by URL-math helpers
    (``urljoin`` / ``urlparse`` / ``url2pathname``) that the shipped payload no
    longer needs: the loader's ``baseUrl`` is the composition file's own
    ``file://`` directory, so joining a *relative* reference against it is
    exactly ``preset_dir / <rel>``. Those helpers were the module's only
    ``urllib`` consumers, so the imports that existed solely for them are gone
    (D-50 / D-56: dead code removed rather than kept alive by its own tests).
    """
    raw = entry.strip()
    if raw.startswith("!!js"):
        body = raw[len("!!js"):].strip().strip('"').strip("'")
        match = re.search(r"new URL\(\s*'([^']+)'\s*,\s*baseUrl\s*\)", body)
        if not match:
            return "baseUrl", None, (
                f"customSkillDirs entry is a !!js expression that does not "
                f"resolve against baseUrl: {raw}")
        return "baseUrl", preset_dir.resolve() / match.group(1), None
    raw = raw.strip("'\"")
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        return "relative", candidate, (
            f"customSkillDirs entry is a literal relative path ({raw!r}) — it "
            "resolves against the dsh process CWD (FIX-290) and silently "
            "empties the session catalog")
    return "absolute", candidate, None


def _repo_root_for_preset(preset_dir: Path, catalog_root, issues=None):
    """Repo root of a preset: the skill-root marker, else the catalog parent.

    A marker that cannot be decoded falls through to the catalog parent — but
    it is **disclosed** into ``issues`` rather than silently treated as absent
    (N-6b: a silent downgrade hides a real file defect and contradicts this
    repository's "disclose, never silently degrade" policy). This is called
    from ``verify_preset_loading()``, whose contract is "return a structured
    verdict, never throw"; ``issues=None`` keeps the helper usable outside that
    report.
    """
    marker = preset_dir / _fact("SKILL_ROOT_MARKER")
    if marker.is_file():
        try:
            text = _read_text(marker).strip()
        except CompositionUnreadable as exc:
            if issues is not None:
                issues.append(
                    f"{_fact('SKILL_ROOT_MARKER')} is unreadable ({exc.diagnostic()}) "
                    "— falling back to the skill catalog parent for the repo root")
            text = ""
        except OSError as exc:
            if issues is not None:
                issues.append(
                    f"{_fact('SKILL_ROOT_MARKER')} could not be read ({exc}) "
                    "— falling back to the skill catalog parent for the repo root")
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

    Returns ``{"verdict", "reason", "issues", "rows_enabled", "rows_checked",
    "coverage", "install", "schema_checked"}``. An unreachable harness (no node
    / no discoverable dsh install) is ``NOT_RUN`` — never FAIL and never a
    silent PASS — so the smoke gate stays usable on a machine without dsh
    (FEAT-015 NOT_RUN policy). ``rows_checked`` / ``coverage`` are carried
    through from the guard unchanged, so the smoke gate reports the face that
    was actually *verified* rather than an enabled-row count (G-12).
    """
    fallback = {
        "verdict": "NOT_RUN",
        "reason": "row/config guard unavailable",
        "issues": [],
        "rows_enabled": 0,
        "rows_checked": 0,
        "coverage": {},
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
        "rows_checked": report.get("rows_checked", 0),
        "coverage": dict(report.get("coverage") or {}),
        "install": (report.get("install") or {}).get("node_modules"),
        "schema_checked": report["verdict"] != "NOT_RUN",
    }


def verify_preset_loading(preset_dir: Path, repo_root=None) -> dict:
    """Resolve a preset's skill roots + the ``/governance`` gesture (read-only).

    Pure verification over an installed or shipped preset directory. Returns
    ``{"verdict": "PASS"|"FAIL", "issues": [...], "skill_roots": [...],
    "skill_catalog", "gesture_shim", "gesture_target", "repo_root",
    "row_validation", "custom_skill_dirs_shape"}`` with POSIX-form paths (the
    report and assertions compare them literally). ``row_validation`` records
    the installed-schema row check (see :func:`_validate_composition_rows`); its
    findings are folded into ``issues`` only when it reaches FAIL.

    A composition that is not valid UTF-8 is a **structured FAIL**, not an
    exception: this entry point is public (the smoke gate calls it in-process,
    ``check-governance`` calls the launcher as a subprocess), so it may never
    leak a traceback — and it must never report PASS for a file it could not
    read (G-10 / design §4.4.6 G10-c).
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
        "custom_skill_dirs_shape": None,
    }
    composition_path = preset_dir / _composition_filename()
    if not composition_path.is_file():
        result["issues"].append(
            f"preset composition missing: {composition_path.as_posix()}")
        result["verdict"] = "FAIL"
        return result
    try:
        composition = _read_text(composition_path)
    except CompositionUnreadable as exc:
        result["issues"].append(
            f"preset composition unreadable: {exc.diagnostic()}")
        result["verdict"] = "FAIL"
        return result
    result["row_validation"] = _validate_composition_rows(composition_path)
    if result["row_validation"]["verdict"] == "FAIL":
        result["issues"].extend(
            f"preset row/config rejected by the installed dsh schemas: {issue}"
            for issue in result["row_validation"]["issues"])
    result["custom_skill_dirs_shape"] = _shape_violations(composition)
    result["issues"].extend(
        f"customSkillDirs block shape drift: {violation}"
        for violation in result["custom_skill_dirs_shape"])
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
        _repo_root_for_preset(preset_dir, catalog_root, result["issues"])
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


def _row_schema_face(row_validation: dict) -> str:
    """The *verified* row-schema face of one surface, as one honest phrase.

    Reports how many of the enabled rows were actually validated against the
    installed schemas, and names the unverified remainder by reason. The
    previous wording interpolated ``rows_enabled`` into "N enabled row(s)
    validated", which asserted a verification the guard had not performed —
    the enabled count is a property of the composition, not a measurement
    (G-12, design §4.4.7 G12-a; the same defect class FIX-315 fixed in the
    guard's own PASS wording).
    """
    enabled = row_validation.get("rows_enabled", 0)
    checked = row_validation.get("rows_checked", 0)
    unverified = enabled - checked
    if unverified <= 0:
        return f"{checked}/{enabled} enabled row(s) verified against the installed dsh"
    reasons = (row_validation.get("coverage") or {}).get("unverified_reasons") or {}
    detail = ", ".join(f"{kind}={count}" for kind, count in sorted(reasons.items()))
    return (f"{checked}/{enabled} enabled row(s) verified against the installed "
            f"dsh; {unverified} NOT verified ({detail or 'reason not reported'})")


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
          f"({_row_schema_face(row_validation)}; "
          f"{row_validation.get('reason', '-')})")
    for violation in surface.get("custom_skill_dirs_shape") or []:
        print(f"[SMOKE]   [FAIL] customSkillDirs block shape drift: {violation}")
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
    home_var = _fact("HOME_VAR")
    # The witness needs a real home to fingerprint. When the profile is
    # unresolvable there is nothing to compare against — same fail-closed
    # reasoning as the write guard (N-1): refuse with a stable exit code
    # instead of letting `Path.home()` traceback out of a public entry.
    try:
        home = real_dsh_home()
    except (RuntimeError, OSError) as exc:
        message = (f"[SMOKE] [REFUSED] {home_var} is set but the user profile "
                   f"cannot be resolved ({type(exc).__name__}: {exc}) — "
                   f"refusing to run: the real home cannot be fingerprinted, "
                   f"so an isolated run cannot be proven isolated")
        print(message)
        print(message, file=sys.stderr)
        print(f"[SMOKE] Result: REFUSED (exit {SMOKE_EXIT_REFUSED})")
        return SMOKE_EXIT_REFUSED
    refusal = write_side_refusal(
        home, operation="run the smoke against the real preset root")
    if refusal is not None:
        message = f"[SMOKE] [REFUSED] {refusal}"
        print(message)
        print(message, file=sys.stderr)
        print(f"[SMOKE] Result: REFUSED (exit {SMOKE_EXIT_REFUSED})")
        return SMOKE_EXIT_REFUSED
    env_home = (os.environ.get(home_var) or "").strip()
    isolated = Path(env_home).expanduser()

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

    # The render source is the half the mounted composition can no longer show:
    # once tokens are substituted, `entry_form: ["token"]` is by definition no
    # longer observable, so "the shipped template still uses the declared token
    # form" has to be asserted on the template itself.
    try:
        _template_text = _read_text_with_newline_mode(_composition_template())
    except (CompositionUnreadable, OSError) as exc:
        issues.append(f"shipped render source unreadable: {exc}")
    else:
        issues.extend(
            f"shipped render source customSkillDirs block shape drift: {violation}"
            for violation in _shape_violations(_template_text, stage="template"))

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

    # D-54 sampling definition (design §3.3 row 11): one post-sample, and — only
    # when a top-level delta is suspected — a second one taken immediately after
    # it, so a host race that does not reproduce is disclosed instead of
    # failing the gate. The write surface is never re-sampled: it is the
    # adapter's own write face and a difference there is always a real write.
    after = _real_home_witness(home)
    comparison = witness_verdict(
        (before, after), resample=lambda: _real_home_witness(home))
    for advisory in comparison["advisories"]:
        print(f"[SMOKE] [ADVISORY] {advisory}")
    for failure in comparison["failures"]:
        issues.append(f"{failure} — the isolation guarantee is broken")
    print(f"[SMOKE] real-home writes : {len(comparison['failures'])} "
          f"({'witness unchanged — top-level names + preset write surface '
             'recursive' if comparison['verdict'] == 'PASS' else 'WITNESS CHANGED'})")

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
    print("[SMOKE] Result: PASS (isolated loading surface verified — preset "
          "rendered into a redirected "
          f"{home_var}, skill catalog + /{preset_id} gesture resolved, real "
          "home witness unchanged; row-schema depth is reported per surface "
          "above, and any row it could not validate is disclosed as NOT "
          "verified, never folded into this PASS)")
    return SMOKE_EXIT_PASS


def _entry_projection_shared():
    """FEAT-037: load the canonical entry-projection library.

    The section-span/splice/dual-presence logic lives ONCE in
    ``skills/software-project-governance/infra/sync_entry_projection.py``;
    this adapter imports it instead of duplicating the logic (task FEAT-037
    item 4: 生成逻辑与脚本一致，复用同一函数).
    """
    infra_dir = ROOT / "skills" / "software-project-governance" / "infra"
    if str(infra_dir) not in sys.path:
        sys.path.insert(0, str(infra_dir))
    import sync_entry_projection

    return sync_entry_projection


def write_bootstrap(project: Path, force: bool, dry_run: bool = False) -> int:
    project = project.expanduser().resolve()
    if not project.is_dir():
        print(f"ERROR: project root is not a directory: {project}", file=sys.stderr)
        return 1
    target = project / "AGENTS.md"
    try:
        source = _read_text(BOOTSTRAP_TEMPLATE)
    except CompositionUnreadable as exc:
        print(f"ERROR: {exc.diagnostic()}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: bootstrap template unreadable: {exc}", file=sys.stderr)
        return 1
    rendered, escaped = _substitute_repo_root(source)
    if escaped:
        print("ERROR: bootstrap template carries an unresolved token: "
              + ", ".join(escaped), file=sys.stderr)
        return 1
    try:
        shared = _entry_projection_shared()
    except ImportError as exc:
        print("ERROR: entry-projection shared module unavailable: "
              f"{exc} (FEAT-037 requires skills/software-project-governance/infra)",
              file=sys.stderr)
        return 1
    existing = None
    if target.exists():
        existing = target.read_text(encoding="utf-8", errors="replace")
    span = (shared.bootstrap_section_span(existing)
            if existing is not None else None)
    if existing is not None and span is None and not force:
        print(
            f"ERROR: {target} exists without a Governance Bootstrap section; "
            "re-run with --force to overwrite",
            file=sys.stderr,
        )
        return 1
    if dry_run:
        print(f"[DRY-RUN] bootstrap target: {target}")
        if span is not None:
            print("[DRY-RUN] planned write  : AGENTS.md bootstrap section splice "
                  "(non-bootstrap content preserved; FEAT-037)")
        else:
            print("[DRY-RUN] planned write  : AGENTS.md (thin governance pointer)")
        print("[DRY-RUN] nothing written — re-run without --dry-run to write")
        return 0
    if existing is not None and span is not None:
        # FEAT-037: splice the bootstrap section in place, preserving any
        # non-bootstrap content around it, instead of clobbering the file.
        primary = project / "CLAUDE.md"
        if primary.exists():
            primary_text = primary.read_text(encoding="utf-8", errors="replace")
            primary_section = shared.bootstrap_section_span(primary_text)
            if primary_section is not None and shared.has_full_bootstrap(
                    primary_text[primary_section[0]:primary_section[1]]):
                print("dual-presence note: CLAUDE.md carries the full bootstrap; "
                      "AGENTS.md stays the thin pointer (FEAT-037 dedup)")
        # FEAT-037 P3-4 (closed by FEAT-040): `newline=""` keeps the byte
        # discipline the rest of the projection stack already follows
        # (sync_entry_projection L342). Without it Python's text layer
        # translates every "\n" to os.linesep on Windows, so one bootstrap
        # write silently re-EOLs the WHOLE target file (LF -> CRLF) — a side
        # effect well outside the section this path claims to splice.
        target.write_text(shared.replace_bootstrap_section(existing, rendered),
                          encoding="utf-8", newline="")
    else:
        target.write_text(rendered, encoding="utf-8", newline="")
    print(f"bootstrap written: {target}")
    return 0


def _substitute_repo_root(template: str):
    """Substitute the declared repo-root token → ``(text, escaped_tokens)``.

    The token is looked up by its *target* in ``own.render.tokens`` (the entry
    whose package-relative path is the package root itself) rather than by a
    spelling held here, and ``escaped_tokens`` is scanned with the declared
    ``own.render.leftover_scan`` pattern. That scan — not a fixed list of
    "known" tokens — is what makes a *misspelled* token in the bootstrap
    template (``__Governance_Repo_Root__``) fail here instead of being written
    into a project's ``AGENTS.md`` (G-07).
    """
    targets = _token_paths()
    repo_token = next((token for token, path in targets.items()
                       if path == ROOT), None)
    if repo_token is None:
        raise _contract_error(
            "own.render.tokens",
            "declares no token whose target is the package root itself")
    rendered = template.replace(
        repo_token, str(ROOT.resolve()).replace("\\", "/"))
    return rendered, leftovers(rendered)


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

    try:
        manifest = json.loads(_read_text(MANIFEST_PATH))
    except CompositionUnreadable as exc:
        print(f"ERROR: {exc.diagnostic()}", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: adapter manifest unreadable: {MANIFEST_PATH}: {exc}",
              file=sys.stderr)
        return 1
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
