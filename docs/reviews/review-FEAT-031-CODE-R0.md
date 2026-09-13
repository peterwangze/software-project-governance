# FEAT-031 代码审查报告（Code Review R0 — 切片 V8）

- **任务**：FEAT-031（0.81.0，P1；设计切片 **V8**）— Check 28w（K-1~K-13）+ `dsh-doctor`（S0~S7）+ 升级演练 + registry 接线
- **Round**：R0（首次审查）｜**审查对象**：11 M + 5 新增 = **恰 16 文件**；HEAD = `210b200`
- **Reviewer**：Code Reviewer Agent（只读；全部构造/变异在 `%TEMP%` 副本 + `DSH_HOME` 重定向；**仓库 763 tracked 文件 sha256 跑前/跑后 0 变化**；未执行任何破坏性 git 命令）
- **结论**：**APPROVED_WITH_NOTES / `unresolved_blockers=0`**（P0=0｜P1=3｜P2=4｜P3=7）
- **⚠️ 附发布条件**：**0.81.0 不得在 F-02 与 F-03 未闭环的情况下发布**（该 fixture 随 npm 包发布，设计 §5.4）

## 1. 硬门槛

| 门槛 | 阈值 | 实测 | 判定 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | 0 | PASS |
| 5 维度全覆盖 | 100% | 逐项有结论 | PASS |
| 每条发现标级别 | 100% | 14/14 带 P0~P3 | PASS |
| 设计一致性 | 已完成 | 对照 §2.8/§5.1-5.6/§6.1/§11.1 + ADR-018 + DEC-190/191/192；查出 3 P1 + 4 P2 + 7 P3 | 完成（有偏差，逐条登记） |
| AI 专项 5 项 | 全部完成 | mock 0 / 硬编码 0 / 幻觉 API 0 / TODO 0 / 过度实现 0（**欠实现 1 = F-05**） | PASS |

## 2. 硬基线独立复现（全部由审查方实跑，非采信自述）

| 项 | 实测 | 判定 |
|---|---|---|
| 三路径渲染 sha256 | `00e0d330f3560e10381b54b37a06fe6a626a451e3e70da8126b9c2bc47be3723`（`--stage S4` 双渲染器 parity PASS） | ✅ |
| 28u | exit 0 + `real-home writes: 0` | ✅ |
| 28v | exit 0；`23 / 18 / 5 (NO_SCHEMA=5)`；`isolated-home writes: 0` | ✅ |
| 契约 SHA | `96F92485…43FC6E` 未变 | ✅ |
| 六套件 | **115 / 70 / 77 / 120 / 120 / 50 全 OK**（另 quickscan_registry 82、contract_matrix 27、archguard_ratchet 38 全 OK） | ✅ |
| Check 28w | `--fail-on-issues` exit 0；13 判据 **12 PASS + K-7 NOT_RUN** | ✅ |
| archguard-ratchet | R1 24412≤24412、R2 47≤47、R4 1299≤1299、R5 cli 84/84 + segments 71/71、R6 196 Δ0、**R7 `regen deterministic=True; committed==fresh True`** | ✅ |
| `--selftest` | PASS（8 例崩溃隔离） | ✅ |
| 升级演练 | 6/6 FAIL（4 突变 + no-op + 时间倒置）；TTL 超期 = `[EVIDENCE-STALE]` **+ FAIL**；`synthetic` 逐条标记 | ✅ |
| 写隔离 | **763 tracked 文件 sha256 零变化（审查方独立复算）** | ✅ |

## 3. Findings

| # | 级别 | 位置 | 事实（已独立复现） | 建议 |
|---|---|---|---|---|
| **F-01** | **P1** | `checks/dsh_boundary.py:958-1002` | **K-7 第三条判据未实现**（设计 §2.8 明写「`cordis.patch.yml` 与 `lib/index.js` 内不得再出现 dsh 版本字面量」）。变异：向 patch 副本注入 `version: "0.1.5-rc.2"` → **K-7 不判定该事实**、K-2 亦 PASS（裸版本串不属其任何字面量类）⇒ **该回归路径无任何判据覆盖**（V7 的保证在 28w 上无守护，RISK-050 成因面可无成本回归）。当前仓库事实干净 | K-7 内加 patch/lib 版本字面量扫描，或在设计登记该 clause 收窄 |
| **F-02** | **P1（发布前必须闭环）** | `adapters/dsh/fixtures/host-facts-0.1.5-rc.1.json` | **提交的 fixture 非 `--record-evidence` 产出，provenance 与自身 plane 矛盾**：`provenance`/`notes` 与工具实际发出的文本**逐字不同** ⇒ 至少被人工改写（违反设计 §5.4「只能由 `--record-evidence` 写，禁止人工誊抄」/§2.7 单点写入）；且 fixture 自身 `plane.node_modules = C:\Users\peter\.dsh\profiles\node_modules`、`plane.source = "DSH_HOME/profiles"` ⇒ **记录时探测的是真实平面（未隔离）**，与 §5.5[A]/§5.1 不符，且**该真机读命令在 `.governance/evidence-log.md` 无 R4 逐条上报行**。**正面事实（不得过度指控）**：数据面与工具输出**结构全等**（键集、`oracle_packages` 版本/路径真实、`rows` 29 条、`source: recorded`）⇒ *记录的事实为真*、`synthetic:false` 对数据为真 | 原样重录（或恢复工具自身文本）+ 说明文字移入设计/发布文档 + **补 R4 上报行**；修复前 **不得**随 0.81.0 发布该 fixture |
| **F-03** | **P1** | `dsh_doctor.py:1554-1629` | **`--record-evidence` 不写契约 `evidence.*`**（设计 §2.7/§5.5 定义其为「唯一契约证据写入路径」）⇒ K-7 恒 `NOT_RUN`，而 K-7 的 remediation（`dsh_boundary.py:996`）与 S3 的 remediation（`dsh_doctor.py:677-680`）**承诺"run --record-evidence … to make the TTL and version comparison available"，按文档执行不可能兑现**。裁决（作者请求）：方向（不让探针机变契约）**可接受**，但**当前形态不可作为终态** | 至少 (i) 改写两处 remediation 与实现一致，(ii) 在设计 §2.7/§5.5 或 DEC 中登记「契约证据改为维护者受审提交更新」的口径收窄；否则 §2.7 的"单一写入点"并不存在 |
| F-04 | P2 | `dsh_boundary.py:441-450` | K-2 扫描面比设计窄：设计声明 9 消费者中含 `adapter-manifest.json`/`package.json`/`cordis.patch.yml`，实现只扫 8 个 ⇒ 向这 3 文件注入契约外包名字面量 → **K-2 PASS（未覆盖）**；向已声明消费者注入 → FAIL 且带 `file:line`（判据本身有效） | 补 3 个消费者或 DEC 登记收窄 |
| F-05 | P2 | `dsh_doctor.py:972-1018` | `--allow-host-probe` **无效果**（授权后 S5 恒 `NOT_RUN`）；设计 §5.1「否则拒绝（exit 2）」与 §5.2「授权后 entry 列表超'恰多一行' → FAIL」**未实现**；实测 exit 2 仅由用法错误触发 | 补 exit 2 拒绝码或登记收窄 |
| F-06 | P2 | `dsh_doctor.py:1554-1622` | `--out` **无守卫**：把契约副本交给 `--out` → **被静默覆盖**；docstring 称 refuse 与实现不符（默认目标就在包内） | 拒绝命中 `canonical_product_artifacts`/契约路径 |
| F-07 | P2 | `dsh_doctor.py:406-434, 492-578` | `--stage` 子集不含 S0 ⇒ 归因误导（`--stage S1 --offline` 报「no resolved DSH_HOME」而实际可解析） | 子集自动补跑 S0 或在 reason 显式归因子集 |
| F-08~F-14 | P3 | 设计/EVD-1029/`dsh_doctor.py`/`dsh_fixtures.py:432`/`adapter-manifest.json`/`dsh_boundary.py:1664-1671`/新文件 | 计数漂移（设计写 `FROZEN_CLI_KEYS=83` 实测 **84**；**EVD-1029 叙述的 `126→24405` 与 `1731/1787` 行与实测 `133→24412`、`1758/1810` 不符**，其 `anchor_math` 字段正确）· 自述"正例 30/反例 79/元判据 6"不可复现（总数 115 ✓）· docstring 称 offline 仍跑 28v 而实现返回 None ⇒ S2=NOT_RUN · `DEFERRED["FX-BASEURL-01"].slice=="V2"` 陈旧 · `adapter-manifest.json` 未登记 `dsh-doctor`（设计 §2.9.4/§6.1 明列）· K-12 第五字段判据为整文件字符串存在性（措辞强于实现）· 新增文件行尾不一致（`.gitattributes` 会归一化，无提交面影响） | 逐条更正/登记 |

## 4. 独立复现结论（12 项要点）

1. **K 判据真实性**：13 条均有实质实现（**非空壳**）；审查方在 `%TEMP%` 副本上**独立变异 11 条**（K-2~K-13）逐条得到预期 FAIL。**K-6** 真抓 `- id:` UPDATE / `trust:` / `!!js` / 第二条 insert（注释散文不误报）；**K-8** `strong` 无负相 fixture → FAIL（出厂 14/14 带负相）；**K-11** 额度 0 **拦住 1 条合法豁免**，改锚点文件为 1 后同一豁免通过 ⇒ **天花板确在契约外**；**K-12** 单一生成点 + 第五字段 + 命令键注册三条注入均 FAIL。
2. **阶段隔离/退出码**：审查方**自行 patch `_stage_runners`**（不用实现的测试缝）注入 S0/S3/S6/S7 崩溃 → 崩溃阶段 `NOT_RUN` + `stage_error:true`、**恒 8 条记录**、其余照跑；**exit 0/1/2 正确稳定**；`--offline` 适用域与实现一致（**文件级判据照跑且可真 FAIL**，进程级降 `NOT_RUN`）。
3. **S2 投影**：`_projected_coverage` **逐字段复制**（投影 == 源，含第 5 字段），S2 `credible_face` 与源全等 ⇒ **不重算**。
4. **K-12 双向一致**：独立注入分歧 → `compared:true, agrees:false` + 追加 K-12 FAIL + exit 1（**独立复现 FX-VERDICT-01**）；`--offline` → `compared:false, agrees:null`。
5. **演练隔离**：审查方在 `%TEMP%` 自造 6 例复跑 —— 4 突变全 FAIL 且逐条 `synthetic:true`；no-op FAIL；时间倒置 FAIL；TTL 超期 FAIL；**仓库 763 文件 sha256 零变化（独立复算）**。
6. **两次 `--regen`**：R7 机器自证幂等；**仅两份产物被改写**；**+208 拆解独立复算成立**（`24204(FIX-310) + 75(FIX-319/321) + 133(V8) = 24412`，实测 vw 行数逐一吻合；**两个新模块确实不在 mainfile 面**）。
7. **范围修正 + 三处冻结点常量**：`allowance_lines` 仍 **0**、无夹带；**「确定性后果」认定成立**（三处常量与 `snapshots.json`/baseline 实测一一对应，不改即红）。
8. **`git stash` 影响**：11 文件 diff 均为小范围编辑（最大 `+133/−5`，**无整文件重写**）；5 个新文件齐备可执行 ⇒ **结果无实质影响**；逐字节等同**不可证**（审查方如实声明）。其用途由审查方以 **`%TEMP%` 树手术**独立复现 ⇒ 同 3 条失败 = **FIX-320 既有失败**。
9. **范围纪律**：恰 16 文件、仓库根零 scratch、零夹带、`git stash list` 空。
10. **硬基线**：见 §2 全通过。
11. **AI 专项**：mock 0（`inject`/`compat_runner`/`smoke_runner` 为显式测试缝，生产走真实路径）/ 硬编码 0 / **幻觉 API 0**（逐一 `inspect.signature` 核实 6 个跨模块 API）/ TODO 0 / 过度实现 0。
12. **`check-governance` 归因**：全量清单检索产品面关键词（`28w|dsh-doctor|K-*|registry|dsh_boundary|dsh_doctor`）**零命中**；审查方在 `%TEMP%` 重建「pre-V8 产品 + 同一治理记录」树复跑，**差异仅 1 行**（`[WARN] 25: 5 untracked files`）⇒ **零产品回归，作者归因成立**。

## 5. 对两处偏离与五项未覆盖的独立判定

- **偏离 A（`git stash push -u`）**：**结果无实质影响，方法违规但已登记**（可证部分全通过；不可证部分如实声明）。其对照结论经独立复现一致 ⇒ 无需追溯代码；`EVD-1030` 的登记与纪律约束恰当。
- **偏离 B（三处冻结点常量 + `archguard_ratchet.py` 范围修正）**：**「确定性后果」认定成立**；`allowance_lines` 保持 0、无夹带。**建议**：补入授权面记录，并按 F-08 更正 `EVD-1029` 叙述数值。
- **未覆盖①**（manifest 未登记 `dsh-doctor`）：属实须补（设计明列该文件）。
- **未覆盖②**（`FX-BASEURL-01` slice 陈旧）：属实，随下次触碰更正。
- **未覆盖③**（`--record-evidence` 不写 `evidence.*`）：**不接受为终态** —— 方向可接受，但必须修 remediation + DEC 登记收窄（**F-03**）。
- **未覆盖④**（S5 只报告不代跑）：可接受为"有意收窄"，**但必须登记**（§5.1 exit 2 / §5.2 授权后判据是设计明写项）→ F-05。
- **未覆盖⑤**（`test_verify_workflow` 3 条既有失败）：可接受（**审查方以树手术独立复现为 pre-V8 同 3 条** ⇒ FIX-320）；M-2 须继续披露。

## 6. 结论与下一步

**APPROVED_WITH_NOTES / `unresolved_blockers=0`**，附**发布条件**（F-02、F-03 必须闭环）。

**处置**：退回同一 Developer 修 **F-01（K-7 第三条判据）+ F-02（fixture provenance 重录 + R4 上报）+ F-03（remediation 改写 + DEC 口径登记）**，同批 **F-04（K-2 补 3 消费者）/ F-06（`--out` 守卫）/ F-07（S1 子集补 S0）**；**F-08 的 EVD-1029 数值更正为 Coordinator 侧动作**（已执行）；F-05/F-11/F-12/F-13/F-14 登记或并入后续任务；随后按 M7.4 step 4.6 以 **R1** 复审。

## 7. 真实环境命令上报表（R4）

8 类命令全部只读或落 `%TEMP%`：`resolve_entry`/`git` 只读；九套件在 `%TEMP%` 隔离 home；`check-dsh-boundary`/`archguard-ratchet`/`check-governance` 只读（内部 28u/28v 报 `writes: 0`）；`dsh-doctor` 各开关只读；变异 harness 对**副本**变异；`record_evidence(out=%TEMP%)` ×2；pre-V8 树重建用 `git archive` + 副本覆盖；**763 tracked 文件 sha256 跑前/跑后 0 变化**。**R1 依据**：全部真实平面相关运行为 **(a) 隔离环境（`DSH_HOME` 重定向 `%TEMP%` 一次性目录）**；**零真实 `~/.dsh`/`~/.agent-presets` 写**；零破坏性 git 命令。**保留项**：唯一的真实平面读取发生在**作者侧**的 `--record-evidence`（F-02），其 **R4 上报缺失，请 Coordinator 补登或追认**。

---

*报告结束（R0，APPROVED_WITH_NOTES / unresolved_blockers=0；发布条件：F-02/F-03 必须闭环）。*
