"""Persist independently observed review records and bind scoped reviews to native work units.

The review-record CLI delegates transactions to this module. Only a named
unit's bound native review can authorize its gate, via loop_workflow.gate_review.
Independent observations still receive a durable review record.
  - **复审必达**: a NEEDS_CHANGE record carries the structured revisit fields
    ``next_round=REVIEW-{id}-R{n+1}`` + ``prev_report`` so Check 30 V6 and the
    Coordinator can verify / spawn the R+1 revisit.
  - **覆盖守卫 (FIX-289⑤ / FIX-314 three-key extension)**: a review file is
    an immutable task+round+reviewer record (key extended from task+round by
    FIX-314 so the two halves of one review round never collide — REL-076
    M-3 dual-half defect). The FIRST reviewer of a round owns the canonical
    ``review-{task}-R{n}.md`` name — legacy single-reviewer files included:
    a file without a matching owner is never rewritten, only namespaced
    around. A DIFFERENT reviewer for the same task+round lands in
    ``review-{task}-R{n}-{reviewer-slug}.md`` with the mirrored evidence id
    ``REVIEW-{task}-R{n}-{SLUG}`` (the ``REVIEW-{task}-R{n}`` canonical
    prefix stays intact for the Check 30/30c live row scans and the
    commit-msg evidence gate). Writing over a reviewer's OWN existing file
    is rejected (error dict, nothing written — no overwrite, no evidence
    row) unless ``force=True``:
    the deliberate overwrite then backs up the previous record
    (``review-{id}-R{n}.pre-<ts>.md``), marks the overwrite in the new record,
    and reports the backup in the summary (REL-073 same-number overwrite
    near-miss; historical backfill / migrated data must never be silently
    replaced).
  - **审查结论必机录 (FIX-260 / REQ-107)**: calling this CLI is a MUST for
    every Reviewer conclusion (behavior-protocol.md M7.4 step 4.6 C8; the
    M1.2 fast lane no longer exempts handwritten REVIEW rows). Check 30c
    (``check_review_machine_provenance``) WARNs on REVIEW rows/files dated
    on/after 2026-08-22 that lack the machine markers emitted here — the
    gradual-FAIL escalation path is registered in the FIX-260 decision log.

FEAT-094 — 审查可信链 (five-step indivisible review transaction):

  提交报告 → 验证结构与修订 → 登记发现 → 自动生成后续义务 → 更新状态.
  The RPG long-haul session measured the three trust failures this closes
  (report §3.5): REV-009 reviewed a phantom revision (untracked +
  concurrently rewritten object); REV-001/002 declared R2 obligations in
  machine records that then evaporated; REV-009-R2's machine record said
  APPROVED while the report's own text said NEEDS_CHANGE.

  ① **Immutable snapshot binding** — every record pins the reviewed
  object: the report's byte sha256, the HEAD commit sha, a worktree
  cleanliness disclosure and optional per-file ``git hash-object`` blob
  pins (untracked-safe — a rewrite after the record is detectable via
  :func:`verify_review_trust`).
  ② **R2 obligations live in the authority ledger** — a NEEDS_CHANGE
  record registers its ``RECHECK-{task}-R{n+1}`` obligation in the SAME
  ledger ``transact`` batch as the ``review_recorded`` event (atomic;
  evaporation structurally impossible — the append-only log never drops
  events) and the key is unique (duplicate open registrations refused at
  the writer).  The ONLY discharger is the discharging round's own review
  transaction (or an explicit manual ``recheck_obligation_cleared`` event).
  ③ **CONFLICT, never the optimistic winner** — when the report clearly
  carries verdict token(s) and the claimed result disagrees, the write is
  REFUSED with a manual-resolution disposition (nothing written).
  Supervisor escalation states (BLOCKED — the T2 round≥3 escalation;
  ABORTED / UNKNOWN — agent death) are exempt: an escalation RECORDING a
  harsher state than the report is the designed trigger semantics, not an
  inconsistency.
  ⑤ **Agent death** — the supervisor records ABORTED / UNKNOWN terminal
  records (``--result ABORTED|UNKNOWN`` + ``--abort-reason``); death does
  NOT discharge an open recheck obligation (the round still owes a real
  verdict).

  Ordering (anti-evaporation): the ledger transaction commits FIRST
  (atomic review+obligation batch), then the review file and evidence row
  land; a failure between them is compensated (a file this transaction
  created is unlinked) and disclosed — never silently half-committed.  A
  ledger refusal (integrity broken / contract refused) refuses the whole
  transaction: no file, no row (异常不隐藏).

  复审必达触发器语义 UNCHANGED (non_goal): T1/T2, round+1, prev_report
  injection keep their exact semantics — the ``next_round`` /
  ``prev_report`` fields and summary keys are byte-compatible with the
  pre-FEAT-094 writer; this ticket only ADDS trust binding around them.

The review ledger stores the observation. The native loop checks its
binding before applying a scoped decision.
"""

import json
import hashlib
import os
import re
import subprocess
from datetime import date, datetime
from pathlib import Path

_TASK_ID_RE = re.compile(r"^[A-Z]+-\d+$")
# FEAT-094: ABORTED/UNKNOWN = supervisor-recorded agent-death terminal
# states (never trigger a revisit, never discharge an open obligation).
_RESULT_RE = re.compile(
    r"^(APPROVED|APPROVED_WITH_NOTES|NEEDS_CHANGE|BLOCKED|ABORTED|UNKNOWN)$",
    re.IGNORECASE)
# FEAT-094 ③: verdict tokens a report may clearly carry (bold span or
# 审查结论-line); free-form reports without either shape are NOT
# conflict-judged (the byte-hash pin still applies).
_VERDICT_BOLD_RE = re.compile(
    r"\*\*(APPROVED_WITH_NOTES|APPROVED|NEEDS_CHANGE|BLOCKED)\*\*")
_VERDICT_LINE_RE = re.compile(
    r"审查结论[：:]\s*\**\s*"
    r"(APPROVED_WITH_NOTES|APPROVED|NEEDS_CHANGE|BLOCKED)")
# A source report can quote fields from another round. Only independent
# declarations outside Markdown examples contradict the requested pass.
_REPORT_LIST_MARKER = r"(?:[-+*]|[0-9]{1,9}[.)])[ \t]+"
_REPORT_EXAMPLES_RE = re.compile(
    r"^ {0,3}<!--[\s\S]*?(?:-->|\Z)|"
    rf"^ {{0,3}}(?P<item>{_REPORT_LIST_MARKER})?"
    r"(?P<fence>(?P<mark>[`~])(?P=mark){2,})[^\n]*\n"
    r"[\s\S]*?(?:^(?(item)[ \t]*| {0,3})(?P=fence)(?P=mark)*[ \t]*\r?$|\Z)", re.MULTILINE)
_SOURCE_BLOCKER_FIELD_RE = re.compile(
    rf"^ {{0,3}}(?:{_REPORT_LIST_MARKER})?(?P<cell>\|[ \t]*)?"
    r"(?P<key>unresolved_block(?:er)?s)(?:[ \t]*[=:：][ \t]*(?P<value>[^|\r\n]*))?"
    r"[ \t]*(?(cell)\|[ \t]*)\r?$", re.MULTILINE | re.IGNORECASE)
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_OID = r"(?:[0-9a-f]{40}|[0-9a-f]{64})"
# FEAT-094 ③: conflict-check exemptions — BLOCKED is the T2 round≥3
# escalation verdict (recording ABOVE the report's NEEDS_CHANGE is
# designed trigger semantics); ABORTED/UNKNOWN are supervisor facts about
# the agent. No optimistic uplift is possible through this set.
_CONFLICT_EXEMPT_RESULTS = frozenset(("BLOCKED", "ABORTED", "UNKNOWN"))
# FEAT-094: results that DISCHARGE an open recheck obligation for their
# own round (agent death deliberately does not discharge the owed recheck).
_OBLIGATION_DISCHARGING_RESULTS = frozenset(
    ("APPROVED", "APPROVED_WITH_NOTES", "NEEDS_CHANGE", "BLOCKED"))
# FEAT-094 grep anchors: the pinned-field line shapes emitted into the
# review record (accessibility budget — no implicit knowledge needed).
_REPORT_SHA_FIELD_RE = re.compile(
    r"^- report_sha256: ([0-9a-f]{64})\s*$", re.MULTILINE)
_COMMIT_FIELD_RE = re.compile(
    rf"^- snapshot_commit: ({_GIT_OID}|git:unavailable)\s*$", re.MULTILINE)
_TREE_FIELD_RE = re.compile(rf"^- snapshot_tree: ({_GIT_OID})\s*$", re.MULTILINE)
_BIND_FIELD_RE = re.compile(
    rf"^- snapshot_bind: (.+)=({_GIT_OID})\s*$", re.MULTILINE)
_MODE_FIELD_RE = re.compile(r"^- snapshot_mode: (.+)=([0-7]{6})\s*$", re.MULTILINE)
_REPORT_FIELD_RE = re.compile(
    r"^- report: (.+?)\s*$", re.MULTILINE)

# FIX-314: the reviewer name namespaces the record key (task, round,
# reviewer). The slug is deliberately ASCII-only (cross-platform filename
# safety); a name that normalizes to nothing fails closed at the caller.
_REVIEWER_SLUG_RE = re.compile(r"[^a-z0-9]+")

# FIX-314: the ``- reviewer:`` field line of an existing record — the owner
# probe that decides whether an incoming record matches the canonical slot
# or must be namespaced beside it.
_RECORD_REVIEWER_RE = re.compile(
    r"^[-*][ \t]*reviewer:[ \t]*(.+?)[ \t]*$", re.MULTILINE | re.IGNORECASE)


def _reviewer_slug(reviewer):
    """Normalize a reviewer name into a filename-safe slug (FIX-314).

    Lower-case ASCII alnum runs joined by single dashes, e.g.
    ``"Code Reviewer"`` → ``"code-reviewer"``. Returns ``""`` when nothing
    survives (the caller fails closed — a reviewer that cannot name a file
    must never silently collapse into another reviewer's slot).
    """
    return _REVIEWER_SLUG_RE.sub("-", str(reviewer or "").lower()).strip("-")


def _read_record_reviewer(review_file):
    """Return the ``- reviewer:`` owner of an existing record (FIX-314).

    ``None`` when the field is absent (pre-FIX-314 single-reviewer
    convention / handwritten record) — an unnamed owner is never treated as
    a match, so the incoming reviewer is namespaced beside the legacy file
    instead of claiming it. Read errors propagate: the caller fails closed
    rather than guessing the owner of an unreadable record.
    """
    text = review_file.read_text(encoding="utf-8")
    m = _RECORD_REVIEWER_RE.search(text)
    return m.group(1).strip() if m else None




def _resolve_report_face(report_path, root=None):
    """Locate + read the reviewer's report for trust pinning.

    Absolute paths and cwd-relative paths resolve as-is; a repo-relative
    spelling is additionally tried against ``root`` (the CLI's host-project
    face records paths like ``docs/reviews/...`` while running from the
    repo root). Returns ``(path, data_bytes, text)`` or ``None`` when the
    report cannot be read (fail-closed at the caller — no report, no
    binding, no record).
    """
    report = Path(str(report_path).replace("\\", "/"))
    candidates = [report]
    if root is not None and not report.is_absolute():
        candidates.insert(0, Path(root) / report)
    for candidate in candidates:
        if candidate.is_file():
            try:
                data = candidate.read_bytes()
            except OSError:
                return None
            # Verdict-token scanning is ASCII-anchored — a tolerant decode
            # keeps a non-UTF-8 report scannable while the byte hash (the
            # actual pin) stays encoding-independent.
            return candidate, data, data.decode("utf-8", errors="replace")
    return None


def _report_verdict_tokens(text):
    """Distinct verdict tokens the report clearly carries (FEAT-094 ③)."""
    tokens = set(_VERDICT_BOLD_RE.findall(text or ""))
    tokens.update(_VERDICT_LINE_RE.findall(text or ""))
    return tokens


def _conflicting_blocker_fields(text):
    """Check standalone fields, list items and single-cell report rows.

    Human-authored Markdown also uses colon-delimited metadata. Normalize
    that spelling before applying the same count rules as the machine record.
    """
    from checks.review_domain import _parse_unresolved_blockers_fields

    prose = _REPORT_EXAMPLES_RE.sub("\n", text.lstrip("\ufeff"))
    prose = re.sub(r"(\*\*|__|`)([^\n]+?)\1", r"\2", prose)
    fields = [f"{match['key']}={match['value'] or ''}"
              for match in _SOURCE_BLOCKER_FIELD_RE.finditer(prose)]
    if not fields:
        return []  # Older free-form reports can omit the structured field.
    try:
        facts = _parse_unresolved_blockers_fields(fields)
    except ValueError:  # Python limits conversion of arbitrarily long decimal counts.
        return fields
    if (facts["status"] in ("valid", "missing") and facts["value"] in (0, None)
            and not any(facts["legacy_values"]) and not facts["legacy_invalid_tokens"]):
        return []
    return fields


def _git_output(repo_root, *argv, input_bytes=None):
    """One argv-list git invocation → stripped stdout, or None (git
    unavailable / non-repo / failure — disclosed, never faked). Zero
    shell, zero network; same posture as governance_store's git_object
    reference check."""
    try:
        proc = subprocess.run(
            ["git", "--no-optional-locks", "-C", str(repo_root), *argv],
            capture_output=True, timeout=30, input=input_bytes)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    text = proc.stdout.decode("utf-8", errors="replace")
    return text if "\0" in text else text.strip()


def _file_binding(root, spec):
    """Pin working bytes using Git clean filters and Git's recorded file types."""
    from delivery_acceptance import _plain_stat
    root = Path(root).resolve()
    path = root / spec
    try:
        relative = path.relative_to(root)
        if not relative.parts or ".." in relative.parts:
            raise ValueError("outside review root")
        spec = relative.as_posix()
        parent = path.parent
        while parent != root:
            if parent.exists() or parent.is_symlink():
                _plain_stat(parent)
            parent = parent.parent
    except (OSError, ValueError):
        return {"path": spec, "hash": "unavailable"}
    literal = ":(literal)" + spec
    staged = _git_output(root, "ls-files", "--stage", "--", literal)
    entry = staged.partition("\t")[0].split() if staged and "\n" not in staged else []
    mode = entry[0] if len(entry) == 3 and entry[2] == "0" else None
    if path.is_symlink():
        target = os.fsencode(os.readlink(path))
        blob = _git_output(root, "hash-object", "--stdin", input_bytes=target)
        return {"path": spec, "hash": blob or "unavailable", "mode": "120000"}
    if mode == "160000" and (path / ".git").exists():
        try:
            _plain_stat(path)
        except (OSError, ValueError):
            return {"path": spec, "hash": "unavailable"}
        blob = _git_output(path, "rev-parse", "HEAD")
        if blob:
            return {"path": spec, "hash": blob, "mode": mode}
    if staged == "" and not path.exists() and not path.is_symlink():
        previous = _git_output(root, "rev-parse", "--verify", "HEAD:" + spec)
        if previous and re.fullmatch(_GIT_OID, previous):
            return {"path": spec, "hash": "0" * len(previous), "mode": "000000"}
    blob = _git_output(root, "hash-object", "--", spec)
    if not blob or not re.fullmatch(_GIT_OID, blob):
        return {"path": spec, "hash": "unavailable"}
    if path.is_file():
        if mode == "120000" and entry[1] == blob and _git_output(root, "config", "--bool", "core.symlinks") == "false":
            return {"path": spec, "hash": blob, "mode": mode}
        if _git_output(root, "config", "--bool", "core.filemode") == "true":
            mode = "100755" if path.stat().st_mode & 0o100 else "100644"
        elif mode not in ("100644", "100755"):
            mode = "100644"
    return {"path": spec, "hash": blob, "mode": mode}


def derive_review_facts(root, task, review_ids, *, base=None, commit=None):
    from review_facts import derive_review_facts as derive
    return derive(root, task, review_ids, base=base, commit=commit)


def _bound_tree_entries(root, tree, paths):
    """Read the exact Git modes and object IDs for the requested literal paths."""
    listing = _git_output(root, "--literal-pathspecs", "ls-tree", "-r", "-z", "--full-tree",
                          tree, "--", *paths)
    if listing is None:
        raise ValueError("Git could not verify file bindings against " + tree)
    entries = {}
    for record in listing.split("\0"):
        if record:
            header, path = record.split("\t", 1)
            if path in paths:
                mode, _, oid = header.split()
                entries[path] = (oid, mode)
    return entries


def _entry_spelling(root, relative, directories):
    """Use names from the actual directory entries, preserving links as names."""
    from delivery_acceptance import _plain_stat

    parent = root
    for index, part in enumerate(relative.parts):
        try:
            _plain_stat(parent)
            key = str(parent)  # Path equality can fold case in a case-sensitive NTFS directory.
            if key not in directories:
                directories[key] = set(os.listdir(parent))
            names = directories[key]
            if part not in names:
                info = (parent / part).lstat()
                matches = [name for name in names if name.casefold() == part.casefold()
                           and os.path.samestat(info, (parent / name).lstat())]
                if len(matches) != 1:
                    raise ValueError(f"could not identify directory entry {parent / part}")
                part = matches[0]
        except (FileNotFoundError, NotADirectoryError):
            missing = parent.joinpath(*relative.parts[index:])
            return missing.relative_to(root).as_posix(), False
        except OSError as exc:
            raise ValueError(f"could not read directory entry {parent / part}: {exc}") from exc
        parent /= part
    return parent.relative_to(root).as_posix(), True


def _git_binding_names(root, spelling, treeish):
    history = ["--with-tree=" + treeish] if treeish else []
    pathspec = ":(icase,literal)" + spelling
    if not spelling.isascii():
        # Git's icase matches ASCII. Match non-ASCII runs within their component
        # and let the actual directory entries distinguish possible spellings.
        escaped = re.sub(r"([*?\[\\])", r"\\\1", spelling)
        pathspec = ":(icase,glob)" + re.sub(r"[^\x00-\x7f]+", "*", escaped)
    listing = _git_output(root, "ls-files", "-z", *history, "--", pathspec)
    if listing is None:
        raise ValueError("Git could not read binding names for " + spelling)
    return {name for name in listing.split("\0") if name and name.casefold() == spelling.casefold()}


def _binding_owner(root, spelling, exists, directories, reviewed_tree, commit):
    """Resolve the candidate (or index) first, then a path removed since the captured commit."""
    found_names = False
    sources = [reviewed_tree]  # None selects the index for file-only reviews.
    if commit:
        sources.append(commit)
    for source in sources:
        names = _git_binding_names(root, spelling, source)
        # --with-tree returns names from both the index and this Git object.
        # Only the object's own entries establish its ownership.
        entries = _bound_tree_entries(root, source, names) if source and names else dict.fromkeys(names)
        found_names = found_names or bool(entries)
        aliases = [name for name in entries if name == spelling or
                   _entry_spelling(root, Path(name), directories)[0] == spelling]
        if len(aliases) > 1:
            raise ValueError("multiple Git paths resolve to the same directory entry: " + spelling)
        if aliases:
            name = aliases[0]
            expected = None
            if reviewed_tree:
                expected = entries[name] if source == reviewed_tree else ("0" * len(reviewed_tree), "000000")
            return name, expected
    if not exists and found_names:
        raise ValueError("missing file; use its exact Git path to bind a deletion: " + spelling)
    return spelling, None


def _canonical_bindings(root, bind_files, reviewed_tree, commit, in_repo):
    directories = {}
    owners = {}
    specs = {}
    for raw in bind_files or ():
        path = root / str(raw).replace("\\", "/")
        if not path.is_relative_to(root):
            specs[path.as_posix()] = None
            continue
        relative = path.relative_to(root)
        if not in_repo or not relative.parts or ".." in relative.parts:
            specs[relative.as_posix()] = None
            continue
        spelling, exists = _entry_spelling(root, relative, directories)
        if spelling not in owners:
            owners[spelling] = _binding_owner(root, spelling, exists, directories, reviewed_tree, commit)
        name, expected = owners[spelling]
        specs[name] = expected
    pins = []
    for name, expected in specs.items():
        pin = _file_binding(root, name)
        if expected is not None and (pin["hash"], pin.get("mode")) != expected:
            raise ValueError("file pin disagrees with reviewed tree at " + name)
        pins.append(pin)
    return pins


def snapshot_binding(repo_root, bind_files=()):
    """FEAT-094 ① — the immutable snapshot of the reviewed object.

    ``git rev-parse HEAD`` (the commit being reviewed) + a
    ``git status --porcelain`` worktree disclosure + one
    ``git hash-object`` blob pin per ``bind_files`` path (content hash
    that stays meaningful for UNTRACKED files — the REV-009 phantom
    revision anchored untracked bytes that were rewritten underneath the
    review). git unavailable / not a repo → disclosed markers
    (``git:unavailable`` / ``unavailable``), never a fabricated hash.
    """
    return _snapshot_binding(repo_root, bind_files, None)


def _snapshot_binding(repo_root, bind_files, reviewed_tree):
    root = Path(repo_root).resolve() if repo_root is not None else Path.cwd()
    commit = _git_output(root, "rev-parse", "HEAD")
    unborn = False
    if not commit:
        status_header = _git_output(root, "status", "--porcelain=v2", "--branch", "--untracked-files=no")
        unborn = "# branch.oid (initial)" in (status_header or "").splitlines()
    status = _git_output(root, "status", "--porcelain")
    worktree = "unavailable" if status is None else (
        "clean" if not status else "dirty({0})".format(
            len([ln for ln in status.splitlines() if ln.strip()])))
    in_repo = reviewed_tree is not None or commit is not None or unborn or status is not None
    if bind_files and in_repo and not commit and not unborn:
        raise ValueError("Git could not identify the review's base commit")
    return {
        "commit": commit if commit and re.fullmatch(_GIT_OID, commit)
        else ("git:unborn" if unborn else "git:unavailable"),
        "commit_status": "resolved" if commit and re.fullmatch(_GIT_OID, commit)
        else ("unborn" if unborn else "unavailable"),
        "worktree": worktree,
        "bindings": _canonical_bindings(root, bind_files, reviewed_tree, commit, in_repo),
    }


def _pin_check(checks, kind, pinned, current, note=""):
    """Append one standardized pin-check record (single literal site)."""
    state = "unverified" if current is None else (
        "match" if current == pinned else "mismatch")
    record = {"check": kind, "pinned": pinned, "state": state}
    if current is not None:
        record["current"] = current
    if note:
        record["detail"] = note
    checks.append(record)
    return state


class PublishedReviewObjects:
    """Git-confirmed object types for one repository during one receipt scan."""

    def __init__(self, root, receipts):
        self.root = Path(root).resolve()
        self._types = {}
        queries = {}
        for receipt in receipts:
            for key in ("commit", "tree"):
                oid = receipt.get(key)
                if isinstance(oid, str) and re.fullmatch(_GIT_OID, oid):
                    # Preserve rev-parse's commit peeling and verification.
                    query = oid + "^{commit}" if key == "commit" else oid
                    queries[query] = (oid, key)
        if not queries:
            return
        output = _git_output(self.root, "cat-file", "--batch-check=%(objectname) %(objecttype)",
                             input_bytes=("\n".join(queries) + "\n").encode("ascii"))
        lines = output.splitlines() if output else []
        if len(lines) != len(queries):
            return
        for (oid, expected), line in zip(queries.values(), lines):
            if line == f"{oid} {expected}":
                self._types[oid] = expected

    def verify(self, review_file, root):
        # Only directly confirmed, matching OIDs take the fast path. Missing
        # objects, tags, abbreviated names and failed/malformed Git responses
        # retain the individual reader's HEAD and type-discrimination checks.
        confirmed = self._types if Path(root).resolve() == self.root else {}
        return _verify_review_trust(review_file, root, current_worktree=False, confirmed=confirmed)


def verify_review_trust(review_file, repo_root=None, *, current_worktree=True):
    """FEAT-094 — re-verify a record's trust pins (tamper detection face).

    Re-reads the pinned report bytes and re-hashes them against the
    record's ``- report_sha256:`` pin; resolves the pinned commit and any
    ``- snapshot_bind:`` blob pins against the repo. Returns a structured
    verdict dict — never raises:

    * ``CLEAN`` — every pin re-verified;
    * ``CONFLICT`` — a pin no longer matches (the report was rewritten
      after the record / the bound file drifted / the commit vanished);
      disposition is MANUAL (re-review or supersede — the record itself is
      immutable, provenance honest);
    * ``UNKNOWN`` — a pin exists but cannot be re-verified now (report
      unreadable / git unavailable);
    * ``UNPINNED`` — a legacy pre-FEAT-094 record (no pins by design;
      deliberately NOT a conflict — assumption_record compatibility).
    """
    return _verify_review_trust(review_file, repo_root, current_worktree=current_worktree, confirmed={})


def _verify_review_trust(review_file, repo_root, *, current_worktree, confirmed):
    face = {
        "review_file": str(review_file),
        "verdict": "UNKNOWN",
        "checks": [],
        "reason": "",
    }
    try:
        text = Path(review_file).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        face["reason"] = "record unreadable: {0}".format(exc)
        return face
    sha_match = _REPORT_SHA_FIELD_RE.search(text)
    if sha_match is None:
        face["verdict"] = "UNPINNED"
        face["reason"] = (
            "legacy record (pre-FEAT-094): no report_sha256 pin — "
            "not conflict-judged by design")
        return face
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    conflict = unknown = False

    # 1. report bytes vs the pinned hash
    current = None
    report_match = _REPORT_FIELD_RE.search(text)
    if report_match is not None:
        report_face = _resolve_report_face(report_match.group(1), repo_root)
        if report_face is not None:
            current = hashlib.sha256(report_face[1]).hexdigest()
    state = _pin_check(
        face["checks"], "report_sha256", sha_match.group(1), current,
        "report bytes changed AFTER the record was written "
        "(phantom-revision family) — MANUAL disposition: re-review the "
        "current object or supersede; never edit the record"
        if current is not None else
        "report unreadable — cannot re-hash")
    conflict |= state == "mismatch"
    unknown |= state == "unverified"

    # 2. pinned commit resolvability (git itself down → UNKNOWN; git up
    # but the commit gone → CONFLICT, the history-rewrite family)
    commit_match = _COMMIT_FIELD_RE.search(text)
    if commit_match is not None and commit_match.group(1) != "git:unavailable":
        oid = commit_match[1]
        resolved = oid if confirmed.get(oid) == "commit" else _git_output(
            root, "rev-parse", "--verify", "--quiet", oid + "^{commit}")
        current = resolved
        if resolved is None and _git_output(root, "rev-parse", "--verify", "--quiet", "HEAD") is not None:
            current = ""
        state = _pin_check(
            face["checks"], "snapshot_commit", commit_match.group(1),
            current,
            "pinned commit no longer resolves — history rewritten? "
            "MANUAL disposition")
        conflict |= state == "mismatch"
        unknown |= state == "unverified"

    tree_match = _TREE_FIELD_RE.search(text)
    if tree_match:
        tree = tree_match[1]
        obj_type = "tree" if confirmed.get(tree) == "tree" else _git_output(root, "cat-file", "-t", tree)
        state = _pin_check(face["checks"], "snapshot_tree", tree,
                           tree if obj_type == "tree" else obj_type)
        conflict |= state == "mismatch"
        unknown |= state == "unverified"

    # 3. per-file blob pins (the untracked-safe bindings)
    modes = dict(_MODE_FIELD_RE.findall(text))
    for bind_match in (_BIND_FIELD_RE.finditer(text) if current_worktree else ()):
        spec, pinned_blob = bind_match.group(1), bind_match.group(2)
        current_bind = _file_binding(root, spec)
        blob = current_bind["hash"]
        if modes.get(spec) == "000000" and _git_output(root, "ls-files", "--stage", "--", ":(literal)" + spec) == "":
            path = root / spec
            if not path.exists() and not path.is_symlink():
                blob = "0" * len(pinned_blob)
                current_bind["mode"] = "000000"
        if blob == "unavailable":
            blob = None
        state = _pin_check(
            face["checks"], "snapshot_bind", pinned_blob, blob,
            "bound file content drifted after the review (REV-009 "
            "phantom-revision family) — MANUAL disposition: re-review")
        face["checks"][-1]["path"] = spec
        conflict |= state == "mismatch"
        unknown |= state == "unverified"
        if spec in modes:
            state = _pin_check(face["checks"], "snapshot_mode", modes[spec], current_bind.get("mode"))
            face["checks"][-1]["path"] = spec
            conflict |= state == "mismatch"
            unknown |= state == "unverified"

    if conflict:
        face["verdict"] = "CONFLICT"
        face["reason"] = (
            "trust pins no longer match — 禁乐观者胜出: the conflicting "
            "half must be re-adjudicated manually (FEAT-094 ③)")
    elif unknown:
        face["verdict"] = "UNKNOWN"
        face["reason"] = "pins present but not fully re-verifiable right now"
    else:
        face["verdict"] = "CLEAN"
        face["reason"] = "all trust pins re-verified"
    return face




def _review_file_text(task_id, round_n, result, reviewer, report_path,
                      date_str, wiring_note, force_note=None,
                      scope="full", delta_base=None, trust_fields=None,
                      abort_reason=None):
    """Machine-written review record markdown (Check 30 file-scan parseable).

    ``force_note`` (FIX-289⑤) is the backup filename when this write is a
    deliberate force overwrite; it emits the ``- force_overwrite:`` marker
    line so the overwrite is traceable from the record itself. The marker is
    inert to the Check 30/30c file parsers (date/conclusion/next_round
    extraction are anchored to their own field lines). ``scope`` /
    ``delta_base`` (FEAT-091) record the review injection face the same
    way — additive field lines, inert to the anchored parsers.
    ``trust_fields`` (FEAT-094) are pre-rendered pin lines
    (``- report_sha256:`` / ``- snapshot_commit:`` / ``- snapshot_worktree:``
    / ``- snapshot_bind:``) and ``abort_reason`` rides the same additive
    field-line convention for supervisor terminal records.
    """
    lines = [
        "# Review Record (machine-written by review-record)",
        "",
        "- task: {0}".format(task_id),
        "- round: R{0}".format(round_n),
        "- date: {0}".format(date_str),
        "- reviewer: {0}".format(reviewer or "unknown"),
        "- report: {0}".format(report_path),
        "- wiring: {0}".format(wiring_note),
        "- scope: {0}".format(scope),
    ]
    if delta_base:
        lines.append("- delta_base: {0}".format(delta_base))
    if trust_fields:
        lines.extend(trust_fields)
    if abort_reason:
        lines.append("- abort_reason: {0}".format(abort_reason))
    if force_note:
        lines.append(
            "- force_overwrite: previous record preserved at {0}".format(
                force_note))
    lines += [
        "",
        "**审查结论**: **{0}**".format(result),
    ]
    if result == "APPROVED_WITH_NOTES":
        lines.append("")
        lines.append("unresolved_blockers=0")
    if result == "NEEDS_CHANGE":
        lines.append("")
        lines.append("## 复审必达（NEEDS_CHANGE）")
        lines.append("")
        lines.append("- next_round: REVIEW-{0}-R{1}".format(task_id, round_n + 1))
        lines.append("- prev_report: {0}".format(report_path))
    lines.append("")
    return "\n".join(lines)


def _evidence_row(task_id, round_n, result, reviewer, report_path,
                  review_file_name, date_str, review_id=None, pins=None, gate_id=None):
    """Evidence-log row in the Check 30 live-scan contract.

    Column shape mirrors existing rows: | id | task_ref | type | description |
    basis | artifacts | actor | date | gate | conclusion [| blocker token].
    The description intentionally carries NO ISO date and NO conclusion token
    so the live collector's first-match scan lands on the real columns.
    ``review_id`` (FIX-314) is the caller-resolved record id — the canonical
    ``REVIEW-{task}-R{n}`` for the round's first reviewer, or the mirrored
    ``REVIEW-{task}-R{n}-{SLUG}`` for a namespaced second reviewer; either
    way the Check 30/30c row scans keep matching its canonical prefix.
    ``pins`` (FEAT-094) appends short grep-able trust pins to the artifacts
    cell (full hashes live in the review record; the row carries the
    12-char identification prefix).
    """
    cells = [
        review_id or "REVIEW-{0}-R{1}".format(task_id, round_n),
        task_id,
        "治理记录",
        "review-record CLI 机器写入 review 结论记录（round {0}）".format(round_n),
        "事实依据：review-record 输出摘要（机器写入）",
        "{0}; {1}".format(report_path, review_file_name),
        reviewer or "unknown",
        date_str,
        gate_id or "—",
        result,
    ]
    if pins:
        cells[5] = "{0}; {1}".format(cells[5], pins)
    if result == "APPROVED_WITH_NOTES":
        cells.append("unresolved_blockers=0")
    return "| " + " | ".join(cells) + " |\n"


def _review_ledger_transaction(evidence_dir, *, task_id, round_n,
                               result_norm, review_id, reviewer,
                               report_path, report_sha256, binding,
                               scope_norm, native_binding=None, observed_loop=None):
    """FEAT-094 steps 3+4 — the ATOMIC ledger core of the review
    transaction: the ``review_recorded`` event and the recheck-obligation
    lifecycle events land in ONE ``transact`` batch (validation atomicity,
    single sequential append — a NEEDS_CHANGE record can never exist
    without its R{n+1} obligation, and an obligation can never be
    double-registered or phantom-cleared; the writer's batch contract
    enforces both).

    Returns ``(ledger_face, obligations_face)``; raises
    ``authority_ledger.LedgerError`` on refusal (caller converts to the
    structured error dict — the whole five-step transaction is refused,
    nothing written).
    """
    from authority_ledger import LedgerWriter, obligation_key
    writer = LedgerWriter(evidence_dir, actor="review_record")
    open_keys = {
        obligation_key(item) for item in
        writer.state.get("open_recheck_obligations", ())}
    this_key = "RECHECK-{0}-R{1}".format(task_id, round_n)
    next_key = "RECHECK-{0}-R{1}".format(task_id, round_n + 1)
    if native_binding:
        # A repair gate cannot discharge the parent gate's outstanding recheck.
        scope_key = f"{native_binding['unit']}-{native_binding['gate']}"
        this_key = next((obligation_key(o) for o in writer.state.get("open_recheck_obligations", [])
                         if o.get("gate_scope") == scope_key), "")
        next_key = f"RECHECK-{scope_key}-R{round_n + 1}"
    review_payload = {
        "review_id": review_id,
        "task_id": task_id,
        "round": round_n,
        "verdict": result_norm,
        "reviewer": reviewer or "unknown",
        "report_path": str(report_path),
        "report_sha256": report_sha256,
        "commit": binding["commit"],
        "worktree": binding["worktree"],
        "bindings": binding["bindings"],
        "scope": scope_norm,
    }
    if observed_loop:
        review_payload["observed_loop"] = observed_loop
    if "tree" in binding:
        review_payload["tree"] = binding["tree"]
    if native_binding:
        review_payload["loop_binding"] = native_binding
    batch = [("review_recorded", review_payload)]
    obligations = []
    if result_norm in _OBLIGATION_DISCHARGING_RESULTS \
            and this_key in open_keys:
        batch.append(("recheck_obligation_cleared", {
            "obligation_id": this_key,
            "task_id": task_id,
            "round": round_n,
            "cleared_by": review_id,
            "verdict": result_norm,
        }))
        obligations.append({"id": this_key, "state": "cleared",
                            "by": review_id})
    if result_norm == "NEEDS_CHANGE":
        if next_key in open_keys:
            obligations.append({"id": next_key, "state": "already_open",
                                "by": review_id})
        else:
            batch.append(("recheck_obligation_registered", {
                "obligation_id": next_key,
                "task_id": task_id,
                "round": round_n + 1,
                "created_by": review_id,
                **({"gate_scope": scope_key} if native_binding else {}),
                "prev_report": str(report_path),
                "prev_report_sha256": report_sha256,
                "commit": binding["commit"],
            }))
            obligations.append({"id": next_key, "state": "registered",
                                "by": review_id})
    outcome = writer.transact(batch)
    ledger_face = {
        "transaction_id": outcome.get("transaction_id"),
        "events": [kind for kind, _ in batch],
        "event_count": outcome.get("event_count"),
        "last_seq": outcome.get("last_seq"),
    }
    return ledger_face, obligations


def _serialize_native_review(writer):
    from functools import wraps
    @wraps(writer)
    def guarded(**kwargs):
        root = kwargs.get("root")
        evidence = kwargs.get("evidence_dir") or (Path(root) / ".governance" if root else None)
        if evidence and (kwargs.get("require_loop") or (Path(evidence) / "flow-unit-runtime.json").is_file()):
            from loop_event_log import _cross_process_lock
            try:
                with _cross_process_lock(Path(evidence) / "review-record"):
                    return writer(**kwargs)
            except OSError as exc:
                return {"error": str(exc), "code": "review_io"}
        return writer(**kwargs)
    return guarded


@_serialize_native_review
def write_review_record(
    *,
    task_id,
    round_n,
    result,
    report_path,
    reviewer=None,
    unit_id=None,
    gate_id=None,
    root=None,
    evidence_dir=None,
    runtime_file=None,
    plugin_home=None,
    actor=None,
    force=False,
    scope="full",
    delta_base=None,
    bind_files=(),
    bind_tree=None,
    abort_reason=None,
    require_loop=False,
    record_only=False,
):
    """Persist one review conclusion + Wire A (FIX-236.1) — as the FEAT-094
    five-step indivisible review transaction (提交报告→验证结构与修订→登记
    发现→自动生成后续义务→更新状态).

    Args:
        task_id: task id of the reviewed artifact (e.g. ``FIX-236``).
        round_n: review round (0-based; R0 is the first review).
        result: ``APPROVED`` | ``APPROVED_WITH_NOTES`` | ``NEEDS_CHANGE`` |
            ``BLOCKED`` | ``ABORTED`` | ``UNKNOWN`` (the last two are
            supervisor-recorded agent-death terminal states, FEAT-094 ⑤ —
            they never trigger a revisit and never discharge an open
            recheck obligation).
        report_path: path of the reviewer's full report (embedded in the
            record, hashed into the trust pin, and reused as prev_report
            for the R+1 revisit). MUST be readable — no report, no binding,
            no record (fail-closed).
        reviewer: reviewer/agent name (also the loop actor when given).
            FIX-314: part of the record key — the FIRST reviewer of a
            task+round keeps the canonical ``review-{task}-R{n}.md`` name, a
            DIFFERENT reviewer is namespaced to
            ``review-{task}-R{n}-{reviewer-slug}.md`` (mirrored evidence id
            ``REVIEW-{task}-R{n}-{SLUG}``). A name that does not normalize
            to an ASCII slug fails closed.
        unit_id / gate_id: bind the observation to the current unit and its own gate.
        root: host project root for evidence storage and revision binding.
        evidence_dir: explicit governance directory; defaults to root/.governance.
        runtime_file: when supplied, it must point to the same host's runtime file.
        plugin_home / actor: retained for compatibility with prior callers.
        force: FIX-289⑤ overwrite opt-in (FIX-314: the guard key is the full
            task+round+reviewer triple). When the reviewer's own record
            already exists, the default (``force=False``) fails closed: an
            error dict is returned and nothing is written (no overwrite, no
            evidence row). ``force=True`` overwrites deliberately WITH an
            audit trail — the previous record is backed up to
            ``review-{id}-R{n}.pre-<ts>.md`` beside the record, the new record
            carries a ``- force_overwrite:`` marker naming the backup, and the
            summary reports ``force_overwrite`` + ``previous_record_backup``.
        scope / delta_base: FEAT-091 injection-scope record (unchanged).
        bind_files: FEAT-094 ① — repo paths to pin with ``git hash-object``
            blob hashes (untracked-safe immutable binding of the reviewed
            object's files).
        abort_reason: FEAT-094 ⑤ — supervisor's reason for an ABORTED /
            UNKNOWN terminal record (agent death); rides the record as an
            additive ``- abort_reason:`` field line.

    Returns:
        dict summary: review_id, review_file, evidence_row, wiring {...},
        revisit_required / next_round / prev_report (NEEDS_CHANGE only),
        trust {...} / ledger {...} / obligations [...] (FEAT-094 additive),
        and ``error`` (fail-closed) when inputs are invalid, the report is
        unreadable, the report clearly contradicts the claimed result
        (CONFLICT — manual disposition), or the authority ledger refused
        the transaction (integrity broken / obligation contract). Never
        raises.
    """
    # Input validation (fail-closed).
    if not _TASK_ID_RE.match(str(task_id or "")):
        from loop_workflow import UNIT_ID
        if not (root and UNIT_ID.fullmatch(str(task_id or "")) and
                (Path(root) / ".governance" / "flow-unit-runtime.json").is_file()):
            return {"error": "task_id must name a registered work unit or PREFIX-NNN task"}
    try:
        round_n = int(round_n)
    except (TypeError, ValueError):
        return {"error": "round_n must be an integer"}
    if round_n < 0:
        return {"error": "round_n must be >= 0"}
    result_norm = str(result or "").strip().upper()
    if not _RESULT_RE.match(result_norm):
        return {"error": (
            "result must be APPROVED | APPROVED_WITH_NOTES | NEEDS_CHANGE | "
            "BLOCKED | ABORTED | UNKNOWN (got {0!r})".format(result))}
    if not report_path:
        return {"error": "report_path is required"}
    if abort_reason is not None and result_norm not in ("ABORTED", "UNKNOWN"):
        return {"error": (
            "abort_reason requires result ABORTED|UNKNOWN (FEAT-094 ⑤ "
            "supervisor terminal states; got {0})".format(result_norm))}
    # FEAT-091: review injection-scope record (delta revisit). Default
    # "full" keeps every pre-FEAT-091 caller byte-compatible; "delta"
    # requires an anchor (prev-round report path or diff anchor).
    scope_norm = str(scope or "full").strip().lower()
    if scope_norm not in ("full", "delta"):
        return {"error": (
            "scope must be full | delta (FEAT-091; got {0!r})".format(scope))}
    if delta_base is not None and not str(delta_base).strip():
        return {"error": "delta_base must be a non-empty path/anchor"}
    if delta_base is not None and scope_norm != "delta":
        return {"error": (
            "delta_base requires scope=delta (FEAT-091; scope={0})".format(
                scope_norm))}

    # Resolve destinations.
    if evidence_dir is None:
        if root is None:
            return {"error": "root or evidence_dir is required"}
        evidence_dir = Path(root) / ".governance"
    evidence_dir = Path(evidence_dir)
    native_binding = None
    runtime_path = evidence_dir / "flow-unit-runtime.json"
    if runtime_file is not None and Path(runtime_file).resolve() != runtime_path.resolve():
        return {"error": "the scoped runtime must belong to the review's host", "code": "loop_binding"}
    observed_loop = None
    if record_only and gate_id:
        return {"error": "an independent observation cannot apply a gate verdict"}
    from loop_workflow import _payload, review_binding
    try:
        units = _payload(runtime_path)["flow_units"]
        matching = [u for u in units if u["task_id"] == task_id and (not unit_id or u["flow_unit_id"] == unit_id)]
        assigned = any(u["runtime_status"] in ("active", "dormant") for u in matching)
        if record_only and unit_id and not matching:
            raise ValueError("no such unit for this observed task")
        if len(matching) == 1 and (record_only or (not assigned and not unit_id and not gate_id)):
            subject = matching[0]
            observed_loop = {"unit": subject["flow_unit_id"], "attempt": len(subject.get("gate_history", [])),
                             "cas_version": subject["loop_state"].get("cas_version")}
    except (ValueError, OSError) as exc:
        return {"error": str(exc), "code": "loop_binding"}
    # FIX-314 key-face resolution: the record key is (task, round, reviewer).
    # The canonical name stays the FIRST reviewer's slot — backward
    # compatible with every pre-FIX-314 record (a reviewer-less legacy file
    # is an unnamed owner that is never rewritten); a DIFFERENT reviewer for
    # the same task+round is namespaced beside it. The FIX-289⑤ guard below
    # then protects each reviewer's OWN file: three identical keys are still
    # refused without force, while the two halves of one review round
    # (REL-076 M-3) never overwrite each other.
    canonical_name = "review-{0}-R{1}.md".format(task_id, round_n)
    review_file = evidence_dir / canonical_name
    reviewer_slug = None
    if reviewer:
        reviewer_slug = _reviewer_slug(reviewer)
        if not reviewer_slug:
            return {"error": (
                "reviewer does not normalize to a filename-safe slug "
                "(ASCII alnum runs joined by dashes): {0!r}".format(reviewer))}
        if review_file.exists():
            try:
                owner = _read_record_reviewer(review_file)
            except (OSError, UnicodeDecodeError) as exc:
                # UnicodeDecodeError is a ValueError, NOT an OSError: a
                # non-UTF-8 record (the Windows GBK/ANSI mojibake family)
                # must fail closed to the same error dict — review-FIX-314-
                # CODE-R0 P1-1 — never escape as a raw traceback.
                return {"error": (
                    "cannot read existing review record to resolve the "
                    "(task, round, reviewer) key: {0}".format(exc))}
            if owner != str(reviewer).strip():
                review_file = evidence_dir / (
                    "review-{0}-R{1}-{2}.md".format(
                        task_id, round_n, reviewer_slug))
    review_id = "REVIEW-{0}-R{1}".format(task_id, round_n)
    if reviewer_slug is not None and review_file.name != canonical_name:
        review_id = "REVIEW-{0}-R{1}-{2}".format(
            task_id, round_n, reviewer_slug.upper())
    evidence_path = evidence_dir / "evidence-log.md"
    today = date.today().isoformat()

    # 0. FIX-289⑤ overwrite guard (READ-ONLY face; the backup itself is
    # deferred to the file-write phase so a refused transaction leaves no
    # stray artifacts): a task+round+reviewer review record is immutable by
    # default. Historical backfill / migrated records must never be silently
    # replaced (REL-073 same-number overwrite near-miss). force=True opts in
    # with an audit trail.
    file_preexisted = review_file.exists()
    if file_preexisted and not force:
        return {"error": (
            "review record already exists: {0} — refusing to overwrite "
            "(FIX-289⑤ task+round+reviewer record guard; historical "
            "backfill data is protected). To replace it deliberately, "
            "re-run with force=True: the previous record is backed up "
            "and the overwrite is marked in the new record.".format(
                review_file))}

    # ── FEAT-094 step 1 — 提交报告: read the report + pin its bytes ──
    report_face = _resolve_report_face(report_path, root)
    if report_face is None:
        return {"error": (
            "report not readable: {0} — FEAT-094 trust chain requires the "
            "reviewed report's bytes (sha256 pin); no report, no record "
            "(fail-closed)".format(report_path))}
    report_resolved, report_bytes, report_text = report_face
    report_sha256 = hashlib.sha256(report_bytes).hexdigest()

    repo_root = root if root is not None else evidence_dir.parent
    if bind_tree is not None:
        if (not re.fullmatch(_GIT_OID, bind_tree) or _git_output(repo_root, "cat-file", "-t", bind_tree) != "tree"
                or not re.search(r"(?<![0-9a-f])" + re.escape(bind_tree) + r"(?![0-9a-f])", report_text)):
            return {"error": "the review report must identify the existing immutable candidate tree", "code": "tree_binding"}
    try:
        binding = _snapshot_binding(repo_root, bind_files, bind_tree)
        if bind_tree is not None:
            binding["tree"] = bind_tree
    except ValueError as exc:
        return {"error": str(exc), "code": "tree_binding"}

    # review_binding may activate a newly eligible dormant unit and append its event.
    if not record_only and (unit_id or gate_id or assigned):
        try:
            if not reviewer:
                raise ValueError("a scoped gate requires an identified reviewer")
            from loop_engine import reviewer_gates
            allowed = reviewer_gates(reviewer)
            native_binding = review_binding(root or evidence_dir.parent, task_id, unit_id, gate_id,
                                            allowed_gates=allowed)
            if native_binding.get("release_reviewer") and reviewer != native_binding["release_reviewer"]:
                raise ValueError("this version requires its designated release reviewer")
            if force:
                raise ValueError("a consumed gate review is immutable; use a new review round")
        except (ValueError, OSError) as exc:
            return {"error": str(exc), "code": "loop_binding"}

    # ── FEAT-094 step 2 — 验证结构与修订: conflict check + snapshot ──
    report_verdicts = _report_verdict_tokens(report_text)
    if native_binding and result_norm in ("APPROVED", "APPROVED_WITH_NOTES") and report_verdicts != {result_norm}:
        return {"error": "a scoped approval requires the review report's unambiguous verdict", "code": "review_verdict"}
    if native_binding and native_binding.get("release_version"):
        version = re.escape(native_binding["release_version"])
        if not re.search(r"(?<![0-9.])" + version + r"(?![0-9]|\.[0-9])", report_text):
            return {"error": "the release report must identify the reviewed candidate version", "code": "release_version"}
    if (report_verdicts
            and result_norm not in _CONFLICT_EXEMPT_RESULTS
            and result_norm not in report_verdicts):
        return {
            "error": (
                "CONFLICT: report {0} clearly carries verdict token(s) "
                "{1} but the claimed result is {2} — refused (FEAT-094 ③ "
                "禁乐观者胜出: report/machine-record divergence is never "
                "auto-resolved). Disposition (manual): align the two (fix "
                "the report's conclusion or the --result claim) and re-run; "
                "a supervisor escalation may instead record BLOCKED / "
                "ABORTED / UNKNOWN without a matching token".format(
                    report_path, sorted(report_verdicts), result_norm)),
            "code": "conflict_report_vs_record",
            "conflict": {"report_verdicts": sorted(report_verdicts),
                         "claimed": result_norm},
        }
    if result_norm == "APPROVED_WITH_NOTES":
        fields = _conflicting_blocker_fields(report_text)
        if fields:
            return {
                "error": "CONFLICT: report {0} declares {1}; {2} requires zero "
                         "unresolved blockers".format(report_path, fields, result_norm),
                "code": "conflict_report_vs_record",
                "conflict": {"report_fields": fields, "claimed": result_norm},
            }
    evidence_dir.mkdir(parents=True, exist_ok=True)

    # ── FEAT-094 steps 3+4 — the atomic ledger core (登记发现 event +
    # 自动生成后续义务, one transact batch; anti-evaporation ordering:
    # the ledger commits FIRST, files follow) ──
    try:
        ledger_face, obligations = _review_ledger_transaction(
            evidence_dir, task_id=task_id, round_n=round_n,
            result_norm=result_norm, review_id=review_id, reviewer=reviewer,
            report_path=report_path, report_sha256=report_sha256,
            binding=binding, scope_norm=scope_norm, native_binding=native_binding, observed_loop=observed_loop)
    except Exception as exc:  # LedgerError family — structured, never raise
        return {
            "error": (
                "authority ledger refused the review transaction — the "
                "five-step transaction is refused wholesale (nothing "
                "written; FEAT-094 fail-closed): {0}".format(exc)),
            "code": "ledger_refused",
            "ledger_detail": str(exc),
        }

    # ── FEAT-094 step 3 (file faces) + step 5 (状态) ──
    force_note = None
    if file_preexisted:
        try:
            previous_text = review_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # P1-1 (review-FIX-314-CODE-R0): same half-face on the force
            # backup read — a non-UTF-8 record fails closed to the error
            # dict, not to a raw UnicodeDecodeError. The ledger transaction
            # already committed — disclosed via ledger_face.
            return {
                "error": (
                    "cannot read existing review record for backup: {0} "
                    "(ledger transaction {1} already committed — the "
                    "review events are durable, re-run with force after "
                    "repairing the record encoding)".format(
                        exc, ledger_face.get("transaction_id"))),
                "code": "backup_unreadable",
                "ledger": ledger_face,
            }
        backup_name = "{0}.pre-{1}.md".format(
            review_file.name[: -len(".md")],
            datetime.now().strftime("%Y%m%dT%H%M%S%f"))
        try:
            (evidence_dir / backup_name).write_text(
                previous_text, encoding="utf-8")
        except OSError as exc:
            return {
                "error": "cannot write overwrite backup: {0} (ledger "
                         "transaction {1} already committed)".format(
                             exc, ledger_face.get("transaction_id")),
                "code": "backup_unwritable",
                "ledger": ledger_face,
            }
        force_note = backup_name

    trust_fields = [
        "- report_sha256: {0}".format(report_sha256),
        "- snapshot_commit: {0}".format(binding["commit"]),
        "- snapshot_worktree: {0}".format(binding["worktree"]),
    ]
    if observed_loop:
        trust_fields.append("- observed_loop: " + json.dumps(observed_loop, sort_keys=True, separators=(",", ":")))
    if "tree" in binding:
        trust_fields.append(f"- snapshot_tree: {binding['tree']}")
    if native_binding:
        trust_fields.extend(f"- {key}: {value}" for key, value in native_binding.items())
    for bound in binding["bindings"]:
        trust_fields.append("- snapshot_bind: {0}={1}".format(
            bound["path"], bound["hash"]))
        if bound.get("mode"):
            trust_fields.append("- snapshot_mode: {0}={1}".format(bound["path"], bound["mode"]))
    review_text = _review_file_text(
        task_id, round_n, result_norm, reviewer, report_path, today, "pending",
        force_note=force_note, scope=scope_norm, delta_base=delta_base,
        trust_fields=trust_fields,
        abort_reason=str(abort_reason) if abort_reason else None)
    try:
        review_file.write_text(review_text, encoding="utf-8")
    except OSError as exc:
        return {
            "error": "cannot write review file: {0} (ledger transaction "
                     "{1} already committed — the review events are "
                     "durable; re-running this command converges: the "
                     "obligation is already_open so no duplicate "
                     "registers)".format(
                         exc, ledger_face.get("transaction_id")),
            "code": "review_file_unwritable",
            "ledger": ledger_face,
        }

    pins = "report_sha256={0}; commit={1}".format(
        report_sha256[:12],
        binding["commit"][:12] if binding["commit_status"] == "resolved"
        else "none")
    registered = [ob for ob in obligations
                  if ob["state"] in ("registered", "already_open")]
    if registered:
        pins = "{0}; obligation={1}".format(
            pins, ",".join(ob["id"] for ob in registered))
    row = _evidence_row(
        task_id, round_n, result_norm, reviewer, report_path,
        review_file.name, today, review_id=review_id, pins=pins,
        gate_id=native_binding["gate"] if native_binding else gate_id)
    try:
        with evidence_path.open("a", encoding="utf-8") as fh:
            fh.write("\n" + row)
    except OSError as exc:
        # Compensation (five-step atomicity, no half-commit window): a
        # review file THIS transaction created is removed again; a forced
        # overwrite keeps the new record + backup (the previous record is
        # preserved at the backup path — disclosed, never destroyed).
        if not file_preexisted:
            try:
                review_file.unlink()
            except OSError:
                pass
        return {
            "error": (
                "cannot append evidence row: {0} — review file "
                "{1}was removed again (transaction compensated); the "
                "ledger transaction {2} already committed (durable, "
                "disclosed — re-run to converge)".format(
                    exc,
                    "" if not file_preexisted else
                    "kept (force overwrite; previous record preserved at "
                    "{0}) ".format(force_note),
                    ledger_face.get("transaction_id"))),
            "code": "evidence_row_unwritable",
            "ledger": ledger_face,
        }

    wiring = {"wired": False, "decision": "recorded", "reason": "independent or interrupted observation"}
    if native_binding and not record_only and result_norm not in ("ABORTED", "UNKNOWN"):
        from loop_workflow import gate_review
        try:
            wiring = gate_review(root or evidence_dir.parent, native_binding["unit"], native_binding["gate"], review_id)
        except (ValueError, OSError) as exc:
            return {"error": str(exc), "review_id": review_id, "review_file": str(review_file),
                    "code": "loop_gate_pending", "evidence_row_written": True}

    summary = {
        "review_id": review_id,
        "task_id": task_id,
        "round": round_n,
        "reviewer": reviewer,
        "result": result_norm,
        "review_file": str(review_file),
        "evidence_row_written": True,
        "wiring": wiring,
        "revisit_required": result_norm == "NEEDS_CHANGE",
        "scope": scope_norm,
        "trust": {
            "report_path": str(report_resolved),
            "report_sha256": report_sha256,
            "report_bytes": len(report_bytes),
            "commit": binding["commit"],
            "commit_status": binding["commit_status"],
            "worktree": binding["worktree"],
            "bindings": binding["bindings"],
        },
        "ledger": ledger_face,
        "obligations": obligations,
    }
    if delta_base is not None:
        summary["delta_base"] = str(delta_base)
    if result_norm == "NEEDS_CHANGE":
        summary["next_round"] = "REVIEW-{0}-R{1}".format(task_id, round_n + 1)
        summary["prev_report"] = str(report_path)
    if force_note is not None:
        summary["force_overwrite"] = True
        summary["previous_record_backup"] = str(evidence_dir / force_note)
    return summary


__all__ = [
    "write_review_record",
    "snapshot_binding",
    "verify_review_trust",
]
