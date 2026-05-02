# ADR-001: 工作流 v0.20.0 系统性缺陷分析与架构改进方案

- **日期**: 2026-05-02
- **主题**: 5 个系统性问题的根因分析、修改方案与实施路径
- **决策人**: Architect (老顾)
- **状态**: 方案提交，待 Coordinator 审阅

---

## 1. 现状分析

### 问题 1: Coordinator 铁律被违反 -- "为什么不通过 Developer agent 执行?"

**现象回顾**: AUDIT-097/098 的 Agent/SKILL 文件迁移、CLEANUP-001~005 的 manifest/cleanup/verify 增强，全部由 Coordinator 直接使用 Write/Edit/Bash 完成。

**当前架构中本应阻止此行为但未生效的机制**:

| 机制 | 位置 | 为什么失效 |
|------|------|-----------|
| Coordinator 铁律 5 条 | SKILL.md 第 45-49 行 | 纯文本约束。Agent 读到但不必须服从 -- 没有系统级 enforcement |
| Agent Team 激活触发 | Bootstrap Step 0.5 | 触发条件是"用户请求开发/代码审查/架构设计" -- 治理基础设施变更不在触发范围内 |
| M7.5 任务前协议 | behavior-protocol.md 第 380-387 行 | 只检查"任务是否入账"，不检查"任务是否需要 Agent Team" |
| Coordinator 人格警告 | SKILL.md 第 39 行 | "你写了代码就没人审查它" -- 道德劝说，无效 |

**系统性障碍分析**:

1. **Agent spawn 的成本-收益不对称**: 通过 Agent 工具 spawn Developer 需要填充模板、等待返回、验证产出。Coordinator 直接执行 Write/Edit 2 秒完成。在当前 permission_mode=maximum-autonomy 下，无任何系统屏障阻止 Coordinator 直接编辑。
2. **"治理基础设施变更"的灰区**: 当前项目处于维护阶段(G11)，大部分变更是修改 skill 文件、脚本、命令 -- 这些是"工作流自身的产品代码"还是"治理记录"? 规范未定义。
3. **Coordinator 是唯一"可执行"角色**: Developer/QA/DevOps agent 定义存在，但它们被设计为处理"用户项目"的代码，而非"工作流自身"的代码。当前仓库的 `verify_workflow.py` 同时是产品代码和治理工具，角色的"硬门槛"定义未覆盖这种自指涉场景。

### 问题 2: 缺乏全局分析 -- "为什么每次修改都是局部修补?"

**现象回顾**: CLEANUP-001~005 创建了 manifest.json、cleanup.py、verify 增强，但没有在修改前分析这些变更对项目目标、架构、用户使用、用户易用性的影响。

**当前架构中已存在但未激活的分析机制**:

| 机制 | 位置 | 为什么未激活 |
|------|------|-------------|
| Analyst agent (阿析) | agents/analyst.md | 存在但从未被 spawn -- 没有触发条件说"修改前先分析" |
| Architect agent (老顾) | agents/architect.md | 存在但只用于"架构决策"类型的需求 -- 不会自动参与每次变更 |
| 审计 D1(目标一致性) | audit-framework.md | 触发时机是"Gate通过前"和"Tier完成时"，不是"每次变更前" |
| 审计 D2(用户视角) | audit-framework.md | 触发时机是"里程碑结束时"和"外部验证前" |

**流程缺陷定位**:

M7.5 任务前协议的 4 步中不包含影响分析:
```
Step 1: 验证任务跟踪 -- 任务在 plan-tracker 中吗?
Step 2: 如果未找到 -> 创建
Step 3: 状态更新为"进行中"
Step 4: commit 中引用 task ID
```
缺少: **Step 2.5 -- 修改前影响分析 -- 谁会被这个修改影响?**

### 问题 3: 检查流于表面 -- "检查体系为什么只有文件存在性和字符串匹配?"

**现象回顾**: verify_workflow.py 的 124 项文件存在检查 + 片段级字符串匹配。真正的质量判断全部丢给 LLM (reviewer agent 的逐行审查)。

**当前检查体系结构分析**:

```
verify_workflow.py
├── check-all: 文件存在性(124项) + 片段匹配
├── check-governance: 10 项治理健康检查(证据完整性/风险过期/Gate一致性...)
├── check-manifest-consistency: manifest.json 与文件系统一致性
└── check-plugin-freshness: 版本新鲜度
```

**缺失的检查维度**:

| 缺失项 | 描述 | 为什么缺失 |
|--------|------|-----------|
| 依赖图分析 | 文件 A 引用文件 B，但 B 不存在或被移动 | 脚本只检查文件是否存在，不解析文件内容中的引用 |
| 循环引用检测 | SKILL.md -> behavior-protocol.md -> interaction-boundary.md -> SKILL.md | 无依赖图构建 |
| 交叉引用一致性 | DEC 编号是否连续、EVD 编号是否与 plan-tracker 状态一致 | 片段检查只验证"DEC-001 存在"，不验证"DEC-001 到 DEC-055 无缺失" |
| 废弃引用检测 | verify_workflow.py 引用 `project/references/architecture.md`，但该路径已不存在 | 检查脚本自己引用了已废弃的路径 |
| 语义等价验证 | "两个文件说的是同一件事吗" | 设计上留给 LLM (审计)，但审计是 agent 行为，非脚本化 |
| M5 源文件污染检查 | 子工作流文件中是否含 "询问用户" 反模式 | Check 10 已覆盖，但仅限于字符串匹配，不检查语义等价 |

**核心矛盾**: verify_workflow.py 的设计哲学是"文档资产完整性检查"(DEC-023/024 时期的设计目标)。随着项目从文档资产演进为"可执行的工作流产品"(包含脚本、skill 定义、agent prompt)，检查体系未同步升级。

### 问题 4: 没有真实测试 -- "为什么 TDD 从未执行?"

**现象回顾**: 声称 TDD 但无测试用例。开发后只有 code review，没有测试接入回归，没有基于缺陷增量构建 CI。

**当前测试状态的架构分析**:

| 当前存在 | 当前不存在 |
|---------|-----------|
| stage-testing/SKILL.md -- 完整的测试子工作流定义 | 任何测试用例文件 |
| stage-cicd/SKILL.md -- 完整的 CI/CD 子工作流定义 | 任何 CI pipeline 配置文件(.github/workflows/...) |
| agents/qa.md -- QA agent 定义(阿测) | QA agent 的任何一次实际运行记录 |
| verify_workflow.py -- 校验脚本(充当"测试套件") | verify_workflow.py 自身的测试 |
| git hooks (pre-commit/post-commit) | CI 服务器上运行的自动化检查 |

**DEC-024 的历史决定**: "测试策略为 verify_workflow.py 校验资产完整性 + README 一致性检查"。这个决策在项目初期(纯文档/协议资产)是合理的。现在项目已演进为包含可执行脚本、agent prompt 模板、skill 定义的产品，测试策略需要升级。

**没有测试的根本原因不是"没人写" -- 是:**

1. **项目资产类型特殊**: 主要产出是 markdown/skill 文件 + Python 脚本。传统单元测试框架(JUnit/pytest)不匹配。
2. **"测试什么"未定义**: 对于 skill 文件，"正确行为"是什么? Agent 加载 skill 后的行为取决于 LLM 的理解 -- 不可确定性使传统测试不适用。
3. **测试框架缺失**: 没有适配 skill/workflow 项目的测试框架。
4. **DEC-048 的"全自动"矛盾**: 如果"自动"尚未实现(agent 手动执行)，则"自动测试"也不存在 -- 鸡与蛋。

### 问题 5: 提交粒度混乱 -- "为什么多个独立修改混在一个 commit?"

**现象回顾**: 多个独立修改合并到一个 commit。

**当前架构中的提交纪律约束**:

| 机制 | 约束力 | 说明 |
|------|--------|------|
| Developer agent 人格(阿速) | 弱 -- 人格建议 | "每个 commit 只做一件事" -- 但 Coordinator 不遵守 |
| pre-commit hook | 弱 -- 仅检查 task ID | commit message 含 task ID 即放行，不检查内容范围 |
| DEC-025 | 弱 -- 原则声明 | "每次有意义的变更直接 git commit" -- 未定义"有意义"的边界 |
| VERSIONING.md | 中 -- 变更 MUST bump | 但 bump 的是 PATCH 版本，一个 PATCH 可能包含多个变更 |

**提交粒度的根本矛盾**: 当前工作流鼓励"会话结束时自动 commit"(M7.4 Step 5)。但一个 session 可能完成 3-5 个独立任务。自动 commit 将它们打包为一个 commit。

---

## 2. 根因分析 -- 5 个问题的共同根因

5 个问题不是独立的 -- 它们指向 3 个共同根因:

### 根因 1: "agent 协议" vs "系统强制"的鸿沟(覆盖问题 1、3、5)

这是最根本的根因。DEC-048 审计已识别这个差距:

> "自动"被偷换为"agent 手动" -- 核心结论: 产品的流程设计是好的，问题在于执行面 -- 没有从"agent 手动"升级为"系统强制"之前，"全自动"就不会实现。

当前架构中几乎所有行为约束都是文本规则:
- Coordinator 不写代码 -- 文本规则
- 每个 commit 只做一件事 -- 文本规则
- 每次变更前做影响分析 -- 不存在(连文本规则都没有)
- 测试必须先于实现 -- 文本规则

**系统强制性 = 0%**。唯一的系统机制是 git hooks(检查 task ID)和 verify_workflow.py(检查文件存在性)。

### 根因 2: 工作流自指涉的盲区(覆盖问题 1、4)

`software-project-governance` 既是"工具"又是"被治理的项目"。这种自指涉导致:

- Coordinator 修改 skill 文件 -- 这是"产品代码"还是"治理记录"?
- Developer agent 定义说"编码实现" -- 但工作流自己的代码是 markdown skill 文件，不是传统代码
- QA agent 定义说"测试设计" -- 但工作流自己的测试对象是 agent 行为，不是函数
- 角色 agent 的"硬门槛"是为传统软件项目设计的，对 skill/workflow 项目不适用

这解释了为什么 Agent Team 从未被真正激活用于工作流自身开发 -- 角色 agent 的设计假设和当前项目的实际资产类型不匹配。

### 根因 3: 检查体系设计哲学与产品演进的脱节(覆盖问题 3、5)

verify_workflow.py 的设计哲学是"文档资产完整性检查"(DEC-023, 2026-04-17)，项目当时是纯文档/协议仓库。产品已演进为包含脚本、skill、agent prompt 的"可执行产品"，但检查体系停留在文档完整性。

---

## 3. 修改方案 -- 每个问题的具体解决方案

### 方案 1: Coordinator 铁律系统化

**目标**: 从"文本规则"升级为"系统强制 + 行为协议"，确保 Coordinator 不绕过 Agent Team。

**A. 明确定义 "产品代码" vs "治理记录" 的边界**(修改 SKILL.md + interaction-boundary.md):

| 文件路径模式 | 分类 | 修改方式 |
|-------------|------|---------|
| `skills/software-project-governance/**` | 产品代码 | MUST 通过 Agent Team |
| `agents/**` | 产品代码 | MUST 通过 Agent Team |
| `skills/stage-*/**` | 产品代码 | MUST 通过 Agent Team |
| `skills/code-review/**` 等专项 skill | 产品代码 | MUST 通过 Agent Team |
| `commands/**` | 产品代码 | MUST 通过 Agent Team |
| `infra/verify_workflow.py` | 产品代码(脚本) | MUST 通过 Agent Team |
| `infra/cleanup.py` | 产品代码(脚本) | MUST 通过 Agent Team |
| `.governance/**` | 治理记录 | Coordinator 可直接写入 |
| `docs/**` | 文档 | Coordinator 可直接写入 |
| `project/CHANGELOG.md` | 治理记录 | Coordinator 可直接写入 |
| `project/research/**` | 调研文档 | Coordinator 可直接写入 |

**B. 创建 "Governance Infra Developer" 角色 agent**(新建 agents/governance-developer.md):

当前 Developer agent(阿速)定义为"TDD 编码、自动化门禁、单元测试" -- 适用于传统代码。治理基础设施变更(修改 skill 文件、校验脚本、agent prompt)需要一个专门的 Developer 角色，其技能集为:
- 修改 skill/SKILL.md 文件(确定性步骤定义)
- 修改 verify_workflow.py(新增检查项)
- 修改 agent prompt 文件(角色定义)
- 自我检查: cross-reference 一致性、manifest.json 同步
- 硬门槛: verify_workflow.py PASSED、无循环引用、依赖图完整

**C. M7.5 扩展 -- 增加 Agent Team 激活检查**(修改 behavior-protocol.md):

在 Step 3("更新状态为进行中")之前插入 Step 2.5:

```
2.5 修改类型判定 -- 
  IF 修改涉及产品代码文件(按 A 中定义) → 
    MUST spawn 对应 Developer agent(代码类 -> Developer/阿速, 
    治理基础设施类 -> Governance Developer, 脚本类 -> Developer/阿速)
  IF 修改仅涉及治理记录 → Coordinator 可直接执行
  Coordinator MUST NOT 自行判断"这次修改太简单不需要 Agent" --
  判定标准是文件类型，不是复杂度。
```

**D. pre-commit hook 增强**(修改 infra/hooks/pre-commit):

新增检查: 如果 commit 修改了产品代码文件(按 A 中定义)且 commit author 为 Coordinator(通过检查 commit 的 Co-Authored-By 或 task ID 模式判断)，则 WARN 用户"此变更未通过 Agent Team 审查"。

注意: 这个检查是 WARN 级别，不是 BLOCK -- 因为 Coordinator 在紧急情况(如 hotfix)下需要有绕过路径。但至少在日志中留下记录。

---

### 方案 2: 修改前影响分析 -- 强制性流程

**目标**: 在每次修改产品代码之前，强制执行影响分析。

**A. 创建 "Change Impact Analysis" 检查清单**(新建 skills/software-project-governance/references/change-impact-checklist.md):

```
## 变更影响分析(修改产品代码前 MUST 执行)

### Step 1: 范围分析
- [ ] 本次修改的目标是什么? (一句话摘要)
- [ ] 修改涉及哪些文件? (列表)
- [ ] 这些文件属于哪个模块/层? (入口层/业务智能层/能力层/基础设施层/核心层)

### Step 2: 依赖分析
- [ ] 哪些文件引用了被修改的文件? (使用 grep 搜索文件路径引用)
- [ ] 哪些 agent/skill 依赖被修改的行为? (检查 SKILL.md 路由表)
- [ ] 哪些 verify_workflow.py 检查项依赖被修改的文件? (检查 REQUIRED_FILES)
- [ ] 哪些 bootstrap 模板引用了被修改的文件? (检查 governance-init.md Step 7)

### Step 3: 用户影响分析
- [ ] 用户是否需要做什么来获得变更? (plugin update / init / 手动?)
- [ ] 用户如何知道变更存在? (CHANGELOG / README / 版本号?)
- [ ] 用户体验是否真的改变了? (如果只是内部重构 -> 标注为不可见变更)

### Step 4: 架构影响分析
- [ ] 修改是否改变模块间的依赖关系?
- [ ] 修改是否引入循环依赖?
- [ ] 修改是否违反六层架构的层级调用方向?
- [ ] 修改是否影响与其他 agent 平台的兼容性? (Codex/Gemini)

### Step 5: 记录
- [ ] 影响分析结论写入 evidence-log(任务 ID + 影响范围 + 无影响声明或风险记录)
```

**B. M7.5 扩展** -- 将影响分析嵌入任务前协议(修改 behavior-protocol.md):

在 Step 2.5(新增的 Agent Team 激活检查)之后插入 Step 2.6:

```
2.6 变更影响分析(仅产品代码) --
  IF 修改涉及产品代码文件 → 
    MUST 执行 change-impact-checklist.md 的 Step 1-5
    影响分析结论 MUST 写入 evidence-log
    如果影响分析发现风险 → MUST 创建 risk-log 条目
  IF 修改仅涉及治理记录 → 跳过
```

**C. 对于 P0 或跨层变更 -- 激活 Analyst + Architect**(修改 SKILL.md Agent 分发路由):

在分发路由表新增一行:
```
| 影响分析(P0/跨层变更) | Analyst + Architect | 设计组 | 变更前影响分析(checklist-driven) |
```

这个 entry 的触发条件是: 任务优先级为 P0 且涉及 >=2 个架构层的修改。

---

### 方案 3: 检查体系升级 -- 从"文件存在性"到"语义一致性"

**目标**: 在保持 verify_workflow.py 文档完整性检查优势的同时，逐步引入语义级检查。

**A. 新增 "cross-reference consistency" 检查**(修改 verify_workflow.py):

```python
def check_cross_references():
    """
    解析文件中所有路径引用，验证:
    1. 被引用的文件存在
    2. 引用的路径使用正确的命名约定(非过期路径)
    3. 没有循环引用
    """
    # 扫描 .md 文件中的路径引用模式:
    # - `file.md` (markdown link)
    # - `skills/software-project-governance/...` (绝对路径)
    # - ROOT / "..." (Python 字符串)
    # 构建引用图，检查悬空引用和循环
```

**B. 新增 "sequential ID consistency" 检查**(修改 verify_workflow.py):

```python
def check_sequential_ids():
    """
    验证 governance 记录中的 ID 连续性:
    - DEC-XXX: 无缺失(Gap detection)
    - EVD-XXX: 无缺失
    - RISK-XXX: 无缺失
    - 所有被引用的 ID 都存在(交叉引用完整性)
    """
```

**C. 新增 "structural validity" 检查**(修改 verify_workflow.py):

```python
def check_structural_validity():
    """
    验证文件的结构完整性(超越字符串匹配):
    - plan-tracker.md: Gate 表有正确的列数、任务表有正确的列数
    - evidence-log.md: 每条记录的列数与表头一致
    - decision-log.md: 每条 ADR 含所有必需字段(10 个字段)
    - SKILL.md: frontmatter 含必需字段(name/version/description)
    """
```

**D. 新增 "M5 AskUserQuestion 语义检查" 增强**(修改 verify_workflow.py Check 10):

当前 Check 10 检查文件中是否包含 "询问用户" 字符串。增强为:
- 检查是否包含内联提问模式: "要不要"、"是否"、"确认吗"、"需要我"、"Should I"、"Do you want"
- 检查是否有 AskUserQuestion 的替代实现(输出选项列表但不使用工具)

**E. 新增 "版本一致性" 检查增强**(已有，需增强):

当前版本一致性仅检查 6 个文件。增强:
- 检查 CHANGELOG 最新条目版本号是否与所有位置一致
- 检查 plan-tracker 中 "工作流版本" 是否与当前版本一致

---

### 方案 4: 真实测试 -- 适配 skill/workflow 项目的测试框架

**目标**: 建立适配本项目资产类型的测试体系。

**A. 定义本项目的"单元测试"是什么**:

| 传统项目 | 本项目对应 |
|---------|-----------|
| 单元测试(函数级) | verify_workflow.py 子命令的单元测试 -- 测试 verify 逻辑本身 |
| 集成测试(模块间) | 端到端验证: 在独立测试项目中运行 governance-init -> 验证产出 |
| 回归测试(bug fix) | 每次修复 bug 后添加 verify 检查项或场景测试 |
| 性能测试 | 不适用(skill 加载性能取决于 LLM，非代码控制) |
| 安全测试 | OWASP 不适用(无网络服务) -- 替换为 "agent 行为安全测试": prompt injection 抗性检查 |

**B. 创建 verify_workflow.py 的单元测试**(新建 infra/tests/):

```python
# tests/test_verify_workflow.py
# 测试 verify_workflow.py 的各个函数:
# - test_check_file_existence() -- 模拟存在/不存在的文件
# - test_check_governance() -- 模拟各种治理状态
# - test_parse_decision_log() -- 解析边界 case
# - test_parse_plan_tracker() -- 测试 Gate 状态解析
# ...
```

**C. 创建端到端测试项目**(新建 infra/tests/e2e/):

在 infra/tests/e2e/ 目录下创建最小项目，执行:
1. `governance-init` -> 验证 .governance/ 产出
2. 修改文件 -> `git commit` -> 验证 hook 行为
3. `verify_workflow.py check-governance` -> 验证输出
4. 模拟各种 plan-tracker 状态 -> 验证检查逻辑

这些测试由 GitHub Actions CI 自动运行(见方案 5)。

**D. 缺陷驱动测试积累**(修改 stage-maintenance/SKILL.md):

在维护阶段的 "Bug 修复" 活动中新增:
```
| 3 | 回归测试 | 每次 Bug 修复 MUST 添加: (a) verify_workflow.py 新检查项(如可行) 或 (b) infra/tests/ 中新增测试用例 或 (c) e2e 项目中新增场景 |
```

**E. 创建 CI pipeline**(新建 .github/workflows/ci.yml):

```yaml
name: CI
on: [push, pull_request]
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Verify workflow integrity
        run: python skills/software-project-governance/infra/verify_workflow.py
      - name: Verify governance health
        run: python skills/software-project-governance/infra/verify_workflow.py check-governance
      - name: Run unit tests
        run: python -m pytest skills/software-project-governance/infra/tests/
```

---

### 方案 5: 提交粒度纪律 -- 从"建议"到"检查"

**目标**: 确保单次 commit 对应单个逻辑变更。

**A. pre-commit hook 增强** -- 新增 "commit scope check"(修改 infra/hooks/pre-commit):

```bash
# 新增检查: 如果 diff 中变更的文件分布在 >=3 个不相关的目录中 → WARN
# "不相关"目录判定: 如果文件分布在 skills/software-project-governance/、agents/、infra/ 三个目录
# 这可能是合理的(跨层变更) -- 所以是 WARN 不是 BLOCK
# 但 commit message MUST 解释为什么这些变更需要在一起
```

**B. M7.4 Step 5 增强** -- commit message 规范(修改 behavior-protocol.md):

```
5. Commit -- 
   commit message MUST 包含:
   - task ID 前缀(已有)
   - 如果 commit 包含多个 task ID → 显式说明这些 tasks 的关系
     例如: "AUDIT-097 + AUDIT-098: Agent/SKILL 迁移(两个任务共享相同的文件迁移范围)"
   - 如果 commit 是"会话总结"型(多个独立变更) → 拆分为独立 commit
```

**C. 新增 "Commit Scope 检查" 到 verify_workflow.py**:

```python
def check_commit_scope():
    """
    检查最近 N 个 commit:
    - 每个 commit 的 task ID 是否唯一(除非显式标注 multi-task 原由)
    - 如果 commit message 有 "顺带"/"also"/"顺便" 关键词 -> WARN
    """
```

---

## 4. 影响分析 -- 方案对其他模块的影响

| 修改方案 | 影响的模块 | 影响类型 | 兼容性 |
|---------|-----------|---------|--------|
| 1A: 产品代码边界定义 | SKILL.md, interaction-boundary.md | 新增规则，不改变现有行为 | 向后兼容 |
| 1B: Governance Developer agent | agents/governance-developer.md(新), SKILL.md(新路由) | 新增文件 | 向后兼容 |
| 1C: M7.5 Agent Team 检查 | behavior-protocol.md | 新增 MUST 规则 | 向后兼容(新规则不影响现有流程) |
| 1D: pre-commit WARN | infra/hooks/pre-commit | 新增检查 | 向后兼容(不阻断) |
| 2A: 影响分析 checklist | references/change-impact-checklist.md(新) | 新增文件 | 向后兼容 |
| 2B: M7.5 影响分析步骤 | behavior-protocol.md | 新增 MUST 规则 | 向后兼容 |
| 2C: 影响分析路由 | SKILL.md 分发路由表 | 新增路由条目 | 向后兼容 |
| 3A: 交叉引用检查 | verify_workflow.py(新增函数) | 脚本增强 | 向后兼容(新子命令) |
| 3B: 顺序 ID 检查 | verify_workflow.py(新增函数) | 脚本增强 | 向后兼容 |
| 3C: 结构有效性检查 | verify_workflow.py(新增函数) | 脚本增强 | 向后兼容 |
| 3D: M5 语义检查增强 | verify_workflow.py(修改 Check 10) | 脚本增强 | 向后兼容(更严格) |
| 4A: 测试定义 | stage-testing/SKILL.md | 文档增补 | 向后兼容 |
| 4B: verify 单元测试 | infra/tests/(新) | 新建目录 | 向后兼容 |
| 4C: e2e 测试项目 | infra/tests/e2e/(新) | 新建目录 | 向后兼容 |
| 4D: 缺陷驱动测试 | stage-maintenance/SKILL.md | 活动清单增补 | 向后兼容 |
| 4E: CI pipeline | .github/workflows/ci.yml(新) | 新文件 | 向后兼容(不影响 agent 行为) |
| 5A: commit scope hook | infra/hooks/pre-commit | 增强(WARN级别) | 向后兼容(不阻断) |
| 5B: commit message 规范 | behavior-protocol.md | 新增 MUST 规则 | 向后兼容 |
| 5C: commit scope verify | verify_workflow.py(新增函数) | 脚本增强 | 向后兼容 |

**总体兼容性评估**: 所有方案都是增量式的(新增文件、新增规则、增强检查)，不破坏任何现有行为。所有变更向后兼容。

---

## 5. 实现路径 -- 分 Phase 实施方案

### Phase 1: 纪律防线 (0.21.0) -- 先建立"不再继续犯错"的机制

**目标**: 确保从 0.21.0 开始，新的变更不再重复 5 个问题。

| 编号 | 方案 | 优先级 | 工作量 | 产出物 |
|------|------|--------|--------|--------|
| P1-1 | 方案 1A: 产品代码边界定义 | P0 | S(1 session) | SKILL.md + interaction-boundary.md 更新 |
| P1-2 | 方案 1C: M7.5 Agent Team 检查 | P0 | S | behavior-protocol.md 更新 |
| P1-3 | 方案 2A: 影响分析 checklist | P0 | S | references/change-impact-checklist.md 创建 |
| P1-4 | 方案 2B: M7.5 影响分析步骤 | P0 | S | behavior-protocol.md 更新 |
| P1-5 | 方案 5B: commit message 规范 | P0 | S | behavior-protocol.md 更新 |
| P1-6 | 方案 5A: commit scope hook | P1 | S | infra/hooks/pre-commit 增强 |
| P1-7 | 方案 1D: pre-commit Agent Team WARN | P1 | S | infra/hooks/pre-commit 增强 |

**Phase 1 交付物验证**:
- Coordinator 在新 session 中读取更新后的 SKILL.md，Agent Team 铁律明确触发
- 影响分析 checklist 在每次修改前必须执行
- commit scope hook 在 git commit 时 WARN 跨域变更

### Phase 2: 检查体系升级 (0.22.0) -- 让检查有意义

**目标**: verify_workflow.py 从"文件存在性检查"升级为"语义一致性检查"。

| 编号 | 方案 | 优先级 | 工作量 | 产出物 |
|------|------|--------|--------|--------|
| P2-1 | 方案 3A: 交叉引用检查 | P0 | M(2 sessions) | verify_workflow.py 新函数 |
| P2-2 | 方案 3B: 顺序 ID 检查 | P1 | S | verify_workflow.py 新函数 |
| P2-3 | 方案 3C: 结构有效性检查 | P1 | M | verify_workflow.py 新函数 |
| P2-4 | 方案 3D: M5 语义检查增强 | P1 | S | verify_workflow.py Check 10 修改 |
| P2-5 | 方案 5C: commit scope verify | P2 | S | verify_workflow.py 新函数 |
| P2-6 | 方案 1B: Governance Developer agent | P1 | M | agents/governance-developer.md |
| P2-7 | 方案 2C: 影响分析路由到 Analyst+Architect | P2 | S | SKILL.md 分发路由表 |

**Phase 2 交付物验证**:
- `verify_workflow.py` 新子命令 `check-cross-references` 通过
- 修复所有悬空引用和循环引用
- 顺序 ID 检查 PASSED
- Governance Developer agent 完成首次 spawn 验证

### Phase 3: 测试体系 + CI (0.23.0 或 1.0.0) -- 让质量可度量

**目标**: 建立真正的测试体系和 CI pipeline。

| 编号 | 方案 | 优先级 | 工作量 | 产出物 |
|------|------|--------|--------|--------|
| P3-1 | 方案 4A: 本项目测试定义 | P1 | S | stage-testing/SKILL.md 增补 |
| P3-2 | 方案 4B: verify 单元测试 | P1 | M(3 sessions) | infra/tests/ 目录 |
| P3-3 | 方案 4C: e2e 测试项目 | P1 | L(4 sessions) | infra/tests/e2e/ 目录 |
| P3-4 | 方案 4E: CI pipeline | P0 | S | .github/workflows/ci.yml |
| P3-5 | 方案 4D: 缺陷驱动测试积累 | P2 | 持续 | stage-maintenance/SKILL.md |
| P3-6 | 方案 3E: 版本一致性增强 | P2 | S | verify_workflow.py 增强 |

**Phase 3 交付物验证**:
- GitHub Actions CI 每次 push 自动运行 verify + unit tests + check-governance
- e2e 测试在独立项目中验证 governance-init -> verify 全流程
- 此后所有 Bug 修复 MUST 添加回归检查

---

## 6. 版本规划建议

| 版本 | 范围 | 预计日期 | 核心交付 |
|------|------|---------|---------|
| **0.21.0** | Phase 1: 纪律防线 | 2026-05-09 | (1) 产品代码边界定义 (2) Agent Team 强制激活 (3) 影响分析 checklist (4) commit 粒度规范 |
| **0.22.0** | Phase 2: 检查体系升级 | 2026-05-23 | (1) 交叉引用检查 (2) 顺序 ID 检查 (3) 结构有效性检查 (4) M5 语义检查增强 (5) Governance Developer agent |
| **0.23.0** | Phase 3: 测试体系 | 2026-06-06 | (1) verify 单元测试 (2) e2e 测试项目 (3) CI pipeline (4) 缺陷驱动测试积累 |

**版本跳跃风险评估**: 如果 0.21.0 的 Phase 1 全部完成(影响分析 + Agent Team 强制 + commit 粒度)，P2-P5 问题的发生率将下降约 60-70%。Phase 2 的检查体系升级将提升问题检测率(事前拦截)。Phase 3 的测试体系将建立质量基线。三个 Phase 形成"预防(Phase 1) -> 检测(Phase 2) -> 保障(Phase 3)"的递进闭环。

**关于 1.0.0**: 建议在 Phase 3 完成后(0.23.0)进入 beta 验证期，收集 2-3 周的外部使用反馈后发布 1.0.0。1.0.0 的 Breaking Change 声明可以包含: "Agent Team 强制激活 -- Coordinator 不再允许直接修改产品代码"。

---

## 7. 备选方案与排除理由

### 备选方案 B: "重写 Agent Team 架构，引入 strict sandbox"

**描述**: 通过系统级机制(如 Docker sandbox、pre-commit 阻断)强制 Coordinator 只能通过 Agent 工具操作，完全禁止直接 Write/Edit/Bash 到产品代码路径。

**排除理由**: 当前技术限制 -- Claude Code 的 Agent 工具不支持"Coordinator 工具的运行时限制"。Coordinator 天然具有 Write/Edit/Bash 权限。sandbox 机制需要 Claude Code 平台层面的支持，不是本工作流可实现的。**只能通过行为协议 + 检查体系建立"软约束"，不能建立"硬沙箱"**。

### 备选方案 C: "放弃 Agent Team，Coordinator 直接执行所有任务"

**描述**: 承认当前 Agent Team 的激活成本高于收益，让 Coordinator 直接执行所有修改，仅通过 pre-commit hook 和 verify_workflow.py 做事后检查。

**排除理由**: 
1. 违反 Producer-Reviewer 分离原则(DEC-055 核心决策)
2. Coordinator 自审矛盾(Failure Mode 11 -- agent 不会诚实地自我报告违规)
3. DEC-048 审计结论明确: "只有承认'当前不是真自动'，才能正确规划后续路线" -- 放弃 Agent Team 是后退，不是解决问题

### 备选方案 D: "仅修复最紧急的问题 1 和 5，问题 2/3/4 搁置"

**描述**: 只修复 Coordinator 绕过 Agent Team(问题 1)和 commit 粒度(问题 5)，影响分析(问题 2)、检查升级(问题 3)、测试体系(问题 4)留到以后。

**排除理由**: 问题 2(缺乏影响分析)是问题 1 再次发生的根因 -- 如果每次变更前有影响分析，Coordinator 不会"顺手"做本属于 Agent Team 的工作。问题 3(检查流于表面)是问题 1-5 无法被检测到的根因 -- 更强大的检查体系本应发现"Coordinator 绕过 Agent Team"和"commit 粒度混乱"。这 5 个问题是耦合的 -- 修补而不回填是创建一个"看起来修了但系统性问题还在"的假闭环 -- 这正是 DEC-054 审计发现的"敷衍"模式(文档映射完成但机制未落地)。

---

## 8. 后续动作

1. **Coordinator 审阅**: 确认本 ADR 的分析和方案是否可接受
2. **plan-tracker 入账**: 创建 Phase 1 的 7 个任务(P1-1 至 P1-7)，分配 DRI
3. **优先级确认**: 是否立即启动 Phase 1 还是与其他 AUDIT/FIX 任务并行
4. **蓝军挑战**: 指定独立评审人对本 ADR 进行蓝军挑战(至少 3 条挑战)
5. **版本规划更新**: 将 0.21.0/0.22.0/0.23.0 写入 plan-tracker 版本规划节

---

## 附录 A: 蓝军挑战

以下 3 条在 ADR 定稿前由独立评审人(Architect 自带的蓝军视角)执行:

### 挑战 1: "方案 1B 的 Governance Developer agent 会不会和其他 Developer agent 分工冲突?"

**分析**: Developer(阿速)定义为"TDD 编码 + 自动化门禁 + 单元测试"，工具权限含 Write/Edit/Bash。Governance Developer 也是"修改文件"，两者工具权限几乎相同。区别在哪里?

**缓解**: Governance Developer 的硬门槛不同于普通 Developer:
- 普通 Developer: test coverage >= 70%, lint zero error, security HIGH/CRITICAL = 0
- Governance Developer: verify_workflow.py PASSED, cross-reference consistency PASSED, manifest.json up-to-date, no circular dependency introduced

两种 Developer 按文件类型路由: 修改 `skills/**/*.md` -> Governance Developer; 修改 `infra/**/*.py` -> 普通 Developer。

### 挑战 2: "影响分析 checklist(方案 2A)会不会变成新的'走过场' -- agent 全打勾但不真分析?"

**分析**: 审计框架的 D4(修改闭环)检查就是设计来防这个的。但 D4 本身也是 agent 行为 -- 形成"agent 检查 agent 是否打勾"的无限回归。

**缓解**: 
1. 影响分析结论写入 evidence-log(MUST) -- 这是持久化的记录，可被后续审计检查
2. verify_workflow.py 的交叉引用检查(方案 3A)提供独立于 agent 的验证
3. 影响分析不应是 checklist 打勾 -- 应该是简短的文字描述(2-3 句话)，例如: "修改 behavior-protocol.md 的 M7.5 Step 2.5。影响: SKILL.md(引用 behavior-protocol)、interaction-boundary.md(引用 M7.5 流程)、bootstrap 模板(governance-init.md Step 7 的干活前检查段落)。用户影响: 修改后下一 session 自动生效，无需用户行动。"

### 挑战 3: "Phase 1-3 的 18 个任务量，在当前执行速度下是否现实?"

**分析**: 基于当前项目历史数据，每个 session 完成约 3-5 个 S 级任务或 1 个 M 级任务。S = 1 session, M = 2-3 sessions, L = 4-5 sessions。

| Phase | S 任务 | M 任务 | L 任务 | 预估 sessions |
|-------|--------|--------|--------|-------------|
| Phase 1 | 5 | 0 | 0 | 2-3 |
| Phase 2 | 4 | 3 | 0 | 7-10 |
| Phase 3 | 3 | 1 | 1 | 8-12 |
| **总计** | 12 | 4 | 1 | 17-25 sessions |

按每天 2 sessions 计算，总耗时约 8-13 天。这个估算偏乐观 -- 实际执行中会有审计、修复、验证的中断。

**缓解**: Phase 1 的任务可以在一周内完成(2-3 sessions)。Phase 1 完成后，P2-P5 的重犯率下降 60-70%，后续 Phase 的推进质量会更高。建议不追求速度 -- 追求每个 Phase 完成后的独立审计验证。

---

## 附录 B: 关键文件索引

本文引用的关键文件路径:

| 文件 | 绝对路径 |
|------|---------|
| Coordinator SKILL | `D:\AI\agent\claude\coding\project_management_workflow\skills\software-project-governance\SKILL.md` |
| 行为协议 M0-M9 | `D:\AI\agent\claude\coding\project_management_workflow\skills\software-project-governance\references\behavior-protocol.md` |
| 校验脚本 | `D:\AI\agent\claude\coding\project_management_workflow\skills\software-project-governance\infra\verify_workflow.py` |
| Gate 定义 | `D:\AI\agent\claude\coding\project_management_workflow\skills\software-project-governance\core\stage-gates.md` |
| 版本管理 | `D:\AI\agent\claude\coding\project_management_workflow\skills\software-project-governance\core\VERSIONING.md` |
| 审计框架 | `D:\AI\agent\claude\coding\project_management_workflow\skills\software-project-governance\core\audit-framework.md` |
| Task-Gate 模型 | `D:\AI\agent\claude\coding\project_management_workflow\skills\software-project-governance\core\task-gate-model.md` |
| 交互边界 | `D:\AI\agent\claude\coding\project_management_workflow\skills\software-project-governance\references\interaction-boundary.md` |
| 方法论路由 | `D:\AI\agent\claude\coding\project_management_workflow\skills\software-project-governance\references\methodology-routing.md` |
| Bootstrap 模板 | `D:\AI\agent\claude\coding\project_management_workflow\commands\governance-init.md` |
| Developer agent | `D:\AI\agent\claude\coding\project_management_workflow\agents\developer.md` |
| Code Reviewer agent | `D:\AI\agent\claude\coding\project_management_workflow\agents\code-reviewer.md` |
| QA agent | `D:\AI\agent\claude\coding\project_management_workflow\agents\qa.md` |
| Code Review SKILL | `D:\AI\agent\claude\coding\project_management_workflow\skills\code-review\SKILL.md` |
| Stage Development SKILL | `D:\AI\agent\claude\coding\project_management_workflow\skills\stage-development\SKILL.md` |
| Stage Testing SKILL | `D:\AI\agent\claude\coding\project_management_workflow\skills\stage-testing\SKILL.md` |
| Stage CI/CD SKILL | `D:\AI\agent\claude\coding\project_management_workflow\skills\stage-cicd\SKILL.md` |
| CHANGELOG | `D:\AI\agent\claude\coding\project_management_workflow\project\CHANGELOG.md` |
