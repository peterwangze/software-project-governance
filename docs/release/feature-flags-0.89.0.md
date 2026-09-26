# Feature Flags — 0.89.0（REL-090 M-1R / REL-092）

> **起草说明**：本版 feature-flags 面随 M-1R 四件套一次成形（对照 feature-flags-0.88.0 先例——0.86.0 起四件套为 M-1R 标准面）。**与 0.88.0 的关键差异**：0.88.0 交付 B-12/B-13 机制与运行时姿态通道（出厂未激活）；**0.89.0 无 flag 翻转、无新增功能激活**——DEC-244 明示激活授权票不捆绑（行为变更需逐项明示授权）+ DEC-246⑥ 措辞收紧（「无新增功能激活；含治理判据、恢复安全与锁生命周期行为修正」——CHANGELOG 0.89.0 段行为变更节声明同源）。本文件 = 既有机制出厂态的如实登记面（B-12 分族姿态全 WARN + B-13 MD_ACTIVE 未激活）+ 行为修正三面（无 flag 级通道——版本级回滚唯一路径）+ 既有灰度开关边界重申。起草于 2026-09-26（REL-092），随候选提交入索引。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.89.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.89.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **激活态不越权主张**：本版**无新增功能激活**——不主张任何 write-guard 族已 BLOCK 运行（B-12 出厂全 WARN 姿态不变，0.89 窗口无 `--activate-block` 执行）、不主张 decision-log JSON 权威已生效（B-13 缺省 `MD_ACTIVE` 零足迹，0.89 无真实切换）、不主张行为修正三面具备任何运行时开关（无 flag 级通道——版本级回滚唯一路径）；B-12/B-13 真实激活是发布窗外另行授权的独立动作（DEC-244——激活授权票不捆绑），非本版交付内容。

## 1. 本版 flag 面总览

| 项 | 值 |
|---|---|
| 本版行为变更 | **无新增功能激活**（DEC-246⑥ 措辞收紧——CHANGELOG 0.89.0 段行为变更节原文口径；B-x 新登记预期 = 无，行为变更编号序列止于 0.88 的 B-14）；载荷承载**行为修正三面**（§5——治理判据、恢复安全与锁生命周期行为修正，非激活面） |
| flag 级通道 | **本版零新增**：行为修正三面均无 flag 级中间态（fail-closed 门禁/判据收敛直接生效——版本级回滚唯一路径）；B-12/B-13 既有运行时姿态通道（0.88 交付）维持出厂态不变；B-14 无 flag 面维持 |
| 非破坏性说明 | FIX-391/FEAT-065 新增拒绝面均属 fail-closed 门禁而非既有契约删除（自定义 lock_ttl_le spec 声明被拒 = 闭集纪律非静默降级）；判据收敛不放宽（终态/非终态/未知 token——不绕过 FIX-390 证据检查）；正常链路零感知（FIX-391 兼容矩阵实证不误拒；FEAT-065 真释放后继票不撞人工解锁步）——CHANGELOG semver 论证段同口径（Breaking changes = 无） |
| 既有灰度开关 | `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy`（0.84.0 FEAT-040 交付，本版零改动）——见 §6 边界；**行为修正三面与该开关正交**（恢复安全与锁生命周期属安全语义，不在 LEGACY_REVERTS 白名单） |

## 2. B-12 write-guard 分族姿态（全 WARN 维持——0.89 无激活）

- **机制面（0.88 已交付——FEAT-064/060）**：write-guard 姿态分族化（evidence/review/decision/ops_ledger 四族 BLOCK 目标 + task_status WARN 后置——DEC-239①）；BLOCK 为写后执法；配套 break-glass 四件套（五限定+use 审计不可静默）。
- **姿态面（出厂态——0.89 如实登记）**：`.governance/.write-guard-posture.json` 缺席 = 全 WARN = 零足迹；**0.89 窗口无 `--activate-block` 执行**（DEC-244 激活授权票不捆绑；version-plan §8 原文「0.89 无 `--activate-block` 执行」；REL-091 24 文件面不含 posture 文件——REVIEW-REL-091 §2 全清单实测）。**本版交付态 = 文件缺席（全 WARN）——与 0.88.0 发布态字节等价**。
- **五前置核验（只核验不激活——version-plan §5，M-0 已回填）**：①archive.py DEC 归档路由 ✅ 一致 / ②freshness 接线方案 ✅ 一致 / ③11 处勘误行处置 ⚠️ 口径漂移实测（decision-log 现存 `DEC-\d+①` 形态 3 处出现/2 行 ≠ 登记 11 处——差异归因待考，迁移阻断判定以 B-13 授权票演练引擎实测为准）/ ④archguard R1 锚基线在案（26193 sanctioned）✅ / ⑤F-5①③ 组合测试在案 ✅——核验完成 = 登记一致性确认，**不构成可激活**。
- **激活通道**：`governance-write-guard --activate-block <families>`——**授权票独立决策动作**（DEC-244；防本 session 自锁语义延续——DEC-239②）；前置 = 五前置闭环 + 证明包审查后另行授权；本版零执行零主张。
- **回退通道（激活后——引用不触发）**：族级 flag 回 WARN = `--deactivate-block`（audited）+ break-glass 恢复窗——rollback-plan-0.88.0 §7 专节原文承载、rollback-plan-0.89.0 §7 引用不触发（本版未激活，通道不触发）。

## 3. B-13 decision-log 权威（MD_ACTIVE 未激活——如实登记）

- **机制面（0.88 已交付——FEAT-061 协议层）**：存储分离首表六层（权威状态机/双后端路由/迁移编排/独立校验器）；外部 decision-append CLI 契约零变化。
- **权威状态面（出厂态——0.89 如实登记）**：`.governance/.decision-store-state.json` 缺省缺席 = `MD_ACTIVE` epoch 0 = 零足迹；`decision-log.md` 保持 md 权威——**0.89 无真实切换**（version-plan §8 原文；本版全程 md 权威字节，行为与 0.88.0 等价）。**本版交付态 = 文件缺席（MD_ACTIVE）**。
- **前置缺口（RISK-059 维持打开）**：三缺口（archive DEC 归档路由方案 / freshness 接线方案 / 勘误行源文件处置）已登记未闭环——缺口③勘误行计数口径漂移（登记 11 处 vs 实测 3 处出现/2 行）经 M-0 核验如实登记（version-plan §5 ③——差异归因待考，fail-closed 报真实阻断数）；切换授权票前置 = 五前置闭环 + 证明包审查后另行授权——**非本版动作**。
- **用户视角**：获得 = 判据与门禁面随七票收敛（机录证据行不再假 FAIL〔fixture 面——live 面见披露③〕/ V3 键控伪像 WARN 消失）；本版不主张 JSON 权威已生效（保守边界）。
- **回退通道（切换后——引用不触发）**：反向转换方案 rollback-begin→rollback-export→rollback-activate——rollback-plan-0.88.0 §7 原文承载、rollback-plan-0.89.0 §7 引用不触发。

## 4. B-14 closure 面简注（0.89 行为修正承载——无新 flag 面）

- **机制面（0.88 已交付——FEAT-062/063）**：closure 取消/重开/接管路径（纯新增能力面，无删除；外部 CLI 契约不变）。
- **0.89 行为修正面（非新 flag——§5 同源）**：FIX-391 版本感知门禁（未知事件/出窗 schema 零写拒绝——恢复安全自动化）+ FEAT-065 标准链锁腿真释放（shrink-locks→release-locks + task_locks_released gate）——均无 flag 级通道；**中断遗留锁仍依赖人工恢复（受控流程：确认旧执行者停止→按 task+operation 标识释放→核验索引；禁批量清锁——DEC-248④）**；发布验证双面演示义务见 release-checklist-0.89.0 专席⑤。
- **flag 面**：**无**——也无需：能力开关即「入口守卫」本身（不可取消状态/无授权/有外部副作用 ⇒ 明确拒绝），不存在「关闭后行为分叉」的运行时中间态。
- **回退通道**：版本级回滚即消失（§5 行为修正①②回退注记——rollback-plan-0.89.0 §1；已登记 cancellation/reopen 事件与经受控流程的释放记录为事实保留）。

## 5. 行为修正三面（非激活——无 flag 级通道，版本级回滚唯一路径；DEC-246⑥ 收紧口径）

| # | 变更 | 任务 | 用户视角 | 回退通道 |
|---|---|---|---|---|
| 行为修正① | **FEAT-065 gate 闭集替换**：closure gate kind lock_ttl_le→task_locks_released——自定义 spec 链声明 lock_ttl_le 自 0.89.0 起 **fail-closed 拒绝**（闭集纪律，非静默降级）；lock_ttl 死默认输入移除；锁腿从 TTL 收缩伪释放升级为真释放（任务索引+文件锁归属双面后置条件） | FEAT-065（DEC-248 拆分后链内面——acquire TTL 面拆出 FEAT-066，0.90 池；**不得按 acquire 面宣称完成**——DEC-248④） | 标准 chain 收口后同文件族下一票不再撞人工解锁步；中断遗留锁获明确拒绝+受控恢复指引 | 版本级回滚 = 还原 `closure_chain.py` + `tests/test_closure_chain.py` 两文件（rollback-plan-0.89.0 §1——TTL 收缩伪释放回归为 0.88 已知态；与行为修正②同文件——禁单票选择性还原） |
| 行为修正② | **FIX-391 零写拒绝面**：旧版读取器对新版/未知 journal 事件的语义误读与 seq 碰撞双向量由人工处置路径变为写入口零写拒绝（四写入口全覆盖）——正常链路零感知（兼容矩阵实证不误拒）；跨版本 in-flight closure resume 会 digest 失配拒绝（会话内运营态无跨版本 resume 契约） | FIX-391 | 恢复安全防线自动化（回退 worlds 的 closure 面从有界残余风险变为机器防护——0.88 期人工运行手册门禁仍在场作双保险） | 版本级回滚 = `closure_chain.py` 还原（rollback-plan-0.89.0 §1/§4 #13——journal 事件面与 0.88 兼容〔EVD-1181〕，未知形态行按 0.88 rollback §8 门禁处置；路径 B backport 候选保留） |
| 行为修正③ | **判据收敛面（不放宽）**：FIX-393/394/395 终态/非终态/未知 token 判据收敛——终态不替代证据、不绕过 FIX-390 证据检查（DEC-246① 退出条件）；误推荐/伪 FAIL 消失属判据修正非检查弱化 | FIX-393/394/395 | tpa 零误推荐/零误 blocked；终态行状态列不再滞留过时进度词；热事实源伪 FAIL 簇消失 | 版本级回滚 = 对应文件还原（rollback-plan-0.89.0 §1——误推荐/滞留/伪 FAIL 簇回归为 0.88 已知缺陷态，如实预期非回滚失败） |

## 6. 既有灰度开关边界（非本版新增——边界重申）

`GOVERNANCE_LEGACY_BEHAVIOR=1`（会话级 env，优先级高）> plan-tracker `behavior_profile: legacy`（项目级）> 默认 `modern`（非法值不猜——`governance-bootstrap` behavior.invalid 显式报告）：只回退**性能/编排行为**（4 项）；**安全语义不回退**（六不变量——升级确认门 / 异常不隐藏 / fail-closed〔`resolved_root_ok == false` 即停〕/ 真实环境防护〔三选一〕/ 复审必达 / 升级确认门前零写操作）——边界表权威源 = `skills/software-project-governance/SKILL.md`「行为灰度开关」节。本版未改动该通道与 LEGACY_REVERTS 约束（仅 performance 类可入回退表；任何把安全语义塞入回退表的改动会被守护测试翻红——`behavior_profile.revert_contract_issues()` 机检）。

**行为修正三面与灰度开关的正交性**：`GOVERNANCE_LEGACY_BEHAVIOR` **不承载**行为修正三面的任何回退——FIX-391 零写拒绝与 FEAT-065 锁生命周期 gate 属**恢复安全/安全语义**（legacy 模式下零写拒绝照样拦截、真释放 gate 照样把关，无「legacy=关门禁」中间态）；判据收敛属治理判据面而非性能/编排行为，均不在 LEGACY_REVERTS 白名单；行为修正的合法回退通道唯一 = 版本级回滚（rollback-plan-0.89.0 §1/§8）。**B-12/B-13 正交性维持 0.88 口径**（feature-flags-0.88.0 §6——执法与存储权威属安全语义/治理行为，legacy 模式不提供关闭中间态）。

## 7. 未发布面

- **B-12 真实翻转 / B-13 真实切换**：授权票动作（DEC-244——不捆绑不排期；五前置闭环 + 证明包审查后另行决策；RISK-059 三缺口维持打开——③勘误行计数口径漂移待考）——本版零执行零主张；
- **FEAT-066 acquire TTL 判定面**：0.90 候选池新票（DEC-248②，depends_on=FEAT-065——0.89 已交付，依赖满足）：治理存储层单一执法点（原子临界区：读+过期判定+冲突判定+状态更新），初期 = 过期锁 acquire 拒绝 + 返回过期项与受控回收指引（不自动接管——自动接管需 fencing/代际号等旧持有者隔离前提）；
- **DEC-244 挂起清单**：God Module 拆分 / 存储分离其余表 / task_status BLOCK 机录化 / FEAT-045 P-b / HotFactSource 版本字面量族 / GOVERNANCE_SESSION_ID 复核 / 量测边缘 + FIX-380 P2-1——0.90+（version-plan §7）；
- **flag 清理计划**：不适用（B-12 姿态文件与 B-13 状态文件为**缺省缺席的零足迹工件**——非常驻 flag 债务；健康宿主零文件）；0.89.0 无新行为变更编号登记（B-x 序列止于 B-14——行为修正三面不新设 B-x 号，如实注记）；
- **kill switch 验证**：行为修正三面无运行时关闭通道（fail-closed 门禁/判据收敛即安全兜底——「关闭后行为分叉」中间态不存在）；B-12 的运行时关闭通道（`--deactivate-block` audited + `--break-grant`）与 B-13 的反向转换三段为 0.88 交付面、0.89 引用不触发（rollback-plan-0.89.0 §7）；B-14 无 kill switch 需求（入口守卫即安全兜底）。

## 8. 硬门槛自检（本文件）

| 门槛项 | 判定 |
|---|---|
| 版本串在场 | PASS（0.89.0 多处） |
| 保守边界 5 token 在场 | PASS——五项 boundary token + 激活态不越权主张条齐备于「保守边界声明」节，逐项均携带 No…claim 行首 + 未被主张 的否定形态 |
| 禁用正向主张（overclaim） | PASS——全文按「未被主张/无/不适用」记录性措辞；「无新增功能激活」与 CHANGELOG 0.89.0 段行为变更节同口径；B-12/B-13 出厂态登记如实（全 WARN / MD_ACTIVE 缺省缺席）；无可索引的 loop-runtime 活体声明 |
| 与 CHANGELOG/rollback-plan/version-plan 口径一致 | PASS——行为修正三面回退口径逐字对齐 CHANGELOG 0.89.0 段行为修正节 + rollback-plan-0.89.0 §1/§7 + version-plan §7/§8；五前置核验结论逐项对齐 version-plan §5 回填面（③口径漂移如实转述）；DEC-244/246⑥/248 引用语义一致 |
| 表行管道符转义（FIX-365 ragged 教训） | PASS——表 cell 内零裸管道符，全行单层管道分隔 |

---
*REL-092 M-1R 起草冻结（2026-09-26，REL-092，Governance Developer Agent 起草）。事实基线：无激活声明与行为修正三面回退口径取自 CHANGELOG 0.89.0 段（REL-091 交付版——单 canonical）行为变更节/行为修正节原文 + version-plan-0.89.0 §7/§8 实读；B-12/B-13 出厂态登记取自 version-plan §8 + DEC-244（decision-log 实读 UTF-8）+ REL-091 24 文件面核实（REVIEW-REL-091-RELEASE-R0 §2——posture/state 文件零触碰）；五前置核验结论取自 version-plan §5 回填面实读（①②④⑤一致/③口径漂移 3≠11 如实登记）；FIX-391 兼容矩阵与零写拒绝面取自 EVD-1180 + CHANGELOG 行为修正②；FEAT-065 拆分边界/四红线/中断遗留锁受控流程/双面演示取自 DEC-248 原文 + EVD-1181；journal 事件面不变取自 EVD-1181；灰度开关边界取自 SKILL.md「行为灰度开关」节实读（本版零改动）。*
