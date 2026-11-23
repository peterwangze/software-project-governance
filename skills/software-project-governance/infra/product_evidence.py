"""Validate the published release documentation and architecture facts against their sources."""

from pathlib import Path
import re


def _release_docs_line_has_guard_context(label, line):
    if label != "rollback plan":
        return False
    lower = line.lower()
    return (
        ("release docs" in lower and "changelog" in lower and "声明" in lower)
        or ("release docs" in lower and "claim" in lower)
        or ("requirement reports" in lower and "claim" in lower)
        or "发布提交混入" in lower
        or "release package mixes" in lower
    )


def _tagged_release_replay_hint(version):
    """Release-specific acceptance lives with the source and evidence it inspected."""
    if version in ("0.45.0", "0.46.0", "0.47.0", "0.66.2"):
        return (f"Release v{version} uses its tagged verifier. From the repository root run:\n"
                f"  git worktree add --detach ../replay-{version} v{version}\n"
                "See the historical acceptance steps in skills/software-project-governance/infra/TOOLS.md.")
    return None


def check_release_docs_coverage(
        version, root, *, package_root, display_path, git_files, line_has_scoped_claim_negation,
        release_docs_line_has_guard_context, tagged_release_replay_hint, check_manifest_consistency,
):
    """REL-021: versioned release docs must be present, tracked, and conservative."""
    root = Path(root) if root is not None else package_root
    issues = []
    if not version or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        return issues

    replay_hint = tagged_release_replay_hint(version)
    if replay_hint:
        return [replay_hint]

    release_docs = [
        ("release checklist", f"docs/release/release-checklist-{version}.md"),
        ("feature flags", f"docs/release/feature-flags-{version}.md"),
        ("rollback plan", f"docs/release/rollback-plan-{version}.md"),
    ]
    tracked_files = git_files(["ls-files", "--cached"])
    manifest_result = check_manifest_consistency(root / "skills/software-project-governance/core/manifest.json")
    manifest_missing = set(manifest_result.get("missing", [])) if manifest_result.get("pass") is not None else set()
    manifest_untracked = set(manifest_result.get("untracked", [])) if manifest_result.get("pass") is not None else set()
    boundary_needles = [
        "official approval",
        "marketplace approval",
        "universal/full runtime support",
        "external first-session pilot success",
        "RISK-036",
    ]
    forbidden_positive_claims = [
        "official approval granted",
        "official approval approved",
        "officially approved",
        "marketplace approval granted",
        "marketplace approval approved",
        "marketplace approved",
        "universal runtime support is verified",
        "universal runtime support is supported",
        "universal runtime support verified",
        "universal runtime support supported",
        "full runtime support is verified",
        "full runtime support is supported",
        "full runtime support verified",
        "full runtime support supported",
        "universal/full runtime support is verified",
        "universal/full runtime support is supported",
        "universal/full runtime support verified",
        "universal/full runtime support supported",
        "external first-session pilot success",
        "external first-session pilot pass",
        "external first-session pilot passed",
        "codex desktop marketplace-management e2e pass",
        "codex desktop marketplace-management e2e passed",
        "automatic best-tool selection pass",
        "automatic best-tool selection is passed",
        "automatic best-tool selection passed",
        "automatic best-tool selection is available",
        "automatic best-tool selection available",
        "automatic best-tool selection is verified",
        "automatic best-tool selection verified",
        "universal plugin/skill/tool availability pass",
        "universal plugin/skill/tool availability is passed",
        "universal plugin/skill/tool availability passed",
        "universal plugin/skill/tool availability is available",
        "universal plugin/skill/tool availability available",
        "universal plugin/skill/tool availability is verified",
        "universal plugin/skill/tool availability verified",
        "catalog entry runtime pass",
        "catalog entry runtime is passed",
        "catalog entry runtime passed",
        "catalog entry runtime is available",
        "catalog entry runtime available",
        "catalog entry runtime is verified",
        "catalog entry runtime verified",
        "1.0.0 production-ready",
        "risk-036 closed",
    ]

    for label, rel_path in release_docs:
        path = root / rel_path
        display = display_path(path, root)
        if not path.is_file():
            issues.append(f"{display}: missing {label} for release {version}")
            continue
        if tracked_files is not None and rel_path not in tracked_files:
            issues.append(f"{display}: {label} must be tracked by git")
        if rel_path in manifest_missing:
            issues.append(f"{display}: {label} is declared in manifest but missing from tracked files")
        if rel_path in manifest_untracked:
            issues.append(f"{display}: {label} exists but is not covered by manifest")

        content = path.read_text(encoding="utf-8")
        if version not in content:
            issues.append(f"{display}: {label} missing release version {version}")
        lower_content = content.lower()
        missing_needles = [needle for needle in boundary_needles if needle.lower() not in lower_content]
        if missing_needles:
            issues.append(f"{display}: {label} missing conservative boundary tokens: {', '.join(missing_needles)}")
        for phrase in forbidden_positive_claims:
            for line in content.splitlines():
                if (
                    phrase in line.lower()
                    and not line_has_scoped_claim_negation(line, phrase)
                    and not release_docs_line_has_guard_context(label, line)
                ):
                    issues.append(f"{display}: {label} forbidden release docs overclaim `{phrase}`")
                    break

    return issues


def _markdown_table_row_by_first_cell(content, first_cell, *, split_markdown_table_row):
    for line in content.splitlines():
        cells = split_markdown_table_row(line)
        if cells and cells[0].strip() == first_cell:
            return cells
    return None


def _contains_unnegated_phrase(
        content, phrases, *, line_has_scoped_claim_negation, line_has_structured_status_negation,
):
    for line in content.splitlines():
        lower_line = line.lower()
        for phrase in phrases:
            phrase_lower = phrase.lower()
            if (
                phrase_lower in lower_line
                and not line_has_scoped_claim_negation(line, phrase_lower)
                and not line_has_structured_status_negation(line, phrase_lower)
            ):
                return True
    return False


def _line_has_structured_status_negation(line, phrase):
    lower = line.lower()
    negated_values = (
        "no",
        "false",
        "fail",
        "failed",
        "blocked",
        "not_run",
        "not run",
        "missing",
        "unavailable",
        "not_available",
        "not available",
    )
    value_pattern = "|".join(re.escape(value) for value in negated_values)
    for match in re.finditer(re.escape(phrase.lower()), lower):
        suffix = lower[match.end():match.end() + 96]
        if re.match(rf"\s*(?:[:=：|]\s*)+(?:status\s*)?(?:{value_pattern})(?![a-z0-9_-])", suffix):
            return True
        if re.match(rf"\s+(?:is|are)\s+(?:{value_pattern})(?![a-z0-9_-])", suffix):
            return True
    return False


def _risk_status_is_closed(status):
    normalized = status.strip().strip("*`").lower()
    return normalized in {
        "已关闭",
        "关闭",
        "closed",
        "resolved",
        "closed/resolved",
        "resolved/closed",
    } or normalized.startswith("已关闭 ") or normalized.startswith("closed ")


def check_one_dot_zero_release_blockers(
        root, risk_log_path, external_validation_path, official_submission_path, desktop_lifecycle_path, *,
        package_root, contains_unnegated_phrase, display_path, markdown_table_row_by_first_cell,
        risk_status_is_closed,
):
    """FIX-130: hard-block 1.0.0 while final release evidence remains insufficient."""
    root = Path(root) if root is not None else package_root
    risk_log_path = Path(risk_log_path) if risk_log_path is not None else root / ".governance/risk-log.md"
    external_validation_path = (
        Path(external_validation_path)
        if external_validation_path is not None
        else root / "docs/requirements/external-project-validation-0.49.0.md"
    )
    official_submission_path = (
        Path(official_submission_path)
        if official_submission_path is not None
        else root / "docs/requirements/official-submission-final-bundle-review-0.49.0.md"
    )
    desktop_lifecycle_path = (
        Path(desktop_lifecycle_path)
        if desktop_lifecycle_path is not None
        else root / "docs/requirements/codex-desktop-marketplace-lifecycle-0.49.0.md"
    )

    issues = []

    if not risk_log_path.is_file():
        issues.append(f"{display_path(risk_log_path, root)}: missing RISK-036 status for 1.0.0 release")
    else:
        risk_content = risk_log_path.read_text(encoding="utf-8")
        risk_row = markdown_table_row_by_first_cell(risk_content, "RISK-036")
        if risk_row is None:
            issues.append(f"{display_path(risk_log_path, root)}: missing RISK-036 row for 1.0.0 release")
        else:
            status = risk_row[8].strip() if len(risk_row) > 8 else ""
            if not risk_status_is_closed(status):
                status_detail = status or "missing/unknown"
                issues.append(
                    "RISK-036 is not explicitly closed "
                    f"(`{status_detail}`); 1.0.0 release is blocked until the risk is closed"
                )

    if not external_validation_path.is_file():
        issues.append(f"{display_path(external_validation_path, root)}: missing external validation fact source")
    else:
        external_content = external_validation_path.read_text(encoding="utf-8")
        external_lower = external_content.lower()
        external_blocked_tokens = [
            "not a full pass",
            "no external project validation pass",
            "no external project validation full pass",
            "no external validation pass",
            "no external validation full pass",
            "external validation still未 full pass",
            "external validation full pass is missing",
            "missing external validation full pass",
            "still not full pass",
            "partial / blocked",
            "partial/blocked",
        ]
        external_pass_tokens = [
            "external validation full pass",
            "external project validation full pass",
            "two external project validations full pass",
            "2 external project validations full pass",
        ]
        has_positive_external_pass = contains_unnegated_phrase(external_content, external_pass_tokens)
        if any(token in external_lower for token in external_blocked_tokens):
            issues.append(
                f"{display_path(external_validation_path, root)}: external validation full PASS is missing"
            )
        elif not has_positive_external_pass:
            issues.append(
                f"{display_path(external_validation_path, root)}: missing explicit external validation full PASS evidence"
            )

    if not official_submission_path.is_file():
        issues.append(f"{display_path(official_submission_path, root)}: missing official submission result fact source")
    else:
        official_content = official_submission_path.read_text(encoding="utf-8")
        official_lower = official_content.lower()
        official_blocked_tokens = [
            "does not report any official response",
            "no official approval",
            "no marketplace approval",
            "not_available",
            "official result is not_available",
            "missing official submission result",
            "missing official approval",
            "without official approval",
        ]
        official_positive_tokens = [
            "official submission result: approved",
            "official submission result approved",
            "official approval granted",
            "officially approved",
            "marketplace approval granted",
        ]
        has_positive_official_result = contains_unnegated_phrase(official_content, official_positive_tokens)
        if any(token in official_lower for token in official_blocked_tokens):
            issues.append(
                f"{display_path(official_submission_path, root)}: official submission result or approval evidence is missing"
            )
        elif not has_positive_official_result:
            issues.append(
                f"{display_path(official_submission_path, root)}: missing explicit official submission result or approval evidence"
            )

    if not desktop_lifecycle_path.is_file():
        issues.append(f"{display_path(desktop_lifecycle_path, root)}: missing Codex Desktop lifecycle fact source")
    else:
        desktop_content = desktop_lifecycle_path.read_text(encoding="utf-8")
        desktop_lower = desktop_content.lower()
        desktop_pass = contains_unnegated_phrase(desktop_content, [
            "codex desktop marketplace-management e2e pass",
            "desktop lifecycle e2e pass",
            "desktop lifecycle pass",
        ])
        conservative_disposition = any(token in desktop_lower for token in [
            "conservative blocked carry-forward",
            "conservative blocked carry forward",
            "carry forward the desktop lifecycle blocker",
            "keeps 1.0.0 blocked",
            "desktop ui install/enable/invoke/upgrade/uninstall remains blocked/not_run",
            "desktop lifecycle remains blocked/not_run",
        ])
        if not desktop_pass and not conservative_disposition:
            issues.append(
                f"{display_path(desktop_lifecycle_path, root)}: Codex Desktop lifecycle PASS or explicit conservative disposition is missing"
            )

    return issues


def _specialist_skill_owner_issues(root, router, *, active_agent_roles):
    """Check the same role files and skill-table binding that a dispatched agent reads."""
    roles = {path.stem: path for path in (root / "agents").glob("*.md")}
    expected = {role.lower().replace(" ", "-") for role in active_agent_roles}
    issues = [f"active role files differ: {sorted(set(roles) ^ expected)}"] if set(roles) != expected else []
    specialists = {path.parent.name for path in (root / "skills").glob("*/SKILL.md")}
    specialists -= {"software-project-governance", "main-workflow"}
    owners = {}
    for role, path in roles.items():
        if f"agents/{role}.md" not in router:
            issues.append(f"dispatch route missing role {role}")
        for name in re.findall(r"^\|\s*`?([a-z][a-z0-9-]*)`?\s*\|", path.read_text(encoding="utf-8"), re.M):
            if name not in specialists:
                issues.append(f"{role}: unknown bound skill {name}")
            owners.setdefault(name, set()).add(role)
    issues.extend(f"no dispatched role consumes {name}" for name in sorted(specialists - owners.keys()))
    if owners.get("stage-operations") != {"release"}:
        issues.append("operational feedback requires Release as the responsible role")
    return issues


def check_architecture_fact_source(
        skill_path, skill_index_path, architecture_path, governance_command_path, agent_protocol_path,
        governance_developer_prompt_path, *, package_root, active_agent_roles, loop_role_skill_contracts,
        named_reviewer_roles, display_path, generic_reviewer_cells, markdown_has_heading, markdown_section,
        specialist_skill_owner_issues, check_repository_navigation,
):
    """FIX-065: keep Agent/team architecture facts synchronized."""
    navigation_root = package_root if architecture_path is None else None
    skill_path = skill_path or package_root / "skills/software-project-governance/SKILL.md"
    skill_index_path = skill_index_path or package_root / "skills/software-project-governance/references/skill-index.md"
    architecture_path = architecture_path or package_root / "project/references/architecture.md"
    governance_command_path = governance_command_path or package_root / "commands/governance.md"
    agent_protocol_path = agent_protocol_path or package_root / "skills/software-project-governance/references/agent-communication-protocol.md"
    governance_developer_prompt_path = governance_developer_prompt_path or package_root / "agents/governance-developer.md"

    documents = (
        skill_path, skill_index_path, architecture_path, governance_command_path,
        agent_protocol_path, governance_developer_prompt_path,
    )
    contents = {path: path.read_text(encoding="utf-8") for path in documents}

    current_navigation = markdown_section(contents[architecture_path], "## 当前目录导航")
    failures = check_repository_navigation(architecture_path, current_navigation, navigation_root)
    forbidden_patterns = [
        ("legacy 7 groups / 9 Agent narrative", r"7\s*组\s*9\s*Agent|7组9Agent"),
        ("legacy 46-line SKILL.md entry narrative", r"46\s*行"),
        ("legacy entry-layer no behavior rules narrative", r"不包含任何行为规则"),
        ("legacy native-entry exclusion narrative", r"仓库不包含任何平台原生入口文件"),
    ]
    for path, content in contents.items():
        rel = display_path(path)
        for label, pattern in forbidden_patterns:
            if re.search(pattern, content):
                failures.append(f"{rel}: forbidden {label}")

    skill_index_content = contents[skill_index_path]
    skill_content = contents[skill_path]
    required_skill_phrases = [
        "Coordinator 融入入口层",
        "Coordinator 接管用户交互",
        "Producer-Reviewer 分离",
    ]
    for phrase in required_skill_phrases:
        if phrase not in skill_content:
            failures.append(f"{display_path(skill_path)}: missing architecture fact phrase: {phrase}")

    if "skills/software-project-governance/SKILL.md" not in contents[governance_command_path]:
        failures.append(f"{display_path(governance_command_path)}: missing dispatch route to the main SKILL")
    if "后置审查" not in markdown_section(skill_content, "## Agent 分发路由"):
        failures.append(f"{display_path(skill_path)}: missing post-review routing for the review reader")
    if navigation_root is not None:
        failures.extend(specialist_skill_owner_issues(navigation_root, skill_content))

    rel_skill_index = display_path(skill_index_path)
    from governance_readers import markdown_table_cells
    routes = [cells for line in skill_index_content.splitlines()
              if len(cells := markdown_table_cells(line)) == 3 and "`" in cells[1]]
    reviewed = set()
    governance_route = False
    for activity, producers, consumers in routes:
        skill_ids = re.findall(r"`([a-z][a-z0-9-]*)`", producers + " " + consumers)
        for skill_id in skill_ids:
            if not (package_root / "skills" / skill_id / "SKILL.md").is_file():
                failures.append(f"{rel_skill_index}: {activity} references missing skill {skill_id}")
        if not consumers.strip():
            failures.append(f"{rel_skill_index}: {activity} has no artifact consumer")
        local_reviewers = re.findall(r"`([a-z]+-review)`", consumers)
        reviewed.update(local_reviewers)
        if local_reviewers and not any(role in consumers for role in named_reviewer_roles):
            failures.append(f"{rel_skill_index}: {activity} needs a named independent reviewer")
        if "Governance Developer" in producers and "`code-review`" in consumers and "Code Reviewer" in consumers:
            governance_route = True
    if not governance_route:
        failures.append(f"{rel_skill_index}: missing Governance Developer → independent Code Reviewer route")
    for name in sorted(set(loop_role_skill_contracts) - reviewed):
        failures.append(f"{rel_skill_index}: missing independent consumer for {name}")
    agent_protocol_content = contents[agent_protocol_path]
    rel_protocol = display_path(agent_protocol_path)
    for role in active_agent_roles:
        if not markdown_has_heading(agent_protocol_content, 3, role):
            failures.append(f"{rel_protocol}: missing active role communication contract: {role}")
    for reviewer_role in named_reviewer_roles:
        if not markdown_has_heading(agent_protocol_content, 3, reviewer_role):
            failures.append(f"{rel_protocol}: missing named reviewer communication contract: {reviewer_role}")
    if markdown_has_heading(agent_protocol_content, 3, "Reviewer"):
        failures.append(f"{rel_protocol}: generic Reviewer communication contract is forbidden")

    governance_developer_protocol = markdown_section(agent_protocol_content, "### Governance Developer")
    required_governance_developer_protocol_phrases = [
        "Proposed evidence-log entry",
        "Proposed decision-log / risk-log entry",
    ]
    if not governance_developer_protocol:
        failures.append(f"{rel_protocol}: missing Governance Developer communication contract")
    else:
        for phrase in required_governance_developer_protocol_phrases:
            if phrase not in governance_developer_protocol:
                failures.append(f"{rel_protocol}: Governance Developer contract missing {phrase}")

    governance_developer_prompt_content = contents[governance_developer_prompt_path]
    rel_governance_developer_prompt = display_path(governance_developer_prompt_path)
    if not re.search(r"治理记录由 Coordinator.{0,12}写回|Coordinator 负责最终写回", governance_developer_prompt_content):
        failures.append(f"{rel_governance_developer_prompt}: missing coordinator governance writeback boundary")
    if not re.search(r"(?:不|不得)直接写\s*`\.governance/`", governance_developer_prompt_content):
        failures.append(f"{rel_governance_developer_prompt}: direct governance writes must be prohibited")
    for path in (skill_path, skill_index_path, agent_protocol_path):
        rel = display_path(path)
        for line_no in generic_reviewer_cells(contents[path]):
            failures.append(f"{rel}:{line_no}: generic Reviewer role is forbidden; use named reviewer roles")

    for failure in failures:
        print(f"[FAIL] architecture fact source: {failure}")
    if not failures:
        print("[OK] architecture fact source synchronized")
    return failures
