#!/usr/bin/env python3
"""
Argparse face + subcommand handlers for archive.py — FIX-435 minimal
cohesive split of the 28n module_size debt.

Domain (CLI 壳层): the FIX-417-extracted argparse builder (every subcommand,
its options, the FIX-416 --row-family three-state semantics) and the
per-subcommand handlers (result printing, refusal rendering, exit codes).
The CLI surface is BYTE-COMPATIBLE with the pre-split module: same
subcommands, same flags, same error codes, same output lines.

Seam discipline (FIX-435): handlers take ``impl`` — the archive.py entry
module's live namespace dict. Every orchestrator call
(``impl["migrate_auto"]``, ``impl["build_index"]`` …) resolves at call
time, so the FIX-187/FIX-242 ROOT seam and the tests' patch surface stay
honored, and the isolated spec_from_file_location instance dispatches
against its own namespace. Pure faces (guard, refusals, formatters) are
imported directly from the sibling modules. ``main()`` itself stays in
archive.py (it applies the --project-root global rebind before dispatch).
"""

import sys

from archive_migration_engine import (
    BIG_TABLE_MIGRATION_BATCH_SIZE,
    BigTableMigrationError,
    _SCAN_ROW_FAMILIES,
    _WRITE_MIGRATION_ROW_FAMILIES,
    _guard_row_family_write_migration,
    format_family_scan_summary,
)
from archive_verdicts import (
    _format_auto_summary,
    _format_explain_report,
)

def _build_archive_arg_parser():
    """FIX-417 (moved verbatim from main): the argparse face of the archive
    CLI — every subcommand, its options, and the FIX-416 --row-family
    three-state semantics (explicit --row-family wins; --auto defaults to
    ALL; an explicit version range defaults to EVD)."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="archive",
        description="Governance Data Archive Tool — SYSGAP-030",
    )
    parser.add_argument(
        "--project-root",
        help=(
            "Host project root whose .governance facts should be read. "
            "May also be placed after the subcommand."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # migrate
    migrate_p = subparsers.add_parser("migrate", help="Archive tasks for a version range")
    migrate_p.add_argument("version_start", nargs="?", default=None,
                           help="Start version (e.g. 0.11.0)")
    migrate_p.add_argument("version_end", nargs="?", default=None,
                           help="End version (e.g. 0.24.0)")
    migrate_p.add_argument("--dry-run", action="store_true",
                           help="Report what would be archived without modifying files")
    migrate_p.add_argument("--no-evidence", action="store_true",
                           help="Skip evidence archiving")
    migrate_p.add_argument("--auto", action="store_true",
                           help="Auto-detect version range from plan-tracker roadmap")
    migrate_p.add_argument("--row-family", default=None,
                           choices=sorted(_WRITE_MIGRATION_ROW_FAMILIES) + ["ALL"],
                           help="Governance row family to migrate (FEAT-076: "
                                "all four families are admitted; ALL carries "
                                "EVD+REVIEW+TRIAGE+RECO in one pass — the "
                                "0.93 steady-state M-8 semantics). Default "
                                "(FIX-416): ALL for --auto — Check 27 counts "
                                "all four families, so the hinted command "
                                "must drain them; EVD for an explicit "
                                "version range (0.92 behavior). An explicit "
                                "--row-family always wins.")

    # build-index
    subparsers.add_parser("build-index", help="Rebuild archive/index.md from archive files")

    # rebuild-index (FIX-384 / B-7a): index-loss/corruption recovery entry —
    # rebuild + integrity verification in one step.
    subparsers.add_parser(
        "rebuild-index",
        help="Rebuild archive/index.md from archive files, then verify integrity",
    )

    # verify
    subparsers.add_parser("verify", help="Verify archive integrity")

    # rollback
    subparsers.add_parser("rollback", help="Rollback the most recent migration")

    # migrate-big-table (FIX-385 / B-7b): batched resumable migration of a
    # row-heavy governance table into the archive — journal + batch cursor +
    # crash-safe resume (FEAT-060/061 pattern).
    p = subparsers.add_parser(
        "migrate-big-table",
        help="Batched RESUMABLE migration of a row-heavy governance table "
             "(evidence) into the archive (FIX-385 B-7b)",
    )
    p.add_argument("table", choices=["evidence"],
                   help="Big table to migrate (evidence-log)")
    p.add_argument("version_start", help="Start version (e.g. 0.60.0)")
    p.add_argument("version_end", help="End version (e.g. 0.61.0)")
    p.add_argument("--batch-size", type=int,
                   default=BIG_TABLE_MIGRATION_BATCH_SIZE,
                   help="Rows per staged batch (default: %(default)s)")
    p.add_argument("--dry-run", action="store_true",
                   help="Report what would migrate; zero writes")
    p.add_argument("--row-family", default="EVD",
                   choices=sorted(_WRITE_MIGRATION_ROW_FAMILIES),
                   help="Governance row family for this resumable leg "
                        "(FEAT-076: all four admitted; one family per "
                        "invocation — each leg carries its own journal)")

    # scan-families (FEAT-075 / DEC-278 单元二): READ-ONLY four-family
    # dry-run scan (EVD/REVIEW/RECO/TRIAGE) — reuses unit one's
    # classification semantics; zero writes; per-line report saveable as
    # TSV (--output) / full JSON (--report-json); never writes inside
    # .governance.
    scan_p = subparsers.add_parser(
        "scan-families",
        help="READ-ONLY dry-run scan of the four governance row families "
             "(EVD/REVIEW/RECO/TRIAGE) under unit one's six-condition "
             "classification (FEAT-075 / DEC-278 单元二) — zero writes",
    )
    scan_p.add_argument("version_start", help="Retention-window start (e.g. 0.1.0)")
    scan_p.add_argument("version_end", help="Retention-window end (e.g. 0.91.0)")
    scan_p.add_argument("--family", action="append", metavar="FAM",
                        choices=list(_SCAN_ROW_FAMILIES),
                        help="Restrict to one family (repeatable; "
                             "default: all four)")
    scan_p.add_argument("--output", default=None,
                        help="Write the per-line diffable TSV report here "
                             "(refused inside .governance)")
    scan_p.add_argument("--report-json", default=None,
                        help="Write the full JSON report here (refused "
                             "inside .governance)")
    return parser, migrate_p

def _cli_cmd_migrate(args, migrate_parser, impl):
    """FIX-417 (moved verbatim from main): the migrate subcommand — FIX-416
    row-family three-state resolution, execution, and result printing."""
    try:
        row_family_arg = getattr(args, "row_family", None)
        if row_family_arg is None:
            # FIX-416: --auto defaults to the four-family ALL pass so
            # the command Check 27 hints ("Run archive.py migrate
            # --auto") can actually drain EVERY family the check counts
            # under its ALL caliber — the 0.92-era EVD-only default left
            # REVIEW/TRIAGE/RECO candidates hot forever, a perpetual
            # check-archive-integrity red. An explicit version range
            # keeps the 0.92 EVD default; an explicit --row-family
            # always wins.
            row_family_arg = "ALL" if args.auto else "EVD"
        # "ALL" resolves inside migrate_auto / migrate_by_version (the
        # choke-point guard admits single families only — the old CLI
        # dispatch passed "ALL" straight in, refusing an explicit
        # `--row-family ALL` that argparse itself offered as a choice).
        if row_family_arg != "ALL":
            _guard_row_family_write_migration(row_family_arg)
        if args.auto:
            result = impl["migrate_auto"](dry_run=args.dry_run,
                                         row_family=row_family_arg)
        elif args.version_start and args.version_end:
            result = impl["migrate_by_version"](
                args.version_start,
                args.version_end,
                dry_run=args.dry_run,
                migrate_evidence=not args.no_evidence,
                row_family=row_family_arg,
            )
        else:
            print("Error: Either --auto or both version_start and "
                  "version_end must be provided.")
            migrate_parser.print_usage()
            sys.exit(1)
    except BigTableMigrationError as exc:
        # FEAT-075: the write-boundary refusal is loud, structured, and
        # non-zero-exit (never a silent no-op).
        print(f"  Migration REFUSED: {exc.payload.get('code')}")
        print(f"  {exc.payload.get('detail')}")
        sys.exit(1)
    if args.auto:
        print(_format_auto_summary(result))
        # FIX-301: the auditable explanation renders for BOTH the skip
        # path and the action path — a skip with triggers satisfied must
        # never be a black box again.
        explain_report = _format_explain_report(result.get("explain"))
        if explain_report:
            print(explain_report)
        if not result["skipped"] and not result["success"]:
            sys.exit(1)
    else:
        print(f"  Dry-run: {result['dry_run']}")
        print(f"  Tasks archived: {result['tasks_archived']}")
        print(f"  Tasks remaining: {result['tasks_remaining']}")
        print(f"  Evidence archived: {result.get('evidence_archived', 0)}")
        families = result.get("row_families_archived") or {}
        if families:
            print(f"  Row families archived: "
                  f"{', '.join(f'{k}={v}' for k, v in sorted(families.items()))}")
        print(f"  Files created: {result.get('archive_files_created', [])}")
        print(f"  {result['details']}")
        deferred = result.get("decision_migration_deferred")
        if deferred:
            # FIX-385 衔接面: the deferral is surfaced, never hidden.
            print(f"  Decision migration DEFERRED (fail-closed): "
                  f"authority state {deferred.get('authority_state')!r} "
                  f"— store-backed DEC route is the cutover ticket's "
                  f"obligation")
        if not result["success"]:
            sys.exit(1)


def _cli_cmd_migrate_big_table(args, impl):
    """FIX-417 (moved verbatim from main): the migrate-big-table
    subcommand (FIX-385 B-7b resumable leg)."""
    try:
        result = impl["migrate_evidence_resumable"](
            args.version_start, args.version_end,
            batch_size=args.batch_size, dry_run=args.dry_run,
            row_family=getattr(args, "row_family", "EVD"))
    except BigTableMigrationError as exc:
        # FIX-385: refusals are loud, structured, and non-zero-exit.
        print(f"  Migration REFUSED: {exc.payload.get('code')}")
        print(f"  {exc.payload.get('detail')}")
        sys.exit(1)
    print(f"  Dry-run: {result.get('dry_run', False)}")
    print(f"  Row family: {getattr(args, 'row_family', 'EVD')}")
    print(f"  Migrated rows: {result.get('migrated', 0)}")
    print(f"  Batches: {result.get('batches_total', 0)} "
          f"(batch_size={result.get('batch_size')})")
    print(f"  Resumed: {result.get('resumed', False)}")
    if result.get("archive_file"):
        print(f"  Archive file: {result['archive_file']}")
    if result.get("journal_path"):
        print(f"  Journal: {result['journal_path']}")
    print(f"  Decision authority state: "
          f"{result.get('decision_authority_state')}")
    if not result.get("success"):
        sys.exit(1)


def _cli_cmd_scan_families(args, impl):
    """FIX-417 (moved verbatim from main): the scan-families read-only
    subcommand (FEAT-075). The refusal for output paths under .governance
    is loud + non-zero."""
    try:
        families = tuple(args.family) if args.family else None
        report = impl["scan_row_families"](args.version_start,
                                          args.version_end,
                                          families=families)
        if args.output or args.report_json:
            impl["write_family_scan_outputs"](report, tsv_path=args.output,
                                             json_path=args.report_json)
    except BigTableMigrationError as exc:
        print(f"  Scan REFUSED: {exc.payload.get('code')}")
        print(f"  {exc.payload.get('detail')}")
        sys.exit(1)
    anchors = report["anchors"]
    print("  Row-family dry-run (read-only; zero writes)")
    print(f"  Window: [{report['window']['start']}, "
          f"{report['window']['end']}]")
    print(f"  Anchors: commit={anchors['git_commit']} "
          f"evidence-log={anchors['evidence_log_bytes']:,} B "
          f"sha256={anchors['evidence_log_sha256'][:12]}…")
    print(format_family_scan_summary(report))
    if args.output:
        print(f"  Per-line TSV report: {args.output}")


def _cli_cmd_build_index(args, impl):
    """FIX-417 (moved verbatim from main): the build-index subcommand."""
    result = impl["build_index"]()
    print(f"  Status: {result['status']}")
    print(f"  Task entries: {result['task_entries']}")
    print(f"  Evidence entries: {result['evidence_entries']}")
    print(f"  Decision entries: {result['decision_entries']}")
    print(f"  Risk entries: {result['risk_entries']}")


def _cli_cmd_rebuild_index(args, impl):
    """FIX-417 (moved verbatim from main): the rebuild-index subcommand
    (FIX-384 B-7a recovery entry)."""
    result = impl["rebuild_index"]()
    print(
        f"  Status: {'rebuilt' if result['changed'] else 'unchanged (idempotent no-op equivalent)'}"
    )
    print(f"  Index existed before: {result['index_existed']}")
    print(f"  Task entries: {result['task_entries']}")
    print(f"  Evidence entries: {result['evidence_entries']}")
    print(f"  Decision entries: {result['decision_entries']}")
    print(f"  Risk entries: {result['risk_entries']}")
    damaged = result.get("damaged_files", [])
    if damaged:
        print(f"  Damaged archive files ({len(damaged)}):")
        for d in damaged:
            print(f"    - {d['file']}: {d['kind']} ({d['detail']})")
    print(f"  Integrity: {'PASS' if result['verify_pass'] else 'FAILED'}")
    for issue in result["verify_issues"]:
        print(f"    - {issue}")
    if not result["verify_pass"]:
        sys.exit(1)


def _cli_cmd_verify(args, impl):
    """FIX-417 (moved verbatim from main): the verify subcommand."""
    result = impl["verify_archive_integrity"]()
    print(f"  Pass: {result['pass']}")
    print(f"  Total archived tasks: {result['total_archived_tasks']}")
    print(f"  Total index entries: {result['total_index_entries']}")
    if result["issues"]:
        print(f"  Issues ({len(result['issues'])}):")
        for issue in result["issues"]:
            print(f"    - {issue}")
    if not result["pass"]:
        sys.exit(1)


def _cli_cmd_rollback(args, impl):
    """FIX-417 (moved verbatim from main): the rollback subcommand."""
    result = impl["rollback_last_migration"]()
    print(f"  Success: {result['success']}")
    print(f"  Rolled back: {result['rolled_back_file']}")
    print(f"  {result['details']}")
    if not result["success"]:
        sys.exit(1)
