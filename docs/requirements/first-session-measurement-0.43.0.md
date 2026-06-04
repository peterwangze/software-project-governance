# First-Session Measurement Evidence 0.43.0

Date: 2026-06-04
Task: FIX-107
Requirement: REQ-090
Risk: RISK-036
Version target: 0.43.0

## Purpose

This artifact separates local first-run demo proof from external first-session measurement.

The local demo can prove that the Delivery Trust Snapshot exists and is assertable. It does not prove that external users completed the first session within five minutes.

## Measurement Status

| Signal | Status | Evidence scope | Current result | Boundary |
| --- | --- | --- | --- | --- |
| local_demo | PASS | LOCAL_DEMO_ONLY | `python skills/software-project-governance/infra/verify_workflow.py first-run-demo --assert-snapshot` passes locally and asserts Delivery Trust Snapshot fields. | Local demo-only proof; no external user success claim. |
| external_pilot | NOT_MEASURED | EXTERNAL_PILOT_REQUIRED | 0/5 external pilot users measured for 0.43.0 at this time. Target remains 4/5 users completing setup or resume and naming one trust signal within 5 minutes. | Do not convert local demo PASS into external pilot PASS. |
| release_note_boundary | PASS | TEXT_GUARD | 0.43.0 release notes must publish local_demo=PASS and external_pilot=NOT_MEASURED unless timed pilot evidence is added before release. | No official approval. No marketplace approval. No universal/full runtime support. RISK-036 remains open. |

## Stopwatch Template

Use this table when an external pilot is actually run. Leave rows empty until the run exists.

| Participant | Date | Agent host | Setup or resume path | Time to Delivery Trust Snapshot | Trust signal named | Result | Evidence location |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TO_BE_MEASURED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_MEASURED | NOT_RUN |

## Completion Rule

External pilot status may change from NOT_MEASURED to PASS only when at least 4/5 external pilot users complete setup or resume, reach the Delivery Trust Snapshot within five minutes, and name one concrete trust signal. Local demo output, reviewer approval, governance evidence, commit logs, or release checklist prose are not external pilot evidence.

External pilot status may change from NOT_MEASURED to BLOCKED when a timed pilot is attempted and a concrete blocker prevents measurement. The blocker must be recorded in the Measurement Status table and in release evidence.

## 0.43.0 Release Note Boundary

For 0.43.0, publish the measured state as:

- local_demo: PASS
- external_pilot: NOT_MEASURED
- first-session claim: local/demo proof only
- no-overclaim boundary: No official approval, no marketplace approval, no universal/full runtime support, and RISK-036 remains open.
