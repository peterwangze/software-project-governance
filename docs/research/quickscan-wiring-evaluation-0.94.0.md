# quick-scan 接线 summary 默认路径——立项评估 memo（RISK-044 复评义务兑现）

> 版本基线：0.93.1（已发布 2026-10-01）｜评估窗：0.94.0 立项（2026-10-31 复评窗）
> 任务：RISK-044-QUICKSCAN-EVAL（P2，0.94.0 候选池既有登记——risk-log RISK-044 行「下次复评 = 0.94 立项窗（quick-scan 接线评估入档）」）
> 性质：只读分析 + 评估结论（零代码修改；本 memo 为唯一输出工件）
> 实测环境：2026-10-02 本机（Windows，dogfood 模式——仓库根 cwd，host==plugin roots）；全部命令可复现，参数见 §2

---

## 1. 背景与劣化史

**风险主体**：RISK-044（risk-log L38）——`check-governance --summary-only` 墙钟劣化。机制根因自登记日起未变：**summary-only 复用全量引擎**（`_run_full_engine_checks`），只减输出体积不减计算量（audit-145-watchdog-design-0.76.0.md L167：「复用同引擎=全量引擎耗时」）。

| 时点 | 实测 | 判定 | 决策 |
|---|---|---|---|
| 2026-08-22（FIX-264） | 31-32s | 超 0.76.0 设计 §3.1 <15s 门 | DEC-149 接受，验收修订「单次 <60s 且每会话仅一次」；quick-scan 列 0.78.x+ 候选（DEC-164 收窄） |
| 2026-08-26（DEC-167） | 32.8s / 29.6s | 满足修订验收 | 检查点通过（维持已接受） |
| 2026-09-08（DEC-177② M-0） | 65.7/61.3/64.7/56.6s（4 样本，3/4 超线） | 较 DEC-167 基线抬升 1.7~2× | 已接受→**缓解中**；下次复评 = quick-scan 评估结论入档 |
| 2026-09-18（AUDIT-154） | 45.80s / 50.38s（本机）＋轨迹 67-85s | 劣化随 evidence-log 膨胀（时点 1.5MB） | 确认 FEAT-025/026 **已交付未接线**；切片 B（quick-scan 正式接线）立项候选 |
| 2026-09-26（DEC-246⑨ 链首预检） | 90s 超时 ×1 | 数据膨胀劣化持续 | 0.90+ 候选口径 |
| 2026-10-02（逾期升级线复评） | 62.1s（单样本） | 数据侧已收敛（evidence-log 1.78MB→474KB，−73%＝FEAT-076 三腿迁移 + 0.93.1 归档 sweep〔EVD-1291〕）但墙钟未随数据收敛 | **维持缓解中**——「残余成本在引擎侧非数据侧」；本次评估即该复评登记的义务 |

**数据侧 vs 引擎侧的收敛分叉是本评估的立项依据**：FEAT-076（0.93.0）已把 evidence-log 从 1.78MB 降到 474KB（−73%），但 summary-only 墙钟仍 62.1s——证明残余成本不在治理数据体量，而在引擎执行面（复用全量 70 段 + dogfood 模式全段运行）。quick-scan（FEAT-025 注册表 + FEAT-026 选择器/四态契约/shadow 通道）已交付但未接 summary 默认路径。

---

## 2. 现状实测归因（问题 4——墪钟构成的量化归因）

### 2.1 墙钟基线（2026-10-02 本机，dogfood，仓库根 cwd）

| # | 命令（可复现全文） | 墙钟 |
|---|---|---|
| B1/B2 | `python skills/software-project-governance/infra/verify_workflow.py check-governance --summary-only`（×2 样本） | **70.5s / 67.7s** |
| B3/B4 | `python skills/software-project-governance/infra/verify_workflow.py check-governance --quick`（×2 样本） | **10.7s / 12.1s** |
| B5 | `python skills/software-project-governance/infra/verify_workflow.py check-governance`（full 无参） | **91.4s** |
| B6 | `python -X importtime -c "import verify_workflow"`（infra/ cwd） | **0.29s** |

三个直接结论：

1. **quick 面实测 ~11s，非「秒级」**——比 summary-only（均值 ~69s）快 84%，但远超 AUDIT-154 切片 B 的 p95≤3s 目标（§5 详述口径重定）。
2. **python 启动 + 巨石（27,466 行）import 仅 0.29s，非瓶颈**——quick 的 11s 全部在检查执行面（与 AUDIT-154 §3.4「python 冷启动非瓶颈」结论一致）。
3. full（91.4s）− summary-only（68s）≈ 23s 为全量渲染开销差（print 到管道 vs StringIO 捕获）；summary-only（68s）− quick（11.4s）≈ 57s 为 quick 排除面（25 段）的真实执行成本。

> 样本口径说明：B1-B5 为连续串行采样（后台单 job 顺序执行），本会话有并发会话负载，绝对值比 2026-10-02 单样本 62.1s 偏高约 8-13%；归因分析（§2.2）用比例口径，不受绝对值漂移影响。architecture-audit-facts-0.80.0.md §9.5 先例：无统一硬件 SLA，门禁用同机交错相对容差，绝对值门仅保留已修订验收线。
>
> 〔勘误（Coordinator，2026-10-02）：原稿「实测环境」两处日期误记 2026-10-30，正确为 2026-10-02（测量日＝本 memo 产出日；上句「比 2026-10-02 单样本偏高」自证）。〕

### 2.2 分段归因（cProfile，输出落 %TEMP%、零仓库写）

方法：`python -m cProfile -o %TEMP%\qs_sum.out verify_workflow.py check-governance --summary-only`（overhead-inclusive 墙钟 158.1s，profiled 总量 156.7s）＋ `pstats` 按 cumulative 归属到各 check 函数。**按比例换算真实墙钟**（×0.434＝68s/156.7s）：

**排除面（quick 跳过的 25 段）named 大头**——profiled cum（占比）→ 真实估计：

| 段 | 函数（源码锚） | profiled | 占比 | 真实估计 |
|---|---|---|---|---|
| Check 31 | `scan_loop_runtime_claims`（loop_runtime_claims.py:3212） | **38.09s** | **24.3%** | ~16.5s |
| Check 28b | `check_projection_sync` + `check_legacy_snapshots`（projection.py:78/267） | 8.52s | 5.4% | ~3.7s |
| Check 30b | `check_loop_wiring_call_sites`（review_domain.py:3577） | 5.45s | 3.5% | ~2.4s |
| Check 28o | `check_architecture_health`（verify_workflow.py:20791） | 4.78s | 3.0% | ~2.1s |
| Check 24 | `check_version_consistency`（version.py:78） | 3.25s | 2.1% | ~1.4s |
| Check 28v | `check_dsh_preset_compat`（dsh_compat.py:1738） | 2.39s | 1.5% | ~1.0s |
| Check 15 | `check_commit_scope`（verify_workflow.py:12829） | 1.53s | 1.0% | ~0.7s |
| **排除面 named 小计** | | **~65.4s** | **41.7%** | **~28s** |

**quick 面（45 段）named 大头**：

| 段 | 函数 | profiled | 真实估计 |
|---|---|---|---|
| Check 30/30c | `check_review_closure`（review_domain.py:2274） | 4.30s | ~1.9s |
| Check 32 | `check_change_triage` + `check_triage_wiring`（triage_domain.py:242/110） | 7.43s | ~3.2s |
| Check 28j（C3 保留） | `check_capability_context`（verify_workflow.py:9329，AST 解析巨石自身） | 1.97s | ~0.9s |
| Check 36 | `check_risk_mitigation_closure_with_archive`（verify_workflow.py:15614） | 1.93s | ~0.8s |
| Check 38 | `check_ci_evidence`（ci_domain.py:321） | 1.85s | ~0.8s |
| **quick 面 named 小计** | | **~17.5s** | **~7.6s** |

未归属 ~44%（~69s profiled）＝引擎体内联扫描（Check 13/14/5/6 等无独立函数的段）＋ print/I/O 渲染＋未列小函数。

**「秒级」主张的实测依据**：quick 面（`--quick` 旗标实测可用，FEAT-026 Slice-2 已接线为手动路径）在本仓 dogfood 下为 **10.7-12.1s**，其中 named 检查函数 ~7.6s、其余为引擎内联扫描与渲染。**结论：quick ≠ 秒级（<3s），是「十秒级」（本仓 dogfood）；宿主模式参照系见 §3.3。**

### 2.3 接线现状（代码事实）

`cmd_check_governance`（verify_workflow.py:15792-15829）三分支：

```python
if args.quick or args.shadow:      # L15809 — FEAT-026 手动旗标路径（已接线）
    prepare_quick_args → capture _run_full_engine_checks → render_quick_output
elif args.summary_only:            # L15819 — bootstrap 健康摘要路径（未接 quick）
    capture _run_full_engine_checks(args)   # ← 无条件全量 70 段
    _aggregate_check_summary → _print_check_summary
else:                              # full 默认
    _run_full_engine_checks(args)
```

「未接 summary 默认路径」的确切语义：`--quick` 旗标自 0.79.0 起可用（手动），但 bootstrap 协议（SKILL.md L65）消费的 `--summary-only` 走 `elif` 分支，无条件复用全量引擎。**且 dogfood 模式下 `_product_gate_active`（L15891-15906）返回 True（host==plugin），25 段插件产品自检也全跑**——这是 dogfood 62-70s vs 宿主 ~2.5s（§3.3）的结构性差异来源。

---

## 3. 覆盖面分析（问题 1）

### 3.1 quick 子集包含哪些 check（代码事实，quickscan_registry.py 70 段逐段声明）

- **quick 面 45 段**＝全部宿主治理域段（evidence 1/4/18/18b、risk 2/8/36、gate 3、task 9、registries 13、structure 14、requirements 16/17、planning 18c/18g、protocol 5/18i/29、review 19-22/30/30c、profile 23、git 25、locks 26、archive 27、governance-data 28c/28s、context 28g、snapshot 35、release 37、ci 38、completion 39、priority 41、closure 42、triage 32、capability 28j/28l、commit-scope 外的 28 等）＋ C3 待判定四段按 fail-safe 裁决**保留**（28g 混合根宿主主导 / 28j、28l 插件面但不在 product-gate 清单 / 29 宿主 evidence 语料——C3_ADJUDICATION L651-717）。
- **排除面 25 段**≡ FIX-270 `_PLUGIN_PRODUCT_CHECK_IDS`（verify_workflow.py:15841-15871，机器对账——排除集与宿主 product-gate 正交，QR-5）：插件 git 事实源（7/15）、插件包资产（10/11/12/24/28b/28d/28e/28f/28h/28i/28k/28m/28n/28t/28u/28v/28w/33）、插件树扫描 ArchGuard 四门（28o/28p/28q/28r）＋30b、loop claim attestation（31）。排除原因代码 4 类（EXCLUSION_REASON_CODES，registry L150-163）。

### 3.2 健康语义诚实披露（子集≠全量的呈现口径）

已交付的四态契约（quickscan_selector.py §2.4）就是降级标注机制，**机判口径现成**：

- 汇总行：`Governance: {N} issues (quick) | {p} passed / {f} failed / {nr} not-run / {c} cache-reused / {u} undetermined | run check-governance (full) for the {nr} not-run segments`（`summary_line` L525-536；QR-4 机守卫 `summary_line_contract_violations` L539 强制四态计数必现——「没查」不得报「通过」）。
- NOT_RUN 逐段带注册表原因代码（PLUGIN_TREE_SCAN 等）；UNDETERMINED 触发 fail-closed 回退 full（`prepare_quick_args` L651-675：注册表守卫不可信 → 清除 quick 旗标跑满 70 段）。
- N 只累计执行面＋缓存复用面；全部实质段未执行时输出 `N=unknown` 而非 0（硬约束 1，L21-23）。
- **先例对齐**：FEAT-082 的 `window_note`（bootstrap_aggregate.py:743-754）——投影字段显式声明口径降级（「按日聚合，精度降级」）。quick 摘要行的 `(quick)` 标记 + not-run 计数 + tail action 是同族做法，且更强（机守卫而非纯文本）。

### 3.3 全量引擎何时仍需运行

| 场景 | 面要求 | 依据 |
|---|---|---|
| 推进类深检（发布/版本 bump/治理写回/升级写序列 B~E） | **full 必达** | SKILL.md L63/L132「深检后置 ≠ 深检可选」＋ scenario-c.md L12（DEC-207② P2-1）；arch 顾问（AUDIT-154 §7）：「发布流程显式固定 full」「快速范围通过 ≠ 完整治理通过」 |
| 发布门 Gate #7（release-checklist 各版） | full | 0.78.x-0.96 全系 checklist 实测惯例；N 口径可比性（§4 候选 B 论证） |
| review census（CODE/RELEASE R0/R1 基线对照） | full | review-FIX-*/REL-* 系列惯例 |
| `--level strict` 全明细 | full | SKILL.md L71 三档详略契约 |
| CI（.github/workflows/ci.yml 3 步） | 不消费 --summary-only（无参 + check-manifest-consistency + check-cross-references，exit-code 契约） | ci.yml:19-25 实测 |
| post-commit hook Step 4 | 无参全量（非 summary 路径）——每次 commit 付全量成本，属本票外但同根因（§8 开放问题 6） | infra/hooks/post-commit「Quick governance summary」块 |
| 宿主项目（host≠plugin roots） | **已经只有 45 段**：product-gate 默认跳过 25 段插件自检，summary-only 实测 2.49s（FIX-270，architecture-audit-facts-0.80.0.md L431） | 宿主模式 `_product_gate_active` 走 roots diverge 分支 |

**关键判断**：62-70s 的墙钟问题是 **dogfood 特有口径**（本仓自治理时 70 段全跑）；宿主项目的会话摘要已经是秒级（2.49s@FIX-270 时点）。接线的**主要受益方是插件自开发工作流（dogfood）**；宿主侧收益是契约显式化（四态披露替代 [SKIP] banner）与 C3 保留段的进一步裁决空间（§7 R3）。

---

## 4. 接线形态候选与推荐（问题 2）

### 候选 A——summary-only 内部换选择策略（最小接线）

`--summary-only` 分支跑引擎前置 `args.quick=True`，摘要行换 quick 四态行；全量经 `--level strict` 或新增 `--full` 按需。

- ✅ 改动最小（引擎 ~40 行，协议文本少量）；会话摘要自动受益。
- ❌ **N 口径静默分叉**：`--summary-only` 的 N 从「全量 N」变「quick N」，而全部既有消费方（发布门 Gate #7、review census 基线 117/65/33/20…、contract_matrix golden samples、docs/verification 记录）都按全量口径解读——**历史基线全部不可比**，除非逐个消费方同步改（这个迁移面远大于引擎接线本身）。「小」是假象。
- ❌ 深检语义含混：SKILL.md L65 措辞「运行 check-governance --summary-only」同时服务会话例行摘要与推进类深检（L132）——同一旗标两语义，违反「深检 full 必达」的显式性。
- 回滚：revert 引擎分支即可，但灰度期产生的基线记录已污染。

### 候选 B——显式 `--scope quick|full` 契约 + 会话面默认 quick（**推荐**）

arch 顾问原案（AUDIT-154 §7 P1：「加 `--scope quick|full` 契约（发布流程显式固定 full）」）。要点：

1. `check-governance` 新增 `--scope quick|full`（缺省 **full**——既有旗标语义零变化）；`--scope quick` 时引擎走 FEAT-026 既有 quick 接线（L15809 分支复用），摘要行 = selector 四态汇总行。
2. **bootstrap 会话协议改消费点**：SKILL.md L65 / behavior-protocol M4.1 / commands/governance*.md 的健康摘要命令改为 `check-governance --summary-only --scope quick`；深检（M5.5 条 3 / scenario-c）固定 `--scope full`（措辞显式化，安全语义不回退）。
3. legacy 回退：`behavior_profile.py` `LEGACY_REVERTS` 追加第 5 项（surface=「健康摘要执行面」，modern=「--scope quick 四态摘要」，legacy=「复用全量引擎」，class=performance——现有 4 项全部 performance class，`revert_contract_issues` 机守卫零改动即容纳）。

- ✅ **既有消费方零迁移**：`--summary-only` 不带 scope 默认 full，发布门/census/golden samples 的 N 口径、字节输出零漂移；机器契约（exit code + 文件副作用，audit-facts §9.1 冻结口径）不动。
- ✅ 覆盖面披露免费获得：quick 路径的输出本就是四态行（§3.2），`(quick)` 标记 + not-run 计数机守卫强制。
- ✅ 深检/门禁语义显式：full 不再是「缺省巧合」而是「门禁声明」。
- ✅ 回滚路径干净：单开关（GOVERNANCE_LEGACY_BEHAVIOR=1 回退会话摘要执行面）＋协议文本 revert＋`--scope full` 恒可用；无数据迁移。
- ❌ 协议文本改动面较大（SKILL.md + behavior-protocol + commands/governance 三层 + 入口模板 canonical source + @bootstrap-version bump——Bootstrap 变更纪律：先改 governance-init.md Step 7 模板）。
- ❌ 会话摘要的 N 与深检 full 的 N 是两个数——面板/文档必须始终带 `(quick)` 标记防误读（QR-4 已强制，但文档口径表要同步）。

### 候选 C——quick 先行返回 + 后台/惰性全量

quick 立即返回四态摘要，同会话后台跑 full（shadow 通道 S-B 已有机制，`render_quick_output` L691-697 的 `_capture_full_run` 即一次调用内 quick+full）。

- ✅ 理论上会话摘要秒级可见且最终获得全量结论。
- ❌ arch 顾问明确警示三条（AUDIT-154 §7/盲点 3/4）：「shadow 不应变成每次启动后台全量重跑」（总成本未减，只移出视野——「不能用后台化掩盖总成本」）；「异步健康结果需要快照一致性——旧快照 PASS 不能成为新变更的发布凭据」；C 级后台 daemon 明确未实现（SKILL.md L282）。DSH 会话内后台 job 可行但非平台契约。
- ❌ 引入快照一致性新语义面（结果时效/失效键/single-flight）——超出本票应承载的复杂度；缓存复用子集属 Slice-3（CACHED 态），FEAT-012（task_priority.py G5：last-run cache + 输入指纹失效 + --force 旁路）是现成实现先例，应作为后续演进而非首期。
- 判定：**不推荐首期**；其缓存子集（同输入复用 full 裁决）留 Slice-3 候选（与 AUDIT-154 切片 B 的 single-flight 条目对齐）。

**推荐：候选 B**。核心论据：N 口径可比性是既有治理记录体系（发布门基线、审查 census、版本间漂移对照）的隐形依赖，A 会静默打断它；C 违反「后台化不掩盖总成本」与快照一致性边界；B 用一个显式参数把「会话面要快」与「门面要全」写成调用方声明，正好落 arch 顾问原案，且既有面零迁移。

---

## 5. 目标墙钟口径（问题 3）

三条既有口径的事实关系：

| 口径 | 出处 | 现状判定 |
|---|---|---|
| <15s 设计门（对齐 SPG_RESOLVE_TIMEOUT 量级） | audit-145-watchdog-design-0.76.0.md L167（0.76.0 验收门禁） | 对「复用同引擎」的 summary-only 已证伪（DEC-149 确认前提不成立）；**对 quick 面重新成立**（本实测 10.7-12.1s） |
| 单次 <60s 且每会话仅一次 | DEC-149 修订验收（risk-log RISK-044） | 62-70s 仍超线；quick 接线后轻松满足，但 60s 线对 quick 面过松、失去门禁意义 |
| p95≤3s / 首次有效交互 p50≤15s | AUDIT-154 切片 B 目标（未立项时点） | 本实测证伪「秒级」：dogfood quick 面 11s 中 named 检查 ~7.6s（Check 30 closure 1.9s + Check 32 triage 3.2s + 28j capability 0.9s 为三大头），3s 需追加 quick 面内部优化（非本票范围） |

**建议口径**（供用户裁定）：

- **quick 面会话摘要：dogfood 单次 ≤15s（门禁）**——依据：本实测 10.7/12.1s 双样本 + 30% 同机相对容差（audit-facts §9.5 门禁方法）；宿主 ≤5s（参照 FIX-270 宿主 2.49s 基线 + 同容差）。测量协议：打包期本机双样本 + 会话轨迹抽样。
- **full 面不设墙钟门**：full 成本（91.4s）只付在门禁/深检时刻，属「风险操作按需加税」（AUDIT-154 §6 治理税定价原则）；其看护走既有验收（exit 0/issue 基线对照），不走墙钟。
- REQ-145.7 的「秒级」验收字面（plan-tracker L464 已修订过一次）需随本票再修订一次（DEC 新条目）：验收对象从 `--summary-only` 迁移到 `--summary-only --scope quick`，数值 ≤15s（dogfood）——**该修订属用户裁定点**（开放问题 3）。

---

## 6. 实施票面草案（问题 5）

**票面**：FEAT-0XX「quick-scan 接线会话健康摘要（--scope quick|full 显式契约）」｜P2｜0.94.0 候选｜依赖：无（FEAT-025/026 已交付）

**files 清单**（估计行数依据：FEAT-026 巨石侧实际接线 = L15809-15818 共 10 行；FEAT-040 LEGACY_REVERTS 每项 8 行〔behavior_profile.py L87-116〕；FEAT-082 window_note 单面 +276 行同量级参照）：

| 文件 | 变更 | 估行 |
|---|---|---|
| `skills/software-project-governance/infra/verify_workflow.py` | argparse `--scope`（~6 行）＋ cmd_check_governance quick 分支与 summary 渲染对接（~30 行） | ~40 |
| `skills/software-project-governance/SKILL.md` | 健康摘要段（L63-72）：会话默认 `--scope quick` + 四态行解读 + 深检 full 措辞 | ~25 |
| `skills/software-project-governance/references/behavior-protocol.md` | M4.1 步骤命令 + M5.5 条 3 深检 full 显式化 | ~15 |
| `commands/governance.md` + `commands/governance/overview.md` + `scenario-c.md` + `scenario-f.md` + `commands/governance-status.md` | 契约文本（scope 语义/发布门 full/Health 位数据源注脚） | ~60 |
| `skills/software-project-governance/infra/behavior_profile.py` | LEGACY_REVERTS 第 5 项 | ~10 |
| `commands/governance-init.md` Step 7 + AGENTS.md/CLAUDE.md 入口模板（canonical source 先行）+ @bootstrap-version bump | bootstrap 模板健康摘要行 | ~30 |
| `skills/software-project-governance/infra/tests/`（test_summary_only.py / test_quickscan_selector.py / test_behavior_profile.py 扩展） | 对照测试（见验收） | ~150 |
| `skills/software-project-governance/infra/contract_matrix/generator.py` + golden samples | 新 face：scope-quick 冻结样本 | ~40 |
| CHANGELOG + 本 memo 引用 | 记录 | ~15 |
| **合计** | | **~385 行**（非单文件巨石改写；引擎面仅 ~40 行） |

**验收判据**：

1. **墙钟门**：dogfood `check-governance --summary-only --scope quick` 双样本 ≤15s（本机打包期实测入 evidence）；宿主样例 ≤5s；同机交错相对容差 ±30%（audit-facts §9.5）。
2. **覆盖面披露**：quick 输出含四态汇总行（QR-4 机守卫测试绿）＋ NOT_RUN 逐段原因码 ＋ tail action；`N=unknown` 语义测试在案（test_quickscan_selector 既有面扩展）。
3. **回归保护**：`--summary-only`（无 scope）与现行输出**字节等价**（test_summary_only.py 用例 4「缺省路径字节一致」先例，快照 diff）；`--scope quick` 注册表守卫 fail-closed 路径测试（untrusted → 回退 full 跑满 70 段，FIX-304 口径）；contract_matrix golden samples 双 face（scope-quick / 无 scope）冻结。
4. **深检语义**：SKILL/behavior-protocol 推进类深检 full 必达措辞不变（安全语义不回退）；协议文本守卫测试（marker 检查）绿。
5. **legacy 回退**：`GOVERNANCE_LEGACY_BEHAVIOR=1` → 会话摘要命令回退全量路径（behavior_profile revert_contract_issues 绿 + 集成测试）。

**风险登记候选**（入 risk-log 评审）：

- R1（中）N 口径分叉误读：quick N 与 full N 并存，面板/文档误引 → 缓解：`(quick)` 标记机守卫 + 文档口径表 + review 模板注记。
- R2（中）dogfood 产品自检延迟暴露：会话面不再每会话覆盖 25 段产品自检（ArchGuard/loop-claim 等）→ 缓解：发布门 full 必达 + post-commit hook Step 4 仍全量（每次 commit 覆盖）+ 发布前 Check 面不缩水。
- R3（低）C3 保留段宿主语义：28j/28l（插件面、C3 fail-safe 保留）在宿主 quick 模式下的去留——FEAT-025 已披露（`plugin_face_not_product_gated`）留 Phase-2 input_deps 闭包裁决；本票不改 C3 裁决。
- R4（低）quick 面 11s 内部三大头（Check 30 closure 1.9s / Check 32 triage 3.2s / 28j AST 0.9s）若未来劣化超 15s 门 → 登记后续优化票（28j AST 结果缓存等），不在本票范围。
- R5（低）contract_matrix 冻结面漂移：generator.py L518 硬编码 `--summary-only --level lightweight`——加 scope 后须双 face 冻结防漂移。

**规模估计诚实性**（ADR 估算失准教训）：上表逐文件行数以仓内同族先例实证外推（FEAT-026 巨石接线 10 行、FEAT-040 每 revert 8 行、FEAT-082 +276 行单面）；**未含**发布流程自身开销（release checklist 执行、双审、版本 bump 全套）与协议文本守卫测试的连锁对齐——这两项按 REL 惯例另计。主要不确定项：入口模板 bump 可能触发四平台投影同步（FEAT-037 面）——若投影面连锁，估计上浮 ~80 行。

---

## 7. 风险与决策链衔接（问题 6）

**RISK-044 状态迁移路径**：

1. 本 memo 入档 = 兑现 risk-log RISK-044 行登记的下次复评义务（「quick-scan 接线评估入档」/ 0.94 立项窗）与 DEC-177② 的复评链、DEC-164 的 quick-scan 前移评估义务（0.78.x+ 候选 → 评估结论）。
2. 接线落地前：维持**缓解中**（62-70s 仍超 <60s 修订线）。
3. 接线落地后：若打包期实测满足新口径（quick ≤15s dogfood）→ 复评可转**已缓解**（参照 RISK-048 先例：FIX-401 收窄 + 观察窗证据确认 → 已缓解，2026-10-02）；**关闭标准建议**：连续 2 个发布周期打包期实测达标 + 会话轨迹抽样无回退报告 + full 门禁面（发布门/census）无覆盖缺口事件。若用户裁定不立项 → RISK-044 维持缓解中并修订验收线为现行实测口径（62-70s 带 + 同机容差），或转向候选 C 的缓存路线（Slice-3）。
4. REQ-145.7 验收信号的第二次修订（对象迁移 + 数值 ≤15s）需 DEC 新条目（用户裁定）。

**决策链完整性**：DEC-149（接受+修订）→ DEC-164（前移收窄为候选）→ DEC-167（检查点维持）→ DEC-177②（转缓解中+复评义务）→ DEC-246⑨/DEC-274/278（历次前窗复评维持）→ 2026-10-02 复评（数据侧收敛确认+引擎侧定性）→ **本 memo（评估结论入档）** → 用户立项裁定 → 〔落地 → 观察窗 → 已缓解 → 关闭〕。

---

## 8. 开放问题（需用户裁定）

1. **接线形态**：候选 B（--scope 显式契约，推荐）vs 候选 A（summary-only 内部换策略）vs 暂不接线（修订验收线为现行口径）。
2. **目标口径数值**：quick ≤15s（dogfood）/≤5s（宿主）是否接受；是否同时追加 quick 面内部优化票（向 3s 靠拢：Check 30/32/28j 三大头）。
3. **REQ-145.7 验收字面修订**：走 DEC 新条目（对象迁 `--scope quick`、数值 ≤15s）——需用户确认。
4. **RISK-044 关闭标准**：采纳「落地 + 连续 2 发布周期达标 + 无覆盖缺口事件」或另定。
5. **窗口**：0.94.0 立项（复评窗 2026-10-31）纳入 vs 推迟（0.95+）——注意 R2（dogfood 产品自检延迟暴露）在长窗口下的累积面。
6. **票外同根因项**（本 memo 仅记录不裁定）：post-commit hook Step 4 无参全量（每次 commit ~91s）是否并入本票或另立票；候选 C 的缓存子集（Slice-3 CACHED 态，FEAT-012 先例）是否预约为 0.95+ 候选。

---

## 附：证据锚索引

- quick 交付面：`infra/quickscan_registry.py`（70 段注册表/守卫）、`infra/quickscan_selector.py`（四态契约/`prepare_quick_args` L651/`render_quick_output` L678）
- 巨石接线点：`verify_workflow.py:15792-15829`（三分支）、`15841-15871`（product-gate 25 段）、`15891-15906`（`_product_gate_active`）
- 健康摘要契约：SKILL.md L61-72、behavior-protocol.md L223/L415、commands/governance.md L62、scenario-f.md L12/67/86
- 消费方枚举：发布门（docs/release/release-checklist-0.78.x~0.96 Gate #7 全系）、审查 census（docs/reviews/review-FIX-*/REL-* 系列）、contract_matrix（generator.py:518 + golden_samples.txt:1260）、CI（ci.yml:19-25，不消费 summary-only）、post-commit hook（infra/hooks/post-commit Step 4 无参全量）
- 实测命令：§2.1 表（B1-B6 全文）；cProfile 数据文件 %TEMP%\qs_sum.out / qs_quick.out（会话临时，不入仓）
- 先例：FEAT-012 G5（task_priority.py:2213-2423 缓存抑制）、FEAT-033/034（快路径/首次交互前置）、FEAT-040（behavior_profile.py LEGACY_REVERTS/revert_contract_issues）、FEAT-082（window_note 精度降级标注，bootstrap_aggregate.py:743-754）、FIX-270（宿主 product-gate 提速 25.49→2.40s，audit-facts L431）
- 治理记录：risk-log RISK-044 行（L38）；AUDIT-154（docs/requirements/governance-bootstrap-cost-audit-0.84.0.md §3.4/§7/§9 切片 B）；plan-tracker L464（REQ-145.7 修订史）
