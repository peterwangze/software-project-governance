"""FEAT-116 adapter behavior over fake Cordis/native goal surfaces."""

import shutil
import subprocess
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
    def run_probe(self, probe):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [shutil.which("node"), "--input-type=module", "-", str(_ROOT), directory],
                input=_FAKE_HOST + probe, text=True, encoding="utf-8", capture_output=True,
                timeout=15,
            )
        self.assertEqual(0, result.returncode, result.stderr)

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
