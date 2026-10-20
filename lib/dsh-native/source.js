/**
 * Read the host's current base declaration out of the public Loader tree.
 *
 * Two public facts are read here and nowhere else:
 *
 *   * `ctx.loader.entries()` — every entry of the composed profile tree,
 *     including nested groups. The loader writes an entry's declared options
 *     into the tree *before* it starts any entry, so a row that activates early
 *     still sees the complete sibling declaration set;
 *   * `entry.disabled` — the host's own effective-disable semantics (the entry
 *     plus any owning group), so a disabled base is refused instead of derived
 *     from.
 *
 * No private field, no host package import, no version comparison. The address
 * is the loader's own entry id, which is what makes a diagnostic actionable.
 *
 * @module lib/dsh-native/source
 */

/** Effective disabled state, or `undefined` when the expression itself throws. */
function effectiveDisabled(entry) {
  try {
    return entry.disabled
  } catch {
    // An expression that throws is not "enabled": refuse the candidate rather
    // than deriving from a row the host itself cannot evaluate.
    return undefined
  }
}

/**
 * Does this profile compose a host that owns an agent-preset registry?
 *
 * This is the capability probe that decides native vs. legacy. It reads a
 * *declaration*, not a version: a host that stops declaring the registry row is
 * treated as the old model, and a host that declares it gets the native path —
 * the registry service itself is awaited through `ctx.inject`, because services
 * are not available when a profile row's `apply()` runs.
 *
 * @param {object} loader - public loader service (`ctx.get('loader')`).
 * @param {object} spec - projected native specification.
 * @returns {{present: boolean, enabled: boolean}}
 */
export function probeNativeHost(loader, spec) {
  if (loader === null || loader === undefined || typeof loader.entries !== 'function') {
    return { present: false, enabled: false }
  }
  let present = false
  let enabled = false
  try {
    for (const entry of loader.entries()) {
      if (entry?.options?.name !== spec.registryRowName) continue
      present = true
      if (effectiveDisabled(entry) === false) enabled = true
    }
  } catch {
    return { present: false, enabled: false }
  }
  return { present, enabled }
}

/**
 * Locate exactly one enabled base declaration.
 *
 * @param {object} loader - public loader service.
 * @param {object} spec - projected native specification.
 * @param {string} basePresetId - requested base preset id.
 * @returns {{ok: true, entry: object, address: string}|{ok: false, code: string, message: string}}
 */
export function locateBase(loader, spec, basePresetId) {
  if (loader === null || loader === undefined || typeof loader.entries !== 'function') {
    return { ok: false, code: 'HOST_NO_LOADER_TREE', message: 'the host exposes no loader entry tree' }
  }
  const matches = []
  try {
    for (const entry of loader.entries()) {
      if (entry?.options?.name !== spec.baseRowName) continue
      if (entry.options.config?.id !== basePresetId) continue
      matches.push(entry)
    }
  } catch (error) {
    return { ok: false, code: 'HOST_TREE_UNREADABLE', message: String(error) }
  }
  if (matches.length === 0) {
    return {
      ok: false,
      code: 'BASE_NOT_FOUND',
      message: `no ${spec.baseRowName} declaration with config.id=${JSON.stringify(basePresetId)}`,
    }
  }
  if (matches.length > 1) {
    return {
      ok: false,
      code: 'BASE_DUPLICATE',
      message: `${matches.length} enabled-capable declarations claim id ${JSON.stringify(basePresetId)}`,
    }
  }
  const entry = matches[0]
  const disabled = effectiveDisabled(entry)
  if (disabled !== false) {
    return {
      ok: false,
      code: disabled === undefined ? 'BASE_DISABLED_UNEVALUABLE' : 'BASE_DISABLED',
      message: `the base declaration ${JSON.stringify(entry.id)} is not enabled`,
    }
  }
  return { ok: true, entry, address: String(entry.id) }
}
