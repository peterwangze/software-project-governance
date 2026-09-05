# FIX-285 Code Review R0 — README F-01 引号逐字对齐 + F-3 bootstrap 标记面机器守卫（Option B）

- **Round**: R0
- **任务 ID**: FIX-285（P2，0.78.1 入槽；DEC-172 ①枚举 F-01 README 引号 + F-3 bootstrap 标记面机器守卫、DEC-173③ 扩展方向）
- **审查类型**: 代码审查（Code Reviewer）— 只读；本审未执行任何命令、未修改任何文件（角色硬约束：Read/Grep/Glob 之外全部禁用）
- **被审查变更**（工作树未提交；净变更限定 4 文件）:
  1. `README.md` — F-01：L204 引号短语改逐字（1 行 +1/-1）
  2. `skills/software-project-governance/infra/checks/version.py` — +53/-0 纯追加：L46-51 `_version_tuple()`、L53-75 `_tracked_entry_files()`、L116-137 bootstrap 守卫段
  3. `skills/software-project-governance/infra/verify_workflow.py` — 仅 L20208 文案行
  4. `skills/software-project-governance/infra/tests/test_verify_workflow.py` — L752-881 `VersionConsistencyBootstrapMarkerTests`（5 测试）
- **Date**: 2026-08-28（Coordinator 归档补记）

---

## 1. 审查结论（先给结论）

**APPROVED_WITH_NOTES ｜ unresolved_blockers: 0**

- P0 阻塞 = **0**；P1 关键 = **0**；P2 建议 = **1**；P3 讨论 = **2**
- 5 维度全覆盖 = 100%；AI 专项 5 项全部完成；硬门槛全部通过
- 备注（NOTES）均为非阻塞：F-01（函数长度拆分建议）可本轮顺手修或遗留测试卫生批；F-02/F-03 为口径备案级讨论。全部备注不阻塞本任务合并。

---

## 2. 审查证据方法说明（含命令禁令声明）

- 本 Reviewer 按角色硬约束执行：全部结论基于 **read/grep/glob 只读工具的逐行读取**。未运行 git diff/status、未重跑测试、未复跑 verify_workflow。
- 逐行读取证据面：version.py 全文（138 行）；test_verify_workflow.py L1-45（imports）+ L555-660（既有委托层测试）+ L740-899（新测试类全文）；verify_workflow.py L20190-20229（cmd 文案与分类）+ 委托层 L9993-9995/L6939/L10138/L14870 + ROOT/GOVERNANCE_DIR 定义 L70/L132-136/L216-217 + "bootstrap"全量 grep；README L196-213/L266-275/L308/L336/L346；AGENTS.md L1-8；projection.py 全文（89 行，先例对照）。
- 决策依据实读：`.governance/review-FIX-276-CODE-R0.md`（F-01 原文与修复建议）、`.governance/review-REL-071-CANDIDATE-DESIGN-R0.md`（F-3 原文 + BC-3/F-2 先例）、decision-log L181（DEC-172 ①）/L182（DEC-173③）。
- 现网口径独立佐证：SKILL.md L3 `version: 0.78.0` + plan-tracker L11 `工作流版本: 0.78.0` + AGENTS.md L5 `@bootstrap-version: 0.78.0`（+CLAUDE.md 0.77.0 本地件）→ 与 Developer「现网 exit 0 + 仅 CLAUDE.md WARN」自报在代码路径上静态吻合。
- 范围纪律辅助证据：全仓 mtime 排序（glob 全量 1335 路径）尾部最新产品文件 = 恰为本任务 4 文件，其间仅治理记录与既有已审批次产物交错。
- **未验证项声明**：对 HEAD 的逐字节 diff（+53/-0、4 文件外零改动、version.py hunk 边界）、测试红相/全量/现网三条命令实录——均因命令禁令「未验证（本审）」，以结构重建 + 逐行一致性 + Developer/Coordinator 双重报告采信替代（§7 逐项标注）。

---

## 3. 5 维度逐项结论

### 维度 1：正确性 ✅
| 检查项 | 结论 | 依据 |
|---|---|---|
| Option B 五分支逐一映射 | PASS | tracked 陈旧 → L133-135 FAIL；tracked 缺标记 → L129-131 FAIL（missing=stale）；untracked 陈旧 → L136-137 WARN advisory；当前值 → L133 比较为假无 issue；入口缺失 → L126-127 跳过。与 DEC-173③ + Coordinator 裁决口径逐条对应（唯一未枚举分支见 F-02） |
| 版本比较语义 | PASS | `_version_tuple`（L46-51）三段正则来源保证可解析，元组逐段比较正确；空元组路径对 marker/source 均不可达 |
| host_root 语义 | PASS | L110 既有回退；守卫与 plan-tracker 面同源。生产 wrapper 传 `(ROOT, GOVERNANCE_DIR.parent)`=宿主根；e2e 经 set_context 注入宿主根 → 守卫面指向宿主项目根入口文件；非 git 宿主 → 短路空集 → 全走 WARN 面，不误伤 |
| WARN/FAIL 出口语义 | PASS | cmd 层按 `[WARN]` 前缀分类，WARN 不入 fail_items → exit 0；与 REL-071 F-2/BC-3 先例一致 |
| 测试断言与实现消息对齐 | PASS | 三条 FAIL/WARN 消息模板与断言子串逐一比对逐字可命中 |

**发现：无（正确性维度）**

### 维度 2：安全性 ✅
| 检查项 | 结论 | 依据 |
|---|---|---|
| 命令注入 | PASS | `subprocess.run` 列表参数、无 `shell=True`；`root` 以单参数传 `-C`；文件名为常量元组且前置 `--` 分隔符防御 pathspec 误析 |
| 输入校验/ReDoS | PASS | 正则为线性字面量模式（无嵌套量词/回溯爆炸面）；作用于本地文件内容 |
| 敏感数据/权限 | PASS | `git ls-files` 只读枚举；无凭证、无网络、无写操作 |
| 失败方向 | PASS | git 不可用/超时/非零返回 → 空集 → WARN advisory（降级不静默——WARN 仍可见 + 会话级 FIX-238.2 fail-closed 兜底）；崩溃路径为 fail-closed 非零退出 |

**发现：无**

### 维度 3：可维护性 ⚠️（附 1 条 P2）
| 检查项 | 结论 | 依据 |
|---|---|---|
| 命名可读 | PASS | 命名意图清晰；docstring 与守卫注释块完整引用 FIX-285/DEC-173③/REL-071 F-2/BC-3/FIX-256/FIX-238.2 决策链 |
| 函数长度 | **P2（F-01）** | `check_version_consistency` 现 L77-138 = 62 行 > 50 行建议阈值（FIX-285 前 39 行）；守卫段可提取 helper |
| 重复代码 | PASS | git-probe 与 projection.py 先例同构属有意复用形态（镜像声明 docstring 如实），非坏味道重复 |
| 注释质量 | PASS | 守卫注释逐分支说明口径与先例来源，与实现一致 |

### 维度 4：性能 ✅
| 检查项 | 结论 | 依据 |
|---|---|---|
| 子进程开销 | PASS | 单次 `git ls-files` 承载两个文件名；timeout=15 兜底挂起 |
| 算法/IO | PASS | 两个入口文件各一次线性 read + regex；无 N+1、无嵌套循环 |

### 维度 5：测试覆盖 ✅
| 检查项 | 结论 | 依据 |
|---|---|---|
| Option B 分支覆盖 | PASS | 5 测试对五分支一一对应（L789/L810/L831/L848/L872） |
| 隔离实质 | PASS | 每测试独立 TemporaryDirectory；`git init+add`（无 commit）无需身份配置、ls-files 读 index 稳定；`_bootstrap_issues` 以 `@bootstrap-version` 过滤隔离噪音 |
| 直接调 checks.version 的取舍 | PASS（合理且有必要） | 既有委托层测试 patch vw.ROOT 但 host_root 仍为真实仓根——新守卫会产生额外 FAIL 噪音；新类直接调 `(root, root)` 实现完全隔离，docstring 明示动机 |
| 盲区 | P3（F-02） | untracked 缺标记分支无测试；OSError/非零 returncode 分支无直接测试 |

---

## 4. AI 专项 5 项检查（逐项结论）

| # | 检查项 | 结论 | 依据 |
|---|--------|------|------|
| 1 | mock 残留 | PASS | 新测试类零 mock（直接调用真实 checks.version + 真实 tmp git 仓） |
| 2 | 硬编码失实 | PASS | 测试 source=9.9.9 为合成真值（tmp 仓内自洽）；文案行与实际核对面构成一致 |
| 3 | 幻觉 API/引用 | PASS | `subprocess.TimeoutExpired`/`capture_output`/`errors="replace"`/`check=False` 均真实且用法正确；docstring 引用 projection.py `_tracked_target_files` 实际存在且形态声明属实；注释引用的 DEC/REL/FIX 编号均在实际文件命中 |
| 4 | 未实现 TODO | PASS | 新增段无 TODO/占位；五分支全部落地 |
| 5 | 过度实现 | PASS | 交付严格 = F-01 + F-3；无新检查项、无新 cmd、无 manifest/config 变更面；与 DEC-173③「变更面最小」一致 |

---

## 5. 发现列表（每条含级别、位置、事实依据、修复建议）

### F-01【P2 建议】check_version_consistency 函数长度超阈值（62 行）
- **位置**：`version.py` L77-138
- **事实依据**：按 +53/-0 纯追加重建，FIX-285 前函数体 39 行；守卫段 +22 行后达 62 行，越过「单函数 >50 行建议拆分」线。
- **影响**：非阻塞。守卫段语义自洽、可整体提取为 `_check_bootstrap_markers(root, host_root, source, issues)`。
- **修复建议**：本轮顺手拆分或遗留测试卫生/重构批；不阻塞合并。
- **建议处理**：可遗留（附计划）。

### F-02【P3 讨论】untracked 入口文件缺标记分支静默跳过——裁决未枚举分支 + 测试盲区
- **位置**：`version.py` L129-132；测试类无对应用例
- **事实依据**：Option B 裁决枚举五分支未含「untracked + 缺标记」；实现选择静默 skip。方向可辩护（无法判陈旧 + 本地件 + FIX-238.2 兜底），但与「untracked 陈旧 WARN」相比存在信号盲区：从未带标记头的本地副本零提示。
- **修复建议**：备案该口径于裁决/任务记录（或后续补 WARN + 单测）；不要求本轮修改。
- **建议处理**：讨论备案。

### F-03【P3 讨论】入口文件裸 `read_text(encoding="utf-8")` 无解码容错
- **位置**：`version.py` L128
- **事实依据**：宿主入口文件若为非 UTF-8 编码（Windows GBK 手编辑形态），UnicodeDecodeError 未捕获 → 上抛 → traceback 非零退出。与同文件既有裸读约定同型（非新增风险模式）；崩溃方向 = fail-closed。守卫面将裸读扩展至宿主任意项目入口文件，暴露面较仓内受控文件略增。
- **修复建议**：后续统一容错批（try/except → FAIL NOT READABLE 或跳过+WARN）；不阻塞。
- **建议处理**：讨论备案。

---

## 6. 重点审查项 1-8 逐项核实结果

| # | 重点项 | 核实结果 | 关键依据 |
|---|--------|---------|---------|
| 1 | Option B 口径实现正确性 + host_root 复用 | **PASS** | 五分支逐条对应；host_root 生产链 wrapper→宿主根；e2e set_context→宿主根；非 git 宿主自动降 WARN 面不误伤 |
| 2 | _tracked_entry_files 健壮性 | **PASS；任务书「超时缺失」前提与实现不符** | **L68 实存 `timeout=15` 且 L70 捕获 `subprocess.TimeoutExpired`——挂起风险已有防护**（按实际代码裁决，不按任务书前提）。参数拼接：列表 form + `-C` 单参 + `--` 分隔 + 常量 ASCII 文件名 → 空格/中文路径安全。fail-safe 空集方向合理：git 不可用 → WARN 面（非静默、有 FIX-238.2 兜底）；与 projection.py 先例的差异（彼取严、此取宽）有正当性——projection 字节镜像面无其他兜底故必须取严，本面有会话级 fail-closed 二线，取舍成立且 docstring 如实声明 |
| 3 | 正则与编码 | **PASS** | AGENTS.md L5 实读带尾注形态——捕获组止于三段版本，尾注不进捕获；read_text 显式 UTF-8（容错缺口见 F-03） |
| 4 | 测试隔离与断言实质 | **PASS** | tmp git 仓 init+add 无身份依赖；直接调 (root, root) 的取舍合理且有必要；untracked WARN 双断言实质守住「降级不升格」方向 |
| 5 | 向后兼容 | **结构层 PASS；逐字节 diff 未验证** | +53 算术重建吻合（31+22）；既有段形态完整、无新增检查项、无既有分支改动。文案行无解析方（cmd 层仅按 [WARN] 前缀分类；测试 grep "Files checked" 零命中——纯人读信息） |
| 6 | F-01 引号对齐 | **PASS** | L204 与 L272 字符级逐字子串比对一致；同句其余三引号短语（L308/L336/L346）实读逐字命中 |
| 7 | 范围纪律 | **辅助证据 PASS；git 级核验未验证** | mtime 全量排序尾部最新产品文件 = 恰为 4 文件；git diff 级核验以任务书红线 + mtime 佐证 + Coordinator 职责承接 |
| 8 | 来源覆盖完整性 | **PASS** | FIX-276 F-01 → 单行逐字修正；REL-071 F-3 → 守卫段完整承载无扩界；DEC-173③「扩展 check-version-consistency 不新增检查项、变更面最小」逐点符合：无新 check id、无新 cmd、manifest 零触碰、verify_workflow.py 仅文案行 |

---

## 7. Developer 自报验证逐项核验（独立复核受限声明）

| # | 声明项 | 核验结果 | 依据 |
|---|--------|---------|------|
| 1 | 红相 3 failed exit 1 → 5 passed | ✅ 逻辑自洽（**未独立复跑**） | 无守卫时 2 过 3 败与「3 failed」吻合；5 passed 由 Developer 实录 + Coordinator 抽测双重转述采信 |
| 2 | 全量 733→738+89subtests exit 0 | ✅ 算术吻合（未复跑） | +5 = 新测试类 5 用例；既有委托层测试对额外 FAIL 呈子串断言容忍（实读） |
| 3 | 现网 exit 0（AGENTS.md PASS + CLAUDE.md WARN） | ✅ 静态推演吻合（未复跑） | 独立证据链：SKILL.md 0.78.0 = plan-tracker = AGENTS.md tracked → PASS；CLAUDE.md 0.77.0 gitignored → WARN → 不入 fail_items → exit 0 |
| 4 | check-governance 115 issues 全既有（Check 24 PASS） | ✅ 与「不新增检查项」实现一致（未复跑） | verify_workflow.py "bootstrap" 全量 grep 仅文案行相关，无新 check 注册面 |

---

## 8. 设计一致性检查

| # | 一致性要求 | 判定 | 依据 |
|---|-----------|------|------|
| 1 | DEC-172 ①（F-01 + F-3 两项，零行为面） | ✅ PASS | decision-log 实读枚举含两项；交付恰此两项无第三项混入 |
| 2 | DEC-173③（扩展 check-version-consistency，不新增检查项，变更面最小） | ✅ PASS | 实现内嵌既有 check + 1 文案行，无新 check id/cmd/manifest 面 |
| 3 | Coordinator Option B 裁决口径 | ✅ PASS（1 分支备案） | 五枚举分支逐一映射；唯一未枚举分支实现取 skip，合理但备案为 F-02 |
| 4 | REL-071 F-2/BC-3 先例口径延续 | ✅ PASS | untracked WARN advisory 措辞与先例同构 |
| 5 | FIX-276 R0 F-01 修复建议执行 | ✅ PASS | L204 已改逐字子串，同句三短语未被破坏 |

---

## 9. 硬门槛裁决表

| 门槛项 | 阈值 | 实测 | 裁决 |
|--------|------|------|------|
| P0 阻塞问题数 | = 0 | 0 | ✅ PASS |
| 5 维度全覆盖 | = 100% | 5/5 | ✅ PASS |
| 每条发现标注级别 | = 100% | 3/3 | ✅ PASS |
| 设计一致性检查 | 已完成 | §8 五项 | ✅ PASS |
| AI 专项 5 项 | 全部完成 | 5/5 | ✅ PASS |

---

## 10. 最终结论

**APPROVED_WITH_NOTES — unresolved_blockers: 0**

- 硬门槛全部通过；Option B 五分支落地正确、健壮性取舍成立（timeout 实存）、F-01 逐字闭环、DEC-173③ 符合、测试隔离与断言实质到位。
- NOTES（均非阻塞）：F-01【P2】函数 62 行可拆分（可遗留）；F-02【P3】untracked 缺标记静默分支备案 + 补测建议；F-03【P3】裸 read_text 容错备案。
- 本结论为**通过终态**，可用于结束复审链（Check 30 消费）。
- Review 原则声明：全部结论以逐行读取的文件内容、决策文件实读与 mtime 排序佐证为事实基础；命令级核验因角色禁令如实标注「未验证（本审）」，未将任何 Developer 转述包装为本审实测。无假设、无猜测、无编造。
