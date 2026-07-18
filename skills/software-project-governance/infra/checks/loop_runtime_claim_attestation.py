"""Independent three-root Loop runtime identity attestor (FIX-216).

This leaf intentionally has no dependency on the semantic scanner.  It owns a
second Git/filesystem inventory, byte accounting, canonical attestation, and
the single staged-index to commit-tree comparison relation.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import math
import os
import re
import stat
import subprocess
import tokenize
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence


ROOT_SOURCE_SCHEMA = "loop-root-source/v1"
GIT_ROOT_SCHEMA = "loop-git-repository-tree/v1"
HOST_SNAPSHOT_SCHEMA = "loop-immutable-workspace-snapshot/v1"
IDENTITY_SCHEMA = "loop-identity-attestation/v1"
AGGREGATE_SCHEMA = "loop-claim-aggregate/v1"
SEMANTIC_SCHEMA = "loop-semantic-claim-report/v1"
ACCOUNTING_CONTRACT = "loop-semantic-accounting/v1"
ROLE_ORDER = {"product_root": 0, "plugin_home": 1, "host_root": 2}
SUPPORTED_EXTENSIONS = {".md": "markdown", ".py": "python", ".json": "json"}
HOST_PATHS = (
    ".governance/plan-tracker.md",
    ".governance/session-snapshot.md",
    ".governance/evidence-log.md",
    ".governance/risk-log.md",
)
POLICY_PATH = "core/loop-runtime-claim-allowlist.json"
AUTHORITY_PATH = "core/loop-runtime-claim-authority.json"
ADR_SNAPSHOT_PATH = "docs/architecture/ADR-011-loop-runtime-claim-correction.md"
ADR_DIGEST_RE = re.compile(r"(?m)^(inventory_sha256: )[0-9a-f]{64}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
HEX_OID_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
I1_FIELDS = frozenset({
    "schema_version", "phase", "scan_mode", "subject", "bindings",
    "source_envelope_sha256", "required_paths_digest", "accounting_contract",
    "accounting", "identity_verdict", "created_at",
})


class IdentityAttestationError(ValueError):
    """Typed fail-closed identity error."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class _Record:
    role: str
    path: str
    mode: int
    raw: bytes
    object_id: str | None = None

    @property
    def size(self) -> int:
        return len(self.raw)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.raw).hexdigest()


def _normalized(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise IdentityAttestationError("TYPE_DRIFT", "NaN/Infinity JSON is forbidden")
        return value
    if isinstance(value, list):
        return [_normalized(item) for item in value]
    if isinstance(value, tuple):
        return [_normalized(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise IdentityAttestationError("TYPE_DRIFT", "object keys must be strings")
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in result:
                raise IdentityAttestationError("DUPLICATE", normalized_key)
            result[normalized_key] = _normalized(item)
        return result
    raise IdentityAttestationError("TYPE_DRIFT", type(value).__name__)


def canonical_json_bytes(value: Any) -> bytes:
    """Return the strict canonical UTF-8 JSON encoding with one trailing LF."""
    return (
        json.dumps(
            _normalized(value), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def _strict_json(raw: bytes) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise IdentityAttestationError("CANONICAL_BYTES", "BOM forbidden")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise IdentityAttestationError("CANONICAL_BYTES", str(exc)) from exc

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise IdentityAttestationError("DUPLICATE", key)
            result[key] = value
        return result

    try:
        return json.loads(
            text, object_pairs_hook=pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                IdentityAttestationError("TYPE_DRIFT", value)
            ),
        )
    except IdentityAttestationError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise IdentityAttestationError("CANONICAL_BYTES", str(exc)) from exc


def is_canonical_json(raw: bytes) -> bool:
    try:
        return canonical_json_bytes(_strict_json(raw)) == raw
    except (IdentityAttestationError, TypeError, ValueError):
        return False


def _digest_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)[:-1]).hexdigest()


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_relative(value: str) -> str:
    if not isinstance(value, str):
        raise IdentityAttestationError("TYPE_DRIFT", "path must be string")
    normalized = unicodedata.normalize("NFC", value.replace("\\", "/"))
    pure = PurePosixPath(normalized)
    if (
        not normalized or pure.is_absolute() or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized)
        or any(part in {"", ".", ".."} for part in pure.parts)
        or pure.as_posix() != normalized.rstrip("/")
    ):
        raise IdentityAttestationError("ROOT_SOURCE_AMBIGUOUS", value)
    return pure.as_posix()


def _safe_prefix(value: str) -> str:
    if value == "":
        return ""
    return _safe_relative(value)


def _is_reparse(info: os.stat_result) -> bool:
    return bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _plain_root(path_value: str | os.PathLike[str], *, code: str = "ROOT_SOURCE_AMBIGUOUS") -> Path:
    lexical = Path(path_value).absolute()
    current = Path(lexical.anchor)
    for part in lexical.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", str(exc)) from exc
        if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
            raise IdentityAttestationError(code, f"alias/reparse component: {current}")
    try:
        info = lexical.lstat()
    except OSError as exc:
        raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", str(exc)) from exc
    if not stat.S_ISDIR(info.st_mode):
        raise IdentityAttestationError("ROOT_SOURCE_KIND_INVALID", str(lexical))
    return lexical.resolve(strict=True)


def _plain_regular(root: Path, relative: str) -> tuple[Path, os.stat_result]:
    current = root
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise IdentityAttestationError("REQUIRED_ROOT_UNAVAILABLE", relative) from exc
        if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
            raise IdentityAttestationError("ROOT_SOURCE_AMBIGUOUS", f"alias/reparse: {relative}")
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise IdentityAttestationError("ROOT_SOURCE_KIND_INVALID", relative)
    if not stat.S_ISREG(info.st_mode):
        raise IdentityAttestationError("REQUIRED_PATH_NOT_REGULAR", relative)
    return current, info


def _git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args], input=input_bytes,
            capture_output=True, check=False,
        )
    except OSError as exc:
        raise IdentityAttestationError("UNKNOWN", f"git unavailable: {exc}") from exc
    if completed.returncode:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", detail or "git command failed")
    return completed.stdout


def _git_text(repo: Path, *args: str) -> str:
    return _git(repo, *args).decode("utf-8", errors="strict").strip()


def _git_blobs(repo: Path, object_ids: Sequence[str]) -> list[bytes]:
    """Read an ordered blob set through one independent Git batch process."""
    if not object_ids:
        return []
    request = ("\n".join(object_ids) + "\n").encode("ascii")
    response = _git(repo, "cat-file", "--batch", input_bytes=request)
    cursor = 0
    blobs: list[bytes] = []
    for expected in object_ids:
        line_end = response.find(b"\n", cursor)
        if line_end < 0:
            raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", "truncated cat-file header")
        try:
            oid, object_type, size_text = response[cursor:line_end].decode("ascii").split(" ")
            size = int(size_text)
        except (UnicodeError, ValueError) as exc:
            raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", "invalid cat-file header") from exc
        if oid != expected or object_type != "blob" or size < 0:
            raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", "cat-file identity drift")
        start, end = line_end + 1, line_end + 1 + size
        if end >= len(response) or response[end:end + 1] != b"\n":
            raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", "truncated cat-file body")
        blobs.append(response[start:end])
        cursor = end + 1
    if cursor != len(response):
        raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", "unexpected cat-file bytes")
    return blobs


def _repository_root(repo_value: str | os.PathLike[str]) -> Path:
    repo = _plain_root(repo_value)
    root = Path(_git_text(repo, "rev-parse", "--show-toplevel"))
    root = _plain_root(root)
    if repo != root and root not in repo.parents:
        raise IdentityAttestationError("ROOT_SOURCE_AMBIGUOUS", "repository locator mismatch")
    return root


def _resolve_git_tree(repo: Path, ref: str, *, allow_tree: bool) \
        -> tuple[str, str, str, str | None]:
    object_format = _git_text(repo, "rev-parse", "--show-object-format")
    if object_format not in {"sha1", "sha256"}:
        raise IdentityAttestationError("SCHEMA_UNKNOWN", f"object format {object_format}")
    resolved_commit: str | None = None
    if ref == ":index":
        root_tree = _git_text(repo, "write-tree")
        source_kind = "index"
    else:
        if not isinstance(ref, str) or not ref or ref.startswith("-"):
            raise IdentityAttestationError("ROOT_SOURCE_AMBIGUOUS", "invalid Git ref")
        commit_probe = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", f"{ref}^{{commit}}"],
            capture_output=True, check=False,
        )
        if commit_probe.returncode == 0:
            commit = commit_probe.stdout.decode("ascii", errors="strict").strip()
            if not HEX_OID_RE.fullmatch(commit):
                raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", "invalid commit OID")
            resolved_commit = commit
            root_tree = _git_text(repo, "rev-parse", "--verify", f"{commit}^{{tree}}")
            source_kind = "commit"
        elif allow_tree:
            root_tree = _git_text(repo, "rev-parse", "--verify", f"{ref}^{{tree}}")
            source_kind = "tree"
        else:
            detail = commit_probe.stderr.decode("utf-8", errors="replace").strip()
            raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", detail or "commit unavailable")
    if not HEX_OID_RE.fullmatch(root_tree):
        raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", "invalid root tree OID")
    return object_format, root_tree, source_kind, resolved_commit


def _git_records(repo: Path, root_tree: str, prefix: str, role: str) -> tuple[list[_Record], str]:
    selected = root_tree
    if prefix:
        selected = _git_text(repo, "rev-parse", "--verify", f"{root_tree}:{prefix}")
    raw_listing = _git(repo, "ls-tree", "-r", "-z", "--full-tree", root_tree, "--", prefix or ".")
    descriptors: list[tuple[str, int, str]] = []
    prefix_token = prefix + "/" if prefix else ""
    for row in raw_listing.split(b"\0"):
        if not row:
            continue
        try:
            metadata, path_bytes = row.split(b"\t", 1)
            mode_text, object_type, oid = metadata.decode("ascii").split(" ")
            full_path = path_bytes.decode("utf-8", errors="strict")
        except (ValueError, UnicodeError) as exc:
            raise IdentityAttestationError("ROOT_SOURCE_UNAVAILABLE", "invalid ls-tree record") from exc
        if object_type != "blob" or mode_text not in {"100644", "100755"}:
            raise IdentityAttestationError("REQUIRED_PATH_NOT_REGULAR", full_path)
        if prefix_token and not full_path.startswith(prefix_token):
            raise IdentityAttestationError("ROOT_SOURCE_AMBIGUOUS", full_path)
        relative = full_path[len(prefix_token):] if prefix_token else full_path
        normalized = _safe_relative(relative)
        descriptors.append((normalized, int(mode_text, 8), oid))
    bodies = _git_blobs(repo, [oid for _path, _mode, oid in descriptors])
    records = [
        _Record(role, path, mode, body, oid)
        for (path, mode, oid), body in zip(descriptors, bodies, strict=True)
    ]
    records.sort(key=lambda item: item.path.encode("utf-8"))
    return records, selected


def _record_projection(record: _Record, *, include_oid: bool) -> dict[str, Any]:
    result = {
        "mode": record.mode,
        "path": record.path,
        "sha256": record.sha256,
        "size": record.size,
    }
    if include_oid:
        result["object_id"] = record.object_id
    return result


def _git_binding(repo_value: str | os.PathLike[str], ref: str, prefix_value: str,
                 role: str) -> tuple[dict[str, Any], list[_Record], str, str | None]:
    repo = _repository_root(repo_value)
    prefix = _safe_prefix(prefix_value)
    object_format, root_tree, source_kind, resolved_commit = _resolve_git_tree(
        repo, ref, allow_tree=role == "plugin_home"
    )
    records, selected_tree = _git_records(repo, root_tree, prefix, role)
    record_rows = [_record_projection(record, include_oid=True) for record in records]
    binding = {
        "role": role,
        "repository_identity": {
            "schema_version": GIT_ROOT_SCHEMA,
            "object_format": object_format,
            "repository_root_tree_oid": root_tree,
        },
        "tree_prefix": prefix,
        "selected_tree_oid": selected_tree,
        "records_digest": _digest_json(record_rows),
    }
    return binding, records, source_kind, resolved_commit


def _snapshot_host(root_value: str | os.PathLike[str], snapshot_value: str | os.PathLike[str],
                   extra_paths: Iterable[str] = ()) \
        -> tuple[dict[str, Any], list[_Record]]:
    root = _plain_root(root_value)
    snapshot_lexical = Path(snapshot_value).absolute()
    if snapshot_lexical == root or root in snapshot_lexical.parents or snapshot_lexical in root.parents:
        raise IdentityAttestationError("ROOT_SOURCE_AMBIGUOUS", "snapshot must be outside host root")
    if snapshot_lexical.exists():
        raise IdentityAttestationError("ROOT_SOURCE_AMBIGUOUS", "snapshot directory already exists")
    snapshot_lexical.mkdir(parents=True)
    snapshot = _plain_root(snapshot_lexical)
    records: list[_Record] = []
    snapshot_paths = sorted(
        {*(unicodedata.normalize("NFC", path) for path in HOST_PATHS),
         *(_safe_relative(path) for path in extra_paths)},
        key=lambda item: item.encode("utf-8"),
    )
    for relative in snapshot_paths:
        lexical, info = _plain_regular(root, relative)
        if getattr(info, "st_nlink", 1) != 1:
            raise IdentityAttestationError("ROOT_SOURCE_AMBIGUOUS", f"hardlink: {relative}")
        raw = lexical.read_bytes()
        after = lexical.lstat()
        stable_fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(info, field, None) != getattr(after, field, None) for field in stable_fields):
            raise IdentityAttestationError("UNKNOWN", f"host file changed while reading: {relative}")
        destination = snapshot.joinpath(*PurePosixPath(relative).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        if destination.read_bytes() != raw:
            raise IdentityAttestationError("ROOT_SOURCE_BYTE_MISMATCH", relative)
        records.append(_Record("host_root", relative, stat.S_IMODE(info.st_mode), raw))
    records.sort(key=lambda item: item.path.encode("utf-8"))
    rows = [_record_projection(record, include_oid=False) for record in records]
    manifest_digest = _digest_json(rows)
    byte_stream = bytearray()
    for record in records:
        byte_stream.extend(len(record.raw).to_bytes(8, "big"))
        byte_stream.extend(record.raw)
    binding = {
        "role": "host_root",
        "schema_version": HOST_SNAPSHOT_SCHEMA,
        "manifest_digest": manifest_digest,
        "bytes_digest": hashlib.sha256(bytes(byte_stream)).hexdigest(),
        "records": rows,
    }
    (snapshot / "manifest.json").write_bytes(canonical_json_bytes(binding))
    return binding, records


def _canonical_text(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise IdentityAttestationError("ACCOUNTING_SERIALIZATION_ERROR", "unsupported BOM")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise IdentityAttestationError("ACCOUNTING_SERIALIZATION_ERROR", str(exc)) from exc
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))


def _canonical_content_sha(record: _Record) -> str:
    text = _canonical_text(record.raw)
    if record.role == "product_root" and record.path == ADR_SNAPSHOT_PATH:
        matches = list(ADR_DIGEST_RE.finditer(text))
        if len(matches) != 1:
            raise IdentityAttestationError("INDEPENDENT_CONTENT_MISMATCH", record.path)
        text = ADR_DIGEST_RE.sub(r"\g<1>" + ("0" * 64), text, count=1)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _source_locator(start_line: int, start_column: int, end_line: int, end_column: int) -> dict[str, Any]:
    return {"end_column": end_column, "end_line": end_line, "pointer": None, "role": None,
            "start_column": start_column, "start_line": start_line, "type": "source_span"}


def _pointer_locator(pointer: str, role: str) -> dict[str, Any]:
    return {"end_column": None, "end_line": None, "pointer": pointer, "role": role,
            "start_column": None, "start_line": None, "type": "json_pointer"}


def _context(kind: str, *, index: int | None = None, level: int | None = None,
             name: str | None = None, payload: str | None = None,
             pointer: str | None = None) -> dict[str, Any]:
    return {"index": index, "kind": kind, "level": level, "name": name,
            "payload": payload, "pointer": pointer}


def _unit(record: _Record, ordinal: int, kind: str, locator: dict[str, Any],
          contexts: list[dict[str, Any]], payload: str) -> dict[str, Any]:
    return {
        "context_chain": contexts, "kind": kind,
        "language": SUPPORTED_EXTENSIONS[Path(record.path).suffix.lower()],
        "locator": locator, "normalized_path": record.path,
        "normalized_payload": unicodedata.normalize("NFC", payload.strip(" \t\n")),
        "ordinal": ordinal, "root_owner": record.role,
    }


class _JsonNumber(str):
    pass


def _json_units(record: _Record, text: str) -> list[dict[str, Any]]:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise IdentityAttestationError("ACCOUNTING_JSON_DUPLICATE_KEY", key)
            result[key] = value
        return result

    try:
        data = json.loads(text, object_pairs_hook=pairs, parse_int=_JsonNumber,
                          parse_float=_JsonNumber,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except IdentityAttestationError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise IdentityAttestationError("ACCOUNTING_JSON_PARSE_ERROR", str(exc)) from exc
    units: list[dict[str, Any]] = []

    def escape(value: str) -> str:
        return value.replace("~", "~0").replace("/", "~1")

    def emit(kind: str, pointer: str, role: str, payload: str, contexts: list[dict[str, Any]]) -> None:
        units.append(_unit(record, len(units), kind, _pointer_locator(pointer, role), contexts, payload))

    def walk(value: Any, pointer: str, contexts: list[dict[str, Any]]) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_pointer = f"{pointer}/{escape(key)}"
                emit("json_key", child_pointer, "key", key, contexts)
                walk(child, child_pointer, contexts + [_context("json_key", payload=key, pointer=child_pointer)])
        elif isinstance(value, list):
            for index, child in enumerate(value):
                child_pointer = f"{pointer}/{index}"
                walk(child, child_pointer, contexts + [_context("json_array_index", index=index, pointer=child_pointer)])
        elif isinstance(value, _JsonNumber):
            emit("json_number", pointer, "value", str(value), contexts)
        elif isinstance(value, str):
            emit("json_string", pointer, "value", value, contexts)
        elif value is True or value is False:
            emit("json_boolean", pointer, "value", "true" if value else "false", contexts)
        elif value is None:
            emit("json_null", pointer, "value", "null", contexts)
        else:
            raise IdentityAttestationError("ACCOUNTING_JSON_PARSE_ERROR", "unsupported value")

    walk(data, "", [])
    return units


def _python_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _python_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _python_units(record: _Record, text: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(text, filename=record.path)
        comments = [token for token in tokenize.generate_tokens(io.StringIO(text).readline)
                    if token.type == tokenize.COMMENT] if "#" in text else []
    except (SyntaxError, tokenize.TokenError) as exc:
        raise IdentityAttestationError("ACCOUNTING_PYTHON_PARSE_ERROR", str(exc)) from exc
    nodes: list[ast.AST] = []
    parents: dict[ast.AST, ast.AST] = {}
    stack = [tree]
    while stack:
        parent = stack.pop()
        nodes.append(parent)
        children = list(ast.iter_child_nodes(parent))
        for child in children:
            parents[child] = parent
        stack.extend(reversed(children))
    pending: list[tuple[tuple[int, int, int, int], str, list[dict[str, Any]], str]] = []

    def containers(node: ast.AST) -> list[dict[str, Any]]:
        chain: list[dict[str, Any]] = []
        current = parents.get(node)
        while current is not None:
            if isinstance(current, ast.ClassDef):
                chain.append(_context("py_class", name=current.name))
            elif isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
                chain.append(_context("py_function", name=current.name))
            current = parents.get(current)
        return list(reversed(chain))

    for node in nodes:
        if not isinstance(node, (ast.Constant, ast.JoinedStr)):
            continue
        if isinstance(node, ast.Constant) and not isinstance(node.value, str):
            continue
        if isinstance(parents.get(node), ast.JoinedStr):
            continue
        if not all(hasattr(node, name) for name in ("lineno", "col_offset", "end_lineno", "end_col_offset")):
            raise IdentityAttestationError("ACCOUNTING_PYTHON_SPAN_ERROR")
        contexts = containers(node)
        ancestor = parents.get(node)
        while ancestor is not None and not isinstance(ancestor, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Call)):
            ancestor = parents.get(ancestor)
        if isinstance(ancestor, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = ancestor.targets if isinstance(ancestor, ast.Assign) else [ancestor.target]
            for target in targets:
                name = _python_name(target)
                if name:
                    contexts.append(_context("binding", name=name))
        call = parents.get(node)
        while call is not None and not isinstance(call, ast.Call):
            call = parents.get(call)
        if isinstance(call, ast.Call):
            name = _python_name(call.func)
            if name:
                contexts.append(_context("call", name=name))
            child = node
            while parents.get(child) is not call and parents.get(child) is not None:
                child = parents[child]
            for index, argument in enumerate(call.args):
                if argument is child:
                    contexts.append(_context("parameter_index", index=index))
                    break
            else:
                for keyword in call.keywords:
                    if keyword.value is child:
                        contexts.append(_context("parameter_name", name=keyword.arg))
                        break
        if isinstance(node, ast.Constant):
            payload = node.value
        else:
            pieces: list[str] = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    pieces.append(value.value)
                elif isinstance(value, ast.FormattedValue):
                    pieces.append("{EXPR}")
                    name = _python_name(value.value)
                    if name:
                        contexts.append(_context("formatted_binding", name=name))
            payload = "".join(pieces)
        pending.append(((node.lineno - 1, node.col_offset, node.end_lineno - 1, node.end_col_offset),
                        "py_string", contexts, payload))
    for token in comments:
        pending.append(((token.start[0] - 1, token.start[1], token.end[0] - 1, token.end[1]),
                        "py_comment", [], token.string[1:]))
    pending.sort(key=lambda item: item[0])
    return [_unit(record, ordinal, kind, _source_locator(*span), contexts, payload)
            for ordinal, (span, kind, contexts, payload) in enumerate(pending)
            if payload.strip(" \t\n")]


def _split_markdown_cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    first_pipe, last_pipe = body.find("|"), body.rfind("|")
    protected_pipe = "\\|" in body
    if first_pipe >= 0 and first_pipe != last_pipe:
        for marker, closing in (("`", "`"), ('"', '"'), ("<", ">")):
            start, end = body.find(marker), body.rfind(closing)
            if start >= 0 and start < last_pipe and end > first_pipe:
                protected_pipe = True
                break
    if not protected_pipe:
        return [cell.strip(" \t") for cell in body.split("|")]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    code_delimiter = 0
    quoted = False
    angle_literal = False
    position = 0
    while position < len(body):
        character = body[position]
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            current.append(character)
            escaped = True
        elif character == "`":
            end = position
            while end < len(body) and body[end] == "`":
                end += 1
            run = end - position
            current.extend("`" * run)
            if code_delimiter == 0:
                code_delimiter = run
            elif code_delimiter == run:
                code_delimiter = 0
            position = end - 1
        elif character == '"' and code_delimiter == 0:
            current.append(character)
            quoted = not quoted
        elif character == "<" and code_delimiter == 0 and not quoted and position > 0 \
                and body[position - 1].isalnum() and ">" in body[position + 1:]:
            current.append(character)
            angle_literal = True
        elif character == ">" and angle_literal:
            current.append(character)
            angle_literal = False
        elif character == "|" and code_delimiter == 0 and not quoted and not angle_literal:
            cells.append("".join(current).strip(" \t"))
            current = []
        else:
            current.append(character)
        position += 1
    cells.append("".join(current).strip(" \t"))
    return cells


def _markdown_units(record: _Record, text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    units: list[dict[str, Any]] = []
    headings: list[tuple[int, str]] = []
    list_ancestors: list[tuple[int, str]] = []
    index = 0

    def emit(kind: str, start: int, end: int, payload: str,
             contexts: list[dict[str, Any]], start_column: int = 0,
             end_column: int | None = None) -> None:
        normalized = unicodedata.normalize("NFC", payload.strip(" \t\n"))
        if not normalized:
            return
        units.append(_unit(
            record, len(units), kind,
            _source_locator(start, start_column, end,
                            len(lines[end]) if end_column is None else end_column),
            contexts, normalized,
        ))

    def heading_context() -> list[dict[str, Any]]:
        return [_context("md_heading", level=level, payload=payload) for level, payload in headings]

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        atx = re.match(r"^\s*(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", line)
        setext = index + 1 < len(lines) and bool(re.match(r"^\s*(?:=+|-+)\s*$", lines[index + 1]))
        if atx or setext:
            list_ancestors.clear()
            level = len(atx.group(1)) if atx else (1 if "=" in lines[index + 1] else 2)
            payload = atx.group(2) if atx else stripped
            while headings and headings[-1][0] >= level:
                headings.pop()
            emit("md_heading", index, index if atx else index + 1, payload, heading_context(),
                 0, len(line) if atx else len(lines[index + 1]))
            headings.append((level, unicodedata.normalize("NFC", payload.strip(" \t"))))
            index += 1 if atx else 2
            continue
        fence = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence:
            list_ancestors.clear()
            if index > 0 and re.match(r"^\s*(`{3,}|~{3,})\s*$", lines[index - 1]):
                index += 1
                continue
            delimiter = fence.group(1)
            end = index + 1
            while end < len(lines) and not re.match(
                    rf"^\s*{re.escape(delimiter[0])}{{{len(delimiter)},}}\s*$", lines[end]):
                if lines[end].strip(" \t"):
                    emit("md_fence_line", end, end, lines[end], heading_context())
                end += 1
            if end >= len(lines):
                raise IdentityAttestationError(
                    "ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY", "unterminated fence"
                )
            index = end + 1
            continue
        if "<!--" in line:
            list_ancestors.clear()
            end = index
            body = line.split("<!--", 1)[1]
            while "-->" not in body:
                end += 1
                if end >= len(lines):
                    raise IdentityAttestationError(
                        "ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY", "unterminated comment"
                    )
                body += "\n" + lines[end]
            emit("md_comment", index, end, body.split("-->", 1)[0], heading_context())
            index = end + 1
            continue
        governance_record = re.match(r"^\s*\|\s*((?:EVD|REVIEW|QA)-[^|]+)\s*\|", line)
        if governance_record:
            list_ancestors.clear()
            cells = _split_markdown_cells(line)
            record_context = heading_context() + [
                _context("governance_record", payload=governance_record.group(1).strip())
            ]
            for payload in cells:
                emit("md_governance_record_cell", index, index, payload, record_context)
            index += 1
            continue
        if index + 1 < len(lines) and "|" in line and re.match(
            r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$", lines[index + 1]
        ):
            headers = _split_markdown_cells(line)
            normalized_headers = [header.casefold() for header in headers]
            if len(normalized_headers) != len(set(normalized_headers)):
                raise IdentityAttestationError(
                    "ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY", "duplicate table header"
                )
            list_ancestors.clear()
            for column, payload in enumerate(headers):
                emit("md_table_cell", index, index, payload, heading_context())
            row = index + 2
            while row < len(lines) and "|" in lines[row] and lines[row].strip():
                cells = _split_markdown_cells(lines[row])
                if len(cells) != len(headers):
                    raise IdentityAttestationError(
                        "ACCOUNTING_MARKDOWN_AMBIGUOUS_BOUNDARY", "ragged table row"
                    )
                row_header = cells[0] if cells and cells[0] else None
                for column, payload in enumerate(cells):
                    row_context = heading_context() + [
                        _context("md_table_header", index=column, payload=headers[column])
                    ]
                    if row_header and column:
                        row_context.append(_context("md_table_row_header", index=0, payload=row_header))
                    emit("md_table_cell", row, row, payload, row_context)
                row += 1
            index = row
            continue
        list_match = re.match(r"^(\s*)(?:[-*+] |\d+[.)] )(.*)$", line)
        if list_match:
            level = len(list_match.group(1).expandtabs(4))
            while list_ancestors and list_ancestors[-1][0] >= level:
                list_ancestors.pop()
            payload_lines = [list_match.group(2)]
            end = index
            while end + 1 < len(lines):
                continuation = lines[end + 1]
                if not continuation.strip() or re.match(
                    r"^\s*(?:#{1,6}[ \t]+|`{3,}|~{3,}|<!--)", continuation
                ) or re.match(r"^(\s*)(?:[-*+] |\d+[.)] )", continuation):
                    break
                indentation = len(continuation) - len(continuation.lstrip(" \t"))
                if indentation <= level:
                    break
                payload_lines.append(continuation.strip())
                end += 1
            payload = "\n".join(payload_lines)
            item_context = heading_context() + [
                _context("md_list_item", level=ancestor_level, payload=ancestor_payload)
                for ancestor_level, ancestor_payload in list_ancestors
            ]
            emit("md_list_item", index, end, payload, item_context, 0, len(lines[end]))
            list_ancestors.append((level, unicodedata.normalize("NFC", payload.strip(" \t\n"))))
            index = end + 1
            continue
        list_ancestors.clear()
        start = index
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not re.match(
            r"^\s*(?:#{1,6}[ \t]+|[-*+] |\d+[.)] |```|~~~|<!--)", lines[index]
        ):
            if index + 1 < len(lines) and re.match(r"^\s*(?:=+|-+)\s*$", lines[index + 1]):
                break
            paragraph.append(lines[index])
            index += 1
        emit("md_paragraph", start, start + len(paragraph) - 1,
             "\n".join(paragraph), heading_context())
    return units


def _candidate_records(product_records: Sequence[_Record], host_records: Sequence[_Record]) -> list[_Record]:
    result = [record for record in product_records
              if Path(record.path).suffix.lower() in SUPPORTED_EXTENSIONS
              and PurePosixPath(record.path).parts[0] in {"docs", "project", "skills"}]
    result.extend(record for record in host_records
                  if record.path in HOST_PATHS
                  and Path(record.path).suffix.lower() in SUPPORTED_EXTENSIONS)
    result.sort(key=lambda item: (ROLE_ORDER[item.role], item.path.encode("utf-8")))
    return result


def _independent_accounting(records: Sequence[_Record]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    summaries: dict[str, dict[str, Any]] = {}
    aggregate = hashlib.sha256()
    total_count = 0
    total_payload = 0
    for record in records:
        text = _canonical_text(record.raw)
        suffix = Path(record.path).suffix.lower()
        if suffix == ".json":
            units = _json_units(record, text)
        elif suffix == ".py":
            units = _python_units(record, text)
        elif suffix == ".md":
            units = _markdown_units(record, text)
        else:
            raise IdentityAttestationError("ACCOUNTING_CONTRACT_MISMATCH", record.path)
        serialized = b"".join(canonical_json_bytes(unit) for unit in units)
        key = f"{record.role}:{record.path}"
        payload_bytes = sum(len(unit["normalized_payload"].encode("utf-8")) for unit in units)
        summaries[key] = {
            "unit_count": len(units), "payload_bytes": payload_bytes,
            "record_sha256": hashlib.sha256(serialized).hexdigest(),
        }
        aggregate.update(serialized)
        total_count += len(units)
        total_payload += payload_bytes
    digest_rows = [
        {"path": path, "record_sha256": item["record_sha256"],
         "unit_count": item["unit_count"], "payload_bytes": item["payload_bytes"]}
        for path, item in sorted(summaries.items())
    ]
    accounting = {
        "record_count": total_count,
        "payload_bytes": total_payload,
        "record_digest": hashlib.sha256(json.dumps(
            digest_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest(),
        "aggregate_digest": aggregate.hexdigest(),
    }
    return accounting, summaries


def _control_digest(records: Sequence[_Record], path: str) -> str:
    matching = [record for record in records if record.path == path]
    if len(matching) != 1:
        raise IdentityAttestationError("REQUIRED_ROOT_UNAVAILABLE", f"plugin_home:{path}")
    value = _strict_json(matching[0].raw)
    return hashlib.sha256(json.dumps(
        _normalized(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def _scanner_compatible_envelope(scan_mode: str, candidates: Sequence[_Record],
                                 plugin_records: Sequence[_Record]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {role: [] for role in ROLE_ORDER}
    for record in candidates:
        grouped[record.role].append({
            "path": record.path, "raw_bytes": record.size,
            "sha256": _canonical_content_sha(record),
        })
    policy_sha = _control_digest(plugin_records, POLICY_PATH)
    authority_sha = _control_digest(plugin_records, AUTHORITY_PATH)
    bindings = []
    for role in ROLE_ORDER:
        rows = grouped[role]
        if role == "plugin_home":
            rows = [*rows, {"path": POLICY_PATH, "sha256": policy_sha},
                    {"path": AUTHORITY_PATH, "sha256": authority_sha}]
        bindings.append({"role": role, "records_digest": hashlib.sha256(json.dumps(
            rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()})
    return hashlib.sha256(json.dumps(
        {"schema_version": "loop-semantic-source-envelope/v1", "scan_mode": scan_mode,
         "bindings": bindings},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _required_records(required_paths: Iterable[tuple[str, str]],
                      records_by_role: dict[str, Sequence[_Record]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for role, path_value in required_paths:
        if role not in ROLE_ORDER:
            raise IdentityAttestationError("REQUIRED_ROOT_UNAVAILABLE", str(role))
        path = _safe_relative(path_value)
        key = (role, path)
        if key in seen:
            raise IdentityAttestationError("DUPLICATE", f"{role}:{path}")
        seen.add(key)
        matching = [record for record in records_by_role[role] if record.path == path]
        if len(matching) != 1:
            raise IdentityAttestationError("REQUIRED_ROOT_UNAVAILABLE", f"{role}:{path}")
        record = matching[0]
        rows.append({"root_owner": role, **_record_projection(record, include_oid=False)})
    rows.sort(key=lambda row: (ROLE_ORDER[row["root_owner"]], row["path"].encode("utf-8")))
    return rows


def _validate_phase_subject(phase: str, subject: dict[str, Any], source_kinds: Sequence[str],
                            product_commit: str | None) -> None:
    if phase == "staged_index":
        if subject != {"kind": "index", "sha": None} \
                or source_kinds[0] != "index" or source_kinds[1] not in {"index", "commit", "tree"}:
            raise IdentityAttestationError("PHASE_DRIFT", "staged_index requires index bindings")
    elif phase == "candidate_commit":
        sha = subject.get("sha") if isinstance(subject, dict) else None
        if set(subject) != {"kind", "sha"} or subject.get("kind") != "commit" \
                or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}(?:[0-9a-f]{24})?", sha):
            raise IdentityAttestationError("PHASE_DRIFT", "candidate_commit subject")
        if source_kinds[0] != "commit" or source_kinds[1] not in {"commit", "tree"}:
            raise IdentityAttestationError("PHASE_DRIFT", "candidate_commit requires commit bindings")
        if product_commit != sha:
            raise IdentityAttestationError(
                "SUBJECT_MISMATCH", "candidate subject does not match resolved product commit"
            )
    else:
        raise IdentityAttestationError("PHASE_DRIFT", phase)


def attest_explicit_sources(*, product_git_repo: str | os.PathLike[str], product_git_ref: str,
                            product_prefix: str, plugin_git_repo: str | os.PathLike[str],
                            plugin_git_ref: str, plugin_prefix: str,
                            host_root: str | os.PathLike[str], snapshot_dir: str | os.PathLike[str],
                            required_paths: Iterable[tuple[str, str]], phase: str,
                            subject: dict[str, Any], scan_mode: str = "product_release",
                            created_at: str | None = None) -> dict[str, Any]:
    """Resolve all three sources independently and return exact-schema I1."""
    if scan_mode != "product_release":
        raise IdentityAttestationError("PHASE_DRIFT", "identity attestation is release-mode only")
    product_repository_root = _repository_root(product_git_repo)
    plugin_repository_root = _repository_root(plugin_git_repo)
    host_repository_root = _plain_root(host_root)
    snapshot_lexical = Path(snapshot_dir).absolute()
    for source_root in {product_repository_root, plugin_repository_root, host_repository_root}:
        if snapshot_lexical == source_root or source_root in snapshot_lexical.parents \
                or snapshot_lexical in source_root.parents:
            raise IdentityAttestationError(
                "ROOT_SOURCE_AMBIGUOUS", "snapshot must be outside every scanned root"
            )
    product_binding, product_records, product_kind, product_commit = _git_binding(
        product_repository_root, product_git_ref, product_prefix, "product_root"
    )
    plugin_binding, plugin_records, plugin_kind, _plugin_commit = _git_binding(
        plugin_repository_root, plugin_git_ref, plugin_prefix, "plugin_home"
    )
    _validate_phase_subject(
        phase, subject, (product_kind, plugin_kind), product_commit
    )
    authority_records = [record for record in plugin_records if record.path == AUTHORITY_PATH]
    if len(authority_records) != 1:
        raise IdentityAttestationError("REQUIRED_ROOT_UNAVAILABLE", f"plugin_home:{AUTHORITY_PATH}")
    authority_payload = _strict_json(authority_records[0].raw)
    source_rows = authority_payload.get("source_records") if isinstance(authority_payload, dict) else None
    if not isinstance(source_rows, list):
        raise IdentityAttestationError("SCHEMA_MISSING", "authority source_records")
    extra_host_paths = []
    for row in source_rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            raise IdentityAttestationError("SCHEMA_UNKNOWN", "authority source record")
        extra_host_paths.append(row["path"])
    host_binding, host_records = _snapshot_host(
        host_repository_root, snapshot_dir, extra_host_paths
    )
    candidates = _candidate_records(product_records, host_records)
    accounting, _summaries = _independent_accounting(candidates)
    required = _required_records(required_paths, {
        "product_root": product_records,
        "plugin_home": plugin_records,
        "host_root": host_records,
    })
    timestamp = created_at or _now_utc()
    if not isinstance(timestamp, str) or not UTC_RE.fullmatch(timestamp):
        raise IdentityAttestationError("TYPE_DRIFT", "created_at must be UTC seconds")
    report = {
        "schema_version": IDENTITY_SCHEMA,
        "phase": phase,
        "scan_mode": scan_mode,
        "subject": subject,
        "bindings": {
            "product_root": product_binding,
            "plugin_home": plugin_binding,
            "host_root": host_binding,
        },
        "source_envelope_sha256": _scanner_compatible_envelope(scan_mode, candidates, plugin_records),
        "required_paths_digest": _digest_json(required),
        "accounting_contract": ACCOUNTING_CONTRACT,
        "accounting": accounting,
        "identity_verdict": "PASS",
        "created_at": timestamp,
    }
    validate_identity_attestation(report)
    return report


def attest_loop_runtime_identity(_context: Any, root_source_envelope: dict[str, Any],
                                 _limits: Any = None) -> dict[str, Any]:
    """Architecture-named entry point for an explicit source specification.

    The envelope is a caller-owned acquisition specification, never a scanner
    result.  No implicit current-directory or live-root fallback exists.
    """
    required = {
        "product_git_repo", "product_git_ref", "product_prefix", "plugin_git_repo",
        "plugin_git_ref", "plugin_prefix", "host_root", "snapshot_dir",
        "required_paths", "phase", "subject",
    }
    if not isinstance(root_source_envelope, dict) or not required.issubset(root_source_envelope):
        raise IdentityAttestationError("SCHEMA_MISSING", "explicit root source envelope")
    unknown = set(root_source_envelope) - (required | {"scan_mode", "created_at"})
    if unknown:
        raise IdentityAttestationError("SCHEMA_UNKNOWN", ",".join(sorted(unknown)))
    return attest_explicit_sources(**root_source_envelope)


def validate_identity_attestation(report: dict[str, Any]) -> None:
    if not isinstance(report, dict):
        raise IdentityAttestationError("TYPE_DRIFT", "I1 must be object")
    missing, unknown = I1_FIELDS - set(report), set(report) - I1_FIELDS
    if missing:
        raise IdentityAttestationError("SCHEMA_MISSING", ",".join(sorted(missing)))
    if unknown:
        raise IdentityAttestationError("SCHEMA_UNKNOWN", ",".join(sorted(unknown)))
    if report["schema_version"] != IDENTITY_SCHEMA:
        raise IdentityAttestationError("SCHEMA_UNKNOWN", str(report["schema_version"]))
    if report["phase"] not in {"staged_index", "candidate_commit"}:
        raise IdentityAttestationError("PHASE_DRIFT", str(report["phase"]))
    if report["scan_mode"] != "product_release":
        raise IdentityAttestationError("PHASE_DRIFT", str(report["scan_mode"]))
    subject = report["subject"]
    if not isinstance(subject, dict) or set(subject) != {"kind", "sha"}:
        raise IdentityAttestationError("SCHEMA_UNKNOWN", "subject")
    if report["phase"] == "staged_index":
        if subject != {"kind": "index", "sha": None}:
            raise IdentityAttestationError("PHASE_DRIFT", "staged subject")
    elif subject.get("kind") != "commit" or not isinstance(subject.get("sha"), str) \
            or not HEX_OID_RE.fullmatch(subject["sha"]):
        raise IdentityAttestationError("PHASE_DRIFT", "candidate subject")
    if not isinstance(report["bindings"], dict):
        raise IdentityAttestationError("TYPE_DRIFT", "bindings")
    if set(report["bindings"]) != set(ROLE_ORDER):
        raise IdentityAttestationError("ROOT_SOURCE_ROLE_MISSING", "exactly three bindings required")
    for role, binding in report["bindings"].items():
        if not isinstance(binding, dict) or binding.get("role") != role:
            raise IdentityAttestationError("ROOT_SOURCE_ROLE_MULTIPLE", role)
        if role in {"product_root", "plugin_home"}:
            if set(binding) != {
                "role", "repository_identity", "tree_prefix", "selected_tree_oid", "records_digest"
            }:
                raise IdentityAttestationError("SCHEMA_UNKNOWN", f"binding:{role}")
            repository_identity = binding["repository_identity"]
            if not isinstance(repository_identity, dict) or set(repository_identity) != {
                "schema_version", "object_format", "repository_root_tree_oid"
            } or repository_identity.get("schema_version") != GIT_ROOT_SCHEMA \
                    or repository_identity.get("object_format") not in {"sha1", "sha256"}:
                raise IdentityAttestationError("SCHEMA_UNKNOWN", f"repository_identity:{role}")
            oid_length = 40 if repository_identity["object_format"] == "sha1" else 64
            root_oid = repository_identity.get("repository_root_tree_oid")
            selected_oid = binding.get("selected_tree_oid")
            if not isinstance(root_oid, str) or not re.fullmatch(
                    rf"[0-9a-f]{{{oid_length}}}", root_oid):
                raise IdentityAttestationError("TYPE_DRIFT", f"repository_root_tree_oid:{role}")
            if not isinstance(selected_oid, str) or not re.fullmatch(
                    rf"[0-9a-f]{{{oid_length}}}", selected_oid):
                raise IdentityAttestationError("TYPE_DRIFT", f"selected_tree_oid:{role}")
            if not isinstance(binding.get("tree_prefix"), str):
                raise IdentityAttestationError("TYPE_DRIFT", f"tree_prefix:{role}")
            _safe_prefix(binding["tree_prefix"])
            if not isinstance(binding.get("records_digest"), str) \
                    or not HEX64_RE.fullmatch(binding["records_digest"]):
                raise IdentityAttestationError("TYPE_DRIFT", f"records_digest:{role}")
        else:
            if set(binding) != {"role", "schema_version", "manifest_digest", "bytes_digest", "records"} \
                    or binding.get("schema_version") != HOST_SNAPSHOT_SCHEMA:
                raise IdentityAttestationError("SCHEMA_UNKNOWN", "host binding")
            if not isinstance(binding.get("records"), list):
                raise IdentityAttestationError("TYPE_DRIFT", "host records")
            previous_path: str | None = None
            for row in binding["records"]:
                if not isinstance(row, dict) or set(row) != {"path", "mode", "size", "sha256"}:
                    raise IdentityAttestationError("SCHEMA_UNKNOWN", "host record")
                path = _safe_relative(row["path"])
                if previous_path is not None and previous_path.encode("utf-8") >= path.encode("utf-8"):
                    raise IdentityAttestationError("DUPLICATE", "host record order")
                previous_path = path
                for numeric in ("mode", "size"):
                    if isinstance(row[numeric], bool) or not isinstance(row[numeric], int) or row[numeric] < 0:
                        raise IdentityAttestationError("TYPE_DRIFT", f"host {numeric}")
                if not isinstance(row["sha256"], str) or not HEX64_RE.fullmatch(row["sha256"]):
                    raise IdentityAttestationError("TYPE_DRIFT", "host sha256")
            for digest_field in ("manifest_digest", "bytes_digest"):
                if not isinstance(binding.get(digest_field), str) or not HEX64_RE.fullmatch(binding[digest_field]):
                    raise IdentityAttestationError("TYPE_DRIFT", digest_field)
            if binding["manifest_digest"] != _digest_json(binding["records"]):
                raise IdentityAttestationError("DIGEST_MISMATCH", "host manifest")
    for field in ("source_envelope_sha256", "required_paths_digest"):
        if not isinstance(report[field], str) or not HEX64_RE.fullmatch(report[field]):
            raise IdentityAttestationError("TYPE_DRIFT", field)
    if report["accounting_contract"] != ACCOUNTING_CONTRACT:
        raise IdentityAttestationError("ACCOUNTING_CONTRACT_MISMATCH")
    accounting = report["accounting"]
    if not isinstance(accounting, dict) or set(accounting) != {
        "record_count", "payload_bytes", "record_digest", "aggregate_digest"
    }:
        raise IdentityAttestationError("SCHEMA_UNKNOWN", "accounting")
    for field in ("record_count", "payload_bytes"):
        if isinstance(accounting[field], bool) or not isinstance(accounting[field], int) or accounting[field] < 0:
            raise IdentityAttestationError("TYPE_DRIFT", field)
    for field in ("record_digest", "aggregate_digest"):
        if not isinstance(accounting[field], str) or not HEX64_RE.fullmatch(accounting[field]):
            raise IdentityAttestationError("TYPE_DRIFT", field)
    if report["identity_verdict"] not in {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}:
        raise IdentityAttestationError("SCHEMA_UNKNOWN", "identity_verdict")
    if not isinstance(report["created_at"], str) or not UTC_RE.fullmatch(report["created_at"]):
        raise IdentityAttestationError("TYPE_DRIFT", "created_at")
    try:
        datetime.strptime(report["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise IdentityAttestationError("TYPE_DRIFT", "created_at") from exc


def write_attestation(path_value: str | os.PathLike[str], report: dict[str, Any]) -> str:
    validate_identity_attestation(report)
    path = Path(path_value)
    if path.exists():
        raise IdentityAttestationError("CANDIDATE_ATTESTATION_STALE", "refusing to overwrite attestation")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(report)
    path.write_bytes(raw)
    if path.read_bytes() != raw:
        raise IdentityAttestationError("UNKNOWN", "attestation persistence mismatch")
    return hashlib.sha256(raw).hexdigest()


def load_attestation(path_value: str | os.PathLike[str]) -> dict[str, Any]:
    path = Path(path_value)
    if not path.is_file():
        raise IdentityAttestationError("CANDIDATE_ATTESTATION_MISSING", str(path))
    raw = path.read_bytes()
    if not is_canonical_json(raw):
        raise IdentityAttestationError("CANONICAL_BYTES", str(path))
    report = _strict_json(raw)
    validate_identity_attestation(report)
    return report


def compare_identity_attestations(staged: dict[str, Any], candidate: dict[str, Any], *,
                                  fixture_only: bool, verified_fixture_commit: str | None,
                                  release_authorized: bool = False) -> dict[str, Any]:
    if fixture_only and release_authorized:
        raise IdentityAttestationError("FIXTURE_RELEASE_FORBIDDEN")
    validate_identity_attestation(staged)
    validate_identity_attestation(candidate)
    issues: list[str] = []
    if staged["phase"] != "staged_index" or staged["subject"] != {"kind": "index", "sha": None}:
        issues.append("CANDIDATE_SOURCE_BINDING_MISMATCH")
    candidate_sha = candidate["subject"].get("sha") if isinstance(candidate["subject"], dict) else None
    if candidate["phase"] != "candidate_commit" or candidate["subject"].get("kind") != "commit":
        issues.append("CANDIDATE_SOURCE_BINDING_MISMATCH")
    if fixture_only and (not verified_fixture_commit or candidate_sha != verified_fixture_commit):
        issues.append("FIXTURE_COMMIT_UNVERIFIED")
    for role in ROLE_ORDER:
        left, right = staged["bindings"][role], candidate["bindings"][role]
        if role in {"product_root", "plugin_home"}:
            if left != right:
                issues.append("CANDIDATE_SOURCE_BINDING_MISMATCH")
                if left.get("repository_identity", {}).get("repository_root_tree_oid") != \
                        right.get("repository_identity", {}).get("repository_root_tree_oid") \
                        or left.get("selected_tree_oid") != right.get("selected_tree_oid"):
                    issues.append("CANDIDATE_GIT_TREE_MISMATCH")
        elif left != right:
            issues.append("CANDIDATE_SNAPSHOT_BYTE_MISMATCH")
    comparisons = (
        ("source_envelope_sha256", "CANDIDATE_ATTESTATION_STALE"),
        ("required_paths_digest", "FINAL_REQUIRED_FILE_DIGEST_MISMATCH"),
        ("accounting", "FINAL_ACCOUNTING_DIGEST_MISMATCH"),
    )
    for field, code in comparisons:
        if staged[field] != candidate[field]:
            issues.append(code)
    if staged["identity_verdict"] != "PASS" or candidate["identity_verdict"] != "PASS":
        issues.append("IDENTITY_VERDICT_NON_PASS")
    issues = list(dict.fromkeys(issues))
    verdict = "PASS" if not issues else "FAIL"
    return {
        "schema_version": AGGREGATE_SCHEMA,
        "phase": "candidate",
        "fixture_only": fixture_only,
        "release_authorized": False,
        "authorized": False,
        "verdict": verdict,
        "issues": issues,
        "staged_attestation_sha256": hashlib.sha256(canonical_json_bytes(staged)).hexdigest(),
        "candidate_attestation_sha256": hashlib.sha256(canonical_json_bytes(candidate)).hexdigest(),
    }


def aggregate_claim_reports(semantic_report: dict[str, Any], identity_report: dict[str, Any], *,
                            fixture_only: bool, performance_budget_status: str = "PENDING") -> dict[str, Any]:
    issues: list[str] = []
    if not isinstance(semantic_report, dict) or semantic_report.get("schema_version") != SEMANTIC_SCHEMA:
        issues.append("SEMANTIC_SCHEMA_UNKNOWN")
    try:
        validate_identity_attestation(identity_report)
    except IdentityAttestationError as exc:
        issues.append(exc.code)
    semantic_verdict = semantic_report.get("semantic_verdict", "UNKNOWN")
    identity_verdict = identity_report.get("identity_verdict", "UNKNOWN")
    if semantic_report.get("source_envelope_sha256") != identity_report.get("source_envelope_sha256"):
        issues.append("SOURCE_ENVELOPE_MISMATCH")
    if semantic_report.get("accounting_contract") != ACCOUNTING_CONTRACT \
            or identity_report.get("accounting_contract") != ACCOUNTING_CONTRACT:
        issues.append("ACCOUNTING_CONTRACT_MISMATCH")
    if semantic_report.get("accounting") != identity_report.get("accounting"):
        issues.append("INDEPENDENT_ACCOUNTING_MISMATCH")
    if performance_budget_status != "REVIEWED":
        issues.append("PERFORMANCE_BUDGET_PENDING" if performance_budget_status == "PENDING"
                      else "PERFORMANCE_BUDGET_UNKNOWN")
    if semantic_verdict == "NOT_APPLICABLE" or identity_verdict == "NOT_APPLICABLE":
        verdict = "NOT_APPLICABLE"
    elif semantic_verdict == "UNKNOWN" or identity_verdict == "UNKNOWN":
        verdict = "UNKNOWN"
    elif semantic_verdict == "PASS" and identity_verdict == "PASS" \
            and not [issue for issue in issues if issue != "PERFORMANCE_BUDGET_PENDING"]:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    issues = list(dict.fromkeys(issues))
    return {
        "schema_version": AGGREGATE_SCHEMA,
        "phase": "candidate" if identity_report.get("phase") == "candidate_commit" else "staged_index",
        "semantic_report_sha256": hashlib.sha256(canonical_json_bytes(semantic_report)).hexdigest(),
        "identity_report_sha256": hashlib.sha256(canonical_json_bytes(identity_report)).hexdigest(),
        "semantic_verdict": semantic_verdict,
        "identity_verdict": identity_verdict,
        "source_envelope_sha256": identity_report.get("source_envelope_sha256"),
        "accounting_contract": ACCOUNTING_CONTRACT,
        "performance_budget_status": performance_budget_status,
        "fixture_only": fixture_only,
        "release_authorized": False,
        "authorized": False,
        "verdict": verdict,
        "issues": issues,
    }
