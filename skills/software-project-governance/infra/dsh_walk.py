"""The bounded composition-tree walk (`walk`) — FEAT-113 S2 / FIX-484.

This module is the **extraction** of the traversal FIX-484 built inside
``dsh_compat.discover_compositions`` (commit bf039bc), not a reimplementation
(design §10.2): the loop body, its counters and its raise-not-truncate budget
semantics moved here verbatim, with only the I/O lifted behind injectable
seams (design §9.1 row — ``fs: FsPort``, ``clock: Callable[[], float]``):

* ``fs`` — the only disk this module touches when injected; the default
  :class:`RealFs` wraps the real ``os.scandir``/``os.stat``. The traversal
  itself reads no environment and no disk of its own (§9.1: the constructor
  arguments are the only source of truth).
* ``clock`` — defaults to ``time.monotonic``; tests drive the seconds ceiling
  with a fake clock instead of sleeping (§5.2).
* ``budget`` — a :class:`ScanBudget`; ``None`` means this module's
  ``DEFAULT_SCAN_BUDGET``.
* ``patterns`` — fnmatch **basenames** (``**/name`` is depth-agnostic, so the
  basename is the whole match). Which glob shapes are legal to declare is the
  *caller's* contract policy (``dsh_compat._composition_glob_basename``); this
  module matches whatever it is given and validates nothing.
* ``skip_predicate`` — the prune-before-descend tree policy, asked for each
  child's root-relative path parts. The repository-scan policy
  (``_SKIP_DIRS``/``_SKIP_PATH_PAIRS``/``_is_skipped_relative``) deliberately
  stayed in ``dsh_compat`` and is injected on every call: design §5.4 calls it
  "a repository scan policy, not a host fact", so owning it here would bake
  one caller's policy into the engine. Single source either way — it lives in
  exactly one module (the adapter).

``readlink`` is deliberately NOT on the port (§9.1 minimal port): the walk
never resolves a link, it skips and counts it, so a resolve face would be dead
surface.

Safety semantics preserved exactly (FIX-484, design §10.2): prune *before*
descending; reparse points and symlinks are never followed (counted in
``skipped_reparse_points``, never silently dropped); a directory already
visited — keyed by ``(st_dev, st_ino)`` — is not entered twice; crossing a
budget ceiling raises :class:`CompositionScanOverflow` carrying the counters
instead of returning a partial list (a capped scan that "found the files so
far" would read exactly like a complete one, and every verdict built on it
would be a green lie).

``dsh_compat`` re-exports :class:`ScanBudget`, :class:`CompositionScanOverflow`
and ``DEFAULT_SCAN_BUDGET``, so every existing import, ``except`` clause and
``mock.patch.object`` target keeps working with zero caller changes.
"""

from __future__ import annotations

import fnmatch
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

__all__ = [
    "DEFAULT_SCAN_BUDGET",
    "CompositionScanOverflow",
    "FsPort",
    "RealFs",
    "ScanBudget",
    "walk",
]


# ── the filesystem seam (§9.1: `fs: FsPort`, default reads the real disk) ────
class FsPort:
    """The read-only filesystem operations the walk needs.

    ``scandir`` returns a context manager yielding entry objects with
    ``name``, ``path`` and ``is_symlink()`` (the ``os.scandir`` entry face);
    ``stat`` follows the ``os.stat`` signature the walk calls. Tests inject a
    dict-backed double; the default :class:`RealFs` talks to the real
    filesystem. Nothing here writes.
    """

    def scandir(self, path):  # pragma: no cover - interface
        raise NotImplementedError

    def stat(self, path, *, follow_symlinks=True):  # pragma: no cover
        raise NotImplementedError


class RealFs(FsPort):
    """The default port: the real filesystem, read-only, via ``os``."""

    def scandir(self, path):
        return os.scandir(path)

    def stat(self, path, *, follow_symlinks=True):
        return os.stat(path, follow_symlinks=follow_symlinks)


# ── the budget and the overflow (moved from dsh_compat, verbatim) ────────────
@dataclass(frozen=True)
class ScanBudget:
    """Ceilings for one composition walk; crossing one raises, never truncates."""

    max_depth: int = 32
    max_entries: int = 200_000
    max_seconds: float = 30.0


#: The budget a call that injects none uses. Module-level on purpose: a test (or
#: a host with a known-large package tree) replaces it with `mock.patch.object`.
#: Patching `dsh_compat`'s re-exported name steers `discover_compositions` —
#: the adapter resolves the default in its OWN namespace and passes a concrete
#: budget down. `dsh_walk.DEFAULT_SCAN_BUDGET` steers only a direct `walk()`
#: call that injects no budget of its own.
DEFAULT_SCAN_BUDGET = ScanBudget()


class CompositionScanOverflow(RuntimeError):
    """A composition walk exceeded its ``ScanBudget`` (FIX-484).

    Carries the walk's counters (``dirs``, ``entries``,
    ``skipped_reparse_points``, ``skipped_errors``, ``elapsed``,
    ``max_depth_hit``, ``bounded_out``) so the caller can report *why* discovery
    produced no list. Deliberately not a silent partial return: a capped scan
    that returned "the files found so far" would read exactly like a complete
    scan, and every verdict built on it would be a green lie.
    """

    def __init__(self, message: str, *, counters: dict):
        super().__init__(message)
        self.counters = dict(counters)


#: The attribute a non-following stat reports for every reparse point
#: (junction, symlink, mount point). Spelled with a literal fallback so an
#: INJECTED stat double can simulate one on POSIX too — real POSIX stats never
#: carry `st_file_attributes`, so there the flag only ever fires for fakes;
#: on Windows this is exactly `stat.FILE_ATTRIBUTE_REPARSE_POINT` (0x400).
_REPARSE_FLAG = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def walk(root: os.PathLike, *, fs: Optional[FsPort] = None,
         clock: Callable[[], float] = time.monotonic,
         budget: Optional[ScanBudget] = None,
         report: Optional[dict] = None,
         patterns: Optional[Iterable[str]] = None,
         skip_predicate: Optional[Callable[[Sequence[str]], bool]] = None) -> list:
    """Walk ``root`` bounded, returning matching files sorted by relative path.

    Every decision is made *before* descending:

    * ``skip_predicate`` trees are pruned before ``scandir`` is ever called on
      them (the caller's tree policy — ``None`` prunes nothing by name);
    * reparse points and symlinks are never followed — they are counted in
      ``skipped_reparse_points`` and disclosed, never silently dropped. A
      Windows junction is neither reported by ``os.path.islink`` nor excluded
      by ``is_dir(follow_symlinks=False)``, so the honest test is the
      ``FILE_ATTRIBUTE_REPARSE_POINT`` attribute of the *non-following* stat;
    * a directory already visited — keyed by ``(st_dev, st_ino)`` — is not
      entered twice (a cycle the attribute test cannot see, e.g. a bind mount);
    * ``budget`` ceilings are enforced while walking; crossing one raises
      ``CompositionScanOverflow`` instead of returning a partial list.

    ``report`` is an optional out-parameter: a passed dict is filled with
    ``dirs``, ``entries``, ``skipped_reparse_points``, ``skipped_errors``,
    ``elapsed``, ``max_depth_hit`` and ``bounded_out`` so the caller can
    disclose what the walk skipped (and whether a cap ended it). ``clock`` is
    the injected monotonic clock the time budget reads (tests drive time
    without sleeping).

    Returns ``list[Path]`` sorted by relative posix path — the same shape (and
    the same root-relative-or-absolute spelling) the glob implementation
    returned before FIX-484. Files match when their basename ``fnmatch`` es
    any of ``patterns`` (matched with pathlib's own case rules on Windows);
    ``None`` matches nothing — the caller that wants files passes patterns.
    """
    root = Path(root)
    fs = RealFs() if fs is None else fs
    budget = DEFAULT_SCAN_BUDGET if budget is None else budget
    # `**/name` is depth-agnostic, so the basename is the whole match (verified
    # against pathlib: it matches at depth 0 too). `fnmatch` is the same
    # case-insensitive-on-Windows comparison pathlib itself uses. Which glob
    # shapes a caller may translate into these basenames is that caller's
    # policy (dsh_compat validates its contract's shapes loudly).
    patterns = tuple(patterns) if patterns is not None else ()

    counters = {"dirs": 0, "entries": 0, "skipped_reparse_points": 0,
                "skipped_errors": 0, "elapsed": 0.0, "max_depth_hit": False,
                "bounded_out": False}
    started = clock()
    found: list = []
    visited = set()

    def finish(*, bounded_out: bool, max_depth_hit: bool = False) -> dict:
        counters["elapsed"] = max(0.0, clock() - started)
        counters["max_depth_hit"] = max_depth_hit
        counters["bounded_out"] = bounded_out
        if report is not None:
            report.update(counters)
        return dict(counters)

    def overflow(kind: str, limit, *, max_depth_hit: bool = False) -> None:
        snapshot = finish(bounded_out=True, max_depth_hit=max_depth_hit)
        raise CompositionScanOverflow(
            f"composition scan {kind} budget exceeded (cap {limit!r}) after "
            f"{snapshot['dirs']} dir(s), {snapshot['entries']} entries, "
            f"{snapshot['skipped_reparse_points']} skipped reparse point(s), "
            f"{snapshot['elapsed']:.3f}s — refusing to return a partial "
            f"composition list", counters=snapshot)

    # The root is the caller's explicit choice, so it is walked even when it is
    # itself reached through a junction; its identity only seeds cycle detection.
    try:
        root_stat = fs.stat(root)
    except OSError:
        counters["skipped_errors"] += 1
    else:
        if root_stat.st_ino:  # no inode identity (some filesystems) → budget only
            visited.add((root_stat.st_dev, root_stat.st_ino))

    stack = [(root, 0, ())]
    while stack:
        directory, depth, parts = stack.pop()
        try:
            scan = fs.scandir(directory)
        except OSError:
            counters["skipped_errors"] += 1
            continue
        counters["dirs"] += 1
        with scan:
            for entry in scan:
                counters["entries"] += 1
                if counters["entries"] > budget.max_entries:
                    overflow("entries", budget.max_entries)
                if clock() - started > budget.max_seconds:
                    overflow("seconds", budget.max_seconds)
                try:
                    entry_stat = fs.stat(entry.path, follow_symlinks=False)
                    is_reparse = bool(
                        getattr(entry_stat, "st_file_attributes", 0) & _REPARSE_FLAG)
                    is_link = entry.is_symlink()
                except OSError:  # vanished or unreadable mid-walk
                    counters["skipped_errors"] += 1
                    continue
                if is_reparse or is_link:
                    counters["skipped_reparse_points"] += 1
                    continue
                child_parts = parts + (entry.name,)
                if stat.S_ISDIR(entry_stat.st_mode):
                    if skip_predicate is not None and skip_predicate(child_parts):
                        continue
                    identity = (entry_stat.st_dev, entry_stat.st_ino)
                    if identity in visited:
                        continue
                    if depth + 1 > budget.max_depth:
                        overflow("max_depth", budget.max_depth, max_depth_hit=True)
                    if identity[1]:
                        visited.add(identity)
                    stack.append((Path(entry.path), depth + 1, child_parts))
                elif stat.S_ISREG(entry_stat.st_mode):
                    if skip_predicate is not None and skip_predicate(child_parts):
                        continue
                    if any(fnmatch.fnmatch(entry.name, pattern)
                           for pattern in patterns):
                        found.append(Path(entry.path))

    finish(bounded_out=False)
    return sorted(set(found), key=lambda item: item.relative_to(root).as_posix())
