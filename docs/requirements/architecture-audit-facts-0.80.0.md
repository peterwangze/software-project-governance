# 架构与实现事实基线盘点（0.80.0 重构线输入）— AUDIT-150 Phase 1

> **文档性质**：只读度量事实基线。全文档只登记"现状事实 + 可复现依据"，**不含任何重构建议、方案推荐或优劣评判**（Phase 2 架构顾问咨询 / Phase 3 Architect 演进设计职责）。
> **度量时点**：2026-09-09，本会话现场实测（工作区 HEAD，0.78.1 发布后未发布窗口）。
> **度量环境**：Windows / pwsh / Python（经 `python -B` 禁写字节码缓存）；LOC 计数统一采用 `[System.IO.File]::ReadAllLines($p, UTF8).Count`（精确物理行数）。
> **维度框架**：架构质量 7 维 + 非功能 4 维取自 `skills/tech-review/SKILL.md` 第二步/第三步（本阶段仅作事实组织框架，不作评审判定）。
> **任务依据**：AUDIT-150 Phase 1/4；用户 2026-09-09 指令（架构腐化系统性梳理与重构规划）。

---

## 1. 方法与命令清单（可复现性）

本报告全部现场度量使用的命令原文。除标注"采信治理记录"外，所有数字为本会话实测输出。

### 1.1 度量方法校准（关键前提）

PowerShell `Measure-Object -Line` **跳过空行**（只计非空行）。校准实验（本会话）：

```powershell
$p = 'skills/software-project-governance/infra/verify_workflow.py'
$lines = [System.IO.File]::ReadAllLines((Resolve-Path $p), [System.Text.Encoding]::UTF8)
$lines.Count                          # → 24252（精确物理行数）
(Get-Content $p | Measure-Object -Line).Lines   # → 21886（= 非空行数）
```

**本报告全部 LOC 采用 ReadAllLines 精确计数。** 与 AUDIT-124（2026-06-27，EVD-630"20321 行"）及 RISK-039 行（"20,294 行/439 def/54 子命令"）的历史数字为同时代口径（`git show` + 换行分割），可比。

### 1.2 命令复现包

```powershell
# [目录级 LOC] 精确行数（排除 __pycache__/.pytest_cache/node_modules）
$files = Get-ChildItem <dir> -Recurse -File | Where-Object { $_.FullName -notmatch '__pycache__|\.pytest_cache|node_modules' }
$total = 0; foreach ($f in $files) { $total += [System.IO.File]::ReadAllLines($f.FullName, [System.Text.Encoding]::UTF8).Count }; $total

# [Top-20 文件]（排除 .git）
Get-ChildItem . -Recurse -File -Include *.py,*.md,*.js,*.ts,*.json,*.sh,*.cmd,*.yml,*.yaml,*.html,*.css |
  Where-Object { $_.FullName -notmatch '__pycache__|\.pytest_cache|node_modules|\.git\\' } |
  ForEach-Object { [PSCustomObject]@{LOC=[System.IO.File]::ReadAllLines($_.FullName,[System.Text.Encoding]::UTF8).Count; Path=$_} } |
  Sort-Object LOC -Descending | Select-Object -First 20

# [def / cmd_* 计数]
$lines = [System.IO.File]::ReadAllLines('<verify_workflow.py>', [System.Text.Encoding]::UTF8)
($lines | Select-String '^def\s+(\w+)').Count        # def 总数
($lines | Select-String '^def\s+cmd_\w+').Count      # cmd_* 总数（含行号清单见 §3.2）

# [Check 编号段]
($lines | Select-String '┌─ (Check [^:]+):').Count  # → 70（清单见 §3.3）

# [print 编排面]
($lines | Select-String '^\s*print\(').Count         # → 1315
($lines | Select-String '[┌└├│─]{2,}').Count          # → 343（box-drawing 行）

# [数据表块范围]（起止行 = 定义行到下一个非缩进非空行前一行）
# 单表：定位 '^<NAME>\s*=' 后向下扫描至 '^\S'
# 全量大写字面量块：正则 '^([A-Z][A-Z0-9_]{3,})\s*=\s*[\[\{\("''r]' → 192 块 / 2048 行

# [git tag 时点行数]
git show <tag>:skills/software-project-governance/infra/verify_workflow.py
#   输出 join 后按 "`n" split 计数

# [e2e fixture 对照] fixture 相对路径 ↔ 主树同名文件行数比较（脚本见 §5.3 输出）

# [测试计数]
$testFiles = @(Get-ChildItem skills/software-project-governance/infra/tests -Recurse -File -Filter *.py) + @(Get-ChildItem tests -Recurse -File -Filter *.py)
($testFiles | ForEach-Object { @(Select-String -Path $_.FullName -Pattern '^\s*def test_' -Encoding UTF8).Count } | Measure-Object -Sum).Sum   # → 2201

# [治理数据体积]（只读命令，python -B 禁写缓存）
python -B skills/software-project-governance/infra/archive.py migrate --auto --dry-run
python -B skills/software-project-governance/infra/verify_workflow.py check-governance-data-size
python -B skills/software-project-governance/infra/verify_workflow.py status   # 墙钟计时

# [git 只读] git tag --sort=creatordate / git rev-parse -q --verify refs/tags/<tag>
```

**本阶段未运行**：pytest / unittest 全量测试套件（任务硬门槛禁止）——测试结果一律采信治理记录并标注时点（§7.2）。

---

## 2. 仓库地形

### 2.1 目录级 LOC 表（现场实测，ReadAllLines 精确行数）

说明：仓库根无 `infra/` 顶层目录——本仓库即插件开发仓，`<plugin_home>` = `skills/software-project-governance`（AGENTS.md「方法 B」）；任务所指 `infra/`、`core/`、`references/` 均在该 skill 目录下。`skills/` 一级拆分见 §2.2 注。

| 目录（仓库相对路径） | 文件数 | 总 LOC | 其中 .py LOC |
|---|---|---|---|
| skills/software-project-governance/infra | 102 | 106,809 | 104,299 |
| ├─ infra/checks | 17 | 12,856 | 12,856 |
| ├─ infra/tests | 48 | 47,934 | 47,781 |
| ├─ infra/release | 10 | 3,473 | 3,275 |
| └─ infra/hooks | 4 | 1,276 | 0 |
| skills/software-project-governance/core | 68 | 7,379 | 0 |
| skills/software-project-governance/references | 12 | 2,933 | 0 |
| skills/（全部 26 个 skill 目录合计） | 208 | 105,822 | 92,263* |
| agents | 15 | 1,450 | 0 |
| commands | 9 | 2,354 | 0 |
| adapters（6 平台子目录） | 30 | 2,635 | 1,030 |
| web | 17 | 4,169 | 363 |
| project（含 e2e fixture） | 126 | 44,973 | 26,016 |
| ├─ project/e2e-test-project | 106 | 39,762 | 26,016 |
| docs | 336 | 38,482 | 0 |
| tests（仓库根） | 1 | 107 | 107 |
| presets | 2 | 294 | 0 |
| .github | 1 | 25 | 0 |
| .governance（治理数据，见 §6） | 845 | 158,830 | 467 |

\* 早期一次 `Measure-Object -Line` 口径的中间值；skills 合计与 infra 精确值之间差异 = 度量方法切换（§1.1），以 infra 行精确值为准。

**skills/ 一级分布**：`software-project-governance` 1 个目录 183 文件 / 103,496 行（精确口径 105,822 含空行修正差异，取 ReadAllLines 口径）；其余 25 个 skill 各 1 文件（SKILL.md），LOC 49~146 不等（实测命令：`Get-ChildItem skills -Directory` 逐目录 ReadAllLines 求和）。

### 2.2 Top-20 文件 LOC 排名（全仓，排除 .git/__pycache__/node_modules）

| # | LOC | 文件 |
|---|---|---|
| 1 | 24,252 | skills/software-project-governance/infra/verify_workflow.py |
| 2 | 18,255 | skills/software-project-governance/infra/tests/test_verify_workflow.py |
| 3 | 14,166 | project/e2e-test-project/skills/software-project-governance/infra/verify_workflow.py（e2e 投影，见 §5.3） |
| 4 | 6,678 | project/e2e-test-project/.../infra/tests/test_verify_workflow.py（e2e 投影） |
| 5 | 3,788 | skills/software-project-governance/infra/tests/test_archive.py |
| 6 | 3,148 | skills/software-project-governance/infra/checks/loop_runtime_claims.py |
| 7 | 3,087 | skills/software-project-governance/infra/checks/review_domain.py |
| 8 | 2,971 | skills/software-project-governance/infra/archive.py |
| 9 | 2,674 | project/CHANGELOG.md |
| 10 | 2,441 | skills/software-project-governance/core/lifecycle-registry.json |
| 11 | 2,117 | skills/software-project-governance/infra/release/verify_rel063_evidence.py |
| 12 | 2,064 | project/e2e-test-project/.../infra/tests/test_archive.py（e2e 投影） |
| 13 | 1,835 | .governance/evidence-log.md |
| 14 | 1,677 | web/package-lock.json |
| 15 | 1,671 | project/e2e-test-project/.../infra/archive.py（e2e 投影） |
| 16 | 1,669 | skills/software-project-governance/infra/task_priority.py |
| 17 | 1,651 | skills/software-project-governance/infra/tests/test_loop_runtime_claims.py |
| 18 | 1,646 | skills/software-project-governance/infra/tests/test_task_priority.py |
| 19 | 1,528 | skills/software-project-governance/infra/tests/test_verify_rel063_evidence.py |
| 20 | 1,391 | skills/software-project-governance/infra/loop_paro_engine.py |

（依据：§1.2 Top-20 命令本会话输出原文。）

**非功能-可维护性维度事实（只登记不评判）**：LOC > 2000 的生产代码文件（非测试、非投影、非数据 JSON）= verify_workflow.py（24,252）、checks/loop_runtime_claims.py（3,148）、checks/review_domain.py（3,087）、archive.py（2,971）、release/verify_rel063_evidence.py（2,117）。对照 `core/architecture-health.json` `module_size.warn_lines=2000 / error_lines=5000 / target_lines=1500`，测试文件豁免（`**/tests/**`、`**/test_*.py`，同文件 exclusions 字段）。

---

## 3. 巨石模块剖面（verify_workflow.py）

### 3.1 总量

| 指标 | 本次实测（2026-09-09 HEAD） | 历史锚点（时点+出处） |
|---|---|---|
| 精确 LOC | **24,252**（ReadAllLines） | 24,137（任务书 traceback 实见，2026-09-09 会话）✓ 同量级吻合；22,949（v0.78.1 tag，§4.3）；20,321（2026-06-27，EVD-630）；20,294（2026-06-24，DEC-083 F1/RISK-039） |
| 非空行 | 21,886 | — |
| `def ` 函数总数（top-level） | **504** | 439（2026-06-24，DEC-083 F1）；438（2026-06-27，EVD-630） |
| `cmd_*` 函数 | **74**（全清单含行号，§3.2） | "54 子命令"（2026-06-24/27，DEC-083/EVD-630）；"54 个命令"（DEC-082，2026-06-24） |
| argparse 主表子命令注册 | 25（`add_parser(` 计数，L23385-L24050） | — |
| dispatch 命令字典键 | **80 个命令名 → 77 个唯一 cmd 函数**（L24164-L24245；3 个别名组：dynamic-lifecycle-migration=dynamic-flow-gate-migration；check-deterministic-scaffolds=check-scaffold-templates；check-interruption-policy=check-user-interruption-policy） | — |
| Check 编号段（print 头 `┌─ Check N:` 实测） | **70 段**（含子相位 18b~18i、28b~28u、30c 等 + 汇总 Check N；全清单 §3.3） | 53 段（2026-06-27，EVD-630/632） |
| `print(` 调用 | **1,315** | 437 行 print 在 cmd_check_governance 1126 行内（2026-06-27，EVD-630，指该函数而非全文件） |
| box-drawing（┌└├│─）行 | 343 | — |
| 大写字面量数据块 | **192 块 / 2,048 行**（正则 `^([A-Z][A-Z0-9_]{3,})\s*=\s*[\[\{\("r]`，块范围=定义行至下一 top-level 语句前） | "133 个 ~1,948 行"（2026-06-27，EVD-630） |

### 3.2 cmd_* 全清单（74 个，行号实测）

L10335 cmd_verify；L10937 cmd_status；L11130 cmd_governance_context；L11168 cmd_capability_context；L11224 cmd_first_run_demo；L11245 cmd_gate；L11293 cmd_stage；L11348 cmd_stages；L11376 cmd_gates；L13961 cmd_execution_packet；L14627 cmd_check_governance；L17157 cmd_gate_check；L17886 cmd_check_agent_locks；L17910 cmd_check_archive_integrity；L17940 cmd_check_plugin_freshness；L18996 cmd_agent_runtime_e2e；L19048 cmd_gemini_auth_preflight；L19076 cmd_opencode_provider_preflight；L20273 cmd_external_project_validation；L20314 cmd_e2e_check；L20408 cmd_check_agent_adapters；L20531 cmd_check_release；L20609 cmd_check_cross_references；L20651 cmd_check_loop_role_skills；L20664 cmd_check_loop_runtime_claims；L20854 cmd_check_sequential_ids；L20902 cmd_check_structural_validity；L20924 cmd_check_commit_scope；L20952 cmd_check_goal_alignment；L20991 cmd_check_user_impact；L21032 cmd_check_agent_team；L21085 cmd_check_version_consistency；L21118 cmd_check_projection_sync；L21147 cmd_check_injection_contract；L21169 cmd_check_dsh_skills_manifest；L21191 cmd_check_dsh_preset_smoke；L21215 cmd_release_ledger；L21229 cmd_release_projection；L21242 cmd_quality_tools；L21250 cmd_check_hot_fact_source；L21271 cmd_check_runtime_readiness_matrix；L21292 cmd_check_first_session_measurement；L21313 cmd_check_governance_packs；L21338 cmd_check_lifecycle_registry；L21365 cmd_check_flow_unit_runtime；L21400 cmd_dynamic_lifecycle_migration；L21435 cmd_loop_engineering_migration；L21475 cmd_check_host_capability_context；L21515 cmd_check_official_submission_ecosystem；L21536 cmd_check_mainstream_agent_loading；L21583 cmd_check_architecture_health；L21606 cmd_check_loop_health；L21698 cmd_loop_rollup；L21708 cmd_loop_telemetry；L21975 cmd_task_priority_analysis；L22029 cmd_review_record；L22057 cmd_next_candidates；L22498 cmd_change_triage；L22586 cmd_governance_write_guard；L22647 cmd_check_duplicate_code；L22669 cmd_check_technical_debt；L22692 cmd_check_complexity；L22717 cmd_check_governance_data_size；L22746 cmd_check_readme_pack_guidance；L22767 cmd_check_governance_pack_status；L22788 cmd_check_product_success_contracts；L22815 cmd_check_acceptance_contracts；L22842 cmd_check_quality_budget；L22869 cmd_check_vertical_slices；L22896 cmd_check_deterministic_scaffolds；L22923 cmd_check_interruption_policy；L22957 cmd_generate_deterministic_scaffold；L23043 cmd_web_console；L23303 cmd_resolve_entry。

（依据：`Select-String '^def\s+cmd_\w+'` 本会话输出。dispatch 注册表 L24164-L24245 共 80 键。）

### 3.3 Check 编号段全清单（70 段，print 头行号实测）

Check 1~40 主干（含嵌套子相位）+ 汇总段，行号：1(L14774) 2(L14797) 3(L14817) 4(L14843) 5(L14871) 6(L14910) 7(L14950) 8(L14974) 9(L14988) 10(L15008) 11(L15050) 12(L15079) 13(L15119) 14(L15125) 15(L15155) 16(L15179) 17(L15213) 18(L15244) 18b(L15264) 18c(L15285) 18d(L15307) 18e(L15329) 18f(L15351) 18g(L15373) 18h(L15395) 18i(L15413) 19(L15438) 20(L15459) 21(L15476) 22(L15501) 23(L15519) 24(L15537) 25(L15557) 26(L15602) 27(L15625) 28(L15648) 28b(L15667) 28c(L15687) 28d(L15707) 28e(L15724) 28f(L15741) 28g(L15757) 28h(L15772) 28i(L15789) 28j(L15805) 28k(L15820) 28l(L15836) 28m(L15851) 28n(L15868) 28o(L15887) 28p(L15912) 28q(L15930) 28r(L15948) 28s(L15966) 28t(L15990) 29(L16019) 30(L16039) 30c(L16062) 31(L16105) 32(L16136) 33(L16159) 34(L16178) 35(L16209) 36(L16245) 37(L16284) 38(L16327) 39(L16362) 40(L16389) 28u(L16411) N(L16464 汇总)。

与 AUDIT-124 时点（53 段）的差异构成：28u/30c/31~40 为其后新增编号（0.66.0~0.79.0 期间）。**历史对照原文**（EVD-632，2026-06-27）："53 段 Check 编录……原型 A 12 段 + B 5 段 + D 4 段可压缩；原型 C 4 段 + 原型 Z 28 段是独特逻辑无法泛化"（32 段独特）。

check 域业务函数（非 cmd_ 前缀）共 96 个（`def check\w*\(` 清单实测，L1239 check_files 起 ~ L19835 check_governance_data_size 止；含 `_check_*` 内部族 31 个）。

### 3.4 内嵌数据表盘点（块起止行与行数实测）

块范围定义：赋值行 → 下一个 top-level 非空非缩进行之前。

**任务点名表**：

| 表名 | 定义块（行） | 行数 | AUDIT-124 时点行数（EVD-630） |
|---|---|---|---|
| REQUIRED_FILES | L393-L452 | 60 | 61 |
| OPTIONAL_PROJECTION_FILES | L455-L483 | 29 | — |
| PROJECTION_SNIPPETS | L486-L618 | 133 | 106 |
| WORKFLOW_SNIPPETS | L624-L704 | 81 | 82 |
| REQUIRED_SNIPPETS | L707（`={}` 占位）+ **L711-L1035 实体** | 1 + **325** | 326 |
| ADAPTER_CLAIM_REGISTRY | L19721-L19733 | 13 | —（0.79.0 前不存在，FEAT-014 引入） |
| LOOP_ROLE_SKILL_CONTRACTS | L1286-L1314 | 29 | — |
| LOOP_ROLE_SHARED_SEMANTIC_TOKENS | L1317-L1335 | 19 | — |
| ACTIVE_AGENT_ROLES / NAMED_REVIEWER_ROLES | L1449-L1463 / L1466-L1472 | 15 / 7 | — |
| ADAPTER_REQUIRED_KEYS | L1501-L1515 | 15 | — |
| MAINSTREAM_AGENT_LOADING_ADAPTERS | L2184-L2272 | 89 | — |
| MAINSTREAM_AGENT_LOADING_README_TOKENS 等 5 表（TOKENS/BOUNDARY/CLAIM_TERMS/OVERCLAIMS 族） | L2274-L2341 | 6+8+6+8+36=64 | — |
| DYNAMIC_LIFECYCLE_MIGRATION_BOUNDARY_TOKENS / _FORBIDDEN_OVERCLAIMS | L2351-L2359 / L2361-L2374 | 9 / 14 | — |
| LIFECYCLE_REGISTRY_STAGE_IDS / _BOUNDARY_TOKENS / _FORBIDDEN_OVERCLAIMS | L2377-L2388 / L2445-L2454 / L2456-L2480 | 12 / 10 / 25 | — |
| GATE_EXECUTION_REGISTRY_REQUIRED_FIELDS / ALLOWED_FUNCTIONS | L2489-L2497 / L2525-L2539 | 9 / 15 | — |
| GOVERNANCE_PACK_KNOWN_CHECKS | L2561-L2607 | 47 | — |
| GOVERNANCE_PACK_STATUS_REQUIRED_TOKENS / _FORBIDDEN_OVERCLAIMS | L2615-L2625 / L2652-L2673 | 11 / 22 | — |
| GOVERNANCE_PACK_BOUNDARY_TOKENS / _FORBIDDEN_OVERCLAIMS | L2889-L2893 / L2895-L2904 | 5 / 10 | — |
| OFFICIAL_SUBMISSION_REQUIRED_TOKENS / _FORBIDDEN_OVERCLAIMS | L2822-L2845 / L2847-L2874 | 24 / 28 | — |
| README_PACK_GUIDANCE_REQUIRED_TOKENS | L2906-L2927 | 22 | — |
| ADAPTER_RUNTIME_CAPABILITY_POLICY | L5207-L5255 | 49 | — |
| GEMINI_AUTH_REMEDIATION / OPENCODE_PROVIDER_MODEL_REMEDIATION | L5424-L5429 / L5605-L5609 | 6 / 5 | — |
| PROJECTION_SYNC_PATTERNS | L6571-L6582 | 12 | — |
| INJECTION_CONTRACT_ANCHORS | L6604-L6632 | 29 | — |
| EXTERNAL_PROJECT_VALIDATION_COMMANDS / NATIVE_ENTRY_FILES | L19110-L19114 / L19124-L19130 | 5 / 7 | — |
| HOST_CAPABILITY_CONTEXT_SCENARIOS（+REQUIRED_* 两表） | L2739-L2747（L2749-L2757 / L2695-L2706） | 9（9/12） | — |

**总量**：全文件大写字面量赋值块 **192 块 / 2,048 行**（§3.1 命令实测）。与 EVD-630"硬编码数据表 133 个 ~1,948 行，其中 REQUIRED_FILES 与 manifest.json 300 条目重复（fallback 副本）"并列：**块数 +59、行数 +100**（2026-06-27 → 2026-09-09）。另有 ~40 个 `re.compile` 正则赋值（FIX_105_*、SECRET_*、FACT_BASIS_RE 等，L1858-L19721 散布，不含入 192 计数口径的部分以字符串/元组开头者已计入）。

### 3.5 print 编排重复面抽样证据（≥3 处并排）

**样本 A — Check 10 块（L15008-L15021）**：
```python
print("\n┌─ Check 10: M5 AskUserQuestion Compliance ────────────┐")
m5_result = check_m5_compliance_with_record_scope()
m5_issues = m5_result["issues"]
if m5_issues:
    blocking = [i for i in m5_issues if i["severity"] == "BLOCKING"]
    ...
    print(f"│  [BLOCKING] {len(blocking)} M5 anti-pattern(s) — ...")
    for b in blocking:
        print(f"│    - {b['file']}:{b['line']}: {b['text'][:80]}")
```

**样本 B — Check 18h 块（L15395-L15406）**：
```python
print("\n┌─ Check 18h: Weak-LLM Deterministic Scaffolds (FIX-092) ┐")
scaffold_result = check_deterministic_scaffolds()
scaffold_issues = len(scaffold_result["issues"])
print(f"│  Required scaffold type(s): {len(scaffold_result['required_types'])}")
for issue in scaffold_result["issues"]:
    print(f"│  [FAIL] {issue}")
...
    print(f"│  [PASS] {entry['scaffold_type']}: deterministic scaffold ready")
```

**样本 C — Check 28p 块（L15912-L15923）**：
```python
print("\n┌─ Check 28p: Duplicate Code (ArchGuard/REQ-101) ─────┐")
dup = check_duplicate_code()
if dup.get("error"):
    print(f"│  [SKIP] {dup['error']}")
else:
    ...
    for f in dup["findings"][:8]:
        print(f"│    [{f['severity']}] {f['check']}: ...")
```

三段共享结构：`print("┌─ 标题") → 调 check 函数 → issues 遍历 → │  [FAIL]/[PASS] 行打印`。**编排函数体积**：`_run_full_engine_checks` L14764-L16458（约 1,695 行）承载 70 段 Check 的逐段编排。历史对照（EVD-630，2026-06-27）：cmd_check_governance 1,126 行中 437 行 print（38.8%）、11+ 段逐字相同模板仅替换 4 变量、4 个 31 行 contracts 包装器复制粘贴。

---

## 4. 域模块抽取现状与"拆而未缩"实证

### 4.1 infra 顶层域模块 LOC + 对应测试 + 耦合面

（LOC 实测；"被 import 符号数" = verify_workflow.py `from checks.X import (...)` 块内符号计数实测，release.* 为单行 import 手工核对）

| 模块 | LOC | verify_workflow.py import 的符号数 | 对应测试文件（infra/tests/，LOC） |
|---|---|---|---|
| checks/review_domain.py | 3,087 | **59**（最大耦合面） | test_review_closure_legacy.py(882) / test_review_machine_provenance.py(598) 等 |
| checks/loop_runtime_claims.py | 3,148 | 3（ClaimScanContext/materialize_*/scan_*） | test_loop_runtime_claims.py(1,651) |
| checks/loop_runtime_claim_attestation.py | 1,200† | 7 | test_loop_runtime_claim_attestation.py(805) |
| checks/manifest.py | 517 | 12 | test_verify_workflow.py 内 manifest 用例族 |
| checks/capability_registry.py | 304 | 10 | 同上 |
| checks/evidence_domain.py | 402 | 12 | 同上 |
| checks/risk_domain.py | 543 | 8（含 `_resolve_shared` 延迟刷新注释） | test_risk_mitigation_closure.py(395) |
| checks/snapshot_domain.py | 439 | 1 | test_snapshot_freshness.py(598) |
| checks/gate_domain.py | 661 | 2 | test_gate_sequence_for_release.py(778) |
| checks/ci_domain.py | 492 | 1 | test_ci_evidence.py(537) |
| checks/triage_domain.py | 587 | 2 | test_change_triage.py(1,084) |
| checks/flow_unit_runtime.py / _v2.py | 361 / 709 | 6（仅 v1） | test_flow_unit_runtime_v2.py(529) |
| checks/commit.py / projection.py / version.py | 56 / 89 / 138 | 模块别名 import（3 个） | — |
| release/context / ledger / projection / quality | — | 1 / 1 / 2 / 1（单行） | test_release_ledger.py(911) |
| archive.py | 2,971 | 不被 verify import（反向：Check 27 委托 archive_module.verify_archive_integrity，EVD-666） | test_archive.py(3,788) |
| task_priority.py | 1,669 | 不被 import（独立 CLI） | test_task_priority.py(1,646) |
| change_triage.py | 905 | 不被 import（独立 CLI） | test_change_triage.py(1,084) |
| review_record.py | 451 | 不被 import（独立 CLI） | test_review_record.py(401) |
| loop_migration.py | 1,300 | 不被 import | test_loop_migration.py(851) |
| loop_engine.py / loop_gate_processor.py / loop_paro_engine.py / loop_event_log.py / loop_telemetry.py / loop_health.py / loop_migration_plan.py / loop_admission.py / loop_exit_bridge.py / flow_unit_derive.py | 670 / 1,112 / 1,391 / 833 / 851 / 593 / 958 / 413 / 235 / 757 | 不被 import | 对应 test_loop_*.py（375~1,066） |
| cleanup.py / resolve_entry.py | 665 / 360 | 不被 import | test_cleanup.py(88) / test_resolve_entry.py(407) |

† loop_runtime_claim_attestation.py 早期非精确口径列 1,315 行；ReadAllLines 实测 1,200 行（以本次为准）。

**耦合方向事实**（import 块 L36-L67、L1048-L1237 实测）：verify_workflow.py 从 **19 个内部模块** import（checks×15 + release×4）；checks 子模块反向通过**延迟 `_vw()` accessor 访问 verify_workflow 的共享全局**（import 块注释原文："Shared helpers/constants stay here and are reached by the new module via its deferred `_vw()` accessor (same pattern as manifest/capability_registry)"，L1083-L1087）。无第三方 import（§9.4）。

**架构质量维度-循环依赖现状事实**：代码面为单向分层（verify_workflow → checks/release；checks → 延迟 _vw() 回访）；治理数据面存在已知容忍环 `AUDIT-146 → FEAT-010 → AUDIT-146`（task-priority-analysis 输出 "CYCLE DETECTED (WARNING)"，FIX-237.2 cycle tolerance；.governance/change-triage/*.json report_text 字段多处实证，如 FEAT-014.json L706）。

### 4.2 域拆分交付史（治理记录锚点）

- **0.59/0.60（Phase 1/2）**：manifest/capability-registry 域拆出，"已交付 -616 行"（DEC-088 背景⑤ / EVD-969 历史引用；DEC-088 原文："0.59/0.60 是位置搬运"——主文件保留薄 re-export）。
- **0.61（Phase 3 计划）**：DEC-088 策略转向数据驱动重构 → 用户叫停（"你这逻辑都每理顺"，2026-06-27）→ DEC-145 间接闭合三件套（FIX-155/156/REL-047），"重启=新任务新版本号"。
- **0.70.0（Phase 5a/5b/5c）**：evidence/risk/review 域抽出（import 块注释 L1091/L1111/L1160："extracted to infra/checks/*_domain.py in 0.70.0"）。
- **0.73.0**：triage_domain（L1230 注释："checks/triage_domain.py in 0.73.0"）。
- **0.76.0**：snapshot/gate/ci 域（L1124/L1136/L1148 注释："new in 0.76.0"）。

### 4.3 verify_workflow.py 行数 git tag 曲线（实测）

命令：`git show <tag>:skills/software-project-governance/infra/verify_workflow.py`（join 后按换行 split 计数）。

| 时点 | 行数 | 相邻差 | 事件对照（治理记录） |
|---|---|---|---|
| v0.58.0 | 20,937 | — | DEC-083 F1 记录"20,294 行"为 AUDIT-121 基线（commit 5831cbf，早于 tag） |
| v0.60.0 | 20,321 | **-616** | 0.59/0.60 域拆分 Phase 1/2（EVD-969"-616 行"精确吻合） |
| v0.61.0 | 20,404 | +83 | DEC-088 转向后 FIX-155a 死代码 -25（EVD-631）；REL-048 治理数据修复批 |
| v0.65.0 | 21,814 | +1,410 | 0.62~0.65（loop-engineering 需求/预检 + FEAT-001 release 投影 generator 接线） |
| v0.70.0 | 20,183 | **-1,631** | 0.70.0 域拆分 Phase 5a/5b/5c（evidence/risk/review 域外迁）+ 0.66~0.69 loop 模块外移（DEC-099："新逻辑写入独立模块 infra/loop_*.py，不碰 God Module"） |
| v0.78.1 | 22,949 | +2,766 | 0.71~0.78.1（FIX-270 status/宿主提速、FIX-278 降噪、FEAT-010~016 dsh 面等） |
| **HEAD（2026-09-09）** | **24,252** | **+1,303** | 0.78.1 后未发布窗口（AUDIT-147~149 / FIX-281~297 / FEAT-011~016 波次） |

**曲线形态（事实描述）**：锯齿形——两次拆分窗口（v0.58→v0.60 -616；v0.65→v0.70 -1,631）后均被更大斜率增长覆盖（+1,410 / +2,766 / +1,303）。v0.70.0 至 HEAD 净增 4,069 行，超历史峰值（v0.65.0 的 21,814）11.3%。

---

## 5. 重复与投影面

### 5.1 平台投影机制（manifest + version-projections.json 实测）

- **canonical manifest**：`skills/software-project-governance/core/manifest.json`（831 行，version 0.78.1，`source_of_truth: true`）。
- **投影注册表**：`core/version-projections.json`（schema_version 1，authority = `skills/software-project-governance/SKILL.md` frontmatter version）。
- **投影清单实测：15 个投影条目**（0.78.1 生效中）：
  1. [byte_copy] SKILL.md → project/e2e-test-project/skills/software-project-governance/SKILL.md
  2-8. [structured_json ×7] core/manifest.json、.claude-plugin/plugin.json、.claude-plugin/marketplace.json、.codex-plugin/plugin.json、.zcode-plugin/plugin.json、.chrys-plugin/plugin.json、package.json（JSON pointer 注入 version）
  9. [transformed_text] project/e2e-test-project/.governance/plan-tracker.md
  10-13. [transformed_text ×4] infra/hooks/{pre-commit,commit-msg,post-commit,prepare-commit-msg}
  14-15. [transformed_text ×2] adapters/dsh/agent.cordis.yml.template、adapters/dsh/AGENTS.md.template
- **0.78.1 发布机器记录**（plan-tracker L11）："candidate 8155400（版本投影 **15 projections + @bootstrap-version 标记面 8 行 + REQUIRED_SNIPPETS 6 版本钉**）"；0.78.0 同构（EVD-906："release-projection --write written=15/source 0.78.0 ... @bootstrap-version 标记面 9 行 + REQUIRED_SNIPPETS 6 版本钉"）。
- **投影校验契约**（manifest release_projection_contract）：15 个 projection_id + 3 种 kind + 2 个 validation_inventories（REQUIRED_SNIPPETS dict ≥40 entries；PROJECTION_SYNC_PATTERNS sequence ≥11 且 exact 成员匹配——AST 字面量清点，release/projection.py L30-L61 `_inventory_value`）。
- **写引擎**：`infra/release/projection.py`（313 行）——byte/structured/transformed 三类写入 + journal 备份回滚（L256-L312）。
- **REQUIRED_SNIPPETS/PROJECTION_SNIPPETS 机制占用行数**：325 + 133 = 458 行（§3.4），另有 WORKFLOW_SNIPPETS 81 行、REQUIRED_FILES 60 行、PROJECTION_SYNC_PATTERNS 12 行。

### 5.2 Check 28p duplicate_code 机制（advisory）

`check_duplicate_code`（L19477-L19524）：阈值 warn 60% / error 80%（core/architecture-health.json duplicate_code 字段），配对来源 `_archguard_source_projection_pairs`（L19458-L19474）= **主树 infra/*.py 顶层文件 ↔ e2e fixture 同名文件自动派生**；normalize 行尾 + 忽略空白。Check 28p 打印行自标 "(advisory)"（L15922）；EVD-969 构成定性："28p ×3（infra 薄投影 by-design 100% dup：`__init__`/cleanup/resolve_entry 为 re-export 投影）"。

### 5.3 e2e fixture 全量拷贝实证

对照脚本（fixture 相对路径 ↔ 主树同名文件 ReadAllLines 行数）实测：**91 个同名文件**，其中 **60 个 SAMELOC（行数全等）/ 31 个 DIFF（fixture 为历史快照，行数落后）**。抽样：

| fixture（project/e2e-test-project/...） | fixture LOC | 主树 LOC | 判定 |
|---|---|---|---|
| infra/verify_workflow.py | 14,166 | 24,252 | DIFF（快照落后 ~10k 行） |
| infra/tests/test_verify_workflow.py | 6,678 | 18,255 | DIFF |
| infra/archive.py | 1,671 | 2,971 | DIFF |
| infra/tests/test_archive.py | 2,064 | 3,788 | DIFF |
| infra/cleanup.py | 611 | 665 | DIFF |
| infra/resolve_entry.py | 360 | 360 | **SAMELOC（= 28p by-design 100% dup 对之一）** |
| infra/__init__.py | 1 | 1 | **SAMELOC（by-design dup）** |
| skills/software-project-governance/SKILL.md | 336 | 336 | SAMELOC（byte_copy 投影目标） |
| infra/hooks/pre-commit | 325 | 451 | DIFF |
| commands/governance-init.md | 928 | 928 | SAMELOC |

e2e-test-project 总量：106 文件 / 39,762 行（其中 .py 26,016 行，§2.1）。FIX-270 交付含"e2e fixture 镜像 blob 逐字节一致"门禁（check-projection-sync PASS 15，EVD-906）。

### 5.4 28p by-design 重复实测

EVD-969 定性的 3 对 by-design 重复（28p advisory 输出对象）：`infra/__init__.py`（1=1）、`infra/cleanup.py`（611 vs 665，归一化行集高重合）、`infra/resolve_entry.py`（360=360）。配对机制 = §5.2 主树 infra 顶层 glob；豁免面（"ArchGuard 夹具/投影豁免面"）为 session-snapshot L25 登记的后续候选（未 triage）。

---

## 6. 治理数据面

### 6.1 热文件体积（实测，字节/KB/行数）

| 文件 | bytes | KB | 行数 | 28s 阈值判定（200KB WARN/250KB ERROR） |
|---|---|---|---|---|
| .governance/plan-tracker.md | 352,311 | 344.1 | 717 | **ERROR**（超 error_bytes=250,000） |
| .governance/evidence-log.md | 1,453,573 | 1,419.5 | 1,835 | **ERROR** |
| .governance/decision-log.md | 210,638 | 205.7 | 191 | **WARN** |
| .governance/risk-log.md | 45,397 | 44.3 | 49 | OK |
| .governance/session-snapshot.md | 5.3 KB | — | 62 | 不在 28s 监控列表 |
| .governance/execution-packets.json | 77 KB | — | 898 | 不在列表 |
| .governance/agent-locks.json | 1.4 KB | — | 34 | 不在列表 |

### 6.2 28s 体积告警实测（命令输出原文，2026-09-09）

```
$ python -B skills/software-project-governance/infra/verify_workflow.py check-governance-data-size
=== Governance Data Size Check (ArchGuard/FIX-160) ===
  [ERROR] governance_data_size: .governance/plan-tracker.md 352311 bytes (344.1 KB) exceeds error_bytes=250000 bytes=352311
  [ERROR] governance_data_size: .governance/evidence-log.md 1453573 bytes (1419.5 KB) exceeds error_bytes=250000 bytes=1453573
  [WARN] governance_data_size: .governance/decision-log.md 210638 bytes (205.7 KB) exceeds warn_bytes=200000 bytes=210638

  Result: ISSUES FOUND — 2 ERROR, 1 WARN
  (advisory — fatal_on_error=false; see architecture-health.json governance_data_size)
```

阈值出处：core/architecture-health.json `governance_data_size`（FIX-160；note 原文："Warn at 200KB, error at 250KB (below the 256KB agent single-read limit...)"）。RISK-039 行历史注记（2026-07-25）："evidence-log 1253KB（Check 28s ERROR，advisory）——363/408 EVD 行被 179 个 LIVE 任务阻塞——结构性膨胀非引擎 bug，用户接受现状作为已知 debt"。

### 6.3 归档现状

- archive/ 总量：54 文件 / 1,443.9 KB；index.md 905 行；tasks 20 / evidence 19 / decisions 10 / risks 4 文件。
- **archive dry-run 输出原文（2026-09-09 实测）**：
```
$ python -B skills/software-project-governance/infra/archive.py migrate --auto --dry-run
📦 治理数据归档: 跳过（无可归档数据——归档范围 v0.1.0~v0.78.0 触发器满足（release_forced）但无可归档数据——可能已全部归档或格式未被识别）
```
- EVD-969 处置记录（2026-09-09）："28s 处置：archive.py migrate --auto --dry-run 如实报告「触发器满足（release_forced）但无可归档数据」——热文件超限为诚实残留，不强行归档"。

### 6.4 .governance 全量

845 文件 / 158,830 行 / 467 py LOC（§2.1）。其中 change-triage/ 机器记录 JSON 单文件最大 1,067 行（FIX-250.json），incidents/ 含会话 jsonl 与 patch 残档（audit147 等目录）。

---

## 7. 测试基线

### 7.1 文件与用例计数（实测）

- 测试 py 文件：**47 个**（infra/tests 46 含 3 个 `__init__.py` 与 e2e/test_governance_init.py + 仓库根 tests/test_product_code.py 1 个）。
- `def test_` 总数：**2,201**（grep `^\s*def test_` 求和）。
- Top：test_verify_workflow.py 811 / test_task_priority.py 123 / test_archive.py 119 / test_verify_rel063_evidence.py 92 / test_change_triage.py 70。
- 测试 LOC 合计 47,781（infra/tests）+ 107（根 tests）——测试代码量约为被测 infra 生产代码（104,299 - 47,781 = 56,518）的 0.85 倍（比值事实，非评判）。

### 7.2 最近全量运行结果（采信治理记录，本阶段未运行 pytest——硬门槛）

| 时点 | 记录 | 结果 | 出处 |
|---|---|---|---|
| 2026-09-09 | FEAT-011 交付（EVD-962） | "unittest 775 ran failures=1（既有定性 LoopRuntimeClaimAdapterTests 环境超时）"；"TDD 红→绿 15→30→32 passed" | .governance/evidence-log.md L1804 |
| 2026-09-09 | FIX-297 交付（EVD-964） | "单文件 unittest Ran 788 failures=1（既有定性 LoopRuntimeClaim）" | 同上 L1808 |
| 2026-09-09 | FEAT-016 审查（review-FEAT-016-CODE-R0） | "测试通过结果（811 passed + 89 subtests 等）采信开发者 EVD-970 结构化返回（本审查只读未运行）" | docs/reviews/review-FEAT-016-CODE-R0.md L35 |
| 2026-09-08 | 0.78.1 bootstrap 会话 | "check-governance --summary-only 实测 117 issues（首项 Check 10 M5 anti-pattern ×1 + Check 18c 执行包 scope 过宽 ×4）" | plan-tracker L11 |
| 2026-08-23 | FIX-270（EVD-FIX-270） | "全量 1768 passed+237 subtests 0 failed" | evidence-log L1394 |
| 2026-08-25/26 | FIX-278（EVD-FIX-278） | "全量 1976 passed+215 subtests（27 failed 全既有基线——24 bash/WSL 环境 + cleanup presets + loop-runtime 抖动 + resolve_entry snapshot-freshness）" | evidence-log L1553 |

### 7.3 性能事实（非功能-性能维度）

- **status <2s 基线**（FIX-270，0.76.0，2026-08-23 交付）：宿主实测 0.49s / dogfood 0.56s；验收原文"宿主项目 status <2s"（plan-tracker L243；developer-fix-report.md L33）。**本会话单次实测（dogfood，含解释器启动）：4.04s**——与 RISK-044/048 登记的环境敏感先例同域（本会话为并行治理 agent 负载环境；同时点治理热文件较 2026-08-23 显著增长，§6.1）。两值并列如实登记。
- **summary-only 墙钟敏感（RISK-044，状态"缓解中"）**：FIX-264 实测 31-32s 超设计 §3.1 <15s 门禁 → DEC-149 接受并修订验收为"<60s 且每会话仅一次" → DEC-167 复核 32.8s/29.6s 通过 → **2026-09-08 M-0 复评（DEC-177 ②）转"缓解中"：4 样本墙钟 65.7/61.3/64.7/56.6s——3/4 超 60s 修订验收线**；quick-scan 前移评估随 0.79.0 立项（risk-log L44 全文）。
- **测试环境敏感（RISK-048，打开）**：test_loop_runtime_claims median<8s 断言在同机并行治理 agent 负载下可超阈（FIX-288 全量回归实测 12.4s；因果证伪链：被测模块仅 import stdlib、payload 物化自 git index 且 diff --cached=0 字节一致）（risk-log L48）。
- **check-governance 宿主提速事实**（FIX-270/EVD-FIX-270）：宿主 full 25.49s→2.40s（-91%）、--summary-only 2.49s；机制 = `_PLUGIN_PRODUCT_CHECK_IDS` 22 项产品自检按事实源根切分，宿主默认跳过 + [SKIP] 披露，--product-gates 显式开启。

---

## 8. 已知问题与债务汇编（逐条带出处，未发明）

### 8.1 risk-log open 风险要点（实测：状态"打开"6 条 + "缓解中"1 条）

口径说明：任务书"6 条 open"= 下表前 6 行（状态列="打开"）；RISK-044 状态="缓解中（2026-09-08 M-0 复评转）"单列。risk-log 全文 49 行直读（.governance/risk-log.md L42-L49）。

| 编号 | 要点（原文压缩） | 状态 |
|---|---|---|
| RISK-036（L42） | 官方收录与市场采用准备不足——主流 AI 编程用户无法感知项目价值；1.0.0 前需补官方 plugin manifest/assets/英文首屏/5 分钟成功路径/公开 E2E 矩阵/外部项目验证等 | 打开 |
| RISK-039（L43） | 架构腐化看护缺口——28 check 全是结构/事后/自觉型约束；"verify_workflow.py 已膨胀到 20,294 行/439 def/54 子命令 God Module，source/projection 双写 6128 行差异……全部在零告警下发生"；2026-09-09 复评维持打开（关闭条件"外部宿主验证 ArchGuard 面"未满足） | 打开 |
| RISK-046（L46） | Coordinator 派发锁清单可与机器 triage 记录 files 漂移且引用不存在路径——FIX-288 实证子 agent 空转一个开发波次；根因修复 FEAT-013 在 0.79.0 队列 | 打开 |
| RISK-047（L47） | review-record force 覆盖路径 evidence 行语义与 CLI 出路缺口（低危观察） | 打开 |
| RISK-048（L48） | test_loop_runtime_claims 性能阈值环境敏感（见 §7.3） | 打开 |
| RISK-049（L49） | 适配器面"用户可用性宣示 vs 验证等级"缺口（FIX-290 根因链）；三关闭标准已由 FEAT-014/015/016 齐套，"关闭动作待用户裁决（残余候选：live/headless 会话面〔DEC-180〕、非 dsh 适配器等级映射〔DEC-179〕）" | 打开 |
| RISK-044（L44） | summary-only 墙钟（见 §7.3） | 缓解中 |

### 8.2 治理健康摘要 issues 构成

- **session-snapshot（2026-09-09 上一会话终态，L14）**："治理健康: 26 issues（会话开始 26 → 结束 26，零新增；构成 = EVD-969 定性 advisory 族不变）"。
- **EVD-969（evidence-log L1829，REL-074，2026-09-09）终局构成定性原文**："27 issues 构成——28o ArchGuard advisory ERROR ×8（e2e 夹具度量，fatal_on_error=false 不阻断发布）+ 28p ×3（by-design dup）+ 28s ×2（热文件体积 advisory）+ Check 30 ×7（设计性 fail-closed，用户裁决保留）+ Check 31 ×1（口径差异候选）+ WARN 族——均为 advisory 度量/设计边界/真实数据态，无噪声性误报"。
- 26 vs 27 差异：EVD-969 定性时点（REL-074 收尾）与 snapshot 快照时点的面板计数差 1（未在治理记录中归因——**数据缺口**，如实登记）。

### 8.3 FEAT-016 R0 发现（docs/reviews/review-FEAT-016-CODE-R0.md）

- **F-1（P1，既有缺陷独立核验）**：`cmd_check_release` 无条件 `result["pass"] = False`——**本会话 HEAD 实测仍为 L20568**（read 核验：L20564-L20568，`claim_gate` issues 注入后无条件置 False，无守卫无注释）。引入 commit `4134026`（FIX-199/200/202/213，2026-07-17）。影响：CLI `check-release` 对任何输入恒 FAILED + exit 1（引擎层 `check_release_readiness` L7344-7345 `pass=not issues` 语义正确，受损为 CLI verdict 区分度）（review L41/L58-L65）。
- **F-2（P2）**：test L7491-7499 断言 `assertEqual(1, exit_code)` 在 F-1 quirk 下归因强度为零（exit 1 恒真）（review L42）。
- **F-3（P2）**：L7019-7024 块注释（dsh upgrade regression 组成）范围宽于实际交付（preset 冒烟子集；`dsh plugin add link:/file:` pnpm 侧复验不在机器 gate 内）——RISK-049 关闭标准(3) 措辞 MUST 限定（review L43；DEC-179 同构先例）。

### 8.4 Check 31 身份子相位口径差

EVD-969(1)："残留 1 条身份子相位 FAIL 为口径差异（独立运行 check-loop-runtime-claims = PASS 零 findings vs 引擎内 identity_verdict=FAIL——**未定位，登记候选**）"。session-snapshot L25 沿用登记。

### 8.5 HotFact 环境稳定（FIX-294 P3-5）

EVD-965（evidence-log L1811，FIX-294，2026-09-05）遗留登记原文："P3×6 登记（……P3-5 HotFact 环境稳定性独立候选）"。

### 8.6 混合数组 TypeError（FEAT-011 R2 N-2）

plan-tracker L284（FEAT-011 完成行）："遗留 F-3 部分三项 + F-4~F-6（P3）+ **R2 N-2（HEAD 既有混合数组 TypeError 独立候选）** + F-1 宣示口径（→FIX-297）登记"；EVD-962 同记载。

### 8.7 hook 接线缺口（FIX-297 L37）

- FEAT-011 交付时 hook 接线为后续候选（plan-tracker L284："hook 接线为后续候选"）。
- FIX-297（2026-09-09 完成，plan-tracker L282）：以 behavior-protocol M1.2 MUST「直写后复跑 governance-write-guard」+ SKILL.md L116 投影 + L126 分级口径承接（方案 2，用户批量授权）。
- **version-plan-0.79.0.md L37 原文**："〔2026-09-09 收窄：hook 接线未交付，登记为后续候选；本轮以 behavior-protocol M1.2 MUST 复跑规则 + SKILL.md 分级口径承接（FIX-297，REVIEW-FEAT-011-DESIGN-R0 F-1 方案 2）〕"。
- session-snapshot L25 候选清单原文："hook 接线（FIX-297 L37）"。

### 8.8 非 dsh 适配器映射（DEC-179）与 live 会话面（DEC-180）

- **DEC-179**（decision-log L188，2026-09-09）："其余适配器面（Claude/Codex/Gemini/opencode/Chrys/zcode）宣示未纳入该口径——登记为后续候选，未 triage、不入任务表"。
- **DEC-180**（decision-log L189，2026-09-09）："live/headless 会话面验证登记为后续候选，未 triage、不入任务表；live/headless 会话面 = 后续候选"。

### 8.9 ArchGuard 夹具/投影豁免面

session-snapshot L25 候选清单首项："ArchGuard 夹具/投影豁免面（0.79.0 G5/G6 邻域）"（EVD-969 候选登记原文："候选登记（未 triage）：ArchGuard 夹具/投影豁免面（0.79.0 G5/G6 邻域）、Check 31 身份子相位口径差异"）。机制事实见 §5.2/§5.4。

### 8.10 历史拆分链关键结论原文（逐条）

- **DEC-083**（2026-06-24，archive/decisions/decisions-v0.1.0-0.59.0.md L32/L37）：路线图三项——(1) 0.57.0 深度诊断归档；(2) 0.58.0 ArchGuard 独立产品能力；(3) "verify_workflow.py 采用渐进式按 check 域拆分（0.59.0~0.64.0 每版拆 1~2 域，**最终退化为 <500 行薄入口**），ArchGuard 守护每步拆分质量"。
- **DEC-088**（2026-06-27，同文件 L11/L16）：策略转向原文——"(1) re-export 搬运不降主文件行数……(2) 避开了体量大头（硬编码数据表 ~1948 行 + 重复 print 编排块 ~1126 行）……(3) **业务逻辑 ~16000 行是合理复杂度**（65 个 check 函数 print%=0%，是 54 命令 × 治理规则的真实产物，不可压缩只能搬移）"；Step A+B 单次缩减预估 ~2600 行（20321→~17700）。
- **EVD-630**（2026-06-27，archive/evidence/evidence-v0.1.0-0.61.2.md L23）：诊断实测——438 个 top-level 函数 82% ≤50 行，仅 2 个 >500 行（cmd_check_governance 1126 + main 547）；"膨胀来自函数数量多非单体巨大"；硬编码数据表 133 个 ~1948 行（REQUIRED_SNIPPETS 326/PROJECTION_SNIPPETS 106/WORKFLOW_SNIPPETS 82/REQUIRED_FILES 61）；"REQUIRED_FILES 与 manifest.json 300 条目重复（fallback 副本），本应外部化"；cmd_check_governance 1126 行里 437 行 print。
- **EVD-632**（2026-06-27，同文件 L22）：ROI 修正——"实测 53 段 Check 编录……原型 Z（custom）28 段是独特逻辑无法泛化"；"修正 Step B 净收益 ≈ **~260 行**，不是诊断报告的 ~1100 行"；"诚实结论：verify_workflow.py ~16000 行业务逻辑是 54 命令 × 治理规则的合理复杂度，拆分整体 ROI 有限"；用户叫停（"你这逻辑都每理顺"）。
- **DEC-090/091**（2026-06 下旬）：降级 SoD（single-operator mode）授权链——DEC-091 "REL-048 版本化 0.61.0 授权——延续 DEC-085~090 降级 SoD"（archive/index.md L854/L862）；0.61.0 版本号由治理数据膨胀修复接管（plan-tracker L458："版本号复用 0.61.0（DEC-088 拆分主题已叫停……）原'拆分 Phase 3'规划随 DEC-088 叫停而作废"）。
- **DEC-145**（2026-08-22，archive/decisions/decisions-v0.1.0-0.76.0.md L16）：停滞三件套（FIX-155/156/REL-047）间接闭合——"背景事实：(1) 2026-06-27 用户质疑'20000 行两版只拆 600 行'→ DEC-088 → 详勘（EVD-632）发现 ROI 被高估……(4) 0.61.0 版本槽已由 REL-048 接管，REL-047 行内既定'**重启=新任务新版本号**'"。
- 相关既决：DEC-096（SKILL frontmatter 为 active version 权威）、DEC-099（loop 新逻辑不碰 God Module）、DEC-103（"DEC-088 禁止以 re-export 伪装 God module 拆分"，decision-log L101 引用）。

---

## 9. 消费者/接口/约束面

### 9.1 命令消费方矩阵

| 消费方 | 引用事实（实测） |
|---|---|
| .git/hooks/pre-commit | **不直接调用 verify_workflow.py**（纯 shell 自实现：staged 文件分类、evidence_file 存在性检查、plugin root 解析含 dsh preset root 候选——L21/L32/L60-L81） |
| .git/hooks/commit-msg | **不直接调用 verify_workflow.py**（shell 实现 plan_file/evidence_file 检查，L31/L52/L98） |
| .git/hooks/post-commit | **L190 唯一调用**：`python "$VERIFY_WORKFLOW" check-governance 2>/dev/null`（路径解析序：$REPO_ROOT/scripts/ → $SPG_RESOLVED_HOME/infra/，L181-L190）——hook 面唯一 verify_workflow 子命令消费 = check-governance |
| .github/workflows/ci.yml（Governance CI，唯一 workflow） | 4 步：`verify_workflow.py`（默认 verify）/ `check-manifest-consistency --fail-on-issues` / `python -m unittest discover -s infra/tests -v` / `check-cross-references`（L19-L25；ubuntu-latest + Python 3.11） |
| CLAUDE.md（本地 gitignored，plan-tracker L11 注记） | bootstrap 引用：execution-packet --write（L92）、archive.py migrate --auto --dry-run（L139）、check-archive-integrity（L146）、cleanup.py（L134）、check-governance（L252） |
| AGENTS.md（仓库内） | 第一动作 resolve_entry.py --json（L7）；check-archive-integrity（L145）；verify_workflow.py（L186 验证命令入口） |
| 4×infra/hooks/*（源模板，投影目标 §5.1 #10-13） | @version-line 投影承载（transformed_text） |

### 9.2 平台矩阵（adapters/ 实测）

6 个平台适配器目录，统一三元组（adapter-manifest.json + launch.py + README.md）+ dsh 扩展：

| 平台 | 文件数 | 扩展面 |
|---|---|---|
| dsh | 16 | agent.cordis.yml.template、AGENTS.md.template、preset.yml、skill-shims/ ×9（change-triage/governance-cleanup/gate/init/review/status/update/verify/governance） |
| claude / codex / gemini / opencode | 各 4 | 基础三元组 |
| chrys | 3 | 基础三元组（无独立 launch pyc） |

代码内平台清单：`MAINSTREAM_AGENT_ADAPTERS = ["claude", "codex", "gemini", "opencode", "chrys", "dsh"]`（L1500）；`RUNTIME_MATRIX_AGENT_IDS` 另含 cursor/copilot（research-only，L2156-L2157）；`AGENT_RUNTIME_E2E_PLATFORMS = ("claude","codex","gemini","opencode")`（L18241）。版本投影覆盖 5 个平台 plugin/marketplace JSON + package.json（§5.1）。

### 9.3 Windows-first 与编码纪律（FIX-278）

- **FIX-278 G4/F**（EVD-FIX-278，evidence-log L1553；diff patch L9/L22/L43/L64 四处投影原文）："pwsh 读取 `.governance` 治理文件 MUST 显式 UTF-8——`Get-Content -Encoding UTF8`（或 `[System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8)`）；禁止裸 `Get-Content`——Windows 默认 ANSI/GBK 解码会产生 mojibake（AUDIT-147 D6 / AUDIT-148 §4.3 乱码实证：裸 `-Tail 30` 读 evidence-log → 22,311 字符大面积乱码）"。规约投影落 AGENTS.md/SKILL.md/commands/governance.md + GBK936 负对照仿真（test_utf8_read_guard.py 223 行）。
- 其他 Windows-first 事实：bootstrap.cmd（infra/）；FIX-249 P1-1 _msys POSIX IndexError 平台门控先例；_truncate_repr/多字节截断边界（review-FIX-252-CODE-R1 P3-5/P3-6）。

### 9.4 非标准库 import 清单（grep 实测）

- **verify_workflow.py**：全部 import = stdlib（pathlib/sys/io/contextlib/re/argparse/ast/json/locale/os/signal/subprocess/importlib.util/shutil/hashlib/tempfile/fnmatch/time/urllib.request/webbrowser/datetime）+ 内部 checks×15/release×4（L1-L67、L1048-L1237 实测清单）。**零第三方**。
- **infra 全树 91 个生产+测试 py 文件**：第三方 import 仅 2 处且均为可选保护——
  - `tests/test_dsh_adapter.py:983` `import yaml`：`@unittest.skipUnless(find_spec("yaml") is not None, "PyYAML unavailable (optional progressive check, NOT_RUN)")`（L978-L983）；
  - `tests/test_loop_runtime_claim_attestation.py:543` `import psutil`：try/except Exception → return 0 降级（L541-L550）。
  - **生产代码（非 tests）零第三方依赖**。RISK-048 因果证伪链亦引用此事实（"被测模块 checks/loop_runtime_claims.py 仅 import stdlib"）。

### 9.5 发布流程机器门清单（从代码命令表实测）

- **check-release**（cmd_check_release L20531，CLI argparse L23481）：引擎 `check_release_readiness`——静态门 17 项（EVD-906 实录清单：version/fact-source/hot-fact/runtime-matrix/first-session/pack-status/adapters/projection-crossrefs/archive-integrity/release-docs/lineage/gate-sequence/one-dot-zero/loop-fuse/changelog/loop-runtime-claim + execution gates 族）+ dsh_upgrade_regression 阻断组件（FEAT-016，temp DSH_HOME 隔离复用 FEAT-015 冒烟）+ tag/lineage/push-state 门（FIX-192/RISK-041 链）；已知 CLI 层缺陷 F-1（§8.3）。
- **release-ledger**（cmd_release_ledger L21215；release/ledger.py validate_release_ledger）：0.62.0+ 每版本 manifest + append-only events + candidate→released 单父唯一 transition（DEC-103/DEC-104 链）。
- **release-projection**（cmd_release_projection L21229；release/projection.py write_projections）：15 投影写入 + journal 回滚 + 写后校验（§5.1）。
- 配套门（dispatch 表实测）：check-version-consistency / check-projection-sync / check-injection-contract / check-manifest-consistency / check-cross-references / check-archive-integrity / check-dsh-skills-manifest / check-dsh-preset-smoke 等。

### 9.6 接口形状与数据流（架构质量维度-接口/数据流现状事实）

- CLI 入口链：`main()`（L24247-L24248：`cmd = args.command or "verify"; commands[cmd](args)`）→ cmd_* → check 函数 → Result dict（键形实测：`pass`/`issues`/`details`——如 L20566-L20568 `result["details"]["loop_runtime_claim_gate"]`、L7344-7345 `result["pass"] = not issues`）→ print 编排（§3.5）→ exit code。
- exit code 语义族（实测散布）：0/1 常规；change-triage 写时 guard 失败 exit 2（DEC-166 G3）；governance-write-guard SKIP=产物缺席（EVD-962）。
- 错误处理/降级清单（架构质量维度-错误处理现状）：fail-closed 默认（Check 30 设计性 fail-closed ×7 见 §8.2）；[SKIP] 披露机制（FIX-270 宿主产品门禁跳过）；summary-only top-N 降级（DEC-166 G1）；archive dry-run 只读模式；projection 写入 journal 回滚；resolve_entry resolved_root_ok=false → MUST STOP（DEC-080/RISK-038）。

### 9.7 可扩展性/可测试性现状样本（只登记事实）

- **新增一个 check 的触碰面样本（FEAT-016 实录）**：check_release_readiness 组件接入（引擎 L7264-L7281 + CLI 组件行）+ 测试 13 用例 + review 记录 + change-triage JSON + EVD——单个发布门组件交付触碰 verify_workflow.py 单文件内多区段 + 测试文件 + 治理记录五类文件（review-FEAT-016 §审查对象清单）。
- **新增一个子命令的触碰面样本（FEAT-011 实录）**：cmd_governance_write_guard（L22586）+ argparse add_parser（L24149-L24155）+ dispatch dict 键（L24244）+ behavior-protocol M1.2 协议条目（FIX-297）+ SKILL.md 投影——同文件 3 区段 + 2 外部文件（EVD-962/EVD-964）。
- **可测试性现状**：测试与被测同目录（infra/tests/）；纯函数（parser/check 函数）与子进程依赖（e2e/smoke/外部验证）混合；811 用例集中在单文件 test_verify_workflow.py（§7.1）。

---

## 10. 数据缺口清单（如实登记，未补造）

| # | 缺口 | 说明 |
|---|---|---|
| 1 | pytest/unittest 全量结果 | 本阶段禁止运行测试套件——最近结果采信治理记录多时点（§7.2），无 2026-09-09 当日全量数字 |
| 2 | 健康摘要 26 vs 27 issues 差 1 的归因 | EVD-969 定性 27、session-snapshot 记 26，治理记录未归因差值 |
| 3 | status 墙钟可比基线 | FIX-270 基线 0.49~0.56s（2026-08-23 时点机器/数据态）与本会话 4.04s 无同机同数据对照（RISK-044/048 环境敏感先例） |
| 4 | e2e fixture 31 个 DIFF 文件的逐文件 diff 内容 | 本报告只登记行数差抽样（§5.3）；逐 hunk 差异未展开（fixture 为历史快照，byte 级一致性由 check-projection-sync 守护已发布版本） |
| 5 | loop_runtime_claim_attestation.py 行数两个口径 | 早期清单 1,315 行 vs ReadAllLines 1,200 行（本报告采 ReadAllLines；差异疑为度量方法〔§1.1〕，未深究） |
| 6 | 非 dsh 适配器 claim→evidence 等级映射 | DEC-179 登记为"未 triage 后续候选"——无实现面可度量 |
| 7 | v0.58.0 之前 tag 的 verify_workflow.py 曲线 | 任务书只要求 6 个 tag 点；更早时点未测 |

---

## 附：本报告度量基线快照（供 Phase 2/3 引用）

- HEAD 工作区（未提交窗口）；git tags 至 v0.78.1（2026-09-08 核实存在，plan-tracker L11）。
- verify_workflow.py = 24,252 行 / 504 def / 74 cmd_* / 80 dispatch 键（77 函数 + 3 别名）/ 70 Check 段 / 1,315 print / 192 数据块 2,048 行 / 19 内部 import 源（review_domain 59 符号最大耦合）。
- 投影 15 + 标记面 8 行 + 6 版本钉；e2e fixture 91 同名文件（60 SAMELOC/31 DIFF）；tag 曲线 20937→20321→20404→21814→20183→22949→24252。
- 治理数据：plan-tracker 344.1KB / evidence-log 1,419.5KB / decision-log 205.7KB / risk-log 44.3KB；28s = 2 ERROR + 1 WARN（advisory）；archive dry-run = 触发器满足但无可归档数据。
- 测试：47 文件 / 2,201 def test_；最近采信 788 ran failures=1（既有定性，2026-09-09）。
- 风险面：6 打开 + 1 缓解中；候选债务 6 项（session-snapshot L25）。
