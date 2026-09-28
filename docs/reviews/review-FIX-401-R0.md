# Review: FIX-401-R0 — loop_runtime 计时断言去环境化 + fixture 同步

- **round**: R0（首审；测试面后置审查——治理基础设施测试修改路由 Code Reviewer）
- **审查对象**: 工作树未提交修改，恰 2 个授权文件（test_loop_runtime_claims.py +59/−19；env_failure_classification.json 净 +2 行）
- **日期**: 2026-09-28
- **审查基准**: RISK-048（risk-log L42）、DEC-268（decision-log L210）、DEC-275（L217）、DEC-262/FIX-346（L204）、RISK-044（risk-log L39）、FIX-330/FIX-364 fixture 先例（JSON L129-133/L204-206）
- **结论**: **APPROVED_WITH_NOTES**，unresolved_blockers=0（P0=0，P1=0，P2=0，P3=5——全部非阻塞）

## 审查重点逐项结论（任务七项）

### 1. 计时域切换正确性 — 通过（亲读核实，P0 风险排除）
- `scan_loop_runtime_claims` 函数体（checks/loop_runtime_claims.py L3208-3328）亲读：纯 Python 逻辑 + `_load_json` 文件读取 + AST/tokenize 解析 + hashlib 摘要，无子进程/无线程。
- 模块级 grep `subprocess|threading|Thread|multiprocessing|concurrent|Popen|fork`：全模块仅 2 命中——L12 `import subprocess` 与 L1475 `subprocess.run`；后者位于 `materialize_loop_runtime_git_root`（L1455 起，git :index 物化专用）。
- 该物化函数调用点全仓清点：verify_workflow.py L49/L21538/L21542（CLI 面）与测试（test_loop_runtime_claims.py **L1097——在计时 `for` 循环之前**；attestation 测试 L529/583/584）。scan 路径不可达该函数。
- 二次清查 `os.system|os.spawn|os.exec|asyncio`：零命中；模块 imports（L3-17）全为 stdlib，无传递性风险。
- 计时次序正确：L1108 start → L1109 scan → L1110 stop+append。
- **结论：`time.process_time()`（本进程 user+kernel CPU）与被测区事实完全匹配，无漏计向量，Developer 论断属实。**

### 2. 预算定标纪律 — 通过（一处 P3）
- median(15.453, 18.547, 23.406)=18.547 ✓；18.547×1.5=27.8205→**27.8**（向下取整，保守）✓（L1144-1145/L1173）。
- 系数链实锚：DEC-262「p50×1.5=36s」（decision-log L204）+ DEC-273 同型反相检查（L215）——注释 L1140-1141 引用准确。
- 27.8/23.406=1.188→「19% margin」✓；27.8/2=13.9<15.453 → 反相 RED 保持 ✓；「~2x faster re-tightens」推导精确（18.547/2×1.5=13.91≈13.9）✓；「+50% over p50 → RED」：27.8/18.547=1.499 ✓；负载对照 13.688 不膨胀 ✓。
- 测量值为本会话 Developer 实测（Reviewer 无法复跑，采信+静态自洽核对）；唯一不自洽点见 F-1。

### 3. 「真回归仍红」咬合（DEC-268/275 红线）— 通过
- 断言 L1173 无条件执行；L1086-1173 无 skip 装饰器/分支豁免/try-except 吞断言——**零免检路径，无分级，无 skip-under-load**。
- 拒绝候选论证成立（L1131-1138）：负载检测器本身是环境敏感分支，假阳性恰在最可能引入回归时豁免（DEC-268 红线，decision-log L210 实锚）。实现方向与 RISK-048 缓解列登记原文「按 FIX-240 先例去环境化（**进程级计时**/阈值分级）或标注 skip-under-load」（risk-log L42）二选一中的前者——**落地的是登记的缓解方向本身**。
- 残余敏感性如实披露（L1163-1172：频率降档/热节流/内存带宽竞争）+ median-of-3 吸收 + breach 按 DEC-262 归因重锚。
- DEC-275(4)「无断言弱化争议」：域切换为登记缓解、阈值按公式重定标非任意抬升、反相证明仍咬合——**无弱化争议**（域收窄披露见 F-5）。

### 4. fixture 同步正确性 — 通过（两处 P3 形态注记）
- 条目（JSON L168-179）形态对照 FIX-330（L129-133）/FIX-364（L204-206）：`resolved: true`+`resolved_by`+ticket was-resolution 一致；`pending R0/commit` 标注如实（L174/L177）——**未伪造审查结论**。
- **孪生条目零改动核实**：现行 L180-189 保持 10 行原形态、ticket 原文一致（L188）、零 FIX-401 token。行数算术互证：授权条目恰净增 2 行（resolved+resolved_by），孪生 L178-187→L180-189 的 +2 位移被完全解释。
- evidence 追加不删史：L174 历史（AUDIT-152 原文+FIX-388 注记）逐字保留，FIX-401 以 " | " 追加，与孪生 L186 及同族 L146/L155/L164 形态逐短语平行。
- JSON 结构合法性：全文通读配平无异常（Reviewer 无 Bash 未机器 parse；零代码消费者，爆炸半径限于人工阅读面）。
- 测试名未改：def L1086 + class L997 与 JSON key L168 精确匹配。

### 5. 越界检查 — 静态代理全部一致（恰 2 文件）
- infra 树 347 文件 mtime 尾部：两授权源文件为最新源文件，其后仅 __pycache__ 构建产物。verify_workflow.py/test_verify_workflow.py 同日较早 mtime，归属先前已 commit 票（FEAT-073/DEC-272、FIX-400/DEC-273 为其落点），与「HEAD f06a2bf 干净树」申报相容。
- 全仓（非 gitignore）FIX-401 提及面 = 2 授权文件 + 2 处既有合成夹具用法（test_loop_exit_bridge.py L126-129；test_verify_workflow.py L21009/21013 假想 review 文件名），mtime 均早于授权对、与计时变更无功能关联。
- docs/reviews 最新为 review-FIX-400-R0.md——无预写 FIX-401 审查文档。
- 残留：`27.0` 仅存于历史注释 L1118 与 JSON 历史 evidence（非活断言）；`process_time` 全 tests 目录仅 L1108/L1110。

### 6. AI 专项 5 项 — 全部完成，零发现
mock 残留：无（L1080 patch 为既有他测试）；硬编码：27.8 为定标常量且注释载明推导链（与 8.0/27.0/36s/2333 先例同模式，非坏味）；幻觉 API：无（全部符号/API 实存：L1455/L207/L3208）；未实现 TODO：无；过度实现：无（未引入检测器/分级/skip 机制，代码面净变更 2 行计时 API+1 阈值数字）。

### 7. 向后兼容 — 通过
- 测试面变更，无 CLI/产品行为变化；checks/loop_runtime_claims.py 不在修改集。
- fixture 零程序化消费者：*.py 全仓唯一命中 test_triage_write_guard.py L615 为文档字符串提醒——`resolved: true` 无运行时行为效应（与「-k 0 selected exit 5」互证，pytest exit 5 语义正确）。
- FIX-215 QA 契约判定核实成立：L423-427 为 perf_counter 包裹 **subprocess.run** 的子进程墙钟度量——该场景墙钟是正确时钟（父进程 process_time 看不见子进程 CPU），8.0s exclusive 钉在 L116/L359/L380/L436/L452/L1704，均不在 hunk 内。

## 五维度结论表

| 维度 | 结论 | 依据摘要 |
|---|---|---|
| 正确性 | ✅ 通过 | 计时域与被测区语义匹配（亲读 L3208-3328+模块级清查零命中）；断言/身份校验逻辑未动；计时次序正确 |
| 安全性 | ✅ 通过 | 纯测试面/数据面变更，无输入校验/注入/敏感数据/权限面变化 |
| 可维护性 | ✅ 通过（附注） | 注释机制论证完整、治理引用全部实锚（FIX-288=12.4s 见 RISK-048 L42；DEC-262 L204；FIX-240 类比 L1091-1094）；F-1/F-2 形态注记 |
| 性能 | ✅ 通过 | p50×1.5 纪律链完整（DEC-262/273）；锚定/负载对照/反相三件齐备；无生产性能影响 |
| 测试覆盖 | ✅ 通过（附注） | tripwire 无条件执行零免检路径、反相咬合证明非永绿；F-5 域收窄为既定代价且墙钟面另有看护 |

## Findings

| ID | 级别 | 位置 | 问题 | 建议 |
|----|--------|------|------|------|
| F-1 | P3 | test_loop_runtime_claims.py L1163-1166 | 注释「observed <= +70% over the quiet floor」未注明比较基线；按已记录锚可推导 +51%（23.406/15.453）/+71%（23.406/13.688）/+80%（23.406/13.0），无一处精确等于 +70% | 后续顺手批补注基线或改写为明确数字；不影响断言与咬合（承重数字 23.406<27.8=19% margin 正确） |
| F-2 | P3 | env_failure_classification.json L178 | ticket「was:」仅引用原 ticket 后半句（前半 "notice-binding candidate (report section 7)" 可由孪生 L188 同构重建，未纳入 was: 引号而由相邻从句交代）；FIX-330/364 先例完整保留原文于 was: 内 | 信息无丢失，接受现状；后续同类更新沿用先例完整引用形态 |
| F-3 | P3 | env_failure_classification.json L176-177 | `resolved: true` 先于 R0 终态与 commit 落盘（已如实披露 "pending R0/commit"）；commit 后措辞将滞后（FIX-364 先例含 commit hash）；若 R0 NEEDS_CHANGE 须随返工同步改写 | commit 时顺手补 hash 或接受快照语义 |
| F-4 | P3 | 任务元数据（非代码） | 申报 JSON diffstat「+3/−2」（净 +1）与观测不符：孪生位移 +2、授权条目恰净增 2 行，实际净 +2（git 形态大概率为 +4/−2）；测试文件 +59/−19 与 3 hunk 精确吻合（−2/+2 计时、−16/+56 注释、−1/+1 断言） | 更正申报记录；无产品影响 |
| F-5 | P3 | test_loop_runtime_claims.py L1117-1138（讨论项） | 域切换后纯墙钟/I-O 等待型回归（sleep、阻塞读）不再触发本断言——去环境化的既定语义收窄（RISK-048 登记缓解方向固有代价）；墙钟域仍有看护（FIX-215 QA L423-427 + 孪生 adapter-timeout 面 deferred 0.93+ 已在 ticket 注明） | 知识记录，无需修改 |

## 硬门槛自检

- [x] P0 阻塞问题数 = 0
- [x] 5 维度全覆盖（100%）
- [x] 每条发现标注级别（5/5，全 P3）
- [x] 设计一致性检查完成（RISK-048 缓解方向/DEC-262 系数链/DEC-268·275 红线/FIX-240 类比/FIX-330·364 先例均实锚）
- [x] AI 代码专项 5 项全部完成（零发现）
- [x] 只读审查：零 Write/Edit/Bash/Agent/AskUserQuestion 调用
- [x] 引用事实均带文件+行号；Developer 测试输出采信+静态交叉印证

## 终态结论

**APPROVED_WITH_NOTES — unresolved_blockers=0**

计时域切换正确性（本审查最高风险项）经亲读被测函数与模块级清查确证：被测区纯 Python+文件读取、无子进程/无线程、git 物化在计时区外，process_time 语义精确匹配。预算按 DEC-262/FIX-346 既定系数链重定标且反相咬合证明非永绿（DEC-268/275 红线满足，无断言弱化争议——直接支撑 DEC-275(4) M-0 冻结条件）。fixture 同步符合先例形态、孪生条目零改动、历史逐字保留。5 条 P3 均为文档精度/形态/元数据注记，不阻塞合并。

## 证据清单

1. `skills/software-project-governance/infra/checks/loop_runtime_claims.py` L3208-3328（被测函数亲读）；L12/L1455/L1475（全模块唯一 subprocess 位点=git 物化助手）；L3-17（imports 全 stdlib）；L207/L221（符号实存）
2. `skills/software-project-governance/infra/tests/test_loop_runtime_claims.py` L1086-1173（被审 hunk 全文）；L1097（物化在计时循环外）；L997（class 名）；L423-427+L116/L359/L380/L436/L452/L1704（FIX-215 QA 未动）；L13（import time）
3. `skills/software-project-governance/infra/tests/env_failure_classification.json` L168-179（授权条目）；L180-189（孪生零改动）；L129-133/L204-206（先例）；L146/L155/L164/L186（同族追加式平行）
4. `.governance/risk-log.md` L42（RISK-048 缓解列原文）、L39（RISK-044）
5. `.governance/decision-log.md` L204（DEC-262）、L210（DEC-268）、L215（DEC-273）、L217（DEC-275(4)）
6. 静态代理：infra 树 347 文件 mtime 序（两授权源文件最新，余为 pyc）；全仓 FIX-401 提及面 grep（2 授权+2 既有合成夹具）；docs/reviews 276 文件 mtime 尾（最新=FIX-400，无预写）；*.py 消费者 grep（唯一命中=文档字符串）

## 遗留不确定项

1. **git 级 byte-diff 不可得**（角色禁 Bash）：孪生零改动/历史逐字保留经行数算术+内容形态+短语级平行确证，非字节级；建议 Coordinator 收尾以 `git status`/`git diff --stat` 终验恰 2 文件（含 verify_workflow.py/test_verify_workflow.py 归属先前已 commit 票的确认）。
2. **测量值不可复跑**：锚定与负载对照为 Developer 本会话实测，按硬门槛采信；内部自洽核对全部通过（除 F-1）。
3. **JSON 机器 parse 未执行**（Bash 禁用）：结构通读无异常+零代码消费者；可随聚合验证顺手 `python -m json.tool` 确认。
4. **hunk 计数（申报 3）不可字节级验证**：上下文行合并可能为 2；总量 +59/−19 精确吻合。
