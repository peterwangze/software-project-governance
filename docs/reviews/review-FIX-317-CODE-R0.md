# FIX-317 代码审查报告（Code Review R0）

- **任务**：FIX-317 — V1 审查收口（契约层 4 条 findings 闭合）
- **Round**：0（首次审查；无前轮引用）
- **审查对象**：当前工作树未提交改动（HEAD = `6081285`），FIX-317 的 3 个文件：`skills/software-project-governance/infra/dsh_contract.py`、`skills/software-project-governance/infra/tests/test_dsh_contract.py`、`adapters/dsh/host-contract.json`（其中 17+/1− 属本任务）
- **Reviewer**：Code Reviewer Agent（只读；仓库零写入）
- **结论**：**APPROVED_WITH_NOTES**，`unresolved_blockers=0`
- **来源 finding 闭合**：F-1 ✅ 已修复 / F-2 ✅ 已修复 / F-3 ✅ 已修复 / F-5 ✅ 已修复；**新引入 = 0**

## 1. 硬门槛裁决

| 门槛项 | 阈值 | 实测 | 裁决 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **0** | ✅ PASS |
| 5 维度全覆盖 | = 100% | 5/5 独立结论 | ✅ PASS |
| 每条发现标注级别 | = 100% | 14/14（P1×1 已闭合、P2×1、P3×12） | ✅ PASS |
| 设计一致性检查 | 已完成 | §2.4/§2.5.1/§2.7/§3.2/§3.3/§4.1/§5.6/§6.1/§6.2 逐条比对 | ✅ PASS |
| AI 代码专项 5 项 | 全部完成 | mock/硬编码/幻觉 API/未实现 TODO/过度实现 逐项结论 | ✅ PASS |

## 2. Findings 全表（14 条）

| # | 级别 | 文件:行号 | 事实 | 影响 | 建议 |
|---|---|---|---|---|---|
| **F-1** | **P1→已闭合** | `dsh_contract.py:388-393` | **独立实测**：`UnicodeDecodeError` MRO = `[UnicodeDecodeError, UnicodeError, ValueError, Exception, BaseException, object]`，`isinstance(e, OSError) == False` ⇒ 旧 `except OSError` 确实穿出；新 `except (OSError, UnicodeDecodeError)` → `ContractUnreadable`（实测消息含类名 + 全路径）；不归 `ContractMalformed` 符合 §2.5.1:208；权限/目录/缺失已由 `OSError` 子类覆盖；反相测试走**真实文件系统**（非 mock） | — | ✅ 无需返工 |
| F-2 | P2→已闭合 | `dsh_contract.py:339-343`；测试 `:626` | 旧判据为**存在性**判据，实测 ACCEPT `True`/`null`/`"false"`/`0`；新判据四类全拒；**缺键旧新都拒绝**（旧检查未丢失）；与 `source`（`:335-338`）对称 | 见 §4 | F-N1/F-N2/F-N3 |
| **F-3** | P3→已闭合 | `host-contract.json:1581` | 与 D-05 同形的 `["V1","V8"]` 共 8 条，**全部** `weakened` 且**全部无** `weakened_at`（依据 `elimination.notes.field_semantics`）；抽验 D-07/D-45/D-60 三条同形；`weakened_at ∈ slice` 17/17 成立 | — | ✅ 无需返工 |
| **F-5** | P3→已闭合 | `host-contract.json:1203-1218` | `target:"medium"` **恰当**（`negative_fixtures:[]` ⇒ 不可 strong；也非 weak，因现有守卫抓得住 V1 声明面）；`audit_ids:["D-57"]` **归属成立**（§3.3 第 12 行 D-57 落地形态 = §2.7 + TTL + K-7，与 §6.1 V7 行一致）；**2/2 guard 可解析**；`gap_note` **诚实**（明写 V1 单元级 + 上修前置） | — | 见 F-N1 |
| F-N1 | P3 | `host-contract.json:1209/1212` | `negative_fixtures:[]` + `requires:[]` 抓不住 `--record-evidence` 实际写平面（gap_note 已坦诚登记） | V7/V8 上修需补反相 fixture 与 `requires` | V7/V8：隔离环境实测写路径后再上修 strong |
| F-N2 | P3 | 同上 | `gap_note` 写"上修为 requires 含 dsh-plane"，测试令 `requires` 词表恒为 `{node, dsh-plane}` ⇒ 无漂移 | 无 | 保留 |
| F-N3 | P3 | `dsh_contract.py:342-343` | 缺键消息由"missing required field…"改为"…must be false — present and exactly `false`"，**丢失"缺键 vs 值错"区分度** | 诊断力轻微下降 | 措辞改为 `must be present and exactly false (missing or not-false)` |
| F-N4 | P3 | 测试 `:562/:626` | `_RECORDED_FIELDS` 存在性断言（`:331-334`）已覆盖 `source` 缺键；反相矩阵对 `recorded` 含缺键（7 例 + positive control），对 `source` 仅测值错 | 覆盖不对称（非缺口） | V8 补 `source` 缺键一例 |
| F-N5 | P3 | `dsh_contract.py:339` | `is not False` 是 **V1 特化**断言：V8 若写 `recorded: true` 会**全局拒载** ⇒ 所有消费者失效 | 未来切片耦合风险（当前 V1 正确） | 契约侧登记退出条件，或 V8 改为扫描 `host.rows[]` |
| F-N6 | P3 | `dsh_contract.py:388` | 其它读失败形态已由 `OSError` 覆盖；仅"路径含 NUL → `ValueError`"为理论缺口，但 `contract_path()` 不接受用户输入 ⇒ 不可触发 | 无 | 无需动作 |
| F-N7 | P3 | `dsh_contract.py:231-232` | 消息插值 `{path}` 未做正斜杠归一（显示反斜杠） | 无 | 可选归一化 |
| F-N8 | P3 | 仓库根 | 前轮 F-6 残留 `.tmp-k2-scan.py` **已不存在**；FIX-317 未新增仓库根 scratch | — | 无需动作 |
| F-N9 | P3 | `test_dsh_contract.py`（K-9/K-8 面） | guard 解析 60/60 成功（含 FIX-315 改名后的新名）；`strong` 14/14 均有 `negative_fixtures`；`necessary` 无 `none` | — | 保留 |
| F-N10 | P3 | `host-contract.json` 新增条目 | 未引入第二事实源：`evidence.recording.*` 仍为唯一数据源；测试中三处字面量为**守卫式断言**（模块 `:130-134` 已裁定"人工誊抄 = 契约缺陷，不是数据"） | — | 保留 |

## 3. 独立复算结论（自算，未采信自报）

| 项 | 复算方式 | 结果 | 与自报 |
|---|---|---|---|
| `coverage.entries` 数量 | 自解析契约 JSON | **26** | ✅ 25→26 |
| `subject` 唯一性 | `Counter` 去重 | **26/26 distinct，dup=[]** | ✅ |
| `audit_ids` 并集 | 自算 `set` 并集 | **100**；necessary 72 **uncovered=[]** | ✅ 未退化 |
| `dispositions` | 自算 `D-01..D-100` 差集 | **100/100 distinct**，无缺无重 | ✅ |
| guard 可解析 | 自解析 **60** 条 guard 引用（`file::method` 对真实方法名 / check 段号） | **60/60 成功** | ✅ |
| `strong` ⇒ 反相 | 自算 | 14 个 strong 全部有 `negative_fixtures`；`necessary` 无 `none` | ✅ |
| F-1 反相有效性 | 三路：① 真实字节 `\xff\xfe` 的 `isinstance(e,OSError)=False`；② 打桩 `Path.read_text` → 新处理器 `ContractUnreadable` / **旧处理器裸穿出**；③ 测试走真实文件系统 | **真实有效** | — |
| F-2 反相有效性 | 突变矩阵 7 例 + 2 例 `source` 对照，逐例比对旧判据/新判据/实际 `load_contract` | **真实有效**（含 positive control） | — |
| 三套件 | `test_dsh_contract` / `test_dsh_compat` / `test_dsh_adapter` | **108 OK / 55 OK / 46 OK** | ✅ |
| 门禁 | `check-manifest-consistency --fail-on-issues` / `cleanup.py --dry-run` | **PASSED (exit 0)** / 无冗余文件（零删除） | ✅ |

## 4. F-2「是否过严」判定 —— **不过严**（不是破坏性收紧，是设计要求的收紧）

1. **设计已钉死为布尔常量**：§2.4:148「V1 阶段…MUST 标 `source: recorded` + `recorded: false`」；§6.1 V1② 逐字重复 ⇒ 该字段在 V1 **不是开放值**。
2. **访问器自述即该语义**：`dsh_contract.py:33-38`「must be *present* and flagged `source: recorded` / `recorded: false`」。
3. **旧行为确实宽松（实测）**：旧判据接受 `true`/`null`/`"false"`/`0`，与设计矛盾；缺键旧新都拒绝。
4. **唯一风险"未声明性"已评估**：改动未触碰契约数据；实测 29/29 行 `recorded` 值域 = `{False}` 单值 ⇒ **不存在"旧接受、新拒绝"的实际文件**；拒绝只发生在值已违反 V1 规范时，方向为 fail-closed。
5. **保留意见（非阻塞）**：断言为 V1 特化，V8 写 `recorded: true` 时必须同步上修（F-N5）。

## 5. 五维度结论

- **正确性 ✅**：`is not False` 正确利用 `is` 身份判定（`0 == False` 但 `0 is not False` ⇒ 故意排除 `0`）；`recorded.get()` 缺键返回 `None → is not False → True`，旧键检查语义被同一判据完整覆盖（**实测**）；`raw` 旁路（`:394-401`）与缓存未被失败路径污染。
- **安全性 ✅**：零网络/零 shell/零 `eval`/零凭据；唯一 I/O = 单文件 `read_text`；`test_load_never_writes_the_contract_file` 断言 SHA256 + `st_mtime_ns` 不变；异常消息不泄露环境信息。
- **可维护性 ✅（2 条 P3）**：注释说明"为何不是 OSError"；复用 `_fail_unreadable` 无重复逻辑；F-N3/F-N7 为措辞级。
- **性能 ✅**：无新增复杂度（单次比较 + 异常元组多一元）；契约 74,702 B 单次解析。
- **测试覆盖 ✅（2 条 P3）**：2 条新测试**非自证式**——F-1 反相走真实文件系统并断言 4 项（异常类 / 消息含类名 / 含异常类型名 / 含全路径）；F-2 反相含 5 个突变值 + 缺键 + positive control。合计算 **Ran 108 OK**。

## 6. 设计一致性

- **§2.5.1:206-212**：F-1 落在 Unreadable 行（"文件不存在 / 读失败（OSError）"）且**不**降级为 Malformed ⇒ 消费者语义正确（Malformed = 产品缺陷必须 FAIL）。✅
- **§2.4:148 / §6.1 V1②**：F-2 的 `recorded: false` 硬约束与 §2.7 单点写入方向一致。✅
- **§3.2 D-05 / §3.3**：反查发现 §3.2 的 D-05 切片列原为 **V1（闸门）/ U-1（声明）**；FIX-317 改的 `["V1","V8"]` 对应**弱化落地面**（V1 = `evidence.compat_range`；V8 = S3 越界判据），与 §3.3 给 D-57 写 "V7"、给 D-60 写 "V1/V8" **同口径**；U-1 是 §9 的**验证单元**非切片，由 `notes` 的 `deferred to U-1` 承接 ⇒ **不自相矛盾**。K-9 的 `removed_at ∈ slice` 不适用于 weakened 项（实测 17/17 满足 `weakened_at ∈ slice`）。✅
- **§4.1 + §3.3 第 12 行**：F-5 的 medium + 空 `negative_fixtures` 结构上不可能"声明强于佐证"。✅

## 7. 范围纪律

- FIX-317 契约改动 = **17+/1−** 精确成立（新增条目 15 行 + `D-05.slice` 1+/1−）；逐 hunk 归属已核实（另 1+/1− 属 FIX-315，未评判）。
- 未触碰：`dsh_compat.py` / `test_dsh_compat.py`（FIX-315 面）、`lib/index.js` / `launch.py` / `verify_workflow.py` / `registry.py`（V2/V8 面）、`.governance/`（`git status -- .governance` = 0 行）。
- 仓库根 scratch 残留 = **0**；唯一未跟踪文件 `docs/release/real-machine-acceptance-0.81.0.md`（非本任务产出）。

## 8. 审查期写入防护（Reviewer 自证）

- 审查前后 `host-contract.json` SHA256 均为 `96F92485…43FC6E`，未变；`git status` 5 文件改动集与审查前**逐字相同** ⇒ **全程零仓库写操作**。
- 全部构造性实验（字节损坏探针、`read_text` 抛错探针、突变矩阵、复算脚本）均在 `%TEMP%\spg-fx317-*.py` 与 `TemporaryDirectory()` 内完成，**未在仓库路径上做任何改写-还原**（吸取 `review-FEAT-030-CODE-R0.md` §7 教训）。
- `DSH_HOME` 全程重定向至 `%TEMP%\spg-fx317-probe`，未读/未写 `~/.dsh`。

## 9. 真实环境命令上报表（R4）

| # | 命令 | 退出码 | 影响路径 |
|---|---|---|---|
| 1 | `git log -1` / `git status --porcelain[-uall]` / `git diff HEAD --[--stat/--numstat]` / `git show HEAD:<file>` | 0 | 只读 |
| 2 | `$env:DSH_HOME="$env:TEMP\spg-fx317-probe"; python -m unittest … -p test_dsh_contract.py` | **0（Ran 108, OK）** | 临时目录 |
| 3 | 同法 `-p test_dsh_compat.py` | **0（Ran 55, OK）** | 临时目录 |
| 4 | 同法 `-p test_dsh_adapter.py` | **0（Ran 46, OK）** | 临时目录 |
| 5 | `verify_workflow.py check-manifest-consistency --fail-on-issues` | **0（PASSED）** | 只读仓库 |
| 6 | `cleanup.py --dry-run` | 0（无冗余文件） | 只读仓库 |
| 7 | `python %TEMP%\spg-fx317-{recompute,guards,probe1,probe2,lines}.py` | 0（1 次 GBK `UnicodeEncodeError` 仅发生在分析脚本 stdout，已重跑） | 只读仓库 + `%TEMP%` |
| 8 | `Get-FileHash` / `[System.IO.File]::ReadAllBytes` / `Test-Path` | 0 | 只读 |

**未验证项（NOT_VERIFIED）**：无。

## 10. 结论与后续动作

**APPROVED_WITH_NOTES（`unresolved_blockers=0`）** —— 零 P0；硬门槛 5/5 通过；来源 4 条 findings 全部闭合且经独立复算复现；未引入新缺陷。

后续动作建议（全部非阻塞）：
1. **提交前排程**：FIX-317 与 FIX-315 共享 `host-contract.json` 索引，提交前 MUST 分离（先落 FIX-317 的 2 个 hunk，再落 FIX-315 的 1 行）。
2. V7/V8 工作项：F-N1（`evidence.recording` 上修 strong 的反相 fixture）。
3. V8 MUST 同步：F-N5（`recorded` 谓词放宽）；F-N4（`source` 缺键一例）。

---

*报告结束（R0，APPROVED_WITH_NOTES / unresolved_blockers=0）。*
