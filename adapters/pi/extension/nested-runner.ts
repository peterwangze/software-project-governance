/**
 * Governance pi extension — nested pi process runner (single responsibility:
 * child-process IO only; no tool schema, no governance semantics).
 *
 * Follows the official reference implementation
 * examples/extensions/subagent/index.ts (pi v1.1.0): spawn a nested
 * `pi --mode json -p --no-session` process, parse the JSONL event stream
 * (message_end / tool_result_end), aggregate usage, and honor abort via
 * SIGTERM -> 5s -> SIGKILL (L300/L344-421/L410-420).
 *
 * Windows note (design R-6): `spawn("pi", ..., { shell: false })` cannot
 * resolve the `pi.ps1`/`pi.cmd` shim. Before falling back to the PATH-based
 * invocation (official getPiInvocation L249-263), we try the absolute
 * `process.execPath + <npm-global>/@earendil-works/pi-coding-agent/dist/bundle/cli.js`
 * layout (package.json bin: "pi" -> "dist/bundle/cli.js").
 */

import { spawn } from "node:child_process";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

/** Minimal shape of a pi `--mode json` message event we aggregate. */
export interface NestedMessage {
	role?: string;
	content?: Array<{ type?: string; text?: string }>;
	usage?: {
		input?: number;
		output?: number;
		cacheRead?: number;
		cacheWrite?: number;
		totalTokens?: number;
		cost?: { total?: number };
	};
	model?: string;
	stopReason?: string;
	errorMessage?: string;
}

export interface NestedUsage {
	input: number;
	output: number;
	cacheRead: number;
	cacheWrite: number;
	cost: number;
	contextTokens: number;
	turns: number;
}

export interface NestedRunResult {
	exitCode: number;
	messages: NestedMessage[];
	stderr: string;
	usage: NestedUsage;
	model?: string;
	stopReason?: string;
	errorMessage?: string;
	aborted: boolean;
}

/**
 * Final assistant text (reverse scan for the last assistant text part).
 * Same semantics as the official subagent example's `getFinalOutput`
 * (L170-180) and the SDK `AgentSession.getLastAssistantText()` — design
 * review F-4: the two names are one semantic, the example name is the
 * spawn-path implementation (this one), the SDK name belongs to the
 * in-process candidate B (not implemented; see design ADR-2).
 */
export function getFinalOutput(messages: NestedMessage[]): string {
	for (let i = messages.length - 1; i >= 0; i--) {
		const msg = messages[i];
		if (msg.role === "assistant") {
			for (const part of msg.content ?? []) {
				if (part.type === "text" && typeof part.text === "string") return part.text;
			}
		}
	}
	return "";
}

/** Official failed-run judgment (subagent/index.ts L182-184). */
export function isFailedRun(result: NestedRunResult): boolean {
	return (
		result.exitCode !== 0 ||
		result.stopReason === "error" ||
		result.stopReason === "aborted" ||
		result.aborted
	);
}

/** npm-global cli.js candidate for the Windows-safe absolute invocation (R-6). */
function npmGlobalCliJs(): string | null {
	const candidates: string[] = [];
	if (process.env.APPDATA) {
		candidates.push(
			path.join(
				process.env.APPDATA,
				"npm",
				"node_modules",
				"@earendil-works",
				"pi-coding-agent",
				"dist",
				"bundle",
				"cli.js",
			),
		);
	}
	if (process.env.NPM_CONFIG_PREFIX) {
		candidates.push(
			path.join(
				process.env.NPM_CONFIG_PREFIX,
				"node_modules",
				"@earendil-works",
				"pi-coding-agent",
				"dist",
				"bundle",
				"cli.js",
			),
		);
	}
	for (const candidate of candidates) {
		if (fs.existsSync(candidate)) return candidate;
	}
	return null;
}

/**
 * Resolve how to invoke the nested pi process (official getPiInvocation
 * pattern, subagent/index.ts L249-263, plus the R-6 absolute-layout branch).
 */
export function resolvePiInvocation(args: string[]): { command: string; args: string[] } {
	const currentScript = process.argv[1];
	const isBunVirtualScript = currentScript?.startsWith("/$bunfs/root/");
	if (currentScript && !isBunVirtualScript && fs.existsSync(currentScript)) {
		return { command: process.execPath, args: [currentScript, ...args] };
	}

	// R-6: absolute cli.js beats the bare "pi" PATH fallback because Windows
	// spawn without shell cannot execute the pi.ps1/pi.cmd shim.
	const cliJs = npmGlobalCliJs();
	if (cliJs) {
		return { command: process.execPath, args: [cliJs, ...args] };
	}

	const execName = path.basename(process.execPath).toLowerCase();
	const isGenericRuntime = /^(node|bun)(\.exe)?$/.test(execName);
	if (!isGenericRuntime) {
		return { command: process.execPath, args };
	}

	return { command: "pi", args };
}

/**
 * Write the composed system prompt to a private temp file
 * (official writePromptToTempFile pattern, subagent/index.ts L239-247:
 * mkdtemp under os.tmpdir() + mode 0600; never ~/.pi/, never the repo).
 */
export async function writePromptToTempFile(
	label: string,
	prompt: string,
): Promise<{ dir: string; filePath: string }> {
	const tmpDir = await fs.promises.mkdtemp(path.join(os.tmpdir(), "pi-governance-"));
	const safeName = label.replace(/[^\w.-]+/g, "_");
	const filePath = path.join(tmpDir, `prompt-${safeName}.md`);
	await fs.promises.writeFile(filePath, prompt, { encoding: "utf-8", mode: 0o600 });
	return { dir: tmpDir, filePath };
}

/** Best-effort cleanup of the temp prompt dir (official finally pattern, L426-439). */
export function cleanupTempDir(dir: string | null, filePath: string | null): void {
	if (filePath) {
		try {
			fs.unlinkSync(filePath);
		} catch {
			/* ignore */
		}
	}
	if (dir) {
		try {
			fs.rmdirSync(dir);
		} catch {
			/* ignore */
		}
	}
}

/**
 * Spawn the nested pi process and aggregate its JSONL event stream.
 * Pure orchestration: no UI, no schema knowledge (subagent/index.ts
 * L344-421 pattern: spawn shell:false + stdio pipe, line-buffered JSON
 * parse, SIGTERM -> 5s -> SIGKILL on abort).
 */
export function runNestedPi(
	args: string[],
	options: {
		cwd: string;
		signal?: AbortSignal;
		onEvent?: (result: NestedRunResult) => void;
	},
): Promise<NestedRunResult> {
	const currentResult: NestedRunResult = {
		exitCode: 0,
		messages: [],
		stderr: "",
		usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, cost: 0, contextTokens: 0, turns: 0 },
		aborted: false,
	};

	const processLine = (line: string) => {
		if (!line.trim()) return;
		let event: any;
		try {
			event = JSON.parse(line);
		} catch {
			return;
		}

		if (event.type === "message_end" && event.message) {
			const msg = event.message as NestedMessage;
			currentResult.messages.push(msg);
			if (msg.role === "assistant") {
				currentResult.usage.turns++;
				const usage = msg.usage;
				if (usage) {
					currentResult.usage.input += usage.input || 0;
					currentResult.usage.output += usage.output || 0;
					currentResult.usage.cacheRead += usage.cacheRead || 0;
					currentResult.usage.cacheWrite += usage.cacheWrite || 0;
					currentResult.usage.cost += usage.cost?.total || 0;
					currentResult.usage.contextTokens = usage.totalTokens || 0;
				}
				if (!currentResult.model && msg.model) currentResult.model = msg.model;
				if (msg.stopReason) currentResult.stopReason = msg.stopReason;
				if (msg.errorMessage) currentResult.errorMessage = msg.errorMessage;
			}
			options.onEvent?.(currentResult);
		}

		if (event.type === "tool_result_end" && event.message) {
			currentResult.messages.push(event.message as NestedMessage);
			options.onEvent?.(currentResult);
		}
	};

	return new Promise<NestedRunResult>((resolve) => {
		const invocation = resolvePiInvocation(args);
		const proc = spawn(invocation.command, invocation.args, {
			cwd: options.cwd,
			shell: false,
			stdio: ["ignore", "pipe", "pipe"],
		});
		let buffer = "";

		proc.stdout.on("data", (data) => {
			buffer += data.toString();
			const lines = buffer.split("\n");
			buffer = lines.pop() || "";
			for (const line of lines) processLine(line);
		});

		proc.stderr.on("data", (data) => {
			currentResult.stderr += data.toString();
		});

		proc.on("close", (code) => {
			if (buffer.trim()) processLine(buffer);
			currentResult.exitCode = code ?? 0;
			resolve(currentResult);
		});

		proc.on("error", () => {
			currentResult.exitCode = 1;
			resolve(currentResult);
		});

		if (options.signal) {
			const killProc = () => {
				currentResult.aborted = true;
				proc.kill("SIGTERM");
				setTimeout(() => {
					if (!proc.killed) proc.kill("SIGKILL");
				}, 5000);
			};
			if (options.signal.aborted) killProc();
			else options.signal.addEventListener("abort", killProc, { once: true });
		}
	});
}
