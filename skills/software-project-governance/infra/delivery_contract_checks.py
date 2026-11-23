"""Rules for product outcomes, executable acceptance, quality budgets and vertical slices."""

import re
from typing import Callable, NamedTuple


PRODUCT_SUCCESS_CONTRACT_REQUIRED_FIELDS = {
    "user": str,
    "job_to_be_done": str,
    "non_goals": list,
    "success_metrics": list,
    "competitive_baseline": str,
    "done_definition": list,
}

PRODUCT_SUCCESS_PLACEHOLDER_RE = re.compile(
    r"(?:\b(?:todo|tbd|to_be_defined|n/?a|none|null|unknown)\b|待补|待定|暂无|占位)",
    re.IGNORECASE,
)

PRODUCT_SUCCESS_PROCESS_ONLY_RE = re.compile(
    r"(?:check-governance|verify_workflow|evidence-log|plan-tracker|review|commit|push|archive|"
    r"治理|证据|归档|提交|审查|记录|hook|\bgate\s*(?:G?\d+\s*)?(?:已?通过|pass(?:ed)?\b))",
    re.IGNORECASE,
)

PRODUCT_SUCCESS_USER_OUTCOME_RE = re.compile(
    r"(?:user|customer|persona|outcome|value|usable|acceptance|scenario|quality|competitive|"
    r"用户|客户|使用者|产品|体验|价值|可用|可见|验收|场景|质量|竞争)",
    re.IGNORECASE,
)

PRODUCT_SUCCESS_RUNNABLE_RE = re.compile(
    r"(?:e2e|test|unit|integration|fixture|ci|command|script|execute|run|pass|"
    r"测试|验证|用例|命令|脚本|执行|通过)",
    re.IGNORECASE,
)


ACCEPTANCE_CONTRACT_REQUIRED_FIELDS = {
    "scenario": str,
    "command": str,
    "expected_output": str,
    "last_run": dict,
    "demo_evidence": str,
}

ACCEPTANCE_RUNNABLE_COMMAND_RE = re.compile(
    r"^\s*(?:(?:python|pytest|node|npm|pnpm|yarn|uv|bash|sh|make|go|cargo|npx|cmd|powershell|pwsh)\b|"
    r"(?:\./|\.\\|skills/|skills\\|scripts/|scripts\\).+)",
    re.IGNORECASE,
)

ACCEPTANCE_PASS_STATUSES = {"pass", "passed", "ok", "success", "通过"}

ACCEPTANCE_NOT_RUN_STATUSES = {"not_run_yet", "not run yet", "pending", "planned", "待运行", "未运行"}

QUALITY_BUDGET_PASS_STATUSES = {"pass", "passed", "ok", "success", "通过"}

QUALITY_BUDGET_PENDING_STATUSES = {"not_run_yet", "not run yet", "pending", "planned", "待运行", "未运行"}

QUALITY_BUDGET_EXEMPT_STATUSES = {"exempt", "exception", "waived", "not_applicable", "n/a", "豁免", "不适用"}

QUALITY_BUDGET_VALIDATION_SIGNAL_RE = re.compile(
    r"(?:"
    r"python|pytest|node|npm|pnpm|yarn|uv|bash|sh|make|go|cargo|npx|cmd|powershell|pwsh|"
    r"test|check|scan|lint|audit|metric|score|coverage|threshold|budget|lighthouse|axe|"
    r"latency|p95|error rate|vulnerability|security|a11y|accessibility|maintainability|"
    r"测试|检查|扫描|指标|分数|覆盖率|阈值|预算|延迟|错误率|漏洞|安全|可访问|可维护"
    r")",
    re.IGNORECASE,
)

QUALITY_BUDGET_WEAK_PROSE_RE = re.compile(
    r"(?:"
    r"quality is okay|quality is ok|looks fine|looks good|good enough|review says|review artifact|"
    r"manual reviewer|manual review|prose|subjective|"
    r"质量还行|看起来可以|人工看看|人工审查|审查通过|主观"
    r")",
    re.IGNORECASE,
)

# FIX-475: single shared vocabulary + predicate for the Check 18f/18g
# pending allowance — no second semantic source (FIX-292 lesson). Markers
# substring-match the lowercased plan-tracker status cell, so live emoji
# forms (「📋 规划中 (…)」/「🚧 派发中 (…)」) match via the text marker.
# Terminal words (✅/完成/completed/…) must never join this whitelist;
# terminal tasks are already excluded upstream by
# _active_execution_packet_tasks -> _is_incomplete_task_status.
TASK_PENDING_STATUS_MARKERS = (
    "规划中",
    "待实施",
    "pending",
    "planned",
    "派发中",
    "进行中",
    "开发中",
    "in progress",
    "in_progress",
    "wip",
)

VERTICAL_SLICE_REQUIRED_FIELDS = (
    "user_visible_slice",
    "demo_path",
    "scope_guard",
    "rollback_plan",
    "status",
    "evidence",
)

VERTICAL_SLICE_PASS_STATUSES = {"pass", "passed", "ok", "success", "通过"}

VERTICAL_SLICE_PENDING_STATUSES = {"not_run_yet", "not run yet", "pending", "planned", "待运行", "未运行"}

VERTICAL_SLICE_DEMO_SIGNAL_RE = re.compile(
    r"(?:"
    r"\b(?:python|pytest|node|npm|pnpm|yarn|uv|bash|sh|make|go|cargo|npx|powershell|pwsh|"
    r"test|check|smoke|e2e|demo|browser|screenshot)\b|localhost|https?://|"
    r"测试|检查|冒烟|演示|截图|浏览器|验收"
    r")",
    re.IGNORECASE,
)

VERTICAL_SLICE_USER_SIGNAL_RE = re.compile(
    r"(?:user|persona|customer|operator|viewer|admin|用户|客户|使用者|操作者|可见|页面|命令输出|行为|场景)",
    re.IGNORECASE,
)

VERTICAL_SLICE_BEHAVIOR_SIGNAL_RE = re.compile(
    r"(?:\b(?:run|observe|see|click|open|use|complete|display|command output|scenario|page|form|result|pass)\b|"
    r"运行|观察|看到|点击|打开|使用|完成|显示|命令输出|场景|页面|表单|结果|通过)",
    re.IGNORECASE,
)

VERTICAL_SLICE_TECH_LAYER_RE = re.compile(
    r"(?:repository|service layer|abstraction|refactor|backend|database|schema|dao|model layer|internal|"
    r"技术层|服务层|抽象|重构|后端|数据库|数据表|内部)",
    re.IGNORECASE,
)

VERTICAL_SLICE_BROAD_SCOPE_RE = re.compile(
    r"(?:entire project|whole project|whole codebase|all files|everything|\*|全仓|整个项目|所有文件|全部重构|无边界)",
    re.IGNORECASE,
)

VERTICAL_SLICE_WEAK_PROSE_RE = re.compile(
    r"(?:review says|review artifact|manual review|looks good|looks fine|prose|subjective|审查通过|人工审查|看起来可以|主观)",
    re.IGNORECASE,
)


class ProductSuccessPolicy(NamedTuple):
    required_fields: dict
    placeholder: re.Pattern
    process_only_metric: Callable[[str], bool]
    user_outcome: re.Pattern
    runnable: re.Pattern


class AcceptancePolicy(NamedTuple):
    required_fields: dict
    runnable_command: re.Pattern
    pass_statuses: set
    not_run_statuses: set
    placeholder: re.Pattern


class QualityBudgetPolicy(NamedTuple):
    dimensions: tuple
    pass_statuses: set
    pending_statuses: set
    exempt_statuses: set
    validation_signal: re.Pattern
    weak_prose: re.Pattern
    placeholder: re.Pattern
    pending_task: Callable[[dict], bool]


class VerticalSlicePolicy(NamedTuple):
    required_fields: tuple
    pass_statuses: set
    pending_statuses: set
    demo_signal: re.Pattern
    user_signal: re.Pattern
    behavior_signal: re.Pattern
    tech_layer: re.Pattern
    broad_scope: re.Pattern
    weak_prose: re.Pattern
    weak_quality_prose: re.Pattern
    placeholder: re.Pattern
    pending_task: Callable[[dict], bool]


def _is_meaningful_product_success_text(value, placeholder):
    return isinstance(value, str) and len(value.strip()) >= 8 and not placeholder.match(value)


def _is_meaningful_product_success_list(value, placeholder):
    return (
        isinstance(value, list)
        and bool(value)
        and all(_is_meaningful_product_success_text(item, placeholder) for item in value)
    )


def _is_process_only_product_success_metric(value, process_only=PRODUCT_SUCCESS_PROCESS_ONLY_RE):
    text = value.strip()
    if not process_only.search(text):
        return False
    # A visible, repeatable product interaction can itself display review or evidence data.
    interaction = re.search(
        r"(?:用户|客户|使用者).*?(?:刷新|打开|点击|选择|搜索|运行|执行).*?(?:看到|看见|显示|返回|恢复|找到|获取)"
        r"|\b(?:users?|customers?|operators?)\b.*?\b(?:refresh|open|click|select|search|run|execute)\w*\b"
        r".*?\b(?:see|display|show|return|restore|find|receive)\w*\b",
        text, re.IGNORECASE,
    )
    return interaction is None


def _default_product_success_policy():
    return ProductSuccessPolicy(PRODUCT_SUCCESS_CONTRACT_REQUIRED_FIELDS, PRODUCT_SUCCESS_PLACEHOLDER_RE,
                                _is_process_only_product_success_metric, PRODUCT_SUCCESS_USER_OUTCOME_RE,
                                PRODUCT_SUCCESS_RUNNABLE_RE)


def validate_default_product_success_contract(packet):
    return _validate_product_success_contract(packet, _default_product_success_policy())


def _validate_product_success_contract(packet, policy: ProductSuccessPolicy):
    issues = []
    contract = packet.get("product_success_contract") if isinstance(packet, dict) else None
    if not isinstance(contract, dict):
        return ["missing product_success_contract"]

    for field, expected_type in policy.required_fields.items():
        value = contract.get(field)
        if not isinstance(value, expected_type):
            issues.append(f"product_success_contract.{field} missing or invalid")
            continue
        if expected_type is str and not _is_meaningful_product_success_text(value, policy.placeholder):
            issues.append(f"product_success_contract.{field} must be specific and non-placeholder")
        if expected_type is list and not _is_meaningful_product_success_list(value, policy.placeholder):
            issues.append(f"product_success_contract.{field} must be a non-empty specific string array")

    success_metrics = contract.get("success_metrics")
    if isinstance(success_metrics, list) and success_metrics:
        process_only = [
            metric for metric in success_metrics
            if isinstance(metric, str) and policy.process_only_metric(metric)
        ]
        if process_only:
            issues.append("product_success_contract.success_metrics must not contain process-only metrics")
        if not any(isinstance(metric, str) and policy.user_outcome.search(metric) for metric in success_metrics):
            issues.append("product_success_contract.success_metrics needs at least one user-visible outcome")
        if not any(isinstance(metric, str) and policy.runnable.search(metric) for metric in success_metrics):
            issues.append("product_success_contract.success_metrics needs at least one runnable validation signal")

    return issues


def _is_meaningful_acceptance_text(value, placeholder):
    return _is_meaningful_product_success_text(value, placeholder)


def _is_acceptance_run_deferrable(task):
    status = str(task.get("status", "")).strip().lower()
    return any(marker in status for marker in ("待实施", "待启动", "pending", "planned"))


def _validate_acceptance_contract(task, packet, policy: AcceptancePolicy):
    issues = []
    contract = packet.get("acceptance_contract") if isinstance(packet, dict) else None
    if not isinstance(contract, dict):
        return ["missing acceptance_contract"]

    for field, expected_type in policy.required_fields.items():
        value = contract.get(field)
        if not isinstance(value, expected_type):
            issues.append(f"acceptance_contract.{field} missing or invalid")
            continue
        if expected_type is str and not _is_meaningful_acceptance_text(value, policy.placeholder):
            issues.append(f"acceptance_contract.{field} must be specific and non-placeholder")

    command = contract.get("command")
    if isinstance(command, str) and _is_meaningful_acceptance_text(command, policy.placeholder):
        if not policy.runnable_command.search(command):
            issues.append("acceptance_contract.command must be a runnable validation command")

    last_run = contract.get("last_run")
    if isinstance(last_run, dict):
        status = str(last_run.get("status", "")).strip().lower()
        exit_code = last_run.get("exit_code")
        summary = last_run.get("summary")
        if status in policy.not_run_statuses and _is_acceptance_run_deferrable(task):
            if not _is_meaningful_acceptance_text(summary, policy.placeholder):
                issues.append("acceptance_contract.last_run.summary must be specific and non-placeholder")
            return issues
        if policy.placeholder.search(status) or status not in policy.pass_statuses:
            issues.append("acceptance_contract.last_run.status must be PASS")
        if not isinstance(exit_code, int) or exit_code != 0:
            issues.append("acceptance_contract.last_run.exit_code must be 0")
        if not _is_meaningful_acceptance_text(summary, policy.placeholder):
            issues.append("acceptance_contract.last_run.summary must be specific and non-placeholder")

    return issues


def _normalize_quality_dimension_name(value):
    text = str(value or "").strip().lower()
    aliases = {
        "perf": "performance",
        "性能": "performance",
        "可靠性": "reliability",
        "安全": "security",
        "安全性": "security",
        "a11y": "accessibility",
        "可访问性": "accessibility",
        "无障碍": "accessibility",
        "user_experience": "ux",
        "user experience": "ux",
        "用户体验": "ux",
        "体验": "ux",
        "maint": "maintainability",
        "可维护性": "maintainability",
        "维护性": "maintainability",
    }
    return aliases.get(text, text)


def _quality_budget_dimensions(contract):
    dimensions = contract.get("dimensions") if isinstance(contract, dict) else None
    if isinstance(dimensions, dict):
        rows = []
        for name, payload in dimensions.items():
            if isinstance(payload, dict):
                row = dict(payload)
                row.setdefault("dimension", name)
                rows.append(row)
            else:
                rows.append({"dimension": name, "value": payload})
        return rows
    if isinstance(dimensions, list):
        return dimensions
    return None


def _is_task_pending_status_allowed(task, pending_markers):
    status = str(task.get("status", "")).strip().lower()
    return any(marker in status for marker in pending_markers)


def _has_quality_validation_signal(value, placeholder, validation_signal):
    if not _is_meaningful_product_success_text(value, placeholder):
        return False
    return bool(validation_signal.search(value))


def _is_weak_quality_prose(value, weak_prose):
    return isinstance(value, str) and bool(weak_prose.search(value))


def _validate_quality_budget(task, packet, policy: QualityBudgetPolicy):
    issues = []
    contract = packet.get("quality_budget") if isinstance(packet, dict) else None
    if not isinstance(contract, dict):
        return ["missing quality_budget"]

    dimensions = _quality_budget_dimensions(contract)
    if not isinstance(dimensions, list) or not dimensions:
        return ["quality_budget.dimensions missing or invalid"]

    seen = set()
    for idx, item in enumerate(dimensions):
        if not isinstance(item, dict):
            issues.append(f"quality_budget.dimensions[{idx}] must be an object")
            continue
        dimension = _normalize_quality_dimension_name(item.get("dimension"))
        if dimension not in policy.dimensions:
            issues.append(f"quality_budget dimension invalid: {item.get('dimension')}")
            continue
        if dimension in seen:
            issues.append(f'quality_budget duplicate dimension: {dimension}')
        seen.add(dimension)

        for field in ("threshold", "validation", "evidence"):
            if not _is_meaningful_product_success_text(item.get(field), policy.placeholder):
                issues.append(f"quality_budget.{dimension}.{field} must be specific and non-placeholder")
            elif _is_weak_quality_prose(item.get(field), policy.weak_prose):
                issues.append(f"quality_budget.{dimension}.{field} must not be review/prose-only quality evidence")

        if not _has_quality_validation_signal(item.get("validation"), policy.placeholder, policy.validation_signal):
            issues.append(f"quality_budget.{dimension}.validation must include a runnable command, metric, or quality signal")

        status = str(item.get("status", "")).strip().lower()
        if policy.placeholder.search(status):
            issues.append(f"quality_budget.{dimension}.status must be PASS, NOT_RUN_YET, or EXEMPT")
            continue
        if status in policy.exempt_statuses:
            if not _is_meaningful_product_success_text(item.get("exception"), policy.placeholder):
                issues.append(f"quality_budget.{dimension}.exception must justify the exemption")
            continue
        if status in policy.pending_statuses and policy.pending_task(task):
            continue
        if status not in policy.pass_statuses:
            issues.append(f"quality_budget.{dimension}.status must be PASS or a justified EXEMPT status")

    required = contract.get('required_dimensions', [])
    if not isinstance(required, list) or not all(isinstance(dim, str) and dim in policy.dimensions for dim in required):
        return issues + ['quality_budget.required_dimensions must name supported dimensions']
    missing = [dim for dim in required if dim not in seen]
    if missing:
        issues.append(f"quality_budget missing dimension(s): {', '.join(missing)}")
    return issues


def _validate_vertical_slice(task, packet, policy: VerticalSlicePolicy):
    issues = []
    contract = packet.get("vertical_slice") if isinstance(packet, dict) else None
    if not isinstance(contract, dict):
        return ["missing vertical_slice"]

    for field in policy.required_fields:
        if field == "status":
            continue
        if not _is_meaningful_product_success_text(contract.get(field), policy.placeholder):
            issues.append(f"vertical_slice.{field} must be specific and non-placeholder")
        elif _is_weak_quality_prose(contract.get(field), policy.weak_quality_prose) or policy.weak_prose.search(str(contract.get(field))):
            issues.append(f"vertical_slice.{field} must not be review/prose-only evidence")

    user_slice = str(contract.get("user_visible_slice", ""))
    if _is_meaningful_product_success_text(user_slice, policy.placeholder) and not policy.user_signal.search(user_slice):
        issues.append("vertical_slice.user_visible_slice must describe a user-observable behavior or scenario")
    if policy.tech_layer.search(user_slice) and not policy.behavior_signal.search(user_slice):
        issues.append("vertical_slice.user_visible_slice must not disguise a technical-layer change as a user-visible slice")

    demo_path = str(contract.get("demo_path", ""))
    if _is_meaningful_product_success_text(demo_path, policy.placeholder) and not policy.demo_signal.search(demo_path):
        issues.append("vertical_slice.demo_path must include a runnable demo, smoke, test, check, URL, screenshot, or command signal")

    scope_guard = str(contract.get("scope_guard", ""))
    if policy.broad_scope.search(scope_guard):
        issues.append("vertical_slice.scope_guard must define a narrow slice boundary, not the whole project/codebase")

    status = str(contract.get("status", "")).strip().lower()
    if policy.placeholder.search(status):
        issues.append("vertical_slice.status must be PASS or NOT_RUN_YET for planned work")
    elif status in policy.pending_statuses and policy.pending_task(task):
        pass
    elif status not in policy.pass_statuses:
        issues.append("vertical_slice.status must be PASS unless the task is explicitly pending/planned")

    return issues


def check_declared_contracts(contract, packet_path, select_packets, validate):
    """Evaluate the requested contract for each applicable execution packet."""
    result = {"required_tasks": [], "entries": [], "issues": [], "pass": True}
    for task, packet in select_packets(result, packet_path, contract):
        task_id = task["task_id"]
        issues = validate(task, packet)
        if issues:
            result["pass"] = False
        result["entries"].append({
            "task_id": task_id, "status": "FAIL" if issues else "PASS", "issues": issues,
        })
    return result
