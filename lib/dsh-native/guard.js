/**
 * FEAT-099 — host-level enforcement guard (U1 PoC, minimum slice).
 *
 * The governance host row registers ONE monotonic synchronous guard through
 * the public `ctx.tools.guard()` primitive (dsh-tools README "Enforce policy
 * on calls": "a returned reason denies the call, and no later listener can
 * turn that denial back into permission"). The guard mirrors the
 * revision-mismatch branch of `infra/enforcement.py decide()` — the CLI-level
 * Python face — for the tool face `subagent`/`subagent_fork` only.
 *
 * Anchor protocol (design §2.1): the dispatching side marks the FIRST line
 * of the subagent prompt with a structured tag; the guard extracts it and
 * compares `rev` against the governed expected-revision projection:
 *
 *   [governance-dispatch task=<TASK_ID> rev=<int> channel=<normal|fix|re-review|forensics> actor=<role>]
 *
 * Semantics (mirrors enforcement.py L352-374 + design §3c C0-C7):
 *   rev != expected[task]  -> deny revision-mismatch (reason/remedy templates
 *                             come from the SINGLE SOURCE strategy projection,
 *                             lib/dsh-native/strategy-projection.json, which
 *                             is byte-guarded against `--print-strategy`);
 *   rev == expected[task]  -> allow;
 *   task not in projection -> allow (the Python rule does not fire either);
 *   no anchor              -> allow + counter (C7; forcing anchors would deny
 *                             every non-governance dispatch — U7 gap, filed);
 *   anchor, root missing   -> deny fail-closed (C6b: carrying an anchor IS
 *                             asking for the judgment);
 *   no anchor, root missing-> allow + one-shot disclosure (C6a);
 *   malformed anchor / unreadable projection / guard fault / invalid switch
 *                          -> deny fail-closed (C1-C4; never a silent allow).
 *
 * The guard callback itself is a pure synchronous function over a frozen
 * world snapshot; the governance-state cache (design §3b) refreshes that
 * snapshot by stat fingerprint (path∥mtime_ns∥size per file, TTL 30s,
 * switch- and root-sensitive) — a Python process is NEVER spawned per call.
 *
 * Failure policy: registration failures warn once and degrade to "no
 * host-level enforcement" (the row's warn-only contract is untouched —
 * deny is a first-class host pipeline outcome, not a row exception);
 * guard-callback faults fail CLOSED.
 *
 * @module lib/dsh-native/guard
 */

import { createHash } from 'node:crypto'
import { readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

/** Tools this PoC guard covers (design §2.1; everything else passes through). */
export const GUARDED_TOOLS = Object.freeze(['subagent', 'subagent_fork'])

/** The single-source strategy projection shipped with the package (FEAT-099 D2). */
export const STRATEGY_PROJECTION_URL = new URL('./strategy-projection.json', import.meta.url)

/** Anchor protocol literals (design §2.1). */
export const ANCHOR_TAG = '[governance-dispatch'
export const ANCHOR_RE =
  /^\[governance-dispatch task=(\S+) rev=(-?\d+) channel=(normal|fix|re-review|forensics) actor=(\S+)\]$/

/** Reason strings returned to the host pipeline become `Error: <reason>` for
 *  the model (dsh-tools README "Tool-call history and results"), so the
 *  reason carries the code and the remedy — the model can read its way out. */
export const REASON_PREFIX = '[governance-enforcement]'

/** Cache TTL (ms) — the mtime-granularity / clock-skew backstop (design §3b). */
export const CACHE_TTL_MS = 30_000

/** Governance files whose changes invalidate the cached world (W set). */
export const GOVERNANCE_FILES = Object.freeze([
  '.governance/agent-locks.json',
  '.governance/enforcement-expected-revision.json',
  '.governance/execution-packets.json',
])

/** The expected-revision projection file (fixture in the PoC; a governed
 *  bootstrap aggregate writes it in production — same read interface). */
export const EXPECTED_PROJECTION_REL = '.governance/enforcement-expected-revision.json'

const SWITCH_ENV = 'GOVERNANCE_ENFORCEMENT'
const ROOT_ENV = 'GOVERNANCE_REPO_ROOT'
const SWITCH_OFF_WORDS = new Set(['off', '0', 'false', 'disabled', 'no'])
const SWITCH_ON_WORDS = new Set(['on', '1', 'true', 'enabled', 'yes'])

/**
 * Resolve the enforcement switch word → 'on' | 'off' | null (invalid).
 * Mirrors enforcement.py switch_state(): empty/unset = on; vocabulary words;
 * anything else = null → callers fail CLOSED (never guess).
 */
export function switchState(value) {
  const word = (value ?? '').trim().toLowerCase()
  if (word === '') return 'on'
  if (SWITCH_OFF_WORDS.has(word)) return 'off'
  if (SWITCH_ON_WORDS.has(word)) return 'on'
  return null
}

/**
 * Parse the dispatch anchor from the first line of the subagent prompt.
 *
 * @returns {{kind: 'absent'}} | {{kind: 'ok', task: string, rev: number,
 *           channel: string, actor: string}} | {{kind: 'invalid'}}
 */
export function parseDispatchAnchor(promptFirstLine) {
  const line = typeof promptFirstLine === 'string' ? promptFirstLine.trim() : ''
  if (line === '' || !line.startsWith(ANCHOR_TAG)) return { kind: 'absent' }
  const match = ANCHOR_RE.exec(line)
  if (match === null) return { kind: 'invalid' }
  return {
    kind: 'ok',
    task: match[1],
    rev: Number.parseInt(match[2], 10),
    channel: match[3],
    actor: match[4],
  }
}

/** First line of `arguments.prompt`, defensively (arguments is `unknown`). */
function promptFirstLine(args) {
  if (args === null || typeof args !== 'object') return ''
  const prompt = args.prompt
  if (typeof prompt !== 'string') return ''
  const nl = prompt.indexOf('\n')
  return nl === -1 ? prompt : prompt.slice(0, nl)
}

/** Python str.format subset: replace `{key}` placeholders the template owns. */
export function formatTemplate(template, vars) {
  return String(template).replace(/\{(\w+)\}/g, (whole, key) =>
    Object.prototype.hasOwnProperty.call(vars, key) ? String(vars[key]) : whole)
}

/** Model-facing denial string (code + reason + remedy in one line). */
export function denialReason(reasonCode, reason, remedy) {
  return `${REASON_PREFIX} ${reasonCode}: ${reason} (remedy: ${remedy})`
}

/** The revision-mismatch rule row from the strategy projection (single source). */
function revisionMismatchRule(strategy) {
  const rules = Array.isArray(strategy?.hard_block_rules) ? strategy.hard_block_rules : []
  return rules.find((rule) => rule?.id === 'revision-mismatch') ?? null
}

/**
 * Pure judgment over one tool execution against a frozen world snapshot.
 *
 * @param {{name: string, arguments: unknown}} execution — the two fields of
 *        the host `ToolExecution` this guard consumes.
 * @param {{switchState: 'on'|'off'|null, located: boolean,
 *          strategy: object|null, expectedRevision: {string: number}|null,
 *          projectionFault: string|null}} world
 * @returns {{decision: 'allow', counter?: string} |
 *           {decision: 'deny', reasonCode: string, reason: string}}
 */
export function decideGuard(execution, world) {
  if (world.switchState === 'off') {
    // C5 zero-drift: identical to a world without the guard.
    return { decision: 'allow' }
  }
  if (world.switchState === null) {
    // C4: invalid switch word — fail CLOSED, never guess.
    return {
      decision: 'deny',
      reasonCode: 'enforcement-switch-invalid',
      reason: denialReason(
        'enforcement-switch-invalid',
        `invalid ${SWITCH_ENV} value — fail-closed conservative block (illegal value is never guessed)`,
        `set ${SWITCH_ENV} to on/off or unset it`),
      detail: `invalid ${SWITCH_ENV} value — fail-closed conservative block (illegal value is never guessed)`,
      remedy: `set ${SWITCH_ENV} to on/off or unset it`,
    }
  }
  const name = execution?.name
  if (name !== 'subagent' && name !== 'subagent_fork') {
    return { decision: 'allow' } // not this guard's tool face
  }
  const anchor = parseDispatchAnchor(promptFirstLine(execution.arguments))
  if (anchor.kind === 'absent') {
    if (!world.located) {
      // C6a: no anchor asks for no judgment — non-governance traffic must
      // not be wounded by a missing root; disclose once via the counter.
      return { decision: 'allow', counter: 'enforcement-unlocated' }
    }
    // C7: unanchored dispatch — the coercion gap is filed as U7, not fixed
    // here by denying everything without an anchor.
    return { decision: 'allow', counter: 'enforcement-unanchored' }
  }
  // From here on the call CARRIES an anchor: it explicitly asks for the
  // judgment, so every failure mode below fails CLOSED (design §3c C3/C6b).
  if (anchor.kind === 'invalid') {
    const detail = 'malformed governance-dispatch anchor (expected task=<id> rev=<int> '
      + 'channel=<normal|fix|re-review|forensics> actor=<role>) — a call '
      + 'that declares an anchor asks for the judgment and is refused when '
      + 'the judgment cannot be made'
    const remedy = 'fix the anchor line, or drop it to dispatch without governance '
      + 'enforcement'
    return {
      decision: 'deny',
      reasonCode: 'enforcement-fail-closed',
      reason: denialReason('enforcement-fail-closed', detail, remedy),
      detail,
      remedy,
    }
  }
  if (!world.located) {
    // C6b: anchor present, governance root unlocatable.
    const detail = 'governance root is not locatable (no ' + ROOT_ENV
      + ') — the anchored dispatch asks for a revision judgment whose '
      + 'inputs cannot be read'
    const remedy = `set ${ROOT_ENV} to the governed repository root or fix the session workspace context`
    return {
      decision: 'deny',
      reasonCode: 'enforcement-fail-closed',
      reason: denialReason('enforcement-fail-closed', detail, remedy),
      detail,
      remedy,
    }
  }
  if (world.projectionFault !== null || world.expectedRevision === null) {
    // C1: the expected-revision projection is unreadable or corrupt JSON.
    const detail = `governance expected-revision projection unreadable (${world.projectionFault ?? 'absent'})`
    const remedy = 'repair or restore the projection file, then retry the dispatch'
    return {
      decision: 'deny',
      reasonCode: 'enforcement-fail-closed',
      reason: denialReason('enforcement-fail-closed', detail, remedy),
      detail,
      remedy,
    }
  }
  const rule = revisionMismatchRule(world.strategy)
  if (rule === null) {
    // C2-shape: the single-source strategy projection lacks the rule — the
    // judgment cannot be made, and a hardcoded second template would be an
    // unguarded second source (design §3b rejected option (a)).
    const detail = 'strategy projection carries no revision-mismatch rule templates'
    const remedy = 'restore lib/dsh-native/strategy-projection.json from '
      + '`enforcement-check --print-strategy` output'
    return {
      decision: 'deny',
      reasonCode: 'enforcement-fail-closed',
      reason: denialReason('enforcement-fail-closed', detail, remedy),
      detail,
      remedy,
    }
  }
  if (!(anchor.task in world.expectedRevision)) {
    // Python decide() L368-369: task absent from the map → rule does not
    // fire → ALLOW. Parity is machine-checked by the JS×Python test.
    return { decision: 'allow' }
  }
  const expected = world.expectedRevision[anchor.task]
  if (anchor.rev === expected) {
    return { decision: 'allow' }
  }
  const reason = formatTemplate(rule.reason, {
    revision: anchor.rev, task_id: anchor.task, expected,
  })
  return {
    decision: 'deny',
    reasonCode: 'revision-mismatch',
    reason: denialReason('revision-mismatch', reason, rule.remedy),
    detail: reason,
    remedy: rule.remedy,
  }
}

// ── governance-state cache (design §3b — stat fingerprint, TTL, switch) ────

/**
 * Load the strategy projection once per process (package-shipped bytes are
 * immutable for the process lifetime; drift is guarded by the byte-assertion
 * test, not by runtime re-reads).
 */
let strategyCache
export function loadStrategyProjection(url = STRATEGY_PROJECTION_URL) {
  if (strategyCache !== undefined) return strategyCache
  try {
    strategyCache = JSON.parse(readFileSync(fileURLToPath(url), 'utf8'))
  } catch {
    strategyCache = null
  }
  return strategyCache
}

/** One file's fingerprint contribution: path∥mtime_ns∥size ('-' when absent). */
function fileFingerprint(path, deps) {
  try {
    const st = deps.stat(path)
    return `${path}|${st.mtimeNs ?? '-'}|${st.size ?? '-'}`
  } catch {
    return `${path}|missing|`
  }
}

function wholeFingerprint(paths, deps) {
  const hash = createHash('sha1')
  for (const item of paths) hash.update(fileFingerprint(item, deps) + '\n')
  return hash.digest('hex')
}

/**
 * Parse the expected-revision projection (design §4.1 shape):
 * `{"POC-1": {"expected_revision": 2}, ...}` → `{"POC-1": 2}`.
 * @returns {{expectedRevision: Object, fault: string|null}}
 */
export function parseExpectedProjection(text) {
  let parsed
  try {
    parsed = JSON.parse(text)
  } catch (error) {
    return { expectedRevision: null, fault: `corrupt JSON: ${String(error)}` }
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    return { expectedRevision: null, fault: 'projection is not a JSON object' }
  }
  const flat = {}
  for (const [task, cell] of Object.entries(parsed)) {
    if (cell === null || typeof cell !== 'object'
        || typeof cell.expected_revision !== 'number'
        || !Number.isInteger(cell.expected_revision)) {
      return {
        expectedRevision: null,
        fault: `entry ${JSON.stringify(task)} lacks an integer expected_revision`,
      }
    }
    flat[task] = cell.expected_revision
  }
  return { expectedRevision: flat, fault: null }
}

/**
 * Build the guard's world view with the stat-fingerprint cache.
 *
 * Invalidation (design §3b, any one suffices): a W-file's mtime_ns/size
 * changed, TTL (30s) elapsed, the switch word changed, or the located root
 * changed. Refresh NEVER spawns a Python process — it stats and re-reads.
 *
 * @param {{repoRoot: () => string|null, readSwitch: () => string,
 *          readFile: (path: string) => string, stat: (path: string) => object,
 *          now: () => number, ttlMs?: number, strategy?: object}} deps
 */
export function createGuardWorld(deps) {
  const ttlMs = deps.ttlMs ?? CACHE_TTL_MS
  const strategy = deps.strategy ?? loadStrategyProjection()
  let cache = null
  const govPaths = () => {
    const root = deps.repoRoot()
    return root === null ? null : GOVERNANCE_FILES.map((rel) => join(root, rel))
  }
  const computeView = (root) => {
    const paths = GOVERNANCE_FILES.map((rel) => join(root, rel))
    let expectedRevision = null
    let projectionFault = null
    try {
      const text = deps.readFile(join(root, EXPECTED_PROJECTION_REL))
      const parsed = parseExpectedProjection(text)
      expectedRevision = parsed.expectedRevision
      projectionFault = parsed.fault
    } catch (error) {
      projectionFault = `unreadable: ${String(error)}`
    }
    return {
      switchState: switchState(deps.readSwitch()),
      located: true,
      strategy,
      expectedRevision,
      projectionFault,
      fingerprint: wholeFingerprint(paths, deps),
    }
  }
  return {
    view() {
      const word = switchState(deps.readSwitch())
      if (word === 'off') {
        // C5: zero records, zero side effects — not even a stat.
        return { switchState: 'off', located: false, strategy: null,
                 expectedRevision: null, projectionFault: null, fingerprint: null }
      }
      const root = deps.repoRoot()
      const paths = govPaths()
      if (root === null || paths === null) {
        return { switchState: word, located: false, strategy: null,
                 expectedRevision: null, projectionFault: null, fingerprint: null }
      }
      const now = deps.now()
      const fresh = cache !== null
        && cache.view.switchState === word
        && cache.root === root
        && cache.view.fingerprint === wholeFingerprint(paths, deps)
        && (now - cache.atMs) < ttlMs
      if (fresh) return cache.view
      const view = computeView(root)
      cache = { view, atMs: now, root }
      return view
    },
  }
}

// ── host-row wiring (design §3a/§6 S3) ──────────────────────────────────────

/**
 * Register the enforcement guard on the row's Cordis context.
 *
 * Zero-registration on `off`; capability-miss degrades with ONE structured
 * warn (the row stays warn-only); registration logs the completion timestamp
 * (the V8 window anchor). The returned callback is the exact function handed
 * to `ctx.tools.guard()`.
 *
 * @param {object} ctx - the row's Cordis context.
 * @param {{env?: object, now?: () => number, logger?: object}} [options]
 * @returns {{registered: boolean, code: string, timestamp?: string}}
 */
export function registerEnforcementGuard(ctx, options = {}) {
  const env = options.env ?? process.env
  const now = options.now ?? Date.now
  const logger = options.logger ?? ctx?.logger
  const word = switchState(env[SWITCH_ENV])
  if (word === 'off') {
    // Zero-drift: behave exactly like a world without the guard.
    return { registered: false, code: 'enforcement-disabled' }
  }
  if (typeof ctx?.tools?.guard !== 'function') {
    // Capability miss is a KNOWN host shape (dsh core always mounts
    // dsh-tools; probes/mocks and a future host refactor may not), not an
    // exception: the structured code is reported at INFO so the row's
    // warn face stays "exactly one warning per delivery failure" (the
    // FX-JS-03 family contract). Registration FAULTS below stay warns —
    // those are anomalies and must not be hidden.
    logger?.info?.(
      'software-project-governance: host enforcement not registered '
      + '(ENFORCEMENT_TOOLS_UNAVAILABLE): this host context exposes no '
      + 'ctx.tools.guard primitive; degraded to protocol+CLI enforcement')
    return { registered: false, code: 'ENFORCEMENT_TOOLS_UNAVAILABLE' }
  }
  const repoRoot = () => {
    const root = env[ROOT_ENV]
    return typeof root === 'string' && root.trim() !== '' ? root.trim() : null
  }
  const world = createGuardWorld({
    repoRoot,
    readSwitch: () => env[SWITCH_ENV] ?? '',
    readFile: (p) => readFileSync(p, 'utf8'),
    stat: (p) => statSync(p, { bigint: true }),
    now,
  })
  let unlocatedDisclosed = false
  const guard = (execution) => {
    try {
      const outcome = decideGuard(execution, world.view())
      if (outcome.counter === 'enforcement-unlocated' && !unlocatedDisclosed) {
        unlocatedDisclosed = true // C6a: ONE disclosure, then plain allows
        logger?.warn?.(
          'software-project-governance: enforcement governance root not '
          + `locatable (set ${ROOT_ENV}); unanchored dispatches pass through unjudged`)
      }
      if (outcome.decision === 'deny') return outcome.reason
      return undefined
    } catch (error) {
      // C2: guard-callback fault — fail CLOSED (design §3c), and the reason
      // still carries code+remedy for the model.
      return denialReason(
        'enforcement-fail-closed',
        `governance guard fault — conservative block: ${String(error)}`,
        'fix or report the governance guard fault; do not retry the blocked dispatch as-is')
    }
  }
  try {
    const dispose = ctx.tools.guard(guard)
    const timestamp = new Date(now()).toISOString()
    logger?.info?.(
      `software-project-governance: enforcement guard registered at ${timestamp} `
      + `(host-level, tools=${GUARDED_TOOLS.join('/')}, rule=revision-mismatch) [FEAT-099 V8 anchor]`)
    return {
      registered: true,
      code: 'REGISTERED',
      timestamp,
      dispose: typeof dispose === 'function' ? dispose : undefined,
    }
  } catch (error) {
    logger?.warn?.(
      'software-project-governance: host enforcement not registered '
      + `(ENFORCEMENT_REGISTER_FAILED): ${String(error)}`)
    return { registered: false, code: 'ENFORCEMENT_REGISTER_FAILED' }
  }
}
