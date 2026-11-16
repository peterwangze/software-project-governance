import { createHash } from 'node:crypto'
import { closeSync, linkSync, lstatSync, openSync, readFileSync, realpathSync, unlinkSync, writeFileSync } from 'node:fs'
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from 'node:path'

const MODE = 'workspace-write'
const CHECK_TIMEOUT_MS = 90_000
const SESSION_ID = /^session-[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/u

const objectWith = (value, keys) => value !== null && typeof value === 'object'
  && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key))
const samePath = (left, right) => relative(left, right) === ''
const sha256 = (value) => createHash('sha256').update(value).digest('hex')

function inside(root, path) {
  const name = relative(root, path)
  return !isAbsolute(name) && name !== '..' && !name.startsWith(`..${sep}`)
}

function absolute(value) {
  return typeof value === 'string' && value.length <= 1024 && !value.includes('\0') && isAbsolute(value)
}

function directory(path) {
  if (!absolute(path)) throw new TypeError('expected absolute directory')
  const canonical = realpathSync(path)
  if (!samePath(canonical, resolve(path)) || !lstatSync(canonical).isDirectory()) {
    throw new TypeError('expected canonical directory')
  }
  return canonical
}

function scopedPath(root, name) {
  if (typeof name !== 'string' || !name || name.length > 512 || name.includes('\0')
      || isAbsolute(name) || name.includes(':') || name.split(/[\\/]/u).includes('..')) {
    throw new TypeError('expected relative workspace path')
  }
  const path = resolve(root, name)
  if (!inside(root, path)) throw new TypeError('path escapes workspace')
  return path
}

function checkConfig(value, workspace, build) {
  if (!objectWith(value, build ? ['command', 'cwd', 'artifact'] : ['command', 'cwd'])
      || typeof value.command !== 'string' || !value.command.trim() || value.command.length > 4096
      || /[\r\n\0]/u.test(value.command)) throw new TypeError('invalid execution recipe')
  const cwd = directory(scopedPath(workspace, value.cwd))
  const artifact = build ? scopedPath(workspace, value.artifact) : null
  if (build && (samePath(artifact, workspace) || !artifact.toLowerCase().endsWith('.html'))) {
    throw new TypeError('expected production HTML entry')
  }
  return { command: value.command, cwd, artifact }
}

function preflightConfig(value) {
  if (!objectWith(value, ['sessionId', 'workspace', 'receipt', 'browser', 'build'])
      || typeof value.sessionId !== 'string' || !SESSION_ID.test(value.sessionId)
      || !absolute(value.receipt) || !value.receipt.toLowerCase().endsWith('.json')) {
    throw new TypeError('invalid delivery preflight config')
  }
  const workspace = directory(value.workspace)
  const receipt = join(directory(dirname(value.receipt)), basename(value.receipt))
  if (inside(workspace, receipt)) throw new TypeError('receipt must be outside the workspace')
  return { sessionId: value.sessionId, workspace, receipt,
    browser: checkConfig(value.browser, workspace, false), build: checkConfig(value.build, workspace, true) }
}

function exists(path) {
  try { lstatSync(path); return true }
  catch (error) {
    if (error?.code === 'ENOENT') return false
    throw error
  }
}

function readArtifact(path) {
  try {
    const info = lstatSync(path)
    if (!info.isFile() || info.nlink !== 1 || info.size < 1 || info.size > 5 * 1024 * 1024
        || !samePath(path, realpathSync(path))) return null
    return sha256(readFileSync(path))
  } catch { return null }
}

function journey(result) {
  const stdout = result.stdout?.text
  if (typeof stdout !== 'string' || stdout.length > 64 * 1024) return null
  try {
    const value = JSON.parse(stdout.trimEnd().split(/\r?\n/u).at(-1))
    if (value?.player_path_executed !== true) return null
    if (result.exitCode === 0 && value?.status === 'PASS') return 'PASS'
    if (result.exitCode === 1 && value?.status === 'FAIL') return 'FAIL'
  } catch { /* The browser did not report an executed journey. */ }
  return null
}

function blocked(code, details = {}) { return { status: 'BLOCKED', code, ...details } }

function assess(result, recipe) {
  const { sandbox, exitCode } = result
  if (sandbox?.mode !== MODE || !['partial', 'full'].includes(sandbox.enforcement)) {
    return blocked('SANDBOX_UNCONFIRMED')
  }
  const facts = { exit_code: Number.isInteger(exitCode) ? exitCode : null,
    mode: sandbox.mode, enforcement: sandbox.enforcement }
  if (sandbox.runnerFailed || sandbox.denied !== false) return blocked('SANDBOX_DENIED', facts)
  if (result.timedOut || result.aborted || result.signal) return blocked('EXECUTION_INTERRUPTED', facts)
  const stderr = typeof result.stderr?.text === 'string' ? result.stderr.text : ''
  if (/\bspawn\s+EPERM\b/iu.test(stderr)) {
    return blocked(/\besbuild\b/iu.test(stderr) ? 'ESBUILD_SPAWN_EPERM' : 'PROCESS_SPAWN_EPERM', facts)
  }
  if (recipe.artifact) {
    if (exitCode !== 0) return blocked('BUILD_COMMAND_FAILED', facts)
    const digest = readArtifact(recipe.artifact)
    if (!digest) return blocked('BUILD_ENTRY_MISSING', facts)
    return { status: 'PASS', code: 'BUILD_EXECUTED', artifact_sha256: digest, ...facts }
  }
  const observed = journey(result)
  if (!observed) return blocked('BROWSER_JOURNEY_UNCONFIRMED', facts)
  return { status: 'PASS', code: 'BROWSER_EXECUTED', journey: observed, ...facts }
}

function workspaceOf(agent) {
  try { return directory(agent?.session?.header?.cwd) }
  catch { return null }
}

function getPolicy(ctx, agent, workspace) {
  const current = workspaceOf(agent)
  if (ctx.agents.get(agent.session.id) !== agent || ctx.goals.get(agent)
      || ctx.agentPresets.presetForSession(agent.session) !== 'governance'
      || ctx.shell.sandboxMode !== MODE || !current || !samePath(current, workspace)) return null
  const policy = ctx.sandboxPolicy.resolve({ session: agent.session })
  if (policy?.mode !== MODE || policy.sessionId !== agent.session.id
      || !absolute(policy.workspaceRoot) || !samePath(policy.workspaceRoot, workspace)
      || (policy.additionalWritableRoots?.length ?? 0) !== 0) return null
  return policy
}

async function executeCheck(ctx, agent, signal, workspace, recipe) {
  if (signal.aborted) return blocked('EXECUTION_INTERRUPTED')
  try {
    const policy = getPolicy(ctx, agent, workspace)
    if (!policy) return blocked('SESSION_POLICY_MISMATCH')
    if (recipe.artifact && exists(recipe.artifact)) return blocked('BUILD_ENTRY_NOT_FRESH')
    if (!samePath(directory(recipe.cwd), recipe.cwd)) return blocked('RECIPE_WORKDIR_CHANGED')
    const workdir = await ctx.workingDirectory.ensure(agent, signal)
    if (!absolute(workdir) || !samePath(workdir, workspace)) return blocked('SESSION_WORKDIR_MISMATCH')
    const spec = ctx.shell.resolve({ command: recipe.command, workdir: recipe.cwd, signal,
      timeoutMs: CHECK_TIMEOUT_MS, onExpiry: 'kill', dshEnv: ctx.shellEnv.collect({ agent, signal }),
      sandboxPolicy: policy })
    if (spec.sandboxPolicy !== policy || !samePath(spec.workdir, recipe.cwd)) return blocked('RECIPE_NOT_CONFINED')
    const result = await (await ctx.shell.execute(spec)).result()
    if (!getPolicy(ctx, agent, workspace)) return blocked('SESSION_POLICY_MISMATCH')
    return assess(result, recipe)
  } catch {
    return blocked(signal.aborted ? 'EXECUTION_INTERRUPTED' : 'NATIVE_SHELL_FAILED')
  }
}

function claimOnce(receipt) {
  try { closeSync(openSync(`${receipt}.claim`, 'wx', 0o600)); return true }
  catch (error) {
    if (error?.code === 'EEXIST') return false
    throw error
  }
}

function publishReceipt(receipt, record) {
  const staged = `${receipt}.tmp`
  writeFileSync(staged, `${JSON.stringify(record, null, 2)}\n`, { flag: 'wx', mode: 0o600 })
  try { linkSync(staged, receipt) }
  finally { unlinkSync(staged) }
}

export const deliveryPreflightServices = [
  'agents', 'agentPresets', 'goals', 'shell', 'sandboxPolicy', 'shellEnv', 'workingDirectory',
]

/** Opt in from trusted host configuration for one disposable native Session. */
export function registerDeliveryPreflight(ctx, value) {
  const config = preflightConfig(value)
  const { workspace, receipt, sessionId } = config
  const abort = new AbortController()
  let owner
  const report = (code) => ctx.logger?.info?.(`software-project-governance: delivery preflight (${code})`)
  ctx.on('agent/pre-step', ({ agent }, next) => {
    const project = workspaceOf(agent)
    if (agent?.session?.id === sessionId || (project && samePath(project, workspace))) {
      return { kind: 'reject' }
    }
    return next()
  }, true)
  ctx.on('agent/disposed', ({ agent }) => {
    if (agent === owner) abort.abort()
  })
  ctx.effect(() => () => abort.abort())
  ctx.on('agent/created', ({ agent, source }) => {
    if (source !== 'startup' || agent?.session?.id !== sessionId || owner) return
    const project = workspaceOf(agent)
    if (!project || !samePath(project, workspace)) return
    owner = agent
    void (async () => {
      if (exists(receipt) || !claimOnce(receipt)) return
      const browser = await executeCheck(ctx, agent, abort.signal, workspace, config.browser)
      const build = await executeCheck(ctx, agent, abort.signal, workspace, config.build)
      const pass = browser.status === 'PASS' && build.status === 'PASS'
      const record = { schema_version: 1, session_id: sessionId, workspace,
        recipe_sha256: sha256(JSON.stringify({ browser: config.browser, build: config.build })),
        status: pass ? 'PASS' : 'BLOCKED', browser, build }
      publishReceipt(receipt, record)
      report(pass ? 'PREFLIGHT_PASSED' : 'PREFLIGHT_BLOCKED')
    })().catch(() => report('PREFLIGHT_RECEIPT_FAILED'))
  })
  report('PREFLIGHT_ARMED')
}
