/** FEAT-102 S-A3_G_ONLY. Isolated falsification tool, never product wiring. */
import { createRequire } from 'node:module';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { dirname, resolve, join } from 'node:path';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { performance } from 'node:perf_hooks';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';

const [manifestArg, sandboxArg, scenario = 'normal-first'] = process.argv.slice(2);
const manifest = resolve(manifestArg ?? '');
const sandbox = resolve(sandboxArg ?? '');
const repository = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
assert.equal(sandbox, join(repository, '.governance/sandboxes/feat102-a3'));
for (const key of ['DSH_HOME', 'TEMP', 'TMP', 'DSH_AGENTS_HOME']) assert.equal(resolve(process.env[key] ?? ''), sandbox, `${key} must be isolated`);
const supportedScenarios = ['normal-first', 'normal-last', 'audit-delay', 'import-delay', 'unknown-scope', 'base-disabled', 'base-broken', 'cancel-audit', 'cancel-permitted-flight'];
assert.ok(supportedScenarios.includes(scenario), 'Unknown scenario; no automatic candidate switch');
mkdirSync(sandbox, { recursive: true });
const rawPath = join(sandbox, `${scenario}.json`);
const state = { candidate: 'G', slice: 'S-A3_G_ONLY', scenario, conclusion: 'IN_PROGRESS', productWiringAuthorized: false,
  started: new Date().toISOString(), command: { executable: process.execPath, args: process.argv.slice(1),
    impact_read: [manifest, dirname(manifest), fileURLToPath(import.meta.url)], impact_write: [sandbox],
    access: 'SDK read-only; all runtime writes task sandbox; no profile install/network/paid model' },
  context: { cliManifest: manifest, cli: JSON.parse(readFileSync(manifest, 'utf8')).version, node: process.version,
    repositoryHasHostNodeModules: existsSync(join(repository, 'node_modules/@deepseek-ai/dsh')), resolved: {} },
  events: [], unhandled: [], schemaChecked: 0, ownActivations: 0, permit: false,
  payload: { apply: 0, tool: 0, prompt: 0, skill: 0 }, cleanupComplete: false };
const origin = performance.now();
const save = () => writeFileSync(rawPath, JSON.stringify(state, null, 2) + '\n');
const mark = (event, data = {}) => { state.events.push({ sequence: state.events.length, ms: Number((performance.now() - origin).toFixed(3)), event, ...data }); save(); };
process.on('unhandledRejection', error => { state.unhandled.push(String(error)); mark('unhandled-rejection', { error: String(error) }); });
const sdkRequire = createRequire(manifest);
async function sdk(name) {
  const specifier = `@deepseek-ai/${name}`;
  const path = sdkRequire.resolve(specifier); state.context.resolved[specifier] = path;
  return import(pathToFileURL(path).href);
}
const { boot } = await sdk('dsh-app-boot');
const { resolveConfig } = await sdk('cordis');
const { Group } = await sdk('cordis-plugin-loader');
const Registry = (await sdk('dsh-agent-preset-registry')).default;
const Web = (await sdk('dsh-api-session-controller')).default;
const Persona = await sdk('dsh-persona');
const Filesystem = await sdk('dsh-skill-filesystem');
const nativeToolingReference = (await sdk('dsh-agent-preset')).default;
const builtins = { group: Group, registry: Registry, persona: Persona, filesystem: Filesystem };
for (const [key, name] of Object.entries({ projections: 'dsh-session-projection', sessions: 'dsh-session', agents: 'dsh-agent', llm: 'dsh-llm',
  tools: 'dsh-tools', prompt: 'dsh-system-prompt', skills: 'dsh-skill', typert: 'dsh-typert-registry', defaultModel: 'dsh-agent-default-model', loop: 'dsh-agent-loop' })) builtins[key] = (await sdk(name)).default;
const defer = () => Promise.withResolvers();
const auditGate = defer(), auditEntered = defer(), importGate = defer(), importEntered = defer(), payloadGate = defer(), payloadEntered = defer();
const generations = new Map();
const readyService = 'spgPrototypeReady';
let ctx, ownFiber, registration, ownDispose, auditTask, generation;
async function deadline(promise, label, ms = 2500) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`TIMEOUT ${label}`)), ms); })]); }
  finally { clearTimeout(timer); }
}
function abortable(promise, signal) {
  if (signal.aborted) return Promise.reject(signal.reason);
  return new Promise((res, rej) => {
    const aborted = () => { signal.removeEventListener('abort', aborted); rej(signal.reason); };
    signal.addEventListener('abort', aborted, { once: true });
    promise.then(value => { signal.removeEventListener('abort', aborted); res(value); }, error => { signal.removeEventListener('abort', aborted); rej(error); });
  });
}
const base = { id: 'standard', plugins: [
  { id: 'persona', name: 'cordis:persona', config: { prefix: 'USER PREFIX', suffix: 'USER SUFFIX', includeRuntimeContext: false } },
  { id: 'skills', name: 'cordis:filesystem', config: { customSkillDirs: [join(sandbox, 'user-skills')], includeDefaultRoots: false, watch: false, agentsHome: sandbox } },
  { id: 'literal', name: 'cordis:group', group: true, config: [{ id: 'disabled', name: 'cordis:disabledSentinel', disabled: { __jsExpr: 'true' } }] }
] };
const original = structuredClone(base);
builtins.disabledSentinel = { apply() { throw new Error('DISABLED_ROW_REVIVED'); } };
builtins.payloadProbe = { inject: ['tools', 'systemPrompt', 'skills'], apply(child) {
  assert.equal(generation.permitted, true, 'PAYLOAD_BEFORE_PERMIT');
  state.payload.apply++; mark('payload-apply');
  child.tools.register({ name: 'spg_probe_tool', description: 'Isolated sentinel; never invoked', parameters: { type: 'object', properties: {} },
    output: { schema: { type: 'null' }, render: () => [] }, execute: async () => null }); state.payload.tool++; mark('payload-tool-registered');
  child.systemPrompt.section({ name: 'spg-probe-prompt', order: 900, text: 'Isolated sentinel' }); state.payload.prompt++; mark('payload-prompt-registered');
  child.skills.register({ name: 'spg-probe-skill', description: 'Isolated sentinel', source: 'runtime', content: 'sentinel' }); state.payload.skill++; mark('payload-skill-registered');
} };
builtins.payloadBarrier = { async apply() { mark('payload-flight-barrier-enter'); payloadEntered.resolve(); await payloadGate.promise; mark('payload-flight-barrier-leave'); } };
builtins.guard = { async apply(child, config) {
  const current = generations.get(config.generationId);
  if (!current || current !== generation || current.cancel.signal.aborted) throw new Error('GENERATION_MISSING_OR_STALE');
  mark('guard-enter', { generationId: config.generationId });
  await abortable(current.permit.promise, current.cancel.signal);
  if (generations.get(config.generationId) !== current || current.cancel.signal.aborted) throw new Error('GENERATION_CANCELLED');
  current.permitted = true; state.permit = true;
  const removeReady = child.provide(readyService, { generationId: config.generationId });
  const cancelProvider = () => { Promise.resolve(removeReady()).catch(error => mark('ready-provider-cancel-failed', { error: String(error) })); };
  current.cancel.signal.addEventListener('abort', cancelProvider, { once: true });
  child.effect(() => () => { current.cancel.signal.removeEventListener('abort', cancelProvider); });
  mark('guard-permit-provided');
} };
builtins.io = { apply(child) {
  child.provide('fileUploads', { registerAgentResolver: () => () => {} });
  for (const key of ['attachments', 'workspaceRegistry', 'sessionQuery', 'fs']) child.provide(key, {});
} };
builtins.web = { inject: ['agents', 'agentDefaultModel', 'sessions', 'sessionProjections', 'typert', 'fileUploads'], apply(child) {
  new Web(child, resolveConfig(Web, { nativeOpen: false }));
} };
const ownName = 'cordis:own';
const knownHostRows = new Set([...Object.keys(builtins).map(key => `cordis:${key}`), ownName]);
function collectSeed(group) {
  const found = [];
  function walk(rows, address) {
    if (!Array.isArray(rows)) throw new Error('SOURCE_SCOPE_UNSUPPORTED: nonliteral group');
    for (const row of rows) {
      if (row.name === '@deepseek-ai/dsh-agent-preset') found.push({ row, address: `${address}/${row.id}` });
      else if (row.group === true) walk(row.config, `${address}/${row.id}`);
      else if (!knownHostRows.has(row.name)) throw new Error(`SOURCE_SCOPE_UNSUPPORTED: ${row.name}`);
    }
  }
  walk(group.data, group.ctx.fiber.entry?.id ?? 'root');
  const matching = found.filter(item => item.row.config?.id === 'standard');
  if (matching.length !== 1) throw new Error('SOURCE_SCOPE_UNSUPPORTED: base missing or duplicate');
  return matching[0];
}
builtins.own = { inject: ['agentPresets', 'loader'], async apply(child) {
  state.ownActivations++; ownFiber = child.fiber; mark('own-activation-start');
  const entry = child.fiber.entry, group = entry.parent, tree = group.tree;
  state.source = { parentAddress: group.ctx.fiber.entry?.id ?? 'root', treeBase: tree.ctx.baseUrl, ownAddress: entry.id,
    groupRows: group.data.map(row => ({ id: row.id, name: row.name })), scopeLimit: 'direct native declarations and complete literal groups; fixture core whitelist; unknown Include/dynamic source rejected' };
  const seed = collectSeed(group);
  const rawCopy = structuredClone(seed.row.config);
  mark('seed-copied', { sourceAddress: seed.address });
  if (scenario === 'import-delay') { mark('sdk-import-barrier-enter'); importEntered.resolve(); await deadline(importGate.promise, 'SDK preparation', 1200); }
  // These are the only necessary preparation awaits. Resolution belongs to the selected actual Loader tree.
  const [nativeNamespace, cordisNamespace] = await Promise.all([tree.import('@deepseek-ai/dsh-agent-preset'), tree.import('@deepseek-ai/cordis')]);
  const nativeRuntime = nativeNamespace.default ?? nativeNamespace;
  const normalize = cordisNamespace.resolveConfig;
  assert.equal(typeof normalize, 'function');
  const normalized = normalize(nativeRuntime, rawCopy); state.schemaChecked++;
  state.normalizedSeed = structuredClone(normalized);
  state.source.nativeModuleName = '@deepseek-ai/dsh-agent-preset'; state.source.nativeSchemaSameInstalledContext = nativeRuntime === nativeToolingReference;
  assert.equal(state.source.nativeSchemaSameInstalledContext, true);
  mark('sdk-import-and-native-schema-complete');
  const id = randomUUID(); const permit = defer(); permit.promise.catch(() => {});
  generation = { id, permit, cancel: new AbortController(), permitted: false }; generations.set(id, generation);
  const payload = structuredClone(normalized.plugins);
  payload[0].config.prefix += '\nGOVERNANCE PROBE';
  payload[1].config.customSkillDirs.push(join(repository, 'skills'), join(repository, 'adapters/dsh/skill-shims'));
  for (const [plugin, row] of [[Persona, payload[0]], [Filesystem, payload[1]]]) { normalize(plugin, row.config); state.schemaChecked++; }
  payload.push({ id: 'payload-probe', name: 'cordis:payloadProbe' });
  if (scenario === 'cancel-permitted-flight') payload.push({ id: 'payload-barrier', name: 'cordis:payloadBarrier' });
  const definition = { id: 'governance', plugins: [{ id: 'spg-frame', name: 'cordis:group', group: true, isolate: { [readyService]: true }, config: [
    { id: 'spg-guard', name: 'cordis:guard', config: { generationId: id } },
    { id: 'spg-payload', name: 'cordis:group', group: true, inject: { [readyService]: {} }, config: payload }
  ] }] };
  state.derived = structuredClone(definition);
  mark('register-start'); registration = child.agentPresets.register(definition);
  registration.then(async dispose => {
    mark('register-complete');
    if (generation.cancel.signal.aborted) { await dispose(); mark('late-dispose'); } else ownDispose = dispose;
  }, error => mark('registration-rejected', { error: String(error) }));
  auditTask = (async () => {
    await child.fiber.await(); mark('audit-own-activation-settled');
    await abortable(child.loader.await(), generation.cancel.signal); mark('audit-host-settled');
    if (['audit-delay', 'cancel-audit'].includes(scenario)) { mark('audit-barrier-enter'); auditEntered.resolve(); await abortable(auditGate.promise, generation.cancel.signal); }
    const currentSource = collectSeed(group);
    if (currentSource.address !== seed.address) throw new Error('SOURCE_ADDRESS_CHANGED');
    const acceptedRows = [...tree.entries()].filter(item => item.options.name === '@deepseek-ai/dsh-agent-preset' && item.fiber?.config?.id === 'standard');
    if (acceptedRows.length !== 1 || acceptedRows[0].disabled || acceptedRows[0].fiber.state !== 2) throw new Error('BASE_NOT_UNIQUE_ACTIVE');
    const accepted = acceptedRows[0].fiber.config; state.acceptedBase = structuredClone(accepted);
    assert.deepEqual(normalize(nativeRuntime, accepted), normalized, 'BASE_SEED_ACCEPTED_MISMATCH');
    const metadata = await abortable(child.agentPresets.resolve('standard'), generation.cancel.signal);
    if (metadata.broken) throw new Error(`BASE_BROKEN: ${metadata.broken}`);
    mark('accepted-base-audit-passed');
    assert.deepEqual(state.payload, { apply: 0, tool: 0, prompt: 0, skill: 0 });
    mark('permit-release', { payloadBefore: { ...state.payload } }); generation.permit.resolve();
  })().catch(error => { mark('audit-rejected', { error: String(error) }); generation.permit.reject(error); });
  mark('own-activation-return');
  return async () => {
    mark('cleanup-start'); generation.cancel.abort(new Error('GENERATION_CANCELLED')); generation.permit.reject(new Error('GENERATION_CANCELLED')); generations.delete(id);
    if (ownDispose) await ownDispose();
    state.cleanupComplete = true; mark('cleanup-complete');
  };
} };

const rows = [
  ...['projections', 'sessions', 'agents', 'llm', 'tools', 'prompt', 'skills', 'typert'].map(key => ({ id: `core-${key}`, name: `cordis:${key}` })),
  { id: 'model', name: 'cordis:defaultModel', config: { provider: 'no-network-provider', model: 'no-model' } },
  { id: 'loop', name: 'cordis:loop', config: { agents: [] } }, { id: 'registry', name: 'cordis:registry', config: { default: 'governance' } },
  { id: 'io', name: 'cordis:io' }, { id: 'web', name: 'cordis:web' },
  { id: 'standard', name: '@deepseek-ai/dsh-agent-preset', config: base, ...(scenario === 'base-disabled' ? { disabled: true } : {}) }
];
if (scenario === 'unknown-scope') rows.push({ id: 'unknown-source', name: 'cordis:unexpanded-include', disabled: true });
if (scenario === 'base-broken') base.plugins.push({ id: 'broken-child', name: 'cordis:absent-plugin' });
const own = { id: 'own', name: ownName }; if (scenario === 'normal-last') rows.push(own); else rows.unshift(own);
const configPath = join(sandbox, `${scenario}.yml`); writeFileSync(configPath, JSON.stringify(rows, null, 2)); save();
try {
  const bootPromise = boot('feat102-a3', configPath, [], child => { ctx = child; Object.assign(child.loader.builtins, builtins); }, pathToFileURL(manifest).href)
    .then(() => { mark('actual-boot-return'); return ctx; });
  bootPromise.catch(error => mark('boot-rejected', { error: String(error) }));
  const consumerPromise = bootPromise.then(async () => {
    const requested = 'governance'; mark('first-lookup-start', { requested });
    const lookup = (async () => { state.roster = await ctx.agentPresets.list(); return ctx.agentPresets.resolve(requested); })();
    const creates = Promise.all([ctx.sessionController.create({ cwd: sandbox, agentPreset: requested }), ctx.sessionController.create({ cwd: sandbox })]);
    creates.catch(() => {});
    state.lookup = await lookup; mark('first-lookup-complete', state.lookup);
    state.created = await creates; mark('web-compose-complete');
  });
  consumerPromise.catch(error => { state.consumerError = String(error); mark('consumer-rejected', { error: String(error) }); });
  if (scenario === 'import-delay') {
    await deadline(importEntered.promise, 'import enters'); assert.equal(state.events.some(event => event.event === 'actual-boot-return'), false);
    mark('sdk-import-release'); importGate.resolve();
  }
  if (scenario === 'audit-delay') {
    await deadline(auditEntered.promise, 'audit enters'); assert.deepEqual(state.payload, { apply: 0, tool: 0, prompt: 0, skill: 0 });
    await deadline(bootPromise, 'boot independent of audit barrier');
    assert.ok(state.events.some(event => event.event === 'first-lookup-start'));
    assert.equal(state.events.some(event => event.event === 'first-lookup-complete'), false);
    mark('lookup-waits-record-ready', { payload: { ...state.payload } });
    mark('audit-release'); auditGate.resolve();
  }
  if (scenario === 'cancel-audit' || scenario === 'cancel-permitted-flight') {
    await deadline(scenario === 'cancel-audit' ? auditEntered.promise : payloadEntered.promise, 'cancel window');
    mark('dispose-request'); await deadline(ownFiber.dispose(), 'real own dispose before barrier release', 1000); mark('dispose-complete');
    assert.equal(state.cleanupComplete, true);
    const requested = 'governance'; mark('post-cancel-lookup-start', { requested, barrierStillHeld: true });
    const cancelledMetadata = await deadline(ctx.agentPresets.resolve(requested), 'cancelled record invalid before barrier release', 750);
    mark('post-cancel-lookup-complete', cancelledMetadata);
    assert.ok(cancelledMetadata.broken, 'CANCELLED_RECORD_STILL_USABLE');
    mark('controlled-barrier-release-after-dispose'); auditGate.resolve(); payloadGate.resolve();
  }
  await deadline(bootPromise, 'actual boot');
  await deadline(consumerPromise, 'first actual lookup and concurrent web consumers');
  assert.equal(state.lookup.broken, undefined);
  assert.equal(ctx.get(readyService), undefined, 'READINESS_LEAKED_TO_ROOT');
  for (const result of state.created) assert.equal(ctx.agentPresets.composedPreset(ctx.agents.get(result.sessionId).ctx), 'governance');
  mark('ready');
  mark('dispose-request'); await deadline(ownFiber.dispose(), 'own dispose'); mark('dispose-complete');
  state.afterDispose = await ctx.agentPresets.list(); assert.equal(state.afterDispose.some(item => item.id === 'governance'), false);
  assert.deepEqual([...ctx.loader.entries()].find(entry => entry.options.id === 'standard').fiber.config, original);
  state.conclusion = 'PASS_FIXTURE_ONLY_REVIEW_REQUIRED';
} catch (error) {
  state.conclusion = 'FAIL_G_CHECKPOINT'; state.error = String(error); mark('scenario-failed', { error: String(error) });
  auditGate.resolve(); importGate.resolve(); payloadGate.resolve();
} finally {
  if (ctx) try { await deadline(ctx.fiber.dispose(), 'root drain'); mark('root-drain-complete'); }
  catch (error) { state.drainError = String(error); mark('root-drain-failed', { error: String(error) }); }
  state.completed = new Date().toISOString(); state.exit_code = 0; save();
  console.log(JSON.stringify({ scenario, conclusion: state.conclusion, error: state.error, ownActivations: state.ownActivations, schemaChecked: state.schemaChecked, payload: state.payload, unhandled: state.unhandled }));
}
