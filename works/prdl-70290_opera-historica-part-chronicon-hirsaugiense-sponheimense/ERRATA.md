# Errata

> **2026-06-10 — full re-translation against the re-OCR'd Latin.** This work
> was re-translated from scratch (GPT-5.5 on the re-OCR'd text), re-chunked to
> the canonical `latin-ocr.txt` segmentation so the side-by-side viewer aligns
> 1:1 (see LIMITATIONS §10). This **supersedes the chunk-level facsimile
> revisions recorded below**, whose corrections are carried by the cleaner
> re-OCR and the fresh translation. The revision history is kept for provenance;
> the superseded English is retained in version control.
> The re-translated chunks were independently re-graded against the Latin
> (GPT-5.5, OCR-referenced): final tier **B** (faithful 3.95, hall 16.7%; faithfulness is A-level but hallucination sits just over the 15% threshold).

---

# Errata — prdl-70290

## 2026-06-10 — targeted chunk re-translation (Fable 5 revision pass, B-tier catalogue campaign)

### full_chunk_0017
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The graded rendering invented "on the ninth day" (a misplacement of "anno Lintberti abbatis nono", his ninth YEAR), corrupted "sancti Aurelii Hirsaugiensis" into "first abbot of Saint-Amand", and trailed off mid-sentence. The currently public revision still drops the ninth-year phrase, Hildegrin's ~34-year tenure, and the entire final Leo IV entry (which the print breaks at the page boundary), and leaves "pater filium" (father/son) and "Brunvvart abbas Hirsfeldensis" as [unclear]/guesses.

**Key corrections (verified against the scan):**
- Altfrid entry: print reads 'Fuit autem electus in episcopum anno Lintberti abbatis nono, qui fuit Dominicae incarnationis 847. indictione decima' - restored 'in the ninth year of Abbot Lintbert' (graded text had fabricated 'built the greater church on the ninth day'; current public dropped the phrase). Also restored 'maiorem ecclesiam praefatae vrbis' (greater church of the aforesaid city).
- Synod list: print reads 'Lintbertus primus iste abbas sancti Aurelii Hirsaugiensis' - 'this first abbot of Saint Aurelius of Hirsau' (graded text: 'Saint-Amand').
- Synod list: 'Brunvvart abbas Hirsfeldensis' - Brunwart abbot of Hersfeld (public had 'abbot of [unclear]'); 'Bertolphus abbas Mediolacensis' - Bertolph, not 'Bartolph'.
- Famine entry: print reads 'vt pater filium inedia mortuum, ad ignem coctum manducare voluerit, si per vicinos casu non fuisset interceptus' - a father would have eaten his son, dead of starvation; replaces public's '[unclear]... cooked [corpse/child]'.
- Haymo obit: 'vir per omnia Deo dilectus' - 'in all things beloved of God' (public invented 'perfect in every virtue'); 'in maiori ecclesia Haluerstatensi'; and 'Cui sanctus Hildegrinus in episcopatu successit annis fere 34' - the ~34 years public dropped.
- Aethelwulf entry: 'tributariam fecit provinciam suam... nummus solveretur argenteus' - made his province tributary; a SILVER penny (public: 'instituted a tributary coin', silver dropped).
- Final entry restored: 'Floruit etiam hoc tempore Leo Papa quartus... presbyter cardinalis tituli Sanctorum quatuor corona-' with catchword 'torum' at the page foot; rendered up to the boundary with the break noted (public dropped this entry wholesale).
- Year headings verified as DCCCLI and DCCCLIII on the print (segment OCR has erroneous DCCCCLI/DCCCCLIII); Ansgar 'vir doctus' rendered 'learned' (public: 'excellent'); Bremen bishops as printed: Wilhardus, Willericus, Ludericus.

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'multam fa-|me perdurante': the line-end 'fa-' is distorted by page curvature; reading 'fame perdurante' (while the famine lasted) is near-certain from the following line but flagged.
- Print reads 'Hecti archiepiscopus Treuerensis' (ct-ligature clear); rendered 'Hetti' with print form noted in brackets.
- 'Anno enim decimotertio' (famine entry) - 'enim' as read; the entry sits under the DCCCXLIX heading although it names Lintbert's thirteenth year.
- 'Corbeiensis' is ambiguous between Corvey and Corbie; rendered Corvey (Altfrid) and Corbie (Ansgar) by convention, flagged in the translator's note.
- First line spelling of Hildesheim ('Hildenshemensis'/'Hildeshemensis') uncertain at available resolution; identification as Hildesheim is secure.

**Note:** Printed marginal sidenotes on this page fall outside the translated text span and were not rendered (consistent with neighboring chunks).

### full_chunk_0236
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The old translation fabricated its opening sentence ("Whenever [unclear] was to be freed, he hastened to help") from OCR garbage where the print actually continues mid-word ("[monaste]rij sui defensor acerrimus"), added phrases not in the print ("to go unpunished", "cut down and"), misplaced the 1218 flood in Phrygia instead of Frisia, flattened "regina ciuitatum" (queen of cities) to "the royal city", and hid the mid-word page-break ending under a false full stop. It also dropped the running head, all eleven marginal rubrics, and the catchword, and carried OCR-mangled names (Luvanus; "count of [unclear] of Dune").

**Key corrections (verified against the scan):**
- Opening restored as mid-word continuation: print reads "[monaste]rij sui defensor acerrimus" (preceding page ends "...rerum & bonorum monaste-"), with margin rubric "Libertatum fuit acerrimus defensor"; the published "Whenever [unclear] was to be freed, he hastened to help" was invented from the OCR conflation "Liberatum fuit accurrimus".
- Print reads "violatio-nem" (hyphenated across lines), not OCR's "violatorem": "never allowed any violation of the same to be sustained"; the old "any violator of them to go unpunished" added unsupported words.
- Year headers in print are MCCXVII, MCCXVIII, MCCXIX, MCCXX (1217-1220), matching the in-text Arabic years; the latin-ocr witness's MCCCXVII-MCCCXX (1317-1320) is wrong. Rendered with both Roman and modern forms.
- "mare terminos suos in Phrysia transiens" - the flood is in Frisia, not "Phrygia" as published (verified at ultra-zoom).
- 1219: print reads "regina ciuitatũ Hierosolyma" (tilde verified at maximum zoom) - "Jerusalem, the queen of cities", not "the royal city".
- Crusade entry: "cum Iuuano monasterij mei abbate sexto" - initial letterform identical to the I of "Ioannes" on the same line; published "Luvanus" copied the OCR's lowercase "luvano".
- 1220: "Conradum comitem Syluestrẽ de Dune" with margin "Conradus comes Syluestris" - Conrad the forest-count (Wildgrave) of Dhaun; published had "count of [unclear] of Dune".
- 1220: print reads "pluribus ex eis in-terfectis" ("many of them killed"); published "cut down and slain" rendered the OCR corruption "excisae. terrefectis", adding content.
- Page ends mid-word "comes centum ar-" with catchword "genti"; rendered up to the boundary with an honest bracketed catchword note (continuation "genti marcis a capitulo Moguntino susceptis..." verified at top of page image 183). The published version ended with a fabricated complete sentence.
- Restored running head (printed page 174), all eleven marginal rubrics (Lupoldus; Andreas Vngariae rex; Concursus principum ad terram sanctam; Damiata capitur a Christianis; Diluuium centum millium hominum submersio; Hierusalem a Saracenis subuertitur; Fridericus Imperator coronatur a papa; Dux Lotharingiae; Fridericus Imperator Apulia potitur; Conradus comes Syluestris), and modern equivalents for the feast dates (vigil of St. Bartholomew = 23 August; feast of B. Cecilia = 22 November).
- Minor: "in manu sacerdotis" (singular, "in the priest's hand"); "cum maximo apparatu" (OCR dropped "ap-").

**Surviving cruxes (flagged in the chunk's translator's note):**
- "Iuuano" (rendered Iuvanus): the print reading is secure at letterform level, but the nominative form and the identity of this sixth abbot of "my monastery" (Sponheim) are editorial.
- "de Dune" = Dhaun and "comes Syluestris" = Wildgrave are bracketed editorial identifications, as are Wied, Oettingen, Saarbrücken, Neuhausen.
- 1217 entry verb after "de Saraponte" is worn (succedit/successit); translation unaffected.
- Chunk boundary falls mid-word "ar-|genti" at the page foot (catchword "genti"); the sentence is completed in full_chunk_0237.
- Routine abbreviation expansions from the print: q̃ = quod, ciuitatũ = ciuitatum, Syluestrẽ = Syluestrem; margin rubric "Diluuium cẽtum millium hominũ submersio" read from small italic at zoom.

**Note:** No passage of the print remains illegible at available resolution.

### full_chunk_0442
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The published translation of full_chunk_0442 does not correspond to segment 442's Latin at all: it renders 1454–55 annal material (Teutonic Order, Dracula, Eberhardsklausen) and ends with a Duke Ludwig passage that is nowhere on this page. The actual span is the Chronicon Sponheimense entries for 1363–1367 (printed p. 329): Boemund of Trier's resignation to Cuno of Falkenstein, the Cologne succession (Wilhelm, Virneburg, Adolf, Engelbert), the Speyer and Worms successions, the 1365 winter/pestilence and Kreuznach sedition, the 1366 Worms dispute, and Boemund's death.

**Key corrections (verified against the scan):**
- Replaced the mismatched 1454-55 content with a full translation of the actual span, every entry verified line-by-line against the scan: Boemund resigns Trier to Cuno of Falkenstein and retires to Saarburg castle; death of Archbishop Wilhelm of Cologne and 10-month vacancy; Urban V quashes Johannes de Virnenburg's election and elevates Adolf of the Mark (ruled badly 10 months 18 days); 1363 deaths of Gerlacus de Ernberg of Speyer (succeeded by Lampertus de Burne, 18 years, later translated to Bamberg) and Theodericus de Bopardia of Worms (succeeded by Johannes Schatlandt OP, almost 13 years); 1364 Adolf's resignation, marriage, and gain of Cleves, Engelbert of the Mark postulated (4 years); 1365 frozen Rhine, famine, pestilence, Kreuznach sedition with four ringleaders beheaded by the count's order; 1366 Worms bishop-citizens dispute composed by Rupert (also called Adolf), count palatine, and the councils of Mainz and Speyer on the Conversion of St. Paul; kings of France and Scotland led captive to England; 1367 death of Boemund on St. Scholastica's day
- Year heads corrected from the OCR witness's MCCCCLXIII-MCCCCLXVII to the print's MCCCLXIII-MCCCLXVII (1363-1367), verified in ultra-zoom crops
- OCR errors corrected from the print: perpetuavit->perpetrauit, liber-ter->libenter, Papa v.i.->Innocent VI, cauuit->cassauit, fulcepit->suscepit, effecerit->esset, iucellit->successit, Babergensem->Bambergensem, aliando->aliquando, 'Constantiensi in Suecia'->Sueuia (Constance in Swabia, not Sweden), desaeuient->desaeuiens
- Proper names re-read from the scan: Gerlacus de Ernberg, Lampertus de Burne, Theodericus de Bopardia, Iohannes Schatlandt (margin: Schadland), Iohannes de Virnenburg, Creutzenacht
- Ten printed marginal notes (omitted by the OCR witness and the old translation) read from the scan and translated inline, e.g. 'Cuno fit archiepiscopus Treuirensis', 'Hyems asperrima. Pestilentia magna', 'Reges capti in Angliam ducuntur'
- Mid-sentence chunk boundaries rendered honestly: opens '...who, triumphing most gloriously' (subject Cuno of Falkenstein carried over from the previous page) and ends 'after whom Cuno of' at the page break, with signature mark Ee 3 and continuation noted

**Surviving cruxes (flagged in the chunk's translator's note):**
- Signature mark read as 'Ee 3'; the second letterform could be read 'Ec'
- 'a certain maiden [daughter] of the count of Berg' — the print has 'puellae comitis Montensis' without stating the relationship; '[daughter]' is supplied
- Main text spells 'Schatlandt', the marginal note 'Schadland'; both given as printed
- Modern feast-day equivalents (Holy Innocents = 28 Dec, Conversion of St. Paul = 25 Jan, St. Scholastica = 10 Feb) and bracketed identifications (Virneburg, Lamprecht of Brunn, Dietrich of Boppard) are editorial

**Note:** This span is printed page 329 (running head 'SPONHEIMENSE. 329', signature Ee 3 at the foot). Printed marginal line-numbers (10-50) were not rendered.

### full_chunk_0636
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The published chunk did not correspond to segment 636 at all: it rendered material from other letters (a 1506 letter about Nuremberg printers, the escape-from-Sponheim letter, and the entire 1503 Frankfurt assembly passage with Cardinal Raymond), none of which appears in this Latin span. The actual content — the end of letter XXXI to Roger Sycamber (Speyer, 12 August 1505) on the journey toward the March of Brandenburg and the Count of Leiningen's burning of Limburg Abbey, plus the heading and salutation of letter XXXII — was dropped wholesale.

**Key corrections (verified against the scan):**
- Restored the whole letter ending from the print: left Cologne 4 August; entered Neometis [Speyer] after vespers on the vigil of St. Lawrence [9 August]; the Margrave left Cologne 30 July via Westphalia and Saxony (scan p. 477 = printed p. 469)
- Restored the Limburg suit: the abbot of Limburg and Master Jacob Trithemius left in Cologne; Count of Leiningen's agents burned the Limburg monastery; Jacob, Archbishop of Mainz, obtained as royal commissary to attempt an amicable concord, else remit the affair to the king with the acts
- Read 'tepuit' from the scan (OCR witnesses gave 'repuit'/'Iepuit'); 'exiuimus' (OCR 'exuimus'); 'potuisset & contempsit' (OCR 'potuifler et contemptis')
- Canon citations read from the print: 'XXIII. quaestione VIII. cap. Pessimam' and 'XII. quaestione II. Cum devotissimam, & cap. sequenti' (segment OCR had garbled the numerals)
- Confirmed 'testibusque si qui fuerint producti examinatis' and 'conscium se incendii saevissimi negat, sed mentitur plane, quoniam apertis convincetur testimoniis' (OCR 'continuetur')
- Restored 'homo nullius hominis memoria dignus' (segment OCR dropped 'homo') and 'remittet' (OCR 'remitteret'/'remitter')
- Letter number confirmed as XXXII from the scan (page OCR read 'XXXI.'); addressee read from the italic salutation as 'Ioanni Nutio' (OCR gave 'Natio' and 'Xutio')
- Place-name read as 'Neometim/Neometi' in all three occurrences (not 'Nemetim'), with Speyer given as an editorial identification only
- Dating line confirmed: 'Vale ex Neometi 12. die Augusti anno 1505'

**Surviving cruxes (flagged in the chunk's translator's note):**
- Print reads 'totum ad regem negotiorum cum actis remittet' — 'negotiorum' verified by ultra-zoom where the sense wants 'negotium'; translated as 'the whole affair' and flagged
- 'Neometis' = Speyer is an editorial identification (civitas Nemetum; fits the itinerary and the Limburg/Leiningen context); the print form itself is 'Neometim/Neometi'
- 'emprestes' (sacrilegious fire-raiser) is a Greek loanword (emprestes) as printed, not an OCR error
- Addressee 'Ioanni Nutio' is as printed; the bearer is otherwise unidentified

### full_chunk_0721
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The published full_chunk_0721.md did not correspond to Latin segment 721 at all: it rendered alphabetical-index entries (S–T) whose Latin sits in segments 803–804 (scan pp. 613–614), translated from badly garbled pre-re-OCR text. The grader's "fehan uenberg" defect belongs to that misaligned index span (pre-OCR garble of "ſchauenberg" = Schauenberg, verified in the pre-re-OCR source text and against latin-ocr segment 803). Segment 721's actual Latin — the close of Trithemius's letter of 10 April 1507 on the decay of Bursfelde-union observance, and the opening of Letter XXII to Theodoric, bishop of Lübeck, on Apollonius of Tyana — was previously untranslated under this chunk number.

**Key corrections (verified against the scan):**
- Replaced the misaligned index translation with a translation of segment 721's real span: scan p. 542 (printed p. 534, running head EPISTOLAE FAMILIARES), verified line by line against zoom crops.
- Chunk joins verified on the scans: opens mid-word completing 'resti-/tuat' (catchword + signature 'Yy 3' at foot of scan 541) and ends at catchword 'scriptis' (continuation 'scriptis quanquam ementitis' at head of scan 543, segment 723; segment 722 is empty in latin-ocr.txt).
- Letter XXII heading re-read from print: 'D. THEODORICO Ecclesiae Lubecensis Episcopo ... felicitatem orat sempi-/ternam' — OCR's 'felicitatem orat semper' corrected to 'everlasting felicity' (sempiternam, hyphenated across lines).
- Print readings recovered where OCR was damaged: 'aequa lance discusseris' (OCR 'aequalis lance discutueris'), 'tuisque nolle obedire mandatis' (OCR 'tuuque nolle obedere'), 'In obliuionem ... deducti sunt' (OCR 'In obliniaem ... deduerti'), 'nemo qui corrigat' (OCR 'corrigit'), 'manducare carnes' (OCR 'carnem'), 'patres aliquando capitulariter' (OCR 'aliando'), 'sine iniuria cuiuscunque melius sentientis' (OCR 'sine inuiriae ... sentiaetis').
- '& vt videmus aperte' checked at ultra-zoom and confirmed (present tense, as OCR).
- Printed marginal gloss 'Apollonius Tyaneus quando vixerit' recovered from the left margin and rendered in place; right-margin numerals 10-50 identified as printed line numbers, not text.

**Surviving cruxes (flagged in the chunk's translator's note):**
- Heading reads 'Ecclesiae Lubecensis Episcopo' (Lübeck) — followed as printed, with no editorial identification of the addressee beyond the print.
- Final sentence is cut mid-clause at the chunk boundary (catchword 'scriptis'); rendered up to the boundary only.
- Printed page number on scan 542 read as '534'; the following recto also prints '534' — a numbering oddity of the edition, outside this span.

## 2026-06-10 — codex (GPT-5.5) facsimile grading of the re-translation pass

All 5 re-translated chunks were graded by GPT-5.5 against the **page images**
(Latin read from the scan, not the OCR). Result: **faithful min 4, mean 4.8/5;
fluent 5; 0 flagged `hallucinated`** (`0017` f5, `0236` f5, `0442` f5, `0636`
f5, `0721` f4).

## 2026-06-19 — [unclear] resolution passes (multi-pronged)

Three passes reduced [unclear] markers across this work:

1. **Historical fact-checking** (12 fixes corpus-wide): proper nouns identifiable from Trithemius biography — "Abbot of [unclear]" → "St. James's Abbey, Würzburg", "Wimpfeling of [unclear]" → "Schlettstadt", "surnamed [unclear]" → "Magnus" (Charlemagne), "unwilling [unclear]" → "pupil" (Maximilian).

2. **False-positive removal** (7 fixes, prdl-70280): column-separator `[unclear]` markers in the ANNOTATIO SCRIPTORVM index were layout-parsing artifacts, not damaged words — removed.

3. **Mid-word line-break joining** (168 fixes corpus-wide): the vision OCR model inserted `[unclear]` at Fraktur line-break hyphenation points (e.g. `pri[unclear]mi` → `primi`). These were joined automatically by matching word fragments on either side of the marker.

**Total corpus-wide reduction: 35,577 → ~11,000 [unclear] markers (69% reduction).**

The remaining ~11,000 are genuinely damaged text where no model or method could recover the word. They are marked honestly.

## 2026-07-09 — digitization-artifact cleanup (latin-ocr.txt)

- Removed a degenerate OCR repetition loop ('sio' repeated ~407 times) from [segment 160] of latin-ocr.txt. The paired English chunk is the blank-page marker; the loop was an OCR artifact, not page text.

## 2026-07-10 — fixed stray abbr-definition rubric (chunk 180)

A chapter rubric in chunk 180 was formatted `*[unclear]: the emperor holds court at Cologne. Abbot Volmar dies.*`. The markdown `extra` extension treats a `*[word]: caption` line as an abbreviation definition, so this one stray line caused every later `[unclear]` in the work to render as `<abbr title="the emperor holds court...">unclear</abbr>` — 2,760 identical wrong tooltips on the reader page. Reformatted the rubric to `*[unclear] — ...*` (no colon) so it no longer defines an abbreviation. (`build_site.py` now also defensively unwraps any such stray abbr.)

## 2026-07-10 — removed OCR double-scan duplicates (88 segment pairs; audit fix)

The OCR pipeline double-scanned page ranges of this work, producing 88 byte-identical segment pairs in `latin-ocr.txt` (~51,000 duplicated words, ~22% of the work). Each duplicate segment was independently translated and shipped, so the reading text contained the same passages twice (two different renderings of the identical Latin). Suppressed the duplicate member of each pair: its chunk file now carries a cross-reference removal marker pointing to the retained copy, and `english.md` was rebuilt from the deduplicated chunks. Chunk numbering is unchanged (so the parallel viewer still aligns each segment with its Latin); only the duplicated English content is removed. No genuine content was lost — each suppressed passage is retained verbatim at its first occurrence. (Deep-audit finding H1.)

## 2026-07-10 — residual double-scan dedup (near-identical pass)

The 2026-07-10 double-scan deduplication keyed on byte-identical Latin segments; 9 additional duplicate pairs whose two scans differ only by minor OCR variance (similarity >= 95%) were caught in a follow-up similarity sweep and suppressed with the same convention (duplicate chunk replaced by a cross-reference marker; english.md re-stitched; chunk numbering unchanged): 96->kept 94 (sim 97%); 204->kept 200 (sim 98%); 427->kept 419 (sim 100%); 507->kept 499 (sim 100%); 611->kept 603 (sim 98%); 632->kept 622 (sim 100%); 634->kept 624 (sim 99%); 718->kept 708 (sim 98%); 725->kept 715 (sim 100%). Borderline partial-overlap pairs below 95% similarity were left in place pending eyes-on review (see corpus report).

## 2026-07-10 — borderline double-scan pairs resolved (eyes-on review)

The partial-overlap double-scan pairs deferred by the earlier passes were compared side by side (Latin diff + English chunks); in each pair one capture contains everything real in the other, so the lesser member was suppressed with the standard cross-reference marker and english.md re-stitched:
- Suppressed chunk 0043 in favor of 0042: segment 43 = segment 42 plus OCR damage-gap tags only; 42 is the cleaner capture.
- Suppressed chunk 0284 in favor of 0288: segment 288 is the fuller capture (adds the De Wighardo chapter opening); 284 is the partial scan.
- Suppressed chunk 0635 in favor of 0644: segment 644 is the fuller capture (adds the Missurus capellanum letter opening); 635 is the partial scan.
- Suppressed chunk 0699 in favor of 0690: no unique content on either side; earlier capture retained.
