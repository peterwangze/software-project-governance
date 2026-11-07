"""FEAT-113 S1 — DSH plane identity resolution (design §3.2/§3.3/§3.4).

A *plane* is one executable host installation shape (design appendix B): the
asar desktop face, a disk ``node_modules`` face, a profile elevation tree, or
the PATH shim. :func:`resolve` walks the sources in exactly the contract's
``host.planes.precedence`` order and returns every plane it can identify —
each carrying the §3.2 identity object — without spawning anything.

Degradation semantics (§3.4):

* an **explicit** env point that is set but unusable surfaces as a
  ``PLANE_UNUSABLE`` plane and :func:`plane_verdict` degrades to ``NOT_RUN``;
  resolution never silently falls through to a later source;
* an **implicit** source (process probe, profile scan, PATH) that yields
  nothing is simply skipped — it contributes no plane and raises nothing.

All host facts (precedence order, env var names, asar runner flags, probe
bounds) are read from ``host-contract.json`` via :mod:`dsh_contract`; this
module keeps no second copy. The one env var that is *our* control knob and
not a host fact — the probe kill-switch — is a module constant.
"""

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

import dsh_asar

__all__ = ["Plane", "ProcessPort", "RealProcesses", "plane_verdict",
           "resolve"]

#: Our off-switch for the ancestor-process probe (design §3.2 source 3 / §11
#: R1): ``DSH_PLANE_PROBE_PROCESS=0`` disables the probe even where a caller
#: injected a port. Not a host fact, so it lives here rather than in the
#: contract; the probe's *bounds* (``max_ancestors``) are contract facts.
PROBE_SWITCH_ENV = "DSH_PLANE_PROBE_PROCESS"

PLANE_SCHEMA = "dsh-plane/1"
PLANE_UNUSABLE = "PLANE_UNUSABLE"

_KIND_ASAR = "asar-desktop"
_KIND_DISK = "disk-node-modules"
_KIND_PROFILE = "profile"
_KIND_PATH = "path-shim"

# ── contract facts (lazy; a defect surfaces as the accessor's exception) ────
_FACTS: Dict[str, str] = {
    "precedence": "host.planes.precedence",
    "desktop_env": "host.planes.env.desktop_app_dir",
    "profile_env": "host.planes.env.profile_dir",
    "install_env": "host.install.env_overrides.install_dir",
    "node_modules_env": "host.install.env_overrides.node_modules",
    "home_env": "host.env.home_var",
    "profiles_dir_name": "host.install.profiles_dir_name",
    "anchor_rel": "host.install.anchor_rel",
    "runtime_rel": "host.planes.asar.runtime_rel",
    "runner_module_flag": "host.planes.asar.runner.module_flag",
    "max_ancestors": "host.planes.process_probe.max_ancestors",
}

_fact_cache: Dict[str, Any] = {}


def _fact(name: str) -> Any:
    if name not in _fact_cache:
        import dsh_contract  # noqa: PLC0415 — lazy like every other reader

        value = dsh_contract.get(_FACTS[name])
        if name == "anchor_rel":
            value = tuple(value)
        _fact_cache[name] = value
    return _fact_cache[name]


def _env_text(env: Mapping[str, str], key: str) -> str:
    raw = env.get(key)
    return "" if raw is None else str(raw).strip()


def _posix(path) -> str:
    return str(path).replace("\\", "/")


def _join(*parts: str) -> str:
    return "/".join(part.strip("/\\") for part in parts if part.strip("/\\"))


def _anchor_rel() -> Tuple[str, ...]:
    return tuple(_fact("anchor_rel"))


def _anchor_file(node_modules: str) -> str:
    return _join(node_modules, *_anchor_rel())


def _anchor_ok(fs: dsh_asar.FsPort, node_modules: str) -> bool:
    return fs.is_file(_anchor_file(node_modules))


def _package_version(fs: dsh_asar.FsPort, node_modules: str) -> Optional[str]:
    """The CLI package version inside one plane (never imports anything)."""
    try:
        payload = json.loads(
            fs.read_bytes(_anchor_file(node_modules)).decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    version = payload.get("version") if isinstance(payload, dict) else None
    return version if isinstance(version, str) else None


# ── the plane identity object (§3.2) ────────────────────────────────────────
@dataclass(frozen=True)
class Plane:
    """One resolved plane; ``identity()`` is the report/evidence face."""

    kind: str
    source: str
    anchor: str
    resolution_anchor: Optional[str] = None
    node_modules: Optional[str] = None
    dsh_version: Optional[str] = None
    header_sha256: Optional[str] = None
    runner: Dict[str, Any] = field(default_factory=dict)
    runtime: Dict[str, Any] = field(default_factory=dict)
    asar: Dict[str, Any] = field(default_factory=dict)
    profile: Dict[str, Any] = field(default_factory=dict)
    informational: bool = False
    usable: bool = True
    reason: Optional[str] = None
    detail: str = ""

    def identity(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "schema": PLANE_SCHEMA,
            "kind": self.kind,
            "source": self.source,
            "anchor": _posix(self.anchor),
            "resolution_anchor": _posix(self.resolution_anchor)
            if self.resolution_anchor else None,
            "node_modules": _posix(self.node_modules)
            if self.node_modules else None,
            "dsh_version": self.dsh_version,
            "header_sha256": self.header_sha256,
            "runner": dict(self.runner),
            "runtime": dict(self.runtime),
            "asar": dict(self.asar),
            "profile": dict(self.profile),
            "informational": self.informational,
            "usable": self.usable,
            "reason": self.reason,
        }
        if self.detail:
            out["detail"] = self.detail
        return out


def _disk_runner() -> Dict[str, Any]:
    # §3.2: disk planes run on PATH node — never an ambient Electron variable
    return {"program": None, "electron_run_as_node": False,
            "module_flag": None, "source": "path-node"}


def _asar_runner(program: Optional[str], source: str) -> Dict[str, Any]:
    return {
        "program": _posix(program) if program else None,
        "electron_run_as_node": True,
        "module_flag": _fact("runner_module_flag"),
        "source": source,
    }


def _disk_plane(source: str, node_modules: str,
                fs: dsh_asar.FsPort) -> Plane:
    return Plane(
        kind=_KIND_DISK, source=source, anchor=node_modules,
        resolution_anchor=_anchor_file(node_modules),
        node_modules=node_modules,
        dsh_version=_package_version(fs, node_modules),
        runner=_disk_runner(),
    )


def _profile_plane(directory: str, node_modules: str,
                   fs: dsh_asar.FsPort) -> Plane:
    return Plane(
        kind=_KIND_PROFILE, source="home-profile", anchor=node_modules,
        resolution_anchor=_anchor_file(node_modules),
        node_modules=node_modules,
        dsh_version=_package_version(fs, node_modules),
        runner=_disk_runner(),
        profile={"dir": _posix(directory)},
    )


_identity_memo: Dict[Tuple[str, int], Dict[str, Any]] = {}


def _asar_runtime(fs: dsh_asar.FsPort, asar_path: str) -> Dict[str, Any]:
    """The §3.2 runtime fact: node version from ``runtime_rel`` beside the app.

    The JSON is the desktop app's runtime manifest (``{"node": "24.21.0", …}``
    on 0.2.2-rc.1); an unreadable or differently-shaped file degrades to a
    ``None`` version — a plane identity fact, never a failure.
    """
    runtime_rel = str(_fact("runtime_rel"))
    app_dir = os.path.dirname(os.path.dirname(str(asar_path)))
    runtime_path = _join(app_dir, runtime_rel)
    version = None
    if fs.is_file(runtime_path):
        try:
            payload = json.loads(fs.read_bytes(runtime_path).decode("utf-8"))
            if isinstance(payload, dict):
                candidate = payload.get("node")
                if not isinstance(candidate, str):
                    candidate = payload.get("version")
                if isinstance(candidate, str):
                    version = candidate
        except (OSError, ValueError, UnicodeDecodeError):
            version = None
    return {"version": version, "source": runtime_rel}


def _sibling_executable(fs: dsh_asar.FsPort, asar_path: str) -> Optional[str]:
    """The app's own ``*.exe`` beside ``resources/`` — the Electron runner.

    Real desktop installs carry two exes (``DeepSeek Harness.exe`` plus an
    ``Uninstall DeepSeek Harness.exe``): uninstallers are filtered by name
    prefix, and the pick is only made when exactly one candidate remains —
    ambiguity stays ``None`` (disclosed), never a guess.
    """
    app_dir = os.path.dirname(os.path.dirname(str(asar_path)))
    try:
        names = fs.list_dir(app_dir)
    except Exception:  # pragma: no cover - port robustness
        return None
    exes = [name for name in names
            if name.lower().endswith(".exe")
            and not name.lower().startswith("uninstall")]
    return _join(app_dir, exes[0]) if len(exes) == 1 else None


def _asar_plane(fs: dsh_asar.FsPort, asar_path: str, source: str,
                internal_prefix: Tuple[str, ...] = (),
                *, runner_program: Optional[str] = None,
                runner_source: str = "asar-sibling-executable",
                ) -> Tuple[Optional[Plane], str]:
    """Build the asar-desktop plane, or ``(None, detail)`` when unusable."""
    try:
        reader = dsh_asar.AsarReader(asar_path, fs=fs)
    except dsh_asar.AsarError as error:
        return None, f"unreadable archive: {error}"
    anchor_rel = _anchor_rel()
    if internal_prefix:
        anchor_entry = "/".join(internal_prefix + anchor_rel)
        try:
            reader.entry(anchor_entry)
        except dsh_asar.AsarError as error:
            return None, f"install anchor missing inside archive: {error}"
        hits = [anchor_entry]
    else:
        hits = dsh_asar.find_entry(reader.index, anchor_rel)
        if len(hits) != 1:
            return None, (f"install anchor matched {len(hits)} entries "
                          f"inside the archive, need exactly one")
    anchor_entry = hits[0]
    segments = anchor_entry.split("/")
    if "node_modules" in segments:
        nm_segments = segments[:segments.index("node_modules") + 1]
    else:  # pragma: no cover - anchor_rel always lives under node_modules
        nm_segments = segments[:-1]
    internal_nm = "/".join([_posix(asar_path)] + nm_segments)
    try:
        version = reader.read_json(anchor_entry).get("version")
    except (dsh_asar.AsarError, ValueError, UnicodeDecodeError) as error:
        return None, f"install anchor unreadable inside archive: {error}"
    if not isinstance(version, str):
        return None, "install anchor carries no version string"
    key = (str(asar_path), reader.file_size)
    identity = _identity_memo.get(key)
    if identity is None:
        identity = reader.identity()
        _identity_memo[key] = identity
    program = runner_program or _sibling_executable(fs, asar_path)
    return Plane(
        kind=_KIND_ASAR, source=source, anchor=str(asar_path),
        resolution_anchor=f"{_posix(asar_path)}/{anchor_entry}",
        node_modules=internal_nm,
        dsh_version=version,
        header_sha256=identity["header_sha256"],
        runner=_asar_runner(program, runner_source),
        runtime=_asar_runtime(fs, str(asar_path)),
        asar=dict(identity),
    ), ""


def _unusable(kind: str, source: str, anchor: str, detail: str) -> Plane:
    return Plane(kind=kind, source=source, anchor=anchor, usable=False,
                 reason=PLANE_UNUSABLE, detail=detail)


# ── the process seam (§3.2 source 3: injectable, off unless injected) ───────
class ProcessPort:
    """Read-only ancestor executables, nearest first."""

    def ancestor_executables(self, max_ancestors: int) -> List[str]:
        raise NotImplementedError  # pragma: no cover - interface


class RealProcesses(ProcessPort):
    """Windows Toolhelp32 parent-chain walk + full image names (read-only).

    Every step is best-effort: a denied handle, a missing snapshot or a
    non-Windows host yields a shorter list, never an exception. Nothing is
    written and nothing is spawned (§3.2: 不写、不 spawn).
    """

    def ancestor_executables(self, max_ancestors: int) -> List[str]:
        if sys.platform != "win32" or max_ancestors <= 0:
            return []
        try:
            return self._walk(max_ancestors)
        except Exception:  # tolerant by contract: probes never break resolution
            return []

    def _walk(self, max_ancestors: int) -> List[str]:
        import ctypes
        from ctypes import wintypes

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [
                ("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(wintypes.ULONG)),
                ("th32ModuleID", wintypes.DWORD),
                ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", wintypes.LONG),
                ("dwFlags", wintypes.DWORD),
                ("szExeFile", wintypes.WCHAR * 260),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # Explicit signatures: without restype the default c_int truncates,
        # so an INVALID_HANDLE_VALUE (0xFFFFFFFF…) snapshot would never match
        # and the failure would only surface later via Process32FirstW.
        kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        kernel32.CreateToolhelp32Snapshot.argtypes = [
            wintypes.DWORD, wintypes.DWORD]
        kernel32.Process32FirstW.restype = wintypes.BOOL
        kernel32.Process32FirstW.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
        kernel32.Process32NextW.restype = wintypes.BOOL
        kernel32.Process32NextW.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD)]
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        TH32CS_SNAPPROCESS = 0x2
        INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
        snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == INVALID_HANDLE_VALUE or not snapshot:
            return []
        parents: Dict[int, int] = {}
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
            while ok:
                parents[int(entry.th32ProcessID)] = \
                    int(entry.th32ParentProcessID)
                ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        finally:
            kernel32.CloseHandle(snapshot)
        chain: List[int] = []
        current = parents.get(os.getpid())
        while current is not None and current not in chain \
                and len(chain) < max_ancestors:
            chain.append(current)
            current = parents.get(current)
        out: List[str] = []
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        for pid in chain:
            handle = kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                continue
            try:
                size = wintypes.DWORD(1024)
                buffer = ctypes.create_unicode_buffer(size.value)
                if kernel32.QueryFullProcessImageNameW(
                        handle, 0, buffer, ctypes.byref(size)):
                    out.append(buffer.value)
            finally:
                kernel32.CloseHandle(handle)
        return out


# ── per-source resolvers (one per precedence entry) ─────────────────────────
def _asar_rel_from_runtime(fs: dsh_asar.FsPort, app_dir: str) -> Optional[str]:
    """``<app_dir>/<resources>/app.asar`` — the first ``runtime_rel`` segment
    is the resources dir the desktop archive lives in (§3.2 shapes ①/②)."""
    resources = str(_fact("runtime_rel")).split("/")[0]
    candidate = _join(app_dir, resources, "app.asar")
    return candidate if fs.is_file(candidate) else None


def _split_asar_component(value: str) -> Optional[Tuple[str, Tuple[str, ...]]]:
    """Split ``<…>/x.asar/<internal prefix>`` into (asar, prefix) — or None."""
    segments = [part for part in str(value).replace("\\", "/").split("/")
                if part]
    for index in range(len(segments) - 1, -1, -1):
        if segments[index].lower().endswith(".asar"):
            return "/".join(segments[:index + 1]), tuple(segments[index + 1:])
    return None


def _source_env_install_dir(env: Mapping[str, str], fs: dsh_asar.FsPort,
                            processes: Optional[ProcessPort]) -> List[Plane]:
    source = f"env:{_fact('install_env')}"
    raw = _env_text(env, _fact("install_env"))
    if not raw:
        return []
    split = _split_asar_component(raw)
    if split is not None:  # shape ② (asar file) or ③ (asar-internal prefix)
        asar_path, prefix = split
        if not fs.is_file(asar_path):
            return [_unusable(_KIND_ASAR, source, asar_path,
                              f"{asar_path} is not an asar file")]
        plane, detail = _asar_plane(fs, asar_path, source, prefix)
        return [plane] if plane else [
            _unusable(_KIND_ASAR, source, asar_path, detail)]
    asar_path = _asar_rel_from_runtime(fs, raw)  # shape ① (app directory)
    if asar_path is not None:
        plane, detail = _asar_plane(fs, asar_path, source)
        return [plane] if plane else [
            _unusable(_KIND_ASAR, source, asar_path, detail)]
    for candidate in (raw, _join(raw, "node_modules")):  # shape ④ (disk)
        if _anchor_ok(fs, candidate):
            return [_disk_plane(source, candidate, fs)]
    return [_unusable(_KIND_DISK, source, raw,
                      f"neither an app/asar location nor a node_modules "
                      f"carrying {'/'.join(_anchor_rel())}")]


def _source_env_desktop_app_dir(env: Mapping[str, str], fs: dsh_asar.FsPort,
                                processes: Optional[ProcessPort]) -> List[Plane]:
    source = f"env:{_fact('desktop_env')}"
    raw = _env_text(env, _fact("desktop_env"))
    if not raw:
        return []
    asar_path = _asar_rel_from_runtime(fs, raw)
    if asar_path is None:
        return [_unusable(
            _KIND_ASAR, source, raw,
            f"no app.asar under {raw} (checked the "
            f"{str(_fact('runtime_rel')).split('/')[0]} directory)")]
    plane, detail = _asar_plane(fs, asar_path, source)
    return [plane] if plane else [
        _unusable(_KIND_ASAR, source, asar_path, detail)]


def _source_process_ancestor(env: Mapping[str, str], fs: dsh_asar.FsPort,
                             processes: Optional[ProcessPort]) -> List[Plane]:
    if processes is None:  # off by default (§9.1: the port IS the opt-in)
        return []
    if _env_text(env, PROBE_SWITCH_ENV) == "0":
        return []
    try:
        executables = processes.ancestor_executables(
            int(_fact("max_ancestors")))
    except Exception:  # a broken port never breaks plane resolution
        return []
    planes: List[Plane] = []
    seen = set()
    for executable in executables:
        app_dir = os.path.dirname(str(executable))
        asar_path = _asar_rel_from_runtime(fs, app_dir)
        if asar_path is None or asar_path in seen:
            continue
        plane, _ = _asar_plane(fs, asar_path, "process-ancestor",
                               runner_program=str(executable),
                               runner_source="process-ancestor")
        if plane is not None:
            seen.add(asar_path)
            planes.append(plane)
    return planes


def _source_env_harness_node_modules(env: Mapping[str, str],
                                     fs: dsh_asar.FsPort,
                                     processes: Optional[ProcessPort]
                                     ) -> List[Plane]:
    source = f"env:{_fact('node_modules_env')}"
    raw = _env_text(env, _fact("node_modules_env"))
    if not raw:
        return []
    if _anchor_ok(fs, raw):
        return [_disk_plane(source, raw, fs)]
    return [_unusable(_KIND_DISK, source, raw,
                      f"no {'/'.join(_anchor_rel())} under {raw}")]


def _elevation_tree(fs: dsh_asar.FsPort, node_modules: str) -> bool:
    """A profile plane's usability criterion — the elevation tree itself.

    Profiles are pnpm workspaces: the CLI anchor package legitimately lives
    only in the install tree (design §1.2 F8 — the desktop profile carries
    neither the CLI nor a full oracle set), so the §3.2 criterion is the
    tree itself: a ``node_modules`` directory that actually contains
    packages. An empty or missing tree is not a plane.
    """
    return fs.is_dir(node_modules) and bool(fs.list_dir(node_modules))


def _source_home_profile(env: Mapping[str, str], fs: dsh_asar.FsPort,
                         processes: Optional[ProcessPort]) -> List[Plane]:
    explicit = _env_text(env, _fact("profile_env"))
    if explicit:
        for candidate, directory in (
                (_join(explicit, "node_modules"), explicit),
                (explicit, explicit)):
            if _elevation_tree(fs, candidate):
                return [_profile_plane(directory, candidate, fs)]
        return [_unusable(_KIND_PROFILE, "home-profile", explicit,
                          f"explicit {_fact('profile_env')} has no "
                          f"node_modules elevation tree")]
    home = _env_text(env, _fact("home_env"))
    if not home:  # never guesses ~/.dsh (the probe-side safety property)
        return []
    profiles_dir = _join(home, str(_fact("profiles_dir_name")))
    candidates: List[Tuple[float, str, str]] = []
    for name in fs.list_dir(profiles_dir):
        node_modules = _join(profiles_dir, name, "node_modules")
        if _elevation_tree(fs, node_modules):
            candidates.append((fs.mtime(node_modules),
                               _join(profiles_dir, name), node_modules))
    mirror = _join(profiles_dir, "node_modules")
    if _elevation_tree(fs, mirror):
        candidates.append((fs.mtime(mirror), profiles_dir, mirror))
    candidates.sort(key=lambda item: item[0], reverse=True)  # newest first
    return [_profile_plane(directory, node_modules, fs)
            for _, directory, node_modules in candidates]


#: ``dsh``/``dsh.exe``/``dsh.CMD``… — the PATHEXT order that matters here
_SHIM_NAMES = ("dsh.exe", "dsh.CMD", "dsh.cmd", "dsh.bat", "dsh.com", "dsh")


def _which_dsh(env: Mapping[str, str], fs: dsh_asar.FsPort) -> Optional[str]:
    for directory in str(env.get("PATH", "")).split(os.pathsep):
        directory = directory.strip()
        if not directory:
            continue
        for name in _SHIM_NAMES:
            candidate = _join(directory, name)
            if fs.is_file(candidate):
                return candidate
    return None


def _walk_up_node_modules(fs: dsh_asar.FsPort, start: str) -> Optional[str]:
    current = start
    while True:
        if current.rstrip("/").endswith("/node_modules") \
                and _anchor_ok(fs, current):
            return current
        candidate = _join(current, "node_modules")
        if _anchor_ok(fs, candidate):
            return candidate
        parent = os.path.dirname(current.rstrip("/"))
        if parent.rstrip("/") == current.rstrip("/"):
            return None
        current = parent


def _source_path(env: Mapping[str, str], fs: dsh_asar.FsPort,
                 processes: Optional[ProcessPort]) -> List[Plane]:
    shim = _which_dsh(env, fs)
    if shim is None:
        return []
    node_modules = _walk_up_node_modules(fs, os.path.dirname(shim))
    if node_modules is None:
        return []
    return [Plane(
        kind=_KIND_PATH, source="path", anchor=shim,
        resolution_anchor=_anchor_file(node_modules),
        node_modules=node_modules,
        dsh_version=_package_version(fs, node_modules),
        runner=_disk_runner(), informational=True,
    )]


_HANDLERS = {
    "env:DSH_INSTALL_DIR": _source_env_install_dir,
    "env:DSH_DESKTOP_APP_DIR": _source_env_desktop_app_dir,
    "process-ancestor": _source_process_ancestor,
    "env:DSH_HARNESS_NODE_MODULES": _source_env_harness_node_modules,
    "home-profile": _source_home_profile,
    "path": _source_path,
}


def resolve(env: Optional[Mapping[str, str]] = None,
            fs: Optional[dsh_asar.FsPort] = None,
            processes: Optional[ProcessPort] = None) -> List[Plane]:
    """Resolve every plane, in the contract's precedence order (§3.2).

    ``env`` is the only environment source (never ``os.environ``); ``fs`` is
    the read-only filesystem port (default: real files); ``processes`` is the
    ancestor-probe port — **absent means the probe stays off** (the caller
    decides, per ``host.planes.process_probe.enabled_in``). An explicit env
    point that is set but unusable stops resolution with that single
    ``PLANE_UNUSABLE`` plane: never a silent fallback (§3.4).
    """
    environment: Dict[str, str] = dict(env or {})
    port = fs if fs is not None else dsh_asar.RealFs()
    planes: List[Plane] = []
    for source in list(_fact("precedence")):
        handler = _HANDLERS.get(source)
        if handler is None:
            # A precedence entry without a resolver is contract drift —
            # loud, never skipped (design §13.4 rule 7).
            raise ValueError(
                f"host.planes.precedence names unknown source {source!r}")
        for plane in handler(environment, port, processes):
            if not plane.usable:
                return [plane]  # explicit + unusable: NOT_RUN, no fallback
            planes.append(plane)
    return planes


def plane_verdict(planes: List[Plane]) -> Tuple[str, str]:
    """``(verdict, reason)`` for a resolution result (§3.4).

    ``NOT_RUN`` + ``PLANE_UNUSABLE`` exactly when an explicit plane was set
    but unusable; ``OK`` otherwise (an empty list is a valid no-plane result —
    callers decide what an empty machine means).
    """
    for plane in planes:
        if not plane.usable:
            reason = plane.reason or PLANE_UNUSABLE
            detail = f": {plane.detail}" if plane.detail else ""
            return "NOT_RUN", f"{reason}{detail}"
    return "OK", ""
