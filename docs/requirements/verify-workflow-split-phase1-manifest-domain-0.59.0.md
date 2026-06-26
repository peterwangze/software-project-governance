# verify_workflow.py 拆分 Phase 1 — 抽出 manifest 域 (0.59.0)

> **任务**: REQ-102 / AUDIT-122（规划入账）
> **日期**: 2026-06-26
> **触发**: DEC-083 路线图第 (3) 项——verify_workflow.py 渐进式按 check 域拆分（0.59.0~0.64.0 每版拆 1~2 域），Phase 1 从 manifest 域开始
> **前置**: AUDIT-121（架构腐化审视 F1 God Module + F3 source/projection 双写）、RISK-039（架构腐化看护缺口，关闭标准含拆分完成）、0.58.0 ArchGuard（advisory 守护拆分质量）
> **性质**: 需求 + 设计文档（治理记录范畴）。实现阶段 spawn Governance Developer（产品代码范畴）。
> **决策依据**: DEC-083（用户 2026-06-24 决策）、AUDIT-121 F1（verify_workflow.py 20,294 行 / 439 def / 54 命令）、F6（0 个 check 守护模块大小）

---

## 0. 事实纪律声明

本文档遵循 AUDIT-117「前提事实约束」纪律。所有事实结论均有实测证据；manifest 域边界基于 2026-06-26 Explore sub-agent 实测勘察报告（附录 A 全文引用），推测显式标注 `【推测】`。

实测基线 commit：当前 master HEAD（0.58.0 post-release，REL-044 之后）。verify_workflow.py 实测 20,937 行（勘察时；含 0.58.0 ArchGuard 新增 ~500 行后较 AUDIT-121 基线 20,294 行增长）。

---

## 1. 背景与动机

### 1.1 为什么先拆 manifest 域

DEC-083 路线图要求 0.59.0~0.64.0 渐进式拆分，每版拆 1~2 域。选 manifest 域作为 Phase 1 的理由（实测依据）：

1. **边界最清晰**——manifest 域有 9 个核心函数（A 组），内部仅互相调用 + 调少量共享 helper，与其它域耦合最低（勘察报告 §8）。
2. **规模适中**——纯函数体约 401 行（+ 私有 helper ~27 行），占总量 ~1.9%。抽出后 verify_workflow.py 净减 ~430 行，是一个可验证的小步。
3. **自包含可测**——manifest 域已有完整的 `check-manifest-consistency` CLI 入口和 unittest 覆盖，抽出后可独立验证不破坏 54 个 CLI 命令契约。
4. **示范方法论**——Phase 1 建立的「抽出 → 薄入口委托 → ArchGuard 守护模块大小不增 → 回归测试」流程，将被 0.60.0~0.64.0 后续域复用。

### 1.2 不做什么（边界）

- **不拆其它域**——release / governance / agent / capability 等域留 0.60.0~0.64.0。
- **不重写架构**——渐进式拆分，非分层重写（DEC-083 排除「重写为分层架构」备选）。
- **不改 54 个 CLI 命令契约**——`check-manifest-consistency` 的参数、退出码、输出格式、`--fail-on-issues` 行为必须逐字不变。
- **不关闭 RISK-039**——关闭需外部宿主项目验证（Phase 1 是拆分开始，非完成）。
- **不引入 src/ layout / pyproject.toml / ruff / mypy**——F2 现代工程基础设施留 0.64.0（路线图明确）。
- **不处理 source/projection 双写（F3）**——双写消除留 0.64.0「改为生成时投影」。

---

## 2. manifest 域事实清单（实测）

来源：2026-06-26 Explore 勘察报告（附录 A）。以下为设计决策直接依赖的事实，详见附录。

### 2.1 核心函数（A 组，明确属于 manifest 域）

| 函数 | 行号 | 行数 | 归属判定 |
| --- | --- | --- | --- |
| `build_required_files_from_manifest(manifest_path=None)` | 841-902 | 62 | manifest 域 |
| `expand_manifest_to_canonical_set(manifest_path=None)` | 905-955 | 51 | manifest 域 |
| `check_manifest_canonical_product_artifacts(manifest, manifest_path=None)` | 971-1055 | 85 | manifest 域 |
| `check_manifest_cleanup_scope(manifest, manifest_path=None)` | 1058-1076 | 19 | manifest 域 |
| `check_manifest_consistency(manifest_path=None)` | 1151-1214 | 64 | manifest 域 |
| `cmd_check_manifest_consistency(args)` | 19051-19095 | 45 | manifest 域（CLI 入口）|

### 2.2 私有 helper（仅 manifest 域内引用，随域抽出）

| helper | 行号 | 唯一调用点 |
| --- | --- | --- |
| `_path_to_label(relative_path_str)` | 812-838 | line 869（`build_required_files_from_manifest` 内）|
| `_manifest_product_file_entries(manifest)` | 958-963 | line 985 |
| `_manifest_requires_product_artifact_guards(...)` | 1079-1100 | line 1194 |
| `scan_actual_files(exclude_patterns=None)` | 1103-1133 | line 1148 |
| `scan_manifest_visible_files(exclude_patterns=None)` | 1136-1148 | （manifest 可见性扫描入口）|

### 2.3 共享依赖（被多域调用，必须保留 import）

| 依赖 | 定义行 | manifest 域调用 | 非manifest 域调用 | 处置 |
| --- | --- | --- | --- | --- |
| `_display_path(path, root=None)` | 27 | 2 处 | 全文 **142 处** | **必留 common**（manifest.py import）|
| `_git_files(args)` | 84 | 2 处 | release 域等共 6 处 | **必留 common**（manifest.py import）|
| `PLUGIN_SCOPE_DIRS` | 49 | `check_manifest_cleanup_scope` | `_is_plugin_path`、line 10785 | 见 §3 决策 D1 |
| `_manifest_artifact_entries(manifest)` | 966-968 | manifest 域 1 处 | capability-registry(3114) + lifecycle-registry(3225) + governance-pack(4541) | 见 §3 决策 D2 |
| `REQUIRED_FILES` | 171-231 | `build_required_files_from_manifest` 是其替代源 | `check_files`(1226)、`_check_all_required_files_exist`(15551) 回退消费 | 见 §3 决策 D3 |
| `OPTIONAL_PROJECTION_FILES` | 233-258 | （与上同语义）| files-check 域消费 | 见 §3 决策 D3 |

### 2.4 CLI / dispatch / Check 接入点

- **argparse 注册**：line 20460 `subparsers.add_parser("check-manifest-consistency", ...)`，参数 `--fail-on-issues`（20462-20463）。
- **dispatch 注册**：line 20880 `"check-manifest-consistency": cmd_check_manifest_consistency,`。
- **governance-pack known checks**：line 2395 `GOVERNANCE_PACK_KNOWN_CHECKS` set 含 `"check-manifest-consistency"`。
- **Check 11（非 28x）**：真正的 manifest 一致性打印在 `cmd_verify` 的 Check 11「Manifest Consistency」(line 14662-14686)，调用 `check_manifest_consistency()`。Check 28（governance）**无** manifest 子项。

### 2.5 manifest.json 结构（566 行，只读消费方）

顶层 11 key：`$schema` / `workflow` / `version` / `description` / `source_of_truth` / `root_entries.files`(4) / `product.entries`(**97**) + `glob_patterns`(28) / `canonical_product_artifacts.entries`(**4**: governance-pack-registry / capability-registry / lifecycle-registry / architecture-health-budget) / `repo_only.entries`(7) + `glob_patterns`(14) / `cleanup_scope.directories`(8，与 `PLUGIN_SCOPE_DIRS` 逐字相等) / `exclude_from_cleanup`。

---

## 3. 设计决策

### D1 — `PLUGIN_SCOPE_DIRS` 留在 verify_workflow.py（common 候选）

**事实**：`PLUGIN_SCOPE_DIRS`(line 49) 被 manifest 域（`check_manifest_cleanup_scope`）和 plugin-scope 域（`_is_plugin_path`、line 10785）共享，且注释「keep in sync with cleanup.py」(line 45)。

**决策**：**留**。manifest.py 通过 `from verify_workflow import PLUGIN_SCOPE_DIRS`（或后续 common 模块）引用，不移动常量定义。

**原因**：0.59.0 只抽 manifest 域，不抽 plugin-scope 域。移动 `PLUGIN_SCOPE_DIRS` 会让 plugin-scope 域产生 import 反向依赖（plugin-scope 还没拆）。等 common 模块建立后（【推测】0.64.0 或专门 common 抽出版本）再统一安置。

### D2 — `_manifest_artifact_entries` 抽到 manifest.py，多域通过 import 共享

**事实**：`_manifest_artifact_entries`(966-968) 被 4 个域调用：manifest 域(981)、capability-registry(3114)、lifecycle-registry(3225)、governance-pack(4541)。

**决策**：**抽**到 `infra/checks/manifest.py`，其它 3 个 registry 域通过 `from checks.manifest import _manifest_artifact_entries` 引用。

**原因**：语义上它解析 `manifest.json` 的 `canonical_product_artifacts.entries`，归 manifest 域最自然。其它 3 个 registry 域当前在 verify_workflow.py 内同模块调用，抽成显式 import 后依赖关系更清晰（而非隐式同文件）。0.60.0+ 拆这些 registry 域时，import 路径已就位。

**风险**：增加 3 处 import。但 verify_workflow.py 本就是单体，import 是显式化的成本，可接受。

### D3 — `REQUIRED_FILES` / `OPTIONAL_PROJECTION_FILES` 留在 verify_workflow.py

**事实**：这两个常量是 `manifest.json` 的**硬编码回退**（manifest 解析失败时 `check_files`/`_check_all_required_files_exist` 回退到它们）。它们既是 manifest 数据源的语义（"哪些文件是必需的"），也是 files-check 域的消费方。

**决策**：**留**在 verify_workflow.py。manifest.py 不持有这两个常量。

**原因**：files-check 域（`check_files` 等）是更直接的高频消费者（line 1226、15551）。把常量移到 manifest.py 会让 files-check 域反向 import manifest 域——而 files-check 域还没拆。语义上「必需文件清单」是项目级数据，不专属 manifest 解析逻辑。manifest.py 的 `build_required_files_from_manifest` 返回 dict，调用方自行选择用 manifest 返回值还是回退常量。

### D4 — Check 11 打印段留在 `cmd_verify`

**事实**：Check 11「Manifest Consistency」打印段(line 14662-14686)在 `cmd_verify` 内联，仅消费 `check_manifest_consistency()` 返回值。

**决策**：**留**在 `cmd_verify`。manifest.py 只提供 `check_manifest_consistency()` 函数，`cmd_verify` 通过 import 调用。

**原因**：Check 11 是 `cmd_verify` 编排逻辑的一部分（决定整体 verify 结果），不是 manifest 域自身。移动它会撕裂 `cmd_verify` 的线性结构。manifest.py 保持「纯 check 函数 + 纯 CLI cmd」的职责边界。

### D5 — `cmd_check_manifest_consistency` 迁移到 manifest.py，verify_workflow.py 委托

**决策**：`cmd_check_manifest_consistency(args)`(19051-19095) **迁移**到 manifest.py。verify_workflow.py 的 dispatch 注册改为 `from checks.manifest import cmd_check_manifest_consistency`。

**原因**：cmd 函数是 manifest 域的 CLI 表面，与 `check_manifest_consistency()` 强耦合，应同域安置。verify_workflow.py 退化为薄入口（dispatch dict 引用 import 来的函数）。

### D6 — 目标文件路径与包结构

**决策**：新建 `skills/software-project-governance/infra/checks/__init__.py`（空，标记为包）+ `skills/software-project-governance/infra/checks/manifest.py`。

**import 方案**：verify_workflow.py 顶部新增 `from checks.manifest import (...)`（相对 verify_workflow.py 同级 `infra/` 目录，`checks` 是子包）。

**理由**：`infra/checks/` 子包为后续 0.60.0~0.64.0 各域模块预留位置（`release.py` / `governance.py` / `agent.py`...），目录结构先于内容建立。

---

## 4. 实现规格（交 Governance Developer）

### 4.1 文件变更清单

| 文件 | 操作 | 内容 |
| --- | --- | --- |
| `infra/checks/__init__.py` | **新建** | 空文件（或仅 docstring 说明子包用途）|
| `infra/checks/manifest.py` | **新建** | §2.1 + §2.2 全部函数 + §2.3 必要 import |
| `infra/verify_workflow.py` | **修改** | 删除迁出函数定义；新增 `from checks.manifest import ...`；dispatch/argparse 注册保留但引用迁出函数 |
| `core/manifest.json` | **修改** | `product.entries` 登记 `infra/checks/__init__.py` + `infra/checks/manifest.py`（如 manifest 校验要求所有 .py 登记）|
| `core/technical-debt-ledger.md` | **修改** | 登记 0.59.0 拆分进度（TD-001 God Module 部分闭环）|
| `infra/tests/test_manifest_*.py` 或既有测试 | **确认** | 现有 manifest 测试通过（import 路径变化后）|

### 4.2 manifest.py 内容骨架

```python
"""Manifest domain checks — extracted from verify_workflow.py in 0.59.0 (DEC-083 Phase 1).

Scope: manifest.json canonical-set consistency, product-artifact guards, cleanup-scope sync.
Shared helpers (_display_path, _git_files, PLUGIN_SCOPE_DIRS) imported from parent module.
"""
# imports from verify_workflow (shared helpers) — see D1
from verify_workflow import _display_path, _git_files, PLUGIN_SCOPE_DIRS  # 路径方案见 §4.4

# 私有 helper（随域迁入）
def _path_to_label(relative_path_str): ...
def _manifest_product_file_entries(manifest): ...
def _manifest_artifact_entries(manifest): ...   # D2: 多域共享，迁入 manifest.py
def _manifest_requires_product_artifact_guards(manifest, manifest_path=None): ...
def scan_actual_files(exclude_patterns=None): ...
def scan_manifest_visible_files(exclude_patterns=None): ...

# 核心 check 函数
def build_required_files_from_manifest(manifest_path=None): ...
def expand_manifest_to_canonical_set(manifest_path=None): ...
def check_manifest_canonical_product_artifacts(manifest, manifest_path=None): ...
def check_manifest_cleanup_scope(manifest, manifest_path=None): ...
def check_manifest_consistency(manifest_path=None): ...

# CLI 入口（D5）
def cmd_check_manifest_consistency(args): ...
```

### 4.3 verify_workflow.py 改动点（最小化）

```python
# 顶部新增 import
from checks.manifest import (
    build_required_files_from_manifest,
    expand_manifest_to_canonical_set,
    check_manifest_canonical_product_artifacts,
    check_manifest_cleanup_scope,
    check_manifest_consistency,
    cmd_check_manifest_consistency,
    _manifest_artifact_entries,  # D2: capability/lifecycle/governance-pack 域仍需用
)

# dispatch dict（line 20880）保持不变——引用的 cmd_check_manifest_consistency 现在是 import 来的
# argparse（line 20460）保持不变
# Check 11 打印段（line 14662）保持不变——check_manifest_consistency 是 import 来的
# capability-registry(3114)/lifecycle-registry(3225)/governance-pack(4541) 的 _manifest_artifact_entries 调用
#   改为引用 import 来的同名函数（或删本地定义——已迁出）
```

### 4.4 import 路径方案（关键，需实测确认）

**问题**：`infra/checks/manifest.py` 需 import `infra/verify_workflow.py` 的 `_display_path` 等，存在循环 import 风险（verify_workflow.py 也 import checks.manifest）。

**方案 A（推荐）—— 单向依赖**：manifest.py import verify_workflow 的共享 helper；verify_workflow import manifest 的 check 函数。Python 允许**模块顶部 import** 形成 A→B 且 B→A，只要不在模块顶层执行时触发对方未完成初始化的符号。由于两边都是函数定义（调用时才解析），顶部互 import 通常可行，但**必须在实现时实测验证**。

**方案 B（兜底）—— 函数内延迟 import**：manifest.py 的函数体内 `import verify_workflow as _vw; _vw._display_path(...)`。延迟到调用时，彻底规避循环。代价是每次调用多一次 import 查找（可缓存）。

**决策**：**实现时先试方案 A，py_compile + pytest 通过则采用；若循环 import 报错则降级方案 B**。这是实现细节，Governance Developer 实测决定，本文档不预设。

### 4.5 验收标准（验收门禁，全部 PASS 才算完成）

| 门禁 | 命令 | 期望 |
| --- | --- | --- |
| 编译 | `python -m py_compile infra/checks/manifest.py infra/verify_workflow.py` | exit 0 |
| manifest 一致性 | `python verify_workflow.py check-manifest-consistency --fail-on-issues` | exit 0（新增 checks/ 文件已登记）|
| CLI 契约 | `python verify_workflow.py check-manifest-consistency` 输出与拆分前逐字 diff | 无差异 |
| ArchGuard 模块大小 | `python verify_workflow.py check-architecture-health` | manifest.py 不超 error 阈值（5000 行）；verify_workflow.py 较拆分前**净减**（ArchGuard 守护 D-不增原则）|
| Check 28 governance | `python verify_workflow.py check-governance --fail-on-issues` | exit 0（28o~28r advisory 不阻断）|
| 全量 unittest | `pytest infra/tests/ -q` | 全部 passed，0 回归（基线 629 passed）|
| Check 11 verify | `python verify_workflow.py verify` | Check 11 Manifest Consistency 仍 PASS |

---

## 5. ArchGuard 守护契约（0.58.0 能力首次实战）

0.59.0 是 ArchGuard（0.58.0 advisory-only）**首次用于守护真实拆分**。验证 ArchGuard 是否能捕获拆分引入的腐化：

| 拆分风险 | ArchGuard 检测项 | 期望信号 |
| --- | --- | --- |
| manifest.py 反而膨胀（搬入时塞入无关代码）| `check-architecture-health` module_size | manifest.py < verify_workflow.py 拆分后行数，不触发 error |
| 拆出后 verify_workflow.py 没真正减小（只是复制）| module_size verify_workflow.py | 较基线（20,937）净减 |
| 引入重复代码（helper 复制而非 import）| `check-duplicate-code` source/projection + `check-complexity` | 不新增重复块 |

**产出**：拆分后在 evidence-log 记录 ArchGuard 信号对比（拆分前 vs 后），证明 advisory 能力对真实重构有效。这本身是 RISK-039「外部宿主验证」的部分证据（虽然是自验证，非外部宿主）。

---

## 6. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
| --- | --- | --- | --- |
| 循环 import（§4.4）| 中 | 阻塞实现 | 方案 B 延迟 import 兜底；py_compile 实测 |
| manifest 校验要求 checks/ 下 .py 登记，遗漏致 check-manifest-consistency FAIL | 中 | 门禁阻塞 | §4.1 已列 manifest.json 登记；实现时跑 check 确认 |
| 拆分引入隐性行为变化（如模块级常量初始化顺序）| 低 | 回归 | pytest 629 基线 + CLI 输出 diff 门禁 |
| ArchGuard 自身对拆分误报（advisory 噪音）| 低 | 非阻塞（advisory）| 记录信号，必要时调阈值（TD-012/013 已登记）|

---

## 7. 任务分解（注册到 plan-tracker）

| ID | 类型 | 描述 | 前置 |
| --- | --- | --- | --- |
| **REQ-102** | 需求 | 本文档（manifest 域拆分需求/设计）| AUDIT-121, DEC-083 |
| **FIX-153** | 实现 | manifest 域抽出实现（spawn Governance Developer）| REQ-102, 需 DEC-086 授权路径决策 |
| **REL-045** | 发布 | 发布 0.59.0 | FIX-153✅, release gate 全绿 |

### DEC-086 候选（实现授权路径，参照 DEC-085 先例）

0.58.0 ArchGuard 实现时，因当前 harness 仅有只读 Explore sub-agent（无 Write/Edit），DEC-085 授权主 agent 直写产品代码 + 事后 Explore 审查。0.59.0 拆分同为产品代码范畴，面临相同约束。

**候选决策**（交用户确认）：
- (a) 沿用 DEC-085 模式——主 agent 直写 + 事后 Explore 只读审查（已验证可行）
- (b) 若 harness 已注册写权限 sub-agent——回归标准职责分离（spawn Governance Developer + Code Reviewer）

DEC-085 已验证 (a) 是当前 harness 唯一可行路径，本版**默认沿用**，除非用户指示 (b) 或 harness 能力变化。

---

## 8. 与 RISK-039 关闭标准的关系

RISK-039 关闭标准含「verify_workflow.py 拆分完成」。0.59.0 Phase 1 是拆分**开始**，非完成：
- Phase 1（0.59.0）：manifest 域 ✅（本文档规划）
- Phase 2-6（0.60.0~0.64.0）：release / governance / agent / capability / commit / projection / version 域 + 现代工程基础设施
- 拆分全部完成（【推测】0.64.0）+ 1 个外部宿主项目验证 ArchGuard → RISK-039 关闭候选

**0.59.0 不关闭 RISK-039。**

---

## 附录 A — manifest 域实测勘察报告（2026-06-26 Explore sub-agent 全文）

### A.0 文件规模
- verify_workflow.py: **20,937 行**（`wc -l`，0.58.0 post-release）
- manifest.json: 566 行

### A.1 核心 manifest 域函数（A 组）

| 行号 | 函数签名 | docstring 首行 |
| --- | --- | --- |
| 841-902 | `build_required_files_from_manifest(manifest_path=None)` | Build REQUIRED_FILES-equivalent dict from manifest.json |
| 905-955 | `expand_manifest_to_canonical_set(manifest_path=None)` | Expand manifest.json entries + glob_patterns into a canonical set |
| 958-963 | `_manifest_product_file_entries(manifest)` | (无 docstring) |
| 966-968 | `_manifest_artifact_entries(manifest)` | (无 docstring) |
| 971-1055 | `check_manifest_canonical_product_artifacts(manifest, manifest_path=None)` | FIX-110: critical product artifacts must be explicit, tracked, and validated |
| 1058-1076 | `check_manifest_cleanup_scope(manifest, manifest_path=None)` | FIX-110: cleanup.py scan scope must be manifest-declared and verifier-synced |
| 1079-1100 | `_manifest_requires_product_artifact_guards(manifest, manifest_path=None)` | Return whether FIX-110 manifest guards apply to this manifest |
| 1103-1133 | `scan_actual_files(exclude_patterns=None)` | Scan files relevant to manifest drift |
| 1136-1148 | `scan_manifest_visible_files(exclude_patterns=None)` | Scan files relevant to manifest drift |
| 1151-1214 | `check_manifest_consistency(manifest_path=None)` | Compare manifest.json canonical set against actual filesystem |
| 19051-19095 | `cmd_check_manifest_consistency(args)` | CLI 入口 |

### A.2 跨域借用「manifest」之名（不属于 manifest 域，排除）

| 行号 | 函数 | 实际归属域 |
| --- | --- | --- |
| 1958-1965 | `_load_adapter_manifest(adapter_dir)` | adapter 域（读 adapter-manifest.json）|
| 2846-2854 | `_matrix_status_for_manifest(manifest)` | runtime-readiness-matrix 域 |
| 3217-3234 | `_lifecycle_registry_manifest_issues(...)` | lifecycle-registry 域 |

### A.3 manifest 相关常量

| 行号 | 常量 | 类型 | 元素数 |
| --- | --- | --- | --- |
| 131-136 | `PLATFORM_ENTRY_FILES` | set | 4 |
| 171-231 | `REQUIRED_FILES` | dict(label→Path) | ~60 |
| 233-258 | `OPTIONAL_PROJECTION_FILES` | dict(label→Path) | 25 |
| 260+ | `PROJECTION_SNIPPETS` | dict(Path→list) | （注入 REQUIRED_SNIPPETS）|

无 `*_MANIFEST_*` / `CANONICAL_*` 命名全局常量。canonical product artifacts 来自 manifest.json 运行时解析。

### A.4 CLI / dispatch

- argparse: line 20460 `add_parser("check-manifest-consistency")`，参数 `--fail-on-issues`(20462-20463)
- dispatch dict: line 20880 `"check-manifest-consistency": cmd_check_manifest_consistency`
- cmd 函数体: 19051-19095，内部仅调用 `check_manifest_consistency()`(19053)
- `GOVERNANCE_PACK_KNOWN_CHECKS`(2390-2429): line 2395 含 `"check-manifest-consistency"`

### A.5 依赖分析

**(a) 仅 manifest 域调用（随域抽出）**：
`_path_to_label`(812)、`_manifest_product_file_entries`(958)、`_manifest_requires_product_artifact_guards`(1079)、`check_manifest_cleanup_scope`(1058)、`scan_actual_files`(1103)。

**(b) 共享（保留 import）**：
- `_git_files`(84)：manifest 域 2 处 + release/其它域共 6 处
- `_display_path`(27)：manifest 域 2 处 + 全文 **142 处**
- `PLUGIN_SCOPE_DIRS`(49)：manifest 域 + plugin-scope 域
- `_manifest_artifact_entries`(966)：manifest 域 + capability-registry(3114) + lifecycle-registry(3225) + governance-pack(4541)

### A.6 Check 28 子项

Check 28（governance）子项 28 ~ 28r（line 15242-15500），**无 manifest 子项**。真正的 manifest 一致性检查在 **Check 11**（`cmd_verify` line 14662-14686，调用 `check_manifest_consistency()`）。

### A.7 manifest.json 结构

顶层 11 key：`$schema`/`workflow`/`version`/`description`/`source_of_truth`/`root_entries.files`(4)/`product.entries`(97)+`glob_patterns`(28)/`canonical_product_artifacts.entries`(4)/`repo_only.entries`(7)+`glob_patterns`(14)/`cleanup_scope.directories`(8)/`exclude_from_cleanup`。

### A.8 manifest 域代码占比

A 组 11 个函数纯函数体合计约 **~401 行**（不含共享 helper 定义、不含常量），占 20,937 行约 **1.9%**。加私有 helper `_path_to_label`(~27) 约 428 行。`REQUIRED_FILES`/`OPTIONAL_PROJECTION_FILES`（87 行）决策留原文件（D3），不计入抽出量。

### A.9 边界小结

**明确抽出**：§A.1 全部 11 函数（含 §A.5a 的 5 个私有 helper）。
**边界决策**：`_manifest_artifact_entries`(D2 抽)、`PLUGIN_SCOPE_DIRS`(D1 留)、`REQUIRED_FILES`/`OPTIONAL_PROJECTION_FILES`(D3 留)、Check 11 打印段(D4 留)。
**明确排除**：§A.2 三个跨域「manifest」命名函数。

---

## 变更记录

| 日期 | 版本 | 变更 | 作者 |
| --- | --- | --- | --- |
| 2026-06-26 | 0.1 | 初稿（REQ-102 规划入账，基于 Explore 实测勘察）| Coordinator |
