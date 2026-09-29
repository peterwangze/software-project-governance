"""FIX-405 / RISK-061: security-descriptor readability scan gate.

REL-095 M-1 window evidence (2026-09-29): writes performed under the DSH
sandbox's restricted token produced files/directories whose Windows
security descriptors deny the CURRENT user READ_CONTROL/DELETE — 20
instances (root package.json / the plugin.json faces / DSH AGENTS +
preset templates / core manifest.json / infra hooks x4 / e2e demos x6 /
governance tmp). The root mechanism is undetermined (restricted-token
creation of protected DACLs vs other); this leaf is the 终局处置件's
machine face: probe the WRITE-AFFECTED surfaces with ``os.access(R_OK)``
right after the writing commands (release-projection --write, the release
gate) and name every unreadable path together with the takeown/icacls
remediation template — the damage becomes visible at the moment it is
caused, not at the next random access (fail-loud, never silently).

Layer placement: measurement + guidance leaf (``checks`` package,
ArchGuard R1 discipline — the engine wires dispatch only). The scanner
takes an injectable ``access`` so tests can simulate denial without
touching real descriptors.
"""

import os
from pathlib import Path

__all__ = [
    "HOOK_FACE",
    "REMEDIATION_TEMPLATE_FILE",
    "REMEDIATION_TEMPLATE_DIR",
    "hooks_face_paths",
    "projection_face_paths",
    "remediation_for",
    "scan_sd_readability",
]

#: The four governance hooks the plugin installs into ``.git/hooks`` —
#: the RISK-061 evidence face (infra hooks x4).
HOOK_FACE = ("pre-commit", "prepare-commit-msg", "commit-msg", "post-commit")

REMEDIATION_TEMPLATE_FILE = (
    'takeown /f "{path}" && icacls "{path}" /grant "%USERNAME%":F')
REMEDIATION_TEMPLATE_DIR = (
    'takeown /f "{path}" /r /d y && icacls "{path}" /grant "%USERNAME%":F /t')


def remediation_for(path):
    """The Windows ownership+ACL recovery command template for one path.

    Directories take the recursive variants (``/r`` walk + ``/t`` grant
    inheritance) — a damaged hooks DIRECTORY must heal its children too.
    FIX-406 P3-2: an is_dir probe that itself FAILS (an SD-damaged
    directory can make stat raise) falls back to the RECURSIVE template —
    the file template would lose the /t inheritance grant for the
    directory's children (fail-safe to the wider repair surface).
    """
    text = str(path)
    is_dir = True
    try:
        is_dir = Path(path).is_dir()
    except OSError:
        is_dir = True
    template = (REMEDIATION_TEMPLATE_DIR if is_dir
                else REMEDIATION_TEMPLATE_FILE)
    return template.format(path=text)


def hooks_face_paths(root):
    """The .git/hooks face: the directory itself + the four hook files."""
    hooks_dir = Path(root) / ".git" / "hooks"
    faces = [hooks_dir]
    faces.extend(hooks_dir / name for name in HOOK_FACE)
    return faces


def projection_face_paths(root, config_path=None):
    """The release-projection target face, resolved from the live plan.

    Fail-closed shape: a plan that cannot even be built reports an
    ``error`` key with an empty path list — the caller's existing BLOCKED
    face owns that failure; the SD scan never silently skips.
    """
    from release.projection import build_projection_plan
    root = Path(root).resolve()
    try:
        _version, plan = build_projection_plan(root, config_path)
    except Exception as exc:  # noqa: BLE001 — disclosure, never silent
        return {"error": "projection plan unreadable: {0}".format(exc),
                "paths": []}
    return {"paths": [root / write.relative_path for write in plan]}


def scan_sd_readability(paths, access=None):
    """Probe every path for READ permission; name the unreadable.

    ``access`` is injectable (tests simulate denial); the production
    default is :func:`os.access` with ``os.R_OK`` — the observable of the
    RISK-061 damage class (denied READ_CONTROL surfaces as unreadable to
    the current token). An ``OSError`` from the probe itself counts as
    unreadable (fail-closed, never fail-open).
    """
    access = access or os.access
    items = list(paths)
    unreadable = []
    for path in items:
        try:
            readable = bool(access(path, os.R_OK))
        except OSError:
            readable = False
        if not readable:
            unreadable.append(str(path))
    return {
        "scanned": len(items),
        "unreadable": unreadable,
        "remediation": [remediation_for(path) for path in unreadable],
        "pass": not unreadable,
    }
