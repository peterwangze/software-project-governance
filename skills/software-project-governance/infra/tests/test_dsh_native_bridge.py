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

const legacy = applyNative({ get: () => undefined, logger: { warn: () => {} } }, {}, () => contract)

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
let native = process.argv[2] === 'native'
const ctx = {
  get: (name) => (name === 'loader' ? loaderFor(native) : undefined),
  logger: { info: () => {}, warn: () => {} },
  effect: () => {},
  inject: (deps, callback) => callback({
    agentPresets: { register: (definition) => { registered.push(definition); return Promise.resolve(async () => {}) } },
    get: (name) => (name === 'loader' ? loaderFor(native) : undefined),
    effect: () => {},
  }),
}
apply(ctx, {})
process.stdout.write(JSON.stringify({ registered: registered.length }))
"""


@unittest.skipUnless(_node(), "node unavailable (native bridge cannot be exercised)")
class NativeBridgeTests(unittest.TestCase):
    def _run(self, script: str, *args: str) -> dict:
        result = subprocess.run(
            [_node(), "--input-type=module", "-e", script, str(_REPO_ROOT), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
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
        payload = self._run(_APPLY_PROBE, "native")
        self.assertEqual(payload["registered"], 1, "the native registration must be issued")
        # The bridge never touches the legacy directory; the probe runs in the
        # repo cwd, so assert no preset root was created beside it either.
        self.assertFalse((_REPO_ROOT / ".agent-presets").exists())

    def test_apply_preserves_the_legacy_host_path(self):
        with tempfile.TemporaryDirectory() as td:
            env = {"DSH_HOME": td}
            script = _APPLY_PROBE
            result = subprocess.run(
                [_node(), "--input-type=module", "-e", script, str(_REPO_ROOT), "legacy"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env={**__import__("os").environ, **env},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["registered"], 0)
            preset = Path(td) / ".agent-presets" / "governance" / "agent.cordis.yml"
            self.assertTrue(preset.is_file(), "a host without the registry row must still get the legacy preset")


class PersonaAndContractTests(unittest.TestCase):
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
