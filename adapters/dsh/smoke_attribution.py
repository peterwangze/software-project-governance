#!/usr/bin/env python3
"""Pure witness + FIX-442 attribution machinery for the dsh smoke gate.

Split out of ``launch.py`` (FIX-442, 28n module_size debt): the isolated
preset-session smoke gate (FEAT-015 / RISK-049 ②) compares before/after
witness samples of the real DSH home, and since FIX-442 it must tolerate
write-face changes a CONCURRENT ACTIVE SESSION made during the smoke
window — the 2026-09-13 and 2026-10-10 false positives were a live session
re-rendering its own ``novel-writing`` preset while the smoke ran.

Everything here is PURE with respect to the host contract: no function
reads ``host-contract.json``. The one contract fact the attribution needs
(the adapter's own preset id) is passed in by ``launch.py`` from
``_fact("PRESET_ID")``, so this module can never become a second source
of a declared value (K-2 discipline).

Judgment contract (FIX-442, dual factor — single-factor miss = FAIL):

  * time window — the change happened inside the before/after sampling
    interval (appeared entries prove it by mtime; disappeared entries are
    interval-bounded by the samples themselves);
  * entry semantics — the entry is NOT on this adapter's own write face,
    because a live session owns its preset ids while the adapter's own
    preset face is the one face it could have written.

Both factors together ⇒ the entry is reported as attributed (an advisory,
excluded from the isolation verdict). Anything else — including every
change on the adapter's own preset face — keeps failing the gate: the
isolation guarantee is not loosened (FEAT-040 invariant).
"""

from __future__ import annotations

import os
from pathlib import Path


def home_fingerprint(home: Path) -> dict:
    """Read-only metadata fingerprint of a DSH home (no file content read).

    Returns ``{"state": "absent"|"present", "entries": [kind:rel:size:mtime_ns]}``.
    Only ``lstat`` metadata is collected — file contents (e.g.
    ``credentials.yaml``) are never opened or printed.
    """
    if not home.exists():
        return {"state": "absent", "entries": []}
    entries = []
    for dirpath, dirnames, filenames in os.walk(home, followlinks=False):
        dirnames.sort()
        for name in sorted(dirnames) + sorted(filenames):
            path = Path(dirpath) / name
            try:
                stat = path.lstat()
            except OSError:  # pragma: no cover - transient/racy entry
                continue
            kind = "d" if (stat.st_mode & 0o170000) == 0o040000 else "f"
            entries.append(
                f"{kind}:{path.relative_to(home).as_posix()}:"
                f"{stat.st_size}:{stat.st_mtime_ns}"
            )
    return {"state": "present", "entries": entries}


def witness_deltas(before: dict, after: dict) -> dict:
    """Compare two witness samples → ``{"write_surface", "top_level"}`` deltas.

    The comparison式 is the one design §3.3 (row 11, D-54) fixes, and the two
    components are deliberately **not** symmetric:

    * ``write_surface`` — the adapter's ONLY write face, so a difference is a
      finding on the first comparison; no race is tolerated there.
    * ``top_level`` — only the **name set** is compared. A size/mtime change is
      not even visible here any more (the witness no longer records them), so
      host activity on ``settings.yaml`` cannot produce a delta at all.
    """
    return {
        "write_surface": [entry for entry in before["write_surface"]
                          if entry not in after["write_surface"]]
                         + [entry for entry in after["write_surface"]
                            if entry not in before["write_surface"]],
        "top_level": [name for name in before["top_level"]
                      if name not in after["top_level"]]
                     + [name for name in after["top_level"]
                        if name not in before["top_level"]],
    }


def entry_mtime_ns(entry: str):
    """The ``mtime_ns`` field of one write-surface entry string, or ``None``.

    Entries are ``kind:relpath:size:mtime_ns`` (:func:`home_fingerprint`);
    the mtime is the LAST colon-separated field, so a colon inside
    ``relpath`` cannot shift it. ``None`` — never a guess — when the field
    is absent or not an integer: the FIX-442 attribution judge treats an
    unprovable mtime as fail-closed (the entry stays a failure).
    """
    if ":" not in entry:
        return None
    field = entry.rsplit(":", 1)[1]
    try:
        return int(field)
    except ValueError:
        return None


def entry_relpath(entry: str):
    """The ``relpath`` field of one write-surface entry, or ``None``.

    ``kind`` is the first colon-separated field and ``size``/``mtime_ns``
    the last two, so ``relpath`` is whatever sits between — colons
    included — exactly as :func:`home_fingerprint` wrote it.
    """
    _kind, sep, rest = entry.partition(":")
    if not sep or rest.count(":") < 2:
        return None
    relpath = rest.rsplit(":", 2)[0]
    return relpath or None


def adapter_write_face_entry(entry: str, preset_id: str) -> bool:
    """True when a write-surface entry sits on THIS adapter's own write face.

    The only real-home paths this adapter's code can ever write are the
    preset directory it renders (``.agent-presets/<preset_id>/…``) and its
    staging sibling (``<preset_id>.staging-<pid>-<ms>`` — the
    atomic-replace name the launcher's install path builds). Everything
    else under ``.agent-presets`` — a sibling preset such as
    ``novel-writing``, its own staging dirs, any stray entry — belongs to
    an entry class this adapter has no write path for. An unparsable
    entry counts as the adapter's own face: attribution must fail closed,
    and "cannot prove it is foreign" is the fail-closed direction here
    (FIX-442).
    """
    relpath = entry_relpath(entry)
    if relpath is None:
        return True
    top = relpath.split("/", 1)[0]
    return top == preset_id or top.startswith(preset_id + ".staging-")


def attribute_concurrent_write(entry, *, samples, window,
                               preset_id=None) -> bool:
    """FIX-442 dual-factor attribution of ONE write-surface delta entry.

    ``True`` only when BOTH factors hold — a single-factor miss is a
    conservative non-attribution and the entry then keeps failing the
    isolation verdict (better a few conservative false FAILs than a missed
    escape; FEAT-040 safety semantics are not rolled back):

    * **Factor 1 — time window.** The change happened inside the smoke's
      before/after sampling interval. An entry that APPEARED carries its
      own evidence: its ``mtime_ns`` must fall within ``window`` (a write
      predating the interval belongs to the before-sample, so one that
      still shows up as new with an older mtime is a sampling race, not a
      concurrent write — conservative FAIL). An entry that DISAPPEARED
      cannot carry an mtime (the file is gone), but its removal is bounded
      by the samples themselves — present at ``before``, absent at
      ``after`` — so interval containment holds by construction, not by
      assumption.
    * **Factor 2 — entry semantics.** The entry does NOT sit on the
      adapter's own write face (:func:`adapter_write_face_entry`): an
      active session owns its preset ids (the ``novel-writing`` face of
      the 2026-09-13 / 2026-10-10 false positives), while the adapter's
      own preset face is the one it could write and is therefore never
      attributable away.

    ``window`` is ``(start_ns, end_ns)`` from ``time.time_ns``, taken
    around the two witness samples; ``None`` disables attribution outright
    (the caller is asserting samples without a window — exactly the
    pre-FIX-442 single-shot comparison, kept for every legacy caller).
    ``preset_id`` (the adapter's own preset id, from the host contract)
    is likewise required for attribution; ``None`` keeps the conservative
    legacy judgment.
    """
    if window is None or preset_id is None:
        return False
    start_ns, end_ns = window
    before, after = samples
    before_held = entry in before.get("write_surface", ())
    after_held = entry in after.get("write_surface", ())
    if after_held and not before_held:
        mtime_ns = entry_mtime_ns(entry)
        if mtime_ns is None or not start_ns <= mtime_ns <= end_ns:
            return False  # factor 1 unproven — conservative
    elif before_held and not after_held:
        pass  # removal: interval-bounded by the two samples (docstring)
    else:
        return False  # held by both or neither — not a delta this judge owns
    return not adapter_write_face_entry(entry, preset_id)


def witness_verdict(samples, *, resample=None, window=None,
                    preset_id=None) -> dict:
    """D-54 comparison + FIX-442 attribution:
    ``{"failures", "advisories", "verdict", "attributed_writes"}``.

    ``samples`` is ``(before, after_first)``. Design §3.3's sampling definition:
    a *suspected* top-level change (one seen in the first post-sample but not
    reproducing on a second) is a host race → **advisory, not FAIL**; the write
    surface has no such tolerance.

    ``resample`` — when given, it is called at most once to take the second
    post-sample **only if** a top-level delta was suspected (the sampling
    moment is "immediately after the first post-sample, interval 0"); the delta
    then has to reproduce for the gate to fail. **Without a resampler a
    top-level delta is a failure**: the caller is asserting a single sample, so
    there is nothing that could downgrade it to a race.

    Reproduced-ness is judged **against the baseline**, not against the first
    post-sample (N-5). Design §3.3 fixes both outcomes — "seen once = advisory,
    reproduced = FAIL" — and only the baseline comparison yields both: comparing
    the two post-samples would invert each (a persistent write would look like
    a one-shot race, and a one-shot race would look like a persistent write).
    The trade-off is deliberately the fail-closed side: a *different* top-level
    change present at the resample (not the same entry) still counts as
    reproduced, because "some top-level change survives a resample" is the
    signal this gate acts on. Marked here rather than left to be inferred.

    ``window`` — ``(start_ns, end_ns)`` bracketing the two samples — plus
    ``preset_id`` (the adapter's own preset id) together enable the FIX-442
    attribution: write-surface delta entries that pass the dual-factor
    judgment (:func:`attribute_concurrent_write` — changed inside the
    window AND off the adapter's own write face) are collected in
    ``attributed_writes`` and disclosed as ONE advisory instead of
    failing. A concurrent active session legitimately writing its own
    preset (measured 2026-09-13 and again 2026-10-10: a live session
    re-rendering the ``novel-writing`` preset) is not an isolation breach
    by this smoke. Everything else keeps the pre-FIX-442 semantics: the
    write surface has no race tolerance, and the adapter's own preset
    face can never be attributed away (isolation guarantee preserved —
    FEAT-040 invariant). ``window=None`` or ``preset_id=None`` (every
    legacy caller) disables attribution entirely.
    """
    before, after_first = samples
    deltas = witness_deltas(before, after_first)
    failures = []
    advisories = []
    attributed_writes = []
    if deltas["write_surface"]:
        # The adapter's own write face: never a race, always a real write.
        # FIX-442 splits the delta first: entries attributable to a
        # concurrent active session (dual factor) are disclosed, not
        # failed; the rest keep the zero-tolerance judgment.
        remaining = []
        for entry in deltas["write_surface"]:
            if attribute_concurrent_write(
                    entry, samples=samples, window=window,
                    preset_id=preset_id):
                attributed_writes.append(entry)
            else:
                remaining.append(entry)
        if remaining:
            failures.append(
                "real DSH home preset write surface changed: "
                + ", ".join(remaining))
        if attributed_writes:
            advisories.append(
                "real DSH home write-surface entries attributed to a "
                "concurrent active session (FIX-442 dual factor: changed "
                "inside the smoke window AND outside this adapter's own "
                "preset face) — excluded from the isolation verdict: "
                + ", ".join(attributed_writes))
    if deltas["top_level"]:
        reproduced = True
        if resample is not None:
            # "复现同样变化" = a top-level change is still present relative to the
            # BASELINE (not relative to the first post-sample): a real write
            # persists, a host race is gone by the second sample. See the
            # fail-closed note above (N-5).
            after_second = resample()
            reproduced = bool(witness_deltas(before, after_second)["top_level"])
        if reproduced:
            failures.append(
                "real DSH home top level changed: "
                + ", ".join(deltas["top_level"]))
        else:
            advisories.append(
                "real DSH home top level changed once and did not reproduce "
                "on resample (host activity, not an adapter write): "
                + ", ".join(deltas["top_level"]))
    return {
        "failures": failures,
        "advisories": advisories,
        "verdict": "FAIL" if failures else "PASS",
        "attributed_writes": attributed_writes,
    }
