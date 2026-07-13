# Errata — prdl-24394_sermones-et-exhortationes-ad-monachos-joa

## 2026-07-10 — fixed stray abbr-definition rubric (chunk 62)

A marginal rubric in chunk 62 was formatted `*[unclear]: nor does the delay of repentance [bring] security.*`, which the markdown `extra` extension read as an abbreviation definition — stamping 332 identical wrong `[unclear]` tooltips across the reader page. Reformatted to `*[unclear] — ...*` (no colon).

## 2026-07-10 — collapsed x7 stutter duplication (chunk 139; audit fix)

The 'Sixth, be constant in holy prayers...' paragraph in chunk 0139 was OCR-stutter-scanned 7 times (segment 139, latin-ocr.txt lines 6718-6724 degrading into run-together tokens) and rendered 7 times. Replaced chunk 0139 with the clean parallel rendering from prdl-24393 chunk 0142 (same source text, single clean copy), and collapsed the duplicate region in english.md. (Audit finding M1.)
