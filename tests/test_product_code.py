"""
Test is_product_code() regex patterns for pre-commit hook FIX-026.
Validates that the function's 12 patterns (union of old Step 7b and Step 9)
correctly detect product code files and exclude governance records.
"""
import re

# Same 12 patterns as the is_product_code() function in pre-commit hook
PATTERNS = [
    r'^skills/software-project-governance/',
    r'^agents/',
    r'^skills/stage-',
    r'^skills/[a-z]+-review/',
    r'^skills/code-review/',
    r'^commands/',
    r'^infra/verify_workflow\.py$',
    r'^infra/cleanup\.py$',
    r'^infra/hooks/',
    r'^\.claude-plugin/',
    r'^\.codex-plugin/',
    r'^skills/software-project-governance/references/',  # Union pattern from old Step 7b
]


def is_product_code(file_list):
    for pattern in PATTERNS:
        if re.search(pattern, file_list, re.MULTILINE):
            return True
    return False


def test_pattern_count():
    """Verify exactly 12 patterns (union of old Step 7b:12 and Step 9:11)."""
    assert len(PATTERNS) == 12, f"Expected 12 patterns, got {len(PATTERNS)}"


def test_product_code_files_detected():
    """All 11 base product code file types should be detected."""
    product_files = [
        'skills/software-project-governance/SKILL.md',
        'agents/coordinator/prompt.md',
        'skills/stage-development/SKILL.md',
        'skills/design-review/SKILL.md',
        'skills/code-review/SKILL.md',
        'commands/governance-init.md',
        'infra/verify_workflow.py',
        'infra/cleanup.py',
        'infra/hooks/pre-commit',
        '.claude-plugin/plugin.json',
        '.codex-plugin/plugin.json',
    ]
    for f in product_files:
        assert is_product_code(f), f"Should detect product code: {f}"


def test_references_file_detected():
    """The 12th pattern (references/) from old Step 7b must be in the union."""
    assert is_product_code('skills/software-project-governance/references/agent-failure-modes.md'), \
        "Should detect references/ directory (old Step 7b-only pattern)"


def test_governance_records_excluded():
    """Governance record files should NOT be detected as product code."""
    gov_files = [
        '.governance/plan-tracker.md',
        '.governance/evidence-log.md',
        '.governance/decision-log.md',
        '.governance/risk-log.md',
        'docs/architecture/ADR-003.md',
        'README.md',
        '.gitignore',
    ]
    for f in gov_files:
        assert not is_product_code(f), f"Should NOT detect as product code: {f}"


def test_multi_line_file_list():
    """A list with mixed product and non-product files should return True."""
    multi = '.governance/plan-tracker.md\nskills/software-project-governance/SKILL.md'
    assert is_product_code(multi), "Multi-file with product code should return True"


def test_all_non_product_list():
    """A list of only non-product files should return False."""
    only_gov = '.governance/plan-tracker.md\n.gitignore\nREADME.md'
    assert not is_product_code(only_gov), "All non-product list should return False"


def test_union_completeness():
    """Verify the union includes all unique patterns from both old definitions:
    Old Step 7b: 12 patterns (included references/)
    Old Step 9: 11 patterns (did NOT include references/)
    Union should be 12 patterns.
    """
    assert any('references' in p for p in PATTERNS), \
        "The references/ pattern from old Step 7b must be in the union"


if __name__ == '__main__':
    test_pattern_count()
    test_product_code_files_detected()
    test_references_file_detected()
    test_governance_records_excluded()
    test_multi_line_file_list()
    test_all_non_product_list()
    test_union_completeness()
    print("ALL TESTS PASSED")
