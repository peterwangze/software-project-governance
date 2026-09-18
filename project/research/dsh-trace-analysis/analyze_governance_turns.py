#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEPRECATED — logic promoted to the formal governance cost module (FEAT-032).

This was the EVD-1071 research script behind AUDIT-154 (governance bootstrap
cost audit, 2026-09-18). Its parsing/metric logic now lives in:

    skills/software-project-governance/infra/governance_cost.py

exposed through the verify_workflow CLI:

    python skills/software-project-governance/infra/verify_workflow.py \
        governance-cost-report --sessions-root <dir> --format text

(formerly hardcoded ~ -> pass --sessions-root explicitly now; the module
also honors the DSH_SESSIONS_ROOT environment variable)

Run THIS file and it only prints the pointer below — keeping a second copy
of the parser here would invite dual-source drift (FEAT-032 slice A-1
decision: single formal module, research scripts become thin pointers).
"""

import sys


def main():
    print(__doc__)
    print("Use the formal module / CLI instead of this deprecated script.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
