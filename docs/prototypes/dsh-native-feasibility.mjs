/** FEAT-102 S-A only. Explicit installed SDK context; never a product entry. */
import { createRequire } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { resolve, relative, dirname, join } from 'node:path';
import { mkdir, writeFile, readFile, access } from 'node:fs/promises';
import { performance } from 'node:perf_hooks';
import assert from 'node:assert/strict';

const manifest = resolve(process.argv[2] ?? '');
const sandbox = resolve(process.argv[3] ?? '');
const repository = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const expectedSandbox = join(repository, '.governance/sandboxes/feat102-sa');
assert.equal(sandbox, expectedSandbox, 'Only the task-owned sandbox is allowed');
for (const key of ['DSH_HOME', 'TEMP', 'TMP']) assert.equal(resolve(process.env[key] ?? ''), sandbox, `${key} must be isolated`);
const sdkRequire = createRequire(manifest);
const context = { cliManifest: manifest, cli: JSON.parse(await readFile(manifest, 'utf8')).version, node: process.version, sandbox, repository, resolved: {} };
async function sdk(name) {
  const specifier = `@deepseek-ai/${name}`;
  const path = sdkRequire.resolve(specifier);
  context.resolved[specifier] = path;
  return import(pathToFileURL(path).href);
}
const { Context, resolveConfig } = await sdk('cordis');
const { Loader, EntryGroup } = await sdk('cordis-plugin-loader');
const { default: Registry } = await sdk('dsh-agent-preset-registry');
const { default: NativePreset } = await sdk('dsh-agent-preset');
const { default: Projections } = await sdk('dsh-session-projection');
const { default: Sessions } = await sdk('dsh-session');
const { default: Agents } = await sdk('dsh-agent');
const { default: AgentLoop } = await sdk('dsh-agent-loop');
const { default: Llm } = await sdk('dsh-llm');
const { default: Tools } = await sdk('dsh-tools');
const { default: Prompt } = await sdk('dsh-system-prompt');
const { default: Skills } = await sdk('dsh-skill');
const Persona = await sdk('dsh-persona');
const Filesystem = await sdk('dsh-skill-filesystem');
const { default: DefaultModel } = await sdk('dsh-agent-default-model');
const { default: Typert } = await sdk('dsh-typert-registry');
const { default: SessionController } = await sdk('dsh-api-session-controller');
const { boot } = await sdk('dsh-app-boot');
await mkdir(sandbox, { recursive: true });
const unhandled = [];
process.on('unhandledRejection', reason => unhandled.push(String(reason)));
const results = [];
const defer = () => Promise.withResolvers();
async function bounded(promise, label) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`TIMEOUT ${label}`)), 6000); })]); }
  finally { clearTimeout(timer); }
}

async function scenario({ name, order = 'first', selected = 'governance', rootDelay = false, registrationDelay = false, stopAt, admissionDelay = false, scheduler = 'microtask', preloadedCore = false, brokenRegistration = false, useBoot = false }) {
  const events = [];
  const origin = performance.now();
  const mark = (event, data = {}) => events.push({ sequence: events.length, ms: Number((performance.now() - origin).toFixed(3)), event, ...data });
  const rootGate = defer(), mountGate = defer(), admissionGate = defer(), registerStarted = defer(), applyStarted = defer(), firstAttempt = defer();
  let ctx = new Context();
  const loaderFiber = ctx.plugin(Loader, { baseUrl: pathToFileURL(manifest).href });
  await loaderFiber;
  let loader = ctx.loader;
  const entry = id => [...loader.entries()].find(item => item.options.id === id);
  // Public builtins permit a linked probe with no repository host dependencies.
  Object.assign(loader.builtins, { native: NativePreset, registry: Registry, projections: Projections, sessions: Sessions, agents: Agents,
    loop: AgentLoop, llm: Llm, tools: Tools, prompt: Prompt, skills: Skills, persona: Persona, filesystem: Filesystem,
    defaultModel: DefaultModel, typert: Typert });
  const base = { id: 'standard', name: 'fixture standard', plugins: [
    { id: 'persona', name: 'cordis:persona', config: { prefix: 'USER PREFIX', suffix: 'USER SUFFIX', includeRuntimeContext: false } },
    { id: 'skill-filesystem', name: 'cordis:filesystem', config: { customSkillDirs: [join(sandbox, 'user-skills')], includeDefaultRoots: false, watch: false, agentsHome: sandbox } },
    { id: 'group', name: 'cordis:group', group: true, config: [
      { id: 'disabled-expression', name: 'cordis:sentinel', disabled: { __jsExpr: 'true' }, config: { value: 'preserved' } }
    ] }
  ] };
  const original = structuredClone(base);
  let checked = 0, stopped = false, ownDispose, startup, lateDisposed = false, listenerDisposed = false;
  const core = [
    ['projections', {}], ['sessions', {}], ['agents', {}], ['llm', {}], ['tools', {}], ['prompt', {}], ['skills', {}], ['typert', {}],
    ['defaultModel', { provider: 'no-network-provider', model: 'no-model' }], ['loop', { agents: [] }], ['registry', { default: selected === 'default' ? 'governance' : 'standard' }]
  ].map(([name, config]) => ({ id: `core-${name}`, name: `cordis:${name}`, config }));
  loader.builtins.group = (await sdk('cordis-plugin-loader')).Group;
  loader.builtins.sentinel = { Config: Persona.Config, apply() { throw new Error('Disabled expression was revived'); } };
  loader.builtins.mountGate = { async apply() { mark('mount-delay-enter'); await mountGate.promise; mark('mount-delay-leave'); } };
  loader.builtins.rootGate = { async apply() { mark('root-delay-enter'); await rootGate.promise; mark('root-delay-leave'); } };
  // Only unused file-upload / workspace / cold-query / attachment / fs IO surfaces are substituted.
  // Preset registry, config validation, Loader, Session, Agent factory, and web create implementation are real.
  loader.builtins.io = { apply(child) {
    child.provide('fileUploads', { registerAgentResolver: () => () => {} });
    child.provide('attachments', {}); child.provide('workspaceRegistry', {}); child.provide('sessionQuery', {}); child.provide('fs', {});
  } };
  loader.builtins.web = { inject: ['agents', 'agentDefaultModel', 'sessions', 'sessionProjections', 'typert', 'fileUploads'], apply(child) {
    // Direct construction avoids uncalled IO subplugins delaying this controlled consumer; public schema is still checked.
    new SessionController(child, resolveConfig(SessionController, { nativeOpen: false }));
  } };
  loader.builtins.own = { inject: ['loader', 'agentPresets'], apply(child) {
    mark('own-apply'); applyStarted.resolve();
    const off = child.on('app-boot/config-reload', () => {});
    child.effect(() => async () => {
      stopped = true; off(); listenerDisposed = true; mark('cleanup-start');
      if (ownDispose) await ownDispose();
      mark('cleanup-complete');
    });
    const start = async () => {
      mark('background-task-start', { scheduler });
      await child.loader.await(); mark('own-root-settled');
      if (stopped) return mark('stopped-before-registration');
      const found = [...child.loader.entries()].filter(entry => entry.options.name === 'cordis:native' && entry.fiber?.config?.id === 'standard');
      assert.equal(found.length, 1); assert.equal(found[0].disabled, false);
      const accepted = found[0].fiber.config;
      const definition = structuredClone(accepted); definition.id = 'governance';
      definition.plugins[0].config.prefix += '\nGOVERNANCE PROBE';
      definition.plugins[1].config.customSkillDirs.push(join(repository, 'skills'), join(repository, 'adapters/dsh/skill-shims'));
      assert.deepEqual(accepted.plugins, original.plugins);
      assert.deepEqual(definition.plugins[2], original.plugins[2]);
      for (const row of definition.plugins.slice(0, 2)) { resolveConfig(loader.builtins[row.name.slice(7)], row.config); checked++; }
      if (admissionDelay) { mark('admission-delay-enter'); await admissionGate.promise; mark('admission-delay-leave'); }
      if (stopped) return mark('stopped-before-registration');
      if (registrationDelay) definition.plugins.push({ id: 'activation-delay', name: 'cordis:mountGate' });
      if (brokenRegistration) definition.plugins.push({ id: 'broken-row', name: 'cordis:absent-probe-module' });
      mark('register-start'); registerStarted.resolve();
      const dispose = await child.agentPresets.register(definition); mark('register-complete');
      if (stopped) { await dispose(); lateDisposed = true; return mark('late-register-disposed'); }
      ownDispose = dispose;
      const metadata = await child.agentPresets.resolve('governance');
      assert.equal(metadata.broken, undefined); mark('ready');
    };
    startup = (scheduler === 'microtask' ? Promise.resolve().then(start) : new Promise(resolveStart => setImmediate(resolveStart)).then(start))
      .catch(error => { mark('startup-failed', { message: String(error) }); });
    mark('own-apply-return');
  } };
  let first, bootRoster, bootResolve;
  const firstDone = defer();
  loader.builtins.consumer = { inject: ['sessionController'], apply(child) {
    // Same root-settle entry condition as boot; no wait on the plugin's readiness.
    (async () => {
      await child.loader.await(); mark('consumer-root-settled');
      mark('first-create-attempt', { requested: selected });
      firstAttempt.resolve();
      try {
        first = await child.sessionController.create({ cwd: sandbox, ...(selected === 'default' ? {} : { agentPreset: selected }) });
        mark('first-create-complete', first);
      } catch (error) { first = { error: String(error), code: error.code }; mark('first-create-failed', first); }
      firstDone.resolve();
    })().catch(error => firstDone.reject(error));
  } };
  const own = { id: 'own', name: 'cordis:own' };
  const initial = [...core, { id: 'io', name: 'cordis:io' }, { id: 'web', name: 'cordis:web' }, { id: 'standard', name: 'cordis:native', config: base }];
  if (preloadedCore) { await loader.root.update(initial); await loader.await(); mark('core-and-base-preloaded'); }
  const rows = [...initial,
    ...(rootDelay ? [{ id: 'root-delay', name: 'cordis:rootGate' }] : []), { id: 'consumer', name: 'cordis:consumer' }];
  if (order === 'first') rows.unshift(own); else rows.push(own);
  let update;
  if (useBoot) {
    const builtins = { ...loader.builtins };
    await ctx.fiber.dispose();
    const configPath = join(sandbox, `${name}.yml`);
    await writeFile(configPath, JSON.stringify(rows, null, 2));
    update = boot('feat102-sa', configPath, [], child => {
      ctx = child; loader = child.loader; Object.assign(loader.builtins, builtins);
    }, pathToFileURL(manifest).href).then(async () => {
      mark('actual-boot-return');
      // These are real public roster/selection reads immediately after actual boot, with no own-ready gate.
      bootRoster = await ctx.agentPresets.list();
      mark('boot-roster-read', { ids: bootRoster.map(item => item.id) });
      try { bootResolve = await ctx.agentPresets.resolve('governance'); mark('boot-governance-resolve', bootResolve); }
      catch (error) { bootResolve = { error: String(error), code: error.code }; mark('boot-governance-resolve-failed', bootResolve); }
    });
  } else update = loader.root.update(rows);
  await bounded(applyStarted.promise, 'own apply');
  if (stopAt === 'root') {
    await bounded(entry('own').fiber.dispose(), 'dispose during root await');
    rootGate.resolve();
  } else rootGate.resolve();
  await bounded(update, 'root update');
  const settled = loader.await().then(() => mark('root-settled'));
  await bounded(settled, 'root settled');
  if (stopAt === 'register') {
    await bounded(registerStarted.promise, 'register started');
    await bounded(entry('own').fiber.dispose(), 'dispose during registration');
    mountGate.resolve();
  } else if (registrationDelay) {
    await bounded(registerStarted.promise, 'register started');
    // Release based on the consumer ATTEMPT event, never elapsed sleep or own-ready.
    await bounded(firstAttempt.promise, 'first consumer attempt');
    mountGate.resolve();
  }
  if (admissionDelay) { await bounded(firstDone.promise, 'first consumer'); admissionGate.resolve(); }
  await bounded(firstDone.promise, 'first consumer');
  await bounded(startup, 'startup drain');
  const after = await ctx.agentPresets.list();
  let composed;
  if (!stopAt && after.some(item => item.id === 'governance' && !item.broken)) {
    // This second call is an explicit AFTER-readiness control; it never proves the first-session guarantee.
    const second = await ctx.sessionController.create({ cwd: sandbox, agentPreset: 'governance' });
    const agent = ctx.agents.get(second.sessionId);
    composed = { preset: ctx.agentPresets.composedPreset(agent.ctx), header: agent.session.header.agentPreset };
  }
  await bounded(entry('own').fiber?.dispose() ?? Promise.resolve(), 'own dispose');
  const rosterAfterDispose = await ctx.agentPresets.list();
  assert.equal(rosterAfterDispose.some(item => item.id === 'governance'), false);
  assert.equal(rosterAfterDispose.some(item => item.id === 'standard' && !item.broken), true);
  assert.deepEqual(entry('standard').fiber.config.plugins, original.plugins);
  assert.equal(listenerDisposed, true);
  const result = { name, order, selected, rootDelay, registrationDelay, admissionDelay, stopAt, scheduler, preloadedCore, brokenRegistration, useBoot, bootRoster, bootResolve, first, composed, checked,
    after, rosterAfterDispose, lateDisposed, listenerDisposed, baseUnchanged: true, events };
  await bounded(ctx.fiber.dispose(), 'root dispose');
  results.push(result);
}

try {
  for (const order of ['first', 'last']) for (const selected of ['governance', 'default', 'standard']) {
    await scenario({ name: `${order}-${selected}`, order, selected });
  }
  await scenario({ name: 'admission-delay-explicit', admissionDelay: true });
  await scenario({ name: 'admission-delay-default', selected: 'default', order: 'last', admissionDelay: true });
  await scenario({ name: 'root-delay', rootDelay: true });
  await scenario({ name: 'register-delay', registrationDelay: true });
  await scenario({ name: 'unload-root-await', rootDelay: true, stopAt: 'root' });
  await scenario({ name: 'unload-register-flight', registrationDelay: true, stopAt: 'register' });
  await scenario({ name: 'preloaded-first', preloadedCore: true });
  await scenario({ name: 'preloaded-last', preloadedCore: true, order: 'last' });
  await scenario({ name: 'immediate-first', scheduler: 'immediate' });
  await scenario({ name: 'immediate-last-default', scheduler: 'immediate', order: 'last', selected: 'default' });
  await scenario({ name: 'broken-registration', brokenRegistration: true });
  await scenario({ name: 'actual-boot-microtask', useBoot: true });
  await scenario({ name: 'actual-boot-immediate-default', useBoot: true, scheduler: 'immediate', selected: 'default' });
  await scenario({ name: 'actual-boot-admission-delay', useBoot: true, admissionDelay: true });
  const failures = results.filter(result => ['governance', 'default'].includes(result.selected) && !result.stopAt && !result.brokenRegistration && result.first?.error);
  context.repositoryHasHostNodeModules = await access(join(repository, 'node_modules/@deepseek-ai/dsh')).then(() => true, () => false);
  const naturalFailures = failures.filter(result => !result.admissionDelay);
  const visibilityFailures = results.filter(result => result.useBoot && !result.admissionDelay && result.bootResolve?.error);
  const report = { context, conclusion: naturalFailures.length ? 'FAIL_NATURAL_FIRST_SESSION' : visibilityFailures.length ? 'FAIL_POST_BOOT_PRESET_VISIBILITY' : 'NORMAL_PATH_PASS_ADMISSION_WINDOW_UNPROVEN',
    postBootVisibilityFailures: visibilityFailures.map(result => result.name),
    firstSessionFailures: failures.map(result => result.name), schemaChecked: results.reduce((sum, result) => sum + result.checked, 0), unhandled, results };
  await writeFile(join(sandbox, 'result.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ conclusion: report.conclusion, firstSessionFailures: report.firstSessionFailures, postBootVisibilityFailures: report.postBootVisibilityFailures, schemaChecked: report.schemaChecked, scenarios: results.length, unhandled }));
  if (unhandled.length) process.exitCode = 2;
} catch (error) {
  await writeFile(join(sandbox, 'partial-result.json'), JSON.stringify({ context, results, unhandled, error: String(error), stack: error.stack }, null, 2) + '\n');
  console.error(error); process.exitCode = 2;
}
