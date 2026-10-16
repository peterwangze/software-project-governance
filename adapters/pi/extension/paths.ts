/**
 * Governance pi extension — path resolution (single responsibility: paths only).
 *
 * pluginRoot is derived from this file's own location
 * (adapters/pi/extension/paths.ts -> parents[3] = repository root), so the
 * extension never depends on cwd for resolving governance assets.
 *
 * Evidence anchors (pi v1.1.0): role/skill semantics per
 * references/agent-dispatch-template.md placeholder table L94-108
 * ({role_definition_path} / {task_skill_path}); pi settings wiring uses
 * repo-absolute paths (docs/settings.md L147-158), so both resolution bases
 * (plugin root and cwd) are legitimate for dispatch callers.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";

/** Repository root that ships this extension (adapters/pi/extension -> 3 levels up). */
export function pluginRoot(): string {
	// import.meta.url is available because pi loads extensions as ES modules via jiti.
	const here = path.dirname(fs.realpathSync(fileURLToPath(new URL(".", import.meta.url))));
	return path.resolve(here, "..", "..", "..");
}

/** Expand a leading `~` to the user home directory. */
function expandHome(input: string): string {
	if (input === "~" || input.startsWith("~/") || input.startsWith("~\\")) {
		const home = process.env.USERPROFILE || process.env.HOME || "";
		const rest = input.slice(1);
		return path.join(home, rest);
	}
	return input;
}

/**
 * Resolve a governance asset path (role definition / task SKILL).
 * Absolute paths are used verbatim (after ~ expansion); relative paths are
 * tried against the governance plugin root first, then the session cwd.
 * Returns null when neither candidate exists.
 */
export function resolveRepoPath(input: string, cwd: string): string | null {
	const expanded = expandHome(input);
	if (path.isAbsolute(expanded)) {
		return fs.existsSync(expanded) ? expanded : null;
	}
	const fromPluginRoot = path.join(pluginRoot(), expanded);
	if (fs.existsSync(fromPluginRoot)) return fromPluginRoot;
	const fromCwd = path.join(cwd, expanded);
	if (fs.existsSync(fromCwd)) return fromCwd;
	return null;
}

/** Read a UTF-8 text file, returning null on failure (caller renders the error). */
export function readTextFile(filePath: string): string | null {
	try {
		return fs.readFileSync(filePath, "utf-8");
	} catch {
		return null;
	}
}

/**
 * List dispatchable governance roles (agents/*.md basenames without extension).
 * Used for the "Unknown role ... Available roles" error (official subagent
 * precedent examples/extensions/subagent/index.ts L284-298).
 */
export function listRoleDefinitions(): string[] {
	const agentsDir = path.join(pluginRoot(), "agents");
	try {
		return fs
			.readdirSync(agentsDir)
			.filter((name) => name.toLowerCase().endsWith(".md"))
			.map((name) => `agents/${name}`)
			.sort();
	} catch {
		return [];
	}
}
