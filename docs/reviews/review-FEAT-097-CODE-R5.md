# FEAT-097 Code Review R5 — 性能验收失败后的独立可交付性审查（仅 delta）

- **轮次**: R5（独立可交付性审查——非返工复审；R4 AWN/0 已机录，实现/契约面不重审）
- **前轮引用**: `docs/reviews/review-FEAT-097-CODE-R4.md`（R4 结论 APPROVED_WITH_NOTES，unresolved_blockers=0）
- **审查方**: Code Reviewer Agent（与 R1~R4 同一实例；只读审查——本轮零新测量/零新扫描/零 suite 重跑；唯一写面 = 本报告；未改代码/断言/门限/快照/治理状态，未 commit）
- **审查对象**: 诊断报告 `docs/reviews/performance-FEAT-097-attribution.md`（237 行，§8 含 Coordinator 修正）、incidents raw 工件（shape-command-records.json / shapeI.py / shapeI.json / profile3rd.py / profile_tottime.txt / setup_facts.json）、交付审计 `.governance/reports/FEAT-097-delivery-audit.md`、两个原预算源（test_loop_runtime_claims.py:1086-1173 / test_verify_workflow.py:108-138）
- **结论**: **BLOCKED**（验收性能红灯未解决，维持交付阻断，升级用户裁决）

```json
{"verdict": "BLOCKED", "unresolved_blockers": 2}
```

---

## 0. 结论与理由

**实现审查通过 ≠ 当前交付验收通过**（验收标准 ③ 显式裁定）：R2（实现）/R3/R4（契约）的 AWN/0 覆盖代码与快照面；交付门是独立事实——当前**两个原预算验收在原形态、原断言、原门限下失败**：CPU 守卫三窗全 RED（34.953125 / 34.234375 / 复刻中位 31.515625，全部 ≥ 27.8）、wall 36s 低于全部三个完整 CLI 样本（37.400~39.439）且套内三次 TimeoutExpired（36.043/36.075/36.077）。诊断报告**不能替代通过**——其自身 §8 与 incidents 机录明确承认：根因（形态/GC/环境/算法）未被唯一分解。

**BLOCKED 而非 NEEDS_CHANGE 的依据**：①协议面——本票 NC 轮次计数已达 3+（R0/R1 NC + 本轮），按 SKILL「超过复审 fuse 的 NEEDS_CHANGE 必须升级为 BLOCKED」与角色规则 round≥3 仍 BLOCKING → 转 BLOCKED；②实质面——两条可行处置路径中，预算再校准/测试形态重设计/接受失败均为 scope/risk 变更（M5.3 用户门，诊断报告 §6/§8 同意见），唯一不动预算的路径（scanner 资源优化）因根因未证而**成功不可承诺**（「不能凭 GC 假设承诺根因」对称地禁止凭优化假设承诺修复）——这不是「退回 Developer 即可闭环」的缺陷，而是需要风险所有者裁决的验收阻断。`unresolved_blockers=2`（§3 B1/B2，机读整数）。

**措辞边界**：不宣称全 suite 修后 single 绿；1115 稳定跑=1114 通过+1 时间错误是**失败态**而非接近通过；未验证项 §6 明示。

---

## 1. R4 findings 是否改变 / 新引入（验收标准 ①）

**无改变、无新引入**（一手）：`git diff --cached` 输出为空（staged 空，:index==HEAD）；mtime 面全部保持复审期状态——test_loop_runtime_claims.py 与 checks/loop_runtime_claims.py 10-10 16:14、verify_workflow.py 10-10 23:15、test_verify_workflow.py 10-10 23:29、goal_bridge.py 10-10 23:56、test_goal_bridge.py 10-11 9:39、snapshots.json 10-11 10:19（R4 态）。诊断/审计/观测全部在仓库外隔离目录进行（command-records.json protection 字段机录）。R4 的四项 PASS 判定不受影响。

## 2. 事实 / 算术 / 观测器核验（验收标准 ②——不照抄作者 story）

| # | 核验项 | 判定 | 证据（一手 raw） |
|---|--------|------|------|
| 1 | 原 CPU 断言与锚定 | **属实** | `test_loop_runtime_claims.py:1086-1173`：`:index` 物化在计时区外（:1095-1097，FIX-240）；计时区仅 `scan_loop_runtime_claims`（:1107-1110，process_time）；`:1173 assertLess(median, 27.8)`；锚定注释 :1140-1145（2026-09-28 f06a2bf：15.453/18.547/23.406 → p50 18.547×1.5=27.8，我复算 27.8205 ✓；半额 13.9<min 15.453 反向约束 ✓）；:1170-1172 明示 DEC-262 documented-load 再锚定为协议内路径（attribute first） |
| 2 | 原 wall 超时与规程 | **属实** | `test_verify_workflow.py:108-138`：`timeout=36`（:131）；DEC-262 26→36 史实（24×1.5=36 ✓）；FIX-346 纪程=同会话三样本 p50×1.5 + 半额保持 RED（:114-126）；断言 RC=0/PASS/parsed==candidates/skipped==0/truncated==0 |
| 3 | CPU 三窗 RED + 身份 | **属实** | 归因报告 §1-4/§3.2（02:45 窗 31.766/34.953/36.281 → 中位 34.953125）与 §8-②（03:05 窗 34.234375）；复刻 in-process 29.203125/31.515625/36.25 中位 31.515625（shapeI.json `cpu_median`/`lt_27_8_info_only:false` 机录）；身份三连 1128/24,679,503/332,948/`fb1b0cbf…` 恒定 PASS；staged 空（我方复核）→ :index 树不含本票 WIP 前提成立 |
| 4 | wall 三样本 + 套内超时 | **属实** | §3.1 表：39.439/37.400/39.122（RC 0/PASS/1222/0/0）；§1-1/1-2：稳定 1115/801.783s=1114+1 超时；原测 3×36 超时（36.043/36.075/36.077） |
| 5 | 算术复核（独立重算） | **全部成立** | ceil(39.122×1.5)=ceil(58.683)=**59** ✓；半额 29.5<min 37.400 ✓；34.953125/27.8=+25.7% ✓；25.172 余量 9.45% ✓；µs/unit 75.60 vs 104.98（+38.86%）✓；C/H：CPU +13.37%≈bytes +13.45%（线性重合）✓；每字节 −0.066%（1.0200 vs 1.0207）✓；形态中位差 31.515625/25.953125=+21.43% ✓；fresh 中位 25.953<27.8<31.516 in-proc（判定分裂事实）✓；语料 332,948/301,452=+10.45%、24,679,503/21,752,751=+13.45%、1128/980=+15.1% ✓ |
| 6 | 「不可排除」边界（ Coordinator 修正） | **raw 证实** | `shapeI.py:12` `"traced": sys.gettrace() is not None`——**只测 gettrace，不测 tracemalloc.is_tracing**（脚本无 tracemalloc 调用；8.5 仅查询进程 PYTHONTRACEMALLOC=ABSENT，不回溯子进程）✓；gc_collections 1→188→318→459 为**进程启动以来累计计数**（增量 187/130/141），不证保留对象/GC 压力上升 ✓；顺序批次（in-proc 批后 fresh 批）不隔离形态与时间窗 ✓；profile 无历史对照不排除算法回归 ✓——四条因果边界在 command-records.json `causality_boundaries` 机录 |
| 7 | profile 预热超限 + 零扫描失败 | **raw 证实** | `profile3rd.py:7-11`：两次未计时预热+一次剖析=3 调用（6+3=**9** > 授权 6+1）；command-records 8.4 机录「Two warmups exceeded…total this diagnostic 9. Not used to relax budgets」；8.1/8.2 两轮 wrapper 失败 exit [1,1,1,1]×2 **发生在计时前、零扫描消耗**（KeyError 'threshold'→AttributeError get_thresholds→修正 get_threshold）✓ |
| 8 | 热点数字 | **raw 证实** | profile_tottime.txt：compile 9.738s×181、`_build_python_claim_provenance_index` 6.313（cum 12.147）、`_python_parse_bundle` 6.053（cum 22.201）、isinstance 18,063,231 次 4.856、iterencode 357,788 次 4.832、剖析总 70.472s（非校准样本）✓ |
| 9 | 交付审计一致性 | **一致** | delivery-audit.md D4=BLOCKED（验收性能红灯）与我的独立核验同向；D1=ON-TRACK（范围无偏差）与「性能失败非本票 WIP 直接所致」（:index 不含 WIP + 语料增长 0.90→0.98 批次累积）相容 |

**结论**：诊断报告的**事实层与边界层可信**（多处我以 raw 脚本/JSON/热点文件直接证实，非转述）；其**归因层正确地未越界**（§8 明示「不能声称诊断原因闭环」）。但事实层的直接推论是：**验收在原口径下失败**——这是本轮裁定的基础。

## 3. Findings

### B1（P1·阻塞·验收）原 CPU 守卫在原形态原断言下三窗全 RED——交付验收失败

- **位置**: `skills/software-project-governance/infra/tests/test_loop_runtime_claims.py:1173`（assertLess median 27.8）
- **事实**: 三窗 RED（34.953125 / 34.234375 / 复刻 31.515625），身份恒定 PASS，:index==HEAD（本票 WIP 不在被测树）。语料较锚定期 +10.4% units（已提交流量）与窗口/形态因素共存，**根因未唯一分解**（§2-6）。
- **影响**: 票面 done_definition「全套件回归零退化」与 quality_budget.reliability 不达标；不能交付。
- **处置边界**: 不得用 fresh 形态中位 25.953/25.172 替代原断言（形态混淆已证）；不得以 GC 假设承诺「优化必绿」。

### B2（P1·阻塞·验收）wall 36s 超时低于全部已观察完整 CLI 样本——套内必然超时

- **位置**: `skills/software-project-governance/infra/tests/test_verify_workflow.py:131`（timeout=36）
- **事实**: 三完整样本 37.400/39.122/39.439 全 >36 且套内 3×TimeoutExpired；FIX-346/DEC-262 规程数值=ceil(39.122×1.5)=59（半额 29.5<37.400 保持咬合）——**仅为数值依据，未执行**（前置门正确拦截）。
- **影响**: 稳定 1115 必然含此失败；与 B1 共同构成交付阻断。

### P3-R5-1（讨论·过程偏差，已披露不扩大）诊断过程两处偏差

- profile 命令双预热超限（总 9 扫 > 授权 7）；两轮 wrapper API 失败（零扫描消耗）。均已在 command-records 机录并披露、未用于改阈值——无需行动，留痕即可。

### 边界确认（正面，非 finding）

四条因果边界、setup_facts 双侧 SHA 相等（42925298…，关闭路径混用）、六扫恰用尽授权——raw 证实，诊断纪律整体成立。

## 4. 五维度结论（硬门槛 ②；可交付性 face）

| 维度 | 结论 | 依据 |
|------|------|------|
| 正确性 | **FAIL（验收）** | B1/B2：两个预算断言在原口径下 RED——这是验收事实，非代码逻辑错误（语义身份全 PASS） |
| 安全性 | **PASS** | 无门限/断言/fail-closed 逻辑改动（§1）；诊断未绕过任何门（前置门正确拦截 wall 校准） |
| 可维护性 | **PASS（带 P3-R5-1）** | 诊断工件可追溯（incidents 机录+双侧哈希+原始 JSON）；边界措辞经 Coordinator 修正后与 raw 一致 |
| 性能 | **FAIL（验收）** | 即 B1/B2 本体；归因三层分解（语料实证/单位成本近似持平/窗口-形态未分解）诚实但未闭合 |
| 测试覆盖 | **PASS（带边界）** | 功能/安全断言无新失败（审计 D4）；性能断言本身即为失败载体 |

## 5. AI 代码专项 5 项（硬门槛 ⑤；本轮无代码 delta）

无代码变更 → 五项对诊断脚本面核验：无 mock 残留（观察器零语义修改、不重复扫描——shapeI.py raw）；无硬编码（阈值读自 gc API）；无幻觉 API（两轮失败恰证 wrapper 先对不存在 API 试错后修正——**零影响测量**）；无 TODO；无过度实现（除已披露的双预热）。**通过（诊断面）**。

## 6. 最小处置选项（供用户 M5.3 裁决——本报告不选择、不承诺）

- **Option A（不动任何预算的 Developer 有界修复）**：保持 27.8/36s 原样，对 scanner 跨扫描资源做有界优化——raw 热点线索：181 文件反复 `compile`（9.74s，进程内三扫重复编译同批文件）、provenance index（6.31s）、parse bundle（cum 22.2s）、isinstance 18.06M 次、iterencode 357,788 次；in-process 单调上升（29.2→31.5→36.3）与跨扫保留假设方向一致但**未证实**。成功判据：原形态原断言逐字复验全绿（CPU 三扫中位<27.8 + 套内 CLI<36s）。**风险**：根因未分解（形态/环境贡献未知），成功不可承诺；须限定一轮返工+复验，禁止开放轮次。**无需用户门即可开工，但交付仍以原验收为准。**
- **Option B（用户门 M5.3：受管再校准/形态裁决）**：(B1) wall 36→59 按 FIX-346/DEC-262 既有规程（数值依据如上，半额反向约束保留）+ CPU 走断言注释 :1170-1172 自带的 DEC-262 documented-load 再锚定路径（以归因报告为 attribute-first 记录，**再锚定值须来自新的校准会话三样本 p50×1.5，不得直接取诊断数字**）；或 (B2) 测试形态重设计（fresh-进程断言，需论证不弱化 tripwire）。**风险**：改变看护语义/基线=接受新风险面；三样本小基数的窗口敏感性已知（同树两窗中位 25.172 vs 34.953）。
- **明确拒绝**：接受失败当通过 / 静默豁免 / 「先再测无限轮」取代处置 / 用诊断报告替代验收。

**未验证项明示**：归因 §3.3 六扫逐文件 JSON 与第二次 RED（03:05 窗 34.234375）原始读数、稳定引擎日志尾——本轮未逐件重读（依据=诊断报告+审计+派发三方一致，raw 路径已存 incidents）；全 suite 修后状态未测（不存在「修后 single 绿」宣称）。

## 7. 验证命令记录（本轮全部只读）

| id | command | start(UTC) | end(UTC) | exit | affected_paths | protection |
|----|---------|-----------|----------|------|----------------|------------|
| CMD-1 | git status（20 行）+ git diff --cached --stat（空）+ 7 文件 mtime/Length | unknown（单戳） | 2026-10-11T03:33:24.76Z | 0 | 无写入 | 纯只读 |

其余为 read 工具只读面（R4 报告/诊断/审计/两预算源/6 个 incidents 工件）。零新扫描、零 unittest、零 suite、零隔离目录创建（无写入需求）。

## 8. 硬门槛自检（输出前）

| 门槛 | 判定 |
|------|------|
| P0=0（无新增代码缺陷）+ 阻塞项计数明示 | ✓（本轮阻塞=验收级 B1/B2，`unresolved_blockers=2` 机读整数；无 P0 代码缺陷） |
| 5 维度 100% 覆盖 | ✓（§4，含 2 个 FAIL 如实） |
| 每条发现 P0~P3+位置+事实+建议 | ✓（§3） |
| R4 findings 改变/新引入核验 | ✓（§1：无改变无新增） |
| 事实/算术/观测器独立核验（不照抄 story） | ✓（§2 九项，含 raw 脚本级证实） |
| 实现通过≠交付通过 显式裁定 | ✓（§0） |
| 不为交付勉强通过；BLOCKED+escalation | ✓（协议 fuse + 用户门实质双重依据） |
| 事实依据红线 / 措辞边界 | ✓（未验证项 §6 明示；无全绿/发布宣称） |

## 9. 给 Coordinator 的机录与后续

- **review-record**：`--task FEAT-097 --round 5 --result BLOCKED --report docs/reviews/review-FEAT-097-CODE-R5.md --reviewer 'Code Reviewer' --scope delta --delta-base docs/reviews/review-FEAT-097-CODE-R4.md`——BLOCKED 结束链路且必须 escalation（M5.3 用户裁决，携 §6 Option A/B 与 tradeoff）。
- **锁释放**：R5 报告锁随结论回收。
- **后续**：用户裁决后若走 Option A → Developer 有界返工 + 原口径复验 + 同一 Reviewer R6 delta；若走 Option B → 校准会话 + 受管改面 + 独立复审；两者均不得以诊断替代验收。
