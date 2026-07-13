# Errata — prdl-24373_de-statu-et-ruina-monastici-ordinis

## 2026-07-10 — removed OCR-LLM loop and pseudo-Greek gibberish (latin-ocr.txt only)

Two localized removals from `latin-ocr.txt`, neither affecting the English (both matching English chunks are clean translations):
- Segment 28: an OCR-LLM hallucination loop that degenerates into English dictionary words ("Vobiscum detesting, vobiscum executing... decrease... frequency"); the genuine passage ending "...Quid ergo morā facitis?" is retained.
- Segment 32: a stray "L" and ~4.3 KB of incoherent pseudo-Greek/Byzantine-script gibberish ("Παρὰ τοῦ Πετρίου...") after the genuine 1493 Hirsau chapter colophon ("...vt patet in statutis.").

Segment count and all chunk boundaries unchanged.

## 2026-07-10 — collapsed 'And thus it seems' permutation loop (chunk 30 + english.md)

Chunk 30 ended with ~13 near-identical permutations of one broken sentence about visitors/ministers of visitation ("And thus it seems that when anyone ought to be a minister of visitation of our order..."), an OCR-model degeneration loop. The genuine passage on ignorant/vicious visitors is retained up to its natural close ("...in public, accusers: [unclear]"); the permutations were removed from both the chunk and `english.md`. Segment count and chunk boundaries unchanged.
