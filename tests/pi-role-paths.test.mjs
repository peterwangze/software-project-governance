import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

test("Pi resolves packaged roles and project-local files from another project", {
  skip: !process.features.typescript && "requires Node with native TypeScript support",
}, async (t) => {
  const { listRoleDefinitions, pluginRoot, resolveRepoPath } = await import("../adapters/pi/extension/paths.ts");
  const root = realpathSync(fileURLToPath(new URL("../", import.meta.url)));
  const project = mkdtempSync(path.join(tmpdir(), "spg-pi-project-"));
  t.after(() => rmSync(project, { recursive: true, force: true }));

  assert.equal(pluginRoot(), root);
  const roles = listRoleDefinitions();
  assert.ok(roles.includes("agents/analyst.md"));
  assert.ok(!roles.includes("agents/coordinator.md"));
  for (const role of roles) {
    assert.equal(resolveRepoPath(role, project), path.join(root, role));
  }
  writeFileSync(path.join(project, "project-role.md"), "# Project role\n");
  assert.equal(resolveRepoPath("project-role.md", project), path.join(project, "project-role.md"));
  assert.equal(resolveRepoPath("agents/coordinator.md", project), null);
});

test("Pi dispatch honors the named unit throughout rework and completion", {
  skip: !process.features.typescript && "requires Node with native TypeScript support",
}, async (t) => {
  const { dispatchUnit } = await import("../adapters/pi/extension/work-unit.ts");
  const root = fileURLToPath(new URL("../", import.meta.url));
  const project = mkdtempSync(path.join(tmpdir(), "spg-pi-unit-"));
  t.after(() => rmSync(project, { recursive: true, force: true }));
  mkdirSync(path.join(project, ".governance"));
  const python = process.platform === "win32" ? "python" : "python3";
  const loop = (...args) => execFileSync(python, [
    path.join(root, "skills/software-project-governance/infra/verify_workflow.py"),
    "--project-root", project, "loop", ...args,
  ], { stdio: "pipe" });
  const dispatch = (prompt, id) => dispatchUnit(root, project, prompt, id);
  const start = (id, output) => loop("start", "--tier", "inner", "--unit", id, "--goal", "Check export",
    "--acceptance", "Rows total seven", "--check-command", JSON.stringify([python, "-c", output]),
    "--expect-output", "7");
  start("order-old", "print(7)");
  start("order-live", "print(7)");
  await assert.rejects(dispatch("Review pending work"));
  await assert.rejects(dispatch("Review order-old and order-live"));
  assert.equal(JSON.parse(await dispatch("Review order-old")).unit_id, "order-old");
  loop("verify", "--unit", "order-old");
  assert.equal(JSON.parse(await dispatch("Review pending work")).unit_id, "order-live");
  await assert.rejects(dispatch("Collect evidence for order-old."));
  await assert.rejects(dispatch("Review order-old", "order-live"));
  await assert.rejects(dispatch("Review pending work", "order-old"));
  const blocked = JSON.parse(start("order-blocked", "print(0)"));
  for (let i = 0; i < blocked.loop_state.fuse.max_rounds + 3; i++) {
    const outcome = assertFailedVerification();
    if (outcome.decision === "escalate") break;
    assert.equal(outcome.decision, "iterate");
  }
  function assertFailedVerification() {
    try {
      loop("verify", "--unit", "order-blocked");
    } catch (error) {
      return JSON.parse(error.stdout);
    }
    assert.fail("the bad observation must require rework");
  }
  assert.equal(JSON.parse(loop("status", "--unit", "order-blocked", "--json")).runtime_status, "blocked");
  await assert.rejects(dispatch("Review order-blocked"));
});
