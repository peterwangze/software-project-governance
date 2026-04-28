# governance-update — 更新 CLAUDE.md bootstrap（不覆盖治理数据）

更新已安装用户的 CLAUDE.md 中的 Governance Bootstrap 段到最新版本。**不触碰 `.governance/` 目录中的任何文件**——只更新 bootstrap 模板。

这是老用户升级路径的核心——用户通过 `/plugin update` 获取新版本后，运行此命令将 bootstrap 行为升级到最新。

## Input Parameters

| Parameter | Type | Required | Default | Valid Values | Description |
|-----------|------|----------|---------|-------------|-------------|
| profile | enum | no | (从 plan-tracker 读取) | lightweight / standard / strict | 治理强度 Profile——决定注入精简版还是完整版 bootstrap |

## Execution Flow

### Step 1: 检查是否已初始化
- **IF** `.governance/plan-tracker.md` 不存在 → 返回错误 `UPDATE-ERR-001`（未初始化——请先运行 governance-init）
- **ELSE** → 继续 Step 2

### Step 2: 读取当前 profile
- 读取 `.governance/plan-tracker.md` 的 `## 项目配置` 节，提取 `Profile` 字段
- **IF** 未提供 `profile` 参数 → 使用 plan-tracker 中的 profile
- **IF** plan-tracker 中也无 profile → 默认 `standard`

### Step 3: 检测当前 bootstrap 版本
- **IF** 项目根目录存在 `CLAUDE.md`：
  - 搜索 `## Governance Bootstrap` 段落
  - **IF** 存在 `## Governance Bootstrap（强制` → 已是最新版，输出"Bootstrap 已是最新，无需更新"，**STOP**
  - **IF** 存在 `## Governance Bootstrap (added by software-project-governance plugin)` → 检测到旧版英文 stub
  - **IF** 存在 `## Governance Bootstrap` 但不是以上两种格式 → 旧版
  - **IF** 不存在 `## Governance Bootstrap` → 首次注入
- **IF** 项目根目录不存在 `CLAUDE.md` → 创建，注入完整 bootstrap

### Step 4: 生成最新 bootstrap 模板
- 根据 `profile` 选择模板：
  - **lightweight** → 精简版（3 节）
  - **standard / strict** → 完整版（Step 0~4 + 干活前检查 + 提问规则 + 关键决策 + 收工前检查 + 版本变化自动检测）
- 模板内容 = `governance-init.md` Step 7 中的对应注入模板

### Step 5: 替换 bootstrap 段
- 在 `CLAUDE.md` 中找到 `## Governance Bootstrap` 段落（从该行到下一个 `## ` 标题或文件末尾）
- 替换为最新模板
- **保留 CLAUDE.md 中其他所有内容不变**

### Step 6: 更新 plan-tracker 工作流版本
- 读取当前安装的 workflow 版本（从 `skills/software-project-governance/SKILL.md` frontmatter）
- 更新 `.governance/plan-tracker.md` 中的 `工作流版本` 为当前版本

### Step 7: 记录更新到 decision-log
- 新增一条决策记录：`DEC-xxx | <today> | governance-update——bootstrap 模板从旧版升级到 v{version} | 用户更新插件后发现 bootstrap 版本落后 | 运行 governance-update 更新 CLAUDE.md bootstrap 段 | 备选方案：手动重新 init（会覆盖 plan-tracker） | 选择非破坏性更新——只更新 bootstrap，不动治理数据 | CLAUDE.md | 已执行 | —`

### Step 8: 输出确认

## Output Format

```
Bootstrap updated to v{version}

Before: {old_bootstrap_summary}
After:  {new_bootstrap_summary}

Changes:
  ✅ 新增：{list of new bootstrap features}
  ✅ CLAUDE.md 其他内容未修改
  ✅ .governance/ 数据未修改
  ✅ plan-tracker 工作流版本 → {version}

Next session, the updated bootstrap will activate automatically.
```

## Error Codes

| Code | Condition | User Message | Agent Action |
|------|-----------|-------------|-------------|
| UPDATE-ERR-001 | `.governance/plan-tracker.md` 不存在 | "Project has not been initialized yet. Run /governance-init to set up governance tracking first." | 停止执行 |
| UPDATE-ERR-002 | 无法读取当前 workflow 版本 | "Cannot determine current workflow version. Ensure the plugin is installed correctly." | 停止执行 |

## Self-Validation

After execution, agent MUST verify:
- [ ] CLAUDE.md 中的 bootstrap 段已更新为最新模板
- [ ] CLAUDE.md 中 bootstrap 段之外的内容未变化
- [ ] `.governance/` 目录中所有文件未被修改（除 plan-tracker 的 `工作流版本` 字段）
- [ ] decision-log 中有本次更新的记录
- [ ] plan-tracker 的 `工作流版本` 已更新为当前版本
