# 变更影响分析 Checklist

修改产品代码前 MUST 执行本 checklist。影响分析结论 MUST 写入 `.governance/evidence-log.md`（对应任务 ID）。

## Step 1: 范围分析

- [ ] 本次修改的目标是什么？（一句话摘要）
- [ ] 修改涉及哪些文件？（列出所有文件的相对路径）
- [ ] 这些文件属于哪个模块/层？（入口层 / 业务智能层 / 能力层 / 基础设施层 / 核心层 / 适配层）

## Step 2: 依赖分析

- [ ] 哪些文件引用了被修改的文件？（grep 搜索被修改文件的路径，列出引用者）
- [ ] 哪些 agent 依赖被修改的行为？（检查 SKILL.md Agent 分发路由表、agent 角色定义文件）
- [ ] 哪些 SKILL 引用被修改的内容？（检查 skills/*/SKILL.md 中的路径引用）
- [ ] 哪些 verify_workflow.py 检查项依赖被修改的文件？（检查 REQUIRED_FILES dict）
- [ ] 哪些 bootstrap 模板引用了被修改的文件？（检查 commands/governance-init.md Step 7）
- [ ] 哪些 plugin 包文件依赖被修改的路径？（检查 .claude-plugin/plugin.json、.codex-plugin/plugin.json）

## Step 3: 用户影响分析

- [ ] Q1: 用户是否需要做什么来获得变更？
      答案 MUST 为以下之一：`plugin update` / `governance-init` / `governance-update` / `手动` / `自动生效（下次会话）`
- [ ] Q2: 用户如何知道变更存在？
      答案 MUST 为以下之一：`CHANGELOG` / `README` / `版本号 bump` / `不可见变更`
- [ ] Q3: 用户体验是否真的改变了？
      答案 MUST 为以下之一：`是-需迁移指南` / `是-有说明（见下文）` / `否-内部重构` / `否-治理记录`
- [ ] Q4: 变更是否需要迁移指南？
      IF Q3 = `是-需迁移指南` → MUST 提供迁移指南文件路径
      Breaking change 无迁移指南 → BLOCK

## Step 3.5: 目标一致性分析

- [ ] 读取 plan-tracker `## 项目配置` 中的 `- **项目目标**:` 字段
- [ ] 本次变更是否服务于项目目标？（MUST 回答并论证，min 30 字符）
- [ ] 如果变更引入新功能/新概念/新文件 → MUST 论证此变更如何服务于项目目标
- [ ] 如果变更与项目目标的关系不直接（如重构、基础设施改进）→ MUST 说明间接服务关系
- [ ] 论证缺失或不充分（< 30 字符）→ 本次变更将被 commit-msg hook BLOCK

## Step 4: 架构影响分析

- [ ] 修改是否改变模块间的依赖关系？
- [ ] 修改是否引入循环依赖？
- [ ] 修改是否违反六层架构的层级调用方向（适配层→入口层→业务智能层→能力层→基础设施层→核心层）？
- [ ] 修改是否影响与其他 agent 平台的兼容性？（Codex / Gemini / 国内 Agent CLI）
- [ ] 修改是否改变 manifest.json 的 canonical 文件清单？（如果是 → MUST 同步更新 manifest.json）

## Step 5: 记录

- [ ] 影响分析结论已写入 evidence-log（格式：`| EVD-XXX | TASK-ID | 影响分析 | 范围:{文件数}文件, 依赖:{N}引用者, 目标对齐:{min 30 chars rationale}, 用户影响: 获得={Q1答案}, 感知={Q2答案}, 体验变化={Q3答案}, 迁移指南={path 或 "不需要"}, 架构影响:{无/有-详见risk-log} | ...`）
- [ ] 如果影响分析发现风险 → 已创建 risk-log 条目
- [ ] 如果影响分析确认无影响 → 已声明"无影响"（简短说明原因）

## 执行时机

| 触发条件 | 是否 MUST |
|---------|----------|
| 修改产品代码文件（按产品代码 vs 治理记录边界定义） | **MUST** |
| 修改仅涉及治理记录（.governance/、docs/、project/CHANGELOG.md 等） | 跳过 |
| P0 任务且涉及 >=2 个架构层的修改 | **MUST** + 额外 spawn Analyst + Architect |
| 紧急 hotfix（事后 MUST 补影响分析） | 事后补 |

## 影响分析格式

```
格式: EVD-XXX | TASK-ID | 影响分析 | 
范围:{文件数}文件, 
依赖:{N}引用者, 
目标对齐:{min 30 chars rationale}, 
用户影响: 获得={Q1答案}, 感知={Q2答案}, 体验变化={Q3答案}, 迁移指南={path 或 "不需要"}, 
架构影响:{无/有-详见risk-log}
```
