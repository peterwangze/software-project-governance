/** Opt-in admission of native DSH goal steps and completion. */

import { spawn, spawnSync } from 'node:child_process'
import { accessSync, constants, lstatSync, readFileSync, realpathSync, statSync } from 'node:fs'
import { delimiter, dirname, isAbsolute, join, parse, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const POLICY = fileURLToPath(new URL('../../skills/software-project-governance/infra/dsh_goal_native.py', import.meta.url))
const POLICY_CWD = dirname(POLICY)
const ORIGINAL = Symbol.for('cordis.original')
const PROFILE = '.governance/dsh-goal.json'
const STATE_DIR = '.governance/goal-bridge'
const GOAL_ID = /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/u
const CODE = /^[A-Z][A-Z0-9_]{0,63}$/u
const HASH = /^[0-9a-f]{64}$/u
const TIMEOUT_MS = 4000
const LIMIT = 64 * 1024
const liveInstalls = new WeakSet()

const refusal = (code) => ({ status: 'HOLD', code })
const exactRef = (left, right) => left != null && right != null
  && left.id === right.id && left.revision === right.revision
const natural = (value) => Number.isSafeInteger(value) && value >= 0
const validId = (value) => typeof value === 'string' && GOAL_ID.test(value)

function inWorkspace(root, path) {
  const remainder = relative(root, path)
  return !isAbsolute(remainder) && remainder !== '..' && !remainder.startsWith(`..${sep}`)
}

function policyInterpreter(root) {
  const windows = process.platform === 'win32'
  const executable = windows ? 'python.exe' : 'python3'
  // Resolve the executable ourselves: Windows can search the parent's CWD even without a shell.
  for (const part of (process.env.PATH ?? '').split(delimiter)) {
    const entry = part.trim().replace(/^"(.*)"$/u, '$1')
    if (!isAbsolute(entry) || (windows && parse(entry).root.length <= 1)) continue
    try {
      const directory = realpathSync(entry)
      if (inWorkspace(root, directory)) continue
      const interpreter = realpathSync(join(directory, executable))
      if (inWorkspace(root, interpreter) || !statSync(interpreter).isFile()) continue
      accessSync(interpreter, constants.X_OK)
      return interpreter
    } catch { /* Try the next host PATH entry. */ }
  }
  return null
}

function policyArgs(root) {
  return ['-E', '-s', POLICY, '--project-root', root]
}

function encoded(request) {
  const value = JSON.stringify(request)
  if (Buffer.byteLength(value) > LIMIT) throw new Error('request too large')
  return value
}

function decode(payload, request) {
  const reply = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(payload))
  if (reply?.schema_version !== 1 || reply.session_id !== request.session_id
      || reply.goal_id !== request.goal_id || reply.revision !== request.revision
      || !CODE.test(reply.code) || !['ALLOW', 'HOLD', 'NOT_CONFIGURED'].includes(reply.status)) {
    return refusal('INVALID_POLICY_REPLY')
  }
  if (reply.status === 'ALLOW'
      && (!HASH.test(reply.contract_sha256)
        || reply.code !== (request.action === 'admit' ? 'ADMITTED' : 'DELIVERY_ACCEPTED'))) {
    return refusal('INVALID_POLICY_REPLY')
  }
  return reply
}

function runSync(root, request) {
  try {
    const command = policyInterpreter(root)
    if (!command) return refusal('POLICY_UNAVAILABLE')
    const child = spawnSync(command, policyArgs(root), {
      cwd: POLICY_CWD, input: encoded(request), timeout: TIMEOUT_MS, maxBuffer: LIMIT,
      shell: false, windowsHide: true,
    })
    if (child.error || child.status !== 0) return refusal('POLICY_UNAVAILABLE')
    return decode(child.stdout, request)
  } catch {
    return refusal('INVALID_POLICY_REPLY')
  }
}

async function runAsync(root, request, signal) {
  if (signal?.aborted) return refusal('CANCELLED')
  try {
    const input = encoded(request)
    const command = policyInterpreter(root)
    if (!command) return refusal('POLICY_UNAVAILABLE')
    const child = spawn(command, policyArgs(root), {
      cwd: POLICY_CWD, shell: false, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'],
    })
    return await new Promise((resolve) => {
      const chunks = []
      let size = 0
      let settled = false
      function finish(reply) {
        if (settled) return
        settled = true
        clearTimeout(timer)
        signal?.removeEventListener('abort', cancel)
        resolve(reply)
      }
      function stop(code) {
        child.kill()
        finish(refusal(code))
      }
      function cancel() { stop('CANCELLED') }
      const timer = setTimeout(() => stop('POLICY_TIMEOUT'), TIMEOUT_MS)
      signal?.addEventListener('abort', cancel, { once: true })
      child.stdout.on('data', (chunk) => {
        size += chunk.length
        if (size > LIMIT) stop('POLICY_OUTPUT_LIMIT')
        else chunks.push(chunk)
      })
      child.stderr.on('data', (chunk) => {
        size += chunk.length
        if (size > LIMIT) stop('POLICY_OUTPUT_LIMIT')
      })
      child.on('error', () => finish(refusal('POLICY_UNAVAILABLE')))
      child.stdin.on('error', () => stop('POLICY_UNAVAILABLE'))
      child.on('close', (code) => {
        if (settled) return
        if (code !== 0) return finish(refusal('POLICY_UNAVAILABLE'))
        try { finish(decode(Buffer.concat(chunks), request)) }
        catch { finish(refusal('INVALID_POLICY_REPLY')) }
      })
      if (signal?.aborted) cancel()
      else child.stdin.end(input)
    })
  } catch {
    return refusal('POLICY_UNAVAILABLE')
  }
}

function present(path) {
  try { lstatSync(path); return true }
  catch (error) { return error?.code !== 'ENOENT' && error?.code !== 'ENOTDIR' }
}

function nativeRecord(root, sessionId, goalId) {
  if (!validId(goalId) || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/iu.test(goalId)) return { binding: 'none' }
  try {
    if (!lstatSync(join(root, '.governance')).isDirectory()
        || !lstatSync(join(root, STATE_DIR)).isDirectory()) return { binding: 'uncertain' }
    const path = join(root, STATE_DIR, `${goalId}.json`)
    const info = lstatSync(path)
    if (!info.isFile() || info.nlink !== 1 || info.size > LIMIT) return { binding: 'uncertain' }
    const state = JSON.parse(readFileSync(path, 'utf8'))
    if (state?.goal_id !== goalId) return { binding: 'uncertain' }
    if (typeof state.native_dsh?.session_id !== 'string') return { binding: 'uncertain' }
    return state.native_dsh.session_id === sessionId ? { binding: 'bound', state } : { binding: 'none' }
  } catch (error) {
    return { binding: error?.code === 'ENOENT' ? 'none' : 'uncertain' }
  }
}

function projectFromHeader(header) {
  const cwd = header?.cwd ?? header?.meta?.cwd
  if (typeof cwd !== 'string' || !isAbsolute(cwd)) return null
  try { return realpathSync(cwd) }
  catch { return null }
}

function projectFor(agent) { return projectFromHeader(agent?.session?.header) }

/** Parent-session settled usage for the exact native goal, not process uptime. */
export function settledGoalUsage(session, goal, now = Date.now()) {
  const usage = { rounds: goal.roundsStarted }
  if (typeof session?.snapshotEvents !== 'function') return usage
  const events = session.snapshotEvents(0)
  let anchored = false
  let turn
  let goalTurn
  let turnOpen = false
  let stepStart
  let tokens = 0
  let hadRequest = false
  let measuredTokens = false
  let elapsed = 0
  for (const event of events) {
    const data = event.data
    if (event.type === 'goal/change' && data.operation === 'create' && data.goal?.id === goal.id) {
      anchored = true
      continue
    }
    if (!anchored) continue
    if (event.type === 'turn/start') {
      turn = data.turn
      turnOpen = true
      stepStart = undefined
    } else if (event.type === 'user/message' && data.source?.kind === 'goal'
               && data.source.goalId === goal.id && data.source.round > 0) {
      goalTurn = turn
    } else if (event.type === 'step/start') {
      stepStart = event.time
    } else if (event.type === 'step/end') {
      if (goalTurn === turn && natural(stepStart) && natural(event.time) && event.time >= stepStart) {
        elapsed += event.time - stepStart
      }
      stepStart = undefined
    } else if (event.type === 'turn/end') {
      turnOpen = false
    } else if (event.type === 'assistant/attempt' && goalTurn !== undefined && data.turn === goalTurn) {
      hadRequest = true
    } else if (event.type === 'assistant/message' && goalTurn !== undefined && data.turn === goalTurn) {
      hadRequest = true
      const total = data.usage?.totalTokens
      if (natural(total) && natural(tokens + total)) {
        tokens += total
        measuredTokens = true
      }
    }
  }
  if (!anchored) return usage
  if (goalTurn !== undefined && goalTurn === turn && turnOpen) {
    usage.rounds = Math.max(0, usage.rounds - 1)
    if (natural(stepStart) && natural(now) && now >= stepStart) elapsed += now - stepStart
  }
  if (!hadRequest || measuredTokens) usage.tokens = tokens
  if (natural(elapsed)) usage.seconds = elapsed / 1000
  return usage
}

function nativeRequest(action, agent, goal) {
  return {
    schema_version: 1, action, session_id: agent.session.id, goal_id: goal.id,
    revision: goal.revision, objective: goal.objective, max_rounds: goal.maxGoalRounds,
    usage: settledGoalUsage(agent.session, goal),
  }
}

function validGoal(goal) {
  return goal != null && validId(goal.id)
    && natural(goal.revision) && goal.revision > 0 && typeof goal.objective === 'string'
    && natural(goal.maxGoalRounds) && goal.maxGoalRounds > 0 && natural(goal.roundsStarted)
}

function courseText(goal, outcome) {
  const plan = outcome.plan
  const packages = Array.isArray(plan?.work_packages)
    ? plan.work_packages.slice(0, 3).filter((item) => validId(item?.id)
      && ['repair', 'verify'].includes(item.action) && typeof item.instruction === 'string'
      && item.instruction.length <= 1000 && !/[\r\n]/u.test(item.instruction))
      .map((item) => `${item.id}:${item.action} ${item.instruction}`).join(' | ') : ''
  const choices = Array.isArray(plan?.recommendations)
    ? plan.recommendations.slice(0, 3).filter((item) => validId(item?.task_id) && ['repair', 'verify'].includes(item?.action))
      .map((item) => `${item.task_id}:${item.action}${item.mode === 'resume' ? ':resume' : ''}`).join(', ') : ''
  const limits = ['rounds', 'tokens', 'wall_clock'].map((key) => {
    const zone = outcome.budget?.zones?.[key]
    return zone && natural(zone.limit) && ['safe', 'warning', 'danger'].includes(zone.zone)
      ? `${key}=${zone.limit}:${zone.zone}` : null
  }).filter(Boolean).join(', ')
  return `Governance goal admission: ${goal.id} revision ${goal.revision}. `
    + `Delivery contract SHA-256: ${outcome.contract_sha256}. Native round cap: ${goal.maxGoalRounds}. `
    + `Planner state: ${CODE.test(plan?.state) ? plan.state : 'UNKNOWN'}. `
    + (plan?.direct_repair === true && packages
      ? 'Trusted native direct repair for the single work package below. '
        + '当前代理以已有用户授权直接修复该工作包。对此工作包，本次宿主准入优先于 AGENTS.md 与通用 Coordinator 流程的例行 bootstrap、skill 加载、状态、规划、台账、任务锁及派发步骤。'
        + '读取相关代码并修复，经同一普通玩家入口复验，运行生产构建，再提交独立交付验收。预算、权限及完成验收门禁照常适用。 '
      : '')
    + (packages ? 'The user already authorized these work packages for this unchanged objective. Continue without asking again. '
      + `Work packages: ${packages}. ` : '')
    + (choices ? `Recommended actions: ${choices}. ` : '')
    + (limits ? `Budget limits and zones: ${limits}. ` : '')
    + 'Use the normal delivery acceptance path before completing this goal.'
}

function goalMessage(message) { return message?.source?.kind === 'goal' && message.source.round > 0 }

function firstNativeGoal(session, goalId) {
  const creates = session.snapshotEvents?.(0).filter(event =>
    event.type === 'goal/change' && event.data.operation === 'create') ?? []
  return creates.length === 1 && creates[0].data.goal?.id === goalId
}

function restoreMessages(agent, messages) {
  const inbox = agent?.inbox
  if (typeof inbox?.prepend !== 'function') return
  for (const message of [...messages].reverse()) {
    if (message?.source?.kind === 'goal') continue // the native driver owns goal reservations
    if (inbox.nextStep?.some((item) => item.id === message.id)
        || inbox.nextTurn?.some((item) => item.id === message.id)) continue
    inbox.prepend('next-step', message)
  }
}

function completionTarget(ctx) {
  const service = ctx?.goals?.[ORIGINAL]
  if (!service || liveInstalls.has(service) || !Object.isExtensible(service)) return null
  const own = Object.getOwnPropertyDescriptor(service, 'complete')
  const descriptor = own ?? Object.getOwnPropertyDescriptor(Object.getPrototypeOf(service), 'complete')
  const method = descriptor?.value
  if ((own && !own.configurable) || typeof method !== 'function' || method.length !== 2
      || !/^(?:function\s+)?complete\s*\(\s*agent\s*,\s*ref\s*\)/u.test(Function.prototype.toString.call(method))) {
    return null
  }
  return { service, own, method }
}

export function registerGoalAdmission(ctx, { admit = runAsync, completePolicy = runSync, tree = () => null,
  directRepair = null } = {}) {
  const target = completionTarget(ctx)
  if (!target || typeof ctx?.on !== 'function' || typeof ctx?.effect !== 'function'
    || typeof ctx?.agentPresets?.presetForSession !== 'function'
    || typeof ctx?.systemPrompt?.context !== 'function' || typeof ctx?.systemPrompt?.refreshContext !== 'function'
    || typeof ctx?.goals?.get !== 'function' || typeof ctx?.goals?.block !== 'function') {
    return { registered: false, code: 'GOAL_ADMISSION_HOST_UNSUPPORTED' }
  }

  const bound = new WeakMap()
  const turns = new WeakMap()
  const direct = directRepair == null ? null : Object.freeze({ ...directRepair })
  let directClaim
  let active = true
  const { service, own, method } = target
  function scope(agent, goalId) {
    const saved = bound.get(agent)
    const sessionId = agent?.session?.id
    const remembered = saved != null && saved.goalId === goalId && saved.sessionId === sessionId
    const root = projectFor(agent)
    if (!root || (remembered && saved.root !== root)) return remembered ? { fault: true } : null
    const persisted = nativeRecord(root, sessionId, goalId).binding
    const known = remembered || persisted === 'bound'
      || (ctx.agentPresets.presetForSession(agent.session) === 'governance' && present(join(root, PROFILE)))
    if (known) bound.set(agent, { goalId, root, sessionId })
    return known || persisted === 'uncertain' ? { root, uncertain: !known } : null
  }

  function currentGoal(agent) {
    try { return ctx.goals.get(agent) }
    catch { return null }
  }

  function log(goalId, code) {
    ctx.logger?.warn?.(`software-project-governance: DSH goal ${validId(goalId) ? goalId : 'unknown'} held (${code})`)
  }

  function held(agent, goal, messages, code, signal) {
    turns.delete(agent)
    try { restoreMessages(agent, messages) }
    catch { log(goal?.id, 'INBOX_RESTORE_FAILED') }
    if (!signal?.aborted) {
      log(goal?.id, code)
      try {
        const live = currentGoal(agent)
        if (exactRef(live, goal) && live.phase === 'active' && live.activation === 'armed') {
          ctx.goals.block(agent, { id: goal.id, revision: goal.revision }, {
            code: 'governance-admission', message: `Governance goal admission held: ${code}. Inspect the project governance state before resuming.`,
          })
        }
      } catch { log(goal?.id, 'NATIVE_BLOCK_FAILED') }
    }
    return { kind: 'reject' }
  }

  function restoredStop(supervisor, owner) {
    const goal = currentGoal(owner)
    if (!validGoal(goal) || goal.phase === 'complete') return false
    const root = projectFor(owner)
    if (!root) return false
    const saved = nativeRecord(root, owner.session.id, goal.id)
    if (saved.binding === 'uncertain' && present(join(root, PROFILE))) return true
    const stop = saved.state?.tree_stop
    if (!stop || Object.hasOwn(stop, 'resumed_revision')) return false
    if (['PENDING', 'SETTLED', 'INCOMPLETE'].includes(stop.status)
        && /^[0-9a-f]{32}$/u.test(stop.id) && natural(stop.revision)) {
      supervisor?.watch({ agent: owner, root, request: nativeRequest('admit', owner, goal),
        outcome: { status: 'HOLD', tree_stop: stop }, policy: runAsync })
    }
    return true
  }

  async function restoredColdStop(supervisor, agent) {
    const owner = await supervisor?.coldRootFor?.(agent)
    const root = projectFromHeader(owner?.header)
    if (!root) return false
    const saved = nativeRecord(root, owner.sessionId, owner.goalId)
    if (saved.binding === 'uncertain' && present(join(root, PROFILE))) return true
    const stop = saved.state?.tree_stop
    return Boolean(stop && !Object.hasOwn(stop, 'resumed_revision'))
  }

  async function preStep({ agent, messages, signal, turn }, next) {
    const current = turns.get(agent)
    const reservations = messages.filter(goalMessage)
    const reservation = reservations[0]?.source
    const supervisor = tree()
    const child = agent.session.header.origin === 'subagent'
    if ((!reservation || child) && (supervisor?.isHeld(agent.session.id) || restoredStop(supervisor, agent)
        || (child && await restoredColdStop(supervisor, agent)))) {
      turns.delete(agent)
      restoreMessages(agent, messages)
      return { kind: 'reject' }
    }
    const goalId = reservation?.goalId ?? (current?.turn === turn ? current.goal.id : null)
    if (!goalId) {
      turns.delete(agent)
      return next()
    }
    const selected = scope(agent, goalId)
    if (!selected) return next()
    const goal = currentGoal(agent)
    if (!reservation && goal?.id === goalId && goal.phase === 'complete') {
      turns.delete(agent)
      return next() // native post-completion notice retains its regular final step
    }
    const expected = reservation ? { id: reservation.goalId, revision: reservation.revision } : current.goal
    if (selected.fault || !validGoal(goal) || !exactRef(goal, expected) || reservations.length > 1
      || goal.phase !== 'active' || goal.activation !== 'armed'
      || (reservation && reservation.round !== goal.roundsStarted + 1)) {
      return held(agent, expected, messages, 'NATIVE_CONTEXT_INVALID', signal)
    }
    let outcome, request
    try {
      request = nativeRequest('admit', agent, goal)
      const matches = direct?.sessionId === agent.session.id && !Object.hasOwn(direct, 'contractSha256')
        && ctx.agentPresets.presetForSession(agent.session) === 'governance'
        && typeof direct.workspace === 'string'
        && isAbsolute(direct.workspace) && relative(selected.root, direct.workspace) === ''
        && (directClaim ? directClaim.goalId === goal.id : firstNativeGoal(agent.session, goal.id))
      const repair = matches ? { ...direct, ...(directClaim ? { contractSha256: directClaim.contract } : {}) } : null
      outcome = await admit(selected.root, repair ? { ...request, direct_repair: repair } : request, signal)
    }
    catch { outcome = refusal('POLICY_UNAVAILABLE') }
    if (active && !signal?.aborted && selected.uncertain && outcome?.status === 'NOT_CONFIGURED') return next()
    if (active && !signal?.aborted && exactRef(currentGoal(agent), goal)
        && (outcome?.status === 'ALLOW' || outcome?.tree_stop?.status === 'PENDING')
        && supervisor?.watch({ agent, root: selected.root, request, outcome, policy: runAsync })) {
      turns.delete(agent)
      restoreMessages(agent, messages)
      return { kind: 'reject' }
    }
    if (signal?.aborted || !active || outcome?.status !== 'ALLOW' || !exactRef(currentGoal(agent), goal)) {
      const code = outcome?.status === 'ALLOW' ? 'NATIVE_CONTEXT_INVALID' : outcome?.code ?? 'INVALID_POLICY_REPLY'
      return held(agent, goal, messages, signal?.aborted ? 'CANCELLED' : code, signal)
    }
    if (!directClaim && outcome.direct_repair_attested === true) {
      directClaim = { goalId: goal.id, contract: outcome.contract_sha256 }
    }
    turns.set(agent, { turn, goal, text: courseText(goal, outcome) })
    return next()
  }

  const wrapped = function complete(agent, ref) {
    const selected = scope(agent, ref?.id)
    if (!selected) return Reflect.apply(method, this, arguments)
    let outcome = refusal('NATIVE_CONTEXT_INVALID')
    const goal = currentGoal(agent)
    if (tree()?.isHeld(agent.session.id)) {
      outcome = refusal('TREE_BUDGET_STOPPED')
    } else if (!selected.fault && validGoal(goal) && exactRef(goal, ref)) {
      try { outcome = completePolicy(selected.root, nativeRequest('complete', agent, goal)) }
      catch { outcome = refusal('POLICY_UNAVAILABLE') }
    }
    if (selected.uncertain && outcome?.status === 'NOT_CONFIGURED') return Reflect.apply(method, this, arguments)
    if (outcome?.status !== 'ALLOW' || !exactRef(currentGoal(agent), ref)) {
      const code = outcome?.status === 'ALLOW' ? 'NATIVE_CONTEXT_INVALID' : outcome?.code ?? 'INVALID_POLICY_REPLY'
      log(ref?.id, code)
      throw new Error(`Governance goal completion held: ${code}`)
    }
    return Reflect.apply(method, this, arguments)
  }

  const undo = []
  function dispose() {
    active = false
    for (const remove of undo.splice(0).reverse()) {
      try { remove() }
      catch { /* keep unwinding owned registrations */ }
    }
  }
  try {
    Object.defineProperty(service, 'complete', { configurable: true, writable: true,
      enumerable: own?.enumerable ?? false, value: wrapped })
    undo.push(() => {
      if (Object.getOwnPropertyDescriptor(service, 'complete')?.value !== wrapped) return
      if (own) Object.defineProperty(service, 'complete', own)
      else delete service.complete
    })
    const removeContext = ctx.systemPrompt.context({
      name: 'governance-goal-admission', order: 810, required: true, interpolate: false,
      text: ({ agent }) => turns.get(agent)?.text ?? '',
    })
    if (typeof removeContext === 'function') undo.push(removeContext)
    const removePreStep = ctx.on('agent/pre-step', preStep)
    if (typeof removePreStep === 'function') undo.push(removePreStep)
    const removeAttach = ctx.on('agent/created', ({ agent }) => {
      try { restoredStop(tree(), agent) }
      catch { log(currentGoal(agent)?.id, 'TREE_RESTORE_FAILED') }
    })
    if (typeof removeAttach === 'function') undo.push(removeAttach)
    liveInstalls.add(service)
    undo.unshift(() => liveInstalls.delete(service))
    ctx.effect(() => dispose)
    return { registered: true, code: 'GOAL_ADMISSION_REGISTERED', dispose }
  } catch {
    dispose()
    return { registered: false, code: 'GOAL_ADMISSION_REGISTER_FAILED' }
  }
}
