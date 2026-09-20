"""Phase 6 version extraction and consistency checks."""

import ast
import json
from pathlib import Path
import re
from typing import Dict, List, Optional


VERSION_PATHS = {
    "SKILL.md (source of truth)": ("skills/software-project-governance/SKILL.md", "frontmatter"),
    "manifest.json": ("skills/software-project-governance/core/manifest.json", "/version"),
    ".claude-plugin/plugin.json": (".claude-plugin/plugin.json", "/version"),
    ".claude-plugin/marketplace.json": (".claude-plugin/marketplace.json", "/plugins/0/version"),
    ".codex-plugin/plugin.json": (".codex-plugin/plugin.json", "/version"),
    ".zcode-plugin/plugin.json": (".zcode-plugin/plugin.json", "/version"),
    ".chrys-plugin/plugin.json": (".chrys-plugin/plugin.json", "/version"),
}


def extract_skill_version(path: Path) -> str:
    match = re.search(r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else ""


def _pointer(payload: object, pointer: str) -> object:
    current = payload
    for part in pointer[1:].split("/"):
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def version_facts(root: Path) -> Dict[str, str]:
    facts = {}
    for label, (relative, selector) in VERSION_PATHS.items():
        path = root / relative
        if selector == "frontmatter":
            facts[label] = extract_skill_version(path) if path.is_file() else ""
        else:
            try:
                facts[label] = str(_pointer(json.loads(path.read_text(encoding="utf-8")), selector))
            except (OSError, ValueError, KeyError, IndexError, json.JSONDecodeError):
                facts[label] = ""
    return facts


def _version_tuple(version: str) -> tuple:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError:
        return ()


def _tracked_entry_files(root: Path, names) -> set:
    """Return the subset of ``names`` tracked by git in ``root`` (FIX-285).

    Mirrors the ``_tracked_target_files`` git-probe shape of checks/projection.py:
    a non-git directory or an unavailable git yields an empty set, so callers
    treat entry copies as untracked (advisory face) instead of failing.
    """
    if not (root / ".git").exists():
        return set()
    import subprocess

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", *names],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return set()
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip() in names}


def check_version_consistency(root: Path, host_root: Optional[Path] = None) -> List[str]:
    facts = version_facts(root)
    source = facts.get("SKILL.md (source of truth)", "")
    issues = []
    if not source:
        return ["[FAIL] Cannot determine source version from SKILL.md"]
    for label, version in facts.items():
        if label != "SKILL.md (source of truth)" and version != source:
            issues.append(f"[FAIL] {label}: version={version or 'NOT FOUND'}, expected={source}")
    verifier = root / "skills/software-project-governance/infra/verify_workflow.py"
    if verifier.is_file():
        content = verifier.read_text(encoding="utf-8")
        block = re.search(r"REQUIRED_SNIPPETS\s*=\s*\{(?P<body>.*?)\n\}\n{2,}# ── Manifest", content, re.S)
        if not block:
            issues.append("[FAIL] verify_workflow.py snippet: REQUIRED_SNIPPETS block not found")
        else:
            versions = set()
            for line in block.group("body").splitlines():
                if not line.strip().startswith("#"):
                    versions.update(re.findall(r'"([0-9]+\.[0-9]+\.[0-9]+)"', line))
            if any(version != source for version in versions):
                issues.append("[FAIL] verify_workflow.py snippet: hardcoded version mismatch")
    hooks = root / "skills/software-project-governance/infra/hooks"
    for name in ("pre-commit", "commit-msg", "post-commit", "prepare-commit-msg"):
        path = hooks / name
        match = re.search(r"@version:\s*([0-9]+\.[0-9]+\.[0-9]+)", path.read_text(encoding="utf-8")) if path.is_file() else None
        if not match or match.group(1) != source:
            issues.append(f"[FAIL] hooks/{name}: @version={match.group(1) if match else 'NOT FOUND'}, expected={source}")
    changelog = root / "project/CHANGELOG.md"
    if changelog.is_file():
        match = re.search(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\]", changelog.read_text(encoding="utf-8"), re.MULTILINE)
        if not match or match.group(1) != source:
            issues.append(f"[FAIL] CHANGELOG latest version={match.group(1) if match else 'NOT FOUND'}, expected={source}")
    host_root = host_root or root
    plan = host_root / ".governance/plan-tracker.md"
    if plan.is_file():
        match = re.search(r"工作流版本[^0-9]*([0-9]+\.[0-9]+\.[0-9]+)", plan.read_text(encoding="utf-8"))
        if match and match.group(1) != source:
            issues.append(f"[WARN] plan-tracker workflow version={match.group(1)}, expected={source}")
    # Bootstrap marker face guard (FIX-285 / DEC-173③ / REL-071 F-3).
    # Entry files: AGENTS.md (tracked) + CLAUDE.md (gitignored local sync, FIX-256).
    # Stale tracked marker -> FAIL; stale untracked local copy -> [WARN] advisory
    # (REL-071 F-2/BC-3: the root CLAUDE.md is local-only; FIX-238.2 fail-closed
    # covers its re-sync). A tracked entry file without a marker header is stale
    # per the G-series rule (missing header = pre-0.73.0). Absent files skip.
    entry_names = ("AGENTS.md", "CLAUDE.md")
    tracked = _tracked_entry_files(host_root, entry_names)
    for name in entry_names:
        entry = host_root / name
        if not entry.is_file():
            continue
        match = re.search(r"@bootstrap-version:\s*([0-9]+\.[0-9]+\.[0-9]+)", entry.read_text(encoding="utf-8"))
        if not match:
            if name in tracked:
                issues.append(f"[FAIL] {name}: @bootstrap-version marker NOT FOUND (missing header = stale, expected={source})")
            continue
        if _version_tuple(match.group(1)) < _version_tuple(source):
            if name in tracked:
                issues.append(f"[FAIL] {name}: @bootstrap-version={match.group(1)} is stale (< active_version {source})")
            else:
                issues.append(f"[WARN] {name}: @bootstrap-version={match.group(1)} is stale (< active_version {source}); untracked local copy — advisory (FIX-238.2 fail-closed covers re-sync)")
    # Static version pin scan (DEC-213③ / FIX-361) — appended WARN face over
    # infra/tests; WARN-only posture, no effect on existing FAIL semantics.
    issues.extend(scan_static_version_pins(root, active_version=source))
    return issues


# ── Static version pin scan (DEC-213③ / FIX-361) ────────────────────────────
# M-1 caliber blind spot, rule-ized: release-time test pins (FIX-352/353) were
# found by hand for the fifth consecutive time — no machine face intercepted
# NEW static pins of the active version inside infra/tests.
#
# Judgement semantics (minimal, auditable): a test-file line is a "static
# version pin" when it carries a standalone semver token equal to the CURRENT
# active version (SKILL.md frontmatter — the same authority the rest of this
# module reads) on a line that can actually execute or feed data. Pure `#`
# comment lines and docstrings are annotations — they cannot turn a suite red
# on a bump — so they are skipped (docstrings detected via ast; string CONTENT
# lines that merely start with `#`, e.g. fixture markdown headings, stay
# scanned). This captures the pre-fix defect shapes verbatim (FIX-352
# assertion argument string; FIX-353 module-level fixture head string) while
# synthetic versions (9.9.9), historical references (0.83.0 after the bump),
# and future targets (0.85.0 today) never equal the active version and pass.
# At the next bump today's future targets become equal and surface as WARN —
# derive them or exempt them then.
#
# Posture: WARN-only disclosure (0.85.0 conservative close; FAIL escalation
# is a later ruling). Findings name file:line plus the suggested derivation.
#
# Exemptions (FIX-354-style auditable ledger): synthetic fixture data and
# version-pair test inputs that legitimately mention the active version live
# in STATIC_PIN_EXEMPTIONS as (line, token, reason) rows. The token anchors a
# row to its line's content: an entry whose line no longer carries the token
# (drift or removal) is reported as a stale-exemption warning, so the ledger
# cannot rot into a blanket allow.
STATIC_PIN_SCAN_DIR = "skills/software-project-governance/infra/tests"

_SEMVER_TOKEN_RE = re.compile(r"(?<![\d.])(\d+\.\d+\.\d+)(?![\d.])")

_REASON_FIXTURE_TABLE = (
    "fixture task-table heading/row — synthetic plan-tracker scenario data; "
    "aggregate projection semantics never compare task-table versions to the "
    "active version (shape survived the 0.83.0->0.84.0 bump unchanged)")
_REASON_MIGRATION_PAIR = (
    "migration_flag(plan, active) synthetic version-pair input or its echo "
    "assertion — relative-comparison semantics; neither operand is the real "
    "active version")
_REASON_INSTRUMENT_VERSION = (
    "instrument-version fixture data (\"check-injection-budget@X.Y.Z\") — a "
    "versioned identifier under test, not a pin of the active version; "
    "registered at the 0.85.0 bump (target file belongs to an in-flight "
    "untracked batch — re-audit these rows when the owning batch lands)")
_REASON_FUTURE_TARGET = (
    "synthetic future-target literal proving non-active semver tokens stay "
    "silent; it equals the active version only at the 0.85.0 bump (the "
    "FIX-361 designed bump-time double signal) and goes dormant afterwards")
_REASON_FIXTURE_ROW_TEXT = (
    "fixture task-table row text quoted as synthetic plan-tracker data; the "
    "version column is scenario payload and is never compared to the active "
    "version")
_REASON_GUARD_OUTPUT_ASSERT = (
    "assertion argument quoting the write-guard WARN disclosure's "
    "declarative BLOCK-upgrade version reference (DEC-224 wording) — it "
    "pins a product-output statement, not the active version; re-audit if "
    "the disclosure wording changes (the stale-exemption audit below flags "
    "token drift automatically)")

STATIC_PIN_EXEMPTIONS = {
    "skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py": [
        (116, "0.84.0", _REASON_FIXTURE_TABLE),
        (120, "0.84.0", _REASON_FIXTURE_TABLE),
        (121, "0.84.0", _REASON_FIXTURE_TABLE),
        (122, "0.84.0", _REASON_FIXTURE_TABLE),
        (212, "0.84.0", _REASON_FIXTURE_TABLE),
        (216, "0.84.0", _REASON_FIXTURE_TABLE),
        (217, "0.84.0", _REASON_FIXTURE_TABLE),
        (319, "0.84.0", _REASON_MIGRATION_PAIR),
        (322, "0.84.0", _REASON_MIGRATION_PAIR),
        (326, "0.84.0", _REASON_MIGRATION_PAIR),
        (331, "0.84.0", _REASON_MIGRATION_PAIR),
        (336, "0.84.0", _REASON_MIGRATION_PAIR),
        # 0.85.0 bump-time row (the FIX-361 designed double signal): this
        # fixture row was written with the then-future target while 0.84.0
        # was active, so it surfaces exactly once — at this bump.
        (123, "0.85.0", _REASON_FIXTURE_TABLE),
    ],
    # In-flight untracked batch (baseline/task-row/store tooling): rows pin
    # only fixture data; re-audit at landing per the reason text. NOTE: the
    # baseline-metadata file is being edited by its owning batch while this
    # bump runs — line numbers re-anchored 2026-09-19; the stale-exemption
    # audit below flags any further drift automatically. Re-anchored again
    # by FEAT-055 (0.86.0 batch 2.0 wiring: three import lines + guard-test
    # additions shifted the file; same six instrument-version fixture rows).
    "skills/software-project-governance/infra/tests/test_baseline_metadata.py": [
        (63, "0.85.0", _REASON_INSTRUMENT_VERSION),
        (318, "0.85.0", _REASON_INSTRUMENT_VERSION),
        (395, "0.85.0", _REASON_INSTRUMENT_VERSION),
        (566, "0.85.0", _REASON_INSTRUMENT_VERSION),
        (623, "0.85.0", _REASON_INSTRUMENT_VERSION),
        (741, "0.85.0", _REASON_INSTRUMENT_VERSION),
        # 0.86.0 bump-time row: instrument-version fixture added by the
        # FEAT-047 batch (same shape as the six rows above — a versioned
        # identifier under test, not a pin of the active version).
        (383, "0.86.0", _REASON_INSTRUMENT_VERSION),
    ],
    "skills/software-project-governance/infra/tests/test_task_row_update.py": [
        (74, "0.85.0", _REASON_FIXTURE_ROW_TEXT),
        (76, "0.85.0", _REASON_FIXTURE_ROW_TEXT),
        # 0.86.0 bump-time rows: fixture task-table rows written by the
        # FEAT-051 batch while 0.85.0 was active (the FIX-361 bump-time
        # double signal); the 目标版本 column is scenario payload.
        (59, "0.86.0", _REASON_FIXTURE_ROW_TEXT),
        (68, "0.86.0", _REASON_FIXTURE_ROW_TEXT),
        (203, "0.86.0", _REASON_FIXTURE_ROW_TEXT),
        (421, "0.86.0", _REASON_FIXTURE_ROW_TEXT),
        (441, "0.86.0", _REASON_FIXTURE_ROW_TEXT),
        (586, "0.86.0", _REASON_FIXTURE_ROW_TEXT),
        (594, "0.86.0", _REASON_FIXTURE_ROW_TEXT),
    ],
    "skills/software-project-governance/infra/tests/test_closure_chain.py": [
        # 0.86.0 bump-time row: FEAT-056 fixture tracker row (marked
        # 非真实计划面 in the row itself); version column is scenario payload.
        (83, "0.86.0", _REASON_FIXTURE_ROW_TEXT),
    ],
    "skills/software-project-governance/infra/tests/test_triage_write_guard.py": [
        # 0.86.0 bump-time rows: FEAT-057 fixture tracker row (scenario
        # payload) + one assertion quoting the write-guard WARN disclosure's
        # declarative BLOCK-upgrade version reference (DEC-224 wording).
        (992, "0.86.0", _REASON_FIXTURE_ROW_TEXT),
        (1138, "0.86.0", _REASON_GUARD_OUTPUT_ASSERT),
    ],
    "skills/software-project-governance/infra/tests/test_static_version_pins.py": [
        (158, "0.85.0", _REASON_FUTURE_TARGET),
    ],
}


def _annotation_string_lines(tree):
    """Line spans that are annotation, not executable/data code.

    Returns ``(docstring_lines, multiline_string_inner_lines)``. Docstrings
    are bare string-expression statements heading Module/Class/Function
    bodies. Multiline-string INNER lines physically start with string content
    (e.g. fixture markdown like ``## 0.84.0 task 表``) and must not be misread
    as ``#`` comment lines.
    """
    docstring_lines = set()
    string_inner_lines = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                first = body[0]
                end = getattr(first, "end_lineno", first.lineno)
                docstring_lines.update(range(first.lineno, end + 1))
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            end = getattr(node, "end_lineno", node.lineno)
            if end > node.lineno:
                string_inner_lines.update(range(node.lineno + 1, end + 1))
    return docstring_lines, string_inner_lines


def scan_static_version_pins(root, active_version=None, tests_dir=None, exemptions=None):
    """DEC-213③ (FIX-361): report static pins of the active version in tests.

    WARN-only by design. Returns ``[WARN]``-prefixed issue lines; empty when
    the tree carries no unexempted pin or has no tests directory (advisory
    face — installed packs ship without infra/tests).
    """
    if active_version is None:
        active_version = version_facts(root).get("SKILL.md (source of truth)", "")
    if not active_version:
        return []  # the source-version face already FAILs upstream
    base = Path(tests_dir) if tests_dir else root / STATIC_PIN_SCAN_DIR
    if not base.is_dir():
        return []
    registry = STATIC_PIN_EXEMPTIONS if exemptions is None else exemptions
    issues = []
    for path in sorted(base.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            source_text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            issues.append(f"[WARN] static-version-pin: cannot read {rel} — line scan skipped")
            continue
        try:
            tree = ast.parse(source_text)
        except SyntaxError as exc:
            tree = None
            issues.append(f"[WARN] static-version-pin: cannot parse {rel} ({exc.msg}) — line scan skipped")
        doc_lines, string_inner = _annotation_string_lines(tree) if tree is not None else (set(), set())
        allowed_lines = {entry[0] for entry in registry.get(rel, ()) if entry[1] == active_version}
        for lineno, line in enumerate(source_text.splitlines(), start=1):
            if lineno in doc_lines:
                continue
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") and lineno not in string_inner:
                continue
            tokens = [m.group(1) for m in _SEMVER_TOKEN_RE.finditer(line)]
            if active_version not in tokens:
                continue
            if lineno in allowed_lines:
                continue  # audited exemption (reason lives in the ledger)
            issues.append(
                f"[WARN] static-version-pin: {rel}:{lineno} pins the active version "
                f"\"{active_version}\" literally — derive it instead "
                f"(resolve_entry.read_active_version() / @@ACTIVE_VERSION@@ token, the "
                f"FIX-352/353 shape) or register a reasoned (line, token, reason) "
                f"exemption in checks/version.py STATIC_PIN_EXEMPTIONS (DEC-213③)")
    # Exemption ledger audit: an entry whose target line no longer carries its
    # token has drifted — re-audit (prevents blanket-allow rot).
    for rel, entries in registry.items():
        target = root / rel
        if not target.is_file():
            for lineno, token, _reason in entries:
                issues.append(
                    f"[WARN] static-version-pin: stale exemption {rel}:{lineno} "
                    f"(token \"{token}\") — target file missing; re-audit STATIC_PIN_EXEMPTIONS")
            continue
        try:
            lines = target.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            continue  # unreadable face already covered by the scan above
        for lineno, token, _reason in entries:
            line = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
            if token not in [m.group(1) for m in _SEMVER_TOKEN_RE.finditer(line)]:
                issues.append(
                    f"[WARN] static-version-pin: stale exemption {rel}:{lineno} "
                    f"(token \"{token}\") — line no longer carries the token; "
                    f"re-audit STATIC_PIN_EXEMPTIONS (DEC-213③)")
    return issues
