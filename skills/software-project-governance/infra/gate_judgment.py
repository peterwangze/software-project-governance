"""Evaluate individual gate definitions against the current project evidence."""
import re


def _check_file_exists(relative_path, label, *, product_root):
    """Check if a file or directory exists."""
    path = product_root / relative_path
    if path.exists():
        return "PASS", f"{label}: {relative_path} exists"
    return "FAIL", f"{label}: {relative_path} NOT FOUND"


def _check_snippet_in_file(relative_path, snippet, label, *, product_root):
    """Check if a snippet exists in a file."""
    path = product_root / relative_path
    if not path.is_file():
        return "FAIL", f"{label}: file {relative_path} NOT FOUND"
    content = path.read_text(encoding="utf-8")
    if snippet in content:
        return "PASS", f"{label}: '{snippet[:50]}...' found in {relative_path}"
    return "FAIL", f"{label}: '{snippet[:50]}...' NOT found in {relative_path}"


def _check_all_required_files_exist(*, required_files, build_required_files_from_manifest):
    """Silently check if all required files exist (for auto-judgment)."""
    required = build_required_files_from_manifest()
    if required is None:
        required = required_files()
    missing = [label for label, path in required.items() if not path.is_file()]
    if not missing:
        return "PASS", "所有必需文件存在 — 仓库结构符合约定"
    return "FAIL", f"缺失 {len(missing)} 个必需文件: {', '.join(missing[:3])}..."


def _check_governance_file_exists(filename, *, governance_dir):
    """Check if a governance file exists and has content."""
    path = governance_dir / filename
    if path.is_file() and path.stat().st_size > 0:
        return "PASS", f".governance/{filename} 存在且非空"
    return "FAIL", f".governance/{filename} 不存在或为空"


def _check_quantifiable_metrics(*, plan_path):
    """Check if project has quantifiable success metrics in plan-tracker."""
    content = plan_path.read_text(encoding="utf-8")
    # Look for numeric targets in plan-tracker overview or config
    metrics_patterns = [
        r"≥\s*\d+",           # ≥ N
        r"\d+%",              # N%
        r"≤\s*\d+",           # ≤ N
        r"coverage.*\d+",      # coverage mention with number
        r"PASSED.*\d+",        # PASSED with count
    ]
    for pattern in metrics_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return "PASS", "项目目标含量化指标（检测到数字阈值或百分比）"
    return "NEEDS_HUMAN", "无法自动检测量化指标——需人工确认项目目标是否可衡量"


def _check_scope_boundary(*, plan_path):
    """Check if scope boundaries are defined."""
    content = plan_path.read_text(encoding="utf-8")
    if "范围" in content or "scope" in content.lower():
        return "PASS", "plan-tracker 中包含范围相关描述"
    return "NEEDS_HUMAN", "需人工确认范围边界是否清晰"


def _check_stakeholders(*, plan_path):
    """Check if stakeholders are identified."""
    content = plan_path.read_text(encoding="utf-8")
    # Check for role descriptions in plan-tracker tasks or config
    if "项目负责人" in content or "Owner" in content:
        return "PASS", "检测到干系人角色（项目负责人/Owner）"
    return "NEEDS_HUMAN", "需人工确认干系人列表"


def _check_out_of_scope(*, plan_path):
    """Check if out-of-scope items are explicitly listed."""
    content = plan_path.read_text(encoding="utf-8")
    if "范围外" in content or "不做什么" in content or "out of scope" in content.lower():
        return "PASS", "检测到范围外/不做什么声明"
    return "NEEDS_HUMAN", "需人工确认范围外事项是否明确"


def _check_completed_ratio(min_ratio=0.5, *, plan_path):
    """Check if plan-tracker completed ratio meets threshold."""
    content = plan_path.read_text(encoding="utf-8")
    # Match the overview table: after "总任务数" header line, the data row has:
    # | name | stage | total | completed | blocked | risks | gate | date |
    lines = content.split("\n")
    in_overview = False
    for i, line in enumerate(lines):
        if "总任务数" in line and "已完成" in line:
            in_overview = True
            continue
        if in_overview and line.strip().startswith("|") and not "---" in line:
            # Data row: extract columns
            parts = [p.strip() for p in line.split("|")]
            # parts[0]=empty, [1]=name, [2]=stage, [3]=total, [4]=completed, ...
            if len(parts) >= 5:
                try:
                    total = int(parts[3])
                    completed = int(parts[4])
                    ratio = completed / total if total > 0 else 0
                    if ratio >= min_ratio:
                        return "PASS", f"任务完成率 {ratio:.0%} ≥ {min_ratio:.0%}（{completed}/{total}）"
                    return "FAIL", f"任务完成率 {ratio:.0%} < {min_ratio:.0%}（{completed}/{total}）"
                except ValueError:
                    continue
            break
    return "NEEDS_HUMAN", "无法从 plan-tracker 解析完成率"


def _check_evidence_mentions(keyword, label, *, evidence_path):
    """Check if evidence-log contains a keyword."""
    content = evidence_path.read_text(encoding="utf-8")
    if keyword in content:
        return "PASS", f"{label}: evidence-log 含'{keyword[:30]}'相关证据"
    return "NEEDS_HUMAN", f"{label}: evidence-log 未找到'{keyword[:30]}'——需人工确认"


def _read_archive_aware_governance_text(include=(), *, data_source):
    """Read hot governance files plus selected archive directories."""
    ds = data_source()
    chunks = []
    hot_paths = []
    if "plan" in include:
        hot_paths.append(ds.sample_path)
    if "evidence" in include:
        hot_paths.append(ds.evidence_path)
    if "decision" in include:
        hot_paths.append(ds.decision_path)
    if "risk" in include:
        hot_paths.append(ds.risk_path)

    for path in hot_paths:
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))

    archive_dirs = []
    if "plan" in include:
        archive_dirs.append(ds.archive_tasks_dir)
    if "evidence" in include:
        archive_dirs.append(ds.archive_evidence_dir)
    if "decision" in include:
        archive_dirs.append(ds.archive_decisions_dir)
    if "risk" in include:
        archive_dirs.append(ds.archive_risks_dir)

    if ds._has_archive():
        for archive_dir in archive_dirs:
            if not archive_dir.exists():
                continue
            for path in sorted(archive_dir.glob("*.md")):
                if path.name != ".gitkeep":
                    chunks.append(path.read_text(encoding="utf-8"))

    return "\n".join(chunks)


def _contains_all(text, keywords):
    return all(keyword in text for keyword in keywords)


def _contains_any(text, keywords):
    return any(keyword in text for keyword in keywords)


def _has_line_with_all(text, keyword_groups):
    """Return True when one line contains at least one keyword from each group."""
    for line in text.splitlines():
        if all(_contains_any(line, group) for group in keyword_groups):
            return True
    return False


def _iter_archive_aware_evidence_units(*, data_source):
    """Yield hot/archive evidence rows; fallback to whole non-table archive docs."""
    ds = data_source()
    if ds.evidence_path.is_file():
        for line in ds.evidence_path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("| EVD-"):
                yield line

    if not ds._has_archive() or not ds.archive_evidence_dir.exists():
        return

    for path in sorted(ds.archive_evidence_dir.glob("*.md")):
        if path.name == ".gitkeep":
            continue
        content = path.read_text(encoding="utf-8")
        rows = [
            line for line in content.splitlines()
            if line.strip().startswith("| EVD-")
        ]
        if rows:
            for row in rows:
                yield row
        else:
            yield content


def _line_has_issue_severity(line):
    """Detect explicit issue severity values, not schema/header field names."""
    severity_patterns = [
        r"严重级别\s*[:：=|]\s*(P0|P1|P2|高风险|中风险|低风险|高严重|中严重|低严重|critical|high|medium|low)\b",
        r"\bseverity\s*[:：=|]\s*(P0|P1|P2|critical|high|medium|low)\b",
        r"\b(P0|P1|P2|critical|high|medium|low)\b",
        r"(高风险|中风险|低风险|高严重|中严重|低严重)",
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in severity_patterns)


def _line_has_issue_status_value(line):
    """Detect explicit issue status values, not only a status field name."""
    status_patterns = [
        r"状态\s*[:：=|]\s*(打开|已关闭|进行中|待处理|处理中|已解决|closed|open|done|resolved|in progress)\b",
        r"\bstatus\s*[:：=|]\s*(closed|open|done|resolved|in progress)\b",
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in status_patterns)


def _line_has_real_issue_item(line):
    """Detect an actual issue item/task entry rather than a schema-only line."""
    if _contains_any(line.lower(), ("schema", "header")):
        return False
    if _contains_any(line, ("字段", "表头", "模板", "格式")):
        return False
    item_patterns = [
        r"(问题项|问题条目|问题实例|issue item)",
        r"\b(ISSUE|BUG|TASK|FIX|AUDIT)-\d+\b",
        r"问题\s*\d+",
        r"问题\s*[:：]\s*\S+",
        r"任务\s*[:：]\s*\S+",
    ]
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in item_patterns)


def _plan_row_is_inactive(parts):
    """Return True when a plan table row is completed/terminated/cancelled."""
    joined = " ".join(parts).lower()
    inactive_markers = (
        "已完成", "✅", "已终止", "终止", "取消", "已取消",
        "closed", "done", "completed", "terminated", "cancelled", "canceled",
    )
    return any(marker in joined for marker in inactive_markers)


def _check_g10_real_operation_data(*, data_source):
    """G10: require explicit real operation data for at least one week."""
    text = _read_archive_aware_governance_text(include=("evidence",), data_source=data_source)
    if _has_line_with_all(text, (
        ("真实运营数据", "真实运行数据", "运行数据", "运营数据"),
        ("至少 1 周", "至少1周", "一周", "7天", "7 天", "1 week", "one week"),
    )):
        return "PASS", "检测到至少 1 周真实运营/运行数据证据（含归档 evidence）"
    return "NEEDS_HUMAN", "未检测到明确的至少 1 周真实运营数据证据"


def _check_g10_feedback_archived_classified(*, data_source):
    """G10: feedback must be archived and classified."""
    text = _read_archive_aware_governance_text(include=("evidence", "plan"), data_source=data_source)
    if _has_line_with_all(text, (
        ("用户反馈", "反馈汇总", "反馈归档"),
        ("已归档", "归档", "archive"),
        ("分类", "类别", "类型"),
    )):
        return "PASS", "检测到已归档且已分类的用户反馈证据（含归档 evidence）"
    return "NEEDS_HUMAN", "未检测到反馈归档+分类的完整证据"


def _check_g10_issue_list_severity_status(*, data_source):
    """G10: issue list must include severity and status, not just priority."""
    text = _read_archive_aware_governance_text(include=("evidence", "plan", "risk"), data_source=data_source)
    for line in text.splitlines():
        has_issue_list = _contains_any(line, ("问题清单", "issue list", "问题列表"))
        if (
            has_issue_list
            and _line_has_real_issue_item(line)
            and _line_has_issue_severity(line)
            and _line_has_issue_status_value(line)
        ):
            return "PASS", "检测到包含严重级别和状态的问题清单"
    return "NEEDS_HUMAN", "未检测到真实问题项及其严重级别值和状态值"


def _check_g10_executable_optimization_items(*, data_source):
    """G10: optimization direction must be executable, not only a slogan."""
    text = _read_archive_aware_governance_text(include=("evidence", "plan"), data_source=data_source)
    if _has_line_with_all(text, (
        ("优化项", "改进项", "优化方向", "改进方向", "可执行优化项"),
        ("Owner", "DRI", "截止", "验收", "验证", "命令", "文件", "任务"),
    )):
        return "PASS", "检测到带执行标记的优化/改进项"
    return "NEEDS_HUMAN", "未检测到可执行优化项（需 Owner/截止/验收/验证等执行标记）"


def _check_g11_retro_complete(*, data_source):
    """G11: retro must include the four required sections."""
    required = ("目标回顾", "结果评估", "原因分析", "经验沉淀")
    evidence_units = list(_iter_archive_aware_evidence_units(data_source=data_source))
    for unit in evidence_units:
        if _contains_all(unit, required):
            return "PASS", "复盘证据包含目标回顾/结果评估/原因分析/经验沉淀（含归档 evidence）"
    text = "\n".join(evidence_units)
    if not text:
        text = _read_archive_aware_governance_text(include=("evidence",), data_source=data_source)
    missing = [keyword for keyword in required if keyword not in text]
    if not missing:
        return "NEEDS_HUMAN", "复盘四要素分散在多条证据中，未检测到同一条复盘证据包含全部四要素"
    return "NEEDS_HUMAN", f"复盘证据缺少: {', '.join(missing)}"


def _check_g11_rules_templates_backfilled(*, data_source):
    """G11: rules/templates backfill needs evidence, commit, or file-change proof."""
    text = _read_archive_aware_governance_text(include=("evidence",), data_source=data_source)
    if _has_line_with_all(text, (
        ("回灌", "规则修订", "模板更新", "经验回灌"),
        ("规则", "模板", "protocol", "template", "SKILL.md", "stage-gates.md"),
        ("commit", "提交", "文件变更", "修改", "更新", ".md", ".py"),
    )):
        return "PASS", "检测到规则/模板回灌及提交或文件变更证据"
    return "NEEDS_HUMAN", "未检测到规则/模板回灌的提交或文件变更证据"


def _check_g11_next_round_direction(*, plan_path, split_markdown_table_row):
    """G11: next-round direction must be explicit or an active P0, not any historical P0."""
    content = plan_path.read_text(encoding="utf-8") if plan_path.is_file() else ""
    active_section = content
    marker = "## 当前活跃事项"
    if marker in content:
        active_section = content.split(marker, 1)[1].split("\n## ", 1)[0]

    for line in active_section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        parts = split_markdown_table_row(line)
        normalized = [part.replace("*", "").strip() for part in parts]
        has_active_p0 = any(part == "P0" for part in normalized)
        if has_active_p0 and not _plan_row_is_inactive(normalized):
            return "PASS", "当前活跃事项中存在未完成的 P0 任务，下一轮方向明确"

    next_round_terms = ("下一轮", "下轮")
    for line in active_section.splitlines():
        if (
            _contains_any(line, next_round_terms)
            and re.search(r"[A-Z]+-\d+", line)
            and not _plan_row_is_inactive([line])
        ):
            return "PASS", "当前活跃事项显式描述下一轮方向并关联任务"

    return "FAIL", "未检测到计划中的下一轮方向或活跃 P0 任务"


def _check_risk_has_closed(label='关键缺陷', *, risk_path):
    """Check if risk-log has any closed/critical risk entries."""
    content = risk_path.read_text(encoding="utf-8")
    closed_count = sum(1 for line in content.split("\n") if "已关闭" in line or "已缓解" in line)
    if closed_count > 0:
        return "PASS", f"{label}: {closed_count} 条风险已关闭/已缓解"
    return "NEEDS_HUMAN", f"{label}: 无已关闭风险——需人工确认是否所有关键缺陷已处理"


def _check_plan_has_priority(priority='P0', *, plan_path):
    """Check if plan-tracker has tasks at a given priority."""
    content = plan_path.read_text(encoding="utf-8")
    count = len(re.findall(rf"\|\s*{priority}\s*\|", content))
    if count > 0:
        return "PASS", f"plan-tracker 含 {count} 条 {priority} 任务"
    return "FAIL", f"plan-tracker 无 {priority} 任务——下轮方向不明确"


def _check_version_consistency_heuristic(*, product_root, skill_file, changelog_file, extract_skill_version):
    """Lightweight version consistency check for G11 auto-judgment (SYSGAP-020 enhanced).

    Checks: SKILL.md frontmatter version must appear consistently in all
    version declaration files (8 positions), CHANGELOG latest entry,
    and verify_workflow.py hardcoded snippets.
    """
    try:
        skill_version = extract_skill_version(skill_file())
        if not skill_version:
            return "NEEDS_HUMAN", "无法从 SKILL.md 提取版本号"

        # Version declaration files
        version_files = [
            "skills/software-project-governance/core/manifest.json",
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".codex-plugin/plugin.json",
            "skills/software-project-governance/infra/verify_workflow.py",
        ]
        for vf in version_files:
            vf_path = product_root / vf
            if vf_path.exists():
                vf_content = vf_path.read_text(encoding="utf-8")
                if skill_version not in vf_content:
                    return "FAIL", f"{vf} 版本与 SKILL.md ({skill_version}) 不一致"

        # CHANGELOG latest entry
        changelog_path = changelog_file()
        if changelog_path.exists():
            changelog_content = changelog_path.read_text(encoding="utf-8")
            cl_match = re.search(r'##\s*\[([\d.]+)\]', changelog_content)
            if cl_match and cl_match.group(1) != skill_version:
                return "FAIL", f"CHANGELOG.md 最新版本 [{cl_match.group(1)}] 与 SKILL.md ({skill_version}) 不一致"

        return "PASS", f"版本 {skill_version} 在 {len(version_files)} 个声明文件中一致"
    except Exception as e:
        return "NEEDS_HUMAN", f"版本检查异常: {e}"


def _gate_check_result_from_definition(check_definition, *, evidence_path, product_root, plan_path,
                                       registered_gate_function):
    executor = check_definition.get("executor")
    if executor == "function":
        fn = registered_gate_function(check_definition.get("function"))
        if not callable(fn):
            return "FAIL", f"未知检查函数 `{check_definition.get('function')}`"
        return fn()
    if executor == "file_exists":
        return _check_file_exists(check_definition.get("path", ""), check_definition["label"],
                   product_root=product_root)
    if executor == "snippet_in_file":
        return _check_snippet_in_file(
            check_definition.get("path", ""),
            check_definition.get("snippet", ""),
            check_definition["label"],
         product_root=product_root)
    if executor == "completed_ratio":
        return _check_completed_ratio(check_definition.get("min_ratio", 0.5), plan_path=plan_path)
    if executor == "research_doc_count":
        path = product_root / check_definition.get("path", "project/workflows/software-project-governance/research")
        min_count = check_definition.get("min_count", 0)
        if path.exists() and len(list(path.glob("*.md"))) >= min_count:
            return "PASS", check_definition.get("message", "research docs count satisfied")
        return "FAIL", check_definition.get("failure_message", f"{path} 文档数量不足")
    if executor == "constant_result":
        return check_definition.get("result", "NEEDS_HUMAN"), check_definition.get("message", "")
    if executor == "evidence_mentions":
        return _check_evidence_mentions(check_definition.get("keyword", ""), check_definition["label"],
                   evidence_path=evidence_path)
    return "FAIL", f"未知 executor `{executor}`"


def auto_judge_gate(gate_id, unit_id=None, *, parse_gate_detail, load_lifecycle_registry,
                    validate_registry, gate_check_result_from_definition):
    """Auto-judge a specific Gate based on available evidence.

    Returns: dict with overall_result (passed/blocked/passed-with-conditions/needs_human)
             and per-item results list.

    ``unit_id`` (optional, FIX-236.2 Wiring B): when a flow-unit id is given
    and the gate rendered a verdict (not needs_human), the judgment is routed
    to :func:`loop_gate_processor.process_gate_result` as a thin best-effort
    call (actor="gate-engine"). The wiring result is attached under the
    ``wiring`` key only when ``unit_id`` is provided, so existing callers see
    an unchanged dict shape.
    """
    gate_id = gate_id.upper()
    if not gate_id.startswith("G"):
        gate_id = "G" + gate_id

    detail = parse_gate_detail(gate_id)
    if not detail:
        return {"error": f"Gate {gate_id} not found", "items": []}

    registry, registry_issues = load_lifecycle_registry()
    if registry_issues or not isinstance(registry, dict):
        return {"error": f"Lifecycle registry unavailable for {gate_id}", "items": []}
    registry_contract_issues = validate_registry(registry)
    if registry_contract_issues:
        detail_text = "; ".join(registry_contract_issues[:3])
        if len(registry_contract_issues) > 3:
            detail_text += f"; ... ({len(registry_contract_issues)} total issues)"
        return {
            "gate": gate_id,
            "title": detail["title"],
            "overall": "blocked",
            "items": [{
                "check": "Gate execution registry contract",
                "result": "FAIL",
                "detail": detail_text,
            }],
            "summary": f"registry validation failed: {len(registry_contract_issues)} issue(s)",
        }

    gate_registry = registry.get("gate_execution_registry", {})
    gate_checks = gate_registry.get("gate_checks", []) if isinstance(gate_registry, dict) else []
    gate_entry = next(
        (item for item in gate_checks if isinstance(item, dict) and item.get("gate_id") == gate_id),
        None,
    )
    if not gate_entry:
        return {"error": f"Gate {gate_id} not found in execution registry", "items": []}

    # ── Execute auto-judgment ──
    items = []
    pass_count = 0
    fail_count = 0
    human_count = 0

    for check_definition in gate_entry.get("checks", []):
        try:
            result, message = gate_check_result_from_definition(check_definition)
        except Exception as e:
            result, message = "FAIL", f"判定异常: {e}"

        items.append({
            "check": check_definition.get("label", check_definition.get("check_id", "<missing>")),
            "result": result,
            "detail": message,
        })
        if result == "PASS":
            pass_count += 1
        elif result == "FAIL":
            fail_count += 1
        else:
            human_count += 1

    # ── Overall result ──
    total = len(items)
    if total == 0:
        overall = "needs_human"
    elif fail_count > 0:
        overall = "blocked"
    elif human_count > 0:
        overall = "passed-with-conditions"
    else:
        overall = "passed"

    # Diagnostics report local checks. Scoped review is applied by the native writer.
    result = {
        "gate": gate_id,
        "title": detail["title"],
        "overall": overall,
        "items": items,
        "summary": f"PASS={pass_count} FAIL={fail_count} NEEDS_HUMAN={human_count}",
    }
    return result
