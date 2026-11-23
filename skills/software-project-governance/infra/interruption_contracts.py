"""Interruption-policy classification, examples and execution-packet checks."""

import re
from typing import NamedTuple


INTERRUPTION_POLICY_REQUIRED_PHRASES = (
    "User Interruption Policy v2",
    "critical-only",
    "product intent",
    "acceptance standard",
    "irreversible",
    "record_assumption",
    "interruption_budget",
)

INTERRUPTION_POLICY_REQUIRED_TEMPLATE_PHRASES = (
    "interruption_policy:",
    "critical_triggers:",
    "auto_execute:",
    "assumption_record:",
    "interruption_budget:",
)

INTERRUPTION_POLICY_REQUIRED_ASSUMPTION_FIELDS = (
    "assumption",
    "basis",
    "reversibility",
    "validation",
    "rollback",
)

INTERRUPTION_POLICY_PLACEHOLDER_RE = re.compile(
    r"(?:\b(?:todo|tbd|to_be_defined|n/?a|none|null|unknown)\b|待补|待定|暂无|占位)",
    re.IGNORECASE,
)

INTERRUPTION_POLICY_CRITICAL_TRIGGER_KEYS = (
    "product_intent_unclear",
    "acceptance_standard_unclear",
    "irreversible",
    "risk_acceptance",
    "release_decision",
    "external_dependency",
    "mode_change",
)

INTERRUPTION_POLICY_PACKET_CRITICAL_SIGNALS = (
    "product intent",
    "acceptance",
    "irreversible",
    "release",
    "risk acceptance",
    "external dependency",
    "mode change",
)

INTERRUPTION_POLICY_DEFAULT_EXAMPLES = [
    {
        "id": "product-intent-ambiguity",
        "expected_action": "ask_user",
        "decision": {"product_intent_unclear": True, "reversible": True},
    },
    {
        "id": "acceptance-standard-ambiguity",
        "expected_action": "ask_user",
        "decision": {"acceptance_standard_unclear": True, "reversible": True},
    },
    {
        "id": "irreversible-file-delete",
        "expected_action": "ask_user",
        "decision": {"irreversible": True, "destructive": True},
    },
    {
        "id": "risk-acceptance",
        "expected_action": "ask_user",
        "decision": {"risk_acceptance": True, "reversible": False},
    },
    {
        "id": "release-go-no-go",
        "expected_action": "ask_user",
        "decision": {"release_decision": True, "reversible": False},
    },
    {
        "id": "new-external-dependency",
        "expected_action": "ask_user",
        "decision": {"external_dependency": True, "reversible": True},
    },
    {
        "id": "mode-change",
        "expected_action": "ask_user",
        "decision": {"mode_change": True, "reversible": True},
    },
    {
        "id": "routine-file-edit",
        "expected_action": "auto_execute",
        "decision": {"routine_execution": True, "reversible": True, "known_scope": True},
    },
    {
        "id": "local-validation",
        "expected_action": "auto_execute",
        "decision": {"local_validation": True, "reversible": True, "known_scope": True},
    },
    {
        "id": "governance-record-update",
        "expected_action": "auto_execute",
        "decision": {"governance_record_update": True, "reversible": True, "known_scope": True},
    },
    {
        "id": "normal-commit-push",
        "expected_action": "auto_execute",
        "decision": {"commit_push": True, "reversible": True, "known_scope": True},
    },
    {
        "id": "reversible-default-assumption",
        "expected_action": "record_assumption",
        "decision": {
            "routine_execution": True,
            "reversible": True,
            "known_scope": False,
            "assumption_record": {
                "assumption": "Use existing repository style for naming and structure.",
                "basis": "Nearby files show the prevailing pattern.",
                "reversibility": "Can be renamed or reverted in one focused commit.",
                "validation": "Run the focused test or checker after the edit.",
                "rollback": "Revert the focused change if validation fails.",
            },
        },
    },
]


class InterruptionPolicy(NamedTuple):
    required_phrases: tuple
    template_phrases: tuple
    assumption_fields: tuple
    placeholder: re.Pattern
    critical_keys: tuple
    packet_signals: tuple
    examples: list


def classify_user_interruption(decision, critical_keys):
    """Return the required user-interruption action for a decision fact map."""
    if not isinstance(decision, dict):
        return "ask_user"
    if any(bool(decision.get(key)) for key in critical_keys):
        return "ask_user"
    if bool(decision.get("irreversible")) or bool(decision.get("destructive")):
        return "ask_user"
    if bool(decision.get("routine_execution")) or bool(decision.get("local_validation")) or bool(decision.get("governance_record_update")) or bool(decision.get("commit_push")):
        if decision.get("known_scope", False) is True:
            return "auto_execute"
        return "record_assumption"
    if decision.get("reversible", False) is True:
        return "record_assumption"
    return "ask_user"


def _validate_assumption_record(record, fields, placeholder):
    if not isinstance(record, dict):
        return ["assumption_record missing or invalid"]
    issues = []
    for field in fields:
        value = record.get(field)
        if not isinstance(value, str) or len(value.strip()) < 12:
            issues.append(f"assumption_record.{field} missing or too short")
        elif placeholder.search(value):
            issues.append(f"assumption_record.{field} must not be placeholder text")
    return issues


def _validate_interruption_policy_examples(examples, policy: InterruptionPolicy, classify):
    issues = []
    seen_critical = set()
    seen_auto = set()
    seen_assumption = False
    for example in examples:
        if not isinstance(example, dict):
            issues.append("policy example must be object")
            continue
        example_id = example.get("id", "<unknown>")
        decision = example.get("decision")
        expected = example.get("expected_action")
        actual = classify(decision)
        if actual != expected:
            issues.append(f"{example_id}: expected {expected}, got {actual}")
        if isinstance(decision, dict):
            seen_critical.update(key for key in policy.critical_keys if decision.get(key))
            if expected == "auto_execute":
                if decision.get("routine_execution"):
                    seen_auto.add("routine_execution")
                if decision.get("local_validation"):
                    seen_auto.add("local_validation")
                if decision.get("governance_record_update"):
                    seen_auto.add("governance_record_update")
                if decision.get("commit_push"):
                    seen_auto.add("commit_push")
            if expected == "record_assumption":
                seen_assumption = True
                issues.extend(f"{example_id}: {issue}" for issue in _validate_assumption_record(decision.get("assumption_record"), policy.assumption_fields, policy.placeholder))

    missing_critical = sorted(set(policy.critical_keys) - seen_critical)
    if missing_critical:
        issues.append(f"missing critical trigger examples: {', '.join(missing_critical)}")
    required_auto = {"routine_execution", "local_validation", "governance_record_update", "commit_push"}
    missing_auto = sorted(required_auto - seen_auto)
    if missing_auto:
        issues.append(f"missing auto-execute examples: {', '.join(missing_auto)}")
    if not seen_assumption:
        issues.append("missing record_assumption example")
    return issues


def _validate_packet_interruption_policy(packet, task_id, rules: InterruptionPolicy):
    policy = packet.get("interruption_policy") if isinstance(packet, dict) else None
    if not isinstance(policy, dict):
        return [f"{task_id}: missing interruption_policy"]
    issues = []
    mode = policy.get("mode")
    if not isinstance(mode, str) or "critical" not in mode.lower():
        issues.append(f"{task_id}: interruption_policy.mode must declare critical-only/default execute behavior")
    for field in ("critical_triggers", "auto_execute", "assumption_record", "interruption_budget"):
        if field not in policy:
            issues.append(f"{task_id}: interruption_policy.{field} missing")
    critical = policy.get("critical_triggers")
    if not isinstance(critical, list) or not all(isinstance(item, str) and len(item.strip()) >= 8 for item in critical):
        issues.append(f"{task_id}: interruption_policy.critical_triggers must be a non-empty string array")
    else:
        critical_text = " ".join(critical).lower()
        for token in rules.packet_signals:
            if token not in critical_text:
                issues.append(f"{task_id}: interruption_policy.critical_triggers missing {token}")
    auto_execute = policy.get("auto_execute")
    if not isinstance(auto_execute, list) or not all(isinstance(item, str) and len(item.strip()) >= 8 for item in auto_execute):
        issues.append(f"{task_id}: interruption_policy.auto_execute must be a non-empty string array")
    else:
        auto_text = " ".join(auto_execute).lower()
        if "routine" not in auto_text or "record" not in auto_text:
            issues.append(f"{task_id}: interruption_policy.auto_execute must cover routine execution and record updates")
    issues.extend(f"{task_id}: {issue}" for issue in _validate_assumption_record(policy.get("assumption_record"), rules.assumption_fields, rules.placeholder))
    budget = policy.get("interruption_budget")
    if not isinstance(budget, str) or not re.search(r"(?:one|1|一次|single)", budget, re.IGNORECASE):
        issues.append(f"{task_id}: interruption_policy.interruption_budget must limit interruptions per work unit")
    return issues


def check_interruption_policy(
    boundary_path, policy_template_path, packet_path, examples, select_packets,
    policy: InterruptionPolicy, classify, validate_examples,
):
    """FIX-093: verify critical-only user interruption policy and packet fields."""
    result = {
        "examples": [],
        "required_tasks": [],
        "entries": [],
        "issues": [],
        "pass": True,
    }

    if not boundary_path.is_file():
        result["issues"].append(f"missing interaction boundary policy: {boundary_path}")
    else:
        boundary_text = boundary_path.read_text(encoding="utf-8")
        for phrase in policy.required_phrases:
            if phrase not in boundary_text:
                result["issues"].append(f"interaction boundary missing required phrase: {phrase}")

    if not policy_template_path.is_file():
        result["issues"].append(f"missing interruption policy template: {policy_template_path}")
    else:
        template_text = policy_template_path.read_text(encoding="utf-8")
        for phrase in policy.template_phrases:
            if phrase not in template_text:
                result["issues"].append(f"interruption policy template missing required phrase: {phrase}")

    example_list = examples if examples is not None else policy.examples
    example_issues = validate_examples(example_list)
    for example in example_list:
        decision = example.get("decision", {}) if isinstance(example, dict) else {}
        result["examples"].append({
            "id": example.get("id", "<unknown>") if isinstance(example, dict) else "<invalid>",
            "expected_action": example.get("expected_action") if isinstance(example, dict) else None,
            "actual_action": classify(decision),
        })
    result["issues"].extend(example_issues)

    for task, packet in select_packets(result, packet_path, "interruption_policy"):
        task_id = task["task_id"]
        entry_issues = _validate_packet_interruption_policy(packet, task_id, policy) if isinstance(packet, dict) else ["invalid packet"]
        result["entries"].append({"task_id": task_id, "status": "FAIL" if entry_issues else "PASS", "issues": entry_issues})

    if result["issues"] or any(entry["status"] == "FAIL" for entry in result["entries"]):
        result["pass"] = False
    return result
