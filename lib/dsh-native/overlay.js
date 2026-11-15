/**
 * Pure derivation of the governance preset from the host's current base
 * declaration.
 *
 * Two content deltas, nothing else:
 *
 *   1. the governance body is appended to the base `dsh-persona` prefix (the
 *      host identity line and any user prefix/suffix stay exactly as declared);
 *   2. this package's two skill roots are appended to the base
 *      `dsh-skill-filesystem` `customSkillDirs` (existing roots, provider name,
 *      `includeDefaultRoots`, watch settings and every unknown field survive).
 *      A `customSkillDirs` entry may also be a loader `!!js` expression node
 *      (`{__jsExpr: string}`, the host loader composed tree's only serialized
 *      form for the YAML tag); such nodes are passed through verbatim for the
 *      host to evaluate at child activation, and path de-duplication stays a
 *      string-only comparison.
 *
 * Every other row — tools, groups, isolate realms, `!!js` expressions, order,
 * disabled flags — is carried over by a structured clone, so a host upgrade that
 * adds, replaces or disables a tool row propagates into the governance preset
 * without any change in this package. That inheritance is the version-decoupling
 * property: the package no longer owns a copy of the host's tool list.
 *
 * The function is pure: no I/O, no host access, no mutation of its input. It
 * returns a structured refusal instead of throwing so the caller can log one
 * actionable line and leave the host untouched (fail-closed, warn-only).
 *
 * @module lib/dsh-native/overlay
 */

/**
 * Path identity for `customSkillDirs` de-duplication.
 *
 * Case folding is a FILESYSTEM property, not a portability default (CODE R0
 * F10): on a case-sensitive volume `/A/skills` and `/a/skills` are two real
 * directories, and folding them would silently drop one of the package's skill
 * roots. Separator folding is likewise Windows-only — on POSIX a backslash is
 * an ordinary filename character.
 */
const FOLD_CASE = process.platform === 'win32' || process.platform === 'darwin'

function samePath(left, right) {
  const normalize = (value) => {
    const unified = process.platform === 'win32' ? value.replace(/\\/g, '/') : value
    const trimmed = unified.replace(/\/+$/, '')
    return FOLD_CASE ? trimmed.toLowerCase() : trimmed
  }
  return normalize(left) === normalize(right)
}

/**
 * A serialized loader `!!js` expression node (`{__jsExpr: string}`) — the
 * host loader composed tree's only serialized form (cordis-plugin-loader
 * config/utils.ts `isJsExpr` checks `'__jsExpr' in value`; no other key form
 * exists on a real tree). Accepted only in that narrow shape: a plain object
 * whose single own enumerable key is `__jsExpr` with a string value. Any other
 * shape is unknown data, not an expression, and refuses fail-closed.
 */
function isJsExprNode(value) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false
  const proto = Object.getPrototypeOf(value)
  if (proto !== Object.prototype && proto !== null) return false
  const keys = Object.keys(value)
  return keys.length === 1 && keys[0] === '__jsExpr' && typeof value.__jsExpr === 'string'
}

/** Indexes of the rows whose module specifier is exactly `name`. */
function rowIndexes(rows, name) {
  const indexes = []
  for (let index = 0; index < rows.length; index += 1) {
    if (rows[index] !== null && typeof rows[index] === 'object' && rows[index].name === name) {
      indexes.push(index)
    }
  }
  return indexes
}

/** A declared `disabled` that is not plainly false/absent cannot be merged safely. */
function declaredDisabled(row) {
  return row.disabled !== undefined && row.disabled !== null && row.disabled !== false
}

/**
 * @param {object} baseConfig - the base declaration's config (`{id, plugins}`).
 * @param {object} options - derivation inputs.
 * @param {string} options.personaRowName - persona module specifier.
 * @param {string} options.skillRowName - skill-filesystem module specifier.
 * @param {string} options.personaBody - governance body (already substituted).
 * @param {string[]} options.skillRoots - absolute skill roots for this package.
 * @param {string} options.presetId - the derived preset id.
 * @param {string} options.name - display name.
 * @param {string} [options.description] - display description.
 * @returns {{ok: true, definition: object, baseRows: number}|{ok: false, code: string, message: string}}
 */
export function deriveDefinition(baseConfig, options) {
  if (baseConfig === null || typeof baseConfig !== 'object' || Array.isArray(baseConfig)) {
    return { ok: false, code: 'BASE_CONFIG_INVALID', message: 'base declaration has no config object' }
  }
  const rows = baseConfig.plugins
  if (!Array.isArray(rows) || rows.length === 0) {
    return { ok: false, code: 'BASE_CONFIG_INVALID', message: 'base declaration has no plugin rows' }
  }
  let plugins
  try {
    plugins = structuredClone(rows)
  } catch (error) {
    // A row carrying a function/closure is not declarative data; cloning it would
    // silently drop or share state, so refuse instead of guessing.
    return { ok: false, code: 'BASE_NOT_CLONEABLE', message: String(error) }
  }

  const personaIndexes = rowIndexes(plugins, options.personaRowName)
  if (personaIndexes.length !== 1) {
    return {
      ok: false,
      code: personaIndexes.length === 0 ? 'PERSONA_ROW_MISSING' : 'PERSONA_ROW_DUPLICATE',
      message: `expected exactly one ${options.personaRowName} row, found ${personaIndexes.length}`,
    }
  }
  const personaRow = plugins[personaIndexes[0]]
  if (declaredDisabled(personaRow)) {
    return { ok: false, code: 'PERSONA_ROW_DISABLED', message: 'the base persona row is disabled' }
  }
  if (personaRow.config === null || personaRow.config === undefined) personaRow.config = {}
  if (typeof personaRow.config !== 'object' || Array.isArray(personaRow.config)) {
    return { ok: false, code: 'PERSONA_CONFIG_INVALID', message: 'the base persona config is not an object' }
  }
  const prefix = personaRow.config.prefix
  if (prefix !== undefined && typeof prefix !== 'string') {
    // A `!!js` prefix is resolved against the composing context at mount time;
    // evaluating it early to append text would change its semantics.
    return {
      ok: false,
      code: 'PERSONA_PREFIX_UNSUPPORTED',
      message: 'the base persona prefix is not a literal string',
    }
  }
  const basePrefix = typeof prefix === 'string' ? prefix.trimEnd() : ''
  personaRow.config.prefix = basePrefix === ''
    ? `${options.personaBody}\n`
    : `${basePrefix}\n\n${options.personaBody}\n`

  const skillIndexes = rowIndexes(plugins, options.skillRowName)
  if (skillIndexes.length !== 1) {
    return {
      ok: false,
      code: skillIndexes.length === 0 ? 'SKILL_ROW_MISSING' : 'SKILL_ROW_DUPLICATE',
      message: `expected exactly one ${options.skillRowName} row, found ${skillIndexes.length}`,
    }
  }
  const skillRow = plugins[skillIndexes[0]]
  if (declaredDisabled(skillRow)) {
    return { ok: false, code: 'SKILL_ROW_DISABLED', message: 'the base skill-filesystem row is disabled' }
  }
  if (skillRow.config === null || skillRow.config === undefined) skillRow.config = {}
  if (typeof skillRow.config !== 'object' || Array.isArray(skillRow.config)) {
    return { ok: false, code: 'SKILL_CONFIG_INVALID', message: 'the base skill-filesystem config is not an object' }
  }
  const declaredDirs = skillRow.config.customSkillDirs
  if (declaredDirs !== undefined && !Array.isArray(declaredDirs)) {
    return {
      ok: false,
      code: 'SKILL_DIRS_UNSUPPORTED',
      message: 'the base customSkillDirs is not a literal array',
    }
  }
  // Entry validation inspects the DECLARED entries, not the cloned ones:
  // structured clone launders exotic prototypes (a class instance with an own
  // `__jsExpr` becomes a plain single-key object), which would smuggle a
  // shape that never exists on a real loader tree past the check.
  const declaredRow = rows[skillIndexes[0]]
  const declaredEntries = declaredRow.config !== null && typeof declaredRow.config === 'object'
    && !Array.isArray(declaredRow.config) ? declaredRow.config.customSkillDirs : undefined
  if (Array.isArray(declaredEntries)) {
    for (const dir of declaredEntries) {
      if (typeof dir === 'string' || isJsExprNode(dir)) continue
      return {
        ok: false,
        code: 'SKILL_DIRS_UNSUPPORTED',
        message: dir !== null && typeof dir === 'object' && !Array.isArray(dir) && '__jsExpr' in dir
          ? 'customSkillDirs carries an expression node with an invalid shape'
          : 'customSkillDirs carries a non-string entry',
      }
    }
  }
  const dirs = Array.isArray(declaredDirs) ? declaredDirs.slice() : []
  for (const root of options.skillRoots) {
    // Expression nodes are opaque until the loader evaluates them at child
    // activation, so only literal strings participate in path identity.
    if (!dirs.some((dir) => typeof dir === 'string' && samePath(dir, root))) dirs.push(root)
  }
  skillRow.config = { ...skillRow.config, customSkillDirs: dirs }

  const definition = {
    id: options.presetId,
    name: options.name,
    ...(options.description === undefined ? {} : { description: options.description }),
    plugins,
  }
  return { ok: true, definition, baseRows: rows.length }
}
