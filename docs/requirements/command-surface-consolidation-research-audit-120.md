# Command-Surface Consolidation Research — AUDIT-120

- **Date**: 2026-06-24
- **Task**: AUDIT-120 (命令暴露面收敛调研 + 设计)
- **Decision**: DEC-082 — 先不改命令面，仅入档调研结论（用户决策，2026-06-24）
- **Scope**: 只调研 + 归档，不修产品代码、不发布新版本、不关闭 RISK-036/RISK-037

## 1. 用户请求

用户希望本插件对外**仅暴露 `/governance` 一个命令**，其余 7 个 `governance-*` 命令对用户隐藏，仅作为工作流演进的内部命令保留。

当前 `commands/` 下 8 个命令文件（均为纯 markdown，无 frontmatter）：
- `governance.md` — 统一入口（需保留暴露）
- `governance-init.md` / `governance-status.md` / `governance-gate.md` / `governance-verify.md` / `governance-update.md` / `governance-review.md` / `governance-cleanup.md` — 7 个候选隐藏命令

## 2. 三平台事实（已验证，含来源）

### Claude Code ✅ 有插件侧隐藏机制
- **事实**：Claude Code 把插件 `commands/*.md` 作为 Skills 加载；Skills 支持 frontmatter 字段 `user-invocable: false`，效果是从 `/` 自动补全菜单隐藏，但模型仍可通过 Skill 工具内部调用。
- 来源：https://code.claude.com/docs/en/plugins , https://code.claude.com/docs/en/skills
- **【推测】**：未在运行时逐字确认 `user-invocable: false` 对 `commands/*.md`（而非仅 `skills/` 目录条目）生效，高置信但非 100%。

### zcode ❌ 无插件侧隐藏机制
- **事实**：`D:\app\zcode\resources\glm\zcode.cjs:2552` 的递归扫描器 `Y3r`（深度上限 `fio=12`）会递归发现所有 `.md` 文件；命令名由相对路径派生（`/`、`\` 折叠为 `:`）。
- **事实**：zcode frontmatter allowlist `hio` 恰为 `["allowed-tools","argument-hint","description","disable-noninteractive","model","skills"]`（`zcode.cjs:2554`）。任何其它字段（如 `hidden`、`user-invocable`、`disable-model-invocation`）→ `custom_command_unknown_frontmatter` **警告且无隐藏效果**。
- **事实**：zcode 唯一真正隐藏路径是用户 runtime 配置 `disabledPaths`（`config.skillOverrides` / `config.skills.disabledPaths`，`zcode.cjs:2554`），**非插件可打包**——属于用户/宿主配置。
- **事实**：子目录方案无效。`commands/_internal/x.md` 会被发现为 `_internal:x`，且 `_` 违反命名正则 `pio=/^[a-z0-9][a-z0-9:-]{0,63}$/` → 报 `custom_command_invalid_name` 错误。
- 命令合法性正则：`pio=/^[a-z0-9][a-z0-9:-]{0,63}$/`。

### Codex ❌ 未发现插件侧隐藏机制
- **事实**：`.codex-plugin/plugin.json` 仅声明 `skills: ./skills/` 与 `interface`，无 `commands` 枚举。
- 来源：OpenAI Codex CLI reference；GitHub issue openai/codex#24041（slash 菜单显示 custom prompts/skills，内置命令默认隐藏）。
- 未在官方文档或参考材料中找到任何让插件隐藏 custom prompt/skill 的 frontmatter 字段或 manifest 键。

## 3. 约束（已验证）

- 移动/重命名 7 个命令文件会破坏 `verify_workflow.py` 多处硬编码路径校验，至少包括：
  - `REQUIRED_FILES` dict
  - 逐文件内容检查
  - `governance-init.md` / `governance-review.md` 模板断言
  - E2E 测试标签（引用 `/governance-status`、`/governance-gate` 等）
  - `contract = ROOT / "commands/governance.md"`
  - `USER_VISIBLE_PATTERNS`（含 `commands/`）
- `.zcode-plugin/plugin.json` 是唯一枚举 commands 的 manifest（`"commands": "commands"`）；Claude/Codex 的 plugin.json 无 `commands` 键。
- `manifest.json` 以目录级 `{"path":"commands/","type":"dir"}` + glob `commands/*.md` 声明，不枚举单文件，且 `commands` 在 `cleanup_scope.directories` 下。

## 4. 候选方案评估

| 方案 | Claude Code | zcode | Codex | 验证器风险 | 结论 |
|------|------------|-------|-------|-----------|------|
| A. frontmatter `user-invocable: false` | ✅ 真隐藏 | ⚠️ 7 警告且不隐藏 | ⚠️ 无影响 | 低 | 仅 Claude 有效 |
| B. 子目录 `commands/_internal/` | 【推测】不确定 | ❌ 命名非法/仍发现 | 不确定 | 高（破 6+ 处硬编码） | 不可行 |
| C. 仅文档引导 | 不隐藏 | 不隐藏 | 不变 | 零 | 安全但不达成目标 |
| D. zcode `disabledPaths` 配置 | — | ✅ 真隐藏 | — | — | 非插件可打包 |

最优可落地组合为 **A + C**（Claude 真隐藏 + 文档诚实标注），但只能覆盖 3 平台中的 1 个。

## 5. 用户决策（DEC-082，2026-06-24）

**先不改命令面，仅入档调研结论。**

理由：三平台隐藏能力不一致（Claude Code 可真隐藏，zcode/Codex 无插件侧隐藏机制）。这是 zcode/Codex 平台能力缺口，而非本插件可在本版本安全解决的 bug。强行加 frontmatter 只在 1/3 平台生效且在 zcode 产生 7 个无害警告；移动文件方案破坏验证器且在 zcode 非法。

调研报告归档保留，未来平台能力变化或用户指令明确时基于此快速重启。

## 6. 边界声明

- 本任务**不修改任何产品代码**（无 `commands/**` / 插件 manifest / `verify_workflow.py` 改动）。
- **不发布新版本**（不改 0.56.1 版本号、不开新 tag）。
- **不关闭 RISK-036/RISK-037**。
- 不声明 official/marketplace approval、universal runtime support 或 1.0.0 readiness。
- zcode/Codex 无插件侧隐藏机制属事实陈述，非 overclaim。

## 7. 关键文件引用（绝对路径）

- `D:\AI\agent\claude\coding\project_management_workflow\commands\*.md` — 8 命令文件，无 frontmatter
- `D:\AI\agent\claude\coding\project_management_workflow\.zcode-plugin\plugin.json` — 唯一含 `"commands": "commands"`
- `D:\AI\agent\claude\coding\project_management_workflow\skills\software-project-governance\infra\verify_workflow.py` — 硬编码命令路径校验多处
- `D:\app\zcode\resources\glm\zcode.cjs:2552-2554` — 递归扫描 `Y3r`、allowlist `hio`、隐藏路径 `disabledPaths`

## 8. 来源

- [Create plugins - Claude Code Docs](https://code.claude.com/docs/en/plugins)
- [Extend Claude with skills - Claude Code Docs](https://code.claude.com/docs/en/skills)
- [Command line options - Codex CLI | OpenAI Developers](https://developers.openai.com/codex/cli/reference)
- [openai/codex#24041](https://github.com/openai/codex/issues/24041)
- 本机 zcode runtime `zcode.cjs`（字节级核实）
