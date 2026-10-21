/**
 * software-project-governance — DSH host row.
 *
 * The bundle's `cordis.patch.yml` inserts exactly ONE row naming this package
 * (`- insert: [{ id: governance, name: '@peterwangze/software-project-governance-plugin' }]`).
 * This module is that row. It has two delivery paths, decided by host
 * capability and never by a version number (FEAT-102):
 *
 *   **native (default on a host that declares an agent-preset registry).**
 *   The row derives the governance preset from the host's OWN current base
 *   declaration (`lib/dsh-native/`): it appends exactly two content deltas —
 *   the governance persona body to the base persona prefix, and this package's
 *   two skill roots to the base `skill-filesystem` `customSkillDirs` — and
 *   registers the result through the public `agentPresets.register` service.
 *   Every host tool row, group, isolate realm and `!!js` expression is carried
 *   over verbatim, so a host upgrade that adds, renames or disables a tool
 *   propagates by itself and this package no longer breaks on it. Nothing is
 *   written to `$DSH_HOME`; unload is the registration's own disposer.
 *
 *   **legacy (a host that declares no registry row).** The row renders the
 *   package's preset payload into `$DSH_HOME/.agent-presets/governance/`, which
 *   is the model those hosts read. This path is the coupling the native path
 *   removes: it owns a full copy of the composition and only refreshes on this
 *   package's own version marker.
 *
 * Both paths share `agent-presets/governance/preset.yml` for display metadata
 * and the same `adapters/dsh/host-contract.json` facts (read lazily, never at
 * module load). The native persona body lives in
 * `agent-presets/governance/persona.md.template`; the legacy composition
 * template keeps its own rendered copy for hosts that require it, and a test
 * keeps the two in sync.
 *
 * Failure policy (both paths): warn-only. A failing row breaks the whole dsh
 * boot, a missing preset does not — so `apply()` never throws, and a host whose
 * declarations cannot be derived is left completely untouched instead of being
 * repaired with guesses.
 *
 * The legacy payload is `agent-presets/governance/`: the composition TEMPLATE
 * (`agent.cordis.yml.template`, carrying the `__GOVERNANCE_*__` tokens), the
 * display metadata (`preset.yml`) and the shared persona body
 * (`persona.md.template`). Rendering substitutes the package's ABSOLUTE paths
 * into the composition — the same token contract
 * `adapters/dsh/launch.py --install` implements, so both legacy writers emit
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
 * Architecture boundary — two faces, both forward-only (the host never names
 * this plugin; no vendor row is patched):
 *
 *   * **legacy explicit renderer** (DEC-187 I-1/I-2/I-3, 2026-09-12; narrowed by
 *     DEC-366 ②): publishes no service, registers no host-plane
 *     provider/tool/settings namespace and reads no host service. Its only
 *     effect is writing one user-owned directory inside `$DSH_HOME` — and it is
 *     **never the inserted row's effect**: only an explicit operator/test call
 *     (`launch.py --install` / a direct `ensurePreset()`) reaches it.
 *   * **native** (FEAT-102): consumes exactly two PUBLIC host services —
 *     `loader` (the composed entry tree, read-only) and `agentPresets`
 *     (registration only) — and publishes nothing. It owns one registration and
 *     releases it through the disposer the registry returns; it never mutates
 *     the base declaration, never writes `$DSH_HOME`, and never touches another
 *     preset. That is the minimum needed to inherit the host's current tool set
 *     instead of copying it.
 *
 * Why the explicit renderer targets the USER root: `$DSH_HOME/.agent-presets/`
 * is the first user-trust preset root (`dsh-agent-presets` `resolvedRoots`,
 * first root wins), so a rendered copy would show up as a custom preset with
 * delete and open-folder available. `dsh plugin remove` withdraws the bundle row
 * (it manages the profile's pnpm bundle layer and never the user preset root, so
 * it cannot delete a rendered copy — use the settings page or
 * `launch.py --uninstall` for that). Hosts on the native model do not read that
 * directory at all.
 *
 * Failure policy (both faces): warn-only. Nothing must ever throw out of
 * `apply()` — a throwing row breaks the whole dsh boot, which would be a much
 * worse outcome than a missing preset. The inserted row reports exactly one
 * warning naming the structured code of whatever made native delivery
 * impossible (e.g. `HOST_WITHOUT_REGISTRY`, `REGISTRY_ROW_DISABLED`,
 * `HOST_TREE_UNREADABLE`, `BASE_DUPLICATE`) and writes nothing; the explicit
 * renderer keeps its own warn-only contract for the calls that ask for it.
 *
 * Orphan staging trade-off (P7 safety over tidiness — REVIEW-FIX-313-CODE-R0
 * F4, registered by FIX-325): since V10 this row has NO automatic GC for
 * orphaned `governance.staging-*` directories. A hard crash (process kill,
 * power loss) between the staging create and the rename leaves that orphan
 * behind, and nothing ever deletes it — the pre-V10 prefix scan in the catch
 * block was the only cleaner an abandoned staging tree ever had, but it
 * matched by NAME, which is not proof of ownership, and it destroyed user
 * directories that merely carried the staging prefix. The trade-off is
 * deliberate and one-directional: a permanently accumulating orphan (bounded
 * by the failure frequency, at most a few MB of rendered preset) is the
 * cheaper defect; deleting an unprovable target is not acceptable. Manual
 * cleanup — or a future host-side GC that can itself prove ownership — is the
 * intended remedy; every ordinary failure short of a hard crash still removes
 * its own staging tree, and the circuit breaker never removes anything.
 *
 * @module @peterwangze/software-project-governance-plugin
 */

import { existsSync, mkdirSync, readdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { applyNative } from './dsh-native/bridge.js'

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
  // Line endings: both renderers fold `\r\n` to `\n` EXPLICITLY and leave an
  // isolated `\r` alone — the shared contract FIX-316 pinned when it closed
  // D-66 (this side always folded only `\r\n`; the Python side used to rely
  // on the text layer's universal newlines, which folded EVERY `\r`, so the
  // two delivery paths disagreed by every isolated CR in the template).
  // `launch.py` now reads the template with `newline=""` (translation
  // disabled) and applies the same explicit fold, so neither renderer depends
  // on the checkout's core.autocrlf setting, and the lone-CR parity of the
  // two paths is machine-checked by `test_dsh_adapter.py::
  // test_isolated_cr_template_renders_identically`.
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
 * **Explicit install face only (DEC-366 ②).** The inserted host row never calls
 * this function: its only delivery face is native registration, and every
 * native-unavailable state logs a warning and writes nothing. `ensurePreset`
 * remains exported for the explicit install path (`launch.py --install` mirrors
 * it, and the renderer tests drive it directly); an operator must redirect
 * `DSH_HOME` at an isolated directory to use it.
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
 * @param {object} ctx - Cordis context of the explicit caller.
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
  let staging = ''
  let stagingCreated = false
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
        + `(${CONTRACT_URL.href}); to see the exact error, redirect DSH_HOME to a `
        + 'temporary directory first and run `python adapters/dsh/launch.py --sync` '
        + 'there — in the real home the write side is refused before rendering')
      return outcome
    }
    const payload = layout
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
    // The staging directory must be PROVABLY ours before anything is allowed to
    // delete it (design §6.1 V10 / AUDIT-153). Ownership is established by the
    // create itself, not by the shape of the name:
    //
    //   * the name carries the run's own timestamp + 48 bits of entropy, so a
    //     collision with a pre-existing directory is in practice impossible;
    //   * the directory is then created NON-recursively, so a collision that
    //     does happen raises EEXIST instead of silently adopting a directory
    //     somebody else made. (The old code did the opposite — a recursive
    //     `mkdirSync`, after a `rmSync` of the same path — which both adopted
    //     and destroyed whatever happened to carry the name.)
    //   * `stagingCreated` is assigned only after that unconditional create
    //     returns, so the cleanup in the catch block can never address a
    //     directory this attempt did not itself create.
    //
    // A losing name is retried rather than deleted: what we cannot prove we
    // made, we do not touch (fail-safe direction, V10).
    for (let attempt = 0; attempt < 8 && !stagingCreated; attempt += 1) {
      staging = `${userDir}.staging-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
      try {
        mkdirSync(staging)
        stagingCreated = true
      } catch (existsError) {
        if (existsError?.code !== 'EEXIST') throw existsError
      }
    }
    if (!stagingCreated) {
      // Eight collisions in a row is not a bad draw, it is a directory that
      // cannot be created here. Report the actionable fact and leave every
      // existing directory exactly as it is.
      ctx?.logger?.warn(
        'software-project-governance: preset sync skipped — could not create a fresh staging '
        + `directory under ${dirname(staging)} (repeated EEXIST); no existing directory was removed`)
      return outcome
    }
    // Every file is written as explicit BYTES with an LF terminator, matching
    // `launch.py` and the declared `own.render.newline_policy` ("lf"). The
    // marker files used to be written as text, which let the platform's text
    // layer pick the line ending — so the same preset could carry two
    // conventions depending on which writer produced it.
    writeFileSync(join(staging, payload.file),
                  Buffer.from(text.replace(/\r\n/g, '\n'), 'utf8'))
    const metadata = readFileSync(join(pkgRoot, payload.dir, payload.metadataFile), 'utf8')
    writeFileSync(join(staging, payload.metadataFile),
                  Buffer.from(metadata.replace(/\r\n/g, '\n'), 'utf8'))
    writeFileSync(join(staging, bindings.markers.version),
                  Buffer.from(`${version}\n`, 'utf8'))
    writeFileSync(join(staging, bindings.markers.skillRoot),
                  Buffer.from(`${posixPath(pkgRoot)}\n`, 'utf8'))
    if (existsSync(userDir)) rmSync(userDir, { recursive: true, force: true })
    renameSync(staging, userDir)
    outcome.synced = true
    ctx?.logger?.info?.(`software-project-governance: agent preset synced to ${userDir} (v${version})`)
  } catch (error) {
    // Best-effort cleanup of the staging directory this attempt created (CODE
    // R0 F4): the rename may have failed after the staging tree was written.
    //
    // Design §6.1 V10 / AUDIT-153 — the cleanup may only ever address the ONE
    // directory this attempt proved it created (`stagingCreated` is set only by
    // the successful non-recursive `mkdirSync` above). The former implementation
    // instead enumerated the preset root and deleted every entry whose name
    // started with `<presetId>.staging-`: a name prefix is not proof of
    // ownership, so a user directory that merely carried that name was removed
    // along with the real staging tree — and when the failure happened before
    // the preset root was resolved it enumerated `dirname('.')`, i.e. the
    // process CWD, and deleted matching directories there. Neither branch had
    // any predicate standing between it and the filesystem.
    //
    // Fail-safe direction is keep, never delete: an undecidable target is left
    // alone and reported with the path the user has to remove by hand.
    //
    // Scope note (FIX-313(b)) — this self-removal is NOT the retired orphan
    // GC and does not soften the module-header trade-off above: it addresses
    // only the ordinary failure path, where THIS attempt provably created its
    // staging tree (`stagingCreated`) and then failed to promote it. The F4
    // trade-off (REVIEW-FIX-313-CODE-R0, registered by FIX-325) still stands
    // one door over: an orphan left by a HARD CRASH between the staging
    // create and the rename is never swept by this row, because no surviving
    // process can prove ownership — the two paths are deliberately different,
    // and nothing here enumerates or name-matches anything.
    try {
      if (stagingCreated) {
        rmSync(staging, { recursive: true, force: true })
      } else {
        ctx?.logger?.warn(
          'software-project-governance: preset sync failed before a staging directory of this '
          + `attempt existed; nothing was removed (${String(error)})`)
      }
    } catch (cleanupError) {
      // Deleting the tree did not complete. Never let cleanup throw (J-2), and
      // never fall back to a broader match: name the exact path still on disk.
      ctx?.logger?.warn(
        `software-project-governance: staging directory left behind at ${staging} `
        + `(${String(cleanupError)}); remove it manually if it persists`)
    }
    ctx?.logger?.warn(`software-project-governance: preset sync failed: ${String(error)}`)
  }
  return outcome
}

/**
 * The inserted host row.
 *
 * **Native only (DEC-366 ②).** When the composed profile declares a host-owned
 * agent-preset registry, the governance preset is derived from the host's
 * current base declaration and registered through the public service. In every
 * other case — no registry row, a disabled one, an unreadable composition tree,
 * an ambiguous/unmergeable declaration — the row logs ONE warning and returns.
 * It never renders the legacy user-root directory: writing a directory on a
 * host that may not read it was the coupling FEAT-102 removes, and doing it
 * silently hid the refusal (CODE R0 F1).
 *
 * The explicit renderer lives outside the row: `python adapters/dsh/launch.py
 * --install` (and the exported `ensurePreset()` for code that calls it
 * directly) writes into an explicitly redirected `DSH_HOME` only.
 *
 * @param {object} ctx - Cordis context.
 * @param {object} [config] - row config (`basePresetId` is honoured).
 */
export function apply(ctx, config) {
  let outcome = null
  try {
    outcome = applyNative(ctx, config, contractDocument)
  } catch (error) {
    // The bridge is not supposed to throw; if it ever does, the row still must
    // not take the host boot down (module contract).
    ctx?.logger?.warn?.(`software-project-governance: native preset bridge failed: ${String(error)}`)
  }
  if (outcome !== null && outcome.mode === 'native') return
  const code = (outcome !== null && outcome.code) || 'NATIVE_PATH_UNAVAILABLE'
  const message = (outcome !== null && outcome.message)
    || 'the native bridge reported no outcome'
  if (code === 'CONTRACT_WITHOUT_NATIVE_BLOCK') {
    // The contract is the actionable report (FX-JS-03): name it as such instead
    // of the generic bridge text, keep the diagnostic that reveals the exact
    // read error, and still write nothing (DEC-366 ②).
    ctx?.logger?.warn?.(
      'software-project-governance: agent preset not delivered — contract unreadable '
      + `or missing the native protocol block (${code}): ${message} — the row never `
      + 'renders a preset directory; to see the exact contract error, redirect DSH_HOME '
      + 'to an isolated directory and run `python adapters/dsh/launch.py --sync` there; '
      + 'a directory-model host needs an explicit `python adapters/dsh/launch.py '
      + '--install`',
    )
    return
  }
  ctx?.logger?.warn?.(
    `software-project-governance: agent preset not delivered (${code}): ${message} — `
    + 'the row never renders a preset directory; a directory-model host needs an '
    + 'explicit `python adapters/dsh/launch.py --install` with DSH_HOME redirected '
    + 'to an isolated directory',
  )
}
