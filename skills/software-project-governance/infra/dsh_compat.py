"""DSH preset composition ↔ INSTALLED harness schema compatibility guard.

Why this module exists
----------------------
A ``dsh`` upgrade silently invalidated one row of the shipped ``governance``
preset: the row carried the config key ``text`` while the upgraded
``@deepseek-ai/dsh-persona`` declares ``prefix: z.string().required()``. The
loader rejected the whole preset mount (``invalid config: $.prefix missing
required value``) and users could not start a session. Nothing in CI and
nothing in ``verify_workflow.py`` caught it, because every existing guard
either reads our own files or boots an isolated session — none of them
compares a composition row against the *installed* dsh's real schemas.

What it does (the loader's own code and decision rules, not a re-implementation)
--------------------------------------------------------------------------------
For every preset composition in the package it replays what the loader does,
using the loader's own code taken from the installed dsh:

1. parse the YAML with the loader's own dialect — ``entryListSchema`` from
   ``@deepseek-ai/cordis-plugin-include`` (js-yaml ``JSON_SCHEMA`` extended
   with a ``tag:yaml.org,2002:js`` scalar type producing ``{__jsExpr}``);
2. interpolate ``!!js`` nodes with the loader's own ``evaluate(ctx, expr)``
   (``new Function('ctx','expr','with (ctx) { return eval(expr) }')``) and a
   scope carrying ``baseUrl`` (the composition's own directory URL) plus
   ``process``/``console``;
3. decide who starts, as ``Entry._disabled`` / ``Entry.disabledOf`` do: a
   ``!!js`` node is evaluated (and may throw — the loader calls it unguarded),
   anything else is truthiness; a group row itself is always enabled, **but a
   group's own ``disabled`` is inherited by its children** through the loader's
   owning-parent walk, so those children are reported as not started rather
   than validated;
4. for every row that does start, resolve the row's module the way the loader
   and ``dsh-agent-presets`` resolve it (relative → beside the composition,
   bare package → from the resolved plugin plane, ``cordis:`` → loader
   builtin), import it, and run the *resolved cordis's own*
   ``resolveConfig({Config}, config)`` — the exact call that produces the
   boot-time rejection. A throw IS the finding;
5. recurse into ``group`` rows through their ``config`` list.

No schema is copied or re-declared here. The oracle is whatever ``Config``
schema the resolved package exports, so the guard cannot drift from the plugin
set it validates against — that drift is precisely the defect class it exists
to catch. Known and deliberate divergences from upstream's *reader* helpers
(never from the loader): the group test is truthiness, matching the loader,
where ``dsh-agent-presets`` ``flattenRows`` uses ``=== true``; and a row whose
module cannot be resolved is a finding here, as dsh's own roster health check
also reports it.

Isolation and access boundaries (M7.7 (a) precedent, FEAT-015/016)
------------------------------------------------------------------
* The guard is **read-only static analysis over repo files plus module imports
  from the resolved plugin plane**. It performs one narrow READ of
  ``$DSH_HOME/profiles`` (and, when ``DSH_HOME`` is set, only then — it never
  guesses ``~/.dsh``) to resolve the plugin set dsh would load. It writes
  nothing to ``$DSH_HOME``, and the probe subprocess runs with ``DSH_HOME``
  redirected to a freshly created empty temp directory which is deleted
  afterwards.
* The isolated-home **witness is exactly that**: an entry count of the temp
  directory this run created (empty by construction), reported as
  ``home_writes``. It proves zero writes to that isolated home. It is NOT a
  global no-write proof — it cannot observe a write made anywhere else (a
  plugin's own ``os.homedir()`` write would land outside it), and
  ``USERPROFILE``/``HOME`` are not redirected.
* Module import executes only each package's own top-level evaluation — the
  same code ``dsh`` evaluates when it mounts the row. ``apply`` is never
  called, no ``Context``/``Fiber`` is constructed, and no plugin lifecycle
  runs.

Verdicts (repo optional-tooling policy)
---------------------------------------
``PASS``   every enabled row validated against the resolved schemas.
``FAIL``   a row's config was rejected (row id + module + the schema's exact
           message), a row's module could not be resolved, a ``!!js``
           expression threw, or a composition is not a valid entry list.
``NOT_RUN`` no node and/or no resolvable plugin set (with the reason), or
           nothing could be verified. ``NOT_RUN`` never counts as a gate issue
           — it discloses an unverified fact instead of inventing a green one.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Optional, Sequence

__all__ = [
    "CHECK_SECTION_TITLE",
    "COMPOSITION_FILENAMES",
    "COMPOSITION_GLOBS",
    "INSTALL_DIR_ENV",
    "NODE_MODULES_ENV",
    "ORACLE_PACKAGES",
    "PROBE_SCRIPT",
    "VERDICT_FAIL",
    "VERDICT_NOT_RUN",
    "VERDICT_PASS",
    "check_dsh_preset_compat",
    "discover_compositions",
    "emit_check_section",
    "locate_dsh_install",
    "main",
    "run_cli",
]

# ── verdict + diagnostic vocabulary ─────────────────────────────────────────
VERDICT_PASS = "PASS"
VERDICT_FAIL = "FAIL"
VERDICT_NOT_RUN = "NOT_RUN"

#: Row diagnostics that are findings (they gate).
FINDING_KINDS = (
    "CONFIG_INVALID",
    "MODULE_UNRESOLVED",
    "IMPORT_ERROR",
    "CONFIG_EXPR_ERROR",
    "DISABLED_EXPR_ERROR",
    "ROW_SHAPE",
)

#: Environment overrides for the harness install. Both spellings are honoured
#: so an operator can pin the install explicitly instead of relying on PATH.
INSTALL_DIR_ENV = "DSH_INSTALL_DIR"
NODE_MODULES_ENV = "DSH_HARNESS_NODE_MODULES"

#: dsh's own install anchor package (``INSTALL_ANCHOR`` in
#: ``@deepseek-ai/dsh``'s profile boot is
#: ``<install>/node_modules/@deepseek-ai/dsh/package.json``).
DSH_SCOPE = "@deepseek-ai"
DSH_PACKAGE = "dsh"
INSTALL_ANCHOR_REL = (DSH_SCOPE, DSH_PACKAGE, "package.json")

#: The packages whose OWN code decides a row's fate. Imported from the
#: resolved plane, never re-implemented:
#:   * ``cordis-plugin-include`` — the ``!!js`` YAML dialect (entryListSchema)
#:   * ``cordis-plugin-loader`` — ``evaluate`` / ``isJsExpr``
#:   * ``cordis``               — ``resolveConfig``, the call that throws
#:   * ``js-yaml``              — the parser those schemas are loaded with
#: Their versions are reported next to every verdict, because "which plugin set
#: did this validate against" is part of the answer.
ORACLE_PACKAGES = (
    "@deepseek-ai/cordis-plugin-loader",
    "@deepseek-ai/cordis-plugin-include",
    "@deepseek-ai/cordis",
    "js-yaml",
)

#: Environment variable dsh itself resolves its home from. Only an EXPLICITLY
#: set value is honoured: the guard never guesses ``~/.dsh``.
DSH_HOME_ENV = "DSH_HOME"
PROFILES_DIR_NAME = "profiles"

#: A preset directory is a directory holding this composition file
#: (``COMPOSITION_FILE`` in ``@deepseek-ai/dsh-agent-presets``).
COMPOSITION_FILENAMES = ("agent.cordis.yml",)
#: The package also ships the composition as a token template the adapter
#: launcher substitutes; it must satisfy the same row contract.
COMPOSITION_GLOBS = ("**/agent.cordis.yml", "**/*.cordis.yml.template")

_SKIP_DIRS = frozenset({".git", "node_modules", "__pycache__", ".venv", "venv",
                        ".pytest_cache", ".mypy_cache"})

#: Wall-clock budget for one probe run (it imports ~30 plugin packages).
DEFAULT_PROBE_TIMEOUT = 180


# ── the Node probe: the loader's own code, taken from the installed dsh ──────
# Raw string: the JS uses \n inside string literals, which must reach Node
# unchanged. The probe never imports anything by a relative specifier — every
# module URL is derived from `request.nodeModules`, so the script itself can
# live anywhere.
PROBE_SCRIPT = r"""
import { readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { isAbsolute, join } from 'node:path'
import { pathToFileURL } from 'node:url'

const request = JSON.parse(readFileSync(0, 'utf8'))
const out = { ok: false, probe: {}, files: [] }

function fail(reason) {
  out.error = reason
  writeFileSync(request.output, JSON.stringify(out))
  process.exit(0)
}

// Resolve bare package names exactly the way the loader does for a preset row:
// an upward `node_modules` walk from the harness plane. Anchoring `createRequire`
// at a path INSIDE the plane puts the plane's own `node_modules` first — the
// plane IS a node_modules directory, so the walk finds it one level up.
let req
try {
  req = createRequire(join(request.nodeModules, '__dsh_compat_anchor__.js'))
} catch (error) {
  fail(`createRequire(${request.nodeModules}) failed: ${error && error.message}`)
}
const fileUrl = (spec) => pathToFileURL(req.resolve(spec)).href

let entryListSchema, evaluate, isJsExpr, resolveConfig, yaml
try {
  yaml = await import(fileUrl('js-yaml'))
  const include = await import(fileUrl('@deepseek-ai/cordis-plugin-include'))
  const loader = await import(fileUrl('@deepseek-ai/cordis-plugin-loader'))
  const cordis = await import(fileUrl('@deepseek-ai/cordis'))
  entryListSchema = include.entryListSchema
  evaluate = loader.evaluate
  isJsExpr = loader.isJsExpr
  resolveConfig = cordis.resolveConfig
} catch (error) {
  fail(`installed harness API unavailable: ${error && error.name}: ${error && error.message}`)
}
for (const [name, value] of [['entryListSchema', entryListSchema], ['evaluate', evaluate],
                             ['isJsExpr', isJsExpr], ['resolveConfig', resolveConfig]]) {
  if (typeof value !== 'function' && typeof value !== 'object') {
    fail(`installed harness API is not callable: ${name}`)
  }
}
out.probe = {
  loader: req.resolve('@deepseek-ai/cordis-plugin-loader/package.json'),
  include: req.resolve('@deepseek-ai/cordis-plugin-include/package.json'),
  cordis: req.resolve('@deepseek-ai/cordis/package.json'),
}

/* The loader's own recursive `!!js` interpolation (config/utils.ts). */
function interpolate(ctx, value) {
  if (isJsExpr(value)) return evaluate(ctx, value.__jsExpr)
  if (!value || typeof value !== 'object') return value
  if (Array.isArray(value)) return value.map((item) => interpolate(ctx, item))
  const result = {}
  for (const [key, item] of Object.entries(value)) result[key] = interpolate(ctx, item)
  return result
}

/* The Loader's own export normalization (Loader.unwrapExports). */
function unwrapExports(exports) {
  if (exports === null || exports === undefined) return exports
  exports = exports.default !== undefined && exports.default !== null ? exports.default : exports
  if (!exports.__esModule) return exports
  return exports.default !== undefined && exports.default !== null ? exports.default : exports
}

function message(error) {
  if (error === null || error === undefined) return String(error)
  const text = typeof error.message === 'string' ? error.message : String(error)
  return `${error.name ? error.name + ': ' : ''}${text.split('\n')[0]}`
}

/* The exact call that produces the boot-time rejection (cordis resolveConfig). */
function validateConfig(schema, config) {
  return resolveConfig({ Config: schema }, config)
}

/* Entry.disabledOf, verbatim: a `!!js` node is evaluated against the loader
   context, anything else is truthiness. It is allowed to THROW — the loader's
   own `_disabled` calls it unguarded, so a throwing expression rejects the
   mount instead of being swallowed. */
function disabledOf(row, ctx) {
  return isJsExpr(row.disabled) ? Boolean(evaluate(ctx, row.disabled.__jsExpr))
                                : Boolean(row.disabled)
}

async function walk(rows, at, ctx, entry, inheritedBy) {
  for (const [index, row] of rows.entries()) {
    const positional = at === '' ? `row ${index + 1}` : `${at} row ${index + 1}`
    const id = row && typeof row.id === 'string' && row.id !== '' ? row.id : positional
    if (row === null || typeof row !== 'object' || Array.isArray(row)
        || typeof row.name !== 'string' || row.name === '') {
      entry.rows.push({ row: id, name: '', kind: 'ROW_SHAPE', message:
        `${positional} is not a plugin row (a "name" string is required)` })
      continue
    }
    const name = row.name
    // Group rows: `Entry._disabled` line 1 (`if (options.group) return false`)
    // makes the GROUP itself always enabled, and `Entry.refresh` skips a row
    // only when `_disabled` is true. But the same function then walks the
    // owning-parent chain — `while (entry) { if (this.disabledOf(entry.options))
    // return true; entry = entry.parent.ctx.fiber.entry }` — applying
    // `disabledOf` to every ancestor WITHOUT that short-circuit, so a child of
    // a `disabled: true` group never starts. The roster's own reader agrees
    // (`@deepseek-ai/dsh-agent-presets` composition-inventory
    // `combineDisabled(outer, own)`: "lets children inherit its disabled").
    //
    // Divergence, deliberate: the group test here is truthiness, matching the
    // loader (`if (options.group)`, and the mount path's own `row.group`),
    // rather than `flattenRows`' stricter `=== true`. The loader decides what
    // mounts, so the loader's test is the one reproduced.
    if (row.group) {
      if (!Array.isArray(row.config)) {
        entry.rows.push({ row: id, name, kind: 'ROW_SHAPE', message:
          `group ${positional} must hold a list of plugin rows` })
        continue
      }
      let groupDisabled
      try {
        groupDisabled = disabledOf(row, ctx)
      } catch (error) {
        entry.rows.push({ row: id, name, kind: 'DISABLED_EXPR_ERROR', message:
          `group disabled !!js expression threw: ${message(error)}` })
        continue
      }
      await walk(row.config, positional, ctx, entry,
                 inheritedBy || (groupDisabled ? id : ''))
      continue
    }
    let disabled
    try {
      disabled = disabledOf(row, ctx)
    } catch (error) {
      entry.rows.push({ row: id, name, kind: 'DISABLED_EXPR_ERROR', message:
        `disabled !!js expression threw: ${message(error)}` })
      continue
    }
    if (inheritedBy) {
      // Not a finding: the loader never starts this row. Disclosed so the
      // skip stays visible instead of silently dropping rows.
      entry.inherited_disabled += 1
      entry.rows.push({ row: id, name, kind: 'DISABLED_INHERITED', message:
        `not started — inherits disabled from ancestor entry "${inheritedBy}"` })
      continue
    }
    if (disabled) continue
    entry.enabled += 1

    let config
    try {
      config = interpolate(ctx, row.config)
    } catch (error) {
      entry.rows.push({ row: id, name, kind: 'CONFIG_EXPR_ERROR', message:
        `config !!js expression threw: ${message(error)}` })
      continue
    }

    if (name.startsWith('cordis:')) {
      entry.rows.push({ row: id, name, kind: 'BUILTIN', message:
        'loader builtin — no module to import, no schema to apply' })
      continue
    }
    let target
    if (name.startsWith('file:') || isAbsolute(name)) {
      target = name.startsWith('file:') ? name : pathToFileURL(name).href
    } else if (name.startsWith('.')) {
      target = new URL(name, ctx.baseUrl).href
    } else {
      try {
        target = pathToFileURL(req.resolve(name)).href
      } catch (error) {
        entry.rows.push({ row: id, name, kind: 'MODULE_UNRESOLVED', message:
          `cannot resolve from the installed harness (${request.nodeModules}): ${message(error)}` })
        continue
      }
    }

    let exports
    try {
      exports = unwrapExports(await import(target))
    } catch (error) {
      entry.rows.push({ row: id, name, kind: 'IMPORT_ERROR', message:
        `import failed for ${target}: ${message(error)}` })
      continue
    }
    const schema = exports && exports.Config
    if (!schema) {
      entry.rows.push({ row: id, name, kind: 'NO_SCHEMA', message:
        'module exports no Config schema — the loader passes this config through unvalidated' })
      continue
    }
    entry.checked += 1
    try {
      validateConfig(schema, config)
      entry.rows.push({ row: id, name, kind: 'PASS', message: '' })
    } catch (error) {
      // cordis throws a ValidationError built from the standard-schema issues
      // but does not retain them, so recover the exact per-issue messages by
      // running the same `~standard.validate` call `resolveConfig` performs
      // (cordis lib: `runtime.Config['~standard'].validate(config)`).
      let issues = []
      try {
        const standard = schema['~standard']
        const result = typeof standard?.validate === 'function' ? standard.validate(config) : undefined
        if (result && Array.isArray(result.issues)) {
          issues = result.issues.map((issue) => (issue && issue.message) || String(issue))
        }
      } catch (nested) {
        issues = []
      }
      const full = typeof error.message === 'string' ? error.message : String(error)
      entry.rows.push({
        row: id, name, kind: 'CONFIG_INVALID',
        message: issues.length > 0 ? issues.join('; ') : full.split('\n').join(' '),
        detail: full,
      })
    }
  }
}

for (const file of request.files) {
  const entry = { path: file.path, status: 'OK', rows: [], enabled: 0, checked: 0,
                  inherited_disabled: 0 }
  let text
  try {
    text = readFileSync(file.path, 'utf8')
  } catch (error) {
    entry.status = 'UNREADABLE'
    entry.error = message(error)
    out.files.push(entry)
    continue
  }
  let rows
  try {
    rows = yaml.load(text, { schema: entryListSchema })
  } catch (error) {
    entry.status = 'PARSE_ERROR'
    entry.error = message(error)
    out.files.push(entry)
    continue
  }
  if (!Array.isArray(rows)) {
    entry.status = 'PARSE_ERROR'
    entry.error = 'the composition must be a top-level list of plugin rows'
    out.files.push(entry)
    continue
  }
  const ctx = { baseUrl: pathToFileURL(file.path).href, process, console }
  await walk(rows, '', ctx, entry, '')
  out.files.push(entry)
}

out.ok = true
writeFileSync(request.output, JSON.stringify(out))
process.exit(0)
"""


# ── scratch directories (sandbox-safe) ──────────────────────────────────────
def _make_scratch_dir(prefix: str) -> Path:
    """Create a scratch directory the file sandbox can actually write into.

    ``tempfile.mkdtemp`` creates its directory with mode ``0o700``, whose
    non-inheriting DACL a Windows file sandbox (an ACL-based grant) cannot
    write into; the default mode inherits the grant. The naming and cleanup
    contract is otherwise the same: a unique path under the platform temp
    root, removed by :func:`_remove_scratch_dir`.
    """
    base = Path(tempfile.gettempdir())
    for _ in range(64):
        candidate = base / f"{prefix}{os.urandom(6).hex()}"
        try:
            candidate.mkdir(mode=0o777)
        except FileExistsError:
            continue
        return candidate
    raise OSError(f"cannot create a scratch directory under {base}")


def _remove_scratch_dir(path: Optional[Path]) -> None:
    if path is None:
        return
    shutil.rmtree(path, ignore_errors=True)


def _count_entries(path: Path) -> int:
    try:
        return sum(1 for _ in path.rglob("*"))
    except OSError:
        return -1


# ── plugin-set discovery (read-only; never guesses ~/.dsh) ──────────────────
def _looks_like_node_modules(path: Path) -> bool:
    return (path / INSTALL_ANCHOR_REL[0] / INSTALL_ANCHOR_REL[1]
            / INSTALL_ANCHOR_REL[2]).is_file()


def _walk_up_for_node_modules(start: Path) -> Optional[Path]:
    """Node's own upward ``node_modules`` walk, anchored at dsh's install."""
    current = start
    while True:
        if current.name == "node_modules" and _looks_like_node_modules(current):
            return current
        candidate = current / "node_modules"
        if _looks_like_node_modules(candidate):
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _from_env_override(value: str) -> Optional[Path]:
    """Normalize an operator-supplied install/node_modules path."""
    path = Path(value).expanduser()
    if _looks_like_node_modules(path):
        return path
    if _looks_like_node_modules(path / "node_modules"):
        return path / "node_modules"
    return None


def _package_version(node_modules: Path, name: str) -> Optional[dict]:
    """Version + path of one package inside a resolution plane (never imports)."""
    package_json = node_modules.joinpath(*name.split("/"), "package.json")
    if not package_json.is_file():
        return None
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    try:
        real = package_json.resolve()
    except OSError:  # pragma: no cover - unresolvable link
        real = package_json
    return {
        "version": payload.get("version") if isinstance(payload.get("version"), str) else None,
        "path": real.parent.as_posix(),
    }


def _oracle_versions(node_modules: Path) -> dict:
    out = {}
    for name in ORACLE_PACKAGES:
        found = _package_version(node_modules, name)
        out[name] = found or {"version": None, "path": None}
    return out


def _env_text(env: dict, key: str) -> str:
    """Read one environment value as stripped text (tolerates path-like values)."""
    raw = env.get(key)
    return "" if raw is None else str(raw).strip()


def _profile_planes(env: dict) -> list:
    """dsh's OWN resolution plane, read-only, from an explicitly set ``$DSH_HOME``.

    dsh resolves a profile's bare plugin names out of ``$DSH_HOME/profiles``:
    each profile's own ``node_modules`` is pnpm-managed and authoritative, and
    ``$DSH_HOME/profiles/node_modules`` is the installation mirror dsh heals
    (``healProfilesModuleFallback``). The schemas that decide whether a preset
    row mounts come from the RUNTIME BUNDLE packages resolved there — not from
    the ``@deepseek-ai/dsh`` CLI package, whose version string is a different
    fact entirely.

    Only an explicitly exported ``DSH_HOME`` is consulted — the guard never
    guesses ``~/.dsh`` — and the access is a read of ``profiles/`` only: nothing
    here is written, moved, or created. (The isolated-home witness does not
    prove this; it counts entries in the probe's own temp home, which is a
    different directory. The read-only claim rests on the code: every call in
    this function is ``iterdir``/``is_dir``/``read_text``.)
    """
    raw = _env_text(env, DSH_HOME_ENV)
    if not raw:
        return []
    profiles = Path(raw).expanduser() / PROFILES_DIR_NAME
    planes = []
    try:
        children = sorted(profiles.iterdir())
    except OSError:
        children = []
    for child in children:
        candidate = child / "node_modules"
        if child.is_dir() and candidate.is_dir():
            planes.append((f"{DSH_HOME_ENV}/{PROFILES_DIR_NAME}/{child.name}", candidate))
    fallback = profiles / "node_modules"
    if fallback.is_dir():
        planes.append((f"{DSH_HOME_ENV}/{PROFILES_DIR_NAME}", fallback))
    return planes


def locate_dsh_install(env: Optional[dict] = None,
                       which=shutil.which) -> dict:
    """Locate the plugin set a preset mount actually uses.

    Precedence:

    1. the explicit ``DSH_INSTALL_DIR`` / ``DSH_HARNESS_NODE_MODULES`` override;
    2. dsh's own **profile plane** (``$DSH_HOME/profiles/<profile>/node_modules``,
       then the ``$DSH_HOME/profiles/node_modules`` installation mirror) —
       consulted only when ``DSH_HOME`` is explicitly set, read-only;
    3. the **install anchor** reached from the ``dsh`` executable on PATH —
       the same anchor dsh derives from its own module URL.

    The ``@deepseek-ai/dsh`` CLI package version is reported for context only:
    it is NOT what decides a row's schema. What decides it is the set of
    packages reported under ``oracle_packages`` (and, per row, the module the
    row names), each with the absolute path it was resolved from — a guard that
    silently validated against a different plugin set than the user runs would
    be worse than ``NOT_RUN``.

    Returns ``{"status", "reason", "source", "plane", "node_modules",
    "dsh_package", "dsh_version", "cli_package", "oracle_packages",
    "other_planes"}``.
    """
    env = os.environ if env is None else env
    result = {
        "status": VERDICT_NOT_RUN,
        "reason": "",
        "source": None,
        "plane": None,
        "node_modules": None,
        "dsh_package": None,
        "dsh_version": None,
        "cli_package": None,
        "oracle_packages": {},
        "other_planes": [],
    }

    chosen = None
    chosen_plane = None
    candidates = []
    for key in (INSTALL_DIR_ENV, NODE_MODULES_ENV):
        raw = _env_text(env, key)
        if not raw:
            continue
        resolved = _from_env_override(raw)
        if resolved is None:
            result["reason"] = (
                f"{key}={raw!r} does not contain "
                f"{'/'.join(INSTALL_ANCHOR_REL)} (checked the path itself and "
                f"its node_modules/); refusing to fall back to another install")
            result["source"] = f"${key} (invalid)"
            return result
        chosen, chosen_plane = resolved, f"${key}"
        break
    else:
        candidates = _profile_planes(env)
        for label, plane in candidates:
            if _package_version(plane, ORACLE_PACKAGES[0]) is not None \
                    or _looks_like_node_modules(plane):
                chosen, chosen_plane = plane, label
                break
        if chosen is None:
            executable = which("dsh")
            if executable:
                found = _walk_up_for_node_modules(Path(executable).resolve().parent)
                if found is not None:
                    chosen, chosen_plane = found, f"install anchor (`dsh` on PATH: {executable})"
                else:
                    result["reason"] = (
                        f"`dsh` resolved to {executable}, but no node_modules "
                        f"carrying {'/'.join(INSTALL_ANCHOR_REL)} was found above it")
                    result["source"] = "`dsh` on PATH (anchor not found)"
                    return result

    if chosen is None:
        result["reason"] = result["reason"] or (
            f"no dsh plugin set discovered: set ${INSTALL_DIR_ENV} or "
            f"${NODE_MODULES_ENV}, or put `dsh` on PATH")
        return result

    result.update(status="OK", source=chosen_plane, plane=chosen_plane,
                  node_modules=str(chosen))
    package_json = chosen.joinpath(*INSTALL_ANCHOR_REL)
    result["dsh_package"] = str(package_json.parent) if package_json.is_file() else None
    cli = _package_version(chosen, f"{DSH_SCOPE}/{DSH_PACKAGE}")
    if cli is None:
        # A profile plane mirrors the INSTALLATION's dependencies; the CLI
        # package itself may legitimately live only in the install tree.
        for label, plane in _profile_planes(env):
            cli = _package_version(plane, f"{DSH_SCOPE}/{DSH_PACKAGE}")
            if cli is not None:
                break
    result["dsh_version"] = cli["version"] if cli else None
    result["cli_package"] = dict(cli or {"version": None, "path": None},
                                 note=("informational only — the "
                                       "@deepseek-ai/dsh CLI package version "
                                       "does not decide a row's schema; the "
                                       "oracle packages below do"))
    result["oracle_packages"] = _oracle_versions(chosen)
    for label, plane in candidates:
        if plane == chosen:
            continue
        versions = _oracle_versions(plane)
        if not any(entry["version"] for entry in versions.values()):
            continue  # a plane that carries none of the oracle packages is not a competing set
        result["other_planes"].append({
            "plane": label,
            "node_modules": str(plane),
            "oracle_versions": {name: entry["version"]
                                for name, entry in versions.items()},
        })
    return result


# ── composition discovery ───────────────────────────────────────────────────
def discover_compositions(root: os.PathLike) -> list:
    """Every preset composition in the package, sorted by relative path.

    Covers both shipped forms: a preset's own ``agent.cordis.yml`` and the
    adapter's ``*.cordis.yml.template`` (the same row contract, with the
    launcher's path tokens substituted at install time).
    """
    root = Path(root)
    found = []
    for pattern in COMPOSITION_GLOBS:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if any(part in _SKIP_DIRS for part in relative.parts):
                continue
            found.append(path)
    return sorted(set(found), key=lambda item: item.relative_to(root).as_posix())


# ── the probe run ───────────────────────────────────────────────────────────
def _stderr_head(text: str, lines: int = 6) -> str:
    """First non-empty stderr lines — where a Node/V8 fatal error states itself."""
    head = [line for line in (text or "").splitlines() if line.strip()][:lines]
    return " | ".join(head)


def _run_probe(node: str, install: dict, compositions: Sequence[Path],
               root: Path, timeout: int) -> dict:
    """Run the Node probe once for every composition; return its report.

    The child always inherits this process's environment with ``DSH_HOME``
    redirected to the isolated temp directory — the environment is never
    replaced wholesale, because a stripped environment (no ``SystemRoot``/
    ``PATH``) aborts Node outright and would turn every run into a spurious
    ``NOT_RUN``.

    Returns ``{"status", "reason", "report", "stdout", "stderr",
    "isolation": {"temp_home", "home_writes", "mechanism"}}``.
    """
    scratch = None
    home = None
    result = {
        "status": VERDICT_NOT_RUN,
        "reason": "",
        "report": None,
        "stdout": "",
        "stderr": "",
        "isolation": {
            "temp_home": None,
            "home_writes": None,
            "mechanism": (
                "subprocess DSH_HOME redirected to a freshly created empty temp "
                "directory, removed afterwards; `home_writes` is this run's "
                "entry count of THAT directory (empty by construction), so it "
                "proves zero writes to the isolated home — it is not a global "
                "no-write proof (module imports and a read-only "
                "$DSH_HOME/profiles probe still happen outside it). "
                "M7.7 (a) precedent, FEAT-015/016"),
        },
    }
    try:
        scratch = _make_scratch_dir("spg-dsh-compat-")
        home = _make_scratch_dir("spg-dsh-compat-home-")
    except OSError as exc:
        result["reason"] = f"cannot create the probe scratch directory: {exc}"
        _remove_scratch_dir(scratch)
        _remove_scratch_dir(home)
        return result

    result["isolation"]["temp_home"] = home.as_posix()
    output_path = scratch / "report.json"
    request = {
        "nodeModules": install["node_modules"],
        "output": str(output_path),
        "files": [{"path": str(path)} for path in compositions],
    }
    child_env = os.environ.copy()
    child_env["DSH_HOME"] = str(home)
    try:
        completed = subprocess.run(
            [node, "--input-type=module", "--eval", PROBE_SCRIPT],
            cwd=str(root),
            env=child_env,
            input=json.dumps(request, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["reason"] = f"probe could not run: {type(exc).__name__}: {exc}"
        _remove_scratch_dir(scratch)
        _remove_scratch_dir(home)
        return result

    result["stdout"] = completed.stdout or ""
    result["stderr"] = completed.stderr or ""
    result["isolation"]["home_writes"] = _count_entries(home)

    raw = None
    try:
        raw = output_path.read_text(encoding="utf-8")
    except OSError:
        raw = None
    _remove_scratch_dir(scratch)
    _remove_scratch_dir(home)

    if raw is None:
        result["reason"] = (
            f"probe produced no report (exit {completed.returncode}): "
            f"{_stderr_head(completed.stderr) or 'no stderr'}")
        return result
    try:
        report = json.loads(raw)
    except ValueError as exc:
        result["reason"] = f"probe report is not JSON: {exc}"
        return result
    result["report"] = report
    if not report.get("ok"):
        result["reason"] = (
            f"probe could not build the oracle from the installed harness: "
            f"{report.get('error')}")
        return result
    result["status"] = "OK"
    return result


# ── aggregation ─────────────────────────────────────────────────────────────
def _composition_entry(payload: dict, root: Path) -> dict:
    try:
        display = Path(payload["path"]).relative_to(root).as_posix()
    except (KeyError, ValueError):
        display = str(payload.get("path"))
    return {
        "path": display,
        "status": payload.get("status") or "OK",
        "error": payload.get("error") or "",
        "enabled": int(payload.get("enabled") or 0),
        "checked": int(payload.get("checked") or 0),
        "inherited_disabled": int(payload.get("inherited_disabled") or 0),
        "rows": list(payload.get("rows") or []),
    }


def check_dsh_preset_compat(root: Optional[os.PathLike] = None,
                            compositions: Optional[Iterable[os.PathLike]] = None,
                            env: Optional[dict] = None,
                            which=shutil.which,
                            node: Optional[str] = None,
                            timeout: int = DEFAULT_PROBE_TIMEOUT,
                            install: Optional[dict] = None,
                            probe_runner=None) -> dict:
    """Validate every preset composition against the installed harness schemas.

    Parameters are test seams: ``which``/``node`` override the executable
    lookup, ``install`` injects a discovered install, ``env`` replaces the
    process environment, ``probe_runner`` replaces the Node probe call.
    Returns the aggregate report consumed by ``check-governance`` Check 28v
    and by the ``check-dsh-preset-compat`` subcommand.
    """
    probe_runner = _run_probe if probe_runner is None else probe_runner
    root = Path(root) if root is not None else Path(__file__).resolve().parents[3]
    env = os.environ if env is None else env
    report = {
        "verdict": VERDICT_NOT_RUN,
        "reason": "",
        "issues": [],
        "details": [],
        "install": {},
        "isolation": {"temp_home": None, "home_writes": None, "mechanism": ""},
        "compositions": [],
        "rows_enabled": 0,
        "rows_checked": 0,
        "rows_inherited_disabled": 0,
    }

    paths = ([Path(item) for item in compositions] if compositions is not None
             else discover_compositions(root))
    paths = [path if path.is_absolute() else root / path for path in paths]
    if not paths:
        report["reason"] = (
            f"no preset composition found under {root.as_posix()} "
            f"(looked for {' and '.join(COMPOSITION_GLOBS)})")
        return report

    install_probe = install if install is not None else locate_dsh_install(env=env, which=which)
    report["install"] = dict(install_probe)
    if install_probe.get("status") != "OK":
        report["reason"] = (
            f"installed dsh not available — composition schemas cannot be "
            f"validated: {install_probe.get('reason')}")
        report["details"].append(report["reason"])
        return report

    node_path = node if node is not None else which("node")
    report["install"]["node"] = node_path
    if not node_path:
        report["reason"] = (
            "node executable not found on PATH — the installed harness's own "
            "YAML dialect and Config schemas cannot be reached without it")
        report["details"].append(report["reason"])
        return report
    try:
        version = subprocess.run([node_path, "--version"], capture_output=True,
                                 text=True, encoding="utf-8", errors="replace",
                                 timeout=30)
        report["install"]["node_version"] = (version.stdout or "").strip() or None
    except (OSError, subprocess.TimeoutExpired):
        report["install"]["node_version"] = None

    probe = probe_runner(node_path, install_probe, paths, root, timeout)
    report["isolation"] = probe["isolation"]
    if probe["status"] != "OK":
        report["reason"] = probe["reason"]
        report["details"].append(probe["reason"])
        report["details"].extend(
            line for line in (probe["stderr"] or "").splitlines() if line.strip())
        return report

    payload = probe["report"]
    # Never trust a report that did not build its oracle: an unbuilt oracle
    # means nothing was validated, which is NOT_RUN, never an empty PASS.
    if not payload.get("ok"):
        report["reason"] = (
            f"probe could not build the oracle from the installed harness: "
            f"{payload.get('error')}")
        report["details"].append(report["reason"])
        return report
    report["install"]["probe_versions"] = dict(payload.get("probe") or {})
    resolved = report["install"].get("oracle_packages") or {}
    report["details"].append(
        "resolved plane: " + (report["install"].get("source") or "-")
        + " -> " + (report["install"].get("node_modules") or "-"))
    report["details"].append(
        "oracle packages: " + ", ".join(
            f"{name}@{entry.get('version') or '?'} ({entry.get('path') or '?'})"
            for name, entry in sorted(resolved.items())))
    cli = report["install"].get("cli_package") or {}
    report["details"].append(
        f"@deepseek-ai/dsh CLI package {cli.get('version') or '?'} "
        f"({cli.get('path') or '?'}) — informational only; a row's schema comes "
        f"from the oracle packages above, not from the CLI version")
    for other in report["install"].get("other_planes") or []:
        differing = {
            name: (entry.get("version"), other["oracle_versions"].get(name))
            for name, entry in resolved.items()
            if other["oracle_versions"].get(name) != entry.get("version")
        }
        label = (f"other plane {other['plane']} ({other['node_modules']})")
        if differing:
            report["details"].append(
                f"[SKEW] {label} carries DIFFERENT oracle versions: "
                + ", ".join(f"{n}: using {a} vs {b}" for n, (a, b) in sorted(differing.items()))
                + " — validated against the plane named above")
        else:
            report["details"].append(f"{label} carries the same oracle versions")
    failures = []
    unverified = []
    for item in payload.get("files") or []:
        entry = _composition_entry(item, root)
        report["compositions"].append(entry)
        report["rows_enabled"] += entry["enabled"]
        report["rows_checked"] += entry["checked"]
        report["rows_inherited_disabled"] += entry["inherited_disabled"]
        if entry["status"] == "UNREADABLE":
            unverified.append(
                f"{entry['path']}: composition could not be read "
                f"({entry['error']}) — rows NOT verified")
            continue
        if entry["status"] == "PARSE_ERROR":
            failures.append(
                f"{entry['path']}: not a valid entry list — {entry['error']}")
            continue
        if entry["enabled"] == 0:
            # F4: a discovered composition whose every row is disabled mounts
            # nothing. That is a real user-facing outcome, so it is disclosed
            # — but as [INFO], not [WARN]: the quick-scan reader counts
            # `[WARN]` as an issue token while this does not increment the
            # engine's gate count, and the two faces must not disagree.
            report["details"].append(
                f"{entry['path']}: composition declares no enabled rows — this "
                f"preset would mount nothing")
        for row in entry["rows"]:
            kind = row.get("kind")
            if kind in FINDING_KINDS:
                failures.append(
                    f"{entry['path']}: row \"{row.get('row')}\" "
                    f"({row.get('name') or 'unnamed'}): {row.get('message')}")
            elif kind == "PASS":
                report["details"].append(
                    f"{entry['path']}: row \"{row.get('row')}\" {row.get('name')} OK")
            else:
                report["details"].append(
                    f"{entry['path']}: row \"{row.get('row')}\" {row.get('name')} "
                    f"[{kind}] {row.get('message')}")

    report["details"].extend(unverified)
    report["issues"] = failures
    plane = install_probe.get("source") or "unknown plane"
    oracle_label = ", ".join(
        f"{name}@{entry.get('version') or '?'}"
        for name, entry in sorted(
            (report["install"].get("oracle_packages") or {}).items()))
    if failures:
        report["verdict"] = VERDICT_FAIL
        report["reason"] = (
            f"{len(failures)} preset composition row(s) rejected by the plugin "
            f"set resolved from {plane} ({oracle_label})")
    elif not report["compositions"] or report["rows_enabled"] == 0:
        report["verdict"] = VERDICT_NOT_RUN
        if report["compositions"]:
            # F4: every discovered row is disabled, so the preset mounts
            # nothing. Named explicitly instead of a generic "nothing
            # verified" — it is a user-visible outcome, not a tooling gap.
            report["reason"] = (
                f"no enabled preset row could be validated — every row of "
                f"{len(report['compositions'])} composition(s) is disabled "
                f"({report['rows_inherited_disabled']} inherited from a "
                f"disabled ancestor), so this preset would mount nothing")
        else:
            report["reason"] = (
                "no enabled preset row could be validated — nothing was "
                "verified (fail-closed: never reported as PASS)")
    else:
        report["verdict"] = VERDICT_PASS
        report["reason"] = (
            f"{report['rows_checked']} enabled row(s) validated against the "
            f"plugin set resolved from {plane} ({oracle_label}); "
            f"{len(report['compositions'])} composition(s) checked")
    return report


# ── CLI ─────────────────────────────────────────────────────────────────────
# ── render layer (kept here, not in the engine) ─────────────────────────────
# The engine's own R4 ratchet states it outright: "orchestration output belongs
# to the render layer". Check 28v therefore contributes a banner/footer pair to
# `_run_full_engine_checks` and nothing else — every line of its body is
# rendered here, so adding the check does not grow the monolith's print surface.
CHECK_SECTION_TITLE = "Check 28v: DSH Preset Schema Compat"


def emit_check_section(stream=None) -> int:
    """Run the guard and print the whole framed Check 28v section.

    The engine contributes the call, not the output: its own R4 ratchet budgets
    print calls per function, and a new check must not spend that budget. The
    full rationale for the check is this module's docstring.

    Returns the section's gate issue count — a FAIL returns its finding count
    (the engine adds it to ``all_issues``); ``NOT_RUN`` and a partially verified
    PASS disclose and return 0, because an unverified fact must never read as a
    gate issue.
    """
    report = check_dsh_preset_compat()
    stream = sys.stdout if stream is None else stream
    print(f"\n┌─ {CHECK_SECTION_TITLE} {'─' * max(1, 60 - len(CHECK_SECTION_TITLE))}┐",
          file=stream)
    install = report.get("install") or {}
    isolation = report.get("isolation") or {}
    oracle = ", ".join(
        f"{name}@{entry.get('version') or '?'}"
        for name, entry in sorted((install.get("oracle_packages") or {}).items()))
    print(f"│  resolution plane: {install.get('source') or 'not discovered'}",
          file=stream)
    print(f"│    resolved at: {install.get('node_modules') or '-'}", file=stream)
    print(f"│    oracle: {oracle or '(none resolved)'}", file=stream)
    cli = install.get("cli_package") or {}
    print(f"│    @deepseek-ai/dsh CLI {cli.get('version') or '?'} "
          f"(informational — a row's schema comes from the oracle packages "
          f"above, not from the CLI version)", file=stream)
    for other in install.get("other_planes") or []:
        print(f"│    other plane {other['plane']}: {other['node_modules']} "
              f"{other['oracle_versions']}", file=stream)
    print(f"│  compositions: {len(report['compositions'])}; "
          f"enabled rows: {report['rows_enabled']}; "
          f"schema-checked rows: {report['rows_checked']}; "
          f"inherited-disabled rows: {report.get('rows_inherited_disabled', 0)}; "
          f"isolated-home writes: {isolation.get('home_writes')}", file=stream)
    verdict = report["verdict"]
    if verdict == VERDICT_FAIL:
        print(f"│  [FAIL] {report['reason']}", file=stream)
        for issue in report["issues"][:10]:
            print(f"│    - {issue}", file=stream)
        if len(report["issues"]) > 10:
            print(f"│    ... and {len(report['issues']) - 10} more", file=stream)
        print("└──────────────────────────────────────────────────────┘", file=stream)
        return len(report["issues"])
    if verdict == VERDICT_NOT_RUN:
        print(f"│  [NOT_RUN] {report['reason']}", file=stream)
        print("└──────────────────────────────────────────────────────┘", file=stream)
        return 0
    print(f"│  [PASS] {report['reason']}", file=stream)
    for detail in report["details"]:
        if "NOT verified" in detail:
            print(f"│  [NOT_RUN] {detail}", file=stream)
    print("└──────────────────────────────────────────────────────┘", file=stream)
    return 0


def run_cli(fail_on_issues: bool = False, stream=None) -> int:
    """Render the standalone report for `verify_workflow check-dsh-preset-compat`."""
    stream = sys.stdout if stream is None else stream
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    report = check_dsh_preset_compat()
    install = report["install"]
    isolation = report["isolation"]
    print("\n=== DSH Preset Schema Compat Check ===", file=stream)
    print(f"  Resolution plane: {install.get('source') or 'not discovered'}",
          file=stream)
    print(f"    resolved at: {install.get('node_modules') or '-'}", file=stream)
    for name, entry in sorted((install.get("oracle_packages") or {}).items()):
        print(f"    oracle: {name}@{entry.get('version') or '?'} "
              f"({entry.get('path') or '?'})", file=stream)
    cli = install.get("cli_package") or {}
    print(f"    @deepseek-ai/dsh CLI {cli.get('version') or '?'} "
          f"({cli.get('path') or '?'}) — informational only: a row's schema "
          f"comes from the oracle packages above, not from the CLI version",
          file=stream)
    print(f"  Compositions: {len(report['compositions'])}; "
          f"enabled rows: {report['rows_enabled']}; "
          f"schema-checked rows: {report['rows_checked']}", file=stream)
    print(f"  Isolated temp DSH_HOME: {isolation.get('temp_home') or '-'} "
          f"(writes: {isolation.get('home_writes')})", file=stream)
    for entry in report["compositions"]:
        print(f"  [{entry['status']}] {entry['path']} — "
              f"{entry['enabled']} enabled row(s), {entry['checked']} with a schema",
              file=stream)
        for row in entry["rows"]:
            if row.get("kind") in FINDING_KINDS:
                print(f"      [FAIL] {row.get('row')} ({row.get('name')}): "
                      f"{row.get('message')}", file=stream)
    if report["verdict"] == VERDICT_FAIL:
        print(f"\n  Result: FAILED — {report['reason']}", file=stream)
        for issue in report["issues"][:20]:
            print(f"    - {issue}", file=stream)
        if len(report["issues"]) > 20:
            print(f"    ... and {len(report['issues']) - 20} more", file=stream)
        if fail_on_issues:
            return 1
    elif report["verdict"] == VERDICT_NOT_RUN:
        # Optional-tooling policy: an unresolvable plugin set is disclosed,
        # never a green verdict and never a non-zero exit.
        print(f"\n  Result: NOT_RUN — {report['reason']}", file=stream)
    else:
        print(f"\n  Result: PASSED — {report['reason']}", file=stream)
        for detail in report["details"]:
            if "NOT verified" in detail:
                print(f"    [NOT_RUN] {detail}", file=stream)
    print(file=stream)
    return 0


def _print_human(report: dict, stream) -> None:
    install = report["install"]
    print(f"verdict: {report['verdict']}", file=stream)
    print(f"reason : {report['reason']}", file=stream)
    print(f"plane  : {install.get('source') or '-'}", file=stream)
    print(f"resolve: {install.get('node_modules') or '-'}", file=stream)
    cli = install.get("cli_package") or {}
    print(f"cli    : @deepseek-ai/dsh {cli.get('version') or '?'} "
          f"({cli.get('path') or '?'}) — informational, not the schema authority",
          file=stream)
    for name, entry in sorted((install.get("oracle_packages") or {}).items()):
        print(f"oracle : {name}@{entry.get('version') or '?'} "
              f"({entry.get('path') or '?'})", file=stream)
    print(f"node   : {install.get('node_version') or '?'}", file=stream)
    print(f"home   : {report['isolation'].get('temp_home') or '-'} "
          f"(writes: {report['isolation'].get('home_writes')})", file=stream)
    for other in install.get("other_planes") or []:
        print(f"  [plane] {other['plane']} — {other['node_modules']} — "
              f"{other['oracle_versions']}", file=stream)
    for entry in report["compositions"]:
        print(f"  [{entry['status']}] {entry['path']} — "
              f"{entry['enabled']} enabled row(s), {entry['checked']} with a schema",
              file=stream)
        for row in entry["rows"]:
            if row.get("kind") in FINDING_KINDS:
                print(f"      [FAIL] {row.get('row')} ({row.get('name')}): "
                      f"{row.get('message')}", file=stream)
    for issue in report["issues"]:
        print(f"issue  : {issue}", file=stream)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Standalone entry point: ``python dsh_compat.py [--root DIR] [PATH ...]``."""
    parser = argparse.ArgumentParser(
        prog="dsh_compat.py",
        description="Validate preset composition rows against the INSTALLED "
                    "dsh's own Config schemas (loader dialect, loader "
                    "evaluate, cordis resolveConfig).")
    parser.add_argument("paths", nargs="*", type=Path,
                        help="composition files; default: discover every "
                             "preset composition under --root")
    parser.add_argument("--root", type=Path, default=None,
                        help="package root (default: the repository this module ships in)")
    parser.add_argument("--json", action="store_true",
                        help="emit the machine-readable report on stdout")
    parser.add_argument("--timeout", type=int, default=DEFAULT_PROBE_TIMEOUT,
                        help=f"probe timeout in seconds (default {DEFAULT_PROBE_TIMEOUT})")
    parser.add_argument("--fail-on-issues", action="store_true",
                        help="exit 1 on FAIL (NOT_RUN exits 0 — optional-tooling policy)")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    root = args.root if args.root is not None else Path(__file__).resolve().parents[3]
    report = check_dsh_preset_compat(
        root=root,
        compositions=args.paths or None,
        timeout=args.timeout,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human(report, sys.stdout)
    if args.fail_on_issues and report["verdict"] == VERDICT_FAIL:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
