"""FEAT-102: native preset derivation — unit guard for the decoupled delivery.

The row has two paths. The legacy one renders a full composition into the user
preset root (the coupling this feature removes); the native one derives the
governance preset from the host's OWN current base declaration at boot and only
adds two content deltas. These tests pin the native contract without a host:

* the derived definition is the base rows plus exactly the persona body and the
  two skill roots (order, groups, expressions and unknown fields preserved);
* refusals (ambiguous/disabled/missing base, disabled registry) never register
  and never write the retired directory;
* `apply()` on a host that declares the registry row writes NOTHING to
  `$DSH_HOME`, and on a host without that row it still renders the legacy
  payload (the old-host path is preserved, only the modern one is decoupled);
* the persona body is the same text the legacy composition carries, so the two
  paths cannot drift apart silently.

The derivation is exercised through the real `lib/` modules with a fake Cordis
context; real-host acceptance lives in the FEAT-102 verification record and is
deliberately NOT claimed here.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_NATIVE = _REPO_ROOT / "lib" / "dsh-native"
_CONTRACT = _REPO_ROOT / "adapters" / "dsh" / "host-contract.json"
_PERSONA = _REPO_ROOT / "agent-presets" / "governance" / "persona.md.template"
_TEMPLATE = _REPO_ROOT / "agent-presets" / "governance" / "agent.cordis.yml.template"
_LIB_INDEX = _REPO_ROOT / "lib" / "index.js"


def _node() -> str | None:
    return shutil.which("node")


_PROBE = r"""
import { readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

const repo = process.argv[1]
const { applyNative } = await import(pathToFileURL(`${repo}/lib/dsh-native/bridge.js`).href)
const contract = JSON.parse(readFileSync(`${repo}/adapters/dsh/host-contract.json`, 'utf8'))

const baseConfig = {
  id: 'standard',
  order: 1,
  plugins: [
    { id: 'persona', name: '@deepseek-ai/dsh-persona', config: { prefix: 'HOST PREFIX', suffix: 'S' } },
    { id: 'skill-filesystem', name: '@deepseek-ai/dsh-skill-filesystem', config: { watch: false, customSkillDirs: ['C:\\user\\skills'] } },
    { id: 'tool-fs', name: '@deepseek-ai/dsh-tool-fs' },
    { id: 'group', name: 'cordis:group', group: true, config: [{ id: 'inner', name: 'cordis:x', disabled: { __jsExpr: 'true' } }] },
  ],
}
const entry = (id, name, config, disabled = false) => ({ id, options: { name, config }, disabled })
const baseEntry = entry('include:preset-standard', '@deepseek-ai/dsh-agent-preset', baseConfig)
const registryEntry = entry('include:agent-preset-registry', '@deepseek-ai/dsh-agent-preset-registry', {})

const makeRegistry = (sink) => ({
  register(definition) { sink.push(definition); return Promise.resolve(async () => {}) },
})
const childFor = (loader, sink) => ({
  agentPresets: makeRegistry(sink),
  get: (name) => (name === 'loader' ? loader : undefined),
  effect: () => {},
})
const ctxFor = (loader, sink) => ({
  get: (name) => (name === 'loader' ? loader : undefined),
  logger: { info: () => {}, warn: () => {} },
  // The production row defers on the service; the fake invokes immediately.
  inject: (deps, callback) => { if (deps.join(',') === 'agentPresets') callback(childFor(loader, sink)) },
})

const capture = []
const happy = applyNative(ctxFor({ entries: () => [registryEntry, baseEntry] }, capture), {}, () => contract)
if (capture.length !== 1) throw new Error(`REGISTRATIONS=${capture.length}`)
const definition = capture[0]

const duplicateCapture = []
applyNative(ctxFor({ entries: () => [registryEntry, baseEntry, entry('include:preset-standard-2', '@deepseek-ai/dsh-agent-preset', baseConfig)] }, duplicateCapture), {}, () => contract)
if (duplicateCapture.length !== 0) throw new Error('DUPLICATE_BASE_REGISTERED')

const disabledCapture = []
const disabledRegistry = applyNative(ctxFor({ entries: () => [entry('include:agent-preset-registry', '@deepseek-ai/dsh-agent-preset-registry', {}, true), baseEntry] }, disabledCapture), {}, () => contract)
if (disabledCapture.length !== 0) throw new Error('DISABLED_REGISTRY_REGISTERED')

// A legacy host is one whose tree IS readable and simply declares no registry
// row — not one whose tree cannot be read (CODE R0 F1: the latter refuses).
const legacy = applyNative(
  { get: (name) => (name === 'loader' ? { entries: () => [baseEntry] } : undefined), logger: { warn: () => {} } },
  {}, () => contract)

process.stdout.write(JSON.stringify({
  mode: happy.mode,
  disabledMode: disabledRegistry.mode,
  legacyMode: legacy.mode,
  disabledCode: disabledRegistry.code,
  definitionId: definition.id,
  name: definition.name,
  personaPrefix: definition.plugins[0].config.prefix,
  personaSuffix: definition.plugins[0].config.suffix,
  skillDirs: definition.plugins[1].config.customSkillDirs,
  skillWatch: definition.plugins[1].config.watch,
  unrelatedRow: definition.plugins[2],
  groupRow: definition.plugins[3],
  inputPrefix: baseConfig.plugins[0].config.prefix,
}))
"""


_APPLY_PROBE = r"""
import { readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

const repo = process.argv[1]
const { apply } = await import(pathToFileURL(`${repo}/lib/index.js`).href)
const contract = JSON.parse(readFileSync(`${repo}/adapters/dsh/host-contract.json`, 'utf8'))
const baseConfig = {
  id: 'standard',
  plugins: [
    { id: 'persona', name: '@deepseek-ai/dsh-persona', config: { prefix: 'HOST PREFIX' } },
    { id: 'skill-filesystem', name: '@deepseek-ai/dsh-skill-filesystem' },
  ],
}
const rows = (native) => {
  const list = [
    { id: 'include:preset-standard', options: { name: '@deepseek-ai/dsh-agent-preset', config: baseConfig }, disabled: false },
  ]
  if (native) list.unshift({ id: 'include:agent-preset-registry', options: { name: '@deepseek-ai/dsh-agent-preset-registry' }, disabled: false })
  return list
}
const loaderFor = (native) => ({ entries: () => rows(native) })
const registered = []
const warnings = []
let native = process.argv[2] === 'native'
const ctx = {
  get: (name) => (name === 'loader' ? loaderFor(native) : undefined),
  logger: { info: () => {}, warn: (m) => warnings.push(String(m)) },
  effect: () => {},
  inject: (deps, callback) => callback({
    agentPresets: { register: (definition) => { registered.push(definition); return Promise.resolve(async () => {}) } },
    get: (name) => (name === 'loader' ? loaderFor(native) : undefined),
    effect: () => {},
  }),
}
apply(ctx, {})
process.stdout.write(JSON.stringify({ registered: registered.length, warnings }))
"""


_DECLARATION_REFUSAL_PROBE = r"""
import { readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

const repo = process.argv[1]
const { apply } = await import(pathToFileURL(`${repo}/lib/index.js`).href)
const contract = JSON.parse(readFileSync(`${repo}/adapters/dsh/host-contract.json`, 'utf8'))

const persona = '@deepseek-ai/dsh-persona'
const skills = '@deepseek-ai/dsh-skill-filesystem'
const baseConfig = (plugins) => ({ id: 'standard', plugins })
const entry = (id, name, config, disabled = false) => ({ id, options: { name, config }, disabled })
const registry = entry('include:agent-preset-registry', '@deepseek-ai/dsh-agent-preset-registry', {})
const base = (config) => entry('include:preset-standard', '@deepseek-ai/dsh-agent-preset', config)
const good = baseConfig([
  { id: 'persona', name: persona, config: { prefix: 'HOST' } },
  { id: 'skill-filesystem', name: skills },
])

// DEC-366 ② / D-R6-3: declaration-based negatives — the row must warn once,
// register nothing and write nothing in every one of them.
const cases = {
  missingBase: [registry],
  duplicateBase: [registry, base(good),
    entry('include:preset-standard-2', '@deepseek-ai/dsh-agent-preset', good)],
  unmergeablePersona: [registry, base(baseConfig([
    { id: 'p1', name: persona, config: {} },
    { id: 'p2', name: persona, config: {} },
  ]))],
}

const results = {}
for (const [label, tree] of Object.entries(cases)) {
  const warnings = []
  const registered = []
  const loader = { entries: () => tree }
  const child = {
    agentPresets: { register: (d) => { registered.push(d); return Promise.resolve(async () => {}) } },
    get: (name) => (name === 'loader' ? loader : undefined),
    effect: () => {},
  }
  apply({
    get: (name) => (name === 'loader' ? loader : undefined),
    logger: { info: () => {}, warn: (m) => warnings.push(String(m)) },
    effect: () => {},
    inject: (deps, cb) => cb(child),
  }, {})
  results[label] = {
    registered: registered.length,
    warnings,
    codes: warnings.map((w) => (w.match(/\(([A-Z_]+)\)/) || [])[1]),
  }
}
process.stdout.write(JSON.stringify(results))
"""


_UNREADABLE_TREE_PROBE = r"""
import { readFileSync } from 'node:fs'
import { pathToFileURL } from 'node:url'

const repo = process.argv[1]
const { apply } = await import(pathToFileURL(`${repo}/lib/index.js`).href)
const { applyNative } = await import(pathToFileURL(`${repo}/lib/dsh-native/bridge.js`).href)
const contract = JSON.parse(readFileSync(`${repo}/adapters/dsh/host-contract.json`, 'utf8'))

// CODE R0 F1: an enumeration failure must never read as "old host". The loader
// is a real service whose entries() call can throw; the row must refuse.
const brokenLoader = { entries: () => { throw new Error('tree explosion') } }
const direct = applyNative({ get: (n) => (n === 'loader' ? brokenLoader : undefined) }, {}, () => contract)

const warnings = []
const registered = []
const child = {
  agentPresets: { register: (definition) => { registered.push(definition); return Promise.resolve(async () => {}) } },
  get: (n) => (n === 'loader' ? brokenLoader : undefined),
  effect: () => {},
}
const ctx = {
  get: (n) => (n === 'loader' ? brokenLoader : undefined),
  logger: { info: () => {}, warn: (m) => warnings.push(String(m)) },
  effect: () => {},
  inject: (deps, callback) => callback(child),
}
apply(ctx, {})

// The same fail-open branch when the loader service is absent AND the context
// cannot defer: no inject → no way to distinguish, so it must refuse too.
const noLoader = applyNative({ get: () => undefined, logger: { warn: () => {} } }, {}, () => contract)

process.stdout.write(JSON.stringify({
  directMode: direct.mode,
  directCode: direct.code,
  registered: registered.length,
  warnings: warnings.length,
  warningMentionsCode: warnings.some((w) => w.includes('HOST_TREE_UNREADABLE')),
  noLoaderMode: noLoader.mode,
  noLoaderCode: noLoader.code,
}))
"""


_LIFECYCLE_PROBE = r"""
import { pathToFileURL } from 'node:url'

const repo = process.argv[1]
const { startRegistration } = await import(pathToFileURL(`${repo}/lib/dsh-native/lifecycle.js`).href)

const results = {}

// E1: disposal after activation withdraws exactly once.
{
  let disposerCalls = 0
  let cleanup = null
  const events = []
  const ctx = {
    agentPresets: { register: () => Promise.resolve(async () => { disposerCalls += 1 }) },
    effect: (fn) => { cleanup = fn() },
  }
  const outcome = startRegistration(ctx, { id: 'governance' }, { warn: () => {} }, (e) => events.push(e))
  await Promise.resolve()
  await Promise.resolve()
  cleanup()
  await Promise.resolve()
  results.e1 = { status: outcome.status, code: outcome.code, disposerCalls, events }
}

// E2: the row unloads while activation is in flight; the late disposer is
// invoked immediately when it arrives (never awaited by the unload path).
{
  let settle = null
  let disposerCalls = 0
  let cleanup = null
  const events = []
  const ctx = {
    agentPresets: { register: () => new Promise((resolve) => { settle = resolve }) },
    effect: (fn) => { cleanup = fn() },
  }
  startRegistration(ctx, { id: 'governance' }, { warn: () => {} }, (e) => events.push(e))
  cleanup()
  const callsBefore = disposerCalls
  settle(async () => { disposerCalls += 1 })
  await Promise.resolve()
  await Promise.resolve()
  await Promise.resolve()
  results.e2 = { callsBefore, disposerCalls, events }
}

// E3: a synchronous registry refusal is reported, never thrown.
{
  const ctx = {
    agentPresets: { register: () => { throw new Error('duplicate preset id') } },
    effect: () => {},
  }
  const outcome = startRegistration(ctx, { id: 'governance' }, { warn: () => {} })
  results.e3 = { status: outcome.status, code: outcome.code }
}

// E4: an asynchronous rejection is warn-only and cannot escape the row.
{
  const warnings = []
  let threw = null
  let outcome = null
  try {
    outcome = startRegistration({
      agentPresets: { register: () => Promise.reject(new Error('mount failed')) },
      effect: () => {},
    }, { id: 'governance' }, { warn: (m) => warnings.push(String(m)) })
  } catch (error) {
    threw = String(error)
  }
  await Promise.resolve()
  await Promise.resolve()
  await Promise.resolve()
  results.e4 = { status: outcome && outcome.status, code: outcome && outcome.code, threw, warnings: warnings.length }
}

process.stdout.write(JSON.stringify(results))
"""


_PATH_IDENTITY_PROBE = r"""
import { pathToFileURL } from 'node:url'

const repo = process.argv[1]
const flavour = process.argv[2]
// CODE R0 F10: the module computes its case-folding at import time, so the
// platform must be redefined BEFORE the dynamic import to exercise POSIX.
if (flavour === 'posix') Object.defineProperty(process, 'platform', { value: 'linux' })

const { deriveDefinition } = await import(
  pathToFileURL(`${repo}/lib/dsh-native/overlay.js`).href)

const persona = '@deepseek-ai/dsh-persona'
const skills = '@deepseek-ai/dsh-skill-filesystem'
const base = {
  id: 'standard',
  plugins: [
    { id: 'persona', name: persona, config: { prefix: 'HOST' } },
    { id: 'skills', name: skills, config: { customSkillDirs: ['/A/skills'] } },
  ],
}
const derived = deriveDefinition(base, {
  personaRowName: persona,
  skillRowName: skills,
  personaBody: 'BODY',
  // '/A/skills' is already declared; '/a/skills' differs only by case.
  skillRoots: ['/A/skills', '/a/skills'],
  presetId: 'governance',
  name: 'Governance',
})
const row = derived.ok
  ? derived.definition.plugins.find((plugin) => plugin.name === skills)
  : null
process.stdout.write(JSON.stringify({
  platform: process.platform,
  ok: derived.ok,
  dirs: row ? row.config.customSkillDirs : null,
}))
"""


@unittest.skipUnless(_node(), "node unavailable (native bridge cannot be exercised)")
class NativeBridgeTests(unittest.TestCase):
    def _run(self, script: str, *args: str, env: dict | None = None) -> dict:
        child_env = {**os.environ, **(env or {})}
        result = subprocess.run(
            [_node(), "--input-type=module", "-e", script, str(_REPO_ROOT), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env=child_env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_derived_definition_is_base_plus_two_deltas(self):
        payload = self._run(_PROBE)
        self.assertEqual(payload["mode"], "native")
        self.assertEqual(payload["definitionId"], "governance")
        self.assertTrue(payload["name"])
        # Persona: host prefix preserved, governance body appended, other fields intact.
        self.assertTrue(payload["personaPrefix"].startswith("HOST PREFIX\n\n"))
        self.assertIn("software-project-governance", payload["personaPrefix"])
        self.assertEqual(payload["personaSuffix"], "S")
        # Skills: existing root preserved, exactly the two package roots appended.
        dirs = payload["skillDirs"]
        self.assertEqual(dirs[0], "C:\\user\\skills")
        self.assertEqual(len(dirs), 3)
        self.assertTrue(dirs[1].endswith("/skills"))
        self.assertTrue(dirs[2].endswith("/adapters/dsh/skill-shims"))
        self.assertFalse(payload["skillWatch"], "unrelated skill config must survive")
        # Everything else is byte-identical, including groups and !!js expressions.
        self.assertEqual(payload["unrelatedRow"], {"id": "tool-fs", "name": "@deepseek-ai/dsh-tool-fs"})
        self.assertEqual(payload["groupRow"]["group"], True)
        self.assertEqual(payload["groupRow"]["config"][0]["disabled"], {"__jsExpr": "true"})
        # The base declaration is never mutated.
        self.assertEqual(payload["inputPrefix"], "HOST PREFIX")

    def test_refusals_never_register(self):
        payload = self._run(_PROBE)
        self.assertEqual(payload["disabledMode"], "refused")
        self.assertEqual(payload["disabledCode"], "REGISTRY_ROW_DISABLED")
        self.assertEqual(payload["legacyMode"], "legacy")

    def test_apply_writes_nothing_on_a_native_host(self):
        # CODE R0 F5: the assertion this test is named for needs an EXPLICIT
        # DSH_HOME. Without one, a native-path regression would render into the
        # caller's real `~/.dsh` (or an external DSH_HOME) while the repo-cwd
        # assertion below still passed — a green test that writes a real home.
        with tempfile.TemporaryDirectory() as td:
            payload = self._run(_APPLY_PROBE, "native", env={"DSH_HOME": td})
            self.assertEqual(payload["registered"], 1, "the native registration must be issued")
            self.assertFalse(
                (Path(td) / ".agent-presets").exists(),
                "a native host must never get a preset directory under its DSH_HOME")
        # The probe runs in the repo cwd; no preset root may appear beside it.
        self.assertFalse((_REPO_ROOT / ".agent-presets").exists())

    def test_apply_refuses_an_unreadable_tree_instead_of_rendering_legacy(self):
        """CODE R0 F1: `entries()` throwing is NOT "old host" (fail-closed)."""
        with tempfile.TemporaryDirectory() as td:
            payload = self._run(_UNREADABLE_TREE_PROBE, env={"DSH_HOME": td})
            self.assertEqual(payload["directMode"], "refused")
            self.assertEqual(payload["directCode"], "HOST_TREE_UNREADABLE")
            # `apply()` must neither register nor write on that path.
            self.assertEqual(payload["registered"], 0)
            # R1 P3: exactly ONE warning — a silent doubling would be a
            # behavioural change too, and this is the row's whole report face.
            self.assertEqual(payload["warnings"], 1, "exactly one warning, not zero or many")
            self.assertTrue(payload["warningMentionsCode"])
            self.assertFalse((Path(td) / ".agent-presets").exists(),
                             "an unreadable tree must never produce a legacy directory")
            # The same fail-open branch with no loader at all and no inject seam.
            self.assertEqual(payload["noLoaderMode"], "refused")
            self.assertEqual(payload["noLoaderCode"], "HOST_NO_LOADER_TREE")

    def test_apply_never_renders_a_legacy_host(self):
        """DEC-366 ②: a readable tree without the registry row renders nothing.

        The "absent" state is a warning, not a render: the old expectation that
        this row delivers a user-root preset for an old host is retired (the
        explicit `launch.py --install` is the only renderer).
        """
        with tempfile.TemporaryDirectory() as td:
            payload = self._run(_APPLY_PROBE, "legacy", env={"DSH_HOME": td})
            self.assertEqual(payload["registered"], 0)
            self.assertEqual(len(payload["warnings"]), 1,
                             "the absent-registry state reports exactly one warning")
            self.assertTrue(
                any("HOST_WITHOUT_REGISTRY" in warning
                    for warning in payload["warnings"]), payload["warnings"])
            self.assertFalse(
                (Path(td) / ".agent-presets").exists(),
                "the row must never render a legacy preset directory")

    def test_declaration_based_refusals_never_write(self):
        """D-R6-3: missing/duplicate/unmergeable base → warn, no write."""
        with tempfile.TemporaryDirectory() as td:
            payload = self._run(_DECLARATION_REFUSAL_PROBE, env={"DSH_HOME": td})
            self.assertFalse((Path(td) / ".agent-presets").exists())
        expectations = {
            "missingBase": "BASE_NOT_FOUND",
            "duplicateBase": "BASE_DUPLICATE",
            "unmergeablePersona": "PERSONA_ROW_DUPLICATE",
        }
        for label, code in expectations.items():
            case = payload[label]
            self.assertEqual(case["registered"], 0, label)
            self.assertEqual(len(case["warnings"]), 1,
                             (label, "exactly one warning", case))
            self.assertIn(code, case["codes"], (label, case["warnings"]))

    def test_path_identity_folds_case_per_platform(self):
        """CODE R0 F10: POSIX must not fold /A/skills and /a/skills together."""
        posix = self._run(_PATH_IDENTITY_PROBE, "posix")
        self.assertTrue(posix["ok"], posix)
        self.assertEqual(posix["platform"], "linux")
        self.assertIn("/a/skills", posix["dirs"],
                      "a case-sensitive filesystem must append the distinct root")
        self.assertEqual(len(posix["dirs"]), 2, posix["dirs"])

        native = self._run(_PATH_IDENTITY_PROBE, "native")
        self.assertTrue(native["ok"], native)
        if native["platform"] in ("win32", "darwin"):
            # Case-insensitive volume: the two spellings are one directory.
            self.assertEqual(native["dirs"], ["/A/skills"], native["dirs"])
        else:
            self.assertIn("/a/skills", native["dirs"], native["dirs"])

    def test_registration_lifecycle_disposes_exactly_once(self):
        """CODE R0 F8: the disposal/late-disposer/rejection branches are pinned."""
        payload = self._run(_LIFECYCLE_PROBE)
        self.assertEqual(payload["e1"]["status"], "starting")
        self.assertEqual(payload["e1"]["disposerCalls"], 1)
        self.assertIn("disposed", payload["e1"]["events"])
        # Unload while activation is in flight: the late disposer runs at once.
        self.assertEqual(payload["e2"]["callsBefore"], 0,
                         "unload must not wait for the in-flight activation")
        self.assertEqual(payload["e2"]["disposerCalls"], 1)
        # A synchronous registry refusal is a structured failure, never a throw.
        self.assertEqual(payload["e3"]["status"], "failed")
        self.assertEqual(payload["e3"]["code"], "REGISTER_REFUSED")
        # An asynchronous rejection is warn-only.
        self.assertEqual(payload["e4"]["status"], "starting")
        self.assertIsNone(payload["e4"]["threw"])
        self.assertGreater(payload["e4"]["warnings"], 0)


class PersonaAndContractTests(unittest.TestCase):
    #: R1-F1 (CODE R1): the retired "the row auto-renders the preset" narration
    #: survived in the operator docs, the adapter manifest's descriptive fields
    #: and the launcher docstring while the row already behaved differently.
    #: One list, one guard: no surface may carry any of these again.
    _RETIRED_AUTO_RENDER_WORDING = (
        "ensurePreset() re-renders",
        "let ensurePreset() re-render",
        "宿主行 `ensurePreset()` 按包版本重渲染",
        "宿主行 ensurePreset() 按包版本幂等重渲染",
        "bundle 宿主行 `ensurePreset()` 按包版本幂等重渲染",
        "只有未声明 registry row 的旧宿主才渲染用户根目录",
        "the inserted row then renders the packaged preset",
        "renders the identical",
        "which re-renders it by",
        "by the bundle row lib/index.js on boot",
        "whose lib/index.js ensurePreset() renders",
    )

    def test_contract_input_describes_the_behaviour_the_row_implements(self):
        """DEC-366 ② / D-R6-7 / R1-F1: docs must describe the row that ships.

        Three facts are pinned across the contract, both READMEs, the adapter
        manifest and the launcher docstring: the four unavailable states are
        named; every one of them writes nothing; and the row never renders a
        preset directory. Positive wording is required AND the retired wording
        is forbidden, so this test cannot go green while a doc says the
        opposite of the code.
        """
        contract = json.loads(_CONTRACT.read_text(encoding="utf-8"))
        policy = contract["own"]["native"]["legacy_policy"]
        self.assertNotIn("legacyAutoRender", policy)
        for state in ("absent", "disabled", "unreadable", "ambiguous"):
            self.assertIn(state, policy, state)
        self.assertIn("writes nothing", policy)
        self.assertIn("never renders a directory", policy)
        self.assertNotIn("automatic legacy user-root render", policy)
        root_readme = (_REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("does not fall back to writing a preset directory", root_readme)
        for state in ("absent", "disabled", "unreadable", "ambiguous"):
            self.assertIn(state, root_readme, state)
        self.assertIn("never renders a preset directory", root_readme)
        adapter_readme = (_REPO_ROOT / "adapters" / "dsh" / "README.md").read_text(encoding="utf-8")
        for state in ("absent", "disabled", "unreadable", "ambiguous"):
            self.assertIn(state, adapter_readme, state)
        self.assertIn("绝不写目录", adapter_readme)
        # The row-path comment must state the retirement, and the explicit
        # renderer must stay documented as the only writer.
        lib_source = _LIB_INDEX.read_text(encoding="utf-8")
        self.assertIn("never renders the legacy user-root directory", lib_source)
        self.assertIn("Explicit install face only", lib_source)

        # R1-F1: positive half — the new operational wording must be present in
        # every surface that used to promise the auto-render.
        new_wording = {
            "README.md": (
                "the inserted row never re-renders a directory",
                "the inserted row itself never renders a directory",
                "row 只做登记/warn，**不自动渲染**",
            ),
            "adapters/dsh/README.md": (
                "宿主行不自动渲染",
                "不渲染用户根目录",
                "不再由宿主行渲染",
            ),
        }
        for name, text in (("README.md", root_readme),
                           ("adapters/dsh/README.md", adapter_readme)):
            for phrase in new_wording[name]:
                self.assertIn(phrase, text, f"{name}: missing new wording {phrase!r}")
        manifest = json.loads(
            (_REPO_ROOT / "adapters" / "dsh" / "adapter-manifest.json")
            .read_text(encoding="utf-8"))
        manifest_text = json.dumps(manifest, ensure_ascii=False)
        self.assertIn("registers natively or warns and never writes this file", manifest_text)
        self.assertIn("registers the preset natively through the public agent-presets registry",
                      manifest_text)
        launcher = (_REPO_ROOT / "adapters" / "dsh" / "launch.py").read_text(encoding="utf-8")
        self.assertIn("this launcher is the explicit /", launcher)
        self.assertIn("The inserted host row never re-renders the real user", launcher)
        self.assertIn("directory-model install is this explicit command", launcher)

        # R1-F1: negative half — none of the retired sentences may come back,
        # in any of the four surfaces.
        for name, text in (("README.md", root_readme),
                           ("adapters/dsh/README.md", adapter_readme),
                           ("adapters/dsh/adapter-manifest.json", manifest_text),
                           ("adapters/dsh/launch.py", launcher)):
            for phrase in self._RETIRED_AUTO_RENDER_WORDING:
                self.assertNotIn(
                    phrase, text,
                    f"{name}: retired auto-render wording came back: {phrase!r}")

    def test_persona_body_matches_the_legacy_composition(self):
        """One governance body; the legacy composition carries the same text.

        The composition prepends the host identity line (it REPLACES the prefix,
        so it needs its own identity); the native path APPENDS the body to the
        host's prefix. Everything from the Coordinator paragraph on must match.
        """
        composition = _TEMPLATE.read_text(encoding="utf-8")
        lines = composition.splitlines()
        start = lines.index("    prefix: |-") + 1
        body = []
        for line in lines[start:]:
            if line.strip() == "":
                body.append("")
                continue
            if not line.startswith("      "):
                break
            body.append(line[6:])
        # The block starts with a blank line and the host identity paragraph; the
        # governance body begins at the Coordinator line.
        start_of_body = next(
            index for index, line in enumerate(body)
            if line.startswith("你是 software-project-governance")
        )
        legacy_body = "\n".join(body[start_of_body:]).strip()
        # Both sides carry the same render token; compare them normalized so the
        # check is about the governance text, not about whitespace or the token.
        def normalize(text: str) -> str:
            return re.sub(r"\s+", " ", text.replace("__GOVERNANCE_REPO_ROOT__", "<ROOT>")).strip()

        persona = _PERSONA.read_text(encoding="utf-8")
        self.assertEqual(
            normalize(legacy_body),
            normalize(persona),
            "the native persona body drifted from the legacy composition",
        )

    def test_contract_native_skill_roots_match_the_render_tokens(self):
        contract = json.loads(_CONTRACT.read_text(encoding="utf-8"))
        native = contract["own"]["native"]
        tokens = contract["own"]["render"]["tokens"]
        self.assertEqual(native["skill_roots"], [tokens["__GOVERNANCE_SKILLS_ROOT__"], tokens["__GOVERNANCE_SHIMS_ROOT__"]])
        self.assertEqual(native["persona_source"], "agent-presets/governance/persona.md.template")
        self.assertEqual(contract["own"]["preset"]["id"], "governance")

    def test_row_exports_stay_the_contract_surface(self):
        source = _LIB_INDEX.read_text(encoding="utf-8")
        for export in ("apply", "ensurePreset", "renderComposition", "name"):
            self.assertRegex(source, rf"export (function |const )?{export}\b")
        contract = json.loads(_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(contract["own"]["host_row"]["export_surface"]),
            ["apply", "ensurePreset", "name", "renderComposition"],
        )


if __name__ == "__main__":
    unittest.main()
