<!-- machine-suggested-next-round: none (terminal pass) | round: R0 | reviewer: Code Reviewer (subagent) | verdict: APPROVED_WITH_NOTES | unresolved_blockers: 0 -->

# FIX-313 + FIX-346 合并代码审查 R0（一报告双 task）

- **审查对象**：工作树未提交 4 文件（基线 HEAD `0a13b21`；numstat 实测：`lib/index.js` +20/−4、`tests/test_dsh_adapter.py` +68/−1、`tests/test_loop_runtime_claims.py` +17/−1、`tests/test_verify_workflow.py` +11/−1）。并行批 D 6 文件 + 并行会话 2 个未跟踪审查文档**未纳入审查**（见 §4 归因）。
- **Reviewer**：Code Reviewer（独立 subagent，只读；全部变异/反相/副本实验在 `%TEMP%\fix313-346-review\`（237 MB 全仓镜像，含 `.git`）内完成并已删除；真实仓库零写入、零 commit、真实 home 零触碰）。
- **结论**：**APPROVED_WITH_NOTES / `unresolved_blockers=0`**（P0=0，P1=0；P2=0，P3×5）。
- **一句话**：方向更正事实链逐环核实成立（原处方确会打红 FIX-316 钉死的既有契约测试，具名）；parity 测试双向回归力经三组变异实测证实；定标算术、反相形态（13.5 FAIL / 13 TimeoutExpired）与「非放宽语义」全部独立复现；850 全绿声明在本共享工作树**暂不可字面复现**，但 3 失败经差分实证全部归因于并行会话在审查窗口内投放的未跟踪文档（本批零命中），非本批缺陷。

---

## 1. 方向更正事实链核验（FIX-313）——逐环成立

**① 原处方是什么**：`.governance/plan-tracker.md:82`（FIX-313 登记，源自 REVIEW-REL-076-DESIGN-R0 F8/F9）处方 = 「归一化改用 `\r\n?`→`\n`（并对齐 Python 语义）+ catch 分支 `rmSync(staging)`」；`docs/requirements/dsh-compat-design-0.81.0.md:347`（D-66/D-100 行）处方 = 「两渲染器显式统一为**先归一 CRLF→LF，再归一孤立 CR→LF**（JS 侧正则扩展；Python 侧 newline 与显式替换）+ `checks/projection.py:14` 同步补孤立 CR」。

**② FIX-316 反向收口是事实**（独立核验代码，非转述）：
- `adapters/dsh/launch.py:451-457` docstring 明示 `newline=""` 关闭通用换行翻译 + 显式折叠 `\r\n`、「isolated `\r` is left alone」、点名 D-66；
- `:460` 经 `_read_text_with_newline_mode()`（`:485` `open("r", encoding="utf-8", newline="")`）读模板，`:466` `template.replace("\r\n", "\n")`——孤立 CR 在 Python 侧**存活**；
- `review-FIX-316-CODE-R0.md` §5#3：「D-66 | 孤立 CR：RED 0 → GREEN 1（与 JS 一致）✅」——交付方向 = 双侧**保留**孤立 CR，与设计 L347 的「再归一孤立 CR→LF」**相反**。

**③ 原处方确会打破契约——具名到会打红的测试**：
| 原处方变体 | 撞上的既有契约测试（全部在册、基线绿） |
|---|---|
| 仅 JS 折孤立 CR（plan-tracker L82 原文） | parity 破坏：Python 侧被 `test_dsh_compat.py:2214-2224 test_isolated_cr_is_preserved_like_the_js_renderer`（断言 `rendered.count("\r")==1, "lone CR must survive"`）钉死为保留 ⇒ 两路径再度分歧 |
| 双侧折孤立 CR（设计 L347 原文） | `test_dsh_compat.py:2224` 直接红（Python 存活 pin）；fixture 契约 `test_dsh_contract.py:2391-2394`（FX-CR-01 恰 1 个孤立 CR）+ `dsh_fixtures.py:195-198` 组成的Fixtures族语义随之失效 |

⇒ **「原处方确会打破契约」成立**。方向更正（维持行为 + 注释钉契约 + 补机器校验 parity 测试）是唯一不破坏 FIX-316 已交付契约面的路径。

**④ 注释真实性逐句核对**（lib/index.js 两处纯注释）：
- L387-396 注释：「both renderers fold `\r\n` to `\n` EXPLICITLY and leave an isolated `\r` alone」——JS `renderComposition` 内 `template.replace(/\r\n/g, '\n')`（未改动行，diff 上下文可见）+ Python `:466` 同构，**属实**；「the Python side used to rely on the text layer's universal newlines」与 F8/D-66 历史一致；「machine-checked by `test_dsh_adapter.py::test_isolated_cr_template_renders_identically`」——测试名逐字存在。D-67 引用（「不注入 `\r` ⇒ 抓不到 D-66」）与 `dsh-host-dependency-inventory-0.81.0.md:215` 实录一致。
- L569-577 Scope note（FIX-313(b)）：「self-removal is NOT the retired orphan GC…addresses only the ordinary failure path (`stagingCreated`)…F4 trade-off（REVIEW-FIX-313-CODE-R0，registered by FIX-325）still stands one door over…nothing here enumerates or name-matches anything」——与代码逐句相符（见 ⑤），与 `review-FIX-313-CODE-R0.md` F4 处置 + plan-tracker L94 FIX-325 完成④（「F4/F5 lib/index.js 注释登记」）相符。

**⑤ catch 自清理确已交付（4 守卫在册，逐一定位）**：`lib/index.js` ensurePreset——(G1) EEXIST 换名重试 + 8 次熔断（`:515-532`）；(G2) `stagingCreated` 所有权证明（唯一写入点 `:519`，紧跟非递归 `mkdirSync`；注释 `:498-514`）；(G3) catch 内 `rmSync` 以 `stagingCreated` 为闸（`:578-580`）；(G4) fail-safe 告警族：nothing-removed（`:582-584`）、清理自身抛错点名确切残留路径且不外抛（`:586-592`）。module header 孤儿权衡登记在册（`:55-68`，FIX-325 交付）。**本批对 (G1)-(G4) 零触碰**（diff 仅注释）。

## 2. parity 测试质量——双向回归力实测证实

**结构**：`test_isolated_cr_template_renders_identically`（+68/−1 中的主体）——夹具 = shipped 模板（实测 16651 B、CR=0）去 CRLF 后注入恰 1 个孤立 CR（自断言 `count("\r")==1` 防夹具腐化）；`write_text(..., newline="")` 防平台翻译；Python 侧 monkeypatch `launch._composition_template`（模块级、`finally` 恢复；`_load_launch_module()` 每次新实例，零跨测试污染；`render_composition` 纯读无写）；字节全等断言（字符串全等 ≡ UTF-8 字节全等，UTF-8 单射；JS 侧 JSON round-trip 保留 `\r`）+ **双侧存活 pin**（`rendered.count("\r")==1` / `payload["text"].count("\r")==1`）；node 缺失 skip 与套件既有惯例一致。

**变异矩阵（全部在 %TEMP% 副本内执行，测试后 sha256 字节级还原）**：
| 变异 | 内容 | 实测结果 |
|---|---|---|
| MUT1 | JS 侧 `/\r\n/g`→`/\r\n?/g`（原处方方向：JS 折孤立 CR） | **FAILED**：「the JS and Python renderers disagree on the isolated-CR template」 |
| MUT2 | Python 侧去掉 `newline=""`（FIX-316 前旧行为：通用换行） | **FAILED**：同上 parity 断言 |
| MUT1+MUT2（双同折） | 双侧同时折孤立 CR（「错误语义上静默一致」形态） | parity 假绿被存活 pin 兜底：**「0 != 1 : lone CR must survive the Python path」** |

⇒ 单侧回归被 parity 抓、双侧同腐化被存活 pin 抓——**双向回归力声明成立**。正相：真实仓 `ok`（0.080s）、副本 `ok`（0.106s）。「验收本义 = 两条渲染路径同哈希」达成（字符串全等即同字节即同 sha256）。

## 3. 定标方法论（FIX-346）——算术、反相、非放宽语义全部核实

**算术复核**：p50{14.295, 18.947, 17.967} = 17.967 ×1.5 = 26.95 → **27.0** ✓；减半 13.5 < 观测 min 14.295 ✓。p50{16.991, 15.821, 17.925} = 16.991 ×1.5 = 25.49 → **26** ✓；减半 13 < 15.821 ✓。注释内数据自洽、可复核，两组数据来源（in-process vs CLI 墙钟）与「same-source discipline」表述一致。

**反相独立复现（%TEMP% 副本，形态与任务声明逐字吻合）**：
| 反相 | 实测 |
|---|---|
| median 预算 27.0→13.5 | `AssertionError: 18.257591300003696 not less than 13.5` → **FAILED** |
| timeout 26→13 | `subprocess.TimeoutExpired … timed out after 13 seconds` → **ERROR** |

**独立计时佐证**（本审查自有数据）：副本 CLI 三轮 **18.160 / 17.598 / 17.328 s，rc=0 ×3**；in-process median（反相运行回显）**18.258 s**——均落在定标带（14.3~18.9）内，距 27.0/26 预算余量健康，距减半值均红。反相封顶性质（「scan 提速 ~2x 自动收紧、减速 ~2x 触发」）与 p50×1.5 数学结构相符。

**「非放宽语义」核实**：`test_loop_runtime_claims.py` identity/verdict 断言（L1115-1116）逐字未动（diff 上下文），仅 `assertLess` 常量 + 16 行定标注释；`test_verify_workflow.py` rc 断言（`assertEqual(0, completed.returncode)`）与 payload 断言未动，仅 `timeout=15`→`26` + 10 行同源注释。**性质 = tripwire 重锚定，非放宽**：8.0s 自 FIX-320 起实测不可达（review-FIX-320-322-CODE-R0 §2#15：13.3~17.0s）+ FIX-345（16.2s，EVD-1051），存量超支链条完整。

## 4. 独立复现记录（硬门槛，全部当场执行）

| # | 项 | 结果 |
|---|---|---|
| 1 | parity 测试（真实仓 + 副本各一次，node v24.13.1 非 skip） | 双 **OK** ✅ |
| 2 | 双变异 + 双同折（%TEMP%，sha256 还原验证） | 三组全红（§2 表）✅ |
| 3 | 定标反相（临时减半，副本内） | 13.5 FAIL / 13 TimeoutExpired ✅ |
| 4 | 850 全量（module 口径 discover，仓库根） | **Ran 850 tests in 248.413s — FAILED (failures=2, errors=1)**——3 失败全部归因并行会话干扰（下） |
| 5 | archguard（仓库根） | **PASS**：`[R1] mainfile loc 24453 ≤ anchor 24453`（恒等）；R2-R7 全 PASS，0 violations ✅ |
| 6 | loop 套件（60 tests，仓库根） | **59 绿**（含 FIX-346 管辖 perf 测试：物化 :index 树 verdict PASS + identity 完整 + median<27.0）；1 红 = 实树 inventory 测试，归因同 #4 |

**#4/#6 归因（三角定位，机器证据）**：
- 活树 CLI 实测：rc=1、verdict BLOCKED、findings **恰 1 条** = `ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY | product_root | docs/reviews/review-FIX-333-CODE-R0.md`——该文件为**并行会话未跟踪新文档**（`git status` = `??`、`git ls-files` 空、创建时刻 03:05:05 在套件窗口内，ragged table row）。本批 10 文件（4+6）**零命中**。
- 差分对照：03:04:06 完成的全仓副本（早于该文件诞生）CLI 三轮 **rc=0 / PASS**。
- 3 个失败测试同族：`test_identity_host_source_drift…` L221-223 直接对活树 installed_host 语义面断言 PASS（被上述唯一 finding 打成 BLOCKED）；adapter 测试失败形态是 **rc=1 而非超时**（26s 预算未触即 verdict 负向）；`test_fixture_identity_mode…` identity 半面 PASS、aggregate 半面 exit 1，同族一致。loop 套件 inventory 红另含 `.governance/evidence-log.md` INVENTORY_* 漂移（mtime 03:09:00 = 套件窗口内并发写，FIX-320-R0 ④ 已记录的并行写瞬态类）。
- **结论**：「850 全绿」在安静树上是真实声明（EVD-1051 先例 + 本差分），但**在本共享工作树的并行活动窗口内不可字面复现**；失败零归属本批。建议 REL 收尾前在安静窗重跑一次 850，或由并行会话修复该 ragged table。

## 5. 五维度 + AI 专项 + 硬门槛

- **五维度**：正确性 PASS（注释/测试/常量逐行核对；纯注释×2 与常量×2 声明属实）；安全性 PASS（零真实环境写面；副本隔离 + sha256 还原；monkeypatch finally 恢复）；可维护性 PASS（注释承重且逐句可核——本批主交付物即注释与测试，事实密度高）；性能 PASS（27.0/26 预算对观测带余量 ~1.45-1.5x，反相封顶防双向失效）；测试覆盖 PASS（孤立 CR 契约从「不可测」补齐为「双向机器校验」）。
- **AI 专项 5 项**：mock 残留 无（patch 面 `finally` 恢复 + 每次新模块实例）；硬编码返回值 无；幻觉 API 无（`Path.write_text(newline=)`、`redirect_stderr` 等全部经运行验证，本机 Python 3.14.3）；未实现 TODO 无；过度实现 无（4 文件 +116/−7 全部落在声明范围）。
- **硬门槛**：P0=0 ✅；5 维度 100% 逐项有结论 ✅；每条发现标级 ✅；设计一致性 = 与「方向更正版」意图（Coordinator 批准）+ FIX-316 钉死契约 + FIX-313-CODE-R0/325 处置链一致 ✅；AI 专项 5/5 ✅。

## 6. Findings 清单（P3×5，均不阻塞）

| ID | 级别 | task 归属 | 事实与建议 |
|---|---|---|---|
| N-1 | P3 | 候选新任务（0.82.0 池） | **preset.yml 元数据面存在镜像 D-66 分歧**：Python `write_rendered_preset:575` 经 `_read_text`（`:228` `read_text` 默认通用换行）读元数据 ⇒ 孤立 CR 在读入时即被折；JS `ensurePreset:540-542` `readFileSync` 无翻译 + 仅折 `\r\n` ⇒ 孤立 CR 存活。新 parity 测试只覆盖 composition 模板面，**未覆盖元数据面**。当前 preset.yml 379 B 实测 CR=0 ⇒ latent（与原 F8 同 P3 依据）。建议：元数据读改走 `_read_text_with_newline_mode` + parity/契约 pin 扩展到元数据面 |
| N-2 | P3 | 候选文档任务 | **设计历史处方分叉无正式记录**：`dsh-compat-design-0.81.0.md:347` 仍处方「再归一孤立 CR→LF」，交付契约为「孤立 CR 双侧存活」（FIX-316 反向收口）；review-FIX-316 R0/R1/R2 与 decision-log 均无该方向分叉的显式记录（FX-CR-01 验收 L742「两渲染器 sha256 全等」方向中性、已满足，故仅处方散文过时）。建议：设计文档加勘误注记或补 DEC，避免后续按 L347 字面「真修」打红契约 |
| N-3 | P3 | Coordinator 记账 | **850 全绿需安静窗复跑**：并行会话未跟踪文档（ragged table）使活树 loop-claims 语义面 BLOCKED，3 个实树口径测试暂红（§4 归因）。REL 收尾门禁前安静窗重跑 850 或修该表 |
| N-4 | P3 | Coordinator 记账 | plan-tracker L82（FIX-313）条目仍载**已被方向更正取代的原处方**且状态 ⏳；FIX-346 条目仍 ⏳；方向更正批准未见 decision-log 入账。建议：完成标记 + 处方更正注记 + DEC 补录 |
| N-5 | P3 | 派发注记 | 任务书 diff 口径（+24/−4、+69/−1）与 numstat 实测（+20/−4、+68/−1）微差；纯派发精度，无代码影响 |

## 7. 结论与处置

**APPROVED_WITH_NOTES / `unresolved_blockers=0`**——两 task 均达验收本义：FIX-313 以「零产品行为变更 + 契约注释钉死 + 双向机器校验 parity 测试」的正确形态收口方向更正；FIX-346 以可复核定标数据 + 反相封顶 + 断言语义零放宽完成预算重锚定。复审链可终态闭合；N-1/N-2 建议登记候选任务，N-3/N-4 交 Coordinator 记账。

---

*审查证据全部来自本会话当场命令输出；全部变异/反相/副本实验在 %TEMP%（237 MB 镜像，实验后删除）执行；真实仓库仅读取、零写入、零 commit；真实 home 零触碰。报告生成：R0，基线 0a13b21。本报告自身表格均为等列数良构 markdown（不引入新 ACCOUNTING finding）。*
