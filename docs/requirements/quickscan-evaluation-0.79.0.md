# quick-scan 前移评估（0.79.0）——RISK-044 缓解承载的设计评估

- **Task**: FX-195（P2，0.79.0，设计任务——产出本评估；实现任务另行 triage，不预设 ID）
- **决策链**: DEC-177 ②（2026-09-08 M-0 复评：RISK-044 已接受→缓解中，quick-scan 前移评估随 0.79.0 立项）← DEC-169 ② ← DEC-167 ← DEC-164 ← DEC-149
- **架构位**: 已由演进文档定档——quick-scan 属应用编排层（L4），「同一批检查的选择策略」，非简化版检查逻辑（`docs/requirements/architecture-evolution-0.80.0.md` §9.3，DEC-183 采纳）
- **作者**: Architect Agent（FX-195 派发）；**日期**: 2026-09-10；**测量环境 HEAD**: `c96da1b`
- **边界声明**: 本评估零产品代码修改（仅只读命令实跑）；唯一产物即本文件；`.governance/` 零写入（治理记录由 Coordinator 承接）

---

## 0. 事实锚定（全部结论的可溯引用源）

| # | 事实源 | 位置 | 用途 |
|---|---|---|---|
| F-1 | 演进文档 §9.3（quick-scan 目标架构表态全文） | architecture-evolution-0.80.0.md L454-L462 | 语义定义的目标约束 |
| F-2 | RISK-044 行原文 | .governance/risk-log.md L41 | 风险现状与关闭条件基线 |
| F-3 | FEAT-018 性能基线（summary median 41.796s / warm 41.311s / P95 44.663s；status median 0.5215s；summary import self 仅 103.21ms） | docs/requirements/perf-baseline-0.80.0.json（git_head c443757，2026-09-10T06:25Z，serial-exclusive） | 性能对照基线 |
| F-4 | FEAT-018 容差表（serial：median_rel 0.10 / P95 0.25；parallel-observed 仅观察永不门禁） | skills/.../core/perf-tolerance.json | 复测判定口径 |
| F-5 | FEAT-020 契约快照（check_segments **count=70** + ids + titles；freeze_point.note「冻结基线含此清单」；version_status=0.79.0 未 released） | skills/.../infra/contract_matrix/snapshots.json | 检查面清单唯一事实源 |
| F-6 | FX-195 任务行原文 | .governance/plan-tracker.md L202 | 任务范围锚定 |
| F-7 | summary-only 实现（全引擎跑完再过滤输出） | verify_workflow.py L14630-L14657（`_run_full_engine_checks` L14767 起 70 段顺序内联） | 现状机制实证 |
| F-8 | FIX-270 宿主切分先例（宿主 full 25.49s→2.40s（-91%）、summary-only 2.49s；机制=`_PLUGIN_PRODUCT_CHECK_IDS` 按事实源根切分） | architecture-audit-facts-0.80.0.md §7.3 L431；现行代码 L14669-L14698（现 25 段） | 选择策略可行先例 + 宿主场景已解 |
| F-9 | bootstrap 摘要消费点（读 `Governance: {N} issues` + 首个 FAIL/WARN） | skills/.../SKILL.md L64；references/behavior-protocol.md L221 | quick 面消费分析 |
| F-10 | post-commit hook Step 4 每 commit 跑**全量** check-governance | infra/hooks/post-commit L188-L193 | full 兜底现存节律 + 缓存生产者 |
| F-11 | 当前 issues 构成（27 issues = 28o×8 + 28p×3 + 28s×2 + Check 30×7 + 31×1 + WARN 族） | architecture-audit-facts-0.80.0.md §8.2 L454（EVD-969） | quick 排除面的信息价值取舍 |
| F-12 | 编排重复面证据（print 编排 ≥3 处并排；70 段各自重复解析） | architecture-audit-facts-0.80.0.md §3.5；演进文档 §9.2（隐性成本命名） | 残差归因假设 |
| F-13 | REFACTOR-quickscan-orchestration（目标实现任务：deps = 本评估结论 + REFACTOR-light-registry；0.81.0~0.82.0，L） | architecture-evolution-0.80.0.md §10 L525；light-registry L517（deps=contract-layer，0.80.0，M） | 实现建议的时间线约束 |
| F-14 | 本评估静态复测（2026-09-10 20:00-20:10 +08:00，本机 24 条命令 ×2 采样） | 本文 §5 | 量化估算输入 |

**RISK-044 行关键原文（F-2，摘引）**：「FIX-264 实测 `--summary-only` 墙钟 31-32s，超设计 §3.1 <15s 门禁（复用同引擎=全量引擎耗时；设计「秒级」前提经真机实测不成立）」；「**2026-09-08 正式复评执行（M-0，DEC-177 ②）：已接受→缓解中**（4 样本墙钟 65.7/61.3/64.7/56.6s——3/4 超 60s 修订验收线，较 DEC-167 基线 32.8/29.6s 抬升 1.7~2×；quick-scan 前移评估随 0.79.0 立项；下次复评 = quick-scan 评估结论入档 / 0.79.0 M-8）」。

**§9.3 表态原文（F-1，全文摘引）**：「**表态：采纳顾问 Q7——quick-scan 不是简化检查逻辑，而是同一批检查的选择策略。** 承接 0.79.0 立项评估（DEC-177 ②，RISK-044 缓解分支）结论作为输入；目标架构落位：选择机制 = 变更事实 + CheckSpec.input_deps 声明 + 模式政策 → 受影响检查闭包 → **原有实现**（不改检查体）。支持 full/quick/域选择；增量考虑：文件增删改名、共享 registry 变化、全局不变量、未提交文件、未知输入（未知回退 full）。quick 输出区分：通过 / 未执行 / 缓存复用 / 无法判断（禁把"没查"报成"通过"）。hooks 可消费经验证 quick；CI/发布 full 兜底；**先 shadow 比较再改 hook 政策**。初期只做子集选择；跨进程缓存后置（缓存键 = 引擎/规则版本 + 配置 + 输入指纹）。」

**墙钟演进（六时点，全 dogfood 本机）**：31-32s（2026-08-22，DEC-149）→ 32.8/29.6s（08-26，DEC-167）→ 65.7/61.3/64.7/56.6s（09-08，DEC-177 ②，2 负载+2 空闲）→ 41.796s median（09-10 晨，FEAT-018 serial）→ **47.0/46.8s（09-10 晚，本评估实测，HEAD c96da1b）**。同一机型 3 commit 内 +12%——全量成本随检查段数与治理热文件单调增长，是 RISK-044 的病理本身。

---

## 1. 目标与非目标（Design Doc：目标）

### 1.1 问题陈述

`check-governance --summary-only` 的实现是「全引擎 70 段顺序内联跑完 + StringIO 捕获 + 输出过滤」（F-7）——摘要的「秒级」只过滤了输出，没省略任何执行。dogfood 仓库（=本插件开发仓，RISK-044 全部证据来源）每会话 bootstrap 付出全量墙钟，且随段数/热文件增长单调恶化。宿主项目用户已由 FIX-270 解除（产品自检按事实源根切分，宿主默认跳过，实测 2.40-2.49s，F-8）——**RISK-044 的受害场景是 dogfood 自身**。

### 1.2 目标

1. **G-A 语义定义**：quick 模式选哪些检查——候选策略对照 §9.3 给取舍与推荐；定义「通过/未执行/缓存复用/无法判断」四态输出契约（机器可判定）。
2. **G-B 检查范围**：70 段中 quick 面应含哪些（事实源 = FEAT-020 快照 + bootstrap 摘要消费分析）；full 兜底语义。
3. **G-C 受控复测方案**：shadow 模式设计；性能预期对照 FEAT-018 基线给量级估算；回退路径。
4. **G-D 静态复测**：候选域命令本机实跑墙钟（只读）。
5. **G-E 实现任务建议**：编排层切片位置/依赖/规模/验收要点，供 triage。
6. **G-F 风险与替代 + RISK-044 缓解路径结论**（quick 落地后的关闭条件评估）。

### 1.3 非目标

- 不实现 quick（本文件是评估，实现另行 triage）；不改任何产品代码。
- 不重开 §9.3 已锁架构位（L4 选择策略）——若本评估建议偏离，必须走 decision-log 裁决；本评估无此需要。
- 不虚承诺秒级提速（§9.4 原文约束：「接受单进程下限，不虚承诺」）。
- 不处理宿主场景性能（FIX-270 已闭环，2.40-2.49s）。

---

## 2. 语义定义（六节之一）

### 2.1 现状机制实证（为什么慢在「全量」而非「输出」）

| 消费点 | 机制 | 现状成本 |
|---|---|---|
| bootstrap 健康摘要（SKILL.md L64，F-9） | `check-governance --summary-only` → 全引擎 70 段 → 聚合 `Governance: {N} issues` + 首 FAIL/WARN | dogfood 47s（本评估实测）/ 宿主 2.49s |
| post-commit hook Step 4（F-10） | 每 commit 跑**全量** `check-governance`，grep head -12 | 同上（每 commit 一次） |
| FEAT-020 契约 harness | `--summary-only --level lightweight`（golden 样例） | 同引擎 |

FEAT-018 分解（F-3）：summary 墙钟 41.8s 中 import self 合计仅 **103.21ms（0.25%）**——成本不在导入，在 70 段逐段的执行 I/O（治理热文件反复解析 + 树扫描 + git 扫描）。这决定了 quick 的收益杠杆 = **少执行段**，而不是少导入/少打印。

### 2.2 候选策略对比

| 维度 | 方案 A：命令面白名单 | 方案 B：input_deps 声明式闭包（§9.3 目标） |
|---|---|---|
| 机制 | 按消费命令硬编码清单（bootstrap 只需 Check X/Y/Z） | 变更事实 + CheckSpec.input_deps 声明 + 模式政策 → 受影响检查闭包 → **原有实现**（§9.3 原文） |
| 选择依据 | 消费面直觉，逐命令维护 | 每段声明事实源/输入依赖，选择由策略推导 |
| 漂移风险 | 高——新段不进清单即静默漏检；清单散落代码（RISK-046「登记与实际漂移」同族病理） | 低——注册表 + 完整性守卫可机判（fail-closed：未声明段回退 full） |
| 实现前置 | 无（今天就能写） | 需 L0 契约层 + 轻注册（REFACTOR-contract-layer → light-registry，0.80.0 才开工，F-13） |
| 与 §9.3 一致性 | 形式偏离、可作过渡 | 完全一致（演进文档已表态） |
| dogfood 见效时点 | 0.80.0 早期 | 0.81.0~0.82.0（REFACTOR-quickscan-orchestration，F-13） |

**既有先例（F-8）**：`_PLUGIN_PRODUCT_CHECK_IDS`（L14669）已是一个**声明式事实源根目录表**——代码注释原文：「新增检查只需在目录中登记一行（先声明事实源，再决定归属），不得在引擎代码里硬编码编号黑名单」。它就是「按声明选择段」的最小可行形态，且已在宿主模式生产验证（-91%）。**方案 A 的「散落硬编码白名单」形态已被本仓自己的工程纪律否决**；方案 B 的完整形态要等 0.80.0 结构切片。

### 2.3 推荐：声明式事实源注册表——A 的形态承载 B 的语义，分阶段收敛

**推荐策略（一句话）**：Phase-1 用「检查段事实源注册表」（70 段逐段一行：CheckID → 模式政策面 + 事实源根 + 输入路径清单）作为 quick 选择器——它是 `_PLUGIN_PRODUCT_CHECK_IDS` 目录模式的推广（A 的低成本形态），但每行声明的「事实源根 + 输入路径」正是 CheckSpec.input_deps 的第一列字段（B 的语义）；Phase-2 REFACTOR-quickscan-orchestration 落地时，注册表平移为 CheckSpec.input_deps，选择器平移为 L4 闭包，**零语义分叉**。

分阶段收敛路径：

| 阶段 | 选择机制 | 载体 | 语义 |
|---|---|---|---|
| Phase-1（建议 0.80.0） | 注册表 + 模式政策（bootstrap/hooks）静态选择 | infra/ 独立模块 + 巨石仅接线（FEAT-019 先例，R1 棘轮安全） | B 语义的静态子集 |
| Phase-1.5（建议 0.80.0 同批或紧随） | + 输入指纹 + 段级裁决缓存（缓存键 = 引擎/规则版本 + 配置 + 输入指纹——§9.3 原文） | 同上 | 「缓存复用」态上线 |
| Phase-2（0.81.0~0.82.0，F-13 既定） | 变更事实 + input_deps → 受影响闭包（含文件增删/registry 变化/未提交/未知回退 full 全套增量语义） | L4 + CheckSpec（结构重构后） | §9.3 完整语义 |

**取舍理由**：① RISK-044 的疼痛在 dogfood 每会话，且成本单调增长（3 commit +12%）——等 Phase-2（最快 0.81.0）= 再忍 1~2 个版本的 47s+；② 注册表不是弃子代码：FEAT-020 已冻结 70 段清单（F-5），一次性入表可审查、可机判完整性，Phase-2 直接消费；③ §9.3 自己已留过渡空间（「初期只做子集选择；跨进程缓存后置」原文）——推荐只是把「后置」的缓存提前到 Phase-1.5，理由见 §4.2（纯选择在 dogfood 达不到 <15s，量级突破必须靠缓存）。

### 2.4 四态输出契约（机器可判定）

对每个 Check 段，quick 输出四态之一；**状态描述的是「我们对这段知道了什么」，与该段本身 PASS/FAIL 正交**：

| 态 | 定义（机器判定标准） | 摘出行 token |
|---|---|---|
| **通过**（passed） | 本轮实际执行该段，且 issues=0（执行但有 issues 时计入 N 并列 FAIL/WARN 计数，不占「通过」态） | `PASS` |
| **未执行**（not-run） | 选择策略（模式政策 × 注册表）将本段排除出本轮 quick 面；本轮对该段**零知识** | `NOT_RUN(排除原因代码)` |
| **缓存复用**（cache-reused） | 本轮未执行，但该段输入指纹 + 引擎/规则版本与最近一次 full 运行记录一致，复用那次裁决（含其 issues 计数） | `CACHED(裁决@full运行时间戳)` |
| **无法判断**（undetermined） | 注册表缺该段声明 / 输入指纹集合不完整 / 缓存键不匹配 / 输入未知——**回退执行该段或回退 full**（§9.3「未知回退 full」原文） | `UNDETERMINED(原因)` |

**汇总行格式（契约提案，供实现任务细化）**：

```
Governance: {N} issues (quick) | {passed} passed / {failed} failed / {not_run} not-run / {cached} cache-reused / {undet} undetermined | run `check-governance` (full) for the {not_run} not-run segments
```

**硬约束（禁「没查」报「通过」，§9.3 原文）**：
1. `N` 只累计「通过面执行段 + 缓存复用段」的 issues；**not-run/undetermined 段不得使 N 归零或减少**——若全部实质段未执行，输出 `N=unknown` 而非 `0`。
2. 四态计数必现于汇总行（机器守卫测试：无四态计数的汇总行 = 契约违规）。
3. `--fail-on-issues` 语义不变：仅对 N>0（已执行+缓存态）触发 exit 1；not-run 不触发也不豁免。
4. 默认路径字节等价：`--quick` 是新旗标，不传时输出与现状 byte-identical（`test_summary_only.py` 已有同款契约先例，F-7 注释）。

---

## 3. 检查范围（六节之二）：70 段 quick 面分类

### 3.1 分类事实源与结果

事实源 = FEAT-020 `check_segments`（count=70，F-5）× 代码已验证的产品段清单（`_PLUGIN_PRODUCT_CHECK_IDS`，现行 25 段，F-8）× 治理热文件实测（evidence-log 1,432KB / plan-tracker 288.5KB / decision-log 104.1KB）。

| 类 | 段（FEAT-020 ids） | 判据 | quick 面 |
|---|---|---|---|
| **C1 排除——插件产品自检**（25 段，代码验证 L14669-L14698） | 7, 10, 11, 12, 15, 24, 28b, 28d, 28e, 28f, 28h, 28i, 28k, 28m, 28n, 28o, 28p, 28q, 28r, 28t, 28u, 30b, 31, 33, 40 | 事实源根 = 插件包本体（manifest/投影/插件 git/ArchGuard 树扫描/注入锚点/版本资产）；宿主模式已默认跳过（FIX-270 同族） | **quick 排除**（bootstrap 对产品自检的会话级需求由 post-commit full 兜底，§3.3） |
| **C2 保留——宿主治理数据段**（约 40 段） | 1, 2, 3, 4, 5, 6, 8, 9, 13, 14, 16, 17, 18, 18b, 18c, 18d, 18e, 18f, 18g, 18h, 18i, 19, 20, 21, 22, 23, 25, 26, 27, 28, 28c, 28s, 30, 30c, 32, 34, 35, 36, 37, 38, 39 | 事实源 = `.governance/` 热文件 + 宿主 git 状态——bootstrap 健康摘要的核心目的（evidence/risk/gate/snapshot/triage/locks 会话态一致性） | **quick 保留**（但其中 18/18b/21/22/30/30c/34 等大文件解析段是残差大头，见 §5.3——Phase-1 后靠缓存态消化） |
| **C3 待判定——混合事实源**（约 5 段） | 28g（Governance Context Discovery）, 28j（Capability Context Trace）, 28l（Restricted Host Capability Context）, 29（M5 Runtime Triggers）, 及实现期新发现的混合段 | 事实源同时触及插件面与宿主面，本评估未逐段核验代码 | **默认保留 quick 面**（fail-safe to more checks）+ 实现任务逐段入表时裁决（§6 Slice 1 验收项） |

**quick 面规模结论**：70 段中 quick 首期面 ≈ **40~45 段保留 / 25 段排除（代码已验证）/ ≤5 段待判定默认保留**。精确到段的最终清单 = Slice 1 的注册表交付物（本评估不给未经代码核验的逐段断言）。

### 3.2 bootstrap 摘要消费分析（信息价值取舍，诚实披露）

EVD-969（F-11）：当前 27 issues 中 **28o×8 + 28p×3 + 31×1 = 12 个来自 C1 排除段**（28s×2 + Check 30×7 + WARN 族来自保留段）。quick 排除 C1 后，会话开始可见 issues 从 ~27 降为 ~15——**这是 quick 的既有代价，不是缺陷**：① 28o advisory 族是稳态基线（arch 棘轮 FEAT-019 已机器看护，漂移在 commit 点由 full 拦截）；② 四态契约强制披露「12 段未执行」，会话内 `/governance` 或下次 commit 即得全量；③ DEC-149 的「会话开始看见全部 issues」初衷与 47s 现实已不可兼得——DEC-177 ② 转缓解中即用户已裁决用「诚实的部分可见」换「可用的启动延迟」。（此取舍的蓝军对抗见 §8 BM-1。）

### 3.3 full 兜底语义（与 §9.3 原文对齐）

| 消费面 | 政策 | 依据 |
|---|---|---|
| CI / 发布门禁 | **恒 full**（quick 结果不作为发布证据） | §9.3「CI/发布 full 兜底」原文；check-release 门禁面（facts §9.5） |
| post-commit hook | 维持现状 full（F-10）——它同时是 quick 缓存态的**生产者**（每 commit 刷新段级裁决 + 指纹） | §4.1 缓存闭环 |
| bootstrap 会话摘要 | quick（Phase-1 起切换；shadow 验证先行） | §9.3「先 shadow 比较再改 hook 政策」 |
| hooks 其他消费（pre-commit 等） | **Phase-1/1.5 不动**；待 Phase-2 shadow 累积证据后按 §9.3 评估 | §9.3 原文「hooks 可消费**经验证** quick」 |

---

## 4. 受控复测方案（六节之三）

### 4.1 shadow 模式设计（三级递进，全部先于政策切换）

| 级 | 机制 | 验收标准（可运行判定） |
|---|---|---|
| **S-A 干跑 shadow**（零风险） | `--quick --shadow`：选择器 dry-run 输出「将执行集 + 逐段排除原因 + 逐段输入指纹」，随后照常跑 full，输出对账表：预期未执行集 vs full 实际逐段裁决 | ① 选择集 ∪ 排除集 = 70 段无遗漏无重复（对 FEAT-020 ids 机判）；② 每个排除段有注册表声明 + 原因代码；③ C3 待判定段全部落表 |
| **S-B 执行 shadow**（试点期） | quick 实际执行选择集，同会话再跑 full，逐段比对裁决 | 选择集内每段 quick 裁决 == full 裁决（同输入同码）——任何不一致 = BLOCKING（暴露隐藏输入依赖，反哺 input_deps 完整性） |
| **S-C 缓存 shadow**（Phase-1.5） | 缓存复用态 vs 同输入 fresh full 裁决，跨 N 次运行比对 | ① 不一致率 = 0（指纹碰撞即 BLOCKING）；② 命中率披露（quick 面命中缓存段数/总数）；③ 引擎/规则版本变更后全量失效自证 |

**切换门槛**：S-A + S-B 累计 ≥3 个会话或 ≥10 个 commit 零意外差异，bootstrap 模板才切 quick（§9.3「先 shadow 比较再改 hook 政策」原文的量化落地）；hook 政策维持 full 直至 Phase-2 复评。

### 4.2 性能预期（对照 FEAT-018 基线的量级估算）

| 方案 | dogfood 估算 | 依据链 |
|---|---|---|
| 现状 full（summary-only） | **47.0/46.8s**（本评估实测，HEAD c96da1b）；FEAT-018 median 41.796s（c443757） | §5 实测表 |
| **Phase-1 纯选择 quick**（排除 C1 25 段，无缓存） | **≈ 28~33s** | 47s − 已测/类比重域 ~15-16.5s（31 段 9.5~11.0s + 28o 2.4s + 28b 2.1s + 15 1.5s + 7 类比 ~1s + 其余产品段 ~0.5-1s，§5.2）；**残差 ~30s 是宿主段重复解析大文件（§5.3 归因），选择不消除它** |
| **Phase-1.5 + 输入指纹缓存** | **暖缓存 ≈ 1~5s**；冷缓存/miss 回退 Phase-1 行为（~30s）或 full | 缓存命中时仅付指纹哈希（~60 文件 × ms 级）+ 少量变更段执行；生产者 = post-commit full（F-10 每 commit 刷新）；「秒级」在这一档兑现 |
| **Phase-2 目标架构** | 秒级（按需导入 + 共享快照 + input_deps 闭包） | §9.1/§9.2/§9.3；量级由 R6 预算表量化，**不虚承诺**（§9.4 原文） |

**判定口径**：Phase 间对比沿用 FEAT-018 容差（F-4：serial median_rel ≤0.10 / P95 ≤0.25；parallel-observed 只观察不门禁）；quick 验收目标分档——Phase-1：维持修订验收线「单次 <60s 且每会话仅一次」（DEC-149）为 PASS 下限，恢复 §3.1 <15s 原门禁为 STRETCH（大概率未达，如实披露）；Phase-1.5：<15s 为 PASS（暖缓存 <5s 为 STRETCH）；Phase-2：R6 预算表。

### 4.3 回退路径（全部可逆，ADR 可逆性标注：可逆）

1. **旗标回退**：quick 是显式旗标/模板参数——bootstrap 模板改回一行即恢复 full（无引擎内部改动）。
2. **缓存回退**：删除缓存文件即全量重建（缓存只加速、不承载语义）；缓存中毒处置 = 删文件 + 重跑 full（S-C 验收保证中毒可检测）。
3. **过渡模块回退**：Phase-1/1.5 载体为 infra/ 独立模块 + 巨石仅接线（FEAT-019 先例：主文件 +18 行）——删除模块 + 接线行即回到现状，R1 棘轮（24,302 锚）不受结构性冲击。
4. **政策回退**：hook/bootstrap 消费政策各自独立开关；CI/发布恒 full 不存在回退面。

---

## 5. 静态环境复测（六节之四）：本机实测

**口径**：2026-09-10 20:00-20:10 +08:00；Python 3.14.3（与 FEAT-018 同机同版本）；cwd = 仓库根；HEAD `c96da1b`；每命令连续 2 采样（run1/run2，均为 OS 文件缓存后的暖态；run1 为该命令本会话首次）；`python -B`（禁字节码写，AUDIT-151 测量安全变体）；全部只读检查命令，零写入。**负载披露**：采样期本会话串行执行，但并行治理负载协变量未强制排除（RISK-048 口径）——数值按 serial-adjacent 观察，未过容差门禁。

### 5.1 实测表（24 条命令；完整命令形态 = `python -B skills/software-project-governance/infra/verify_workflow.py <子命令>`）

| 子命令（Check 段映射） | run1 (s) | run2 (s) | 边际成本估算（扣除 ~0.29s 解释器+导入底座*） |
|---|---|---|---|
| `status`（轻入口参照） | 0.543 | 0.555 | ~0.25 |
| `check-loop-runtime-claims`（**31**） | **10.950** | **9.490** | **~9.2-10.7** |
| `check-architecture-health`（28o） | 2.402 | 2.413 | ~2.1 |
| `check-projection-sync`（28b） | 2.052 | 2.061 | ~1.75 |
| `check-commit-scope`（15） | 1.473 | 1.526 | ~1.2 |
| `check-cross-references`（12） | 0.513 | 0.507 | ~0.2 |
| `check-review-debt`（21） | 0.422 | 0.418 | ~0.12 |
| `check-dsh-preset-smoke`（28u） | 0.427 | 0.437 | ~0.13 |
| `check-manifest-consistency`（11） | 0.439 | 0.440 | ~0.14 |
| `check-agent-team`（19/20 面） | 0.380 | 0.387 | ~0.09 |
| `check-duplicate-code`（28p） | 0.390 | 0.355 | ~0.07 |
| `check-sequential-ids`（13） | 0.380 | 0.370 | ~0.08 |
| `check-user-impact`（17） | 0.368 | 0.397 | ~0.09 |
| `check-archive-integrity`（27） | 0.361 | 0.358 | ~0.07 |
| `check-goal-alignment`（16） | 0.342 | 0.346 | ~0.05 |
| `check-structural-validity`（14） | 0.337 | 0.342 | ~0.05 |
| `check-version-consistency`（24） | 0.347 | 0.351 | ~0.05 |
| `check-plugin-freshness` | 0.312 | 0.302 | ~0.02 |
| `check-technical-debt`（28q） | 0.287 | 0.290 | ~0.00 |
| `check-complexity`（28r） | 0.288 | 0.284 | ~0.00 |
| `check-locks`（26） | 0.300 | 0.301 | ~0.01 |
| `check-governance-data-size`（28s） | 0.296 | 0.302 | ~0.01 |
| `check-injection-contract`（33） | 0.293 | 0.296 | ~0.00 |
| **`check-governance --summary-only`（全量 70 段）** | **47.026** | **46.776** | — |

\* 底座锚点 = 全表最廉价三条（28q/28r/33 ≈ 0.287-0.296s），与 FEAT-018 status 分解（import self 101.9ms + 解释器/业务残余）量级自洽。

### 5.2 可归因成本（measured + analogous）

已测重域边际合计 **≈ 14.5-16.0s**（31：9.2-10.7；28o：2.1；28b：1.75；15：1.2；12：0.2；轻域 ~20 条 × ~0.05）；加未测的 Check 7（commit-task traceability，与 15 同为插件 git log 全扫，类比 ~1s）与其余产品段（28d-n/28t/30b/40 等，多为廉价文件核对，类比 28p/28q/28r 实测 ~0-0.1s）→ **C1 25 段合计 ≈ 15-16.5s**。

### 5.3 残差归因（数据缺口，如实登记 + 假设链）

**47.0s − 15-16.5s ≈ 30-32s 无法用独立命令归因**（本评估不改产品代码，无法逐段插桩）。归因假设（证据链，非断言）：

1. 治理热文件实测：evidence-log.md **1,432KB**、plan-tracker.md **288.5KB**、decision-log.md **104.1KB**——C2 保留段中 18/18b（事实 grounding/结构化证据扫 evidence-log）、21/22（review 债/覆盖）、30/30c（review 闭环/机器溯源）、34（完成推荐）、18c-18i 族（plan-tracker 字段）等十余段**各自重复全文件解析/正则**，无共享快照（facts §3.5「print 编排重复面 ≥3 处并排」实证 + §9.2 将其命名为「编排现状的隐性成本」）。
2. 旁证：全部独立域命令边际成本都廉价（≤0.15s 除四大重域）——排除「单段隐藏巨石」假设；FEAT-018 import 分解 0.103s——排除导入假设。
3. **该残差正是 §9.2 共享快照 / §7.4 派生索引的目标成本，也是本评估「纯选择达不到 <15s」结论的量化依据**（§4.2）。Phase-2 切片时以此数为基线复测。

### 5.4 复现命令（验收 ③）

```powershell
# 本节全部数字的复现形态（每条 ×2 采样，取两值并列报告）
python -B skills/software-project-governance/infra/verify_workflow.py <子命令>   # 子命令取 §5.1 表第一列
Measure-Command { python -B skills/software-project-governance/infra/verify_workflow.py check-governance --summary-only *> $null }   # 全量 47.0/46.8s
```

---

## 6. 实现任务建议（六节之五）——供 triage，不预设 ID

**总原则**：载体一律 infra/ 独立模块 + 巨石仅接线（FEAT-019 先例：主文件 +18 行，R1 棘轮 24,302 锚安全）；每切片独立可回退（§4.3）；产物可被 REFACTOR-quickscan-orchestration（F-13）平移消费，零弃子。

| 切片 | 内容 | 依赖 | 规模 | 验收要点 |
|---|---|---|---|---|
| **Slice-1 检查段事实源注册表** | 70 段逐段一行（CheckID → 模式政策面 + 事实源根 + 输入路径清单 + 排除原因代码）；C3 待判定段逐段裁决落表 | 无（FEAT-020 快照已冻结 70 段 ids，F-5） | **S-M** | ① 70/70 覆盖（对 FEAT-020 ids 机判）；② 完整性守卫：新段未入表 → check 告警（fail-closed 回退 full）；③ 表 schema ⊂ CheckSpec.input_deps 字段集（Phase-2 平移性声明） |
| **Slice-2 quick 编排器 + 四态契约 + shadow 通道** | `--quick` 旗标（默认路径字节等价）；选择器消费注册表；四态汇总行 + 逐段行；`--shadow`（S-A/S-B 两级，§4.1） | Slice-1 | **M** | ① S-B：选择集裁决 == full 裁决，≥3 会话/≥10 commit 零意外；② 四态守卫测试（无计数汇总行 = 违规；not-run 不得使 N 归零）；③ 性能实测入档（对照 §4.2 Phase-1 目标 28-33s，容差按 F-4） |
| **Slice-3 段级裁决缓存**（输入指纹） | 缓存键 = 引擎/规则版本 + 配置 + 输入指纹（§9.3 原文）；生产者 = post-commit full 追加段级裁决记录；quick 消费「缓存复用」态；S-C shadow | Slice-2；与 post-commit hook 的集成点（F-10） | **M** | ① S-C：不一致率 0 + 命中率披露；② 缓存中毒负对照（篡改指纹 → 必须失效）；③ 缓存文件体积受 28s 看护（放置路径与豁免声明随 triage 裁决：`.governance/cache/` 受治理 vs 仓外 temp 不受治理） |
| **（既定）REFACTOR-quickscan-orchestration** | L4 input_deps 闭包 + hooks 政策评估（Phase-2，演进文档 §10 L525 原定） | 本评估结论 + REFACTOR-light-registry（F-13） | L（0.81.0~0.82.0） | 按演进文档：shadow 全量对照报告 + quick 四态输出（§9.3）；**平移 Slice-1 注册表为 CheckSpec.input_deps、Slice-3 缓存键语义不变** |

**与 REFACTOR-light-registry 的前置关系（任务书点名问题的直接回答）**：对 Slice-1/2/3 **不是硬前置**——注册表 schema 设计为 CheckSpec 子集即可在巨石旁先行；对 REFACTOR-quickscan-orchestration **是硬前置**（演进文档 §10 已编码，F-13）。风险对冲：Slice 载体禁写入巨石编排体（只允许 dispatch 接线行），避免在重构前给 24,302 行锚增重。

**版本槽建议**：Slice-1/2/3 建议 0.80.0（与 P0/P1 重构波次并行，不触碰 0.79.0 范围内核——DEC-145 新任务新版本原则，正式入账走 change-triage）；最晚不迟于 0.81.0（与 quickscan-orchestration 的输入衔接）。

---

## 7. 风险与替代（六节之六）（Design Doc：替代方案/风险）

### 7.1 否决项（≥2，带理由）

| 否决项 | 理由 |
|---|---|
| **ALT-1 散落硬编码白名单**（quick 面按命令写死在引擎代码） | 本仓自己的工程纪律已否决——FIX-270 注释原文「不得在引擎代码里硬编码编号黑名单」（L14668）；漂移病理有实证先例（RISK-046：登记与实际 files 漂移致子 agent 空转一个波次）；70 段散落多处不可审查。被 2.3 注册表方案替代。 |
| **ALT-2 第二套轻量引擎**（quick = 简化版检查逻辑） | DEC-149 已否决（原文：「产生第二套引擎语义（子集 ≠ 全量看护完整性）、与『复用同一引擎』设计冲突、规模扩张」）；§9.3 定档「不是简化检查逻辑，而是同一批检查的选择策略」。**任何 quick 实现必须复用原有检查体**。 |
| **ALT-3 跳过过渡、直接做 input_deps 完整闭包**（把首期 quick 合并进 0.81-0.82 的 REFACTOR-quickscan-orchestration） | 依赖链最长（contract-layer → light-registry → 本体，F-13），dogfood 再忍 1~2 版本的 47s+ 且成本单调增长（3 commit +12% 实测）；注册表/缓存/影子通道无论早晚都要做，先行不产生弃子。分层推进收益/风险比更优。 |
| **ALT-4 只优化慢检查**（ targeted 优化 Check 31 等重域） | DEC-149 方案 C 已定性（超范围、不治本）；本评估量化加持：四重域仅占 15-16.5s / 47s，**残差 ~30s 在宿主段重复解析**——优化重域后仍 ~37s，负载下仍超 60s 修订线，量级不对。 |

### 7.2 风险登记（实现期风险，≥5 含回滚）

| # | 风险 | 缓解 | 回滚 |
|---|---|---|---|
| QR-1 | 注册表漂移：新段未入表 → quick 静默漏检 | 完整性守卫（未入表段默认 full + check 告警，Slice-1 验收②）；FEAT-020 harness 每次快照再生成时对账 70 段 | 删表回 full |
| QR-2 | 分类错判：C1/C2 边界段事实源判错（C3 族），quick 漏检而 full 只在 commit 点 | C3 默认保留（fail-safe to more checks）；S-B 执行 shadow 全量比对（§4.1）零意外才切政策 | 改表该行即可（单行可逆） |
| QR-3 | 缓存中毒/陈旧：指纹碰撞、mtime 粒度、引擎版本未入键 | 内容哈希（非 mtime）+ 引擎/规则版本入键（§9.3 缓存键原文）+ S-C 不一致率 0 门禁 + 中毒负对照测试 | 删缓存文件全量重建 |
| QR-4 | 四态披露被消费面吞掉（UI 只显示 N，not-run 不可见）→「没查」事实上的「通过」 | 汇总行四态计数必现 + 机器守卫测试（Slice-2 验收②）；bootstrap 模板消费契约同步修订 | 模板回 full 一行 |
| QR-5 | dogfood/宿主语义分叉：quick 策略与 FIX-270 product-gate 切分不正交（宿主 quick 遇已跳过段） | 正交性测试：宿主模式下 quick∩product-skip 段态 = NOT_RUN(原因=product-gate) 不产生第三语义 | — |
| QR-6 | 性能预期未达（Phase-1 实测 >33s 或负载下仍 >60s） | §4.2 目标分档如实披露；Phase-1.5 缓存为主要杠杆；容差口径 F-4 | 旗标回退（§4.3①） |

### 7.3 RISK-044 缓解路径结论（关闭条件评估）

**结论：quick-scan 落地 ≠ RISK-044 自动关闭；关闭条件应为一组可验证断言**（建议随 quick 实现任务的验收条款入账，下次复评按此判定）：

1. **C-1 语义就绪**：四态输出契约上线且机器守卫（禁「没查」报「通过」）通过——Slice-2 交付。
2. **C-2 等价性证明**：S-B/S-C shadow 累计 ≥3 会话或 ≥10 commit，quick 集裁决 == full 裁决、缓存不一致率 0——Slice-2/3 交付。
3. **C-3 消费切换**：bootstrap 模板消费 quick（含 not-run 披露）；CI/发布与 post-commit 维持 full。
4. **C-4 墙钟达标**：dogfood 会话启动摘要暖缓存 ≤15s（恢复 §3.1 原门禁量级；<60s 修订线为底线），FEAT-018 容差口径实测入档 ≥2 个版本周期稳定。
5. **C-5 看护移交**：全量完整性由 commit 点 full（F-10 节律）+ 棘轮/契约面（FEAT-019/020）承接，有据可查。

C-1~C-4 全满足 → RISK-044 可关（状态：缓解中 → 已关闭）；仅 C-1~C-3 满足而 C-4 未达 → 维持缓解中并按 §4.2 分档重设预期；**任一切片中止** → 回退 full（§4.3）+ RISK-044 恢复「已接受（修订线 <60s）」口径并如实登记墙钟现状。0.79.0 M-8 复评时点（risk-log 下次复评锚点）：本评估入档 = 缓解路径已立项证据，风险维持「缓解中」。

---

## 8. 蓝军挑战（≥3，独立 ID + 回应）

| ID | 挑战（如果……会怎样） | 回应与缓解 |
|---|---|---|
| **BM-1** | 如果 bootstrap 摘要的原始目的是「会话开始看见**全部** issues」（DEC-149 初衷），而当前 27 issues 中 12 个恰来自 quick 排除段（28o×8+28p×3+31×1，F-11）——quick 化后会话开始**可见信息倒退**，摘要的存在价值被掏空？ | 承认取舍（§3.2 诚实披露）：① 12 个中 11 个为 advisory 稳态基线（28o/28p 族），会话间漂移由 commit 点 full + FEAT-019 棘轮看护；② 四态契约强制披露 12 段 NOT_RUN（不是消失，是显式未知）；③ 会话内 /governance 显式 full 随时可得。信息「延迟可见」换「启动可用」——DEC-177 ② 已裁决方向，本评估仅要求披露义务机器化（QR-4）。 |
| **BM-2** | 如果缓存复用态依赖 post-commit full 作生产者，而现实是 agent 会话常跨多 commit 未跑 full（hook 失效/--no-verify 跳过——DEC-171 有先例）、或 .governance 在会话中被直接改写——缓存陈旧，bootstrap 基于陈旧裁决行动？ | 缓存键 = **输入指纹**（内容哈希）而非时间戳：post-commit 只是「自然的刷新点」不是「唯一生产者」；指纹不匹配 = 缓存 miss = 无法判断态 → 回退执行选择集/full（§2.4 定义），**永不把陈旧当新鲜**。S-C shadow 的 0 不一致率门禁（§4.1）是上线前置。生产者缺失的降级路径 = 冷缓存行为，已定义。 |
| **BM-3** | 如果 70 段分类表本身有错（如 28g/28j/28l/29 混合事实源判错），quick 漏检该段而 full 只在 commit 时跑——两次 commit 之间的违规提交/违规治理写入在会话摘要里不可见，看护出现窗口期？ | 三重防线：① C3 待判定段**默认保留** quick 面（fail-safe to more checks，判错只损失性能不损失覆盖）；② S-B 执行 shadow 全量比对期间一切分类错判必现（full 裁决 != quick 排除假设的段会以「意外差异」暴露）；③ 窗口期本身非新增——现状 full 也只在 commit/e2e 点跑，quick 不缩小既有看护节律，只缩小摘要延迟。 |
| **BM-4** | 如果 Phase-1 纯选择只把 47s→~30s（§4.2），花 S-M 规模做一个不达 <15s 门禁的中间物，是否为「忙碌工作」？ | Phase-1 的真正交付物是**语义地基**（注册表 + 四态契约 + shadow 通道）——Phase-1.5 秒级兑现与 Phase-2 结构迁移都消费它；墙钟收益是顺带。且不做的替代（ALT-3 等结构重构）把秒级兑现推到 0.81-0.82，dogfood 在成本单调增长下（3 commit +12%）持续付费。分档验收（§4.2）保证 Phase-1 不虚报达标。 |

---

## 9. 非功能需求覆盖矩阵（Design Doc：非功能）

| 非功能需求 | 设计措施 | 承载节 |
|---|---|---|
| 性能 | 选择策略排除 C1（~15-16.5s 实测）+ 输入指纹缓存（暖 1-5s 估算）+ 目标分档验收 + FEAT-018 容差口径 | §2/§4/§5 |
| 可用性（agent/用户面） | 四态披露 + 汇总行四态计数必现 + `[SKIP]`/NOT_RUN 披露沿用（演进 §9.6 已列「quick 输出四态披露」）+ 默认路径字节等价 | §2.4 |
| 可维护性 | 注册表一行登记（FIX-270 模式原文「新增检查只需在目录中登记一行」）+ 完整性守卫（QR-1）+ schema ⊂ CheckSpec（平移性） | §2.3/§6 |
| 可测试性 | 三级 shadow harness（S-A/B/C 可运行判定）+ 四态守卫测试 + 缓存中毒负对照 + 契约 byte-identical 测试（test_summary_only.py 先例） | §4.1/§6 |
| 兼容性（Windows-first） | stdlib-only（哈希/文件枚举）；UTF-8 纪律沿用（FIX-278）；`python -B` 测量口径；不引入符号链接/软链假设 | §5/§6 |
| 安全（数据安全 P7） | 缓存只加速不承载语义（删除即重建，零治理数据损失面）；缓存文件放置与 28s 体积看护关系显式留 triage 裁决；零产品代码行为变更（Phase-1 仅为增量旗标） | §4.3/§6 |
| 可扩展性 | 模式政策维度（bootstrap/hooks/CI）与事实源声明维度正交；域选择（§9.3「full/quick/域选择」）由同一注册表支撑 | §2.3 |

---

## 10. Design Doc 结构自检与验收对照

**Design Doc 最小结构（G5 门）**：目标（§1）/ 方案（§2-§4）/ 替代方案 ≥2 含否决理由（§7.1，4 项）/ 风险含回滚（§7.2，6 项）/ 非功能覆盖（§9）——五项齐全。

**任务书验收对照**：①六节齐备（§2 语义定义 / §3 检查范围 / §4 受控复测 / §5 静态复测 / §6 实现建议 / §7 风险与替代）✓；②事实锚定（§0 引用表 + 各节原文摘引：§9.3 全文 / RISK-044 行 / FEAT-018 数字 / FEAT-020 count=70 / FX-195 行）✓；③实测数字带命令（§5.1 表 + §5.4 复现命令）✓；④Design Doc 结构（上文）✓；⑤蓝军 ≥3（§8，4 条带回应）✓；⑥零产品代码修改（本评估仅只读命令 + 本文件单产物）✓。

**硬门槛**（agents/architect.md）：候选方案 ≥2（§2.2 两策略 + §7.1 四否决）✓；蓝军 ≥3（§8）✓；关键结论可溯（§0 全引用表）✓；不写产品代码 ✓；ADR 式字段（本文件为评估文档，proposed DEC 由 Coordinator 按需入账——本评估不含架构决策变更，仅确认 §9.3 既定架构位，无需新 DEC）✓。

**开放事项（留 triage / Coordinator）**：① Slice-1/2/3 正式 ID 与版本槽（0.80.0 建议）；② 缓存文件放置路径（.governance/cache 受治理 vs 仓外）；③ C3 四段（28g/28j/28l/29）逐段事实源裁决（Slice-1 验收项）；④ bootstrap 模板消费契约的最终措辞（Slice-2 交付时与 SKILL.md L64/behavior-protocol L221 同步修订）。
