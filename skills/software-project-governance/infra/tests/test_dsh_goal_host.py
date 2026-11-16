"""FEAT-116 adapter behavior over fake Cordis/native goal surfaces."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]

_FAKE_HOST = r"""
import assert from 'node:assert/strict'
import { mkdirSync, rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

const [, , repo, workspace] = process.argv
const { registerGoalAdmission, settledGoalUsage } = await import(pathToFileURL(join(repo, 'lib/dsh-native/goal-admission.js')).href)
const key = Symbol.for('cordis.original')
const profile = join(workspace, '.governance', 'dsh-goal.json')
const state = join(workspace, '.governance', 'goal-bridge', 'goal-1.json')
class Goals {
  get(agent) { return agent.goal }
  block(agent, ref, reason) {
    assert.equal(ref.revision, agent.goal.revision)
    agent.blocks.push(reason)
    agent.goal = { ...agent.goal, phase: 'blocked', activation: 'disarmed', revision: ref.revision + 1 }
  }
  complete(agent, ref) {
    assert.ok(this instanceof Goals)
    assert.equal(ref.revision, agent.goal.revision)
    agent.completions++
    agent.goal = { ...agent.goal, phase: 'complete', revision: ref.revision + 1 }
    return agent.goal
  }
}
function host() {
  const service = new Goals()
  const callbacks = new Map()
  const warnings = []
  let context
  const goals = new Proxy(service, { get: (target, property) => property === key ? target : Reflect.get(target, property) })
  return {
    service, callbacks, warnings,
    ctx: {
      goals,
      on(name, callback) { callbacks.set(name, callback); return () => callbacks.delete(name) },
      effect(callback) { this.cleanup = callback() },
      agentPresets: { presetForSession(session) { return session.preset } },
      logger: { warn(message) { warnings.push(message) } },
      systemPrompt: {
        context(registration) { context = registration; return () => { context = undefined } },
        refreshContext() {},
      },
    },
    context() { return context },
  }
}
function actor(id = 'session-1', preset = 'governance') {
  const events = []
  return {
    events, blocks: [], completions: 0,
    goal: { id: 'goal-1', revision: 3, maxGoalRounds: 8, roundsStarted: 7, objective: 'local objective', phase: 'active', activation: 'armed' },
    session: { id, preset, header: { cwd: workspace }, snapshotEvents(start) { assert.equal(start, 0); return events } },
    inbox: { nextStep: [], nextTurn: [], prepend(queue, message) { assert.equal(queue, 'next-step'); this.nextStep.unshift(message) } },
  }
}
function reserved(agent) {
  const { id, revision, roundsStarted } = agent.goal
  return { id: 'reserved', source: { kind: 'goal', goalId: id, revision, round: roundsStarted + 1 } }
}
const ref = (agent) => ({ id: agent.goal.id, revision: agent.goal.revision })
const pass = { status: 'ALLOW', code: 'ADMITTED', contract_sha256: 'a'.repeat(64), plan: {
  state: 'READY', recommendations: [{ task_id: 'FEAT-116', action: 'repair', mode: 'resume' }],
} }
const accepted = { status: 'ALLOW', code: 'DELIVERY_ACCEPTED', contract_sha256: 'a'.repeat(64) }
const hold = (code) => ({ status: 'HOLD', code })
const runStep = (fake, agent, messages = [], turn = 1, signal = undefined) => fake.callbacks.get('agent/pre-step')(
  { agent, messages, turn, signal }, async () => ({ kind: 'enter', messages }),
)
mkdirSync(join(workspace, '.governance', 'goal-bridge'), { recursive: true })
writeFileSync(profile, '{}')
"""


@unittest.skipUnless(shutil.which("node"), "Node is unavailable")
class DshGoalHostTests(unittest.TestCase):
    def run_probe(self, probe, *, poison_python=False):
        with tempfile.TemporaryDirectory() as directory:
            env = None
            if poison_python:
                workspace = Path(directory)
                shadow = workspace / ("python.exe" if os.name == "nt" else "python3")
                if os.name == "nt":
                    shutil.copyfile(Path(os.environ["SystemRoot"]) / "System32" / "whoami.exe", shadow)
                else:
                    shadow.write_text("#!/bin/sh\nprintf 'workspace executable ran\\n'\n", encoding="utf-8")
                    shadow.chmod(0o700)
                executable_dir = Path(sys.executable).parent
                if not (executable_dir / shadow.name).is_file():
                    executable = shutil.which(shadow.name)
                    if executable is None:
                        self.skipTest(f"Host {shadow.name} is unavailable")
                    executable_dir = Path(executable).parent
                env = os.environ.copy()
                env["PATH"] = os.pathsep.join((".", directory, str(executable_dir)))
                env["PYTHONHOME"] = str(workspace / "invalid-python-home")
                env.pop("GOVERNANCE_GOAL_BRIDGE", None)
            result = subprocess.run(
                [shutil.which("node"), "--input-type=module", "-", str(_ROOT), directory],
                input=_FAKE_HOST + probe, text=True, encoding="utf-8", capture_output=True,
                timeout=15, cwd=directory if poison_python else None, env=env,
            )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_production_policy_ignores_workspace_python_and_python_home(self):
        self.run_probe(r"""
const fake = host()
const agent = actor()
registerGoalAdmission(fake.ctx)
assert.throws(() => fake.ctx.goals.complete(agent, ref(agent)), /NATIVE_BINDING_REQUIRED/u)
assert.equal((await runStep(fake, agent, [reserved(agent)])).kind, 'reject')
assert.match(agent.blocks[0].message, /GOVERNANCE_RECORD_INVALID/u)

// The only remaining candidates are the host CWD and entries within the consumer workspace.
process.env.PATH = ['.', workspace].join(process.platform === 'win32' ? ';' : ':')
const unavailable = actor()
assert.throws(() => fake.ctx.goals.complete(unavailable, ref(unavailable)), /POLICY_UNAVAILABLE/u)
assert.equal((await runStep(fake, unavailable, [reserved(unavailable)])).kind, 'reject')
assert.match(unavailable.blocks[0].message, /POLICY_UNAVAILABLE/u)
""", poison_python=True)

    def test_native_tree_stops_before_pause_and_flushes_tail_without_fork_seed(self):
        self.run_probe(r"""
const { createGoalTreeBudget } = await import(pathToFileURL(join(repo, 'lib/dsh-native/goal-tree-budget.js')).href)
const fake = host()
const root = actor(), child = actor('child-1'), unrelated = actor('unrelated')
const agents = new Map([root, child, unrelated].map(agent => [agent.session.id, agent]))
const headers = new Map([...agents].map(([id, agent]) => [id, agent.session.header]))
const disk = new Map(), interrupted = [], requests = []
const append = (agent, type, data) => {
  const event = { seq: agent.events.length, type, time: Date.now(), data }
  agent.events.push(event)
  fake.callbacks.get('session/event')?.(agent.session, event)
}
for (const agent of agents.values()) {
  agent.status = 'running'
  agent.session.header.id = agent.session.id
  agent.session.inheritedEventCount = 0
  Object.defineProperty(agent.session, 'seq', { get: () => agent.events.length })
  agent.session.snapshotEvents = (start, end) => agent.events.slice(start, end)
  agent.cancel = () => {
    agent.status = 'idle'
    append(agent, 'step/end', { turn: 1, step: 1 })
    append(agent, 'turn/end', { turn: 1 })
  }
}
child.session.header.origin = 'subagent'
child.session.header.parentSession = root.session.id
append(child, 'assistant/message', { turn: 1, usage: { totalTokens: 3000 } })
child.session.inheritedEventCount = 1
append(root, 'goal/change', { operation: 'create', goal: root.goal })
append(root, 'turn/start', { turn: 1 })
append(root, 'step/start', { turn: 1, step: 1 })
append(root, 'user/message', { source: reserved(root).source })
append(root, 'assistant/message', { turn: 1, usage: { totalTokens: 18 } })
append(root, 'subagent/catalog', { childId: child.session.id })

fake.ctx.agents = agents
fake.ctx.sessions = { get: id => agents.get(id)?.session, async flush(session) {
  disk.set(session.id, [...agents.get(session.id).events])
  return true
} }
fake.ctx.sessionPersistence = { async open(id) {
  return { header: headers.get(id), inheritedEventCount: 0, async read(start, count) {
    return { events: disk.get(id)?.slice(start, start + count) ?? [] }
  }, async close() {} }
} }
fake.ctx.subagents = { interrupt(id, authority) {
  assert.equal(authority.agent, root)
  interrupted.push(id)
  append(child, 'assistant/message', { turn: 1, usage: { totalTokens: 3 } })
  child.cancel()
} }
fake.ctx.goals.pause = (agent, ref) => {
  assert.equal(requests[0].action, 'tree-stop')
  assert.equal(agent, root)
  agent.goal = { ...agent.goal, phase: 'paused', revision: ref.revision + 1 }
}
const budget = createGoalTreeBudget(fake.ctx)
assert.ok(budget)
let grantStop, grantTail
const tail = new Promise(resolve => { grantTail = resolve })
const policy = async (_, request) => {
  requests.push(request)
  if (request.action === 'tree-stop') await new Promise(resolve => { grantStop = resolve })
  else grantTail()
  return { code: request.action === 'tree-stop' ? 'TREE_BUDGET_STOPPED' : 'TREE_TAIL_RECORDED',
    tree_stop: { id: request.tree.id } }
}
const request = { goal_id: root.goal.id, revision: root.goal.revision, usage: { rounds: 0 } }
const outcome = { status: 'ALLOW', budget: { zones: { tokens: { limit: 30 }, wall_clock: { limit: 600 } } } }
assert.equal(budget.watch({ agent: root, root: workspace, request, outcome, policy }), false)
append(child, 'turn/start', { turn: 1 })
append(child, 'step/start', { turn: 1, step: 1 })
append(child, 'assistant/message', { turn: 1, usage: { totalTokens: 18 } })
assert.equal(root.goal.phase, 'active')
assert.equal(requests[0].usage.tokens, 36)
assert.equal(requests[0].tree.observation.sessions, 2)
const stream = fake.callbacks.get('llm/stream')
assert.throws(() => stream({ sessionId: root.session.id }, () => {}), /budget stopped/u)
assert.throws(() => stream({ sessionId: child.session.id }, () => {}), /budget stopped/u)
assert.equal(stream({ sessionId: unrelated.session.id }, () => 'ok'), 'ok')
grantStop()
let deadline
try {
  await Promise.race([tail, new Promise((_, reject) => { deadline = setTimeout(() => reject(new Error('missing tail')), 3000) })])
} finally { clearTimeout(deadline) }
assert.equal(root.goal.phase, 'paused')
assert.deepEqual(interrupted, [child.session.id])
assert.equal(requests[1].tree.id, requests[0].tree.id)
assert.equal(requests[1].usage.tokens, 39)
assert.equal(requests[1].tree.observation.open_steps, 0)
assert.equal(requests[1].tree.observation.flush_failures, 0)
budget.dispose()

// A cold root can be identified by its exact catalog event even if it later cleared the goal.
agents.delete(root.session.id)
disk.get(root.session.id).push({ type: 'goal/change', data: { operation: 'clear' } })
const recovered = createGoalTreeBudget(fake.ctx)
const owner = await recovered.coldRootFor(child)
assert.equal(owner.sessionId, root.session.id)
assert.equal(owner.goalId, root.goal.id)
assert.equal(await recovered.coldRootFor(unrelated), null)
writeFileSync(state, JSON.stringify({ goal_id: root.goal.id, native_dsh: { session_id: root.session.id },
  tree_stop: { id: requests[0].tree.id, revision: request.revision, status: 'SETTLED' } }))
registerGoalAdmission(fake.ctx, { tree: () => recovered })
const manual = { id: 'human', source: { kind: 'user' } }
assert.equal((await runStep(fake, child, [manual])).kind, 'reject')
assert.equal((await runStep(fake, unrelated, [manual])).kind, 'enter')
recovered.dispose()
""")

    def test_native_tree_restores_scope_before_root_and_child_manual_steps(self):
        self.run_probe(r"""
const fake = host()
const root = actor(), child = actor('child-1'), other = actor('other')
root.goal = { ...root.goal, phase: 'paused', activation: 'disarmed', revision: 6 }
child.session.header.origin = 'subagent'
const stop = { id: 'a'.repeat(32), revision: 3, status: 'SETTLED' }
const saved = { goal_id: root.goal.id, native_dsh: { session_id: root.session.id }, tree_stop: stop }
writeFileSync(state, JSON.stringify(saved))
const tree = () => ({ isHeld: () => false, watch() {}, async coldRootFor(agent) {
  return agent === child ? { header: root.session.header, sessionId: root.session.id, goalId: root.goal.id } : null
} })
registerGoalAdmission(fake.ctx, { tree })
const manual = { id: 'human', source: { kind: 'user' } }
assert.equal((await runStep(fake, root, [manual])).kind, 'reject')
assert.equal((await runStep(fake, child, [manual])).kind, 'reject')
assert.equal((await runStep(fake, other, [manual])).kind, 'enter')
writeFileSync(state, JSON.stringify({ ...saved, tree_stop: { ...stop, resumed_revision: 7 } }))
assert.equal((await runStep(fake, root, [manual])).kind, 'enter')
assert.equal((await runStep(fake, child, [manual])).kind, 'enter')
""")

    def test_native_round_admission_then_followup_hold_preserves_manual_messages(self):
        self.run_probe(r"""
const fake = host()
const agent = actor()
const seen = []
const registration = registerGoalAdmission(fake.ctx, { admit: async (root, request) => {
  assert.equal(root, workspace)
  seen.push(request)
  return seen.length === 1 ? pass : hold('BUDGET_LIMIT_REACHED')
} })
assert.equal(registration.registered, true)
assert.equal(fake.context().required, true)
assert.equal(fake.context().interpolate, false)
assert.equal((await runStep(fake, agent, [reserved(agent)])).kind, 'enter')
assert.deepEqual(seen[0].usage, { rounds: 7 }) // last legal reservation may still run
assert.match(fake.context().text({ agent }), /FEAT-116:repair:resume/u)
assert.equal(fake.context().text({ agent: actor('different') }), '')
const manual = { id: 'human', source: { kind: 'user' } }
assert.equal((await runStep(fake, agent, [manual])).kind, 'reject')
assert.equal(seen.length, 2) // subsequent model step rechecks policy
assert.equal(agent.goal.phase, 'blocked')
assert.equal(agent.blocks.length, 1)
assert.deepEqual(agent.inbox.nextStep, [manual])
assert.equal(fake.context().text({ agent }), '')
assert.ok(!fake.warnings.join(' ').includes(agent.goal.objective))
""")

    def test_direct_repair_projection_retains_only_the_exact_native_claim(self):
        self.run_probe(r"""
const fake = host()
const agent = actor()
const foreign = actor('different-session')
agent.events.push({ type: 'goal/change', data: { operation: 'create', goal: agent.goal } })
const configured = { workspace, sessionId: agent.session.id }
const received = []
const rootPolicy = async (_, request) => {
  received.push(request)
  if (!request.direct_repair) return pass
  return { ...pass, direct_repair_attested: true, plan: { ...pass.plan, direct_repair: true,
    work_packages: [{ id: 'repair-main', action: 'repair', instruction: 'Repair only the verified player result' }] } }
}
registerGoalAdmission(fake.ctx, { directRepair: configured, admit: rootPolicy,
  completePolicy: (_, request) => {
    assert.equal(request.action, 'complete')
    assert.ok(!Object.hasOwn(request, 'direct_repair'))
    return hold('DELIVERY_ACCEPTANCE_FAILED')
  },
  tree: () => ({ isHeld: () => false, watch({ request }) {
    assert.ok(!Object.hasOwn(request, 'direct_repair'))
    return false
  } }),
})
assert.equal((await runStep(fake, agent, [reserved(agent)])).kind, 'enter')
assert.deepEqual(received[0].direct_repair, configured)
assert.match(fake.context().text({ agent }), /Trusted native direct repair for the single work package/u)
assert.equal((await runStep(fake, foreign, [reserved(foreign)])).kind, 'enter')
assert.ok(!Object.hasOwn(received[1], 'direct_repair'))
assert.doesNotMatch(fake.context().text({ agent: foreign }), /Trusted native direct repair/u)
assert.equal((await runStep(fake, agent)).kind, 'enter')
assert.equal(received[2].direct_repair.contractSha256, pass.contract_sha256)
assert.throws(() => fake.ctx.goals.complete(agent, ref(agent)), /DELIVERY_ACCEPTANCE_FAILED/u)
agent.session.preset = 'standard'
assert.equal((await runStep(fake, agent)).kind, 'enter')
assert.ok(!Object.hasOwn(received[3], 'direct_repair'))
agent.session.preset = 'governance'
agent.goal = { ...agent.goal, id: 'other-goal' }
assert.equal((await runStep(fake, agent, [reserved(agent)], 2)).kind, 'enter')
assert.ok(!Object.hasOwn(received[4], 'direct_repair'))

agent.events.push({ type: 'goal/change', data: { operation: 'clear' } },
  { type: 'goal/change', data: { operation: 'create', goal: agent.goal } })
const restarted = host()
registerGoalAdmission(restarted.ctx, { directRepair: configured, admit: rootPolicy })
assert.equal((await runStep(restarted, agent, [reserved(agent)], 3)).kind, 'enter')
assert.ok(!Object.hasOwn(received[5], 'direct_repair'))
""")

    def test_completion_wrapper_keeps_scope_after_restart_and_restores_ownership(self):
        self.run_probe(r"""
const fake = host()
const agent = actor()
let completionPolicy = hold('DELIVERY_ACCEPTANCE_FAILED')
let attempts = 0
const registration = registerGoalAdmission(fake.ctx, { admit: async () => pass, completePolicy: (_, request) => {
  assert.equal(request.action, 'complete')
  attempts++
  return completionPolicy
} })
assert.equal(registration.registered, true)
assert.throws(() => fake.ctx.goals.complete(agent, ref(agent)), /DELIVERY_ACCEPTANCE_FAILED/u)
assert.equal(agent.completions, 0)
const other = actor('session-2', 'standard')
assert.equal(fake.ctx.goals.complete(other, ref(other)).phase, 'complete')
assert.equal(attempts, 1) // profile presence alone does not opt in a different preset
assert.equal((await runStep(fake, agent, [reserved(agent)])).kind, 'enter')
completionPolicy = accepted
assert.equal(fake.ctx.goals.complete(agent, ref(agent)).phase, 'complete')
assert.equal((await runStep(fake, agent)).kind, 'enter') // native wrap-up after successful completion
registration.dispose()
assert.equal(Object.hasOwn(fake.service, 'complete'), false)
assert.equal(fake.callbacks.size, 0)

rmSync(profile)
writeFileSync(state, JSON.stringify({ goal_id: 'goal-1', native_dsh: { session_id: 'session-1' } }))
const restarted = host()
const resumed = actor('session-1', 'standard')
registerGoalAdmission(restarted.ctx, { completePolicy: () => ({ status: 'NOT_CONFIGURED' }) })
assert.throws(() => restarted.ctx.goals.complete(resumed, ref(resumed)), /INVALID_POLICY_REPLY/u)
assert.equal(resumed.completions, 0)
const untouched = actor('session-other', 'standard')
assert.equal(restarted.ctx.goals.complete(untouched, ref(untouched)).phase, 'complete')

writeFileSync(state, '{ corrupt')
const uncertain = host()
let observed = 0
registerGoalAdmission(uncertain.ctx, { completePolicy: () => { observed++; return hold('STATE_INVALID') } })
assert.throws(() => uncertain.ctx.goals.complete(resumed, ref(resumed)), /STATE_INVALID/u)
assert.equal(observed, 1)
assert.equal(resumed.completions, 0)
""")

    def test_usage_counts_only_this_goal_and_does_not_lose_settled_tokens(self):
        self.run_probe(r"""
const agent = actor()
agent.goal.roundsStarted = 2
const event = (type, time, data) => ({ type, time, data })
agent.events.push(
  event('assistant/message', 5, { turn: 1, usage: { totalTokens: 9000 } }),
  event('goal/change', 10, { operation: 'create', goal: { id: 'goal-1' } }),
  event('turn/start', 100, { turn: 2 }),
  event('step/start', 200, { turn: 2 }),
  event('user/message', 220, { source: { kind: 'goal', goalId: 'goal-1', round: 1 } }),
  event('assistant/attempt', 250, { turn: 2 }),
  event('assistant/message', 290, { turn: 2, usage: { totalTokens: 15 } }),
  event('step/end', 300, { turn: 2 }),
  event('turn/end', 301, { turn: 2 }),
  event('turn/start', 400, { turn: 3 }),
  event('step/start', 500, { turn: 3 }),
  event('user/message', 520, { source: { kind: 'goal', goalId: 'goal-1', round: 2 } }),
  event('assistant/message', 540, { turn: 3, usage: { totalTokens: 5 } }),
)
assert.deepEqual(settledGoalUsage(agent.session, agent.goal, 600), { rounds: 1, tokens: 20, seconds: 0.2 })
agent.events.push(event('step/end', 650, { turn: 3 }), event('turn/end', 660, { turn: 3 }))
assert.deepEqual(settledGoalUsage(agent.session, agent.goal, 670), { rounds: 2, tokens: 20, seconds: 0.25 })
""")


if __name__ == "__main__":
    unittest.main()
