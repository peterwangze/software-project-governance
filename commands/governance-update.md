# governance-update — 更新 平台原生入口文件 bootstrap（已弃用）

> **已弃用——使用 `/governance`**，它会自动检测版本差距并触发 Scenario C 升级。本命令保留为手动回退。

更新 平台原生入口文件 中的 Governance Bootstrap 段到最新版本。**不触碰 `.governance/` 目录中的任何文件**。

**注意**：此命令是手动回退选项。正常情况下，bootstrap 在每次会话开始时会**自动检测版本变化并自升级**——用户不需要手动运行此命令。仅在自动升级失败或用户想立即升级（不等下次会话）时使用。

## 输入参数

| 参数 | 类型 | 必需 | 默认值 | 有效值 | 描述 |
|-----------|------|----------|---------|-------------|-------------|
| profile | 枚举 | 否 | (从 plan-tracker 读取) | lightweight / standard / strict | 治理强度 Profile——决定注入精简版还是完整版 bootstrap |

## 执行流程

### Step 1: 检查是否已初始化
- **IF** `.governance/plan-tracker.md` 不存在 → 返回错误 `UPDATE-ERR-001`（未初始化——请先运行 governance-init）
- **ELSE** → 继续 Step 2

### Step 2: 读取当前 profile
- 读取 `.governance/plan-tracker.md` 的 `## 项目配置` 节，提取 `Profile` 字段
- **IF** 未提供 `profile` 参数 → 使用 plan-tracker 中的 profile
- **IF** plan-tracker 中也无 profile → 默认 `standard`

### Step 3: 检测当前 bootstrap 版本
- **IF** 项目根目录存在 `平台原生入口文件`：
  - 搜索 `## Governance Bootstrap` 段落
  - **IF** 存在 `## Governance Bootstrap（强制` → 已是最新版，输出"Bootstrap 已是最新，无需更新"，**停止**
  - **IF** 存在 `## Governance Bootstrap (added by software-project-governance plugin)` → 检测到旧版英文 stub
  - **IF** 存在 `## Governance Bootstrap` 但不是以上两种格式 → 旧版
  - **IF** 不存在 `## Governance Bootstrap` → 首次注入
- **IF** 项目根目录不存在 `平台原生入口文件` → 创建，注入完整 bootstrap

### Step 4: 生成最新 bootstrap 模板
- 根据 `profile` 选择模板：
  - **lightweight** → 精简版（3 节）
  - **standard / strict** → 完整版（Step 0~4 + 干活前检查 + 提问规则 + 关键决策 + 收工前检查 + 版本变化自动检测）
- 模板内容 = `governance-init.md` Step 7 中的对应注入模板

### Step 5: 替换 bootstrap 段
- 在 `平台原生入口文件` 中找到 `## Governance Bootstrap` 段落（从该行到下一个 `## ` 标题或文件末尾）
- 替换为最新模板
- **保留 平台原生入口文件 中其他所有内容不变**

### Step 6: 更新 plan-tracker 工作流版本
- 读取当前安装的 workflow 版本（从 `skills/software-project-governance/SKILL.md` frontmatter）
- 更新 `.governance/plan-tracker.md` 中的 `工作流版本` 为当前版本

### Step 7: 记录更新到 decision-log
- 新增一条决策记录：`DEC-xxx | <今天> | governance-update——bootstrap 模板从旧版升级到 v{version} | 用户更新插件后发现 bootstrap 版本落后 | 运行 governance-update 更新 平台原生入口文件 bootstrap 段 | 备选方案：手动重新 init（会覆盖 plan-tracker） | 选择非破坏性更新——只更新 bootstrap，不动治理数据 | 平台原生入口文件 | 已执行 | —`

### Step 8: 输出确认

## 输出格式

```
Bootstrap 已更新至 v{version}

更新前: {旧版 bootstrap 摘要}
更新后: {新版 bootstrap 摘要}

变更:
  ✅ 新增：{新版 bootstrap 功能列表}
  ✅ 平台原生入口文件 其他内容未修改
  ✅ .governance/ 数据未修改
  ✅ plan-tracker 工作流版本 → {version}

下次会话时，更新后的 bootstrap 将自动生效。
```

## 错误码

| 代码 | 条件 | 用户消息 | Agent 动作 |
|------|-----------|-------------|-------------|
| UPDATE-ERR-001 | `.governance/plan-tracker.md` 不存在 | "项目尚未初始化。请先运行 /governance-init 设置治理跟踪。" | 停止执行 |
| UPDATE-ERR-002 | 无法读取当前 workflow 版本 | "无法确定当前工作流版本。请确认插件安装正确。" | 停止执行 |

## 自校验

执行后，agent MUST 验证：
- [ ] 平台原生入口文件 中的 bootstrap 段已更新为最新模板
- [ ] 平台原生入口文件 中 bootstrap 段之外的内容未变化
- [ ] `.governance/` 目录中所有文件未被修改（除 plan-tracker 的 `工作流版本` 字段）
- [ ] decision-log 中有本次更新的记录
- [ ] plan-tracker 的 `工作流版本` 已更新为当前版本
