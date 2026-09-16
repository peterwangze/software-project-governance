<!-- machine-suggested-next-round: REVIEW-FIX-320-R1 / REVIEW-FIX-322-R1 | round: R0 | reviewer: Code Reviewer (subagent) | verdict: NEEDS_CHANGE | unresolved_blockers: 1 -->

# FIX-320 + FIX-322 合并代码审查 R0（一报告双 task）

- 审查对象：工作树未提交改动（基线 HEAD `a260637`）本批 6 文件；并行批 A（FIX-342/344：archive.py / review_domain.py / task_priority.py / test_archive_decision_attribution.py / test_task_priority.py / test_verify_workflow.py）已排除，其 diff 未纳入审查。
- 审查者：Code Reviewer（独立 subagent，只读审查 + 只读验证命令；反相全部在 %TEMP%/临时副本执行，真实仓库零改动、零 commit、零 stash——并行批 A 共享工作树，stash 被主动禁用）。
- 结论：**NEEDS_CHANGE**（P0=0，P1=1，unresolved_blockers=1）。6 文件代码本身零 P0/P1 缺陷；P1 针对 Developer 声明①的**自愈范围口径过宽**（证据见 F-1），返工面为声明/证据措辞修正 + 性能缺口任务登记，非代码返工。复审轮建议：REVIEW-FIX-320-R1 / REVIEW-FIX-322-R1（轻量）。

---

## 1. 逐行审查结论（6 文件）

### FIX-322：`infra/checks/dsh_boundary.py`（K-2 package 类整串判定）
- 实现：`_PACKAGE_RE.match(literal)` 锚定字面量起点 + `rest` 为空或 `/` 前缀子路径归属 + `declared["package"]` 判定 + `report(group(0))`（上报包 token 而非整字面量）。+8 行设计注释如实记录动机（F-07/N-2 闭环）与 `_ENV_NAME_LITERAL_RE` 整串判定的类比。
- 边界语义核实：`rest.startswith("/")` 使 `"@scope/pkg/sub"` 按包前缀归属判定；`"@scope/pkg"` 裸形维持原判。锚定用 `.match()`（位置 0），模式本身未加 `^`，正确。
- 语义边界（P2-1，见 §4）：版本后缀形态（如 `"@scope/pkg@^1.2"`，rest 以 `@` 开头）在新语义下**不再触发**；真实盘点无此形态（新旧违规集 0=0），守卫测试未覆盖该形态——建议注释显式声明或补守卫，可遗留。

### FIX-322：`tests/test_dsh_boundary.py`（+3）
- 2 条规格负相（句子提及未声明包 = prose；转义内引号消息不暴露包事实）+ 1 条防过矫正守卫（裸/子路径整字面量仍触发，断言违规元组逐字段）。
- 夹具模式与既有套件一致（临时目录 + `_copy_artifact`，零仓库写入）。
- **反相实证**（%TEMP% 镜像 788 个 git 跟踪文件 → 恢复 findall 旧实现）：`Ran 134 tests, FAILED (failures=2)`，恰为上述 2 条负相红，防过矫正守卫与其余 132 条保持绿——「恢复 findall→恰 2 新负相红」成立。工作树版 134 tests OK（红→绿成立）。

### FIX-322：`tests/test_dsh_contract.py`（锁外纯注释）
- diff 逐行核对：仅 `k2_scan` docstring 重写 + 内联注释更新，功能代码（`findall` oracle）未动。「锁外纯注释」声明**属实**。oracle/产品分叉标注（V2 oracle 保守保留 findall、整串判定仅产品扫描器）与两处实现现状**如实相符**。

### FIX-320：`core/loop-runtime-claim-exemptions.json`（新，4 条）
- 结构：4 条 × 九键精确（`exemption_id/finding_code/root_owner/normalized_path/locator/claim_id/reason/source/expected_duration`）。
- 归因质量：每条 reason 写明误判机理（记录性文本被语义分类器误判），source 可追溯（EVD-1018 / DEC-195 处置(b) / EVD-1041 + Coordinator 裁决日期 2026-09-16），expected_duration 含存续条件 + 删除义务 + digest 同步义务。**可审计性良好**。
- 裁决口径一致性：3×UNSUPPORTED_AFFIRMATIVE + 1×AMBIGUOUS_SUBJECT_RELATION = 豁免面 4 条；2×AUTHORITY 未入账本 = FIX-345。**与声明一致**。
- digest 锚覆盖面：`_exemptions_digest` 为**整个解析对象的 canonical JSON 摘要**（sort_keys + 紧凑分隔符）——九键 schema 全部字段、全部条目、schema_version 全在内。当场实测 `digest_match=True`；id 锚与代码 `REQUIRED_EXEMPTION_IDS` 一致。

### FIX-320：`infra/checks/loop_runtime_claims.py`（+135）
- **三态加载 fail-closed 方向**（逐分支核实 + 实测）：
  - absent（安全解析后文件不存在）→ `[], []` 严态零豁免——实测未提交态（index 物化树无账本）= BLOCKED/4 classify findings 幸存/0 豁免；
  - drift（digest/id 集/重复 id/键面不精确/空列表/坏 JSON/symlink-reparse 路径）→ typed finding（`EXEMPTIONS_CONTRACT_DIGEST_DRIFT/EXEMPTIONS_SET_DRIFT/EXEMPTIONS_DUPLICATE_ID/EXEMPTIONS_SCHEMA/EXEMPTIONS_INVALID/EXEMPTIONS_MISSING/EXEMPTIONS_PATH_INVALID`）且**豁免全作废**——三反相全部实测复活；
  - present+匹配 → 豁免应用。
  - `_load_json` 错误码族（`{KIND}_MISSING/INVALID/SCHEMA/PATH_INVALID`）与 `_load_exemptions` 的双确认（guarded reader EXEMPTIONS_MISSING + 裸路径 `.exists()` 复核）防「symlink 目录 + 裸路径存在」被误判为严态缺席——方向正确（落入 fail-closed findings）。
- **五元组匹配紧致性**：`finding_code + root_owner + normalized_path + locator + claim_id` 全键相等才命中；无单键/前缀匹配。误命中面分析：locator 为语义会计 `accounting:<line>:<col>`，目标文档任何增删行都会使 locator 漂移 → 豁免失配 → findings 复活（fail-closed 方向）；未来同形 finding 需精确落在同 path+locator+claim_id 才会被吞——面积极窄且该文档改写本受 `expected_duration` 删除义务约束。判为可接受残留（P3-4 讨论项：同一五元组多个 findings 理论上可被单条目重复豁免，现景观测不可达，且每次应用均有披露）。
- **应用点**：`scan_loop_runtime_claims` 尾部——所有 findings 源（含 final_errors + INVENTORY_DIGEST_DRIFT）之后、verdict 之前；豁免错误先并入 findings（drift 即 BLOCKED）；verdict 只看 findings 剩余。与设计声明一致。
- **审计披露**：`exemptions_applied` 每条含 id/五元组/reason/source/expected_duration；`as_dict()` 纯加性新增 `exemptions_applied` + `exemptions_count` 两键（diff 逐行核实，无键面变更）——「CLI 键面纯加性」声明**属实**。
- **schema_role 自保护**：`_json_units` 对账本候选（root_owner+精确路径+含 `exemptions` 键）打 schema_role → 描述性文本不生成语义 claim 单元。实测：installed_host 全仓扫描 PASS/0 findings——账本自身文本（含 "active and complete" 类描述词）零触发。充分。
- 防篡改三反相（真实仓库扫描面 + 临时 plugin_home，逐项实测）：digest 改词 → `EXEMPTIONS_CONTRACT_DIGEST_DRIFT`；删条目 → `+EXEMPTIONS_SET_DRIFT`；加字段 → `+EXEMPTIONS_SCHEMA`；三者全部 4 findings 复活 + `exemptions_applied=0` + verdict BLOCKED。**「篡改→豁免全作废+finding 复活」实证成立**。

### FIX-320：`tests/test_loop_runtime_claims.py`（+FIX320ExemptionLedgerTests）
- 实测 **7 方法 / 8 次执行全部 OK**（`test_real_repository…` 含 installed_host/product_release 双 subTest； Developer 声明「8 测试」按执行次数口径成立，方法数 7——P3-2 口径注记）。
- 质量要点：fixture 测试以 `patch.object` 临时替换 digest/id 锚（addCleanup 清理，无残留）；`TRIGGER_TEXT` 运行时拼接避免测试文件自身被判活能力声明（自指防护，注释如实）；实树集成测试刻意不断言顶层 verdict 并如实注明 INVENTORY_* 并行写窗口瞬态（遗留④既有防护确认）。
- 覆盖面：转移+披露、digest 漂移、id 集漂移、未知字段、缺席严态、不匹配不动、实树双模式——机制六面 + 集成，覆盖充分。

## 2. 独立复现记录（全部当场执行）

| # | 验证项 | 命令/手段 | 实测结果 |
|---|--------|-----------|----------|
| 1 | digest/id/键面锚 | `checks.loop_runtime_claims` API 实测 | digest_match=True；id 集一致；九键精确 |
| 2 | CLI installed_host | `verify_workflow.py check-loop-runtime-claims --scan-mode installed_host` | **PASS / 0 findings / 4 披露**（exit 0），locator 与账本逐一对应 |
| 3 | CLI product_release | 同上 `--scan-mode product_release` | **BLOCKED / 恰剩 2×AUTHORITY_SOURCE_OCCURRENCE**（host `.governance/decision-log.md`、`plan-tracker.md` "found 0"）/ 4 披露（exit 1）——「如实披露」成立 |
| 4 | dsh 测试 | `python -m unittest tests.test_dsh_boundary tests.test_dsh_contract`（infra cwd） | **254 tests OK**（boundary=134，contract=120）——「134+120 passed」成立 |
| 5 | loop 测试 | `python -m unittest tests.test_loop_runtime_claims` | 59 tests：**2 FAIL**（inventory 预算测试 2×AUTHORITY；perf 测试 verdict BLOCKED）——失败面与声明③②吻合，归因见 §3 |
| 6 | FIX320 新测试类 | `unittest tests.test_loop_runtime_claims.FIX320ExemptionLedgerTests -v` | 7 方法/8 执行 **OK** |
| 7 | FIX-322 反相 | %TEMP% 镜像 788 git 跟踪文件 + 恢复 findall | **恰 2 新负相红**（句子提及/转义内引号），守卫绿，其余 132 绿 |
| 8 | 两态模拟（归因①机理） | %TEMP%：`materialize_loop_runtime_git_root(repo,":index")` ± 投放账本 | 未提交=BLOCKED/4 classify/0 豁免；投放账本（模拟已提交）=**PASS/0 findings/4 豁免**。仓库零改动 |
| 9 | 防篡改三反相 | 真实扫描面 + 临时 plugin_home 三种篡改 | 三者全部 EXEMPTIONS_* + 4 findings 复活 + 0 豁免 + BLOCKED |
| 10 | 归因②事实 | `Select-String` 统计锚行 | DEC-104 行=0、AUDIT-133 行=0、EVD-707 行=1——恰 2×AUTHORITY；FIX-345 已登记 P2（「6 条中 2 条属非豁免族」+ REL-078 门禁前置）|
| 11 | Check 28w | `verify_workflow.py check-dsh-boundary` | **PASS 0 failing**；K-2「outside-contract host literals: 0 (11 declared consumer(s) scanned)」逐字吻合 |
| 12 | archguard | `verify_workflow.py archguard-ratchet` | PASS（0 violations；CLI keys 84/84 frozen）|
| 13 | cleanup 残留 | `cleanup.py --dry-run --json` | status=clean——账本经 manifest `core/` 整目录声明（product.entries `skills/software-project-governance/core/` type=dir → expand）入 canonical，**无残留删除风险** |
| 14 | K-2 新旧盘点 | 仓库内 K2_CONSUMERS 逐行 quoted-literal 双逻辑比对 | consumers=11 ✓；旧 findall 违规=0 / 新 match 违规=0，**违规集全等**；含 @ 字面量 52、包形字面量 30（声明 37 未按两种口径复现——P3-1）|
| 15 | perf 预算（归因①补充） | 两态模拟 PASS 后计时 3 轮 × 3 次扫描 | **median = 13.341s / 17.019s / 13.338s，全部 > 8.0s 硬预算**（测试 L1083 `assertLess(median, 8.0)`）→ F-1 |

## 3. 存量红自愈归因——独立验证结论

- **② inventory 2×AUTHORITY（FIX-345）**：✅ 完全证实。host 热文件锚行 0 次出现为客观事实（FIX-343 归档迁移所致，工作树 `.governance/` 未被本批触碰，检查逻辑不在本批 diff 内 → 基线同红）；fail-closed 正确触发；FIX-345 已在册（P2，0.82.0，REL-078 门禁前置）。
- **① performance 测试 commit 后自愈**：⚠️ **机理成立但范围声明过宽（F-1，P1）**。`materialize_loop_runtime_git_root(product_root, ":index")` 物化 git index 树（`.governance` 被 gitignore，物化树无 AUTHORITY 检查对象——与失败快照仅 4 classify 吻合）；账本未跟踪（`git ls-files` 空）→ 严态 → BLOCKED。模拟投放账本后 verdict/identity 断言（L1081-1082）转绿。**但** L1083 性能断言（median<8.0s，硬编码）在当前环境下三轮实测 13.3s/17.0s/13.3s——基线上该断言因 L1082 先失败而**不可达**（被 verdict 红掩盖），commit 后将变为可达且按实测预计仍红。注：测量处于并行批 A 负载下（RISK-048/AUDIT-151 自认负载为协变量），但 66%~113% 超支幅度远超合理协变量修正，且无任何一轮接近 8.0s。
- **③ adapter 15s 超时**：⏳ **未独立复现**（dsh adapter/compat 测试面不在本批 6 文件测试范围内，未运行）——按事实红线标「未验证」。支持登记独立小任务的处置建议。
- **④ 并行写窗口 INVENTORY_* 瞬态**：✅ 既有防护确认（final inventory re-check + DIGEST_DRIFT finding；实树集成测试注释如实披露该瞬态并刻意不断言顶层 verdict）。

## 4. Findings 清单

| ID | 级别 | task 归属 | 位置/事实 | 描述与修复建议 |
|----|------|-----------|-----------|----------------|
| F-1 | **P1** | FIX-320 批（Developer 声明①口径）/ 根因存量（FIX-215 时代预算定标） | `tests/test_loop_runtime_claims.py` L1083；实测 §2#15 | 「commit 后自愈」仅对 verdict/identity 断言成立；性能断言 median<8.0s 实测 13.3~17.0s 超支 66%~113%，commit 后将由不可达转为持续红。修复：修正声明/EVD 措辞为「verdict/identity 自愈；性能断言待空闲环境复测定标」，并与遗留③（adapter 15s）同族登记性能预算重校准独立任务（0.82.0）。若空闲环境复测 median<8.0s，可在 R1 以数据降级为 P3 |
| F-2 | P2 | FIX-322 | `checks/dsh_boundary.py` 整串判定 rest 语义 | 版本后缀形态（`@scope/pkg@^1.2`，rest 以 `@` 开头）新语义下不触发，防过矫正守卫未锁此形态；真实盘点无此形态（0/0）。建议：设计注释显式声明该语义边界，或补一条守卫测试。可遗留至下一轮 |
| F-3 | P3 | FIX-322（声明） | §2#14 | 「37 处 @literal」未按两种口径复现（含 @ 52 / 包形 30）；实质等价（违规集全等）已独立证明，仅数字口径存疑，建议 EVD 注明盘点口径 |
| F-4 | P3 | FIX-320（声明） | §2#6 | 「8 测试」实为 7 方法/8 次执行（双模式 subTest）；建议 EVD 按方法数口径记录 |
| F-5 | P3 | FIX-320 | `core/manifest.json` artifacts 段 | 账本未获显式 artifact_role（allowlist/authority 均有）；由 `core/` 整目录声明覆盖、cleanup 实证 clean，无功能风险；可选改进为显式登记以对称 |
| F-6 | P3 讨论 | FIX-320 | `_apply_exemptions` | 同一五元组的多个 findings 理论上可被单条目重复豁免（条目不消耗）；现景观测不可达（同 locator 单单元），且逐条披露自足。仅记录 |

## 5. 五维度 + AI 专项 + 硬门槛

**五维度**：正确性 PASS（逻辑/边界/fail-closed 方向全实测）；安全性 PASS（无注入/敏感数据；`_safe_join` 防 symlink/reparse；防篡改三反相实证）；可维护性 PASS（注释记录设计意图/分叉/.fail-closed 理由，命名清晰，无重复）；性能 **WARN（F-1）**（本批扫描面增量 +1 文件 ≈75 units 影响微小；暴露存量预算超支）；测试覆盖 PASS（机制六面 + 实树集成 + 红绿双向 + 反相实证）。

**AI 专项 5 项**：mock 残留 无（patch 均带 addCleanup；产品代码零 mock）；硬编码返回值 无；幻觉 API 无（全部调用经运行验证）；未实现 TODO 无；过度实现 无（+412/−12 与声明范围一致，账本恰 4 条与裁决面一致）。

**硬门槛**：P0=0；5 维度 100% 覆盖；每条发现已标级；设计一致性 = 与 DEC-195 处置(b)/Coordinator 裁决豁免面 4 条一致、FIX-322 与 REVIEW-FEAT-030 F-07/N-2 闭环意图一致、oracle/产品分叉标注如实；AI 专项 5 项完成。

## 6. 遗留处置建议（交 Coordinator）

1. F-1：修正 FIX-320 批完成声明的自愈口径 + 空闲环境复测 perf 或登记预算重校准任务（可与 adapter 15s 合并一个独立小任务，0.82.0）。
2. F-2：FIX-322 语义边界注释/守卫（可随 R1 或下一批）。
3. F-3/F-4：EVD 口径注记。
4. ③ adapter 15s：登记独立小任务（未验证项，处置前需先复现）。
5. ④ INVENTORY_* 瞬态：既有防护维持，无需动作。

---
*审查证据全部来自本会话当场命令输出；反相/模拟均在 %TEMP% 执行，真实仓库仅读取。报告生成：R0，基线 a260637。*
