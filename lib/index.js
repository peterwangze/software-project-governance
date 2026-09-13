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

// ── the host-dependency contract (single source of the dsh facts) ───────────
//
// `adapters/dsh/host-contract.json` is the ONE machine-readable source of the
// dsh facts this plugin consumes (design §2.5 C-1). Every literal this row
// would otherwise inline — the preset id, the marker file names, the render
// token table, the `$DSH_HOME` environment variable name, the `.agent-presets`
// root and its `~/.dsh` fallback — is read from it here. There is deliberately
// NO inlined fallback copy (J-4): a second copy is a second source of truth.
//
// Two structural rules of that migration:
//
//   * **top-level zero I/O (J-3)** — the contract is read lazily, from
//     `contractBindings()`, which is called inside `ensurePreset()` and inside
//     `renderComposition()` only. A module-level read would turn "the package
//     is missing one file" into "the host row fails to import", and a failing
//     import takes down the whole dsh boot.
//   * **memoized read** — one process reads the contract at most once. The only
//     two read points are the two functions the test suite calls directly
//     (`test_dsh_adapter.py` calls `renderComposition(template, pkgRoot)`), so
//     the token table must be available there.
//
// Failure policy is `contractBindings()`'s: any read/parse/validation failure
// degrades to an empty binding set and is reported by the caller through
// `ctx.logger.warn` — it is never thrown (J-2).

/**
 * Package identity; the row id in `cordis.patch.yml` is the preset id.
 *
 * The literal is the traceability anchor `test_dsh_contract.py` compares
 * against `own.package.name`; the contract is the source of the value it
 * stands for.
 */
export const name = '@peterwangze/software-project-governance-plugin'

/**
 * Declared dsh/protocol literals and the contract binding each one resolves.
 *
 * The values are never hard-coded here: `own.preset.id`,
 * `host.home.user_preset_dir`, `host.env.home_var`, the path segments of
 * `host.env.write_side.fallback`, `own.preset.version_marker`,
 * `own.preset.skill_root_marker`, `own.render.tokens` and
 * `own.render.leftover_scan` are all read from the contract at call time.
 */
const CONTRACT_BINDING = {
  presetId: 'own.preset.id',
  presetDir: 'host.home.user_preset_dir',
  homeVar: 'host.env.home_var',
  homeFallback: 'host.env.write_side.fallback',
  versionMarker: 'own.preset.version_marker',
  skillRootMarker: 'own.preset.skill_root_marker',
  tokens: 'own.render.tokens',
  leftoverScan: 'own.render.leftover_scan',
}

/** Contract URL, derived from this module's own URL (never the process cwd).
 *  `lib/index.js` → package root is one level up, so `../` repeats it. */
const CONTRACT_URL = new URL('../adapters/dsh/host-contract.json', import.meta.url)

/** The trailing path segment of a contract path expression (`<home>/.dsh`). */
const PATH_SEGMENT_RE = /[^\\/]+$/

/** Token names, kept as the declared symbols of the shared render contract. */
const SKILLS_TOKEN = '__GOVERNANCE_SKILLS_ROOT__'
const SHIMS_TOKEN = '__GOVERNANCE_SHIMS_ROOT__'
const REPO_TOKEN = '__GOVERNANCE_REPO_ROOT__'

/** Memoized contract view; the empty view means "no binding could be read".
 *  `null` only before the first read — the memo keeps one process at one read,
 *  and a failed read is not retried on every boot step. */
let bindingsCache = null

/** Parsed contract document; `undefined` = not attempted, `null` = unreadable. */
let contractCache

/**
 * The degraded contract view: no token is substituted, and the leftover scan is
 * the conservative catch-all. Every template token is therefore reported as an
 * unresolved leftover by `renderComposition()` — which is exactly the J-3
 * failure semantics this module promises — and `ensurePreset()` sees a
 * non-empty leftover list and skips the sync instead of throwing.
 *
 * The scan is a RegExp, never `null`: `String.prototype.match(null)` throws a
 * `TypeError`, which would escape `renderComposition()` and degrade
 * `ensurePreset()`'s actionable "contract unreadable" warning into a generic
 * "preset sync failed: TypeError" (CODE R0 F-01). The pattern is assembled
 * rather than written out so `own.render.leftover_scan` stays the only copy of
 * the declared expression.
 */
const EMPTY_BINDINGS = {
  presetId: '',
  presetDir: '',
  homeVar: '',
  homeFallbackName: '',
  markers: { version: '', skillRoot: '' },
  tokens: [],
  leftoverScan: new RegExp('__' + '[A-Za-z0-9_]+' + '__', 'g'),
}

/** The declared payload sub-directories, resolved as one dotted path per
 *  segment so `own.preset.payload_dir` stays the only place the names live. */
const PAYLOAD_ROOT_BINDING = [
  ['_payload', 'own.preset.payload_dir'],
  ['_template', 'own.preset.template'],
  ['_metadata', 'own.preset.metadata'],
]

/**
 * The declared payload layout **as separate values** (`own.preset.payload_dir`
 * → directory segments, `own.preset.template` → render-source name,
 * `own.preset.metadata` → metadata name, `own.package.name` → package name).
 *
 * Kept as individual references, not as a pre-joined path, because the caller
 * needs the raw segments twice: once to locate the payload before reading the
 * contract (the "payload absent" report must not depend on the contract), and
 * once to derive the names written into the preset.
 */
function contractPayloadLayout() {
  const contract = contractDocument()
  if (contract === null) return null
  const declared = {}
  for (const [key, path] of PAYLOAD_ROOT_BINDING) declared[key] = contractAt(contract, path)
  for (const value of Object.values(declared)) {
    if (typeof value !== 'string' || value === '') return null
  }
  const segments = declared._payload.replace(/\\/g, '/').split('/').filter(Boolean)
  const templateSegments = declared._template.replace(/\\/g, '/').split('/').filter(Boolean)
  const metadataSegments = declared._metadata.replace(/\\/g, '/').split('/').filter(Boolean)
  if (segments.length === 0 || templateSegments.length < 2) return null
  if (metadataSegments.length < 2) return null
  if (templateSegments.slice(0, -1).join('/') !== segments.join('/')) return null
  if (metadataSegments.slice(0, -1).join('/') !== segments.join('/')) return null
  const templateFile = templateSegments[templateSegments.length - 1]
  return {
    presetId: segments[segments.length - 1],
    dir: join(...segments),
    // `templateFile` is the shipped render source inside the payload;
    // `file` is the mounted composition name. The template carries the
    // render-source suffix, the mounted file does not (both declared —
    // `own.preset.template` vs `host.home.composition_file`).
    templateFile,
    file: templateFile.replace(/\.template$/, ''),
    metadataFile: metadataSegments[metadataSegments.length - 1],
  }
}

/** Parse the contract once per process; `null` when it cannot be read.
 *
 *  `schema_version` is checked here (CODE R0 F-16): design §2.5.1 makes an
 *  unsupported version fail-closed for *every* consumer, and the JS row is one
 *  of them. An unknown version is treated exactly like an unreadable contract —
 *  no binding is handed out, and the row never guesses at the old shape.
 *  `OWN_SCHEMA_VERSION` mirrors `dsh_contract.SUPPORTED_SCHEMA_VERSIONS`, which
 *  is a closed set; the JSON accessor's K-1/`test_dsh_contract.py` self-check is
 *  what keeps the two spellings in step.
 */
const OWN_SCHEMA_VERSION = 1

function contractDocument() {
  if (contractCache === undefined) {
    contractCache = null
    try {
      const parsed = JSON.parse(readFileSync(CONTRACT_URL, 'utf8'))
      if (parsed !== null && typeof parsed === 'object'
          && parsed.schema_version === OWN_SCHEMA_VERSION) {
        contractCache = parsed
      }
    } catch {
      contractCache = null
    }
  }
  return contractCache
}

/**
 * Read the host-dependency contract (J-3 memoized, warn-only).
 *
 * Returns :data:`EMPTY_BINDINGS` when the contract is missing, unreadable, not
 * JSON, not an object, or leaves one of the bindings undeclared. The caller
 * warns and skips the sync, so `apply()` can still never throw (J-2); an empty
 * binding set is the honest answer, while an inlined fallback copy would be a
 * second source of truth (J-4).
 *
 * @returns {{presetId: string, presetDir: string, homeVar: string,
 *            homeFallbackName: string, markers: {version: string, skillRoot: string},
 *            tokens: Array<[string, string]>, leftoverScan: RegExp|null}}
 */
function contractBindings() {
  if (bindingsCache !== null) return bindingsCache
  const contract = contractDocument()
  if (contract === null) return EMPTY_BINDINGS
  const declared = {}
  for (const [key, path] of Object.entries(CONTRACT_BINDING)) declared[key] = contractAt(contract, path)
  const fallbackName = typeof declared.homeFallback === 'string'
    ? (declared.homeFallback.match(PATH_SEGMENT_RE) || [''])[0]
    : ''
  if (typeof declared.presetId !== 'string' || declared.presetId === '') return EMPTY_BINDINGS
  if (typeof declared.presetDir !== 'string' || declared.presetDir === '') return EMPTY_BINDINGS
  if (typeof declared.homeVar !== 'string' || declared.homeVar === '') return EMPTY_BINDINGS
  if (fallbackName === '') return EMPTY_BINDINGS
  if (typeof declared.versionMarker !== 'string' || declared.versionMarker === '') return EMPTY_BINDINGS
  if (typeof declared.skillRootMarker !== 'string' || declared.skillRootMarker === '') return EMPTY_BINDINGS
  if (declared.tokens === null || typeof declared.tokens !== 'object') return EMPTY_BINDINGS
  const tokens = []
  for (const [token, relative] of Object.entries(declared.tokens)) {
    if (typeof relative !== 'string') return EMPTY_BINDINGS
    tokens.push([token, relative])
  }
  if (tokens.length === 0) return EMPTY_BINDINGS
  const leftoverScan = typeof declared.leftoverScan === 'string' && declared.leftoverScan !== ''
    ? new RegExp(declared.leftoverScan, 'g')
    // No declared scan (unreachable for a valid contract): a conservative
    // catch-all for anything shaped like a token, assembled here rather than
    // restated as a literal so the declared pattern stays the only copy.
    : new RegExp('__' + '[A-Za-z0-9_]+' + '__', 'g')
  bindingsCache = {
    presetId: declared.presetId,
    presetDir: declared.presetDir,
    homeVar: declared.homeVar,
    homeFallbackName: fallbackName,
    markers: { version: declared.versionMarker, skillRoot: declared.skillRootMarker },
    tokens,
    leftoverScan,
  }
  return bindingsCache
}

/** Dotted / `[key]` contract path lookup; `undefined` when not declared. */
function contractAt(contract, path) {
  let node = contract
  for (const key of path.split('.')) {
    if (node === null || typeof node !== 'object') return undefined
    node = node[key]
  }
  return node
}

/**
 * Resolve the DeepSeek Harness home.
 *
 * Mirrors `resolveDshHome()` from the host's own home-paths helper (explicit
 * path > `$DSH_HOME` > `~/.dsh`; a blank `$DSH_HOME` counts as unset) — the
 * variable name, the blank policy, the tilde forms and the fallback segment all
 * come from `host.env.*`, so this resolution cannot drift from the contract.
 * Deliberately inlined instead of imported: this package declares no runtime
 * dependency, so a module-load failure can never take down the host's boot —
 * the one failure mode a host row must not have.
 *
 * @param {{homeVar: string, homeFallbackName: string, markers: object}} bindings
 * @returns {string} absolute harness home path.
 */
function resolveDshHome(bindings) {
  const fromEnv = process.env[bindings.homeVar]
  const configured = typeof fromEnv === 'string' && fromEnv.trim().length > 0
    ? fromEnv.trim()
    : join(homedir(), bindings.homeFallbackName)
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
 * Mirrors `adapters/dsh/launch.py`'s substitution exactly (the same token set,
 * same target strings, both read from `own.render.tokens`) so `dsh plugin add`
 * and `--install` cannot disagree; an unconsumed token is a hard error for the
 * caller, never a silently wrong skill root. The leftover scan is the declared
 * `own.render.leftover_scan` pattern, so a token this renderer does not know
 * (a misspelling in the template) is reported too, not silently left behind.
 *
 * The contract is read here as well as in `ensurePreset()` because this
 * function is a public export the test suite calls directly (J-3). A contract
 * that cannot be read yields the empty binding set: **no** token is substituted
 * and **every** `__…__` token in the template is reported as a leftover — so an
 * unreadable contract never produces a composition that looks renderable, and
 * the caller skips the sync instead of writing a broken preset. Nothing is
 * thrown (design §2.6 J-3, regression `FX-JS-03`).
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
  const bindings = contractBindings()
  for (const [token, relative] of (bindings && bindings.tokens) || []) {
    // `relative === ''` means the package root itself — `join(root, '')` would
    // append a separator and break parity with the Python renderer.
    const value = posixPath(relative === '' ? pkgRoot : join(pkgRoot, relative))
    text = text.split(token).join(value)
  }
  // The declared scan catches mixed-case misspellings (`__Governance_Repo_Root__`)
  // that a fixed known-token list cannot see. Deduplicated (CODE R0 F-17): the
  // scan is global, so a token appearing twice would otherwise be named twice in
  // the warning and in the returned `leftovers`.
  const leftovers = [...new Set(text.match(bindings.leftoverScan) || [])]
  return { text, leftovers }
}

/**
 * Sync the rendered preset into the user preset root (idempotent).
 *
 * Idempotence is version-marker based: when the destination exists and its
 * contract-declared version marker (`own.preset.version_marker`) equals this
 * package's version, nothing is written. On an upgrade the whole directory is
 * rebuilt through a staging directory + `rename`, so a crash mid-sync can never
 * leave a half-rendered preset that would break every governance session.
 *
 * Warn-only by contract: every failure is reported through `ctx.logger` and
 * swallowed (see the module header).
 *
 * @param {object} ctx - Cordis context of the inserted row.
 * @returns {{synced: boolean, dir: string, version: string}} observable outcome.
 */
export function ensurePreset(ctx) {
  // Everything — including the contract read and `resolveDshHome()`, which
  // reads `homedir()` and can throw (node `uv_os_homedir ENOENT`) when
  // HOME/USERPROFILE/DSH_HOME are all unset — lives inside the try: the
  // module's contract is that `apply()` can never throw, because a throwing
  // host row takes down the whole dsh boot, which is far worse than a missing
  // preset (CODE R0 F2, 2026-09-12).
  // `ctx?.logger` likewise guards the catch itself when the row is called
  // without a Cordis context.
  const version = packageVersion()
  let userDir = ''
  let presetId = ''
  const outcome = { synced: false, dir: '', version }
  try {
    // Order matters here, and it is the order the original row used.
    //
    // `contractPayloadLayout()` resolves `own.preset.payload_dir` against this
    // *package's* root, so an installed copy whose payload was left out of the
    // tarball is detected first — and that report does not depend on the
    // contract being present next to that copy. Reporting "contract unreadable"
    // for a package that simply shipped without its payload would be a
    // misattribution, and it is exactly the failure the original check named.
    const layout = contractPayloadLayout()
    let payloadIncomplete = false
    let payloadRoot = ''
    if (layout !== null) {
      payloadRoot = join(packageRoot(), layout.dir)
      const payloadNames = new Set()
      try {
        for (const entry of readdirSync(payloadRoot)) payloadNames.add(entry)
      } catch { /* an unreadable payload directory IS an incomplete payload */ }
      payloadIncomplete = !payloadNames.has(layout.templateFile)
        || !payloadNames.has(layout.metadataFile)
    }
    const bindings = contractBindings()
    if (payloadIncomplete) {
      ctx?.logger?.warn(`software-project-governance: in-package preset payload incomplete at ${payloadRoot}; skipped`)
      return outcome
    }
    if (layout === null || bindings.homeVar === '') {
      // Warn-only, and no inlined fallback: without the contract the preset id,
      // the preset root and the marker names are unknown, so a sync would write
      // a guessed directory. Skip and say so (J-4).
      outcome.contract = 'unreadable'
      ctx?.logger?.warn(
        'software-project-governance: dsh host contract unreadable — preset sync skipped '
        + `(${CONTRACT_URL.href}); run \`python adapters/dsh/launch.py --sync\` to see the exact error`)
      return outcome
    }
    const payload = layout
    presetId = payload.presetId
    const pkgRoot = packageRoot()
    const templatePath = join(pkgRoot, payload.dir, payload.templateFile)
    userDir = join(resolveDshHome(bindings), bindings.presetDir, bindings.presetId)
    outcome.dir = userDir
    const markerPath = join(userDir, bindings.markers.version)
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

    mkdirSync(join(resolveDshHome(bindings), bindings.presetDir), { recursive: true })
    const staging = `${userDir}.staging-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    rmSync(staging, { recursive: true, force: true })
    mkdirSync(staging, { recursive: true })
    writeFileSync(join(staging, payload.file), text, 'utf8')
    cpSync(join(pkgRoot, payload.dir, payload.metadataFile),
           join(staging, payload.metadataFile))
    writeFileSync(join(staging, bindings.markers.version), `${version}\n`, 'utf8')
    writeFileSync(join(staging, bindings.markers.skillRoot), `${posixPath(pkgRoot)}\n`, 'utf8')
    if (existsSync(userDir)) rmSync(userDir, { recursive: true, force: true })
    renameSync(staging, userDir)
    outcome.synced = true
    ctx?.logger?.info?.(`software-project-governance: agent preset synced to ${userDir} (v${version})`)
  } catch (error) {
    // Best-effort cleanup of our own staging directory (CODE R0 F4): the
    // rename may have failed after the staging tree was written.
    try {
      const stagingPrefix = presetId ? `${presetId}.staging-` : ''
      for (const entry of readdirSync(dirname(outcome.dir || '.'))) {
        if (stagingPrefix && entry.startsWith(stagingPrefix)) {
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
