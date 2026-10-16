/**
 * Governance pi extension — entry point (single responsibility: registration
 * assembly only).
 *
 * A directory containing index.ts is recognized by pi as a multi-file
 * extension (docs/extensions.md L46); wiring goes through the settings.json
 * `extensions` path array (docs/settings.md L152) or a one-shot
 * `pi -e adapters/pi/extension` (docs/cli.md L194-195).
 *
 * Registers the two governance bridge tools, both `model-only` exposure
 * (declared to the model, never callable — docs/extensions.md L157):
 *   - ask_user_question: interaction-boundary bridge (dialog methods,
 *     tui/rpc; structured headless error otherwise)
 *   - dispatch_agent:    role-agent dispatch bridge (nested pi process with
 *     isolated context window, per the official subagent example)
 *
 * Dependency direction (design §2.1, acyclic):
 *   index -> { ask-user, dispatch-agent } -> { nested-runner, paths }
 * Runtime value imports are limited to `typebox` (virtualized by the pi
 * runtime — dist/core/extensions/virtual-modules.js L14-19); all
 * "@earendil-works/pi-coding-agent" imports are `import type` and erased at
 * compile time, so no node_modules shipping is needed (design §2.2/§2.3).
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

import { governanceAskUserTool } from "./ask-user.ts";
import { governanceDispatchAgentTool } from "./dispatch-agent.ts";

export default function governanceExtension(pi: ExtensionAPI): void {
	pi.registerTool(governanceAskUserTool());
	pi.registerTool(governanceDispatchAgentTool());
}
