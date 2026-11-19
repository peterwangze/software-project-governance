import assert from "node:assert/strict";
import { mkdtempSync, realpathSync, rmSync, writeFileSync } from "node:fs";
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
