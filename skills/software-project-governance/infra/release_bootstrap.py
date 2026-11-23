"""Inspect and converge release-window write-guard state through its governed writer."""

import json
import sys


# ═══════════════════════════════════════════════════════════════════════════
# Release-window bootstrap (FIX-383 — 0.88.0 阶段 B2, rollback §8 #7
# ⑩拆票之一): the release chain (M-1~M-8) depends on checkers/writers whose
# OWN state can sit in an intermediate condition across a version switch —
# the reconciliation baseline not re-generated (基线未 regen), a
# violation-ledger line-index drift (账本行号漂移), a guard state file whose
# schema the current code no longer reads (状态文件版本变化), or a pending
# FEAT-060 consumption transaction. The world check below judges that
# world READ-ONLY (查世界不信日志 — the closure-chain effect-based resume
# discipline pointed at the checker state); the converge action recovers
# it through the guard's ONE persist path (guard-owned artifacts only —
# zero governance-record writes, the FEAT-057 contract unchanged).
# ═══════════════════════════════════════════════════════════════════════════


def check_release_bootstrap_world(*, governance_dir, tool, baseline_filename, load_baseline, reconcile):
    """FIX-383 release-window bootstrap world check — READ-ONLY.

    Judges the world the release chain re-enters after a version-switch
    interruption, over the write-guard's OWN state artifacts only:

      1. ``guard_state_current`` — the reconciliation baseline
        (``.write-guard-state.json``) is present and loads under the
        CURRENT schema. Absent + zero managed surfaces = a guard zero-
        footprint host (nothing to baseline, ok); absent WITH managed
        surfaces = the guard never baselined this window; corrupt or
        foreign schema = the deliberate re-baseline belongs to a
        converge run (loudly disclosed by the guard), never an
        incidental amnesty.
      2. ``row_families_clean`` — the face-5 probe
        (``persist_state=False``: zero writes, window never consumed)
        reports zero issues.
      3. ``violation_ledger_healthy`` — the FEAT-060 ledger loads clean
        (R6: a corrupt ledger is NEVER absorbed here — manual recovery
        is the rule, disclosed not silent).
      4. ``no_pending_txn`` — the ops-recoverable consumption journal is
        empty; an open transaction is recovered by ONE converge run via
        the three-branch world-judged ``resume_pending_txn``.
      5. ``ledger_no_drift`` — no OPEN violation whose recorded content
        digest no longer sits at its recorded object identity
        (账本行号漂移 audit — a mid-window line-index shift; a converge
        run consumes the records the eligibility rule can judge, the
        rest stay open loud per R1/R4).

    ``converged`` = all five. Recovery = ONE ``write-guard-bootstrap``
    converge run; unjudgeable states stay loud, never silently absorbed.
    """
    checks = []
    state_path = governance_dir / baseline_filename
    state, state_issue = load_baseline(governance_dir)

    records_index = {}
    row_face, _ = reconcile(
        governance_dir, persist_state=False,
        records_index_out=records_index)
    row_issues = list(row_face["issues"])

    if not state_path.is_file():
        if row_face["status"] == "SKIPPED":
            checks.append({
                "id": "guard_state_current", "ok": True,
                "detail": "无受管面（守卫零足迹）——无需基线，视为收敛",
            })
        else:
            checks.append({
                "id": "guard_state_current", "ok": False,
                "detail": "对账状态基线缺席而受管面在场（本发布窗口 guard 从未"
                          "建立基线）——恢复 = 一次 write-guard-bootstrap 收敛"
                          "运行（首跑 amnesty 建基线，零人工）",
            })
    elif state_issue is not None:
        checks.append({
            "id": "guard_state_current", "ok": False,
            "detail": "对账状态基线不可读或 schema 不识别（{0}）——恢复 = 一次"
                      "收敛运行（guard 显式重建基线并响亮披露，非静默吸收）"
                      .format(state_issue.get("detail")),
        })
    else:
        checks.append({
            "id": "guard_state_current", "ok": True,
            "detail": "状态基线在场且 schema 当前（schema_version={0}）"
                      .format(state.get("schema_version")),
        })
    checks.append({
        "id": "row_families_clean", "ok": not row_issues,
        "detail": ("受管行族对账零问题（probe face，零写入零消费）"
                   if not row_issues else
                   "{0} 个对账问题（未归属行变更/基线写入让行/面不可读等）——"
                   "恢复 = 写入器补凭证后收敛运行（响亮披露，不静默）"
                   .format(len(row_issues))),
    })

    import write_guard_state  # deferred — heavy peer module (FEAT-060)
    ledger, ledger_issue = write_guard_state.load_ledger(governance_dir)
    drift = []
    open_count = None
    if ledger_issue is not None:
        checks.append({
            "id": "violation_ledger_healthy", "ok": False,
            "detail": ledger_issue.get("detail") or "违规台账不可读",
        })
        checks.append({
            "id": "no_pending_txn", "ok": False,
            "detail": "台账不可读——待完成消费事务无法判定（由 "
                      "violation_ledger_healthy 承载，R6 不吸收不前移）",
        })
        checks.append({
            "id": "ledger_no_drift", "ok": False,
            "detail": "台账不可读——行号漂移无法判定（由 "
                      "violation_ledger_healthy 承载，R6 恢复 = 人工修复台账）",
        })
    else:
        open_records = [record for record in ledger["violations"].values()
                        if record.get("status") == "open"]
        open_count = len(open_records)
        pending = ledger.get("pending_txn")
        checks.append({
            "id": "violation_ledger_healthy", "ok": True,
            "detail": "违规台账健康（open={0}）".format(open_count),
        })
        checks.append({
            "id": "no_pending_txn", "ok": pending is None,
            "detail": ("无待完成消费事务" if pending is None else
                       "存在待完成消费事务（{0}）——恢复 = 一次收敛运行"
                       "（FEAT-060 三分支查世界 resume，零人工）".format(
                           pending.get("txn_id"))),
        })
        for record in open_records:
            surface_index = records_index.get(record.get("family"))
            if surface_index is None:
                drift.append({
                    "violation_id": record.get("violation_id"),
                    "family": record.get("family"),
                    "object_id": record.get("object_id"),
                    "detail": "登记面本轮缺席——记录不可判定；收敛运行按资格"
                              "规则消费（面缺席 = 对象不再复现）",
                })
                continue
            if surface_index.get("kind") == "unreadable":
                continue  # already loud as a row-family issue — no double count
            instances = (surface_index.get("by_key") or {}).get(
                str(record.get("object_id")), [])
            if not any(instance.get("digest") == record.get("after_hash")
                       for instance in instances):
                drift.append({
                    "violation_id": record.get("violation_id"),
                    "family": record.get("family"),
                    "object_id": record.get("object_id"),
                    "detail": "记录内容摘要不再命中其登记身份（账本行号漂移或"
                              "已修复）——收敛运行消费资格规则可判定者，其余按 "
                              "R1/R4 保持 open 响亮",
                })
        checks.append({
            "id": "ledger_no_drift", "ok": not drift,
            "detail": ("无行号漂移记录" if not drift else
                       "{0} 条 open 违规的登记身份已漂移（账本行号漂移）——"
                       "恢复 = 一次收敛运行".format(len(drift))),
        })

    not_ok = [c["id"] for c in checks if not c["ok"]]
    return {
        "tool": tool,
        "converged": not not_ok,
        "not_converged": not_ok,
        "checks": checks,
        "row_family_issues": row_issues,
        "open_violations": open_count,
        "ledger_drift": drift,
    }


def run_release_bootstrap_converge(*, check_shapes, check_world):
    """FIX-383 — the ONE governed recovery action of the release-window
    bootstrap: a guard persist-path run (the guard's OWN artifacts only —
    baseline re-gen/advance + FEAT-060 three-branch transaction resume +
    violation re-detection/eligible consumption), then a read-only world
    judgment.

    Returns ``(converged, payload)``. A non-converged payload carries the
    closed-vocabulary ``manual_intervention`` refusal code so the
    closure-chain bootstrap step halts loudly with a structured refusal —
    nothing is silently absorbed, and the remediation text names the
    governed path (writers / rule-mandated manual) per state.
    """
    guard = check_shapes(persist_state=True)
    failed_faces = sorted(
        key for key, face in guard.items()
        if isinstance(face, dict) and face.get("status") == "FAIL")
    if failed_faces:
        return False, {
            "converged": False,
            "code": "manual_intervention",
            "stage": "guard_structural_fail",
            "failed_faces": failed_faces,
            "detail": "guard 结构面 FAIL（{0}）——按 guard 各面输出经写入器路径"
                      "修复后重入；本自举路径只收敛守卫自身状态工件，不改写"
                      "治理记录".format(", ".join(failed_faces)),
        }
    report = check_world()
    if not report["converged"]:
        report["code"] = "manual_intervention"
        report["stage"] = "post_converge_not_converged"
        report["detail"] = ("收敛运行后世界仍未收敛（{0}）——响亮阻断：基线写入"
                            "让行/失败时复跑收敛即可续推；R6 损坏台账按规则"
                            "人工处置（不吸收不前移）；发散事务按三分支第三"
                            "分支响亮披露".format(
                                ", ".join(report["not_converged"])))
        return False, report
    return True, report


def cmd_write_guard_bootstrap(args, *, check_world, converge):
    """Thin entry — write-guard-bootstrap CLI (FIX-383 release-window
    bootstrap): the release chain's checker-state convergence face.

    Default (converge) mode: ONE guard persist-path run + post-run world
    judgment — the guard writes ONLY its own state artifacts (the
    reconciliation baseline + the FEAT-060 violation ledger; zero
    governance-record writes, the FEAT-057 check-only contract
    unchanged). ``--check-only`` mode: the read-only world judgment
    alone — the closure-chain bootstrap step's effect probe and the
    release-window preflight/audit face (zero writes, zero window
    consumption).

    Exit 0 = converged; exit 1 = not converged (structured JSON carries
    the closed-vocabulary ``manual_intervention`` refusal when converge
    mode fails — callers branch on the payload, never on prose). The
    JSON report is machine-provenance stamped (``tool`` field).
    """
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — best-effort console hygiene
        pass
    if getattr(args, "check_only", False):
        report = check_world()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["converged"] else 1
    converged, payload = converge()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if converged else 1
