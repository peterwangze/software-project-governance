# CODE R0 — FIX-458 / FIX-459 独立审查报告

- **Reviewer**：Code Reviewer（M7.4 独立审查；Developer 不自审，Reviewer 不改码）
- **日期**：2026-10-24
- **审查对象**：working tree vs HEAD=fb56415（工作区冻结态：stash 恰 1〔FIX-444/455 暂停 WIP〕、未跟踪×2 不在范围）
- **审查方式**：逐项证据核验 + 只读命令独立复跑（不信 Developer 自报）
- **triage/证据链**：TRIAGE-FIX-458.json / TRIAGE-FIX-459.json / EVD-2150 / EVD-2151

## 结论

| 任务 | 结论 |
|---|---|
| **FIX-458**（committed commit-msg hook pin 0.98.0→0.99.0） | **APPROVED** |
| **FIX-459**（STATIC_PIN_EXEMPTIONS 台账 re-anchor + 新增豁免 5 行 + tvw 六处派生） | **APPROVED_WITH_NOTES（unresolved_blockers=0）** |

## 审查清单逐项证据

### 1. FIX-458 diff 精确性 — PASS
`git diff HEAD -- skills/software-project-governance/infra/hooks/commit-msg`：恰 1 行（`-# @version: 0.98.0` / `+# @version: 0.99.0`，diffstat 2± 即此行）；上下文行零变化；与 SKILL.md frontmatter `version: 0.99.0`（L3）一致——即 `check_version_consistency` 的权威源。

### 2. 台账 re-anchor 真实性 — PASS（8/8 行号核验）
| 台账行（新） | token | 实测该行内容 | 旧行实测 |
|---|---|---|---|
| tvw:21309 | "0.93.0" | `result = vw.check_release_readiness(version="0.93.0")` ✓ | L21304 无 token ✓ |
| tvw:21341 | "0.93.0" | `result = vw.check_release_readiness(version="0.93.0")` ✓ | L21336 无 token ✓ |
| tvw:20808 | "0.94.0" | `"\| **P1** \| FEAT-081 \| 词集夹具票 \| — \| 0.94.0 \| closure \| "` ✓ | L20803 无 token ✓ |
| tvw:20811 | "0.94.0" | `"\| **P2** \| FEAT-082 \| 下版处理 票 \| — \| 0.94.0 \| closure \| "` ✓ | L20806 无 token ✓ |

行号漂移真实（e254584 载荷插入致 +5），条目形态与既有行一致（`_REASON_FUTURE_TARGET`/`_REASON_FIXTURE_ROW_TEXT` 沿用原 reason 常量）。

### 3. 新增豁免 5 行（line, token, reason）完整性与实质理由 — PASS
| 条目 | 目标行实测（逐行读取证实携带字面 0.99.0） | 理由核验 |
|---|---|---|
| tba:331 | `flag = ba.migration_flag("0.99.0", "0.84.0")` | migration_flag 的 plan-newer 操作数=frozen scenario payload，镜像同块既有 0.84.0 行（326/331/336）——同线双条目合法（allowed_lines 按 token==active 精确匹配，rot-guard 双向审计） |
| tarc:549 | `result = archive.migrate_by_version("0.99.0", "0.99.9", dry_run=False)` | 迁移窗操作数为合成 future-cycle 对——被测对象本身，不可派生 |
| tarc:724 | 任务行夹具文本（目标版本列 0.99.0） | out-of-range 场景载荷，判定消费行文本非版本单元格 |
| tarc:4005 | 同上形态（REL-999 行） | 同上 |
| tem:61 | `\| **P1** \| FIX-903 \| 活动任务丙 \| — \| 0.99.0 \| 在途 \| 🔄 进行中 \|` | 在途行经 evidence migration 保持热的证明夹具——被测语义即版本单元格文本 |

派生 vs 豁免的判定原则一致且有据：**字面值编码「相对 active 的语义」处派生（tvw 六处）；字面值是 frozen 场景载荷处豁免（本 5 行）**——与台账内 0.84/0.93/0.94/0.95 既有行的哲学完全同构。

### 4. 六处派生形态与语义等价 — PASS
- 形态：`from resolve_entry import read_active_version` + `(read_active_version() or "0.0.0").split(".")[:2]` + `f"{_major}.{_minor + 1}.0"`——与库内既有先例（test_verify_workflow.py L2263-2265、L20468-20474、L25594+）逐字同形（含 `or "0.0.0"` 守卫）。
- 语义等价：方法一（six-condition 3）`later`=active 次版本+1，按定义超出一切以 active 为上界的窗口——`assertFalse(migrate)`/`reason=="ref_version_out_of_range"`/`assertIn(later, detail)`/`end=later 时 migrate=True 且 version==later` 五项断言对象未变，仅参数化；SUT 为数值元组比较，0.100.0>0.99.0 恒成立，未来每次 bump 均保持原语义。方法二 `in_flight` 同理（原注释自认 literal「assumed it would never ship」——派生恢复原始意图）。
- 旧注释修正准确（两处新注释如实描述派生与 459 缘起）。

### 5. 安全语义不回退（关键项）— PASS
- `check_version_consistency`（version.py L77-104）的 hook pin 检查（L99-104，本次抓出 `[FAIL] hooks/commit-msg: @version=0.98.0` 的那条）**不读取 STATIC_PIN_EXEMPTIONS**——豁免表无法触及该 FAIL 路径；本次修复正是让真实 pin 对齐而非豁免掉检查。
- 豁免消费点唯一（L490-556 测试文件 pin 扫描）：`allowed_lines` 仅收纳「entry token == active_version」的行号——非无差别放行；且 L535-555 rot-guard 反向审计（目标行失 token 即 WARN）——正是抓出 stale 4 行的机制，re-anchor 后继续守护新增 5 行。
- version.py diff 三个 hunk 全部落在 STATIC_PIN_EXEMPTIONS 字典数据行/注释，零逻辑改动。

### 6. 范围纪律 — PASS
`git diff HEAD --stat`：恰 3 文件（commit-msg 2± / version.py 34 / test_verify_workflow.py 33）= 两任务声明文件面；tba/tarc/tem 四个测试文件按方案走台账豁免**不改文件**（diff 中 absent，符合设计）；未跟踪×2 与 stash 未触碰。

### 7. 独立复跑四门 — PASS（全绿）
| 命令 | 结果 |
|---|---|
| `verify_workflow.py`（落盘全量） | exit 0，`== Verification Result: PASSED ==`，**static-version-pin WARN=0（修复前 15）**，FAIL 行=0（日志 %TEMP%\review-fix458-459-verify.log） |
| `unittest discover -p test_static_version_pins.py -v` | `Ran 25 tests in 2.753s — OK` exit 0（含此前失败的 `test_ledger_rows_are_live_on_current_tree` / `test_real_tree_scan_is_warn_only_and_clean` 双双 ok） |
| `check-manifest-consistency --fail-on-issues` | `[PASS] Manifest and filesystem are consistent.` exit 0 |
| `check-cross-references` | exit 0 |

## Notes（非阻塞）
- **N1**：tba:331 现为同线双条目（0.84.0 + 0.99.0）——token 作用域合法、rot-guard 双向覆盖；0.84 token 未来漂移时 rot-guard 会如实报警。
- **N2**：本地全量套件 A组 7 项 Windows-bash 族 FAIL 为存量环境缺陷（暂停 FIX-444/445 WIP 所有，其 docstring 逐字预言），不在本审查范围；CI Linux 为权威门。
- **N3**：CRLF 规范化警告（commit-msg / test_verify_workflow.py）为 git 提交期常规行为，diff 内容干净，无实质影响。
- **N4**：tba331 注释自述「dormant after this bump」——0.100 窗口可随例行情节修剪台账，属常规维护。

## 审查边界声明
本审查仅运行只读命令与写入本报告文件；未修改任何代码、未触碰 .governance/、未动 git stash/.git。Developer 本地门自报与独立复跑结果一致。
