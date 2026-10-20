/**
 * Package-owned inputs of the native derivation: the governance persona body and
 * the display metadata.
 *
 * Both are plain files in this package, read from the *package root derived from
 * this module's URL* — never from the process cwd and never from a stored
 * absolute path. A checkout that moves, or a same-version reinstall under a
 * different prefix, therefore still resolves its own content (the coupling the
 * old version marker could not see).
 *
 * Reading happens inside the registration callback, not at module load: an
 * import-time read would turn "one file is missing" into "the host row fails to
 * import", and a failing import takes down the whole boot.
 *
 * @module lib/dsh-native/persona
 */

import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/** Forward-slash spelling for text embedded in prompts (matches the renderer). */
export function posixPath(value) {
  return value.replace(/\\/g, '/')
}

/**
 * Load the governance persona body and substitute the package-root token.
 *
 * The body is appended to the host's own persona prefix, so it must NOT repeat
 * the host identity line: the base preset keeps ownership of that text and of
 * any user override.
 *
 * @param {string} pkgRoot - absolute package root (from `import.meta.url`).
 * @param {object} spec - the projected native specification.
 * @returns {string} the body with the package root substituted.
 * @throws {Error} when the file is unreadable or still carries a render token.
 */
export function loadPersonaBody(pkgRoot, spec) {
  const text = readFileSync(join(pkgRoot, spec.personaSource), 'utf8').replace(/\r\n/g, '\n')
  if (!text.includes(spec.personaToken)) {
    throw new Error(`persona source declares no ${spec.personaToken} token`)
  }
  const body = text.split(spec.personaToken).join(posixPath(pkgRoot)).trim()
  const leftovers = body.match(new RegExp(spec.leftoverScan, 'g'))
  if (leftovers !== null) {
    throw new Error(`persona body carries unresolved token(s) ${[...new Set(leftovers)].join(', ')}`)
  }
  if (body === '') throw new Error('persona body is empty')
  return body
}

/**
 * Read the preset display metadata (`name` / `description`) from the shipped
 * `preset.yml`.
 *
 * The file is a two-scalar YAML projection, not a general document, so this is a
 * deliberate scalar parser rather than a YAML dependency: the package declares
 * no runtime dependency, and a dependency here would be a new thing to break on
 * every host upgrade. An unparseable value degrades to the preset id — display
 * metadata must never be able to fail the registration.
 *
 * @param {string} pkgRoot - absolute package root.
 * @param {object} spec - the projected native specification.
 * @returns {{name: string, description: string|undefined}} display metadata.
 */
export function loadPresetMetadata(pkgRoot, spec) {
  const metadata = { name: spec.presetId, description: undefined }
  let text = ''
  try {
    text = readFileSync(join(pkgRoot, spec.metadataPath), 'utf8')
  } catch {
    return metadata
  }
  for (const line of text.split(/\r?\n/)) {
    const match = /^(name|description):\s*(.+)$/.exec(line)
    if (match === null) continue
    const value = match[2].trim().replace(/^(['"])(.*)\1$/, '$2').trim()
    if (value === '') continue
    if (match[1] === 'name') metadata.name = value
    else metadata.description = value
  }
  return metadata
}
