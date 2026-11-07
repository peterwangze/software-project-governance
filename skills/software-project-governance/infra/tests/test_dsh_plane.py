"""FEAT-113 S1 tests — plane identity resolution (design §3.2/§3.4).

Synthetic env/fs/process ports only (§9.3): the fake asar is built from
bytes in the test, the fake filesystem is a dict, the fake process port
returns canned executables. Nothing here touches the real ``D:\\app\\dsh``.
"""

import json
import os
import struct
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INFRA_DIR = _HERE.parent

if str(_INFRA_DIR) not in sys.path:
    sys.path.insert(0, str(_INFRA_DIR))

import dsh_asar  # noqa: E402
import dsh_contract  # noqa: E402
import dsh_plane  # noqa: E402


def _pad4(text_bytes):
    return b"\x00" * ((-len(text_bytes)) % 4)


def _build_archive(entries):
    """The same tiny synthetic asar shape as ``test_dsh_asar._build_archive``."""
    index = {"files": {}}
    content = bytearray()
    for rel, blob in entries.items():
        node = index
        parts = rel.split("/")
        for part in parts[:-1]:
            node = node["files"].setdefault(part, {"files": {}})
        node["files"][parts[-1]] = {"size": len(blob),
                                    "offset": str(len(content))}
        content.extend(blob)
    text = json.dumps(index).encode("utf-8")
    pad = _pad4(text)
    payload = 8 + len(text) + len(pad)
    header = struct.pack("<IIII", 4, payload, 4 + len(text) + len(pad),
                         len(text))
    return header + text + pad + bytes(content)


class _FakeFs(dsh_asar.FsPort):
    """Dict-backed filesystem: bytes = file, ``None`` = directory."""

    def __init__(self):
        self.files = {}

    def add_file(self, path, blob):
        self.files[str(path)] = blob
        return path

    def add_dir(self, path):
        self.files[str(path)] = None
        return path

    def exists(self, path):
        return str(path) in self.files

    def is_file(self, path):
        return self.files.get(str(path)) is not None

    def is_dir(self, path):
        return str(path) in self.files and self.files[str(path)] is None

    def size(self, path):
        value = self.files.get(str(path))
        return len(value) if value is not None else 0

    def read_head(self, path, count):
        return self.files[str(path)][:count]

    def read_at(self, path, offset, count):
        return self.files[str(path)][offset:offset + count]

    def read_bytes(self, path):
        return self.files[str(path)]

    def list_dir(self, path):
        prefix = str(path).rstrip("\\/") + "/"
        names = set()
        for candidate in self.files:
            if candidate.startswith(prefix) and len(candidate) > len(prefix):
                names.add(candidate[len(prefix):].split("/")[0])
        return sorted(names)

    def mtime(self, path):
        key = str(path) + ".mtime"
        return float(self.files[key]) if key in self.files else 0.0


class _FakeProcesses:
    """ProcessPort double: canned executables + a call recorder."""

    def __init__(self, executables):
        self.executables = list(executables)
        self.calls = []

    def ancestor_executables(self, max_ancestors):
        self.calls.append(max_ancestors)
        return list(self.executables)


class _BoomProcesses(_FakeProcesses):

    def ancestor_executables(self, max_ancestors):
        raise AssertionError("the probe must not run when it is off")


def _desktop_app(fs, *, root="D:/app/dsh", version="0.2.2-rc.1",
                 node="24.21.0", exe="DeepSeek Harness.exe"):
    """A synthetic desktop installation: app dir + asar + sibling runtime."""
    asar = f"{root}/resources/app.asar"
    blob = _build_archive({
        "dsh/node_modules/@deepseek-ai/dsh/package.json":
            json.dumps({"version": version}).encode("utf-8"),
    })
    fs.add_file(asar, blob)
    fs.add_dir(f"{root}/resources")
    fs.add_dir(f"{root}/resources/runtime")
    fs.add_file(f"{root}/resources/runtime/versions.json",
                json.dumps({"node": node, "pnpm": "11.28.5"}).encode("utf-8"))
    fs.add_file(f"{root}/{exe}", b"MZ-fake")
    return root, asar


def _node_modules(fs, path, version="0.2.1-rc.2"):
    fs.add_dir(path)
    fs.add_file(f"{path}/@deepseek-ai/dsh/package.json",
                json.dumps({"version": version}).encode("utf-8"))
    return path


_ANCHOR = "@deepseek-ai/dsh/package.json"


class PrecedenceTests(unittest.TestCase):
    """§3.2: the order is exactly the contract's `host.planes.precedence`."""

    def test_every_source_contributing_produces_planes_in_contract_order(self):
        fs = _FakeFs()
        app, asar = _desktop_app(fs, root="D:/app/dsh")
        _node_modules(fs, "synth/npm/node_modules")
        fs.add_dir("D:/home/profiles")
        _node_modules(fs, "D:/home/profiles/desktop/node_modules",
                      version="0.2.1-rc.2")
        _node_modules(fs, "synth/shim/node_modules", version="0.2.1-rc.2")
        fs.add_file("synth/shim/dsh.exe", b"MZ")
        env = {
            "DSH_INSTALL_DIR": app,
            "DSH_DESKTOP_APP_DIR": app,
            "DSH_HARNESS_NODE_MODULES": "synth/npm/node_modules",
            "DSH_HOME": "D:/home",
            # FIX-485: separator-free PATH entry (no ":" — POSIX splits on it)
            "PATH": os.pathsep.join(["synth/shim"]),
        }
        planes = dsh_plane.resolve(env, fs=fs,
                                   processes=_FakeProcesses(
                                       ["D:/app/dsh/DeepSeek Harness.exe"]))
        self.assertEqual([plane.source for plane in planes],
                         dsh_contract.get("host.planes.precedence"))
        # one plane per source, each carrying its own version fact
        by_source = {plane.source: plane for plane in planes}
        self.assertEqual(by_source["env:DSH_INSTALL_DIR"].dsh_version,
                         "0.2.2-rc.1")
        self.assertEqual(by_source["process-ancestor"].kind, "asar-desktop")
        self.assertEqual(by_source["env:DSH_HARNESS_NODE_MODULES"].kind,
                         "disk-node-modules")
        self.assertEqual(by_source["home-profile"].kind, "profile")
        self.assertEqual(by_source["path"].kind, "path-shim")
        self.assertTrue(by_source["path"].informational)

    def test_the_pinned_precedence_is_the_six_declared_sources(self):
        self.assertEqual(dsh_contract.get("host.planes.precedence"), [
            "env:DSH_INSTALL_DIR", "env:DSH_DESKTOP_APP_DIR",
            "process-ancestor", "env:DSH_HARNESS_NODE_MODULES",
            "home-profile", "path",
        ])


class InstallDirShapesTests(unittest.TestCase):
    """§3.2 source 1: the four accepted DSH_INSTALL_DIR shapes."""

    def test_app_dir_containing_resources_app_asar(self):
        fs = _FakeFs()
        app, _ = _desktop_app(fs)
        planes = dsh_plane.resolve({"DSH_INSTALL_DIR": app}, fs=fs)
        self.assertEqual(len(planes), 1)
        self.assertEqual(planes[0].kind, "asar-desktop")
        self.assertTrue(planes[0].header_sha256)
        self.assertEqual(planes[0].dsh_version, "0.2.2-rc.1")

    def test_asar_file_path_directly(self):
        fs = _FakeFs()
        _, asar = _desktop_app(fs)
        planes = dsh_plane.resolve({"DSH_INSTALL_DIR": asar}, fs=fs)
        self.assertEqual(planes[0].kind, "asar-desktop")
        self.assertEqual(planes[0].anchor.replace("\\", "/"), asar)

    def test_asar_internal_prefix_directory(self):
        fs = _FakeFs()
        _, asar = _desktop_app(fs)
        planes = dsh_plane.resolve(
            {"DSH_INSTALL_DIR": asar + "/dsh/node_modules"}, fs=fs)
        self.assertEqual(planes[0].kind, "asar-desktop")
        self.assertIn("/dsh/node_modules", planes[0].node_modules)

    def test_disk_node_modules_directory(self):
        fs = _FakeFs()
        _node_modules(fs, "D:/npm/node_modules")
        planes = dsh_plane.resolve(
            {"DSH_INSTALL_DIR": "D:/npm/node_modules"}, fs=fs)
        self.assertEqual(planes[0].kind, "disk-node-modules")
        self.assertIsNone(planes[0].header_sha256)


class ExplicitUnusableTests(unittest.TestCase):
    """§3.4: explicit-but-unusable never falls back; verdict is NOT_RUN."""

    def test_unusable_install_dir_yields_plane_unusable_and_not_run(self):
        fs = _FakeFs()
        # a later, perfectly usable source exists — it must NOT be used
        _node_modules(fs, "D:/npm/node_modules")
        planes = dsh_plane.resolve(
            {"DSH_INSTALL_DIR": "D:/nowhere", "DSH_HARNESS_NODE_MODULES":
             "D:/npm/node_modules"}, fs=fs)
        self.assertEqual(len(planes), 1)
        self.assertFalse(planes[0].usable)
        self.assertEqual(planes[0].reason, "PLANE_UNUSABLE")
        verdict, reason = dsh_plane.plane_verdict(planes)
        self.assertEqual(verdict, "NOT_RUN")
        self.assertIn("PLANE_UNUSABLE", reason)

    def test_unusable_desktop_app_dir_degrades_to_not_run(self):
        fs = _FakeFs()
        fs.add_dir("D:/empty-app")
        planes = dsh_plane.resolve({"DSH_DESKTOP_APP_DIR": "D:/empty-app"},
                                   fs=fs)
        self.assertEqual(planes[0].reason, "PLANE_UNUSABLE")
        self.assertEqual(dsh_plane.plane_verdict(planes)[0], "NOT_RUN")

    def test_a_corrupt_asar_header_under_an_explicit_dir_is_unusable(self):
        fs = _FakeFs()
        fs.add_dir("D:/broken/resources")
        fs.add_file("D:/broken/resources/app.asar", b"\x07\x00\x00\x00junk")
        planes = dsh_plane.resolve({"DSH_DESKTOP_APP_DIR": "D:/broken"},
                                   fs=fs)
        self.assertFalse(planes[0].usable)
        self.assertEqual(planes[0].reason, "PLANE_UNUSABLE")

    def test_unusable_explicit_profile_dir_is_unusable(self):
        fs = _FakeFs()
        planes = dsh_plane.resolve({"DSH_PROFILE_DIR": "D:/no-profile"},
                                   fs=fs)
        self.assertEqual(planes[0].reason, "PLANE_UNUSABLE")

    def test_usable_planes_verdict_ok(self):
        fs = _FakeFs()
        _node_modules(fs, "D:/npm/node_modules")
        planes = dsh_plane.resolve(
            {"DSH_HARNESS_NODE_MODULES": "D:/npm/node_modules"}, fs=fs)
        self.assertEqual(dsh_plane.plane_verdict(planes), ("OK", ""))


class ProcessProbeTests(unittest.TestCase):
    """§3.2 source 3: injectable, OFF by default, env kill-switch."""

    def test_the_probe_is_off_by_default_and_the_port_is_never_called(self):
        fs = _FakeFs()
        _desktop_app(fs)
        planes = dsh_plane.resolve({}, fs=fs, processes=None)
        self.assertEqual([p.kind for p in planes], [])
        # a port handed in still must not run when later sources answer

    def test_no_port_means_the_probe_source_contributes_nothing(self):
        fs = _FakeFs()
        app, _ = _desktop_app(fs)
        planes = dsh_plane.resolve({"DSH_INSTALL_DIR": app}, fs=fs,
                                   processes=None)
        self.assertEqual([plane.source for plane in planes],
                         ["env:DSH_INSTALL_DIR"])

    def test_the_probe_finds_an_ancestor_desktop_install(self):
        fs = _FakeFs()
        _desktop_app(fs)
        probe = _FakeProcesses(["D:/app/dsh/DeepSeek Harness.exe"])
        planes = dsh_plane.resolve({}, fs=fs, processes=probe)
        self.assertEqual(len(planes), 1)
        plane = planes[0]
        self.assertEqual(plane.source, "process-ancestor")
        self.assertEqual(plane.kind, "asar-desktop")
        self.assertEqual(plane.runner["program"],
                         "D:/app/dsh/DeepSeek Harness.exe")
        self.assertTrue(plane.runner["electron_run_as_node"])
        self.assertEqual(plane.runner["module_flag"], "--input-type=module")
        # the port saw the contract's bound
        self.assertEqual(probe.calls,
                         [dsh_contract.get(
                             "host.planes.process_probe.max_ancestors")])

    def test_the_env_kill_switch_disables_an_injected_probe(self):
        fs = _FakeFs()
        _desktop_app(fs)
        probe = _BoomProcesses(["D:/app/dsh/DeepSeek Harness.exe"])
        planes = dsh_plane.resolve({"DSH_PLANE_PROBE_PROCESS": "0"},
                                   fs=fs, processes=probe)
        self.assertEqual(planes, [])

    def test_an_ancestor_without_an_asar_contributes_no_plane(self):
        fs = _FakeFs()
        fs.add_file("C:/Windows/System32/cmd.exe", b"MZ")
        planes = dsh_plane.resolve({}, fs=fs,
                                   processes=_FakeProcesses(
                                       ["C:/Windows/System32/cmd.exe"]))
        self.assertEqual(planes, [])


class ProfilePlaneTests(unittest.TestCase):

    def test_dsh_home_profiles_are_listed_newest_mtime_first(self):
        fs = _FakeFs()
        fs.add_dir("D:/home/profiles")
        _node_modules(fs, "D:/home/profiles/old/node_modules", "0.1.0")
        _node_modules(fs, "D:/home/profiles/new/node_modules", "0.2.0")
        fs.files["D:/home/profiles/old/node_modules.mtime"] = 100
        fs.files["D:/home/profiles/new/node_modules.mtime"] = 200
        planes = dsh_plane.resolve({"DSH_HOME": "D:/home"}, fs=fs)
        profiled = [p for p in planes if p.kind == "profile"]
        self.assertEqual([p.dsh_version for p in profiled],
                         ["0.2.0", "0.1.0"])

    def test_unset_dsh_home_is_never_guessed(self):
        fs = _FakeFs()
        _node_modules(fs, "C:/Users/x/.dsh/profiles/p/node_modules")
        planes = dsh_plane.resolve({}, fs=fs)
        self.assertEqual(planes, [])

    def test_the_installation_mirror_is_a_plane_too(self):
        fs = _FakeFs()
        fs.add_dir("D:/home/profiles")
        _node_modules(fs, "D:/home/profiles/node_modules", "0.2.1-rc.2")
        planes = dsh_plane.resolve({"DSH_HOME": "D:/home"}, fs=fs)
        self.assertEqual(len(planes), 1)
        self.assertEqual(planes[0].profile["dir"], "D:/home/profiles")

    def test_explicit_profile_dir_beats_the_home_scan(self):
        fs = _FakeFs()
        fs.add_dir("D:/home/profiles")
        _node_modules(fs, "D:/home/profiles/other/node_modules", "0.1.0")
        _node_modules(fs, "D:/explicit/prof/node_modules", "9.9.9")
        planes = dsh_plane.resolve({"DSH_HOME": "D:/home",
                                    "DSH_PROFILE_DIR": "D:/explicit/prof"},
                                   fs=fs)
        self.assertEqual(len(planes), 1)
        self.assertEqual(planes[0].dsh_version, "9.9.9")
        self.assertEqual(planes[0].source, "home-profile")


class PathShimTests(unittest.TestCase):

    def test_the_path_shim_is_last_and_informational(self):
        fs = _FakeFs()
        # FIX-485: the fake PATH entry must carry no ":" (the POSIX path
        # separator) — a "D:/…" fixture split into ["D", "/…"] on Linux CI
        # and the shim vanished. Synthetic roots are separator-free.
        _node_modules(fs, "synth/npm/node_modules")
        fs.add_file("synth/npm/dsh.exe", b"MZ")
        planes = dsh_plane.resolve(
            {"PATH": os.pathsep.join(["synth/npm"])}, fs=fs)
        self.assertEqual(len(planes), 1)
        self.assertEqual(planes[0].kind, "path-shim")
        self.assertEqual(planes[0].source, "path")
        self.assertTrue(planes[planes.__len__() - 1].informational)
        self.assertEqual(planes[0].dsh_version, "0.2.1-rc.2")
        self.assertEqual(planes[0].node_modules, "synth/npm/node_modules")

    def test_no_path_means_no_shim_plane(self):
        fs = _FakeFs()
        self.assertEqual(dsh_plane.resolve({"PATH": ""}, fs=fs), [])

    def test_a_shim_without_an_install_anchor_is_skipped(self):
        fs = _FakeFs()
        fs.add_file("synth/bare/dsh.exe", b"MZ")
        self.assertEqual(
            dsh_plane.resolve({"PATH": os.pathsep.join(["synth/bare"])}, fs=fs),
            [])


class AsarIdentityTests(unittest.TestCase):

    def test_the_real_install_exes_do_not_confuse_the_runner_pick(self):
        # R1 (review finding 3): real desktop installs carry
        # "DeepSeek Harness.exe" AND "Uninstall DeepSeek Harness.exe" — the
        # uninstaller must not blank the runner program.
        fs = _FakeFs()
        app, asar = _desktop_app(fs)
        fs.add_file(f"{app}/Uninstall DeepSeek Harness.exe", b"MZ-uninstall")
        planes = dsh_plane.resolve({"DSH_DESKTOP_APP_DIR": app}, fs=fs)
        self.assertEqual(planes[0].runner["program"],
                         "D:/app/dsh/DeepSeek Harness.exe")
        self.assertEqual(planes[0].runner["source"],
                         "asar-sibling-executable")

    def test_the_identity_object_shape(self):
        fs = _FakeFs()
        app, asar = _desktop_app(fs)
        planes = dsh_plane.resolve({"DSH_DESKTOP_APP_DIR": app}, fs=fs)
        identity = planes[0].identity()
        self.assertEqual(identity["schema"], "dsh-plane/1")
        self.assertEqual(identity["kind"], "asar-desktop")
        self.assertEqual(identity["source"], "env:DSH_DESKTOP_APP_DIR")
        self.assertEqual(identity["anchor"].replace("\\", "/"), asar)
        self.assertEqual(identity["dsh_version"], "0.2.2-rc.1")
        self.assertEqual(identity["header_sha256"],
                         identity["asar"]["header_sha256"])
        self.assertEqual(identity["runtime"],
                         {"version": "24.21.0",
                          "source": dsh_contract.get(
                              "host.planes.asar.runtime_rel")})
        self.assertIn("runner", identity)
        self.assertEqual(identity["node_modules"],
                         f"{asar}/dsh/node_modules".replace("\\", "/"))
        self.assertTrue(identity["runner"]["electron_run_as_node"])

    def test_the_disk_identity_has_no_asar_face(self):
        fs = _FakeFs()
        _node_modules(fs, "D:/npm/node_modules")
        planes = dsh_plane.resolve(
            {"DSH_HARNESS_NODE_MODULES": "D:/npm/node_modules"}, fs=fs)
        identity = planes[0].identity()
        self.assertIsNone(identity["header_sha256"])
        self.assertEqual(identity["asar"], {})
        self.assertFalse(identity["runner"]["electron_run_as_node"])


class ImplicitSkipTests(unittest.TestCase):
    """§3.4: implicit sources skip and stay disclosed, never block."""

    def test_a_corrupt_profile_plane_is_skipped_not_fatal(self):
        fs = _FakeFs()
        fs.add_dir("D:/home/profiles")
        fs.add_dir("D:/home/profiles/broken/node_modules")
        # no package.json inside — unusable, but implicit: no plane, no raise
        planes = dsh_plane.resolve({"DSH_HOME": "D:/home"}, fs=fs)
        self.assertEqual(planes, [])

    def test_no_plane_at_all_resolves_to_an_empty_list(self):
        self.assertEqual(dsh_plane.resolve({}, fs=_FakeFs()), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
