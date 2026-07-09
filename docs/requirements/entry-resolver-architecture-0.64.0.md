# `/governance` 入口确定性重构架构 ADR — AUDIT-129

> **版本**: 0.64.0 (MINOR) · **决策**: DEC-096 · **状态**: 诊断完成，FX-130/131/REL-052 待实施
> **风险**: RISK-040（双 root 发散测试 + 真实宿主项目验证门禁）
> **历史约束**: DEC-080 / RISK-038 / AUDIT-115（0.54.2/0.54.3 入口 fast-start 失败链，不得复用其关闭）

---

## 1. 问题陈述

用户反馈 `/governance` 入口三大缺陷：

1. **版本激活探测不自洽**：安装 0.63.4，但 LLM 判定激活 0.54.1。工作流用 `installed_plugins.json`（可能滞后的元数据）重新考古宿主层已决定的事实。
2. **依赖未定义的 `WORKFLOW_HOME` 环境变量**：全仓 `grep -r "export WORKFLOW_HOME"` 零命中。它从未被任何代码设置，纯粹是命令 prose 里的占位符，14+ 处 `commands/*.md` 依赖 LLM 按 4 层优先级解析。自包含性缺失。
3. **入口靠 LLM 推理，启动成本 5min+ / 十万 token**：三层入口 prose 重叠（AGENTS.md bootstrap 176 行 + governance.md 决策树 621 行 + SKILL.md Coordinator 身份），确定性工作（路径/版本/文件状态）与语义工作（场景判断）混淆，全部以自然语言编码交由 LLM 概率执行。

---

## 2. 根因分析（共同根因）

> **确定性工作（路径/版本/状态）与语义工作（场景判断）混淆，且全部以自然语言编码、交由 LLM 概率执行。** 已有的确定性实现证明这些都能做成函数——入口 prose 只是没用它们。

### 2.1 缺陷 1：版本激活探测不自洽

**根因链**：
- `governance.md:119` 决策树 Check 4 让 LLM 查 `installed_plugins.json` 推断"安装版本"
- `verify_workflow.py:16749 check_plugin_freshness()` 读 `installed_plugins.json` 的 `gitCommitSha` 做新鲜度判断——但该文件按项目维度记录，可能滞后（更新后旧记录未刷新，cache 新旧版本并存是正常更新机制）
- 与此同时，**插件宿主在加载 SKILL.md 时已经确定了激活版本**——加载的那份 SKILL.md 的 frontmatter `version` 就是权威，其绝对路径已在 LLM 上下文（system-reminder skill 列表每条带 `file:` 绝对路径）
- **架构层次错位**：应用层用一份可能滞后的元数据，去推翻一份宿主已决定、且 LLM 已可见的权威事实

### 2.2 缺陷 2：WORKFLOW_HOME 依赖

**事实**：
- `WORKFLOW_HOME` 全仓零 `export`/赋值——纯占位符
- 14+ 处引用（governance.md / governance-init.md / governance-status.md / governance-verify.md），每处要求 LLM 按 4 层优先级"解析"：`SOFTWARE_PROJECT_GOVERNANCE_HOME` → `SPG_HOME` → 项目内 `skills/` → 插件 cache
- **同款算法在 git hooks 里用 50 行 bash 确定性实现**（`infra/hooks/pre-commit:55-89 find_spg_home()`）——证明它本是个函数，却被编码成自然语言
- Python 脚本一旦被调用是自定位的（`ROOT = Path(__file__).resolve().parents[3]`）——唯一难的，是 LLM 找到"调用它的那条路径"

### 2.3 缺陷 3：启动成本

- `governance.md:99-123` 决策树（`.governance/` 存在？snapshot 新鲜？异常？版本对比？）每一支都是文件系统 stat，本可一次脚本调用完成
- LLM 每次要把三层 prose 读进上下文并推理路径/版本/场景

---

## 3. 关键历史教训：0.54.2/0.54.3 失败链（DEC-080 / RISK-038）

> ⚠️ **本节是设计 hard constraint。任何入口解析器方案 MUST 满足此教训，否则会重蹈覆辙。**

### 3.1 失败经过

- **0.54.2**（FIX-143/REL-037）：引入 `governance-fast-start --json` 确定性入口 envelope，`commands/governance.md` 从 ~603 行瘦身到 ~83 行。内部测试全绿。
- **真实宿主项目验证**：用户在 `D:\AI\agent\claude\plugin\plugin` 安装 0.54.2 后运行 `/governance`，envelope 显示 **SPG 插件自身的状态**（0.38→0.54.2 版本路线图、VAL-005、FIX-114）而非宿主项目的（v4.0.0–v4.3.0/G6）。
- **0.54.3**（FIX-144/REL-038）：试图修复为"同包 skill 直达"，但只修了定位可执行文件的路径，没修事实源 root——**修错了问题层级**。
- **用户回退**：0.54.2/0.54.3 标记撤回/失效，RISK-038 关闭（触发路径物理移除，非设计验证通过）。

### 3.2 根因

`verify_workflow.py:21` `ROOT = Path(__file__).resolve().parents[3]`：
- 在**开发仓**（狗粮项目），`__file__` 在 `project_management_workflow/skills/.../verify_workflow.py`，`parents[3]` = `project_management_workflow`（插件自身仓库根）——与宿主项目 root **重合**，测不出问题
- 在**真实安装态**，`__file__` 在插件 cache 目录，`parents[3]` = **插件 cache 包根**——**永远不是**用户的宿主项目 cwd

`cmd_governance_fast_start`（FIX-143 `verify_workflow.py:10684`）默认 `root = ROOT`，所有 `.governance/plan-tracker.md` / `evidence-log.md` / `risk-log.md` 读取都相对这个 plugin ROOT → 读了插件自己的 `.governance/`。

**为什么所有测试绿（masking 效应）**：`GovernanceFastStartTests` 总是通过 `--fixture` 显式传 root，从不测默认 `root=ROOT` 路径；e2e fixture 在插件仓内部，projection-sync 也读 in-repo 路径——**没有"插件安装在非狗粮项目"的测试**。

### 3.3 教训（设计 hard constraint，源自 DEC-080 + RISK-038 关闭标准）

| # | 约束 |
|---|------|
| C1 | **双 root 分离**：PLUGIN_HOME（定位可执行文件+读激活版本）与 HOST_PROJECT_ROOT（读事实源）严格分离，绝不从 `__file__` 推导事实源 root |
| C2 | **显式 host-root 参数**：解析器 CLI MUST 接受、`/governance` 命令 MUST 传递显式 host-project-root（cwd 或平台工作区），不依赖 `--fixture` 式的可选覆盖 |
| C3 | **发散测试**：MUST 有 cwd ≠ plugin-package-root ≠ skill-path 三者完全不同的测试，断言事实源读自 host |
| C4 | **fail-closed**：HOST_PROJECT_ROOT 无法确定 → 输出诊断 envelope 拒绝展示治理状态，绝不回退到插件自身状态 |
| C5 | **真实宿主项目验证门禁**：发布前 MUST 在真实插件安装项目验证 `source_facts` 反映宿主项目而非插件自身 |

---

## 4. 解决方案：确定性入口解析器（双 root 模型）

### 4.1 新增 `infra/resolve_entry.py`（~150 行，自定位）

**核心设计**：所有"确定性发现"集中成一次脚本调用 → 结构化 JSON，LLM 只消费结果做语义决策。

#### 双 root 解析

```
PLUGIN_HOME = Path(__file__).resolve().parent.parent
# = skills/software-project-governance/（SKILL.md 所在目录）
# 用途：(a) 定位可执行文件 infra/verify_workflow.py 等
#       (b) 读 SKILL.md frontmatter active_version —— 唯一权威激活版本源

HOST_PROJECT_ROOT = 从 --project-root 显式参数 → cwd → 平台工作区上下文解析
# 用途：读 .governance/ 事实源（plan-tracker/evidence/risk/snapshot）
# 绝不从 __file__ 推导
```

#### 输出 JSON

```json
{
  "plugin_home": "C:/Users/.../cache/.../0.63.4/skills/software-project-governance",
  "host_project_root": "D:/AI/.../user-project",
  "active_version": "0.63.4",
  "version_source": "skill_frontmatter",
  "root_divergence": true,
  "governance_initialized": false,
  "snapshot_exists": false,
  "snapshot_fresh": null,
  "hooks_installed": {"pre-commit": false, "commit-msg": false, "post-commit": false},
  "scenario_hint": "A",
  "resolved_root_ok": true
}
```

- `version_source: "skill_frontmatter"` —— 宿主加载哪份 SKILL.md，其 frontmatter version 即激活版本。废弃 `installed_plugins.json` 作为激活判定源（降 `check_plugin_freshness` 为纯 advisory）。
- `scenario_hint` —— 对应 `governance.md` 决策树 A-F（A=全新初始化/B=半途接入/C=升级/D=会话恢复/E=异常/F=状态），由脚本确定性计算，替代 LLM 多步 stat 推理。
- `resolved_root_ok: false` + 诊断 —— fail-closed，HOST_PROJECT_ROOT 无法确定时拒绝展示治理状态。

### 4.2 三层 prose 瘦身

| 文件 | 当前 | 目标 | 改动 |
|------|------|------|------|
| `governance.md` | 621 行 | ~250 行 | 决策树 6 支文件 stat → `resolve_entry.py` 一次调用，据 `scenario_hint` 分发 |
| `AGENTS.md` | 176 行 | ~90 行 | bootstrap 第一动作改为"调 resolve_entry.py 拿 JSON"+保留 SELF-CHECK+语义纪律；版本自升级对比源从 `installed_plugins.json` 改 SKILL frontmatter |
| `governance-init.md` | 904 行 | ~400 行 | bootstrap 模板瘦身，消除 WORKFLOW_HOME |
| `governance-status.md` | 162 行 | ~80 行 | WORKFLOW_HOME 解析删除 |
| `governance-verify.md` | 106 行 | ~60 行 | WORKFLOW_HOME 解析删除 |

### 4.3 WORKFLOW_HOME 消除

14+ 处 `$WORKFLOW_HOME/infra/x.py` 全部替换为脚本输出的 `plugin_home` 确定性绝对路径。消除 4 层优先级 LLM 推理。

### 4.4 LLM 如何第一次就找到脚本？

宿主加载 SKILL.md/AGENTS.md 时，**其绝对路径已在上下文**（system-reminder skill 列表带 `file:` 字段）。prose 用确定性相对锚定：

> "本 SKILL.md 所在目录 = 激活版本根；入口解析器在 `infra/resolve_entry.py`。运行它，据 `scenario_hint` 分发。"

消除 LLM 的路径/版本推理——上下文里已有的事实，不再要求重新发现。

---

## 5. 解决三缺陷对照

| 缺陷 | 解法 | 验证 |
|------|------|------|
| 版本不自洽 | 权威源：`installed_plugins.json` → **自身 SKILL.md frontmatter**（宿主加载即权威，LLM 上下文已可见） | `active_version` = SKILL frontmatter，`check_plugin_freshness` 降 advisory |
| WORKFLOW_HOME 依赖 | 脚本自定位输出 `plugin_home`/`host_project_root` 绝对路径 | 14+ 处 prose `$WORKFLOW_HOME` 全消除 |
| 启动成本 | 决策树 6 支 stat → 脚本 1 次输出；三层 prose 瘦身 | 启动 token 基线对比（目标 < 5min/<50k token） |

---

## 6. RISK-040 关闭标准（独立制定，不复用 RISK-038 关闭）

1. `resolve_entry.py` 单元测试覆盖 cwd ≠ plugin-root ≠ skill-path 三者完全不同场景（模拟真实安装态），断言 `active_version` = SKILL frontmatter 且事实源读自 host
2. HOST_PROJECT_ROOT 无法确定时输出 fail-closed 诊断 envelope，绝不展示插件自身状态
3. 真实宿主项目验证——部署到至少 1 个非狗粮项目验证 `source_facts` 反映该宿主项目版本/阶段而非插件自身
4. FX-130/131/REL-052 经 Design Reviewer + Code Reviewer 独立审查

---

## 7. 版本规划

- **target 0.64.0 (MINOR)** —— 入口架构级重构
- **版本路线图变更（DEC-096，用户确认）**：原 0.64.0 预留给 verify_workflow.py 拆分 Phase 6（DEC-083/RISK-039），用户决策入口重构占用 0.64.0（用户痛点优先于内部拆分），拆分 Phase 6 顺延到 0.66.0，Phase 5 顺延到 0.67.0
- **任务链**：AUDIT-129（诊断ADR ✅）→ FX-130（resolve_entry.py）→ FX-131（prose 重构）→ REL-052（发布 0.64.0）

### 边界（no-overclaim）

- 不关闭 RISK-036/037/039/040
- 不声明 1.0.0 readiness
- 不触碰 1.0.0 外部验证/官方提交链
- FX-130/131 执行时 MUST 满足 RISK-040 关闭标准方可发布
- 不复用 RISK-038 关闭作为准入门禁（EVD-587/DEC-081）
- 本方案是确定性解析器 + 完整 skill load，**不是** 0.54.2/0.54.3 的 fast-start 简化路径（DEC-080 约束）

---

## 参考

- DEC-096（本决策）· AUDIT-129（本诊断）· RISK-040（新增风险）
- DEC-080 / RISK-038 / AUDIT-115（历史失败链）· EVD-577~587（失败+关闭证据）
- DEC-083（原 0.64.0 拆分主题，顺延到 0.66.0）
- `infra/hooks/pre-commit:55-89 find_spg_home()`（确定性 root 解析的 bash 实现，设计参考）
- `verify_workflow.py:21 ROOT = Path(__file__).resolve().parents[3]`（当前 root 解析，待重构）
