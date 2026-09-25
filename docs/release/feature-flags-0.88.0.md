# Feature Flags — 0.88.0（REL-086 M-1R / REL-088）

> **起草说明**：本版 feature-flags 面随 M-1R 四件套一次成形（对照 feature-flags-0.87.0 先例——0.86.0 起四件套为 M-1R 标准面）。**与 0.87.0 的关键差异**：0.87.0 三项行为变更均「无 flag 级降级通道（版本级回滚唯一路径）」；0.88.0 的 B-12/B-13 **首次自带运行时姿态通道**——但均为「机制交付未激活」出厂态（B-12 出厂全 WARN / B-13 缺省 MD_ACTIVE 零足迹），flag 面即该双层事实的登记面 + 激活后回退通道声明（`--deactivate-block`/break-glass 与 `rollback-export/rollback-activate`）+ 既有灰度开关边界重申。起草于 2026-09-25（REL-088），随候选提交入索引。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.88.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.88.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。本版全部验收在仓库内与隔离 `DSH_HOME`（环境变量重定向至临时目录）类口径下完成——隔离验收不等于真实外部环境验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开；do not claim 1.0.0 production-ready。
- **激活态不越权主张**：本版不主张任何 write-guard 族已 BLOCK 运行、不主张 decision-log JSON 权威已生效——B-12/B-13 的真实翻转/切换是发布窗内另行授权的独立动作，非本版交付内容（CHANGELOG 0.88.0 段披露④⑤同口径）。

## 1. 本版 flag 面总览

| 项 | 值 |
|---|---|
| 本版行为变更 | **B-12**（write-guard 分族 BLOCK 激活机制，FEAT-064）/ **B-13**（decision-log JSON 权威化机制，FEAT-061 阶段性交付）/ **B-14**（closure 取消/重开/接管路径，FEAT-062/063）——CHANGELOG 0.88.0 段行为变更节原文口径；另有 FIX-375 writer 族退出码透传（非独立变更号，§5） |
| flag 级通道 | **B-12/B-13 首次具备运行时姿态通道**（分族 posture 配置 + 存储权威状态机）——但**出厂态 = 全 WARN / MD_ACTIVE**（零足迹），激活/切换均经授权票另行执行；B-14 **无 flag 面也无需求**（纯新增能力，版本级回滚即消失）；通道的回退方向（`--deactivate-block`/break-glass、`rollback-export/rollback-activate`）为 FEAT-064/061 交付面，非灰度放量开关 |
| 非破坏性说明 | B-12 为 DEC-224 双约束内执法硬化（BLOCK 写后执法——不能阻止文件被修改，M-0 事实填充③如实措辞；FEAT-060 持久状态机+B-11 三面留痕为前置基座）；B-13 外部 decision-append CLI 契约零变化、旧工具对新格式明确拒绝非静默误读；B-14 纯新增无删除面——CHANGELOG semver 论证段同口径（Breaking changes = 无） |
| 既有灰度开关 | `GOVERNANCE_LEGACY_BEHAVIOR` / `behavior_profile: legacy`（0.84.0 FEAT-040 交付，本版零改动）——见 §6 边界 |

## 2. B-12 write-guard 分族 BLOCK 激活（FEAT-064；DEC-239）

- **变更**：write-guard 姿态分族化——五族裁定（**evidence / review / decision / ops_ledger 四族 BLOCK 目标 + task_status WARN 后置**——DEC-239①；裁定表 = FAMILY_RULING_DECLARATION，枚举基线 = FEAT-049 写入器契约注册表）；BLOCK 为**写后执法**（FAIL face + 被阻塞面基线保持前像，恢复 = 写入器补凭证自动消费——DEC-236① R2 逐面钳制语义）；配套 FEAT-060 遗留三件（hook_identity / A-B-A 会话累计定案 / SESSION_ID 接线）+ FIX-383 registry 收口（96→97 键）。
- **姿态面（出厂态）**：`.governance/.write-guard-posture.json`（`write_guard_state.py` POSTURE_CONFIG_FILE_NAME L301）——**由 guard CLI 管理模式独占写入**；**文件缺席 = 全 WARN = 零足迹**（健康宿主零输出变化——字节恒等探针实证，EVD-1156）。**本版交付态 = 文件缺席（全 WARN）**。
- **激活通道**：`governance-write-guard --activate-block <families>`——**由 Coordinator 于发布窗裁决执行**（DEC-239②——机制交付/真实翻转分离，与 FEAT-061 切换授权同型防本 session 自锁）；激活即写入姿态文件，报告留痕。
- **用户视角**：获得 = 分族执法的**机制与通道**（激活前后姿态可查——`--show-posture` 渲染裁定表/现值/BLOCK 标记）；本版不主张全族已 BLOCK 运行（保守边界——真实翻转是授权票动作）。
- **回退通道（激活后）**：**族级 flag 回 WARN** = `governance-write-guard --deactivate-block <families>`（audited B-12 flag rollback——reason + authorized-by 必填，`verify_workflow.py` L23916 实读）；紧急止损 = `--break-grant` break-glass 恢复窗（五限定=对象/操作者/理由/有效期/次数 + use 审计不可静默——**guard 自指场景同样适用不可静默**）；机制级缺陷 = 版本级回滚（整窗 revert——出厂全 WARN 态下零姿态残留）。程序与后果核验见 rollback-plan-0.88.0 §7.1/§4 #11。
- **task_status 族**：WARN 后置 0.89+（合法手工面机录化后再 BLOCK——DEC-239①/version-plan §6）。

## 3. B-13 decision-log JSON 权威化（FEAT-061 阶段性交付；DEC-237/238）

- **变更**：decision-log 存储分离首表六层落地——权威状态机（`MD_ACTIVE → CUTOVER_FROZEN → JSON_ACTIVE → ROLLBACK_FROZEN → (rollback) MD_ACTIVE`；闭表 + epoch fencing 端到端 + 唯一线性化点 = 状态文件原子替换）/双后端写入路由（MD 字节零变化 + JSON 同 CAS/幂等）/迁移编排（freeze 四闭合 + activate 三段 journal + rollback 对称复检）/独立校验器（禁导入自签拒绝 + 旧解析器逐字符镜像 + 负向注入 7 例）；外部 `decision-append` CLI 契约**零变化**；旧工具对新格式**明确拒绝**（非静默误读）。
- **权威状态面（出厂态）**：`.governance/.decision-store-state.json`（`decision_repository.py` AUTHORITY_STATE_FILE L131）——**缺省 `MD_ACTIVE` epoch 0 = 零足迹**（文件缺席即初始世界；DEC-238②）。**本版交付态 = 文件缺席（MD_ACTIVE）**——`decision-log.md` 保持 md 权威，行为与 0.87.0 字节等价。
- **切换通道**：真实切换经**授权票**执行——前置 = **DEC-238④ 三缺口（RISK-059 承载：①archive.py DEC 归档路由改造方案 ②verify_workflow freshness 接线方案 ③11 处 DEC-nnn① 勘误行源文件处置）+ DEC-239⑦ 归票的 F-5①③ 组合测试两项（台账损坏×切换窗共存 / 基线更新×投影失败恢复）——合计五项前置**；另 R1 N-1~N-5 清扫项同批 + 真实演练重跑 + 证明包（feat061-rehearsal-result.json 口径）审查通过后授权（RISK-059 缓解行原文）。
- **用户视角**：获得 = 存储分离的**机制与回退路径**（`decision_migration.py status` 随时可查权威/新鲜度——当前必为 MD_ACTIVE）；本版不主张 JSON 权威已生效（保守边界）。
- **回退通道（切换后）**：**反向转换方案（显式交付件——非隐含承载）** = `decision_migration.py rollback-begin`（JSON_ACTIVE→ROLLBACK_FROZEN）→ `rollback-export`（当前 JSON **全量**反向导出至 rollback-export.md——**MUST 覆盖迁移后新增行**；仅切换前快照备份不算可回滚——version-plan §5 B-13 原文）→ `rollback-activate`（ROLLBACK_FROZEN→MD_ACTIVE）——FEAT-061 已交付该 CLI 面（argparse L1029-1035 实读）且真实 179 行演练 round_trip 已证**字节回环**（EVD-1155）；DEC-237 条款 01 权威恢复协议 + 07 回退兼容窗口承载。程序与后果核验见 rollback-plan-0.88.0 §7.1/§4 #12。
- **阶段边界**：存储分离其余表（evidence-log 等）出槽 0.89+（version-plan §6——首表模式验证后推广）。

## 4. B-14 closure 取消/重开/接管路径（FEAT-062/063）

- **变更**：限定入口（可取消状态+明确授权者+无在途写+锁属当前执行者）→ CAS 单终态 → cancellation op 登记（原因/幂等键）→ 终态 → 仅释放自有锁（ARCH-09 同型）→ 对账（世界是真相）；重开 = 保留原 closure 新尝试编号关联（不擦历史）；接管 = 执行代际 fencing（写入端校验——旧执行者恢复后不能继续提交；心跳超时不构成停止证明）。
- **用户视角**：获得 = closure 生命周期的三条新路径（纯新增能力面，无删除；外部 CLI 契约不变）。
- **flag 面**：**无**——也无需：能力开关即「入口守卫」本身（不可取消状态/无授权/有外部副作用 ⇒ 明确拒绝，FEAT-062 验收项），不存在「关闭后行为分叉」的运行时中间态。
- **回退通道**：版本级回滚即消失（纯新增——无数据迁移无删除面；已登记 cancellation/reopen 事件为事实记录保留）。程序见 rollback-plan-0.88.0 §1/§3。

## 5. FIX-375 writer 族退出码透传（非独立变更号——行为面索引）

- **变更**：引擎分发返回码透传——writer 族失败 exit 0 假绿 → **exit 2**（8 return-style handlers 全透传；库面 ContractViolation 语义钉；无 SystemExit 桥接——DEC-230/231）+ 畸形 --operation-id 结构化 schema_violation + locks-release 三恢复腿 released_files 审计一致。
- **用户视角**：获得 = 治理写入失败从「静默假绿」变为「显式退出码」；迁移 = 消费方读退出码。
- **回退通道**：随 FIX-375 版本级回滚恢复旧行为（exit 0 假绿态回归——门禁信号弱化面如实披露，rollback-plan §1/披露⑨）；无 flag 级中间态。

## 6. 既有灰度开关边界（非本版新增——边界重申）

`GOVERNANCE_LEGACY_BEHAVIOR=1`（会话级 env，优先级高）> plan-tracker `behavior_profile: legacy`（项目级）> 默认 `modern`（非法值不猜——`governance-bootstrap` behavior.invalid 显式报告）：只回退**性能/编排行为**（4 项）；**安全语义不回退**（六不变量——升级确认门 / 异常不隐藏 / fail-closed〔`resolved_root_ok == false` 即停〕/ 真实环境防护〔三选一〕/ 复审必达 / 升级确认门前零写操作）——边界表权威源 = `skills/software-project-governance/SKILL.md`「行为灰度开关」节。本版未改动该通道与 LEGACY_REVERTS 约束（仅 performance 类可入回退表；任何把安全语义塞入回退表的改动会被守护测试翻红——`behavior_profile.revert_contract_issues()` 机检）。

**B-12/B-13/B-14 与灰度开关的正交性**：`GOVERNANCE_LEGACY_BEHAVIOR` **不承载**三项变更的任何回退——B-12 guard 执法与 break-glass 不可静默属**安全语义**（legacy 模式下 BLOCK 族照样拦截、审计照样留痕，无「legacy=关执法」中间态）；B-13 存储权威与 B-14 closure 生命周期属**治理行为**而非性能/编排行为，均不在 LEGACY_REVERTS 白名单；B-12/B-13 的合法回退通道唯一 = §2/§3 声明的授权票通道（deactivate/rollback-export）与版本级回滚（rollback-plan-0.88.0 §7）。

## 7. 未发布面

- **write-guard task_status 族 BLOCK**：留 0.89+（DEC-239① WARN 后置——合法手工面机录化后再 BLOCK）；
- **B-12 真实翻转 / B-13 真实切换**：授权票动作（DEC-239② / RISK-059+DEC-238④+DEC-239⑦ 五前置）——本版零执行零主张；
- **存储分离其余表 / 主文件大拆解**：0.89+（version-plan §6）；
- **flag 清理计划**：不适用（B-12 姿态文件与 B-13 状态文件为**缺省缺席的零足迹工件**——非常驻 flag 债务；健康宿主零文件）；0.88.0 行为变更编号序列止于 B-14；
- **kill switch 验证**：B-12 的运行时关闭 = `--deactivate-block`（audited）+ `--break-grant`（限定留痕）——通道在场且 break-glass use 审计不可静默为验收面（EVD-1156 八焦点含 break-glass 四件套）；B-13 的运行时回退 = `rollback-begin/export/activate` 三段——真实 179 行演练 round_trip 已验（EVD-1155）；B-14 无 kill switch 需求（入口守卫即安全兜底）。

## 8. 硬门槛自检（本文件）

| 门槛项 | 判定 |
|---|---|
| 版本串在场 | PASS（0.88.0 多处） |
| 保守边界 5 token 在场 | PASS——五项 boundary token + 激活态不越权主张条齐备于「保守边界声明」节，逐项均携带 No…claim 行首 + 未被主张 的否定形态 |
| 禁用正向主张（overclaim） | PASS——全文按「未被主张/无/不适用」记录性措辞；B-12/B-13 出厂态双层表述与 CHANGELOG 披露④⑤同口径；无可索引的 loop-runtime 活体声明 |
| 与 CHANGELOG/rollback-plan/version-plan 口径一致 | PASS——B-12/B-13/B-14 回退口径逐字对齐 CHANGELOG 0.88.0 段行为变更节 + rollback-plan §7 专节 + version-plan §3b/§5；姿态/状态文件名与管理命令面取自 write_guard_state.py/verify_workflow.py/decision_repository.py/decision_migration.py 实读 |
| 表行管道符转义（FIX-365 ragged 教训） | PASS——表 cell 内零裸管道符，全行单层管道分隔 |

---
*REL-088 M-1R 起草冻结（2026-09-25，REL-088，Governance Developer Agent 起草）。事实基线：B-12/B-13/B-14 回退口径取自 CHANGELOG 0.88.0 段（REL-087 交付版）行为变更节原文 + version-plan-0.88.0 §3b/§5；B-12 姿态面取自 `infra/write_guard_state.py` 实读（POSTURE_CONFIG_FILE_NAME L301 / FAMILY_RULING_DECLARATION 渲染 L1642-1650 / 管理 CLI L1668-1699）+ `verify_workflow.py` L23908-23917（deactivate-block = audited B-12 flag rollback）/L25869-25893（CLI 旗标面）实读；B-13 权威状态面取自 `infra/decision_repository.py` 实读（AUTHORITY_STATE_FILE L131 / 状态机 L151-163 / 缺省零足迹 L41）+ `infra/decision_migration.py` argparse L1009-1048 实读；五前置授权票口径取自 DEC-238④/DEC-239⑦（`.governance/decision-log.md` 实读）+ RISK-059（`.governance/risk-log.md` 实读）；B-14 口径取自 FEAT-062/063 交付记录（EVD-1157/1160）；灰度开关边界取自 SKILL.md「行为灰度开关」节实读。*
