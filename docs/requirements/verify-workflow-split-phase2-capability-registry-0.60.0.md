# verify_workflow.py 拆分 Phase 2 — 抽出 capability-registry 域 (0.60.0)

> **任务**: REQ-103 / AUDIT-123（规划入账）
> **日期**: 2026-06-26
> **触发**: DEC-083 路线图第 (3) 项——verify_workflow.py 渐进式按 check 域拆分，0.60.0 为 Phase 2
> **前置**: FIX-153（Phase 1 manifest 域已发布 0.59.0）、AUDIT-121、RISK-039
> **性质**: 需求 + 设计文档（治理记录范畴）。实现阶段 spawn Governance Developer（产品代码范畴）。
> **决策依据**: DEC-083、AUDIT-121 F1、Phase 1 (FIX-153/REQ-102) 建立的方法论

---

## 0. 事实纪律声明

本文档遵循 AUDIT-117「前提事实约束」纪律。所有事实结论均有实测证据；capability-registry 域边界基于 2026-06-26 Explore sub-agent 实测勘察报告（附录 A 全文引用）。

实测基线 commit：master HEAD（v0.59.0 之后，e3cbe8d）。verify_workflow.py 实测 20,516 行（Phase 1 manifest 域抽出后的状态）。

---

## 1. 背景与动机

### 1.1 为什么 Phase 2 选 capability-registry 域

DEC-083 路线图要求 0.59.0~0.64.0 渐进式拆分，每版拆 1~2 域。Explore sub-agent 实测了 4 个候选域（release / governance / agent / capability-registry），按"边界清晰度 + 规模适中 + 自包含可测 + 方法论延续性"4 标准排序，**capability-registry 排名第一**：

1. **与 Phase 1 manifest 域完美同构**——都是"registry schema 校验"模式（1 个主 check 函数 + 专用常量簇 + 专用 helper）。机械搬迁方法论可逐字套用 Phase 1 已建立的模板。
2. **边界最清晰**——`check_capability_registry` + `_capability_registry_text_values` + 7 个 `CAPABILITY_REGISTRY_*` 常量，全部仅本域使用，零跨域私有依赖。
3. **理顺 `_manifest_artifact_entries` 共享路径**——Phase 1 把 `_manifest_artifact_entries` 迁到 manifest.py 后，它被 3 个 registry 域调用。capability-registry 是其中之一（line 2732），抽出后该调用点随域迁出，调用路径自然落位。
4. **风险为零**——规模虽偏小（~200 行），但作为"方法论延续 + 共享路径理顺"的版本，价值在质量而非体量。

### 1.2 不做什么（边界）

- **不拆其它域**——release（14 路扇出聚合门面，非独立域）、governance（1,133 行 print orchestrator）、agent/adapter（与 runtime 域共享常量，留 0.61.0+ 成对拆分）。勘察报告已排除。
- **不重写架构**——渐进式拆分，非分层重写。
- **不改 54 个 CLI 命令契约**——`check-capability-registry` 的参数、退出码、输出格式必须逐字不变。
- **不引入 src/ layout / pyproject.toml / ruff / mypy**——F2 现代工程基础设施留 0.64.0。
- **不关闭 RISK-039**——关闭需外部宿主项目验证（Phase 2 是拆分 2/6，非完成）。
- **不移动共享通用 helper**——`_is_valid_string_list`（21 处）、`_line_has_scoped_claim_negation`（18 处）保留在 verify_workflow.py，capability_registry.py 通过 import 引用。

---

## 2. capability-registry 域事实清单（实测）

来源：2026-06-26 Explore 勘察报告（附录 A）。

### 2.1 核心函数（明确属于 capability-registry 域）

| 函数 | 行号 | 行数 | 归属判定 |
| --- | --- | --- | --- |
| `_capability_registry_text_values(value)` | 2675-2683 | 9 | capability-registry 域（仅本域调用，5 次内部递归）|
| `check_capability_registry(root=None)` | 2690-2809 | 120 | capability-registry 域 |
| `cmd_check_capability_registry(args)` | 19172-19191 | 21 | capability-registry 域（CLI 入口）|

### 2.2 域专用常量（全部仅本域使用）

| 常量 | 定义行 | verify_workflow.py 内使用 |
| --- | --- | --- |
| `CAPABILITY_REGISTRY_PATH` | 1758 | 1（**仅定义未被引用——死常量**，搬迁时一并归位清理）|
| `CAPABILITY_REGISTRY_ALLOWED_KINDS` | 2171 | 4（全在 2713/2714/2766）|
| `CAPABILITY_REGISTRY_ALLOWED_STATUSES` | 2181 | 4 |
| `CAPABILITY_REGISTRY_REQUIRED_FIELDS` | 2189 | 2 |
| `CAPABILITY_REGISTRY_REQUIRED_KINDS` | 2200 | 2 |
| `CAPABILITY_REGISTRY_BOUNDARY_TOKENS` | 2210 | 2 |
| `CAPABILITY_REGISTRY_FORBIDDEN_OVERCLAIMS` | 2220 | 2 |

### 2.3 共享依赖（被多域调用，必须保留 import）

| 依赖 | 定义行 | capability 域调用 | 非capability 域调用 | 处置 |
| --- | --- | --- | --- | --- |
| `_is_valid_string_list` | 2686 | check_capability_registry 内 | 全文 **21 处** | **必留** verify_workflow.py（通用 validator，capability_registry.py import）|
| `_line_has_scoped_claim_negation` | — | check_capability_registry 内 | 全文 **18 处** | **必留**（no-overclaim 通用 helper）|
| `_manifest_artifact_entries` | `checks/manifest.py`（Phase 1 迁出）| line 2732 | lifecycle-registry(2843) + governance-pack(4159) | **import from checks.manifest**（Phase 1 已建立委托）|
| `_display_path` | 27 | — | 全文 142 处 | **必留 common** |
| `ROOT` | 21 | check_capability_registry 内 | 全局 | 通过 `_vw()` 或直接 import |

### 2.4 CLI / dispatch 接入点

- **argparse 注册**：`check-capability-registry` parser（parser 段）。
- **dispatch 注册**：`"check-capability-registry": cmd_check_capability_registry`（dispatch map line ~20484）。
- **Check 28k（governance）**：`cmd_check_governance` 的 Check 28k 子项打印段调用 `check_capability_registry()`——走 import 委托，与 Phase 1 manifest 委托模式一致。

### 2.5 边界澄清

`cmd_capability_context`（line 10126）用 `discover_capability_context`，是**独立的 capability-context 选择机制**，与 `check_capability_registry`（FIX-116 schema 校验）**无函数级共享**——不属本域，不抽出。

---

## 3. 设计决策

### D1 — 7 个 `CAPABILITY_REGISTRY_*` 常量全部迁到 capability_registry.py

**事实**：7 个常量全部仅 capability-registry 域使用（`CAPABILITY_REGISTRY_PATH` 是死常量，仅定义未被引用）。

**决策**：**全部迁**到 `infra/checks/capability_registry.py`。包括死常量 `CAPABILITY_REGISTRY_PATH`（一并归位清理，迁入后可保留或删除——实现时决定，倾向保留以维持 registry 常量簇完整性）。

**原因**：与 Phase 1 manifest 域 `_manifest_artifact_entries` 迁出同构——域专用数据随域走。死常量一并归位，避免散落。

### D2 — `_is_valid_string_list` / `_line_has_scoped_claim_negation` 保留在 verify_workflow.py

**事实**：这两个 helper 是通用 validator（分别 21 处、18 处跨域调用），非 capability-registry 域专用。

**决策**：**留**。capability_registry.py 通过 `_vw()` 延迟 import 引用（沿用 Phase 1 manifest.py 的 `_vw()` 模式）。

**原因**：迁移通用 helper 会引入反向依赖链（其它 20+ 调用者要 import capability_registry.py），违背渐进式拆分原则。通用 helper 留原文件，等 common 模块建立（0.64.0+）统一安置。

### D3 — `check_capability_registry` 内的 `_manifest_artifact_entries` 调用改 import

**事实**：line 2732 调用 `_manifest_artifact_entries`（Phase 1 已迁到 checks/manifest.py）。

**决策**：capability_registry.py 顶部 `from checks.manifest import _manifest_artifact_entries`，或通过 `_vw()._manifest_artifact_entries`（后者更一致，但前者更直接）。

**实现选择**：倾向 `from checks.manifest import _manifest_artifact_entries`——因为 manifest.py 已稳定，跨子包 import 是 check 域间的自然协作。若引发循环 import（checks.manifest → verify_workflow → checks.capability_registry → checks.manifest），降级为 `_vw()` 延迟。

### D4 — `cmd_check_capability_registry` 迁移到 capability_registry.py，verify_workflow.py 委托

**决策**：与 Phase 1 D5 同构——cmd 函数迁移，verify_workflow.py 的 dispatch 注册引用 import 来的函数。

### D5 — 目标文件路径与包结构

**决策**：新建 `infra/checks/capability_registry.py`（`infra/checks/__init__.py` 已存在，Phase 1 已建子包）。

**import 方案**：capability_registry.py 用 `_vw()` 延迟 import 访问 verify_workflow 的共享 helper（`_is_valid_string_list` / `_line_has_scoped_claim_negation` / `_display_path` / `ROOT`），沿用 Phase 1 manifest.py 已验证的模式（含 `_VW_CACHE` 缓存）。`_manifest_artifact_entries` 用 `from checks.manifest import`（D3）。

---

## 4. 实现规格（交 Governance Developer）

### 4.1 文件变更清单

| 文件 | 操作 | 内容 |
| --- | --- | --- |
| `infra/checks/capability_registry.py` | **新建** | §2.1 全部函数 + §2.2 全部常量 + §2.3 必要 import |
| `infra/verify_workflow.py` | **修改** | 删除迁出函数/常量定义；新增 `from checks.capability_registry import ...`；dispatch/argparse 注册保留但引用迁出函数 |
| `core/manifest.json` | **修改** | 登记 `infra/checks/capability_registry.py` |

### 4.2 capability_registry.py 内容骨架

```python
"""Capability-registry domain checks — extracted from verify_workflow.py in 0.60.0.

Scope (DEC-083 Phase 2 / REQ-103): capability-registry.json schema validation
(FIX-116). Same registry-schema-check pattern as the manifest domain (Phase 1).
Shared helpers (_is_valid_string_list, _line_has_scoped_claim_negation,
_display_path, ROOT) reached via deferred _vw() reference, same as manifest.py.
_manifest_artifact_entries imported from checks.manifest (Phase 1 sibling).
"""

# 域专用常量（随域迁入）
CAPABILITY_REGISTRY_PATH = "..."
CAPABILITY_REGISTRY_ALLOWED_KINDS = (...)
CAPABILITY_REGISTRY_ALLOWED_STATUSES = (...)
CAPABILITY_REGISTRY_REQUIRED_FIELDS = (...)
CAPABILITY_REGISTRY_REQUIRED_KINDS = (...)
CAPABILITY_REGISTRY_BOUNDARY_TOKENS = (...)
CAPABILITY_REGISTRY_FORBIDDEN_OVERCLAIMS = (...)

# Shared-helper access (deferred to avoid import cycle) — 沿用 Phase 1 manifest.py 模式
def _vw(): ...

def _is_valid_string_list(value): return _vw()._is_valid_string_list(value)
def _line_has_scoped_claim_negation(...): return _vw()._line_has_scoped_claim_negation(...)
def _display_path(path, root=None): return _vw()._display_path(path, root)
def _root(): return _vw().ROOT

# 跨 check 域 import（D3）
from checks.manifest import _manifest_artifact_entries

# 域专用 helper
def _capability_registry_text_values(value): ...

# 核心 check 函数
def check_capability_registry(root=None): ...

# CLI 入口（D4）
def cmd_check_capability_registry(args): ...
```

### 4.3 verify_workflow.py 改动点（最小化）

```python
# 顶部新增 import（紧邻 Phase 1 manifest 委托块）
from checks.capability_registry import (
    check_capability_registry,
    cmd_check_capability_registry,
    _capability_registry_text_values,
    # 常量不 re-export（域专用，迁出后 verify_workflow.py 不再需要）
)

# 删除 7 个 CAPABILITY_REGISTRY_* 常量定义（1758, 2171, 2181, 2189, 2200, 2210, 2220）
# 删除 _capability_registry_text_values 定义（2675）
# 删除 check_capability_registry 定义（2690）
# 删除 cmd_check_capability_registry 定义（19172）
# dispatch dict（~20484）保持不变——引用 import 来的 cmd_check_capability_registry
# argparse 注册保持不变
# Check 28k（governance）的 check_capability_registry() 调用走 import 委托
```

### 4.4 import 路径方案（沿用 Phase 1 经验）

Phase 1 已验证 `_vw()` 延迟 import（带 `_VW_CACHE` 缓存）规避循环依赖。Phase 2 沿用：
- `_is_valid_string_list` / `_line_has_scoped_claim_negation` / `_display_path` / `ROOT` → `_vw()` 延迟
- `_manifest_artifact_entries` → `from checks.manifest import`（checks 子包内 sibling import，不经过 verify_workflow，无循环风险）

### 4.5 验收标准（沿用 Phase 1 7 项门禁）

| 门禁 | 命令 | 期望 |
| --- | --- | --- |
| 编译 | `python -m py_compile infra/checks/capability_registry.py infra/verify_workflow.py` | exit 0 |
| capability-registry | `python verify_workflow.py check-capability-registry --fail-on-issues` | exit 0 |
| CLI 契约 | `check-capability-registry` 输出与拆分前逐字 diff | 无差异 |
| ArchGuard 模块大小 | `check-architecture-health` | capability_registry.py 不超阈值；verify_workflow.py 较拆分前净减 |
| Check 28k governance | `check-governance` | Check 28k capability registry 仍 PASS |
| 全量 unittest | `pytest infra/tests/ -q` | 全部 passed，0 回归（基线 629 passed）|
| Check 11 verify | `verify` | capability-registry 相关项 PASS |

---

## 5. ArchGuard 守护契约（延续 Phase 1）

| 拆分风险 | ArchGuard 检测项 | 期望信号 |
| --- | --- | --- |
| capability_registry.py 膨胀 | module_size | 低于所有阈值（~200 行远低于 error 阈值）|
| verify_workflow.py 没真正减小 | module_size | 较 0.59.0 基线（20,516）净减 |
| 引入重复代码 | duplicate_code / complexity | 不新增重复块 |

---

## 6. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
| --- | --- | --- | --- |
| `from checks.manifest import` 与 `_vw()` 混用引发 import 顺序问题 | 低 | 阻塞实现 | Phase 1 已验证 checks 子包 sibling import 可靠；py_compile 实测 |
| manifest.json 登记遗漏致 check-manifest-consistency FAIL | 中 | 门禁阻塞 | §4.1 已列登记；实现时跑 check 确认 |
| 迁出死常量 `CAPABILITY_REGISTRY_PATH` 后有隐藏引用 | 极低 | NameError | Explore 已确认仅定义未引用；grep 复核 |

---

## 7. 任务分解（注册到 plan-tracker）

| ID | 类型 | 描述 | 前置 |
| --- | --- | --- | --- |
| **REQ-103** | 需求 | 本文档（capability-registry 域拆分需求/设计）| AUDIT-123, DEC-083, FIX-153 |
| **FIX-154** | 实现 | capability-registry 域抽出实现 | REQ-103, DEC-087 授权 |
| **REL-046** | 发布 | 发布 0.60.0 | FIX-154✅, release gate 全绿 |

### DEC-087 候选（实现授权路径）

沿用 DEC-085/DEC-086 先例（harness 仍仅只读 Explore sub-agent）。本版**默认沿用**主 agent 直写 + 事后 Explore 审查，除非用户指示。

---

## 8. 与 RISK-039 关闭标准的关系

0.60.0 Phase 2 是拆分 **2/6**，非完成。RISK-039 关闭需：
- Phase 1-6 全部完成（0.59.0~0.64.0）
- 1 个外部宿主项目验证 ArchGuard

**0.60.0 不关闭 RISK-039。**

---

## 附录 A — capability-registry 域实测勘察报告（2026-06-26 Explore sub-agent）

### A.0 基线
- verify_workflow.py: 20,516 行（0.59.0 post-release）
- Phase 1 已落地: `infra/checks/manifest.py`（517 行, 12 函数）

### A.1 四候选域测绘摘要

| 候选域 | 规模 | 边界清晰度 | 排名 |
| --- | --- | --- | --- |
| **capability-registry** | ~200 行（偏小但风险零） | 最清晰（1 check + 1 helper + 7 专用常量）| **1（推荐）** |
| agent/adapter | ~565 行 | 清晰（5 validator）但与 runtime 域共享常量 | 2（0.61.0+ 候选）|
| release | ~1,050 行 | 差（14 路扇出聚合门面，非独立域）| 3（排除）|
| governance | 1,133 行 | 差（print orchestrator，无域专用 helper）| 4（排除）|

### A.2 `_manifest_artifact_entries` 跨域耦合热力图

3 个调用者（高度同构——都是 "registry → 读 manifest → 过滤 artifact 条目 → 校验"）：
- **2732** `check_capability_registry`（capability-registry 域）← **本域抽出时随迁**
- 2843 `_lifecycle_registry_manifest_issues`（lifecycle-registry 域）← 留 0.61.0+ 拆 lifecycle 时带走
- 4159 `check_governance_packs`（governance-pack 域）← 留 0.62.0+ 拆 governance-pack 时带走

**结论**：capability-registry 抽出把第一个跨域调用点正式归位，是最自然理顺共享路径的域。

### A.3 capability-registry 域边界候选

**明确抽出（机械搬迁，零设计决策）**：`check_capability_registry`(2690)、`_capability_registry_text_values`(2675)、`cmd_check_capability_registry`(19172)、7 个 `CAPABILITY_REGISTRY_*` 常量、`_manifest_artifact_entries` 调用点(2732)。

**边界模糊（保留共享）**：`_is_valid_string_list`(2686, 21 处)、`_line_has_scoped_claim_negation`(18 处)、`_display_path`(142 处)、`ROOT`。

---

## 变更记录

| 日期 | 版本 | 变更 | 作者 |
| --- | --- | --- | --- |
| 2026-06-26 | 0.1 | 初稿（REQ-103 规划入账，基于 Explore 实测勘察）| Coordinator |
