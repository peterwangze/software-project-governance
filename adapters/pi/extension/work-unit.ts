import { execFile } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);
type Unit = {flow_unit_id: string; task_id: string; runtime_status: string; goal: string;
    acceptance: string; blockers: string[]; active_loop_tier: string; gate_id: string; next_action: string};

export async function dispatchUnit(root: string, cwd: string, prompt: string, requested?: string): Promise<string> {
    if (!requested && !["flow-unit-runtime.json", "loop-event-log.jsonl"].some((name) =>
        existsSync(join(cwd, ".governance", name)))) return "";
    const cli = join(root, "skills", "software-project-governance", "infra", "verify_workflow.py");
    const args = ["-X", "utf8", cli, "--project-root", cwd, "loop", "status", "--json"];
    const { stdout } = await run(process.platform === "win32" ? "python" : "python3", args,
        { cwd, encoding: "utf8", timeout: 15000, maxBuffer: 8 * 1024 * 1024, windowsHide: true });
    const view = JSON.parse(stdout);
    if (view.state === "invalid") throw new Error(view.message);
    const units: Unit[] = view.units;
    const words = prompt.match(/[A-Za-z0-9][A-Za-z0-9_.-]*/g) ?? [];
    const identifiers = new Set(words.flatMap((word) => [word, word.replace(/\.+$/, "")]));
    const mentions = units.filter((unit) => identifiers.has(unit.flow_unit_id) || identifiers.has(unit.task_id));
    const active = units.filter((unit) => unit.runtime_status === "active" && !unit.blockers.length);
    if (!requested && !units.length) return "";
    const candidates = requested ? units.filter((unit) => unit.flow_unit_id === requested) :
        (mentions.length ? mentions : active);
    if (candidates.length !== 1 || !active.includes(candidates[0]) ||
        mentions.some((unit) => unit !== candidates[0])) {
        throw new Error("Select one active work_unit_id for this dispatch.");
    }
    const unit = candidates[0];
    return JSON.stringify({unit_id: unit.flow_unit_id, goal: unit.goal, acceptance: unit.acceptance,
        tier: unit.active_loop_tier, gate: unit.gate_id, next_action: unit.next_action});
}
