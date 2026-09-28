# Code Review 报告 — FIX-400 R0（check-release 180s 墙钟预算再校准）

| 项 | 值 |
|---|---|
| 审查轮次 | **R0**（round=0；脚本面后置审查——治理基础设施脚本修改 → Code Reviewer） |
| 审查对象 | ① `skills/software-project-governance/infra/verify_workflow.py` ② `skills/software-project-governance/infra/tests/test_verify_workflow.py`（工作树现行态，未提交修改） |
| 日期 | 2026-09-28 |
| 审查人 | Code Reviewer Agent（只读；Write/Edit/Bash 零调用；未与用户交互） |
| 审查依据 | agents/code-reviewer.md + skills/code-review/SKILL.md + DEC-262(1)/FIX-346 先例 + DEC-264(2) 机录锚 + plan-tracker FIX-400 行（TRIAGE-FIX-400；用户 ask 裁决 2026-09-28） |
| 结论 | **APPROVED_WITH_NOTES（unresolved_blockers=0）** |
| 硬门槛 | P0=0 ✓ / 5 维度全覆盖 ✓ / 每条发现带级 ✓ / 设计一致性已完成 ✓ / AI 专项 5 项全完成 ✓ |

## 1. 审查重点逐项结论（票面重点 1-7）

### 重点 1 正确性 — PASS
- **算术核实**：1554.78 × 1.5 = 2332.17，ceil = **2333**（verify_workflow.py:6091 注释与 :6099 常量一致；2333 全仓 10 处出现无一拼写漂移）。
- **`_resolve_release_gate_timeout` 语义未变**（:6103-6119 逐行）：strip→空取默认 / ValueError 取默认 / >0 取值否则默认——fallback-not-crash 契约保持；SPG_RELEASE_GATE_TIMEOUT env 优先（FIX-234）保持。测试 L7754-7765 三族（正整数覆盖 / 带空白 / 非法值族 "abc","12.5","0","-5"," "）与实现逐条吻合。
- **消费面传递链未误改**：面 A `run_release_execution_gates`（:6166-6184）四子进程 verify / check-governance --fail-on-issues / e2e-check / unittest test_verify_workflow.py -v——timeout=None 时 runner 自解析、显式 timeout 转发、两参 runner 契约保持（测试 L7767-7817 三族不变）；面 B `run_dsh_upgrade_regression_gates`（:7142-7144）→ `check_dsh_preset_smoke(timeout=…)`（签名 :7033 `root=None, timeout=120`——显式传参覆盖其本地默认，链路正确）。全仓 `_RELEASE_GATE_TIMEOUT_DEFAULT` 引用 13 处：两授权文件 + docs/ 三份 0.80/0.81 历史记录（历史文档不可回改，非消费面）——零外部断裂。

### 重点 2 溯源纪律（本票核心）— PASS（silent raise = 0）
注释块（:6075-6098，实数 24 行）逐要素核对：
| 要素 | 内容 | 交叉验证 |
|---|---|---|
| 旧值→新值 | 180→2333（:6075） | ✓ 与 plan-tracker FIX-400 行一致 |
| 先例纪律 | DEC-262(1)/FIX-346，明示 "NOT a green-wash"（:6076-6077） | ✓ DEC-262 L204 实锚（p50×1.5 公式+注释溯源先例） |
| 历史成因 | 180s 源于 FIX-234；0.80.0 REL-077 ~258s / 0.84.0 273.4s / 0.91.0 M 1554.78s 趋势（:6078-6080） | ✓ 258s 实锚 review-REL-077-RELEASE-R0.md:197（258.1s）；273.4s 实锚 release-checklist-0.84.0.md:147/179 |
| 机录锚 | DEC-264(2) + pwsh-167 M-1（4351P/1F/1S/540 in 1554.78s）+ M-2 双源 pwsh-170/171（4359P/0F/1S/527）（:6081-6090） | ✓ DEC-264 L206 逐字一致（pwsh-167 为锚）；EVD-1210（evidence-log L2871：pwsh-170 1364.03s / pwsh-171 1394.55s 同值双源） |
| n=1 p50 代理明示 | "Single observation … (n=1, disclosed)"（:6090） | ✓ |
| 公式 | p50×1.5 = ceil(1554.78×1.5) = 2333（:6091） | ✓ |
| 反向验证 | halved 1166.5s < 1554.78s 观测 → 预算仍有咬合力（:6092-6093） | ✓ 算术复核成立——「不单为转绿拍数」红线满足（预算=公式输出、非拍脑袋转绿；方向取 M-1 FAILING 实测高值，保守侧） |
| 范围界定 | 四子进程 + FEAT-016 preset smoke（:6083-6086） | ✓ 与实际消费面一致 |
| 票号+日期 | FIX-400 (2026-09-28)（:6075） | ✓ |
| env 优先保留 | :6098 明示 | ✓ |
本轮佐证（15.844s 代表子集 / 948 静态方法数）在注释内如实标注为 same-session corroboration、明确"校准基准仍为机录全量锚"（:6094-6097）——口径不混淆。**静默抬值 = 零**。

### 重点 3 断言同步完整性 — PASS
- 方法改名 `…_defaults_to_180` → `…_defaults_to_budget`（test:7744）：全仓 grep 旧名 **0 命中**——零外部断裂。
- 新增常量值锁定断言 `assertEqual(vw._RELEASE_GATE_TIMEOUT_DEFAULT, 2333)`（test:7750）✓；empty/None→2333（:7751-7752）✓；非法值族→2333（:7763-7765）✓；FEAT-016 env-free 默认→2333（:7984-7997，清 env 后断言）✓。env 覆盖族（300/999）正确地**未**改动（钉的是 env 值非默认值）。
- 残留 "180" 精确盘点：verify_workflow.py 3 处（:6075/:6078/:6107）+ test 2 处（:7746/:7996）——**全部为溯源/历史限定语（纪律要求载明旧值），零未注记操作性残留**；test:2991 gemini e2e `--timeout 180` 为无关 CLI 字面量（票面预期项，符合）。票面「预期仅 test L2991」应精确理解为"唯一无关残留"；其余 5 处属溯源正文，合规。

### 重点 4 越界检查 — PASS（静态代理核实；边界见 P3-2）
- glob mtime 代理：infra 子树 154 个 .py 中最近修改的两位恰为两授权文件（其余 152 个均更早）。
- 行数交叉印证：verify_workflow.py 现行 **26413** 行 = archguard 棘轮锚 26385 + **28** 净增——与上报"注释净增 28 行"精确吻合（亦是已知预期红 R1 的成因，非本票缺陷）。
- 上报清单逐项在工作树现行态找到对应实体（常量+24 行块+4 处 docstring/注释；测试 3 处同步+改名+锁定断言），未发现清单外代码改动。精确 hunk 边界的 git 级复核属 Coordinator 提交前门（本角色 Bash 禁用）。

### 重点 5 docstring 一致性 — PASS
4 处去硬引用逐一核实：`_resolve_release_gate_timeout`（:6107-6108）、`_run_release_validation_command`（:6125-6127）、`run_release_execution_gates`（:6170-6173）、FEAT-016 注释块（:7120-7122）——均改为"module default + FIX-400 再校准 + 溯源驻留常量处"指针式表述。单一事实源模式（溯源只在常量处）避免多处注释漂移——语义准确、无过时口径。

### 重点 6 AI 专项 5 项 — 全过
mock 残留=无（新增零 mock；存量 fake_run/fake_runner/smoke 为 FIX-234/FEAT-016 合法测试缝）/ 硬编码返回值=无（2333 即票面交付物，有溯源+测试锁定）/ 幻觉 API=无（全部符号存在；全部引用锚 DEC-264(2)/pwsh-167/pwsh-170/171/DEC-262(1)/FIX-346/REL-077/0.84.0 均在仓内解析成功）/ 未实现 TODO=无 / 过度实现=无（24 行块每句对应一项必载溯源要素，对照 FIX-346 先例：本票爆炸半径为模块级默认×5 门禁路径 vs 先例单测预算，密度成比例）。

### 重点 7 baseline-register 不登记理由 — 论证成立
Read `baseline_metadata.py`（L1-80）+ `.governance/baselines.json` + CLI 映射面（verify_workflow.py:99/:26385-26386）核实：(a) register 唯一写目标是 baselines.json，evaluate 是其唯一消费语义，而 evaluate 调用面仅 CLI 手动命令——timeout 常量无任何 evaluate 消费流，登记即死行；(b) 登记面现状仅 1 条（check-loop-runtime-claims.candidate-bytes）——有真实消费检查器的数值门才登记，先例自洽；(c) FIX-346 先例（26s→36s）即以注释溯源承载、未登记，DEC-262(1) 原文「baseline-register **如适用**」为条件式授权。Developer 论证（无消费流死行 + 先例族走注释溯源）**成立**；实际执法面已由断言锁定（test:7750）+ 注释溯源 + DEC-264(2) 机录三层覆盖。

## 2. 审查维度五表
| 维度 | 结论 | 依据 |
|---|---|---|
| 正确性 | PASS | 算术/语义/传递链/断言族逐项核实（§1 重点 1/3） |
| 安全性 | PASS | 纯常量与注释变更；零新增输入面/注入面/敏感数据/权限面；env 解析 fallback-not-crash 保持（:6112-6119）；本票无真实环境操作 |
| 可维护性 | PASS | 单一事实源溯源模式（:6108）；4 处指针式 docstring 防漂移；24 行块密度与爆炸半径成比例；常量命名未变（兼容） |
| 性能 | PASS（不适用为主） | 无算法/数据结构变化；2333s 为每子进程独立预算（语义未变，面 A 最坏 4×2333s 属既有形状）；预算值消解确定性超时（非 flake——REL-077 R1 F-07 已定性行为保持） |
| 测试覆盖 | PASS | 默认值变更被 4 层锁定（常量值/empty/None/非法族）+ FEAT-016 env-free 路径 + env 覆盖/显式优先/透传契约族不变；上报定向族 72 OK/聚合 exit 0 **采信上报**（本角色不可复跑），以静态对照交叉印证 |

## 3. Findings（全部非阻塞）
| ID | 级别 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| F-1 | P3 | verify_workflow.py:6080 | 两条历史趋势值（0.80.0 ~258s / 0.84.0 273.4s）注释内未带内联指针（本次审查已代查实锚：docs/reviews/review-REL-077-RELEASE-R0.md:197、docs/release/release-checklist-0.84.0.md:147/179） | 可留待后续顺手批补指针；不阻断 |
| F-2 | P3 | 工作树（流程性） | 精确修改集的 git 级边界（git status/diff）本角色不可复核——静态代理（mtime+行数差+清单实体逐一对应）全过 | Coordinator 提交前照例 git status/diff 复核；archguard `--regen` 按 DEC-260 审查通过后分离提交（票面既定收口） |
| F-3 | P3 | test_verify_workflow.py:2991 | gemini e2e `--timeout 180` 字面量与发布门预算无关（agent-runtime-e2e CLI 参数） | 无需修改——登记为预期残留，防未来误清理 |

## 4. 硬门槛自检
P0=0 ✓｜5 维度逐一有结论 ✓｜每条发现 P0-P3 标注 ✓｜设计一致性：DEC-262(1)/FIX-346 公式化再校准纪律吻合 + DEC-264(2) 锚链忠实 + DEC-260 分离提交遵守（regen 未混入本 diff）✓｜AI 专项 5 项逐一有结论 ✓

## 5. 终态结论
**APPROVED_WITH_NOTES（unresolved_blockers=0）**——常量再校准算术正确、溯源纪律完整兑现（silent raise=0）、断言族同步完备、零越界实体、零外部引用断裂、baseline-register 免登记论证成立。已知预期红（archguard R1 26413>26385 / R7 stale）为注释净增 28 行的机械结果，非本票缺陷；收口路径（审查通过后 regen 分离提交）已在票面。

## 6. 证据清单
1. verify_workflow.py :6075-6100（24 行溯源块+常量 2333+env 名）、:6103-6119（resolver 逐行）、:6122-6163（runner）、:6166-6184（四子进程面）、:7033（smoke 签名）、:7110-7169（FEAT-016 面传递链）；全文 26413 行
2. test_verify_workflow.py :7744-7817（改名+锁定断言+覆盖/回退/透传族）、:7984-7997（FEAT-016 默认）、:2991（预期字面量）
3. .governance/decision-log.md L204（DEC-262 FIX-346 先例）、L206（DEC-264(2) 1554.78s/pwsh-167 逐字锚）、L210（DEC-268 pwsh-170/171）
4. .governance/evidence-log.md L2871（EVD-1210 双源 4359P/0F/1S/527，pwsh-170 1364.03s/pwsh-171 1394.55s）
5. .governance/plan-tracker.md L81（FIX-400 票面范围=审查范围吻合）、L11/L283（M-2 双源）
6. .governance/baselines.json（仅 1 条有消费流基线）+ baseline_metadata.py L1-80（register/evaluate 语义）
7. docs/reviews/review-REL-077-RELEASE-R0.md:197（258.1s）、docs/release/release-checklist-0.84.0.md:147/179（273.4s）
8. mtime 代理（infra 子树 154 .py 排序，两授权文件居最末两位）；全仓 grep：旧方法名 0 命中、常量 13 处全在授权面+历史 docs

## 7. 遗留不确定项
1. **采信上报面**：定向族 72 tests OK（11.157s）/聚合 verify exit 0/cross-refs PASS/manifest PASS——本角色 Bash 禁用不可复跑；已以静态对照交叉印证（断言实体逐一核实、26413=26385+28 行数自洽），风险归 Coordinator 提交前门。
2. **越界检查边界**：无 git 访问，修改集边界为静态代理结论（P3-2）；精确 hunk 边界由 Coordinator git diff 复核。
3. **决策建议（非本审查职责，供裁定参考）**：审查通过 → 按 DEC-260 先例执行 `archguard-ratchet --regen` 分离提交收口已知红，随后方可进入提交流程。
