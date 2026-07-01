# zcode Marketplace Install - 0.62.0

Version target: 0.62.0

Related task: FIX-167

Related decision: DEC-093

Related risk: RISK-036

## Purpose

This document records how `software-project-governance` is installed into zcode through the zcode plugin marketplace, replacing the earlier 0.56.0 local-load mechanism (`project/zcode-local-load.py`, now removed). The goal is conservative: a contributor who wants to run this plugin in zcode uses the same marketplace protocol that zcode and Claude Code share, and should understand exactly what is and is not claimed.

## Why the Local-Load Mechanism Was Retired

The 0.56.0 local-load tool reverse-engineered the zcode runtime (`D:\app\zcode\resources\glm\zcode.cjs`) `rdt()`/`sCr()` seed-hash algorithm and manually planted four artifacts into the local zcode install to bypass `isSeedCurrent`. It existed because, at 0.56.0, the zcode runtime had no `/plugin install` or third-party marketplace consumption path.

Newer zcode runtime versions now ship a full marketplace chain. A runtime scan confirms the presence of `addMarketplace`, `installMarketplacePlugin`, `clonePluginSource`, `resolveGitPluginSource`, and `known_marketplaces.json`, and the source parser accepts `{source:"github",repo:"owner/repo"}` inputs. The reverse-engineered seed-hash loader is therefore obsolete and a fragile coupling (any runtime algorithm change would silently break it). DEC-093 retired it in favor of the native marketplace protocol.

## Verified Facts About zcode Plugin Distribution (0.62.0)

These facts were established by reading the zcode runtime bundle (`D:\app\zcode\resources\glm\zcode.cjs`) and the local zcode plugin state (`C:\Users\peter\.zcode\cli\plugins\`).

| Fact | Evidence |
| --- | --- |
| zcode runtime now resolves third-party marketplace sources. | The runtime exports `addMarketplace`, `installMarketplacePlugin`, `cloneMarketplaceSource`, `clonePluginSource`, `resolveGitPluginSource`, and reads `known_marketplaces.json`. |
| The source parser accepts `owner/repo` github inputs. | The source-input parser returns `{source:"github",repo:o}` when the input contains `/` and no `:`, matching the Claude Code marketplace convention. |
| zcode reuses the Claude marketplace protocol path constants. | Runtime constants point at `.claude-plugin/marketplace.json`, `.zcode-plugin/plugin.json`, `.claude-plugin/plugin.json`, and `.codex-plugin/plugin.json`. |
| The local official marketplace is operational. | `~/.zcode/cli/plugins/marketplaces/zcode-plugins-official/marketplace.json` is populated and `known_marketplaces.json` tracks added marketplaces. |

## What 0.62.0 Ships

| Artifact | Path | Role |
| --- | --- | --- |
| zcode plugin manifest | `.zcode-plugin/plugin.json` | Declares name/version/description/author/homepage/repository/license/skills/commands. |
| Claude/zcode marketplace registry | `.claude-plugin/marketplace.json` | Declares the marketplace (`name: spg`) and the plugin entry with `source: {source:"github", repo:"peterwangze/software-project-governance"}`. zcode and Claude Code both read this path. |
| npm package identity | `package.json` (root) | `@zcode/software-project-governance-plugin` scope. |
| Brand assets | `.zcode-plugin/assets/{logo,composer-icon,governance-preview}.svg` | Placeholder brand assets. |

## Marketplace Install Procedure

```bash
# 1. Add this repository as a plugin marketplace (zcode and Claude Code share the protocol).
/plugin marketplace add peterwangze/software-project-governance

# 2. Install the plugin from the marketplace.
/plugin install software-project-governance@spg

# 3. Restart the host if required, then confirm:
/plugins list            # software-project-governance should appear
/governance              # exercises the plugin; Coordinator activates
```

Alternative direct-from-git path (same protocol family):

```bash
/plugin install https://github.com/peterwangze/software-project-governance.git
```

## Migration From the 0.56.0 Local Load

If you previously used `project/zcode-local-load.py` to install the plugin into a local zcode:

1. Unload the old seed-based entry first to avoid a stale cache entry:
   ```bash
   # On a 0.61.x checkout, before upgrading:
   python project/zcode-local-load.py --unload
   ```
2. Update to 0.62.0 (the loader is removed in this version).
3. Install through the marketplace procedure above.

The cache directory and seed file planted by the old loader are not automatically cleaned by zcode (the runtime only re-seeds its hardcoded official set). The `--unload` step removes this plugin's entry only.

## Known Limits (Honest Disclosure)

1. **No official curation.** This plugin is not part of `zcode-plugins-official`. Marketplace install proves the plugin runs via the marketplace protocol; it is not a zcode official submission, approval, or curated listing.
2. **Protocol compatibility, not partnership.** zcode reuses the Claude marketplace protocol; this lets a standards-conforming repository be installed. It does not imply any zcode/Anthropic relationship or endorsement.
3. **Runtime-verified locally.** The marketplace protocol is present in the local zcode runtime; universal/full runtime support across all zcode versions/hosts is not claimed.
4. **Source is a public GitHub repository.** The `source` field points at `peterwangze/software-project-governance`. Private/fork deployments must adjust the source accordingly.

## No-Overclaim Boundary

No zcode official approval. No zcode curated marketplace listing. No universal/full runtime support. No zcode/Anthropic partnership. The marketplace install proves protocol-conformant installability, not official endorsement.

RISK-036 remains open. RISK-037 remains open.
