"""Default policies for external-project validation and its target diagnostics."""

import re


EXTERNAL_PROJECT_VALIDATION_COMMANDS = [
    ("status", ["status"]),
    ("gate G1", ["gate", "G1"]),
    ("governance-context", ["governance-context", "--fail-on-issues"]),
    ("check-governance", ["check-governance", "--fail-on-issues"]),
]

EXTERNAL_PROJECT_VALIDATION_BOUNDARY = (
    "No official approval. No marketplace approval. No external validation full PASS. "
    "No Codex Desktop marketplace-management E2E PASS. No Desktop lifecycle E2E PASS. "
    "No automatic best-tool selection. No universal plugin/skill/tool availability. "
    "No catalog entry runtime PASS. No RISK-036 closure. No 1.0.0 production-ready."
)


EXTERNAL_PROJECT_NATIVE_ENTRY_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".cursorrules",
    ".cursor/rules",
    ".github/copilot-instructions.md",
)

EXTERNAL_PROJECT_NATIVE_ENTRY_PATTERNS = (
    (
        "repo-local workflow home",
        re.compile(r"(?<![A-Z0-9_])skills/software-project-governance/", re.I),
        "hardcodes repo-local skills/software-project-governance/ instead of installed workflow home",
    ),
    (
        "repo-local verify command",
        re.compile(r"\bpython(?:3)?\s+skills/software-project-governance/infra/verify_workflow\.py\b", re.I),
        "hardcodes python skills/software-project-governance/infra/verify_workflow.py",
    ),
    (
        "repo-local hook install command",
        re.compile(r"\bcp\s+skills/software-project-governance/infra/hooks/", re.I),
        "hardcodes cp skills/software-project-governance/infra/hooks... hook install path",
    ),
)

EXTERNAL_PROJECT_REQUIRED_INSTALLED_HOOKS = ("pre-commit", "commit-msg", "post-commit")
