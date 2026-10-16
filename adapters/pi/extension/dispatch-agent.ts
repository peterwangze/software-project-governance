/**
 * Governance pi extension — dispatch_agent bridge tool
 * (single responsibility: translating dispatch semantics into nested-pi CLI
 * flags; child-process IO lives in nested-runner.ts).
 *
 * Bridges the software-project-governance agent dispatch template
 * (references/agent-dispatch-template.md placeholder table L94-108) onto a
 * nested `pi --mode json -p --no-session` child process with an isolated
 * context window — the official subagent reference path
 * (examples/extensions/subagent/index.ts; design ADR-2 candidate A).
 *
 * Review F-3 (adopted): the nested child inherits global extension wiring
 * (settings.json extensions array), so both bridge tools would be re-declared
 * to the nested model by default. The nested args therefore always append
 * `--exclude-tools ask_user_question,dispatch_agent` (cli.md L121-122) to
 * machine-block recursive dispatch; an explicit allowed_tools allowlist
 * narrows further (cli.md L119-120: unlisted tools are not declared).
 */

import type { AgentToolResult, ExtensionToolContext, ToolDefinition } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

import {
	cleanupTempDir,
	getFinalOutput,
	isFailedRun,
	runNestedPi,
	writePromptToTempFile,
	type NestedRunResult,
} from "./nested-runner.ts";
import { listRoleDefinitions, pluginRoot, readTextFile, resolveRepoPath } from "./paths.ts";

// ── Tool schema (design §1b.2 — dispatch-template placeholders as params) ──

const GovDispatchParams = Type.Object({
	role_definition_path: Type.String({
		description:
			"Path to the role definition markdown, e.g. agents/developer.md. " +
			"Relative paths resolve against the governance plugin root or cwd",
	}),
	task_skill_path: Type.Optional(
		Type.String({
			description: "Path to the task SKILL spec, e.g. skills/stage-development/SKILL.md",
		}),
	),
	task_prompt: Type.String({
		description:
			"Fully-filled dispatch prompt following " +
			"references/agent-dispatch-template.md (task id, description, file list, " +
			"acceptance criteria, hard gates, destructive redlines)",
	}),
	working_dir: Type.Optional(
		Type.String({
			description: "Working directory for the nested agent. Defaults to the current cwd",
		}),
	),
	allowed_tools: Type.Optional(
		Type.Array(Type.String(), {
			description:
				"Tool allowlist for the nested agent, e.g. ['read','grep','find','ls'] " +
				"for read-only roles (Reviewer). Defaults to pi default tools",
		}),
	),
	// NOTE: design sketch used Type.StringEnum (a pi-ai helper). Expressed here
	// as a typebox-only union of literals to keep the runtime-value dependency
	// surface at exactly `typebox` (design §2.2); semantics identical.
	system_prompt_mode: Type.Optional(
		Type.Union([Type.Literal("append"), Type.Literal("replace")], {
			description:
				"'append' (default, official subagent precedent) appends the role " +
				"definition after pi's default prompt; 'replace' swaps it entirely. " +
				"Use 'replace' only when default tool guidance must not leak",
		}),
	),
});

type GovDispatchParamsValue = {
	role_definition_path: string;
	task_skill_path?: string;
	task_prompt: string;
	working_dir?: string;
	allowed_tools?: string[];
	system_prompt_mode?: "append" | "replace";
};

export interface GovDispatchDetails {
	role_definition_path: string;
	task_skill_path?: string;
	system_prompt_mode: "append" | "replace";
	working_dir: string;
	pi_args: string[];
	usage: { input: number; output: number; turns: number; cost: number };
	turns: number;
	exitCode: number;
	model?: string;
	stopReason?: string;
}

function dispatchResult(
	text: string,
	details: GovDispatchDetails,
	isError = false,
): AgentToolResult<GovDispatchDetails> {
	return { content: [{ type: "text", text }], details, isError };
}

/** Official error style: unknown role -> list what exists (subagent L284-298). */
function unknownRoleResult(
	rolePath: string,
	details: GovDispatchDetails,
): AgentToolResult<GovDispatchDetails> {
	const available = listRoleDefinitions().join(", ") || "none";
	return dispatchResult(
		`Error: Unknown role definition: "${rolePath}". Available roles: ${available}. ` +
			"(Relative paths resolve against the governance plugin root or cwd.)",
		details,
		true,
	);
}

export function governanceDispatchAgentTool(pluginRootOverride?: string): ToolDefinition<typeof GovDispatchParams, GovDispatchDetails> {
	const root = pluginRootOverride ?? pluginRoot();
	return {
		name: "dispatch_agent",
		label: "Dispatch Agent (governance)",
		description:
			"Dispatch a governance role agent (Developer/Reviewer/Analyst/...) as a " +
			"nested pi process with an isolated context window. Provide the role definition " +
			"path, optional task SKILL path, and the fully-filled dispatch prompt per " +
			"references/agent-dispatch-template.md. Returns the agent's final structured " +
			"report text. Read-only roles should pass allowed_tools=['read','grep','find','ls']. " +
			"The governance bridge tools (ask_user_question, dispatch_agent) are always " +
			"excluded from the nested agent to prevent recursive dispatch.",
		parameters: GovDispatchParams,
		exposure: "model-only", // orchestrating tool (docs/extensions.md L157)
		namespace: { name: "governance", description: "software-project-governance bridge tools" },
		annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: false },
		async execute(_toolCallId, paramsRaw, signal, onUpdate, ctx) {
			const params = paramsRaw as GovDispatchParamsValue;
			const cwd = params.working_dir || ctx.cwd;
			const systemPromptMode = params.system_prompt_mode ?? "append";

			// 1. resolve role/skill paths against pluginRoot (read files)
			const rolePath = resolveRepoPath(params.role_definition_path, cwd);
			const skillPath = params.task_skill_path ? resolveRepoPath(params.task_skill_path, cwd) : null;
			if (params.task_skill_path && !skillPath) {
				// A requested task spec that cannot be found is a dispatch error,
				// not a silent skip (fail-closed).
				return dispatchResult(
					`Error: task SKILL spec not found: "${params.task_skill_path}" (resolved against ${root} and ${cwd}).`,
					{
						role_definition_path: params.role_definition_path,
						task_skill_path: params.task_skill_path,
						system_prompt_mode: systemPromptMode,
						working_dir: cwd,
						pi_args: [],
						usage: { input: 0, output: 0, turns: 0, cost: 0 },
						turns: 0,
						exitCode: 1,
					},
					true,
				);
			}
			if (!rolePath) return unknownRoleResult(params.role_definition_path, {
				role_definition_path: params.role_definition_path,
				task_skill_path: params.task_skill_path,
				system_prompt_mode: systemPromptMode,
				working_dir: cwd,
				pi_args: [],
				usage: { input: 0, output: 0, turns: 0, cost: 0 },
				turns: 0,
				exitCode: 1,
			});

			const roleText = readTextFile(rolePath);
			if (roleText === null) {
				return dispatchResult(
					`Error: role definition unreadable: "${rolePath}".`,
					{
						role_definition_path: params.role_definition_path,
						task_skill_path: params.task_skill_path,
						system_prompt_mode: systemPromptMode,
						working_dir: cwd,
						pi_args: [],
						usage: { input: 0, output: 0, turns: 0, cost: 0 },
						turns: 0,
						exitCode: 1,
					},
					true,
				);
			}

			// 2. compose systemPromptText = roleText + optional task spec section
			const skillText = skillPath ? readTextFile(skillPath) : null;
			let systemPromptText = roleText;
			if (skillText !== null) {
				systemPromptText = `${roleText}\n\n# 任务规范\n${skillText}`;
			} else if (skillPath !== null) {
				return dispatchResult(
					`Error: task SKILL spec unreadable: "${skillPath}".`,
					{
						role_definition_path: params.role_definition_path,
						task_skill_path: params.task_skill_path,
						system_prompt_mode: systemPromptMode,
						working_dir: cwd,
						pi_args: [],
						usage: { input: 0, output: 0, turns: 0, cost: 0 },
						turns: 0,
						exitCode: 1,
					},
					true,
				);
			}

			const makeDetails = (piArgs: string[], run?: NestedRunResult): GovDispatchDetails => ({
				role_definition_path: params.role_definition_path,
				task_skill_path: params.task_skill_path,
				system_prompt_mode: systemPromptMode,
				working_dir: cwd,
				pi_args: piArgs,
				usage: run
					? { input: run.usage.input, output: run.usage.output, turns: run.usage.turns, cost: run.usage.cost }
					: { input: 0, output: 0, turns: 0, cost: 0 },
				turns: run?.usage.turns ?? 0,
				exitCode: run?.exitCode ?? -1,
				model: run?.model,
				stopReason: run?.stopReason,
			});

			// 3. write composed prompt to a private temp file (tmpdir + 0600)
			const tmp = await writePromptToTempFile(
				params.role_definition_path.replace(/[^\w.-]+/g, "_") || "role",
				systemPromptText,
			);

			try {
				// 4. compose nested args (official subagent L300-307 pattern + F-3)
				const args: string[] = ["--mode", "json", "-p", "--no-session"];
				args.push(
					systemPromptMode === "replace"
						? "--system-prompt"
						: "--append-system-prompt",
					tmp.filePath,
				);
				const inheritedModel = ctx.model ? `${ctx.model.provider}/${ctx.model.id}` : undefined;
				if (inheritedModel) args.push("--model", inheritedModel);
				if (ctx.thinkingLevel) args.push("--thinking", String(ctx.thinkingLevel));
				if (params.allowed_tools && params.allowed_tools.length > 0) {
					args.push("--tools", params.allowed_tools.join(","));
				}
				// F-3: always machine-block the bridge tools in the nested child
				// (inherited global extension wiring would otherwise re-declare them).
				args.push("--exclude-tools", "ask_user_question,dispatch_agent");
				args.push(`Task:\n${params.task_prompt}`);

				// 5. spawn + parse JSONL, stream onUpdate (official L324-331 pattern)
				const run = await runNestedPi(args, {
					cwd,
					signal,
					onEvent: (partial) => {
						onUpdate?.({
							content: [{ type: "text", text: getFinalOutput(partial.messages) || "(running...)" }],
							details: makeDetails(args, partial),
						});
					},
				});

				// 6. final result (official isFailedResult judgment L182-191)
				if (isFailedRun(run)) {
					const failureText =
						run.errorMessage ||
						run.stderr ||
						getFinalOutput(run.messages) ||
						"(no output)";
					return dispatchResult(
						`Nested governance agent failed (exit ${run.exitCode}${run.stopReason ? `, stopReason=${run.stopReason}` : ""}):\n${failureText}`,
						makeDetails(args, run),
						true,
					);
				}
				const finalOutput = getFinalOutput(run.messages) || "(no output)";
				return dispatchResult(finalOutput, makeDetails(args, run));
			} finally {
				// temp prompt red line: always cleaned up, never persisted
				cleanupTempDir(tmp.dir, tmp.filePath);
			}
		},
	};
}
