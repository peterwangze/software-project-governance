/** Scoped native DSH usage and cancellation; Python owns the durable goal state. */

import { randomBytes } from 'node:crypto'

const MAX_SESSIONS = 64
const MAX_EVENTS = 20_000
const TICK_MS = 500
const TAIL_MS = 8_000
const OBSERVED_EVENTS = new Set(['assistant/message', 'assistant/attempt', 'compaction/summary',
  'goal/change', 'subagent/catalog', 'step/end', 'turn/end'])
const isCount = (value) => Number.isSafeInteger(value) && value >= 0
const isChild = (header, id, parent) => header?.id === id && header.origin === 'subagent'
  && header.parentSession === parent

function readLive(session) {
  const start = session.inheritedEventCount
  if (!isCount(start) || !isCount(session.seq) || session.seq < start) return null
  const end = Math.min(session.seq, start + MAX_EVENTS)
  return { events: session.snapshotEvents(start, end), truncated: end < session.seq }
}

function countUsage(events, goalId, now) {
  let anchored = goalId == null
  let turn, goalTurn, stepStart, openTurn = false
  let tokens = 0, missing = 0
  const spans = [], children = []
  for (const { type, time, data } of events) {
    if (type === 'goal/change' && data.operation === 'create' && data.goal?.id === goalId) anchored = true
    if (!anchored) continue
    if (type === 'turn/start') {
      turn = data.turn
      openTurn = true
      stepStart = undefined
    } else if (type === 'user/message' && data.source?.kind === 'goal'
               && data.source.goalId === goalId && data.source.round > 0) {
      goalTurn = turn
    }
    const selected = goalId == null || (goalTurn !== undefined && goalTurn === turn)
    if (type === 'step/start') stepStart = time
    if (type === 'step/end') {
      if (selected && isCount(stepStart) && isCount(time) && time >= stepStart) spans.push([stepStart, time])
      stepStart = undefined
    }
    if (type === 'turn/end') openTurn = false
    if (!selected) continue
    if (type === 'subagent/catalog' && typeof data.childId === 'string' && data.childId) children.push(data)
    if (!['assistant/message', 'assistant/attempt', 'compaction/summary'].includes(type)) continue
    const total = data.usage?.totalTokens
    if (isCount(total) && isCount(tokens + total)) tokens += total
    else missing++
  }
  const selectedTurn = openTurn && (goalId == null || (goalTurn !== undefined && goalTurn === turn))
  const open = selectedTurn && isCount(stepStart)
  if (open && now >= stepStart) spans.push([stepStart, now])
  return { tokens, missing, spans, children, selectedTurn, open, anchored }
}

function wallSeconds(spans) {
  spans.sort((left, right) => left[0] - right[0])
  let used = 0, lastEnd = 0
  for (const [start, end] of spans) {
    used += Math.max(0, end - Math.max(start, lastEnd))
    lastEnd = Math.max(lastEnd, end)
  }
  return used / 1000
}

async function flushCut(ctx, session, seq) {
  let handle
  const signal = AbortSignal.timeout(1500)
  try {
    const flushed = await Promise.race([ctx.sessions.flush(session), new Promise((resolve) => {
      signal.addEventListener('abort', () => resolve(false), { once: true })
    })])
    if (!flushed) return false
    handle = await ctx.sessionPersistence.open(session.id, 'read', { signal })
    const { events } = await handle.read(seq, 1, { signal })
    return events[0]?.seq === seq && handle.header.id === session.id
  } catch {
    return false
  } finally {
    try { await handle?.close() } catch { /* The cut, if verified, remains durable. */ }
  }
}

async function readCold(ctx, id, signal) {
  const handle = await ctx.sessionPersistence.open(id, 'read', { signal })
  try {
    const { events } = await handle.read(handle.inheritedEventCount, MAX_EVENTS + 1, { signal })
    return { header: handle.header, events: events.slice(0, MAX_EVENTS), truncated: events.length > MAX_EVENTS }
  } finally { await handle.close() }
}

function lookupCold(ctx, state, id) {
  const previous = state.cold.get(id)
  if (previous && Date.now() < previous.refreshAfter) return
  const slot = { refreshAfter: Infinity, record: null }
  state.cold.set(id, slot)
  const signal = AbortSignal.timeout(3_000)
  void readCold(ctx, id, signal).then(record => { slot.record = record }, () => {
    slot.refreshAfter = Date.now() + 1000
  })
}

async function coldOwner(ctx, agent) {
  let child = agent.session.header
  const seen = new Set([child.id])
  const signal = AbortSignal.timeout(3000)
  while (child.origin === 'subagent' && typeof child.parentSession === 'string' && seen.size < MAX_SESSIONS) {
    const parent = child.parentSession
    if (seen.has(parent)) return null
    seen.add(parent)
    const live = ctx.sessions.get(parent)
    const record = live ? { ...readLive(live), header: live.header } : await readCold(ctx, parent, signal)
    if (record?.header?.id !== parent || record.truncated || !record.events) return null
    const childId = child.id
    if (!record.events.some(event => event.type === 'subagent/catalog' && event.data.childId === childId)) return null
    if (record.header.origin !== 'subagent') {
      let turnGoal, ownerGoal
      for (const { type, data } of record.events) {
        if (type === 'turn/start' || type === 'turn/end') turnGoal = undefined
        if (type === 'user/message' && data.source?.kind === 'goal' && data.source.round > 0) {
          turnGoal = data.source.goalId
        }
        if (type === 'subagent/catalog' && data.childId === childId && turnGoal) ownerGoal = turnGoal
      }
      return ownerGoal ? { header: record.header, sessionId: parent, goalId: ownerGoal } : null
    }
    child = record.header
  }
  return null
}

function observeTree(ctx, state) {
  const now = Date.now()
  const rootSession = state.agent.session
  const rootId = rootSession.id
  const queue = [{ id: rootId }], members = new Set(), liveSessions = new Set(), visited = new Set()
  const interruptible = new Set(), spans = []
  const observation = { sessions: 0, open_steps: 0, missing_sessions: 0, missing_usage: 0, flush_failures: 0 }
  let tokens = 0, rootTurn = false, busy = false
  while (queue.length && visited.size < MAX_SESSIONS) {
    const { id, parent, external } = queue.shift()
    if (visited.has(id)) continue
    visited.add(id)
    if (external) {
      interruptible.add(id)
      observation.missing_sessions++
      continue
    }
    const session = id === rootId ? rootSession : ctx.sessions.get(id)
    if (session) state.cold.delete(id)
    else lookupCold(ctx, state, id)
    const record = session ? readLive(session) : state.cold.get(id)?.record
    if (id !== rootId && !isChild(session?.header ?? record?.header, id, parent)) {
      observation.missing_sessions++
      continue
    }
    members.add(id)
    if (id !== rootId) interruptible.add(id)
    if (!record) {
      observation.missing_sessions++
      continue
    }
    observation.sessions++
    if (session) liveSessions.add(session)
    const row = countUsage(record.events, id === rootId ? state.request.goal_id : null, now)
    if (id === rootId) rootTurn = row.selectedTurn
    if (record.truncated || !row.anchored) observation.missing_sessions++
    if (isCount(tokens + row.tokens)) tokens += row.tokens
    else observation.missing_usage++
    observation.missing_usage += row.missing
    observation.open_steps += Number(row.open)
    busy ||= row.selectedTurn || (id !== rootId && ctx.agents.get(id)?.status === 'running')
    spans.push(...row.spans)
    for (const child of row.children) {
      if (queue.length + visited.size >= MAX_SESSIONS) observation.missing_sessions++
      else queue.push({ id: child.childId, parent: id, external: child.mode === 'external' })
    }
  }
  observation.sessions = Math.max(1, observation.sessions)
  const goal = ctx.goals.get(state.agent)
  const rounds = goal?.id === state.request.goal_id
    ? Math.max(0, goal.roundsStarted - Number(rootTurn)) : state.request.usage.rounds
  return { usage: { rounds, tokens, seconds: wallSeconds(spans) }, observation,
    members, liveSessions, interruptible, rootTurn, busy }
}

export function createGoalTreeBudget(ctx) {
  if (typeof ctx?.sessions?.get !== 'function' || typeof ctx.sessions.flush !== 'function'
      || typeof ctx?.sessionPersistence?.open !== 'function' || typeof ctx?.agents?.get !== 'function'
      || typeof ctx?.subagents?.interrupt !== 'function' || typeof ctx?.goals?.pause !== 'function') return null

  const roots = new Map(), owners = new Map(), disposers = []
  let disposed = false

  function release(state) {
    roots.delete(state.agent.session.id)
    for (const member of state.members) if (owners.get(member) === state) owners.delete(member)
  }

  function sample(state) {
    const reading = observeTree(ctx, state)
    for (const member of reading.members) {
      state.members.add(member)
      owners.set(member, state)
    }
    return reading
  }

  function log(state, code) {
    ctx.logger?.info?.(`software-project-governance: DSH goal ${state.request.goal_id} (${code})`)
  }

  function signalStop(state, reading) {
    const stop = state.stop
    const goal = ctx.goals.get(state.agent)
    try {
      if (goal?.id === state.request.goal_id && goal.phase === 'active') {
        ctx.goals.pause(state.agent, { id: goal.id, revision: goal.revision })
      }
      if (reading.rootTurn && state.agent.status === 'running') {
        state.agent.cancel({ kind: 'user' }, { keepInbox: true })
      }
    } catch { stop.errors.add(state.agent.session.id) }
    for (const id of reading.interruptible) {
      if (stop.signalled.has(id)) continue
      try { ctx.subagents.interrupt(id, { kind: 'ancestor', agent: state.agent }) }
      catch { stop.errors.add(id) }
      stop.signalled.add(id)
    }
  }

  async function submit(state, action, reading) {
    const { stop, request } = state
    return state.policy(state.root, { ...request, action, revision: stop.revision, usage: reading.usage,
      tree: { id: stop.id, observation: reading.observation } })
  }

  async function advance(state, reading) {
    const stop = state.stop
    if (stop.pending || stop.done) return
    stop.pending = true
    try {
      if (!stop.durable) {
        const answer = await submit(state, 'tree-stop', reading)
        if (disposed || state.stop !== stop) return
        if (answer?.code !== 'TREE_BUDGET_STOPPED' || answer.tree_stop?.id !== stop.id) {
          if (answer?.code === 'STALE_REVISION' && state.request.revision > stop.revision) stop.revision = state.request.revision
          if (stop.fault !== answer?.code) {
            stop.fault = answer?.code
            log(state, 'TREE_STOP_POLICY_FAILED')
          }
          return
        }
        stop.durable = true
        stop.deadline = Date.now() + TAIL_MS
        log(state, 'TREE_BUDGET_STOPPED')
      }
      reading = sample(state)
      signalStop(state, reading)
      reading = sample(state)
      if ((reading.busy || reading.observation.missing_sessions) && Date.now() < stop.deadline) return
      const cuts = new Map([...reading.liveSessions].map((session) => [session, session.seq - 1]))
      const flushed = await Promise.all([...cuts].map(([session, seq]) => flushCut(ctx, session, seq)))
      if (disposed || state.stop !== stop) return
      reading = sample(state)
      signalStop(state, reading)
      const changing = [...reading.liveSessions].filter((session) => cuts.get(session) !== session.seq - 1)
      if ((reading.busy || changing.length) && Date.now() < stop.deadline) return
      reading.observation.flush_failures = stop.errors.size
        + changing.length + flushed.filter((success) => !success).length
      if (reading.busy && reading.observation.open_steps === 0) reading.observation.open_steps = 1
      const answer = await submit(state, 'tree-settle', reading)
      if (disposed || state.stop !== stop) return
      if (answer?.code === 'TREE_TAIL_RECORDED' && answer.tree_stop?.id === stop.id) {
        stop.done = true
        log(state, 'TREE_TAIL_RECORDED')
      }
    } finally {
      stop.pending = false
    }
  }

  function tick(state) {
    const goal = ctx.goals.get(state.agent)
    if (ctx.agents.get(state.agent.session.id) !== state.agent || goal?.id !== state.request.goal_id
        || goal.phase === 'complete') {
      if (!state.stop || state.stop.done) release(state)
      return
    }
    if (state.stop?.done) return
    const reading = sample(state)
    if (!state.stop && (reading.usage.tokens >= state.tokenLimit || reading.usage.seconds >= state.wallLimit)) {
      state.stop = { id: randomBytes(16).toString('hex'), revision: state.request.revision,
        deadline: Infinity, signalled: new Set(), errors: new Set() }
    }
    if (state.stop) void advance(state, reading).catch(() => log(state, 'TREE_BUDGET_SUPERVISOR_FAILED'))
  }

  function safeTick(state) {
    try { tick(state) } catch { log(state, 'TREE_BUDGET_SUPERVISOR_FAILED') }
  }

  function watch({ agent, root, request, outcome, policy }) {
    const id = agent.session.id
    let state = roots.get(id)
    if (state && (state.agent !== agent || state.request.goal_id !== request.goal_id)) {
      release(state)
      state = undefined
    }
    if (!state) {
      state = { agent, root, request, policy, members: new Set([id]), cold: new Map() }
      roots.set(id, state)
      owners.set(id, state)
    }
    if (outcome.status === 'ALLOW') {
      const zones = outcome.budget?.zones
      state.tokenLimit = zones?.tokens?.limit ?? state.tokenLimit ?? Infinity
      state.wallLimit = zones?.wall_clock?.limit ?? state.wallLimit ?? Infinity
      if (state.stop?.done && request.revision > state.stop.revision) state.stop = undefined
      state.request = request
    } else if (outcome.tree_stop && !state.stop) {
      const { id: stopId, revision, status } = outcome.tree_stop
      state.stop = { id: stopId, revision, durable: true, deadline: Date.now() + TAIL_MS,
        signalled: new Set(), errors: new Set(), done: status !== 'PENDING' }
    }
    safeTick(state)
    return Boolean(state.stop)
  }

  function isHeld(sessionId) { return Boolean(owners.get(sessionId)?.stop) }

  async function coldRootFor(agent) {
    try { return await coldOwner(ctx, agent) }
    catch { return null }
  }

  function onEvent(session, event) {
    const state = owners.get(session.id)
    if (state && OBSERVED_EVENTS.has(event.type)) safeTick(state)
  }

  const interval = setInterval(() => roots.forEach(safeTick), TICK_MS)
  interval.unref?.()
  function dispose() {
    disposed = true
    clearInterval(interval)
    for (const remove of disposers) if (typeof remove === 'function') remove()
    roots.clear()
    owners.clear()
  }
  try {
    disposers.push(ctx.on('session/event', onEvent))
    disposers.push(ctx.on('llm/stream', (options, next) => {
      if (isHeld(options.sessionId)) throw new Error('Governance goal budget stopped this native request')
      return next()
    }))
    return { watch, isHeld, coldRootFor, dispose }
  } catch {
    dispose()
    return null
  }
}
