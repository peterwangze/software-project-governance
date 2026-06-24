# ArchGuard — 架构腐化看护能力设计（REQ-101 / 0.58.0）

> **任务**: REQ-101
> **承载版本**: 0.58.0
> **来源**: AUDIT-121 F6（架构腐化看护缺口根因）、DEC-083
> **日期**: 2026-06-25
> **性质**: 设计文档（治理记录范畴）。本文档定义 ArchGuard 的 check 项、阈值、schema、告警级别和实施约束；产品代码实现由 0.58.0 开发阶段 spawn Governance Developer 执行。
> **数据基础**: 2026-06-25 Explore agent 在 commit `2e19dbf` 基线采集的真实校准数据（遵循 AUDIT-117 前提事实约束纪律）

---

## 0. 设计目标与原则

### 目标
把 AUDIT-121 诊断的"工作流缺少架构/实现腐化看护"（F6 根因）转化为**可复用于其他大型项目的产品能力**。ArchGuard 不只是本项目的自检工具，而是任何采用本工作流的大型宿主项目都能获得的架构预警层。

### 设计原则
1. **诊断不阻断**：ArchGuard 默认 WARN/ERROR 告警，**不阻断现有 release gate**。阈值保守，先观测后收紧。
2. **声明式预算**：架构健康度阈值通过 `core/architecture-health.json` 声明（类似 quality-budget），项目可自定义。
3. **渐进式采纳**：check 默认 enabled 但非 fatal，让现有项目平稳接入。
4. **可复用**：check 逻辑不硬编码本项目路径，基于通用规则（模块大小、重复、复杂度、技术债）。
5. **事实优先**：所有阈值基于真实校准数据，推测性建议显式标注【推测】。

---

## 1. 阈值校准数据基线（事实）

基于 2026-06-25 Explore agent 采集（commit `2e19dbf`）：

| 维度 | 实测值 | 含义 |
| --- | --- | --- |
| 单文件最大行数 | verify_workflow.py **20,294 行**（占全仓 .py 51.8%） | 极端 God Module |
| 单函数最大行数 | `cmd_check_governance` **1,065 行** | 极端长函数 |
| ≥200 行函数数 | **9 个**（累计 4,518 行，占 22%） | 长函数集中区 |
| ≥100 行函数数 | **46 个**（累计 9,718 行，占 48%） | 近半代码在长函数中 |
| 函数总数 | 439 个，平均 46.2 行 | 基线 |
| 模块级常量数 | **212 个**（远超预期 40+） | 全局可变状态膨胀 |
| source/projection 语义重复 | **67.5%**（差异 32.5%） | 双写负担量化 |
| CLI 子命令数 | 54 个（累计 3,083 行，占 15%） | 命令面规模 |
| 全仓 .py 文件数 | 14 个（39,137 行） | 前一名占 51.8% |

### 阈值推导逻辑（事实→阈值）

**模块大小**：现有最差值 20,294 行。健康目标应远低于此，但立即要求会全部告警。
- 观测基线：≥5,000 行 = 严重（当前 verify_workflow.py 触发）
- 警告基线：≥2,000 行 = 需关注（archive.py 1,675 接近但未触发；test_verify_workflow 12,754 触发）
- 【推测】拆分目标：单文件 <1,500 行（verify_workflow.py 拆分后各域模块应达此值）

**函数复杂度**：现有最差 1,065 行。
- ERROR：函数 ≥500 行（当前 2 个：cmd_check_governance 1065、_run_version_command 806）
- WARN：函数 ≥200 行（当前 9 个触发）
- 【推测】健康目标：函数 <100 行

**重复代码**：source/projection 67.5% 语义重复。
- ERROR：语义重复 ≥80%（当前未触发，因差异 32.5%）
- WARN：语义重复 ≥60%（当前触发）
- 关键：必须 normalize 换行符（CRLF/LF）后再比较，否则裸 diff 误判 100% 差异

---

## 2. Check 项设计

### 2.1 `check-architecture-health`（核心）

**检测维度**：
1. **单文件行数阈值**：扫描 `core/architecture-health.json` 声明的 `module_size` 规则适用的所有 `.py`/`.js`/`.ts` 文件
2. **单函数行数阈值**：AST 解析（Python 用 `ast`，JS/TS 用正则或 `esprima`）统计每个顶层 def/function 行数
3. **模块级常量数**：统计模块级 `^[A-Z][A-Z_0-9]+ =` 赋值数量（Python）
4. **重复定义检测**：同一常量名在文件中多次赋值（如 `PRODUCT_CODE_PATTERNS` 在 verify_workflow.py:11666 与 :14064 重复——实测发现）

**输出格式**：
```
=== Architecture Health Check ===
Module size (thresholds: WARN ≥2000, ERROR ≥5000):
  [ERROR] skills/software-project-governance/infra/verify_workflow.py: 20294 lines
  [WARN]  skills/software-project-governance/infra/tests/test_verify_workflow.py: 12754 lines

Function length (thresholds: WARN ≥200, ERROR ≥500):
  [ERROR] cmd_check_governance: 1065 lines (verify_workflow.py:14396)
  [ERROR] _run_version_command: 806 lines (verify_workflow.py:1967)
  [WARN]  7 more functions ≥200 lines

Module constants (threshold: WARN ≥150):
  [WARN]  verify_workflow.py: 212 module-level constants
  [ERROR] duplicate definition: PRODUCT_CODE_PATTERNS at :11666 and :14064

Result: ISSUES FOUND — 2 ERROR, 11 WARN
```

**默认行为**：ERROR 不阻断 release gate（0.58.0 首版），仅告警。后续版本可配置为 fatal。

### 2.2 `check-duplicate-code`（source/projection 重复检测）

**检测逻辑**：
1. 扫描 `core/manifest.json` 或显式声明的 source/projection 对
2. 对每对文件：normalize 换行符（CRLF→LF）+ 忽略空白，计算语义差异行数
3. 重复率 = (1 - 差异行数 / max(source行数, projection行数)) × 100%
4. 阈值：WARN ≥60%，ERROR ≥80%

**关键技术约束**（基于实测）：
- **MUST normalize 换行符**：source 是 CRLF、projection 是 LF，裸 diff 会误判 100% 差异
- **MUST 忽略空白差异**：否则缩进/尾部空格干扰

**输出格式**：
```
=== Duplicate Code Check (source vs projection) ===
Pairs checked: 5
  [WARN] verify_workflow.py: source 20294 vs projection 14166 → 67.5% duplicate (32.5% semantic diff)
  [PASS] archive.py: 98.2% duplicate (acceptable)

Result: ISSUES FOUND — 0 ERROR, 1 WARN
```

### 2.3 `check-technical-debt`（游离脚本/历史文档/漂移检测）

**检测维度**：
1. **根目录游离脚本**：扫描根目录 `_fix_*`、`_tmp_*`、`debug_*` 等一次性脚本模式
2. **未归档历史文档**：`docs/release/` 中超过 N 个版本的 release docs（基于 version roadmap 判断哪些可归档）
3. **hooks 内容漂移**（本轮发现的 TD-007）：对比 `skills/software-project-governance/infra/hooks/*` 源与 `.git/hooks/*` 已安装副本的 @version 和内容
4. **技术债登记交叉验证**：读取 `core/technical-debt-ledger.md`，校验 OPEN/IN_PROGRESS 项是否在版本路线图中有承载版本

**hooks 漂移检测**（TD-007，本轮实测发现）：
- 对比 4 个 hook（pre-commit/commit-msg/post-commit/prepare-commit-msg）源 vs 已安装
- 内容不一致 → WARN（含 @version 差异 + 函数体差异）
- 这填补了 bootstrap "只检测存在不检测内容" 的缺口

**输出格式**：
```
=== Technical Debt Check ===
Root-directory residue scripts: 0 (clean)
Historical release docs: 108 files across 36 versions (WARN: ≥30 versions, consider archiving pre-current)
Hooks content drift:
  [PASS] pre-commit: source = installed
  [PASS] commit-msg: source = installed
  [PASS] post-commit: source = installed
  [PASS] prepare-commit-msg: source = installed
Technical-debt ledger: 6 OPEN items, 5 have carrying versions in roadmap, 1 DEFERRED (AUDIT-120)

Result: ISSUES FOUND — 0 ERROR, 1 WARN
```

### 2.4 `check-complexity`（函数圈复杂度，可选 AST 分析）

**检测逻辑**：
- 用 Python `ast` 模块计算圈复杂度（分支数：if/for/while/and/or/elif/except 各 +1）
- JS/TS：退化到嵌套深度启发式【推测】（无轻量 AST 库时）
- 阈值：WARN 圈复杂度 ≥15，ERROR ≥30

**输出格式**：
```
=== Complexity Check ===
Python files analyzed: 14
  [ERROR] cmd_check_governance: cyclomatic complexity 87 (verify_workflow.py:14396)
  [WARN]  check_lifecycle_registry: cyclomatic complexity 42
  [WARN]  12 more functions ≥15

Result: ISSUES FOUND — 3 ERROR, 13 WARN
```

**实现优先级**：0.58.0 可先实现行数代理（line-based proxy），圈复杂度 AST 留作 0.59.0+ 增强【推测】。

---

## 3. `core/architecture-health.json` Schema

声明式架构健康预算，项目可自定义。

```json
{
  "$schema": "architecture-health-v1.json",
  "version": "1.0",
  "description": "Declarative architecture health budget. ArchGuard reads this to calibrate thresholds.",
  "module_size": {
    "warn_lines": 2000,
    "error_lines": 5000,
    "target_lines": 1500,
    "exclusions": [
      {"path": "**/tests/**", "reason": "test files exempted from size limits"},
      {"path": "**/test_*.py", "reason": "test files exempted from size limits"}
    ]
  },
  "function_size": {
    "warn_lines": 200,
    "error_lines": 500,
    "target_lines": 100
  },
  "module_constants": {
    "warn_count": 150,
    "error_count": 300,
    "detect_duplicates": true
  },
  "duplicate_code": {
    "warn_pct": 60,
    "error_pct": 80,
    "normalize_line_endings": true,
    "ignore_whitespace": true,
    "source_projection_pairs": "auto-from-manifest"
  },
  "complexity": {
    "enabled": false,
    "warn_cyclomatic": 15,
    "error_cyclomatic": 30,
    "note": "AST-based complexity deferred to 0.59.0+; 0.58.0 uses line-based proxy"
  },
  "technical_debt": {
    "root_residue_patterns": ["_fix_*", "_tmp_*", "debug_*", "scratch_*"],
    "release_docs_archive_threshold_versions": 30,
    "hooks_drift_detection": true,
    "ledger_cross_validate": true
  },
  "gate_integration": {
    "fatal_on_error": false,
    "note": "0.58.0 first release: WARN/ERROR are advisory, do not block release gate. Future versions may enable fatal."
  }
}
```

### Schema 字段说明

| 段 | 字段 | 默认值 | 校准依据 |
| --- | --- | --- | --- |
| module_size | warn_lines | 2000 | archive.py(1675)未触发、test(12754)触发 |
| module_size | error_lines | 5000 | verify_workflow.py(20294)触发 |
| module_size | target_lines | 1500 | 【推测】拆分后各域模块目标 |
| function_size | warn_lines | 200 | 实测 9 个函数触发 |
| function_size | error_lines | 500 | 实测 2 个函数触发 |
| module_constants | warn_count | 150 | verify_workflow.py 212 个触发 |
| duplicate_code | warn_pct | 60 | source/projection 67.5% 触发 |
| gate_integration | fatal_on_error | false | 0.58.0 保守，先观测 |

---

## 4. 告警级别与 Gate 集成

### 告警级别
| 级别 | 含义 | 0.58.0 行为 |
| --- | --- | --- |
| PASS | 所有指标在目标内 | 无输出或简略 |
| WARN | 指标超过 warn 阈值 | 列出，**不阻断** |
| ERROR | 指标超过 error 阈值 | 列出，**不阻断**（0.58.0）；可配置为阻断（未来） |

### Gate 集成（Check 28 扩展）
ArchGuard 作为 Check 28 的子项接入（Check 28 已有 28a~28n，ArchGuard 为 28o~28r）：
- **Check 28o**: architecture-health（module size + function size + constants）
- **Check 28p**: duplicate-code（source/projection）
- **Check 28q**: technical-debt（residue + drift + ledger）
- **Check 28r**: complexity（可选，0.58.0 可为 line-proxy）

### release gate 集成
- `check-release --runtime-adapters` 的 execution gates **不包含** ArchGuard（0.58.0 首版）
- ArchGuard 通过 `check-governance` 的 Check 28 子项报告，WARN/ERROR 不阻断 release
- 用户可通过 `architecture-health.json` 的 `gate_integration.fatal_on_error` 启用阻断（默认 false）

---

## 5. 实施约束与边界

### 0.58.0 实施范围（产品代码，由 Governance Developer 实现）
1. 在 `verify_workflow.py` 新增 4 个 check 函数 + 4 个 cmd_ 入口（约 +400~600 行）
2. 新增 `core/architecture-health.json` 配置文件 + manifest 声明
3. Check 28 扩展 4 个子项（28o~28r）
4. 配套 unittest（infra/tests/test_architecture_health.py）

**讽刺但必要的边界**：0.58.0 在已经 20,294 行的 verify_workflow.py 里**新增** ~500 行 ArchGuard 代码，会让 God Module 更严重。这是 F1 与 F6 的张力——ArchGuard 检测架构腐化，但自身实现暂时加剧它。**缓解**：ArchGuard 的 check 函数设计为自包含模块，便于 0.59.0+ 拆分时第一个抽离（可作为拆分方法论的验证用例）。【推测】

### 边界声明（no-overclaim）
1. ArchGuard 是诊断型工具，**不自动重构**——它发现腐化，重构仍需人工/版本规划
2. 0.58.0 的阈值保守，不阻断 release gate，先积累观测数据
3. 圈复杂度 AST 分析可能推迟到 0.59.0+
4. ArchGuard 不关闭 RISK-039——关闭标准含"1 个外部宿主项目验证 ArchGuard 能发现真实腐化信号"
5. 本设计文档不修改 verify_workflow.py 产品代码（纯设计）

### 与 RISK-039 关闭标准的关系
RISK-039 关闭需要：
- ✅ ArchGuard 交付（0.58.0 实现本设计）
- ✅ architecture-health.json 发布（0.58.0）
- ⏳ verify_workflow.py 拆分完成（0.59.0~0.64.0）
- ⏳ source/projection 双写消除（0.64.0）
- ⏳ 技术债登记机制运行（0.57.0 已建立）
- ⏳ **1 个外部宿主项目验证**（未来 VAL 任务）

---

## 6. 证据索引

阈值校准数据来源（2026-06-25 Explore agent 实测）：
- 单文件行数：`find . -name "*.py" ... | xargs wc -l | sort -rn`
- 函数行数：`grep -nE "^def |^class "` + 起止行计算
- source/projection 重复：`diff -w`（normalize 空白后）语义差异 6586/20294 = 32.5%
- 模块常量：`grep -nE "^[A-Z][A-Z_0-9]+ *="` → 212 个
- 重复定义：`PRODUCT_CODE_PATTERNS` 在 :11666 与 :14064

---

*本文档为 REQ-101 / 0.58.0 ArchGuard 设计归档。实现阶段（0.58.0 开发）spawn Governance Developer 依据本文档编码，后置 Code Reviewer 审查。*
