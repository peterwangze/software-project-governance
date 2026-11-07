"""Unit tests for the bounded composition-tree walk (`dsh_walk.walk`).

FEAT-113 S2 (design §5.2/§9.1/§10.2): the FIX-484 traversal was extracted from
``dsh_compat.discover_compositions`` into ``dsh_walk`` with its I/O behind
injectable seams. Every case here drives the walk through a dict-backed
``FakeFs`` and a stepped fake clock — no real directory is created, no real
time elapses (design §5.2: "测试用假时钟断言『预算触发即停』，不依赖真实计时"),
and no reparse point is materialized on disk: the reparse attribute is a field
of the injected stat double (§9.2 C5).

What these cases pin is the walk's own contract — sort order, prune-before-
descend, reparse/symlink skip + counters, ``(st_dev, st_ino)`` visited dedupe,
budget ceilings raising ``CompositionScanOverflow`` with the counters attached
— while ``test_dsh_compat.py`` keeps pinning the adapter semantics FIX-484
defined on the real filesystem (①–⑤).

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -p "test_dsh_walk.py" -v
"""

import os
import stat
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent

if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import dsh_walk  # noqa: E402

#: `stat.FILE_ATTRIBUTE_REPARSE_POINT` (0x400) — spelled as a literal because
#: POSIX `os.stat` results never carry `st_file_attributes`; the walk accepts
#: the attribute via `getattr(..., 0)`, so the fake stat drives the skip on
#: every platform without a real junction (§9.2 C5).
REPARSE = 0x400

#: The counter-key contract FIX-484 disclosed (§10.2 verbatim) — the walk may
#: not add, rename or drop a key here without that being a semantic change.
COUNTER_KEYS = {"dirs", "entries", "skipped_reparse_points", "skipped_errors",
                "elapsed", "max_depth_hit", "bounded_out"}


class _FakeStat:
    def __init__(self, mode, *, dev=1, ino=0, file_attributes=0):
        self.st_mode = mode
        self.st_dev = dev
        self.st_ino = ino
        self.st_file_attributes = file_attributes


class _FakeEntry:
    """A `os.scandir` entry double: name, path and the link test only."""

    def __init__(self, name, path, is_symlink=False):
        self.name = name
        self.path = path
        self._is_symlink = is_symlink

    def is_symlink(self):
        return self._is_symlink


class _FakeScan:
    """The context-manager iterable `RealFs.scandir` returns."""

    def __init__(self, entries):
        self._entries = list(entries)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def __iter__(self):
        return iter(self._entries)


class FakeFs:
    """A dict-backed filesystem double — the whole disk of these tests.

    Paths are posix strings under one root; directories carry their entry
    list, every node carries a stat. Tests observe `scandir_calls` to prove
    prune-before-descend (a pruned directory is never even listed).
    """

    def __init__(self, root="/fake"):
        self.root = root
        self._entries = {root: []}
        self._stats = {root: self._dir_stat()}
        self._stat_failures = set()
        self._scandir_failures = set()
        self.scandir_calls = []
        self.stat_calls = []

    @staticmethod
    def _dir_stat(**kwargs):
        return _FakeStat(stat.S_IFDIR | 0o755, **kwargs)

    @staticmethod
    def _file_stat(**kwargs):
        return _FakeStat(stat.S_IFREG | 0o644, **kwargs)

    def _child(self, relative):
        return f"{self.root}/{relative}" if relative else self.root

    def _attach(self, path, stat_obj, entry):
        """Register `path` and grow its parent chain as `os` would have it."""
        directory, _, _ = path.rpartition("/")
        cursor = directory
        while cursor not in self._entries and cursor != self.root:
            self._entries[cursor] = []
            self._stats[cursor] = self._dir_stat()
            grandparent, _, name = cursor.rpartition("/")
            self._entries.setdefault(grandparent, []).append(
                _FakeEntry(name, cursor))
            cursor = grandparent
        self._stats[path] = stat_obj
        self._entries.setdefault(directory, []).append(entry)

    def add_dir(self, relative, *, attrs=0, dev=1, ino=None, is_symlink=False):
        path = self._child(relative)
        _, _, name = path.rpartition("/")
        self._entries.setdefault(path, [])
        self._attach(path, self._dir_stat(dev=dev, ino=self._next_ino(ino),
                                          file_attributes=attrs),
                     _FakeEntry(name, path, is_symlink))
        return path

    def add_file(self, relative, *, attrs=0, dev=1, ino=None):
        path = self._child(relative)
        _, _, name = path.rpartition("/")
        self._attach(path, self._file_stat(dev=dev, ino=self._next_ino(ino),
                                           file_attributes=attrs),
                     _FakeEntry(name, path))
        return path

    def _next_ino(self, ino):
        if ino is not None:
            return ino
        return max((s.st_ino for s in self._stats.values()), default=0) + 1

    def fail_stat(self, relative):
        self._stat_failures.add(self._child(relative))

    def fail_scandir(self, relative):
        self._scandir_failures.add(self._child(relative))

    # ── the FsPort face ─────────────────────────────────────────────────────
    def scandir(self, path):
        key = Path(path).as_posix()
        self.scandir_calls.append(key)
        if key in self._scandir_failures:
            raise OSError(f"scandir refused: {key}")
        return _FakeScan(self._entries.get(key, ()))

    def stat(self, path, *, follow_symlinks=True):
        key = Path(path).as_posix()
        self.stat_calls.append((key, follow_symlinks))
        if key in self._stat_failures:
            raise OSError(f"stat refused: {key}")
        try:
            return self._stats[key]
        except KeyError:
            raise OSError(f"no such node: {key}") from None


class FakeClock:
    """A monotonic clock double: returns `now`, then advances by `step`."""

    def __init__(self, start=0.0, step=0.0):
        self.now = float(start)
        self.step = float(step)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        value = self.now
        self.now += self.step
        return value


_PATTERNS = ("agent.cordis.yml", "*.cordis.yml.template")


class WalkTests(unittest.TestCase):
    """The walk's own contract, entirely behind the injected seams."""

    def test_matches_patterns_and_sorts_by_relative_posix_path(self):
        fs = FakeFs()
        fs.add_file("agent.cordis.yml")
        fs.add_file("m/agent.cordis.yml")
        fs.add_file("a/z.cordis.yml.template")
        fs.add_file("a/ignored.txt")
        fs.add_file("b/agent.cordis.yml")
        found = dsh_walk.walk(Path("/fake"), fs=fs, patterns=_PATTERNS)
        self.assertEqual([item.relative_to("/fake").as_posix() for item in found],
                         ["a/z.cordis.yml.template", "agent.cordis.yml",
                          "b/agent.cordis.yml", "m/agent.cordis.yml"])
        self.assertTrue(all(isinstance(item, Path) for item in found))

    def test_a_reparse_point_is_skipped_counted_and_never_entered(self):
        fs = FakeFs()
        fs.add_file("z/agent.cordis.yml")
        fs.add_dir("z/loop", attrs=REPARSE)
        fs.add_file("z/loop/agent.cordis.yml")  # visible only if followed
        report = {}
        found = dsh_walk.walk(Path("/fake"), fs=fs, report=report,
                              patterns=_PATTERNS)
        self.assertEqual([p.relative_to("/fake").as_posix() for p in found],
                         ["z/agent.cordis.yml"])
        self.assertEqual(report["skipped_reparse_points"], 1, report)
        # Observable never-entered: the loop directory was never listed.
        self.assertNotIn("/fake/z/loop", fs.scandir_calls, fs.scandir_calls)
        # root + z only.
        self.assertEqual(report["dirs"], 2, report)
        self.assertFalse(report["bounded_out"], report)

    def test_a_symlink_entry_is_skipped_and_counted(self):
        fs = FakeFs()
        fs.add_file("real/agent.cordis.yml")
        fs.add_dir("link", is_symlink=True)
        fs.add_file("link/agent.cordis.yml")
        report = {}
        found = dsh_walk.walk(Path("/fake"), fs=fs, report=report,
                              patterns=_PATTERNS)
        self.assertEqual([p.relative_to("/fake").as_posix() for p in found],
                         ["real/agent.cordis.yml"])
        self.assertEqual(report["skipped_reparse_points"], 1, report)
        self.assertNotIn("/fake/link", fs.scandir_calls)

    def test_a_directory_already_visited_by_identity_is_not_entered_twice(self):
        # A cycle the reparse attribute cannot see (e.g. a bind mount): the
        # (st_dev, st_ino) visited set is the only defense. The alias carries
        # the SAME identity as `first`, so it is skipped without a counter —
        # FIX-484 semantics, preserved verbatim by the extraction.
        fs = FakeFs()
        fs.add_dir("first", dev=7, ino=42)
        fs.add_file("first/agent.cordis.yml")
        fs.add_dir("alias", dev=7, ino=42)
        fs.add_file("alias/agent.cordis.yml")
        report = {}
        found = dsh_walk.walk(Path("/fake"), fs=fs, report=report,
                              patterns=_PATTERNS)
        self.assertEqual([p.relative_to("/fake").as_posix() for p in found],
                         ["first/agent.cordis.yml"])
        self.assertEqual(report["dirs"], 2, report)  # root + first
        self.assertNotIn("/fake/alias", fs.scandir_calls)
        self.assertEqual(report["skipped_reparse_points"], 0, report)

    def test_the_entries_ceiling_raises_with_the_counters_attached(self):
        fs = FakeFs()
        for index in range(5):
            fs.add_file(f"d{index}/agent.cordis.yml")
        report = {}
        with self.assertRaises(dsh_walk.CompositionScanOverflow) as caught:
            dsh_walk.walk(Path("/fake"), fs=fs,
                          budget=dsh_walk.ScanBudget(max_entries=2),
                          report=report, patterns=_PATTERNS)
        counters = caught.exception.counters
        self.assertTrue(counters["bounded_out"], counters)
        self.assertGreaterEqual(counters["entries"], 2, counters)
        self.assertEqual(set(counters), COUNTER_KEYS, counters)
        # The out-parameter is filled before the raise (FIX-484): a caller
        # never has to catch the exception to learn what the walk saw.
        self.assertTrue(report["bounded_out"], report)
        self.assertIn("entries", str(caught.exception))

    def test_the_seconds_ceiling_reads_the_injected_clock_not_the_wall(self):
        clock = FakeClock(start=100.0, step=1.0)
        fs = FakeFs()
        fs.add_file("agent.cordis.yml")
        with self.assertRaises(dsh_walk.CompositionScanOverflow) as caught:
            dsh_walk.walk(Path("/fake"), fs=fs, clock=clock,
                          budget=dsh_walk.ScanBudget(max_seconds=0.5),
                          patterns=_PATTERNS)
        counters = caught.exception.counters
        self.assertIn("seconds", str(caught.exception))
        self.assertTrue(counters["bounded_out"], counters)
        self.assertFalse(counters["max_depth_hit"], counters)
        # Elapsed comes from the injected clock only — no sleep happened.
        self.assertGreaterEqual(counters["elapsed"], 1.0, counters)
        self.assertGreaterEqual(clock.calls, 2)

    def test_a_file_at_max_depth_matches_while_a_deeper_directory_overflows(self):
        fs = FakeFs()
        fs.add_file("sub/agent.cordis.yml")
        report = {}
        found = dsh_walk.walk(Path("/fake"), fs=fs,
                              budget=dsh_walk.ScanBudget(max_depth=1),
                              report=report, patterns=_PATTERNS)
        self.assertEqual([p.relative_to("/fake").as_posix() for p in found],
                         ["sub/agent.cordis.yml"])
        self.assertFalse(report["bounded_out"], report)
        fs.add_dir("sub/deep")
        with self.assertRaises(dsh_walk.CompositionScanOverflow) as caught:
            dsh_walk.walk(Path("/fake"), fs=fs,
                          budget=dsh_walk.ScanBudget(max_depth=1),
                          patterns=_PATTERNS)
        self.assertTrue(caught.exception.counters["max_depth_hit"],
                        caught.exception.counters)

    def test_the_skip_predicate_prunes_before_descending(self):
        fs = FakeFs()
        fs.add_file("presets/agent.cordis.yml")
        fs.add_dir("node_modules/pkg")
        fs.add_file("node_modules/pkg/agent.cordis.yml")
        report = {}
        found = dsh_walk.walk(Path("/fake"), fs=fs, report=report,
                              patterns=_PATTERNS,
                              skip_predicate=lambda parts: "node_modules" in parts)
        self.assertEqual([p.relative_to("/fake").as_posix() for p in found],
                         ["presets/agent.cordis.yml"])
        # Prune-before-descend: the vendored tree was never listed.
        self.assertFalse(any("node_modules" in call for call in fs.scandir_calls),
                         fs.scandir_calls)
        self.assertEqual(report["dirs"], 2, report)  # root + presets

    def test_unreadable_entries_and_directories_are_counted_not_fatal(self):
        fs = FakeFs()
        fs.add_file("ok/agent.cordis.yml")
        fs.add_file("ok/vanished.yml")   # stat refuses mid-walk
        fs.add_dir("sealed")             # scandir refuses
        fs.add_file("sealed/agent.cordis.yml")
        fs.fail_stat("ok/vanished.yml")
        fs.fail_scandir("sealed")
        report = {}
        found = dsh_walk.walk(Path("/fake"), fs=fs, report=report,
                              patterns=_PATTERNS)
        self.assertEqual([p.relative_to("/fake").as_posix() for p in found],
                         ["ok/agent.cordis.yml"])
        self.assertEqual(report["skipped_errors"], 2, report)
        self.assertFalse(report["bounded_out"], report)

    def test_a_root_that_cannot_be_stated_or_listed_reports_and_returns_empty(self):
        fs = FakeFs("/gone")
        fs.fail_stat("")        # the root itself
        fs.fail_scandir("")     # and its listing
        report = {}
        found = dsh_walk.walk(Path("/gone"), fs=fs, report=report,
                              patterns=_PATTERNS)
        self.assertEqual(found, [])
        self.assertEqual(report["skipped_errors"], 2, report)
        self.assertEqual(report["dirs"], 0, report)
        self.assertFalse(report["bounded_out"], report)

    def test_the_report_keys_are_exactly_the_disclosure_contract(self):
        fs = FakeFs()
        fs.add_file("agent.cordis.yml")
        report = {}
        dsh_walk.walk(Path("/fake"), fs=fs, report=report, patterns=_PATTERNS)
        self.assertEqual(set(report), COUNTER_KEYS, sorted(report))
        self.assertEqual(report["dirs"], 1, report)
        self.assertEqual(report["entries"], 1, report)

    def test_a_missing_budget_uses_the_module_default(self):
        # The default ceiling is generous: an ordinary tree finishes under it
        # with bounded_out False (the module default is what `discover_
        # compositions` injects when its caller passes none).
        fs = FakeFs()
        fs.add_file("a/b/c/agent.cordis.yml")
        report = {}
        dsh_walk.walk(Path("/fake"), fs=fs, report=report, patterns=_PATTERNS)
        self.assertFalse(report["bounded_out"], report)
        self.assertEqual(report["max_depth_hit"], False, report)


if __name__ == "__main__":
    unittest.main()
