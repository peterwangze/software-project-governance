/**
 * Native-declaration protocol: read the `own.native` block of the host contract.
 *
 * FEAT-102 (DSH 0.2 upgrade + version-dependency decoupling). The legacy
 * delivery renders a whole composition (every host tool row copied into the
 * package) into `$DSH_HOME/.agent-presets/`. That model is retired by the host
 * and, worse, it re-couples this package to every host tool change: a rename or
 * a new row in the host's base preset silently invalidates the copy.
 *
 * The native model keeps exactly two content deltas over whatever the host
 * currently declares (persona prefix + the two skill roots) and derives the
 * rest at boot from the host's own accepted declaration. No version equality is
 * ever consulted: a host that exposes the capability is supported, a host that
 * does not is refused with an explicit reason.
 *
 * This module only *reads* the contract view handed in by the entry module
 * (`lib/index.js` owns the one memoized file read, J-3). It performs no I/O and
 * never writes.
 *
 * @module lib/dsh-native/spec
 */

/** Dotted path lookup; `undefined` when any hop is absent. */
function at(node, path) {
  let cursor = node
  for (const key of path.split('.')) {
    if (cursor === null || typeof cursor !== 'object') return undefined
    cursor = cursor[key]
  }
  return cursor
}

/**
 * Project the contract into the frozen native specification.
 *
 * @param {object|null} contract - parsed host contract, or `null` when unreadable.
 * @returns {null|object} the specification, or `null` when the contract does
 *   not declare the native protocol (an old package/contract, never guessed).
 */
export function nativeSpec(contract) {
  const declared = at(contract, 'own.native')
  if (declared === null || typeof declared !== 'object') return null
  const strings = {
    protocol: declared.protocol,
    baseRowName: declared.base_row_name,
    personaRowName: declared.persona_row_name,
    skillRowName: declared.skill_row_name,
    registryRowName: declared.registry_row_name,
    basePresetId: declared.base_preset_id_default,
    personaSource: declared.persona_source,
    personaToken: declared.persona_repo_token,
  }
  for (const [key, value] of Object.entries(strings)) {
    if (typeof value !== 'string' || value.trim() === '') return null
  }
  const presetId = at(contract, 'own.preset.id')
  const metadataPath = at(contract, 'own.preset.metadata')
  const leftoverScan = at(contract, 'own.render.leftover_scan')
  const skillRoots = declared.skill_roots
  if (typeof presetId !== 'string' || presetId === '') return null
  if (typeof metadataPath !== 'string' || metadataPath === '') return null
  if (!Array.isArray(skillRoots) || skillRoots.length === 0) return null
  for (const root of skillRoots) {
    if (typeof root !== 'string' || root === '') return null
  }
  return {
    ...strings,
    presetId,
    metadataPath,
    skillRoots: skillRoots.slice(),
    // The scan is the same declared expression the legacy renderer uses for
    // leftover tokens; a persona body that still carries one is a defect.
    leftoverScan: typeof leftoverScan === 'string' && leftoverScan !== ''
      ? leftoverScan
      : '__[A-Za-z0-9_]+__',
  }
}
