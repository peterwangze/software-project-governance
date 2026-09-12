"""FEAT-025 Slice-1 — quick-scan 检查段事实源注册表（70 段逐段一行）。

独立数据模块：本文件是 quick 选择器的**事实源声明表**，不导入、不修改、不被
巨石编排体 ``verify_workflow.py`` 引用（FX-195 §255「载体禁写入巨石编排体」，
FEAT-019 先例：主文件 +18 行；本切片对主文件零修改）。禁止在本模块登记 CLI
子命令或 argparse 入口——quick 编排属 Slice-2。

设计事实源（MUST 引用，不得改写）：

* ``docs/requirements/quickscan-evaluation-0.79.0.md``（FX-195）
  - §3.1 检查范围：C1 排除 25 段 / C2 保留 41 段 / C3 待判定 4 段；
  - §6「Slice-1 检查段事实源注册表」验收要点 ①②③；
  - §136（源文件行号）C3 行：28g / 28j / 28l / 29「默认保留 quick 面
    （fail-safe to more checks）+ 实现任务逐段入表时裁决」；
  - §250 验收原文锚定；§255 与 REFACTOR-light-registry 的前置关系。
* ``docs/requirements/architecture-evolution-0.80.0.md`` §3.6 ``CheckSpec``
  契约形状（``check_id`` / ``domain`` / ``loader`` / ``input_deps`` /
  ``severity_floor`` / ``modes``）——本表行 schema 取其子集，Phase-2 平移零语义分叉。
* FEAT-020 冻结快照（freeze commit ``c92bf5d``）——
  ``infra/contract_matrix/snapshots.json`` ``faces.check_segments``
  （``count=70`` + ``ids``）为 70 段 id 的唯一权威清单。
* FIX-270 机判 product-gate 声明（``verify_workflow.py``
  ``_PLUGIN_PRODUCT_CHECK_IDS``，现行 25 段）——排除集与它恒等，保证
  quick 政策与宿主 product-gate 正交（quickscan-evaluation §7.2 QR-5）。

行 schema（``⊂ CheckSpec`` 字段集，见 ``SEGMENT_SPEC_FIELDS``）::

    check_id    — CheckID（冻结清单，§3.5）
    domain      — 治理领域（evidence/risk/review/...）
    input_deps  — 输入路径清单；每个条目形如 ``<root>:<kind>:<path-or-expr>``，
                  root ∈ {plugin, host}——root 标签**即**事实源根声明，
                  ``fact_source_root()`` 由它纯函数派生（无第二份真相）。
    modes       — 模式政策面：``("full","quick")`` 保留 /
                  ``("full","not-quick:<REASON_CODE>")`` 排除。
                  ``not-quick:<CODE>`` 是 Slice-1 引入的**扩展词汇**：§3.6 L221
                  示例只列 ``("full","quick","domain:<name>")``，本 token 沿用的是
                  其**形态约定**，不是既定词汇。Phase-2 平移口径由
                  REFACTOR-light-registry / REFACTOR-quickscan-orchestration 定义
                  （quickscan-evaluation §6 L253「平移 Slice-1 注册表为
                  CheckSpec.input_deps」）；本切片不预设映射，防第二份真相。

派生列（不落表，全部是以上四列的纯函数，避免漂移）：

* ``fact_source_root`` = dep root 标签的并集 → plugin / host / mixed / unknown；
* ``exclusion_reason_code`` = modes 的 ``not-quick:`` 标签（排除原因代码常量表
  ``EXCLUSION_REASON_CODES`` 定义代码语义）；
* ``quick face`` = 未携带 ``not-quick:`` 的段（45 段）；排除面 25 段。

事实源根的证据方法（代码级，非推测）：对真实引擎
``_run_full_engine_checks`` 做一次性插桩运行，拦截 banner 打印把每次
文件/目录/git 访问归属到所在检查段，产出 70 段「实际读取路径」清单；再逐段
回读代码确认锚定根（``ROOT``/``PLUGIN_ROOT`` vs ``SAMPLE_PATH``/``EVIDENCE_PATH``/
``GOVERNANCE_DIR``/``HOST_PROJECT_ROOT``）。C3 四段的逐段裁决与依据见
``C3_ADJUDICATION``。

已知披露（事实登记，非缺陷）：

1. **双根排除段（24 / 31）**：两段的事实源同时触及插件面与宿主面，却被 FIX-270
   与 §3.1 C1 登记为插件产品自检（排除）。本表沿用该政策，并以
   ``dual_root_disclosures()`` 显式披露，供 Phase-2 闭包裁决——
   - **24**：``check_version_consistency()`` → ``version_checks.check_version_consistency(ROOT,
     GOVERNANCE_DIR.parent)`` 同时吃插件版本资产与宿主 ``.governance/plan-tracker.md``
     的 ``工作流版本`` 投影；
   - **31**：``checks/loop_runtime_claims.py`` 的 ``_owner_roots()`` 显式返回
     ``("product_root", …)`` 与 ``("host_root", host_root, HOT_PATHS)`` 两组根，
     且 ``scan_mode ∈ {"product_release","installed_host"}``。
2. **28o ArchGuard 根巧合**：ArchGuard 四门的树锚是 ``ROOT``（插件包根）；dogfood
   下 ``ROOT == HOST_PROJECT_ROOT``，通用树遍历会扫到 ``.governance/**`` 的代码
   文件——这是根巧合，不是声明依赖，故 ``input_deps`` 只声明 ``plugin:tree``，
   避免 Phase-2 闭包被治理数据变更误触发。
3. **实现期新发现**：``18h`` / ``28`` / ``28j`` / ``28l`` 的事实源根为插件面，但
   不在 FIX-270 ``_PLUGIN_PRODUCT_CHECK_IDS`` 内（宿主模式不跳过）。按 §3.1 C3
   fail-safe 原则**保留** quick 面，并经 ``plugin_face_not_product_gated()`` 披露
   给后续 product-gate 复核。
4. **排除集机判锚定**：排除集 ≡ FIX-270 ``_PLUGIN_PRODUCT_CHECK_IDS``（25 段），
   即事实源根判据（§3.1 C1）与宿主 product-gate 政策同源，quick 排除面与
   宿主 product-skip 面正交（quickscan-evaluation §7.2 QR-5）。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields as dataclass_fields
from pathlib import Path

__all__ = [
    "C3_ADJUDICATED_SEGMENTS",
    "C3_ADJUDICATION",
    "C3_VERDICT_RETAIN",
    "CHECKSPEC_FIELDS",
    "DEP_KINDS",
    "DEP_ROOTS",
    "EXCLUSION_REASON_CODES",
    "FACT_SOURCE_HOST",
    "FACT_SOURCE_MIXED",
    "FACT_SOURCE_PLUGIN",
    "FACT_SOURCE_UNKNOWN",
    "FALLBACK_REASON_CODES",
    "MODE_FULL",
    "MODE_FULL_FALLBACK",
    "MODE_QUICK",
    "NOT_QUICK_PREFIX",
    "REASON_UNDECLARED_SEGMENT",
    "REASON_UNKNOWN_INPUT",
    "SEGMENTS",
    "SEGMENT_SPEC_FIELDS",
    "CompletenessReport",
    "ReconcileReport",
    "SegmentSpec",
    "all_segments",
    "discover_engine_segment_ids",
    "discover_product_gate_ids",
    "dual_root_disclosures",
    "excluded_ids",
    "exclusion_reason_code",
    "fact_source_root",
    "guard_completeness",
    "load_frozen_snapshot_ids",
    "plugin_face_not_product_gated",
    "quick_face_ids",
    "reconcile_snapshot",
    "registry_ids",
    "segment",
]

# ── 常量：模式政策面 token（§3.6 modes 文法）──────────────────────────────
MODE_FULL = "full"
MODE_QUICK = "quick"
NOT_QUICK_PREFIX = "not-quick:"

# 完整性守卫 fail-closed 回退目标（Slice-2 编排器消费；本切片只声明）。
MODE_FULL_FALLBACK = MODE_FULL

# ── 常量：事实源根取值 ───────────────────────────────────────────────────
FACT_SOURCE_PLUGIN = "plugin"
FACT_SOURCE_HOST = "host"
FACT_SOURCE_MIXED = "mixed"
FACT_SOURCE_UNKNOWN = "unknown"

# 输入依赖的 root 标签域 + kind 标签域（dep token = "<root>:<kind>:<target>"）。
DEP_ROOTS = (FACT_SOURCE_PLUGIN, FACT_SOURCE_HOST)
DEP_KINDS = {
    FACT_SOURCE_PLUGIN: ("asset", "tree", "git", "attestation"),
    FACT_SOURCE_HOST: ("governance", "repo", "git"),
}

# ── 常量表：排除原因代码（"含排除原因代码常量表"，§6 Slice-1 验收）──────────
# 代码分组逐条对应 FIX-270 ``_PLUGIN_PRODUCT_CHECK_IDS`` 的源码注释分组。
EXCLUSION_REASON_CODES = {
    "PLUGIN_GIT_FACT_SOURCE": (
        "插件 git 作为事实源（-C ROOT 而非宿主仓库）：提交历史/改动面只对插件自身成立"
    ),
    "PLUGIN_PACKAGE_ASSET": (
        "插件包本体文件作为事实源（manifest/投影 fixtures/插件 docs/版本资产/注入锚点/入口文档）"
    ),
    "PLUGIN_TREE_SCAN": (
        "插件包树扫描或插件 infra AST 扫描作为事实源（ArchGuard 四门 + loop wiring call sites）"
    ),
    "PLUGIN_CLAIM_ATTESTATION": (
        "插件树扫描 + identity attestation 作为事实源（loop runtime claim gate）"
    ),
}

# ── 常量表：守卫/回退原因代码（非排除政策；§2.4 四态契约 not-run/undetermined）──
REASON_UNDECLARED_SEGMENT = "UNDECLARED_SEGMENT"
REASON_UNKNOWN_INPUT = "UNKNOWN_INPUT"
FALLBACK_REASON_CODES = {
    REASON_UNDECLARED_SEGMENT: "引擎存在但注册表未声明的段 → 告警 + fail-closed 回退 full",
    REASON_UNKNOWN_INPUT: "段未声明或输入未知 → 未知回退 full（§9.3 原文）",
}

# ── §3.6 CheckSpec 契约字段集（Phase-2 平移目标形状）──────────────────────
CHECKSPEC_FIELDS = (
    "check_id",
    "domain",
    "loader",
    "input_deps",
    "severity_floor",
    "modes",
)


@dataclass(frozen=True)
class SegmentSpec:
    """一行注册项。字段名 ∈ §3.6 ``CheckSpec`` 字段集（本切片取 4 列子集）。"""

    check_id: str
    domain: str
    input_deps: tuple
    modes: tuple

    @property
    def fact_source_root(self):
        """事实源根：由 input_deps 的 root 标签纯函数派生（plugin/host/mixed）。"""
        return _derive_fact_source_root(self.input_deps)

    @property
    def excluded_from_quick(self):
        return MODE_QUICK not in self.modes

    @property
    def exclusion_reason_code(self):
        if not self.excluded_from_quick:
            return None
        for mode in self.modes:
            if mode.startswith(NOT_QUICK_PREFIX):
                return mode.split(":", 1)[1]
        return None

    def as_dict(self):
        """四列视图（字段名与 dataclass 字段一致，供机判对账）。"""
        return {
            "check_id": self.check_id,
            "domain": self.domain,
            "input_deps": self.input_deps,
            "modes": self.modes,
        }


SEGMENT_SPEC_FIELDS = tuple(f.name for f in dataclass_fields(SegmentSpec))

_RETAIN = (MODE_FULL, MODE_QUICK)


def _excluded(reason_code):
    """排除行的模式政策面 token（原因代码必须来自常量表）。"""
    if reason_code not in EXCLUSION_REASON_CODES:
        raise KeyError(f"unknown exclusion reason code: {reason_code}")
    return (MODE_FULL, NOT_QUICK_PREFIX + reason_code)


# ── 70 段事实源注册表（冻结快照 c92bf5d 顺序；FEAT-020 faces.check_segments）──
SEGMENTS = (
    SegmentSpec("1", "evidence", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/archive/evidence/**",
    ), _RETAIN),
    SegmentSpec("2", "risk", (
        "host:governance:.governance/risk-log.md",
    ), _RETAIN),
    SegmentSpec("3", "gate", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/archive/**",
    ), _RETAIN),
    SegmentSpec("4", "evidence", (
        "host:governance:.governance/evidence-log.md",
    ), _RETAIN),
    SegmentSpec("5", "protocol", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
    ), _RETAIN),
    SegmentSpec("6", "audit", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
    ), _RETAIN),
    # FIX-270：「插件 git 作为事实源（-C ROOT 而非宿主仓库）」
    SegmentSpec("7", "commit", (
        "plugin:git:log --format=%H %s -20",
    ), _excluded("PLUGIN_GIT_FACT_SOURCE")),
    SegmentSpec("8", "risk", (
        "host:governance:.governance/risk-log.md",
    ), _RETAIN),
    SegmentSpec("9", "task", (
        "host:governance:.governance/plan-tracker.md",
    ), _RETAIN),
    # 插件 source 扫描（入口文档 + commands + 插件 references）
    SegmentSpec("10", "protocol", (
        "plugin:asset:AGENTS.md",
        "plugin:asset:CLAUDE.md",
        "plugin:asset:commands/**",
        "plugin:asset:docs/**",
        "plugin:asset:skills/software-project-governance/references/**",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("11", "manifest", (
        "plugin:asset:package.json",
        "plugin:asset:.claude-plugin/**",
        "plugin:asset:.codex-plugin/**",
        "plugin:asset:.chrys-plugin/**",
        "plugin:asset:.zcode-plugin/**",
        "plugin:asset:.agents/plugins/**",
        "plugin:asset:AGENTS.md",
        "plugin:asset:CLAUDE.md",
        "plugin:asset:skills/**",
        "plugin:asset:agents/**",
        "plugin:asset:commands/**",
        "plugin:asset:adapters/**",
        "plugin:asset:docs/**",
        "plugin:asset:tests/**",
        "plugin:asset:web/**",
        "plugin:asset:agent-presets/**",
        "plugin:asset:project/**",
        "plugin:git:ls-files --cached",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("12", "manifest", (
        "plugin:asset:README.md",
        "plugin:asset:package.json",
        "plugin:asset:.claude-plugin/**",
        "plugin:asset:.codex-plugin/**",
        "plugin:asset:.chrys-plugin/**",
        "plugin:asset:.zcode-plugin/**",
        "plugin:asset:skills/**",
        "plugin:asset:commands/**",
        "plugin:asset:agents/**",
        "plugin:asset:docs/**",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("13", "registries", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/decision-log.md",
        "host:governance:.governance/risk-log.md",
        "host:governance:.governance/archive/**",
    ), _RETAIN),
    SegmentSpec("14", "structure", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/decision-log.md",
        "plugin:asset:skills/software-project-governance/SKILL.md",
        "plugin:asset:skills/software-project-governance/core/manifest.json",
    ), _RETAIN),
    SegmentSpec("15", "commit", (
        "plugin:git:log --format=%H%x00%s -20 --no-merges",
        "plugin:git:show --stat",
    ), _excluded("PLUGIN_GIT_FACT_SOURCE")),
    SegmentSpec("16", "requirements", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
    ), _RETAIN),
    SegmentSpec("17", "requirements", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
    ), _RETAIN),
    SegmentSpec("18", "evidence", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
    ), _RETAIN),
    SegmentSpec("18b", "evidence", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
    ), _RETAIN),
    SegmentSpec("18c", "planning", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/execution-packets.json",
    ), _RETAIN),
    SegmentSpec("18d", "requirements", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/execution-packets.json",
    ), _RETAIN),
    SegmentSpec("18e", "requirements", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/execution-packets.json",
    ), _RETAIN),
    SegmentSpec("18f", "quality", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/execution-packets.json",
    ), _RETAIN),
    SegmentSpec("18g", "planning", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/execution-packets.json",
    ), _RETAIN),
    # 事实源 = 插件 core templates（未入 FIX-270 product-gate；fail-safe 保留）
    SegmentSpec("18h", "planning", (
        "plugin:asset:skills/software-project-governance/core/templates/deterministic-scaffolds/**",
    ), _RETAIN),
    SegmentSpec("18i", "protocol", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/execution-packets.json",
        "plugin:asset:skills/software-project-governance/references/interaction-boundary.md",
        "plugin:asset:skills/software-project-governance/core/templates/user-interruption-policy.md",
    ), _RETAIN),
    SegmentSpec("19", "review", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/review-*.md",
    ), _RETAIN),
    SegmentSpec("20", "review", (
        "host:governance:.governance/plan-tracker.md",
    ), _RETAIN),
    SegmentSpec("21", "review", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/review-*.md",
    ), _RETAIN),
    SegmentSpec("22", "review", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/review-*.md",
    ), _RETAIN),
    SegmentSpec("23", "profile", (
        "host:governance:.governance/plan-tracker.md",
    ), _RETAIN),
    SegmentSpec("24", "version", (
        "host:governance:.governance/plan-tracker.md",
        "plugin:asset:skills/software-project-governance/SKILL.md",
        "plugin:asset:skills/software-project-governance/core/manifest.json",
        "plugin:asset:skills/software-project-governance/core/version-projections.json",
        "plugin:asset:.claude-plugin/plugin.json",
        "plugin:asset:.codex-plugin/plugin.json",
        "plugin:asset:.chrys-plugin/plugin.json",
        "plugin:asset:.zcode-plugin/plugin.json",
        "plugin:asset:AGENTS.md",
        "plugin:asset:CLAUDE.md",
        "plugin:git:ls-files -- AGENTS.md CLAUDE.md",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("25", "git", (
        "host:git:ls-files --others --exclude-standard",
    ), _RETAIN),
    SegmentSpec("26", "locks", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/agent-locks.json",
    ), _RETAIN),
    SegmentSpec("27", "archive", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/decision-log.md",
        "host:governance:.governance/risk-log.md",
        "host:governance:.governance/archive/**",
        "plugin:asset:skills/software-project-governance/core/releases/**",
        "plugin:asset:skills/software-project-governance/infra/archive.py",
    ), _RETAIN),
    SegmentSpec("28", "review", (
        "plugin:asset:commands/governance-review.md",
        "plugin:asset:project/e2e-test-project/commands/governance-review.md",
    ), _RETAIN),
    SegmentSpec("28b", "projection", (
        "plugin:asset:skills/**",
        "plugin:asset:package.json",
        "plugin:asset:.claude-plugin/**",
        "plugin:asset:adapters/dsh/**",
        "plugin:asset:project/e2e-test-project/**",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("28c", "governance-data", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/session-snapshot.md",
    ), _RETAIN),
    SegmentSpec("28d", "capability", (
        "plugin:asset:docs/requirements/runtime-readiness-matrix-0.43.0.md",
        "plugin:asset:adapters/*/adapter-manifest.json",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("28e", "capability", (
        "plugin:asset:docs/requirements/first-session-measurement-0.43.0.md",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("28f", "capability", (
        "plugin:asset:skills/software-project-governance/core/governance-packs.json",
        "plugin:asset:docs/requirements/composable-governance-packs-0.44.0.md",
        "plugin:asset:skills/*/SKILL.md",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    # ── C3 待判定 ①：事实源根 = 混合（宿主治理热文件 + 宿主 git + 插件 command 契约文档）──
    SegmentSpec("28g", "context", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/session-snapshot.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/risk-log.md",
        "host:governance:.governance/flow-unit-runtime.json",
        "host:git:status --short --untracked-files=all",
        "host:git:log --oneline -5",
        "plugin:asset:commands/governance.md",
        "plugin:asset:commands/governance-status.md",
    ), _RETAIN),
    SegmentSpec("28h", "capability", (
        "plugin:asset:README.md",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("28i", "capability", (
        "plugin:asset:commands/governance.md",
        "plugin:asset:commands/governance-status.md",
        "plugin:asset:docs/requirements/composable-governance-packs-0.44.0.md",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    # ── C3 待判定 ②：事实源根 = 插件面（纯插件资产）──
    SegmentSpec("28j", "capability", (
        "plugin:asset:.claude-plugin/plugin.json",
        "plugin:asset:.codex-plugin/plugin.json",
        "plugin:asset:AGENTS.md",
        "plugin:asset:skills/software-project-governance/SKILL.md",
        "plugin:asset:skills/software-project-governance/core/governance-packs.json",
        "plugin:asset:skills/software-project-governance/core/capability-registry.json",
        "plugin:asset:skills/software-project-governance/infra/TOOLS.md",
        "plugin:asset:skills/software-project-governance/infra/verify_workflow.py",
        "plugin:asset:docs/requirements/capability-discovery-orchestration-0.45.0.md",
        "plugin:asset:docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md",
        "plugin:asset:docs/requirements/runtime-readiness-matrix-0.43.0.md",
    ), _RETAIN),
    SegmentSpec("28k", "capability", (
        "plugin:asset:skills/software-project-governance/core/capability-registry.json",
        "plugin:asset:skills/software-project-governance/core/manifest.json",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    # ── C3 待判定 ③：事实源根 = 插件面（纯插件资产）──
    SegmentSpec("28l", "capability", (
        "plugin:asset:.claude-plugin/plugin.json",
        "plugin:asset:.codex-plugin/plugin.json",
        "plugin:asset:AGENTS.md",
        "plugin:asset:skills/software-project-governance/SKILL.md",
        "plugin:asset:skills/software-project-governance/core/capability-registry.json",
        "plugin:asset:skills/software-project-governance/infra/TOOLS.md",
        "plugin:asset:skills/software-project-governance/infra/verify_workflow.py",
        "plugin:asset:docs/requirements/capability-discovery-orchestration-0.45.0.md",
    ), _RETAIN),
    SegmentSpec("28m", "distribution", (
        "plugin:asset:package.json",
        "plugin:asset:README.md",
        "plugin:asset:.claude-plugin/**",
        "plugin:asset:.agents/plugins/**",
        "plugin:asset:.github/workflows/ci.yml",
        "plugin:asset:skills/**",
        "plugin:git:ls-files --cached",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("28n", "distribution", (
        "plugin:asset:README.md",
        "plugin:asset:adapters/*/README.md",
        "plugin:asset:docs/requirements/mainstream-agent-loading-0.47.0.md",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("28o", "architecture", (
        "plugin:tree:.",
    ), _excluded("PLUGIN_TREE_SCAN")),
    SegmentSpec("28p", "architecture", (
        "plugin:tree:skills/software-project-governance/infra/**",
    ), _excluded("PLUGIN_TREE_SCAN")),
    SegmentSpec("28q", "architecture", (
        "plugin:tree:skills/software-project-governance/infra/**",
        "plugin:asset:skills/software-project-governance/core/architecture-health.json",
        "plugin:asset:skills/software-project-governance/core/technical-debt-ledger.md",
    ), _excluded("PLUGIN_TREE_SCAN")),
    SegmentSpec("28r", "architecture", (
        "plugin:tree:skills/software-project-governance/infra/**",
        "plugin:asset:skills/software-project-governance/core/architecture-health.json",
    ), _excluded("PLUGIN_TREE_SCAN")),
    SegmentSpec("28s", "governance-data", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/decision-log.md",
        "host:governance:.governance/risk-log.md",
        "plugin:asset:skills/software-project-governance/core/architecture-health.json",
    ), _RETAIN),
    SegmentSpec("28t", "documentation", (
        "plugin:asset:README.md",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("28u", "distribution", (
        "plugin:asset:adapters/dsh/launch.py",
        "plugin:asset:agent-presets/**",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("28v", "distribution", (
        "plugin:asset:agent-presets/**",
        "plugin:asset:lib/index.js",
        "plugin:asset:cordis.patch.yml",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    # ── C3 待判定 ④：事实源根 = 宿主面（宿主治理证据语料）──
    SegmentSpec("29", "protocol", (
        "host:governance:.governance/evidence-log.md",
    ), _RETAIN),
    SegmentSpec("30", "review", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/review-*.md",
        "plugin:asset:skills/software-project-governance/SKILL.md",
        "plugin:asset:skills/software-project-governance/references/methodology-routing.md",
    ), _RETAIN),
    SegmentSpec("30b", "loop", (
        "plugin:tree:skills/software-project-governance/infra/**",
    ), _excluded("PLUGIN_TREE_SCAN")),
    SegmentSpec("30c", "review", (
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/review-*.md",
        "plugin:tree:skills/software-project-governance/infra/**",
    ), _RETAIN),
    SegmentSpec("31", "loop", (
        "plugin:tree:skills/software-project-governance/**",
        "plugin:asset:skills/software-project-governance/core/loop-runtime-claim-allowlist.json",
        "plugin:asset:skills/software-project-governance/core/loop-runtime-claim-authority.json",
        "plugin:asset:skills/software-project-governance/references/loop-role-mapping.md",
        "plugin:attestation:identity attestation fixture snapshot",
        "host:governance:.governance/**",
    ), _excluded("PLUGIN_CLAIM_ATTESTATION")),
    SegmentSpec("32", "triage", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/change-triage/**",
        "plugin:asset:skills/software-project-governance/infra/change_triage.py",
    ), _RETAIN),
    SegmentSpec("33", "injection", (
        "plugin:asset:skills/software-project-governance/SKILL.md",
        "plugin:asset:adapters/dsh/AGENTS.md.template",
        "plugin:asset:agent-presets/governance/agent.cordis.yml.template",
    ), _excluded("PLUGIN_PACKAGE_ASSET")),
    SegmentSpec("34", "recommendation", (
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/session-snapshot.md",
    ), _RETAIN),
    SegmentSpec("35", "snapshot", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/session-snapshot.md",
        "host:governance:.governance/evidence-log.md",
        "host:git:ls-files -- .governance/",
    ), _RETAIN),
    SegmentSpec("36", "risk", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/risk-log.md",
        "host:governance:.governance/archive/**",
    ), _RETAIN),
    SegmentSpec("37", "release", (
        "host:governance:.governance/plan-tracker.md",
        "host:git:for-each-ref --sort=-creatordate refs/tags",
    ), _RETAIN),
    SegmentSpec("38", "ci", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/archive/**",
        "host:repo:.github/workflows/**",
        "host:git:remote -v",
    ), _RETAIN),
    SegmentSpec("39", "completion", (
        "host:governance:.governance/plan-tracker.md",
        "host:governance:.governance/evidence-log.md",
        "host:governance:.governance/change-triage/**",
    ), _RETAIN),
)

# ── C3 逐段裁决（FX-195 §136 C3 行 + 代码核验；默认保留 quick 面）──────────
C3_ADJUDICATED_SEGMENTS = ("28g", "28j", "28l", "29")
C3_VERDICT_RETAIN = "retain-quick"

C3_ADJUDICATION = {
    "28g": {
        "verdict": C3_VERDICT_RETAIN,
        "root": FACT_SOURCE_MIXED,
        "review": "FX-195 §136 C3 行 + 代码核验",
        "basis": (
            "check_governance_context() → discover_governance_context()："
            "_parse_plan_context_tasks/_parse_snapshot_context_tasks/_parse_evidence_context_tasks/"
            "_parse_context_open_risks 经 _context_file(root,…) 读 "
            ".governance/plan-tracker.md、.governance/session-snapshot.md、"
            ".governance/evidence-log.md、.governance/risk-log.md；"
            "_parse_git_status_context_tasks / _parse_recent_commit_context_facts 经 _run_context_git 跑 "
            "git status --short --untracked-files=all 与 git log --oneline -5；"
            "discover_flow_unit_runtime_context 读 .governance/flow-unit-runtime.json —— 宿主治理会话态主体；"
            "插件面部分 = 函数尾 docs 列表 root/commands/governance.md + root/commands/governance-status.md "
            "的契约 token 校验。故事实源根 = 混合（宿主主导）→ 保留。",
        ),
    },
    "28j": {
        "verdict": C3_VERDICT_RETAIN,
        "root": FACT_SOURCE_PLUGIN,
        "review": "FX-195 §136 C3 行 + 代码核验",
        "basis": (
            "check_capability_context() → discover_capability_context()：全部事实取自插件包本体——"
            "skills/software-project-governance/infra/verify_workflow.py（_capability_cli_registration_fact "
            "AST 解析 capability-context CLI 注册）、skills/software-project-governance/infra/TOOLS.md、"
            "skills/software-project-governance/core/governance-packs.json、"
            "skills/software-project-governance/core/capability-registry.json、"
            "docs/requirements/capability-discovery-orchestration-0.45.0.md、"
            "docs/requirements/codex-desktop-marketplace-e2e-0.45.0.md、"
            "docs/requirements/runtime-readiness-matrix-0.43.0.md；_capability_host_id 的 "
            ".claude-plugin/plugin.json、.codex-plugin/plugin.json、AGENTS.md、"
            "skills/software-project-governance/SKILL.md 同为插件包元数据。"
            "事实源根 = 插件面（零宿主 .governance 事实）；且 28j 不在 FIX-270 "
            "_PLUGIN_PRODUCT_CHECK_IDS 内（宿主模式不跳过）→ 按 §3.1 C3 fail-safe 默认保留，"
            "排除提案留 Phase-2 input_deps 闭包统一裁决。",
        ),
    },
    "28l": {
        "verdict": C3_VERDICT_RETAIN,
        "root": FACT_SOURCE_PLUGIN,
        "review": "FX-195 §136 C3 行 + 代码核验",
        "basis": (
            "check_host_capability_context() → discover_host_capability_context()：受限宿主场景事实取自"
            "插件包本体——skills/software-project-governance/infra/verify_workflow.py、"
            "skills/software-project-governance/infra/TOOLS.md、"
            "skills/software-project-governance/core/capability-registry.json、"
            "docs/requirements/capability-discovery-orchestration-0.45.0.md，"
            "外加 .claude-plugin/plugin.json、.codex-plugin/plugin.json、AGENTS.md、"
            "skills/software-project-governance/SKILL.md 元数据；"
            "函数名含 host 但其读的是「本机受限能力降级声明」类插件资产（无 .governance 读）。"
            "事实源根 = 插件面；不在 FIX-270 product-gate 清单内 → fail-safe 默认保留。",
        ),
    },
    "29": {
        "verdict": C3_VERDICT_RETAIN,
        "root": FACT_SOURCE_HOST,
        "review": "FX-195 §136 C3 行 + 代码核验",
        "basis": (
            "check_m5_runtime_triggers()（checks/review_domain.py）auto-discovery 分支只读 "
            "EVIDENCE_PATH = SAMPLE_PATH.parent/evidence-log.md（SAMPLE_PATH = "
            "HOST_PROJECT_ROOT/.governance/plan-tracker.md）→ .governance/evidence-log.md；"
            "FIX-178 已显式排除 session-snapshot.md；语料为空时降级 no-verdict（不 FAIL）。"
            "事实源根 = 宿主面（bootstrap 健康摘要的会话态目的域）→ 保留。",
        ),
    },
}


# ── 表查询 ──────────────────────────────────────────────────────────────
def _id_sort_key(check_id):
    match = re.match(r"^(\d+)(.*)$", check_id)
    return (0, int(match.group(1)), match.group(2)) if match else (1, 0, check_id)


def _duplicate_ids(check_id_seq):
    """Ids occurring more than once, in deterministic id-sort order.

    §4.1 R5「Check ID 唯一」为**零容忍**——注册表侧在导入期守卫，观察侧
    （census）在返回前守卫，两侧同构，重复即抛 ``ValueError``（FIX-304 F-3）。
    """
    seen = set()
    duplicates = set()
    for check_id in check_id_seq:
        if check_id in seen:
            duplicates.add(check_id)
        seen.add(check_id)
    return tuple(sorted(duplicates, key=_id_sort_key))


def _reject_duplicate_check_ids(check_id_seq, context):
    """§4.1 R5 零容忍：**每个取得 id 序列的公开入口**见重复即拒绝回答。

    覆盖面（FIX-304 G-1：守卫不再只挂在发现路径上）——
    ``discover_engine_segment_ids`` 的引擎 census、``guard_completeness`` 的
    ``observed``（发现路径 **或** 显式 ``observed_ids``）与 ``declared``、
    ``reconcile_snapshot`` 的 ``actual`` 与 ``expected``。任一入口带入重复
    CheckID 都会让 ``len(…)`` 与集合差失真并传递到消费面，故统一抛
    ``ValueError``（消费方按 §2.4 映射 undetermined → 回退 full）。
    """
    duplicates = _duplicate_ids(check_id_seq)
    if duplicates:
        raise ValueError(
            f"{context}: duplicate CheckID(s) {list(duplicates)} — "
            "Check ID uniqueness is zero-tolerance (§4.1 R5)"
        )
    return check_id_seq


def _index():
    return {spec.check_id: spec for spec in SEGMENTS}


_BY_ID = _index()
_IDS = tuple(spec.check_id for spec in SEGMENTS)

if len(_BY_ID) != len(_IDS):
    raise ValueError("quickscan registry declares duplicate CheckID rows")


def all_segments():
    return SEGMENTS


def registry_ids():
    return _IDS


def segment(check_id):
    """Look up a row. Unknown ids raise ``KeyError`` (fail-closed, never guessed)."""
    return _BY_ID[check_id]


def _derive_fact_source_root(input_deps):
    roots = {dep.split(":", 1)[0] for dep in input_deps}
    if roots == {FACT_SOURCE_PLUGIN}:
        return FACT_SOURCE_PLUGIN
    if roots == {FACT_SOURCE_HOST}:
        return FACT_SOURCE_HOST
    if roots:
        return FACT_SOURCE_MIXED
    return FACT_SOURCE_UNKNOWN


def fact_source_root(check_id):
    """事实源根：plugin / host / mixed / unknown（未声明段 fail-closed 为 unknown）。"""
    spec = _BY_ID.get(check_id)
    if spec is None:
        return FACT_SOURCE_UNKNOWN
    return spec.fact_source_root


def exclusion_reason_code(check_id):
    """排除原因代码；保留段返回 ``None``，未声明段抛 ``KeyError``。"""
    return _BY_ID[check_id].exclusion_reason_code


def quick_face_ids():
    return tuple(spec.check_id for spec in SEGMENTS if MODE_QUICK in spec.modes)


def excluded_ids():
    return tuple(spec.check_id for spec in SEGMENTS if MODE_QUICK not in spec.modes)


# ── 引擎侧机判读取（只读文本，不 import 巨石）────────────────────────────
def _default_engine_path():
    return Path(__file__).resolve().parent / "verify_workflow.py"


def _default_snapshot_path():
    return Path(__file__).resolve().parent / "contract_matrix" / "snapshots.json"


_SEGMENT_SECTION_RE = re.compile(r"^\s*#\s*\u2500\u2500\s*([0-9][A-Za-z0-9]*)\.\s", re.M)
_ENGINE_ENTRY = "def _run_full_engine_checks"
_PRODUCT_GATE_RE = re.compile(r'"Check ([A-Za-z0-9]+)"')


def discover_engine_segment_ids(engine_path=None):
    """Live segment census: the ``# ── <id>. `` sections of the engine body.

    Scoped to ``_run_full_engine_checks`` because the engine prints banners for
    only 69 of the 70 segments (30b has no ``┌─ Check 30b:`` banner line) and
    the file also quotes the ``┌─ Check N:`` marker in prose — the section
    comments are the only complete, unambiguous census.

    口径（FIX-304 显式化，消费面 MUST 遵守）：

    * **返回序 = 引擎源码顺序（engine source order）**，与 FEAT-020 快照 / 注册表
      **位序（positional order）无关**——实测首个错位下标 = 55：census[55]="29"
      vs 快照[55]="28u"。消费面 MUST 用集合运算或显式排序，禁止按位 positional
      zip 两份清单；
    * **唯一性零容忍**（``architecture-evolution-0.80.0`` §4.1 R5）：段落注释
      重复出现即抛 ``ValueError``，与注册表侧导入期守卫（``_BY_ID`` 长度校验）
      同构——重复段号会让 ``len(observed)`` 失真并传递给消费面。
    """
    path = Path(engine_path) if engine_path is not None else _default_engine_path()
    lines = path.read_text(encoding="utf-8").splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.startswith(_ENGINE_ENTRY):
            start = index
            break
    if start is None:
        raise ValueError(f"{path}: engine entry {_ENGINE_ENTRY!r} not found")
    end = len(lines)
    # Body starts on the line right after the ``def``: a top-level ``def `` can
    # never appear inside the (indented) docstring, so no offset is needed.
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("def "):
            end = index
            break
    body = "\n".join(lines[start:end])
    observed = tuple(_SEGMENT_SECTION_RE.findall(body))
    return _reject_duplicate_check_ids(observed, str(path))


def discover_product_gate_ids(engine_path=None):
    """FIX-270 product-gate declaration as read from the engine source (25 ids).

    实现口径 = 源码**文本**解析（``frozenset({…})`` 块 + ``"Check <ID>"`` 字面量，
    **not AST**）；两条 fail-closed 分支：锚点缺失即抛，锚点在而条目形态变化
    导致零命中亦抛——退化静默返回 ``()`` 会把全部插件面段误报为「未受
    product-gate 管辖」（过度披露方向），故与兄弟 ``load_frozen_snapshot_ids``
    的 count 校验同族：结果为空即拒绝回答（FIX-304 F-2）。
    """
    path = Path(engine_path) if engine_path is not None else _default_engine_path()
    source = path.read_text(encoding="utf-8")
    anchor = "_PLUGIN_PRODUCT_CHECK_IDS = frozenset({"
    if anchor not in source:
        raise ValueError(f"{path}: {anchor!r} declaration not found")
    block = source.split(anchor, 1)[1].split("})", 1)[0]
    ids = tuple(_PRODUCT_GATE_RE.findall(block))
    if not ids:
        raise ValueError(
            f"{path}: {anchor!r} found but no \"Check <ID>\" entry parsed in the "
            "declaration block — format changed, refusing an empty product-gate set"
        )
    return ids


def load_frozen_snapshot_ids(snapshot_path=None):
    """FEAT-020 frozen Check id清单（``faces.check_segments.ids``）。"""
    path = Path(snapshot_path) if snapshot_path is not None else _default_snapshot_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    face = data["faces"]["check_segments"]
    ids = tuple(face["ids"])
    if face.get("count") != len(ids):
        raise ValueError(f"{path}: count={face.get('count')} != len(ids)={len(ids)}")
    return ids


# ── 对账 / 完整性守卫（Slice-1 验收 ① ②）────────────────────────────────
@dataclass(frozen=True)
class ReconcileReport:
    """注册表 ↔ FEAT-020 冻结快照 的对账结果（非注册行 schema，不受 CheckSpec 约束）。"""

    expected: tuple
    actual: tuple
    missing: tuple
    extra: tuple

    @property
    def ok(self):
        return not self.missing and not self.extra

    def lines(self):
        out = [
            f"registry={len(self.actual)} snapshot={len(self.expected)} "
            f"missing={list(self.missing)} extra={list(self.extra)}"
        ]
        if self.missing:
            out.append(
                "[FAIL] segments present in the frozen snapshot but absent from "
                f"the registry: {list(self.missing)}"
            )
        if self.extra:
            out.append(
                "[FAIL] segments declared by the registry but absent from the "
                f"frozen snapshot: {list(self.extra)}"
            )
        return tuple(out)


@dataclass(frozen=True)
class CompletenessReport:
    """完整性守卫结果：未声明段 → 告警 + fail-closed 回退 full（QR-1）。

    ``fail_closed`` 是「本次是否已回退」的**唯一判别字段**；``fallback_target``
    恒为回退**目标**（``full``），与本次是否熔断无关——Slice-2 编排器 MUST 用
    ``fail_closed`` 判定，单看 ``fallback_target`` 会把正常 quick 运行报成
    「已回退 full」（FIX-304 F-5：字段名原为歧义的 ``fallback_mode``）。
    """

    declared: tuple
    observed: tuple
    undeclared: tuple
    stale: tuple
    warnings: tuple
    fail_closed: bool
    fallback_target: str

    @property
    def ok(self):
        return not self.undeclared

    def lines(self):
        return self.warnings or (
            f"registry={len(self.declared)} engine={len(self.observed)} "
            f"undeclared=[] stale=[] fallback_target={self.fallback_target}",
        )


def reconcile_snapshot(actual_ids=None, snapshot_ids=None, snapshot_path=None):
    """70/70 覆盖机判：注册表 id 集必须与 FEAT-020 冻结快照恒等（验收 ①）。

    ``actual``（注册表 **或** 显式 ``actual_ids``）与 ``expected``（冻结快照 loader
    **或** 显式 ``snapshot_ids``）两侧统一落唯一性校验：重复 CheckID 即抛
    ``ValueError``（§4.1 R5 零容忍，FIX-304 G-1），不产出 ``ok=True`` 裁决——
    重复项会让 ``len(…)`` 与差集失真并传递给消费面。
    """
    actual = _reject_duplicate_check_ids(
        tuple(registry_ids() if actual_ids is None else actual_ids),
        "reconcile_snapshot(actual_ids)",
    )
    expected = _reject_duplicate_check_ids(
        tuple(
            load_frozen_snapshot_ids(snapshot_path) if snapshot_ids is None else snapshot_ids
        ),
        "reconcile_snapshot(snapshot_ids)",
    )
    missing = tuple(sorted(set(expected) - set(actual), key=_id_sort_key))
    extra = tuple(sorted(set(actual) - set(expected), key=_id_sort_key))
    return ReconcileReport(expected=expected, actual=actual, missing=missing, extra=extra)


def guard_completeness(observed_ids=None, declared_ids=None, engine_path=None):
    """完整性守卫：新段未入表 → 告警且 fail-closed 回退 full（验收 ②）。

    ``undeclared``（引擎有、表无）= 覆盖缺口 → ``fail_closed=True``、
    ``fallback_target="full"``；``stale``（表有、引擎无）= 注册表漂移 →
    仅告警（不损失覆盖，quick 仍可用）。**重复 CheckID 不在本函数静默容忍**：
    ``observed``（发现路径 ``discover_engine_segment_ids`` 或显式 ``observed_ids``）
    与 ``declared``（注册表或显式 ``declared_ids``）两侧统一落唯一性校验，重复即抛
    ``ValueError``（§4.1 R5 零容忍，FIX-304 F-3 + G-1），故本守卫永不把重复输入
    报成 ``ok``。
    """
    declared = _reject_duplicate_check_ids(
        tuple(registry_ids() if declared_ids is None else declared_ids),
        "guard_completeness(declared_ids)",
    )
    observed = _reject_duplicate_check_ids(
        tuple(
            discover_engine_segment_ids(engine_path) if observed_ids is None else observed_ids
        ),
        "guard_completeness(observed_ids)",
    )
    undeclared = tuple(sorted(set(observed) - set(declared), key=_id_sort_key))
    stale = tuple(sorted(set(declared) - set(observed), key=_id_sort_key))
    warnings = []
    if undeclared:
        warnings.append(
            f"[FAIL-CLOSED] {len(undeclared)} engine segment(s) missing from the "
            f"quickscan registry: {list(undeclared)} — reason={REASON_UNDECLARED_SEGMENT}; "
            f"quick face disabled, fell back to full"
        )
    if stale:
        warnings.append(
            f"[WARN] {len(stale)} registry segment(s) no longer present in the engine: "
            f"{list(stale)} — registry drift, quick face unaffected"
        )
    fail_closed = bool(undeclared)
    return CompletenessReport(
        declared=declared,
        observed=observed,
        undeclared=undeclared,
        stale=stale,
        warnings=tuple(warnings),
        fail_closed=fail_closed,
        fallback_target=MODE_FULL_FALLBACK,
    )


# ── 披露（实现期新发现 → 供 product-gate / Phase-2 复核）──────────────────
def plugin_face_not_product_gated(engine_path=None):
    """插件面但不在 FIX-270 product-gate 清单内 → 必须保留（fail-safe）+ 披露。"""
    gated = set(discover_product_gate_ids(engine_path))
    return tuple(
        spec.check_id
        for spec in sorted(SEGMENTS, key=lambda s: _id_sort_key(s.check_id))
        if spec.fact_source_root == FACT_SOURCE_PLUGIN and spec.check_id not in gated
    )


def dual_root_disclosures(engine_path=None):
    """排除集内事实源根非纯插件面（= 混合双根）的段 → 显式披露，禁静默。

    观察到的双根排除段 = 24（插件版本资产 + 宿主 plan-tracker 版本投影）与
    31（product_root + host_root，installed_host scan mode）。两者均为 FIX-270 与
    §3.1 C1 登记的插件产品自检，本表沿用排除政策并将双根事实移交 Phase-2 裁决。
    ``engine_path`` 保留为签名一致（当前披露不消费引擎文本）。
    """
    return tuple(
        spec.check_id
        for spec in sorted(SEGMENTS, key=lambda s: _id_sort_key(s.check_id))
        if spec.excluded_from_quick and spec.fact_source_root != FACT_SOURCE_PLUGIN
    )
