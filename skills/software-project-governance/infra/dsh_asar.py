"""FEAT-113 S1 — the pure-stdlib asar reader (design §3.3).

Reads the Electron ``app.asar`` container **without unpacking it**: the 16-byte
header is parsed, the JSON index is kept in memory, and file content is read
by ``offset``/``size`` straight out of the archive. Nothing here writes,
extracts, or spawns — every mutating operation is out of scope by design
(§3.5: full unpacking is rejected).

Layout (the contract's ``host.planes.asar.header`` facts, verified read-only
against the real desktop archive):

* ``[0:4]``  LE uint32 — the pickle size prefix; must equal 4
* ``[4:8]``  LE uint32 — payload size; content base = ``8 + payload``
* ``[8:12]`` the payload-size duplicate (header pickle payload size)
* ``[12:16]``LE uint32 — header JSON byte length
* byte 16 → the header JSON, trimmed to the last ``}`` (alignment padding)

Purity rules (§9.1): the parsing functions take **bytes**, never paths; the
only I/O lives behind :class:`FsPort` (default :class:`RealFs`), and no pure
function imports ``os``/``subprocess``. ``entry_count_cap`` enforcement reads
the contract fact ``host.planes.asar.entry_count_cap`` lazily — the one
contract dependency of this module.
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "AsarError", "AsarEntry", "AsarHeader", "AsarReader", "FsPort", "RealFs",
    "ResolvedEntry", "count_entries", "find_entry", "index_entry",
    "parse_header", "parse_index", "resolve_entry",
]

#: Error codes (§3.3). Each is a distinct string so callers can pin semantics
#: without matching message text.
ASAR_HEADER_TRUNCATED = "ASAR_HEADER_TRUNCATED"
ASAR_MAGIC_INVALID = "ASAR_MAGIC_INVALID"
ASAR_JSON_INVALID = "ASAR_JSON_INVALID"
ASAR_ENTRY_MISSING = "ASAR_ENTRY_MISSING"
ASAR_ENTRY_OUT_OF_RANGE = "ASAR_ENTRY_OUT_OF_RANGE"
ASAR_ENTRY_CORRUPT = "ASAR_ENTRY_CORRUPT"
ASAR_LINK_CYCLE = "ASAR_LINK_CYCLE"

#: Link chains resolve at most this many hops (§3.3).
MAX_LINK_HOPS = 8


class AsarError(Exception):
    """One asar read failure, carrying its §3.3 reason code."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


# ── the filesystem seam (§9.1: `fs: FsPort`, default reads real files) ──────
class FsPort:
    """The read-only filesystem operations this module needs.

    Tests inject a dict-backed double; the default :class:`RealFs` talks to
    the real filesystem. Methods take ``str`` or ``Path`` paths and never
    write.
    """

    def exists(self, path) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def is_file(self, path) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def is_dir(self, path) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def size(self, path) -> int:  # pragma: no cover - interface
        raise NotImplementedError

    def read_head(self, path, count: int) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def read_at(self, path, offset: int, count: int) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def read_bytes(self, path) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError

    def list_dir(self, path) -> List[str]:  # pragma: no cover - interface
        raise NotImplementedError

    def mtime(self, path) -> float:  # pragma: no cover - interface
        raise NotImplementedError


class RealFs(FsPort):
    """The default port: real files, read-only, via ``pathlib``."""

    def exists(self, path) -> bool:
        return Path(path).exists()

    def is_file(self, path) -> bool:
        return Path(path).is_file()

    def is_dir(self, path) -> bool:
        return Path(path).is_dir()

    def size(self, path) -> int:
        return Path(path).stat().st_size

    def read_head(self, path, count: int) -> bytes:
        with open(path, "rb") as handle:
            return handle.read(count)

    def read_at(self, path, offset: int, count: int) -> bytes:
        with open(path, "rb") as handle:
            handle.seek(offset)
            return handle.read(count)

    def read_bytes(self, path) -> bytes:
        with open(path, "rb") as handle:
            return handle.read()

    def list_dir(self, path) -> List[str]:
        try:
            return sorted(entry.name for entry in Path(path).iterdir())
        except OSError:
            return []

    def mtime(self, path) -> float:
        try:
            return Path(path).stat().st_mtime
        except OSError:
            return 0.0


# ── pure header/index parsing (bytes in, values out) ────────────────────────
@dataclass(frozen=True)
class AsarHeader:
    payload_size: int
    json_size: int
    content_base: int


def parse_header(data: bytes) -> AsarHeader:
    """Parse the 16-byte asar prefix (the contract's header facts).

    Raises :class:`AsarError` with ``ASAR_HEADER_TRUNCATED`` when fewer than
    16 bytes are available and ``ASAR_MAGIC_INVALID`` when ``[0:4]`` is not
    the little-endian pickle prefix 4.
    """
    if len(data) < 16:
        raise AsarError(ASAR_HEADER_TRUNCATED,
                        f"header needs 16 bytes, got {len(data)}")
    prefix = int.from_bytes(data[0:4], "little")
    if prefix != 4:
        raise AsarError(ASAR_MAGIC_INVALID,
                        f"[0:4] must be 4 (LE), got {prefix}")
    payload_size = int.from_bytes(data[4:8], "little")
    json_size = int.from_bytes(data[12:16], "little")
    return AsarHeader(payload_size=payload_size, json_size=json_size,
                      content_base=8 + payload_size)


def parse_index(raw: bytes) -> Dict[str, Any]:
    """Decode the header JSON, trimmed to the last ``}`` (alignment padding).

    Undecodable bytes and non-JSON payloads both raise ``ASAR_JSON_INVALID``
    — the reader never lets a raw ``UnicodeDecodeError`` escape.
    """
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AsarError(ASAR_JSON_INVALID,
                        f"header is not UTF-8: {error}") from error
    end = text.rfind("}")
    if end < 0:
        raise AsarError(ASAR_JSON_INVALID, "header has no JSON object")
    try:
        index = json.loads(text[:end + 1])
    except ValueError as error:
        raise AsarError(ASAR_JSON_INVALID,
                        f"header is not JSON: {error}") from error
    if not isinstance(index, dict):
        raise AsarError(ASAR_JSON_INVALID, "header is not a JSON object")
    return index


@dataclass(frozen=True)
class AsarEntry:
    """One indexed file: string ``offset`` from the JSON is already an int."""

    offset: Optional[int]
    size: int
    link: Optional[str] = None
    unpacked: bool = False


@dataclass(frozen=True)
class ResolvedEntry:
    rel: str
    entry: AsarEntry
    link_chain: Tuple[str, ...] = field(default=())


def _walk_index(index: Dict[str, Any], rel: str) -> Dict[str, Any]:
    """Walk ``rel`` (slash-separated) through the index's ``files`` tree."""
    segments = [part for part in str(rel).split("/") if part]
    if not segments or any(part in (".", "..") for part in segments):
        raise AsarError(ASAR_ENTRY_MISSING,
                        f"path {rel!r} is not a plain archive-relative path")
    node: Any = index
    for part in segments:
        if not isinstance(node, dict) or "files" not in node:
            raise AsarError(ASAR_ENTRY_MISSING, f"{rel!r}: not a directory")
        node = node["files"].get(part)
        if node is None:
            raise AsarError(ASAR_ENTRY_MISSING, f"{rel!r}: no such entry")
    if not isinstance(node, dict):
        raise AsarError(ASAR_ENTRY_MISSING, f"{rel!r}: not an entry")
    return node


def _as_entry(node: Dict[str, Any], rel: str) -> AsarEntry:
    if "files" in node and "offset" not in node and "link" not in node:
        raise AsarError(ASAR_ENTRY_MISSING, f"{rel!r} is a directory")
    offset = node.get("offset")
    if isinstance(offset, str):
        try:
            offset = int(offset)
        except ValueError as error:
            raise AsarError(ASAR_JSON_INVALID,
                            f"{rel!r}: offset {offset!r} is not an integer"
                            ) from error
    link = node.get("link")
    return AsarEntry(offset=offset,
                     size=int(node.get("size", 0) or 0),
                     link=link if isinstance(link, str) else None,
                     unpacked=bool(node.get("unpacked", False)))


def index_entry(index: Dict[str, Any], rel: str) -> AsarEntry:
    """The entry at ``rel``; ``.``/``..`` segments are refused."""
    return _as_entry(_walk_index(index, rel), rel)


def resolve_entry(index: Dict[str, Any], rel: str,
                  *, max_link_hops: int = MAX_LINK_HOPS) -> ResolvedEntry:
    """Resolve ``rel`` following ``link`` entries (bounded, cycle-detecting).

    ``max_link_hops`` counts *hops* (link→target transitions), not chain
    entries: a legal 8-hop chain resolves, the 9th hop is refused (§3.3).
    """
    chain: List[str] = [rel]
    current = rel
    hops = 0
    node = _walk_index(index, current)
    while isinstance(node.get("link"), str):
        hops += 1
        if hops > max_link_hops:
            raise AsarError(ASAR_LINK_CYCLE,
                            f"{rel!r}: more than {max_link_hops} link hops")
        current = node["link"]
        if current in chain:
            raise AsarError(ASAR_LINK_CYCLE,
                            f"{rel!r}: link cycle at {current!r}")
        chain.append(current)
        node = _walk_index(index, current)
    return ResolvedEntry(rel=rel, entry=_as_entry(node, rel),
                         link_chain=tuple(chain))


def _iter_files(index: Dict[str, Any], cap: int):
    """Bounded depth-first walk yielding ``(rel, node)`` — at most ``cap``."""
    stack: List[Tuple[str, Dict[str, Any]]] = [("", index)]
    seen = 0
    while stack:
        prefix, node = stack.pop()
        for name, child in node.get("files", {}).items():
            if seen >= cap:
                return
            seen += 1
            rel = f"{prefix}/{name}" if prefix else name
            yield rel, child
            if isinstance(child, dict) and "files" in child:
                stack.append((rel, child))


def count_entries(index: Dict[str, Any], cap: int) -> int:
    """Count index entries, stopping at ``cap`` (§3.3: bounded counting)."""
    counted = 0
    for _ in _iter_files(index, cap):
        counted += 1
    return counted


def find_entry(index: Dict[str, Any], tail: Tuple[str, ...]) -> List[str]:
    """All entry paths ending with ``tail`` (bounded by the contract cap).

    Plane discovery uses this to locate the install anchor inside an archive
    without knowing the archive's internal prefix (§3.2 source 1 shape ③).
    """
    cap = _contract_entry_count_cap()
    wanted = "/".join(tail)
    return [rel for rel, _ in _iter_files(index, cap)
            if rel == wanted or rel.endswith("/" + wanted)]


def _entry_in_bounds(entry: AsarEntry, content_base: int,
                     file_size: int) -> bool:
    if entry.offset is None or entry.unpacked:
        return True
    start = content_base + entry.offset
    return content_base <= start and start + entry.size <= file_size


# ── the contract's one fact this module enforces ────────────────────────────
def _contract_entry_count_cap() -> int:
    """``host.planes.asar.entry_count_cap`` — read lazily, never inlined."""
    import dsh_contract  # noqa: PLC0415 — sibling accessor, lazy on purpose

    return int(dsh_contract.get("host.planes.asar.entry_count_cap"))


def _unpacked_path(asar_path: str, rel: str) -> str:
    # posix-literal on purpose: the archive's internal paths are posix, and
    # Windows open() accepts forward slashes, so no OS normalization is needed
    # (and none is wanted — normalization would rewrite injectable fake roots)
    return f"{asar_path}.unpacked/{rel}"


# ── the reader (path + FsPort; content reads by offset/size) ────────────────
class AsarReader:
    """Zero-unpack reader over one archive file, behind an :class:`FsPort`.

    The header and index are parsed once, lazily; ``read_bytes`` then reads
    content slices directly from the archive. ``unpacked`` entries are read
    from the ``<asar>.unpacked`` sibling — as a *single-entry source only*:
    the unpacked tree has no index and cannot serve as a plane (§3.3).
    """

    def __init__(self, path, *, fs: Optional[FsPort] = None):
        self.path = str(path)
        self.fs = fs if fs is not None else RealFs()
        try:
            file_size = self.fs.size(self.path)
        except OSError as error:
            raise AsarError(ASAR_HEADER_TRUNCATED,
                            f"{self.path}: {error}") from error
        if file_size < 16:
            raise AsarError(ASAR_HEADER_TRUNCATED,
                            f"{self.path}: {file_size} bytes is too short")
        self.file_size = file_size
        try:
            head = self.fs.read_head(self.path, 16)
            self.header = parse_header(head)
            raw = self.fs.read_at(self.path, 16, self.header.json_size)
        except OSError as error:
            raise AsarError(ASAR_HEADER_TRUNCATED,
                            f"{self.path}: {error}") from error
        self.index = parse_index(raw)
        self._json_bytes = raw[:raw.rfind(b"}") + 1]

    @property
    def content_base(self) -> int:
        return self.header.content_base

    def entry(self, rel: str) -> ResolvedEntry:
        return resolve_entry(self.index, rel)

    def read_bytes(self, rel: str) -> bytes:
        resolved = self.entry(rel)
        node = resolved.entry
        if node.unpacked:
            try:
                return self.fs.read_bytes(_unpacked_path(self.path, rel))
            except OSError as error:
                raise AsarError(ASAR_ENTRY_MISSING,
                                f"{rel!r}: unpacked copy unreadable: "
                                f"{error}") from error
        if node.offset is None:
            # A packed file entry needs an offset as soon as it has content:
            # size>0 with no offset is a corrupt index node, and size 0 needs
            # no archive bytes at all. Neither may reach the bounds math.
            if node.size:
                raise AsarError(
                    ASAR_ENTRY_CORRUPT,
                    f"{rel!r}: file entry has size {node.size} but no offset")
            return b""
        if not _entry_in_bounds(node, self.header.content_base,
                                self.file_size):
            raise AsarError(
                ASAR_ENTRY_OUT_OF_RANGE,
                f"{rel!r}: offset {node.offset}+{node.size} outside "
                f"[{self.header.content_base}, {self.file_size}]")
        try:
            return self.fs.read_at(
                self.path, self.header.content_base + node.offset, node.size)
        except OSError as error:
            raise AsarError(ASAR_ENTRY_OUT_OF_RANGE,
                            f"{rel!r}: {error}") from error

    def read_json(self, rel: str) -> Any:
        return json.loads(self.read_bytes(rel).decode("utf-8"))

    def identity(self, entry_count_cap: Optional[int] = None) -> Dict[str, Any]:
        """The §3.3 identity: no mtime (evidence must not jitter)."""
        cap = entry_count_cap if entry_count_cap is not None \
            else _contract_entry_count_cap()
        unpacked_present = False
        for _, node in _iter_files(self.index, cap):
            if node.get("unpacked"):
                unpacked_present = True
                break
        return {
            "path": self.path,
            "size": self.file_size,
            "header_sha256": hashlib.sha256(self._json_bytes).hexdigest(),
            "entry_count": count_entries(self.index, cap),
            "content_base": self.header.content_base,
            "unpacked_present": unpacked_present,
        }
