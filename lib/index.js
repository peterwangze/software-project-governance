/**
 * software-project-governance — DSH host row.
 *
 * The bundle's `cordis.patch.yml` inserts exactly ONE row naming this package
 * (`- insert: [{ id: governance, name: '@peterwangze/software-project-governance-plugin' }]`).
 * This module is that row, and it has exactly one job:
 *
 *   `ensurePreset()` — render the package's preset payload into
 *   `$DSH_HOME/.agent-presets/governance/` so `dsh plugin add` alone gives the
 *   user a selectable preset, with no manual step.
 *
 * The payload is `agent-presets/governance/` and holds exactly two files: the
 * composition TEMPLATE (`agent.cordis.yml.template`, carrying the
 * `__GOVERNANCE_*__` tokens) and `preset.yml`. Rendering substitutes the
 * package's ABSOLUTE paths into the composition — the same token contract
 * `adapters/dsh/launch.py --install` implements, so both delivery paths write
 * byte-identical compositions:
 *
 *   __GOVERNANCE_SKILLS_ROOT__  <pkg>/skills
 *   __GOVERNANCE_SHIMS_ROOT__   <pkg>/adapters/dsh/skill-shims
 *   __GOVERNANCE_REPO_ROOT__    <pkg>
 *
 * Why render instead of shipping a pre-baked copy: this repository is one
 * shared core (`skills/`, `commands/`, `agents/`) with six thin adapters. A
 * copied `skills/` tree inside the preset would be a second source of the same
 * 231 files, and `customSkillDirs` entries are resolved against the dsh
 * process CWD (installed dsh: `dsh-skill-filesystem/lib/index.js`), so only
 * absolute paths are correct from a user-root preset directory anyway. With
 * absolute roots the rendered `<plugin_root>` IS the package root, so the
 * guidance the composition, the command shims and the project `AGENTS.md`
 * already carry stays literally true and no core prose changes.
 *
 * Architecture boundary (DEC-187 I-1/I-2/I-3 — verified 2026-09-12):
 * the plugin publishes NO service, registers NO host-plane provider, tool or
 * settings namespace, and reads NO host service. Its only effect is writing
 * one directory inside `$DSH_HOME` that the user owns, which is why the patch
 * layer can insert it without changing any pre-existing host row. The host
 * never learns that this plugin exists: the dependency is forward-only (the
 * bundle row names the plugin; the plugin names nothing in dsh).
 *
 * Why the preset lands in the USER root: `$DSH_HOME/.agent-presets/` is the
 * first user-trust preset root (`dsh-agent-presets` `resolvedRoots`, first
 * root wins), so the settings page shows it as a custom preset with delete and
 * open-folder available. `dsh plugin remove` withdraws the bundle row (it
 * manages the profile's pnpm bundle layer and never the user preset root, so
 * it cannot delete the rendered preset — use the settings page or
 * `launch.py --uninstall` for that); a subsequent boot with the row still
 * present re-renders the preset, so deleting it alone is not persistent.
 *
 * Failure policy: warn-only. A preset render failure must never throw out of
 * `apply()` — a throwing row breaks the whole dsh boot, which would be a much
 * worse outcome than a missing preset (the user can re-run
 * `python adapters/dsh/launch.py --install`).
 *
 * @module @peterwangze/software-project-governance-plugin
 */

import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

/** Package identity; the row id in `cordis.patch.yml` is the preset id. */
export const name = '@peterwangze/software-project-governance-plugin'

/** Agent-preset id — also the `$DSH_HOME/.agent-presets/<id>/` directory name. */
const PRESET_ID = 'governance'

/** Version marker inside the rendered preset; a match means "already current". */
const PRESET_MARKER = '.dsh-bundle-version'

/**
 * Plugin-home marker consumed by the shipped git hooks.
 *
 * `skills/software-project-governance/infra/hooks/*` resolve the workflow home
 * from `$DSH_HOME/.agent-presets/governance/skill-root.txt` (the hook's
 * `find_spg_home` candidate list) so an installed project hook self-upgrades
 * from this package after `git pull`.
 */
const SKILL_ROOT_MARKER = 'skill-root.txt'

/** Token → package-relative path, mirroring `adapters/dsh/launch.py`. */
const TOKEN_PATHS = {
  __GOVERNANCE_SKILLS_ROOT__: 'skills',
  __GOVERNANCE_SHIMS_ROOT__: join('adapters', 'dsh', 'skill-shims'),
  __GOVERNANCE_REPO_ROOT__: '',
}

/**
 * Resolve the DeepSeek Harness home.
 *
 * Mirrors `resolveDshHome()` from `@deepseek-ai/dsh-home-paths` (installed
 * dsh 0.1.5-rc.2, `lib/index.js`: explicit path > `$DSH_HOME` > `~/.dsh`; a
 * blank `$DSH_HOME` counts as unset). Deliberately inlined instead of
 * imported: this package declares no runtime dependency, so a module-load
 * failure can never take down the host's boot — the one failure mode a host
 * row must not have.
 *
 * @returns {string} absolute harness home path.
 */
function resolveDshHome() {
  const fromEnv = process.env.DSH_HOME
  const configured = typeof fromEnv === 'string' && fromEnv.trim().length > 0
    ? fromEnv.trim()
    : join(homedir(), '.dsh')
  if (configured === '~') return homedir()
  if (configured.startsWith('~/') || configured.startsWith('~\\')) {
    return resolve(join(homedir(), configured.slice(2)))
  }
  return resolve(configured)
}

/** Package root derived from this module's own URL (never the process cwd). */
function packageRoot() {
  // `new URL('..', fileUrl)` always ends in a separator; strip it so the
  // repo-root token renders exactly as `adapters/dsh/launch.py` renders it
  // (`Path.resolve()` has no trailing separator) — renderer parity is a
  // machine-checked contract, not an intention.
  return fileURLToPath(new URL('..', import.meta.url)).replace(/[\\/]+$/, '')
}

/** Forward-slash spelling of an absolute path (the composition is portable). */
function posixPath(value) {
  return value.replace(/\\/g, '/')
}

/** Package version, or `'0'` when package.json is unreadable. */
function packageVersion() {
  try {
    const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))
    return typeof pkg.version === 'string' ? pkg.version : '0'
  } catch {
    return '0'
  }
}

/**
 * Render the composition template with the package's absolute paths.
 *
 * Mirrors `adapters/dsh/launch.py`'s substitution exactly (same three tokens,
 * same target strings) so `dsh plugin add` and `--install` cannot disagree;
 * an unconsumed token is a hard error for the caller, never a silently wrong
 * skill root.
 *
 * @param {string} template - `agent.cordis.yml.template` content.
 * @param {string} pkgRoot - absolute package root.
 * @returns {{text: string, leftovers: string[]}} rendered text + unresolved tokens.
 */
export function renderComposition(template, pkgRoot) {
  // Line endings are normalized to LF first: the renderer must be independent
  // of the checkout's core.autocrlf setting, otherwise this path and
  // `launch.py` (whose Python text-mode read normalizes to LF) would write
  // compositions that differ by every newline.
  let text = template.replace(/\r\n/g, '\n')
  for (const [token, relative] of Object.entries(TOKEN_PATHS)) {
    // `relative === ''` means the package root itself — `join(root, '')` would
    // append a separator and break parity with the Python renderer.
    const value = posixPath(relative === '' ? pkgRoot : join(pkgRoot, relative))
    text = text.split(token).join(value)
  }
  const leftovers = Object.keys(TOKEN_PATHS).filter((token) => text.includes(token))
  return { text, leftovers }
}

/**
 * Sync the rendered preset into the user preset root (idempotent).
 *
 * Idempotence is version-marker based: when the destination exists and its
 * `.dsh-bundle-version` equals this package's version, nothing is written. On
 * an upgrade the whole directory is rebuilt through a staging directory +
 * `rename`, so a crash mid-sync can never leave a half-rendered preset that
 * would break every governance session.
 *
 * Warn-only by contract: every failure is reported through `ctx.logger` and
 * swallowed (see the module header).
 *
 * @param {object} ctx - Cordis context of the inserted row.
 * @returns {{synced: boolean, dir: string, version: string}} observable outcome.
 */
export function ensurePreset(ctx) {
  // Everything — including `resolveDshHome()`, which reads `homedir()` and can
  // throw (node `uv_os_homedir ENOENT`) when HOME/USERPROFILE/DSH_HOME are all
  // unset — lives inside the try: the module's contract is that `apply()` can
  // never throw, because a throwing host row takes down the whole dsh boot,
  // which is far worse than a missing preset (CODE R0 F2, 2026-09-12).
  // `ctx?.logger` likewise guards the catch itself when the row is called
  // without a Cordis context.
  const version = packageVersion()
  let userDir = ''
  const outcome = { synced: false, dir: '', version }
  try {
    userDir = join(resolveDshHome(), '.agent-presets', PRESET_ID)
    outcome.dir = userDir
    const pkgRoot = packageRoot()
    const payload = join(pkgRoot, 'agent-presets', PRESET_ID)
    const templatePath = join(payload, 'agent.cordis.yml.template')
    if (!existsSync(templatePath) || !existsSync(join(payload, 'preset.yml'))) {
      ctx?.logger?.warn(`software-project-governance: in-package preset payload incomplete at ${payload}; skipped`)
      return outcome
    }
    const markerPath = join(userDir, PRESET_MARKER)
    let current = ''
    try {
      current = readFileSync(markerPath, 'utf8').trim()
    } catch { /* no marker = first install */ }
    if (existsSync(userDir) && current === version) return outcome

    const { text, leftovers } = renderComposition(readFileSync(templatePath, 'utf8'), pkgRoot)
    if (leftovers.length > 0) {
      ctx?.logger?.warn(
        `software-project-governance: preset render left unresolved token(s) ${leftovers.join(', ')}; skipped`)
      return outcome
    }

    mkdirSync(join(resolveDshHome(), '.agent-presets'), { recursive: true })
    const staging = `${userDir}.staging-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    rmSync(staging, { recursive: true, force: true })
    mkdirSync(staging, { recursive: true })
    writeFileSync(join(staging, 'agent.cordis.yml'), text, 'utf8')
    cpSync(join(payload, 'preset.yml'), join(staging, 'preset.yml'))
    writeFileSync(join(staging, PRESET_MARKER), `${version}\n`, 'utf8')
    writeFileSync(join(staging, SKILL_ROOT_MARKER), `${posixPath(pkgRoot)}\n`, 'utf8')
    if (existsSync(userDir)) rmSync(userDir, { recursive: true, force: true })
    renameSync(staging, userDir)
    outcome.synced = true
    ctx?.logger?.info?.(`software-project-governance: agent preset synced to ${userDir} (v${version})`)
  } catch (error) {
    // Best-effort cleanup of our own staging directory (CODE R0 F4): the
    // rename may have failed after the staging tree was written.
    try {
      for (const entry of readdirSync(dirname(outcome.dir || '.'))) {
        if (entry.startsWith(`${PRESET_ID}.staging-`)) {
          rmSync(join(dirname(outcome.dir), entry), { recursive: true, force: true })
        }
      }
    } catch { /* nothing to clean up — never let cleanup throw */ }
    ctx?.logger?.warn(`software-project-governance: preset sync failed: ${String(error)}`)
  }
  return outcome
}

/**
 * The inserted host row.
 *
 * @param {object} ctx - Cordis context.
 */
export function apply(ctx) {
  ensurePreset(ctx)
}
