"""Repository architecture, duplicate code, technical debt and governance size diagnostics."""

from checks.architecture_health import _archguard_exclusion_match, _archguard_severity
from pathlib import Path
from project_paths import default_host_root
from project_paths import package_root as _package_root, display_path as _display
import fnmatch
import json
import os
import re
import sys


ARCHGUARD_SCHEMA_REL = "skills/software-project-governance/core/architecture-health.json"


ARCHGUARD_LEDGER_REL = "skills/software-project-governance/core/technical-debt-ledger.md"


ARCHGUARD_HOOKS_REL = "skills/software-project-governance/infra/hooks"


ARCHGUARD_DEFAULT_ROOT_RESIDUE = ("_fix_*", "_tmp_*", "debug_*", "scratch_*")


def _archguard_load_schema(root=None, *, package_root=None, archguard_schema_rel=ARCHGUARD_SCHEMA_REL, display_path=_display):
    """Load architecture-health.json; return (schema_dict, error_str_or_None)."""
    root = Path(root) if root is not None else (package_root or _package_root())
    schema_path = root / archguard_schema_rel
    if not schema_path.is_file():
        return None, f"missing schema: {display_path(schema_path, root)}"
    try:
        return json.loads(schema_path.read_text(encoding="utf-8")), None
    except (ValueError, OSError) as exc:
        return None, f"invalid schema {schema_path}: {exc}"


def check_architecture_health(root=None, schema=None, *, package_root=None, archguard_load_schema=_archguard_load_schema):
    """Check the plugin (or a supplied fixture root) with its original policy."""
    from checks.architecture_health import scan_architecture

    root = Path(root) if root is not None else (package_root or _package_root())
    if schema is None:
        schema, err = archguard_load_schema(root)
        if schema is None:
            return {"error": err, "findings": [], "summary": {"errors": 0, "warnings": 0}}
    return scan_architecture(root, schema)


def _archguard_normalized_lines(text, normalize_le=True, ignore_ws=True):
    """Normalize text to a list of content lines (the CRLF/whitespace-safe comparator)."""
    if normalize_le:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    out = []
    for ln in text.split("\n"):
        if ignore_ws:
            compact = re.sub(r"\s+", "", ln)
            if not compact:
                continue
            out.append(compact)
        else:
            if not ln.strip():
                continue
            out.append(ln)
    return out


def _archguard_source_projection_pairs(root):
    """Return [(source_rel, source_abs, projection_abs), ...] for source/projection dup check.

    Derives pairs from the e2e-test-project projection tree: for each infra/*.py under
    the source skills tree, look for the mirrored file under the projection copy.
    """
    root = Path(root)
    src_base = root / "skills/software-project-governance/infra"
    proj_base = root / "project/e2e-test-project/skills/software-project-governance/infra"
    pairs = []
    if not src_base.is_dir() or not proj_base.is_dir():
        return pairs
    for py in sorted(src_base.glob("*.py")):
        candidate = proj_base / py.name
        if candidate.is_file():
            pairs.append((py.relative_to(root), py, candidate))
    return pairs


def check_duplicate_code(root=None, schema=None, *, package_root=None, archguard_exclusion_match=_archguard_exclusion_match,
                         archguard_load_schema=_archguard_load_schema, archguard_normalized_lines=_archguard_normalized_lines,
                         archguard_source_projection_pairs=_archguard_source_projection_pairs):
    """REQ-101 ArchGuard check 2: source/projection semantic duplicate.

    MUST normalize line endings + ignore whitespace, otherwise CRLF(source) vs
    LF(projection) yields a false ~100% diff.
    """
    root = Path(root) if root is not None else (package_root or _package_root())
    if schema is None:
        schema, err = archguard_load_schema(root)
        if schema is None:
            return {"error": err, "findings": [], "pairs_checked": 0,
                    "summary": {"errors": 0, "warnings": 0}}
    dc = schema.get("duplicate_code", {})
    warn_pct = dc.get("warn_pct", 60)
    error_pct = dc.get("error_pct", 80)
    normalize_le = bool(dc.get("normalize_line_endings", True))
    ignore_ws = bool(dc.get("ignore_whitespace", True))
    # FIX-350: schema-driven pair exemptions ([{path, reason}] on the SOURCE
    # rel path, same caliber as module_size.exclusions). An exempt pair still
    # counts toward pairs_checked and is disclosed — never silently dropped.
    dc_exclusions = dc.get("exclusions", [])

    findings = []
    exemptions = []
    pairs = archguard_source_projection_pairs(root)
    for rel, src_abs, proj_abs in pairs:
        match = archguard_exclusion_match(rel, dc_exclusions)
        if match is not None:
            reason = match.get("reason", "") if isinstance(match, dict) else ""
            # posix form for the disclosure — same caliber as the schema glob.
            exemptions.append({"path": str(rel).replace("\\", "/"),
                               "reason": reason})
            continue
        try:
            src_text = src_abs.read_text(encoding="utf-8", errors="replace")
            proj_text = proj_abs.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        src_lines = set(archguard_normalized_lines(src_text, normalize_le, ignore_ws))
        proj_lines = set(archguard_normalized_lines(proj_text, normalize_le, ignore_ws))
        denom = max(len(src_lines), len(proj_lines)) or 1
        diff_count = len(src_lines.symmetric_difference(proj_lines))
        duplicate_pct = round((1 - diff_count / denom) * 100, 1)
        sev = None
        if duplicate_pct >= error_pct:
            sev = "ERROR"
        elif duplicate_pct >= warn_pct:
            sev = "WARN"
        if sev:
            findings.append({
                "check": "duplicate_code", "severity": sev, "path": str(rel),
                "source_lines": len(src_lines), "projection_lines": len(proj_lines),
                "duplicate_pct": duplicate_pct,
            })
    errors = sum(1 for f in findings if f["severity"] == "ERROR")
    warnings = sum(1 for f in findings if f["severity"] == "WARN")
    return {
        "findings": findings, "pairs_checked": len(pairs),
        "exemptions": exemptions,
        "summary": {"errors": errors, "warnings": warnings},
    }


def check_technical_debt(
        root, schema, *, package_root, archguard_default_root_residue, archguard_hooks_rel,
        archguard_ledger_rel, archguard_load_schema, external_validation_canonical_hook_text,
        external_validation_read_text, parse_markdown_table_rows,
):
    """REQ-101 ArchGuard check 3: root residue / release docs / hooks drift / ledger cross-validate.

    G9: hooks-drift MUST reuse ``_external_validation_read_text`` and
    ``_external_validation_canonical_hook_text`` — do not reimplement.
    """
    root = Path(root) if root is not None else package_root
    if schema is None:
        schema, err = archguard_load_schema(root)
        if schema is None:
            return {"error": err, "findings": [],
                    "summary": {"errors": 0, "warnings": 0,
                                "open_items": 0, "deferred_items": 0}}
    td = schema.get("technical_debt", {})
    findings = []

    # 1. root-directory residue scripts
    patterns = td.get("root_residue_patterns") or list(archguard_default_root_residue)
    for entry in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        for pat in patterns:
            if fnmatch.fnmatch(entry, pat):
                findings.append({
                    "check": "root_residue", "severity": "WARN",
                    "path": entry, "pattern": pat,
                })
                break

    # 2. historical release docs version count
    threshold = td.get("release_docs_archive_threshold_versions", 30)
    release_dir = root / "docs/release"
    versions = set()
    if release_dir.is_dir():
        for child in release_dir.iterdir():
            # collect version-like tokens from filenames (e.g. 0.57.0)
            m = re.search(r"(\d+\.\d+\.\d+)", child.name)
            if m:
                versions.add(m.group(1))
    if len(versions) >= threshold:
        findings.append({
            "check": "release_docs_versions", "severity": "WARN",
            "path": str(release_dir.relative_to(root)) if release_dir.is_dir() else "docs/release",
            "versions": len(versions), "threshold": threshold,
        })

    # 3. hooks content drift (G9: reuse existing helpers)
    if td.get("hooks_drift_detection", True):
        hooks_src_dir = root / archguard_hooks_rel
        git_hooks_dir = root / ".git/hooks"
        if hooks_src_dir.is_dir():
            for hook_name in sorted(p.name for p in hooks_src_dir.iterdir() if p.is_file()):
                installed = git_hooks_dir / hook_name
                if not installed.is_file():
                    findings.append({
                        "check": "hooks_drift", "severity": "WARN",
                        "hook": hook_name, "reason": "not installed in .git/hooks",
                    })
                    continue
                installed_text, read_err = external_validation_read_text(installed)
                if installed_text is None:
                    findings.append({
                        "check": "hooks_drift", "severity": "WARN",
                        "hook": hook_name, "reason": f"cannot read installed: {read_err}",
                    })
                    continue
                installed_text = installed_text.replace("\r\n", "\n")
                source_text = external_validation_canonical_hook_text(hook_name, root=root)
                if source_text is None:
                    findings.append({
                        "check": "hooks_drift", "severity": "WARN",
                        "hook": hook_name, "reason": "canonical source missing",
                    })
                elif source_text != installed_text:
                    findings.append({
                        "check": "hooks_drift", "severity": "WARN",
                        "hook": hook_name, "reason": "source != installed content",
                    })

    # 4. technical-debt ledger cross-validation
    open_items = deferred_items = 0
    if td.get("ledger_cross_validate", True):
        ledger_path = root / archguard_ledger_rel
        if ledger_path.is_file():
            try:
                ledger_text = ledger_path.read_text(encoding="utf-8")
                # Restrict to the 登记项 section so other tables are not parsed.
                rows = parse_markdown_table_rows(ledger_text, section_title="登记项")
            except OSError:
                rows = []
            # _parse_markdown_table_rows returns list-of-cell-lists. The first surviving
            # row is the header (e.g. 债务 ID | ... | 承载版本 | 状态 | ...).
            header = rows[0] if rows else []
            norm_header = [h.strip().replace(" ", "") for h in header]
            idx_status = norm_header.index("状态") if "状态" in norm_header else None
            idx_carry = norm_header.index("承载版本") if "承载版本" in norm_header else None
            idx_id = norm_header.index("债务ID") if "债务ID" in norm_header else 0
            for cells in rows[1:]:
                def _cell(i):
                    return cells[i].strip() if (i is not None and i < len(cells)) else ""
                status = _cell(idx_status)
                carrying = _cell(idx_carry)
                tid = _cell(idx_id) or "?"
                if status in ("OPEN", "IN_PROGRESS"):
                    open_items += 1
                    if not carrying or carrying in ("待评估", "TBD", "N/A"):
                        findings.append({
                            "check": "ledger_no_carrying_version", "severity": "WARN",
                            "ledger_id": tid, "status": status,
                            "reason": "OPEN/IN_PROGRESS without 承载版本",
                        })
                elif status == "DEFERRED":
                    deferred_items += 1

    errors = sum(1 for f in findings if f["severity"] == "ERROR")
    warnings = sum(1 for f in findings if f["severity"] == "WARN")
    return {
        "findings": findings,
        "summary": {"errors": errors, "warnings": warnings,
                    "open_items": open_items, "deferred_items": deferred_items},
    }


def check_complexity(root=None, schema=None, *, package_root=None, archguard_load_schema=_archguard_load_schema,
                     archguard_severity=_archguard_severity, check_architecture_health=check_architecture_health):
    """REQ-101 ArchGuard check 4: complexity. 0.58.0 uses a line-based proxy.

    AST cyclomatic complexity is deferred to 0.59.0+ (complexity.enabled=false).
    The line-based proxy reuses function-length data from architecture-health.
    """
    root = Path(root) if root is not None else (package_root or _package_root())
    if schema is None:
        schema, err = archguard_load_schema(root)
        if schema is None:
            return {"error": err, "findings": [],
                    "summary": {"errors": 0, "warnings": 0},
                    "enabled": False}
    cx = schema.get("complexity", {})
    enabled = bool(cx.get("enabled", False))
    if not enabled:
        return {
            "enabled": False,
            "findings": [],
            "summary": {"errors": 0, "warnings": 0},
            "note": cx.get("note") or "AST complexity deferred; 0.58.0 uses line-based proxy — see check-architecture-health",
        }
    # When enabled (future 0.59.0+), repurpose the architecture-health function-size
    # data as a line-based proxy for cyclomatic complexity.
    arch = check_architecture_health(root=root, schema=schema)
    warn_n = cx.get("warn_cyclomatic", 15)
    error_n = cx.get("error_cyclomatic", 30)
    findings = []
    for f in arch.get("findings", []):
        if f.get("check") != "function_size":
            continue
        n = f.get("lines", 0)
        sev = archguard_severity(n, warn_n, error_n)
        if sev:
            findings.append({
                "check": "complexity_proxy", "severity": sev,
                "path": f.get("path"), "name": f.get("name"),
                "lines": n, "lineno": f.get("lineno"),
            })
    errors = sum(1 for f in findings if f["severity"] == "ERROR")
    warnings = sum(1 for f in findings if f["severity"] == "WARN")
    return {
        "enabled": True, "findings": findings,
        "summary": {"errors": errors, "warnings": warnings},
    }


def check_governance_data_size(root=None, schema=None, *, host_project_root=None, package_root=None,
                               archguard_load_schema=_archguard_load_schema, archguard_severity=_archguard_severity,
                               archive_reader=None):
    """FIX-160: ArchGuard check 5 — governance data volume threshold.

    Guards RISK-039 (governance data bloat) directly. Scans the governance
    hot files (plan-tracker / evidence-log / decision-log / risk-log) declared
    in architecture-health.json `governance_data_size.files` and emits a
    WARN/ERROR finding when a file exceeds warn_bytes / error_bytes. The
    error threshold (250KB) is set just below the 256KB agent single-read
    limit so the warning fires before a governance file becomes unreadable.

    FIX-270 (mixed-root): the *schema* (thresholds / file list) is a plugin
    asset and is loaded from the plugin package; the *facts* to measure are
    the governed project's hot files, so when ``root`` is not explicit the
    file paths resolve against HOST_PROJECT_ROOT (never the plugin package
    root). An explicit ``root`` keeps the legacy fixture semantics (schema +
    facts from the same root).

    Advisory by default (inherits gate_integration.fatal_on_error=false).
    """
    if root is not None:
        schema_root = fact_root = Path(root)
    else:
        schema_root = package_root if package_root is not None else _package_root()
        fact_root = host_project_root if host_project_root is not None else default_host_root()
    if schema is None:
        schema, err = archguard_load_schema(schema_root)
        if schema is None:
            return {"error": err, "findings": [],
                    "summary": {"errors": 0, "warnings": 0},
                    "enabled": False}
    gds = schema.get("governance_data_size", {})
    enabled = bool(gds.get("enabled", True))
    if not enabled:
        return {
            "enabled": False, "findings": [],
            "summary": {"errors": 0, "warnings": 0},
            "note": gds.get("note") or "governance_data_size disabled",
        }
    # DEC-295(1) track-1 recalibration (user ruling, 2026-09-29): the
    # evidence-log face carries a PER-FILE override — warn 400000 /
    # error 650000. Calibration basis: the typed hot-table steady state =
    # 199 permanently-hot registered-ID rows (~280-300KB) + the working
    # set (0.92 closeout + 0.93 in flight); measured 515KB + migration
    # wobble headroom. All OTHER faces keep the global 200000/250000
    # lines (the 256KB single-read guard rationale stays intact for
    # them; decision-log's EXC-003 exception remains meaningful).
    warn_bytes = gds.get("warn_bytes", 200000)
    error_bytes = gds.get("error_bytes", 250000)
    file_overrides = gds.get("file_overrides", {})
    files = gds.get("files", [])
    findings = []
    for rel in files:
        path = fact_root / rel
        if not path.exists():
            continue
        size = path.stat().st_size
        override = file_overrides.get(rel, {})
        face_warn = override.get("warn_bytes", warn_bytes)
        face_error = override.get("error_bytes", error_bytes)
        sev = archguard_severity(size, face_warn, face_error)
        if sev:
            findings.append({
                "check": "governance_data_size", "severity": sev,
                "path": rel, "bytes": size,
                "reason": f"{size} bytes ({size/1024:.1f} KB) exceeds {sev.lower()}_bytes={face_warn if sev=='WARN' else face_error}",
            })
    errors = sum(1 for f in findings if f["severity"] == "ERROR")
    warnings = sum(1 for f in findings if f["severity"] == "WARN")
    result = {
        "enabled": True, "findings": findings,
        "summary": {"errors": errors, "warnings": warnings},
    }
    # FEAT-076 (DEC-278 Q5 three-track semantics, 0.93 switch): track 1 =
    # the hot working-set capacity gate above (unchanged schema-driven
    # severity); track 2 = full-library integrity (check-archive-integrity,
    # separate check); track 3 = total-volume growth monitoring — reported
    # here as informational layer facts (hot/cold/total), no new finding
    # severity. Growth-rate alerting rides the weekly metric duty (EXC
    # family terms) instead of a second threshold.
    try:
        if archive_reader is None:
            from governance_archive_data import GovernanceDataSource
            ds = GovernanceDataSource(fact_root / ".governance")
        elif root is not None:
            _gov = Path(root) / ".governance"
            ds = archive_reader(
                sample_path=_gov / "plan-tracker.md",
                evidence_path=_gov / "evidence-log.md",
            )
        else:
            ds = archive_reader()
        _stats = ds.layer_stats()
        result["layers"] = _stats["layers"]
        result["family_stats"] = _stats["families"]
    except Exception:  # noqa: BLE001 — informational track, never fatal
        result["layers"] = None
    return result


def _archguard_print_findings(title, result, hint_key, *, exception_note, exception_registry_error_note):
    """Render a 3-level ArchGuard result; return (errors, warnings).

    FEAT-075: findings matched by an EFFECTIVE governance exception carry an
    ``exception accepted (ref, expires)`` suffix — annotation only; the
    severity, bytes, and summary counts above stay exactly as the check
    produced them (no registry → byte-identical pre-FEAT-075 output).
    """
    s = result.get("summary", {}) or {}
    errors = int(s.get("errors", 0))
    warnings = int(s.get("warnings", 0))
    # FEAT-075 R0 F-2: file-level registry errors disclosed once (first
    # finding line); "" when clean — output unchanged.
    reg_err = exception_registry_error_note()
    err_shown = not reg_err
    for f in result.get("findings", [])[:25]:
        sev = f.get("severity", "?")
        extra = ""
        for k in ("lines", "count", "duplicate_pct", "versions", "bytes"):
            if k in f:
                extra = f" {k}={f[k]}"
                break
        loc = f.get("path") or f.get("hook") or f.get("ledger_id") or ""
        detail = f.get("name") or f.get("reason") or f.get("pattern") or ""
        note = exception_note(f.get(hint_key), loc, f.get("severity"),
                               bytes_value=f.get("bytes"))
        if not err_shown:
            note += ("  " if note else "") + reg_err
            err_shown = True
        print(f"  [{sev}] {f.get(hint_key, '?')}: {loc} {detail}{extra}{note}".rstrip())
    more = len(result.get("findings", [])) - 25
    if more > 0:
        print(f"    ... and {more} more")
    return errors, warnings


def cmd_check_architecture_health(
        args, *, host_project_root, plugin_root, archguard_schema_rel, archguard_print_findings,
        check_architecture_health,
):
    from checks.architecture_health import run_architecture_health

    run_architecture_health(args, host_project_root, plugin_root, plugin_root / archguard_schema_rel,
                            check_architecture_health, archguard_print_findings)


def cmd_check_duplicate_code(args, *, archguard_print_findings, check_duplicate_code):
    """Run REQ-101 ArchGuard source/projection duplicate-code guard (advisory in 0.58.0)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_duplicate_code()
    print("\n=== Duplicate Code Check (ArchGuard) ===")
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
        print()
        return
    errors, warnings = archguard_print_findings("Duplicate Code", result)
    print(f"\n  Pairs checked: {result.get('pairs_checked', 0)}")
    for x in result.get("exemptions", []):
        reason = x.get("reason", "")
        print(f"  [EXEMPT] {x.get('path', '')}"
              + (f" — {reason}" if reason else ""))
    print(f"  Result: ISSUES FOUND — {errors} ERROR, {warnings} WARN")
    if getattr(args, "fail_on_issues", False) and errors > 0:
        sys.exit(1)
    print()


def cmd_check_technical_debt(args, *, archguard_print_findings, check_technical_debt):
    """Run REQ-101 ArchGuard technical-debt guard (residue/docs/hooks-drift/ledger; advisory)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_technical_debt()
    print("\n=== Technical Debt Check (ArchGuard) ===")
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
        print()
        return
    errors, warnings = archguard_print_findings("Technical Debt", result)
    s = result.get("summary", {}) or {}
    print(f"\n  Ledger: {s.get('open_items', 0)} OPEN/IN_PROGRESS, {s.get('deferred_items', 0)} DEFERRED")
    print(f"  Result: ISSUES FOUND — {errors} ERROR, {warnings} WARN")
    if getattr(args, "fail_on_issues", False) and errors > 0:
        sys.exit(1)
    print()


def cmd_check_complexity(args, *, archguard_print_findings, check_complexity):
    """Run REQ-101 ArchGuard complexity guard (line-based proxy in 0.58.0; advisory)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_complexity()
    print("\n=== Complexity Check (ArchGuard) ===")
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
        print()
        return
    if not result.get("enabled", False):
        print(f"  [INFO] complexity disabled — {result.get('note', 'line-based proxy; see check-architecture-health')}")
        print()
        return
    errors, warnings = archguard_print_findings("Complexity", result)
    print(f"\n  Result: ISSUES FOUND — {errors} ERROR, {warnings} WARN")
    if getattr(args, "fail_on_issues", False) and errors > 0:
        sys.exit(1)
    print()


def cmd_check_governance_data_size(args, *, archguard_print_findings, check_governance_data_size):
    """FIX-160: Run governance data volume threshold guard (advisory)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_governance_data_size()
    print("\n=== Governance Data Size Check (ArchGuard/FIX-160) ===")
    if result.get("error"):
        print(f"  [ERROR] {result['error']}")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
        print()
        return
    if not result.get("enabled", False):
        print(f"  [INFO] governance_data_size disabled — {result.get('note', '')}")
        print()
        return
    errors, warnings = archguard_print_findings("GovernanceDataSize", result)
    if errors or warnings:
        print(f"\n  Result: ISSUES FOUND — {errors} ERROR, {warnings} WARN")
        print("  (advisory — fatal_on_error=false; see architecture-health.json governance_data_size)")
    else:
        print("\n  Result: PASSED — all governance files within size budget")
    if getattr(args, "fail_on_issues", False) and errors > 0:
        sys.exit(1)
    print()
