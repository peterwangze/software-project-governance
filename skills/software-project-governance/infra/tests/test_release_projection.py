"""FIX-366 — two-stage decoupling of byte_copy from in-batch transformed targets.

`build_projection_plan` used to build its writes in a single pass: a
``byte_copy`` read its source straight from disk while a ``transformed_text``
result only lived in memory. When the byte_copy's source was another
projection's target in the SAME batch, the plan pinned the STALE on-disk
version into the mirror — so every ``write_projections`` updated the transformed
file, failed its own post-write validation (mirror drift), rolled back, and the
plan could never converge. The fix resolves every transformed/structured
projection in memory FIRST, then lets byte_copy sources consume the resolved
content; non-overlapping sources keep reading raw disk bytes.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

INFRA = Path(__file__).resolve().parents[1]
if str(INFRA) not in sys.path:
    sys.path.insert(0, str(INFRA))

from release.projection import (  # noqa: E402
    build_projection_plan, check_projections, write_projections)

OLD_VERSION = "0.86.0"
NEW_VERSION = "0.87.0"


class ProjectionPlanOverlapTests(unittest.TestCase):
    """byte_copy mirroring an in-batch transformed target must see the bump."""

    def fixture(self, root):
        (root / "skills/software-project-governance/core").mkdir(parents=True)
        (root / "skills/software-project-governance/SKILL.md").write_text(
            f"---\nversion: {NEW_VERSION}\n---\nbody\n", encoding="utf-8")
        (root / "inventory.py").write_text(
            "REQUIRED_SNIPPETS = {'x': ['required-marker']}\n"
            "PROJECTION_SYNC_PATTERNS = ('mirror-pattern',)\n", encoding="utf-8")
        contract = {
            "projection_ids": ["text", "mirror"],
            "projection_kinds": ["byte_copy", "transformed_text"],
            "validation_inventories": [
                {"id": "required-snippets", "source": "inventory.py",
                 "symbol": "REQUIRED_SNIPPETS", "value_type": "dict",
                 "min_entries": 1, "required_members": ["required-marker"]},
                {"id": "fixture-mirror-patterns", "source": "inventory.py",
                 "symbol": "PROJECTION_SYNC_PATTERNS", "value_type": "sequence",
                 "min_entries": 1, "member_match": "exact",
                 "required_members": ["mirror-pattern"]}]}
        (root / "skills/software-project-governance/core/manifest.json").write_text(
            json.dumps({"release_projection_contract": contract}), encoding="utf-8")
        config = {
            "schema_version": 1,
            "authority": {"kind": "skill_frontmatter_version",
                          "path": "skills/software-project-governance/SKILL.md"},
            "validation_inventories": [
                {"id": "required-snippets", "source": "inventory.py",
                 "symbol": "REQUIRED_SNIPPETS"},
                {"id": "fixture-mirror-patterns", "source": "inventory.py",
                 "symbol": "PROJECTION_SYNC_PATTERNS"}],
            "projections": [
                {"id": "text", "kind": "transformed_text", "target": "report.txt",
                 "pattern": "version=[0-9.]+", "replacement": "version={version}",
                 "count": 1},
                {"id": "mirror", "kind": "byte_copy", "source": "report.txt",
                 "target": "mirror.bin"}]}
        (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
        (root / "report.txt").write_bytes(f"version={OLD_VERSION}\n".encode("utf-8"))
        (root / "mirror.bin").write_bytes(f"version={OLD_VERSION}\n".encode("utf-8"))

    def test_byte_copy_plan_carries_resolved_version_of_overlapped_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            _version, plan = build_projection_plan(root, root / "config.json")
            writes = {write.relative_path: write for write in plan}
            self.assertEqual(writes["report.txt"].content,
                             f"version={NEW_VERSION}\n".encode("utf-8"))
            self.assertEqual(writes["mirror.bin"].kind, "byte_copy")
            self.assertEqual(
                writes["mirror.bin"].content,
                f"version={NEW_VERSION}\n".encode("utf-8"),
                "a byte_copy whose source is an in-batch transformed target "
                "MUST mirror the resolved content, not the stale disk bytes "
                "(FIX-366)")

    def test_write_converges_instead_of_rolling_back(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            result = write_projections(root, root / "config.json")
            self.assertEqual(result.state, "PASS", result.issues)
            self.assertEqual((root / "report.txt").read_bytes(),
                             f"version={NEW_VERSION}\n".encode("utf-8"))
            self.assertEqual((root / "mirror.bin").read_bytes(),
                             f"version={NEW_VERSION}\n".encode("utf-8"))
            self.assertEqual(check_projections(root, root / "config.json").state,
                             "PASS")
            self.assertEqual(
                write_projections(root, root / "config.json").facts["written"], 0)

    def test_non_overlapping_byte_copy_still_reads_raw_source_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            (root / "other.bin").write_bytes(b"\x00raw-bytes\n")
            (root / "copy.bin").write_bytes(b"stale\n")
            config = json.loads((root / "config.json").read_text(encoding="utf-8"))
            config["projections"].append(
                {"id": "plain", "kind": "byte_copy", "source": "other.bin",
                 "target": "copy.bin"})
            contract = json.loads(
                (root / "skills/software-project-governance/core/manifest.json")
                .read_text(encoding="utf-8"))
            ids = contract["release_projection_contract"]["projection_ids"]
            ids.append("plain")
            (root / "skills/software-project-governance/core/manifest.json").write_text(
                json.dumps(contract), encoding="utf-8")
            (root / "config.json").write_text(json.dumps(config), encoding="utf-8")
            _version, plan = build_projection_plan(root, root / "config.json")
            writes = {write.relative_path: write for write in plan}
            self.assertEqual(writes["copy.bin"].content, b"\x00raw-bytes\n")
            self.assertEqual(writes["report.txt"].content,
                             f"version={NEW_VERSION}\n".encode("utf-8"))
            self.assertEqual(writes["mirror.bin"].content,
                             f"version={NEW_VERSION}\n".encode("utf-8"))


    def test_crlf_transformed_content_stays_byte_faithful(self):
        """Regression guard (review FIX-366 F-1): native CRLF survives planning.

        If the transformed resolution ever regresses to ``read_text()``, its
        universal-newline translation strips ``\\r`` and BOTH assertions
        redden: the transformed plan content would be LF-normalized, and the
        byte_copy mirror of that same target would stop being byte-identical.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.fixture(root)
            old_crlf = (f"# report\r\nversion={OLD_VERSION}\r\ntail\r\n").encode("utf-8")
            new_crlf = (f"# report\r\nversion={NEW_VERSION}\r\ntail\r\n").encode("utf-8")
            (root / "report.txt").write_bytes(old_crlf)
            (root / "mirror.bin").write_bytes(old_crlf)
            _version, plan = build_projection_plan(root, root / "config.json")
            writes = {write.relative_path: write for write in plan}
            self.assertEqual(writes["report.txt"].content, new_crlf,
                             "transformed content must keep the file's native "
                             "\\r\\n — universal-newline translation is a "
                             "byte-faithfulness bug")
            self.assertEqual(writes["mirror.bin"].content, new_crlf,
                             "a byte_copy mirroring this target must equal the "
                             "resolved bytes exactly, \\r\\n included")


if __name__ == "__main__":
    unittest.main()
