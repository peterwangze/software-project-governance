"""Register work planning, review, write controls and governance ledgers."""


def register_task_review(subparsers):
    # task-priority-analysis (FIX-226 / AUDIT-141 / DEC-134)
    tpa_p = subparsers.add_parser(
        "task-priority-analysis",
        help="Parse plan-tracker dependencies, build DAG, recommend next task (FIX-226)",
    )
    tpa_p.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when the dependency graph contains a cycle (default: "
             "exit 0 + WARNING banner; FIX-237.3 cycle tolerance)",
    )
    tpa_p.add_argument(
        "--evidence-task",
        dest="evidence_task",
        metavar="TASK_ID",
        help="Machine-write a RECO-{TASK_ID} recommendation-snapshot row to "
             "the evidence log (M7.4 step 6 completion evidence; FIX-262 / "
             "REQ-108). Fail-closed (exit 2, no write) on a malformed id.",
    )
    tpa_p.add_argument(
        "--force",
        action="store_true",
        help="Bypass the same-session duplicate-run suppression (FEAT-012 "
             "G5): re-run the full analysis even when a cached same-day run "
             "over an unchanged plan-tracker matches, and re-append the "
             "RECO row even when one is already recorded today.",
    )

    # review-record (FIX-236.1 / ADR-017 §3.4 Wiring A — the single
    # machine-written review-conclusion persistence path; FEAT-094 extends
    # it into the five-step review trust transaction: report-hash pin +
    # immutable snapshot binding + CONFLICT refusal + R2 obligation
    # auto-registration in the authority ledger + supervisor ABORTED /
    # UNKNOWN terminal states)
    rr_p = subparsers.add_parser(
        "review-record",
        help="Machine-write one review conclusion + wire it to the loop engine (FIX-236)",
    )
    rr_p.add_argument("--task", required=True,
                      help="Reviewed task id (PREFIX-NNN, e.g. FIX-236)")
    rr_p.add_argument("--round", type=int, default=0,
                      help="Review round (default 0 = R0)")
    rr_p.add_argument("--result", required=True,
                      choices=["APPROVED", "APPROVED_WITH_NOTES",
                               "NEEDS_CHANGE", "BLOCKED",
                               "ABORTED", "UNKNOWN"],
                      help="Review conclusion (ABORTED/UNKNOWN = supervisor-"
                           "recorded agent-death terminal states, FEAT-094 — "
                           "no revisit, no obligation discharge)")
    rr_p.add_argument("--report", required=True,
                      help="Path to the reviewer's full report (MUST be "
                            "readable — its bytes are sha256-pinned into "
                            "the record, FEAT-094)")
    rr_p.add_argument("--reviewer", default=None,
                      help="Reviewer/agent name")
    rr_p.add_argument("--record-only", action="store_true", help="Archive an independent review without a gate decision")
    rr_p.add_argument("--unit", default=None,
                      help="Flow-unit id (wiring; optional — else registry mapping)")
    rr_p.add_argument("--gate", default=None,
                      help="Gate id G1..G11 (wiring; optional — else registry mapping)")
    rr_p.add_argument("--scope", default="full", choices=["full", "delta"],
                      help="Review injection scope (FEAT-091): 'delta' = "
                           "R2+ revisit reviews the fix diff + prev-round "
                           "report + acceptance criteria (M7.4 T1 R2 "
                           "injection face); default 'full' is backward "
                           "compatible")
    rr_p.add_argument("--delta-base", default=None,
                      help="Delta anchor for --scope delta (FEAT-091): "
                           "prev-round review report path or diff anchor")
    rr_p.add_argument("--bind-tree", help="Full Git tree OID declared in the signed review report")
    rr_p.add_argument("--bind-file", action="append", default=None,
                      metavar="PATH",
                      help="FEAT-094: pin one reviewed repo file with a "
                           "git hash-object blob hash (repeatable; "
                           "untracked-safe immutable binding)")
    rr_p.add_argument("--abort-reason", default=None,
                      help="FEAT-094: supervisor's reason for an ABORTED / "
                           "UNKNOWN terminal record (agent death)")

    # next-candidates (FIX-236.3 / ADR-017 §3.4, P3-5 — read end of the
    # loop_exit → next-unit recommendation bridge)
    nc_p = subparsers.add_parser(
        "next-candidates",
        help="Read the loop_exit → next-unit recommendation snapshot (FIX-236)",
    )
    nc_p.add_argument("--top-n", type=int, default=3,
                      help="Number of candidates (default 3)")
    nc_p.add_argument("--refresh", action="store_true",
                      help="Recompute from plan-tracker + loop event log")
    nc_p.add_argument("--write", action="store_true",
                      help="Persist the recomputed snapshot")
    nc_p.add_argument("--goal", help="Read current recommendations for a bound goal without writing")


def register_change_requests(subparsers):
    # change-triage (FIX-237.4 / ADR-017 §4.4 — mandatory change-control
    # triage for product-code task intake; fail-closed: no record → the task
    # MUST NOT be created)
    ctri_p = subparsers.add_parser(
        "change-triage",
        help="Run the mandatory 5-step triage (dependency/priority/conflict/"
             "version/side-effect) for a new product-code task (FIX-237/FIX-271)",
    )
    ctri_p.add_argument("--task", required=True,
                        help="New task id (PREFIX-NNN, e.g. FIX-241)")
    ctri_p.add_argument("--title", default="",
                        help="One-line task title")
    ctri_p.add_argument("--tier", choices=("setup", "inner", "middle", "outer"), default="inner")
    ctri_p.add_argument("--gate")
    ctri_p.add_argument("--parent")
    ctri_p.add_argument("--priority", required=True,
                        choices=["P0", "P1", "P2"],
                        help="Proposed priority (determined with in-flight + "
                             "version-chain context)")
    # FEAT-080 / ADR-021 §2.2.1 写路径窗口关闭 (DEC-290(5)): the B2-era
    # conservative machine-signal default could not be passed through the
    # locked CLI; required=True closes the window — a missing flag exits 2
    # upstream and the library-level default path becomes unreachable from
    # this CLI (user-named additionally requires --demand-basis and defaults
    # to P1 per DEC-286(7), library-side enforcement).
    ctri_p.add_argument("--demand-source", required=True, dest="demand_source",
                        choices=["user-named", "active-defect", "machine-signal"],
                        help="Demand provenance (ADR-021 §2.2.1 three-value "
                             "enum; REQUIRED — the intake window default is "
                             "closed, FEAT-080)")
    ctri_p.add_argument("--demand-basis", default="", dest="demand_basis",
                        help="Traceability basis REQUIRED for user-named "
                             "(user quote / DEC ref / session-record anchor; "
                             "BC-4 防 出身洗白)")
    ctri_p.add_argument("--prior-art", action="append", metavar="REF",
                        help="Precedent or external source. Repeat for each reference or "
                             "separate with commas/semicolons. Required for FEAT, DESIGN, "
                             "RESEARCH and AUDIT.")
    ctri_p.add_argument("--version", default="未规划版本",
                        help="Target version (semver X.Y.Z or 未规划版本)")
    ctri_p.add_argument("--depends-on", default="",
                        help="Comma-separated task-family dependency IDs "
                             "(cross-entity refs like RISK-/DEC- are ignored)")
    ctri_p.add_argument("--files", required=True,
                        help="Comma-separated product files the task will "
                             "modify (quick lane covers .governance/ only)")
    ctri_p.add_argument("--reason", default="",
                        help="Triage rationale (priority determination)")
    ctri_p.add_argument("--acceptance", default="",
                        help="Acceptance criteria copied verbatim into triage and execution packets. R5 "
                             "banned real-env wording (真实安装/真实环境) "
                             "auto-attaches the R1 review condition "
                             "(FIX-271 / AUDIT-146)")
    ctri_p.add_argument("--side-effects", default="",
                        help="Side-effect declaration (surface + blast "
                             "radius) for outside-repo effects (installer "
                             "runs / profile writes / network publishing) — "
                             "R2 fifth step: undeclared detectable side "
                             "effects record a WARN issue")

    # demand-source-revise (FEAT-080 / ADR-021 §2.2.1 F-P1-3 — the revision
    # channel's B3 CLI regularization; the window-era Coordinator library
    # API becomes a first-class face)
    dsr_p = subparsers.add_parser(
        "demand-source-revise",
        help="Append one demand_source revision event (append-only jsonl "
             "+ evidence row; the triage record stays immutable — "
             "ADR-021 §2.2.1 / FEAT-080)",
    )
    dsr_p.add_argument("--task", required=True,
                       help="Task id (PREFIX-NNN) — MUST already have a "
                            "triage record")
    dsr_p.add_argument("--to", required=True,
                       choices=["user-named", "active-defect", "machine-signal"],
                       help="Target demand_source (three-value enum)")
    dsr_p.add_argument("--basis", required=True,
                       help="Traceability basis (REQUIRED non-empty — the "
                            "revision re-asserts the provenance claim, same "
                            "obligation as the initial labeling, BC-4)")
    dsr_p.add_argument("--basis-kind", default="session-record",
                       dest="basis_kind",
                       choices=["user-quote", "dec-ref", "session-record"],
                       help="Basis kind (default session-record)")
    dsr_p.add_argument("--authorized-by", default="", dest="authorized_by",
                       help="Actor annotation (e.g. Coordinator)")


def register_governance_tools(subparsers):
    import bootstrap_aggregate
    import governance_cost

    # governance-cost-report (FEAT-032 / AUDIT-154 slice A-1 — governance
    # cost observability: TTFA, time-to-substantive-work, token breakdown,
    # tool duration distribution; read-only scan of session traces; args
    # and handler live in governance_cost.py — the engine only wires
    # dispatch, ArchGuard R4 print budget untouched)
    gcr_p = subparsers.add_parser(
        "governance-cost-report",
        help="Governance cost observability report (FEAT-032): TTFA, "
             "time-to-substantive-work, governance token breakdown, tool "
             "duration distribution (read-only scan; --format json|text)",
    )
    governance_cost.add_arguments(gcr_p)

    # governance-bootstrap (FEAT-033 / AUDIT-154 slice A-2 — read-only
    # bootstrap aggregate: resolve envelope + lean status projection +
    # v1-deferred health face + task-priority light candidates in ONE
    # output, ≤2K token projection; args and handler live in
    # bootstrap_aggregate.py — the engine only wires dispatch, ArchGuard
    # R4 print budget untouched)
    gb_p = subparsers.add_parser(
        "governance-bootstrap",
        help="Read-only bootstrap aggregate (FEAT-033): resolve envelope + "
             "status projection + deferred health face + light candidates "
             "in one output (--budget-ms/--format/--profile)",
    )
    bootstrap_aggregate.add_arguments(gb_p)


def register_write_guard(subparsers):
    # governance-write-guard (FEAT-011 / G3 extension — structural write
    # guard over the Coordinator's DIRECT .governance writes; check-only)
    # FEAT-064: + family-posture management modes (--activate-block /
    # --deactivate-block / --show-posture) and the recovery break-glass
    # channel (--break-grant / --break-clear / --break-show); the default
    # no-flag invocation stays the check run.
    wgp = subparsers.add_parser(
        "governance-write-guard",
        help="Check .governance structural integrity after a Coordinator "
             "direct write (plan-tracker task rows / evidence-log machine "
             "rows / agent-locks / execution-packets — FEAT-011 G3 "
             "extension; check-only, zero writes) — plus FEAT-064 family "
             "posture management (--activate-block/--deactivate-block/"
             "--show-posture) and the break-glass channel (--break-grant/"
             "--break-clear/--break-show)",
    )
    wgp_action = wgp.add_mutually_exclusive_group()
    wgp_action.add_argument(
        "--activate-block", metavar="FAMILIES", default=None,
        help="FEAT-064: activate BLOCK posture for comma-listed managed "
             "families (evidence, review, decision, task_status, "
             "ops_ledger) — requires --reason/--authorized-by; writes the "
             "guard-owned posture config (.write-guard-posture.json); the "
             "REAL flip moment is the Coordinator's decision",
    )
    wgp_action.add_argument(
        "--deactivate-block", metavar="FAMILIES", default=None,
        help="FEAT-064: the audited B-12 flag rollback — set comma-listed "
             "families back to WARN (requires --reason/--authorized-by; "
             "recorded in the posture config history)",
    )
    wgp_action.add_argument(
        "--show-posture", action="store_true",
        help="FEAT-064: show the declared per-family ruling, the active "
             "postures and the break-glass state (read-only)",
    )
    wgp_action.add_argument(
        "--break-grant", action="store_true",
        help="FEAT-064: open the recovery break-glass window (限定留痕: "
             "--reason/--authorized-by required; scope --families, "
             "validity --ttl-hours, use count --max-uses; one use event "
             "per guard CLI run — 不可静默)",
    )
    wgp_action.add_argument(
        "--break-clear", action="store_true",
        help="FEAT-064: clear the active break-glass window (grant moves "
             "to break_glass_history; --authorized-by/--reason audited)",
    )
    wgp_action.add_argument(
        "--break-show", action="store_true",
        help="FEAT-064: show the active break-glass window and history "
             "(read-only)",
    )
    wgp.add_argument(
        "--families", default="",
        help="break-glass scope: comma-listed managed families (default: "
             "* = every BLOCK-active family)",
    )
    wgp.add_argument("--reason", default="",
                     help="why (posture change / break-glass audit)")
    wgp.add_argument("--authorized-by", dest="authorized_by", default="",
                     help="who authorized (posture change / break-glass "
                          "audit)")
    wgp.add_argument("--ttl-hours", type=float, default=None,
                     help="break-glass validity in hours "
                          "(default 24)")
    wgp.add_argument("--max-uses", type=int, default=None,
                     help="break-glass use-count limit (default 3)")
    wgp.add_argument(
        "--session-id", dest="session_id", default=None,
        help="FEAT-064 R3 wiring: explicit session identity for the "
             "violation state machine's same-session escalation rule "
             "(overrides GOVERNANCE_SESSION_ID)",
    )

    # write-guard-bootstrap (FIX-383 — 0.88.0 阶段 B2 发版管线自举): the
    # release chain's checker-state convergence face (guard-owned
    # artifacts only) + read-only world check (the closure-chain
    # bootstrap step's effect probe / release-window preflight audit)
    wbp = subparsers.add_parser(
        "write-guard-bootstrap",
        help="Release-window bootstrap for the write-guard's own state "
             "artifacts (FIX-383): converge mode re-generates/advances "
             "the reconciliation baseline, resumes a pending FEAT-060 "
             "consumption transaction and re-judges the world; "
             "--check-only is the read-only probe/audit face",
    )
    wbp.add_argument(
        "--check-only", action="store_true",
        help="Read-only world judgment (zero writes, zero window "
             "consumption) — the release-window preflight/audit face "
             "and the closure-chain bootstrap step's effect probe",
    )

    # agent-locks-acquire (FEAT-013 / RISK-046 — machine dispatch-lock
    # acquisition: pre-write path existence validation + expected-new
    # pre-created-file exemption + same-day change-triage files
    # cross-check; hand-writing agent-locks.json is forbidden)
    ala_p = subparsers.add_parser(
        "agent-locks-acquire",
        help="Acquire dispatch locks with write-time validation: path "
             "existence + expected-new exemption + change-triage files "
             "cross-check (FEAT-013 / RISK-046)",
    )
    ala_p.add_argument("--task", required=True,
                       help="Dispatch task id (PREFIX-NNN)")
    ala_p.add_argument("--files", required=True,
                       help="Comma-separated repo-relative lock targets")
    ala_p.add_argument("--expected-new", default="",
                       help="Comma-separated subset of --files the task "
                            "will create (not on disk yet) — the "
                            "pre-created-file exemption, persisted as "
                            "expected_new: true on those entries")
    ala_p.add_argument("--role", default="Developer",
                       help="Agent role for the active_tasks entry")
    ala_p.add_argument("--session", default="",
                       help="Coordinator session id")
    ala_p.add_argument("--description", default="",
                       help="One-line dispatch description")
    ala_p.add_argument("--ttl", type=int, default=14400,
                       help="Lock TTL in seconds (default 14400 = 4h)")
    ala_p.add_argument("--ttl-reason", default="",
                       help="Why this lock is held (recorded per entry)")


def register_ledger_writers(subparsers):
    import baseline_metadata
    import governance_store
    import pin_ledger
    import premise_tracker
    import task_row_update

    # task-row-update (FEAT-055 / 0.86.0 batch 2.0 — governed task-row
    # state-flip writer, FEAT-051): args and handler live in
    # task_row_update.py — the engine only wires dispatch, ArchGuard R4
    # print budget untouched)
    tru_p = subparsers.add_parser(
        "task-row-update",
        help="Governed single write path for plan-tracker task-row state "
             "flips (FEAT-051): state CAS + short-term lock + operation "
             "receipts; --inspect is the read-only observation surface",
    )
    task_row_update.add_arguments(tru_p)

    # governance_store writer family (FEAT-055 / 0.86.0 batch 2.0 —
    # FEAT-046): locks-extend / locks-amend / locks-release (FIX-370) /
    # evidence-append / decision-append; args and handlers live in
    # governance_store.py — the
    # engine only wires dispatch, ArchGuard R4 print budget untouched)
    lse_p = subparsers.add_parser(
        "locks-extend",
        help="Extend dispatch file-lock TTLs (FEAT-046 governed writer; "
             "operation_id idempotent, structured JSON result)",
    )
    governance_store.add_locks_extend_arguments(lse_p)
    lsa_p = subparsers.add_parser(
        "locks-amend",
        help="Amend a dispatch lock: add files / retune TTL (FEAT-046 "
             "governed writer; operation_id idempotent)",
    )
    governance_store.add_locks_amend_arguments(lsa_p)
    lsr_p = subparsers.add_parser(
        "locks-release",
        help="Release a dispatch task's locks: the active_tasks entry and "
             "all its file_locks entries, one atomic governed write "
             "(FIX-370; operation_id idempotent; fail-closed on a lockless "
             "task)",
    )
    governance_store.add_locks_release_arguments(lsr_p)
    eva_p = subparsers.add_parser(
        "evidence-append",
        help="Append one machine-written EVD row (FEAT-046 governed "
             "writer; five typed refs machine-checked, effect-based "
             "idempotency, --dry-run preview)",
    )
    governance_store.add_evidence_append_arguments(eva_p)
    dea_p = subparsers.add_parser(
        "decision-append",
        help="Append one machine-written DEC row (FEAT-046 governed "
             "writer; effect-based idempotency, --dry-run preview)",
    )
    governance_store.add_decision_append_arguments(dea_p)

    # FIX-462: pins ledger machine writer (register / re-anchor over
    # checks/version.py STATIC_PIN_EXEMPTIONS) — args and handlers live in
    # pin_ledger.py, engine wires dispatch only (ArchGuard R4 print budget
    # untouched; exit 0 ok / 2 refusal / 3 retryable).
    pins_p = subparsers.add_parser(
        "pins",
        help="Machine writer for the STATIC_PIN_EXEMPTIONS ledger (FIX-462): "
             "pins register / pins re-anchor — AST-anchored validated edits "
             "with provenance comments; effect-idempotent, --dry-run preview",
    )
    pin_ledger.add_arguments(pins_p)

    # FIX-463: decision-premise invalidator (count / review / status over
    # .governance/premise-events.jsonl, DEC-368② class) — args and handlers
    # live in premise_tracker.py, engine wires dispatch only (ArchGuard R4
    # print budget untouched; exit 0 ok / 2 refusal / 3 retryable).
    premise_p = subparsers.add_parser(
        "premise",
        help="Decision-premise invalidator (FIX-463): premise count / "
             "premise review / premise status — replayable event ledger; "
             "a collapsed premise strips the decision's ranking authority",
    )
    premise_tracker.add_arguments(premise_p)

    # baseline_metadata commands (FEAT-055 / 0.86.0 batch 2.0 — FEAT-047):
    # baseline-register / baseline-evaluate; args and handlers live in
    # baseline_metadata.py — the engine only wires dispatch, ArchGuard R4
    # print budget untouched; exit 0/1/2 are gate verdicts, 3 is a
    # command error)
    blr_p = subparsers.add_parser(
        "baseline-register",
        help="Register one numeric-gate baseline with seven provenance "
             "elements (FEAT-047; --dry-run previews without writing)",
    )
    baseline_metadata.add_register_arguments(blr_p)
    ble_p = subparsers.add_parser(
        "baseline-evaluate",
        help="Evaluate an observation against the registered baseline "
             "(FEAT-047; exit 0 pass / 1 fail / 2 not_evaluable)",
    )
    baseline_metadata.add_evaluate_arguments(ble_p)


def register_authority_and_isolation(subparsers):
    import authority_ledger
    import enforcement
    import execution_isolation
    import goal_bridge

    # authority-ledger (FEAT-093 / 0.98.0 — the authority ledger for
    # governance core state): args and handler live in
    # authority_ledger.py — the engine only wires dispatch (the
    # governance_cost pattern); the migrate/rebuild faces carry the
    # identity contract + zero-loss counts proof.
    al_p = subparsers.add_parser(
        "authority-ledger",
        help="FEAT-093 authority ledger: task identity contract (same-id "
             "different-semantics writes REFUSED + audited) + append-only "
             "event log + rebuildable plan-tracker projection (dry-run "
             "first)",
    )
    authority_ledger.add_arguments(al_p)

    # FEAT-096 (0.98.0 — execution isolation conservative surface): args
    # and handlers live in execution_isolation.py — the engine only wires
    # dispatch (the governance_cost pattern; ArchGuard R4 print budget
    # untouched). Exit 0 ok / 2 refusal (fail-closed; judge's
    # allowed=false also exits 2).
    isw_p = subparsers.add_parser(
        "isolation-write",
        help="FEAT-096 exclusive write slot per file domain (--action "
             "begin/end/judge): shared-file write concurrency limit — a "
             "second writer on the same domain is refused with holder + "
             "expected release",
    )
    execution_isolation.add_write_arguments(isw_p)
    iss_p = subparsers.add_parser(
        "isolation-snapshot",
        help="FEAT-096 read-only review snapshot (--action create/release): "
             "domains under review refuse writes (被审/在写互斥); snapshot "
             "files + sha256 manifest are chmod read-only",
    )
    execution_isolation.add_snapshot_arguments(iss_p)
    isl_p = subparsers.add_parser(
        "isolation-lease-reclaim",
        help="FEAT-096 reclaim expired agent-locks leases with "
             "loss-of-authority verification (expired writer's residual "
             "write slot revoked; old-format lock files stay readable)",
    )
    execution_isolation.add_lease_reclaim_arguments(isl_p)
    ist_p = subparsers.add_parser(
        "isolation-status",
        help="FEAT-096 machine-readable isolation world: writers / lease "
             "expiries / reviews / waiters / reclaim log (--text for "
             "grep anchors)",
    )
    execution_isolation.add_status_arguments(ist_p)
    isc_p = subparsers.add_parser(
        "isolation-capability",
        help="FEAT-096 capability disclosure — references the FEAT-095 "
             "harness-enforcement research report; NO host-level "
             "isolation claim (U1 unverified)",
    )
    execution_isolation.add_capability_arguments(isc_p)

    # FEAT-097 (0.98.0 — goal↔budget bridge): args and handler live in
    # goal_bridge.py — the engine only wires dispatch (governance_cost
    # pattern; ArchGuard R4 print budget untouched). Exit 0 ok /
    # 2 refusal (blocked/scope-ruling gate; judge's any_danger also 2).
    gbr_p = subparsers.add_parser(
        "goal-bridge",
        help="FEAT-097 goal and budget bridge (--action record/checkpoint/"
             "ruling/status/judge/thresholds/mapping): state mapping + "
             "danger-zone collection + checkpoint artifacts + resume "
             "authorization (blocked 后禁未授权续跑)",
    )
    goal_bridge.add_goal_bridge_arguments(gbr_p)

    # FEAT-095 (0.98.0 — action-level enforcement): args and handler
    # live in enforcement.py — the engine only wires dispatch (same
    # pattern).  Exit 0 allow / 2 hard block (incl. fail-closed) /
    # 3 throttle (review-debt budget) / 4 stale notice (non-blocking);
    # GOVERNANCE_ENFORCEMENT=off = zero-drift advisory baseline.
    enf_p = subparsers.add_parser(
        "enforcement-check",
        help="FEAT-095 action-level enforcement (--facts JSON / "
             "--print-strategy): six boundaries × three layers — "
             "hard block exit 2 / throttle exit 3 / stale notice "
             "exit 4 / allow exit 0 (protocol+CLI face, no host-level "
             "interception claim)",
    )
    enforcement.add_enforcement_check_arguments(enf_p)
