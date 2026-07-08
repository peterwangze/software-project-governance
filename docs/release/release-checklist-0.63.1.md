# Release Checklist - 0.63.1

**Version**: 0.63.1 (patch)
**Release**: archive 引擎 build_index 非结构化归档登记修复（FIX-176）
**Date**: 2026-07-05

## 1. Release Scope

| # | Check | Status |
| --- | --- | --- |
| 1 | Version number defined (semver) | ✅ 0.63.1 (patch: archive engine coverage gap fix) |
| 2 | Change list enumerated | ✅ FIX-176 — archive build_index registers narrative/recent-completed unstructured archive files |
| 3 | Change types marked | ✅ Bugfix (archive engine coverage) / Documentation (version sync) |
| 4 | Release window | ✅ 2026-07-05 |

### Change inventory
- **FIX-176**: archive.py `build_index()` (line 1389-1540) originally only extracted entries from archive file **content** (tasks via `_extract_tasks_from_archive_file`, evidence via EVD ID, decisions via `## DEC-` header, risks via `| RISK-` row). `narrative-*.md`/`recent-completed-*.md` are free-form narrative archive files (no task rows, no DEC header, no RISK row) → build_index generated no index entries for them → orphan after rebuild → `verify_archive_integrity` Check 2 (every archive file must be index-referenced) FAIL. FIX-169 had manually registered narrative, but build_index rebuild would lose that manual entry.
- **Fix (Plan A)**: (1) new `_UNSTRUCTURED_ARCHIVE_PREFIXES` tuple + 3 helpers (`_is_unstructured_archive_file`/`_unstructured_archive_kind`/`_unstructured_archive_description`, name-prefix match + defensive frontmatter description parse); (2) `build_index()` adds `elif _is_unstructured_archive_file(f)` branch registering to `narrative_entries`; (3) index.md appends `## 非结构化归档` section after Risk index (3-column `| 归档文件 | 类型 | 描述 |`); (4) `verify_archive_integrity._parse_index_section` adds `"非结构化归档"` branch into `all_index_refs`; (5) Check 3 per-category count double-insurance not polluted (new section not in `section_map` + narrative rows don't match `[A-Z]+-\d+` regex). **Avoid duplicate registration**: `recent-completed-*.md` with 60-row task table goes through structured branch, not narrative_entries.
- **Version bump**: 0.63.0→0.63.1
- **verify output**: test_archive.py 89 passed (86 baseline + 3 new FAIL-on-buggy/PASS-after-fix), infra suite 700 passed.

## 2-6. (Standard checks — all PASS, see release-checklist-0.61.0 template)

## 7. Release Gate Evidence

```
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.63.1 --require-changelog --runtime-adapters
→ Result: baseline-consistent with 0.63.0
python skills/software-project-governance/infra/verify_workflow.py check-archive-integrity — PASS
```

Review evidence: FX-177 Release Agent + Release Reviewer R0→R1.

### Boundaries (no-overclaim)

No official approval. No marketplace approval. No universal/full runtime support. No external validation full PASS. No external first-session pilot success. No external host-project validation. No Codex Desktop marketplace-management E2E PASS. No automatic best-tool selection. No universal plugin/skill/tool availability. No RISK-036 closure. No RISK-037 closure. No RISK-039 closure (本体已修, build_index is automating the symptom, but RISK-039 needs external host validation). No 1.0.0 readiness. Pure bug fix, no behavior change. 降级 SoD (DEC-090/091).
