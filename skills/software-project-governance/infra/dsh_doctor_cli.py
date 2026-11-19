"""Argument declarations shared by the workflow and standalone DSH doctor. Direct diagnostics are loaded on demand."""

import argparse


def add_cli_arguments(parser: argparse.ArgumentParser, *, engine_entry=False) -> None:
    """Install the diagnostic options on either supported CLI entry."""

    def wording(standalone, engine=None):
        if engine_entry:
            return engine or standalone[0].upper() + standalone[1:]
        return standalone

    parser.add_argument("--json", action="store_true",
                        help=wording("emit the machine-readable report"))
    parser.add_argument("--stage", action="append", default=None,
                        metavar="S0..S7", help=wording("run only these stages (repeatable)"))
    parser.add_argument("--offline", action="store_true",
                        help=wording("forbid every subprocess and host-plane probe; "
                                     "file-level judgments still run",
                                     "Forbid every subprocess and host-plane probe; the file-level "
                                     "judgments still run"))
    parser.add_argument("--selftest", action="store_true",
                        help=wording("crash each stage in turn and assert the isolation rules"))
    parser.add_argument("--record-evidence", action="store_true",
                        help=wording("probe the plane (read-only) and write the "
                                     "host-facts fixture named by --out",
                                     "Probe the plane read-only and write the host-facts fixture (the "
                                     "only writing path)"))
    parser.add_argument("--out", default=None,
                        help=wording("destination of --record-evidence (default: "
                                     "adapters/dsh/fixtures/host-facts-<version>.json)",
                                     "Destination of --record-evidence"))
    parser.add_argument("--rehearse", default=None, metavar="CANDIDATE.json",
                        help=wording("replay a recorded candidate against --against"))
    parser.add_argument("--against", default=None, metavar="BASELINE.json",
                        help=wording("the baseline record to rehearse against"))
    parser.add_argument("--allow-host-probe", action="store_true",
                        help=wording("allow the S5 host probe (requires M7.7 R1 to be "
                                     "satisfied first; refused otherwise)",
                                     "Allow the S5 host probe (M7.7 R1 must be satisfied first; refused "
                                     "otherwise)"))
    parser.add_argument("--fail-on-issues", action="store_true",
                        help=wording("exit 1 when a stage FAILs (the default already does)"))
