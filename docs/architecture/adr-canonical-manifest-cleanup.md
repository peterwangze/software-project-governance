# ADR: 声明式清理机制——基于 Canonical Manifest 的结构 Diff 清理

| 字段 | 内容 |
|------|------|
| **ADR 编号** | ADR-001 |
| **日期** | 2026-05-02 |
| **状态** | 提案（待 Coordinator 决策） |
| **决策人** | Architect（老顾）→ 待 Coordinator 确认 |
| **关联任务** | 待创建 |
| **关联 ADR** | 无前序 ADR |

---

## 1. 背景

### 1.1 问题陈述

`governance-cleanup` 命令（`commands/governance-cleanup.md`）负责在用户升级插件后清理残留的旧版本文件。当前实现是**硬编码的"已知冗余列表"**——每个版本升级后手动追加要删除的路径。例如：

- v0.12.0 清理列表：手动列出 15 个根目录冗余文件 + 5 个 references 冗余文件
- v0.18.0 清理列表：手动追加 25 个 SKILL stub 目录

**每次目录结构调整都需要手动适配清理命令。** 例如 AUDIT-097/098 把 Agent 从 `skills/software-project-governance/agents/`（nested）迁到 `agents/`（flat），把 SKILL 从 `skills/software-project-governance/skills/`（nested）迁到 `skills/<name>/SKILL.md`（flat）。这些调整完成后，又需要手动更新 cleanup 列表。

CLAUDE.md bootstrap 中的自动清理逻辑也只覆盖了 SKILL stub 检测（内容检测 `plugin 发现 stub`），不是通用的结构 diff。

### 1.2 根因分析

三个结构性缺陷：

1. **没有 canonical manifest**。没有一份声明"当前版本应该有哪些文件/目录"的权威清单。`skills/software-project-governance/core/manifest.md` 描述了组成结构，但是人类可读的散文格式，不是可机器 diff 的数据格式。

2. **清理逻辑是"已知冗余"而非"结构 diff"**。维护者需要记住"上个版本有 X，这个版本删了 X，所以 X 是冗余"。随着版本累积，这个知识只存在于维护者的脑子里。

3. **`verify_workflow.py` 的 `REQUIRED_FILES` 是正向检查（文件应该存在），不是反向检查（不应该存在的文件）。** 两者互补但当前各自维护独立的硬编码列表。

### 1.3 设计目标

设计一个声明式的清理机制：

- **Canonical manifest**：定义每个版本的文件/目录结构（所有**应存在**的文件）
- **自动 diff**：`governance-cleanup` 的清理列表 = `(用户安装目录的文件集) - (canonical manifest 的文件集)`
- **可持续**：未来任何目录结构调整后，只需更新 manifest，清理命令自动生效，不需要额外适配
- **单一事实源**：manifest 同时服务于 `verify_workflow.py` 的正向检查和 cleanup 的反向检查

---

## 2. 决策

### 2.1 Canonical Manifest 数据格式

**选择 JSON 格式**，文件路径：`skills/software-project-governance/core/manifest.json`

#### 2.1.1 格式设计

```json
{
  "$schema": "https://example.com/manifest-schema-v1.json",
  "workflow": "software-project-governance",
  "version": "0.19.0",
  "description": "Canonical file manifest. All entries define files/directories/patterns that SHOULD exist after plugin installation or repo checkout.",
  "source_of_truth": true,

  "root_entries": {
    "files": [
      "README.md",
      "CLAUDE.md"
    ],
    "directories": []
  },

  "product": {
    "description": "Files shipped to end users via plugin installation.",
    "entries": [
      { "path": "skills/software-project-governance/SKILL.md", "type": "file" },
      { "path": "skills/software-project-governance/core/", "type": "dir" },
      { "path": "skills/software-project-governance/infra/", "type": "dir" },
      { "path": "skills/software-project-governance/references/", "type": "dir" },
      { "path": "skills/software-project-governance/core/templates/", "type": "dir" },
      { "path": "skills/software-project-governance/core/protocol/", "type": "dir" },
      { "path": "skills/software-project-governance/infra/hooks/", "type": "dir" },
      { "path": "skills/software-project-governance/infra/TOOLS.md", "type": "file" },
      { "path": "skills/software-project-governance/infra/verify_workflow.py", "type": "file" },
      { "path": "skills/software-project-governance/infra/verify-e2e.sh", "type": "file" },
      { "path": "agents/", "type": "dir" },
      { "path": "commands/", "type": "dir" },
      { "path": "adapters/", "type": "dir" },
      { "path": ".claude-plugin/", "type": "dir" },
      { "path": ".codex-plugin/", "type": "dir" },
      { "path": ".agents/", "type": "dir" }
    ],
    "glob_patterns": [
      "skills/software-project-governance/core/**/*.md",
      "skills/software-project-governance/references/**/*.md",
      "skills/software-project-governance/infra/hooks/*",
      "skills/stage-*/SKILL.md",
      "skills/code-review/SKILL.md",
      "skills/design-review/SKILL.md",
      "skills/main-workflow/SKILL.md",
      "skills/okr/SKILL.md",
      "skills/pr-faq/SKILL.md",
      "skills/release-checklist/SKILL.md",
      "skills/release-review/SKILL.md",
      "skills/requirement-clarification/SKILL.md",
      "skills/requirement-review/SKILL.md",
      "skills/retro-meeting/SKILL.md",
      "skills/retro-review/SKILL.md",
      "skills/six-pager/SKILL.md",
      "skills/tech-review/SKILL.md",
      "skills/test-review/SKILL.md",
      "agents/*.md",
      "commands/*.md",
      "adapters/*/README.md",
      "adapters/*/adapter-manifest.json",
      "adapters/*/launch.py",
      ".claude-plugin/*.json",
      ".codex-plugin/*.json",
      ".agents/plugins/*.json"
    ]
  },

  "repo_only": {
    "description": "Files that exist only in the development repository, NOT shipped to end users.",
    "entries": [
      { "path": "project/", "type": "dir" },
      { "path": ".github/", "type": "dir" },
      { "path": ".governance/", "type": "dir" },
      { "path": ".git/", "type": "dir" },
      { "path": ".claude/", "type": "dir" },
      { "path": "docs/", "type": "dir" },
      { "path": "e2e-test-project/", "type": "dir" }
    ],
    "glob_patterns": [
      "project/**/*.md",
      "project/**/*.json",
      ".github/**/*",
      ".governance/*.md",
      "docs/**/*.md"
    ]
  },

  "exclude_from_cleanup": {
    "description": "Paths NEVER considered redundant, even if not in the manifest above. These are user-generated or external.",
    "entries": [
      ".git/",
      "node_modules/",
      "__pycache__/",
      "*.pyc",
      ".env",
      ".env.*",
      "*.log"
    ],
    "user_data_dirs": [
      ".governance/"
    ]
  }
}
```

#### 2.1.2 设计决策与理由

| 设计选择 | 选择 | 排除方案 | 理由 |
|---------|------|---------|------|
| **数据格式** | JSON | YAML（需要 pyyaml 依赖）、TOML（需要 tomli/tomllib 依赖） | JSON 是 Python stdlib 原生支持，零依赖。Claude Code 环境保证有 Python。 |
| **组织方式** | `product` + `repo_only` 两段式 | 单段混合（需额外字段标注每个条目是否 product） | 两段式语义清晰：product = 用户获得什么，repo_only = 开发仓库专属。cleanup 默认只操作 product 段。 |
| **glob 支持** | 与显式条目并存 | 纯显式（手动列出数百个文件）、纯 glob（难以表达不规则结构） | 混合模式：目录级用显式条目声明"这个目录属于我们"，文件级用 glob 避免逐个列举。 |
| **排除清单** | 内置于 manifest | 分离到独立 `.gitignore` 式文件 | 排除清单和包含清单放在同一文件：一个文件看清"什么属于我们 + 什么绝不删除"。 |
| **版本声明** | manifest 内含 `version` 字段 | 版本从外部传入 | manifest 自身版本化，可以回答"这个 manifest 描述的是哪个版本的结构"。version bump 时同步更新 manifest。 |
| **schema 声明** | `$schema` 字段（URI） | 无 schema | 为将来的 schema 演进和验证留入口。后续可创建 JSON Schema 文件做 manifest 自校验。 |

### 2.2 清理流程设计

#### 2.2.1 核心算法

```
CANONICAL = expand_globs(manifest.product.entries + manifest.product.glob_patterns)
ACTUAL     = scan_directory(plugin_install_root)
EXCLUDE    = expand_globs(manifest.exclude_from_cleanup)
REDUNDANT  = ACTUAL - CANONICAL - EXCLUDE
```

#### 2.2.2 执行步骤

```
Step 1: 加载 manifest
  - 读取 skills/software-project-governance/core/manifest.json
  - 校验 JSON 结构完整性（必须字段：version, product.entries, product.glob_patterns）

Step 2: 展开 canonical 文件集
  - 对 product.entries 中的 file 类型 → 直接加入集合
  - 对 product.entries 中的 dir 类型 → 递归列出目录下所有文件的相对路径
  - 对 product.glob_patterns → 使用 pathlib.glob() 展开

Step 3: 扫描安装目录
  - 递归扫描 plugin install root（通常是 skills/ 的父目录）
  - 收集所有文件的相对路径
  - 过滤排除清单

Step 4: 计算冗余集
  REDUNDANT = ACTUAL - CANONICAL_EXPANDED - EXCLUDE_EXPANDED

Step 5: 分类
  P0（必须清理）:
    - 旧版本目录结构残留（如 nested agents/ → flat agents/ 迁移后，旧的 nested 目录）
    - SKILL stub（内容检测辅助：含 "plugin 发现 stub"）
  P1（建议清理）:
    - 旧版本文件（manifest 不再声明的单文件）
    - 空目录
  P2（谨慎清理）:
    - 无法确定来源的文件（文件名不在任何已知模式中）

Step 6: 展示并确认
  - 按分类展示冗余文件列表
  - AskUserQuestion 确认清理范围

Step 7: 执行清理
  - 先删文件，再尝试删空目录
  - 记录操作日志到 evidence-log.md
```

#### 2.2.3 边缘情况处理

| 边缘情况 | 处理策略 |
|---------|---------|
| manifest.json 本身不存在 | 降级为当前硬编码模式（向后兼容）。输出警告："未找到 canonical manifest，使用旧版硬编码清理列表。建议升级插件。" |
| manifest 声明了但实际文件缺失 | **不是 cleanup 的职责**——这是 `verify_workflow.py` 的正向检查职责。cleanup 只做"多余文件清理"，不做"缺失文件告警"。 |
| 用户修改了 canonical 文件（内容变了但路径在 manifest 中） | 路径在 manifest 中 → 不是冗余 → 不删除。内容变化是 verify_workflow.py 的 snippet check 职责。 |
| 两个版本之间 manifest 声明了不同的目录结构 | 这是设计目标。旧结构文件不在新 manifest 中 → 自动识别为冗余 → 清理。 |
| 用户项目中也有同名目录（如 `agents/`、`commands/`） | 危险。cleanup MUST 只操作**插件安装目录**（如 `~/.claude/plugins/cache/software-project-governance/`），不得操作用户项目根目录。通过 `--target` 参数显式指定目标目录。 |
| 空目录 | 单独处理——先删文件，再扫描空目录并删除。空目录即使不在 manifest 中（因为 manifest 的 dir entry 已声明该目录属于我们），也不应视为"冗余目录"，但可以在确认后清理。 |

#### 2.2.4 安全边界

```
CRITICAL SAFETY RULES（MUST NOT 违反）:
1. 绝不在用户项目根目录运行清理（仅限插件安装目录）
2. 绝不删除 .governance/ 目录（用户治理数据，已列入 exclude_from_cleanup）
3. 绝不删除 .git/ 目录
4. 清理前必须展示完整待删列表并获取用户确认
5. 保留 --dry-run 模式：只展示不执行
6. 保留 --json 模式：输出机器可解析的冗余文件列表（供外部脚本消费）
```

### 2.3 与 verify_workflow.py 的关系

#### 2.3.1 职责边界

| 职责 | verify_workflow.py | manifest.json + cleanup |
|------|-------------------|------------------------|
| 检查必需文件是否存在 | **正向检查**：REQUIRED_FILES | **不负责**（这不是 cleanup 的职责） |
| 检查文件内容片段是否正确 | **snippet check** | **不负责** |
| 检查多余文件 | 不负责 | **反向检查**：ACTUAL - CANONICAL |
| 清理旧版本残留 | 不负责 | **执行清理** |
| 版本一致性 | check-version-consistency | **不负责**（属于 verify 职责） |

#### 2.3.2 共享数据源方案

**Phase 3（推荐但非 Phase 1 必需）**：将 `verify_workflow.py` 的 `REQUIRED_FILES` dict 迁移为从 `manifest.json` 读取。实现单一事实源。

具体做法：
```python
# verify_workflow.py 新逻辑
def load_manifest():
    manifest_path = ROOT / "skills/software-project-governance/core/manifest.json"
    with open(manifest_path) as f:
        return json.load(f)

def build_required_files_from_manifest(manifest):
    # 展开 manifest.product.entries + manifest.product.glob_patterns
    # + manifest.repo_only.entries + manifest.repo_only.glob_patterns
    # 生成等价于当前 REQUIRED_FILES dict 的数据结构
    ...

# 旧 REQUIRED_FILES dict 保留为 fallback（manifest 不存在时使用）
```

迁移后，`verify_workflow.py` 不再独立维护 `REQUIRED_FILES` dict——所有文件声明集中在 `manifest.json`。

#### 2.3.3 双轨运行期

在 Phase 3 完成之前，`manifest.json` 和 `verify_workflow.py` 的 `REQUIRED_FILES` 各自维护。通过 CI 检查确保两者一致（manifest.json 中声明了但 REQUIRE_FILES 中没有 → 告警；反之亦然）。

### 2.4 governance-cleanup.md 重设计方案

#### 2.4.1 当前问题

- 硬编码列表（15 + 5 + 25 = 45 个手动维护的路径）
- 按版本组织但无结构化数据
- 内容检测 `plugin 发现 stub` 是特例化逻辑，不通用

#### 2.4.2 重设计后的结构

```markdown
# governance-cleanup — 声明式插件残留清理

## 触发条件
- `/governance-cleanup` — 执行清理
- 首次使用 `/governance` 时自动检测（Scenario C 升级场景）
- CLAUDE.md bootstrap 自动升级序列中执行

## 执行流程

### Step 1: 加载 Canonical Manifest
- 读取 `skills/software-project-governance/core/manifest.json`
- IF 不存在 → 降级为旧版硬编码模式（临时兼容路径，输出废弃警告）

### Step 2: 展开 Canonical 文件集
- 展开 `product.entries`（文件 + 目录递归）
- 展开 `product.glob_patterns`（使用 Python `pathlib` 或等效 glob）
- 加载 `exclude_from_cleanup`

### Step 3: 扫描安装目录
- 确定清理目标目录（默认：插件安装缓存目录）
- 递归收集所有文件的相对路径
- 应用排除规则

### Step 4: 计算冗余集
REDUNDANT = ACTUAL - CANONICAL - EXCLUDE

### Step 5: 分类展示
按 P0/P1/P2 分类展示待清理文件列表

### Step 6: 用户确认
通过 AskUserQuestion 展示选项：
(1) 一键清理全部
(2) 仅清理 P0 必须移除的
(3) 逐文件确认
(4) 跳过

### Step 7: 执行清理 + 输出报告

## 参数
| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|---------|------|
| target | 路径 | 否 | 自动检测 | 清理目标目录（默认：插件安装缓存） |
| dry-run | 布尔 | 否 | false | 仅展示冗余文件不删除 |
| json | 布尔 | 否 | false | JSON 格式输出（供外部脚本消费） |
| manifest | 路径 | 否 | manifest.json | 自定义 manifest 路径 |

## 错误码
| 代码 | 条件 | 动作 |
|------|------|------|
| CLEANUP-ERR-001 | 插件缓存目录不存在 | 提示用户检查插件安装状态 |
| CLEANUP-ERR-002 | 无可清理文件 | 告知用户插件已是纯净版本 |
| CLEANUP-ERR-003 | manifest.json 不存在或格式错误 | 降级为旧版硬编码模式并输出废弃警告 |

## 自校验
- [ ] manifest.json 已加载且版本匹配
- [ ] 冗余文件列表已按 P0/P1/P2 分类
- [ ] 用户已确认清理范围
- [ ] 排除清单中的文件未被触碰
- [ ] 用户项目文件未被触碰
```

#### 2.4.3 关键变化

| 旧设计 | 新设计 |
|-------|-------|
| 硬编码冗余文件列表（45 行手动维护） | 从 manifest.json 自动计算 |
| "已知冗余"——维护者需要知道上个版本有什么 | "结构 diff"——manifest 声明当前版本有什么，其余 = 冗余 |
| 内容检测（stub pattern）是特例化逻辑 | 不再需要内容检测（路径不在 manifest 中 → 自动被识别为冗余） |
| 版本升级需手动追加清理条目 | 版本升级只需更新 manifest.json（移除旧路径、添加新路径） |
| 无 dry-run/json 输出 | 支持 `--dry-run` 和 `--json` |

### 2.5 与 CLAUDE.md / governance-init.md 中 bootstrap 清理逻辑的关系

#### 2.5.1 当前状态

CLAUDE.md bootstrap 的自动清理逻辑：
```
自动清理升级残留：检测 skills/ 下是否存在旧版 stub
（文件内容含 "plugin 发现 stub"）。
v0.19.0+ 真实 SKILL 已直接迁至 skills/<name>/SKILL.md 平铺，stub 不再需要 → 自动删除。
```

governance-init.md Step 7 中的升级序列同样包含此逻辑。

#### 2.5.2 重设计方案

bootstrap 升级序列中的清理逻辑改为：

```
自动清理升级残留：
  1. 加载 skills/software-project-governance/core/manifest.json
  2. 展开 canonical 文件集
  3. 扫描当前安装目录（排除 exclude_from_cleanup）
  4. 自动删除不在 canonical 集中的文件（无需用户确认——这是自动升级的一部分）
  5. 输出: ✅ 已清理 {N} 个过期文件/目录
```

此变更同时更新 `CLAUDE.md` 和 `commands/governance-init.md` 中的对应段落。

---

## 3. 备选方案及排除理由

### 方案 B：纯 auto-generated manifest（不维护静态文件）

**描述**：manifest 由脚本从当前目录结构自动生成，没有静态文件。

**排除理由**：
- 无法区分"应该存在的文件"和"恰好存在的临时文件"。开发过程中可能产生 `__pycache__/`、`*.pyc`、临时脚本等——auto-generate 会把它们也写入 manifest。
- 版本间对比困难。没有静态 manifest，无法回答"v0.18 的目录结构和 v0.19 有什么不同"。
- 无法作为 CI 检查源。CI 需要一份"应该是什么"的声明来对比"实际是什么"。

### 方案 C：manifest 嵌入 verify_workflow.py（不创建新文件）

**描述**：扩展现有 `REQUIRED_FILES` dict 使其包含反向检查能力（声明"不应该有的文件"），不新建 manifest.json。

**排除理由**：
- `REQUIRED_FILES` dict 已经是 ~200 行，再加入反向检查逻辑会让文件更加臃肿。
- verify_workflow.py 是 Python 代码——不是数据。manifest 应该是"数据"而非"代码"，因为它描述的是"世界应该是什么样"，不包含逻辑。
- 数据格式（JSON）比 Python dict 更易于被外部工具消费（如 `jq` 查询、GitHub Actions 解析、跨语言脚本读取）。
- 关注点分离：验证逻辑（verify）和结构声明（manifest）是两类不同资产，应各自演进。

### 方案 D：使用 `.gitignore` 式 pattern 文件（反向：定义"应保留的"）

**描述**：创建一个类似 `.gitignore` 的文件，定义"应保留的模式"，不在模式中的 = 冗余。

**排除理由**：
- gitignore 语义是排除（ignore），我们需要的是包含（keep）。语义相反容易混淆。
- glob 表达能力有限。某些结构（如"这个目录应该存在但允许用户在其中创建任意文件"）难以用纯 glob 表达。
- 需要显式目录声明（用于创建时的目录存在性检查），glob 无法表达"这个目录应该存在即使是空的"。

---

## 4. 蓝军挑战

### CH-001: manifest.json 本身成为新的维护负担
**挑战**：如果开发者在添加/删除文件后忘记更新 manifest.json，manifest 会与实际结构漂移——清理命令可能误删新文件或保留已删除文件。

**缓解措施**：
1. `verify_workflow.py` 新增 `check-manifest-consistency` 检查：对比 manifest 展开集与实际文件系统，报告差异（manifest 声明了但不存在 / 存在但 manifest 未声明）。
2. CI 强制执行 `check-manifest-consistency`，漂移时阻断。
3. `VERSIONING.md` 中新增 manifest 更新义务：文件增删 MUST 同步更新 manifest.json。
4. 版本 bump 前 MUST 通过 `check-manifest-consistency`。

### CH-002: glob 展开性能——大型 repos 中可能很慢
**挑战**：如果 manifest 中的 glob pattern 过多或范围过大，展开操作可能耗时。

**缓解措施**：
1. 插件安装目录文件数有限（当前约 80 个文件），O(n) 扫描可忽略不计。
2. 实现中使用 `os.scandir()` 而非 `os.walk()` 以提高遍历效率。
3. 添加 `--fast` 模式：仅对比顶级目录结构（不递归），适用于快速检测。

### CH-003: 两个 manifest（manifest.md 人类可读 + manifest.json 机器可读）可能漂移
**挑战**：人类维护 manifest.md 描述结构，机器读取 manifest.json 执行清理。两者如果不同步，人类看到的和机器执行的可能不一致。

**缓解措施**：
1. manifest.json 是唯一事实源（canonical source of truth）。manifest.md 简化为概述性说明（不重复逐文件列表），在开头声明"详细文件清单见 manifest.json"。
2. 或者：manifest.md 完全移除文件级结构描述，只保留"组成概览"（五层架构说明）。文件级精确声明只存在于 manifest.json。
3. verify_workflow.py 校验：manifest.md 中不应包含文件级路径列表（检测到则告警）。

### CH-004: 用户自定义的合法文件可能被误识别为冗余
**挑战**：用户可能在插件目录中放置自定义文件（如本地调试配置、patch 文件），这些不在 manifest 中，会被标记为冗余。

**缓解措施**：
1. `exclude_from_cleanup` 支持用户自定义排除项（通过 `--exclude` 参数追加）。
2. P2 分类"无法确定来源的文件"默认为"不自动清理，需用户逐项确认"。
3. 支持 `.cleanupignore` 文件（类似 `.gitignore`），用户可以手动声明不想被清理的路径。
4. 文档明确说明：插件目录中的用户自定义文件应在升级后重新添加（这是插件系统的一般性预期）。

---

## 5. 影响范围

### 5.1 新增文件

| 文件 | 说明 |
|------|------|
| `skills/software-project-governance/core/manifest.json` | Canonical manifest——机器可读的文件结构声明 |

### 5.2 修改文件

| 文件 | 变更说明 |
|------|---------|
| `commands/governance-cleanup.md` | 重写为声明式清理流程（基于 manifest.json diff） |
| `CLAUDE.md` bootstrap 自动清理段 | 替换 stub 内容检测为 manifest diff |
| `commands/governance-init.md` Step 7 清理段 | 同上 |
| `skills/software-project-governance/core/manifest.md` | 简化为概述性说明，移除文件级路径列表 |
| `skills/software-project-governance/core/VERSIONING.md` | 新增规则：文件增删 MUST 更新 manifest.json |

### 5.3 可选变更（Phase 3）

| 文件 | 变更说明 |
|------|---------|
| `skills/software-project-governance/infra/verify_workflow.py` | 新增 `check-manifest-consistency` 命令；可选迁移 REQUIRED_FILES 为从 manifest.json 读取 |

### 5.4 不受影响

| 文件/组件 | 原因 |
|-----------|------|
| `.governance/` 治理记录 | 始终在 exclude_from_cleanup 中 |
| `adapters/` | 是 manifest 的一部分（product），正常受保护 |
| `.claude-plugin/`, `.codex-plugin/` | 是 manifest 的一部分（product） |
| 用户项目文件 | cleanup 只操作插件安装目录 |
| `skills/software-project-governance/references/` | 是 manifest 的一部分 |

---

## 6. 实现路径

### Phase 1: Canonical Manifest 创建（0.5 人天）

**产出**：
- `skills/software-project-governance/core/manifest.json`——完整描述 v0.19.0 目录结构

**步骤**：
1. 扫描当前 `skills/`、`agents/`、`commands/`、`adapters/`、`project/` 的实际文件列表
2. 按 product / repo_only 分类
3. 确定 glob pattern 覆盖范围（在精确性和可维护性之间平衡）
4. 添加 exclude_from_cleanup 清单
5. 自检：展开 manifest，与 `verify_workflow.py` 的 `REQUIRED_FILES` 做交叉校验

### Phase 2: governance-cleanup.md 重写（0.5 人天）

**产出**：
- 重写 `commands/governance-cleanup.md`——基于 manifest diff 的声明式清理流程

**步骤**：
1. 按 2.4 节方案重写
2. 保留旧版硬编码逻辑作为 manifest 不存在时的 fallback
3. 实现 `--dry-run` 和 `--json` 参数
4. 自检：在开发仓库中运行 dry-run，确认不会误删任何 canonical 文件

### Phase 3: verify_workflow.py 增强（1 人天）

**产出**：
- `verify_workflow.py` 新增 `check-manifest-consistency` 子命令
- 可选：REQUIRED_FILES 从 manifest.json 读取

**步骤**：
1. 实现 `check-manifest-consistency`：对比 manifest 展开集与实际文件系统
2. 在 CI 中启用此检查
3. 评估 REQUIRED_FILES 迁移到 manifest.json 的成本和收益
4. 如果迁移：实现读取逻辑 + 保留 fallback

### Phase 4: Bootstrap 清理逻辑更新（0.25 人天）

**产出**：
- CLAUDE.md 和 governance-init.md 中的自动清理逻辑更新为 manifest-based

**步骤**：
1. 更新 CLAUDE.md bootstrap 自动清理段
2. 更新 governance-init.md Step 7 清理段
3. bump PATCH 版本

### Phase 5: 文档和纪律更新（0.25 人天）

**产出**：
- manifest.md 简化为概述
- VERSIONING.md 新增 manifest 更新纪律
- CHANGELOG 更新

---

## 7. 后续动作

1. Coordinator 审阅本 ADR——确认方案方向
2. 创建 plan-tracker 任务（如 `CLEANUP-001` ~ `CLEANUP-005`，对应 Phase 1~5）
3. 确认是否需要在 Phase 3 中完成 REQUIRED_FILES 迁移（增加工作量但消除双源漂移风险）
4. 确定 target version（建议作为 v0.20.0 或 v0.19.x 的 PATCH 发布）

---

## 附录 A: manifest.json 完整示例（v0.19.0 结构）

参见上文 2.1.1 格式设计节。完整的 v0.19.0 manifest.json 应在 Phase 1 中通过实际目录扫描生成，此处提供的是格式模板而非完整数据。

## 附录 B: 清理算法伪代码

```python
import json, os
from pathlib import Path

def load_manifest(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)

def expand_canonical(manifest: dict, root: Path) -> set:
    """Expand manifest entries + globs into a set of relative paths."""
    canonical = set()
    for entry in manifest["product"]["entries"]:
        p = root / entry["path"]
        if entry["type"] == "file":
            canonical.add(entry["path"])
        elif entry["type"] == "dir":
            if p.exists():
                for f in p.rglob("*"):
                    if f.is_file():
                        canonical.add(str(f.relative_to(root)))
            canonical.add(entry["path"])  # dir itself
    for pattern in manifest["product"]["glob_patterns"]:
        for match in root.glob(pattern):
            canonical.add(str(match.relative_to(root)))
    return canonical

def scan_actual(root: Path, excludes: set) -> set:
    """Scan actual filesystem, return set of relative paths."""
    actual = set()
    for f in root.rglob("*"):
        if f.is_file():
            rel = str(f.relative_to(root))
            if not any(rel.startswith(e.rstrip("/")) for e in excludes):
                actual.add(rel)
    return actual

def compute_redundant(manifest_path: Path, target_root: Path) -> dict:
    manifest = load_manifest(manifest_path)
    canonical = expand_canonical(manifest, target_root)
    excludes = set(manifest["exclude_from_cleanup"].get("entries", []) +
                   manifest["exclude_from_cleanup"].get("user_data_dirs", []))
    actual = scan_actual(target_root, excludes)
    redundant = actual - canonical
    return {
        "total_actual": len(actual),
        "total_canonical": len(canonical),
        "redundant_count": len(redundant),
        "redundant_files": sorted(redundant),
    }
```
