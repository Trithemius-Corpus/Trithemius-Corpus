# Errata — prdl-24374_de-vanitate-et-miseria-humanae-vitae

## 2026-07-10 — removed fabricated 'Dutch schout' hallucination (chunk 2 / segment 2)

The entire second segment was a degenerate OCR-model hallucination: a fabricated 1568 Dutch legal document about an Amsterdam 'schout' (bailiff), burgomasters, and debts — anachronistic for a 1495 Mainz incunable by an author who died in 1516, and decaying into a pseudo-German repetition loop on the Latin side. It was the OCR model confabulating an expansion of a flyleaf inscription; the translator rendered the hallucination faithfully, producing a 6 KB loop with no genuine Trithemius content.

- `latin-ocr.txt` segment 2: the pseudo-German loop removed; segment marker retained.
- `chunks/full_chunk_0002.md`: replaced with a removal marker.
- `english.md`: the loop paragraphs removed; the work now flows from the title/folio (chunk 1) directly to the genuine opening (chunk 3, "*Book on the vanity and misery of human life...*").
- `chunks/grades.csv`: chunk 2 row annotated (the prior faith=5.0 grade scored the hallucinated text).

Segment count and all chunk boundaries unchanged. (This work also has a double-translation defect in chunks 21/22 and a missing segment 21 — tracked separately under W2.)

## 2026-07-10 — fixed double-translated chunk 21/22 and missing segment 21

The pipeline translated Latin segment 22 (the death/penance discourse beginning "acriore seuit inuidia") twice — once as chunk 21 and once as chunk 22 — while segment 21 (the catechetical dialogue on the watchful servant: the three vigils of life, the wise and foolish virgins) was never translated. Chunk 22's cleaner rendering of segment 22 is retained as the canonical translation; the duplicate (chunk 21) was removed from `english.md`, and chunk 21 is now an honest missing-translation placeholder documenting the untranslated segment 21. Re-translation of segment 21 is tracked for v1.1. Segment count and chunk boundaries unchanged.
