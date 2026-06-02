# Submission checklist

Audience: official marketplace evaluators, release reviewers, and maintainers preparing Software Project Governance for 0.41.0 marketplace-readiness review.

This checklist is a pre-submission readiness aid. It does not submit the package, approve the package, or replace any marketplace-specific review process.

## Scope

| Item | Status for 0.41.0 readiness | Notes |
| --- | --- | --- |
| Product positioning | Ready for pre-submission review | README first screen presents the package as an AI coding delivery trust layer. |
| Metadata | Ready for pre-submission review | Codex and Claude manifests use conservative package metadata and avoid broad runtime claims. |
| Privacy/security | Ready for pre-submission review | Dedicated local data boundary and side-effect documentation is present. |
| Assets | Ready for pre-submission review | Tracked logo, composer icon, and governance preview SVG assets are referenced from plugin manifests. |
| Release | Ready for release review | REL-017 versions and packages the 0.41.0 readiness release without submitting it to a marketplace. |

## Manifests

- [x] `.codex-plugin/plugin.json` has package metadata suitable for review.
- [x] `.codex-plugin/plugin.json` includes skill/interface metadata without overstating runtime support.
- [x] `.claude-plugin/plugin.json` has homepage, repository, license, author, description, and keywords.
- [x] `.claude-plugin/marketplace.json` points to the current local plugin source and version.
- [x] Manifest descriptions do not claim official acceptance, every-runtime behavior, or listing approval.

## README first screen

- [x] README first viewport is in English for evaluator orientation.
- [x] README states the package category and value: AI coding delivery trust layer.
- [x] README gives install paths without implying every host has the same runtime behavior.
- [x] README includes a concise trust/data boundary summary.
- [x] README points new users to a short start path without hiding initialization requirements.

## Privacy/security doc

- [x] `docs/marketplace/privacy-security.md` exists.
- [x] It explains the `Local data boundary`.
- [x] It explains `Permissions and side effects`.
- [x] It explains `Runtime capability honesty`.
- [x] It states `No telemetry service`.
- [x] It states `No official acceptance claim`.
- [x] It avoids adding a privacy or terms link that has not been approved.

## Assets status

- [x] Marketplace logo/icon assets are tracked.
- [x] Screenshot or rendered preview assets are tracked.
- [x] Asset references in manifests point to existing files.
- [x] Assets are inspectable and do not imply official acceptance.
- [x] FIX-099 closed the visual asset gap for 0.41.0 readiness.

## Validation commands

Run these before submission review:

```powershell
powershell -NoProfile -Command "Select-String -Path docs/marketplace/privacy-security.md,docs/marketplace/submission-checklist-0.41.0.md -Pattern 'Local data boundary','Permissions and side effects','Runtime capability honesty','No telemetry service','Submission checklist','No official acceptance claim'"
```

```powershell
python skills/software-project-governance/infra/verify_workflow.py verify
python skills/software-project-governance/infra/verify_workflow.py check-version-consistency
python skills/software-project-governance/infra/verify_workflow.py check-cross-references
python skills/software-project-governance/infra/verify_workflow.py check-manifest-consistency
python skills/software-project-governance/infra/verify_workflow.py check-release --version 0.41.0 --require-changelog --runtime-adapters
python skills/software-project-governance/infra/verify_workflow.py check-governance --fail-on-issues
git diff --check
```

## E2E/degraded status

- [x] Runtime claims preserve pass, blocked, degraded, and environment-dependent distinctions.
- [x] Codex package assets are not described as one universal install behavior across every Codex environment.
- [x] Other-agent compatibility is not described as complete unless current runtime evidence proves it.
- [x] Degraded reviewer evidence is not counted as independent review approval.
- [x] Any blocked runtime path remains visible in release or readiness notes.

## Risk disclosures

- [x] RISK-036 official marketplace readiness risk remains visible; 0.41.0 readiness does not close the broader adoption risk.
- [x] Missing assets gap is closed for 0.41.0 by FIX-099 tracked SVG assets.
- [x] Legal privacy and terms links are not invented by documentation-only work.
- [x] Local command, git hook, git remote, package install, and host-agent side effects are disclosed as environment-dependent risks.

## No-overclaim checks

- [x] No claim of official marketplace acceptance.
- [x] No claim that every agent runtime is fully supported.
- [x] No claim that metadata or assets equal listing approval.
- [x] No claim that the repository provides a telemetry service or hosted compliance backend.
- [x] No claim that local governance records are a replacement for organization-specific security review.
- [x] No external policy URL is added unless separately approved.

## No official acceptance claim

This checklist is evidence of preparation, not acceptance. Official acceptance, listing, or approval can only come from the relevant marketplace review process.
