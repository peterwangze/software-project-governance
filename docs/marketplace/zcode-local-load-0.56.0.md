# zcode Local Load Readiness - 0.56.0

> **⚠️ DEPRECATED in 0.62.0 (DEC-093, FIX-167).** The `project/zcode-local-load.py`
> tool this document describes has been removed. Newer zcode runtime versions ship
> a full marketplace chain (`addMarketplace` / `installMarketplacePlugin` /
> `clonePluginSource` / `known_marketplaces.json`) that accepts
> `{source:"github",repo:"owner/repo"}` sources, making the reverse-engineered
> seed-hash loader obsolete and a fragile coupling. Use the marketplace install
> procedure in [`zcode-marketplace-install.md`](./zcode-marketplace-install.md)
> instead. This file is retained as a historical record of the 0.56.0 mechanism
> and its honest limits; it is not an active install path.

Version target: 0.56.0

Related task: AUDIT-118

Related risk: RISK-036

## Purpose

This document records the verified facts about loading `software-project-governance` into a local zcode installation, and the honest limits of that path. It replaces any assumption that "a zcode marketplace submission" exists. The goal is conservative: a contributor who wants to run this plugin in zcode should be able to do so locally, and should understand exactly what is and is not claimed.

## Verified Facts About zcode Plugin Distribution

These facts were established by reading the zcode runtime bundle (`D:\app\zcode\resources\glm\zcode.cjs`), the zcode official plugin cache (`C:\Users\peter\.zcode\cli\plugins\`), and the zcode plugin documentation (`https://zcode.z.ai/cn/docs/plugin`).

| Fact | Evidence |
| --- | --- |
| zcode has no `/plugin install` or `marketplace add` command for third-party plugins. | The only plugin command is `/plugins [list \| enable <p> \| disable <p>]`. Searching the runtime for `addMarketplace`, `plugin marketplace`, `loadPlugin`, `registerPlugin` returns zero matches. |
| The official plugin set is hardcoded. | `Mue` is a fixed array of 6 plugins: `android-emulator`, `document-skills`, `ios-simulator`, `restore-legacy-sessions`, `skill-creator`, `superpowers`. The marketplace name is hardcoded as `zcode-plugins-official`. |
| There is no public submission channel to join `zcode-plugins-official`. | The "official" source label is defined as "智谱AI 官方开发并维护的插件". The only precedent for an external plugin entering the official set is `superpowers`, which is a Claude-Code-era community plugin that Zhipu vendored/repackaged via internal curation, not a public submission. |
| The zcode runtime has no third-party marketplace consumption path in the current version. | A runtime scan found the literal string `third-party` only 3 times, all as static labels. There is no `addMarketplace` / `customMarketplace` / `userMarketplace` handler. The documented "third-party / team-private marketplace" feature is not backed by runtime code in this version. |
| Third-party plugins can only load by emulating the seed output. | The runtime's `seedBundledOfficialPlugins` writes three artifacts per plugin: a cache dir, a `.zcode-plugin-seed.json`, and a `marketplace.json` entry. A third-party plugin must replicate all three manually. |

## What 0.56.0 Ships

| Artifact | Path | Role |
| --- | --- | --- |
| zcode plugin manifest | `.zcode-plugin/plugin.json` | Declares name/version/description/author/homepage/repository/license/skills/commands, matching the field set of official `superpowers`/`restore-legacy-sessions`/`skill-creator`. |
| npm package identity | `package.json` (root) | `@zcode/software-project-governance-plugin` scope, aligning with the `@zcode/<name>-plugin` convention used by official plugins. |
| Local load tool | `project/zcode-local-load.py` | One-shot developer tool that emulates the runtime seed output. Faithful port of the runtime `rdt`/`sCr` seed-hash algorithm (byte-level reproduction of official `skill-creator` seed hash verified). Provides `load`/`--verify`/`--reload`/`--unload`, idempotent with backups. |
| Brand assets | `.zcode-plugin/assets/{logo,composer-icon,governance-preview}.svg` | Placeholder brand assets matching the codex assets. |

## Local Load Procedure

```bash
# 1. Load the plugin into the local zcode cache + registry + config.
python project/zcode-local-load.py

# 2. Restart zcode, then confirm:
/plugins list            # software-project-governance should appear as enabled
/governance              # exercises the plugin; Coordinator activates

# 3. If the marketplace entry was dropped by a zcode restart (known limit), restore it:
python project/zcode-local-load.py --reload

# 4. Verify all four artifacts are present at any time (read-only):
python project/zcode-local-load.py --verify

# To remove the plugin from local zcode:
python project/zcode-local-load.py --unload
```

## Known Limits (Honest Disclosure)

1. **No official curation channel.** This plugin is not, and cannot currently become, part of `zcode-plugins-official`. The local load proves the plugin runs in zcode; it is not a submission, an approval, or an official listing.
2. **Marketplace entry may be overwritten on restart.** The runtime's `seedBundledOfficialPlugins` rewrites `marketplace.json` from its hardcoded official set on startup, dropping any third-party entry. The cache directory and seed file are not overwritten (the runtime only re-seeds plugins in its hardcoded list). Use `--reload` to restore the registry entry. This depends on the current zcode runtime behavior; a zcode upgrade may change the seed flow and require an updated loader.
3. **Runtime-verified on one machine.** EVD-610 confirms the plugin runs in one local zcode installation after restart. This is not universal/full runtime support.
4. **No zcode-native marketplace for self-distribution.** Because the runtime has no third-party marketplace consumption path in this version, this project does not ship a zcode third-party marketplace registry. Attempting one would produce an artifact the runtime cannot consume. The actionable self-distribution path for zcode users is the local load tool above.

## No-Overclaim Boundary

No zcode official approval. No zcode marketplace approval. No universal/full runtime support. No submission channel. No third-party marketplace listing in this version. The local load proves local runtime only.

RISK-036 remains open. RISK-037 remains open.
