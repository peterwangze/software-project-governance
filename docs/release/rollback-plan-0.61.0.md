# Rollback Plan - 0.61.0

**Version**: 0.61.0
**Release**: Governance Data Bloat Remediation
**Task**: REL-048
**Date**: 2026-06-28

## 1. Rollback Triggers

Rollback to 0.60.0 if ANY of:

| # | Trigger | Detection |
| --- | --- | --- |
| 1 | archive.py regression — existing archive test fails or real archive migration corrupts data | `python -m pytest skills/software-project-governance/infra/tests/test_archive.py` exits non-zero (excluding 0 pre-existing test-isolation failures), OR `archive.py verify` reports Pass:False after a real migration |
| 2 | `_parse_priority_table_tasks` false-positives — archives tasks that should stay active | A task with open status (进行中/待启动/停滞) gets moved to archive unexpectedly; `_task_status_is_archivable` returns True for an open state |
| 3 | Check 28s false positive — blocks legitimate release on a normal-sized governance file | A governance file under 200KB triggers a finding, or `check-governance-data-size` exits non-zero with `--fail-on-issues` without `fatal_on_error=true` |
| 4 | Version-consistency regression | `check-version-consistency` reports mismatch after 0.61.0 sync |
| 5 | Test regression beyond the 2 known pre-existing | pytest fails on previously-passing test_archive or test_architecture_health test |

## 2. Rollback Steps

```bash
# 1. Revert the 0.61.0 version bump + release docs commit (after it lands)
git revert <0.61.0-commit-sha>
# OR, to roll back both the FIX-157~160 code AND the version bump:
git revert 188a6aa   # the FIX-157~160 commit
git revert <0.61.0-bump-commit-sha>

# 2. Restore strict archive behavior (0.60.0):
#    - _parse_task_status hardcoded to parts[10] (status col 9)
#    - status match == "已完成" (no ✅-variants)
#    - early-return on tasks_archived==0 (triggers as dead code)
#    - _extract_tasks_from_archive_file col-1 only
#    These are restored automatically by reverting commit 188a6aa.

# 3. .governance/ runtime state (gitignored) is independent of code version.
#    - plan-tracker.md compression (FIX-157) is local runtime state — no rollback needed,
#      history is preserved in .governance/archive/tasks/*.md and queryable via index.md
#    - To restore the pre-FIX-157 plan-tracker, use: git show <pre-188a6aa>:<n/a — gitignored>
#      (since .governance/ is gitignored, the 298KB plan-tracker is NOT in git history;
#       the compressed version + archive files are the source of truth)

# 4. Verify rollback
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python -m pytest skills/software-project-governance/infra/tests/test_archive.py -q
```

## 3. Reversibility Assessment

| Aspect | Classification | Notes |
|--------|---------------|-------|
| Code changes | **Fully reversible** | `git revert 188a6aa` restores exact 0.60.0 archive engine behavior |
| Version bump | **Fully reversible** | `git revert <bump-commit>` restores 0.60.0 version strings |
| .governance/ runtime state | **Independent / no rollback needed** | plan-tracker compression + archive files are additive, gitignored; code revert doesn't affect them, and they remain queryable |
| CHANGELOG | **Reversible** | Remove [0.61.0] section |

## 4. Data Compatibility

- **No data migration** — FIX-157~160 changes are code/parser-level only
- **Archive files** (`.governance/archive/tasks/*.md`) created by FIX-157 remain valid for both 0.60.0 and 0.61.0 (the 7-col format is readable by the reverted 0.60.0 extractor via the col-2 branch... wait — reverting to 0.60.0 removes the col-2 branch. The archive files use ID-in-col-2 format, which 0.60.0's `_extract` can't read.)
- **IMPACT**: If rolled back to 0.60.0, the FIX-157 archive files (completed-tasks/recent-completed) won't be parseable by `_extract_tasks_from_archive_file`. This is acceptable because:
  1. The archive files are still human-readable markdown
  2. `archive/index.md` (manually maintained) still references them
  3. The 0.60.0 `verify` Check 3 was already a dead-statistic (TD-015), so integrity drift was already undetectable
- **Recommendation**: If rolling back, keep the 0.61.0 archive.py (the col-2 branch) OR regenerate index.md manually. Simplest: do not roll back archive.py unless a real regression is found — it's strictly more permissive.

## 5. Monitoring Post-Rollback

- Watch `check-governance-data-size` (Check 28s) — if rolled back, this check disappears, so governance-data bloat returns to unmonitored state (the original RISK-039 condition). Re-apply FIX-160 if bloat recurs.
- Watch `archive.py migrate --auto --dry-run` — if rolled back, it returns to "无可归档数据" silent skip. Monitor plan-tracker size manually.

## 6. Boundary Tokens (conservative)

- Rollback restores 0.60.0 behavior but loses the RISK-039 data-bloat guard (Check 28s) and the archive engine's ability to parse real plan-tracker format — both are net-positive improvements; rollback should only be for a confirmed regression, not "abundance of caution"
- No external approval needed to roll back (internal infra release)
- Rolled-back state has the same no-overclaim boundaries as 0.60.0 (no 1.0.0 readiness, etc.)

### No-overclaim boundaries

No official approval. No marketplace approval (zcode or otherwise). No universal/full runtime support. No external first-session pilot success. No external host-project validation of rollback safety. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure. No 1.0.0 readiness. DEC-090/091 degraded SoD honestly noted. Rollback plan is internal documentation, not an external guarantee.
