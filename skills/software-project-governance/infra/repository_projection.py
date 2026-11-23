"""Repository mirror inventory and injection contract checks."""

from checks.version import extract_skill_version
from pathlib import Path
from project_paths import package_root as _package_root
import hashlib
import json
import re
import subprocess
import sys


PROJECTION_SYNC_PATTERNS = (
    "skills/*/SKILL.md",
    "skills/software-project-governance/SKILL.md",
    "skills/software-project-governance/core/**/*.md",
    "skills/software-project-governance/core/**/*.json",
    "skills/software-project-governance/infra/**/*.py",
    "skills/software-project-governance/infra/**/*.md",
    "skills/software-project-governance/infra/**/*.sh",
    "skills/software-project-governance/infra/hooks/*",
    "skills/software-project-governance/references/**/*.md",
    "commands/*.md",
    # FEAT-038 (AUDIT-154 A-7): `/governance` was split into a router layer plus
    # per-Scenario on-demand documents under `commands/governance/`. The extra
    # pattern keeps the fixture-mirror inventory (and its manifest contract
    # `required_members`) exact — the legacy glob `commands/*.md` does not
    # descend into the new directory.
    "commands/governance/*.md",
    "agents/*.md",
)


# The version-line marker resolves against the active SKILL frontmatter.
VERSION_LINE_ANCHOR = "@version-line"


INJECTION_CONTRACT_ANCHORS = {
    # FIX-310 / DEC-187: the composition template is the SINGLE persona surface
    # (the former second spelling, `presets/governance/agent.cordis.yml`, is
    # gone with the copy model), so it carries the whole anchor set:
    #   * FIX-274 / F-02 — the M7.7 real-environment contract keywords;
    #   * FIX-272 / FEAT-010 R0 F1 — the persona VERSION-LINE same-source guard
    #     (`治理工作流（vX.Y.Z）` must track the SKILL.md authority; the
    #     dsh-persona-version projection guards it too, the dynamic marker here
    #     is the belt-and-braces layer that also covers a hand-edited file).
    "agent-presets/governance/persona.md.template": [
        "关键行为契约", "复审必达", "NEEDS_CHANGE", "完成必推荐",
        "task-priority-analysis", "选项必带依据",
        # FIX-260 / REQ-107: 4th contract line — review conclusions MUST be
        # persisted through the review-record CLI machine path.
        "审查结论必机录", "review-record",
        # FIX-274 / F-02 (M7.7 projection): 5th contract line — user
        # real-environment protection (R1 one-of-three / R4 per-command
        # relay / R5 acceptance wording).
        "真实环境必防护", "三选一", "逐条上报", "隔离环境安装冒烟",
        # FEAT-072 / DEC-266: three-element recommendation-card contract
        # (M7.4 step 6 projection — card prose before AskUserQuestion).
        "三要素", "推荐卡",
        VERSION_LINE_ANCHOR,
    ],
    "skills/software-project-governance/SKILL.md": [
        "关键行为契约", "复审必达", "完成必推荐",
        "task-priority-analysis", "选项必带依据",
        # FIX-274 / F-02 (M7.7 projection): 4th contract item.
        "真实环境必防护", "三选一", "逐条上报", "隔离环境安装冒烟",
        # FEAT-072 / DEC-266: three-element recommendation-card contract
        # (M7.4 step 6 projection — card prose before AskUserQuestion).
        "三要素", "推荐卡",
    ],
    # FEAT-072 / DEC-266: canonical surface — M7.4 step 6c MUST carry the
    # three full card labels; existence-only, fail-closed like every path
    # above.
    "skills/software-project-governance/references/behavior-protocol.md": [
        "服务目标：", "解决问题：", "方案要点：",
    ],
    "adapters/dsh/AGENTS.md.template": ["关键行为契约"],
}


# Staged clauses activate once any member of their group appears in the surface.
INJECTION_CONTRACT_STAGED_ANCHORS = {
    "ADR-021-B1a": {
        # persona face: M1 clause + the persona-only 用户点名 (ADR-021 §2.1
        # file table) + M2 clause.
        "agent-presets/governance/persona.md.template": [
            "推荐必标需求源", "用户点名", "发现即闭环",
        ],
        "skills/software-project-governance/SKILL.md": [
            "推荐必标需求源", "发现即闭环",
        ],
        "skills/software-project-governance/references/behavior-protocol.md": [
            "推荐必标需求源", "发现即闭环",
        ],
        "adapters/dsh/AGENTS.md.template": [
            "推荐必标需求源", "发现即闭环",
        ],
    },
}


def _extract_json_version(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str(payload.get("version", "")).strip()


def _extract_plan_workflow_version(path):
    if not path.is_file():
        return ""
    content = path.read_text(encoding="utf-8")
    match = re.search(r"工作流版本\*\*:\s*([0-9]+\.[0-9]+\.[0-9]+)", content)
    if not match:
        match = re.search(r"工作流版本.*?([0-9]+\.[0-9]+\.[0-9]+)", content)
    return match.group(1) if match else ""


def _projection_hash(path, *, read_text_normalized):
    text = read_text_normalized(path)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _projection_source_files(root, patterns, *, projection_sync_patterns):
    root = Path(root)
    patterns = patterns or projection_sync_patterns
    files = set()
    for pattern in patterns:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if "__pycache__" in rel or rel.endswith(".pyc"):
                continue
            files.add(rel)
    return sorted(files)


def _projection_target_tracked_files(root, target_dir):
    """Return target fixture files tracked by git, or None outside a git checkout."""
    root = Path(root)
    target_dir = Path(target_dir)
    if not (root / ".git").exists():
        return None
    try:
        target_rel = target_dir.relative_to(root).as_posix()
    except ValueError:
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", target_rel],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    prefix = target_rel.rstrip("/") + "/"
    tracked = set()
    for line in result.stdout.splitlines():
        item = line.strip().replace("\\", "/")
        if item.startswith(prefix):
            tracked.add(item[len(prefix):])
    return tracked


def _target_fixture_file_is_checkable(rel_path, target_tracked):
    if target_tracked is None:
        return True
    return rel_path.replace("\\", "/") in target_tracked


def check_injection_contract(root=None, *, package_root=None, injection_contract_anchors=INJECTION_CONTRACT_ANCHORS,
                             injection_contract_staged_anchors=INJECTION_CONTRACT_STAGED_ANCHORS,
                             version_line_anchor=VERSION_LINE_ANCHOR, extract_skill_version=extract_skill_version):
    """FIX-253 / REQ-112 (design §6.5): injection-surface anchor existence check.

    Asserts that each deterministic injection surface (DSH persona template /
    entry SKILL / DSH thin pointer) carries its anchor keyword set from
    INJECTION_CONTRACT_ANCHORS. Boundary (design §6.5): existence only —
    never full-text equality, and no behavior detection (that boundary stays
    with REQ-107/108/113 per DEC-143).

    FIX-272 / FEAT-010 R0 F1: ``VERSION_LINE_ANCHOR`` entries are DYNAMIC —
    resolved at check time to the persona version line
    ``治理工作流（v<authority>）`` from the SKILL.md frontmatter version, so
    the shipped preset can never silently drift from the release authority
    (FIX-250 precedent). Unresolvable authority → explicit FAIL (fail-closed:
    useless to report a missing keyword when the version source is broken).
    """
    root = Path(root) if root is not None else (package_root or _package_root())
    issues = []
    files_checked = 0
    authority = extract_skill_version(
        root / "skills/software-project-governance/SKILL.md")
    for relative, anchors in sorted(injection_contract_anchors.items()):
        path = root / relative
        if not path.is_file():
            issues.append(f"{relative}: injection-surface file missing")
            continue
        files_checked += 1
        text = path.read_text(encoding="utf-8")
        for anchor in anchors:
            if anchor == version_line_anchor:
                if not authority:
                    issues.append(
                        f"{relative}: {version_line_anchor} unresolved — "
                        "SKILL.md frontmatter version missing")
                    continue
                anchor = f"治理工作流（v{authority}）"
            if anchor not in text:
                issues.append(f"{relative}: anchor missing: {anchor}")
    # FEAT-079 / DEC-290(4): staged anchor faces — activation-gated
    # existence assertions (all-absent → inactive + disclosure; any-present
    # → active, every staged anchor then fails closed when missing).
    staged = {}
    for stage, anchors_by_path in sorted(
            injection_contract_staged_anchors.items()):
        present = {}
        for relative, anchors in sorted(anchors_by_path.items()):
            path = root / relative
            if not path.is_file():
                present[relative] = {anchor: False for anchor in anchors}
                continue
            text = path.read_text(encoding="utf-8")
            present[relative] = {anchor: anchor in text
                                 for anchor in anchors}
        active = any(any(hits.values()) for hits in present.values())
        missing = []
        if active:
            for relative, hits in sorted(present.items()):
                for anchor, hit in hits.items():
                    if not hit:
                        missing.append(
                            f"{relative}: staged anchor missing "
                            f"({stage}): {anchor}")
        staged[stage] = {
            "active": active,
            "missing": missing,
            "anchors_checked": sum(len(v) for v in anchors_by_path.values()),
            "inactive_reason": (
                None if active else
                f"{stage}: no staged anchor present yet — B1a contract "
                "text not landed (activation-gated; DEC-290(4) commit "
                "order: text before registry)"),
        }
        issues.extend(missing)
    staged_summary = "; ".join(
        (f"staged {stage}: inactive (B1a text not landed; DEC-290(4))"
         if not state["active"] else
         f"staged {stage}: active, {state['anchors_checked']} anchors guarded")
        for stage, state in sorted(staged.items()))
    return {
        "issues": issues,
        "files_checked": files_checked,
        "anchors_checked": sum(len(v) for v in injection_contract_anchors.values()),
        "staged": staged,
        "staged_summary": staged_summary,
    }


def cmd_check_version_consistency(_args, *, check_version_consistency):
    """Run version consistency check across all declaration locations."""
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

    issues = check_version_consistency()

    print("\n=== Version Consistency Check ===")
    print(f"  Source of truth: skills/software-project-governance/SKILL.md")
    print(f"  Files checked: 12 (SKILL.md, manifest.json, marketplace.json, 3 plugin.json, CHANGELOG, plan-tracker, 4 hooks) + bootstrap markers (AGENTS.md, CLAUDE.md)")

    fail_items = [i for i in issues if not i.startswith("[WARN]")]
    warn_items = [i for i in issues if i.startswith("[WARN]")]

    if warn_items:
        print(f"\n  Warnings ({len(warn_items)}):")
        for w in warn_items:
            print(f"    {w}")

    if fail_items:
        print(f"\n  Failures ({len(fail_items)}):")
        for f in fail_items:
            print(f"    {f}")
        print(f"\n  Result: FAILED — {len(fail_items)} mismatch(es)")
        sys.exit(1)
    else:
        print(f"\n  Result: PASSED — all version declarations consistent")
    print()


def cmd_check_projection_sync(
        args, *, check_projection_sync, check_entry_bootstrap_sync, print_entry_bootstrap_report,
):
    """Run projection/fixture sync guard independently."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_projection_sync()
    print("\n=== Projection Sync Check ===")
    print(f"  Source version: {result['source_version'] or 'unknown'}")
    print(f"  Mirrored files checked: {result['mirrors_checked']}")
    if result.get("mirrors_skipped_untracked"):
        print(f"  Untracked local projection copies skipped: {result['mirrors_skipped_untracked']}")
    if result["version_checks"]:
        print("  Version checks:")
        for item in result["version_checks"]:
            print(f"    - {item['label']}: {item['version'] or 'missing'} ({item['path']})")
    if result["issues"]:
        print(f"\n  Result: FAILED — {len(result['issues'])} issue(s)")
        for issue in result["issues"][:20]:
            print(f"    - {issue}")
        if len(result["issues"]) > 20:
            print(f"    ... and {len(result['issues']) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("\n  Result: PASSED — projection files and version declarations are synchronized")
    print()
    # FEAT-037: entry-file bootstrap projection rides the same guard (one command covers both surfaces).
    entry_result = check_entry_bootstrap_sync()
    entry_failed = not print_entry_bootstrap_report(entry_result)
    if entry_failed or (getattr(args, "fail_on_issues", False) and not entry_result["pass"]):
        sys.exit(1)


def cmd_check_injection_contract(args, *, check_injection_contract):
    """Run the injection-surface anchor check independently (FIX-253/REQ-112)."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    result = check_injection_contract()
    print("\n=== Injection Contract Check (FIX-253/REQ-112) ===")
    print(f"  Files checked: {result['files_checked']}; anchors: {result['anchors_checked']}"
          + (f"; {result['staged_summary']}" if result["staged_summary"] else ""))
    if result["issues"]:
        print(f"\n  Result: FAILED — {len(result['issues'])} issue(s)")
        for issue in result["issues"][:20]:
            print(f"    - {issue}")
        if len(result["issues"]) > 20:
            print(f"    ... and {len(result['issues']) - 20} more")
        if getattr(args, "fail_on_issues", False):
            sys.exit(1)
    else:
        print("\n  Result: PASSED — injection surfaces carry the behavior-contract anchors")
    print()
