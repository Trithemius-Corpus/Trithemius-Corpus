# Errata — prdl-24383_septem-secundeis-intelligentiis-spiritibus-orbes-post-deum-moventibus



## 2026-07-09 — digitization-artifact cleanup (latin-ocr.txt)

- Removed a generation fill artifact (an asterisk run of ~4,000 characters) from [segment 2] of latin-ocr.txt. The run length (~4096) marks it as a model/pipeline artifact, not page content. Segment structure unchanged.

## 2026-07-10 — removed pseudo-Greek hallucination tail from segment 19 (latin-ocr.txt only)

The final segment of `latin-ocr.txt` was ~4 KB of hallucinated pseudo-Greek gibberish (mixed Greek script, fake Latin transliteration, and abbreviation glyphs) plus an English blank-page meta line, after the genuine Nuremberg/Haselperg 1522 colophon (`¶Impressum Nurnberge impens Ioānis Haselbergs, Anno, XXII.`). The English chunk 0019 carries only a brief flagged stutter-summary and does not reproduce the pseudo-Greek. Segment marker retained; segment count and chunk boundaries unchanged. (The segment-2 asterisk wall was already collapsed to a summary note by an earlier fix.)

## 2026-07-10 — removed stutter-summary tail chunk 19 (english + chunk)

Chunk 0019 (88 bytes) was a brief flagged stutter-summary ("And the king, son of [Roli?]... [repeated throughout]") appearing after the genuine Haselperg/Nuremberg 1522 colophon. Replaced `chunks/full_chunk_0019.md` with a removal marker and dropped the line from `english.md`. (The underlying Latin segment 19 — pseudo-Greek hallucination — was removed separately, logged above.) Segment count and chunk boundaries unchanged.

## 2026-11-18 · seven-michael

The numeral at the start of Michael’s rule is 2126. The preceding page ends the previous period in the same year. AI visual collation. Human review is undocumented.

Previous wording: according to the common reckoning, 2116

Revised wording: according to the common reckoning, 2126

*anno mundi secundum communem supputationem 2126 … usque ad annum aetatis mundi 2480*. [BSB, image 9](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00013346_00009/120,582,1475,248/full/0/default.jpg)

*usque ad annum aetatis mundi 2126*. [BSB, image 8](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00013346_00008/389,1949,1463,230/full/0/default.jpg)


## 2026-11-18 · seven-samael

The text gives 4252 as the endpoint of Samael’s rule. AI visual collation. Human review is undocumented.

Previous wording: His rule lasted 354 years and 4 months, until the year 4152.

Revised wording: His rule lasted 354 years and 4 months, until the year 4252.

*duravitque regimen eius annis 354, mensibus 4 usque ad annos 4252*. [BSB, image 11](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00013346_00011/116,1188,1420,253/full/0/default.jpg)


## 2026-11-18 · seven-temple

<span id="a-en-0008-0005-001"></span>

Solomon is the subject of the one sentence about the temple. The word famosissimum and the clause continue across the page turn. Gabriel first appears in the following account. AI visual collation. Human review is undocumented.

Previous wording: Saul was made the first king of the Jews, and after him David, whose son King Solomon built the temple of the true God with all [unclear].

Revised wording: Saul was made the first king of the Jews, and David succeeded him.

Previous wording: Gabriel built the temple in the midst of Jerusalem.

Revised wording: David’s son King Solomon built the temple of God in Jerusalem, a temple renowned throughout the world.

*posteaque David cuius filius rex Salomon templum Dei … famosissi-*. [BSB, image 11](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00013346_00011/107,1944,1430,235/full/0/default.jpg)

*-mum in mundo in Hierusalem construxit … Ordine tertio decimo Gabriel*. [BSB, image 12](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00013346_00012/396,235,1454,520/full/0/default.jpg)

## 2026-11-23 · seven-direction-of-michael

At the page turn ad directionem Michaelis qualifies Evil-merodach’s restoration of liberty and a king to the Hebrews. The next clause describes Michael’s role in Daniel. AI visual collation. No human verification of these readings is documented.

Previous wording

In the time of this rule Evil-merodach king of Babylon restored liberty and a king to the people of the Hebrews.

Revised wording

During this reign, at Michael’s direction, Evil-merodach king of Babylon restored liberty and a king to the Hebrew people.

Previous wording

of Michael, who, as Daniel writes, stood for the people of the Jews, who had been entrusted to him by God.

Revised wording

As Daniel writes, Michael stood for the Jewish people, whom God had entrusted to him.

*In tempore huius regiminis Evilmerodach rex Babilonis libertatem et regem populo restituit Hebreorum ad directio-*. [Bayerische Staatsbibliothek, (0012)](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00013346_00012/432,1949,1360,249/full/0/default.jpg)

*-nem Michaelis qui, ut Daniel scribit, pro populo stetit Iudeorum cui a Deo fuerant commissi.*. [Bayerische Staatsbibliothek, (0013)](https://api.digitale-sammlungen.de/iiif/image/v2/bsb00013346_00013/126,269,1339,209/full/0/default.jpg)
