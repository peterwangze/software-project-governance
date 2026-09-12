# Feature Flags - 0.80.0

**Version**: 0.80.0 (minor)
**Release**: 0.80.0 重构线 P1 首批（契约层 / 轻量注册 / quick-scan 两切片）+ dsh 适配层零侵入改造三连
**Date**: 2026-09-12

## Feature Flag Inventory

This release has **no runtime feature flags** — 全部变更为确定性契约层/注册表/检查器/适配层交付形态与缺陷修复（0.78.0/0.78.1/0.79.0 无 flag 先例延续）：无 rollout 门控、无灰度放量面。

涉及「行为变化」的项均带**确定性旁路或降级路径**（见 Behavior 表），不需要 flag 化：quick-scan shadow 通道为单旗标**默认旁路**且组合口径已在 R0 独立复现；Check 28v 为 advisory 级且缺真实 dsh 时显式 NOT_RUN（不虚构 PASS）；预设渲染失败只 warn 不抛出（fail-open——抛出的宿主行会拖垮整个 dsh boot）；`launch.py --install` 保留为手动/离线旁路路径。

## Behavior

| Component | Default | Notes |
|-----------|---------|-------|
| 最小契约层 L0（FEAT-021） | enabled（库面，无运行时开关） | `Finding`(frozen)/`CheckResult`/`CheckSpec` + 四端口 Protocol + `to_legacy_dict` 键集恒等（`pass`/`issues`/`details` 恰三元）；legacy tri-state `pass: None` **显式拒绝**并给出三条出路（fail-closed 构造校验，`ContractViolation` 单一异常型） |
| 轻量注册与按命令加载（FEAT-022） | enabled | `infra/registry.py`：82 命令键 + 70 CheckSpec；受控 loader **白名单**（未声明键/非白名单模块/畸形路径/缺属性/非 callable/白名单导入失败 六类 fail-closed）；导入期 join 守卫（面分歧 → `RegistryError`）。**引擎未接线**（`verify_workflow.py` 零修改）——registry 为并置事实源，非执行路径 |
| quick-scan Slice-1 检查段事实源注册表（FEAT-025） | enabled（advisory 事实源） | 70 段逐段一行（CheckID→模式政策面 + 事实源根 + 输入路径清单 + 排除原因代码）+ C3 四段逐段裁决 + 完整性守卫 fail-closed + FEAT-020 快照对账 |
| quick-scan Slice-2 编排器 + shadow 通道（FEAT-026） | enabled；shadow 为**单旗标默认旁路** | `--quick` 复用 FIX-270 product-gate 跳过机制；引擎仅 1 处惰性 import（启动 import 零增）；四态契约；shadow 通道用于新旧口径对账（真跑 chosen=45/compared=45 mismatches=0；性能实测 5.3×，quick<15s） |
| Check 28v `check-dsh-preset-compat`（FIX-309） | enabled（advisory） | 用**真实安装的 dsh 插件 Config schema** 逐行校验预设组合——不复制任何 schema（独立遮蔽实验证明：改写已安装 persona 键名后判定随之翻转）；缺真实 dsh 安装时显式 NOT_RUN |
| dsh bundle 层 `cordis.patch.yml`（FIX-310） | enabled（boot 期；bundle layer 非 HMR） | **恰一行自有 `- insert:`**，零 UPDATE、零 `!!js`、零宿主平面注册；不生效时用户可改走 `adapters/dsh/launch.py --install`（手动/离线旁路） |
| 本包宿主行 `lib/index.js`（FIX-310） | enabled（warn-only） | 唯一动作 `ensurePreset(ctx)`：渲染包内模板（三 token → 绝对路径）写入 `$DSH_HOME/.agent-presets/governance/`；`.dsh-bundle-version` 标记幂等；staging 目录 + 先删后改名（**极短替换窗口**，非「原子」——RELEASE R0 P3-7）；**任何失败只 `ctx.logger.warn` 并吞掉**（绝不从 `apply()` 抛出）；无运行时依赖（`resolveDshHome()` 内联，模块加载失败不会拖垮宿主 boot） |
| 预设载荷源（FIX-310） | enabled | `agent-presets/governance/`（模板 + `preset.yml` 两文件）；`customSkillDirs` = 渲染后的包内绝对路径（不复制 `skills/`——单源；`<plugin_root>` 即包根，核心 prose 零改动） |
| `dsh.skills` 清单字段（FIX-310 移除） | **retired** | 该字段经全量核实 dsh 核心从不读取；35 项清单 + `check_dsh_skills_manifest` 守卫扇出（`verify_workflow.py` −239 行）同步退役 |
| 架构守卫（DEC-187 机检判据的落地形态） | enabled（组合面人工/隔离验证） | 判定 = `dsh --profile <p> --dump-config` 安装前后：**既有宿主行的存在性/config/disabled 与任何宿主平面注册表内容零变化**，列表恰多一行且该行只命名本包 |

DSH upgrade path: bundle 安装则 `dsh plugin --profile <name> update` + **重启**（bundle layer 为 boot 期生效）；手动/离线路径 `git -C <plugin_root> pull && python <plugin_root>/adapters/dsh/launch.py --install`。The persona version line (v0.80.0) reaches sessions only after the preset is re-rendered (restart / `--install`); a pulled-but-not-re-rendered checkout still injects the old template. Do not claim session-level effects for unsynced installations.

## No-overclaim boundaries

本候选不创建也不证明 `v0.80.0`，且不关闭 RISK-036 / RISK-039。0.80.0 does not close RISK-036/RISK-039 (official marketplace operations and ArchGuard external validation each have independent closure criteria not yet satisfied). RISK-050（dsh 上游内部面耦合——FIX-307/308 两次事故同源）本版交付**结构性根因消除**（上游内部行 UPDATE 面 + `!!js` 自定位面退役）但**维持打开**：收口条件 = 真实环境验收 + 复评窗，**不声明关闭**。RISK-044 缓解中（本版不改变）；RISK-046 根因修复已交付维持打开至 2026-09-30 复评窗；RISK-047/048 维持观察；RISK-049 已关闭（DEC-185，非本版范围）。**真机验收面未验证**：设置页「自定义」标签/删除/打开目录三项 UI 行为、非治理预设会话不含治理技能、治理会话技能目录完整性——本候选不声明其成立。No official approval, zcode official approval, marketplace approval, curated listing, universal/full runtime support, external first-session pilot success, RISK-036/RISK-039 closure, or 1.0.0 production-ready claim is made. No official approval. No marketplace approval. No universal/full runtime support. No external first-session pilot success. No RISK-036 closure. No 1.0.0 readiness.
