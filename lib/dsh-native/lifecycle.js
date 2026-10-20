/**
 * Registration lifecycle of the derived preset.
 *
 * The host's public contract is `agentPresets.register(definition):
 * Promise<disposer>`: the registry record is created synchronously, then the
 * activation (mount + audit) runs and the returned promise settles with the
 * disposer this package owns. Two consequences drive this module:
 *
 *   * **admission is synchronous** — consumers that look the preset up right
 *     after the call already see the record and wait for its readiness, which
 *     is why the registration is issued as early as the service exists;
 *   * **disposal must not wait for activation** — this row's cleanup only marks
 *     itself disposed and detaches its own registration. It never awaits a
 *     registration still in flight: waiting would let this row's unload depend
 *     on a mount that may itself be waiting on the host. A disposer that
 *     arrives after the row is gone is invoked immediately and its rejection
 *     consumed.
 *
 * Failure policy stays warn-only: a registration rejection is reported and the
 * host continues without the governance preset. It never throws out of the
 * row's activation.
 *
 * @module lib/dsh-native/lifecycle
 */

/** Swallow a late disposer rejection; a failed unload must not become a crash. */
function consume(promise, logger, label) {
  Promise.resolve(promise).catch((error) => {
    logger?.warn?.(`software-project-governance: ${label} failed: ${String(error)}`)
  })
}

/**
 * Issue the registration and own exactly one disposal handle.
 *
 * @param {object} ctx - a context that carries the agent-preset registry.
 * @param {object} definition - derived preset definition.
 * @param {object} logger - context logger (may be a no-op).
 * @param {(event: string, data?: object) => void} [observe] - optional sink used
 *   by tests/diagnostics; production passes nothing.
 * @returns {{status: 'starting'|'failed', code: string, message?: string}}
 */
export function startRegistration(ctx, definition, logger, observe) {
  const registry = ctx?.agentPresets
  if (registry === null || registry === undefined || typeof registry.register !== 'function') {
    return { status: 'failed', code: 'HOST_NO_AGENT_PRESETS', message: 'the registry service exposes no register()' }
  }
  let registration
  try {
    registration = registry.register(definition)
  } catch (error) {
    // Synchronous refusals are the registry's own validation: empty id, a
    // duplicate id, or an id already owned by another declaration.
    return { status: 'failed', code: 'REGISTER_REFUSED', message: String(error) }
  }
  const state = { disposed: false, disposer: null }
  Promise.resolve(registration).then(
    (disposer) => {
      if (typeof disposer !== 'function') return
      state.disposer = disposer
      observe?.('registration-activated')
      if (state.disposed) {
        // The row was unloaded while activation was in flight; the registration
        // it no longer wants is withdrawn now that the host handed over the way
        // to withdraw it.
        state.disposer = null
        consume(disposer(), logger, 'late registration disposal')
      }
    },
    (error) => {
      logger?.warn?.(`software-project-governance: agent preset registration failed: ${String(error)}`)
      observe?.('registration-rejected')
    },
  )
  if (typeof ctx.effect === 'function') {
    ctx.effect(() => () => {
      state.disposed = true
      const disposer = state.disposer
      state.disposer = null
      observe?.('disposed')
      if (disposer !== null) consume(disposer(), logger, 'registration disposal')
    })
  }
  observe?.('registration-issued')
  return { status: 'starting', code: 'REGISTERED' }
}
