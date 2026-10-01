# Feature Flags — 0.82.0（REL-078）

> **M-0 草案（REL-078 prep，2026-09-18）**——Coordinator 审后随 M-1 候选提交；措辞对齐 `docs/release/feature-flags-0.81.0.md` 先例结构。M-3 Release Reviewer 审查与 M-2 门禁实测前，本文件不构成发布声明。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.82.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.82.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。0.82.0 的引擎/守卫改动全部在隔离 `DSH_HOME`（环境变量重定向至临时目录）下验收，隔离验收不等于真实外部首会话验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开，未关闭；do not claim 1.0.0 production-ready。
- **B-8 守卫覆盖限定**：FIX-325 的 CWD 退化反相守卫以 **Node ≥22.15** 的 ESM `registerHooks` 故障注入交付（仓声明 engines≥20）；任何发布注记 MUST 携带该限定语，**不得声称全引擎覆盖**。

## 1. 新增/变更的开关

| # | 开关 | 类型 | 默认 | 说明 |
|---|---|---|---|---|
| — | **（无新增运行时开关）** | — | — | 本版**未引入**任何需要用户显式打开的 opt-in 运行时 flag。0.82.0 的全部行为面（B-1~B-8）随版本生效，无灰度开关——与 0.81.0「写入守卫刻意没有 opt-in」的取舍不同，本版没有任何需要豁免披露的新写入面（dsh 交付面产品零变更） |

### 1.1 豁免账本 digest 治理面（FIX-320，数据资产而非运行时开关）

`core/loop-runtime-claim-exemptions.json` 是本版新增的**数据资产**（消费方 = `check-loop-runtime-claims`），不是 flag——它没有开/关语义，只有「命中九键豁免 ⇒ 披露放行 / 其余 ⇒ 原判定」一条路径。治理面：

- **键面**：九键全键（报告文件 / finding code / 行 / 列 / 消息形态五元组 + 裁决字段）——**五元组全键匹配**，任何一键漂移即不命中（真实漂移不豁免）；
- **锚面**：digest/ID/键面**三锚 fail-closed**——账本文件的 digest 被 `REQUIRED_EXEMPTIONS_SHA256` 锚定（FIX-320 交付常量；authority 链的 `REQUIRED_POLICY_SHA256` + `AUTHORITY_POLICY_DIGEST` 为同族机制先例），未登记的账本改动 = 断锚 FAIL；防篡改三反相（改键/改裁决/改 digest）全部复活为红；
- **披露面**：每次运行在结果中携带 `exemptions_applied` 审计披露（命中条目可追溯）——`UNKNOWN`/静默放行不存在；
- **登记面**：4 条豁免全部裁决扩面留痕（3×UNSUPPORTED@`docs/reviews/review-FIX-300-CODE-R0.md`〔0.66.1 期历史报告〕+ 1×AMBIGUOUS@`docs/release/release-checklist-0.81.0.md`）；
- **效果**：`installed_host` 模式 BLOCKED→PASS（0 findings / 4 披露）；`product_release` 模式的 2×AUTHORITY 真实漂移**不豁免**（由 FIX-345 重锚收口——豁免账本与真实漂移修复是两条独立通道，不互相替代）。

### 1.2 B-8 的环境限定（非开关，如实登记）

FIX-325 的 3 条真守卫（EEXIST 熔断 / 碰撞换名重试 / CWD 退化反相）中，CWD 反相依赖 **Node ≥22.15** 的 ESM `registerHooks`；在不满足的引擎上该用例按 skip/NOT_RUN 政策处理（开发机 Windows Node v24.13.1 真跑 0 skip）。这不是运行时降级通道——守卫存在于交付面，只是其**测试证据**有引擎版本下限；发布注记措辞纪律见保守边界声明末条。

## 2. 行为变更（用户可感知 —— MUST 写入 CHANGELOG 与升级说明）

| # | 变更 | 旧行为（0.81.0） | 新行为（0.82.0） | 理由 | 影响面 |
|---|---|---|---|---|---|
| **B-1** | `check-hot-fact-source` 进行中面的「进行中」字样断言（FIX-339，R0 F-04） | 进行中面断言活跃版本 roadmap 行必须含「进行中」字样 | **放宽**：仅保留「不得虚写已发布」；活跃版本行写「规划中/待启动」不再报 | 与版本锚参数化目标一致；无虚报风险——「进行中」字样要求是与已发布事实互斥的假阳源（0.38.x 族 9 条假阳的构成面之一） | 仅活跃版本的 roadmap 行措辞检查；「不得虚写已发布」保护断言不变 |
| **B-2** | 未发布版本的「自称已发布」防护判据（FIX-339，R1 F-R1-01） | REL 行对 released face 的贡献为「任意格 token OR 累积」——叙事提及即可抬面（探针实证 5→1 逃逸） | **收紧为双判据（fail-closed）**：仅目标版本列锚 token（精确/「或后续」）或事项格「发布 <版本>」头形态抬面；叙事格/依赖格/状态格裸提及**永不抬面**；「无交付 REL 行佐证而自称已发布」= 显式 FAIL | 修复「未发布虚报已发布」在叙事提及形态下的完全逃逸 | 治理检查判定面；对如实填写的行为零影响（真实「发布 X.Y.Z」事项行照常识别） |
| **B-3** | REL 行版本归属识别宽度（FIX-339，R0 F-01/F-05） | 目标版本 cell **精确相等**才识别——cell 错位（日期占位）或「X.Y.Z 或后续」形态被静默跳过 | **放宽为任意格召回**：任意 cell 含锚版本 token（词界守卫）即入任务集；REL 行抬面仍走 B-2 双判据 | 消除「识别静默失败 ⇒ 退化路径吞掉虚报」的 fail-open 面（0.81.0 的 REL-077 行即实形态） | 识别召回变宽的方向为**过报**（fail-closed）；12 项边界探针验证无前缀渗透；D 形态新增的「missing active task REL-077」类过报为已声明预期后果 |
| **B-4** | `check-loop-runtime-claims` 豁免披露机制（FIX-320） | 无豁免通道——3 条 0.66.1 期历史 `UNSUPPORTED_AFFIRMATIVE` 使 `installed_host` 恒 BLOCKED（0.81.0 处置 = 如实披露） | **豁免账本**（`core/loop-runtime-claim-exemptions.json`）：九键 + 三锚 + 五元组匹配 + `exemptions_applied` 披露；`installed_host` BLOCKED→PASS（0 findings / 4 披露）；**真实漂移不豁免** | 历史报告措辞与现行身份门禁的不可解冲突（处置 (a) 改历史记录需 DEC 且改写历史；账本 = 显式、可审计、防篡改的第三条路） | 语义面判定结果翻转（BLOCKED→PASS）伴随**逐条披露**；真实漂移（AUTHORITY 族）仍 fail-closed |
| **B-5** | review_record 唯一键语义（FIX-314） | 键 = `(task, round)`——同 task 同轮第二位审查方 CLI exit 2（「review record already exists」），M-3 双审只能借 `--round 2` 落位 | 键 = **`(task, round, reviewer)`**：同 task 同轮两位审查方各得一条记录（canonical-first 命名 + `-{slug}` 派生文件与镜像行 ID）；FIX-289⑤ 不静默覆盖保持；旧记录字节级不可变；commit-msg/Check 30 兼容 | M-3 双半面审查模型在现有 CLI 下不可表达的流程缺口（REL-076 实证） | 审查记录文件命名空间扩展；旧格式记录零改写；hook 行前缀匹配与 Check 30 复审终态校验经实测兼容 |
| **B-6** | authority source records 锚位置（FIX-345） | DEC-104 / AUDIT-133 双锚指向**热文件**位置——归档迁移（FIX-343）把锚点行移出热文件 ⇒ 2×AUTHORITY_SOURCE_OCCURRENCE 真实漂移 FAIL | 双锚**重锚到归档感知位置**：DEC-104 → `archive/decisions/decisions-v0.1.0-0.78.0.md` L289（归档决策行）；AUDIT-133 → `docs/requirements/loop-engineering-post-implementation-audit-0.66.0.md` L3（审计报告本体，免疫归档迁移）；治理化重锚（不静默改锚），断锚 fail-closed 三形态负例锁死 | 锚定对象为「可验证的现行位置」而非「历史位置」——双 digest 治理化重锚 + `product_release` BLOCKED→PASS | authority 链校验的位置事实变更；校验强度不弱化（断锚三形态负例独立复现） |
| **B-7** | 全量测试基线计数口径（FIX-336） | 「Ran 2983 tests」**实为非全量**——`test_dsh_compat` 整模块在 discover 口径下 `ModuleNotFoundError`（120+ 用例不可见，双侧同现） | **3193**（FIX-336 期实测；M-0 prep 复测 pristine `845c050` = **3200**，TestLoader discover 口径；M-2 以当场值为准）——compat 126 用例恢复被收集，M-2「全量测试基线」恢复真全量语义 | 收集面缺陷（`_HERE` sys.path）使 M-2 门禁长期基于缩水口径 | 测试基线数字 + 口径声明；无运行时行为变化 |
| **B-8** | G-04 CWD 退化反相守卫的覆盖面限定语（FIX-325） | 0.81.0 验收①由独立审查的故障注入复现成立，**无机器守卫**（「机器守卫待 FIX-325」） | **3 条真守卫交付**（EEXIST 熔断 / 碰撞换名重试 / CWD 退化反相）；CWD 反相经 **Node ≥22.15** ESM `registerHooks` 真故障注入（开发机 Node v24.13.1 真跑 0 skip）；发布注记 MUST 携带 Node ≥22.15 限定语，**不得声称全引擎覆盖** | 关闭 0.81.0 Honesty Note 的「机器守卫待 FIX-325」义务；部分回归变异 M1 2/2 + M2 1/1 双向红实证捕获力 | 守卫证据面的环境限定披露；守卫本体随交付面存在，无运行时分支 |

> **升级提示（面向用户）**：B-1~B-3/B-5/B-6 是治理引擎**判定面**变更——对如实填写的治理数据零影响，历史治理记录零改写（FIX-341/343 的数据批为**补录**缺失归档行与更正一处归属误注，非改写既有终态）。若 0.81.0 下依赖「叙事提及即可抬 released face」的旧判据形态（B-2 修复的逃逸面），升级后该形态会从 PASS 翻转为 FAIL——翻转方向为 fail-closed，属预期。

## 3. 新增的检查面与命令（加性，默认启用）

| # | 项 | 形态 | 默认 | 说明 |
|---|---|---|---|---|
| — | **（无新增检查段/命令）** | — | — | 本版**未新增** registry 检查段或 CLI 命令；棘轮口径 **cli keys 84/84 + segments 71/71 不变**（M-2 复跑核实）。FIX-320 豁免账本为既有检查 `check-loop-runtime-claims` 的数据资产消费面；FIX-344（30c 后缀感知）与 FIX-322（K-2 整串）为**既有检查面**（Check 30c / Check 28w K-2）的行为修正，不扩段 |

## 4. 建议的"降级/回退"开关（本版**未**提供，如实列出）

| # | 场景 | 本版处置 | 归属 |
|---|---|---|---|
| D-1 | 用户需要在本机对真实 `~/.dsh` 执行手工 `--install`（离线/无 dsh CLI 场景） | **不可用**（0.81.0 B-2 延续）——README 已同步 B-2 拒绝面与 `DSH_HOME` 重定向指引（0.81.0 起两处） | FIX-324⑤（F-1）的「文档同步」半边**已由 0.81.0 README 更新兑现**；「显式 opt-in」半边**未采**——缺口维持登记于 FIX-324（持久归属行），本版不扩面 |
| D-2 | 豁免账本被误改/损坏导致 loop-claims 异常 | **fail-closed**（三锚断锚 FAIL，不静默放行）；恢复路径 = 从受审提交恢复账本文件 | FIX-320 设计语义（防篡改三反相为交付面） |

## 5. 与 0.81.0 的开关对照（无删除）

- 0.81.0 的既有开关（`--quick` 影子通道、product-gate 跳过机制、`check-release --skip-execution-gates`/BR-4、`dsh-doctor` 四开关等）**全部保留**，语义未变；
- 本版**未删除**任何开关；
- `dsh-doctor` 本版新增**登记面**一行（adapter-manifest.json `native_entry.note`，FIX-326①，设计 §2.9.4）——纯声明性登记，不改变命令行为；
- 0.81.0 的两项行为变更 B-1（`package.json` 缺失/不可读 ⇒ rc 1）与 B-2（真实 home 形态写面 ⇒ exit 2 + `[REFUSED]`）**延续有效**。

---

*M-0 草案冻结（2026-09-18，REL-078 prep）。事实基线：FIX-320/322/339/341/342/343/344/345 终态取自 plan-tracker 任务行与对应 REVIEW 报告（机录）；「无新增运行时开关/检查段」与「棘轮 84/84 + 71/71 不变」由 M-2 门禁复跑核实（本文件为草案，不预填 M-2 实测值）。*
