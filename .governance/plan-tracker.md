# 当前项目样例

本文件使用当前项目作为 `software-project-governance` workflow 的样例项目。

## 项目配置

- **项目目标**: 将大型软件公司的项目管理经验沉淀为可被 coding agent 消费的项目治理 workflow plugin/skill——过程自动（agent 在后台持续看护，用户专注思考而非流程管理）、交互友好（AskUserQuestion 仅在关键决策打断，其余自动执行）、目标不偏离、质量不低质
- **Profile**: standard（本项目即为工作流产品本身，需要充分验证标准 profile 的治理能力）
- **触发模式**: always-on（每次会话自动加载，持续跟踪项目状态）
- **操作权限模式**: maximum-autonomy
- **工作流版本**: 0.33.0（自动检测版本变化——更新后首次会话自动触发增量采纳）
- **当前阶段**: 维护与演进（第 11 阶段）— 六层架构重构进行中
- **并行活跃阶段**: 架构设计（第 5 阶段）— AUDIT-082 Phase 3-5 能力层+业务智能层迁移
- **接入方式**: 从立项开始，但前期未正式执行 Gate 检查，2026-04-20 起补正式 onboarding

## Onboarding 声明

本项目从立项开始就使用工作流跟踪，但前期仅使用了记录层（证据、决策、风险），未执行正式 Gate 检查。2026-04-20 起正式执行 onboarding 协议：

- **前置阶段（1~10）Gate**: 全部标记为 `passed-on-entry`
- **当前阶段（11）Gate**: G11 pending，待维护阶段任务进一步推进后检查
- **已补齐的前置阶段关键决策**: 每个前置阶段至少 1 条（见决策记录 DEC-001~DEC-023）

## Gate 状态跟踪

| Gate | 阶段转换 | 状态 | 通过日期 | 关键证据 |
| --- | --- | --- | --- | --- |
| G1 | → 调研 | passed-on-entry | 2026-04-20 | DEC-001：仓库定位升级为 agent plugin/skill 仓库 |
| G2 | → 技术选型 | passed-on-entry | 2026-04-20 | DEC-006：调研结果驱动后续主线 |
| G3 | → 环境搭建 | passed-on-entry | 2026-04-20 | DEC-005：集成模式优先于目录布局 |
| G4 | → 架构设计 | passed-on-entry | 2026-04-20 | DEC-022：环境配置以仓库分层结构为准 |
| G5 | → 开发实现 | passed-on-entry | 2026-04-20 | DEC-023：CI 校验脚本覆盖全部关键资产 |
| G6 | → 测试 | passed-on-entry | 2026-04-20 | DEC-003：Claude 入口分层设计 |
| G7 | → 防护网与CI/CD | passed-on-entry | 2026-04-20 | DEC-024：测试以校验脚本和 README 一致性检查为主 |
| G8 | → 版本发布 | passed-on-entry | 2026-04-20 | DEC-015：外部能力层首轮验证先走 shared command |
| G9 | → 运营 | passed-on-entry | 2026-04-20 | DEC-025：版本发布以 git commit 为最小发布单元 |
| G10 | → 维护 | passed-on-entry | 2026-04-20 | DEC-009：Gemini 兼容路线规划作为运营回收产出 |
| G11 | → 下一轮 | passed | 2026-04-21 | 复盘完成、经验已回灌到规则和模板（子工作流+skill）、下轮方向明确、版本化记录已更新 |

## 项目总览

| 项目 | 当前阶段 | 总任务数 | 已完成 | 阻塞中 | 关键风险数 | 最近 Gate 结论 | 最近复盘日期 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 项目管理工作流插件 | 维护（并行活跃：架构） | 168 | 154 | 0 | 2 | G11 通过 | 2026-05-07 |

## 当前活跃事项（2026-05-03 全路径架构审查后更新）

AUDIT-082 Phase 1-5 全部完成 ✅。六层架构已落地。

**2026-05-03 全路径架构审查**：Architect (老顾) + Design Reviewer (老洪) 独立审查完成。19 项发现经用户视角过滤后入账。新增 FIX-043：Release Agent 零激活——版本规划/发布管理全部由 Coordinator 自执行，无独立审查。详见 DEC-060。

### 优先级一览

| 优先级 | ID | 事项 | 依赖 | 目标版本 | 闭环路径 | 状态 |
|--------|----|------|------|---------|---------|
| **P0** | AUDIT-083 | 审查防护覆盖 ✅ | — | 0.11.0 | 5 个新审查 SKILL + Reviewer 绑定——已完成 | | — |
| **P0** | AUDIT-084 | Release Agent 职责拆分 ✅ | AUDIT-083 | 0.11.0 | Release 解除 stage-operations 绑定——已完成 | | — |
| **P1** | AUDIT-085 | 新增 `/governance-review` 斜杠命令 ✅ | — | 0.11.0 | 用户可手动触发独立审查——已完成 | | — |
| **P1** | AUDIT-086 | pre-commit hook 行为层检测 ✅ | AUDIT-083 | 0.11.0 | hook Step 7 review evidence chain 检查——已完成 | | — |
| **P1** | AUDIT-068 | 方法论路由集成 ✅ | — | 0.11.0 | Coordinator 内嵌路由表——已完成 | | — |
| **P1** | AUDIT-069 | Agent 提示词工程 ✅ | — | 0.11.0 | 9 Agent 完整 prompt 结构——已完成 | | — |
| **P0** | AUDIT-088 | 产品-项目物理分离 ✅ | — | 0.12.0 | project/ 目录+references/净化+cleanup命令——已完成 | | — |
| **P0** | AUDIT-089 | Agent Team 激活注入——bootstrap 模板补 M1.1 触发 ✅ | — | 0.13.0 | governance-init.md 模板 + SKILL.md + 版本 bump——已完成 | | — |
| **P1** | AUDIT-090 | 命令重命名——/software-project-governance→/governance ✅ | — | 0.13.1 | 与 /governance-* 体系统一——已完成 | | — |
| **P0** | AUDIT-091 | SKILL 独立可调用——25 能力 SKILL 注册为 plugin 可见 ✅ | — | 0.14.0 | plugin.json 发现→每个 SKILL 可被独立调用——已完成 | | — |
| **P0** | AUDIT-092 | Agent 职责强化+提示词增强——Coordinator→Agent→SKILL 链路 ✅ | — | 0.15.0 | 9 Agent prompt 增强+职责边界+SKILL 加载指令——已完成 | | — |
| **P0** | REL-002 | 0.15.0 正式发布——git tags v0.8.0~v0.15.0 ✅ | — | 0.15.0 | 8 个版本 tags 创建并推送——已完成 | | — |
| **P0** | AUDIT-093 | Agent 命名纠正+动作下沉——SKILL.md→prompt.md + 重复动作抽象为 SKILL ✅ | — | 0.16.0 | 9 文件重命名 + 全仓引用更新 + agent prompt 瘦身——已完成 | | — |
| **P0** | AUDIT-094 | 借鉴 writing-workflow 架构优化——硬门槛量化+审查组拆分+输出具体化 ✅ | — | 0.17.0 | 6 新审查 Agent + 9 Agent 硬门槛表 + 输出路径具体化——已完成 | | — |
| **P0** | AUDIT-095 | 入口统一——主 SKILL 即 Coordinator，消除跳转层 + Agent 标准化 ✅ | — | 0.18.0 | Coordinator 合并入 SKILL.md + 7 组分组表 + coordinator/prompt.md 废弃——已完成 | | — |
| **P0** | AUDIT-096 | adapter 配置修复——plugin.json 回退 + stub 恢复 ✅ | — | 0.18.0 | 紧急修复：skills 数组格式不被支持导致插件失效，回退到 string + 恢复 stub——已完成 | | — |
| **P0** | AUDIT-097 | 代码仓对齐官方约定——Agent 目录结构标准化 | — | 0.19.0 | agents/<组>/<角色>/prompt.md → agents/<name>.md（plugin root 平铺） | ✅ 已完成 |
| **P0** | AUDIT-098 | 代码仓对齐官方约定——SKILL 目录结构标准化 | AUDIT-097 | 0.19.0 | skills/software-project-governance/skills/ → skills/<name>/（plugin root 平铺），删除 25 stub | ✅ 已完成 |
| **P2** | AUDIT-087 | 命令端到端验证——e2e-test-project 逐命令验证 | — | 1.0.0 | 6 个命令全部 PASS——Phase 1 ✅ (infra 修复) Phase 2 ✅ (静态 2/6) Phase 3 ✅ (QA 静态验证 6/6, 0 P0/P1 缺陷) | ✅ 已完成 (2026-05-08) |
| **P2** | AUDIT-025 | Stage skill 质量均衡 ✅ | — | 1.0.0 | Stage Skill 深度评分 Rubric 设计完成——6 维度/1-5 分/最低门槛/均衡目标/11 skill 评分/自动化检查脚本 | ✅ 已完成 | — |
| **P1** | FIX-026 | Hook 产品代码检测同步——Step 7b/9 公共变量提取 ✅ | — | 0.27.0 | pre-commit——is_product_code() 函数提取 + 7 单元测试 | ✅ 已完成 |
| **P1** | FIX-027 | SKILL.md 模板引用补充 ✅ | — | 0.27.0 | governance-init.md 模板——Agent 分发路由后补充调度模板+行为协议引用 | ✅ 已完成 |
| **P1** | FIX-028 | COMMIT_EDITMSG 时序修复——消除版本 bump 的 --no-verify 依赖 ✅ | — | 0.27.0 | pre-commit——过期窗口 5→60 秒 | ✅ 已完成 |
| **P0** | FIX-029 | pre-commit "integer expression expected" 修复——IS_P0 初始化 + TASK_ID 变量名隔离 ✅ | — | 0.27.0 | pre-commit——IS_P0=0 初始化 + STEP7_TASK_ID 局部变量 | ✅ 已完成 |
| **P0** | SYSGAP-043 | Phase 1: Coordinator 并行调度预检规则——spawn 前校验文件目标无重叠 ✅ | — | 0.27.0 | behavior-protocol.md + SKILL.md + agent-dispatch-template.md（3 文件, +24 行）| 阿速 | ✅ 已完成 |
| **P1** | SYSGAP-044 | Phase 2: Worktree 隔离——并行 Agent 使用独立 git worktree ✅ | SYSGAP-043 | 1.0.0 | behavior-protocol.md + SKILL.md + agent-dispatch-template.md（4 文件, +18/-8，含 P2-001 修复） | 阿速 | ✅ 已完成 |
| **P0** | REL-003 | 0.27.0 版本发布——CHANGELOG 补全 0.25~0.27 条目 + bump 版本号 ✅ | — | 0.27.0 | CHANGELOG.md（+32 行，0.25.0~0.27.0）+ plan-tracker 版本 0.26.0→0.27.0 | Coordinator | ✅ 已完成 |
| **P0** | FIX-030 | Profile 差异化 bootstrap 模板——lightweight/standard/strict 三级 ✅ | — | 0.28.0 | governance-init.md Step 7 三级模板：lightweight ~47行, standard ~212行, strict ~232行 | ✅ 已完成 |
| **P2** | FIX-031 | [内部归档] 六层架构文档——从 SKILL.md 移除空引用，归档到 docs/architecture/ | — | 0.31.0 | SKILL.md line 13: `references/architecture.md`→`docs/architecture/` | ✅ 已完成 |
| **P2** | FIX-032 | [内部归档] 修复 M2 预加载路径——behavior-protocol.md L79 | — | 1.0.0 | behavior-protocol.md M2 预加载: `main-workflow.md`→`skills/main-workflow/SKILL.md` | ✅ 已完成 |
| **P0** | FIX-036 | pre-commit hook Step 7 升级为 BLOCK——产品代码无审查证据 → 拒绝 commit ✅ | — | 0.29.0 | pre-commit: WARN→BLOCK + is_product_code() 重写 + IS_P0 初始化修复 | ✅ 已完成 |
| **P0** | FIX-037 | verify_workflow.py 新增审查覆盖率检查——check-review-coverage ✅ | — | 0.29.0 | Check 21: 产品代码任务审查覆盖率统计 + 未审查任务清单 | ✅ 已完成 |
| **P0** | FIX-038 | Profile 差异化的代码级 Gate 裁剪——verify_workflow.py check-profile-consistency ✅ | — | 0.29.0 | Check 22: Gate 行数/任务列数/profile 一致性 + strict 禁止条件通过 | ✅ 已完成 |
| **P0** | FIX-043 | 路由表补全——版本规划/任务排布 → Release+Analyst + Agent namespace 降级方案 ✅ | — | 0.29.0 | SKILL.md 路由表 16→18行 + 4文件 Agent namespace 文档化 | ✅ 已完成 |
| **P0** | REL-005 | 0.29.0 版本发布——版本 bump 0.28.0→0.29.0 + 路线图新增 0.30.0 ✅ | — | 0.29.0 | 6 文件版本号同步 + CHANGELOG 0.29.0 条目 + 版本路线图 0.30.0 规划 | ✅ 已完成 |
| **P0** | REL-004 | 0.28.0 版本发布——版本 bump + CHANGELOG ✅ | — | 0.28.0 | 7 文件版本号同步 0.27.0→0.28.0 + CHANGELOG 新增条目 | ✅ 已完成 |
| **P1** | FIX-033 | bootstrap 与 /governance 职责边界重定义——bootstrap=最小初始化, /governance=完整交互 ✅ | — | 0.28.0 | governance.md 新增分工章节 + governance-init.md 三级模板追加 /governance 引用 | ✅ 已完成 |
| **P2** | FIX-034 | [内部归档] 清理幽灵 Agent 文件——coordinator.md/governance-developer.md | — | 1.0.0 | coordinator.md 已于 AUDIT-095 标注 DEPRECATED；governance-developer.md 仍被 SKILL.md 路由表引用（非幽灵文件） | ✅ 已完成（无需操作） |
| **P1** | FIX-035 | 简单操作快速通道——治理记录修改跳过 Agent Team 激活 ✅ | — | 0.28.0 | behavior-protocol.md 新增 M1.2 + governance-init.md 模板追加快速通道引用 | ✅ 已完成 |
| **P0** | FIX-044 | GOV_COMMIT_MSG 桥接文件清理——prepare-commit-msg 写后未清理，导致残留文件干扰下一次 commit 的 task ID 提取 ✅ | — | 0.30.0 | post-commit: 安全网兜底清理 .git/GOV_COMMIT_MSG（修正：移除 pre-commit 清理——因 prepare-commit-msg 在 pre-commit 之后运行） | ✅ 已完成 |
| **P1** | FIX-045 | COMMIT_EDITMSG 过期彻底修复——GOV_COMMIT_MSG 可用时跳过 Source 3 COMMIT_EDITMSG ✅ | — | 0.30.0 | pre-commit: GOV_COMMIT_MSG 非空 → GOV_BRIDGE_VALID=1 → 跳过 Source 3 不可靠的时间戳启发式 | ✅ 已完成 |
| **P1** | FIX-046 | Hook 自升级链路——版本 bump 时 .git/hooks/ 自动同步到源文件最新版本 ✅ | — | 0.30.0 | pre-commit Step 0: @version 标记 → cmp 比较 → cp + exec 热更新 | ✅ 已完成 |
| **P0** | FIX-047 | pre-commit 无法读取当前 commit message——Git hook 顺序 pre-commit→prepare-commit-msg→commit-msg 导致 GOV_COMMIT_MSG 桥接永远滞后一个 commit ✅ | FIX-044 | 0.30.0 | 新增 commit-msg hook（Steps 1-5, 10-12）+ 精简 pre-commit（仅 Steps 6-9 文件依赖检查） | ✅ 已完成 |
| **P1** | FIX-048 | pre-commit integer expression 残留 + commit-msg 冒号匹配 + 3-hook 存活检测更新 ✅ | — | 0.30.0 | pre-commit: tr -d '\r' \| head -1 净化 + commit-msg: 目标对齐[:：]/用户影响[:：] + governance-init.md: 2→3 hook | ✅ 已完成 |
| **P0** | FIX-049 | README 安装链接修复——仓库名 peterwangze/governance→peterwangze/software-project-governance + 命令引用更新 + 用户指引重写（唯一命令 /governance）+ 7 命令加重定向头 | — | 0.30.0 | README.md（repo 名+命令章节+5分钟开始+验证）+ 3 commands（gate/cleanup/review 加重定向） | ✅ 已完成 |
| **P0** | FIX-050 | /governance 嵌入 Coordinator 激活——身份+铁律+路由表+产品代码边界+交互规则，使其成为"Coordinator 激活 + 场景路由"唯一入口 | FIX-049 | 0.30.0 | governance.md（+65行 Coordinator 激活章节）+ SKILL.md（描述更新）+ 分工表更新 | ✅ 已完成 |
| **P0** | FIX-051 | 用户视角审视——Scenario 衔接引导（A/B→F, C→F, E→F）+ Scenario F 任务入口（4 种情况引导）+ Scenario D 新鲜度放宽（24h~7d 仍提供继续）+ 决策树补全"日常干活"路径 | FIX-050 | 0.30.0 | governance.md（+45 行：4 个 Scenario 衔接 + Scenario F 任务入口 + Scenario D 新鲜度调整） | ✅ 已完成 |
| **P1** | FIX-052 | 版本 bump 自动化——checklist/脚本防版本号遗漏（0.30.0 开发中 5 次版本 bump 均需人工逐文件同步） | REL-006 | 0.31.0 | verify_workflow.py 新增 check-version-consistency 子命令 + check-governance Check 23 + hook @version 检查 + 2 bug 修复 | ✅ 已完成 |
| **P0** | REL-006 | 0.30.0 版本发布——版本 bump 0.29.0→0.30.0 + CHANGELOG + 路线图更新 | FIX-051 | 0.30.0 | 6 文件版本号同步 + CHANGELOG 0.30.0 条目 + 版本路线图 0.30.0 标记已发布 | ✅ 已完成 |
| **P0** | REL-007 | 0.31.0 版本发布——版本 bump 0.30.0→0.31.0 + CHANGELOG + 路线图更新 + tag | — | 0.31.0 | 11 文件版本号同步 + CHANGELOG 0.31.0 条目 + 版本路线图 0.31.0 标记已发布 + git tag v0.31.0 | ✅ 已完成 |
| **P0** | REL-008 | 0.32.0 版本发布——版本 bump 0.31.0→0.32.0 + CHANGELOG + 路线图更新 + tag | FIX-056, FIX-057 | 0.32.0 | 14 文件版本号同步 + CHANGELOG 0.32.0 条目(FIX-056+057) + 版本路线图 0.32.0 标记已发布 + 3 份 release docs + git tag v0.32.0 + hooks 同步修复(F-001) | ✅ 已完成 |
| **P2** | FIX-039 | Agent 工作可见性——Coordinator spawn agent 时输出进度通知 | — | 0.31.0 | SKILL.md + agent-dispatch-template.md——进度通知规范 + 完成报告格式 | ✅ 已完成 |
| **P2** | FIX-040 | 角色昵称不再向用户输出——用户可见消息用功能性描述 | — | 0.31.0 | 5 文件——SKILL.md + agent-dispatch-template.md + behavior-protocol.md + skill-index.md + agent-communication-protocol.md | ✅ 已完成 |
| **P2** | FIX-041 | Scenario F 状态面板输出折叠优化——非关键信息默认折叠 | — | 1.0.0 | governance.md Scenario F——3 项非关键信息（Gate 表/最近活动/插件版本）用 <details> 折叠 | ✅ 已完成 |
| **P2** | FIX-042 | 外部项目实战验证——1-2 个真实外部项目接入 + 反馈收集 | — | 1.0.0 | 验证报告（evidence-FIX-042-validation-plan.md）+ 问题清单（3 项：P0 cleanup 边界/P1 Check 10 误报/P2 commit-msg hook） | ✅ 已完成 (2026-05-06) |
| **P0** | FIX-053 | cleanup.py 范围边界修复——仅扫描 plugin 目录，不触碰用户项目文件 | FIX-042 | 0.31.0 | cleanup.py（PLUGIN_SCOPE_DIRS 常量 + scan_actual() 重写 + test_cleanup.py）+ Review ✅ | ✅ 已完成 (2026-05-06) |
| **P1** | FIX-054 | Check 10 M5 误报修复——排除 skills/ agents/ commands/ 等 plugin 源文件，仅检查用户项目文件 | FIX-042 | 0.31.0 | verify_workflow.py（PLUGIN_SCOPE_DIRS + _is_plugin_path() + 用户文件扫描 + 死代码清理）+ Review ✅ | ✅ 已完成 (2026-05-07) |
| **P2** | FIX-055 | commit-msg hook 安装——governance-init.md/bootstrap 增加 commit-msg 安装步骤 + Hook 存活检测增加 commit-msg | FIX-042 | 0.31.0 | governance-init.md + CLAUDE.md bootstrap 模板（9 文件各 +1 hook 引用）+ Review ✅ (APPROVED) | ✅ 已完成 (2026-05-07) |
| **P0** | FIX-056 | Agent 意外并发防护——Coordinator 误判超时导致重复 spawn 同一任务 | 用户反馈 (2026-05-07) | 0.32.0 | Phase 1 ✅: agent-locks.json + behavior-protocol/SKILL/communication/dispatch-template (6 文件). Phase 2 ✅: post-commit Step 5 (锁清理+scope creep检测) + Check 25 (agent_lock_consistency) + check-locks 子命令 (965133e) | ✅ 已完成 (2026-05-07) |
| **P1** | FIX-057 | 项目清洁度治理——未跟踪文件分类归档 + .gitignore + 未跟踪检测机制 | 用户反馈 (2026-05-07) | 0.32.0 | Phase 1: 6 文档归档 + .gitignore + evidence-log 解除跟踪 (f293743). Phase 2: check-governance Check 24 + pre-commit Step 10 未跟踪检测 (a9225cf) | ✅ 已完成 (2026-05-07) |
| **P0** | SYSGAP-030 | 治理数据伸缩性——归档/分层存储/增量索引，解决 plan-tracker/evidence-log 无限膨胀 + 每次会话治理负担线性增长 | — | 1.0.0 | Phase 1 ✅ + Phase 2 ✅ (archive.py --auto + 模板同步 + CLAUDE.md Step E + 狗粮首次迁移: 36 tasks + 30 evidence 归档, plan-tracker 101→99KB, evidence 106→91KB) | ✅ 已完成 (2026-05-10) |
| **降级** | REQ-014/016/017/018/019/027/028 | Agent Team 实战验证后 | 1.0.0 | Task-Gate/Phase-Gate 迁移 + E2E |
| **P0** | CLEANUP-001 | Phase 1: 创建 canonical manifest.json | — | 0.20.0 | v0.19.0 完整目录结构 JSON 声明（product + repo_only + exclude） | | — |
| **P0** | CLEANUP-002 | Phase 2: 重写 governance-cleanup.md | CLEANUP-001 | 0.20.0 | 声明式 diff 清理——基于 manifest.json 自动计算冗余 | | — |
| **P0** | CLEANUP-003 | Phase 3: verify_workflow.py 增强 | CLEANUP-001 | 0.20.0 | check-manifest-consistency + REQUIRED_FILES 迁移至 manifest.json | | — |
| **P0** | CLEANUP-004 | Phase 4: Bootstrap 清理逻辑更新 | CLEANUP-002 | 0.20.0 | CLAUDE.md + governance-init.md 自动清理段改为 manifest-based | | — |
| **P0** | CLEANUP-005 | Phase 5: 文档纪律更新 | CLEANUP-002, CLEANUP-003 | 0.20.0 | manifest.md 简化 + VERSIONING.md 补规则 + CHANGELOG | | — |
| **P0** | SYSGAP-001 | 方案 1A: 产品代码边界定义 | — | 0.21.0 | SKILL.md + interaction-boundary.md 定义产品代码 vs 治理记录边界 | ✅ 已完成 |
| **P0** | SYSGAP-002 | 方案 1C: M7.5 Agent Team 强制激活检查 | SYSGAP-001 | 0.21.0 | behavior-protocol.md M7.5 Step 2.5——产品代码 MUST spawn Agent Team | ✅ 已完成 |
| **P0** | SYSGAP-003 | 方案 2A: 影响分析 checklist 创建 | — | 0.21.0 | references/change-impact-checklist.md——5 步影响分析 | ✅ 已完成 |
| **P0** | SYSGAP-004 | 方案 2B: M7.5 影响分析步骤嵌入 | SYSGAP-003 | 0.21.0 | behavior-protocol.md M7.5 Step 2.6——变更前影响分析 | ✅ 已完成 |
| **P0** | SYSGAP-005 | 方案 5B: Commit message 规范强化 | — | 0.21.0 | behavior-protocol.md M7.4——单 task 单 commit + 禁止"顺带" | ✅ 已完成 |
| **P0** | SYSGAP-006 | 方案 5A: Pre-commit scope WARN | — | 0.21.0 | infra/hooks/pre-commit——跨域变更 WARN | ✅ 已完成 |
| **P0** | SYSGAP-007 | 方案 1D: Pre-commit Agent Team WARN | SYSGAP-001 | 0.21.0 | infra/hooks/pre-commit——产品代码 bypass 检查 | ✅ 已完成 |
| **P0** | SYSGAP-008 | 方案 3A: 交叉引用检查 | — | 0.22.0 | verify_workflow.py——悬空引用+废弃路径+循环引用检测 | ✅ 已完成 |
| **P0** | SYSGAP-009 | 方案 3B: 顺序 ID 检查 | — | 0.22.0 | verify_workflow.py——DEC/EVD/RISK 编号连续+交叉引用完整性 | ✅ 已完成 |
| **P0** | SYSGAP-010 | 方案 3C: 结构有效性检查 | — | 0.22.0 | verify_workflow.py——表格列数+frontmatter+JSON段完整性 | ✅ 已完成 |
| **P0** | SYSGAP-011 | 方案 3D: M5 语义检查增强 | — | 0.22.0 | verify_workflow.py Check 10——内联提问模式+选项列表检测 | ✅ 已完成 |
| **P0** | SYSGAP-012 | 方案 5C: Commit scope verify | — | 0.22.0 | verify_workflow.py——重复taskID+关键字+bulk commit检测 | ✅ 已完成 |
| **P0** | SYSGAP-013 | 方案 1B: Governance Developer agent | — | 0.22.0 | agents/governance-developer.md——治理基础设施专用Developer | ✅ 已完成 |
| **P0** | SYSGAP-014 | 方案 2C: 影响分析路由 | — | 0.22.0 | SKILL.md 分发路由表——Analyst+Architect 影响分析行 | ✅ 已完成 |
| **P0** | FIX-021 | DEC-046 缺失 Gap 修复 | — | 0.22.1 | decision-log.md DEC-046 占位补充 | ✅ 已完成 |
| **P0** | FIX-022 | Plan-tracker 表格列数修复 | — | 0.22.1 | plan-tracker.md 任务表头补"状态"列 | ✅ 已完成 |
| **P0** | FIX-023 | Evidence-log 交叉引用孤儿修复 | — | 0.22.1 | verify_workflow.py sequential ID parser | ✅ 已完成 |
| **P0** | FIX-024 | 交叉引用悬空引用修复 | — | 0.22.1 | verify_workflow.py 代码块过滤 + exclude 字段名 | ✅ 已完成 |
| **P0** | SYSGAP-015 | 方案 4A: 本项目测试定义 | — | 0.23.0 | stage-testing/SKILL.md——测试类型对应表 | ✅ 已完成 |
| **P0** | SYSGAP-016 | 方案 4B: verify 单元测试 | — | 0.23.0 | infra/tests/——23 tests, 6 测试类 | ✅ 已完成 |
| **P0** | SYSGAP-017 | 方案 4C: e2e 测试项目 | — | 0.23.0 | infra/tests/e2e/——13 tests, 5 测试类 | ✅ 已完成 |
| **P0** | SYSGAP-018 | 方案 4E: CI pipeline | — | 0.23.0 | .github/workflows/ci.yml——6 步自动检查 | ✅ 已完成 |
| **P0** | SYSGAP-019 | 方案 4D: 缺陷驱动测试积累 | — | 0.23.0 | stage-maintenance/SKILL.md——Bug修复 MUST 添加测试 | ✅ 已完成 |
| **P0** | SYSGAP-020 | 方案 3E: 版本一致性增强 | — | 0.23.0 | verify_workflow.py——CHANGELOG + plan-tracker 版本检查 | ✅ 已完成 |
| **P0** | SYSGAP-021 | project_goal 字段存储 | — | 0.24.0 | governance-init.md 模板——plan-tracker 配置块新增 项目目标 | ✅ 已完成 |
| **P0** | SYSGAP-022 | Checklist 增强——Step 3.5 + 强制格式 | SYSGAP-021 | 0.24.0 | change-impact-checklist.md——目标一致性 + 用户影响强制格式 | ✅ 已完成 |
| **P0** | SYSGAP-023 | Check 16 目标一致性检查 | SYSGAP-022 | 0.24.0 | verify_workflow.py——project_goal + 目标对齐字段验证 | ✅ 已完成 |
| **P0** | SYSGAP-024 | Check 17 用户影响检查 | SYSGAP-022 | 0.24.0 | verify_workflow.py——用户影响字段解析 + 矛盾检测 + BLOCK | ✅ 已完成 |
| **P0** | SYSGAP-025 | Hook Step 10-12 BLOCK 增强 | SYSGAP-023, SYSGAP-024 | 0.24.0 | pre-commit——目标一致性 BLOCK + 用户影响 BLOCK + 迁移指南 BLOCK | ✅ 已完成 |
| **P0** | SYSGAP-026 | 模板 project_goal 注入 | SYSGAP-021 | 0.24.0 | governance-init.md——新项目自动含 project_goal 字段 | ✅ 已完成 |
| **P0** | SYSGAP-027 | M7.5 系统强制说明 | SYSGAP-025 | 0.24.0 | behavior-protocol.md——注明 pre-commit hook 系统强制 | ✅ 已完成 |
| **P0** | SYSGAP-028 | D1/D2 引用 Check 16/17 | SYSGAP-023, SYSGAP-024 | 0.24.0 | audit-framework.md——Gate 级深度审计引用 commit 级轻量检查 | ✅ 已完成 |
| **P0** | SYSGAP-029 | 回归测试——8 新用例 | SYSGAP-027 | 0.24.0 | test_verify_workflow.py——GoalAlignmentTests + UserImpactTests | ✅ 已完成 |
| **P0** | FIX-025 | Hook 缺陷修复——grep -P 兼容 + task ID 模式 + 时序 | — | 0.24.1 | pre-commit——Windows grep -P → sed + SYSGAP/CLEANUP 加入模式 + COMMIT_EDITMSG 过期检测 | ✅ 已完成 |

### 0.24.0 — 目标一致性 + 用户影响系统强制 ✅ 已发布 [已归档]

**目标**: 三层强制体系——每次 commit 产品代码时 MUST 论证变更如何服务于项目目标 + 回答用户影响三问。缺失 → BLOCK。

**设计方案**: ADR-002（`docs/architecture/ADR-002-goal-alignment-user-impact-enforcement.md`）

**交付清单**:
- [x] 首次 commit 被 Step 11 BLOCK——系统自执行验证通过
- [x] git tag v0.24.0

### 0.23.0 — 测试体系 + CI ✅ 已发布 [已归档]

**目标**: 建立适配 skill/workflow 项目的测试体系和 CI pipeline。

**交付清单**:
- [x] 36 tests PASSED
- [x] git tag v0.23.0

### 0.21.0 — 纪律防线 [已归档]

**目标**: 对照 Claude Code 官方 plugin 规范（`claude-code/plugins/plugin-dev/skills/plugin-structure/SKILL.md`），修正目录结构违规项。

**官方约定**:
- `skills/<name>/SKILL.md` — skill 子目录在 plugin root 平铺
- `agents/<name>.md` — agent 文件在 plugin root 平铺
- `commands/<name>.md` — command 文件在 plugin root 平铺
- plugin.json 不需要 `skills`/`agents`/`commands` 字段（靠约定自动发现）

**当前违规**:
- [x] 全仓路径引用更新（SKILL.md、behavior-protocol.md、verify_workflow.py、CLAUDE.md、governance-init.md 等 11 文件）
- [x] governance-cleanup 更新（旧路径残留清理）
- [x] verify PASSED
- [x] git tag v0.19.0 → pushed

### 0.20.0 — 声明式清理机制 ✅ 已发布 [已归档]

**目标**: 清理命令从"硬编码已知冗余列表"改为"canonical manifest + 结构 diff"，每次目录结构调整后清理命令自动生效，不再需要手动适配。

**设计方案**: ADR-001（`docs/architecture/adr-canonical-manifest-cleanup.md`）

**核心思路**:
- `manifest.json` 声明当前版本应该有哪些文件（product + repo_only）
- cleanup = `(实际文件) - (manifest 展开) - (排除清单) = 待清理`
- verify_workflow.py 的 REQUIRED_FILES 同步迁移至从 manifest.json 读取（单一事实源）

**交付清单**:
- [x] verify PASSED
- [x] git tag v0.20.0

### 0.21.0 — 纪律防线 ✅ 已发布 [已归档]

**目标**: 建立"不再继续犯错"的系统机制——从文本规则升级为行为协议 + 系统检查。

**设计方案**: ADR-001（`docs/architecture/ADR-001-systemic-gap-analysis.md`）

**核心思路**:
- 产品代码 vs 治理记录边界定义 → Coordinator 明确什么必须通过 Agent Team
- M7.5 扩展 → 修改前 MUST 判定文件类型 + 执行影响分析
- Commit 粒度规范 → 单 task 单 commit，禁止"顺带"修改
- Pre-commit hook 增强 → Agent Team bypass WARN + 跨域变更 WARN

**交付清单**:
- [x] verify PASSED
- [x] git tag v0.21.0

### 0.22.0 — 检查体系升级 ✅ 已发布 [已归档]

**目标**: verify_workflow.py 从"文件存在性检查"升级为"语义一致性检查"（11→15 项自动检查）。

**核心思路**:
- 交叉引用检查——悬空引用+废弃路径+循环引用
- 顺序 ID 检查——DEC/EVD/RISK 编号 Gap detection
- 结构有效性检查——表格列数+frontmatter+JSON 段完整性
- M5 语义增强——内联提问模式取代字符串匹配
- Commit scope verify——重复 task ID+关键字+bulk

**交付清单**:
- [x] verify PASSED(新检查发现预存问题——按预期工作)
- [x] git tag v0.22.0

### 0.15.0 — Agent 职责强化+提示词增强 ✅ 已发布 [已归档]

**目标**: Coordinator→Agent→SKILL 三层链路闭环——Coordinator 按需选择 Agent → Agent 收到任务 MUST 加载 SKILL → SKILL 提供确定性执行步骤

**交付清单**:
- [x] 职责边界硬声明（你负责X，你绝不Y）
- [x] SKILL 加载指令（收到X任务→MUST加载Y SKILL→按步骤执行）
- [x] 返回协议（完成后返回结论+证据给Coordinator）
- [x] 9 Agent 全部更新
- [x] verify PASSED
- [x] git tag v0.15.0 → pushed (2026-05-01)

### 0.14.0 — SKILL 独立可调用 ✅ 已发布 [已归档]

**目标**: 25 能力 SKILL 不再是被动文档，而是 plugin 系统可发现的独立可调用实体

**交付清单**:
- [x] plugin.json skills 路径覆盖能力层 SKILL 目录
- [x] 每个 SKILL 可作为独立 skill 被 sub-agent 调用
- [x] Coordinator spawn sub-agent 时 MUST 加载对应能力 SKILL
- [x] verify PASSED
- [x] git tag v0.14.0 → pushed (2026-05-01)

### 0.13.0 — Agent Team 激活注入 ✅ 已发布 (0.13.1 PATCH) [已归档]

**目标**: bootstrap 模板补入 Agent Team 身份声明——每次会话自动激活 Coordinator

**交付清单**:
- [x] governance-init.md Step 7 模板新增 Agent Team 激活段
- [x] SKILL.md 入口更新——引用新 bootstrap
- [x] Coordinator 作为 sub-agent 运行的说明
- [x] 版本 bump 0.12.0→0.13.0
- [x] verify PASSED
- [x] git tag v0.13.0 → pushed (2026-05-01)
- [x] git tag v0.13.1 → pushed (2026-05-01, PATCH: 命令重命名追加修复)

### 0.12.0（✅ 已完成） [已归档]

```
AUDIT-088 ✅ → 0.12.0 ✅
  39文件 git mv: project/ 目录建立 + references/ 净化 + governance-cleanup 命令
  版本 bump: 0.11.0→0.12.0
```

### 0.11.0（✅ 已完成） [已归档]

```
AUDIT-082 Phase 1-5 ✅ → AUDIT-083~086 ✅ + AUDIT-068~069 ✅ → 0.11.0 ✅
```

### 0.11.0 交付清单（12/12 ✅） [已归档]

- [x] `skills/` 目录建立——25 SKILL 就位 ✅
- [x] 所有 SKILL 统一 YAML frontmatter ✅
- [x] 9 Agent × SKILL 绑定声明 ✅
- [x] SKILL 分类索引 ✅
- [x] infra/TOOLS.md 升级 ✅
- [x] 5 个新审查 SKILL ✅
- [x] Reviewer Agent 绑定 7 个审查 SKILL ✅
- [x] Release Agent 解除 stage-operations 绑定 ✅
- [x] 新增 `/governance-review` 命令 ✅
- [x] pre-commit hook review 证据检查 ✅
- [x] 方法论路由集成 ✅
- [x] verify_workflow.py PASSED ✅

### 1.0.0 依赖链

```
0.11.0 ✅
    │
    ▼
AUDIT-087: 命令E2E验证(P2)
AUDIT-025: Skill质量均衡(P2)
    │
    ▼
AUDIT-072: 外部验证≥2(P0)
AUDIT-073: 迁移指南(P0)
AUDIT-074~076: 文档+E2E(P1)
    │
    ▼
1.0.0 正式发布
```
- [ ] pre-commit hook 新增 review evidence chain 检查
- [ ] AUDIT-068 方法论路由集成
- [ ] AUDIT-069 提示词工程
- [ ] verify_workflow.py PASSED

## 实施路线图（DEC-052）—— ✅ 已完成并归档

**DEC-052 分层推进模型已于 2026-05-01 完成全部 4 层任务。后续按 AUDIT-082 六层架构 Phase 模型推进。**

### 四层推进模型（历史参考）

```
Layer 0: 防跑偏基础 ──→ Layer 1: 外部验证 ──→ Layer 2: 产品内容 ──→ Layer 3: 体验增强
  (项目不会跑偏)         (产品真的存在)         (工作流有价值)         (从能用到好用)
```

### Layer 0: 防跑偏基础（Anti-Drift Foundation）

**目标**：建立治理强制力——证据可信、责任明确、Gate 可脚本判定、agent 行为可外部验证。不依赖 agent "记得"或"自觉"。

```
Tier 0-A: 快速修复（3 tasks, ~1 session）
  AUDIT-026 (P2) — 平台原生入口文件/SKILL.md 循环依赖解耦
  AUDIT-027 (P2) — 协议层与实际目录命名统一
  AUDIT-035 (P1) — Agent 失败模式文档与应急预案
  │ 无前置依赖，三个可并行
  ▼
Tier 0-B: 证据可信度（1 task, ~1 session）
  AUDIT-022 (P1) — 证据质量基线升级
  │ 产出：check-governance 新增证据质量检查（循环引用/会话上下文/空输出）
  │ 前置：0-A 完成（证据格式需先稳定）
  ▼
Tier 0-C: 治理强制力（3 tasks, ~2 sessions）
  AUDIT-030 (P1) — DRI 模型落地（Owner 唯一化 + escalation path）
  AUDIT-031 (P1) — M8 自检外部验证（依赖 0-B 的证据检查基础）
  AUDIT-011 (P1) — Gate 自动判定脚本（依赖 0-B 的证据质量模式）
  │ 产出：Gate 可脚本判定，治理合规可外部验证，DRI 唯一化
  ▼
Tier 0-D: 防漂移机制（3 tasks, ~2 sessions）
  AUDIT-029 (P1) — 跨会话记忆机制（session snapshot）
  AUDIT-017 (P1) — 触发模式实现（always-on/on-demand/silent-track）
  AUDIT-018 (P1) — Profile 差异化行为落地（依赖 0-C 的 Gate 判定能力）
```

**Layer 0 小计：10 tasks，P0:0 P1:8 P2:2，预计 ~6 sessions**

### Layer 1: 外部验证（External Validation）

**目标**：在外部项目中验证产品是否真的可用。没有外部反馈，所有内容改进方向都是猜测。

```
Tier 1-A: 最小外部验证（1 task, ~1 session + 外部项目时间）
  AUDIT-003 (P0) — 外部项目验证最小路径
  │ 产出：第一个真实用户反馈
  │ 前置：Layer 0 完成（防跑偏机制就位后，外部验证才有意义）
  ▼
Tier 1-B: 端到端验证（3 tasks, ~1 session）
  AUDIT-023 (P1) — 端到端可用性验证（依赖 AUDIT-003 的外部项目）
  AUDIT-004 (P1) — governance-init 端到端验证（依赖 AUDIT-003）
  AUDIT-006 (P1) — Claude Code 插件命令验证（依赖 AUDIT-003）
```

**Layer 1 小计：4 tasks，P0:1 P1:3，预计 ~2 sessions**

### Layer 2: 产品内容（Product Content）

**目标**：子工作流从骨架升级为深度指南，企业实践从概念变成可执行步骤。

```
Tier 2-A: 内容深度（2 tasks, ~2 sessions）
  AUDIT-021 (P0) — 7 个子工作流内容深度补强（AI风险表+企业实践映射+Gate自动判定列）
  AUDIT-024 (P1) — company-practices-summary 重写（自包含可执行摘要）
  │ 前置：Layer 1 完成（外部反馈告诉我们哪些阶段最需要补强）
  ▼
Tier 2-B: 企业实践落地（4 tasks, ~2 sessions，可并行）
  AUDIT-032 (P1) — Bar Raiser 否决权（Amazon）
  AUDIT-033 (P1) — 字节 A/B 测试纳入 release
  AUDIT-034 (P2) — 华为蓝军单 agent 适配
  AUDIT-036 (P2) — Release 现代发布实践（依赖 AUDIT-021 release 需先有基础深度）
  ▼
Tier 2-C: 质量均衡（3 tasks, ~1 session）
  AUDIT-025 (P2) — Stage skill 质量均衡（依赖 AUDIT-021）
  AUDIT-038 (P2) — 子工作流独立使用目标锚定强制机制（依赖 AUDIT-021）
  MAINT-002 (P2) — 更多大厂实践映射
```

**Layer 2 小计：9 tasks，P0:1 P1:3 P2:5，预计 ~5 sessions**

### Layer 3: 体验增强（Enhancement）

**目标**：从"能用"到"好用"——B/C 级自动化、工具通用化、兼容性政策。

```
Tier 3-A: 自动化升级（4 tasks, ~2 sessions，严格顺序依赖）
  AUDIT-010 (P1) — CI 集成 check-governance（依赖 0-C AUDIT-011）
  AUDIT-014 (P2) — git hook 治理触发（依赖 AUDIT-010）
  AUDIT-012 (P2) — headless runner 可执行版（依赖 0-C AUDIT-011）
  AUDIT-013 (P2) — MCP server 最小实现（依赖 0-C AUDIT-011）
  │
Tier 3-B: 工具通用化（3 tasks, ~2 sessions）
  AUDIT-009 (P2) — 外部项目中途接入验证（依赖 Layer 1 AUDIT-003）
  AUDIT-019 (P2) — verify_workflow.py 通用化（依赖 Layer 1 AUDIT-003）
  AUDIT-020 (P2) — 自定义 Profile YAML 解析（依赖 0-D AUDIT-018）
  │
Tier 3-C: 兼容与政策（4 tasks, ~2 sessions，可并行）
  AUDIT-037 (P2) — 向后兼容性政策与废弃通知
  MAINT-013 (P1) — 用户项目/样例数据边界说明
  MAINT-014 (P1) — Agent 入口差异显式化
  MAINT-023 (P1) — Gemini/国内 agent CLI 最小验证
```

**Layer 3 小计：11 tasks，P0:0 P1:4 P2:7，预计 ~6 sessions**

### 依赖关系总表

| 任务 | 所属 Tier | 前置任务 | 被依赖 |
|------|----------|---------|--------|
| AUDIT-026 | 0-A | 无 | — |
| AUDIT-027 | 0-A | 无 | — |
| AUDIT-035 | 0-A | 无 | — |
| AUDIT-022 | 0-B | 0-A 完成 | AUDIT-031, AUDIT-011 |
| AUDIT-030 | 0-C | 0-B 完成 | — |
| AUDIT-031 | 0-C | AUDIT-022 | — |
| AUDIT-011 | 0-C | AUDIT-022 | AUDIT-018, AUDIT-010/012/013 |
| AUDIT-029 | 0-D | 0-C 完成 | — |
| AUDIT-017 | 0-D | 0-C 完成 | — |
| AUDIT-018 | 0-D | AUDIT-011 | AUDIT-020 |
| AUDIT-003 | 1-A | Layer 0 完成 | AUDIT-023/004/006/009/019 |
| AUDIT-023 | 1-B | AUDIT-003 | — |
| AUDIT-004 | 1-B | AUDIT-003 | — |
| AUDIT-006 | 1-B | AUDIT-003 | — |
| AUDIT-021 | 2-A | Layer 1 完成 | AUDIT-036/025/038 |
| AUDIT-024 | 2-A | Layer 1 完成 | — |
| AUDIT-032 | 2-B | 2-A 完成 | — |
| AUDIT-033 | 2-B | 2-A 完成 | — |
| AUDIT-034 | 2-B | 2-A 完成 | — |
| AUDIT-036 | 2-B | AUDIT-021 | — |
| AUDIT-025 | 2-C | AUDIT-021 | — |
| AUDIT-038 | 2-C | AUDIT-021 | — |
| MAINT-002 | 2-C | 2-A 完成 | — |
| AUDIT-010 | 3-A | AUDIT-011 | AUDIT-014 |
| AUDIT-014 | 3-A | AUDIT-010 | — |
| AUDIT-012 | 3-A | AUDIT-011 | — |
| AUDIT-013 | 3-A | AUDIT-011 | — |
| AUDIT-009 | 3-B | AUDIT-003 | — |
| AUDIT-019 | 3-B | AUDIT-003 | — |
| AUDIT-020 | 3-B | AUDIT-018 | — |
| AUDIT-037 | 3-C | 无 | — |
| MAINT-013 | 3-C | 无 | — |
| MAINT-014 | 3-C | 无 | — |
| MAINT-023 | 3-C | 无 | — |

### 执行纪律

1. **严格按 Tier 顺序推进**：当前 Tier 的所有任务完成后才能进入下一 Tier。
2. **Tier 内部任务可并行**：同一 Tier 内无依赖关系的任务可并行执行。
3. **每个 Tier 完成后执行审计（D1+D3+D4 维度）**：确认 Tier 的目标是否达成，偏差是否已纠正。
4. **计划本身接受 Meta-Audit**：如果连续 2 个 Tier 的执行顺序被打破，说明依赖分析有误 → 重新梳理依赖。


## 版本规划

版本规划回答"何时交付什么"——与 DEC-052 分层执行计划（"按什么顺序做"）互补。执行计划控制推进节奏，版本规划控制交付边界。

### 版本路线图

| 版本 | 状态 | 预计日期 | 核心范围 | 包含 Tier/Layer | 关键交付物 |
|------|------|---------|---------|---------------|-----------|
| 0.1.0 | 已发布 | 2026-04-17 | 仓库骨架 + 协议层 V1 | — | plugin-contract, workflow-schema, adapters/ |
| 0.2.0 | 已发布 | 2026-04-19 | 产品形态重定义 | — | agent-integration-models, default-product-shape, repo-local-termination |
| 0.3.0 | 已发布 | 2026-04-24 | 用户视角审视 + 三层架构落地 | — | main-workflow.md, TOOLS.md, stages/, references/ 补全 |
| 0.4.0 | 已发布 | 2026-04-26 | 治理强制力 V1 | Layer 0-A/B/C | DRI, M8外部验证, Gate自动判定, 证据质量基线 |
| 0.5.0 | 已发布 | 2026-04-26 | 执行连续性 + Deadline 强制 | — | M7.4/M7.5, Check 8/9, audit-framework 融入 |
| 0.5.1 | 已发布 | 2026-04-27 | Gate 自动判定 45%→100% | — | G6-G11 启发式规则, company-practices-summary |
| **0.6.0** | **已发布** | **2026-04-28** | **用户体验断层闭环 + 内容深度** | **AUDIT-021,024,029,017,032,033,010,018,047 + FIX-001~005 + DIAG-001** | **bootstrap升级, session-snapshot, 触发模式×权限模式双维度, 交互式init, 7子工作流深度, BarRaiser否决权, A/B测试, CI集成, Profile差异化, 版本规划, 需求跟踪, 变更控制, 里程碑, PR/FAQ/OKR/6-Pager模板** |
| 0.6.10 | 已发布 | 2026-04-29 | 系统级约束架构——pre-commit hook（阻断型） | CONSTRAINT-001 | pre-commit-hook.sh, governance-init Step 8 双 hook 安装, Hook 存活检测升级, 版本 0.6.9→0.6.10 |
| 0.6.11 | 已发布 | 2026-04-29 | 版本规划纪律强化——8 条纪律 + 违规案例 + failure mode 9 | CONSTRAINT-001 | plan-tracker 版本规划纪律重写, VERSIONING.md 版本规划纪律, agent-failure-modes 失败模式 9, 版本 0.6.10→0.6.11 |
| **0.7.0** | **已发布** | **2026-04-29** | **外部验证 + 企业实践 + 交互覆盖闭环（12/12 完成）** | **AUDIT-003(P0)✅, FIX-014(P0)✅, FIX-013(P1)✅, AUDIT-034(P2)✅, AUDIT-036(P2)✅, AUDIT-038(P2)✅ + AUDIT-004(P1), AUDIT-006(P1), AUDIT-023(P1), MAINT-013(P1), MAINT-014(P1), MAINT-023(P1)** | **外部项目验证报告, governance-init/命令端到端验证, 蓝军单agent适配, 现代发布实践, 用户数据边界/agent入口差异文档, Gemini最小验证, 目标锚定强制机制** |
| **0.7.1** | **已发布** | **2026-04-30** | **M5 AskUserQuestion 绕过根因修复（6 缺口闭环）** | **FIX-015(P0)** | **development sub-workflow 清除内联问题指令, SKILL.md M2.3 M5 交互信号, 轻量 profile M5 规则, stage-gates.md 原则#10 Gate-M5 绑定, verify_workflow.py Check 10 M5 反模式检测** |
| **0.8.0** | **已发布** | **2026-05-01** | **统一治理命令——一键入口+6场景自动分类（用户易用性基础设施）** | **AUDIT-077(P0) 统一命令设计+场景A/C/F, AUDIT-078(P0) 场景B半途接入(/init探索+阶段推断), AUDIT-079(P0) 场景D/E会话恢复+异常恢复, AUDIT-080(P1) snapshot格式升级, AUDIT-081(P1) governance-init/status/gate/verify/update 统一路由** | **`/software-project-governance` 一个命令覆盖全部6场景** |
| **0.9.0** | **已发布** | **2026-05-01** | **Agent Team 基础架构——Coordinator + 3 核心角色 + Task-Gate 模型** | **AUDIT-052(P0) 架构设计, AUDIT-053(P0) Coordinator, AUDIT-054(P0) Developer, AUDIT-055(P0) Reviewer, AUDIT-056(P0) Architect, AUDIT-057(P0) Task-Gate 数据结构, AUDIT-058(P0) Agent 通信协议** | **4角色Agent Team + Task-Gate plan-tracker改造 + Agent间通信协议** |
| **0.10.0** | **已发布** | **2026-05-01** | **Agent Team 全角色 + 六层架构设计 + 统一治理命令 + 入口瘦身 + core/infra 目录建立** | **8 角色 Agent SKILL✅, 统一命令 6 场景✅, SKILL.md 瘦身✅, behavior-protocol.md 独立✅, core/ 7 文件迁移✅, infra/ 4 文件迁移✅, 全仓路径更新✅, 环境依赖移除✅, 六层架构文档✅** | **AUDIT-082 Phase 1+2 完成。未完成项（AUDIT-068~071）降级到 0.11.0** |
| **0.11.0** | **已发布** | **2026-05-01** | **审查防护全覆盖 + 架构闭环 + 方法论路由** | **AUDIT-083(P0) 5 审查 SKILL✅, AUDIT-084(P0) Release 拆分✅, AUDIT-085(P1) 审查命令✅, AUDIT-086(P1) hook 行为检测✅, AUDIT-068(P1) 方法论路由✅, AUDIT-069(P1) 提示词工程✅** | **11 阶段 100% 审查覆盖 + 系统级 review 检测 + 12/12 交付清单** |
| **0.12.0** | **已发布** | **2026-05-01** | **产品-项目物理分离——用户插件清洁** | **AUDIT-088(P0) 39文件迁入 project/, references/净化至7文件, governance-cleanup 命令, 版本 bump** | **根目录只剩用户产品文件** |
| **0.13.0** | **进行中** | **2026-05-02** | **Agent Team 激活注入——bootstrap 模板补 M1.1** | **AUDIT-089(P0) governance-init.md 模板+Agent Team身份, SKILL.md更新, 版本 bump** | **每次会话自动激活 Coordinator** |
| **0.28.0** | **已发布** | **2026-05-04** | **用户入口精简——bootstrap 减半 + 轻量路径** | **FIX-030(P0) 三级差异化 bootstrap, FIX-033(P1) bootstrap/governance 职责边界重定义, FIX-035(P1) 简单操作快速通道** | **lightweight ~80行 bootstrap, standard ~212行, strict +30行** |
| **0.29.0** | **已发布** | **2026-05-04** | **系统级强制——pre-commit BLOCK + 审查覆盖率检查 + Profile 一致性校验 + 路由表补全** | **FIX-036(P0) pre-commit BLOCK, FIX-037(P0) 审查覆盖率检查, FIX-038(P0) Profile 代码级强制, FIX-043(P0) 路由表补全 16→18行** | **审查覆盖率量化检查 + Profile 一致性自动校验 + pre-commit 真阻断** |
| **0.30.0** | **已发布** | **2026-05-04** | **用户入口统一 + Hook 架构修复——8 项 P0/P1 全部交付** | **FIX-044~048(P0+P1) 3-hook 架构修复, FIX-049~051(P0) 用户入口统一 + Coordinator 激活 + 全路径引导** | **用户只需 /governance 一条命令，3-hook 端到端验证通过** |
| **0.31.0** | **已发布** | **2026-05-05** | **收尾打磨——P2 内部归档 + 体验打磨 + 版本 bump 自动化 + 外部验证 + 验证驱动修复** | **FIX-031/032/034(P2) 内部归档✅, FIX-039~042(P2) 体验打磨✅, AUDIT-087 Ph3(P2) E2E 验证 静态2/6✅, FIX-052(P1) 版本 bump 自动化✅, FIX-053(P0) cleanup 边界✅, FIX-054(P1) Check 10 误报✅, FIX-055(P2) commit-msg hook✅** | **3 FIX 验证驱动修复 + E2E 静态验证完成** |
| **0.32.0** | **已发布** | **2026-05-08** | **Agent 调度可靠性——并发控制 + 清洁度治理** | **FIX-056(P0) Agent 意外并发防护——锁机制+post-commit锁清理+Check 25+check-locks子命令, FIX-057(P1) 项目清洁度治理——未跟踪文件分类归档+.gitignore+Check 24+pre-commit Step 10** | **Agent 并发防护 + 仓库清洁度系统级防护** |
| **1.0.0** | **预留** | **—** | **首次正式发布标签——不承载修改，仅当所有 0.32.0 任务完成 + 外部验证通过后打 tag** | **—** | **纯版本标签——production-ready 声明** |

### 版本 Gate（V-Gate）

每个版本发布前，除对应阶段 Gate（G9）外，额外检查：

| 检查项 | 判定标准 | 适用版本 |
|--------|---------|---------|
| 版本范围完成率 | 该版本规划的 tasks ≥90% 已完成 | ≥0.5.0 |
| Breaking Change 文档化 | 如有 breaking change，VERSIONING.md + CHANGELOG + 迁移指南齐全 | 所有版本 |
| 版本号一致性 | 5 个声明文件版本号一致 + verify_workflow.py PASSED | 所有版本 |
| 未完成项处置 | 版本范围内未完成的任务已显式降级或移至下一版本 | 所有版本 |
| 用户文档更新 | README/CHANGELOG 反映本版本变更 | ≥0.5.0 |
| 外部验证 | ≥1 个外部项目验证通过（或显式声明"本版本跳过外部验证"） | ≥1.0.0 |

### 版本规划纪律

#### 版本号分配规则

1. **已预留版本号不可占用**：版本路线图中已规划的版本号（如 0.7.0）已被预留——不得用其他内容发布该版本号。违反 = 版本路线图失效。
2. **计划外变更使用 PATCH**：不在当前 MINOR 范围内的紧急变更 → bump PATCH（如 0.6.9→0.6.10），不占用下一 MINOR 版本号。
3. **版本号 bump 前 MUST 检查路线图**：bump 到 X.Y.Z 之前，确认该版本号未被预留，或 bump 内容与预留内容一致。如果路线图中该版本已有任务列表但当前变更不在其中 → MUST bump 为不同的版本号。
4. **PATCH 版本事后追加**：PATCH 版本不要求预先在路线图中规划，但发布后 MUST 追加到路线图（版本号 + 状态 + 核心范围简述）。

#### 版本内容一致性规则

5. **发布内容 MUST 匹配路线图**：版本发布时的实际内容与路线图中该版本的"包含任务"必须一致。如果不一致 → 先更新路线图（记录 decision-log），再发布。
6. **版本范围变更 MUST 记录 decision-log**：什么任务被移入/移出，为什么，对后续版本的影响。
7. **90% 完成率**：版本范围内 ≥90% 的 task 已完成才能发布。未完成的 10% MUST 显式降级或移至下一版本。
8. **路线图实时更新**：版本发布后 MUST 立即更新路线图（状态→已发布 + 日期），下一版本范围重新确认。

#### 违规示例（来自实际教训）

| 违规 | 正确做法 |
|------|---------|
| 0.7.0 被预留给 10 个外部验证任务，但被 CONSTRAINT-001 占用 | CONSTRAINT-001 应 bump 到 0.6.10。0.7.0 继续保留给原计划 |
| 版本 bump 时只看 semver 规则，不查路线图 | bump 前 MUST `grep` 路线图中目标版本号的预留情况 |
| PATCH 发布后路线图无记录 | PATCH 发布后追加到路线图——哪怕是单行记录 |

### 版本里程碑

里程碑是版本内部的时间锚点——Gates 是阶段转换检查，里程碑是"在 X 日期前完成 Y"的承诺。

| 里程碑 | 目标日期 | 包含版本 | 判定标准 | 状态 |
|--------|---------|---------|---------|------|
| M1: 防跑偏基础完成 | 2026-04-26 | 0.4.0 | Layer 0-A/B/C 全部任务完成 + check-governance 9 checks 就位 | ✅ 已完成 |
| M2: 内容深度基线 | 2026-04-28 | 0.6.0 | Layer 0-D + 2-A + 2-B(部分) 完成 + 用户体验断层闭环 | ✅ 已完成 |
| M3: 外部验证通过 | 2026-05-04 | 0.7.0 | ≥1 个外部项目走通全链路 + 体验问题清单 | 待到达 |
| M4: 全自动化就绪 | 2026-05-18 | 0.10.0 | CI + headless runner + MCP server + git hook 全部可运行 | 待到达 |
| M5: 1.0.0 正式发布 | 2026-06-01 | 1.0.0 | 全部 P0/P1 关闭 + 外部验证报告 + 用户文档完整 | 待到达 |

**里程碑纪律**：
- 里程碑到期时 MUST 执行检查——达成/延期/重新规划
- 延期 MUST 记录到 decision-log 并更新版本路线图
- 连续 2 个里程碑延期 → 触发版本范围重评估

## 需求跟踪矩阵

需求跟踪回答"这个任务服务于哪个用户需求"——从立项的 PR/FAQ 到开发的 task 到测试的验证，全程可追溯。

| 需求ID | 需求描述 | 来源 | 优先级 | 关联任务 | 当前状态 | 验证方式 |
|--------|---------|------|--------|---------|---------|---------|
| REQ-001 | 用户安装插件后 agent 自动执行项目治理 | PR/FAQ: "用户不需要手动管理流程" | P0 | INIT-001, PLAN-001~004, DESIGN-001~005, MAINT-021~022 | ✅ 已交付 | check-governance PASSED |
| REQ-002 | 用户能在 5 分钟内完成初始化 | PR/FAQ: "新用户立即可用" | P0 | MAINT-012, AUDIT-003, FIX-001 | ⚠️ 部分 | 外部验证 (AUDIT-003 待执行) |
| REQ-003 | 工作流不被 agent 跳过或忽略 | PR/FAQ: "自动看护不依赖 agent 自觉" | P0 | AUDIT-043, AUDIT-044, FIX-002 | ✅ 已交付 | SELF-CHECK + 脱轨检测 + check-governance |
| REQ-004 | 用户能按项目规模选择治理强度 | PR/FAQ: "小项目不用全套流程" | P1 | AUDIT-018, FIX-004 | ✅ 已交付 | governance-init Step 0 交互式选择 |
| REQ-005 | 用户思考流不被无意义确认打断 | PR/FAQ: "不打断用户" | P1 | FIX-004 | ✅ 已交付 | maximum-autonomy 模式 |
| REQ-006 | 版本规划先于执行——知道何时交付什么 | 用户反馈 (2026-04-28) | P0 | FIX-005 | ✅ 已交付 | 版本路线图 + V-Gate |
| REQ-007 | 临时任务能按优先级纳入版本 | 用户反馈 (2026-04-28) | P0 | FIX-006 | 🔧 进行中 | 变更控制流程 |
| REQ-008 | 企业实践不只是文档——有模板和强制力 | 用户反馈 (2026-04-28) | P0 | FIX-006 | ✅ 已交付 | PR/FAQ 模板 + OKR 模板 + 6-Pager 模板 |
| REQ-009 | M5 AskUserQuestion 不被绕过——系统级源头防污染 | 用户反馈 (2026-04-30) | P0 | FIX-015 | ✅ 已交付 | SKILL.md M2.3 交互信号 + verify_workflow.py Check 10 + 轻量 profile M5 规则 |
| REQ-010 | Coordinator Agent——用户交互+任务分解+Agent 路由+治理看护 | AUDIT-052 | P0 | AUDIT-053 | ✅ 已完成 | 0.10.0 |
| REQ-011 | Developer Agent——TDD 编码+自动化门禁+M7.4 协议 | AUDIT-052 | P0 | AUDIT-054 | ✅ 已完成 | 0.10.0 |
| REQ-012 | Reviewer Agent——独立代码审查+安全检查+AI 专项检查 | AUDIT-052 | P0 | AUDIT-055 | ✅ 已完成 | 0.10.0 |
| REQ-013 | Architect Agent——技术选型+系统设计+ADR+技术评审 | AUDIT-052 | P0 | AUDIT-056 | ✅ 已完成 | 0.10.0 |
| REQ-014 | Task-Gate 模型——plan-tracker 数据结构改造 | AUDIT-052 | P0 | AUDIT-057 | 📋 降级到 1.0.0 | — |
| REQ-015 | Agent 间通信协议——Coordinator↔Role Agent 输入/输出契约 | AUDIT-052 | P0 | AUDIT-058 | ✅ 已完成 | 0.10.0 |
| REQ-016 | main-workflow.md 重写——串行路由到 Agent Team 路由 | AUDIT-052 | P1 | AUDIT-059 | 📋 降级到 1.0.0 | — |
| REQ-017 | stage-gates.md 重写——Phase-Gate 到 Task-Gate | AUDIT-052 | P1 | AUDIT-060 | 📋 降级到 1.0.0 | — |
| REQ-018 | verify_workflow.py 升级——支持 Agent Team 结构验证 | AUDIT-052 | P1 | AUDIT-061 | 📋 降级到 1.0.0 | — |
| REQ-019 | e2e-test-project 更新——Agent Team 模式全链路 | AUDIT-052 | P1 | AUDIT-062 | 📋 降级到 1.0.0 | — |
| REQ-020 | QA Agent——测试设计+集成/性能/安全测试 | AUDIT-052 | P1 | AUDIT-063 | ✅ 已完成 | 0.10.0 |
| REQ-021 | DevOps Agent——CI/CD 配置+环境管理 | AUDIT-052 | P1 | AUDIT-064 | ✅ 已完成 | 0.10.0 |
| REQ-022 | Analyst Agent——需求澄清+调研+竞品分析 | AUDIT-052 | P1 | AUDIT-065 | ✅ 已完成 | 0.10.0 |
| REQ-023 | Release Agent——发布管理+版本规划+回滚 | AUDIT-052 | P1 | AUDIT-066 | ✅ 已完成 | 0.10.0 |
| REQ-024 | Maintenance Agent——缺陷修复+复盘+规则演进 | AUDIT-052 | P2 | AUDIT-067 | ✅ 已完成 | 0.10.0 |
| REQ-025 | 方法论智能路由集成——PUA 味道→角色 Agent 自动匹配 | AUDIT-052 | P1 | AUDIT-068 | 📋 0.11.0 | AUDIT-082 Phase 4 |
| REQ-026 | Agent 角色提示词工程——每个角色提示词独立调优 | AUDIT-052 | P1 | AUDIT-069 | 📋 0.11.0 | AUDIT-082 Phase 4 |
| REQ-027 | 治理模型完整迁移——risk/decision/evidence 任务级粒度 | AUDIT-052 | P1 | AUDIT-070 | 📋 降级到 1.0.0 | — |
| REQ-028 | profiles.md 重写——profile 定义角色 Agent 启用范围 | AUDIT-052 | P2 | AUDIT-071 | 📋 降级到 1.0.0 | — |
| REQ-029 | 外部项目验证——≥2 个外部项目用 Agent Team 走通 | AUDIT-052 (2026-04-30) | P0 | AUDIT-072 | 📋 待启动 | 1.0.0 交付 |
| REQ-030 | 迁移指南——从旧串行模型到 Agent Team 的用户升级文档 | AUDIT-052 (2026-04-30) | P0 | AUDIT-073 | 📋 待启动 | 1.0.0 交付 |
| REQ-031 | 旧模型废弃通知——Phase-Gate deprecated + v2.0 移除时间线 | AUDIT-052 (2026-04-30) | P1 | AUDIT-074 | 📋 待启动 | 1.0.0 交付 |
| REQ-032 | 用户文档完整——README + 快速开始 + 角色配置指南 | AUDIT-052 (2026-04-30) | P1 | AUDIT-075 | 📋 待启动 | 1.0.0 交付 |
| REQ-033 | 全套 E2E 测试——Agent Team 所有角色+所有场景验证脚本 | AUDIT-052 (2026-04-30) | P1 | AUDIT-076 | 📋 待启动 | 1.0.0 交付 |
| REQ-034 | 统一命令自动分类——检测项目状态并路由到正确的初始化/升级/恢复/状态场景 | 用户反馈 (2026-04-30) | P0 | AUDIT-077 | 📋 待启动 | 0.10.0: 场景A/C/F, 0.10.0: 场景B/D/E |
| REQ-035 | 全新项目一键初始化——替代 governance-init 的碎片化 Q&A，单面板收集所有参数 | 用户反馈 (2026-04-30) | P0 | AUDIT-077 | 📋 待启动 | 0.10.0 场景A |
| REQ-036 | 工作流升级自动化——检测版本差距→提取CHANGELOG→自动升级bootstrap+补全plan-tracker结构→输出升级摘要 | 用户反馈 (2026-04-30) | P0 | AUDIT-077 | 📋 待启动 | 0.10.0 场景C |
| REQ-037 | 半途接入——借助 Claude /init 探索项目→推断当前阶段→映射到治理生命周期→创建onboarding记录 | 用户反馈 (2026-04-30) | P0 | AUDIT-078 | 📋 待启动 | 0.10.0 场景B |
| REQ-038 | 会话恢复——从 session-snapshot.md 恢复 carry-over 任务/待确认决策/活跃风险→展示"欢迎回来"面板 | 用户反馈 (2026-04-30) | P0 | AUDIT-078 | 📋 待启动 | 0.10.0 场景D |
| REQ-039 | 异常恢复——诊断 hooks 缺失/plan-tracker 损坏/证据缺口→分类严重级别→提供一键修复 | 用户反馈 (2026-04-30) | P0 | AUDIT-078 | 📋 待启动 | 0.10.0 场景E |
| REQ-040 | Snapshot 格式升级 | 用户反馈 | P1 | AUDIT-078 | ✅ | 0.9.0 |
| REQ-041 | 主 SKILL.md 瘦身为入口 | AUDIT-082 | P0 | AUDIT-082 | ✅ 已完成 | Phase 1 (0.10.0) |
| REQ-042 | 统一 SKILL 库目录结构——skills/{category}/{name}/SKILL.md | AUDIT-082 | P0 | AUDIT-082 | 📋 待实施 | Phase 3 (0.11.0) |
| REQ-043 | 统一 SKILL 格式——所有 SKILL 相同 frontmatter+触发条件+执行流程+步骤清单 | AUDIT-082 | P0 | AUDIT-082 | 📋 待实施 | Phase 3 (0.11.0) |
| REQ-044 | 迁移 stages/ 和 commands/ 到统一的 skills/ 目录 | AUDIT-082 | P0 | AUDIT-082 | 📋 待实施 | Phase 3 (0.11.0) |
| REQ-045 | 分离核心层——创建 core/ 目录 | AUDIT-082 | P0 | AUDIT-082 | ✅ 已完成 | Phase 2 (0.10.0) |
| REQ-046 | 建立基础设施层——infra/hooks/ | AUDIT-082 | P0 | AUDIT-082 | ✅ 已完成 | Phase 2 (0.10.0) |
| REQ-047 | Agent↔SKILL 绑定——每个 Agent 声明可调用的 SKILL | AUDIT-082 | P1 | AUDIT-082 | 📋 待实施 | Phase 4 (0.11.0) |
| REQ-048 | SKILL 分类索引 | AUDIT-082 | P1 | AUDIT-082 | 📋 待实施 | Phase 4 (0.11.0) |
| REQ-049 | references/ 清理——核心层已移出 | AUDIT-082 | P1 | AUDIT-082 | ✅ 已完成 | Phase 2 (0.10.0) |
| REQ-050 | 统一工具/MCP 库索引——infra/TOOLS.md 升级 | AUDIT-082 | P2 | AUDIT-082 | 📋 待实施 | Phase 5 (0.11.0) |
| REQ-051 | verify_workflow.py 适配新目录结构 | AUDIT-082 | P2 | AUDIT-082 | ✅ 已完成 | Phase 2 (0.10.0) |
| REQ-052 | 适配层正式纳入六层架构——adapter 标准字段+新增平台流程 | AUDIT-082 | P0 | AUDIT-082 | ✅ 已完成 | Phase 1 (0.10.0) |
| REQ-053 | adapter 标准字段校验——verify_workflow.py 检查 adapter-manifest.json 完整性 | AUDIT-082 | P2 | AUDIT-082 | 📋 待实施 | Phase 5 (0.11.0) |
| REQ-054 | 审查防护全覆盖——11 阶段 100% 有独立审查 SKILL | 全维度审计 (2026-05-01) | P0 | AUDIT-083 | 📋 待实施 | 0.11.0 |
| REQ-055 | Agent 职责单一性——Release 不承担运营 | 全维度审计 (2026-05-01) | P0 | AUDIT-084 | 📋 待实施 | 0.11.0 |
| REQ-056 | 审查触发命令——用户可主动调用 `/governance-review` | 全维度审计 (2026-05-01) | P1 | AUDIT-085 | 📋 待实施 | 0.11.0 |
| REQ-057 | 系统级 review 证据检查——pre-commit hook 行为层检测 | 全维度审计 (2026-05-01) | P1 | AUDIT-086 | 📋 待实施 | 0.11.0 |
| REQ-058 | 命令端到端验证——e2e-test-project 全命令走通 | 全维度审计 (2026-05-01) | P2 | AUDIT-087 | 📋 待实施 | 1.0.0 |

**需求跟踪纪律**：
- 每个 P0 任务 MUST 关联到至少 1 条需求
- 需求状态变更（交付/延期/取消）MUST 更新跟踪矩阵
- 无关联需求的任务 = 范围漂移，MUST 在 decision-log 中记录

## 变更控制（临时任务纳入机制）

临时任务（emergent work）——用户反馈、审计发现、线上问题——必须经过 triage 才能进入执行。

### 纳入流程（两条路径）

#### 标准路径（计划性变更）

适用：计划内任务、跨版本大变更、需要版本协调的工作。

```
变更提出 → 优先级判定 → 版本适配 → 冲突检查 → 创建 task → 更新路线图
```

#### 快速通道（紧急/反馈驱动变更）

适用：用户即时反馈、审计发现、线上问题——**需要立刻动手**的变更。标准路径的 4 步 triage 在等待中消耗的时间比修复本身还长。

```
用户反馈/审计发现
    ↓
Step 1: 最小入账（30 秒内完成）
    - 创建 task ID（如 FIX-xxx 或 AUDIT-xxx）
    - 一句话描述
    - 标记优先级和 Gate
    - 写入 plan-tracker
    ↓
Step 2: 立即执行
    - 不需要版本适配——紧急变更默认纳入当前版本
    - 不需要冲突检查——如发现冲突在 commit 前标记
    ↓
Step 3: 事后补齐（本次 session 内）
    - 补证据到 evidence-log
    - 补版本路线图更新（如果纳入当前版本）
    ↓
Step 4: 下一 Gate 检查时正式审计
    - 快速通道的变更在下次 Gate 检查时批量审计
    - 审计维度：D1（目标一致性）+ D3（证据可信度）
```

**快速通道 vs 标准路径的判断标准**：
- 修复时间 < 1 session？→ 快速通道
- 修复不改变项目方向或架构？→ 快速通道
- 修复是用户刚刚说的话（"现在就改"）？→ 快速通道——等 triage 完用户已经忘了
- 修复涉及跨版本协调或 breaking change？→ 标准路径
- 修复需要用户确认优先级（和其他 P0 任务冲突）？→ 标准路径

### 变更控制纪律
- 临时任务 MUST 经过 triage（标准路径）或快速通道（最小入账）才能进入 plan-tracker——不得直接创建 task 开始执行
- 快速通道变更 MUST 在**本次 session 内**补齐证据和版本记录——不得跨 session
- 纳入当前版本的变更 MUST 更新版本路线图
- 被拒绝或延期的变更 MUST 记录理由到 decision-log
- 版本发布时，所有"已纳入但未完成"的变更 MUST 显式处置
- **post-commit hook 是快速通道的安全网**——如果 agent 连最小入账都忘了，hook 在 commit 后强制提醒

## 样例跟踪表

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DESIGN-002 | 设计 | 补齐 Claude 半可执行入口 | 让 Claude adapter 从说明文档升级为机器可读入口 | `adapters/claude/README.md` | `adapters/claude/adapter-manifest.json`, `adapters/claude/launch.py` | Claude | 项目负责人 | 项目负责人 | 已终止 | P1 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G3 | 完成探索性验证并输出可运行样例 | `adapters/claude/adapter-manifest.json` | repo-local 入口侵入性高，不再作为默认产品主线 | 保留为 sample / fallback，不继续扩展 | 已完成历史验证，但从主线路线图降级 |
| DESIGN-003 | 设计 | 补齐 Codex 半可执行入口 | 让 Codex adapter 从说明文档升级为机器可读入口 | `adapters/codex/README.md` | `adapters/codex/adapter-manifest.json`, `adapters/codex/launch.py` | Claude | 项目负责人 | 项目负责人 | 已终止 | P1 | 2026-04-17 | 2026-04-18 | 2026-04-17 | G3 | 完成探索性验证并输出可运行样例 | `adapters/codex/adapter-manifest.json` | 缺少对 Codex 主流集成方式的系统调研 | 保留为 sample / fallback，不继续扩展 | 已完成历史验证，但不再视为默认接入方案 |
| ACCEPT-001 | 验收 | 落地 Claude 原生 skill 入口 | 让当前项目可直接通过 Claude skill 机制加载 workflow | `平台原生入口文件`, `.claude/skills/software-project-governance/SKILL.md` | 可用的 Claude skill 入口与回写后的样例记录 | Claude | 项目负责人 | 项目负责人 | 已终止 | P1 | 2026-04-18 | 2026-04-18 | 2026-04-18 | G6 | 完成 Claude repo-local 入口验证 | `平台原生入口文件` | 当前仅证明仓库内接法可运行，不足以证明产品形态正确 | 保留为 sample / fallback，不再作为默认主线 | 当前作为探索性样板保留 |
| MAINT-002 | 维护 | 补更多大厂实践映射 | 增强规则与流程的经验来源 | 当前 research 文档 | 更丰富的实践映射文档 | 项目负责人 | Claude | 项目负责人 | 已终止 | P2 | 2026-04-19 | 2026-04-25 | 2026-04-27 | G8 | 增补至少一轮公司实践案例 | — | 被 RESEARCH-002（企业经验深度补强，Google/Amazon/华为/字节 4 家企业差异化实践）和 AUDIT-024（company-practices-summary 自包含可执行摘要重写）覆盖 | 由 RESEARCH-002 + AUDIT-024 替代，MAINT-002 目标已融入后续任务 | RESEARCH-002 已完成 4 家企业实践映射，超出 MAINT-002 原始范围；AUDIT-024 将进一步升级 summary 为可执行规则 |

## 优先级重排后的新主线

以下任务承接"共同抽象基座补强 -> Claude -> Codex -> Gemini / 国内 agent CLI"的优先级顺序。此前 `OPS-001`、`MAINT-003`~`MAINT-006` 构成 V1 骨架与兼容预研资产，不等于正式 agent 适配已完成。

### 主线 A：产品内容层（愿景驱动）

实现"解放用户非思考动作"愿景的核心内容——没有可执行的子工作流和自动化能力，协议架构再好也是空架子。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 主线 B：交付架构层（已有主线）

与主线 A 并行推进，不互相阻塞但互相验证。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MAINT-007 | 维护 | Gemini / 国内 agent CLI 在强基座上的最小验证 | 等 Claude/Codex 收敛后，再进入第三优先级 | Claude/Codex 验收结论、`OPS-001`、`MAINT-003` 兼容预研 | Gemini / 国内 agent CLI 最小验证结论 | 项目负责人 | Claude | 项目负责人 | 已终止 | P3 | 2026-05-02 | 2026-05-08 | | G8 | 在强基座上验证 Gemini / 国内 agent CLI 是否可复用共同抽象 | 待补 | P3 长期搁置被挤出视线，被 MAINT-023 替代 | 由 MAINT-023 接管，改为"选最友好目标先验证"策略 | 原"等最后"策略失效，DEC-039 决定替换 |

### 实战验证：CLI 工具升级

用自身工作流管理一个真实项目，验证"内容是否有用"。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 实战验证：Plugin Marketplace 打包

将现有 workflow 资产打包为 Claude Code 和 Codex 官方插件格式，验证交付架构能否真正对接平台。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### 实战验证：SKILL.md 行为协议重构

将 SKILL.md 从参考文档范式重构为行为协议范式，解决 agent 不遵循 skill 规则的根本问题。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
### README 承诺 vs 实现 审计驱动任务（AUDIT-xxx）

以下任务基于 2026-04-24 全量审计（DEC-045），按 P0→P1→P2 排序。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-003 | 维护 | P0: 外部项目验证——e2e-test-project/ 为永久验收基准 | 验证工作流在真实用户场景。已完成：e2e-test-project 创建 + governance-init 模拟 + 任务执行→evidence→commit→hook 全链路验证。发现并修复 pre-commit Windows 兼容问题（prepare-commit-msg bridge）。EVD-125 + EVD-125 补充 | 验收报告 + 修复的 hook | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-28 | 2026-05-04 | 2026-04-29 | G11 | e2e 全链路走通 + hook 修复 + prepare-commit-msg bridge | EVD-125 | Windows pre-commit 消息传递需 prepare-commit-msg 桥接——已修复 | 路径: e2e-test-project/ | P0 闭环——首个外部项目验证完成 |
| AUDIT-008 | 维护 | P2: README 承诺措辞修正 | 基于审计结论修正 README 中过度承诺的措辞，区分"当前能做到""近期将做到""需要外部框架" | 审计报告 P0-1, P1-5 | 修正后的 README（尤其是标题、一句话说明、日常体验三个区域） | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-04-27 | 2026-04-28 | | G8 | 用户读完 README 后对"自动"的理解与当前实际能力一致；承诺 = 已验证能力 | 待补 | 当前 README 的"全自动"在用户心中建立的是 system automation 预期 | 在 AUDIT-001 语义分级完成后执行 | 先用诚实的语言描述当前能力，等 (B)/(C) 自动化实现后再升级承诺 |
| AUDIT-009 | 维护 | P2: 外部项目中途接入体验验证 | 在外部已有项目中验证 onboarding 协议的用户体验 | 审计报告 P2-2 | 验证报告：用户能否在 5 分钟内完成中途接入、是否需要补充过多信息、前置 Gate 标记是否合理 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-02 | 2026-05-06 | | G8 | 用户在 5 个问答内完成中途接入、agent 正确标记前置 Gate、下一会话 agent 正确识别当前阶段 | 待补 | 中途接入体验完全未验证 | P0 外部验证（AUDIT-003）的延伸任务 | 可与非狗粮项目验证合并执行 |
| AUDIT-012 | 维护 | P2: headless runner 可执行版（C 级自动化） | 将 MAINT-006 的 headless runner 从协议样例升级为可运行脚本，首次实现无 agent 参与的治理巡检 | MAINT-006（headless runner 样例）、shared command contract | 可执行的 headless runner 脚本，支持 dry-run/apply 模式，可被 cron/CI 调度 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-02 | 2026-05-08 | | G8 | (1) 可在无 agent 环境下运行；(2) dry-run 输出治理状态报告；(3) apply 模式自动补 evidence-log 和风险标记 | 待补 | 当前 headless runner 只是协议定义，无可执行代码 | 先实现 status 模式（只读巡检），再扩展 apply 模式（自动写回） | C 级自动化从纸面进入可运行 |
| AUDIT-013 | 维护 | P2: MCP server 最小实现（C 级自动化） | 提供 MCP server，让 external agent 可以通过 MCP 协议查询治理状态，首次验证三层架构中"外部能力层"的 MCP 路径 | shared command contract、headless runner、三层承载模型 | MCP server 最小实现，支持 status / gate / check-governance 三个 tool | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-05 | 2026-05-12 | | G8 | MCP server 可通过 MCP 协议被 agent 发现和调用；3 个 tool 返回结构化 JSON | 待补 | 外部能力层从未通过 MCP 验证过 | 先做 Python MCP server，使用 mcp 官方 SDK | C 级自动化进入 MCP 路径验证 |

### 用户视角审视驱动任务（AUDIT-015~020）

以下任务基于 2026-04-25 全量用户视角审视（本次会话），聚焦 README 承诺 vs 实现的系统性差距。与 AUDIT-001~014（README 审计驱动，2026-04-24）互补。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-019 | 维护 | P2: verify_workflow.py 通用化——从狗粮工具升级为外部项目可用 | `verify_workflow.py` 的 check-governance 子命令解析的是工作流仓库自身的 `.governance/` 记录（evidence-log、risk-log 的特定编号格式），无法直接在外部项目中使用。用户在自己的项目里运行 check-governance 将因字段格式差异而失败或产出错误结果 | 用户视角审视报告（类别 H） | check-governance 子命令支持解析外部项目的治理记录：(1) 不再硬编码 EVD-xxx/RISK-xxx/DEC-xxx 编号格式；(2) 基于字段名而非编号前缀匹配；(3) 在外部项目中测试通过 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-08 | 2026-05-14 | | G8 | (1) check-governance 在外部项目（非工作流仓库）中运行正确；(2) PASSED/FAILED 判定基于治理记录实际内容而非预期编号 | 待补 | 当前 check-governance 只能在工作流仓库自身运行——这是狗粮工具不是产品工具 | 先在 AUDIT-003 选定的外部测试项目中验证，再修代码 | CLI 工具如果只在开发仓库能用，就不是产品 |
| AUDIT-020 | 维护 | P2: 自定义 Profile YAML 解析实现 | `references/profiles.md` 第 75-101 行定义了用户在项目中通过 YAML 自定义 profile 的格式（声明阶段启用/禁用、Gate 合并规则、记录强度），但无任何代码解析此配置。用户写了自定义配置也不会生效 | 用户视角审视报告（类别 H） | 在 verify_workflow.py 或独立脚本中实现自定义 profile 解析：(1) 读取项目根目录的 profile 配置文件；(2) 根据配置调整 Gate 检查范围和强度；(3) 解析失败时有明确错误提示 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-12 | 2026-05-20 | | G8 | (1) 用户在项目中创建 profile 配置文件后，Gate 检查行为确实按配置改变；(2) 格式错误时有可读的错误提示；(3) 文档中的 YAML 样例可被解析 | 待补 | profiles.md 定义了 YAML 格式但无解析代码——用户按文档写配置但不会生效 | 先定义解析规则和 schema，再做最小实现 | P2 增强功能，不阻塞基本使用 |

### 第二轮全量审计驱动任务（AUDIT-021~027）

以下任务基于 2026-04-26 第二轮全量审计（目标→实现差距），与 AUDIT-001~020（前两轮审计）互补。本轮聚焦 3 个维度：(1) 内容深度——59 个已完成任务中有多少是"真正有用"的；(2) 证据可信度——证据能否经得起复盘；(3) 外部可用性——用户能否端到端使用。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-025 | 维护 | P2: Stage skill 质量均衡——5 个 stage skill 达到一致深度 | 5 个 stage skill 深度差异显著：code-review-standard（159 行，P0-P3 分级，4 步执行流程）远深于 release-checklist（112 行，部分步骤标记 agent 执行但需外部环境）。用户在不同阶段调用 skill 得到不一致的体验质量——code review 得到系统级评审框架，release 得到基础 checklist | 第二轮全量审计类别 B4 | (1) release-checklist 升级：增加可逆性判断矩阵、回滚验证的具体步骤模板、监控指标清单；(2) retro-meeting-template 升级：增加数据驱动复盘（量化指标 vs 目标对比表）、action item 跟踪模板；(3) 5 个 skill 的深度标准统一：≥120 行、≥4 步执行流程、≥1 个可填充模板 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-10 | 2026-05-18 | | G8 | (1) release-checklist ≥ 130 行含具体步骤模板；(2) retro-meeting-template ≥ 130 行含量化对比表；(3) 5 个 skill 全部达到统一深度标准 | 待补 | tech-review 和 code-review 是深度产品，release 和 retro 是半成品——同一产品包里质量不一致 | 先升级 release-checklist（最常用），再升级 retro-meeting-template | P2 质量均衡——不阻塞使用但影响专业感受 |


### 第三轮审计驱动任务（AUDIT-029~038）

以下任务基于 2026-04-26 第三轮全量审计（成熟企业实践 + AI 编程特殊性视角），与前两轮审计互补。本轮聚焦 3 个维度：(1) 企业实践映射——Google/Amazon/Meta/Apple/华为/字节的成熟机制在工作流中的缺失；(2) AI 编程特殊性——agent 执行可靠性、证据持久化、人-AI 交接、跨会话记忆；(3) 架构一致性——协议与实现的对齐、质量均衡。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-037 | 维护 | P2: 向后兼容性政策与废弃通知机制 | 当目录被删除（MAINT-028 删除 workflows/rules/）、路径重命名或字段更新时，已安装工作流的用户可能遇到加载错误。当前无版本升级指南、无废弃通知期、无兼容性承诺。成熟软件产品（Google Cloud/AWS）都有明确的 deprecation policy——废弃前至少一个版本的通知期 | 第三轮审计类别 架构一致性 | (1) 创建 `VERSIONING.md`：定义语义化版本规则（Major.Minor.Patch）、废弃通知期（至少一个 Minor 版本）、兼容性承诺范围；(2) manifest.md 新增"版本兼容性"章节；(3) 每次 Breaking Change 前在 CHANGELOG 中标注废弃日期和迁移指南 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-12 | 2026-05-18 | | G8 | (1) VERSIONING.md 存在且定义明确的 semver 规则和废弃期；(2) manifest.md 有兼容性声明；(3) 最近一次 Breaking Change（MAINT-028）有迁移指南 | 待补 | 用户安装了 0.1.0 → 升级到 0.2.0 时加载失败 → 卸载。没有兼容性政策 = 每次升级都是一次赌博 | 当前版本 0.1.0——在 1.0.0 之前可以有 breaking change，但必须文档化 | P2——先有产品再有政策，但不应该等到 1.0 才想这个问题 |
### 第四轮审计驱动任务（AUDIT-039~042）—— Tier 审计跳过根因闭环

以下任务基于 2026-04-26 Tier 0-C 审计被跳过的根因分析。分析发现两类问题叠加导致审计可被跳过：(1) 工作流协议漏洞——"每个 Tier 完成后执行审计"规则仅存在于 plan-tracker.md 项目特定说明中，未烘焙到 SKILL.md 的 MUST 规则体系；(2) 用户真实使用场景漏洞——插件缓存过时（落后 6 个 commits），版本号冻结在 0.1.0，无版本升级/不匹配检测/用户通知机制。

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-049 | 维护 | P2: D5 易用性审计首次执行——验证 audit-framework 6 维度全覆盖 | audit-framework 要求 D5 在"外部验证时（强制）"执行。evidence-log 中无任何 D5 审计记录。6 个审计维度只有 D1/D3/D4/D6 被实际触发过 | 深度审计（2026-04-26）| (1) 对当前工作流产品执行首次 D5 审计：安装→初始化→首次使用步骤数、错误消息可操作性、隐性知识依赖；(2) 产出 D5 审计报告→写入 evidence-log | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-04-28 | 2026-05-02 | | G8 | evidence-log 中有 D5 审计条目 | 待补 | 审计框架承诺 6 维度实际只执行了 4 个——与 Gate 只覆盖 5/11 同类 | 在 AUDIT-003 外部验证时同步执行 D5 | P2：流程完整性 |
| AUDIT-050 | 维护 | P2: M8 自检外部验证覆盖率扩展——补充 M2/M5/M7 行为层检测 | M8 的 7 个自检项中 Check 1-7 覆盖了结构层检测，但 M2 pre-loading/M5 AskUserQuestion/M7 执行连续性的遵守情况完全无外部脚本检测。M8.1 双重机制的覆盖范围只有结构层没有行为层 | 深度审计（2026-04-26）| (1) 分析 M2/M5/M7 可脚本检测的部分；(2) 对可检测项实现脚本检查；(3) 对不可检测项标注"NEEDS_HUMAN"；(4) 更新 M8.1 表格增加"检测方式"列 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-04 | 2026-05-12 | | G8 | (1) M8.1 表格新增"检测方式"列；(2) 至少新增 1 个可脚本检测的行为层检查 | 待补 | 行为层检测本质困难但至少应标注哪些是脚本强制、哪些依赖 agent 自觉——当前 M8.1 暗示全部 7 checks 同等可信 | 先做分类标注（坦诚），再做可检测实现 | P2：防护网透明性 |



### 用户反馈驱动修复任务（FIX-xxx）

| ID | 阶段 | 任务项 | 目标/预期结果 | 输入 | 输出 | Owner (DRI) | 协同角色 | Escalation | 状态 | 优先级 | 计划开始 | 计划完成 | 实际完成 | Gate | 验收标准 | 证据 | 风险/偏差 | 纠偏动作 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| REL-001 | 维护 | 发布 0.7.0——创建 git tag v0.7.0 并推送远程 | 0.7.0 全部 12 任务完成，需正式打 tag | git tag v0.7.0 + git push --tags | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-29 | 2026-04-29 | 2026-04-29 | G11 | tag 创建成功 + 远程可见 | EVD-131 | — | — | 版本路线图中 0.7.0 已标记"已发布"但无 git tag |
| FIX-004 | 维护 | 触发模式扩展——最高权限模式 + 默认操作确认模式 | 用户反馈 (2026-04-28) | governance-init Step 0 新增 Q4 + interaction-boundary 重写 + 平台原生入口文件 双维度融合 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G11 | 双维度正交融合 + 治理开关可用 | EVD-122 | 用户需要不被打断的自主模式 | — | — |
| FIX-005 | 维护 | 版本规划机制——从只有计划到计划+版本规划双轨 | 用户反馈 (2026-04-28) | plan-tracker 版本规划节 + VERSIONING.md 版本规划机制 + governance-init 模板 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G11 | 版本路线图 + V-Gate + 里程碑 | EVD-122 | 版本规划之前完全缺失 | — | — |
| AUDIT-051 | 维护 | 企业经验融合真实度审计 | 用户反馈 (2026-04-28) | 16条实践逐条对照 + 31%敷衍率 + DEC-054 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G11 | 敷衍实践补模板 + 缺失实践补机制 | EVD-122 | — | — | — |
| FIX-006 | 维护 | 补全被忽略的基础实践——需求跟踪+变更控制+里程碑 | AUDIT-051 审计发现 | 需求跟踪矩阵 + 变更控制流程 + 里程碑管理 + pr-faq/okr/6-pager 模板 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G11 | 3 项基础实践机制落地 + 3 个模板创建 | EVD-122 | — | — | — |
| FIX-007 | 维护 | 细粒度版本控制——Patch即细粒度+check-plugin-freshness+更新指引 | 用户反馈 (2026-04-28) | VERSIONING.md 重写 + check-plugin-freshness 子命令 + CHANGELOG | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G11 | Patch bump 纪律 + freshness 可用 | EVD-122 | — | — | — |
| FIX-008 | 维护 | post-commit governance hook——消除任务间治理盲区 | 5-Why 根因分析 (2026-04-28) | post-commit-hook.sh + governance-init Step 8 + 平台原生入口文件 hook 存活检测 + RISK-024 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G11 | hook 首次 commit 即检测到自身 gap | EVD-122 | 端点强制模型 vs 流式执行行为的结构性不匹配 | — | — |
| CONSTRAINT-001 | 维护 | 系统级约束架构——设计假设从"agent会遵守"翻转为"agent一定不自觉" | 本会话全部违规模式分析 | pre-commit-hook（阻断型）+ post-commit-hook（报告型）双重屏障 + governance-init Step 8 双 hook 安装 + bootstrap Hook 存活检测升级 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-29 | 2026-04-29 | 2026-04-29 | G11 | pre-commit 阻断无 task ID / task 不在 plan-tracker 的 commit | EVD-124 | agent 反复违反自设规则——自执行约束不可信 | 所有新规则 MUST 优先设计系统级强制执行方案 | P0——最高优先级 |
| FIX-014 | 维护 | 任务级防护——消灭任务间盲区（跨任务 evidence 链 + 用户插入先入账） | 用户反馈 (2026-04-29) | pre-commit Step 4.5 跨任务 evidence chain + governance-init 干活前检查升级（3→5 件事） | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-29 | 2026-04-29 | 2026-04-29 | G11 | pre-commit 检测到前序 task 无 evidence 时输出 M7.4 DEBT 警告 + 干活前检查含任务入账和跨任务检查 | 待补 | 任务间盲区——上一个 task 证据未补齐就开始下一个 | — | 纳入 0.7.0 |
| FIX-013 | 维护 | M5 AskUserQuestion 交互覆盖审计——修复 3 个缺口（risk escalation触发+deliverable review强制+阶段跳跃AskUserQuestion格式） | 用户反馈 (2026-04-29)——agent 反复使用内联文字而非 AskUserQuestion | interaction-boundary.md 升级 + SKILL.md M5.2 触发机制补全 + risk-log escalation AskUserQuestion 触发 | Claude | 项目负责人 | 项目负责人 | 已完成 | P1 | 2026-04-29 | 2026-04-29 | 2026-04-29 | G11 | 3 个缺口修复 + M5.2 8 个触发点全部有对应落地机制 | EVD-127 | M5 规则存在但 agent 反复违规——规则无强制力 | — | 0.7.0 已发布 |
| FIX-016 | 维护 | M5.1 运行时违规修复——预输出自拦截机制 | 用户反馈 (2026-04-30)——FIX-015 后 agent 仍输出"要继续吗？"内联问题 | (1) 平台原生入口文件 SELF-CHECK #4 (2) governance-init 模板同步 (3) SKILL.md M5.1 "STOP and replace" (4) 失败模式10 (5) Check 10.4 SELF-CHECK 覆盖检测 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-30 | 2026-04-30 | 2026-04-30 | G11 | Check 10: 4/4 PASSED | EVD-134 | — | 失败模式10: 对话习惯违规 |
| FIX-019 | 维护 | M5 模型方向性翻转——从"白名单触发"到"默认审查" | M5 under-use 复发 9 次后方向性根因——白名单模式导致 agent 只在命中触发点时使用 AskUserQuestion | (1) M5.2 元规则 (2) M5.4 重构为 When to SKIP (3) SELF-CHECK #5 (4) 失败模式11 第三次更新 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-30 | 2026-04-30 | 2026-05-01 | G11 | verify PASSED + 模型翻转 + SELF-CHECK #5 | EVD-139 | 6 层修复(FIX-013/015/016/017+AUDIT-053 C1+FIX-018)都在白名单模式内打转——FIX-019 是第一个跳出白名单框架的修复 | — |
| FIX-018 | 维护 | M7.4 结构修复——review移到commit之前+summary嵌入AskUserQuestion | M5 under-use 复发7次深度根因——summary与AskUserQuestion结构性竞争 | (A)summary嵌入AskUserQuestion (B)审查移到commit之前 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-30 | 2026-04-30 | 2026-04-30 | G11 | verify PASSED | EVD-137 | — | — |
| FIX-017 | 维护 | M5 under-use 修复——AskUserQuestion 触发点静默跳过 | 用户反馈 (2026-04-30)——FIX-016 完成后 agent 直接总结+停止 | (1) M7.4 新增 step 5 (2) M5.2 新增触发点 (3) 失败模式11 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-30 | 2026-04-30 | 2026-04-30 | G11 | M7.4 step 5 + M5.2 + 失败模式11 | EVD-135 | — | — |
| FIX-015 | 维护 | M5 AskUserQuestion 绕过根因修复——6 缺口系统性闭环 | 用户反馈 (2026-04-30)——实战中仍存在绕过 AskUserQuestion | (1) development/sub-workflow.md 内联问题指令修复 (2) 全子工作流 AskUserQuestion 交互标注审计 (3) 轻量 profile bootstrap 模板补 M5 规则 (4) SKILL.md M2.3 M5 交互信号 (5) verify_workflow.py 新增 Check 10 M5 反模式检测 (6) stage-gates.md 原则#10 Gate-M5 绑定 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-30 | 2026-04-30 | 2026-04-30 | G11 | 6 缺口修复 + verify_workflow.py PASSED + check-governance Check 10 PASSED | EVD-132 | FIX-013 修复了 M5 触发覆盖但未解决子工作流层面的源头污染——agent 读到 `询问用户："..."` 这样的内联指令会直接照做。M2.3 绑定规则建立：子工作流交互标注→AskUserQuestion 工具 | 版本 bump 0.7.0→0.7.1 |
| FIX-012 | 维护 | 变更控制新增快速通道——顺应紧急修复节奏，不强推全 ceremony | EVD-123审计发现（先执行后入账违规） | plan-tracker 变更控制节新增快速通道（最小入账→立即执行→事后补齐→Gate审计） | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-29 | 2026-04-29 | 2026-04-29 | G11 | 快速通道定义 + 判断标准 + post-commit hook 安全网 | EVD-123 | 工作流强制全ceremony在对抗自然的修复节奏 | 本 commit 自身就是快速通道的首次实践——先执行后入账，hook 抓到后补记录 | — |
| FIX-011 | 维护 | bootstrap 自升级——agent 检测到版本落后自动更新 平台原生入口文件 bootstrap 段 | 用户反馈 (2026-04-29) | 平台原生入口文件 Step 1 自升级逻辑 + governance-init 模板同步 + governance-update 降级为回退 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-29 | 2026-04-29 | 2026-04-29 | G11 | 用户 /plugin update → 下次会话 → bootstrap 自动替换为最新，零行动 | EVD-122 | 之前假设用户会主动运行命令——真实用户不会 | — | — |
| FIX-010 | 维护 | governance-update——老用户升级路径（只更新 bootstrap，不动 .governance/） | 用户反馈 (2026-04-28) | governance-update.md 命令 + verify_workflow.py snippet + TOOLS.md + bootstrap 版本检测提示 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-29 | 2026-04-29 | 2026-04-29 | G11 | 老用户 /plugin update 后运行此命令，bootstrap 段升级到最新，不动治理数据 | EVD-122 | 老用户 平台原生入口文件 是 init 时注入的旧版，升级后不会自动更新 | — | — |
| FIX-009 | 维护 | bootstrap 自动版本变化检测——用户更新后自动感知 | 用户反馈 (2026-04-28) | 平台原生入口文件 Step 1 版本变化检测 + plan-tracker 工作流版本字段 + governance-init 模板 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G11 | bootstrap 每次会话自动对比版本 + 输出版本跨度/CHANGELOG摘要/需采纳项/自动生效项 | EVD-122 | governance-status 需主动调用——更新后无人跑 | — | 用户更新插件→下次会话→自动感知 |
| AUDIT-077 | 架构 | 统一治理命令设计+场景A/C/F实现——`/software-project-governance` 6场景自动分类+一键入口 | 用户反馈——5命令碎片化,需统一入口 | 6场景决策树+设计文档+snapshot格式升级+旧命令路由 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-30 | 2026-05-02 | 2026-05-01 | G11 | 统一命令文件+snapshot升级+命令路由 | EVD-138+EVD-140 | — | 0.10.0 基础设施 |
| AUDIT-078 | 架构 | Scenario B 半途接入实现——项目探索+阶段推断+onboarding | 用户反馈——已有项目用户需要无缝接入 | 8步流程: B1项目探索(8维度信号矩阵) B2阶段推断(11阶段优先级匹配) B3 AskUserQuestion确认 B4-B8参数+onboarding+bootstrap+hooks | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-30 | 2026-05-02 | 2026-05-01 | G11 | 信号矩阵+阶段推断规则+差异化onboarding | EVD-140 | — | 0.10.0 用户存留关键 |
| AUDIT-079 | 架构 | Scenario D/E 会话恢复+异常恢复实现 | 用户反馈——会话中断后需无缝恢复,异常需自动诊断修复 | D1-D4+E1-E4详细实现 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-30 | 2026-05-02 | 2026-05-01 | G11 | verify PASSED | EVD-141 | — | 0.10.0 |
| AUDIT-082 | 架构 | 六层架构重构——全部 5 Phase 完成 | 用户反馈——架构混乱：主SKILL.md是500行行为协议非入口、Agent和SKILL概念混淆 | Phase 1: SKILL.md 瘦身✅ Phase 2: core/+infra/ 建立✅ Phase 3: stages/protocol/templates 迁移✅ Phase 4: Agent↔SKILL 绑定✅ Phase 5: verify+TOOLS 适配✅ + 闭环审计修复 8 问题✅ + Agent 7 职能分组✅ | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-05-01 | 2026-05-03 | 2026-05-01 | G11 | 六层架构落地：入口/适配/业务智能/能力/基础设施/核心。105 文件迁移完成，verify PASSED | EVD-145 | — | 0.11.0 架构重构 |
| AUDIT-083 | 架构 | P0: 审查防护覆盖——9 个无审查阶段补独立审查 SKILL | 全维度审计发现——11 阶段中仅 2 个（架构设计、开发）有 Reviewer 独立审查，其余 9 阶段无审查防护 | (1) 新增 5 个审查 SKILL：需求审查(stage-initiation+research)、设计审查(stage-selection+infra+architecture)、测试审查(stage-testing)、发布审查(stage-release)、复盘审查(stage-maintenance)；(2) Reviewer Agent 绑定新审查 SKILL；(3) 更新 skill-index.md | Claude | 项目负责人 | 项目负责人 | 未开始 | P0 | 2026-05-02 | 2026-05-02 | | G11 | (1) 5 个新审查 SKILL 创建；(2) Reviewer 绑定全部审查 SKILL；(3) 11 阶段 100% 有独立审查覆盖 | 待补 | Producer-Reviewer 分离只覆盖了代码和架构，9 个阶段的产出物无独立验证 | 0.11.0 |
| AUDIT-084 | 架构 | P0: Release Agent 职责拆分——运营阶段移交 | 全维度审计发现——Release Agent 同时承担发布（事件型）和运营（持续型），职责不单一 | (1) stage-operations SKILL 从 Release Agent 移除绑定；(2) 运营阶段执行移交 Coordinator 直接调度 Analyst + DevOps 协同；(3) 更新 skill-index.md | Claude | 项目负责人 | 项目负责人 | 未开始 | P0 | 2026-05-02 | 2026-05-02 | | G11 | Release Agent 只绑定 stage-release + release-checklist | 待补 | 发布是事件（切版本），运营是持续过程（监控→反馈→优化），不应由同一 Agent 承担 | 0.11.0 |
| AUDIT-085 | 架构 | P1: 新增 `/governance-review` 斜杠命令 | 全维度审计发现——用户无法通过斜杠命令直接触发独立审查 | (1) 创建 `commands/governance-review.md`；(2) 命令支持指定审查类型（code/tech/requirement/design/test/release/retro）；(3) 自动匹配 Reviewer Agent 并返回审查结论；(4) 更新 plugin.json（如需） | Claude | 项目负责人 | 项目负责人 | 未开始 | P1 | 2026-05-02 | 2026-05-03 | | G11 | 用户输入 `/governance-review code` 即可触发 Reviewer 审查 | 待补 | 当前所有审查靠 Coordinator 自动判断——用户无法主动请求审查 | 0.11.0 |
| AUDIT-086 | 架构 | P1: pre-commit hook 行为层检测——review evidence chain | 全维度审计发现——约束依赖 LLM 自觉，无系统级 review 证据检查 | (1) pre-commit hook 新增 Step：检查 commit 涉及的 task ID 是否有对应 review 证据；(2) 无可 review 证据时 WARN——提示可能缺少独立审查；(3) P0 任务无 review 证据时 BLOCK | Claude | 项目负责人 | 项目负责人 | 未开始 | P1 | 2026-05-03 | 2026-05-03 | | G11 | hook 检测到无 review 证据的 P0 commit → BLOCK | 待补 | 当前 hook 只检查 task ID 引用和 evidence chain——未检查 review 证据 | 0.11.0 |
| AUDIT-087 | 架构 | P2: 命令端到端验证——e2e-test-project 逐命令验证 | 全维度审计发现——6 个命令从未在外部项目中端到端验证 | (1) 在 e2e-test-project 中逐一运行 6 个命令；(2) 记录每个命令的实际输出 vs 预期；(3) 修复发现的问题；(4) 产出验证报告 | Claude | 项目负责人 | 项目负责人 | 未开始 | P2 | 2026-05-04 | 2026-05-05 | | G11 | 6 个命令在外部项目中全部 PASS | 待补 | 命令设计完整但未验证实际可运行性 | 1.0.0 |
| FIX-020 | 架构 | Agent 角色从 prompt 模板升级为行为约束 SKILL——消除"靠自觉"的架构缺陷 | Agent Team 首次验证暴露 | (1) agents/ 目录重构 (2) 工具权限声明 (3) 中文化 (4) verify 检测 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-05-01 | 2026-05-01 | 2026-05-01 | G11 | 9 个 Agent SKILL + 工具权限 + 中文化 | EVD-143+EVD-144 | — | 0.10.0 |，Reviewer 不修代码全靠"你痛恨修改代码"。CONSTRAINT-001 框架下 prompt 级约束已被证明不可靠。需将每个角色升级为工具权限声明+行为约束+可验证的 SKILL | (1) agents/ 目录重构为 skills/{role}/SKILL.md 格式 (2) 每个 SKILL 声明工具权限边界 (3) verify_workflow.py 新增 Agent Team 协议违规检测 (4) 更新 M1.1+M2.2b 引用新格式 | Claude | 项目负责人 | 项目负责人 | 进行中 | P0 | 2026-05-01 | 2026-05-01 | | G11 | 8 个角色 SKILL 含权限声明 + verify 检测 + 首次验证通过 | 待补 | M5 10次复发和Agent Team自觉约束是同一根因——text rules without enforcement | 0.10.0 基础设施修复 |
| AUDIT-053 | 架构 | Coordinator Agent skill 实现 | Agent Team 核心枢纽 | 角色定位+核心能力+执行流程+子任务格式+禁止事项+治理协议 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-05-01 | 2026-05-04 | 2026-05-01 | G11 | agents/coordinator.md | EVD-138 | — | 0.9.0 |
| AUDIT-054 | 架构 | Developer Agent skill 实现——开发实现者 | TDD编码+自动化门禁+完工标准 | The Algorithm+职责+输入输出契约+禁止事项+失败处理+治理协议 | Claude | 项目负责人 | 项目负责人 | 进行中 | P0 | 2026-05-01 | 2026-05-04 | | G11 | agents/developer.md | 待补 | — | 0.10.0 |
| AUDIT-055 | 架构 | Reviewer Agent skill 实现——独立审查者 | 逐行审查+AI专项检查+安全审查+设计一致性 | 4维审查+输入输出契约+审查结论(APPROVED/NEEDS_CHANGE/BLOCKED)+审查清单 | Claude | 项目负责人 | 项目负责人 | 进行中 | P0 | 2026-05-01 | 2026-05-04 | | G11 | agents/reviewer.md | 待补 | — | 0.10.0 |
| AUDIT-056 | 架构 | Architect Agent skill 实现——架构设计者 | 技术选型+系统设计+ADR+技术评审 | 4项核心方法+输入输出契约+禁止事项+完工标准+治理协议 | Claude | 项目负责人 | 项目负责人 | 进行中 | P0 | 2026-05-01 | 2026-05-04 | | G11 | agents/architect.md | 待补 | — | 0.10.0 |
| PRINCIPLE-001 | 维护 | 用户视角强制原则——所有变更必须回答"用户怎么用" | 用户反馈 (2026-04-28) | user-perspective-principle.md + governance-status Step 3.5 + SKILL.md M2.1 + 平台原生入口文件 + governance-init 模板 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-28 | 2026-04-28 | 2026-04-28 | G11 | 3 必答问题 + 6 检查清单 + 5 反模式 + 近期变更用户可达性审计 | EVD-122 | 3/4 版本对已安装用户有断点 | — | 工作流是给人用的，不是自嗨 |
| AUDIT-053 | 维护 | 全规则一致性审计修复——32项中20项已闭环,剩余12项P2归入0.10.0 | 全规则审计发现32问题 | 20/32已修复: P0 8/8, P1 5/7, P2 7/17。剩余12项(R4/D1-D7/DR1-DR3/AQ2)归入0.10.0 | Claude | 项目负责人 | 项目负责人 | 已完成 | P0 | 2026-04-30 | 2026-04-30 | 2026-04-30 | G11 | verify PASSED, 20项修复记录在EVD-136 | EVD-136 | — | 0.10.0前置质量门已通过 |
