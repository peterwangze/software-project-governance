#!/usr/bin/env python3
"""FEAT-040 — the session-scoped gray-release switch (rollback channel).

Slice A (AUDIT-154, v0.84.0) landed four behaviour changes on the hot session
path: FEAT-034 (first-interaction front-loading), FEAT-035 (upgrade
confirmation gate), FEAT-036 (snapshot dual contract) and FEAT-038 (Scenario
on-demand loading). Shipping four protocol changes without a rollback channel
means a user who hits a regression has no way back except editing governance
files by hand. This module is that channel — **one master switch**, not a
per-FEAT matrix.

Design (hybrid, minimal viable surface):

1. **Two entry points, one decision.**
   * session level — the environment variable ``GOVERNANCE_LEGACY_BEHAVIOR``;
   * project level — the ``behavior_profile`` key of the plan-tracker's
     ``## 项目配置`` section.
   Precedence: env > plan-tracker > the shipped default (``modern``).
   The env arm exists because the rollback case is "the user hit the problem
   *now*": it works without touching a governance file. The plan-tracker arm
   exists because a project may need the old shape for longer than a session.

2. **The safety boundary is data, not prose.** ``LEGACY_REVERTS`` carries the
   performance-only rollbacks; ``SAFETY_INVARIANTS`` carries the semantics
   legacy MUST NOT touch. ``revert_contract_issues()`` is the machine check
   that keeps the two sets disjoint and the revert classes closed — so
   "legacy never weakens safety" is a property of this module, not a promise
   in a comment.

3. **The declared boundary is not the enforced one.** The step that actually
   keeps safety intact is that neither arm implements a safety rollback:
   FEAT-035's upgrade confirmation gate lives in the migration write sequence
   (``commands/governance/scenario-c.md`` + the entry templates) and is
   independent of this profile. This module only publishes WHICH behaviours
   may fall back, so a future maintainer cannot add a safety entry to
   ``LEGACY_REVERTS`` without reddening the guard.

4. **Fail-closed on garbage, never a guess.** An unset/empty value falls
   through to the next arm. A non-empty value outside the vocabulary is
   reported explicitly (``invalid``) and the *next* arm still decides —
   ``legacyy`` must never be read as ``legacy`` (silently honouring a typo
   would defeat the rollback intent) and must never be read as ``modern``
   without saying so. The echoed raw value is clipped to
   ``INVALID_VALUE_LIMIT`` (R0 P2-3) — disclosed, never silently trimmed.

Boundary: read-only, no imports beyond the stdlib (ArchGuard R6), no
``verify_workflow`` import (ArchGuard R2). Consumed by ``bootstrap_aggregate``
(the ``behavior`` face of ``governance-bootstrap``) and by the protocol text
guards in ``infra/tests``.
"""

from __future__ import annotations

import os
import re

TASK_ID = "FEAT-040"

#: Session-level arm (highest precedence).
ENV_VAR = "GOVERNANCE_LEGACY_BEHAVIOR"

#: Project-level arm — a ``## 项目配置`` key, same shape as ``Profile``.
PLAN_TRACKER_KEY = "behavior_profile"
CONFIG_SECTION_PREFIX = "## 项目配置"

PROFILE_MODERN = "modern"
PROFILE_LEGACY = "legacy"
PROFILE_VALUES = (PROFILE_MODERN, PROFILE_LEGACY)
DEFAULT_PROFILE = PROFILE_MODERN

SOURCE_ENV = "env"
SOURCE_PLAN_TRACKER = "plan-tracker"
SOURCE_DEFAULT = "default"

#: Accepted spellings per arm. Kept as closed vocabularies so a typo is an
#: explicit ``invalid`` report instead of a silent membership test.
LEGACY_TOKENS = frozenset(("1", "true", "yes", "on", "legacy"))
MODERN_TOKENS = frozenset(("0", "false", "no", "off", "modern"))

#: Revert classes. The closed set is the whole point of the boundary: an
#: entry that claims to roll back anything else fails ``revert_contract_issues``.
REVERT_CLASS_PERFORMANCE = "performance"
ALLOWED_REVERT_CLASSES = frozenset((REVERT_CLASS_PERFORMANCE,))

#: `--` the behaviours legacy mode IS allowed to roll back: performance and
#: orchestration only (AUDIT-154 slice-A scope: FEAT-034/036/038).
LEGACY_REVERTS = (
    {
        "feat": "FEAT-034",
        "surface": "bootstrap 热数据入口",
        "modern": "`governance-bootstrap --format json` 单命令快路径（≤8KB 投影）",
        "legacy": "plan-tracker 六段热数据逐段读取（原路径）",
        "class": REVERT_CLASS_PERFORMANCE,
    },
    {
        "feat": "FEAT-034",
        "surface": "首次交互时序",
        "modern": "热数据就绪后立即 AskUserQuestion；深检（健康摘要/交叉验证）后置",
        "legacy": "深检先行（健康摘要 + 交叉验证）再进入首次 ask",
        "class": REVERT_CLASS_PERFORMANCE,
    },
    {
        "feat": "FEAT-036",
        "surface": "snapshot 渲染契约",
        "modern": "默认交互视图 ≤8 字段；完整契约（20 字段 CLI + 4 字段 pack）按需取",
        "legacy": "直接渲染完整交付信任快照（不区分默认视图/完整契约）",
        "class": REVERT_CLASS_PERFORMANCE,
    },
    {
        "feat": "FEAT-038",
        "surface": "Scenario 文档加载",
        "modern": "路由层为默认载荷；命中场景再按需 Read 对应文件",
        "legacy": "会话开始预加载全部 `commands/governance/*.md`（无按需门控）",
        "class": REVERT_CLASS_PERFORMANCE,
    },
)

#: `--` the semantics legacy mode MUST NOT touch. ``marker`` tokens must be
#: present in the protocol text that publishes the boundary (guard-tested), so
#: the documented boundary cannot drift away from this table.
SAFETY_INVARIANTS = (
    {
        "id": "upgrade-confirmation-gate",
        "feat": "FEAT-035",
        "statement": "版本升级写序列 MUST 先呈现摘要并经用户确认；确认前零写操作",
        "marker": "升级确认门",
    },
    {
        "id": "anomaly-not-hidden",
        "feat": "M9 / 设计原则 3",
        "statement": "异常先于状态展示——异常不隐藏（deferred 显示「待检查」而非通过）",
        "marker": "异常不隐藏",
    },
    {
        "id": "fail-closed-resolve",
        "feat": "DEC-080 / RISK-038",
        "statement": "`resolved_root_ok == false` → MUST STOP，不呈现治理状态",
        "marker": "fail-closed",
    },
    {
        "id": "real-environment-protection",
        "feat": "M7.7",
        "statement": "真实环境操作三选一（隔离/备份+校验/逐项授权），三者皆缺即禁止执行",
        "marker": "真实环境防护",
    },
    {
        "id": "mandatory-re-review",
        "feat": "M7.4",
        "statement": "NEEDS_CHANGE 且 round<3 → MUST 立即复审，不得跳过",
        "marker": "复审必达",
    },
)

#: R0 P1-2 — the action line for an invalid switch value. It lives here, next
#: to ``next_action_line``, because this module owns the never-guess contract:
#: both hints the aggregate renders for the switch come from one place.
#: ``bootstrap_aggregate`` consumes it as ``INVALID_VALUE_ACTION``.
INVALID_VALUE_ACTION = (
    "行为开关取值非法已被忽略（不猜、按下一优先级执行）——检查 "
    "GOVERNANCE_LEGACY_BEHAVIOR / plan-tracker 的 behavior_profile 拼写"
)

#: Protocol-text anchor: every surface that publishes the switch must carry
#: this marker (guard-tested), so a split/rewrite cannot silently drop it.
PROTOCOL_MARKER = "行为灰度开关"

#: Surfaces that MUST publish the switch (repo-relative, guard-tested).
PROTOCOL_SURFACES = (
    "commands/governance-init.md",
    "commands/governance.md",
    "commands/governance/bootstrap.md",
    "skills/software-project-governance/SKILL.md",
    "adapters/dsh/AGENTS.md.template",
    "agent-presets/governance/agent.cordis.yml.template",
)

_CONFIG_LINE_RE = re.compile(r"^- \*\*(?P<key>.+?)\*\*:\s*(?P<value>.+?)\s*$")

#: R0 P2-3 — ceiling for an echoed invalid value. The raw value is a switch
#: token, not payload: it is echoed into the aggregate face (and from there
#: into the agent's context), so an arbitrarily long string set in the env var
#: must not ride along. Same disclosed-marker caliber as
#: ``bootstrap_aggregate._clip``.
INVALID_VALUE_LIMIT = 64


def _clip_value(value, limit=INVALID_VALUE_LIMIT):
    """Truncate an echoed raw value, marking the cut (never a silent trim)."""
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


# ── arm parsers (pure: text in, verdict out) ────────────────────────────────


def classify_token(raw):
    """Classify one arm's raw value.

    Returns ``(profile | None, status)`` where status ∈
    ``{"unset", "set", "invalid"}``. ``invalid`` carries no profile: the caller
    falls through to the next arm and reports the bad value.
    """
    if raw is None:
        return None, "unset"
    token = str(raw).strip().lower()
    if not token:
        return None, "unset"
    if token in LEGACY_TOKENS:
        return PROFILE_LEGACY, "set"
    if token in MODERN_TOKENS:
        return PROFILE_MODERN, "set"
    return None, "invalid"


def plan_tracker_value(text):
    """Read the ``behavior_profile`` cell of the ``## 项目配置`` section.

    Line-wise and section-bounded, mirroring ``bootstrap_aggregate``'s
    ``parse_project_config`` caliber (the same ``- **key**: value`` shape).
    """
    if not text:
        return None
    inside = False
    for line in str(text).split("\n"):
        stripped = line.strip()
        if inside and stripped.startswith("## "):
            return None
        if not inside:
            if stripped.startswith(CONFIG_SECTION_PREFIX):
                inside = True
            continue
        match = _CONFIG_LINE_RE.match(stripped)
        if match and match.group("key").strip() == PLAN_TRACKER_KEY:
            return match.group("value").strip()
    return None


def resolve_behavior_profile(env=None, plan_tracker_text=None):
    """Resolve the active profile from both arms (pure, never raises).

    ``env`` defaults to ``os.environ``. Returns a dict carrying the decision,
    the arm that made it, both raw inputs, and every invalid value seen — an
    invalid value is always disclosed, never laundered into a silent default.
    """
    environ = os.environ if env is None else env
    raw_env = None
    try:
        raw_env = environ.get(ENV_VAR)
    except AttributeError:  # pragma: no cover - defensive (non-mapping env)
        raw_env = None

    env_profile, env_status = classify_token(raw_env)
    plan_raw = plan_tracker_value(plan_tracker_text)
    plan_profile, plan_status = classify_token(plan_raw)

    invalid = []
    if env_status == "invalid":
        invalid.append({"arm": SOURCE_ENV, "name": ENV_VAR,
                        "value": _clip_value(raw_env)})
    if plan_status == "invalid":
        invalid.append({"arm": SOURCE_PLAN_TRACKER,
                        "name": PLAN_TRACKER_KEY,
                        "value": _clip_value(plan_raw)})

    if env_status == "set":
        profile, source = env_profile, SOURCE_ENV
    elif plan_status == "set":
        profile, source = plan_profile, SOURCE_PLAN_TRACKER
    else:
        profile, source = DEFAULT_PROFILE, SOURCE_DEFAULT

    return {
        "profile": profile,
        "source": source,
        "is_legacy": profile == PROFILE_LEGACY,
        "env_var": ENV_VAR,
        "plan_tracker_key": PLAN_TRACKER_KEY,
        "env_value": None if env_status == "unset" else str(raw_env),
        "env_status": env_status,
        "plan_tracker_value": None if plan_status == "unset" else str(plan_raw),
        "plan_tracker_status": plan_status,
        "invalid": invalid,
        "revert_ids": ([item["surface"] for item in LEGACY_REVERTS]
                       if profile == PROFILE_LEGACY else []),
        "invariant_ids": [item["id"] for item in SAFETY_INVARIANTS],
    }


def behavior_face(plan_tracker_text=None, env=None):
    """The ``behavior`` face projected into ``governance-bootstrap``.

    Compact by design (the aggregate carries an 8KB hard budget): the ids of
    what fell back plus the ids of what did not, never the full tables.
    """
    resolution = resolve_behavior_profile(
        env=env, plan_tracker_text=plan_tracker_text)
    return {
        "profile": resolution["profile"],
        "source": resolution["source"],
        "env_var": resolution["env_var"],
        "plan_tracker_key": resolution["plan_tracker_key"],
        "reverted": resolution["revert_ids"],
        "invariants": resolution["invariant_ids"],
        "invalid": resolution["invalid"],
    }


# ── rendering (the protocol/CLI text face) ──────────────────────────────────


def next_action_line(resolution):
    """One ``next_actions`` line for the aggregate — None when modern.

    Accepts either the resolver's own dict or the projected ``behavior`` face
    (both carry ``profile``/``source``), so the aggregate does not have to
    keep the full resolution around just to render one line.
    """
    if not resolution or resolution.get("profile") != PROFILE_LEGACY:
        return None
    feats = []
    for item in LEGACY_REVERTS:
        if item["feat"] not in feats:
            feats.append(item["feat"])
    return ("灰度回退生效（legacy，source=%s）：仅性能/编排行为回退（%s）；"
            "安全语义不变（升级确认门/异常不隐藏/fail-closed/真实环境防护/复审必达）"
            % (resolution.get("source"), "/".join(feats)))


def format_behavior_line(resolution):
    """One-line text rendering for the aggregate's ``--format text`` face."""
    resolution = resolution or {}
    line = "behavior: %s (source %s)" % (resolution.get("profile"),
                                         resolution.get("source"))
    if resolution.get("profile") == PROFILE_LEGACY:
        line += " — legacy: performance-only rollback, safety invariants intact"
    for item in resolution.get("invalid") or []:
        line += (" | INVALID %s=%r ignored (fail-closed, never guessed)"
                 % (item.get("name"), item.get("value")))
    return line


def render_boundary_table(resolution=None):
    """The full revert/invariant table for the on-demand protocol documents."""
    resolution = resolution or resolve_behavior_profile()
    lines = [
        "| 面 | 现代（modern，默认） | legacy 回退 | 类别 |",
        "|----|--------------------|------------|------|",
    ]
    for item in LEGACY_REVERTS:
        lines.append("| %s · %s | %s | %s | %s |"
                     % (item["feat"], item["surface"], item["modern"],
                        item["legacy"], item["class"]))
    lines.append("")
    lines.append("**安全语义硬边界（legacy 模式一律不回退）**：")
    for item in SAFETY_INVARIANTS:
        lines.append("- `%s`（%s）：%s" % (item["id"], item["feat"],
                                          item["statement"]))
    lines.append("")
    lines.append("当前解析：profile=%s source=%s"
                 % (resolution["profile"], resolution["source"]))
    return "\n".join(lines)


# ── machine contract of the boundary itself ─────────────────────────────────


def revert_contract_issues():
    """Check the module's OWN boundary invariants (empty list == consistent).

    Enforced properties:

    1. every revert entry declares a class inside ``ALLOWED_REVERT_CLASSES``
       — a future edit that tries to smuggle a safety rollback into the
       revert table fails here instead of shipping;
    2. no revert entry shares a ``feat`` id with a safety invariant (slice-A
       FEAT-035 has safety semantics only, so it must stay out entirely);
    3. every safety invariant carries a non-empty ``marker`` (the protocol
       text guard needs a token to look for);
    4. revert surfaces and invariant ids are unique (a duplicate would make
       the projection ambiguous).
    """
    issues = []
    revert_feats = set()
    surfaces = set()
    for item in LEGACY_REVERTS:
        if item.get("class") not in ALLOWED_REVERT_CLASSES:
            issues.append(
                "revert entry %r declares class %r outside %s — legacy mode "
                "may only roll back performance/orchestration behaviour"
                % (item.get("surface"), item.get("class"),
                   sorted(ALLOWED_REVERT_CLASSES)))
        if item.get("surface") in surfaces:
            issues.append("duplicate revert surface: %r" % item.get("surface"))
        surfaces.add(item.get("surface"))
        revert_feats.add(item.get("feat"))

    invariant_feats = set()
    ids = set()
    for item in SAFETY_INVARIANTS:
        if not item.get("marker"):
            issues.append("safety invariant %r has no protocol marker"
                          % item.get("id"))
        if item.get("id") in ids:
            issues.append("duplicate safety invariant id: %r" % item.get("id"))
        ids.add(item.get("id"))
        invariant_feats.add(item.get("feat"))

    overlap = sorted(revert_feats & invariant_feats)
    if overlap:
        issues.append(
            "FEAT(s) appear in BOTH the revert table and the safety "
            "invariants: %s — a task with safety semantics must not be "
            "revertible" % overlap)
    return issues
