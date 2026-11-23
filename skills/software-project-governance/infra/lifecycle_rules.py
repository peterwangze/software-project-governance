"""Read and validate the lifecycle registry, its project presets and evidence contracts."""

import json
import re
import sys
from pathlib import Path


LIFECYCLE_REGISTRY_ACTIVE_MODE = "classic-phase-gate"
LIFECYCLE_REGISTRY_DYNAMIC_MODE = "dynamic-flow-gate"
LIFECYCLE_REGISTRY_GATES = [f"G{i}" for i in range(1, 12)]
LIFECYCLE_REGISTRY_STAGE_IDS = [
    "initiation",
    "research",
    "selection",
    "infrastructure",
    "architecture",
    "development",
    "testing",
    "ci-cd",
    "release",
    "operations",
    "maintenance",
]
LIFECYCLE_REGISTRY_REQUIRED_PROJECT_TYPES = {
    "game",
    "web-app",
    "mobile-app",
    "library",
    "cli-tool",
    "ai-agent-plugin",
    "internal-script",
}
LIFECYCLE_REGISTRY_REQUIRED_PRESET_FIELDS = {
    "profile_intensity_boundary",
    "default_packs",
    "quality_budget",
    "acceptance_templates",
    "release_checks",
    "gate_policy",
    "gate_standards",
}
LIFECYCLE_REGISTRY_GATE_POLICY_REQUIRED_FIELDS = {
    "can_skip_stages",
    "can_merge_stages",
    "stage_skip_requires",
    "blocked_dependency_rule",
    "sibling_completion_rule",
}
LIFECYCLE_REGISTRY_REQUIRED_GAME_STANDARDS = {
    "chapter",
    "level",
    "asset",
    "narrative",
    "playability",
}
LIFECYCLE_REGISTRY_REQUIRED_LIBRARY_STANDARDS = {
    "api",
    "semver",
    "docs",
    "downstream-tests",
}
LIFECYCLE_REGISTRY_RISK_CLAIMS = [
    ("risk-036 closed", re.compile(r"\brisk-036\b[^\n.;|]{0,48}\bclosed\b")),
    ("risk-036 closed", re.compile(r"\bclosed\b[^\n.;|]{0,48}\brisk-036\b")),
    ("risk-036 closure achieved", re.compile(r"\brisk-036\b[^\n.;|]{0,48}\bclosure\s+achieved\b")),
    ("risk-037 closed", re.compile(r"\brisk-037\b[^\n.;|]{0,48}\bclosed\b")),
    ("risk-037 closed", re.compile(r"\bclosed\b[^\n.;|]{0,48}\brisk-037\b")),
    ("risk-037 closure achieved", re.compile(r"\brisk-037\b[^\n.;|]{0,48}\bclosure\s+achieved\b")),
    ("1.0.0 production-ready", re.compile(r"\b1\.0\.0\s+production-ready\b")),
]
LIFECYCLE_REGISTRY_FORBIDDEN_OVERCLAIMS = [
    (
        "declarative gate engine active",
        re.compile(r"\bdeclarative\s+gate\s+engine\s+(?:is\s+)?active\b"),
    ),
    (
        "declarative gate engine active",
        re.compile(r"\bdeclarative\s+gate\s+engine\s+activated\b"),
    ),
    (
        "declarative gate engine active",
        re.compile(r"\b(?:activate|activates|activated|activating)\s+(?:the\s+)?declarative\s+gate\s+engine\b"),
    ),
    (
        "dynamic-flow-gate default",
        re.compile(r"\bdynamic-flow-gate\s+(?:is\s+)?(?:now\s+)?(?:the\s+)?default(?:\s+lifecycle\s+mode)?\b"),
    ),
    (
        "dynamic-flow-gate default",
        re.compile(r"\b(?:make|makes|made|making)\s+dynamic-flow-gate\s+(?:the\s+)?default(?:\s+lifecycle\s+mode)?\b"),
    ),
    (
        "dynamic-flow-gate default",
        re.compile(r"\bdefault\s+lifecycle\s+mode\s+(?:is\s+|now\s+)?dynamic-flow-gate\b"),
    ),
]


def _lifecycle_registry_text_values(value, *, inputs):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from inputs.lifecycle_registry_text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from inputs.lifecycle_registry_text_values(item)


def _load_lifecycle_registry(root=None, *, inputs):
    root = root or inputs.product_root
    registry_path = root / "skills/software-project-governance/core/lifecycle-registry.json"
    display = inputs.display_path(registry_path, root)
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"{display}: missing lifecycle registry"]
    except json.JSONDecodeError as exc:
        return None, [f"{display}: invalid JSON: {exc}"]
    except (ValueError, OSError, RecursionError) as exc:
        return None, [f"{display}: unreadable lifecycle registry: {exc}"]
    if not isinstance(registry, dict):
        return None, [f"{display}: lifecycle registry root must be an object"]
    return registry, []


def _lifecycle_registry_manifest_issues(root, registry_path, display, *, inputs):
    manifest_path = root / "skills/software-project-governance/core/manifest.json"
    if not manifest_path.exists():
        return [f"{display}: core/manifest.json is required to make the lifecycle registry a canonical product artifact"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{inputs.display_path(manifest_path, root)}: invalid JSON: {exc}"]
    artifact_entries = inputs.manifest_artifact_entries(manifest)
    registry_artifacts = [
        entry for entry in artifact_entries
        if isinstance(entry, dict)
        and entry.get("id") == "lifecycle-registry"
        and entry.get("path") == "skills/software-project-governance/core/lifecycle-registry.json"
    ]
    if not registry_artifacts:
        return [f"{display}: core/manifest.json must declare lifecycle-registry as a canonical product artifact"]
    return []


def check_lifecycle_registry(root=None, registry=None, *, inputs):
    """Resolve the active workflow, tier routes, local evidence contracts and project presets."""
    import loop_engine
    from loop_workflow import TIERS

    root = Path(root or inputs.product_root)
    core = root / "skills/software-project-governance/core"
    path = core / "lifecycle-registry.json"
    display = inputs.display_path(path, root)
    if registry is None:
        registry, issues = inputs.load_lifecycle_registry(root)
        if issues:
            return issues

    failures = inputs.lifecycle_registry_manifest_issues(root, path, display)
    if registry.get("workflow") != "software-project-governance" or registry.get("source_of_truth") is not True:
        failures.append(f"{display}: invalid workflow or source_of_truth")
    if registry.get("registry_mode") != "loop-unit-gates":
        failures.append(f"{display}: registry_mode must be loop-unit-gates")
    for key in ("active_lifecycle_mode", "default_lifecycle_mode"):
        if registry.get(key) != "loop-engineering":
            failures.append(f"{display}: {key} must be loop-engineering")
    activation = registry.get("runtime_activation")
    for key in ("flow_unit_status_runtime", "unit_scoped_gate_execution"):
        if not isinstance(activation, dict) or activation.get(key) is not True:
            failures.append(f"{display}: runtime_activation.{key} must be true")
    modes = registry.get("lifecycle_modes")
    if not isinstance(modes, list) or len(modes) != 1 or not isinstance(modes[0], dict):
        return failures + [f"{display}: exactly one executable lifecycle mode is required"]
    mode = modes[0]
    if (mode.get("id") != "loop-engineering" or mode.get("active") is not True
            or mode.get("default") is not True or mode.get("runtime_command") != "loop"):
        failures.append(f"{display}: lifecycle_modes must select the loop command")
    if mode.get("workflow_source") != "lifecycle.md" or not (core / "lifecycle.md").is_file():
        failures.append(f"{display}: missing lifecycle.md workflow source")
    policy = registry.get("loop_policy")
    if not isinstance(policy, dict) or policy.get("scope") != "per-flow-unit" or policy.get("runtime_activation") is not True:
        failures.append(f"{display}: loop_policy must activate per-flow-unit execution")
        policy = policy if isinstance(policy, dict) else {}
    if policy.get("read_command") != "loop status --unit <id> --json":
        failures.append(f"{display}: loop_policy.read_command must select the unit")
    if any(item.get("topology_source") != "loop-engineering-registry.json" for item in (mode, policy)):
        failures.append(f"{display}: workflow and policy must reference the runtime topology")
    topology, topology_issues = loop_engine.load_loop_registry(core.parent)
    failures.extend(topology_issues)
    topology = topology if isinstance(topology, dict) else {}
    if topology.get("registry_mode") != "native-loop-execution" or topology.get("workflow_model") != "loop-engineering":
        failures.append(f"{display}: runtime topology must declare native loop execution")
    paths = topology.get("iteration_paths")
    if not isinstance(paths, dict) or set(paths) != set(TIERS):
        failures.append(f"{display}: every executable tier needs an iteration path")
        paths = paths if isinstance(paths, dict) else {}
    gates = set(inputs.gates)
    consumed = {"G1"}  # explicit one-time project decision at setup intake
    for tier, route in paths.items():
        if not inputs.is_valid_string_list(route) or not set(route) <= gates or len(route) != len(set(route)):
            failures.append(f"{display}: {tier} has invalid or empty local gates")
        else:
            consumed.update(route)
    if gates != consumed:
        failures.append(f"{display}: unconsumed local gates: {sorted(gates - consumed)}")
    targets = topology.get("rework_targets")
    if not isinstance(targets, dict):
        failures.append(f"{display}: topology must declare rework targets")
    else:
        for gate, pair in targets.items():
            if (gate not in gates or not isinstance(pair, list) or len(pair) != 2
                    or not isinstance(pair[0], str) or not isinstance(paths.get(pair[0]), list)
                    or pair[1] not in paths[pair[0]]):
                failures.append(f"{display}: invalid rework target for {gate}")

    activities = registry.get("stage_vocabulary") or []
    activity_gates = {a["id"]: a.get("related_gate") for a in activities
                      if isinstance(a, dict) and isinstance(a.get("id"), str)}
    refs = registry.get("gate_references")
    if not isinstance(refs, list):
        return failures + [f"{display}: missing gate_references"]
    catalog = core / "stage-gates.md"
    headings = set(re.findall(r"^##\s+(G\d+)\b", inputs.read_text_normalized(catalog), re.M)) if catalog.is_file() else set()
    gate_id_set = set()
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("gate_id"), str):
            failures.append(f"{display}: invalid gate reference")
            continue
        gate = ref["gate_id"]
        if gate in gate_id_set or gate not in gates:
            failures.append(f"{display}: duplicate or unknown gate reference {gate}")
        gate_id_set.add(gate)
        if (not isinstance(ref.get("activity"), str) or activity_gates.get(ref["activity"]) != gate
                or ref.get("source") != f"skills/software-project-governance/core/stage-gates.md#{gate}"
                or gate not in headings):
            failures.append(f"{display}: {gate} must resolve to its activity and gate evidence catalog section")
    if gate_id_set != gates:
        failures.append(f"{display}: missing gate reference {sorted(gates - gate_id_set)}")
    project_type_hooks = registry.get("project_type_hooks")
    if not isinstance(project_type_hooks, dict):
        failures.append(f"{display}: project_type_hooks must be an object")
        project_type_hooks = {}
    missing_hook_project_types = sorted(inputs.required_project_types - set(project_type_hooks))
    if missing_hook_project_types:
        failures.append(f"{display}: missing project_type_hooks for {', '.join(missing_hook_project_types)}")

    project_type_gate_presets = registry.get("project_type_gate_presets")
    if not isinstance(project_type_gate_presets, dict):
        failures.append(f"{display}: project_type_gate_presets must be an object")
        project_type_gate_presets = {}
    missing_preset_project_types = sorted(inputs.required_project_types - set(project_type_gate_presets))
    if missing_preset_project_types:
        failures.append(f"{display}: missing project_type_gate_presets for {', '.join(missing_preset_project_types)}")
    if set(project_type_gate_presets) != set(project_type_hooks):
        failures.append(f"{display}: project_type_gate_presets keys must match project_type_hooks keys")

    failures.extend(inputs.check_gate_execution_registry(registry, display, gate_id_set, project_type_hooks))

    for project_type, hooks in project_type_hooks.items():
        hook_label = f"{display}: project_type_hooks.{project_type}"
        if not isinstance(hooks, dict):
            failures.append(f"{hook_label} must be an object")
            continue
        unit_templates = hooks.get("unit_templates")
        if not inputs.is_valid_string_list(unit_templates):
            failures.append(f"{hook_label}.unit_templates must be a non-empty string list")
            continue
        default_flow_unit_type = hooks.get("default_flow_unit_type")
        if default_flow_unit_type not in unit_templates:
            failures.append(
                f"{hook_label}.default_flow_unit_type must be included in unit_templates"
            )
    for project_type, preset in project_type_gate_presets.items():
        preset_label = f"{display}: project_type_gate_presets.{project_type}"
        hooks = project_type_hooks.get(project_type, {})
        if not isinstance(preset, dict):
            failures.append(f"{preset_label} must be an object")
            continue
        missing_fields = sorted(inputs.required_preset_fields - set(preset))
        for field in missing_fields:
            failures.append(f"{preset_label}: missing required field `{field}`")

        boundary_text = preset.get("profile_intensity_boundary")
        if not isinstance(boundary_text, str) or not boundary_text.strip():
            failures.append(f"{preset_label}.profile_intensity_boundary must be a non-empty string")
        else:
            lowered_boundary = boundary_text.lower()
            if "project type" not in lowered_boundary or "profile" not in lowered_boundary or "orthogonal" not in lowered_boundary:
                failures.append(
                    f"{preset_label}.profile_intensity_boundary must state project type and profile are orthogonal"
                )

        for field in ("default_packs", "acceptance_templates", "release_checks"):
            if not inputs.is_valid_string_list(preset.get(field)):
                failures.append(f"{preset_label}.{field} must be a non-empty string list")
        if "governance-core" not in preset.get("default_packs", []):
            failures.append(f"{preset_label}.default_packs must include governance-core")

        quality_budget = preset.get("quality_budget")
        if not isinstance(quality_budget, dict) or not quality_budget:
            failures.append(f"{preset_label}.quality_budget must be a non-empty object")
        else:
            for key, value in quality_budget.items():
                if not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not value.strip():
                    failures.append(f"{preset_label}.quality_budget entries must be non-empty strings")

        gate_policy = preset.get("gate_policy")
        if not isinstance(gate_policy, dict):
            failures.append(f"{preset_label}.gate_policy must be an object")
            gate_policy = {}
        for field in sorted(inputs.gate_policy_required_fields):
            if field not in gate_policy:
                failures.append(f"{preset_label}.gate_policy missing `{field}`")
        if not isinstance(gate_policy.get("can_skip_stages", []), list):
            failures.append(f"{preset_label}.gate_policy.can_skip_stages must be a list")
        if not isinstance(gate_policy.get("can_merge_stages", []), list):
            failures.append(f"{preset_label}.gate_policy.can_merge_stages must be a list")
        for field in ("stage_skip_requires", "blocked_dependency_rule", "sibling_completion_rule"):
            if not isinstance(gate_policy.get(field), str) or not gate_policy.get(field, "").strip():
                failures.append(f"{preset_label}.gate_policy.{field} must be a non-empty string")

        preset_unit_templates = preset.get("unit_templates")
        if not inputs.is_valid_string_list(preset_unit_templates):
            failures.append(f"{preset_label}.unit_templates must be a non-empty string list")
            preset_unit_templates = []
        elif isinstance(hooks, dict) and inputs.is_valid_string_list(hooks.get("unit_templates")) and preset_unit_templates != hooks.get("unit_templates"):
            failures.append(f"{preset_label}.unit_templates must match project_type_hooks.{project_type}.unit_templates")
        default_flow_unit_type = preset.get("default_flow_unit_type")
        if isinstance(hooks, dict) and hooks.get("default_flow_unit_type") and default_flow_unit_type != hooks.get("default_flow_unit_type"):
            failures.append(f"{preset_label}.default_flow_unit_type must match project_type_hooks.{project_type}.default_flow_unit_type")
        if default_flow_unit_type not in preset_unit_templates:
            failures.append(f"{preset_label}.default_flow_unit_type must be included in unit_templates")
        gate_standards = preset.get("gate_standards")
        if not isinstance(gate_standards, list) or not gate_standards:
            failures.append(f"{preset_label}.gate_standards must be a non-empty list")
            gate_standards = []
        standard_ids = set()
        for standard in gate_standards:
            if not isinstance(standard, dict):
                failures.append(f"{preset_label}.gate_standards entries must be objects")
                continue
            standard_id = standard.get("standard_id")
            if not isinstance(standard_id, str) or not standard_id.strip():
                failures.append(f"{preset_label}.gate_standards entry missing standard_id")
            else:
                standard_ids.add(standard_id)
            gate_refs = standard.get("gate_references")
            if not inputs.is_valid_string_list(gate_refs):
                failures.append(f"{preset_label}.gate_standards.{standard_id}.gate_references must be a non-empty string list")
            else:
                for gate_id in gate_refs:
                    if gate_id not in gate_id_set:
                        failures.append(f"{preset_label}.gate_standards.{standard_id}: unknown gate reference `{gate_id}`")
            if not inputs.is_valid_string_list(standard.get("required_evidence")):
                failures.append(f"{preset_label}.gate_standards.{standard_id}.required_evidence must be a non-empty string list")
        if project_type == "game":
            missing_standards = sorted(inputs.required_game_standards - standard_ids)
            if missing_standards:
                failures.append(
                    f"{preset_label}.gate_standards missing game standards: {', '.join(missing_standards)}"
                )
        if project_type == "library":
            missing_standards = sorted(inputs.required_library_standards - standard_ids)
            if missing_standards:
                failures.append(
                    f"{preset_label}.gate_standards missing library standards: {', '.join(missing_standards)}"
                )

    for text in inputs.lifecycle_registry_text_values(registry):
        lowered = text.lower()
        for label, pattern in inputs.forbidden_overclaims:
            for match in pattern.finditer(lowered):
                matched_text = text[match.start():match.end()]
                if not inputs.line_has_scoped_claim_negation(text, matched_text):
                    failures.append(f"{display}: forbidden lifecycle overclaim `{label}`")
                    break
        for label, pattern in inputs.risk_claims:
            if pattern.search(lowered) and not inputs.line_has_scoped_claim_negation(text, label):
                failures.append(f"{display}: forbidden lifecycle overclaim `{label}`")

    return failures


def cmd_check_lifecycle_registry(args, *, load_lifecycle_registry, check_lifecycle_registry):
    """Run dynamic lifecycle registry schema-only consistency guard."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    registry, load_issues = load_lifecycle_registry()
    active_mode = registry.get("active_lifecycle_mode", "<unreadable>") if isinstance(registry, dict) else "<unreadable>"
    default_mode = registry.get("default_lifecycle_mode", "<unreadable>") if isinstance(registry, dict) else "<unreadable>"
    issues = load_issues or check_lifecycle_registry(registry=registry)
    print("\n=== Lifecycle Registry Check ===")
    print(f"  Active lifecycle mode: {active_mode}")
    print(f"  Default lifecycle mode: {default_mode}")
    if issues:
        print(f"  Result: FAILED — {len(issues)} issue(s)")
        for issue in issues[:20]:
            print(f"    - {issue}")
        if len(issues) > 20:
            print(f"    ... and {len(issues) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("  Result: PASSED — work-unit routes and evidence requirements resolve")
    print()
