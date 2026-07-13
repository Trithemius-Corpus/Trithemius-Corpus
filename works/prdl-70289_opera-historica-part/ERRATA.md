# Errata

> **2026-06-10 — full re-translation against the re-OCR'd Latin.** This work
> was re-translated from scratch (GPT-5.5 on the re-OCR'd text), re-chunked to
> the canonical `latin-ocr.txt` segmentation so the side-by-side viewer aligns
> 1:1 (see LIMITATIONS §10). This **supersedes the chunk-level facsimile
> revisions recorded below**, whose corrections are carried by the cleaner
> re-OCR and the fresh translation. The revision history is kept for provenance;
> the superseded English is retained in version control.
> The re-translated chunks were independently re-graded against the Latin
> (GPT-5.5, OCR-referenced): final tier **A** (faithful 3.97, hall 14.4%, up from B).

---

# Errata — prdl-70289

## 2026-06-10 — targeted chunk re-translation (Fable 5 revision pass)

### full_chunk_0084
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The old rendering smoothed OCR damage into confident prose: "Richard" for the print's Richaredus (Reccared), "perhaps slain" for "miserabili sorte peremptus" (OCR long-s read as "forte"), "as is related" for "(sicut iusserat)", and "acquaintances" for "cognatos" (kinsmen); it also silently completed the final sentence whose verb stands on the page only as the catchword, and dropped the running head. The grader's specific charge — an added St. Remi monastery — is NOT present in the current public chunk file and has no basis in the print (only Monte Cassino appears); that part of the grade note appears misassigned or to refer to a superseded version.

**Key corrections (verified against the scan):**
- 'Richaredus' (Reccared), king of the Visigoths — read clearly on the scan (sub-strips s1b/s1c); old translation printed 'Richard'
- 'miserabili sorte peremptus' ('cut off by a miserable lot') — ultra-zoom shows long-s matching the ſ glyphs in 'miſerabili', and grammar excludes 'forte'; old rendering 'perhaps slain' followed the OCR's 'forte'
- '(sicut iusserat)' = 'as he had ordered' — verified on scan (s3c); old rendering 'as is related' followed OCR garble 'sic ut seruat'
- 'apud cognatos suos' = 'among his kinsmen' — verified (s4b/s4c); old rendering 'among his acquaintances'
- Final sentence ends mid-clause at the page boundary: 'interijt.' at the foot of page 48 is the catchword (page 49 begins 'interijt, anno regni sui nonodecimo'); rendered up to the boundary with the catchword bracketed, per house convention
- Restored running head 'COMPENDIVM LIB. I.' and printed page number 48, omitted before
- 'itinere toto' ('along the whole route') restored in the pursuit sentence — omitted by the old translation
- Year of Theodoric's death printed CCCCCCXVIII (six C's) = 618, indiction 6 — verified on ultra-zoom; the latin-ocr witness shows only five C's
- 'fratrueli Hildeberto' rendered 'nephew' with Latin tag (Trithemius himself makes Hildebert son of Gunthram's brother Sigebert); old rendering 'cousin'
- Verified intact against the scan: indiction XV and regnal year XXXIII for Gunthram; Columbanus died 21 November; war of 605, indiction 8, Lothar's 18th year; 30,000 fighters; Genebald the Third; Main and Würzburg (print 'Menum & Wirciburg'); Upper Alemannia 'now called Helvetia'

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'legatione testantis' (Gunthram's bequest to Hildebert) — print reading verified on ultra-zoom but grammatically odd; rendered by sense as 'by testamentary bequest' with the Latin bracketed
- Sixteen printed marginal glosses run down the inner margin; they fall outside the chunk's OCR span and are not translated (per the convention established in full_chunk_0102); several are partly lost in gutter shadow
- Catchword 'interijt.' (with period) vs next-page 'interijt,' (with comma) — normal compositor variation, noted in the bracketed catchword line

### full_chunk_0086
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The grader's note was misattributed: "monasterium Dologiense" sits in segment 94 (latin-ocr.txt line 2479), and neither the Latin nor the old English of chunk 86 mentions any monastery. The old translation's real defects, verified against the scan, were hallucinated name normalizations in the genealogy ("King Pharamund" for print "Pharaberti", "Duke Meroncus" for "Merouei", "Cligio"/"Clodonin" for "Clogionis"), omission of the link "qui fuit sancti Arnulphi", "enlarged" for "erexit" (erected) of Frankfurt, and silent omission of the running head and all ten printed marginal notes.

**Key corrections (verified against the scan):**
- 'Qui fuit Pharaberti regis' read clearly on the scan: rendered 'King Pharabert', replacing the old version's invented 'King Pharamund'
- 'Qui fuit Merouei ducis' read on the scan: 'Duke Meroveus', replacing 'Duke Meroncus' (OCR artifact 'Meronci')
- 'Qui fuit Clogionis regis' appears twice in the print: both rendered 'King Clogio', replacing 'Cligio' and the invented 'Clodonin'
- Restored 'qui fuit sancti Arnulphi' (Pippin's grandfather link through Saint Arnulf), dropped by the OCR witness and the old translation; confirmed on the scan
- 'qui Franckenfurt villam iuxta Moenum erexit': 'erected the town of Franckenfurt', replacing the unsupported 'enlarged'
- Restored the running head 'ANNAL. TRITHEMII. 49' and all ten printed marginal notes (Lotharius monarch, Brunichildis slain, Guarnerius/Harpo/Rado appointments, Genebald duke of Mainz, Marcopolis=Wirciburg, Palatine-Bavaria union, Sigebert in Alemannia, Lombard tribute, Wernher dies, Pippin mayor, Charlemagne descent line), all read from margin ultra-zooms
- Peoples list confirmed as 'Mosellani, Lucenburgij, Austrasij, Euphalij, Namercij' on the scan (OCR's 'Austrasiae...Namerci' garbled)
- 'monarcha totius regni Francorum euasit' confirmed (OCR had 'equalis'); 'Eudolina', 'Tarauanos', 'florenorum auri', 'comitem siue praefectum', 'Rauricos', and 'decem & octo' (eighteen) all confirmed at ultra-zoom
- Honest boundary handling added: opening mid-sentence continuation and the page-final dangling 'Qui' are now marked instead of smoothed away

**Surviving cruxes (flagged in the chunk's translator's note):**
- Print reads 'Oodomari regis' (double O) where Odomar is expected; rendered 'Odomar [print: Oodomari]'
- Print reads 'Namercij' for the people of Namur; rendered 'Namur [print: Namercij]'
- Margin spelling of Wuerzburg uncertain between 'Wirciburg' and 'Wirceburg' (main text blackletter reads 'Wirtzburg')
- '[son] of Clovis' supplied in 'ex Blidehilde filia Lotharij regis primi Clodouei natus'
- Margin note 'Guarnerius maior domus': italic 'maior' resembles 'mater' at available resolution; read as 'maior' from parallel notes and main text

### full_chunk_0102
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The old rendering opened with "[unclear] he had seized dignities" where the print is fully legible: the verb is "contu-|lerit" split across the chunk boundary (previous segment ends "militibus suis Ecclesiasticas contu-"), i.e. Charles Martel CONFERRED ecclesiastical dignities on his soldiers, not "seized" them; it also dropped "visus sit" (he "was seen" after death buried in hell — the vision motif), rendered the Greek "Τέλος." as "Title." (OCR "Titul."), and omitted the running head and catchword. The grader-flagged "Cifrhena" appears nowhere in this segment's print or the current public file.

**Key corrections (verified against the scan):**
- Page mapping off-by-one: chunk is on page image 93 (printed page 62), not 94; page 94 begins the next work (De origine gentis Francorum compendium).
- Opening crux resolved from scan: '...lerit dignitates, Ecclesiasque spoliauerit' completes 'contu-lerit' (seg. 101 ends 'Ecclesiasticas contu-'); rendered 'confer]red [ecclesiastical] dignities [upon his soldiers], and despoiled churches' replacing the old '[unclear] he had seized dignities and despoiled the Church'.
- Restored 'visus sit': print reads 'ob ea visus sit scelera post mortem in inferno sepultus' — 'was seen after death buried in hell', not flatly 'was buried in hell'.
- OCR 'Titul.' / old 'Title.' is actually Greek 'Τέλος.' in the print (verified on zoom), rendered as such with gloss.
- All numerals verified on scan and consistent: DCCXLVI (746)/5th regnal year/14th indiction; DCC.XLVIII (748)/7th year/1st indiction; DCC.XLIX (749)/2nd indiction/9th regnal year; Burghard presided 'annis XL' (40); 'mille centum nonaginta' (1,190 years); 'vnus & sexaginta' (61 kings); Grifo held captive 'annis quatuor'; Pippin sole rule 'annis sex'; colophon 'vicesima die mensis Nouembris ... millesimo quingentesimo quartodecimo' (20 Nov 1514), 52nd year of his age.
- Name forms verified against print: Tecla (not Thecla), Buchouia (Buchonia glossed), Mogonum (the Main), Hirsfeldia (Hersfeld), Bischoffsheim, Thubera (Tauber), Laudunum (Laon), Hildericus (Childeric III glossed), Carlomannus, Doringos (Thuringians), Kyliani/Kiliani.
- OCR damage corrected from scan: 'per faenum Bonifacium' is 'per sanctum Bonifacium'; 'vioem recepit' is 'visum recepit' (received his sight); 'rapta forore' is 'rapta sorore' (carried off Pippin's sister); 'luit exordium' is 'sumit exordium'.
- Added running head 'COMPENDIVM LIB. I. ANNAL. TRITHEMII.' with printed page number 62, and the catchword 'Et', both omitted from the old version.

**Surviving cruxes (flagged in the chunk's translator's note):**
- Chunk opens mid-word at the boundary: 'contu-|lerit' — the bracketed supplements ('Of his deeds, good and ill, and how he confer-', 'ecclesiastical', 'upon his soldiers') are taken from the preceding segment's print, flagged as conjectural connection.
- Marginal sidenotes on printed page 62 (e.g. 'Grifo capitur & custodiae mancipatur', 'Annis complectitur in summa 1189', 'Natus anno 1462') are legible in the print but fall outside this chunk's OCR span and were not absorbed; note that the marginal total '1189' differs from the main text's 1,190 years.
- No genuinely illegible print survives in this span — no [unclear] markers were needed.

### full_chunk_0116
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The public translation followed the damaged OCR in the Suimo entry: it reproduced an OCR dittography of Farabert's invasion sentence (with two [unclear] gaps) and had Suimo die "in the eighteenth year of his reign," whereas the print reads "quod Suimoni & principibus suis non placuit. Vnde mortuo in Britannia Seuero, Suimo Galliam vastauit, anno regni sui penultimo, & victor remeauit," with death in regnal year XXVIII. It also gave Richimer's death in his twenty-third regnal year where the print has XXIIII, mangled names (Arthildis, Haifda, "fortress Neocum Cisthenanum," "Morandum"), silently supplied "and Rorich" in a list where the print names only two sons, dropped "Titi frater iunior," and omitted all ten printed marginal notes.

**Key corrections (verified against the scan):**
- Suimo paragraph rebuilt from print: 'which did not please Suimo and his chieftains. Whence, when Severus had died in Britain, Suimo laid Gaul waste in the next-to-last year of his reign, and returned victorious' replaces the OCR dittography of the Farabert sentence (verified in word-level zoom of page 102)
- Suimo's death corrected from 'eighteenth' to twenty-eighth regnal year (print: 'anno regni sui XXVIII'; margin note 'Suimo regnauit annis 28')
- Richimer's death corrected to 'Anno Domini CXIII, regnal year XXIIII' - extreme zoom shows four minims; OCR witness and old translation had 23
- Restored 'Titi frater iunior' (younger brother of Titus) for Domitian, dropped by the old translation
- Athildis (print 'Athildem'), not 'Arthildis'; Hasilda (print 'Hafildam', long s), not 'Haifda'
- 'inter Neocum castellum Cisrhenanum & ciuitatem Murandum' rendered as 'the fort Neocum on this side of the Rhine and the city of Murandum'; old version treated 'Cisthenanum' as part of the name and read 'Morandum'
- Print lists only two of Clodomer's 'three sons' ('tres filios, Farabertum, Nicanorem.'); the old translation silently added 'and Rorich' - now rendered as printed with an editorial bracket
- Fraktur place-names re-read from scan: Odemarsheim (not 'Odemarshem') and Franckenfurt (not 'Frankensfurt'), each confirmed by the roman-type margin notes 'Oppidum Odemarsheim' and 'Franckenfurt iuxta Moganum'
- 'ad Thermas Grani' rendered 'the Baths of Granus [Aachen]' instead of bare 'Aachen'; 'Nitriones' (print) not 'Nitrones'; 'sponte se ingerentes' rendered 'those who thrust themselves forward of their own accord'
- All ten printed marginalia restored in marked brackets (Domicianus Imperator; Traianus apud Coloniam fit Imperator; Odemar 14-year peaceful reign; Oppidum Odemarsheim; Marcomerus 21; Franckenfurt iuxta Moganum; Francorum potentia Romanis semper suspecta; Clodomerus 17; Farabertus 20; Suimo 28) - read from a dedicated margin-column zoom

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'Cisrhenanum': the fourth letter is ambiguous between r and t at scan resolution; read as cis-Rhenan adjective ('Cisthenanum' paleographically possible) and flagged in the translator's note
- 'Murandum' vs 'Morandum': corpus OCR witness reads Morandum; the print letter reads as 'u' at word-level zoom - flagged
- Print's own defect: only two names (Farabertum, Nicanorem) given for Clodomer's 'three sons'; rendered as printed with editorial bracket rather than smoothed
- Print reads 'pacem habentis' where grammar expects 'habens'; translated as 'having peace with all' without emendation

### full_chunk_0144
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The old translation flattened the print's three distinct annal dates to a single 733: the print reads DCCXXIII (723) for Lothar's death and DCCXXIIII (724) for Daniel/Chilperic's death, with only the Frisian war at DCCXXXIII (733). It also followed OCR garbles ("Walconia/Walcons" for Wasconiam/Wascones = Gascony/Gascons; "Austales" for Australes), left "[unclear]" at two points where the print is legible (Eudo's people; the catchword "Picta-"), and silently dropped the running head and all eleven printed marginal rubrics.

**Key corrections (verified against the scan):**
- Lothar's death date 733 -> 723: print reads DCCXXIII, 'regni sui octauo anno, indictione Romanorum sexta' (internally consistent: 715+8=723, indiction 6 fits 723, not 733)
- Daniel/Chilperic's death date 733 -> 724: print reads 'anno sequenti, hoc est, DCCXXIIII. obiit'
- 'Walconia'/'prince of the Walcons' -> 'Wasconia [Gascony]'/'prince of the Wascons': print reads 'in Wasconiam' and 'princeps Wasconum' (OCR misread long-s as l/t)
- 'Eudo, prince of the [unclear]' -> 'Eudo, prince of the Wascons': print reads 'Eudovvastonum princeps' set solid, bracketed as evidently 'Eudo Wasconum'
- 'Austales' -> 'Australes' (print clear in scan)
- 'Eudo' -> 'Edulo' in the Bordeaux entry: print reads 'Nam Edulo princeps Wasconum' (next page confirms 'mortuo Edulone, qui & Eudo')
- 'haberet auxiliantem' construed correctly: Edulo, having Abdiramus king of Spain as helper, burst in (OCR 'habet')
- Print name-forms restored: Pleutrudis (not Plektrudis), Rangafred/Regenfrid (not Raganfrid twice), Leufred (not Leutfred), Helperici/Hilpericus as the print alternates
- Running head '92 IOANNES TRITHEMIVS' and all eleven marginal rubrics restored (Dagobertus regnauit annis 5; Pippinus bellat contra Bertharium; Pippinus maioritatem domus recuperat; Daniel presbyter interrex an. 9; Lotharius interrex contra Danielem; Carolus Martellus maior domus; Theodoricus regnat annis 13; Carolus Martellus maior domus, regni Francorum instaurator; Sueui rebelles superantur a Francis; Phrisones ad obedientiam compulsi sunt per bellum; Wascones deuastant Francorum fines)
- Final '[unclear]' replaced with honest chunk-boundary note: page ends 'simili clade Picta-' (catchword), completed as 'Pictauienses affecit' at the head of the next chunk

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'Eudovvastonum' — print sets the words solid; read conjecturally as 'Eudo Wasconum' (Eudo, prince of the Gascons), bracketed in the translation
- 'Baugarenses' — u/n indistinct at available resolution; possibly 'Bangarenses' (OCR witnesses split both ways); flagged in text
- Margin note verb 'regnauit' (Dagobertus regnauit annis 5) — could be 'regnans' as the segment OCR has it; meaning unaffected

### full_chunk_0184
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The old translation followed the damaged OCR rather than the print: it undercounted nine of Rabanus's book-counts (Genesis, Exodus, Numbers, Leviticus, Deuteronomy, Kings, and Chronicles given as three instead of the print's four; Wisdom two for three; Mark three for four), rendered the OCR's "lectus" as "chosen archbishop" where the print reads "sextus" (sixth archbishop after Boniface), and dated Strabus to 850 where the print clearly reads DCCC.LX (860) "under the emperors Louis and Lothair." It also silently normalized "Baymonem" to "Haymo" and omitted the marginal rubrics, running head, mid-word page opening, and catchword.

**Key corrections (verified against the scan):**
- 'post sanctum Bonifacium sextus archiepiscopus' — print reads 'sextus' (sixth), not OCR 'lectus'; old rendering 'chosen archbishop' corrected to 'the sixth archbishop of Mainz after Saint Boniface' (verified in band crop b01)
- Book-counts re-read from print (crops u_freculph, b04, u_regum, b05, b06): Genesis IIII, Exodus IIII, Numbers IIII, Leviticus IIII, Deuteronomy IIII (old: three each); Kings to Hilduin IIII (old: three); Paralipomenon IIII (old: three); Wisdom III (old: two); Mark IIII (old: three, confirmed by line-start 'IIII.' before 'in euangelium Iohannis')
- Strabus floruit: print 'Claruit sub Ludouico & Lothario Imperatoribus, anno Domini DCCC.LX' — 860 under the emperors Louis and Lothair, plural (old: 850 'under Louis and Emperor Lothair'); confirmed in ultra-zoom u_strabusyear
- 'Ad Baymonem episcopum' — print unambiguously reads 'Baymonem' with capital B (ultra-zoom u_baymo); now rendered as printed with bracketed note that Haymo is presumably meant, instead of the old silent normalization to 'Haymo'
- 'in librum Iudith lib. VII' confirmed in print (ultra-zoom u_iudith) — the anomalous 'seven books' is the print's reading, retained with a bracketed '[so the print]' flag
- 'qui ad manus nostras adhuc minime venerunt' (OCR 'quid manus nostras') and 'praesulatu sedens' (OCR 'praefaturu') re-read from print
- Restored apparatus: running head '126 IOANNIS TRITHEMII', three marginal rubrics (Rabanus Maurus archiepiscopus Maguntinensis / Strabus monachus coenobij Fuldensis / Lupus Seruatus presbyter), catchword 'NOTGE-', and the mid-word opening 'mira|bili' concluding the Amalarius of Trier entry from printed p. 125

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'Albani discipulus' — print reading confirmed against the scan; the bracketed identification with Alcuin (Albinus) is editorial conjecture, not in the print
- 'Baymonem' — print's reading; 'Haymonem' (Haymo) presumably intended by the printer
- 'in librum Iudith lib. VII' — clearly VII in the print though historically anomalous; translated as printed
- Small numeral '30' in the outer margin beside the 'De natura' line (also visible on the adjacent leaf edge) — copy or press mark of uncertain purpose, noted but unrendered

### full_chunk_0267
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The graded rendering left raw OCR garbage untranslated ('CA fasefitaten tuaps', 'tapro[-', 'u eri d IUBE'), turned other mangled incipits into nonsense English ("What about your destruction", "I do not know God and I do not know"), misread proper names (Terus for Laetus, Tientarius for Armentarius, "Renedi" for the De visione Dei ad Fortunatianum entry), and silently dropped two entries (De poenitentia, 2 books; Quaeris a me vtrum). It also concealed the page's two-column structure (titles+book-counts vs. italic incipits), translating truncated incipits as if they were connected prose.

**Key corrections (verified against the scan):**
- 'CA fasefitaten tuaps' -> print reads 'Ad sanctitatem tuam.' (To your holiness...), verified in ultra-zoom of scan p. 252 right column
- 'What about your destruction tapro[-' -> print reads 'Quid de perue[n]tione ta[m] pros.' (transcribed; expansion flagged uncertain), verified in ultra-zoom
- 'u eri d IUBE' (left raw) -> print reads 'Quaeris a me vtrum.' (You ask of me whether...), verified
- 'Consolation to Terus' -> 'Consolationis ad Laetum' (Of Consolation, to Laetus), verified
- 'On Tientarius and Paulinus, homily 1' -> 'Ad Armentarium & Paulinum, li. 1.' (To Armentarius and Paulinus, 1 book), verified
- 'On Aulinus, on questions' -> 'Ad Paulinum de quaestionibus', verified
- 'On memory, book 1' (addressee dropped) -> 'Ad Nebrium de memoria' (Nebrius, i.e. Nebridius), verified
- 'On Renedi and Fortunatianus, homily 1' -> 'De visione Dei ad Fortunatianum, li. 1.' (On the Vision of God, to Fortunatianus), verified
- 'Against heresies, book 1' -> 'De 88. haeresibus, li. 1.' (the count 88 restored from print), verified
- Dropped entry restored: 'De poenitentia, li. 2.' (On Penitence, 2 books), verified in bottom-of-page zoom
- 'on the angel of John, homily 124' -> 'In Euangelium Iohannis, ho. 124.' (On the Gospel of John, 124 homilies), verified
- 'On the well-known song' (noto) -> 'De cantico nouo' (On the New Song), verified
- 'I do not know God and I do not know.' -> 'Deum nemo vidit vnquam.' (No one has ever seen God), verified
- 'For the award, if there be.' -> 'A prooemio super sede.', verified
- Running head restored as rubric: DE SCRIPTORIBVS ECCLES. 221 (was left as '- DE-SCRIPTORIBY$-ECCLES.: 221')
- Layout made explicit: left column = titles with book-counts, right column = italic incipits truncated at the column edge; roman-type inserts (De moribus Donatistarum lib. 1, De cataclysmo li. 1, De virtute animae) marked as such

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'Quid de perue[n]tione ta[m] pros.' - print clearly reads 'peruetione' with macron; expansion (perventione = attainment?) conjectural; incipit truncated
- 'Ad Hieronymum de reprehensione Pe' - 'Pe' cut off by column width; expansion Pe[ter/Petri] conjectural
- 'Ad Nebrium de memoria' - print reads 'Nebrium'; identification with Nebridius is editorial conjecture
- 'Commonitorium sancto.' - ending of final word uncertain (sancto/sancte)
- 'Intuentes quod modo au.' - final cut syllable could be 'au.' or 'an.'
- All right-column incipits are truncated at the column edge in the print; truncations kept, not completed
- The two columns drift out of row-register, so title-to-incipit pairing was not imposed

### full_chunk_0298
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The OCR collapses into a repetition loop after "Nam talem poterimus vi-" (one line repeated ~30x), and the old translation simply stopped there with "[unclear]", silently dropping the final third of printed fol. 185 (~10 lines: the rhetorical question, the "no equal among the Germans" passage, the Plato/Antimachus comparison, the public-fame and orations/letters/epigrams testimony, and the dedication sentence). It also carried several OCR-induced misreadings ("infect" for infigere, "Nor is the opinion false" for Nec eos fallebat opinio, "innocence" omitting ovium).

**Key corrections (verified against the scan):**
- Restored the dropped final passage of fol. 185 from the print: 'Nam talem poterimus virum praeter te vsquam inuenire, in quo haec omnia simul concurrant? Inter Alemannos neminem... Non loquor ad aurem, testis assit omnipotens... Te colunt docti... tu nobis quod Plato narratur fuisse Antimacho... Publica fama quae non mentitur agnouimus... Testantur hoc lucidissimae orationes... testantur Epistolae, testantur Epigrammata plura. Siquidem clarissima nominis tui fama... Italis & Gallis cum laude innotuit. Hinc subiit animum, vt tanto tibi pontifici subiectum opus de scriptoribus Ecclesiasticis inscriberem, diceremque tuo nomini, quatenus' — all read directly from the scan (ultra-zoom bands c08-c10)
- Print reads 'infigere' (verified by ultra-zoom of the descender g): 'to fix in it the tooth of its wicked bite', not OCR's 'inficere'/old 'infect it with the tooth'
- Print reads 'Nec eos fallebat opinio quae ex humilitate processit' — 'Nor did that conviction... deceive them', not old 'Nor is the opinion false'
- Print reads 'Tuto quiescit innocentia ouium' — 'the innocence of the sheep'; old version dropped 'of the sheep' (OCR had 'innocenti aequum')
- Print reads 'ne vestigiis veterum oberrarem' — plain 'lest I stray'; old added 'lest I seem to wander' (no 'seem' in print)
- Print reads 'de quorum doctrina & beneuolentia' — 'learning'; old 'very great learning' followed OCR's corrupt 'doctissima'
- 'lumine maiestatis reuerberata' confirmed present in print (OCR and old translation were right on this point)
- Confirmed chunk boundary: page ends mid-sentence at 'quatenus' (signature Q 3), continuing into segment 299's 'Sub umbra pontificalis culminis quiescerem securus' at printed fol. 186

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'facilem accusat' — print clearly has 'facilem', translated as 'facile' (readily accuses); likely a printer's error
- 'nec blandus capto laudator' — 'capto' is legible but its sense is uncertain; rendered 'a fawning praiser angling for favor' and flagged in the text
- 'considerem' vs 'confiderem' (cui eandem lucubratiunculam ... gratiorem) — long-s/f ambiguous at available resolution; translated as 'reckon'
- Chunk ends mid-sentence at 'quatenus'; the clause is completed at the head of fol. 186 (next chunk) — noted editorially, not absorbed

### full_chunk_0405
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The public rendering followed the damaged OCR instead of the print: it gave "On the Restoration of the Stone" (print reads *De reparatione lapsi*, "of the fallen"), left "On the Four [unclear]" where the print legibly reads *De quatuor coæuis* ("Four Coevals"), guessed "On Domestic Matters" for OCR "Demonstica" (print: *De monastica*), dropped the page's final entry (*De Astronomia*, 1 book) and the catchword, and omitted roughly thirty right-column book-counts that are present in the print (e.g. Chronicles 2, Politics 8, Economics 4, De animalibus 20). The grade note's specific claims ("surpassed life", ellipses, interpretive first sentence) do not occur in the current public text — see notes.

**Key corrections (verified against the scan):**
- Print reads 'De reparatione lapsi' (On the Restoration of the Fallen), not OCR 'lapidi'/'Stone' — verified in ultra-zoom of scan p.323
- Print reads 'De quatuor coæuis' (On the Four Coevals) — the æ ligature was OCR-misread as 'x' ('coxuis'); old translation's 'On the Four [unclear]' resolved
- Print reads 'De monastica' lib.5 (the individual branch of moral philosophy), not 'On Domestic Matters' (OCR 'Demonstica')
- Restored the final line of the page, 'De Astronomia lib.1.', dropped by the segment OCR, plus the catchword 'Specu-' (-> Speculum Astronomiae, next chunk)
- Restored right-column book-counts from the print that OCR and old translation dropped: In Iosue 1, In Ruth 1, In Paralipomenon 2, In Tobiam 1, In Prouerbia 1, In librum Sapientiae 1, In Ecclesiasticum 1, In Iob 1, In Hieremiam 1, In Danielem 1, In Euangelium Iohannis 1, Orationum super sententias 1, De differentia spiritus & animae 1, Diuersarum quaestionum 1, De causis elementorum 1, De intellectu & intelligibili 1, De vita & morte 1, Summa Philosophiae 1, Quaestiones contra Auerroistas 1, De Sphaera 1, De Astris 1, and notably De animalibus 20, Philosophia moralis 16, De Oeconomica 4, De politica 8
- Count-to-title alignment of the far-right column verified by the incipit test (counts attach to the row below the half-row-raised margin position; incipit rows take no count)
- Print reads 'In officium missae' (OCR 'In officio'); 'Venite post me faciam.' (OCR 'posse'); 'Clara est & quae nunquam.' and 'Laudes ecclesiae de.' confirmed as incipits in italic type
- Page mapping corrected: chunk map said scan p.324, but the segment is on scan p.323 (= printed p.292); p.324 holds the entry's continuation (Speculum Astronomiae onward) belonging to segment 406

**Surviving cruxes (flagged in the chunk's translator's note):**
- De animalibus book-count: print reads 'li.20.' at available resolution; the digit is worn and may be a damaged '26' (the traditional count) — flagged as conjectural in the text and note
- Philosophia moralis book-count: print reads 'li.16.'; the thin stroke before the 6 makes the numeral uncertain (conceivably 10) — flagged in the text and note
- Several incipits are truncated in the print itself (e.g. 'Quoniam plus exemplo quam ver.', 'Sume tibi librum gran.', 'Quoniam veritatis testimon.') — rendered as printed, not expanded; noted as the print's own truncation, not illegibility

### full_chunk_0449
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The public translation matched the right Latin span but left the opening crux as "[unclear]" where the print plainly reads "carnium esus" ("eating of meat") and dropped "monacho sano" ("for a healthy monk"); it copied OCR corruptions ("Indiamur" for "Induamur", "precious" from "praecarium" for print "praeclarum", "daily" from "diurna" for print "diuturna"); and it silently dropped the incipits and several book-counts in the Lavynham and Thomas Walensis book lists. Notably, the grader's alleged fabricated names (Anacletus, Chrodechildis, Ammianus) occur nowhere in this chunk or its public rendering — that part of the grade note does not describe this span.

**Key corrections (verified against the scan):**
- Opening fragment restored from print: '& probe concludit quod monacho sano, secundum regulam S. Benedicti professo, carnium esus illicitus sit' — 'for a healthy monk... the eating of meat is unlawful' (public had '[unclear]' and omitted 'healthy'); fragment completes the entry on John, abbot of St. Bavo, per scan p. 366.
- John of Werden's incipit reads 'Induamur, &c. vide.' in the print (Rom. 13:12), not OCR's 'Indiamur'.
- Thomas Walensis list: restored the incipits 'Beatus qui custodit.' and 'In absconditis parabo.' and the book-counts (lib.1 / lib.1 / lib.10 / lib.1), all dropped or partly dropped in the public version; 'Fluminis impetus laeti.' confirmed.
- Richard Lavynham: print spelling 'Lauinham' confirmed (latin-ocr 'Lauinharn'); right-column book-counts (lib.1 for De fundatione sui ordinis, Sermones varii, Et variae quaestiones) restored from the scan.
- Philip of Otterberg: print reads 'praeclarum & insigne' (OCR 'praecarium' had produced 'precious') and 'diuturna exercitatione' ('long-continued practice', not 'daily'); 'Otterburgensis, dioecesis Wormacien.' confirmed.
- Jacobus Magnus: 'de sermone & inquisitione sapientiae praenotatum' verified by ultra-zoom (long-s 'sermone' — public's 'On Speech...' was in fact supported); 'Bonifacii Papae 9' and year '1400' confirmed (page-OCR read 1490).
- 'Iohannes Campscen' verified letter-by-letter as the printed form; 'Wi-cleffi' hyphenation and 'coepit in Bohaemia' confirmed.
- Running head 'ABBAS SPANHEMENSIS', printed page number 336, and the page-end catchword 'clarus' (mid-sentence chunk boundary, continuing '& comptus eloquio' on the next page) all verified.

**Surviving cruxes (flagged in the chunk's translator's note):**
- Philip of Otterberg: line-end after 'exercitatione sa' lost in the gutter curvature — 'sa[tis?] doctus' is conjectural.
- Book-count after 'Epistolarum ad diuersos' in Philip's list lost in the gutter.
- 'Campscen': printed form verified but the bearer is unidentified; possibly a corruption in the 1531 print itself.
- 'Opus praeclarum & insigne': placement ambiguous — sits at the end of the 'feruntur' line, apparently an annotation heading the list; rendered in printed position with a bracketed note.

### full_chunk_0450
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The old translation followed corrupt OCR: it attached incipits to the wrong titles in both the Johannes de Duren and Paulus Venetus booklists (e.g. "Sanctify yourself" for the print's "Sanctificate ieiunium"/"Sanctify a fast", which belongs to the Quadragesimale), and it dropped two entries from Paul of Venice's list (Sermones de quadragesima; Super lib. Porphyr.). Several readings also deviated from the print: "Sletzstrad" for Sletstadt, "compositions" for comportationes, "reader" (lector) for sectator, and "practiced in writings" where the print has "in scrip. sanctis" (trained in the holy Scriptures).

**Key corrections (verified against the scan):**
- Page mapping corrected: segment 450 is scan page 368 (printed p. 337), not page 369 — verified by running head 'DE SCRIPTORIBVS ECCLESI. 337' and the 'Ff' signature at page foot.
- Duren booklist incipits realigned per the print's rows: 'Sanctificate ieiunium' (Sanctify a fast, not 'Sanctify yourself') pairs with the Quadragesimale; 'Cum confessor idoneus' with De septem peccatis mortalibus; 'Est via quae videtur ho.' with De occultis vitiis (old version had each shifted up one title and gave De occultis vitiis no incipit).
- Restored two entries dropped from Paul of Venice's list: 'Sermones de quadragesima, lib.1.' and 'Super lib. Porphyr., lib.1. Maxima & forti, &c.' — both clearly printed.
- Paulus Venetus incipits re-paired per the print: Plurimorum astrictus → Summa de naturalibus (anchor: the known opening of the Summa naturalium); Omnis doctrina → Super lib. Posteriorum; Naturali philosophia → Super Physicorum; Tecum sapientissime re. → Super Metaphysicam; Tanta literarum → Super de anima; Colloquium infa. → Summa philosophiae; Conspiciens → Logica duplex; Humanarum divinarumque → Super de generatione & corrupt. The old version had every pairing displaced.
- 'Hugo de Sletstadt' read clearly in the print (old: 'Sletzstrad'); identified as Schlettstadt/Sélestat.
- 'extant comportationes' (compilations) confirmed in the Ligniano entry, not 'compositiones'.
- 'in suis determinationibus sectator & interpres luculentus' confirmed — 'follower and lucid interpreter' of Bonaventure, not 'reader' (OCR 'lector').
- Duren described 'in scrip. sanctis nobiliter exercitatus' — trained in the holy Scriptures, not 'in writings'; 'magnae & praeclarae opinionis' (not 'praecipue').
- First entry confirmed: 'non meis verbis, sed eorum testimoniis comprobatur', 'praeclara opuscula', death date '1412. Indict. 5.' under Rupert and John XXIII; identified as the tail of the Nicolaus of Florence (physician) entry from the previous page.
- Chunk boundary handled honestly: span ends at the 'Ff' signature mid-booklist; continuation onto the next page noted editorially instead of absorbing it.

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'hic praedi.' (tail of Tilmannus's Sermones de tempore incipit) — abbreviated in the print; expansion 'here is preached' is conjectural.
- 'Tecum sapientissime re.' (Super Metaphysicam incipit) — printed without clear word division; continuation unknown, left in Latin with a bracketed partial gloss.
- 'Colloquium infa. &c.' (Summa philosophiae incipit) — abbreviation unresolved; left in Latin.
- 'Maxima & forti, &c.' (Super lib. Porphyr. incipit) — sense uncertain; left untranslated in Latin.
- 'Est via quae videtur ho.' — print breaks off at 'ho.'; ho(mini) 'to a man' (Prov. 14:12) is the natural but conjectural expansion.
- 'Plurimorum astrictus' — the elided noun ('precibus', entreaties) supplied in brackets from the known incipit of Paul of Venice's Summa naturalium.

### full_chunk_0454
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The published file under this chunk number translated the wrong Latin span entirely: it renders the chronicle's INDEX (Clodoveus/Conradus entries, = latin-ocr segments ~537–539), not segment 454. In fact full_chunk_0454 is the De scriptoribus ecclesiasticis page (printed p. 341) on Lorenzo Giustiniani, Augustinus de Roma, Baldus, Angelus Perusinus, and Pietro d'Ancarano — previously untranslated under this number. The grader's defects (pervasive [unclear], Clodoveus errors, broken English) belong to that misplaced index rendering; the public repo's chunks/ use an older 478-chunk numbering (neighbors 0453/0455 are also index material).

**Key corrections (verified against the scan):**
- Replaced the misassigned index translation with the actual span of full_chunk_0454: the De scriptoribus ecclesiasticis catalogue page, printed p. 341, scan page 372 (supplied mapping p. 373 is off by one; scan page 373 begins '-rarum studio uersans', the continuation)
- Laurentius Justinianus: print reads 'natione Venetus, ordinis Coelestini, & Venetus post-/ea patriarcha' — 'and afterwards patriarch of Venice'; OCR had garbled this to 'Venetus post-capitarcha'
- Title 'De complanctu Ecclesiae' (On the Lament of the Church) verified in the print; OCR gave 'complanetu'. Also verified 'De connubio verbi & animae' (OCR 'coniubio'), 'De interiori conflictu' (OCR 'confitu'), 'De sermone domini in coena' (OCR 'Defermone')
- 'Claruit temporibus Sigismundi Imp. & Iohannis Papae 23. Anno domini 1410' verified — Pope John XXIII (per-page OCR read '25')
- Baldus: 'Anno Domini 1423. In-/dict. prima. Papiae in conuentu fratrum minorum sancti Francisci, mense Iulio cum honore sepultus' verified by ultra-zoom (OCR had 'Indidiet. prima', 'conuenu', 'mensi Iulio'); the print's 1423 reproduced as printed
- Angelus Perusinus: death year 1423, 'eodem anno quo Baldus frater eius', verified (page OCR showed only 'r42..')
- 'PETRVS de Ancharano' verified against the scan (page OCR read 'Aucharano'); 'qui & si [etsi] vxoris vinculo fuerit colligatus' rendered 'although bound by the tie of a wife'
- Baldus/Angelus title lists verified row by row: Super Codice lib.9, Super ff.veteri lib.24, Super ff.nouo lib.12, Super ff.Infortiati lib.14, Super Institutis lib.4, De vsu feudorum (OCR 'De viu'), Super Autenti., Super secundo Decretalium, Additiones Speculi, Consilia multa
- Chunk-final mid-word break rendered honestly: 'in lite-' with signature mark Ff 3; continuation '-rarum studio uersans' confirmed at head of page 373

**Surviving cruxes (flagged in the chunk's translator's note):**
- None illegible at available resolution; the final entry (Petrus de Ancharano) ends mid-word at 'in lite-' at the chunk/page boundary — continuation verified, not rendered
- Print states Giustiniani was 'ordinis Coelestini' and gives Baldus's death as 1423 (historically c. 1400); both reproduced as printed and flagged in the translator's note

### full_chunk_0455
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The published full_chunk_0455.md translated the wrong Latin span entirely: it is an [unclear]-riddled rendering of the volume's alphabetical D-index (= Latin segment 539, scan page 450), with zero overlap with segment 455 (the De scriptoribus ecclesiasticis page on Angelus Perusinus, Vincent Gruner, Johannes de Auerbach, Dionigi da Borgo San Sepolcro, and Pierre d'Ailly, scan page 373 / printed p. 342). Additionally, the OCR witness for segment 455 drops eleven entries of d'Ailly's works list wholesale; the new translation restores them from the print.

**Key corrections (verified against the scan):**
- Identified the correct span: chunk 0455 = segment 455 = scan page 373 (printed p. 342, running head ABBAS SPANHEMENSIS); the assigned page [374] is off by one (page 374 = printed 343 = segment 456). Verified chunk 0450 matches segment 450 while public files 0454-0456 hold misassigned index translations (segments ~538-540).
- Restored from the print eleven d'Ailly entries omitted by the OCR after 'Compendium contemplationis, lib.3.': De spiritali scala; In psalterio breuiter; In psal. 70. meditationes; De legibus & sectis + De Concilio generali; Expositionis psalmi 70; In psal. 72. meditationes; In cantica canticorum; In septem psal. poenitentiales; De oratione dominica; Super eadem anagogice; Super Aue Maria - each with its printed incipit - plus the catchword 'Super'.
- Gruner's date reads 'Anno domini 1410' in the print; latin-ocr.txt has 1419 (ultra-zoom verified).
- 'In principium Marci' (print) vs OCR 'In principio Marci' (ultra-zoom verified).
- 'lectura notabilis, quam [qua-macron] in nouella plantatione Liptzensis gymnasii ... scripsit & legit' - OCR's 'quae ... scriploit' corrected.
- Incipit column restored as incipits, not garbled prose: 'Super hanc petram aedifi.' (OCR 'banc...edifi'), 'Quisquis qui a mundi' (OCR 'Quisquis qui ? murdi'), 'Quoniam multi sapientes' (dropped by OCR), 'Ad honorem benedictae', 'Ad laudem Dei animarum'.
- 'declamator quoque sermonum egregius' (OCR 'sermoni feregregius'); 'diui patris Augustini' (OCR 'diuipatris'); marginal line-numbers 10/20/50 recognized as print apparatus, not text (OCR had absorbed them as 'non to spernenda', 'no 20').
- Book-counts verified against the tally column: Super Decretalibus lib.5, Super ff.veteri lib.24, Super ff.nouo lib.12, Super officio missae lib.3, Quaestiones disputatae lib.1, Speculum considerationis lib.3, Compendium contemplationis lib.3.
- Auerbach entry confirmed to carry no year in the print ('Claruit in ciuitate Bambergensi, & varia conscripsit opuscula.'); Dionysius year confirmed 1412.

**Surviving cruxes (flagged in the chunk's translator's note):**
- Truncated incipits are the print's own column-edge cuts, reproduced as printed: 'aedifi.', 'le.', 'spirita.', 'fa.', 'sanctiss.', 'Ad honorem benedictae'.
- 'Vtrum Petri Ecclesia le.' - completion le[ge] ('by law') is conjectural.
- 'Cogitanti mihio sanctiss.' read as 'Cogitanti mihi, o sanctiss[ima]' - the vocative-o reading is conjectural.
- 'In psal. 72. meditationes' - the digit is the z-form 2 of this fount (as in printed page number '342'); 71 cannot be fully excluded.
- 'Expositionis psalmi. 70.' - odd genitive is what the print reads; rendered 'An Exposition of Psalm 70'.
- Opening word '-rarum' completes 'lite-rarum' split across the page break from p. 341.

### full_chunk_0462
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The published translation dropped two Hildebertus entries at the chunk head, miscopied the majority of the reference numbers (verified wrong in ~30 entries), and contained unsupported content the print does not have: "Trier" in Hilderic's conquest list, "He cruelly executes Pelagius by law" (print: "bellum cum eo crudele gerit"), "Honorius, priest of Jerusalem" (print: "Honorius Augustinensis presbyter"), "He dies as a monk, 11.47" (print: "quando mortuus sit 22.27"), and "Hispania Tarraconensis, so called" (print: "Hispania trifariam diuisa desolatur & affligitur").

**Key corrections (verified against the scan):**
- Restored two dropped entries: 'Hildebertus Francorum rex 57. quot annis regnarit 57.53. Quando mortuus sit 58.33' and 'Hildebertus Grunwaldi filius, a Sigeberto Francorum in Austrasia rege in filium adoptatur 55.25'
- 'Hispania trifariam diuisa desolatur & affligitur 35.20' (Spain divided into three parts) replaces the invented 'Hispania Tarraconensis, so called'
- Hilderic/Doringorum entry: print lists 'Coloniam Agrippinam, Moguntiam, Wormatiam, Spiram Argentinam, &c.' - no Trier; numbers corrected to 38.50/ibid.55/39.13/ibid.32/ibid.41/ibid.45/40.4 (public had 37.30/59.14/ibid.33/ibid.41/ibid.49/40.14); subject is Hilderic taking the wife of the king of the Thuringians, his host (public made him 'king of the Thuringians')
- 'bellum cum eo crudele gerit 47.18' (wages cruel war with him) replaces fabricated 'cruelly executes Pelagius by law'; Hilperic rex numbers corrected to 45.11/ibid.24, Brunhild exiled 'vna cum filiis' (with her sons, not 'her son')
- 'Honorius Augustinensis presbyter ... 269.49' replaces 'Honorius, priest of Jerusalem ... [unclear]'
- 'Hildeburgum Castellum non longe a Neoco ... 72.3' - 'Neoco' confirmed against the chronicle's own text at printed p. 72 (scan page 103: 'CONDIT CASTELLUM, NON LONGE A NEOCO ... HILDEBURGUM'); public had 'Meoco, 71.3'
- Hogel entry: 'in sportula a Parisiis in Bauariam portatur 116.55' (carried in a basket from Paris) replaces 'carried from Sportula into Bavaria, 116.4'; '117.13. item 118.11' replaces '117.15. His death, 118.11'
- Reference numbers corrected against the scan throughout: Hilarius Pictaviensis 205.13 (OCR 204.14), Hildefonsus 201.25, Hildebert of Le Mans 268.2, Hildericus rex 46: 38.20/ibid.21/ibid.23, rex 55: 56.23/ibid.30, rex 30: 21.8/22.27 (no monk), Hildegard abbess 138.5 (not 338.5), Hildegard/Charlemagne 98.9 (not 28.9), Hildegast 22.10 and 21.2/ibid.25, Hildouinus 259.4 (not 'Lodeve 140.4'), Hilduin abbot 252.44, Hilperic monk 263.56, Hincmar 252.51 (not 201.1), Hippolytus 197.30, Hippo 83.51 (not 85.51), Spain/Goths 76.22 (not 75.21), Holland entries 111.46 / 4.30 (not 69.39) / 116.30 (not 318.30), Hormisdas 239.38 (not 339.38), Horreum 53.48 (not 335.48)
- Hugbald is the '12th duke of the Eastern Franks ... 79.55' (public: 'Hugbaldus I ... 79.13'); 'Hubertinus de Casali ... 304.35' (public: 'Husbertinus de Casale ... 304.3'); Hugo is the '16th bishop of Wuerzburg' (public: 'VI'); Hugbald monk 256.45, Hugbert of Upper Traiectum 58.11, Hugo priest 271.41, Hugo of Siena 353.33, Hugo of Corvey 274.24, Hugo Sletstatinus 155.32, Hunibald's history carried to 4.57 (public: '7.')
- 'Hunni sunt Vngari' rendered 'The Huns are the Hungarians' (public: 'are called'); running heads *INDEX* (p. 456) and *IN I. TOM. IOH. TRITHEMII* (p. 457) and signature mark Nn restored

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'Laudociensis' (see of Hildouinus) is as printed but unidentified - perhaps for Laudunensis (Laon); public's 'Lodeve' is unsupported
- 'Hogel' and 'Grunwaldi' are the print's forms (Grunwald likely for Grimoald; Hildebertus Grunwaldi filius = Childebert the Adopted)
- 'Augustinensis' (Honorius) probably stands for Augustodunensis (Autun)
- Final digits of 96.10 (Hildegarius), 197.30 (Hippolytus), and 4.57 (Hunibald) were read at high zoom but carry minor uncertainty
- Chunk-boundary overlap: previous chunk 0461's tail 'Hilary' entries correspond to Hilarius papa 231.20 and Hilarius Arelatensis 229.9; this chunk begins at Hilarius Pictaviensis 205.13

### full_chunk_0465
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The published file under full_chunk_0465 does not correspond to segment 465 at all: it translates alphabetical-index entries (I/J–L: "Iubalcus", "Lotharingia, whence it is so called", etc.) whose Latin sits near segment 552 of latin-ocr.txt, with dozens of "[unclear]" placeholders. Segment 465's actual Latin — the end of the Thomas Walden (Netter) entry plus the Paulus de Castro, Ambrosius Florentinus (Traversari), and Caietanus entries with their book-lists — was effectively untranslated under this chunk number, which is consistent with the grader's "entries skipped" complaint.

**Key corrections (verified against the scan):**
- Mismatch resolved: translated the true segment-465 span (scan p. 383 = printed p. 352, running head ABBAS SPANHEMENSIS), verified by sequential context of segments 464/466 on scan pp. 382/384.
- Identified the entry continuing at the chunk's opening as THOMAS Walden (Thomas Netter, Carmelite, confessor and secretary of Henry V of England) from the foot of scan p. 382; chunk opens mid-word ('ad dispu-/tandum satis idoneus').
- OCR 'ad Colnam de medicis' re-read from scan as 'ad Cosmam de medicis' (Cosimo de' Medici) in the Traversari entry.
- OCR 'In lib. Methecorum' re-read as 'In lib. Metheororum' (Meteorology, 4 books).
- OCR 'Rothomagin suo conuentu' re-read as 'Rothomagi in suo conuentu' (died at Rouen); death date verified: 1430, Indiction 8, 'tertia die mensis Nouemb. Id est 3. Non.' (3 November).
- OCR phantom 'et f[unclear]' in the Caietanus entry shown by ultra-zoom to be the printed marginal line-number '50'; the print reads 'vir in diuinis scripturis studiosus & eruditus'.
- All book-counts verified digit-by-digit against zoom crops: Netter (Doctrinale 3; Sentences 4; Physics 8; Gen.&Corr. 2; De anima 4; Ethics 10; De caelo 4; Meteor. 4); Paulus de Castro (Codex 9; ff. nouum 12; Institutes 4; ff. vetus 24; Infortiatum 14; Consilia 1); Caietanus (Physics 8; De caelo 4; De anima 4).
- Paulus de Castro death date verified: 1437, Indiction 15, under Sigismund and Eugenius IV; Ambrosius's printed year verified as 1430.
- Chunk boundary honored: page ends with catchword 'Et'; Caietanus entry continues in segment 466 (scan p. 384) and was not absorbed.

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'scriptu[ris]' in the Caietanus opening line: the line tail runs into the gutter shadow; completion is near-certain but bracketed as conjectural.
- 'Epistolarum ad diuersos libros lib.1.' is printed thus (apparently redundant 'libros'); rendered literally as 'Books of letters to various persons, 1 book'.
- Ambrosius's floruit year is printed '1430' and rendered as printed, though historically his activity extended later.

### full_chunk_0469
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The published rendering of this index chunk invented or mangled proper names (Ortolf/Ortlieb for the print's Otto Wolffskell and Otto de Lodenburg, Orbio for Othilo, Paternus for Petronius of Bologna, Obertus for Osbertus), asserted facts the print does not ("Offa founded" where the print asks "whether Offa founded"; "taken by Charlemagne" where the print reads "a Carlomanno" = by Carloman; "Of the tithe of the Christian churches" for "Persecutio Christianorum decima" = the tenth persecution), reversed the Brunswick entry (Otto, William's son, obtains the duchy — not William), and dropped every page.line locator plus the bishops' ordinals.

**Key corrections (verified against the scan):**
- 'Ortolf, bishop of Würzburg' -> 'Otto Wolffskell, bishop of Würzburg, the 50th ... 82.46' (scan p.462, ultra-zoom verified)
- 'Ortlieb, bishop of Würzburg' -> 'Otto de Lodenburg, bishop of Würzburg, the 41st ... 82.28'
- 'Orbio, king of Bavaria' -> 'Othilo, king of Bavaria, when he reigned 100.46'
- 'founded the monastery of Schuttern' -> 'Whether Offa ... founded' (print: 'an monasterium Schutterense fundarit')
- 'taken by Charlemagne' -> 'stormed by Carloman' (print: 'à Carlomanno expugnatum 94.55')
- 'Of the tithe of the Christian churches' -> 'The tenth persecution of the Christians 13.20' (print: 'Persecutio Christianorum decima')
- 'Paternus the bishop [unclear]' -> 'Petronius, bishop of Bologna ... 210.2' (locator carried to head of next column)
- 'Obertus monk of Canterbury / Obertus the Englishman' -> 'Osbertus' both times (262.5, 319.9)
- 'From Helena ... William his son obtains the duchy' -> 'Otto, son of William by Helena ... obtains' (print: 'Ottho ex Helena ... Wilhelmi filius ... obtinet 108.30')
- 'Pope John is declared a heretic' -> 'Pope John XXII' (print: 'Ioannes 22.')
- 'Pavia, by whom among the Lombards and by what name it was called' -> 'occupied by the Lombards, who are also called Winuli' (print: 'qui & Winuli dicti')
- 'many years after his suffering and burial' -> 'ten years after his burial' (print: 'post 10 à sepultura eius annos'; no 'suffering' in print)
- Odoacer entry sub-clauses restored from print: 'occupies Angers by surrender ... is put to flight with his army' (print: 'fugatur cum exercitu', OCR had 'fungitur')
- 'Schneevogel' -> 'Schnefogel' as printed; 'Warner' -> 'Guarnerius' as printed; Paulinus of Trier's [unclear] is the printed ordinal '28'
- All ~62 entries' page.line locators restored (258.14 through 231.10), none present in the published version

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'Moritur 441.ibid.112.14' (Otto of Hungary entry): locator string corrupt as printed; transcribed with [sic]
- Otfrid of Weissenburg's first locator read as 127.5, possibly 127.1 (1/5 ambiguous at available resolution); second locator 257.44 clear
- 'Oriesiesis monachus' as printed (Trithemius's spelling for Horsiesios); kept as printed
- 'Odo Episcopus Camnacensis' (Cambrai, likely misprint for Cameracensis) sits just above the chunk boundary in chunk 0468, noted only

### full_chunk_0471
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The published full_chunk_0471.md does not correspond to [segment 471] at all: it renders alphabetical R-index entries (whose Latin sits near segment 560), including entries with no Latin source anywhere in this chunk (e.g. "Remigius baptized Hunibald"), while segment 471 is print page 358 of De scriptoribus ecclesiasticis (Palmieri continuation, Iohannes Ernesti, Bartholomaeus of Roermond, Henricus de Werlis, Andreas de Traiecto) — none of which the published file translated.

**Key corrections (verified against the scan):**
- Replaced the misplaced index translation with a translation of the chunk's actual Latin span (segment 471 = print p. 358, scan page 389), following the accepted precedent of the earlier full_chunk_0465 correction, which handled the identical mismatch the same way
- Page mapping off-by-one confirmed: given page 390 is print p. 359 (segment 472); the chunk's page is scan 389, running-head page number verified as 358 by zoom (per-page OCR misread it as 353)
- Verified 'inter praeclaros viros annumeratus fuit' (OCR: 'praecarios...annumerans in') and 'apud Cornam ciuitatem exustus est' (OCR: 'exultus'); 'Cornam' (r-n) confirmed by ultra-zoom
- Verified '...ad annum domini 1448. complens intitulauit' (OCR had 'compleps'/'comple')
- Verified 'transmisit ad posteros' (past tense; latin-ocr witness reads 'tranmittit')
- Fixed Ernesti work-table row alignment to the print: 'Sermones multi lib.1.' has an empty right column; 'Etsi loquendi de maxi.' and 'Sacratissimam desidera.' sit on the De nativitate / De ieiunio rows (latin-ocr had them shifted up one row)
- Verified Bartholomaeus death line: 'Anno domini 1446. Indictione 9. quarto Idus Iulii' rendered with modern equivalent 12 July
- Verified by ultra-zoom that the print reads 'Anno domini 1490.' in the Henricus de Werlis entry; kept as printed with a [sic] note that context (Basel council, Eugenius IV) shows a printer's error, evidently for 1440
- Verified 'quae Saonus dicta Treuerim versus ad occidentem extenditur' and identified the Saon as the Soonwald (flagged as translator's identification)
- Verified 'Carmina & rhythmi' row carries no 'lib.1.' in the print (latin-ocr added one); right-margin 'lib.1.' marks for Summa vitiorum / De proclamationibus fratrum / De iuramento confirmed by margin zoom

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'apud Cornam ciuitatem' — place-name of Palmieri's alleged burning kept exactly as printed; historically suspect but clearly legible
- 'Anno domini 1490.' (Henricus de Werlis) — legible print reading retained with [sic]; evidently a printer's error for 1440
- All work-list incipits are abbreviated by the printer (e.g. 'Etsi loquendi de maxi.', 'Dum olim diuinae voca.', 'Egressus forsan cubiti') and are left as printed, untranslated
- 'Saon' = Soonwald is a translator's identification, flagged as such
- 'Andreas de Traiecto' — Traiectum left ambiguous (Utrecht or Maastricht), glossed in brackets

### full_chunk_0472
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The old translation followed badly interleaved two-column index OCR: entries from the left and right columns of the page were jumbled together out of order, dozens of lemmata were reduced to bare "[unclear]", several proper names were guessed wrong (e.g. "bishop of Worms" for Breslau, "Schlüchtern/King Otto" for Schuttern/Offo king of England, "Sebald under the oak" for "the school under the oak"), and many page.line references were miscopied (233 for 60.33, 50 for 53.20, 103.19 for 103.29, etc.). It did not invent narrative — consistent with the grade note — but most of what the print actually says was recoverable and is now restored in print column order.

**Key corrections (verified against the scan):**
- Chunk located on scan pages 465-466 (not page 391, and not latin-ocr.txt [segment 472], which is a different text)
- Rudolph of Rüdesheim is 'Episc. Vratislaviensis' (bishop of Breslau), 163.27 — old translation said 'bishop of Worms'
- 'Schutterense monasterium non fundatum ab Offone Angliae Rege 61.7' — Schuttern abbey / Offo king of England; old translation had 'Schlüchtern ... King Otto'
- 'Schola sub quercu 19.8' (the school under the oak) — old translation invented 'Sebald under the oak'
- Previously '[unclear]' lemmata restored from the print: Rupertus Anglicus (d. without children, 118.36); Rupertus Pipinus (sets out against the Turk 117.19, where buried ibid.26); Rupert count palatine captured by the Saxons after a second same-day triumph 115.30; Rupert baptizes Theodo, the Bavarian duke's son, at Regensburg 100.52; Rupertus abbas Lympurgensis; Rutgerus Sicamber Gelrensis 174.49; Sacerdos Iouem consulens 2.54; Sala fluuius 26.39; Salagast villa on the Main 35.12; Saligae leges a Salagasto latae 83.44; Salomon of Constance 127.17; Salvian of Marseille 233.45; Samuel presbyter 233.58; Sanctes de Arduinis 353.51(?)
- Saxon entries restored: 300 horses promised to Pippin yearly 96.30; 500-oxen tribute 90.37; Hessians loyal to Charles devastated 97.16; Saxons & Slavs brought to order 98.7; trans-Elbe Saxons transferred to Francia 98.23; Fritzlar church saved by two angels 97.20(?); Saxony seven times subdued 97.3.24.30.36.56, pag.98.5.23; proverb 'Ecce Camber' 5.20; Saxons signified to Marcomir by the lion 3.34
- Reference numbers corrected against the print: 60.33 (old '233'), 53.20 (old '50'), 28.32 (old '18.31'), 103.29 + ibid.34 (old '103.19'), 105.45 (old '103.4'), 110.21 (old '110.1'), 39.22 (old '30.12'), 168.18 (old '166.18'), 136.25;273.8 (old '136.15.274.8'), 154.18;353.23 (old '18.353.23.14'), 116.36 (old '112.36'), 168.32 (old '169'), 105.12 (OCR witness '107.12'), 272.18 for Rupert of Deutz (old '171.18'; a second Deutz entry 135.41 also exists on p466)
- Chunk boundaries rendered honestly: opens at the left column's last two lines ('Romani Francos ex Hispaniae finibus eiiciunt 72.50'), ends mid-word in the Sebastian Brant entry at the print line-break 'quid scri-', with the continuation (173.32) noted as belonging to the next chunk

**Surviving cruxes (flagged in the chunk's translator's note):**
- 'Rudolphus de Euschringen' — name legible only as Euschringen(?); its line reference after '172.' is unresolved at scan resolution
- 'Ruggandus Epis. Metensis' — printed form transcribed as seen, possibly a corrupt name in the print; refs read 124.26; 251.9
- 'Ruthwicus Francorum historiographus 18.45' — name uncertain
- 'Cancellarius Archiepiscopi Badensis' — the print's wording ('archbishop of Baden'), historically odd, kept as printed
- Final line-digits flagged (?) where the page-curve blurs numerals: 20.18 (legions driven back), ibid.35 (Rudolph dies in England), 196.30 (Agricola), 212.54 (Rufinus), 81.14 (Rugerus), 272.54 (Lympurgensis), 353.51 (Sanctes), 97.20 (Fritzlar); 260.30, 262.32 and 272.18 read at high zoom though the older OCR witness differed
- Print spellings retained: 'Schyren' for Scheyern, 'Astila' (Theodomer's mother, elsewhere Ascyla), 'cadunt' for 'caedunt'

### full_chunk_0475
Re-translated from scratch against the source page-scans, superseding the earlier machine rendering, and independently re-graded against the Latin; the superseded text is retained in version control.

**What was wrong:** The published rendering was translated from badly damaged OCR of the T–V index pages: a large fraction of the page.line reference numbers were wrong (verified against the scan, e.g. 59.3 not 9.3, 255.20 not 165.10, 1.27/44/53 not 1.13/43/93, 28.29 not 18.19), several proper names were guessed or mangled (Hildegard for Hildegasti, "Zrrentina" for de Argentina/Strasbourg, "Tawilgran" for de Aquisgrani/Aachen, "of Fijen" for Vlsenus, "son of Grimoald" for Gresemundus, "the Amur" for "à mari"), entries were misdivided ("The poisons of Brunhild" split off from the Theodoric entry) and content dropped ("500" cattle, "he dies, 57.37", "king of the Visigoths").

**Key corrections (verified against the scan):**
- Chunk-to-segment mismatch resolved: latin-ocr [segment 475] is catalogue text (Kanneman/Juterbock/Dorbellus, scan p.393) and does NOT correspond to public chunk 0475; the chunk's true Latin is the index span on scan pages 468-469 (alignment verified intact at segments 1 and 250, broken by 474; latin-ocr has 570 segments vs 477 chunks). Translated the correct span; supplied page mapping [394] was wrong.
- Opening fragment restored as continuation: 'vniuerso Austrasiorum regno in deditionem accipit ibid.39 moritur veneno Brunihildis auiae suae ib.58' - one entry, not a separate 'poisons of Brunhild, 84' entry.
- 'Vaticinium Hildegasti' (twice, refs 72.10 and 21.30) - prophecy of Hildegast, not 'Hildegard' (public also had refs 71.10/21.50 wrong).
- 'Vdalricus de Argentina monachus' = Ulrich of Strasbourg, not 'Ulrich of Zrrentina'.
- 'Thilmannus de Aquisgrani, Prior inferioris Alemanniae, 146.16' = Tilmann of Aachen, prior of Lower Alemannia, not 'of Tawilgran, prior of Lower Alsace'.
- 'Theodoricus Vlsenus 176.55' (Ulsenius), not 'Theodoric of Fijen 175.55'; 'Theodericus Grespmundus [Gresemund] Moguntinus, adolescens 18 annorum, 176.6', not 'son of Grimoald, 131.36'.
- 'Theodoricus Episcop. Wirtzburg.42 quot annis praefuerit 82.30' - Theodoric, not 'Theodard', ref 82.30 not 130.
- 'Theodoricus rex Wisogothorum interfectus 37.17' - king of the Visigoths slain (public dropped 'Visigoths' and added 'treacherously').
- 'Synodum conuocat & epis. ab officio remouet ib.48 moritur 57.37' - ref ib.48 not 15.48, and the dropped death notice restored.
- 'Treuirorum Ciuitas sub quo imperatore capta 37.33' - 'under which emperor it was taken', not 'founded under Emperor Ninus, 37.53'.
- 'Treuirorum vrbs sedes Imperii a Maximo facta 30.55' - by Maximus, not 'under Maximinus, 30.1'.
- 'Tributum 500 boum ... 90.51' - five hundred cattle restored (public: 'cows ... 90.1').
- 'non procul a mari 28.29' - 'not far from the sea', not 'not far from the Amur, 18.19'; 'cis Oderam' = on this side of the Oder.
- 'Tungrorum fines, regum Francorum sedes 27.95' - 'territory of the Tongri, seat of the KINGS of the Franks', not 'Tongeren, without kings'.
- Reference numbers corrected throughout, each read at 2-4x zoom: 131.26;266.56 (Trier archbp.), 205.49 (Titus of Bostra), 211.1 (Ticonius), 204.51 (Triphyllius), 71.8&10 (persecutions), 58.19 (Traiectum-Liege), 11.43 (truce), 16.25, 28.9, 32.44, 33.44, 37.48, 37.29, 44.25, 31.54, 78.15, 36.33, 18.40, 27.37, 85.52, 165.56, 181.54, 33.10, 35.30, 1.27/ibid.44/47/53 (Trithemius's three volumes), 59.3, 63.2 ('conseruatum' = preserved, not 'confirmed 203.1'), 42.54, 56.4, 134.24, 31.53, 32.51, 51.15, 19.11, ibid.32, 24.42, 249.21, 235.5.

**Surviving cruxes (flagged in the chunk's translator's note):**
- Numerals printed after royal/episcopal titles ('Francorum rex 54/60', 'Episcop. Wirtzburg.42') are interpreted as ordinals of Trithemius's king/bishop lists; flagged as conjectural in the translator's note.
- Print spells 'Grespmundus' for the Mainz humanist Gresemund and 'Hasbasiensis' for Hasbaniensis (Hesbaye); both print spellings kept in brackets.
- 'Tungrorum fines ... 27.95' - the line number 95 is unusually high but is what the print clearly shows.
- 'epis. ab officio remouet' - abbreviation leaves singular/plural indeterminate; rendered 'bishops'.
- The p.468 running head 'INDEX.' falls mid-entry at the column break in the witness's reading order; rendered as an italic running-head line with an editorial bracket.

## 2026-06-10 — codex (GPT-5.5) facsimile grading of the re-translation pass

All 19 re-translated chunks were graded by GPT-5.5 against the **page images**
(the grader reads the Latin from the scan, not the OCR, which is the honest
measure for facsimile-grounded work). Result: **faithful min 4, mean 4.05/5;
fluent min 4; 1 of 19 flagged `hallucinated`** — chunk `full_chunk_0144`.

The single flag was adjudicated against the scan and **the translation was
upheld**: the grader's three specific objections do not hold. (1) It claimed the
printed page is 93 — a high-zoom crop of the running-head band shows the page
number is **92** (running head *IOANNES TRITHEMIVS*), exactly as rendered. (2) It
called "Eudo, prince of the Wascons" overconfident — but the text already
brackets the crux inline (*the print runs the words together as "Eudovvastonum"*)
and again in the translator's note. (3) It proposed "Bungarenses" for the minim
crux the translation already flags as *"Baugarenses [u/n indistinct, possibly
Bangarenses]"*. The `hallucinated` flag is the expected apparatus artifact (the
grader reads bracketed editorial cruxes as additions); no change was made.

## 2026-07-09 — structural: removed-chunk placeholders restored

- Chunks [548, 550, 556] were source-digitization boilerplate removed during the quality sweep; the files were deleted outright, leaving numbering gaps and dangling grade/chapter references. Restored them as standard removal-marker placeholder files (the same convention build_work_artifacts.py uses), so chunk numbering, chapter anchors, and the grade ledger resolve. No translation content was added; the reading text (english.md) is unchanged.

## 2026-07-10 — removed OCR double-scan duplicates (47 segment pairs; audit fix)

The OCR pipeline double-scanned page ranges of this work, producing 47 byte-identical segment pairs in `latin-ocr.txt` (~29,000 duplicated words, ~17% of the work). Each duplicate segment was independently translated and shipped, so the reading text contained the same passages twice (two different renderings of the identical Latin). Suppressed the duplicate member of each pair: its chunk file now carries a cross-reference removal marker pointing to the retained copy, and `english.md` was rebuilt from the deduplicated chunks. Chunk numbering is unchanged (so the parallel viewer still aligns each segment with its Latin); only the duplicated English content is removed. No genuine content was lost — each suppressed passage is retained verbatim at its first occurrence. (Deep-audit finding H1.)

## 2026-07-10 — residual double-scan dedup (near-identical pass)

The 2026-07-10 double-scan deduplication keyed on byte-identical Latin segments; 3 additional duplicate pairs whose two scans differ only by minor OCR variance (similarity >= 95%) were caught in a follow-up similarity sweep and suppressed with the same convention (duplicate chunk replaced by a cross-reference marker; english.md re-stitched; chunk numbering unchanged): 93->kept 90 (sim 100%); 102->kept 99 (sim 100%); 118->kept 115 (sim 100%). Borderline partial-overlap pairs below 95% similarity were left in place pending eyes-on review (see corpus report).

## 2026-07-10 — borderline double-scan pairs resolved (eyes-on review)

The partial-overlap double-scan pairs deferred by the earlier passes were compared side by side (Latin diff + English chunks); in each pair one capture contains everything real in the other, so the lesser member was suppressed with the standard cross-reference marker and english.md re-stitched:
- Suppressed chunk 0539 in favor of 0531: no unique content on either side; earlier capture retained.
