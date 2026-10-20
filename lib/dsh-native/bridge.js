/**
 * Native bridge: derive the governance preset from the host's own declaration.
 *
 * FEAT-102. The entry row (`lib/index.js`) delegates here when the composed
 * profile declares a host-owned agent-preset registry. The bridge:
 *
 *   1. projects the contract's native block (`spec.js`);
 *   2. decides native vs. legacy from the *declaration* of the registry row,
 *      never from a host version (`source.js` `probeNativeHost`);
 *   3. defers the actual registration to the moment the registry service
 *      exists — a profile row's `apply()` runs before services are provided, so
 *      `ctx.inject(['agentPresets'], …)` is the public wait, and it is a service
 *      dependency, not a sleep or an ordering guess;
 *   4. locates one enabled base declaration, loads this package's two inputs,
 *      derives the definition (`overlay.js`) and hands it to the registry
 *      (`lifecycle.js`).
 *
 * Every step reports a structured code and never throws: the row's failure
 * policy is warn-only, because a throwing row takes down the whole host boot.
 *
 * @module lib/dsh-native/bridge
 */

import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { startRegistration } from './lifecycle.js'
import { deriveDefinition } from './overlay.js'
import { loadPersonaBody, loadPresetMetadata, posixPath } from './persona.js'
import { locateBase, probeNativeHost } from './source.js'
import { nativeSpec } from './spec.js'

/** Package root from this module's URL: `lib/dsh-native/bridge.js` → package. */
function packageRoot() {
  return fileURLToPath(new URL('../..', import.meta.url)).replace(/[\\/]+$/, '')
}

/** Absolute skill roots, forward-slashed exactly like the legacy renderer. */
function absoluteRoots(pkgRoot, spec) {
  return spec.skillRoots.map((relative) => posixPath(relative === '' ? pkgRoot : join(pkgRoot, relative)))
}

/** Read the injected service defensively (`ctx.get` never throws on absence). */
function service(ctx, name) {
  try {
    return typeof ctx?.get === 'function' ? ctx.get(name) : undefined
  } catch {
    return undefined
  }
}

/**
 * Run one native attempt with the registry available.
 *
 * @returns {{status: string, code: string, message?: string, presetId?: string,
 *            baseAddress?: string, rows?: number}}
 */
function registerDerived(child, config, spec, pkgRoot, logger) {
  const basePresetId = typeof config?.basePresetId === 'string' && config.basePresetId.trim() !== ''
    ? config.basePresetId.trim()
    : spec.basePresetId
  if (basePresetId === spec.presetId) {
    return {
      status: 'refused',
      code: 'BASE_IS_SELF',
      message: `basePresetId must differ from the derived preset id ${JSON.stringify(spec.presetId)}`,
    }
  }
  const located = locateBase(service(child, 'loader'), spec, basePresetId)
  if (!located.ok) return { status: 'refused', code: located.code, message: located.message }

  let personaBody
  try {
    personaBody = loadPersonaBody(pkgRoot, spec)
  } catch (error) {
    return { status: 'refused', code: 'PERSONA_UNREADABLE', message: String(error) }
  }
  const metadata = loadPresetMetadata(pkgRoot, spec)
  const derived = deriveDefinition(located.entry.options.config, {
    personaRowName: spec.personaRowName,
    skillRowName: spec.skillRowName,
    personaBody,
    skillRoots: absoluteRoots(pkgRoot, spec),
    presetId: spec.presetId,
    name: metadata.name,
    description: metadata.description,
  })
  if (!derived.ok) return { status: 'refused', code: derived.code, message: derived.message }

  const started = startRegistration(child, derived.definition, logger)
  if (started.status !== 'starting') return { status: 'failed', code: started.code, message: started.message }
  logger?.info?.(
    `software-project-governance: agent preset '${spec.presetId}' derived from base `
    + `'${basePresetId}' (${located.address}, ${derived.baseRows} rows, native declarations)`,
  )
  return {
    status: 'starting',
    code: 'REGISTERED',
    presetId: spec.presetId,
    baseAddress: located.address,
    rows: derived.baseRows,
  }
}

/**
 * Apply the native path, or report why the host is not a native host.
 *
 * @param {object} ctx - the row's Cordis context.
 * @param {object|undefined} config - the row config (`basePresetId` supported).
 * @param {() => object|null} readContract - the entry module's memoized contract reader.
 * @returns {{mode: 'native'|'legacy'|'refused', code: string, message?: string,
 *            presetId?: string, baseAddress?: string, rows?: number}}
 */
export function applyNative(ctx, config, readContract) {
  let contract = null
  try {
    contract = typeof readContract === 'function' ? readContract() : null
  } catch {
    contract = null
  }
  const spec = nativeSpec(contract)
  if (spec === null) {
    return {
      mode: 'refused',
      code: 'CONTRACT_WITHOUT_NATIVE_BLOCK',
      message: 'the shipped host contract does not declare the native protocol',
    }
  }
  const loader = service(ctx, 'loader')
  if (loader === undefined && typeof ctx?.inject === 'function') {
    // A real Cordis row that cannot read the composed tree: refusing beats
    // guessing "old host" and writing the retired directory on a modern one.
    return {
      mode: 'refused',
      code: 'HOST_TREE_UNAVAILABLE',
      message: 'the composed loader entry tree is not readable during row activation',
    }
  }
  const host = probeNativeHost(loader, spec)
  if (!host.present) {
    return {
      mode: 'legacy',
      code: 'HOST_WITHOUT_REGISTRY',
      message: `this profile declares no ${spec.registryRowName} row; the host predates natively declared agent presets`,
    }
  }
  if (!host.enabled) {
    return {
      mode: 'refused',
      code: 'REGISTRY_ROW_DISABLED',
      message: `the profile declares ${spec.registryRowName} but disables it; nothing was written`,
    }
  }

  const pkgRoot = packageRoot()
  const logger = ctx?.logger
  const runNow = () => {
    try {
      return registerDerived(ctx, config, spec, pkgRoot, logger)
    } catch (error) {
      return { status: 'failed', code: 'NATIVE_BRIDGE_THREW', message: String(error) }
    }
  }

  const report = (outcome) => {
    if (outcome.status === 'starting') return
    logger?.warn?.(
      `software-project-governance: agent preset not registered (${outcome.code}): ${outcome.message ?? ''}`,
    )
  }

  // The registry service is provided after the profile rows' apply() calls, so
  // the common path defers to the public service dependency. If the service is
  // already there (another registration ordered it earlier), register now.
  if (service(ctx, 'agentPresets') !== undefined) {
    const outcome = runNow()
    report(outcome)
    return { mode: 'native', ...outcome }
  }
  if (typeof ctx?.inject !== 'function') {
    return {
      mode: 'refused',
      code: 'HOST_NO_SERVICE_INJECTION',
      message: 'the host context cannot defer on a service, so the registry was never awaited',
    }
  }
  try {
    ctx.inject(['agentPresets'], (child) => {
      let outcome
      try {
        outcome = registerDerived(child, config, spec, pkgRoot, logger)
      } catch (error) {
        outcome = { status: 'failed', code: 'NATIVE_BRIDGE_THREW', message: String(error) }
      }
      report(outcome)
    })
  } catch (error) {
    return { mode: 'refused', code: 'INJECT_FAILED', message: String(error) }
  }
  return { mode: 'native', code: 'DEFERRED', presetId: spec.presetId }
}
