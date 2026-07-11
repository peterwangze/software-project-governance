# Marketplace Source Matrix - 0.65.3

**Audit date**: 2026-07-11  
**Task**: FIX-192 / SYSGAP-046 / RISK-041

This matrix separates repository packaging, locally observed protocol behavior, and external marketplace curation. A supported packaging path is not evidence of official listing, approval, endorsement, or universal runtime compatibility.

| Source path | Repository support | Verified boundary | Required evidence before stronger claim |
| --- | --- | --- | --- |
| Local marketplace add + install | `.claude-plugin/marketplace.json` declares `source: "./"`; after adding a local marketplace directory, install resolves the plugin from that marketplace root without a network clone | Protocol-conformant repository metadata and locally observed zcode marketplace commands; not an official listing | Repeatable runtime E2E on the named host/version plus captured command result |
| Offline zip/package | Repository can be cloned or packaged without relying on marketplace discovery; offline installation remains host-specific | Artifact availability does not prove the host imports or activates the plugin from an arbitrary zip | Host-specific offline install, activation, `/governance`, upgrade, and removal evidence |
| Remote marketplace | `/plugin marketplace add owner/repo` clones/adds the marketplace repository; install then resolves `source: "./"` inside that local clone. `repository` and `homepage` URLs are metadata, not plugin source declarations. | A cloneable marketplace repository is not zcode official marketplace approval or curated availability | Official submission result or independently captured marketplace listing/install evidence |
| Direct git URL | Not supported by the current 0.64.1+ contract. FIX-186 restored `source: "./"` for local/offline use and explicitly removed direct `/plugin install <git-url>` as a supported path. | Historical 0.62.0 documentation described this path, but it must not be presented as current or runtime-dependent support | A future governed contract change, implementation, and named-host E2E would be required before restoring this row to supported |

## No-Overclaim Boundary

No zcode official approval. No zcode curated marketplace listing. No zcode/Anthropic partnership or endorsement. No universal/full runtime support. Direct git URL installation is not supported by the current contract. RISK-041 remains open until the wider release-lineage closure criteria are met.
