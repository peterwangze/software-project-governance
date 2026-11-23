"""Dispatch full and quick governance checks and their summary presentations."""

from contextlib import redirect_stdout
import io
import re
import sys


def cmd_check_governance(args):
    """Run governance health checks: evidence completeness, risk staleness, gate consistency.

    REQ-145.7/FIX-278 G1: with ``--summary-only``, the full engine is run under
    a stdout capture and only the ``Governance: {N} issues`` summary (+ first
    FAIL/WARN, plus --level standard's top-5 bounded detail lines and the
    ``共 N issues，--level strict 查看全部`` guidance — lightweight=summary+
    first FAIL; strict=all FAIL/WARN) is printed. The default (no
    ``--summary-only``) path is byte-identical to the pre-existing output —
    the engine body lives in ``_run_full_engine_checks``.

    FEAT-084 (DEC-303 form B): ``--scope quick|full`` declares the execution
    scope — quick normalizes onto the FEAT-026 wiring (four-state line); the
    default / ``--scope full`` stay byte-identical (full-caliber N for release
    gates, census baselines and golden samples — the caliber split is caller
    declared, never silent).
    """
    # Ensure UTF-8 stdout to handle Chinese characters from .md files (Windows GBK workaround)
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    # FEAT-084: scope quick ⇒ the quick face (FEAT-026 wiring below owns
    # selection + four-state rendering + FIX-304 fail-closed fallback).
    if getattr(args, "scope", "full") == "quick":
        setattr(args, "quick", True)

    if getattr(args, "quick", False) or getattr(args, "shadow", False):
        # FEAT-026 Slice-2 wiring: the selector owns the four-state contract and
        # the S-A/S-B shadow channel; the engine only provides the run + capture.
        from quickscan_selector import run_quick_checks
        all_issues, output = run_quick_checks(args, _run_full_engine_checks)
        print(output, end="")
    elif getattr(args, "summary_only", False):
        buf = io.StringIO()
        with redirect_stdout(buf):
            all_issues = _run_full_engine_checks(args)
        summary = _aggregate_check_summary(buf.getvalue())
        _print_check_summary(summary, args)
    else:
        all_issues = _run_full_engine_checks(args)

    if getattr(args, "fail_on_issues", False) and all_issues > 0:
        sys.exit(1)


def _run_full_engine_checks(args):
    from full_check_runner import run_full_checks
    from workflow_report_selection import _full_check_results
    return run_full_checks(_full_check_results(args))


def _extract_summary_count(stdout_text):
    """Return (issues_count, parse_degraded) from the engine's summary line.

    Anchors on the stable ``Result: ISSUES FOUND — N issue(s)`` (or the
    ``Result: PASSED — 0 issues found``) line. A format drift (neither line
    matches) degrades to ``(0, True)`` so the caller emits a fail-safe
    ``(parse degraded)`` marker instead of a hard error.
    """
    m = re.search(r"Result:\s*ISSUES FOUND\s*[—\-–]\s*(\d+)\s*issue\(s\)", stdout_text)
    if m:
        return int(m.group(1)), False
    m2 = re.search(r"Result:\s*PASSED\s*[—\-–]\s*0\s*issues found", stdout_text)
    if m2:
        return 0, False
    return 0, True


def _aggregate_check_summary(stdout_text):
    """Parse captured full engine output into a summary dict (REQ-145.7).

    Anchors the issue count on the ``Result: ISSUES FOUND — N issue(s)`` line
    and the ``[FAIL]`` / ``[WARN]`` / ``[ADVISORY]`` severity lines, correlating
    each to its enclosing ``┌─ Check N: ... ┐`` section. Returns
    ``{issues_count, parse_degraded, first_fail, first_warn, fail_items,
    warn_items, advisory_items, advisory}``.
    """
    issues_count, parse_degraded = _extract_summary_count(stdout_text)
    fail_items, warn_items, advisory_items = [], [], []
    current_check = ""
    for line in stdout_text.splitlines():
        hm = re.search(r"┌─\s*Check\s+(.+?)\s*[─-]+┐", line)
        if hm:
            current_check = hm.group(1).strip()
            continue
        # FIX-278 G2/P2-4: [BLOCKING]/[ERROR] severity markers (M5 structural
        # gaps, runtime-readiness errors — counted into all_issues by the
        # engine) are FAIL-class tokens; leaving them out would render the
        # standard-summary detail section empty for M5-only inputs and push
        # the model back into a full-check chase (the G1 behavior gap).
        for token in ("[FAIL]", "[BLOCKING]", "[ERROR]", "[WARN]", "[ADVISORY]"):
            idx = line.find(token)
            if idx >= 0:
                detail = line[idx + len(token):].strip()
                label = f"{current_check}: {detail}" if current_check else detail
                if token in ("[FAIL]", "[BLOCKING]", "[ERROR]"):
                    fail_items.append(label)
                elif token == "[WARN]":
                    warn_items.append(label)
                else:
                    advisory_items.append(label)
                break
    return {
        "issues_count": issues_count,
        "parse_degraded": parse_degraded,
        "first_fail": fail_items[0] if fail_items else None,
        "first_warn": warn_items[0] if warn_items else None,
        "fail_items": fail_items,
        "warn_items": warn_items,
        "advisory_items": advisory_items,
        "advisory": advisory_items[0] if advisory_items else None,
    }


def _summary_detail_cap():
    """FIX-278 G1: max issue detail lines in the default summary output."""
    return 5


def _summary_detail_char_limit():
    """FIX-278 G1: per-line truncation budget for summary detail lines.

    130 chars × ≤5 lines ≲ 700 chars — the G1 output budget (audit-148 §2.1:
    the detail section must stay well under the ~1.7KB full-check output so a
    model never re-runs the whole engine to understand the summary).
    """
    return 130


def _truncate_summary_detail(label):
    """Bound one summary detail line (G1: header + ≤130 chars, ellipsis)."""
    limit = _summary_detail_char_limit()
    if len(label) <= limit:
        return label
    return label[: max(1, limit - 1)] + "…"


def _ordered_detail_items(summary):
    """Return [(severity, label), ...]: FAIL items first, then WARN — capped.

    FIX-278 G1: the default summary shows the first FAIL/WARN plus at most
    ``_summary_detail_cap()`` ordered details (audit-148 §2.1: the 103-char
    summary line alone triggered a 25KB model chase chain; giving the top
    items removes the need for the full check re-run).
    """
    items = []
    for item in summary.get("fail_items") or []:
        items.append(("FAIL", item))
    for item in summary.get("warn_items") or []:
        items.append(("WARN", item))
    return items[:_summary_detail_cap()]


def _print_check_summary(summary, args):
    """Render the ``--summary-only`` output (REQ-145.7 output contract).

    Summary line ``Governance: {N} issues`` (or ``Governance: [PASS]`` when
    N==0) followed by the first FAIL/WARN detail line; the detail granularity
    follows ``--level`` (lightweight → summary + first FAIL; standard →
    summary + first FAIL/WARN + top-5 ordered details + a TWO-STATE tail
    line — ``构成已全量展示（N 项）`` when all details are already displayed
    (≤ cap, FEAT-012 G6: no chase invitation) and ``共 N issues，--level
    strict 查看全部`` above the cap (FIX-278 G1); strict → summary + all
    FAIL/WARN). Advisory (``fatal_on_error=false``) issues are not counted
    and are only annotated when they are the first issue surfaced.
    """
    count = summary.get("issues_count") or 0
    if summary.get("parse_degraded"):
        print(f"Governance: {count} issues (parse degraded)")
        return
    if count == 0:
        print("Governance: [PASS]")
    else:
        print(f"Governance: {count} issues")
    level = getattr(args, "summary_level", None) or "standard"
    if count > 0:
        if level == "lightweight":
            if summary["first_fail"]:
                print(f"[FAIL] {summary['first_fail']}")
        elif level == "strict":
            for item in summary["fail_items"]:
                print(f"[FAIL] {item}")
            for item in summary["warn_items"]:
                print(f"[WARN] {item}")
        else:  # standard — FIX-278 G1 top-N + FEAT-012 G6 two-state tail
            for sev, item in _ordered_detail_items(summary):
                print(f"[{sev}] {_truncate_summary_detail(item)}")
            # FEAT-012 G6: when every FAIL/WARN detail is ALREADY on screen
            # (≤ _summary_detail_cap() lines) the tail states that fact
            # instead of inviting a --level strict chase — a small-N chase
            # invitation re-creates the audit-148 §2.1 amplification G1 was
            # built to remove (103-char summary → ~25KB chain). Judged on
            # the actual detail count (not issues_count) so the 全量展示
            # claim is literally true; count>0 with no parsed details keeps
            # the guidance (nothing is on screen to display).
            total_details = (len(summary.get("fail_items") or [])
                             + len(summary.get("warn_items") or []))
            tail = (f"构成已全量展示（{total_details} 项）"
                    if 0 < total_details <= _summary_detail_cap()
                    else f"共 {count} issues，--level strict 查看全部")
            print(tail)
    if not summary["fail_items"] and not summary["warn_items"] and summary["advisory"]:
        print(f"[ADVISORY] {summary['advisory']}")
