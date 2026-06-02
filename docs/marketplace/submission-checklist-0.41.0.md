# Submission checklist

Audience: official marketplace evaluators, release reviewers, and maintainers preparing Software Project Governance for 0.41.0 marketplace-readiness review.

This checklist is a pre-submission readiness aid. It does not submit the package, approve the package, or replace any marketplace-specific review process.

## Scope

| Item | Status for 0.41.0 readiness | Notes |
| --- | --- | --- |
| Product positioning | In progress | README first screen presents the package as an AI coding delivery trust layer. |
| Metadata | In progress | Codex and Claude manifests use conservative package metadata and avoid broad runtime claims. |
| Privacy/security | In progress | Dedicated local data boundary and side-effect documentation is now present. |
| Assets | Pending | Logo, icon, screenshots, and visual previews are planned for FIX-099. |
| Release | Pending | REL-017 should version and release the full 0.41.0 package after review. |

## Manifests

- [ ] `.codex-plugin/plugin.json` has package metadata suitable for review.
- [ ] `.codex-plugin/plugin.json` includes skill/interface metadata without overstating runtime support.
- [ ] `.claude-plugin/plugin.json` has homepage, repository, license, author, description, and keywords.
- [ ] `.claude-plugin/marketplace.json` points to the current local plugin source and version.
- [ ] Manifest descriptions do not claim official acceptance, every-runtime behavior, or listing approval.

## README first screen

- [ ] README first viewport is in English for evaluator orientation.
- [ ] README states the package category and value: AI coding delivery trust layer.
- [ ] README gives install paths without implying every host has the same runtime behavior.
- [ ] README includes a concise trust/data boundary summary.
- [ ] README points new users to a short start path without hiding initialization requirements.

## Privacy/security doc

- [ ] `docs/marketplace/privacy-security.md` exists.
- [ ] It explains the `Local data boundary`.
- [ ] It explains `Permissions and side effects`.
- [ ] It explains `Runtime capability honesty`.
- [ ] It states `No telemetry service`.
- [ ] It states `No official acceptance claim`.
- [ ] It avoids adding a privacy or terms link that has not been approved.

## Assets status

- [ ] Marketplace logo/icon assets are tracked.
- [ ] Screenshot or rendered preview assets are tracked.
- [ ] Asset references in manifests point to existing files.
- [ ] Assets are inspectable and do not imply official acceptance.
- [ ] Current known gap: visual assets are not complete before FIX-099.

## Validation commands

Run these before submission review:

```powershell
powershell -NoProfile -Command "Select-String -Path docs/marketplace/privacy-security.md,docs/marketplace/submission-checklist-0.41.0.md -Pattern 'Local data boundary','Permissions and side effects','Runtime capability honesty','No telemetry service','Submission checklist','No official acceptance claim'"
```

```powershell
python skills/software-project-governance/infra/verify_workflow.py verify
python skills/software-project-governance/infra/verify_workflow.py check-cross-references
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
git diff --check -- docs/marketplace/privacy-security.md docs/marketplace/submission-checklist-0.41.0.md
```

## E2E/degraded status

- [ ] Runtime claims preserve pass, blocked, degraded, and environment-dependent distinctions.
- [ ] Codex package assets are not described as one universal install behavior across every Codex environment.
- [ ] Other-agent compatibility is not described as complete unless current runtime evidence proves it.
- [ ] Degraded reviewer evidence is not counted as independent review approval.
- [ ] Any blocked runtime path remains visible in release or readiness notes.

## Risk disclosures

- [ ] RISK-036 official marketplace readiness risk remains visible until 0.41.0 readiness is closed by review and release evidence.
- [ ] Missing assets remain disclosed until FIX-099 closes them.
- [ ] Legal privacy and terms links are not invented by documentation-only work.
- [ ] Local command, git hook, git remote, package install, and host-agent side effects are disclosed as environment-dependent risks.

## No-overclaim checks

- [ ] No claim of official marketplace acceptance.
- [ ] No claim that every agent runtime is fully supported.
- [ ] No claim that metadata or assets equal listing approval.
- [ ] No claim that the repository provides a telemetry service or hosted compliance backend.
- [ ] No claim that local governance records are a replacement for organization-specific security review.
- [ ] No external policy URL is added unless separately approved.

## No official acceptance claim

This checklist is evidence of preparation, not acceptance. Official acceptance, listing, or approval can only come from the relevant marketplace review process.
