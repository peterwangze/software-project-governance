#!/usr/bin/env python3
"""zcode local plugin loader for software-project-governance.

This is a one-shot developer tool (not a product artifact). It emulates the
zcode official-plugin seed output so a locally developed plugin can be loaded
into the local zcode installation for verification.

How zcode loads plugins (verified facts from the runtime bundle
D:\\app\\zcode\\resources\\glm\\zcode.cjs):
  1. There is NO `/plugin install` or `marketplace add` command for third-party
     plugins. `/plugins` only supports `list | enable <p> | disable <p>` and
     only affects the hardcoded official set.
  2. At startup, seedBundledOfficialPlugins resolves a fixed plugin list and
     writes three artifacts: a cache dir, a `.zcode-plugin-seed.json`, and a
     marketplace registry entry; enable state lives in config.json.
  3. isSeedCurrent skips re-seeding only if the existing seed's `hash` and
     `pluginVersion` match a freshly computed value. If the hash is wrong the
     runtime OVERWRITES our cache from its official source, undoing our load.

So to load a third-party plugin we must place all four artifacts ourselves and
compute the seed hash with the exact algorithm the runtime expects.

Seed hash algorithm (hashSeedFiles / sCr, byte-level verified against
superpowers 5.1.0 and skill-creator 0.1.0):
  - Walk the plugin root; skip dirs named node_modules, .turgo, coverage.
  - Only include files whose FIRST path segment is in ALLOWED_TOP:
        .mcp.json, .zcode-plugin, README.md, commands, dist, hooks,
        output-styles, package.json, skills, templates
    (.zcode-plugin-seed.json itself is NOT in the allow-list, so it never
    participates in its own hash.)
  - For each included file build a triple [posixRelPath, sha256(bytes), mode].
    mode = 493 (0o755) when:
        - the real stat mode sets any group/other bit (statMode & 0o111 != 0), or
        - path matches 'dist/mcp/server.js' (anchored, any case), or
        - path starts with 'hooks/' and does NOT end with .json/.md/.txt.
      otherwise mode = 420 (0o644).
  - Sort triples by posix path (localeCompare) and hash
    sha256(JSON.stringify(triples)) as hex.

Note: the algorithm is a faithful port of the runtime rdt()/sCr(). The on-disk
mode used for the exec-bit branch reflects THIS machine's stat, which on
Windows does not preserve Unix exec bits. That is fine for this plugin (it
ships no executable scripts), but it means the hash computed here will not, in
general, equal the hash an official Unix-built seed carries for plugins that do
ship executables. zcode does not re-seed plugins outside its hardcoded official
set, so a self-consistent seed is sufficient for a third-party local load.

Usage:
    python project/zcode-local-load.py            # load (idempotent)
    python project/zcode-local-load.py --unload   # remove this plugin only
    python project/zcode-local-load.py --dry-run  # print plan, write nothing

The script backs up marketplace.json and config.json before editing and only
touches the entry for this plugin.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PLUGIN_NAME = "software-project-governance"
PLUGIN_VERSION = "0.55.3"
MARKETPLACE = "zcode-plugins-official"

REPO_ROOT = Path(__file__).resolve().parent.parent

# Where the local zcode install keeps plugin state.
ZCODE_HOME = Path(os.environ.get("ZCODE_HOME", str(Path.home() / ".zcode")))
PLUGINS_ROOT = ZCODE_HOME / "cli" / "plugins"
CACHE_ROOT = PLUGINS_ROOT / "cache" / MARKETPLACE
MARKETPLACE_JSON = PLUGINS_ROOT / "marketplaces" / MARKETPLACE / "marketplace.json"
CONFIG_JSON = ZCODE_HOME / "cli" / "config.json"

PLUGIN_CACHE_DIR = CACHE_ROOT / PLUGIN_NAME / PLUGIN_VERSION

# Top-level repo subtrees that zcode cares about and that should be copied.
# Matches the runtime ALLOWED_TOP set, restricted to what this repo ships.
COPY_TOPS = [
    ".zcode-plugin",
    "commands",
    "skills",
    "README.md",
    "package.json",
]

# Repo-internal / dev / governance dirs that must NEVER be copied into a
# distributable plugin cache (they are not plugin surface and some are huge).
EXCLUDE_TOPS = {
    ".git",
    ".github",
    ".governance",
    ".pytest_cache",
    "adapters",
    "agents",
    "docs",
    "project",
    "tests",
    "web",
}

# Exact ALLOWED_TOP set from the runtime. Files whose first path segment is
# not in this set are excluded from the seed hash.
ALLOWED_TOP = {
    ".mcp.json",
    ".zcode-plugin",
    "README.md",
    "commands",
    "dist",
    "hooks",
    "output-styles",
    "package.json",
    "skills",
    "templates",
}

# Directories skipped during the seed walk (runtime: shouldSkipDirectory).
SKIP_DIRS = {"node_modules", ".turbo", "coverage"}


# ---------------------------------------------------------------------------
# Seed hash (runtime algorithm port)
# ---------------------------------------------------------------------------

# Runtime rdt(): /(?:^|\/)dist\/mcp\/server\.js$/i  — anchored, case-insensitive.
_DIST_SERVER_JS = re.compile(r"(?:^|/)dist/mcp/server\.js$", re.IGNORECASE)


def _posix(rel: Path) -> str:
    return rel.as_posix()


def _mode_for(rel_posix: str, stat_mode: int) -> int:
    """Compute the Unix permission number the runtime assigns (rdt).

    Runtime: function rdt(e,t){if(t!==void 0&&(t&73)!==0)return 493; ...}
    73 == 0o111. The hooks/ and dist/mcp/server.js branches are fallbacks for
    when the on-disk mode carries no exec bits (e.g. on Windows).
    """
    if stat_mode & 0o111:
        return 493
    if _DIST_SERVER_JS.search(rel_posix):
        return 493
    if rel_posix.startswith("hooks/") and not rel_posix.endswith((".json", ".md", ".txt")):
        return 493
    return 420


def compute_seed_hash(plugin_root: Path) -> str:
    """Compute the zcode plugin seed hash for *plugin_root*.

    Walks the tree, keeps only ALLOWED_TOP first-segment files, builds sorted
    [path, sha256(content), mode] triples, and returns sha256(JSON.stringify).
    """
    triples = []
    for dirpath, dirnames, filenames in os.walk(plugin_root):
        # Prune skipped directories in-place.
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            full = Path(dirpath) / fname
            try:
                rel = full.relative_to(plugin_root)
            except ValueError:
                continue
            rel_posix = _posix(rel)
            first_seg = rel_posix.split("/", 1)[0]
            if first_seg not in ALLOWED_TOP:
                continue
            data = full.read_bytes()
            st = full.stat()
            triples.append([rel_posix, hashlib.sha256(data).hexdigest(), _mode_for(rel_posix, st.st_mode)])
    triples.sort(key=lambda t: t[0])
    payload = json.dumps(triples, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_seed_marker(seed_hash: str) -> dict:
    return {
        "hash": seed_hash,
        "marketplace": MARKETPLACE,
        "plugin": PLUGIN_NAME,
        "pluginVersion": PLUGIN_VERSION,
        "source": "filesystem",
        "version": 1,
    }


# ---------------------------------------------------------------------------
# Copy plugin surface into cache
# ---------------------------------------------------------------------------

def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name in EXCLUDE_TOPS or name == "__pycache__"


def copy_plugin_surface(repo_root: Path, dest: Path) -> list[str]:
    """Copy only the plugin-surface subtrees into *dest*.

    Returns the list of relative (posix) paths that were copied, for logging.
    """
    copied = []
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    for top in COPY_TOPS:
        src = repo_root / top
        if not src.exists():
            continue
        if src.is_file():
            shutil.copy2(src, dest / top)
            copied.append(_posix(Path(top)))
        else:
            for dirpath, dirnames, filenames in os.walk(src):
                dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
                for fname in filenames:
                    s = Path(dirpath) / fname
                    rel = s.relative_to(repo_root)
                    d = dest / rel
                    d.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(s, d)
                    copied.append(_posix(rel))
    return copied


# ---------------------------------------------------------------------------
# Registry + config edits
# ---------------------------------------------------------------------------

def _backup(path: Path) -> Path:
    bak = path.with_suffix(path.suffix + ".bak-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(path, bak)
    return bak


def update_marketplace(cached: dict) -> tuple[bool, list[str]]:
    """Add this plugin's entry to the marketplace registry (idempotent).

    Returns (changed, actions).
    """
    actions = []
    entry = {
        "cachePath": str(PLUGIN_CACHE_DIR),
        "name": PLUGIN_NAME,
        "source": "filesystem",
        "version": PLUGIN_VERSION,
    }
    plugins = cached.setdefault("plugins", [])
    existing = [p for p in plugins if p.get("name") == PLUGIN_NAME]
    if existing:
        if existing[0] == entry:
            return False, actions
        plugins[plugins.index(existing[0])] = entry
        actions.append(f"updated marketplace entry for {PLUGIN_NAME}")
        return True, actions
    # Keep alphabetical order to match the official registry style.
    plugins.append(entry)
    plugins.sort(key=lambda p: p.get("name", ""))
    actions.append(f"added marketplace entry for {PLUGIN_NAME}")
    return True, actions


def update_config(cached: dict) -> tuple[bool, list[str]]:
    """Enable this plugin in config.json (idempotent)."""
    actions = []
    plugins = cached.setdefault("plugins", {})
    enabled = plugins.setdefault("enabledPlugins", {})
    key = f"{PLUGIN_NAME}@{MARKETPLACE}"
    if enabled.get(key) is True:
        return False, actions
    enabled[key] = True
    actions.append(f"enabled {key} in config.json")
    return True, actions


def remove_from_marketplace(cached: dict) -> tuple[bool, list[str]]:
    actions = []
    plugins = cached.get("plugins", [])
    before = len(plugins)
    plugins[:] = [p for p in plugins if p.get("name") != PLUGIN_NAME]
    if len(plugins) != before:
        actions.append(f"removed marketplace entry for {PLUGIN_NAME}")
        return True, actions
    return False, actions


def remove_from_config(cached: dict) -> tuple[bool, list[str]]:
    actions = []
    plugins = cached.get("plugins", {})
    enabled = plugins.get("enabledPlugins", {})
    key = f"{PLUGIN_NAME}@{MARKETPLACE}"
    if key in enabled:
        del enabled[key]
        actions.append(f"disabled {key} in config.json")
        return True, actions
    return False, actions


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def cmd_load(dry_run: bool) -> int:
    steps = []
    # 1. verify plugin manifest exists
    manifest = REPO_ROOT / ".zcode-plugin" / "plugin.json"
    if not manifest.exists():
        print(f"[FAIL] missing {manifest}", file=sys.stderr)
        return 2
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    if manifest_data.get("name") != PLUGIN_NAME or manifest_data.get("version") != PLUGIN_VERSION:
        print(
            f"[FAIL] manifest name/version mismatch: "
            f"got {manifest_data.get('name')} {manifest_data.get('version')}",
            file=sys.stderr,
        )
        return 2

    # 2. copy surface
    steps.append(f"copy plugin surface -> {PLUGIN_CACHE_DIR}")
    # 3. compute hash over the populated cache (hash reflects shipped bytes)
    # 4. write seed marker
    steps.append("write .zcode-plugin-seed.json")
    # 5. update marketplace.json
    steps.append(f"register in {MARKETPLACE_JSON}")
    # 6. enable in config.json
    steps.append(f"enable in {CONFIG_JSON}")

    print("== zcode local load plan ==")
    for s in steps:
        print(f"  - {s}")

    if dry_run:
        print("\n[dry-run] no files written.")
        return 0

    print("\n== executing ==")
    copied = copy_plugin_surface(REPO_ROOT, PLUGIN_CACHE_DIR)
    print(f"  copied {len(copied)} file(s) into cache")

    seed_hash = compute_seed_hash(PLUGIN_CACHE_DIR)
    marker = build_seed_marker(seed_hash)
    seed_path = PLUGIN_CACHE_DIR / ".zcode-plugin-seed.json"
    seed_path.write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    print(f"  seed hash = {seed_hash}")
    print(f"  wrote {seed_path}")

    bak = _backup(MARKETPLACE_JSON)
    mp = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    changed, acts = update_marketplace(mp)
    MARKETPLACE_JSON.write_text(json.dumps(mp, indent=2) + "\n", encoding="utf-8")
    print(f"  marketplace.json backed up -> {bak.name}")
    for a in acts:
        print(f"    {a}")

    bak2 = _backup(CONFIG_JSON)
    cfg = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
    changed2, acts2 = update_config(cfg)
    CONFIG_JSON.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"  config.json backed up -> {bak2.name}")
    for a in acts2:
        print(f"    {a}")

    print("\n== done ==")
    print("Restart zcode and run `/plugins list` to confirm the plugin is enabled.")
    print("Call `/governance` or the `software-project-governance` skill to load it.")
    return 0


def cmd_unload(dry_run: bool) -> int:
    print("== zcode local unload plan ==")
    print(f"  - remove cache dir {PLUGIN_CACHE_DIR}")
    print(f"  - remove marketplace entry for {PLUGIN_NAME}")
    print(f"  - disable {PLUGIN_NAME}@{MARKETPLACE} in config.json")
    if dry_run:
        print("\n[dry-run] no files written.")
        return 0

    if PLUGIN_CACHE_DIR.exists():
        shutil.rmtree(PLUGIN_CACHE_DIR)
        print(f"  removed {PLUGIN_CACHE_DIR}")

    bak = _backup(MARKETPLACE_JSON)
    mp = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    _, acts = remove_from_marketplace(mp)
    MARKETPLACE_JSON.write_text(json.dumps(mp, indent=2) + "\n", encoding="utf-8")
    print(f"  marketplace.json backed up -> {bak.name}")
    for a in acts:
        print(f"    {a}")

    bak2 = _backup(CONFIG_JSON)
    cfg = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
    _, acts2 = remove_from_config(cfg)
    CONFIG_JSON.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"  config.json backed up -> {bak2.name}")
    for a in acts2:
        print(f"    {a}")

    print("\n== unloaded ==")
    return 0


def cmd_verify() -> int:
    """Check that all four load artifacts survive (e.g. after a zcode restart).

    zcode rewrites marketplace.json from its hardcoded official plugin set on
    startup, so a third-party entry can be dropped. This command reports which
    of the four artifacts are present without writing anything.
    """
    print("== zcode local load verification ==")
    ok = True

    cache_ok = PLUGIN_CACHE_DIR.is_dir() and (PLUGIN_CACHE_DIR / ".zcode-plugin" / "plugin.json").exists()
    print(f"  [{'OK' if cache_ok else 'MISSING'}] cache dir + plugin.json: {PLUGIN_CACHE_DIR}")
    ok = ok and cache_ok

    seed_path = PLUGIN_CACHE_DIR / ".zcode-plugin-seed.json"
    seed_ok = False
    if seed_path.exists():
        marker = json.loads(seed_path.read_text(encoding="utf-8"))
        recomputed = compute_seed_hash(PLUGIN_CACHE_DIR)
        seed_ok = marker.get("hash") == recomputed and marker.get("plugin") == PLUGIN_NAME
        status = "OK (hash matches cache)" if seed_ok else f"STALE (seed={marker.get('hash')[:12]}.. cache={recomputed[:12]}..)"
    else:
        status = "MISSING"
    print(f"  [{status}] seed marker: {seed_path}")
    ok = ok and seed_ok

    mp_ok = False
    if MARKETPLACE_JSON.exists():
        mp = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
        entry = [p for p in mp.get("plugins", []) if p.get("name") == PLUGIN_NAME]
        mp_ok = bool(entry)
        note = "present" if mp_ok else "ABSENT (likely rewritten by zcode restart)"
    else:
        note = "marketplace.json MISSING"
    print(f"  [{'OK' if mp_ok else 'ABSENT'}] marketplace entry: {note}")
    ok = ok and mp_ok

    cfg_ok = False
    if CONFIG_JSON.exists():
        cfg = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
        key = f"{PLUGIN_NAME}@{MARKETPLACE}"
        cfg_ok = cfg.get("plugins", {}).get("enabledPlugins", {}).get(key) is True
    print(f"  [{'OK' if cfg_ok else 'OFF'}] enabled in config.json")
    ok = ok and cfg_ok

    print()
    if ok:
        print("== ALL ARTIFACTS PRESENT ==")
        return 0
    print("== INCOMPLETE — run `--reload` to re-register after a zcode restart ==")
    return 1


def cmd_reload() -> int:
    """Re-inject marketplace + config entries and refresh the cache.

    Use after a zcode restart drops the marketplace entry (zcode rewrites it
    from its hardcoded official set). Recopies the cache surface, recomputes
    the seed, and re-adds the marketplace/config entries idempotently.
    """
    print("== reloading software-project-governance into local zcode ==")
    copied = copy_plugin_surface(REPO_ROOT, PLUGIN_CACHE_DIR)
    print(f"  refreshed cache ({len(copied)} file(s))")
    seed_hash = compute_seed_hash(PLUGIN_CACHE_DIR)
    marker = build_seed_marker(seed_hash)
    (PLUGIN_CACHE_DIR / ".zcode-plugin-seed.json").write_text(
        json.dumps(marker, indent=2) + "\n", encoding="utf-8"
    )
    print(f"  seed hash = {seed_hash}")

    bak = _backup(MARKETPLACE_JSON)
    mp = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    _, acts = update_marketplace(mp)
    MARKETPLACE_JSON.write_text(json.dumps(mp, indent=2) + "\n", encoding="utf-8")
    print(f"  marketplace.json backed up -> {bak.name}")
    for a in acts or ["marketplace entry already present"]:
        print(f"    {a}")

    bak2 = _backup(CONFIG_JSON)
    cfg = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
    _, acts2 = update_config(cfg)
    CONFIG_JSON.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    print(f"  config.json backed up -> {bak2.name}")
    for a in acts2 or ["config entry already enabled"]:
        print(f"    {a}")

    print("\n== reload complete ==")
    print("Restart zcode and run `/plugins list` to confirm the plugin is enabled.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Load software-project-governance into local zcode.")
    p.add_argument("--unload", action="store_true", help="Remove this plugin from local zcode.")
    p.add_argument("--verify", action="store_true", help="Check whether the load artifacts survive (read-only).")
    p.add_argument("--reload", action="store_true", help="Re-inject marketplace/config + refresh cache (use after a zcode restart).")
    p.add_argument("--dry-run", action="store_true", help="Print the plan only; write nothing.")
    args = p.parse_args(argv)
    if args.unload:
        return cmd_unload(args.dry_run)
    if args.verify:
        return cmd_verify()
    if args.reload:
        return cmd_reload()
    return cmd_load(args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
