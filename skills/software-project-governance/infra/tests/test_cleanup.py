"""Unit tests for cleanup.py — FIX-053 follow-up.

Run:
    python -m unittest discover -s skills/software-project-governance/infra/tests -v
"""

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent
if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import cleanup


class TestPluginScopeDirs(unittest.TestCase):
    """Verification that PLUGIN_SCOPE_DIRS covers all manifest-declared
    plugin directories (FIX-053 review finding F-001)."""

    def test_adapters_in_plugin_scope_dirs(self):
        """`adapters/` is declared in manifest.json product.entries and
        must be included in PLUGIN_SCOPE_DIRS so residual files under
        adapters/ are detected by scan_actual()."""
        self.assertIn(
            "adapters",
            cleanup.PLUGIN_SCOPE_DIRS,
            "FIX-053 F-001: PLUGIN_SCOPE_DIRS must include 'adapters' "
            "(declared in manifest.json product.entries line 32)",
        )

    def test_all_manifest_dirs_covered(self):
        """Every top-level directory declared in manifest.json
        product.entries must appear in or be a child of an entry in
        PLUGIN_SCOPE_DIRS.

        Nested dirs like ``skills/software-project-governance/core/``
        are already covered because ``skills/`` is in PLUGIN_SCOPE_DIRS
        and scan_actual() uses rglob.
        """
        manifest_path = (
            _INFRA_DIR.parent / "core" / "manifest.json"
        )
        if not manifest_path.exists():
            manifest_path = (
                Path.cwd()
                / "skills"
                / "software-project-governance"
                / "core"
                / "manifest.json"
            )

        if not manifest_path.exists():
            self.skipTest("manifest.json not found — cannot verify coverage")

        import json
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        manifest_dirs = set()
        for entry in manifest.get("product", {}).get("entries", []):
            if entry["type"] == "dir":
                dir_name = entry["path"].rstrip("/").rstrip("\\")
                manifest_dirs.add(dir_name)

        # A dir is "covered" if it IS in PLUGIN_SCOPE_DIRS, or is a
        # child of an entry in PLUGIN_SCOPE_DIRS.
        uncovered = set()
        for d in sorted(manifest_dirs):
            covered = d in cleanup.PLUGIN_SCOPE_DIRS or any(
                d.startswith(sd + "/") or d.startswith(sd + "\\")
                for sd in cleanup.PLUGIN_SCOPE_DIRS
            )
            if not covered:
                uncovered.add(d)

        self.assertEqual(
            set(),
            uncovered,
            f"FIX-053 F-001: manifest.json declares these top-level "
            f"dirs not covered by PLUGIN_SCOPE_DIRS: {uncovered}",
        )


if __name__ == "__main__":
    unittest.main()
