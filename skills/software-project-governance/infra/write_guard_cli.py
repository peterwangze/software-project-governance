"""Run the governance write guard and its posture-management commands."""

import sys


def cmd_governance_write_guard(args, *, governance_dir, check_shapes):
    """Thin entry — governance-write-guard CLI (FEAT-011 / G3 extension).

    One command after a Coordinator direct write to ``.governance/`` gives
    the same G3 structural validation the change-triage CLI has at write
    time: plan-tracker task-row shape (AUDIT-149 §4 M1 signatures),
    evidence-log machine-family columns + ID format (DEC-168), agent-locks
    schema (Check 26), execution-packets structure (Check 18c field table),
    plus the FEAT-057 row-family reconciliation (managed-row provenance
    against the ``.write-guard-state.json`` baseline). All logic lives in
    :func:`check_shapes`; this entry is argparse glue +
    printing (RISK-039 thin-entry discipline).

    Check-only contract (FEAT-057 amendment): the guard repairs NOTHING —
    governance records are never rewritten. The artifacts it maintains are
    its OWN state: the reconciliation baseline
    (``.governance/.write-guard-state.json``) — the first run establishes
    the baseline (amnesty — 存量行不追溯, zero WARN), every later run
    diffs the delta since the previous run and re-baselines after judging —
    and, since FEAT-060, the violation ledger
    (``.governance/.write-guard-violations.json``, written by
    infra/write_guard_state.py on this CLI path only: persistent open/
    consumed/superseded records + consumption-right grants + the
    ops-recoverable consume transaction; a host with zero violations never
    sees the file). FEAT-064: face 5 posture is per-family — the shipped
    default is all-WARN (loud disclosure, exit code unaffected); a family
    activated BLOCK (guard-owned posture config via ``--activate-block``)
    FAILs the face on uncredentialed changes (exit 1 — the workflow is
    blocked loudly; the guard is write-AFTER and cannot stop the file from
    being modified) and holds its baseline until the writer remediation
    loop closes the window through the consumption transaction. The
    recovery break-glass channel (``--break-grant``; 限定留痕 =
    对象/操作者/理由/有效期/次数 + 每次 CLI 运行 use 审计事件——不可
    静默) downgrades scoped BLOCK issues to loud WARN-class disclosures
    while open; ``--deactivate-block`` is the audited B-12 flag rollback
    (reason + authorized-by demanded). Management-mode reports render
    inside ``write_guard_state.run_guard_management_cli`` (leaf-module
    precedent — the engine's print budget does not grow).

    Exit 0 = no FAIL face (or the management mode completed); exit 1 = at
    least one FAIL face (a structural breach must not pass silently — the
    same fail-closed posture as the change-triage write guard); exit 2 =
    a fail-closed management-mode refusal; SKIPPED faces (artifact absent)
    never fail.
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for candidate in ("activate_block", "deactivate_block", "show_posture",
                      "break_grant", "break_clear", "break_show"):
        if getattr(args, candidate, None):
            import write_guard_state
            sys.exit(write_guard_state.run_guard_management_cli(
                candidate, args, governance_dir=governance_dir))
    result = check_shapes(
        persist_state=True,
        session_id=getattr(args, "session_id", None),
        deferred_ledger=True)  # FEAT-081 B4: M2 词集台账随 CLI 面落账
    faces = (
        ("plan_tracker",
         "plan-tracker 任务表行（M1 签名：重复优先级列/行尾空单元格）"),
        ("evidence_log",
         "evidence-log 机器行族 TRIAGE/RECO（DEC-168 行族列数 + ID 格式）"),
        ("agent_locks", "agent-locks.json schema（Check 26）"),
        ("execution_packets", "execution-packets.json 结构（Check 18c 字段表）"),
        ("row_families",
         "受管行族对账（EVD/DEC/REVIEW/任务状态列/ops 台账——机器凭证披露，"
         "分族姿态 FEAT-057/FEAT-064）"),
        ("pin_ledger",
         "pin 豁免台账（FIX-462：STATIC_PIN_EXEMPTIONS 结构 FAIL + 手改无 "
         "provenance WARN vs 交付 amnesty）"),
    )
    print()
    print("=== Governance Write Guard (G3 扩展 — FEAT-011, Coordinator 直写路径) ===")
    total = 0
    failed = False
    for key, label in faces:
        face = result[key]
        count = len(face["issues"])
        total += count
        failed |= face["status"] == "FAIL"
        print("  [{0}] {1} — {2} issue(s)".format(
            face["status"], label, count))
        for issue in face["issues"]:
            where = ""
            if issue.get("line"):
                where = "L{0} ".format(issue["line"])
            if issue.get("task_id"):
                where += "{0} ".format(issue["task_id"])
            print("    - {0}: {1}".format(where.strip(), issue["detail"]))
            if issue.get("expected"):
                print("      期望列形: {0}".format(issue["expected"]))
    baselined = result["row_families"].get("baselined") or []
    for rel in baselined:
        print("  [BASELINE] {0} — 首见受管面建立状态基线（存量行不追溯——amnesty，"
              "零 WARN）".format(rel))
    print()
    if failed:
        print("Result: FAIL — {0} issue(s)。守卫只检不改（零 .governance 修复——"
              "状态基线 .write-guard-state.json 为守卫自身工件，FEAT-057）；"
              "按上方行号与期望列形修复后由写入者复跑本命令（BLOCK 姿态面："
              "补救 = 经写入器补机器凭证后复跑自动消费，或经 --break-grant "
              "限定恢复通道处置——FEAT-064）".format(total))
        sys.exit(1)
    warn_total = len(result["row_families"]["issues"])
    if warn_total:
        print("Result: PASS — 0 FAIL issue(s), {0} WARN(s)（受管行变更无机器"
              "凭证——响亮披露不阻断；补 governance_store/task_row_update "
              "凭证或由写入者复核后复跑本命令即基线翻新；分族 BLOCK 机制已"
              "交付未激活——FEAT-064，姿态经 --show-posture 查看）。"
              "守卫只检不改（零 .governance 治理记录写入）。".format(warn_total))
        return
    print("Result: PASS — 0 issue(s)（SKIPPED = 产物缺席，非缺陷）。"
          "守卫只检不改（零 .governance 治理记录写入；状态基线 "
          ".write-guard-state.json 为守卫自身工件）。")
