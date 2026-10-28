"""FIX-462 — machine writer for the STATIC_PIN_EXEMPTIONS ledger (DEC-220).

The pin-exemption ledger in ``checks/version.py`` was hand-edited through
five consecutive release windows (FIX-416/418/421/442/453 re-anchor chain,
then FIX-459/460) — every edit was a manual line-number surgery on a live
Python literal, exactly the rot the ledger's own stale-audit exists to
catch.  This module closes that class (TRIAGE-FIX-462): the ONLY sanctioned
write path is now

    python infra/verify_workflow.py pins register --file F --line N \
        --token T --reason R
    python infra/verify_workflow.py pins re-anchor --file F \
        --from N --to N [--token T]

Writer contract (governance_store / agent-locks-acquire precedent shape):

  * AST-anchored surgery — the entry tuple's source location comes from
    parsing ``checks/version.py``; bytes outside the edited hunk are
    preserved verbatim (no regex guessing over the dict).
  * fail-closed — every validation runs BEFORE any write; a single
    ``tempfile`` + ``os.replace`` performs the atomic swap; a failed
    post-check restores the original bytes and refuses.
  * effect-based idempotency — re-running an already-applied register or
    re-anchor returns ``effect=idempotent_noop`` with zero byte changes.
  * provenance comments — every machine write lands with a
    ``# pins register|re-anchor op-<32hex> ...`` comment line directly
    above the entry tuple; governance-write-guard face 6 warns on ledger
    rows that lack one (outside the delivery amnesty snapshot below).
  * exit scale (governance_store _emit): 0 ok / 2 refusal / 3 retryable.
  * post-check self-verification — the candidate source is shadow-imported
    from the temp file and its own ``scan_static_version_pins`` must show
    (a) the registered line no longer surfaces as a hit and (b) no stale
    exemption for the entry, before the swap is committed.

No ``.governance`` writes, no prints outside the JSON receipt path (the
engine wires dispatch only — the governance_cost pattern).

Run:
    python infra/verify_workflow.py pins register --help
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

TASK_ID = "FIX-462"
SCHEMA = "pin-ledger/1"

LEDGER_REL = "skills/software-project-governance/infra/checks/version.py"
SELF_REL = "skills/software-project-governance/infra/pin_ledger.py"
SCAN_DIR_REL = "skills/software-project-governance/infra/tests"
SKILL_MD_REL = "skills/software-project-governance/SKILL.md"

#: Provenance marker the writer stamps above every entry it touches; the
#: write-guard face matches this exact shape (op id = uuid4().hex, 32 hex).
_PROVENANCE_RE = re.compile(
    r"#\s*pins\s+(register|re-anchor)\s+op-[0-9a-f]{32}\b")

_SEMVER_RE = re.compile(r"(?<![\d.])(\d+\.\d+\.\d+)(?![\d.])")

_REASON_NAME_RE = re.compile(r"^_REASON_[A-Z0-9_]+$")


def _repo_root(root: Path) -> Path:
    return Path(root).resolve()


def _ledger_path(root: Path) -> Path:
    return _repo_root(root) / LEDGER_REL


def _new_op_id() -> str:
    return "op-" + uuid.uuid4().hex


# ── ledger AST location ─────────────────────────────────────────────────────


def _parse_ledger(text: str):
    """Return (tree, dict_node) for STATIC_PIN_EXEMPTIONS, else (None, err)."""
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return None, "ledger source does not parse: {0}".format(exc.msg)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "STATIC_PIN_EXEMPTIONS"
                        for t in node.targets)
                and isinstance(node.value, ast.Dict)):
            return (tree, node.value), None
    return None, "STATIC_PIN_EXEMPTIONS dict not found"


def _entry_tuples(dict_node: ast.Dict):
    """Yield (key, tuple_node, line_value, token_value) for every entry."""
    for key_node, value_node in zip(dict_node.keys, dict_node.values):
        if not (isinstance(key_node, ast.Constant) and isinstance(key_node.value, str)):
            continue
        if not isinstance(value_node, ast.List):
            continue
        for elem in value_node.elts:
            if (isinstance(elem, ast.Tuple) and len(elem.elts) == 3
                    and isinstance(elem.elts[0], ast.Constant)
                    and isinstance(elem.elts[0].value, int)
                    and isinstance(elem.elts[1], ast.Constant)
                    and isinstance(elem.elts[1].value, str)):
                yield key_node.value, elem, elem.elts[0].value, elem.elts[1].value


def _line_tokens(line_text: str):
    return [m.group(1) for m in _SEMVER_RE.finditer(line_text)]


# ── validation helpers (fail-closed: pure reads) ────────────────────────────


def _active_version(root: Path):
    skill = _repo_root(root) / SKILL_MD_REL
    if not skill.is_file():
        return None, "SKILL.md not found under the project root"
    match = re.search(r"^version:\s*(\d+\.\d+\.\d+)\s*$",
                      skill.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        return None, "SKILL.md frontmatter carries no active version"
    return match.group(1), None


def _normalized_rel(file_arg: str):
    rel = Path(file_arg.replace("\\", "/")).as_posix().lstrip("/")
    if rel.startswith("./"):
        rel = rel[2:]
    return rel


def _target_line_carries(root: Path, rel: str, line: int, token: str):
    target = _repo_root(root) / rel
    if not target.is_file():
        return False, "target file not found: {0}".format(rel)
    lines = target.read_text(encoding="utf-8").splitlines()
    if not 0 < line <= len(lines):
        return False, "line {0} out of range (file has {1} lines)".format(line, len(lines))
    if token not in _line_tokens(lines[line - 1]):
        return False, ("line {0} does not carry token \"{1}\" as a standalone "
                       "semver token".format(line, token))
    return True, None


def _shadow_module(path: Path):
    """Import a ledger source under a throwaway module name (never the
    ambient ``checks.version`` cache — a non-repo root must consult ITS
    own ledger, and post-checks must consult the CANDIDATE source)."""
    module_name = "pin_ledger_shadow_" + uuid.uuid4().hex[:12]
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scan_hits(root: Path, registry=None):
    """Run root's OWN scan module over root; return its issue lines."""
    root = _repo_root(root)
    module = _shadow_module(root / LEDGER_REL)
    kwargs = {"exemptions": registry} if registry is not None else {}
    return module.scan_static_version_pins(root, **kwargs)


def _shadow_scan(root: Path, candidate_path: Path):
    """Import the CANDIDATE ledger source and run its own scan over root."""
    module = _shadow_module(candidate_path)
    return module.scan_static_version_pins(_repo_root(root))


# ── atomic write + post-check ───────────────────────────────────────────────


def _atomic_write_with_postcheck(root: Path, ledger_path: Path,
                                 original_bytes: bytes, candidate_text: str,
                                 rel: str, line: int, token: str):
    """Write candidate to a temp file, self-verify, then os.replace.

    Returns (ok, detail, post_checks). On any failure the ledger keeps its
    original bytes and the temp file is removed.
    """
    post_checks = {"compile_ok": False, "entry_present": False,
                   "scan_hit_absent": False, "stale_absent": False}
    try:
        compile(candidate_text, str(ledger_path), "exec")
    except SyntaxError as exc:
        return False, "candidate source does not compile: {0}".format(exc.msg), post_checks
    post_checks["compile_ok"] = True

    parsed, err = _parse_ledger(candidate_text)
    if err:
        return False, "candidate ledger unreadable: {0}".format(err), post_checks
    _tree, dict_node = parsed
    present = any(k == rel and ln == line and tok == token
                  for k, _elem, ln, tok in _entry_tuples(dict_node))
    if not present:
        return False, "entry not present in candidate ledger", post_checks
    post_checks["entry_present"] = True

    fd, temp_name = tempfile.mkstemp(
        dir=str(ledger_path.parent), prefix=".pin_ledger_", suffix=".py")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(candidate_text)
        findings = _shadow_scan(root, temp_path)
    except Exception as exc:  # retryable class: IO / import environment
        temp_path.unlink(missing_ok=True)
        return None, "post-check could not run: {0}".format(exc), post_checks
    try:
        hit_key = "static-version-pin: {0}:{1} ".format(rel, line)
        stale_key = "stale exemption {0}:{1} ".format(rel, line)
        post_checks["scan_hit_absent"] = not any(hit_key in f for f in findings)
        post_checks["stale_absent"] = not any(stale_key in f for f in findings)
        if not (post_checks["scan_hit_absent"] and post_checks["stale_absent"]):
            temp_path.unlink(missing_ok=True)
            return False, ("post-check failed: the new entry did not suppress "
                           "its own scan hit / went stale immediately"), post_checks
        os.replace(temp_path, ledger_path)
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        return None, "atomic swap failed: {0}".format(exc), post_checks
    return True, "written", post_checks


def _restore(ledger_path: Path, original_bytes: bytes):
    ledger_path.write_bytes(original_bytes)


# ── FIX-464: delivery-amnesty exit sync ──────────────────────────────────────


def _sync_amnesty_exit(root: Path, rel: str, line: int, token: str,
                       command: str, op_id: str):
    """FIX-464 — a writer-touched row leaves DELIVERY_AMNESTY_ENTRIES.

    The amnesty contract (:data:`DELIVERY_AMNESTY_ENTRIES` docstring) says
    "rows leave this set the moment the writer touches them" — the FIX-462
    writer updated the ledger but never removed the touched row from the
    frozen in-source amnesty set, so a re-anchored row became an amnesty
    GHOST row (still listed, no longer live) and the snapshot contract
    test failed on the very first real write.  This sync runs after every
    successful register/re-anchor ledger swap: it rewrites this module's
    own source to drop the touched ``(rel, line, token)`` tuple from the
    frozenset, leaving a provenance-shaped comment in its place.

    Post-check (fail-closed, temp-file shadow import — the ledger
    post-check precedent): the candidate amnesty set (a) no longer lists
    the touched row, (b) contains NO ghost rows (amnesty ⊆ live ledger),
    and (c) every live row outside amnesty carries a provenance comment
    directly above it — the exact invariant the write-guard face 6 and the
    snapshot contract test assert.

    Returns ``(state, error)``: ``("noop_not_in_amnesty", None)`` /
    ``("noop_self_absent", None)`` (mini-root harnesses without a
    pin_ledger.py copy) / ``("written", None)`` / ``(_, detail)`` on
    refusal (the caller then restores BOTH files — ledger + this module).
    """
    root = _repo_root(root)
    self_path = root / SELF_REL
    if not self_path.is_file():
        return "noop_self_absent", None
    original_bytes = self_path.read_bytes()
    text = original_bytes.decode("utf-8")

    row_re = re.compile(r"^(?P<indent>\s*)\(\"{0}\", {1}, \"{2}\"\),$".format(
        re.escape(rel), line, re.escape(token)))
    lines = text.splitlines(keepends=True)
    hit_idx = next((i for i, l in enumerate(lines)
                    if row_re.match(l.rstrip("\r\n"))), None)
    if hit_idx is None:
        return "noop_not_in_amnesty", None

    comment = ("{0}# pins {1} {2} (FIX-464): writer touched ({3}, {4}, "
               "\"{5}\") — row left DELIVERY_AMNESTY_ENTRIES\n").format(
        lines[hit_idx][:len(lines[hit_idx]) - len(lines[hit_idx].lstrip())],
        command, op_id, rel, line, token)
    candidate = "".join(lines[:hit_idx] + [comment] + lines[hit_idx + 1:])

    try:
        compile(candidate, str(self_path), "exec")
    except SyntaxError as exc:
        return "refused", "amnesty candidate does not compile: {0}".format(exc.msg)
    fd, temp_name = tempfile.mkstemp(
        dir=str(self_path.parent), prefix=".pin_ledger_amnesty_", suffix=".py")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(candidate)
        new_amnesty = _shadow_module(temp_path).DELIVERY_AMNESTY_ENTRIES
        live, live_text = _live_entries(root)
        if (rel, line, token) in new_amnesty:
            return "refused", "post-check failed: the touched row is still in the candidate amnesty"
        ghosts = new_amnesty - live
        if ghosts:
            return "refused", ("post-check failed: candidate amnesty keeps "
                               "ghost rows absent from the live ledger: {0}".format(
                                   sorted(ghosts)[:3]))
        live_lines = live_text.splitlines()
        for (lrel, lln, ltok) in (live - new_amnesty):
            idx = _ledger_entry_lineno(live_text, lrel, lln, ltok)
            if idx is None or idx < 2 or not _PROVENANCE_RE.search(live_lines[idx - 2]):
                return "refused", ("post-check failed: live row ({0}, {1}, "
                                   "\"{2}\") is outside amnesty without a "
                                   "provenance comment".format(lrel, lln, ltok))
        os.replace(temp_path, self_path)
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        return "refused", "amnesty post-check could not run: {0}".format(exc)
    return "written", None


def _live_entries(root: Path):
    """(frozenset of live (rel, line, token), ledger text) from disk."""
    ledger_text = (_repo_root(root) / LEDGER_REL).read_text(encoding="utf-8")
    parsed, err = _parse_ledger(ledger_text)
    if err:
        raise ValueError("ledger unreadable: {0}".format(err))
    _tree, dict_node = parsed
    return (frozenset((k, ln, tok) for k, _e, ln, tok in _entry_tuples(dict_node)),
            ledger_text)


def _ledger_entry_lineno(ledger_text: str, rel: str, line: int, token: str):
    """1-based source line of the ``(line, "token", …)`` tuple under ``rel``."""
    parsed, err = _parse_ledger(ledger_text)
    if err:
        return None
    _tree, dict_node = parsed
    for key_node, value_node in zip(dict_node.keys, dict_node.values):
        if not (isinstance(key_node, ast.Constant) and key_node.value == rel):
            continue
        for elem in value_node.elts:
            if (isinstance(elem, ast.Tuple) and len(elem.elts) == 3
                    and elem.elts[0].value == line
                    and elem.elts[1].value == token):
                return elem.lineno
    return None


# ── register ────────────────────────────────────────────────────────────────


def register_exemption(root: Path, file: str, line: int, token: str,
                       reason: str, *, dry_run: bool = False):
    """Register one (line, token, reason) exemption row for ``file``."""
    receipt = {"schema": SCHEMA, "command": "pins register", "task": TASK_ID,
               "file": file, "line": line, "token": token, "dry_run": dry_run}

    def refuse(detail):
        receipt.update({"code": "refused", "error": True, "detail": detail})
        return receipt, 2

    rel = _normalized_rel(file)
    if not rel.startswith(SCAN_DIR_REL + "/") or not rel.endswith(".py"):
        return refuse("file must live under {0} and end in .py".format(SCAN_DIR_REL))
    if line < 1:
        return refuse("line must be >= 1")
    if not reason or not reason.strip():
        return refuse("reason must be non-empty")

    root = _repo_root(root)
    ledger_path = _ledger_path(root)
    if not ledger_path.is_file():
        return refuse("ledger not found: {0}".format(LEDGER_REL))
    original_bytes = ledger_path.read_bytes()
    text = original_bytes.decode("utf-8")

    parsed, err = _parse_ledger(text)
    if err:
        return refuse("ledger unreadable: {0}".format(err))
    _tree, dict_node = parsed

    # Idempotency: an identical row already present = effect achieved.
    existing = [(k, ln, tok) for k, _e, ln, tok in _entry_tuples(dict_node)]
    if (rel, line, token) in existing:
        receipt.update({"code": "ok", "error": False, "effect": "idempotent_noop",
                        "detail": "identical exemption already registered"})
        return receipt, 0

    # The row must be needed: the scan flags this exact line today.
    carries, cdetail = _target_line_carries(root, rel, line, token)
    if not carries:
        return refuse(cdetail)
    hits = _scan_hits(root)
    hit_key = "static-version-pin: {0}:{1} ".format(rel, line)
    if not any(hit_key in f for f in hits):
        return refuse(("line {0} is not a live pin hit (annotation line, "
                       "token != active version, or already exempted)").format(line))

    # Reason: a _REASON_* name must exist in the module; free text is
    # written as a quoted literal.
    if _REASON_NAME_RE.match(reason.strip()):
        if not re.search(r"^{0}\s*=".format(re.escape(reason.strip())),
                         text, re.MULTILINE):
            return refuse("reason name {0} not defined in the ledger module".format(reason))
        reason_literal = reason.strip()
    else:
        reason_literal = json.dumps(reason.strip(), ensure_ascii=False)

    op_id = _new_op_id()
    comment = ("# pins register {0} (FIX-462): machine-written exemption "
               "for a live scan hit".format(op_id))
    tuple_line = "        ({0}, {1}, {2}),".format(line, json.dumps(token), reason_literal)

    lines = text.splitlines(keepends=True)
    insert_at = None
    indent = "        "
    for key_node, value_node in zip(dict_node.keys, dict_node.values):
        if isinstance(key_node, ast.Constant) and key_node.value == rel:
            insert_at = value_node.end_lineno  # 1-based line of the closing "]"
            break
    if insert_at is not None:
        new_lines = lines[:insert_at] + [indent + comment + "\n", tuple_line + "\n"] + lines[insert_at:]
    else:
        # New file key: append a block just before the dict's closing "}".
        insert_at = dict_node.end_lineno
        block = [
            "    # pins register {0} (FIX-462): new file-key block — the file "
            "had no exemptions yet".format(op_id),
            '    "{0}": ['.format(rel),
            "        " + comment,
            tuple_line,
            "    ],",
        ]
        new_lines = lines[:insert_at - 1] + [b + "\n" for b in block] + lines[insert_at - 1:]
    candidate = "".join(new_lines)

    if dry_run:
        receipt.update({"code": "ok", "error": False, "effect": "dry_run",
                        "operation_id": op_id,
                        "planned_hunk": [comment, tuple_line]})
        return receipt, 0

    ok, detail, post_checks = _atomic_write_with_postcheck(
        root, ledger_path, original_bytes, candidate, rel, line, token)
    if ok is False:
        return refuse(detail)
    if ok is None:  # retryable
        _restore(ledger_path, original_bytes)
        receipt.update({"code": "retryable", "error": True, "detail": detail,
                        "post_checks": post_checks})
        return receipt, 3
    # FIX-464: the touched row leaves the delivery amnesty in the same
    # transaction — a failure restores BOTH files (ledger + pin_ledger).
    sync_state, sync_err = _sync_amnesty_exit(
        root, rel, line, token, "register", op_id)
    if sync_err is not None:
        _restore(ledger_path, original_bytes)
        return refuse("amnesty exit sync failed: {0}".format(sync_err))
    receipt.update({"code": "ok", "error": False, "effect": "written",
                    "operation_id": op_id, "detail": detail,
                    "post_checks": post_checks, "amnesty_sync": sync_state})
    return receipt, 0


# ── re-anchor ───────────────────────────────────────────────────────────────


def reanchor_exemption(root: Path, file: str, line_from: int, line_to: int,
                       token: str = None, *, dry_run: bool = False):
    """Migrate one entry's line number (pure re-anchor, token unchanged)."""
    receipt = {"schema": SCHEMA, "command": "pins re-anchor", "task": TASK_ID,
               "file": file, "from": line_from, "to": line_to, "token": token,
               "dry_run": dry_run}

    def refuse(detail):
        receipt.update({"code": "refused", "error": True, "detail": detail})
        return receipt, 2

    rel = _normalized_rel(file)
    if line_from < 1 or line_to < 1:
        return refuse("line numbers must be >= 1")
    if line_from == line_to:
        return refuse("--from and --to are identical (nothing to re-anchor)")

    root = _repo_root(root)
    ledger_path = _ledger_path(root)
    if not ledger_path.is_file():
        return refuse("ledger not found: {0}".format(LEDGER_REL))
    original_bytes = ledger_path.read_bytes()
    text = original_bytes.decode("utf-8")

    parsed, err = _parse_ledger(text)
    if err:
        return refuse("ledger unreadable: {0}".format(err))
    _tree, dict_node = parsed

    entries = [(k, elem, ln, tok) for k, elem, ln, tok in _entry_tuples(dict_node)
               if k == rel and ln == line_from]
    if token is not None:
        entries = [e for e in entries if e[3] == token]
    if not entries:
        # Idempotency: already anchored at the target line?
        already = [e for e in _entry_tuples(dict_node)
                   if e[0] == rel and e[2] == line_to
                   and (token is None or e[3] == token)]
        if already:
            receipt.update({"code": "ok", "error": False,
                            "effect": "idempotent_noop",
                            "detail": "entry already anchored at line {0}".format(line_to)})
            # FIX-464 self-heal: an earlier write may have drifted the
            # amnesty set (the FIX-462 writer gap) — the noop path still
            # runs the exit sync so re-running the command repairs the
            # ghost row without a ledger byte change.
            sync_state, _sync_err = _sync_amnesty_exit(
                root, rel, line_from,
                token if token is not None else already[0][3],
                "re-anchor", _new_op_id())
            receipt["amnesty_sync"] = sync_state
            return receipt, 0
        return refuse("no exemption entry at {0}:{1}{2}".format(
            rel, line_from, " with token \"{0}\"".format(token) if token else ""))
    if len(entries) > 1:
        return refuse("ambiguous entries at {0}:{1} (tokens {2}) — pass --token".format(
            rel, line_from, ", ".join(sorted({e[3] for e in entries}))))
    _k, elem, _ln, entry_token = entries[0]

    # Token-content search validation: the token now lives on --to, not --from.
    carries_to, detail = _target_line_carries(root, rel, line_to, entry_token)
    if not carries_to:
        return refuse("--to invalid: {0}".format(detail))
    from_lines = (_repo_root(root) / rel).read_text(encoding="utf-8").splitlines()
    if line_from <= len(from_lines) and entry_token in _line_tokens(from_lines[line_from - 1]):
        return refuse("--from line {0} still carries the token — nothing drifted; "
                      "refusing to move a live anchor".format(line_from))

    first = elem.elts[0]
    if first.lineno != elem.lineno:
        return refuse("multi-line tuple entries are unsupported (found at ledger "
                      "line {0})".format(elem.lineno))
    lines = text.splitlines(keepends=True)
    idx = elem.lineno - 1
    raw = lines[idx]
    replacement = (raw[:first.col_offset] + str(line_to)
                   + raw[first.end_col_offset:])
    if raw.endswith("\n") and not replacement.endswith("\n"):
        replacement += "\n"

    op_id = _new_op_id()
    comment = ("# pins re-anchor {0} (FIX-462): {1}->{2} via machine writer "
               "(token unchanged)".format(op_id, line_from, line_to))
    comment_idx = idx - 1
    prefix_indent = raw[:len(raw) - len(raw.lstrip())]
    if comment_idx >= 0 and _PROVENANCE_RE.search(lines[comment_idx]):
        lines[comment_idx] = prefix_indent + comment + "\n"
        lines[idx] = replacement
    else:
        lines[idx] = replacement
        lines.insert(idx, prefix_indent + comment + "\n")
    candidate = "".join(lines)

    if dry_run:
        receipt.update({"code": "ok", "error": False, "effect": "dry_run",
                        "operation_id": op_id,
                        "planned_hunk": [comment, replacement.rstrip("\n")]})
        return receipt, 0

    ok, detail, post_checks = _atomic_write_with_postcheck(
        root, ledger_path, original_bytes, candidate, rel, line_to, entry_token)
    if ok is False:
        return refuse(detail)
    if ok is None:
        _restore(ledger_path, original_bytes)
        receipt.update({"code": "retryable", "error": True, "detail": detail,
                        "post_checks": post_checks})
        return receipt, 3
    # FIX-464: the FROM row leaves the delivery amnesty in the same
    # transaction — failure restores BOTH files (ledger + pin_ledger).
    sync_state, sync_err = _sync_amnesty_exit(
        root, rel, line_from, entry_token, "re-anchor", op_id)
    if sync_err is not None:
        _restore(ledger_path, original_bytes)
        return refuse("amnesty exit sync failed: {0}".format(sync_err))
    receipt.update({"code": "ok", "error": False, "effect": "written",
                    "operation_id": op_id, "token": entry_token,
                    "detail": detail, "post_checks": post_checks,
                    "amnesty_sync": sync_state})
    return receipt, 0


# ── write-guard face 6 (attribution) ────────────────────────────────────────

#: Delivery amnesty (FIX-462): the 55 hand-written rows that existed when
#: the machine writer landed. Rows leave this set the moment the writer
#: touches them (their provenance comment then carries the attribution);
#: NEW rows without a provenance comment warn on the guard face. Same
#: semantics as the row-families first-sight baseline amnesty (FEAT-057),
#: frozen in-source so the face never reads guard state.
DELIVERY_AMNESTY_ENTRIES = frozenset({
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 116, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 120, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 121, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 122, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 212, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 216, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 217, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 319, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 322, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 326, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 331, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 336, "0.84.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 331, "0.99.0"),
    ("skills/software-project-governance/infra/tests/test_bootstrap_aggregate.py", 123, "0.85.0"),
    ("skills/software-project-governance/infra/tests/test_baseline_metadata.py", 63, "0.85.0"),
    ("skills/software-project-governance/infra/tests/test_baseline_metadata.py", 318, "0.85.0"),
    ("skills/software-project-governance/infra/tests/test_baseline_metadata.py", 395, "0.85.0"),
    ("skills/software-project-governance/infra/tests/test_baseline_metadata.py", 566, "0.85.0"),
    ("skills/software-project-governance/infra/tests/test_baseline_metadata.py", 623, "0.85.0"),
    ("skills/software-project-governance/infra/tests/test_baseline_metadata.py", 741, "0.85.0"),
    ("skills/software-project-governance/infra/tests/test_baseline_metadata.py", 383, "0.86.0"),
    ("skills/software-project-governance/infra/tests/test_task_row_update.py", 74, "0.85.0"),
    ("skills/software-project-governance/infra/tests/test_task_row_update.py", 76, "0.85.0"),
    ("skills/software-project-governance/infra/tests/test_task_row_update.py", 59, "0.86.0"),
    ("skills/software-project-governance/infra/tests/test_task_row_update.py", 68, "0.86.0"),
    ("skills/software-project-governance/infra/tests/test_task_row_update.py", 203, "0.86.0"),
    ("skills/software-project-governance/infra/tests/test_task_row_update.py", 421, "0.86.0"),
    ("skills/software-project-governance/infra/tests/test_task_row_update.py", 441, "0.86.0"),
    ("skills/software-project-governance/infra/tests/test_task_row_update.py", 586, "0.86.0"),
    ("skills/software-project-governance/infra/tests/test_task_row_update.py", 597, "0.86.0"),
    ("skills/software-project-governance/infra/tests/test_closure_chain.py", 86, "0.86.0"),
    ("skills/software-project-governance/infra/tests/test_triage_write_guard.py", 997, "0.86.0"),
    ("skills/software-project-governance/infra/tests/test_triage_write_guard.py", 1143, "0.86.0"),
    # pins re-anchor op-0d25848adfe445ae9b8cb515b7f036ca (FIX-464): writer touched (skills/software-project-governance/infra/tests/test_static_version_pins.py, 166, "0.85.0") — row left DELIVERY_AMNESTY_ENTRIES
    ("skills/software-project-governance/infra/tests/test_release_projection.py", 35, "0.87.0"),
    ("skills/software-project-governance/infra/tests/test_provenance_domain.py", 323, "0.93.0"),
    ("skills/software-project-governance/infra/tests/test_provenance_domain.py", 342, "0.93.0"),
    # pins re-anchor op-e074d2043855458c93570f778c026b89 (FIX-464): writer touched (skills/software-project-governance/infra/tests/test_verify_workflow.py, 21309, "0.93.0") — row left DELIVERY_AMNESTY_ENTRIES
    # pins re-anchor op-6ad5349fce3c4a6db28a8e5bfc6fc278 (FIX-464): writer touched (skills/software-project-governance/infra/tests/test_verify_workflow.py, 21341, "0.93.0") — row left DELIVERY_AMNESTY_ENTRIES
    # pins re-anchor op-493e21b7822b433eb69cb0ed4dfbefc0 (FIX-464): writer touched (skills/software-project-governance/infra/tests/test_verify_workflow.py, 20808, "0.94.0") — row left DELIVERY_AMNESTY_ENTRIES
    # pins re-anchor op-b81c0a2b03d245518cf7d592d513c4fd (FIX-464): writer touched (skills/software-project-governance/infra/tests/test_verify_workflow.py, 20811, "0.94.0") — row left DELIVERY_AMNESTY_ENTRIES
    ("skills/software-project-governance/infra/tests/test_archive.py", 5870, "0.95.0"),
    ("skills/software-project-governance/infra/tests/test_archive.py", 549, "0.99.0"),
    ("skills/software-project-governance/infra/tests/test_archive.py", 724, "0.99.0"),
    ("skills/software-project-governance/infra/tests/test_archive.py", 4005, "0.99.0"),
    # pins re-anchor op-ababe4456fb347b2b8c5f4d88b160ecd (FIX-464): writer touched (skills/software-project-governance/infra/tests/test_evidence_migration.py, 80, "0.99.0") — row left DELIVERY_AMNESTY_ENTRIES
    ("skills/software-project-governance/infra/tests/test_fix390_structured_status_judgment.py", 190, "0.89.0"),
    ("skills/software-project-governance/infra/tests/test_fix390_structured_status_judgment.py", 202, "0.89.0"),
    ("skills/software-project-governance/infra/tests/test_fix390_structured_status_judgment.py", 306, "0.89.0"),
    ("skills/software-project-governance/infra/tests/test_fix393_writer_terminal_states.py", 103, "0.89.0"),
    ("skills/software-project-governance/infra/tests/test_fix393_writer_terminal_states.py", 174, "0.89.0"),
    ("skills/software-project-governance/infra/tests/test_fix393_writer_terminal_states.py", 311, "0.89.0"),
    ("skills/software-project-governance/infra/tests/test_fix393_writer_terminal_states.py", 313, "0.89.0"),
    ("skills/software-project-governance/infra/tests/test_fix394_progress_suffix_refresh.py", 115, "0.89.0"),
    ("skills/software-project-governance/infra/tests/test_fix394_progress_suffix_refresh.py", 529, "0.89.0"),
})


def exemption_face_issues(root: Path):
    """Face 6 issues over the ledger source (never raises).

    FAIL-class: ledger missing/unparseable, malformed entries, keys outside
    the scan dir. WARN-class: an entry neither covered by the delivery
    amnesty nor carrying a ``pins`` provenance comment directly above its
    tuple (the hand-edit alarm).
    """
    ledger_path = _ledger_path(root)
    if not ledger_path.is_file():
        return [], "SKIPPED"
    try:
        text = ledger_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [{"type": "pin_ledger_unreadable", "line": None,
                 "detail": "checks/version.py unreadable: {0}".format(exc)}], "FAIL"
    parsed, err = _parse_ledger(text)
    if err:
        return [{"type": "pin_ledger_unparseable", "line": None,
                 "detail": err}], "FAIL"
    _tree, dict_node = parsed
    lines = text.splitlines()
    issues = []
    status = "PASS"
    for key_node, value_node in zip(dict_node.keys, dict_node.values):
        key = key_node.value if isinstance(key_node, ast.Constant) else None
        if not isinstance(key, str):
            issues.append({"type": "pin_ledger_malformed_key", "line": key_node.lineno,
                           "detail": "non-string ledger key"})
            status = "FAIL"
            continue
        if not key.startswith(SCAN_DIR_REL + "/"):
            issues.append({"type": "pin_ledger_key_outside_scan_dir", "line": key_node.lineno,
                           "detail": "ledger key outside {0}: {1}".format(SCAN_DIR_REL, key)})
            status = "FAIL"
        if not isinstance(value_node, ast.List):
            issues.append({"type": "pin_ledger_malformed_list", "line": key_node.lineno,
                           "detail": "ledger value for {0} is not a list".format(key)})
            status = "FAIL"
            continue
        for elem in value_node.elts:
            if not (isinstance(elem, ast.Tuple) and len(elem.elts) == 3
                    and isinstance(elem.elts[0], ast.Constant)
                    and isinstance(elem.elts[0].value, int)
                    and isinstance(elem.elts[1], ast.Constant)
                    and isinstance(elem.elts[1].value, str)):
                issues.append({"type": "pin_ledger_malformed_entry", "line": elem.lineno,
                               "detail": "entry is not (int, str, reason) at {0}".format(key)})
                status = "FAIL"
                continue
            entry = (key, elem.elts[0].value, elem.elts[1].value)
            if entry in DELIVERY_AMNESTY_ENTRIES:
                continue
            above = lines[elem.lineno - 2] if elem.lineno >= 2 else ""
            if _PROVENANCE_RE.search(above):
                continue
            issues.append({
                "type": "pin_ledger_unattributed",
                "line": elem.lineno,
                "detail": ("exemption {0}:{1} (\"{2}\") has no pins provenance "
                           "comment and is not in the FIX-462 delivery amnesty — "
                           "hand edit? use `pins register/re-anchor` "
                           "(TRIAGE-FIX-462, DEC-220)").format(key, elem.elts[0].value,
                                                               elem.elts[1].value),
            })
    return issues, status


# ── CLI (engine wires dispatch only) ────────────────────────────────────────


def _resolve_root(args):
    explicit = getattr(args, "project_root", None)
    return Path(explicit).resolve() if explicit else Path(__file__).resolve().parents[3]


def add_register_arguments(parser):
    parser.add_argument("--file", required=True,
                        help="repo-relative test file carrying the pin (under infra/tests)")
    parser.add_argument("--line", type=int, required=True,
                        help="1-based line number carrying the token")
    parser.add_argument("--token", required=True,
                        help="the semver token to exempt (must be the active version)")
    parser.add_argument("--reason", required=True,
                        help="_REASON_* name defined in the ledger, or free text")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate and preview the hunk without writing")


def add_reanchor_arguments(parser):
    parser.add_argument("--file", required=True,
                        help="repo-relative test file of the exemption entry")
    parser.add_argument("--from", dest="line_from", type=int, required=True,
                        help="the entry's current (drifted) line number in the ledger")
    parser.add_argument("--to", dest="line_to", type=int, required=True,
                        help="the token's actual line number now")
    parser.add_argument("--token", default=None,
                        help="disambiguate when the --from line held several entries")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate and preview the hunk without writing")


def add_arguments(pins_parser):
    sub = pins_parser.add_subparsers(dest="pins_command", metavar="{register,re-anchor}")
    reg = sub.add_parser(
        "register", help="register one reasoned (line, token, reason) exemption "
                         "(fail-closed; effect-idempotent; --dry-run preview)")
    add_register_arguments(reg)
    rea = sub.add_parser(
        "re-anchor", help="migrate one entry's line number after drift "
                          "(token-content verified; --dry-run preview)")
    add_reanchor_arguments(rea)


def cmd_pins(args):
    root = _resolve_root(args)
    pins_command = getattr(args, "pins_command", None)
    if pins_command == "register":
        receipt, code = register_exemption(
            root, args.file, args.line, args.token, args.reason,
            dry_run=bool(getattr(args, "dry_run", False)))
    elif pins_command == "re-anchor":
        receipt, code = reanchor_exemption(
            root, args.file, args.line_from, args.line_to,
            token=args.token, dry_run=bool(getattr(args, "dry_run", False)))
    else:
        receipt = {"schema": SCHEMA, "command": "pins", "task": TASK_ID,
                   "code": "refused", "error": True,
                   "detail": "missing pins subcommand (register|re-anchor)"}
        code = 2
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return code
