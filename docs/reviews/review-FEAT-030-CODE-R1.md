# FIX-315 之外的独立审查：FEAT-030 代码复审报告（Code Review R1）

- **任务**：FEAT-030（0.81.0 切片 V2：消费方改读契约 + K-2 静态扫描）
- **Round**：**R1（复审）**；**前轮引用**：`docs/reviews/review-FEAT-030-CODE-R0.md`（NEEDS_CHANGE / unresolved_blockers=1；P0×1 / P1×2 / P2×12 / P3×3），机录 `next_round=REVIEW-FEAT-030-R1`
- **审查对象**：工作树 staged 三文件（HEAD `3fb90fe`）：`lib/index.js`（blob `91a46f6`）、`skills/software-project-governance/infra/dsh_compat.py`（`6907feb`）、`infra/tests/test_dsh_contract.py`（`00d89c5`）
- **Reviewer**：Code Reviewer Agent（只读；全部构造/变异实验在 `%TEMP%` 整仓副本上进行；仓库零写入、零 scratch）
- **结论**：**APPROVED_WITH_NOTES** / `unresolved_blockers=0`
- **本轮分级**：P0×0 / P1×1（N-1，非阻塞）/ P2×2 / P3×1

## 1. 复审方法（M7.4 step 4.6）

逐条比对 R0 findings；头部声明 round 与前言轮引用；round=1 < 3；**未依赖前轮印象直接通过**——每条结论均以本轮回读代码或复跑实测为据。

**隔离纪律（F-09 的直接后果）**：全部构造性实验（契约缺失/截断/schema=99/exports 缺省、突变矩阵、JS 假包）一律在 `%TEMP%` 下的**整仓副本**上进行；**未在仓库路径做任何改写/变异/还原**。仓库 `host-contract.json` SHA-256 全程保持 `96F9248579FCE72592C000D410C0466CBB035D7C7E8D5885941FB6434643FC6E`。

## 2. 逐条比对（R0 全 18 条）

| # | R0 级别 | 本轮判定 | 独立证据 | 仍存问题 |
|---|---|---|---|---|
| **F-01** | P0 | **已修复（代码）/ 未修复（测试）** | 假包（仅 `lib/index.js`+`package.json`，无契约）实测：`renderComposition` `threw=null`、**`leftovers` 恰为全 3 个模板 token**、`ensurePreset` 不抛、`outcome.contract='unreadable'`、warn 含 `--sync` | ⚠ **N-1**：`renderComposition` 契约缺失这一条**仍无专属回归测试**；自述"新增 3 条 FX-JS-03 等价回归"与测试树不符 |
| **F-02** | P1 | **已修复** | 副本上 5 场景 `--json`：**全部无 Traceback**；缺失→`NOT_RUN`、截断→`FAIL`、`schema=99`→`FAIL`、`exports` 缺省→`FAIL`、健康→`PASS` | 无 |
| **F-03** | P1 | **已修复** | `host.apis['js-yaml'].exports` 缺省 → `ContractMalformed` → **verdict=FAIL**（R0 为 NOT_RUN），reason 含 `host.apis` 与修复指引 | 无 |
| **F-04** | P2 | **订正成立 + 已修复（方向非 R0 所指）** | 实测 `.agent-presets` 属申报值集合 ⇒ 旧扫描返回 `[]` 是"**申报值被接受**"而非漏报；旧版**真实缺陷**是匹配裸行 ⇒ 散文行**假阳性**。R1 改判**引号串内容**：散文行 → `[]`（假阳性消除）、申报值 → `[]`（接受）、`.agent-presetsX` → `[]`（词边界正确） | 无 |
| **F-05** | P2 | **已修复** | `_QUOTED_RE` 收 `'`/`"`/反引号；`` `@deepseek-ai/dsh-x` `` 与 `String.raw\`…\`` 由 `[]` 变为命中 | 无 |
| **F-06** | P2 | 未修复（登记 + 本轮写入注释） | `os.getenv('DSH_ZZZ')` 仍 `[]`；已把该漏报面写入 `_QUOTED_RE` 上方注释（"Known residual blind spot … V8 work"） | 留 V8（按裁定） |
| **F-07** | P2 | **部分未修复（换向残留）** | R1 修了"散文行假阳性"，但 `_PACKAGE_RE` 仍对引号串**全文 findall**（非整串相等）：`throw new Error("… \"@deepseek-ai/dsh-x\"")` → 命中（误报）。HEAD 亦命中 ⇒ **非 R1 引入** | 见 **N-2** |
| **F-08** | P2 | 未修复（按裁定） | `ALLOWLIST_BUDGET=0`（契约外）、`K2_ALLOWLIST=()`；0 条时 necessity 断言仍空转；**新增一条仍被长度断言判死** | 留 V8 |
| **F-09** | P2 | **已修复（实证级）** | `_contract_swapped` 整体删除，改 `_mutated_repo()`（`copytree`→`%TEMP%/feat030-mut-*`）。**硬证据**：对 `Path.write_bytes`/`write_text` 打桩跑完 9 条矩阵 → **写入仓库路径的调用数 = 0**；出厂契约 SHA 前后不变 | 无（R0 §7 瞬时写风险**结构性消除**） |
| **F-10** | P2 | **已修复** | 矩阵 6→**9 条 / 7 字段**；两条新突变经实跑确认**真读契约**（突变后**只有**新值被消费，旧值断言 `False`/`not exists`） | 无 |
| **F-11/F-12/F-13** | P2 | 未修复（按裁定留 V8） | `K2_CONSUMERS` 仍 8 项；无新增消费者反向门；`_render_probe_script` 角色→符号字面量仍在（fail-loud） | 留 V8 |
| **F-14/F-15/F-18** | P2/P3 | 保持（已接受/已裁定） | 本任务未改 `test_dsh_adapter.py` / E 类断言 / `launch.py` | 无 |
| **F-16** | P3 | **已修复** | 新增 `OWN_SCHEMA_VERSION=1` 接入 `contractDocument()`；6 场景实测：`=1` 正常；`=2`/`='1'`/缺失/非对象/非 JSON → **全部 `contract unreadable` 且不抛** ⇒ JS 侧 fail-closed 成立 | 无 |
| **F-17** | P3 | **已修复** | `leftovers = [...new Set(text.match(...) || [])]`；健康路径实测 `leftovers: []` | 无 |

### 2.1 F-04 事实订正裁决（本轮重点）

R0 称「`const d = ".agent-presets"` → `k2_scan` 返回 `[]` = 漏报」。本轮独立复核：`_declared_literal_sets()` 的 `path` 集合 = `{".agent-presets", "agent.cordis.yml"}`；旧 `k2_scan` 的 path 分支对申报值 `continue` ⇒ 返回 `[]` 是**"申报值被接受"**。**R0 把"接受"误读为"漏报"；Developer 的订正成立。** 旧版真实缺陷是匹配**裸行** ⇒ 散文行假阳性（`// the .agent-presets root …` 被判违约），而假阳性只能用 allowlist 压制 ⇒ 直通 BT-R-01 的 **allowlist 侵蚀**。R1 的"引号串内容"修复正是对症。**结论：订正采纳，F-04 记为已修复（方向经订正）。**

### 2.2 F-01 的一点不对称（N-4）

契约缺失时 `renderComposition` 仍返回**含原始 `__…__` token 的 `text`**（§2.6 J-3 只约束 `leftovers` 覆盖全部 token，**未**要求 text 净化）；唯一消费者先判 `leftovers.length>0` 即跳过。

## 3. 本轮新发现

| # | 级别 | 位置 | 事实（实测） | 影响 | 建议 |
|---|---|---|---|---|---|
| **N-1** | **P1** | `test_dsh_contract.py`（缺 renderComposition-契约缺失用例）；`lib/index.js:388` | 全库 `renderComposition` 命中仅 `test_dsh_adapter.py:1139-1142`（**契约在位**，只测 parity）与 `test_dsh_contract.py:1761/1780`（**契约在位**）⇒ **无一处在契约缺失时直调**。**代码修复已实测有效** | **非阻塞**；但 P0 根因正是"该执行项无测试" ⇒ 缺失 = 可再静默回归；§6.1 V2⑦ 指定验收项仍缺 | 补 1 条：把仓库 `lib/index.js` 拷进只带 `package.json` 的临时包（不带契约），`node` 内直调 `renderComposition(template, pkgRoot)`，断言 ①不抛 ②`leftovers` == 模板全部 token（3 个）③`apply()` 不抛且 warn 含 `contract unreadable` + `--sync`。**`dsh_fixtures.py` 无需改**（`FX-JS-03` 已于 `:280-282` 登记 slice V2） |
| **N-2** | P2 | `test_dsh_contract.py:436-460` | 包名类仍**非词边界**：字符串内未申报包名被误报（`ctx.logger.warn("host row @deepseek-ai/dsh-other is required")` → 命中）。HEAD 亦命中（**非 R1 引入**，R0 F-07 的换向残留） | 假阳性 → allowlist 侵蚀压力 → K-11 棘轮承压 | 包名类与 path/marker 统一为词边界/整串判定；同步修正注释 |
| **N-3** | P2 | 过程/声明 | 本轮基线含**已提交**的 FIX-315，其 `dsh_compat.py` 贡献（`rows_checked==0 ⇒ NOT_RUN`、`coverage`、`emit_disclosures`、`UNVERIFIED_KINDS`）**不属** FEAT-030 diff；实测结论对"契约故障裁决"独立成立，但**归因须记边界** | 归因边界 | 保留边界声明；FIX-315 记于 `REVIEW-FIX-315-R1` |
| **N-4** | P3 | `lib/index.js:388` | 见 §2.2 | 无功能影响；潜在误用面 | 留 V8 或于 J-3 登记该语义边界 |

## 4. 硬门槛复核

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0** | 通过 |
| 5 维度全覆盖 | = 100% | 逐一有结论 | 通过 |
| 每条发现标注级别 | = 100% | 22 条（18 R0 + 4 新）全带级别 | 通过 |
| 设计一致性检查 | 已完成 | §2.5 C-1/C-2/C-3、§2.5.1 三态表、§2.6 J-1~J-7、§2.8 K-2/K-11、§6.1 V2①~⑦ 逐条 | **通过**（V2⑦ 的"指定测试"见 N-1） |
| AI 代码专项 5 项 | 全部完成 | mock 残留无新增 / 硬编码无 / 幻觉 API 无 / TODO 无 / 过度实现轻微 | 通过 |

## 5. 五维度结论

- **正确性 ✅**：F-01 的 J-3 失败语义实测达标；F-02/F-03 三态裁决落地且无 traceback；F-16 JS fail-closed 补齐；三路径 sha256 全等、导出面不变、CLI 契约不变。
- **安全性 ✅**：无新增外部输入面；`--uninstall` 逃逸守卫与 `DSH_HOME` 重定向语义不变；**测试隔离性显著改善**——真实路径写入实测 **0**。
- **可维护性 ✅**：惰性访问器（`_contract_value`/`_FACT_ALIASES`/`_fact` + PEP 562 `__getattr__`）分层清晰；N-2 的注释失实仍存（已登记）。
- **性能 ✅**：memoize 保留；健康路径单次读；矩阵 9 用例 1.6s。
- **测试覆盖 ✅（附 N-1）**：119 / 60 / 46 全绿；矩阵 7 字段；K-2 引号串原则（含反引号）；剩余缺口 = N-1。

## 6. 设计一致性检查

- ✅ §2.5 C-1/C-2/C-3：三消费方真读契约（矩阵 7 字段实证）。
- ✅ §2.5.1：`ContractUnreadable→NOT_RUN`、`ContractMalformed`/`ContractSchemaUnknown→FAIL` **实测落地**；JS 侧 `schema_version` fail-closed 补齐。
- ✅ §2.6 J-1~J-7 **七项全保**。
- ✅ §2.8 K-2：按引号串内容判定 + 反引号覆盖；`allowlist 0/0` 与 budget 契约外锚定不变。
- ⚠ §6.1 V2⑦：`FX-JS-03` 的直接断言未交付（N-1），但**行为已由代码满足并经实测**。
- ✅ 范围：仅 3 文件；未触碰 `docs/`、`.governance/`、`dsh_fixtures.py`（正确地未越权）。

## 7. 独立复现结论

| 项 | 自报 | 复现 | 裁决 |
|---|---|---|---|
| F-01 实测 | leftovers 覆盖全 token、不抛 | 假包无契约：`threw=null`；`leftovers` = 3/3；`ensurePreset` 不抛、`contract:'unreadable'`、warn 含 `--sync` | **成立** |
| F-02 三场景 | 无 traceback、裁决正确 | 副本 5 场景全部无 Traceback，裁决正确 | **成立** |
| F-03 归因 | 契约缺陷→FAIL | `exports` 缺省 → `ContractMalformed` → FAIL，reason 含 `host.apis` | **成立** |
| F-04 订正 | 旧扫描本就不报；真缺陷是散文假阳性 | **订正成立**，R1 引号串原则对症 | **订正采纳** |
| F-09 副本方案 | 不再真实路径改写 | 对 `Path.write_*` 打桩跑完 9 条矩阵：**仓库路径写入 = 0**；契约 SHA 前后不变 | **成立（实证级）** |
| F-10 新突变 | 2 条真读契约 | 均副本 + 独立进程；突变后只有新值被消费 | **成立** |
| 三套件 | 119 / 60 / 46 | 仓库与副本各跑一次：**119 OK / 60 OK / 46 OK** | **成立** |
| 三路径 sha256 | `00e0d330…3723` | 三路径全等，且 == 真实 `~/.dsh` 只读哈希 | **成立** |
| 导出面 | — | `["apply","ensurePreset","name","renderComposition"]` == J-5 | **成立** |
| 28u / 28v | exit 0；23/18 | 28u exit 0 + `real-home writes: 0`；28v `PASSED`、`23/18`、`coverage.rows_unverified=5` | **成立** |
| check-governance / manifest / cleanup | 92 / 46；PASSED；零删除 | **92 issues / 46 FAIL 行**；`PASSED`（676 canonical / 753 actual）；`CLEANUP-ERR-002` | **成立** |
| 口径订正 | "截断 → FAIL（exit 1）" | 实测 `--json` **exit 0**、需 `--fail-on-issues` 才 exit 1（既有可选工具策略） | 自述**表述不准，非缺陷** |

## 8. 结论与建议

**`APPROVED_WITH_NOTES` / `unresolved_blockers=0`** —— R0 的唯一 P0 与两条 P1 均已修复且经独立实测确认；F-16/F-17 一并闭合；F-09 的并发/中断风险被副本方案**结构性消除**（实证：真实路径写入 0）。

**Notes（非阻塞）**：
1. **N-1（P1）**：补 `renderComposition` 契约缺失的直接回归（V2⑦ 指定项）。建议**同一 commit 内补**——因为 P0 的根因就是该执行项的缺失。
2. **N-2（P2）**：包名类词边界对齐（消除假阳性 → 减轻 allowlist 侵蚀压力）。
3. **N-3（P2）**：回执与证据保留"FIX-315 贡献不属本 diff"的归因边界。
4. **N-4（P3）**：J-3 的 text 语义边界登记。
5. **口径订正**：`--json` 下 FAIL **不**退出 1（需 `--fail-on-issues`）。

**可提交性判断**：就"行为保持重构 + K-2 前置"的 V2 目标而言，代码已可提交；P0/P1 阻塞为零。N-1 是**测试完备性**缺项，建议随即补齐（或在 commit message / 遗留项中显式登记为 V2 未完项）。

## 9. 真实环境命令上报表（R1/R4）

| # | 命令（摘要） | 退出码 | 影响路径 | 留痕 |
|---|---|---|---|---|
| 1 | `Get-FileHash ~/.dsh/…/agent.cordis.yml` | 0 | **只读**，`00E0D330…3723` | R1 只读 |
| 2 | 三套件（仓库 / 副本 各一轮） | 0 | 无仓库写入（打桩实证） | R1 |
| 3 | 突变矩阵（副本方案） | 0 | **仓库写入 0 次**；副本在 `%TEMP%` | 隔离（副本） |
| 4 | 契约故障注入（缺失/截断/schema=99/exports 缺省/健康） | 0 | 仅在 `%TEMP%` 整仓副本改写；仓库契约 SHA 前后不变 | 隔离（副本） |
| 5 | `launch.py --smoke`（`DSH_HOME=tempdir`） | 0 | 写仅限临时目录；`real-home writes: 0` | R1 隔离重定向 |
| 6 | 三路径渲染复现（路径③ `DSH_HOME=tempdir`） | 0 | 写仅限临时目录 | R1 隔离重定向 |
| 7 | `check-governance` / `check-manifest-consistency` / `cleanup --dry-run` / `check-dsh-preset-compat` | 0/0/1(约定)/0 | 只读 | R1 |

**受影响路径**：真实环境仅 `~/.dsh`（只读 1 次）。仓库 `host-contract.json` SHA 审查期间**始终未变**；仓库内零 scratch；`%TEMP%` 实验目录已全部清理。

---

*报告结束（R1，APPROVED_WITH_NOTES / unresolved_blockers=0）。*
