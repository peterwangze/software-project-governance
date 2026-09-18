# Scenario A: 全新项目初始化

> 本文件不在默认注入面——命中 `scenario_hint == "A"` 后按路由层契约 Read。
> 完整执行规程：原 `## Scenario A: 全新项目初始化` 节逐字搬移（零语义丢失）。

## Scenario A: 全新项目初始化

**检测条件**：`.governance/` 不存在 AND 目录基本为空

**流程**：
1. 通过 AskUserQuestion 收集参数（合并为 1-2 个面板，非 4 个连续问题）
2. 创建 `.governance/` 目录及 4 个治理文件（按 profile 差异化）
3. 注入 平台原生入口文件 bootstrap（按 profile 差异化）
4. 安装 git hooks（pre-commit + prepare-commit-msg + commit-msg + post-commit）
5. 输出初始化确认面板
6. 询问是否创建首个任务（INIT-001: 定义项目目标）
7. 初始化完成后 **MUST 自动衔接 Scenario F**——展示治理面板 → 引导用户进入下一步（创建任务/查看详情）

**参数收集**（单面板）：
- project_name（从目录名推断，可修改）
- project_goal（一句话）
- profile（lightweight/standard/strict）
- trigger_mode（always-on/on-demand/silent-track）
- permission_mode（maximum-autonomy/default-confirm）

**输出**：初始化确认面板 + 已创建文件清单

**参考**：`commands/governance-init.md` 完整实现
