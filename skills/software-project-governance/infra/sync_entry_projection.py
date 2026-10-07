"""FEAT-037 — single canonical bootstrap source → thin platform projections.

AUDIT-154 slice A-6: when a workspace carries BOTH platform-native entry
files (``AGENTS.md`` + ``CLAUDE.md``), injecting the full bootstrap template
into both doubles the fixed per-session cost.  This module keeps
``commands/governance-init.md`` Step 7 as the ONLY template fact source and
derives every entry-file bootstrap section from it:

* primary entry  → the selected profile's full template (unchanged flow);
* secondary entry → a generated thin pointer (≤40 lines, ≤3072 bytes) that
  keeps the minimal survival checks (resolve_entry first action, plan-tracker
  read, SELF-CHECK, mode confirmation, governance quick entries) and points
  at the primary entry instead of duplicating the full template;
* single-entry workspaces keep the full bootstrap (backward compatible).

Everything is deterministic and idempotent: applying the projection twice
yields a zero diff, and ``build_sync_report`` is the read-only drift guard
wired into ``verify_workflow.py check-projection-sync``.

CLI:
    python sync_entry_projection.py --project <dir> [--source-root <repo>]
        [--profile standard] [--primary CLAUDE.md] [--write] [--dry-run]

Default mode is read-only (check); ``--write`` applies the projection.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

CANONICAL_SOURCE = Path("commands") / "governance-init.md"
PRIMARY_DEFAULT = "CLAUDE.md"
SECONDARY_OF = {"CLAUDE.md": "AGENTS.md", "AGENTS.md": "CLAUDE.md"}
THIN_MAX_LINES = 40
THIN_MAX_BYTES = 3072
FULL_PROFILE_KEYS = ("lightweight", "standard", "strict")

# The bootstrap section always opens with an H1/H2 "Governance Bootstrap"
# header (H1 only in the whole-file DSH template variant).
_SECTION_START_RE = re.compile(r"(?m)^#{1,2} Governance Bootstrap[^\n]*\n")
_H2_LINE_RE = re.compile(r"(?m)^## [^\n]*\n")
_STEP_HEADER_RE = re.compile(r"(?m)^### Step [0-9]")
_FENCE_LINE_RE = re.compile(r"(?m)^```\s*$")
_TEMPLATE_LABEL_RE = re.compile(
    r"(?m)^\*\*(?P<label>lightweight profile|standard profile|strict profile"
    r"|secondary-thin) 注入模板[^\n]*\n```markdown\n"
)
_FULL_BOOTSTRAP_MARKER = "### Step 0: 确定双维度模式"
_THIN_BOOTSTRAP_MARKER = "次要平台入口薄指针"
_PLACEHOLDER = "{PRIMARY_ENTRY}"

#: FEAT-037 P3-6 (closed by FEAT-040) — thin-pointer DIALECT contract.
#:
#: Two thin-pointer dialects legitimately coexist and can never be byte-equal:
#: the generated secondary-thin projection (H2 header + `次要平台入口薄指针`
#: marker + the governance quick-entry block) and the DSH agent-instructions
#: template (`adapters/dsh/AGENTS.md.template`: H1 header, DSH-only sections for
#: the subagent mapping / hooks / upgrade path, no quick-entry block). The
#: FEAT-037 guard only knew the first, so it classified the second as `unknown`
#: and left it unguarded. Reconciliation = **shared core + per-dialect extras**:
#: the survival semantics a thin pointer exists to preserve are dialect-neutral
#: and machine-checked for BOTH, while the dialect-specific sections stay free.
THIN_SHARED_CORE_ANCHORS = (
    ("bootstrap header", "Governance Bootstrap"),
    ("bootstrap version line", "> @bootstrap-version: "),
    ("resolve_entry first action", "resolve_entry.py"),
    ("plan-tracker read", ".governance/plan-tracker.md"),
    ("SELF-CHECK", "SELF-CHECK"),
    ("mode confirmation (always-on)", "always-on"),
    ("mode confirmation (silent-track)", "silent-track"),
)

#: Extras carried by the GENERATED secondary-thin projection only.
THIN_DIALECT_GENERATED_ANCHORS = (
    ("bootstrap header (H2 form)", "## Governance Bootstrap"),
    ("resolve_entry (full command)", "resolve_entry.py --json"),
    ("AskUserQuestion (generated spelling)", "AskUserQuestion"),
    ("quick entries", ".governance/evidence-log.md"),
    ("skill entry", "skills/software-project-governance/SKILL.md"),
)

#: Extras carried by the DSH dialect only (agent-instructions template).
THIN_DIALECT_DSH_ANCHORS = (
    ("bootstrap header (H1 form)", "# Governance Bootstrap"),
    ("ask tool (DSH spelling)", "ask_user_question"),
    ("skill package name", "software-project-governance"),
)

#: Back-compat alias — the full anchor set of the generated dialect.
_THIN_REQUIRED_ANCHORS = THIN_SHARED_CORE_ANCHORS + THIN_DIALECT_GENERATED_ANCHORS

#: The DSH dialect's own template (guarded as a thin-pointer surface).
DSH_THIN_TEMPLATE = "adapters/dsh/AGENTS.md.template"
#: The DSH dialect must also carry the gray-release switch (FEAT-040): the
#: agent-instructions payload is the only project-level surface a DSH-hosted
#: session sees before the skill loads.
DSH_THIN_REQUIRED_EXTRA = ("行为灰度开关",)


class CanonicalSourceError(ValueError):
    """Raised when the canonical template source cannot be parsed (fail-closed)."""


class BootstrapSpliceError(CanonicalSourceError):
    """FIX-439: raised when a splice would break the section-singleton
    invariant (duplicate/missing template H2) — the write is refused and the
    original entry file kept. Subclasses :class:`CanonicalSourceError` so the
    existing fail-closed CLI/report catch sites answer it with the same
    structured ERROR instead of a traceback."""


@dataclass(frozen=True)
class EntryWrite:
    relative_path: str
    kind: str  # "full" | "thin"
    section_text: str
    reason: str


# ── canonical extraction ──────────────────────────────────────────────────

def extract_canonical_templates(text: str) -> dict[str, str]:
    """Extract the Step 7 injection templates keyed by profile.

    Boundary rule: a block runs from its label's ````` ```markdown ````` open
    fence to the NEXT label line (or the next ``### Step N`` header for the
    last block).  The block's closing fence is the LAST bare ```` ``` ````
    line inside that slice — nested fences (e.g. the Bootstrap 变更纪律
    block inside the standard template) therefore cannot truncate a block.

    FEAT-041 composition (DEC-218 shared base): the ``strict`` block carries
    ONLY the strict-profile delta (``### Strict Profile 强制规则`` …); the
    shipped strict template is the standard shared base with that delta
    appended.  Composing here — the single extraction authority — keeps the
    canonical source single-maintenance while every consumer (entry
    projection, ``check-entry-bootstrap-sync``, injection budget, tests)
    sees and prices the exact text that gets injected.
    """
    labels = list(_TEMPLATE_LABEL_RE.finditer(text))
    if not labels:
        raise CanonicalSourceError(
            "canonical source carries no Step 7 injection template labels"
        )
    templates: dict[str, str] = {}
    for index, match in enumerate(labels):
        key = match.group("label").removesuffix(" profile")
        start = match.end()
        if index + 1 < len(labels):
            region_end = labels[index + 1].start()
        else:
            # Last block: bounded by the first command Step header after the
            # label (e.g. `### Step 8`), never by template-internal headers.
            step_after = _STEP_HEADER_RE.search(text, start)
            region_end = step_after.start() if step_after else len(text)
        stop = _closing_fence_stop(text, start, region_end, key)
        chunk = text[start:stop].rstrip("\n")
        if not chunk:
            raise CanonicalSourceError(f"canonical template block `{key}` is empty")
        templates[key] = chunk + "\n"
    missing = [key for key in (*FULL_PROFILE_KEYS, "secondary-thin") if key not in templates]
    if missing:
        raise CanonicalSourceError(f"canonical template blocks missing: {missing}")
    templates["strict"] = (
        templates["standard"].rstrip("\n")
        + "\n\n"
        + templates["strict"].rstrip("\n")
        + "\n"
    )
    return templates


def load_canonical_templates(source_root: Path) -> dict[str, str]:
    source = Path(source_root) / CANONICAL_SOURCE
    if not source.is_file():
        # FEAT-034 P3-6 (DX trap, closed by FEAT-040): `--source-root` defaults
        # to `--project`, so a projection run whose project is a FIXTURE
        # workspace fails here with a bare "missing" that reads as if the
        # canonical source were damaged. Name the fix in the error instead:
        # fail-closed stays, the misdiagnosis does not.
        raise CanonicalSourceError(
            f"canonical source is missing: {source} — `--source-root` defaults "
            f"to `--project`, so pass the PLUGIN REPO ROOT explicitly "
            f"(`--source-root <dir carrying {CANONICAL_SOURCE}>`) when the "
            f"project being projected is a fixture/secondary workspace"
        )
    return extract_canonical_templates(source.read_text(encoding="utf-8"))


def _closing_fence_stop(text: str, open_end: int, region_end: int, key: str) -> int:
    """Return the char offset of a block's true closing fence.

    The region passed in is already bounded by the next template label or,
    for the last block, by the first ``### Step N`` command header after the
    label — so the closing fence is simply the LAST bare fence in the
    region: nested fences inside template content (e.g. the Bootstrap
    变更纪律 block) always close before it.
    """
    region = text[open_end:region_end]
    fences = list(_FENCE_LINE_RE.finditer(region))
    if not fences:
        raise CanonicalSourceError(
            f"canonical template block `{key}` has no closing fence"
        )
    return open_end + fences[-1].start()


# ── section span + splice ─────────────────────────────────────────────────

#: FIX-439 explicit span terminators. A bootstrap section NEVER crosses the
#: first thematic break (``---``) or the first H1 line after its own start,
#: even when every H2 in between is whitelisted: without them, a boundary
#: set covering the section's own H2 subsections (the DSH agent-instructions
#: dialect carries six) lets the span run past the ``---`` separator and the
#: host's trailing H1 section up to the next non-whitelisted H2, so a splice
#: would DELETE host content (incident-20261006 §4). The canonical templates
#: contain neither a thematic break nor an H1 after their header, so for the
#: in-repo guarded surfaces these terminators are a no-op.
_H1_LINE_RE = re.compile(r"(?m)^# [^\n]*\n")
_HR_LINE_RE = re.compile(r"(?m)^-{3,}[ \t]*\r?$")


def _h2_titles(text: str) -> frozenset[str]:
    return frozenset(line.rstrip("\n").strip() for line in _H2_LINE_RE.findall(text))


def bootstrap_boundary_titles(*section_texts: str) -> frozenset[str]:
    """Union of every H2 title carried by the given (canonical) section texts.

    FIX-439: the ONE boundary caliber both entry writers splice under —
    ``apply_entry_projection`` passes the union over every canonical
    template (a drifted full bootstrap from ANY profile is replaced as one
    section), and the DSH ``write_bootstrap`` passes the rendered
    template's own H2 full set (its six in-section H2 subsections are part
    of the section being replaced, not section boundaries — the no-set call
    left them behind as a stale duplicate, incident-20261006 §3).
    """
    titles: set[str] = set()
    for text in section_texts:
        titles.update(_h2_titles(text))
    return frozenset(titles)


def _match_newlines(section: str, target_text: str) -> str:
    """FIX-440: live again. Pre-FIX-440 this branch could never fire on the
    file path chain — the universal-newline read normalized every \\r\\n
    away before the comparison, so a CRLF host file got its WHOLE content
    re-encoded as LF by the newline="" write. With raw-EOL reads (see
    ``_read_text``) the target's true EOL form reaches the splice: the
    section being written takes the host's own newline form under the same
    whole-text CRLF heuristic ``replace_bootstrap_section`` uses for its
    separator (``nl``) — a single-EOL host stays single-EOL, a mixed file
    converges to the tail's form. Revived rather than removed because the
    separator already commits to that heuristic: removing only this half
    would mint mixed-EOL seams (LF section body + CRLF separators) and
    destabilize the append-path blank-line detection. Downstream faces are
    EOL-insensitive by design (``_norm`` content comparisons; the singleton
    guard's ``\\r?`` line anchor; span regexes tolerate a trailing \\r)."""
    if "\r\n" in target_text and "\r\n" not in section:
        return section.replace("\n", "\r\n")
    return section


def bootstrap_section_span(text: str, boundary_titles: frozenset[str] | None = None):
    """Return the (start, end) char span of the bootstrap section, or None.

    The section starts at the first ``#``/``##`` Governance Bootstrap header
    and ends before the next H2 header whose full title is NOT part of
    ``boundary_titles`` (``None`` → any H2 ends the section; the thin
    pointer uses H3 subsections only, so ``None`` is its natural boundary),
    OR before the first thematic break / H1 line after the section start —
    whichever boundary comes first (see ``_H1_LINE_RE`` / ``_HR_LINE_RE``).
    """
    start_match = _SECTION_START_RE.search(text)
    if start_match is None:
        return None
    cursor = start_match.end()
    hard_end = len(text)
    for terminator in (_HR_LINE_RE, _H1_LINE_RE):
        match = terminator.search(text, cursor)
        if match is not None and match.start() < hard_end:
            hard_end = match.start()
    region = text[cursor:hard_end]
    for line_match in _H2_LINE_RE.finditer(region):
        title = line_match.group(0).strip()
        if boundary_titles is None or title not in boundary_titles:
            return (start_match.start(), cursor + line_match.start())
    return (start_match.start(), hard_end)


def _slice_span(text: str, span) -> str:
    if span is None:
        return ""
    return text[span[0]:span[1]]


def replace_bootstrap_section(
    text: str, new_section: str, boundary_titles: frozenset[str] | None = None
) -> str:
    """Replace (or append) the bootstrap section; idempotent by construction.

    ``boundary_titles`` must cover every H2 title that can legally appear
    INSIDE the section being written — callers pass the union of all
    canonical template H2 titles (see ``apply_entry_projection``) so a
    drifted full bootstrap is replaced as a whole instead of being split at
    its internal H2s.  ``None`` means any H2 ends the section.
    """
    new_section = new_section.rstrip("\n") + "\n"
    new_section = _match_newlines(new_section, text)
    nl = "\r\n" if "\r\n" in text else "\n"
    span = bootstrap_section_span(text, boundary_titles)
    if span is None:
        if not text.strip():
            return new_section
        base = text if text.endswith("\n") else text + "\n"
        if not base.endswith(nl * 2):
            base += nl
        return base + new_section
    before, after = text[:span[0]], text[span[1]:]
    after_body = after.lstrip("\r\n")
    after = nl + after_body if after_body else ""
    return before + new_section + after


def bootstrap_h2_singleton_violations(new_text: str, section_text: str) -> list[str]:
    """FIX-439 fail-closed post-splice guard: H2 singletons or refusal.

    After a splice, every H2 title carried by the section being written
    (``section_text``) must appear in the resulting text EXACTLY once,
    line-anchored. A count above 1 means a stale earlier section would
    survive the splice (the duplication defect — two bootstrap sections
    injected into every session, incident-20261006 §2); a count of 0 means
    the splice dropped part of the section it was supposed to write. Either
    way the caller MUST refuse the write and keep the original file.
    """
    violations: list[str] = []
    for title in sorted(_h2_titles(section_text)):
        pattern = re.compile(r"(?m)^" + re.escape(title) + r"[ \t]*\r?$")
        count = len(pattern.findall(new_text))
        if count != 1:
            violations.append(
                f"H2 heading appears {count}x, expected exactly 1: "
                f"{title!r}")
    return violations


def has_full_bootstrap(section_text: str) -> bool:
    return _FULL_BOOTSTRAP_MARKER in section_text


def is_thin_pointer_section(section_text: str) -> bool:
    return _THIN_BOOTSTRAP_MARKER in section_text


# ── thin pointer rendering + validation ───────────────────────────────────

def render_thin_pointer(thin_template: str, primary_entry: str) -> str:
    return thin_template.replace(_PLACEHOLDER, primary_entry)


def validate_dsh_thin_pointer(section_text: str) -> list[str]:
    """FEAT-037 P3-6 / FEAT-040: guard the DSH thin-pointer dialect.

    Mutual recognition instead of byte-equality (see
    ``THIN_SHARED_CORE_ANCHORS``): the dialect must carry the shared survival
    core plus its own extras, and it must publish the FEAT-040 gray-release
    switch. Returns the issue list (empty == valid).
    """
    issues: list[str] = []
    for anchor_label, needle in THIN_SHARED_CORE_ANCHORS + THIN_DIALECT_DSH_ANCHORS:
        if needle not in section_text:
            issues.append(f"dsh thin pointer missing anchor: {anchor_label}")
    for needle in DSH_THIN_REQUIRED_EXTRA:
        if needle not in section_text:
            issues.append(
                f"dsh thin pointer missing required marker: {needle!r} "
                f"(FEAT-040 gray-release switch)")
    return issues


def check_dsh_thin_pointer(source_root: Path) -> dict:
    """Read-only result for the DSH dialect surface (fail-closed when absent)."""
    path = Path(source_root) / DSH_THIN_TEMPLATE
    if not path.is_file():
        return {
            "path": DSH_THIN_TEMPLATE,
            "state": "missing",
            "bytes": 0,
            "lines": 0,
            "issues": [f"{DSH_THIN_TEMPLATE}: DSH thin-pointer template missing"],
        }
    text = path.read_text(encoding="utf-8")
    return {
        "path": DSH_THIN_TEMPLATE,
        "state": "present",
        "bytes": len(text.encode("utf-8")),
        "lines": len(text.splitlines()),
        "issues": [f"{DSH_THIN_TEMPLATE}: {issue}"
                   for issue in validate_dsh_thin_pointer(text)],
    }


def validate_thin_pointer(section_text: str, primary_entry: str) -> list[str]:
    issues: list[str] = []
    line_count = len(section_text.splitlines())
    byte_count = len(section_text.encode("utf-8"))
    if line_count > THIN_MAX_LINES:
        issues.append(f"thin pointer exceeds {THIN_MAX_LINES} lines: {line_count}")
    if byte_count > THIN_MAX_BYTES:
        issues.append(f"thin pointer exceeds {THIN_MAX_BYTES} bytes: {byte_count}")
    for anchor_label, needle in _THIN_REQUIRED_ANCHORS:
        if needle not in section_text:
            issues.append(f"thin pointer missing anchor: {anchor_label}")
    if primary_entry not in section_text:
        issues.append(f"thin pointer missing primary pointer: {primary_entry}")
    if _PLACEHOLDER in section_text:
        issues.append(f"thin pointer carries unrendered placeholder: {_PLACEHOLDER}")
    return issues


# ── plan / apply / report ─────────────────────────────────────────────────

def _read_text(path: Path) -> str:
    # FIX-440 (review-FIX-439-CODE-R0 F-1): read with newline translation
    # DISABLED so a CRLF entry file keeps its \r\n through the splice. The
    # default universal-newline read collapses every \r\n to \n, and the
    # newline="" write then re-encodes the WHOLE file as LF — flipping the
    # EOL of every non-bootstrap byte (the byte-preservation promise
    # broken). Path.read_text has no newline parameter before Python 3.13,
    # hence the explicit open().
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _entry_sections(templates: dict[str, str], profile: str, primary: str) -> dict[str, str]:
    if profile not in FULL_PROFILE_KEYS:
        raise CanonicalSourceError(f"unknown profile: {profile}")
    return {
        "full": templates[profile],
        "thin": render_thin_pointer(templates["secondary-thin"], primary),
    }


def plan_entry_writes(
    project_root: Path,
    *,
    profile: str = "standard",
    primary: str = PRIMARY_DEFAULT,
    source_root: Path | None = None,
) -> list[EntryWrite]:
    """Decide what each entry file's bootstrap section must be.

    * primary present → primary full (+ secondary thin when present);
    * only secondary present → secondary full, UNLESS it already carries a
      valid thin pointer (sticky: never flip a committed dedup projection
      back to full just because the gitignored primary is absent locally);
    * no entry file → nothing (governance-init owns first-time creation).
    """
    root = Path(project_root)
    src = Path(source_root) if source_root else root
    templates = load_canonical_templates(src)
    sections = _entry_sections(templates, profile, primary)
    secondary = SECONDARY_OF[primary]
    primary_path, secondary_path = root / primary, root / secondary
    plan: list[EntryWrite] = []

    if primary_path.exists():
        plan.append(EntryWrite(
            primary, "full", sections["full"],
            "primary entry carries the canonical full bootstrap",
        ))
        if secondary_path.exists():
            plan.append(EntryWrite(
                secondary, "thin", sections["thin"],
                "secondary entry thin pointer (FEAT-037 dual-presence dedup)",
            ))
        return plan

    if secondary_path.exists():
        existing = _read_text(secondary_path)
        span = bootstrap_section_span(existing)
        current = _section_content(existing, span)
        if span is not None and is_thin_pointer_section(current) and \
                not validate_thin_pointer(current, primary):
            return []  # sticky thin pointer; nothing to do
        plan.append(EntryWrite(
            secondary, "full", sections["full"],
            "single-entry workspace: full bootstrap (backward compatible)",
        ))
    return plan


def _normalized_content(section: str) -> str:
    """One canonical measurement caliber for a bootstrap section body.

    The splice separator blank line between the section end and the following
    H2 belongs to the span, not to the section content — measure and compare
    the content without trailing newlines or CRLF variance.
    """
    return _norm(section).rstrip("\n")


def _section_content(text: str, span) -> str:
    """The section body in the ONE canonical caliber.

    FEAT-037 P3-2 (closed by FEAT-040): the sticky check and the drift report
    measured the same span two ways — the sticky arm compared the RAW span
    (whose tail carries the splice separator blank line, +1 line) while the
    report compared the rstripped content. On a thin pointer sitting exactly on
    the 40-line / 3072-byte line the sticky arm was strictly harsher and could
    flip a committed dedup projection back to the full template, i.e. double the
    session injection cost it exists to prevent. Both arms now come through
    here, so the two calibers cannot diverge again.
    """
    return _normalized_content(_slice_span(text, span))


def apply_entry_projection(
    project_root: Path,
    *,
    source_root: Path | None = None,
    profile: str = "standard",
    primary: str = PRIMARY_DEFAULT,
    dry_run: bool = False,
) -> dict:
    root = Path(project_root)
    src = Path(source_root) if source_root else root
    templates = load_canonical_templates(src)
    # Splice boundary = union of every canonical template's H2 titles: a
    # drifted full bootstrap (whatever profile it came from) is replaced as
    # ONE section, and foreign trailing H2 sections (e.g. 项目质量原则)
    # survive outside the span. FIX-439: the same boundary caliber the DSH
    # write_bootstrap uses (bootstrap_boundary_titles), plus the explicit
    # `---`/H1 span terminators — one shared splice implementation.
    boundary = bootstrap_boundary_titles(
        *(templates[key] for key in (*FULL_PROFILE_KEYS, "secondary-thin"))
    )
    plan = plan_entry_writes(
        root, profile=profile, primary=primary, source_root=src
    )
    applied, unchanged = [], []
    for write in plan:
        path = root / write.relative_path
        old_text = _read_text(path) if path.exists() else ""
        new_text = replace_bootstrap_section(old_text, write.section_text, boundary)
        # FIX-439 fail-closed splice guard: every H2 of the section being
        # written must land in the file exactly once — a duplicate means a
        # stale section would survive the splice; refuse and keep the file.
        violations = bootstrap_h2_singleton_violations(
            new_text, write.section_text)
        if violations:
            raise BootstrapSpliceError(
                f"bootstrap splice guard refused to write "
                f"{write.relative_path} (original kept): "
                + "; ".join(violations)
            )
        if new_text == old_text:
            unchanged.append(write.relative_path)
            continue
        applied.append(write.relative_path)
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_text, encoding="utf-8", newline="")
    return {
        "applied": applied,
        "unchanged": unchanged,
        "dry_run": dry_run,
        "bytes": {
            w.relative_path: len(w.section_text.encode("utf-8")) for w in plan
        },
    }


def _classify_entry(text: str, boundary_titles: frozenset[str]) -> tuple[str, str]:
    """Return (kind, section) where kind ∈ {full, thin, none, unknown}."""
    span = bootstrap_section_span(text, boundary_titles)
    section = _slice_span(text, span)
    if span is None:
        return "none", ""
    if has_full_bootstrap(section):
        return "full", section
    span = bootstrap_section_span(text)
    section = _slice_span(text, span)
    if is_thin_pointer_section(section):
        return "thin", section
    return "unknown", section


def build_sync_report(
    project_root: Path,
    *,
    source_root: Path | None = None,
    profile: str = "standard",
    primary: str = PRIMARY_DEFAULT,
) -> dict:
    """Read-only drift guard: every bootstrap section must be exactly the
    canonical full template (primary) or the rendered thin pointer
    (secondary); a dual-full workspace is a dedup violation."""
    root = Path(project_root)
    src = Path(source_root) if source_root else root
    templates = load_canonical_templates(src)
    sections = _entry_sections(templates, profile, primary)
    secondary = SECONDARY_OF[primary]
    issues: list[str] = []
    entries: list[dict] = []
    kinds: dict[str, str] = {}

    for name, expected_kind in ((primary, "full"), (secondary, "thin")):
        path = root / name
        if not path.exists():
            entries.append({"file": name, "state": "absent", "bytes": 0})
            continue
        kind, section = _classify_entry(_read_text(path), _h2_titles(templates[profile]))
        kinds[name] = kind
        content = _normalized_content(section)
        entry = {
            "file": name,
            "state": "present",
            "kind": kind,
            "bytes": len(content.encode("utf-8")),
            "lines": len(content.splitlines()),
        }
        if kind == "none":
            issues.append(f"entry bootstrap section missing: {name}")
        elif kind == "unknown":
            issues.append(
                f"entry bootstrap section is neither canonical full nor thin pointer: {name}"
            )
        elif kind != expected_kind:
            issues.append(
                f"entry bootstrap role mismatch: {name} carries `{kind}`, expected `{expected_kind}`"
            )
        elif content != _norm(sections[expected_kind]).rstrip("\n"):
            issues.append(f"bootstrap drift ({expected_kind}): {name}")
        if kind == "thin" and expected_kind == "thin":
            issues.extend(
                f"{name}: {issue}" for issue in validate_thin_pointer(content, primary)
            )
        entries.append(entry)

    if kinds.get(primary) == "full" and kinds.get(secondary) == "full":
        issues.append(
            "dual-full bootstrap detected (FEAT-037 dedup violation): "
            f"{primary} and {secondary} both carry the full template"
        )
    if primary in kinds and secondary in kinds and \
            "full" not in kinds.values() and len(kinds) == 2:
        issues.append("no entry carries the canonical full bootstrap")

    return {
        "pass": not issues,
        "issues": issues,
        "primary": primary,
        "secondary": secondary,
        "profile": profile,
        "entries": entries,
        "total_section_bytes": sum(entry["bytes"] for entry in entries),
    }


def _norm(text: str) -> str:
    return text.replace("\r\n", "\n")


# ── CLI ───────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "FEAT-037 entry bootstrap projection: generate AGENTS.md/CLAUDE.md "
            "bootstrap sections from the canonical governance-init.md Step 7 "
            "templates (read-only check by default)."
        )
    )
    parser.add_argument("--project", default=".", help="workspace root to guard")
    parser.add_argument(
        "--source-root",
        default=None,
        help="plugin repository root carrying commands/governance-init.md "
        "(defaults to --project)",
    )
    parser.add_argument(
        "--profile", default="standard", choices=FULL_PROFILE_KEYS
    )
    parser.add_argument(
        "--primary", default=PRIMARY_DEFAULT, choices=tuple(SECONDARY_OF)
    )
    parser.add_argument(
        "--write", action="store_true", help="apply the projection (default: check only)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="plan the writes without touching the filesystem",
    )
    args = parser.parse_args(argv)

    project_root = Path(args.project).resolve()
    source_root = Path(args.source_root).resolve() if args.source_root else project_root
    try:
        if args.write or args.dry_run:
            result = apply_entry_projection(
                project_root,
                source_root=source_root,
                profile=args.profile,
                primary=args.primary,
                dry_run=args.dry_run,
            )
            for name in result["applied"]:
                verb = "would write" if args.dry_run else "wrote"
                print(f"[{verb.upper()}] {name} bootstrap section "
                      f"({result['bytes'][name]} bytes)")
            for name in result["unchanged"]:
                print(f"[SKIP] {name} already synchronized")
        report = build_sync_report(
            project_root,
            source_root=source_root,
            profile=args.profile,
            primary=args.primary,
        )
    except CanonicalSourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    for entry in report["entries"]:
        state = entry.get("kind", entry["state"])
        print(f"[ENTRY] {entry['file']}: {state} "
              f"({entry['bytes']} bytes, {entry.get('lines', 0)} lines)")
    if report["issues"]:
        for issue in report["issues"]:
            print(f"[FAIL] {issue}")
        return 1
    print("[PASS] entry bootstrap sections synchronized with the canonical source")
    return 0


if __name__ == "__main__":
    sys.exit(main())
