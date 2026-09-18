# Scenario C: 工作流升级

> 本文件不在默认注入面——命中 `scenario_hint == "C"` 后按路由层契约 Read。
> 完整执行规程：原 `## Scenario C: 工作流升级` 节逐字搬移（零语义丢失）。

## Scenario C: 工作流升级

**检测条件**：`resolve_entry.py` 输出 `scenario_hint == "C"`——即 `.governance/` 存在、无异常、且 host `工作流版本` < `active_version`（`active_version` 来自 SKILL.md frontmatter，权威；DEC-096）。不再由本命令在 prose 中比较版本号。

**时序（FEAT-034 首次交互前置）**：版本差距 + CHANGELOG delta 摘要随快路径首次 ask 一并呈现征询确认；下方步骤 4 的升级写序列（入口 bootstrap 替换 / plan-tracker 结构补全 / 归档迁移等写操作）在用户确认升级后执行——写序列不前置于首次交互，**用户未响应前零写操作**（FEAT-035——读入口与写迁移解耦：展示状态不拥有修改项目的隐含授权）。

**深检衔接（DEC-207② P2-1，MUST）**：版本升级写序列属推进类动作——用户确认升级后、执行写序列前 MUST 先满足 M5.5 条 3 的深检前置（健康摘要 `check-governance --summary-only` + 交叉验证；FEAT-034 后置时序的必达补齐），不得以"已获得升级确认"替代深检。

**流程**：
1. 从 resolve_entry envelope 读取 `active_version`（权威）与 plan-tracker 记录版本，计算版本差距
2. 提取 CHANGELOG delta（从 plan-tracker 版本到当前版本）
3. **AskUserQuestion 呈现升级摘要，征询确认（FEAT-035——确认前不执行任何写操作）**：
   - 版本跨度（记录版本 → `active_version`）
   - CHANGELOG 要点（新增/修复行数 + 代表条目）
   - 将执行的写操作清单（显式列出目标文件）：平台原生入口文件 bootstrap 段（AGENTS.md/CLAUDE.md 等按平台实际入口）、`.governance/plan-tracker.md`（结构补全 + `工作流版本` 字段）、`.git/hooks/*`（缺失时提示安装命令，不代写）、插件残留清理删除面（cleanup.py——dry-run 先行 + 确认后执行；删除插件安装目录中不在 canonical manifest 中的文件，`.governance/`/`.git/` 不触碰）、其它模板补全涉及的治理文件
   - 回滚方式（入口文件 bootstrap 段按 git/备份恢复、plan-tracker `工作流版本` 字段回退；归档迁移执行前 dry-run 报告先行呈现并留存）
   - 选项：**(1) 执行升级（推荐——保持既有"自动完成"精神，确认后其余步骤全自动）** / (2) 暂不升级（记录 migration 待处理状态，不影响会话其余功能）/ (3) 查看完整 CHANGELOG 后再决定
4. 用户确认后执行升级序列：
   - A. 替换 平台原生入口文件 bootstrap 段为最新模板（保留 profile 差异化）
   - B. 补全 plan-tracker 缺失结构（permission_mode、版本规划、需求跟踪矩阵、变更控制含快速通道）
   - C. Hook 存活检测——缺失则提示安装命令（hook 路径用 `<plugin_home>/infra/hooks/*`）
    - C-2. 插件残留清理删除面（与模板 C-2 同序同措辞——dry-run 先行 + 确认后执行）：先运行 `python <plugin_home>/infra/cleanup.py --dry-run` 呈现待删报告（基于 manifest.json 的结构 diff），AskUserQuestion 确认后再执行 `python <plugin_home>/infra/cleanup.py`（不确认 → 跳过清理，不影响其余步骤）
   - D. 更新 `工作流版本` 为 `active_version`
   - E. 持续归档触发检测与执行（`<plugin_home>` 来自 resolve_entry.py，取代 `$WORKFLOW_HOME` 路径考古；归档写操作同 ask-确认前置——dry-run 报告先行呈现，用户确认后才执行迁移）：
     - 运行 `python <plugin_home>/infra/archive.py migrate --auto --dry-run` 检测四类触发器：
       1. 首次迁移：`.governance/archive/index.md` 不存在 AND `plan-tracker.md` > 80 KB AND 已发布版本 ≥ 2
       2. 发布强制：出现新的已发布版本后，除最新已发布版本外仍有未归档历史 task
       3. task 增量：热文件中可归档 completed task 达到阈值
       4. 90 天兜底：长期未归档但仍有可归档历史数据
     - dry-run 报告需要归档 → **呈现 dry-run 报告并通过 AskUserQuestion 确认** → 运行 `python <plugin_home>/infra/archive.py migrate --auto`，再运行 `python <plugin_home>/infra/verify_workflow.py check-archive-integrity`
     - 归档成功 → 输出归档迁移摘要（格式: 📦 治理数据归档完成: 归档{N}个task→..., plan-tracker: {old}KB→{new}KB(-{pct}%)）
     - 归档完整性失败 → 记录到 risk-log；发布/版本 bump 收尾场景 MUST 阻断完成
     - 无可归档数据 → 跳过归档（不修改文件）
5. 输出升级摘要面板

**输出**：升级摘要（版本跨度 + 新增功能 + 已升级项 + 需手动操作）

升级完成后 **MUST 自动衔接 Scenario F**——展示最新状态面板。

**幂等性**：运行两次安全——已是最新版本时自动路由到 Scenario F；用户拒绝升级时同样路由到 Scenario F（migration 待处理状态经 FEAT-033 migration 标志在状态行持续可见）
