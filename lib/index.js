/**
 * software-project-governance — DSH host row.
 *
 * Registers the governance preset from the host's current base declaration,
 * plus the host integrations requested by the workflow. Preset delivery uses
 * the public registry. If the declaration cannot be used, the row warns once
 * and leaves the preset directory untouched. See adapters/dsh/README.md.
 *
 * The explicit directory installer derives its rows from the selected host's
 * base preset. The deprecated ensurePreset() export reports the CLI entry.
 *
 * @module @peterwangze/software-project-governance-plugin
 */

import { readFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join, resolve } from 'node:path'

import { applyNative } from './dsh-native/bridge.js'
import { registerEnforcementGuard } from './dsh-native/guard.js'
import { registerGoalAdmission } from './dsh-native/goal-admission.js'
import { createGoalTreeBudget } from './dsh-native/goal-tree-budget.js'
import { deliveryPreflightServices, registerDeliveryPreflight } from './dsh-native/delivery-preflight.js'

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
const OWN_SCHEMA_VERSION = 2

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
 * same target strings, both read from `own.render.tokens`) so explicit renders
 * agree across both APIs; an unconsumed token is a hard error for the
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
  const contract = contractDocument()
  const bodyToken = contract?.own?.overlay?.persona_body_token
  if (bodyToken && text.includes(bodyToken)) {
    try {
      const source = contract.own.native.persona_source
      const repoToken = contract.own.native.persona_repo_token
      const body = readFileSync(join(pkgRoot, source), 'utf8').replace(/\r\n/g, '\n')
      if (body.includes(repoToken)) {
        const content = body.split(repoToken).join(posixPath(pkgRoot)).trim()
        text = text.split(bodyToken).join(content.split('\n').join('\n      '))
      }
    } catch { /* A missing body leaves its token in the diagnostic below. */ }
  }
  const leftovers = [...new Set(text.match(bindings.leftoverScan) || [])]
  return { text, leftovers }
}

/** Deprecated directory-writer export. Keep the structured return value for
 * existing callers and direct installation to the host-aware CLI. */
export function ensurePreset(ctx) {
  const outcome = { synced: false, dir: '', version: packageVersion() }
  try {
    const bindings = contractBindings()
    if (bindings.homeVar) {
      outcome.dir = join(resolveDshHome(bindings), bindings.presetDir, bindings.presetId)
    }
    ctx?.logger?.warn?.('software-project-governance: directory rendering moved to '
      + 'adapters/dsh/launch.py --install with a redirected DSH_HOME; the host registers the native preset')
  } catch { /* The compatibility shim never writes or interrupts host startup. */ }
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
  if (config?.deliveryPreflight) {
    const register = (child) => {
      try { registerDeliveryPreflight(child, config.deliveryPreflight) }
      catch { ctx?.logger?.warn?.('software-project-governance: delivery preflight (PREFLIGHT_UNAVAILABLE)') }
    }
    try { ctx?.inject?.(deliveryPreflightServices, register) }
    catch { ctx?.logger?.warn?.('software-project-governance: delivery preflight (PREFLIGHT_UNAVAILABLE)') }
  }
  // FEAT-099 (U1 PoC): the host-level enforcement guard is an INDEPENDENT
  // face of this row — it registers when the host exposes ctx.tools.guard(),
  // degrades with one structured warn when it does not, and never affects
  // preset delivery above or below (warn-only row contract untouched; the
  // guard's deny is a first-class host pipeline outcome, not a row throw).
  // GOVERNANCE_ENFORCEMENT=off registers nothing (zero-drift switch).
  try {
    registerEnforcementGuard(ctx)
  } catch {
    // registerEnforcementGuard is itself warn-only; this belt keeps the row's
    // never-throw contract absolute.
  }
  try {
    const services = ['goals', 'agentPresets', 'systemPrompt']
    let tree = null
    const register = (child) => {
      try {
        const { code } = registerGoalAdmission(child, { tree: () => tree, directRepair: config?.directRepair })
        ctx?.logger?.info?.(`software-project-governance: DSH goal admission (${code})`)
      } catch {
        ctx?.logger?.info?.('software-project-governance: DSH goal admission (GOAL_ADMISSION_REGISTER_FAILED)')
      }
    }
    // A Cordis service facade can exist before the injected service is ready.
    if (typeof ctx?.inject === 'function') {
      ctx.inject(services, register)
      ctx.inject(['goals', 'agents', 'sessions', 'sessionPersistence', 'subagents', 'llm'], (child) => {
        const budget = createGoalTreeBudget(child)
        if (!budget) return
        tree = budget
        child.effect(() => () => { tree = null; budget.dispose() })
        ctx?.logger?.info?.('software-project-governance: DSH goal tree budget (TREE_BUDGET_REGISTERED)')
      })
    } else {
      register(ctx)
    }
  } catch {
    ctx?.logger?.info?.('software-project-governance: DSH goal admission (GOAL_ADMISSION_REGISTER_FAILED)')
  }
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
