# FIX-445 Design Review R8

- Round: 8. Delta scope. DEC-339. Ledger max7+1.
- Prev: review-FIX-445-DESIGN-R7.md, explicit read this round, 66 lines.
- Binding: docs/design/FIX-445-source-verification-R8.md. Parent SHA binding authoritative. 5012 bytes. 72 lines.
- Reviewer: same Design Reviewer instance, R0 to R7. Read only. Sole write: this report.
- No shell, no hash, no probe this round. Parent binds hash. Counterexamples are spec reasoning, not product probes.
- Scope: F2 delta only. F1, F3, B2, B3 and all prior closed faces carried.

Verdict:

{"verdict": "APPROVED_WITH_NOTES", "round": 8, "unresolved_blockers": 0}

## 1. R7-A closure

The suffix path now requires full closed-predicate consumption. Only two forms pass.

- D form: suffix equals "shi bu ke qu" optionally plus "de". Reads as: is-inadmissible.
- T form: five slots, all consumed, no residue. Slots: strong negation, then mention verb, then approval noun, then safety noun, then tail noun.

Prefix runs first. Suffix only after prefix fails. Bad only after both fail. No early bad.

Suffix exempts only the match itself. No ex write. No inheritance. Old prefix containment inheritance kept.

Window: from match end to nearest terminator. Raw length pre-check, at most 16, then trim. Longer raw rejects. Question mark rejects. Control chars reject. Stacked negation rejects. Affirmative tail rejects. Quotes are not boundaries.

R7-A counterexample set now all reject:

- "wei jing fu he" rejects: not D start, not T start.
- "bing wei kua da" rejects.
- "shi ... wei jing ... de" rejects: after shi comes wei, not bu ke.
- "bu neng fu he" rejects: slot mismatch.
- " bu neng'->'->'->' stop."
- Nested second operator in suffix rejects.
- Raw length 17 rejects. Question mark rejects.

Legit denials pass:

- D: object frame, with or without.
- T core sentence of 1587.
- Variant slot combinations.
- Full sentence with comma tail clean.

Polarity holds. Both are denials of the frame itself. No unrelated predicated path inside. Closed full consumption leaves no room.

Endpoint: match end. Unique now.

## 2. Three sentences

- 1587: sole frame bare suffix T full, after comma clean.
- 1536: F1 as R7.
- 1588: F3 as R7.

Legacy: "bu ba ... dangzuo" passes via original prefix and containment. Two D matches pass independently. No ex reuse. Prior attack faces carried, no new surface.

## 3. Independent probes

- Polarity: all R7-A forms reject. Only true denials pass.
- Mixed tech denial plus real endorsement in later clause: suffix stops at comma, later frame triggers.
- No fixture whitewash: token level closed tables, no EVD id, no sentence hardcode, no field-wide exemption, no old row edit.
- Ten code point fact checked, five by two.
- Pre-check then trim order verified, seventeen rejects.
- No early bad: current hook lines 804 to 806 set bad early. Implementation must reorder per spec step 3. Noted.

## 4. Gates

Alternatives at least two, with rejection reasons. Challenge at least three. No cycle. Independent review is this report. Zero unresolved.

## 5. Notes

- N1: source text of R8 design is compressed in style. Implementer must use the Coordinator bound canonical text only. First draft preserved in incidents for provenance.
- N2: D variants, with and without optional tail, plus adjacent near-miss forms, need red tests both ways.
- N3: T slot combinations need coverage both directions, assert code point count.
- N4: suffix writes no ex, contained prefix only, hook early bad reorder.
- N: bounded by design, not measured. Design pass is not product pass. Code chain later.

## 6. Read faces

R8 72 lines. R7 report 66. R7 design 76 from last round. Hook and test sections from last round. No shell.

## 7. Record

Parent records round 8 result per ledger. File name of this report is the canonical one ending in Dashes. After send no append. Supplement separate.

Note by coordinator: an earlier draft write under a wrong name occurred and was superseded by this file; quarantine as needed.
