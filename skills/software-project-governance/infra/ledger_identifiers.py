"""Verify ordered ledger identifiers and the structure of governance files."""
import re


def check_sequential_ids(*, governance_dir, data_source):
    """Verify ID continuity in governance records:
    1. DEC-XXX: detect numbering gaps starting from 001
    2. EVD-XXX: detect numbering gaps
    3. RISK-XXX: detect numbering gaps
    4. Cross-reference integrity: task IDs referenced in evidence/decision/risk
       must exist in plan-tracker
    5. Completed tasks in plan-tracker must have evidence entries
    """

    def _extract_ids(file_path, prefix):
        """Extract sequential IDs with given prefix from a file, return sorted list of ints."""
        if not file_path.is_file():
            return []
        content = file_path.read_text(encoding="utf-8")
        ids = set()
        for m in re.finditer(rf"\b{re.escape(prefix)}(\d+)\b", content):
            ids.add(int(m.group(1)))
        return sorted(ids)

    def _find_gaps(sorted_ids, prefix):
        """Find gaps in a sorted list of integer IDs. Returns list of missing numbers."""
        if not sorted_ids:
            return []
        gaps = []
        expected = 1  # IDs start at 001
        for num in sorted_ids:
            while expected < num:
                gaps.append(expected)
                expected += 1
            expected = num + 1
        return gaps

    dec_path = governance_dir / "decision-log.md"
    evd_path = governance_dir / "evidence-log.md"
    risk_path = governance_dir / "risk-log.md"

    # Use GovernanceDataSource for archive-aware ID collection.
    # Falls back to hot-file-only when archive/index.md does not exist.
    ds = data_source()

    # DEC/RISK: via GovernanceDataSource (hot + archive)
    dec_ids = ds.get_all_decision_ids()
    risk_ids = ds.get_all_risk_ids()

    # EVD: collect from hot evidence-log + archive evidence files
    evd_id_set = set()
    if evd_path.is_file():
        evd_content = evd_path.read_text(encoding="utf-8")
        for m in re.finditer(r"\bEVD-(\d+)\b", evd_content):
            evd_id_set.add(int(m.group(1)))
    for entry in ds._scan_archive_files(ds.archive_evidence_dir,
                                         ds._extract_evidence_entries):
        evd_match = re.match(r"EVD-(\d+)", entry.get("evd_id", ""))
        if evd_match:
            evd_id_set.add(int(evd_match.group(1)))
    evd_ids = sorted(evd_id_set)

    dec_gaps = _find_gaps(dec_ids, "DEC-")
    evd_gaps = _find_gaps(evd_ids, "EVD-")
    risk_gaps = _find_gaps(risk_ids, "RISK-")

    # Cross-reference: all task IDs in evidence/decision/risk must exist
    # in plan-tracker.  Use GovernanceDataSource to include archived tasks.
    all_task_ids = ds.get_all_task_ids()

    # Collect task IDs referenced in evidence-log (hot + archive)
    evd_task_ids = ds.get_all_evidence_task_ids()

    # Collect task IDs referenced in decision-log
    dec_task_ids = set()
    if dec_path.is_file():
        dec_content = dec_path.read_text(encoding="utf-8")
        for m in re.finditer(r"\b([A-Z]+-\d+)\b", dec_content):
            task_id = m.group(1)
            if re.match(r"^[A-Z]+-\d+$", task_id) and not task_id.startswith("DEC-"):
                dec_task_ids.add(task_id)

    # Collect task IDs referenced in risk-log
    risk_task_ids = set()
    if risk_path.is_file():
        risk_content = risk_path.read_text(encoding="utf-8")
        for m in re.finditer(r"\b([A-Z]+-\d+)\b", risk_content):
            task_id = m.group(1)
            if re.match(r"^[A-Z]+-\d+$", task_id) and not task_id.startswith("RISK-"):
                risk_task_ids.add(task_id)

    orphan_evd = sorted(evd_task_ids - all_task_ids)
    orphan_dec = sorted(dec_task_ids - all_task_ids - evd_task_ids)  # avoid dup reporting
    orphan_risk = sorted(risk_task_ids - all_task_ids)

    # Completed tasks without evidence (archive-aware). Only hot missing
    # evidence is actionable; archived gaps are historical residue.
    completed_entries = ds.get_all_completed_task_entries()
    completed = {entry["id"] for entry in completed_entries}
    hot_completed = {
        entry["id"] for entry in completed_entries
        if entry.get("source") == "hot"
    }
    missing_evd_all = completed - evd_task_ids
    missing_evd = sorted(missing_evd_all & hot_completed)
    historical_missing_evd = sorted(missing_evd_all - set(missing_evd))

    return {
        "dec_ids": dec_ids,
        "evd_ids": evd_ids,
        "risk_ids": risk_ids,
        "dec_gaps": dec_gaps,
        "evd_gaps": evd_gaps,
        "risk_gaps": risk_gaps,
        "orphan_evidence_refs": orphan_evd,
        "orphan_decision_refs": orphan_dec,
        "orphan_risk_refs": orphan_risk,
        "completed_missing_evidence": missing_evd,
        "historical_completed_missing_evidence": historical_missing_evd,
    }


def _format_id_sequence_status(prefix, ids):
    """Return a compact, empty-safe ID range summary."""
    if not ids:
        return f"{prefix}-IDs: no entries found."
    return f"{prefix}-IDs: {ids[0]:03d}-{ids[-1]:03d} ({len(ids)} entries, no gaps)"


def _print_sequential_id_check(si_result):
    """Print Check 13 details and return the blocking issue count."""
    issue_count = 0
    if si_result["dec_gaps"]:
        issue_count += 1
        print(f"│  [WARN] DEC-ID gaps: missing {si_result['dec_gaps']}")
    else:
        print(f"│  [PASS] {_format_id_sequence_status('DEC', si_result['dec_ids'])}")

    if si_result["evd_gaps"]:
        print(f"│  [INFO] EVD-ID gaps: missing {si_result['evd_gaps']} "
              f"(historical archive residue)")
    else:
        print(f"│  [PASS] {_format_id_sequence_status('EVD', si_result['evd_ids'])}")

    if si_result["risk_gaps"]:
        issue_count += 1
        print(f"│  [WARN] RISK-ID gaps: missing {si_result['risk_gaps']}")
    else:
        print(f"│  [PASS] {_format_id_sequence_status('RISK', si_result['risk_ids'])}")

    # Orphan cross-references: info-only — these are historical cleanup residues
    # (old task IDs removed from plan-tracker during intentional cleanup, not errors)
    orphans = (si_result.get("orphan_evidence_refs", []) +
               si_result.get("orphan_decision_refs", []) +
               si_result.get("orphan_risk_refs", []))
    if orphans:
        print(f"│  [INFO] {len(orphans)} cross-reference(s) to non-existent task ID(s)"
              f" (historical cleanup residue): {orphans[:10]}")
        if len(orphans) > 10:
            print(f"│         ... and {len(orphans) - 10} more")
    else:
        print(f"│  [PASS] All cross-referenced task IDs exist in plan-tracker.")

    missing_evd = si_result.get("completed_missing_evidence", [])
    if missing_evd:
        issue_count += len(missing_evd)
        print(f"│  [WARN] {len(missing_evd)} completed task(s) without evidence: {missing_evd[:10]}")
    else:
        print(f"│  [PASS] All completed tasks have evidence entries.")

    historical_missing_evd = si_result.get("historical_completed_missing_evidence", [])
    if historical_missing_evd:
        print(f"│  [INFO] {len(historical_missing_evd)} archived completed task(s) "
              f"without evidence (historical residue): {historical_missing_evd[:10]}")
    if issue_count == 0:
        print(f"│  [PASS] All ID sequences are clean.")
    return issue_count


def _scan_unicode_line_separators(*, governance_dir):
    """FIX-349 ⑥: Unicode line/segment separators in governance hot files.

    EVD-890: a U+000B (VT) inside one evidence-log row silently became a line
    boundary for splitlines-style consumers (Python ``str.splitlines``,
    editors, markdown renderers) while the "\\n"-based governance checks saw
    one long line — the M5.4b false positive. EVD-1063 repaired that single
    occurrence without a systemic guard; this scan closes the class. It
    reports every occurrence of the FIX-349 ⑥ separator family (VT, FF,
    FS/GS/RS, NEL, LS, PS — all honored as line boundaries by splitlines-style
    consumers) in the hot files that line-based governance checks parse.

    Severity caliber (FIX-350 F-2): the WARN issues emitted here are
    non-blocking inside the ``check-governance`` aggregation
    (``structural_issue_is_blocking`` treats WARN as non-blocking), but the
    standalone ``check-structural-validity`` CLI exits 1 on ANY issue,
    WARN included — run it only when a fail-closed reading is intended.

    WARN severity (same caliber as ``evidence_col_mismatch``): the
    characters are a parsing hazard, not a broken schema, and the data fix
    belongs to the Coordinator's governance write-back, not to this check.
    """
    scan_files = (
        "plan-tracker.md", "evidence-log.md", "decision-log.md",
        "risk-log.md", "session-snapshot.md",
    )
    separators = (
        ("U+000B", "\x0b"),    # VT  — vertical tab (EVD-890 incident character)
        ("U+000C", "\x0c"),    # FF  — form feed (FIX-350 F-1: splitlines boundary)
        ("U+001C", "\x1c"),    # FS  — file separator
        ("U+001D", "\x1d"),    # GS  — group separator
        ("U+001E", "\x1e"),    # RS  — record separator
        ("U+0085", "\x85"),    # NEL — next line
        ("U+2028", "\u2028"),  # LS  — line separator
        ("U+2029", "\u2029"),  # PS  — paragraph separator
    )
    issues = []
    for name in scan_files:
        path = governance_dir / name
        if not path.is_file():
            continue  # 存在才扫 — optional hot files (e.g. session-snapshot)
        content = path.read_text(encoding="utf-8")
        for label, char in separators:
            pos = content.find(char)
            while pos != -1:
                issues.append({
                    "type": "unicode_line_separator",
                    "severity": "WARN",
                    "file": f".governance/{name}",
                    "line": content.count("\n", 0, pos) + 1,
                    "col": pos - content.rfind("\n", 0, pos),
                    "detail": f"{label} line/segment separator in hot file "
                              f"(breaks splitlines-style parsing; "
                              f"EVD-890 class)",
                })
                pos = content.find(char, pos + 1)
    return issues


def check_structural_validity(*, governance_dir, skill_file, manifest_file, extract_skill_version,
                              split_markdown_table_row):
    """Validate structural integrity of governance files:
    1. plan-tracker.md: table column count consistency (every row
       pipe-count matches header)
    2. evidence-log.md: every record has consistent column count
       (10 columns standard)
    3. decision-log.md: each ADR contains all required fields
    4. SKILL.md: frontmatter contains required fields (name/version/description)
    5. manifest.json: product / repo_only / exclude sections all present
    6. Unicode line/segment separators (FIX-349 ⑥) in the governance hot
       files — WARN-level disclosure via _scan_unicode_line_separators()
    """
    import json as _json
    issues = []

    # ── 1. plan-tracker.md table column consistency ──
    pt_path = governance_dir / "plan-tracker.md"
    if pt_path.is_file():
        pt_content = pt_path.read_text(encoding="utf-8")
        # Find all markdown tables: contiguous |...| lines after a header row
        lines = pt_content.split("\n")
        current_header_cols = None
        current_header_line = 0
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line.startswith("|"):
                current_header_cols = None
                continue
            if "---" in line or ":--" in line:
                continue  # separator row
            # Strip inline code (backtick-quoted) to avoid false | in column count
            # e.g., | text `✅ 已完成 |` next | → the | inside backticks is NOT a column separator
            clean_line = re.sub(r'`+[^`]*`+', '__CODE__', line)
            cols = len(clean_line.split("|")) - 2  # strip outer empty parts
            if not cols:
                continue

            # Heuristic: if this looks like a header (next line is separator),
            # treat it as header
            is_header = False
            if i < len(lines):
                next_line = lines[i].strip()
                if re.match(r"^\|[\s\-:]+\|", next_line):
                    is_header = True

            if is_header:
                current_header_cols = cols
                current_header_line = i
                continue

            if current_header_cols is not None and cols != current_header_cols:
                issues.append({
                    "type": "table_column_mismatch",
                    "file": ".governance/plan-tracker.md",
                    "line": i,
                    "detail": f"Row has {cols} columns, header (line {current_header_line}) has {current_header_cols}",
                })
    else:
        issues.append({
            "type": "file_missing",
            "file": ".governance/plan-tracker.md",
            "detail": "plan-tracker.md not found",
        })

    # ── 2. evidence-log.md column count consistency ──
    evd_path = governance_dir / "evidence-log.md"
    if evd_path.is_file():
        evd_content = evd_path.read_text(encoding="utf-8")
        evd_lines = evd_content.split("\n")
        standard_cols = None
        for i, line in enumerate(evd_lines, 1):
            line = line.strip()
            if not line.startswith("| EVD-"):
                continue
            parts = split_markdown_table_row(line)
            cols = len(parts)
            if standard_cols is None:
                standard_cols = cols
            elif cols != standard_cols:
                evd_id = parts[0] if parts else "???"
                issues.append({
                    "type": "evidence_col_mismatch",
                    "severity": "WARN",
                    "file": ".governance/evidence-log.md",
                    "line": i,
                    "detail": f"{evd_id}: {cols} columns (expected {standard_cols})",
                })
    else:
        issues.append({
            "type": "file_missing",
            "file": ".governance/evidence-log.md",
            "detail": "evidence-log.md not found",
        })

    # ── 3. decision-log.md ADR required fields ──
    dec_path = governance_dir / "decision-log.md"
    required_decision_fields = ["日期", "状态", "决策", "原因"]
    if dec_path.is_file():
        dec_content = dec_path.read_text(encoding="utf-8")
        # Parse ADR sections: each ADR starts with "## DEC-XXX"
        adr_sections = re.split(r"\n(?=## DEC-)", dec_content)
        for section in adr_sections:
            if not section.strip().startswith("## DEC-"):
                continue
            adr_id = section.split("\n")[0].replace("##", "").strip()
            missing = []
            for field in required_decision_fields:
                if field not in section:
                    missing.append(field)
            if missing:
                issues.append({
                    "type": "decision_missing_fields",
                    "file": ".governance/decision-log.md",
                    "detail": f"{adr_id}: missing required fields — {', '.join(missing)}",
                })
    else:
        issues.append({
            "type": "file_missing",
            "file": ".governance/decision-log.md",
            "detail": "decision-log.md not found",
        })

    # ── 4. SKILL.md frontmatter required fields ──
    skill_path = skill_file()
    if skill_path.is_file():
        content = skill_path.read_text(encoding="utf-8")
        # Extract frontmatter: content between first --- and second ---
        fm_match = re.match(r"^\s*---\s*\n(.*?)\n\s*---", content, re.DOTALL)
        if fm_match:
            fm_text = fm_match.group(1)
            required_frontmatter = ["name:", "description:"]
            missing = []
            for fm_field in required_frontmatter:
                if fm_field not in fm_text:
                    missing.append(fm_field.rstrip(":"))
            if not extract_skill_version(skill_path):
                missing.append("version")
            if missing:
                issues.append({
                    "type": "skill_frontmatter_missing",
                    "file": "skills/software-project-governance/SKILL.md",
                    "detail": f"Frontmatter missing required fields: {', '.join(missing)}",
                })
        else:
            issues.append({
                "type": "skill_frontmatter_missing",
                "file": "skills/software-project-governance/SKILL.md",
                "detail": "No YAML frontmatter found (missing --- delimiters)",
            })

    # ── 5. manifest.json structure ──
    manifest_path = manifest_file()
    if manifest_path.is_file():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = _json.load(f)
            for section in ["product", "repo_only", "exclude_from_cleanup"]:
                if section not in manifest:
                    issues.append({
                        "type": "manifest_section_missing",
                        "file": "skills/software-project-governance/core/manifest.json",
                        "detail": f"manifest.json is missing '{section}' section",
                    })
        except (_json.JSONDecodeError, IOError) as e:
            issues.append({
                "type": "manifest_parse_error",
                "file": "skills/software-project-governance/core/manifest.json",
                "detail": str(e),
            })
    else:
        issues.append({
            "type": "file_missing",
            "file": "skills/software-project-governance/core/manifest.json",
            "detail": "manifest.json not found",
        })

    # ── 6. Unicode line/segment separators in hot files (FIX-349 ⑥) ──
    issues.extend(_scan_unicode_line_separators(governance_dir=governance_dir))

    return issues
