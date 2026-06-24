# ARCH-AUDIT / 架构腐化深度审视与重构路线图

> **任务**: AUDIT-121
> **日期**: 2026-06-24
> **触发**: 用户指出"当前项目代码组织不合理，未按现代软件工程方式管理；工作流缺少大型项目持续演进中架构/实现腐化部分的看护"
> **范围**: 全项目深度审视（事实清单 + 影响分析 + 分版本重构路线图 + ArchGuard 看护能力规划）
> **性质**: 纯诊断文档，不改产品代码；产出后续版本承载依据
> **决策依据**: DEC-083（用户 2026-06-24 三项决策：全项目深度审视 / 独立版本承载 ArchGuard / 渐进式按 check 域拆分）

---

## 0. 审视方法与事实纪律

本文档遵循 AUDIT-117 确立的**"前提事实约束"纪律**——所有结论必须有实测证据，推测必须显式标注 `【推测】`，禁止基于"代码看起来像"推进结论。

所有事实信号采集命令均在 2026-06-24 于仓库根 `D:\AI\agent\claude\coding\project_management_workflow` 实测，commit 基线为 `5831cbf`（master HEAD）。

---

## 1. 事实清单（实测证据）

### F1 — God Module 反模式：verify_workflow.py 膨胀失控 🔴 P0

**实测证据**:

| 指标 | 实测值 | 行号/命令 |
| --- | --- | --- |
| 文件行数 | **20,294 行** | `wc -l` |
| 顶层 `def` + `class` 数量 | **439 个** | `grep -cE "^def \|^class "` |
| CLI 子命令数量 | **54 个** | `grep -cE "subparsers.add_parser"`，行 19781~20152 |
| `import` 语句 | 18 个 | 行 1~18 |
| 模块级全局可变状态常量 | **40+ 个** | `ROOT`/`REQUIRED_FILES`/`PROJECTION_SNIPPETS`/`REQUIRED_SNIPPETS`/`MAINSTREAM_AGENT_ADAPTERS`... 行 20~2099 |

**54 个子命令清单**（按 main() dispatch 顺序）:
```
verify, status, governance-context, capability-context,
gate, gate-check, gates, stage, stages, check-governance,
check-projection-sync, check-manifest-consistency, check-plugin-freshness,
check-agent-adapters, check-release, e2e-check, external-project-validation,
first-run-demo, web-console, agent-runtime-e2e,
check-cross-references, check-sequential-ids, check-structural-validity,
check-commit-scope, check-goal-alignment, check-user-impact,
check-agent-team, check-review-debt, check-version-consistency,
check-governance-packs, check-hot-fact-source, check-runtime-readiness-matrix,
check-first-session-measurement, check-governance-pack-status,
check-lifecycle-registry, check-host-capability-context, check-official-submission-ecosystem,
check-manifest-artifact-locks, check-flow-unit-runtime, check-governance-health,
check-official-submission-status, check-readme-pack-guidance,
check-release-projection-guide, check-quality-budget,
check-version-snapshot, check-installation-path, check-governance-debt,
check-locks, check-archive-integrity
```
（注：grep 输出 54 个 `add_parser`，部分为多行声明未在单行匹配到，实际去重后约 48~54 个命令）

**自然功能域聚类**（基于 `def check_*` 命名启发式）:
```
manifest 域 (3+ check)        | release 域 (3+)        | governance 域 (4+)
agent 域 (5+)                 | capability 域 (2+)     | evidence 域 (2+)
commit 域 (2+)                | risk 域 (2+)           | review 域 (2+)
projection/version/runtime/profile/protocol/quality... 各 1+
```

**诊断**: 单一文件承载 54 个不相关 CLI 命令、439 个函数、40+ 全局常量，违反**单一职责原则**、**开闭原则**（新增 check 必须修改同一个 main()）、**高内聚低耦合**。这是教科书级的 God Module / Blob 反模式。

**影响**:
- 认知负担：任何修改需在 2 万行中定位上下文，AI agent 和人类 alike 都面临"迷失在巨石文件"
- 测试耦合：12,754 行测试 (`test_verify_workflow.py`) 通过模块级 import 强耦合，无法对单个 check 域独立测试
- 演进摩擦：新增一个 check 需触碰 dispatch 表 + 全局常量区 + 检查实现区三处，且都在同一文件
- AI 可维护性差：LLM context window 装不下整个文件，agent 无法一次性理解全貌——**对一个 AI-first 项目，这是致命缺陷**

---

### F2 — 缺失现代软件工程基础设施 🔴 P0

**实测证据**:

| 维度 | 实测 | 现代标准 |
| --- | --- | --- |
| 包结构 | `skills/software-project-governance/infra/__init__.py` 仅 1 行；无 `src/` layout | `src/` + 显式包 `__init__.py` |
| Linter | 无 `ruff.toml` / `.flake8` / `pyproject.toml [tool.ruff]` | 强制 lint 门禁 |
| Formatter | 无 `black` / `ruff format` 配置 | 强制格式统一 |
| Type checker | 无 `mypy.ini` / `pyright` 配置 | 渐进式类型检查 |
| 打包元数据 | `package.json` 仅 npm identity（zcode host 用），Python 侧无 `pyproject.toml` | PEP 517/518 |
| 测试组织 | 根 `tests/` 只有 1 个 `test_product_code.py`（107 行）；真实测试全堆在 `infra/tests/test_verify_workflow.py`（12,754 行） | 按 check 域分文件 |
| CI 质量门 | `.github/workflows/ci.yml` 仅 1 个 workflow；只跑 unittest + verify | lint+type+test+cov+arch 多维门禁 |

**诊断**: 项目以"AI plugin/skill"形态存在，但 `infra/` 下有 **65,000 行 Python 产品代码**（verify 20k + test 12.7k + archive 1.6k + cleanup 0.6k + projection 副本）。这部分是**实质的软件工程资产**，却完全没有享受现代 Python 工程实践。

**影响**:
- 代码风格漂移无机制约束（2 万行靠人工保持一致不现实）
- 类型错误只能在 runtime 暴露
- 新贡献者无 onboarding 路径（无 lint/格式说明）
- 静态分析缺失，潜在 bug 只能靠 unittest 发现

---

### F3 — Source/Projection 双写负担 🟠 P1

**实测证据**:
```
skills/software-project-governance/infra/verify_workflow.py        20,294 行 (source)
project/e2e-test-project/skills/.../verify_workflow.py             14,166 行 (projection)
→ 差异 6,128 行，需 check-projection-sync 人工盯防
```
同样双写：`archive.py`（1,675/1,671）、`cleanup.py`（664/611）、`test_verify_workflow.py`（12,754/6,678）、`test_archive.py`（2,064/2,064）

**诊断**: e2e-test-project 是 target fixture（用于 external-project-validation harness），但它**整包复制** source 而非符号链接或生成时投影。每次 source 改动需手动同步 projection，靠 `check-projection-sync` 防止漂移——这是**反 DRY**的人工负担。

**影响**:
- 双重维护成本（每个 FIX 改两份）
- projection 漂移风险（check-projection-sync 是事后告警，非源头消除）
- fixture 体积膨胀（e2e-test-project 本身 ~28k 行 Python）

---

### F4 — 命令面冗余 🟡 P2（已知，AUDIT-120 已调研）

**实测证据**:
```
commands/governance.md                 620 行 (唯一真实入口)
commands/governance-init.md            904 行 (>> "推荐使用 /governance")
commands/governance-status.md          162 行 (>> "推荐使用 /governance")
commands/governance-verify.md          106 行 (>> "推荐使用 /governance")
commands/governance-gate.md            113 行 (>> "推荐使用 /governance")
commands/governance-review.md          109 行 (>> "推荐使用 /governance")
commands/governance-cleanup.md         132 行 (>> "推荐使用 /governance")
commands/governance-update.md           86 行 (>> "已弃用，使用 /governance")
```
8 文件 2,232 行，7 个是 `/governance` 的"快捷方式"重复入口。

**诊断**: AUDIT-120（DEC-082）已调研——三平台命令隐藏能力不一致（Claude 支持 `user-invocable: false`；zcode/Codex 无插件侧隐藏机制），当前决策不改命令面。这是**已知平台能力缺口**，非本项目可独立解决的 bug。

**影响**: 文档维护冗余，但不阻塞功能。作为已知债登记，等待上游能力补齐。

---

### F5 — 自演进遗留物堆积 🟠 P1

**实测证据**:

| 文件 | 性质 | 来源 |
| --- | --- | --- |
| `_fix_030_reconstruct.py` (90 行, 根目录) | 一次性重构脚本残留 | FIX-030（2026-05-04，已完成多月） |
| `nul` (189 字节, 根目录) | Windows `nul` 设备误创建 | 内容为某次 `dir /b ... > nul` 命令在 bash 下被当成普通文件写入；内容是错误重定向的 stderr |
| `docs/release/` (105 个文件) | 每个版本一堆 checklist/feature-flags/rollback-plan | 0.34.0~0.56.1 累积 |

**诊断**: 这是**当前问题的直接物证**——"自演进方式"导致一次性脚本、误创建文件、历史发布文档**从未被清理**。工作流有 `archive.py`（治理数据归档）和 `cleanup.py`（manifest 外残留清理），但 cleanup scope 只看 manifest 声明的产物，**不看根目录游离脚本和历史发布文档膨胀**。

**影响**:
- 仓库根污染（新用户/CI clone 后看到 `_fix_030_reconstruct.py` 会困惑）
- 历史发布文档无归档机制，`docs/release/` 只增不减
- 清理看护盲区：cleanup.py 不知道"根目录的一次性脚本算残留"

---

### F6 — 架构腐化看护缺口（根因）🔴 P0

**实测证据（这是用户核心痛点的铁证）**:

当前工作流的看护体系（28 个 check + SELF-CHECK + 3 层 hook）全部是**结构/事后/自觉型**约束（AUDIT-117 已证实 0 个事前/前提验证型）。具体到架构健康，**没有任何 check 守护以下维度**:

| 维度 | 当前是否有 check | 后果 |
| --- | --- | --- |
| 模块大小阈值（如单文件 > N 行告警） | ❌ 无 | verify_workflow.py 从合理大小膨胀到 20,294 行，**触发零告警** |
| 循环依赖检测 | ❌ 无 | 无机制发现 import 循环 |
| 重复代码检测 | ❌ 无 | source/projection 双写靠人工 |
| 函数复杂度/圈复杂度 | ❌ 无 | 439 个函数无复杂度门禁 |
| 技术债登记/跟踪 | ❌ 无 | F1~F5 从未被任何机制发现或登记 |
| 依赖图健康度 | ❌ 无 | 无依赖分析 |
| 测试覆盖率门禁 | ❌ 无 | 无 coverage 阈值 |

**铁证链**: `verify_workflow.py` 能膨胀到 20,294 行而工作流**毫无察觉**——这本身证明了看护盲区。工作流能看护"证据完整/Gate 一致/版本声明/no-overclaim"，但**完全不看护"代码是否还在可维护状态"**。

**诊断**: 这是**系统性缺陷**，不是个案。工作流把"治理"定义为"流程合规看护"，遗漏了"工程资产健康度看护"。对于声称是"AI coding delivery trust layer"的产品，无法看护自身代码健康，是**可信度根部的裂痕**。

**影响**:
- 问题持续累积：F1~F5 都是在没有告警的情况下悄悄长出来的
- 外部项目采用本工作流后，**同样的腐化会发生在宿主项目**——工作流给不出架构预警
- 1.0.0 若不补齐，"production-ready"标签建立在流程完整而非工程健康之上（呼应已关闭的 RISK-034 精神）

---

## 2. AI 项目特殊性审视

本项目既是"软件"，又是"被 AI agent 消费的治理产品"。从 AI 项目特殊性角度，额外发现:

### AI-1 — LLM 可读性反向约束缺失
2 万行单文件**超过任何 LLM 的有效 context window**。agent 修改 verify_workflow.py 时无法一次性加载全貌，只能靠 grep 片段拼凑理解——**这直接降低了工作流自身的 AI 可维护性**。现代 AI 项目应有"单文件可被 LLM 整体理解"的隐性约束，当前完全缺失。

### AI-2 — 自演进（dogfood）盲区
项目用自己管自己，但"自己"只被当作**治理流程的样例**，没有被当作**工程质量的被看护对象**。dogfood 只验证了"流程能跑通"，没验证"流程能发现代码腐化"。这是 dogfood 的**深度不足**。

### AI-3 — 演进路径无技术债缓冲
28 个版本（0.34.0→0.56.1）几乎都是**功能增量**（新 check/新命令/新 pack），**没有一个版本是"偿还技术债"**。长期纯增量演进必然导致腐化累积——这是自演进模式的系统性风险。

---

## 3. 重构路线图（分版本规划）

基于 DEC-083 三项决策（全项目深度审视 / 独立版本承载 ArchGuard / 渐进式按 check 域拆分）。

### 版本规划原则
1. **不破坏 54 个 CLI 命令契约**（外部项目和 CI 依赖命令名/参数）
2. **渐进式**：每个版本只拆一个域，可独立验证、可回滚
3. **ArchGuard 先于大规模拆分**：先建立看护能力，再用它守护拆分质量
4. **技术债版本与功能版本分离**：避免混入新功能

### 路线图

#### 0.57.0 — 架构审视归档 + 遗留物清理（本审计承载版本）
- **范围**: 纯文档 + 治理记录 + 根目录垃圾清理，不改 verify_workflow.py
- **交付**:
  - 本 ARCH-AUDIT 文档（docs/requirements/architecture-degradation-audit-0.57.0.md）
  - 清理 `_fix_030_reconstruct.py` + `nul`（F5 闭环示范）
  - AUDIT-121 / RISK-039 / DEC-083 入账
  - 建立技术债登记机制（technical-debt-ledger）
- **不包含**: verify_workflow.py 拆分（留给 0.58.0+）

#### 0.58.0 — ArchGuard 看护能力（独立产品能力版本）
- **范围**: 新增架构健康度 check 体系，作为可复用于其他大型项目的产品能力
- **交付**:
  - `check-architecture-health`：模块大小阈值（可配置，默认单 .py 文件 > 2000 行 WARN、> 5000 行 ERROR）
  - `check-duplicate-code`：source/projection 重复检测（基于 hash/AST）
  - `check-technical-debt`：扫描根目录游离脚本、未归档历史文档
  - `check-complexity`：函数圈复杂度阈值（可选，AST 分析）
  - `core/architecture-health.json`：声明式架构健康预算（类似 quality-budget）
- **边界**: ArchGuard 是诊断型 check（WARN/ERROR 告警），不自动重构；阈值保守，默认不阻断现有 release gate

#### 0.59.0~0.6x.0 — verify_workflow.py 渐进式按域拆分
按功能域分版本拆分（每个版本拆 1~2 个域，ArchGuard 守护每步质量）:
- **0.59.0**: 抽出 `manifest` 域 → `infra/checks/manifest.py`（check-manifest-consistency + 相关常量/函数）
- **0.60.0**: 抽出 `release` 域 → `infra/checks/release.py`
- **0.61.0**: 抽出 `governance` 域（check-governance 主入口）→ `infra/checks/governance.py`
- **0.62.0**: 抽出 `agent` 域 + `capability` 域
- **0.63.0**: 抽出 `evidence/risk/review` 域
- **0.64.0**: 抽出 `commit/projection/version` 域
- **最终**: verify_workflow.py 退化为 < 500 行的薄入口（argparse dispatch + 委托调用），各域独立模块 + 独立测试文件

#### 0.6x.0 — 现代工程基础设施补齐
- 引入 `pyproject.toml`（PEP 517/518）+ `ruff` lint/format + `mypy` 渐进类型
- 测试按域拆分：`infra/tests/checks/test_manifest.py` / `test_release.py` / ...
- CI 增加 lint + type 门禁
- source/projection 改为生成时投影（消除 F3 双写）

---

## 4. 风险与边界声明

### 本审计文档的边界（no-overclaim）
1. **本审计只诊断不修复**——不修改 verify_workflow.py、不拆分任何模块、不引入 lint
2. **版本规划是路线图不是承诺**——每个版本的实际范围在启动该版本时再细化（遵循版本规划纪律）
3. **ArchGuard 阈值是推测性建议**【推测】——具体阈值需在 0.58.0 实现时基于真实数据校准
4. **本审计不关闭 RISK-036/RISK-037**，不声明 official/marketplace approval、external validation full PASS、Codex Desktop lifecycle PASS 或 1.0.0 readiness
5. **拆分顺序是建议非最优解**【推测】——实际拆分可能根据依赖关系调整顺序

### 新增风险（同步登记到 risk-log）
- **RISK-039**: 架构腐化看护缺口（F6 根因）——详见 risk-log

### 不改变的事项
- RISK-036/RISK-037 继续打开
- 1.0.0 仍 blocked
- 当前 0.56.1 版本边界不变
- AUDIT-120（命令面收敛）结论不变——平台能力缺口，非本项目可解

---

## 5. 证据索引

- F1 证据: `wc -l skills/software-project-governance/infra/verify_workflow.py` → 20294；`grep -cE "^def |^class "` → 439；`grep -cE "subparsers.add_parser"` → 54
- F2 证据: `ls pyproject.toml ruff.toml .flake8 mypy.ini` → 全部 not found；`tests/test_product_code.py` 107 行
- F3 证据: `diff -q` source vs projection → DIFFER；行数差异 6128
- F4 证据: `head -3 commands/*.md` → 7 个文件均含"推荐使用 /governance"
- F5 证据: `ls -la nul _fix_030_reconstruct.py`；`cat nul` → stderr 内容；`docs/release/` 105 文件
- F6 证据: AUDIT-117（0 个事前 check）；verify_workflow.py 20294 行零告警事实

---

*本文档为 AUDIT-121 归档产物。后续版本（0.58.0 ArchGuard、0.59.0+ 拆分）启动时，以其为依据。*
