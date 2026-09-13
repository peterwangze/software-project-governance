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
``PASS``   at least one enabled row was validated against the resolved
           schemas, **and** every enabled row that could not be validated is
           disclosed (the ``coverage`` block, plus one ``[NOT_RUN]`` line per
           unverified row).
``FAIL``   a row's config was rejected (row id + module + the schema's exact
           message), a row's module could not be resolved, a ``!!js``
           expression threw, or a composition is not a valid entry list.
``NOT_RUN`` no node and/or no resolvable plugin set (with the reason), nothing
           could be verified, **or enabled rows exist but not one of them was
           compared against a schema** (``rows_checked == 0`` — e.g. every
           enabled row's module exports no ``Config``). ``NOT_RUN`` never counts
           as a gate issue — it discloses an unverified fact instead of
           inventing a green one. The second clause is the invariant behind
           ``coverage``: zero validated rows can never render as ``PASS``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
    "UNVERIFIED_KINDS",
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

#: Row diagnostics that mean "an **enabled** row's config was NOT verified by
#: any schema". They are **not** findings — the row may be perfectly valid —
#: but they must never be counted as validated either (design §4.4.1 G01-c /
#: §4.3 L3).
#:
#: The PASS branch of the render layer decides what to put on screen from this
#: set instead of from a substring of a message ("NOT verified"): that string
#: coupling is why five ``NO_SCHEMA`` rows could be unverified and invisible at
#: the same time (AUDIT-153 G-01④).
#:
#: * ``NO_SCHEMA`` — the module exports no ``Config``, so nothing to validate
#:   the row's config against. The message asserts nothing about what the
#:   loader then does with it (that behaviour is a separate, unverified fact).
#: * ``BUILTIN`` — a ``cordis:`` loader builtin: no module to import, hence no
#:   schema to apply.
#:
#: ``DISABLED_INHERITED`` is deliberately **absent**: such a row never starts
#: (its ancestor is disabled), so the probe does not count it in
#: ``entry.enabled`` either (`inherited_disabled` is its own counter, read from
#: `Entry._disabled`'s ancestor walk). Counting it here would put a row into
#: the trust surface that is not part of the enabled denominator, and the PASS
#: sentence would then contradict itself ("verified 1 of 1 … 1 enabled row(s)
#: NOT verified", F-01). Not started is not "we failed to check it" — and it
#: stays visible: the row keeps its `details` line and every surface reports
#: the `inherited-disabled rows:` count (plus the F4 "would mount nothing"
#: disclosure when nothing else is enabled).
UNVERIFIED_KINDS = (
    "NO_SCHEMA",
    "BUILTIN",
)

# ── the dsh host-dependency contract (single source of the host facts) ─────
# Design §2.5 C-3: every host literal this guard used to inline — the install
# scope / cli package / anchor, the two environment overrides, the profiles
# directory name, the `DSH_HOME` variable it reads, the composition file name and
# its globs, and the oracle packages with the symbols this guard calls them
# through — is declared in `adapters/dsh/host-contract.json`.
#
# The declared symbols are read from the contract at import (see
# `_declared`/the binding block below), so this module holds no copy of a host
# value. A contract that is missing, unreadable, malformed or of an unknown
# schema makes that read raise and the module fail to import its facts;
# `check_dsh_preset_compat()` maps the same failure to `NOT_RUN` (unreadable) or
# `FAIL` (malformed) per §2.5.1 instead of validating against an inlined copy.
#
# `PROBE_SCRIPT` likewise carries no package name and no symbol name of its own:
# both are injected into the probe request (see `_probe_request`).
#
# The oracle packages are the ones whose OWN code decides a row's fate, imported
# from the resolved plane, never re-implemented:
#   * `cordis-plugin-include` — the `!!js` YAML dialect (its entry-list schema)
#   * `cordis-plugin-loader`  — the `!!js` evaluate / isJsExpr pair
#   * `cordis`                — `resolveConfig`, the call that throws
#   * `js-yaml`               — the parser those schemas are loaded with
# Their versions are reported next to every verdict, because "which plugin set
# did this validate against" is part of the answer.
#
# A preset directory is a directory holding the declared composition file
# (`COMPOSITION_FILE` in the presets package); the shipped render source — the
# token template the two renderers substitute — must satisfy the same row
# contract as a mounted preset. FIX-310: the template now lives with the preset
# payload it renders; the composition globs are depth-agnostic.
#
# The declared symbols below are the *source* names of the facts; their values
# are read from the contract lazily (see `__getattr__` after `_declared`), so a
# contract defect surfaces as a verdict instead of an import-time traceback.
_DECLARED_BINDING = {
    "INSTALL_DIR_ENV": "host.install.env_overrides.install_dir",
    "NODE_MODULES_ENV": "host.install.env_overrides.node_modules",
    "DSH_SCOPE": "host.install.scope",
    "DSH_PACKAGE": "host.install.cli_package",
    "INSTALL_ANCHOR_REL": "host.install.anchor_rel",
    "ORACLE_PACKAGES": "host.apis",
    "DSH_HOME_ENV": "host.env.home_var",
    "PROFILES_DIR_NAME": "host.install.profiles_dir_name",
    "COMPOSITION_FILENAMES": "host.home.composition_file",
    "COMPOSITION_GLOBS": "host.home.composition_globs",
    "COMPAT_SECTION_TITLE": "own.checks.compat_section_title",
}

#: Sequence-shaped bindings: the contract field is a JSON array.
_SEQUENCE_FACTS = frozenset({"INSTALL_ANCHOR_REL", "COMPOSITION_GLOBS"})
#: Single-value bindings wrapped into the one-element tuple the guard uses.
_WRAPPED_FACTS = frozenset({"COMPOSITION_FILENAMES"})

_declared_cache: dict = {}

#: Short internal aliases for the declared symbols this module's own code reads.
#: In-module call sites use `_fact("<alias>")` because a bare global lookup does
#: **not** consult the module-level `__getattr__` below — only attribute access
#: does. Binding them eagerly at import would make any contract defect abort the
#: import, which is exactly the F-02 defect: the §2.5.1 three-state verdict
#: (`NOT_RUN` / `FAIL`) must stay reachable, and it is the *verdict* that reports
#: a bad contract. No inlined fallback is introduced: `_fact()` raises.
_FACT_ALIASES = {
    "_install_dir_env": "INSTALL_DIR_ENV",
    "_node_modules_env": "NODE_MODULES_ENV",
    "_scope": "DSH_SCOPE",
    "_cli_package": "DSH_PACKAGE",
    "_install_anchor_rel": "INSTALL_ANCHOR_REL",
    "_oracle_packages": "ORACLE_PACKAGES",
    "_home_env": "DSH_HOME_ENV",
    "_profiles_dir_name": "PROFILES_DIR_NAME",
    "_composition_filenames": "COMPOSITION_FILENAMES",
    "_composition_globs": "COMPOSITION_GLOBS",
    "_section_title": "COMPAT_SECTION_TITLE",
}


def _contract_value(name: str):
    """One declared dsh fact, read from the host contract (memoized per process).

    Raises the accessor's `ContractUnreadable` / `ContractMalformed` /
    `ContractSchemaUnknown` when the contract cannot supply the fact — the caller
    classifies that per design §2.5.1. There is no inlined fallback: a second
    copy of a host fact is the defect class this guard exists to catch.
    """
    if name in _declared_cache:
        return _declared_cache[name]
    import dsh_contract  # noqa: PLC0415 — sibling accessor, imported on first need

    value = dsh_contract.get(_DECLARED_BINDING[name])
    if name == "ORACLE_PACKAGES":
        # `host.apis` is the package → {exports, role} map; the declared order is
        # the order the probe reports them in.
        value = tuple(value)
    elif name in _SEQUENCE_FACTS:
        value = tuple(value)
    elif name in _WRAPPED_FACTS:
        value = (value,)
    _declared_cache[name] = value
    return value


def _fact(alias: str):
    """Resolve one of the short internal aliases (see `_FACT_ALIASES`)."""
    return _contract_value(_FACT_ALIASES[alias])


def __getattr__(name: str):
    """Resolve a declared symbol on first access (PEP 562 module attribute).

    Public compatibility surface only: code *inside* this module cannot rely on
    this hook (a bare global lookup does not consult it), so in-module call
    sites go through `_fact()` / `_contract_value()` directly. The names served
    here are exactly the ones outside callers already use —
    `dsh_compat.DSH_HOME_ENV`, `dsh_compat.INSTALL_DIR_ENV`, … — and a typo
    still raises `AttributeError` instead of resolving to something else.

    `CHECK_SECTION_TITLE` is the alias the render layer has always exported for
    `own.checks.compat_section_title`; the binding keeps the contract path.
    """
    if name == "CLI_PACKAGE":
        return "{0}/{1}".format(_fact("_scope"), _fact("_cli_package"))
    if name == "CHECK_SECTION_TITLE":
        return _contract_value("COMPAT_SECTION_TITLE")
    if name in _DECLARED_BINDING:
        return _contract_value(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def oracle_api_symbols() -> dict:
    """Oracle package → the exported symbols this guard calls it through.

    Declared in `host.apis[<package>].exports`. The probe imports exactly these
    names, so a symbol rename upstream becomes a contract change instead of a
    silent `undefined` at runtime. A declared package without an `exports` list
    is a contract defect and raises `ContractMalformed` (never a silent skip).
    """
    import dsh_contract  # noqa: PLC0415 — sibling accessor, imported on first need

    apis = dsh_contract.get("host.apis")
    symbols = {}
    for package, entry in apis.items():
        exports = entry.get("exports") if isinstance(entry, dict) else None
        if not isinstance(exports, list) or not exports:
            raise dsh_contract.ContractMalformed(
                f"ContractMalformed: `host.apis[{package}].exports` must be a "
                f"non-empty list (declared: {entry!r})")
        symbols[package] = tuple(exports)
    return symbols

_SKIP_DIRS = frozenset({".git", "node_modules", "__pycache__", ".venv", "venv",
                        ".pytest_cache", ".mypy_cache"})

#: Wall-clock budget for one probe run (it imports ~30 plugin packages).
DEFAULT_PROBE_TIMEOUT = 180

#: Probe-internal status meaning "the contract could not supply the probe facts".
#: Distinct from the default `NOT_RUN` on purpose (CODE R0 F-03): a contract
#: defect is a product failure and must never share a status with "the optional
#: tooling is unavailable", or a broken contract would read as an absent dsh.
PROBE_STATUS_CONTRACT_FAIL = "CONTRACT_FAIL"

#: Memo for `_contract_failure_types()`; `None` until resolved (or when the
#: accessor cannot be imported at all).
_CONTRACT_TYPES_CACHE = None


def _contract_failure_types():
    """The accessor's three failure classes, in its own vocabulary.

    Resolved on demand from the sibling module rather than restated here: design
    §2.5.1 fixes one vocabulary, and `dsh_contract` owns it (it is also the
    module that raises them).

    Returns `None` when the accessor itself cannot be imported. That matters
    because this function is called from an `except` clause — where its own
    failure would escape as a fresh traceback instead of a verdict — so it never
    raises: a missing accessor is reported as `NOT_RUN` by the caller.
    """
    global _CONTRACT_TYPES_CACHE
    if _CONTRACT_TYPES_CACHE is None:
        try:
            import dsh_contract  # noqa: PLC0415 — sibling accessor, on first need
        except ImportError:
            return None
        _CONTRACT_TYPES_CACHE = (dsh_contract.ContractUnreadable,
                                 dsh_contract.ContractMalformed,
                                 dsh_contract.ContractSchemaUnknown)
    return _CONTRACT_TYPES_CACHE


def _contract_failure_report(report: dict, exc: Exception) -> dict:
    """Classify a contract failure into the §2.5.1 verdict for this consumer.

    ``ContractUnreadable`` → ``NOT_RUN`` (the contract is not there; an
    environment fact, never a gate issue). ``ContractMalformed`` /
    ``ContractSchemaUnknown`` → ``FAIL`` (the contract is there and wrong; a
    product defect that MUST NOT be downgraded to `NOT_RUN`).
    """
    types = _contract_failure_types()
    if types is None:
        report["verdict"] = VERDICT_NOT_RUN
    else:
        unreadable, rest = types[0], tuple(types[1:])
        report["verdict"] = VERDICT_FAIL if isinstance(exc, rest) else VERDICT_NOT_RUN
    report["reason"] = f"{type(exc).__name__}: {exc}"
    report["details"].append(report["reason"])
    if report["verdict"] == VERDICT_FAIL:
        report["issues"] = [report["reason"]]
    return report


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

// Symbol names and package names are rendered in from the contract at request
// build time (design §2.5 C-3): this script names nothing of its own.
let entryListSchema, evaluate, isJsExpr, resolveConfig, yaml
try {
  yaml = await import(fileUrl('__YAML_PACKAGE__'))
  const include = await import(fileUrl('__INCLUDE_PACKAGE__'))
  const loader = await import(fileUrl('__LOADER_PACKAGE__'))
  const cordis = await import(fileUrl('__CORDIS_PACKAGE__'))
  entryListSchema = include.__ENTRY_LIST_SCHEMA__
  evaluate = loader.__EVALUATE__
  isJsExpr = loader.__IS_JS_EXPR__
  resolveConfig = cordis.__RESOLVE_CONFIG__
} catch (error) {
  fail(`installed harness API unavailable: ${error && error.name}: ${error && error.message}`)
}
for (const [name, value] of [['__ENTRY_LIST_SCHEMA__', entryListSchema],
                             ['__EVALUATE__', evaluate],
                             ['__IS_JS_EXPR__', isJsExpr],
                             ['__RESOLVE_CONFIG__', resolveConfig]]) {
  if (typeof value !== 'function' && typeof value !== 'object') {
    fail(`installed harness API is not callable: ${name}`)
  }
}
out.probe = { yaml: req.resolve('__YAML_PACKAGE__/package.json'),
              include: req.resolve('__INCLUDE_PACKAGE__/package.json'),
              loader: req.resolve('__LOADER_PACKAGE__/package.json'),
              cordis: req.resolve('__CORDIS_PACKAGE__/package.json') }

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
    // a `disabled: true` group never starts. The roster's own reader, a
    // composition-inventory helper in the host's own presets package
    // (`combineDisabled(outer, own)`), agrees: it "lets children inherit its
    // disabled".
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
      // G01-e: this text states only what was measured (the module exports no
      // `Config`, so this guard has nothing to validate the config against).
      // It must NOT claim what the loader then does with the config — "passes
      // it through unvalidated" is an unverified statement about loader
      // behaviour, not an observation of this run.
      entry.rows.push({ row: id, name, kind: 'NO_SCHEMA', message:
        "this guard cannot validate this row's config (the module exports no Config schema)" })
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
    anchor = _fact("_install_anchor_rel")
    return (path / anchor[0] / anchor[1] / anchor[2]).is_file()


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
    for name in _fact("_oracle_packages"):
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
    the CLI package, whose version string is a different
    fact entirely.

    Only an explicitly exported ``DSH_HOME`` is consulted — the guard never
    guesses ``~/.dsh`` — and the access is a read of ``profiles/`` only: nothing
    here is written, moved, or created. (The isolated-home witness does not
    prove this; it counts entries in the probe's own temp home, which is a
    different directory. The read-only claim rests on the code: every call in
    this function is ``iterdir``/``is_dir``/``read_text``.)
    """
    raw = _env_text(env, _fact("_home_env"))
    if not raw:
        return []
    profiles = Path(raw).expanduser() / _fact("_profiles_dir_name")
    planes = []
    try:
        children = sorted(profiles.iterdir())
    except OSError:
        children = []
    for child in children:
        candidate = child / "node_modules"
        if child.is_dir() and candidate.is_dir():
            planes.append((f"{_fact('_home_env')}/{_fact('_profiles_dir_name')}"
                           f"/{child.name}", candidate))
    fallback = profiles / "node_modules"
    if fallback.is_dir():
        planes.append((f"{_fact('_home_env')}/{_fact('_profiles_dir_name')}",
                       fallback))
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

    The ``CLI_PACKAGE`` CLI package version is reported for context only:
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
    for key in (_fact("_install_dir_env"), _fact("_node_modules_env")):
        raw = _env_text(env, key)
        if not raw:
            continue
        resolved = _from_env_override(raw)
        if resolved is None:
            result["reason"] = (
                f"{key}={raw!r} does not contain "
                f"{'/'.join(_fact('_install_anchor_rel'))} (checked the path itself and "
                f"its node_modules/); refusing to fall back to another install")
            result["source"] = f"${key} (invalid)"
            return result
        chosen, chosen_plane = resolved, f"${key}"
        break
    else:
        candidates = _profile_planes(env)
        for label, plane in candidates:
            if _package_version(plane, _fact("_oracle_packages")[0]) is not None \
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
                        f"carrying {'/'.join(_fact('_install_anchor_rel'))} "
                        f"was found above it")
                    result["source"] = "`dsh` on PATH (anchor not found)"
                    return result

    if chosen is None:
        install_dir_env = _fact("_install_dir_env")
        node_modules_env = _fact("_node_modules_env")
        result["reason"] = result["reason"] or (
            f"no dsh plugin set discovered: set ${install_dir_env} or "
            f"${node_modules_env}, or put `dsh` on PATH")
        return result

    result.update(status="OK", source=chosen_plane, plane=chosen_plane,
                  node_modules=str(chosen))
    install_anchor = _fact("_install_anchor_rel")
    cli_package_name = "{0}/{1}".format(_fact("_scope"), _fact("_cli_package"))
    package_json = chosen.joinpath(*install_anchor)
    result["dsh_package"] = str(package_json.parent) if package_json.is_file() else None
    cli = _package_version(chosen, cli_package_name)
    if cli is None:
        # A profile plane mirrors the INSTALLATION's dependencies; the CLI
        # package itself may legitimately live only in the install tree.
        for label, plane in _profile_planes(env):
            cli = _package_version(plane, cli_package_name)
            if cli is not None:
                break
    result["dsh_version"] = cli["version"] if cli else None
    result["cli_package"] = dict(cli or {"version": None, "path": None},
                                 note=("informational only — the installed CLI "
                                       "package version does not decide a row's "
                                       "schema; the oracle packages below do"))
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

    Covers both shipped forms: a mounted preset's own ``agent.cordis.yml`` and
    the render source ``*.cordis.yml.template`` (the same row contract, with
    the renderer's absolute path tokens substituted at sync time).
    """
    root = Path(root)
    found = []
    for pattern in _fact("_composition_globs"):
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if any(part in _SKIP_DIRS for part in relative.parts):
                continue
            found.append(path)
    return sorted(set(found), key=lambda item: item.relative_to(root).as_posix())


# ── the probe request: the contract-declared API facts, injected ────────────
def _probe_request(install: dict, compositions: Sequence[Path],
                   output: Path) -> dict:
    """Build the probe request, injecting the declared API facts.

    Every package name and every symbol name the probe calls comes from
    `host.apis`; the probe script itself carries none (design §2.5 C-3). Each
    role is resolved by the symbols its package must export — the YAML parser by
    `load`, the `!!js` dialect by `entryListSchema`, the loader by
    `evaluate`/`isJsExpr` and cordis by `resolveConfig` — so a contract
    reordering is a loud failure, never a silent `undefined`.
    """
    return {
        "nodeModules": install["node_modules"],
        "output": str(output),
        "files": [{"path": str(path)} for path in compositions],
    }


def _render_probe_script() -> str:
    """The probe script with the contract-declared names substituted in.

    The script is a module constant so its JS stays a readable artifact; the
    package and symbol names it calls are injected here, which keeps the "no
    host literal in the consumer" rule (K-2) satisfiable without hiding the
    names behind a second copy. An unresolved placeholder raises — a probe
    naming a package or a symbol we did not declare must not run.
    """
    apis = oracle_api_symbols()

    def package_exporting(*symbols: str) -> tuple:
        for package, exports in apis.items():
            if all(symbol in exports for symbol in symbols):
                return package, exports
        raise ValueError(
            "the contract's host.apis declares no package exporting "
            + "/".join(symbols) + " (declared: "
            + ", ".join(f"{name} -> {list(entry)}" for name, entry in sorted(apis.items()))
            + ")")

    def symbol_of(package: str, exports: tuple, *candidates: str) -> str:
        for symbol in candidates:
            if symbol in exports:
                return symbol
        raise ValueError(
            f"the contract declares no symbol {candidates[0]} for {package} "
            f"(declared: {list(exports)})")

    yaml_package, _ = package_exporting("load")
    include_package, include_exports = package_exporting("entryListSchema")
    loader_package, loader_exports = package_exporting("evaluate", "isJsExpr")
    cordis_package, cordis_exports = package_exporting("resolveConfig")

    replacements = {
        "__YAML_PACKAGE__": yaml_package,
        "__INCLUDE_PACKAGE__": include_package,
        "__LOADER_PACKAGE__": loader_package,
        "__CORDIS_PACKAGE__": cordis_package,
        "__ENTRY_LIST_SCHEMA__": symbol_of(include_package, include_exports,
                                           "entryListSchema"),
        "__EVALUATE__": symbol_of(loader_package, loader_exports, "evaluate"),
        "__IS_JS_EXPR__": symbol_of(loader_package, loader_exports, "isJsExpr"),
        "__RESOLVE_CONFIG__": symbol_of(cordis_package, cordis_exports,
                                        "resolveConfig"),
    }
    rendered = PROBE_SCRIPT
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    leftover = sorted(set(re.findall(r"__[A-Z0-9_]+__", rendered)))
    if leftover:
        raise ValueError(
            f"probe script placeholders not resolved: {leftover}")
    return rendered


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
                "<home-var>/<profiles-dir> probe still happen outside it). "
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
    try:
        request = _probe_request(install, compositions, output_path)
        script = _render_probe_script()
    except Exception as exc:  # noqa: BLE001 — classified, never a stack
        # The probe facts come from the contract (`host.apis` and the declared
        # composition/globs). A failure here is the contract failing to supply
        # them — a product defect, NOT an environment gap — so it gets its own
        # status instead of the ambient `NOT_RUN` it used to share (CODE R0 F-03).
        result["status"] = PROBE_STATUS_CONTRACT_FAIL
        result["reason"] = (
            f"the dsh host contract could not supply the probe facts: "
            f"{type(exc).__name__}: {exc} — this is a contract defect, not a "
            f"missing environment; repair the contract's `host.apis` entries "
            f"(each needs a non-empty `exports` list)")
        _remove_scratch_dir(scratch)
        _remove_scratch_dir(home)
        return result
    child_env = os.environ.copy()
    child_env[_fact("_home_env")] = str(home)
    try:
        completed = subprocess.run(
            [node, "--input-type=module", "--eval", script],
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
#: Max unverified-disclosure lines one surface prints before summarising the
#: remainder. One constant, so the three surfaces (Check 28v section, the
#: `check-dsh-preset-compat` CLI, `--json`-less human output) cannot drift apart
#: in either prefix or cap (F-08).
DISCLOSURE_LIMIT = 10


def emit_disclosures(report: dict, stream, *, prefix: str = "│  ",
                     indent: str = "│    ") -> None:
    """Print the report's unverified disclosure lines, uniformly (F-08).

    Called only under the verdicts that own a disclosure face: `PASS` (a
    partially verified run) and `NOT_RUN` (nothing verified). Under `FAIL` the
    findings are the screen's content; repeating the unverified rows there adds
    noise without changing the action.
    """
    lines = report.get("unverified") or []
    for line in lines[:DISCLOSURE_LIMIT]:
        print(f"{prefix}[NOT_RUN] {line}", file=stream)
    if len(lines) > DISCLOSURE_LIMIT:
        print(f"{indent}... and {len(lines) - DISCLOSURE_LIMIT} more unverified "
              f"item(s) — see the machine-readable report", file=stream)


def _informational_details(report: dict) -> list:
    """Detail lines about rows that were neither verified nor left unverified.

    A row that never STARTED (`DISABLED_INHERITED`) is not part of the trust
    surface — the probe counts it in `inherited_disabled`, not in `enabled` — so
    it carries no `[NOT_RUN]` disclosure. It must not vanish either (F-01): its
    own line is printed under the verdicts that show detail, next to the
    `inherited-disabled rows:` count every surface already reports.
    """
    lines = []
    for entry in report["compositions"]:
        for row in entry["rows"]:
            kind = row.get("kind")
            if kind in FINDING_KINDS or kind in UNVERIFIED_KINDS or kind == "PASS":
                continue
            lines.append(f"{entry['path']}: row \"{row.get('row')}\" "
                         f"({row.get('name') or 'unnamed'}) [{kind}] "
                         f"{row.get('message')}")
    return lines


def _unverified_disclosure(entry: dict, row: dict) -> str:
    """One on-screen line for a row that was NOT verified by any schema (L3).

    Structured (`kind in UNVERIFIED_KINDS`), never a substring test on the
    message: the message text is a wording choice, the kind is the fact.
    """
    kind = row.get("kind") or "UNKNOWN"
    name = row.get("name") or "unnamed"
    return (f'{entry["path"]}: row "{row.get("row")}" ({name}) '
            f"[{kind}] — NOT verified: {row.get('message')}")


def _reason_histogram(coverage: dict) -> str:
    """The `NO_SCHEMA=5, BUILTIN=2` tail of a verdict reason.

    File-level facts are deliberately not in this histogram (see the report
    skeleton in `check_dsh_preset_compat`), so the empty case says exactly that
    rather than implying a key.
    """
    reasons = coverage.get("unverified_reasons") or {}
    if not reasons:
        return "no unverified row"
    return ", ".join(f"{kind}={count}" for kind, count in sorted(reasons.items()))


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


def _aggregate_composition(item: dict, root: Path, report: dict,
                           coverage: dict) -> list:
    """Fold one probed composition into ``report``; return its findings.

    Row classification lives here so the verdict function stays a verdict
    function: `FINDING_KINDS` become findings, `UNVERIFIED_KINDS` become the
    disclosed unverified half of the trust surface, `PASS` becomes a detail
    line. The outcomes are disjoint by construction, which is what makes
    "every **enabled** row is accounted for exactly once" checkable (G01-b):
    ``rows_verified + rows_unverified == rows_enabled``, with the rows the walk
    could not evaluate (import failures, inherited-disabled) counted in neither
    half — the probe does not count them in ``enabled`` either.
    """
    failures = []
    entry = _composition_entry(item, root)
    report["compositions"].append(entry)
    report["rows_enabled"] += entry["enabled"]
    report["rows_checked"] += entry["checked"]
    report["rows_inherited_disabled"] += entry["inherited_disabled"]
    coverage["rows_enabled"] += entry["enabled"]
    coverage["rows_verified"] += entry["checked"]
    if entry["status"] == "UNREADABLE":
        # Not one row of this file could be read, so there is no enabled row to
        # account for (`rows_enabled` stays 0 — the probe cannot know how many
        # rows the file had). The composition itself is the unverified fact, and
        # it is disclosed on the same `unverified` channel the row-level
        # disclosures use, so every surface shows it (F-02).
        coverage["unreadable_compositions"] += 1
        line = (f"{entry['path']}: composition could not be read "
                f"({entry['error']}) — rows NOT verified")
        report["unverified"].append(line)
        report["details"].append(line)
        return failures
    if entry["status"] == "PARSE_ERROR":
        failures.append(
            f"{entry['path']}: not a valid entry list — {entry['error']}")
        return failures
    if entry["enabled"] == 0 and entry["inherited_disabled"] == 0:
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
        elif kind in UNVERIFIED_KINDS:
            # L3: an enabled row that no schema could check is disclosed on
            # BOTH faces — its own `[NOT_RUN]` line, and the
            # `unverified_reasons` histogram the verdict reasons quote.
            line = _unverified_disclosure(entry, row)
            report["unverified"].append(line)
            coverage["rows_unverified"] += 1
            coverage["unverified_reasons"][kind] = (
                coverage["unverified_reasons"].get(kind, 0) + 1)
            report["details"].append(line)
        elif kind == "PASS":
            report["details"].append(
                f"{entry['path']}: row \"{row.get('row')}\" {row.get('name')} OK")
        else:
            report["details"].append(
                f"{entry['path']}: row \"{row.get('row')}\" {row.get('name')} "
                f"[{kind}] {row.get('message')}")
    return failures


def _resolve_verdict(report: dict, failures: list, plane: str,
                     oracle_label: str) -> None:
    """Set ``verdict`` and ``reason`` on ``report`` (design §4.6 three states).

    The order of the branches is the contract, not an accident:

    1. a finding is `FAIL` — a rejected row is an actionable defect, and
       degrading it to "unverified" would trade one wrong verdict for another;
    2. nothing enabled (or nothing discovered) is `NOT_RUN`, with the cause
       named per composition state (unreadable file / all rows disabled /
       nothing discovered);
    3. **enabled rows but zero comparisons is `NOT_RUN`** (G01-a, L1) — a green
       verdict here is the exact defect this module exists to prevent;
    4. otherwise `PASS`, and only because at least one row really was compared;
       its sentence carries the denominator so a partially verified run cannot
       read as a fully verified one (G01-d).
    """
    coverage = report["coverage"]
    if failures:
        report["verdict"] = VERDICT_FAIL
        report["reason"] = (
            f"{len(failures)} preset composition row(s) rejected by the plugin "
            f"set resolved from {plane} ({oracle_label})")
    elif not report["compositions"] or report["rows_enabled"] == 0:
        report["verdict"] = VERDICT_NOT_RUN
        if not report["compositions"]:
            report["reason"] = (
                "no enabled preset row could be validated — nothing was "
                "verified (fail-closed: never reported as PASS)")
        elif coverage["unreadable_compositions"]:
            # F-06: nothing is enabled here because the composition could not
            # be READ, not because its rows are disabled. Asserting "every row
            # is disabled … would mount nothing" about a file we never opened
            # names the wrong cause; the read failure is the reason.
            report["reason"] = (
                f"no preset row could be validated — "
                f"{coverage['unreadable_compositions']} composition(s) could not "
                f"be read, so their rows were NOT verified: "
                + "; ".join(line for line in report["unverified"])
                + " (fail-closed: never reported as PASS)")
        else:
            # F4: every discovered row is disabled, so the preset mounts
            # nothing. Named explicitly instead of a generic "nothing
            # verified" — it is a user-visible outcome, not a tooling gap.
            report["reason"] = (
                f"no enabled preset row could be validated — every row of "
                f"{len(report['compositions'])} composition(s) is disabled "
                f"({report['rows_inherited_disabled']} inherited from a "
                f"disabled ancestor), so this preset would mount nothing")
    elif report["rows_checked"] == 0:
        report["verdict"] = VERDICT_NOT_RUN
        report["reason"] = (
            f"rows_verified 0 of {report['rows_enabled']} enabled row(s) — "
            f"NOT verified: no enabled row's config could be compared against "
            f"a schema ({_reason_histogram(coverage)}); fail-closed: a run that "
            f"verified nothing is never reported as PASS")
    else:
        report["verdict"] = VERDICT_PASS
        report["reason"] = (
            f"verified {report['rows_checked']} of {report['rows_enabled']} "
            f"enabled row(s) against the plugin set resolved from {plane} "
            f"({oracle_label}); {len(report['compositions'])} composition(s) "
            f"checked")
        if coverage["rows_unverified"]:
            report["reason"] += (
                f"; {coverage['rows_unverified']} enabled row(s) NOT verified "
                f"({_reason_histogram(coverage)}) — disclosed as [NOT_RUN]")


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
        # G01-b: the trust surface, made visible. `rows_verified` is the same
        # fact as `rows_checked` (kept for the two readers that already spell
        # it that way); the unverified half is what the verdicts below turn on.
        # `unverified_reasons` is a histogram **of rows**, so it never carries a
        # file-level key: an unreadable composition's row count is unknowable
        # (its probe entry reports `enabled: 0`), and a `UNREADABLE=0` bucket
        # would read as "no unreadable composition" (F-03). That fact has its
        # own counter instead.
        "coverage": {
            "rows_enabled": 0,
            "rows_verified": 0,
            "rows_unverified": 0,
            "unverified_reasons": {},
            "unreadable_compositions": 0,
        },
        # Disclosure lines shown as `[NOT_RUN]` by every output surface: one per
        # enabled row no schema could check, plus one per composition that could
        # not be read at all (F-02).
        "unverified": [],
    }

    # The declared facts are read inside this function's scope (through the
    # lazily-resolving accessors), and a contract that cannot supply them is a
    # verdict, not a crash (design §2.5.1, CODE R0 F-02/F-03):
    #
    #   * `ContractUnreadable` — the contract is absent or unreadable. That is
    #     an *environment* fact, so it degrades to `NOT_RUN`, which never counts
    #     as a gate issue.
    #   * `ContractMalformed` / `ContractSchemaUnknown` — the contract is present
    #     but wrong. That is a **product defect** and MUST NOT be downgraded to
    #     `NOT_RUN`, so it is reported as `FAIL`.
    #
    # Both messages carry the exception class plus the offending field/path, so
    # the remediation is actionable without a stack trace. The composition
    # discovery is inside the same try: it reads `host.home.composition_globs`,
    # which is a declared fact like any other.
    try:
        paths = ([Path(item) for item in compositions] if compositions is not None
                 else discover_compositions(root))
        paths = [path if path.is_absolute() else root / path for path in paths]
        if not paths:
            report["reason"] = (
                f"no preset composition found under {root.as_posix()} "
                f"(looked for {' and '.join(_fact('_composition_globs'))})")
            return report

        install_probe = (install if install is not None
                         else locate_dsh_install(env=env, which=which))
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
        if probe["status"] == PROBE_STATUS_CONTRACT_FAIL:
            # The contract itself could not supply the probe facts: a product
            # defect, never an environment gap (CODE R0 F-03).
            report["verdict"] = VERDICT_FAIL
            report["reason"] = probe["reason"]
            report["issues"] = [probe["reason"]]
            report["details"].append(probe["reason"])
            return report
    # `_contract_failure_types()` can raise nothing (it returns None when the
    # accessor module itself is missing), which matters here: a raise inside an
    # `except` clause escapes as a fresh traceback instead of a verdict.
    except Exception as exc:  # noqa: BLE001 — classified below
        return _contract_failure_report(report, exc)

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
        f"installed CLI package {cli.get('version') or '?'} "
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
    for item in payload.get("files") or []:
        failures.extend(_aggregate_composition(
            item, root, report, report["coverage"]))

    report["issues"] = failures
    plane = install_probe.get("source") or "unknown plane"
    oracle_label = ", ".join(
        f"{name}@{entry.get('version') or '?'}"
        for name, entry in sorted(
            (report["install"].get("oracle_packages") or {}).items()))
    _resolve_verdict(report, failures, plane, oracle_label)
    return report


# ── CLI ─────────────────────────────────────────────────────────────────────
# ── render layer (kept here, not in the engine) ─────────────────────────────
# The engine's own R4 ratchet states it outright: "orchestration output belongs
# to the render layer". Check 28v therefore contributes a banner/footer pair to
# `_run_full_engine_checks` and nothing else — every line of its body is
# rendered here, so adding the check does not grow the monolith's print surface.
# The section title is declared in the contract (`own.checks.compat_section_title`,
# bound at the top of this module) so the render face has one source too.


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
    title = _fact("_section_title")
    print(f"\n┌─ {title} {'─' * max(1, 60 - len(title))}┐",
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
    print(f"│    installed CLI {cli.get('version') or '?'} "
          f"(informational — a row's schema comes from the oracle packages "
          f"above, not from the CLI version)", file=stream)
    for other in install.get("other_planes") or []:
        print(f"│    other plane {other['plane']}: {other['node_modules']} "
              f"{other['oracle_versions']}", file=stream)
    print(f"│  compositions: {len(report['compositions'])}; "
          f"enabled rows: {report['rows_enabled']}; "
          f"schema-checked rows: {report['rows_checked']}; "
          f"NOT verified: {report['coverage']['rows_unverified']}; "
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
        # L2: a report that verified nothing renders as [NOT_RUN], never as
        # [PASS] — and the unverified items that produced that verdict are
        # listed underneath it instead of staying invisible.
        print(f"│  [NOT_RUN] {report['reason']}", file=stream)
        emit_disclosures(report, stream, prefix="│    ", indent="│    ")
        print("└──────────────────────────────────────────────────────┘", file=stream)
        return 0
    print(f"│  [PASS] {report['reason']}", file=stream)
    # G01-c (L3): the disclosure is driven by the structured `unverified` set,
    # not by a substring of a detail line (the old `if "NOT verified" in detail`
    # was the reason five NO_SCHEMA rows were unverified and invisible at once).
    # It carries one line per enabled row no schema could check **and** one per
    # composition that could not be read (F-02), so a partial PASS is never
    # silent about either.
    emit_disclosures(report, stream)
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
    print(f"    installed CLI {cli.get('version') or '?'} "
          f"({cli.get('path') or '?'}) — informational only: a row's schema "
          f"comes from the oracle packages above, not from the CLI version",
          file=stream)
    print(f"  Compositions: {len(report['compositions'])}; "
          f"enabled rows: {report['rows_enabled']}; "
          f"schema-checked rows: {report['rows_checked']}; "
          f"NOT verified: {report['coverage']['rows_unverified']}; "
          f"inherited-disabled rows: "
          f"{report.get('rows_inherited_disabled', 0)}", file=stream)
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
    for line in _informational_details(report):
        print(f"      [INFO] {line}", file=stream)
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
        emit_disclosures(report, stream, prefix="    ", indent="    ")
    else:
        print(f"\n  Result: PASSED — {report['reason']}", file=stream)
        # Same structured disclosure as `emit_check_section`: the items no
        # schema could check — and the compositions that could not be read —
        # are printed under this terminal verdict too, so neither is ever only
        # in the machine-readable report.
        emit_disclosures(report, stream, prefix="    ", indent="    ")
    print(file=stream)
    return 0


def _print_human(report: dict, stream) -> None:
    install = report["install"]
    print(f"verdict: {report['verdict']}", file=stream)
    print(f"reason : {report['reason']}", file=stream)
    print(f"plane  : {install.get('source') or '-'}", file=stream)
    print(f"resolve: {install.get('node_modules') or '-'}", file=stream)
    cli = install.get("cli_package") or {}
    print(f"cli    : {_fact('_scope')}/{_fact('_cli_package')} "
          f"{cli.get('version') or '?'} "
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
    # Same disclosure face as the two command surfaces, under the same verdicts:
    # an item no schema could check is named, so `verdict: PASS` with "18 with a
    # schema" can never be read as "all 23 were checked" (G01-c). Under FAIL the
    # findings above are the actionable content, exactly as in the other two
    # surfaces (F-08).
    if report["verdict"] in (VERDICT_PASS, VERDICT_NOT_RUN):
        emit_disclosures(report, stream)
    for line in _informational_details(report):
        print(f"  [INFO] {line}", file=stream)
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
