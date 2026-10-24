/** FEAT-102 S-A2_ONLY: candidate L falsification, never a product module. */
import { createRequire } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { resolve, dirname, join } from 'node:path';
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs';
import { spawn } from 'node:child_process';
import { performance } from 'node:perf_hooks';
import assert from 'node:assert/strict';

const [manifestArg, sandboxArg, mode, scenarioName] = process.argv.slice(2);
const manifest = resolve(manifestArg ?? '');
const sandbox = resolve(sandboxArg ?? '');
const repository = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
assert.equal(sandbox, join(repository, '.governance/sandboxes/feat102-a2'));
for (const key of ['DSH_HOME', 'TEMP', 'TMP', 'DSH_AGENTS_HOME']) assert.equal(resolve(process.env[key] ?? ''), sandbox, `${key} must be isolated`);
mkdirSync(sandbox, { recursive: true });

if (mode !== '--worker') {
  const commands = [];
  const results = [];
  const planned = ['normal-first', 'unload-register-flight', 'normal-last', 'preloaded-first', 'mount-delay', 'pre-register-delay', 'base-pending', 'broken-registration'];
  const executeFirst = ['normal-first', 'unload-register-flight'];
  for (const name of executeFirst) {
    const args = [fileURLToPath(import.meta.url), manifest, sandbox, '--worker', name];
    const command = { id: `A2-RUN-${String(commands.length + 1).padStart(2, '0')}`, executable: process.execPath, args,
      started: new Date().toISOString(), impact_read: [manifest, dirname(manifest)], impact_write: [sandbox],
      access: 'SDK read-only; runtime writes only validated task sandbox; no network/model provider/profile installation' };
    const outcome = await new Promise(resolveExit => {
      const child = spawn(process.execPath, args, { env: process.env, cwd: repository, stdio: ['ignore', 'pipe', 'pipe'] });
      let stdout = '', stderr = '', killed = false;
      child.stdout.on('data', chunk => { stdout += chunk; });
      child.stderr.on('data', chunk => { stderr += chunk; });
      const timeout = setTimeout(() => { killed = true; child.kill(); }, 9000);
      child.on('error', error => { clearTimeout(timeout); resolveExit({ error: String(error), stdout, stderr }); });
      child.on('exit', (exit_code, signal) => { clearTimeout(timeout); resolveExit({ exit_code, signal, killed, stdout, stderr }); });
    });
    Object.assign(command, outcome, { completed: new Date().toISOString() }); commands.push(command);
    const path = join(sandbox, `${name}.json`);
    const result = existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : { name, conclusion: 'FAIL_NO_RAW_ARTIFACT' };
    if (outcome.killed) result.conclusion = 'FAIL_PROCESS_DEADLINE';
    results.push(result);
    if (result.conclusion !== 'PASS_FIXTURE_ONLY') break;
  }
  const report = { candidate: 'L', authorizedSlice: 'S-A2_ONLY', productWiringAuthorized: false, commands, results,
    notRun: planned.filter(name => !results.some(result => result.name === name)),
    conclusion: results.some(result => result.conclusion !== 'PASS_FIXTURE_ONLY') ? 'FAIL_CANDIDATE_L' : 'PARTIAL_CHECKPOINT_REVIEW_REQUIRED' };
  writeFileSync(join(sandbox, 'result.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ conclusion: report.conclusion, results: results.map(({ name, conclusion }) => ({ name, conclusion })), notRun: report.notRun }));
  process.exitCode = results.some(result => result.conclusion === 'FAIL_NO_RAW_ARTIFACT') ? 2 : 0;
} else {
  const sdkRequire = createRequire(manifest);
  const context = { cliManifest: manifest, cli: JSON.parse(readFileSync(manifest, 'utf8')).version, node: process.version, sandbox, repository,
    repositoryHasHostNodeModules: existsSync(join(repository, 'node_modules/@deepseek-ai/dsh')), resolved: {} };
  async function sdk(name) {
    const specifier = `@deepseek-ai/${name}`;
    const path = sdkRequire.resolve(specifier); context.resolved[specifier] = path;
    return import(pathToFileURL(path).href);
  }
  const { resolveConfig } = await sdk('cordis');
  const { Group } = await sdk('cordis-plugin-loader');
  const RegistryModule = await sdk('dsh-agent-preset-registry');
  const Native = (await sdk('dsh-agent-preset')).default;
  const { boot } = await sdk('dsh-app-boot');
  const Web = (await sdk('dsh-api-session-controller')).default;
  const Persona = await sdk('dsh-persona');
  const Filesystem = await sdk('dsh-skill-filesystem');
  const builtins = { native: Native, registry: RegistryModule.default, group: Group, persona: Persona, filesystem: Filesystem };
  for (const [key, name] of Object.entries({ projections: 'dsh-session-projection', sessions: 'dsh-session', agents: 'dsh-agent',
    llm: 'dsh-llm', tools: 'dsh-tools', prompt: 'dsh-system-prompt', skills: 'dsh-skill', typert: 'dsh-typert-registry',
    defaultModel: 'dsh-agent-default-model', loop: 'dsh-agent-loop' })) builtins[key] = (await sdk(name)).default;
  const state = { name: scenarioName, candidate: 'L', conclusion: 'IN_PROGRESS', context,
    inject: { loader: { await: true }, agentPresets: {} }, events: [], unhandled: [], checked: 0, activationCount: 0 };
  const rawPath = join(sandbox, `${scenarioName}.json`);
  const origin = performance.now();
  const save = () => writeFileSync(rawPath, JSON.stringify(state, null, 2) + '\n');
  const mark = (event, data = {}) => { state.events.push({ sequence: state.events.length, ms: Number((performance.now() - origin).toFixed(3)), event, ...data }); save(); };
  process.on('unhandledRejection', error => { state.unhandled.push(String(error)); mark('unhandled-rejection', { error: String(error) }); });
  const defer = () => Promise.withResolvers();
  const mountGate = defer(), mountEntered = defer(), applyEntered = defer(), admissionGate = defer();
  let ctx, ownFiber, ownDispose, cleanupComplete = false, disposed = false;
  async function deadline(promise, label, ms = 2500) {
    let timer;
    try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`TIMEOUT ${label}`)), ms); })]); }
    finally { clearTimeout(timer); }
  }
  const base = { id: 'standard', plugins: [
    { id: 'persona', name: 'cordis:persona', config: { prefix: 'USER PREFIX', suffix: 'USER SUFFIX', includeRuntimeContext: false } },
    { id: 'skills', name: 'cordis:filesystem', config: { customSkillDirs: [join(sandbox, 'user-skills')], includeDefaultRoots: false, watch: false, agentsHome: sandbox } },
    { id: 'group', name: 'cordis:group', group: true, config: [{ id: 'disabled', name: 'cordis:absent-disabled', disabled: { __jsExpr: 'true' } }] }
  ] };
  const original = structuredClone(base);
  builtins.mountGate = { async apply() { mark('mount-barrier-enter'); mountEntered.resolve(); await mountGate.promise; mark('mount-barrier-leave'); } };
  builtins.io = { apply(child) {
    child.provide('fileUploads', { registerAgentResolver: () => () => {} });
    for (const key of ['attachments', 'workspaceRegistry', 'sessionQuery', 'fs']) child.provide(key, {});
  } };
  builtins.web = { inject: ['agents', 'agentDefaultModel', 'sessions', 'sessionProjections', 'typert', 'fileUploads'], apply(child) {
    new Web(child, resolveConfig(Web, { nativeOpen: false }));
  } };
  builtins.own = { inject: state.inject, async apply(child) {
    state.activationCount++; ownFiber = child.fiber; mark('own-activation-start', { count: state.activationCount, inertia: Boolean(ownFiber.inertia) }); applyEntered.resolve();
    const off = child.on('app-boot/config-reload', () => {});
    child.effect(() => async () => {
      mark('cleanup-start'); off();
      if (ownDispose) await ownDispose();
      cleanupComplete = true; mark('cleanup-complete');
    });
    // No root.await, list, or fallback-capable resolve is used before the public audit establishes no pending base children.
    const candidates = [...child.loader.entries()].filter(entry => entry.options.name === 'cordis:native' && entry.fiber?.config?.id === 'standard');
    mark('base-source-scan', { count: candidates.length });
    assert.equal(candidates.length, 1); const entry = candidates[0];
    assert.equal(entry.disabled, false); assert.equal(entry.fiber.state, 2); assert.equal(entry.fiber.inertia, undefined);
    mark('base-fiber-settled');
    const mounts = RegistryModule.livePresetMounts(child.root.fiber).filter(mount => mount.presetId === 'standard');
    assert.equal(mounts.length, 1);
    const audit = await RegistryModule.auditRows(mounts[0].tree);
    mark('base-public-row-audit', audit);
    if (audit.pending.length || audit.failed.length) throw new Error('BASE_AUDIT_UNSAFE_FOR_ACTIVATION: pending or failed base children; do not invoke fallback-root diagnostic');
    const baseMetadata = await child.agentPresets.resolve('standard');
    mark('base-registry-audit', baseMetadata); assert.equal(baseMetadata.broken, undefined);
    const accepted = entry.fiber.config;
    const definition = structuredClone(accepted); definition.id = 'governance';
    definition.plugins[0].config.prefix += '\nGOVERNANCE PROBE';
    definition.plugins[1].config.customSkillDirs.push(join(repository, 'skills'), join(repository, 'adapters/dsh/skill-shims'));
    assert.deepEqual(accepted.plugins, original.plugins); assert.deepEqual(definition.plugins[2], original.plugins[2]);
    for (const [plugin, row] of [[Persona, definition.plugins[0]], [Filesystem, definition.plugins[1]]]) { resolveConfig(plugin, row.config); state.checked++; }
    if (scenarioName === 'pre-register-delay') { mark('admission-barrier-enter'); await admissionGate.promise; }
    if (scenarioName === 'unload-register-flight' || scenarioName === 'mount-delay') definition.plugins.push({ id: 'mount-delay', name: 'cordis:mountGate' });
    if (scenarioName === 'broken-registration') definition.plugins.push({ id: 'bad-row', name: 'cordis:absent-module' });
    mark('register-start'); ownDispose = await child.agentPresets.register(definition); mark('register-complete');
    // Never resolve/list own record inside its activation: diagnostic could fall back to root await.
    mark('own-activation-return');
  } };
  const rows = [
    ...['projections', 'sessions', 'agents', 'llm', 'tools', 'prompt', 'skills', 'typert'].map(name => ({ id: `core-${name}`, name: `cordis:${name}` })),
    { id: 'model', name: 'cordis:defaultModel', config: { provider: 'no-network-provider', model: 'no-model' } },
    { id: 'loop', name: 'cordis:loop', config: { agents: [] } },
    { id: 'registry', name: 'cordis:registry', config: { default: 'governance' } },
    { id: 'io', name: 'cordis:io' }, { id: 'web', name: 'cordis:web' }, { id: 'standard', name: 'cordis:native', config: base }
  ];
  const own = { id: 'own', name: 'cordis:own' };
  if (scenarioName === 'normal-last') rows.push(own); else rows.unshift(own);
  const configPath = join(sandbox, `${scenarioName}.yml`);
  writeFileSync(configPath, JSON.stringify(rows, null, 2)); save();
  try {
    const bootPromise = boot('feat102-a2', configPath, [], child => {
      ctx = child; Object.assign(child.loader.builtins, builtins);
      child.on('internal/status', fiber => { if (fiber.entry?.options.id === 'own') mark('own-fiber-state', { state: fiber.state, inertia: Boolean(fiber.inertia) }); });
    }, pathToFileURL(manifest).href).then(async () => {
      mark('actual-boot-return');
      state.bootLoaderTaskCount = ctx.loader.getTasks().length;
      state.bootEntries = [...ctx.loader.entries()].map(entry => ({ id: entry.options.id, module: entry.options.name,
        state: entry.fiber?.state, inertia: Boolean(entry.fiber?.inertia),
        ...(entry.options.id === 'own' ? { inject: entry.fiber?.inject } : {}) }));
      mark('boot-public-state-snapshot', { loaderTasks: state.bootLoaderTaskCount, own: state.bootEntries.find(entry => entry.id === 'own') });
      const requested = 'governance'; mark('first-lookup-start', { requested });
      state.firstRoster = await ctx.agentPresets.list();
      state.firstLookup = await ctx.agentPresets.resolve(requested); mark('first-lookup-complete', state.firstLookup);
    });
    // Consume immediately to prevent rejected in-flight boot from being an unhandled rejection.
    bootPromise.catch(error => mark('boot-rejected', { error: String(error) }));
    if (scenarioName === 'unload-register-flight') {
      await deadline(mountEntered.promise, 'register enters real mount barrier');
      mark('dispose-request', { inertia: Boolean(ownFiber.inertia) });
      const disposal = ownFiber.dispose().then(() => { disposed = true; mark('dispose-complete'); });
      try { await deadline(disposal, 'real Fiber.dispose before mount release', 750); }
      catch (error) { state.conclusion = 'FAIL_DISPOSE_WAITING_ACTIVATION'; mark('dispose-deadline-failed', { error: String(error), cleanupComplete, disposed }); }
      mark('mount-release-after-dispose-observation', { cleanupComplete, disposed }); mountGate.resolve();
      await deadline(disposal, 'disposal drain after failure release');
    }
    await deadline(bootPromise, 'actual boot and first lookup');
    if (scenarioName !== 'unload-register-flight') {
      assert.equal(state.firstLookup.broken, undefined);
      state.created = await Promise.all([ctx.sessionController.create({ cwd: sandbox, agentPreset: 'governance' }), ctx.sessionController.create({ cwd: sandbox })]);
      mark('web-explicit-and-default-created', { sessions: state.created });
      for (const item of state.created) assert.equal(ctx.agentPresets.composedPreset(ctx.agents.get(item.sessionId).ctx), 'governance');
      mark('dispose-request'); await ownFiber.dispose(); disposed = true; mark('dispose-complete');
    }
    state.afterDispose = await ctx.agentPresets.list();
    assert.equal(state.afterDispose.some(row => row.id === 'governance'), false);
    assert.equal(state.afterDispose.some(row => row.id === 'standard' && !row.broken), true);
    state.baseUnchanged = true;
    if (state.conclusion === 'IN_PROGRESS') state.conclusion = 'PASS_FIXTURE_ONLY';
  } catch (error) {
    if (state.conclusion === 'IN_PROGRESS') state.conclusion = 'FAIL_NORMAL_WAIT_CHAIN';
    state.error = String(error); mark('scenario-failed', { error: String(error) });
    mountGate.resolve(); admissionGate.resolve();
  } finally {
    if (ctx) try { await deadline(ctx.fiber.dispose(), 'root drain after checkpoint'); mark('root-drain-complete'); }
    catch (error) { state.drainError = String(error); mark('root-drain-failed', { error: String(error) }); }
    save(); console.log(JSON.stringify({ name: scenarioName, conclusion: state.conclusion, activationCount: state.activationCount, checked: state.checked }));
  }
}
