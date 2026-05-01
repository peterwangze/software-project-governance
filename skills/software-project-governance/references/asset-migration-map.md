# 全量资产迁移映射

每个文件有明确去向。无删除，无遗漏。97 个 git 跟踪文件全部映射。

## 迁移状态说明

- **留存原地**：文件已在正确的架构位置，不需要移动
- **git mv**：用 git mv 迁移到目标位置（保留历史）
- **合并**：内容融入目标文件后，原文件 git rm（保留历史记录）

## 适配层（12 文件）— 留存原地

平台投影文件，已在正确位置。

| 当前路径 | 去向 | 方式 |
|---------|------|------|
| `.claude-plugin/plugin.json` | 留存 | — |
| `.claude-plugin/marketplace.json` | 留存 | — |
| `.codex-plugin/plugin.json` | 留存 | — |
| `.agents/plugins/marketplace.json` | 留存 | — |
| `adapters/claude/adapter-manifest.json` | 留存 | — |
| `adapters/claude/launch.py` | 留存 | — |
| `adapters/claude/README.md` | 留存 | — |
| `adapters/codex/adapter-manifest.json` | 留存 | — |
| `adapters/codex/launch.py` | 留存 | — |
| `adapters/codex/README.md` | 留存 | — |
| `adapters/gemini/README.md` | 留存 | — |
| `.github/workflows/governance-check.yml` | 留存（CI 配置） | — |

## 入口层（1 文件）— 留存原地

| 当前路径 | 去向 | 方式 |
|---------|------|------|
| `skills/software-project-governance/SKILL.md` | 留存（已在正确位置） | — |

## 业务智能层 — Agent 库（9 文件）— 留存原地

每个 Agent 已是独立 SKILL 目录，工具权限+persona 完整。

| 当前路径 | 去向 | 方式 |
|---------|------|------|
| `skills/software-project-governance/agents/coordinator/SKILL.md` | 留存 | — |
| `skills/software-project-governance/agents/developer/SKILL.md` | 留存 | — |
| `skills/software-project-governance/agents/reviewer/SKILL.md` | 留存 | — |
| `skills/software-project-governance/agents/architect/SKILL.md` | 留存 | — |
| `skills/software-project-governance/agents/qa/SKILL.md` | 留存 | — |
| `skills/software-project-governance/agents/devops/SKILL.md` | 留存 | — |
| `skills/software-project-governance/agents/analyst/SKILL.md` | 留存 | — |
| `skills/software-project-governance/agents/release/SKILL.md` | 留存 | — |
| `skills/software-project-governance/agents/maintenance/SKILL.md` | 留存 | — |

## 用户交互层 — 斜杠命令入口（6 文件）— 留存原地

`commands/` 是用户通过 Claude Code 斜杠命令调用治理功能的入口（`/governance-init`、`/governance-status` 等）。它们属于适配层——平台原生交互机制。

**不迁移**。这些命令文件本身已包含完整实现，且 `plugin.json` 第 6 行 `"commands": "./commands/"` 依赖此路径。迁移会破坏用户斜杠命令功能。

| 当前路径 | 去向 | 方式 |
|---------|------|------|
| `commands/software-project-governance.md` | 留存 | — |
| `commands/governance-init.md` | 留存 | — |
| `commands/governance-status.md` | 留存 | — |
| `commands/governance-gate.md` | 留存 | — |
| `commands/governance-verify.md` | 留存 | — |
| `commands/governance-update.md` | 留存 | — |

## 能力层 — SKILL 库（21 文件）— stages/ → skills/

| 当前路径 | 目标路径 | 方式 |
|---------|---------|------|
| `skills/stage-initiation/SKILL.md` | `skills/stage-initiation/SKILL.md` | git mv + 格式标准化 |
| `skills/stage-research/SKILL.md` | `skills/stage-research/SKILL.md` | git mv + 格式标准化 |
| `skills/stage-selection/SKILL.md` | `skills/stage-selection/SKILL.md` | git mv + 格式标准化 |
| `skills/stage-infra/SKILL.md` | `skills/stage-infra/SKILL.md` | git mv + 格式标准化 |
| `skills/stage-architecture/SKILL.md` | `skills/stage-architecture/SKILL.md` | git mv + 格式标准化 |
| `skills/stage-development/SKILL.md` | `skills/stage-development/SKILL.md` | git mv + 格式标准化 |
| `skills/stage-testing/SKILL.md` | `skills/stage-testing/SKILL.md` | git mv + 格式标准化 |
| `skills/stage-cicd/SKILL.md` | `skills/stage-cicd/SKILL.md` | git mv + 格式标准化 |
| `skills/stage-release/SKILL.md` | `skills/stage-release/SKILL.md` | git mv + 格式标准化 |
| `skills/stage-operations/SKILL.md` | `skills/stage-operations/SKILL.md` | git mv + 格式标准化 |
| `skills/stage-maintenance/SKILL.md` | `skills/stage-maintenance/SKILL.md` | git mv + 格式标准化 |
| `stages/initiation/requirement-clarification.md` | `skills/requirement-clarification/SKILL.md` | git mv + 格式标准化 |
| `stages/architecture/tech-review-checklist.md` | `skills/tech-review/SKILL.md` | git mv + 格式标准化 |
| `stages/development/code-review-standard.md` | `skills/code-review/SKILL.md` | git mv + 格式标准化 |
| `stages/release/release-checklist.md` | `skills/release-checklist/SKILL.md` | git mv + 格式标准化 |
| `stages/maintenance/retro-meeting-template.md` | `skills/retro-meeting/SKILL.md` | git mv + 格式标准化 |

### stages/ 模板文件（3 文件）

| 当前路径 | 目标路径 | 方式 |
|---------|---------|------|
| `stages/initiation/pr-faq-template.md` | `skills/pr-faq/SKILL.md` | git mv + 格式标准化 |
| `stages/initiation/okr-template.md` | `skills/okr/SKILL.md` | git mv + 格式标准化 |
| `stages/selection/six-pager-template.md` | `skills/six-pager/SKILL.md` | git mv + 格式标准化 |

### 能力层入口（1 文件）

| 当前路径 | 目标路径 | 方式 |
|---------|---------|------|
| `skills/software-project-governance/main-workflow.md` | `skills/main-workflow/SKILL.md` | git mv |

## 基础设施层（5 文件）— 部分需迁移

| 当前路径 | 目标路径 | 方式 |
|---------|---------|------|
| `skills/software-project-governance/infra/verify_workflow.py` | 留存 | — |
| `skills/software-project-governance/infra/hooks/pre-commit` | 留存 | — |
| `skills/software-project-governance/infra/hooks/post-commit` | 留存 | — |
| `skills/software-project-governance/infra/hooks/prepare-commit-msg` | 留存 | — |
| `skills/software-project-governance/TOOLS.md` | `skills/software-project-governance/infra/TOOLS.md` | git mv |
| `scripts/verify-e2e.sh` | `skills/software-project-governance/infra/verify-e2e.sh` | git mv |

## 核心层（18 文件）— 部分需迁移

### 已迁移（7 文件）

| 当前路径 | 状态 |
|---------|------|
| `skills/software-project-governance/core/lifecycle.md` | ✅ 留存 |
| `skills/software-project-governance/core/stage-gates.md` | ✅ 留存 |
| `skills/software-project-governance/core/profiles.md` | ✅ 留存 |
| `skills/software-project-governance/core/onboarding.md` | ✅ 留存 |
| `skills/software-project-governance/core/audit-framework.md` | ✅ 留存 |
| `skills/software-project-governance/core/task-gate-model.md` | ✅ 留存 |
| `skills/software-project-governance/core/VERSIONING.md` | ✅ 留存 |

### 待迁移：protocol/ → core/protocol/（5 文件）

| 当前路径 | 目标路径 | 方式 |
|---------|---------|------|
| `protocol/workflow-schema.md` | `core/protocol/workflow-schema.md` | git mv |
| `protocol/plugin-contract.md` | `core/protocol/plugin-contract.md` | git mv |
| `protocol/external-command-contract.md` | `core/protocol/external-command-contract.md` | git mv |
| `protocol/headless-runner-sample.md` | `core/protocol/headless-runner-sample.md` | git mv |
| `protocol/command-schema.md` | `core/protocol/command-schema.md` | git mv |

### 待迁移：workflows/ 核心资产（6 文件）

| 当前路径 | 目标路径 | 方式 |
|---------|---------|------|
| `workflows/software-project-governance/manifest.md` | `core/manifest.md` | git mv |
| `workflows/software-project-governance/templates/plan-tracker.md` | `core/templates/plan-tracker.md` | git mv |
| `workflows/software-project-governance/templates/evidence-log.md` | `core/templates/evidence-log.md` | git mv |
| `workflows/software-project-governance/templates/decision-log.md` | `core/templates/decision-log.md` | git mv |
| `workflows/software-project-governance/templates/risk-log.md` | `core/templates/risk-log.md` | git mv |

## 参考知识层（10 文件）— 留存原地

Coordinator 按需读取的参考知识，保留在 `references/`。

| 当前路径 | 去向 | 方式 |
|---------|------|------|
| `skills/software-project-governance/references/behavior-protocol.md` | 留存 | — |
| `skills/software-project-governance/references/four-layer-architecture.md` | 留存 | — |
| `skills/software-project-governance/references/agent-team-architecture.md` | 留存 | — |
| `skills/software-project-governance/references/agent-failure-modes.md` | 留存 | — |
| `skills/software-project-governance/references/agent-communication-protocol.md` | 留存 | — |
| `skills/software-project-governance/references/methodology-routing.md` | 留存 | — |
| `skills/software-project-governance/references/interaction-boundary.md` | 留存 | — |
| `skills/software-project-governance/references/user-perspective-principle.md` | 留存 | — |
| `skills/software-project-governance/references/data-boundary.md` | 留存 | — |
| `skills/software-project-governance/references/agent-entry-differences.md` | 留存 | — |
| `skills/software-project-governance/references/company-practices-summary.md` | 留存 | — |

## 设计时资产 — 留存原地（10 文件）

不属于运行时 skill 包，但属于仓库的调研和样例资产。

| 当前路径 | 去向 | 方式 |
|---------|------|------|
| `workflows/software-project-governance/research/agent-integration-models.md` | 留存 | — |
| `workflows/software-project-governance/research/company-practices.md` | 留存 | — |
| `workflows/software-project-governance/research/default-product-shape.md` | 留存 | — |
| `workflows/software-project-governance/research/domestic-agent-cli-compatibility.md` | 留存 | — |
| `workflows/software-project-governance/research/external-capability-minimum-validation.md` | 留存 | — |
| `workflows/software-project-governance/research/external-validation-plan.md` | 留存 | — |
| `workflows/software-project-governance/research/repo-local-termination-note.md` | 留存 | — |
| `workflows/software-project-governance/examples/current-project-sample.md` | 留存 | — |
| `workflows/software-project-governance/examples/current-project-evidence-log.md` | 留存 | — |
| `workflows/software-project-governance/examples/current-project-decision-log.md` | 留存 | — |
| `workflows/software-project-governance/examples/current-project-risk-log.md` | 留存 | — |

## 根目录文件（4 文件）— 留存原地

| 当前路径 | 去向 | 方式 |
|---------|------|------|
| `README.md` | 留存 | — |
| `CHANGELOG.md` | 留存 | — |
| `.gitignore` | 留存 | — |

## E2E 测试项目（8 文件）— 留存原地

| 当前路径 | 去向 | 方式 |
|---------|------|------|
| `e2e-test-project/` 全部 8 个文件 | 留存 | — |

## 汇总统计

| 分类 | 总数 | 留存原地 | git mv | 合并 |
|------|------|---------|--------|------|
| 适配层 | 12 | 12 | 0 | 0 |
| 入口层 | 1 | 1 | 0 | 0 |
| 用户交互层(commands/) | 6 | 6 | 0 | 0 |
| 业务智能层 | 9 | 9 | 0 | 0 |
| 能力层(stages→skills) | 21 | 0 | 21 | 0 |
| 基础设施层 | 6 | 4 | 2 | 0 |
| 核心层 | 18 | 7 | 10 | 1 |
| 参考知识 | 11 | 11 | 0 | 0 |
| 设计时资产 | 10 | 10 | 0 | 0 |
| 根目录 | 3 | 3 | 0 | 0 |
| E2E | 8 | 8 | 0 | 0 |
| **合计** | **105** | **71** | **33** | **1** |

> 注：105 > 97（git ls-files），因为部分文件将在迁移中新增（如 SKILL 索引）。

## 迁移执行顺序

```
Phase 3a: stages/ → skills/（19 文件，子工作流+模板+skill）
Phase 3b: main-workflow.md → skills/（1 文件）
Phase 3c: TOOLS.md → infra/ + verify-e2e.sh → infra/（2 文件）
Phase 3d: protocol/ → core/protocol/ + workflows/ 核心资产 → core/（10 文件）
Phase 3e: 全仓路径引用更新 + verify_workflow.py 适配
Phase 3f: SKILL 格式标准化（统一 frontmatter + 触发条件 + 执行流程 + 步骤清单）
```

> **commands/ 不迁移**——它们是 Claude Code 斜杠命令入口，`plugin.json` 依赖此路径。
> 每步 `git mv`（保留历史），完成后 `verify_workflow.py` 确认通过，然后 commit。
