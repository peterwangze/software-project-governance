# Code Review: FIX-300 — Check 31 口径差修复（R0，commit 前置工作树审查）

- **Task ID**: FIX-300（R0）
- **Reviewer**: Code Reviewer Agent（只读审查）
- **审查对象**: 未提交工作树改动（`git diff HEAD`）——`skills/software-project-governance/infra/verify_workflow.py`（+26/−2，hunk 统计 29 行变更）+ `skills/software-project-governance/infra/tests/test_verify_workflow.py`（+131/−1）
- **审查日期**: 2026-09（R0 首轮）
- **绑定规范**: `agents/code-reviewer.md` + `skills/code-review/SKILL.md`（含 APPROVED_WITH_NOTES 需 `unresolved_blockers=0` 规则）
- **方法边界（采信声明）**: 只读审查——只读 git（diff HEAD/show/log/check-ignore/ls-files）+ 读文件/搜索；**未运行测试**（Developer 声称的 816 passed 按采信处理，辅以测试代码内容交叉印证，见 §7）；唯一产物 = 本报告。

---

## 0. 硬门槛裁决

| 门槛项 | 阈值 | 裁决 | 依据 |
|---|---|---|---|
| P0 阻塞问题数 | = 0 | **通过（0）** | 发现列表（§8）零 P0 |
| 5 维度全覆盖 | = 100% | **通过** | §4 逐一有结论 |
| 每条发现标注级别 | = 100% | **通过** | F-1(P2)/F-2(P3)/F-3(P3) |
| 设计一致性检查 | 已完成 | **通过** | §5：判定规则零改动、复用同一装配、修改面与 triage 声明一致 |
| AI 代码专项 5 项 | 全部完成 | **通过** | §6 逐一有结论 |
| 消费面实证义务（verdict_scope 兼容性 grep） | MUST | **已完成** | §6.6/§3-E5b：全仓 grep + 逐一消费者核对 |

---

## 1. 变更摘要（diff 复核）

`verify_workflow.py` 仅两个 hunk（git diff HEAD 核实）：

1. **`cmd_check_loop_runtime_claims` 输出装配**（verify_workflow.py L20711-20732）：
   - `payload = report.as_dict()` 后按分支追加 `verdict_scope`：默认 `"semantic_only"`（L20729）；`--fixture-identity` 时调用 `_run_identity_attestation_fixture_only()` 并追加 `identity_phase`/`identity_issues`/`identity_verdict` 三键 + `"semantic+identity_fixture"`（L20719-20723），且 `identity["verdict"] != "PASS"` → `payload["verdict"] = "FAIL"`（L20724-20725）。
   - 退出判定从 `report.verdict` 改为 `payload["verdict"]`（L20731）——默认路径下两者同源（`as_dict()` L346 `"verdict": self.verdict`），语义等价。
2. **argparse 注册**（verify_workflow.py L23946-23951）：`clrc_p.add_argument("--fixture-identity", action="store_true", ...)` → dest `fixture_identity`，与代码侧 `getattr(args, "fixture_identity", False)`（L20712）一致。

`tests/test_verify_workflow.py`：既有 adapter 测试断言更新（L110-114，精确 dict 相等改为子集断言）+ 新增 `FIX300DualCaliberAgreementTests` 类（L117-239，恰好 3 个测试方法）。

修改面声称（verify_workflow.py + tests；`checks/loop_runtime_claims.py` 不改）与 `git status --porcelain` 一致：仅 2 文件改动。

---

## 2. RCA 证据链抽查（E1-E5 逐一结论）

### E1 — worktree 复现（identity 源面缺失的确定性触发）
- **机制核实（通过）**：`.gitignore` L10 为 `.governance/`；`git check-ignore -v` 命中全部 5 个 host 源文件；`git ls-files .governance/` 计数 = **0**（全 git-untracked 属实）。⇒ 任何 git worktree / clean checkout / 非 governed cwd 下这 5 个文件必然缺失，identity 走 `REQUIRED_ROOT_UNAVAILABLE`。
- **commit 58f8e9f**：`git show` 核实存在（2026-09-09，"FIX-292 审查报告表格格式修复"，doc-only 1 文件）——作为复现基线 commit 合理。历史复现操作本身**未验证**（只读审查不可重放），按采信处理；机制面已由上列 ignore/untracked 事实独立成立。
- EVD-969 登记原文核实：`docs/requirements/architecture-audit-facts-0.80.0.md` L465 引述"独立运行 check-loop-runtime-claims = PASS 零 findings vs 引擎内 identity_verdict=FAIL——未定位，登记候选"——与 FIX-300 RCA 定位（口径差非实质矛盾）吻合。

### E2 — 裸 cwd 解析
- **通过（行号精确命中）**：`resolve_entry.py` L318-325——L319 `cwd = Path(os.getcwd())` 无任何 `.governance` 存在性探测的最终 fallback；`verify_workflow.py` L113-133 `_resolve_host_root()` → `resolve_host_root(None)` → 上述 cwd 路径（L116 注释明言 "explicit cwd -> os.getcwd()"）。`HOST_PROJECT_ROOT`（L133）确为裸 cwd 解析产物（除非显式 `--project-root`，L190-216）。

### E3 — attestation 裸路径 FAIL
- **通过（行号精确命中）**：`checks/loop_runtime_claim_attestation.py` L36-41 `HOST_PATHS`（4 文件）+ L218 `_plain_regular` 中 `raise IdentityAttestationError("REQUIRED_ROOT_UNAVAILABLE", relative)`——确以裸相对路径报错、无 host 根上下文。
- 5 文件源面核实：`HOST_PATHS`(4: plan-tracker/session-snapshot/evidence-log/risk-log) ∪ authority `source_records`(实测 JSON = decision-log/evidence-log/plan-tracker 3 条) = **并集恰 5 文件**；并集在 attestation L397-401 按 UTF-8 字节序排序迭代 ⇒ 缺失时第一个 FAIL 路径确定性地为 `.governance/decision-log.md`——与测试断言的报文一致。

### E4 — 豁免不对称（策略差各自正确）
- **通过（行号精确命中）**：semantic 侧双豁免——`checks/loop_runtime_claims.py` L2584-2587（host_root required paths：`root is None or not (root/".governance").is_dir()` → skip，注释标 FIX-240）+ L1244-1248（`_validate_source_records`：`.governance` 不存在 → 返回空，注释标 FIX-240 对齐）；identity 侧 `_plain_regular`/`attest_explicit_sources` 无任何 `.governance` 存在性豁免。不对称属实，且两侧均为显式设计（semantic 豁免有 FIX-240 注释锚点；identity fail-closed 是 attestation 完整性要求）——"策略差各自正确"结论成立。

### E5 — 独立命令默认 semantic-only + 顶层 PASS 未声明覆盖面（伪矛盾）
- **通过（行号精确命中）**：`verify_workflow.py` L20677-20700——`identity_options` 门控（`--require-identity` 或任一 identity 显式源参数才走 identity 分支并 early-return），默认 fall-through 到 L20702+ 纯 semantic 路径。引擎侧对照：check-governance Check 31（L16106 semantic + L16118 `_run_identity_attestation_fixture_only()` 直调）与 check-release（L20564-20565 经 `_loop_runtime_claim_gate_detail` L20515 同一 identity 调用）均为 semantic+identity 聚合。⇒ "独立 CLI PASS vs 引擎 FAIL" 的表象 = 覆盖面未声明的伪矛盾，RCA 定位正确。
- **E5b（修复对应面）**：`--fixture-identity` 分支调用的是 `_run_identity_attestation_fixture_only()`（L20719）——与引擎两处调用点（L16118/L20515）**同一函数**，非逻辑复制；该函数 L20476 在调用时读取模块级 `HOST_PROJECT_ROOT`（测试 patch 有效的前提，已核实）。

### "已排除方向"（checks/loop_runtime_claims.py 无需改）
- **通过**：判定/扫描规则零改动（§5）；口径差源于 adapter 层输出未声明 scope + 缺可比通道，修复落于 adapter 层（verify_workflow.py）是正确位置。triage 声明"3 文件面内用 2"与 git status 一致。

---

## 3. 修复正确性（审查重点 2）

1. **verdict_scope 语义**：默认 `"semantic_only"` 仅加性标注，不改变既有 verdict 计算与退出码（§1）。PENDING 降级（`_run_identity_attestation_fixture_only` L20454-20464/L20489-20494 可返回 PENDING）在 CLI 侧按 `!= "PASS"` → FAIL 聚合，与引擎 `_loop_runtime_claim_gate_detail` L20519（要求 `== "PASS"`）语义一致——降级不漏报。
2. **--fixture-identity 复用同一装配**：E5b 已核实——同一函数、同一 `PLUGIN_ROOT/":index"` + `HOST_PROJECT_ROOT` 输入面，非复制逻辑。identity≠PASS 聚合 FAIL 路径（L20724-20725）+ exit 1（L20731-20732）正确；semantic 已 FAIL 时不受 identity PASS 影响（仅在 verdict 非 PASS 时覆盖为 FAIL，不会把 FAIL 翻成 PASS）。
3. **argparse 注册**：dest 命名、`store_true`、防御式 `getattr(args, "fixture_identity", False)`（对 SimpleNamespace 旧调用者安全——被修改的 adapter 测试 L102-106 的 args 即不含该属性，默认分支正确命中）。
4. **消费面实证（硬门槛 MUST，已完成）**：
   - `verdict_scope` 全仓 grep：仅命中新代码 2 处 + 新测试 3 处——**零既有读者**。
   - CLI stdout 消费者全量枚举（grep `check-loop-runtime-claims` 全仓 24 处命中归类）：
     a. `core/manifest.json` L692/L703 validation_commands——命令串按退出码消费，不解析 stdout ⇒ 兼容；
     b. `tests/test_loop_runtime_claims.py` L412-434（FIX-215 gate runner）——`json.loads(stdout)` 后 `scanner_payload.get("semantic_verdict", scanner_payload.get("verdict", "UNKNOWN"))`，容错读取、加性键无影响 ⇒ 兼容（且该 runner 不传 `--fixture-identity`，输出面不变）；
     c. `tests/test_verify_workflow.py` adapter 测试——唯一曾经的全 dict 精确断言消费者，本次 diff 已同步更新为子集断言（L112-114）⇒ 兼容；
     d. 文档引用（ADR-012 L893-899、release-incident-recovery-0.66.2 L670-671）均属 `--require-identity` identity 分支——该分支输出（`canonical_attestation_json_bytes`，loop-claim-aggregate/v1 schema）本 diff 未触碰 ⇒ 兼容；
     e. 引擎 Check 31 / release gate——进程内调用，不消费 CLI stdout ⇒ 无关。
   - `as_dict()` 键面（loop_runtime_claims.py L343-367）无 `verdict_scope`/`identity_*` 键——4 个新键纯加性、零碰撞。
   - **结论：加性字段对全部已枚举消费者兼容，无破坏性。**

---

## 4. 五维度结论

| 维度 | 结论 | 依据 |
|---|---|---|
| 1 正确性 | **通过** | §3.1-3.2：分支/聚合/退出码逐行核实；边界（PENDING、semantic 先 FAIL、双旗标组合见 F-3）无逻辑错误 |
| 2 安全性 | **通过** | 无新增输入解析面；旗标为 `store_true` 布尔；attestation 对 git index 只读；临时目录 `tempfile.TemporaryDirectory` 自动清理（测试 L185/204/230）；无注入/敏感数据面 |
| 3 可维护性 | **通过（附 F-2/F-3 备注）** | 复用单一装配函数零重复；命名与引擎术语一致（identity_verdict/issues/phase）；注释解释 FIX-300 意图与 EVD-969 锚点；TOOLS.md TOOL-050 未同步新旗标（F-2，既有文档，非阻塞） |
| 4 性能 | **通过** | 默认路径仅增 1 次 dict 赋值；`--fixture-identity` 双倍开销仅在显式请求时发生（identity attestation 需 staged_index 快照构建，属 opt-in 语义可接受） |
| 5 测试覆盖 | **通过（附 F-1 备注）** | §6.1/§7：3 差分用例覆盖红/绿双形 + scope 双分支 + 形态锁定；cwd 漂移形态经排序确定性锁定为 decision-log 首报；测试精度备注见 F-1 |

---

## 5. 非目标遵守：判定规则零改动（审查重点 3）

**核实通过**：diff 仅含输出装配 hunk（L20711-20732）与 argparse hunk（L23946-23951）——`scan_loop_runtime_claims` 调用参数（L20702-20710）、`ClaimScanContext` 构造、判定/发现逻辑零触碰；`checks/loop_runtime_claims.py`、`checks/loop_runtime_claim_attestation.py`、allowlist/authority JSON 均无工作树改动（git status 仅 2 文件）。既有 `--require-identity` 分支（L20685-20700）输出与行为原样。

---

## 6. AI 专项 5 项 + 消费面

1. **mock 残留**：无新增。3 个新测试**零 scanner mock**（声称核实：新类 L117-239 无 `patch.object(vw, "scan_loop_runtime_claims")`/`_run_identity_attestation_fixture_only` 的 patch；仅 `HOST_PROJECT_ROOT` 重定向至 temp host = 环境隔离非判定 mock，及 `redirect_stdout` 输出捕获）。被修改的 adapter 测试保留其 scanner mock——FIX-197 既有 thin-adapter 覆盖模式，非本次引入。
2. **硬编码返回值**：无——payload 各值均来自真实 `report.as_dict()`/真实 identity 引擎返回；测试中的期望报文串是形态锁定断言（合理）。
3. **幻觉 API**：无——`_run_identity_attestation_fixture_only` 存在（L20425，签名/返回键与用法一致）；argparse dest 与 getattr 名一致；`_loop_runtime_claim_context` 存在（L20415）。
4. **未实现 TODO**：无——diff 内零 TODO/FIXME/占位。
5. **过度实现**：无——最小修改面（2 键域标注 + 1 旗标 + 聚合），无越界功能。
6. **消费面**：§3.4（硬门槛实证完毕）。

---

## 7. 测试质量与回归面（审查重点 4/5）

- **3 差分用例真实覆盖核实**：
  - `test_identity_host_source_drift_reproduces_divergence_shape`（L180-197）：真实引擎 identity FAIL + 报文形态锁定（decision-log 首报，由 attestation L397-401 排序确定性支撑）；
  - `test_fixture_identity_mode_agrees_with_engine_on_missing_sources`（L199-224）：红形——CLI 与引擎 sub-phase **同 verdict 同 issues 逐字相等断言**（L220-221）+ 顶层 FAIL + `SystemExit(1)`；
  - `test_fixture_identity_mode_agrees_with_engine_on_present_sources`（L226-239）：绿形——真实治理文件 5 份拷入 temp host（L157-160，`_INFRA_DIR.parents[2]` = 仓库根核实）→ 双口径 PASS。
  - scope 断言：`semantic_only`（L114）/`semantic+identity_fixture`（L219/L237）双分支均锁定。
  - "零 mock"声称：见 §6.1——属实（新测试）。
- **816 passed（813+3 恰加 3）**：**采信**（未运行）。交叉印证：新增恰 3 个测试方法、零删除/重命名；被修改断言与新输出代码一致；全仓无其他依赖旧精确键集的语义 CLI payload 断言（grep `{"verdict"` 归类核实，其余命中均属其他命令的 payload schema）；adapter subprocess 测试（L44-56）走真实 CLI 且仓库根 `.governance` 存在——与"仓库根 PASS"实录声称一致。
- **"两口径双场景实录一致"**：与 test 2/test 3 断言结构一一对应（采信 + 静态印证）。
- **"健康 26 前后恒等零新增"**：diff 不触碰 manifest.json/任何健康检查清单（git status 仅 2 文件）⇒ 结构性恒等成立；"EVD-969 时代 Check 31 ×1 已自然消失"的历史陈述**采信**（与 EVD-969 登记文档 L465 相符，未重放）。

---

## 8. 发现列表（P0~P3，全部非阻塞）

| ID | 级别 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| F-1 | **P2** | `tests/test_verify_workflow.py` L195-197（对照 docstring L181-184） | test 1 的 semantic PASS 断言在 `HOST_PROJECT_ROOT` drift patch **之外**执行（patch 域 L187-188 仅包住 `_engine_identity()`），故 semantic PASS 实际验证的是真实 governed 根而非漂移 host；docstring"with the host sources unreachable … semantic caliber PASSes"的双腿同条件声称未被该断言直接覆盖（漂移下 semantic PASS 目前仅由 FIX-240 豁免代码路径 L1244-1248/L2584-2587 静态成立） | 将 L195-197 移入 patch 域内，或在 test 2 断言 `payload["findings"] == []` 以直接锁定"漂移下 semantic 仍 PASS"的分歧形态 |
| F-2 | **P3** | `infra/TOOLS.md` L541-550（TOOL-050） | TOOL-050 子命令文档未收录 `--fixture-identity` 旗标与 `verdict_scope` 输出（其"四个热治理文件"措辞与 identity 实际 5 文件并集面亦有既有出入——非本 diff 引入） | 后续文档任务补一行旗标说明 |
| F-3 | **P3** | `verify_workflow.py` L20685-20700 vs L20712 | `--fixture-identity` 与 `--require-identity`/任一 identity 显式源参数组合时被静默忽略（identity 分支 early-return，不达 fixture_identity 判定点）——行为合理（identity 分支本就运行更强形态）但 help 文本未注明 | 在 argparse help 或 TOOLS.md 注明"仅在默认 semantic 路径生效" |

---

## 9. 终态结论

- **结论：`APPROVED_WITH_NOTES`**
- **unresolved_blockers = 0**（P0 = 0，P1 = 0；F-1/F-2/F-3 为 P2/P3 非阻塞备注，不构成 BLOCKING finding）
- 硬门槛全部通过（§0）；RCA E1-E5 抽查全部成立（E1 历史复现操作按采信处理、机制面已独立核实）；修复正确性、非目标遵守、消费面兼容性均实证通过。
- F-1 建议在后续测试任务中采纳（提升差分形态锁定精度），不阻塞本次交付。
