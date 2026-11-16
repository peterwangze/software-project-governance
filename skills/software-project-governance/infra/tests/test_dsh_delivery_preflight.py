"""Exercise the delivery preflight hooks through a disposable native-host fixture."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
_NODE = shutil.which("node")

_HOST = r"""
import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { setImmediate } from 'node:timers/promises'
import { pathToFileURL } from 'node:url'

const [, , repo, temp] = process.argv
const { registerDeliveryPreflight } = await import(
  pathToFileURL(join(repo, 'lib', 'dsh-native', 'delivery-preflight.js')).href
)
const root = realpathSync(temp)
const targetId = 'session-12345678-abcd-1234-abcd-123456789abc'
const otherId = 'session-87654321-abcd-1234-abcd-123456789abc'
const unrelated = join(root, 'unrelated')
mkdirSync(unrelated, { recursive: true })
const candidate = '<html>fresh production output</html>'

function fixture(name) {
  const directory = join(root, name)
  const workspace = join(directory, 'workspace with spaces')
  mkdirSync(join(workspace, 'product', 'dist'), { recursive: true })
  return {
    entry: join(workspace, 'product', 'dist', 'index.html'),
    config: {
      sessionId: targetId, workspace, receipt: join(directory, 'native-receipt.json'),
      browser: { command: 'browser-check', cwd: 'product' },
      build: { command: 'production-build', cwd: 'product', artifact: 'product/dist/index.html' },
    },
  }
}

function actor(cwd, id = targetId) {
  return { session: { id, header: { cwd } } }
}

function host(config, options = {}) {
  const callbacks = new Map()
  const preStepOrder = []
  const executions = []
  const agent = actor(config.workspace)
  const policy = {
    mode: 'workspace-write', sessionId: agent.session.id, workspaceRoot: config.workspace,
    additionalWritableRoots: [], ...options.policy,
  }
  const ctx = {
    on(event, callback, first) {
      callbacks.set(event, callback)
      if (event === 'agent/pre-step') preStepOrder.push(first)
    },
    effect(register) { this.dispose = register() },
    agents: { get: () => options.foreignOwner ? actor(config.workspace) : agent },
    agentPresets: { presetForSession: () => options.preset ?? 'governance' },
    goals: { get: () => options.goal },
    workingDirectory: { ensure: async () => options.workdir ?? config.workspace },
    sandboxPolicy: { resolve: () => policy },
    shellEnv: { collect: () => ({ FIXTURE_NATIVE_ENV: 'present' }) },
    shell: {
      sandboxMode: options.shellMode ?? 'workspace-write',
      resolve: (spec) => spec,
      execute(spec) {
        executions.push(spec.command)
        assert.equal(spec.sandboxPolicy, policy)
        assert.equal(spec.workdir, join(config.workspace, 'product'))
        assert.equal(spec.dshEnv.FIXTURE_NATIVE_ENV, 'present')
        assert.ok(spec.timeoutMs > 0 && spec.timeoutMs <= 120_000)
        assert.equal(spec.onExpiry, 'kill')
        const isBrowser = spec.command === config.browser.command
        const isBuild = spec.command === config.build.command
        assert.ok(isBrowser || isBuild)
        const browserStatus = options.browserStatus ?? 'PASS'
        const browserExit = options.browserExit ?? (browserStatus === 'PASS' ? 0 : 1)
        const program = isBrowser
          ? `console.log('journey fixture ran'); console.log(${JSON.stringify(JSON.stringify({ status: browserStatus, player_path_executed: !options.missingProof }))}); process.exit(${browserExit})`
          : options.buildEperm
            ? `console.error('esbuild: spawn EPERM'); process.exit(1)`
            : options.omitEntry
              ? `console.log('build exited without creating the production entry')`
              : `import { writeFileSync } from 'node:fs'; writeFileSync('dist/index.html', ${JSON.stringify(candidate)})`
        const result = spawnSync(process.execPath, ['--input-type=module', '-e', program], {
          cwd: spec.workdir, encoding: 'utf8', shell: false, windowsHide: true, timeout: 5000,
        })
        assert.ifError(result.error)
        return { result: async () => ({
          sandbox: { mode: 'workspace-write', enforcement: 'partial', denied: false, ...options.observedSandbox },
          exitCode: result.status, signal: result.signal,
          stdout: { text: result.stdout }, stderr: { text: result.stderr },
        }) }
      },
    },
  }
  registerDeliveryPreflight(ctx, config)
  return {
    agent, executions, preStepOrder,
    created: (who = agent, source = 'startup') => callbacks.get('agent/created')({ agent: who, source }),
    step: (who, next) => callbacks.get('agent/pre-step')({ agent: who }, next),
  }
}

async function record(config) {
  const deadline = Date.now() + 5000
  while (!existsSync(config.receipt) && Date.now() < deadline) await setImmediate()
  return JSON.parse(readFileSync(config.receipt, 'utf8'))
}
"""


@unittest.skipUnless(_NODE, "Node is unavailable")
class DshDeliveryPreflightTests(unittest.TestCase):
    def run_probe(self, *probes):
        with tempfile.TemporaryDirectory() as directory:
            for probe in probes:
                result = subprocess.run(
                    [_NODE, "--input-type=module", "-", str(_ROOT), directory],
                    input=_HOST + probe, text=True, encoding="utf-8", capture_output=True, timeout=25,
                )
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_native_startup_scope_and_zero_model_step(self):
        self.run_probe(r"""
const { config } = fixture('scope')
const native = host(config)
let modelCalls = 0
const model = () => { modelCalls++; return { kind: 'enter' } }
assert.deepEqual(native.preStepOrder, [true])
assert.deepEqual(native.step(native.agent, model), { kind: 'reject' })
assert.deepEqual(native.step(actor(config.workspace, otherId), model), { kind: 'reject' })
assert.deepEqual(native.step(actor(unrelated), model), { kind: 'reject' })
assert.deepEqual(native.step(actor(unrelated, otherId), model), { kind: 'enter' })
assert.equal(modelCalls, 1)
native.created(actor(config.workspace, otherId))
native.created(actor(unrelated))
native.created(native.agent, 'message')
await setImmediate()
assert.deepEqual(native.executions, [])
assert.ok(!existsSync(config.receipt))
native.created()
assert.equal((await record(config)).status, 'PASS')
assert.deepEqual(native.executions, ['browser-check', 'production-build'])
""")

    def test_pass_and_executed_broken_journey_are_distinguished(self):
        self.run_probe(r"""
for (const [browserStatus, exit] of [['PASS', 0], ['FAIL', 1]]) {
  const { config, entry } = fixture(browserStatus)
  const native = host(config, { browserStatus })
  native.created()
  const receipt = await record(config)
  assert.equal(receipt.status, 'PASS')
  assert.equal(receipt.session_id, targetId)
  assert.deepEqual(receipt.browser, {
    status: 'PASS', code: 'BROWSER_EXECUTED', journey: browserStatus,
    exit_code: exit, mode: 'workspace-write', enforcement: 'partial',
  })
  assert.equal(receipt.build.code, 'BUILD_EXECUTED')
  assert.equal(receipt.build.artifact_sha256, createHash('sha256').update(candidate).digest('hex'))
  assert.equal(readFileSync(entry, 'utf8'), candidate)
}
""")

    def test_missing_native_scope_and_unconfined_execution_are_refused(self):
        self.run_probe(r"""
const refused = [
  { foreignOwner: true },
  { goal: { id: 'live-goal' } },
  { preset: 'different-preset' },
  { shellMode: 'read-only' },
  { policy: { mode: 'danger-full-access' } },
  { policy: { sessionId: otherId } },
  { policy: { workspaceRoot: unrelated } },
  { policy: { additionalWritableRoots: [unrelated] } },
]
for (let index = 0; index < refused.length; index++) {
  const { config } = fixture(`wrong-policy-${index}`)
  const native = host(config, refused[index])
  native.created()
  const receipt = await record(config)
  assert.equal(receipt.status, 'BLOCKED')
  assert.equal(receipt.browser.code, 'SESSION_POLICY_MISMATCH')
  assert.equal(receipt.build.code, 'SESSION_POLICY_MISMATCH')
  assert.deepEqual(native.executions, [])
}
for (const [options, expected, commands] of [
  [{ workdir: unrelated }, 'SESSION_WORKDIR_MISMATCH', []],
  [{ observedSandbox: { mode: 'read-only' } }, 'SANDBOX_UNCONFIRMED', ['browser-check', 'production-build']],
]) {
  const { config } = fixture(expected)
  const native = host(config, options)
  native.created()
  const receipt = await record(config)
  assert.equal(receipt.status, 'BLOCKED')
  assert.equal(receipt.browser.code, expected)
  assert.equal(receipt.build.code, expected)
  assert.deepEqual(native.executions, commands)
}
""")

    def test_zero_exit_requires_a_fresh_build_and_valid_journey(self):
        self.run_probe(r"""
const stale = fixture('stale')
writeFileSync(stale.entry, 'existing production output')
const native = host(stale.config)
native.created()
const staleReport = await record(stale.config)
assert.equal(staleReport.status, 'BLOCKED')
assert.equal(staleReport.build.code, 'BUILD_ENTRY_NOT_FRESH')
assert.deepEqual(native.executions, ['browser-check'])
assert.equal(readFileSync(stale.entry, 'utf8'), 'existing production output')

for (const [options, field, expected] of [
  [{ omitEntry: true }, 'build', 'BUILD_ENTRY_MISSING'],
  [{ buildEperm: true }, 'build', 'ESBUILD_SPAWN_EPERM'],
  [{ browserStatus: 'FAIL', browserExit: 0 }, 'browser', 'BROWSER_JOURNEY_UNCONFIRMED'],
  [{ browserStatus: 'PASS', browserExit: 1 }, 'browser', 'BROWSER_JOURNEY_UNCONFIRMED'],
  [{ missingProof: true }, 'browser', 'BROWSER_JOURNEY_UNCONFIRMED'],
]) {
  const { config } = fixture(`${expected}-${options.missingProof ? 'missing-proof' : options.browserExit ?? 'build'}`)
  host(config, options).created()
  const receipt = await record(config)
  assert.equal(receipt.status, 'BLOCKED')
  assert.equal(receipt[field].code, expected)
  assert.equal(receipt[field].artifact_sha256, undefined)
}
""")

    def test_duplicate_registration_and_restart_leave_original_receipt_untouched(self):
        self.run_probe(r"""
const { config } = fixture('claim')
const first = host(config)
const duplicate = host(config)
first.created()
first.created()
duplicate.created()
assert.equal((await record(config)).status, 'PASS')
assert.deepEqual(first.executions, ['browser-check', 'production-build'])
assert.deepEqual(duplicate.executions, [])
writeFileSync(join(root, 'original-receipt'), readFileSync(config.receipt))

const interrupted = fixture('interrupted')
writeFileSync(`${interrupted.config.receipt}.claim`, '', { flag: 'wx' })
""", r"""
const { config } = fixture('claim')
const restarted = host(config)
restarted.created()
await setImmediate()
assert.deepEqual(restarted.executions, [])
assert.deepEqual(readFileSync(config.receipt), readFileSync(join(root, 'original-receipt')))

const interrupted = fixture('interrupted')
const afterCrash = host(interrupted.config)
afterCrash.created()
await setImmediate()
assert.deepEqual(afterCrash.executions, [])
assert.ok(!existsSync(interrupted.config.receipt))
""")


if __name__ == "__main__":
    unittest.main()
