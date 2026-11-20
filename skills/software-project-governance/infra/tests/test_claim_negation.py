"""Boundary cases for the shared claim matcher at its three callers."""

import subprocess
import sys
import unittest
from pathlib import Path


INFRA = Path(__file__).resolve().parents[1]
if str(INFRA) not in sys.path:
    sys.path.insert(0, str(INFRA))

import archguard_ratchet
import verify_workflow
from checks import capability_registry, flow_unit_runtime


class ClaimNegationTests(unittest.TestCase):
    def test_callers_preserve_negation_scope_and_their_own_vocabulary(self):
        phrase = "risk-036 closed"
        cases = [
            ("no supporting evidence", False, False),
            (phrase, False, False),
            (f"NOT {phrase.upper()}", True, True),
            (f"nobody reported {phrase}", False, False),
            (f"不声明{phrase}", True, True),
            (f"{phrase}仍不可发布", True, True),
            (f"not verified；{phrase}", False, False),
            (f"no {phrase}; {phrase}", False, False),
            (f"no {phrase}; not {phrase}", True, True),
            (f"no official approval, external first-session pilot success, and {phrase}", True, False),
            (f"no risk-037 closed, planning and confirming {phrase}", True, True),
        ]
        for text, general, visibility in cases:
            with self.subTest(text=text):
                self.assertEqual(verify_workflow._line_has_scoped_claim_negation(text, phrase), general)
                self.assertEqual(capability_registry._line_has_scoped_claim_negation(text, phrase), general)
                self.assertEqual(flow_unit_runtime._claim_is_negated(text, phrase), visibility)

    def test_layer_matrix_allows_both_domains_to_import_the_shared_matcher(self):
        matcher = "infra/claim_negation.py"
        modules = {
            matcher: archguard_ratchet.DEFAULT_MANAGED_MODULES[matcher],
            "infra/checks/capability_registry.py": {"layer": "L3"},
            "infra/checks/flow_unit_runtime.py": {"layer": "L3"},
        }
        violations, report = archguard_ratchet.check_r3(modules, INFRA)
        self.assertEqual(violations, [])
        self.assertEqual(report["managed_edges"], 2)

    def test_v1_file_spec_loads_the_sibling_without_an_installed_checks_package(self):
        source = INFRA / "checks" / "flow_unit_runtime.py"
        script = """
import importlib.util, sys, types
if sys.argv[3] == "foreign":
    unrelated = types.ModuleType("claim_negation")
    unrelated.__spec__ = importlib.util.spec_from_file_location("claim_negation", sys.argv[1])
    sys.modules["claim_negation"] = unrelated
spec = importlib.util.spec_from_file_location(sys.argv[2], sys.argv[1])
mod = importlib.util.module_from_spec(spec)
paths = sys.path.copy()
spec.loader.exec_module(mod)
assert mod._claim_is_negated("not ready", "ready")
assert not mod._claim_is_negated("ready", "ready")
assert sys.path == paths
assert "checks" not in sys.modules and "verify_workflow" not in sys.modules
"""
        for name in ("standalone_v1", "checks.flow_unit_runtime"):
            for ambient in ("absent", "foreign"):
                with self.subTest(name=name, ambient=ambient):
                    subprocess.run(
                        [sys.executable, "-I", "-B", "-c", script, str(source), name, ambient],
                        check=True,
                    )


if __name__ == "__main__":
    unittest.main()
