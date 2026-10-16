/**
 * Governance pi extension — ask_user_question bridge tool
 * (single responsibility: interaction-contract mapping only).
 *
 * Bridges the software-project-governance AskUserQuestion contract
 * (questions[]: {id, question, header?, options?[{label, description?}],
 * multi_select?}) onto pi's dialog method family (select / confirm / input),
 * which is available in tui AND rpc modes (`ctx.hasUI === true`;
 * dist/core/extensions/types.d.ts L72-79 dialog signatures, L219 hasUI).
 * In headless json/print modes the tool fails fast with a structured
 * `isError` result carrying the GOV_ASK_USER_HEADLESS marker — the official
 * ask-user precedent returns an error in non-interactive modes
 * (examples/extensions/question.ts L53-62, questionnaire.ts L93-95); JSON and
 * print modes have no UI protocol surface at all (docs/extensions.md
 * L248-251), so RPC forwarding is not a carrier there by protocol definition.
 */

import type { AgentToolResult, ExtensionToolContext, ToolDefinition } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

// ── Tool schema (verbatim from design §1a.4 — matches the repo interaction
// contract field-for-field) ─────────────────────────────────────────────────

const GovAskOption = Type.Object({
	label: Type.String({ description: "Short user-facing option label" }),
	description: Type.Optional(
		Type.String({
			description: "One sentence explaining the tradeoff or impact",
		}),
	),
});

const GovAskQuestion = Type.Object({
	id: Type.String({ description: "Stable id for this question; echoed in the answer" }),
	question: Type.String({ description: "The specific question to ask the user" }),
	header: Type.Optional(
		Type.String({
			description: "Optional short heading, e.g. 'Confirm' or 'Choose Mode'",
		}),
	),
	options: Type.Optional(
		Type.Array(GovAskOption, {
			description: "Choices to show. Omit for free-text input",
		}),
	),
	multi_select: Type.Optional(
		Type.Boolean({
			description: "Whether more than one option may be selected. Defaults to false",
		}),
	),
});

const GovAskUserParams = Type.Object({
	questions: Type.Array(GovAskQuestion, {
		description: "Questions to ask before continuing",
	}),
});

type GovAskOptionValue = { label: string; description?: string };
type GovAskQuestionValue = {
	id: string;
	question: string;
	header?: string;
	options?: GovAskOptionValue[];
	multi_select?: boolean;
};
type GovAskParamsValue = { questions: GovAskQuestionValue[] };

export interface GovAskAnswer {
	id: string;
	selected: string[];
	custom?: string;
}

export interface GovAskDetails {
	answers: GovAskAnswer[];
	cancelled?: boolean;
	cancelled_reason?: "user" | "timeout";
}

const OPTION_LINE_TRUNCATE = 80;
/** Dialog timeout so a forgotten dialog cannot hang a governance session. */
const DIALOG_TIMEOUT_MS = 10 * 60 * 1000;

function dialogTitle(q: GovAskQuestionValue): string {
	// pi select has no separate header concept (types.d.ts L74: title + options only).
	return q.header ? `[${q.header}] ${q.question}` : q.question;
}

/**
 * Render options as `"{i+1}. {label}"`, appending `" — {description}"` and
 * truncating to ~80 chars so long descriptions cannot overflow the list
 * (select takes string[] only — concatenation is the sole lossless channel).
 */
function renderOptions(options: GovAskOptionValue[]): string[] {
	return options.map((option, index) => {
		let line = `${index + 1}. ${option.label}`;
		if (option.description) {
			line += ` — ${option.description}`;
		}
		if (line.length > OPTION_LINE_TRUNCATE) {
			line = `${line.slice(0, OPTION_LINE_TRUNCATE - 1)}…`;
		}
		return line;
	});
}

/** Parse the selected display string back to the option label via its index prefix. */
function parseSelectedLabel(selected: string, options: GovAskOptionValue[]): string | undefined {
	const match = /^(\d+)\. /.exec(selected);
	if (match) {
		const index = Number(match[1]) - 1;
		if (index >= 0 && index < options.length) return options[index].label;
	}
	return options.find((option) => selected === option.label)?.label;
}

function textResult(text: string, details: GovAskDetails, isError = false): AgentToolResult<GovAskDetails> {
	return { content: [{ type: "text", text }], details, isError };
}

/** Structured headless error (design §1a.3) — fixed marker for E2E assertions. */
export function headlessErrorResult(params: GovAskParamsValue): AgentToolResult<GovAskDetails> {
	return {
		content: [
			{
				type: "text",
				text:
					"Error: GOV_ASK_USER_HEADLESS — the governance ask_user_question bridge needs a " +
					"dialog-capable UI. Re-run in interactive mode (pi without -p/--mode json) or " +
					"connect an RPC client, then retry the question batch. " +
					"Pending questions: " +
					params.questions.map((q) => q.id).join(", "),
			},
		],
		details: { answers: [] },
		isError: true,
	};
}

/** Validate the contract invariants the schema alone cannot express (question.ts L64-69 precedent). */
function validateQuestions(params: GovAskParamsValue): string | null {
	if (!Array.isArray(params.questions) || params.questions.length === 0) {
		return "questions must be a non-empty array";
	}
	for (const q of params.questions) {
		if (!q.id || !q.question) {
			return "each question requires `id` and `question`";
		}
		if (q.options !== undefined && !Array.isArray(q.options)) {
			return `question ${q.id}: options must be an array when provided`;
		}
		if (Array.isArray(q.options) && q.options.length === 0) {
			return `question ${q.id}: options must not be an empty array (omit options for free-text input)`;
		}
		for (const option of q.options ?? []) {
			if (!option || !option.label) {
				return `question ${q.id}: every option requires a label`;
			}
		}
	}
	return null;
}

class UserCancelled extends Error {
	constructor(public readonly reason: "user" | "timeout") {
		super("cancelled");
	}
}

/**
 * Ask one question via the dialog mapping (design §1a.2):
 *   options && !multi_select -> ctx.ui.select(...)
 *   options &&  multi_select -> per-option ctx.ui.confirm(...) sequence
 *   !options                 -> ctx.ui.input(...)
 * select/input resolving undefined means dismissal; pi's dialog API does not
 * distinguish user dismissal from auto-timeout (both resolve undefined —
 * rpc-extension-ui.md L188-194 cancel form; timeout auto-dismisses,
 * types.d.ts L44), so the batch is cancelled and the reason text carries
 * both possibilities honestly. A confirm sequence answered No everywhere is
 * treated as cancellation as well (pi confirm cannot distinguish No from
 * dismiss).
 */
async function askOne(
	q: GovAskQuestionValue,
	ctx: ExtensionToolContext,
	signal: AbortSignal | undefined,
): Promise<GovAskAnswer> {
	const title = dialogTitle(q);
	const dialogOptions = { signal, timeout: DIALOG_TIMEOUT_MS };

	if (Array.isArray(q.options) && q.options.length > 0) {
		if (q.multi_select) {
			const selected: string[] = [];
			for (const option of q.options!) {
				let message = option.label;
				if (option.description) message += ` — ${option.description}`;
				const confirmed = await ctx.ui.confirm(title, message, dialogOptions);
				if (confirmed) selected.push(option.label);
			}
			if (selected.length === 0) throw new UserCancelled("user");
			return { id: q.id, selected };
		}

		const chosen = await ctx.ui.select(title, renderOptions(q.options!), dialogOptions);
		if (chosen === undefined) throw new UserCancelled("timeout");
		const label = parseSelectedLabel(chosen, q.options!);
		return { id: q.id, selected: label ? [label] : [chosen] };
	}

	const answer = await ctx.ui.input(title, q.question, dialogOptions);
	if (answer === undefined) throw new UserCancelled("timeout");
	const trimmed = answer.trim();
	if (!trimmed) throw new UserCancelled("user");
	return { id: q.id, selected: [], custom: trimmed };
}

/** Render answers back to the model, echoed per question id. */
export function renderAnswers(answers: GovAskAnswer[]): string {
	if (answers.length === 0) return "User cancelled all questions";
	return answers
		.map((answer) => {
			const value = answer.custom !== undefined ? answer.custom : answer.selected.join(", ");
			return `${answer.id}: ${value}`;
		})
		.join("\n");
}

export function governanceAskUserTool(): ToolDefinition<typeof GovAskUserParams, GovAskDetails> {
	return {
		name: "ask_user_question",
		label: "Ask User (governance)",
		description:
			"Ask the user one or more structured questions when a decision, " +
			"confirmation, or missing information blocks governance-safe progress. " +
			"Each question carries a stable id; answers are echoed per id. " +
			"Reaches the user in interactive and RPC modes; in headless print/json " +
			"modes it fails fast with a headless-mode error.",
		parameters: GovAskUserParams,
		exposure: "model-only", // docs/extensions.md L157: designed for ask-the-user tools
		namespace: { name: "governance", description: "software-project-governance bridge tools" },
		annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
		executionMode: "sequential", // interactive tools must serialize (question.ts L50 precedent)
		async execute(_toolCallId, params, signal, _onUpdate, ctx) {
			const invalid = validateQuestions(params as GovAskParamsValue);
			if (invalid) {
				return textResult(`Error: invalid questions payload — ${invalid}`, { answers: [] }, true);
			}

			if (!ctx.hasUI) return headlessErrorResult(params as GovAskParamsValue); // §1a.3 guard

			const answers: GovAskAnswer[] = [];
			for (const q of (params as GovAskParamsValue).questions) {
				signal?.throwIfAborted();
				try {
					answers.push(await askOne(q, ctx, signal)); // §1a.2 mapping
				} catch (error) {
					if (error instanceof UserCancelled) {
						const reasonText =
							error.reason === "timeout"
								? "user dismissed the dialog or the dialog timed out"
								: "user cancelled";
						return textResult(
							`User cancelled all questions (${reasonText})`,
							{ answers: [], cancelled: true, cancelled_reason: error.reason },
						);
					}
					throw error;
				}
			}
			return textResult(renderAnswers(answers), { answers });
		},
	};
}
