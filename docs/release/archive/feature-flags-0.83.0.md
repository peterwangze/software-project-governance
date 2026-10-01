# Feature Flags — 0.83.0（REL-079）

> **M-0 草案（REL-079 prep，2026-09-17）**——Coordinator 审后随 M-1 候选提交；措辞对齐 `docs/release/feature-flags-0.82.0.md` 先例结构。M-3 Release Reviewer 审查与 M-2 门禁实测前，本文件不构成发布声明。

## 保守边界声明（no-overclaim boundary）

本版**不**主张、也不构成以下任何一项；下列边界按 release gate 的保守边界 token 如实声明：

- **No official approval claim**：official approval 未被授予、未被主张；0.83.0 不主张官方认可。
- **No marketplace approval claim**：marketplace approval 未被授予、未被主张；0.83.0 不主张已进入任何市场或商店。
- **No universal/full runtime support claim**：universal/full runtime support 未被主张；非 Windows 平台未验证。0.83.0 的引擎/判定面改动全部在仓库内测试与隔离 `DSH_HOME`（环境变量重定向至临时目录）下验收，隔离验收不等于真实外部首会话验证通过。
- **No external first-session pilot success claim**：external first-session pilot success 未被主张。
- **RISK-036 remains open / do not claim 1.0.0 production-ready**：RISK-036（官方收录与外部验证）继续打开，未关闭；0.83.0 为内部治理健康收口版；do not claim 1.0.0 production-ready。
- **ArchGuard advisory 边界**：Check 28n/28o/28p 维持 `fatal_on_error=false` 既有边界——本版不声称 ArchGuard advisory fatal 化；28o 残余 4E 为产品源真实 advisory（God-module 族），如实披露。

## 1. 新增/变更的开关

| # | 开关 | 类型 | 默认 | 说明 |
|---|---|---|---|---|
| — | **（无 feature flag——本版声明）** | — | — | **本版无任何 feature flag**：0.83.0 的全部行为面（B-1~B-4）随版本生效——所有变更默认生效、无灰度面、无 kill switch 需求。依据：① 本批均为既有检查面的判定口径修正（Check 16/Check 10 M5）、扫描面扩展（Check 14 子检查 6）与判定面校准（ArchGuard/DEC-201），不引入新运行时能力分支，不存在「新旧行为并存」的灰度前提；② 变更方向为消除过报/披露化/阈值校准，无「需要紧急关闭的新行为」形态；③ 回退通道 = 版本级回滚（见 `docs/release/rollback-plan-0.83.0.md`），无 flag 级降级需求 |

### 1.1 ArchGuard advisory 边界（非开关，如实登记）

Check 28n（module/function size）/ 28o（architecture health advisory）/ 28p（duplicate code）维持 **`fatal_on_error=false` 既有边界**——advisory 不阻断发布。本版（FIX-350/DEC-201）改变的是**判定面**（豁免 gate 四面扩展 + 三精确路径 dup 豁免 + release_docs 阈值 30→80），**不改变该 advisory 边界本身**。28o 残余 4E 为产品源真实 advisory（God-module 族——`verify_workflow.py` 24583 行，RISK-039 登记 + 棘轮锚定），如实披露。豁免的治理面：全部豁免走 [EXEMPT] 双面披露（DEC-151 不静默语义）——豁免 pair 计入 pairs_checked，无豁免 schema 行为不变（负例测试锁定）。

### 1.2 Check 14 子检查 6 与 Check 10 M5 白名单（非开关，如实登记）

- Check 14 子检查 6（Unicode 行/段分隔符扫描，8 字符族含 U+000C）为**既有 Check 14 段内新增子检查**——随版本默认生效，无 opt-in/opt-out 开关；
- Check 10 M5 record-doc 白名单扩展（`docs/requirements/**`）为**既有白名单机制的目录面扩展**（FIX-295 先例同族）——PATH-CLASSIFICATION only、豁免必披露（[EXEMPT]）、fail-closed 不弱化（其余 docs/ 子树全量扫描不变）。

## 2. 行为变更（用户可感知 —— MUST 写入 CHANGELOG 与升级说明）

| # | 变更 | 旧行为（0.82.0） | 新行为（0.83.0） | 理由 | 影响面 |
|---|---|---|---|---|---|
| **B-1** | Check 16 同 EVD fan-out 判定口径（FIX-349③） | 同一证据行服务多需求被判「模板复用」——live 假阳 19 条 | **不再判「模板复用」**——live 假阳 **19→0** | 同 EVD fan-out 是合法治理数据形态，判定为结构性过报 | Check 16 判定面；「模板复用」判据收窄方向为消除过报，Check 16 其余判据不变 |
| **B-2** | Check 14 新增子检查 6——Unicode 行/段分隔符扫描（FIX-349⑥） | 无该扫描面——不可见 Unicode 分隔符（EVD-890 实证形态）可致扫描假阴性且无制度化检测 | **新增 8 字符族（含 U+000C）行/段分隔符扫描**，覆盖 5 个治理热文件，命中报 WARN | EVD-890 一次性修复升级为制度化机检面 | 治理热文件扫描面；既有 live U+000B 残留已清除——如实填写的治理数据预期零新增告警 |
| **B-3** | ArchGuard 判定面校准（FIX-350；DEC-201） | fixture 投影镜像（`project/**`）与 `.governance/**` 进架构扫描产生误报；镜像 dup 无豁免披露通道；release_docs 阈值 30 已被 74 版本现状击穿（红）；ratchet 锚 R1 24453 | **豁免 gate 四面扩展**（module_size/function_size/module_constants/duplicate_constant 经 `_archguard_exclusion_match` 单一实现）——`project/**` 与 `.governance/**` 不再进架构扫描；**3 对镜像 dup 以 [EXEMPT] 双面披露**（pair 计入 pairs_checked）；**release_docs 阈值 30→80**（74 版本现状）；**ratchet 重锚 R1 24453→24583、R4 print 1299→1301**（七规则全 PASS + 套件 38/38 三红转绿） | 判定面与实际工程事实校准：fixture 镜像属预期投影（双写债登记 RISK-039，长期解 = 投影单源）；`.governance/**` 为宿主治理运行时数据非产品代码；docs/release 全历史保留为蓄意策略；重锚 = sanctioned 行数演进入账（+130 = FIX-348/349 预存 +85 + FIX-350 +45） | ArchGuard 扫描面与棘轮锚；28n/28o/28p **仍为 advisory（fatal_on_error=false 既有边界不变）**；机制不弱化——archive.py 与 verify_workflow.py 两对镜像保持受检，无豁免 schema 行为不变（负例测试锁定） |
| **B-4** | Check 10 M5 record-doc 白名单扩展（FIX-348；DEC-198） | `docs/requirements/**` 全量扫描——已交付设计文档中的 (a)/(b) 处置记录行被 `m5_option_list_no_auq` 误报为 agent 运行时指令（live 实例 `dsh-compat-design-0.81.0.md:292`） | **`docs/requirements/**` 纳入 record-doc 白名单**——设计文档处置记录行不再误报；其余 docs/ 子树全量扫描不变 | 已交付设计文档属记录类文本（FIX-295 对 docs/release + docs/reviews 同类扩展的延续）；边界保持 PATH-CLASSIFICATION only + [EXEMPT] 披露 + fail-closed 不弱化（前缀 trap `docs/requirements-notes.md` 永不匹配，测试锁定） | Check 10 M5 扫描面；base `check_m5_compliance()` 字节不变 |

> **升级提示（面向用户）**：B-1/B-4 是检查器**判定面过报消除**、B-2 是**新增告警面**（方向 = 检出能力增强）、B-3 是**判定面校准 + 披露化**——对如实填写的治理数据与产品代码零破坏；历史治理记录零改写（FIX-349 数据面为字段补全与通道标注，非改写既有终态；DEC-199 (a) 明确不改写历史审查记录）。无 breaking change；无新 CLI 命令；无新文件格式。

## 3. 新增的检查面与命令（加性，默认启用）

| # | 项 | 形态 | 默认 | 说明 |
|---|---|---|---|---|
| 1 | Check 14 子检查 6（Unicode 行/段分隔符扫描） | **既有 Check 14 段内新增子检查**——不加段、不加 CLI 命令 | 随版本默认生效 | 8 字符族（含 U+000C）× 5 治理热文件；命中 WARN（FIX-349⑥） |
| — | **（无新增 CLI 命令）** | — | — | 本版未新增任何 CLI 命令；棘轮口径（cli keys / segments 计数）由 M-2 门禁复跑核实——Check 14 子检查 6 为段内扫描面扩展，段计数是否变化以 M-2 当场值为准，**不预填** |

## 4. 建议的"降级/回退"开关（本版**未**提供，如实列出）

| # | 场景 | 本版处置 | 归属 |
|---|---|---|---|
| D-1 | 判定面变更后某检查在合法数据上误报（B-1/B-2/B-4 面） | **无 flag 级降级**——回退通道 = 版本级回滚（`docs/release/rollback-plan-0.83.0.md`；回滚即恢复 0.82.0 判定行为，含已知过报面回归，逐项见 rollback-plan §1）；无「按检查关闭」的运行时开关需求（历史上未提供，本版亦不新增） | 版本级回滚通道 |
| D-2 | ArchGuard 豁免面被质疑放行真实架构漂移 | **无 flag**——豁免面为配置面（module_size/duplicate_code exclusions + 阈值）而非开关；全部豁免 [EXEMPT] 双面披露可审计；如需收严 = 调整配置并走受审提交，如需临时回到 0.82.0 判定 = 版本级回滚 | FIX-350/DEC-201 配置面 + [EXEMPT] 披露（DEC-151 语义） |

**Kill switch 需求声明**：本版**无 kill switch 需求**——所有变更默认生效且方向为过报消除/披露化/阈值校准，不存在需要秒级紧急关闭的新行为面；紧急回退走版本级回滚（rollback-plan §2/§6）。

## 5. 与 0.82.0 的开关对照（无删除）

- 0.82.0 的既有开关**全部保留**，语义未变：`--quick` 影子通道、product-gate 跳过机制、`check-release --skip-execution-gates`/BR-4、`dsh-doctor` 四开关、loop-claims 豁免账本（`core/loop-runtime-claim-exemptions.json`——4 条豁免维持，digest 锚不变）等；
- 本版**未删除**任何开关、未删除任何豁免登记；
- 0.82.0 的行为变更 B-1~B-8（版本锚参数化/豁免披露机制/review_record 三键/authority 重锚/计数口径/CWD 守卫限定语等）**延续有效**；
- ArchGuard advisory `fatal_on_error=false` 既有边界**延续不变**（B-3 仅校准判定面，不改 advisory 边界）。

---

*M-0 草案冻结（2026-09-17，REL-079 prep）。事实基线：FIX-348/349/350 终态取自 plan-tracker 任务行、DEC-198~201、EVD-1064~1067 与对应 REVIEW 报告（机录）；「无新增 CLI 命令」「棘轮 cli keys/segments 口径」「28u/28v/28w 维持基线」由 M-2 门禁复跑核实（本文件为草案，不预填 M-2 实测值）。*
