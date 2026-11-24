# The Ciphers of Trithemius

Johannes Trithemius (1462–1516), abbot of Sponheim and later of the Schottenkloster in Würzburg, stands at the head of printed cryptography. His *Polygraphiae libri VI* — "Six Books of Polygraphy" — is his open cryptographic manual, the first printed book on the subject in the West: completed late in his life, dedicated to Emperor Maximilian I, and printed in 1518, two years after his death. Its notorious companion, the *Steganographia* (composed around 1499–1500), circulated only in manuscript during his lifetime and earned him lasting accusations of necromancy, because its cipher instructions are dressed as conjurations of angels and spirits. Both systems — and the explanatory keys Trithemius supplied for them — are in this corpus.

## The "Ave Maria" cipher: a prayer that is also a message

The heart of the *Polygraphia* is verbal substitution, often called the "Ave Maria" cipher. Each of its books presents a different *modus* of enciphering, but the basic mechanism is constant. The plaintext is broken into individual letters, and each letter is replaced by a Latin word drawn from a substitution column — an *alphabetum* of cipher words. In the multi-column *modi* the substitution rotates with the letter's position: position 1 uses column 1, position 2 uses column 2, and so on, returning to column 1 once the columns are exhausted. The columns are built so that *any* plaintext produces a grammatical Latin sentence — invariably a devotional invocation. The ciphertext is thus undetectable: it reads as ordinary monastic prayer.

The corpus's own worked example takes the eight-letter plaintext `ABCDEFGH` through the eight columns of *Modus Primus* (the first cipher of the *Clavis Polygraphiae*): A in column 1 becomes *facti*, B in column 2 *certe*, C in column 3 *timendum*, D in column 4 *continue*, E in column 5 *sempiternum*, F in column 6 *fabricatorem*, G in column 7 *supercaelestium*, and H in column 8 *compassionem*. The resulting ciphertext reads:

> *Facti certe timendum continue sempiternum fabricatorem supercaelestium compassionem.*

To an eavesdropper this is a pious Latin sentence; only the recipient who knows to take each word back through its enciphering column recovers `ABCDEFGH`.

The cipher words above are given in their *intended* forms, to show the mechanism clearly. The OCR'd source cells themselves carry scannos — *certe* appears as `Lerte`, *fabricatorem* as `fabricatosem`, *supercaelestium* as `supercelestvm` — and those damaged forms are preserved as they appear in the rendered chunk tables and the facsimile beside them, per the editorial principle below.

The published tables let you watch this machinery at full width. One chunk of the *Clavis Polygraphiae* (`full_chunk_0085`) parses twenty-two substitution columns against Trithemius's 24-letter alphabet (`a b c d e f g h i k l m n o p q r s t v x y z w`, omitting *j* and *u*). Reading across the row for the letter `b`, the first columns give *ebales*, *abadan*, *abzym*, *abenoz*, *abadiel*, *abnason* — six different ways of saying "b", each pulled from a different prayer-vocabulary.

## Rotating alphabets: the *tabula recta* and the *Orchema numerale*

The *Polygraphia*'s sixth book moves from words to tables. Its alphabet-rotation expansion figures (*tabula recta* / *auersa* / *aucta*) derive new cipher alphabets from a base alphabet by transposition — in the rendered *Prima figura expansionis tabulae rectae*, each row is the alphabet stepped one place from the row above. This rotating-alphabet family is the ancestor of what later cryptographers know as the Vigenère table. Alongside it sits the *Orchema numerale*, a numerical-substitution matrix indexed by Latin letters with Trithemius's own note describing its diagonal use.

An honest note about what you will see. In the printed book these are worked *example* figures, set as paired plaintext/cipher columns — not one mechanical master grid. The OCR that underlies this corpus frequently linearised those paired columns into identical rows, a layout that cannot be recovered from the text alone. Rather than fabricate grids, this corpus omits the misleading transcription in 31 of the 54 cipher-grid chunks and shows the source facsimile instead; where the OCR did preserve the rows, they are transcribed as tables with illegible cells marked `—` and OCR noise left visible. In every case the facsimile shown beside the rendering is authoritative for the cipher.

## The *Steganographia*: ciphers dressed as conjurations

The *Steganographia* works differently, and its mechanism is documented in Trithemius's own key, the *Clavis generalis triplex* — the "Threefold General Key to the Steganographic Books." Unlike the *Polygraphia* scheme (plaintext letter → Latin word), the *Clavis* convention is letter-pair substitution: each plaintext letter maps to a single ciphertext letter. The source records each alphabet as comma-separated pairs of the form `Ax,bz,ca,db…` — read as `A→x, b→z, c→a, d→b, …`. The cipher letters are then padded out into an innocent-looking Latin prose *Exemplum* that reads as ordinary devotional writing.

The rendered chunks show the full anatomy of one concealment: the *Alphabetum* (the substitution table); the *Intentio Mysterij*, the secret message in early-modern German — in one example, *"Ich bitte dich komm von stund an zu mir/ es thut sehr noth"* ("I beg you, come to me at once; the need is great"); the *Literae significantes*, the bare ciphertext letters; and the *Exemplum*, the Latin cover prose that carries them, opening *“Creator generis humani aspice Deus…”* in the 1608 print.

In the *Steganographia*, instructions take the form of conjurations addressed to Pamersiel, Padiel, Camuel, Aseliel and other spirits. The *Clavis* explains how letters can carry a second message under this cover. The edition preserves the spirit names and quotes the conjurations. The *Steganographia* first appeared in print in 1606 and was later placed on the *Index Librorum Prohibitorum*.

## Reading Modus II against the 1608 print

In the Frankfurt *Clavis*, Modus II starts with an empty word and takes the initial of every second word. The decorated C belongs to *Creator*. The first fourteen words of the printed *Exemplum* give seven significant initials, `gafzgbc`. On printed p. 56 Trithemius specifies the second preceding letter and gives the examples A→x, b→z, c→a. Page 57 prints all 22 pairs on the alphabet `abcdefghiklmnopqrstvxz`. Inverting the first four significant letters yields *ich b*, the beginning of the printed German request. [HAB Fb 243, printed p. 56](https://diglib.hab.de/drucke/fb-243/start.htm?image=00248) · [Printed p. 57](https://diglib.hab.de/drucke/fb-243/start.htm?image=00249)

The [executable cipher edition](cipher-solutions.html) applies that rule to the 42 letters of the previously archived transcription. The result begins `ichbiderich`. The printed *Intentio* begins *Ich bitte dich*. After spaces and punctuation are removed and u is represented by v, it has 45 letters. The first difference occurs at position 6. The cause of each remaining difference requires further collation. The full page, a detail of the significant letters, the 22 substitutions and both readings are available with the JSON and TSV downloads.

### Earlier experimental readings

The archive reports the following results for ten other examples. The page numbers in these tables are corpus image numbers. The matches and proposed shifts are historical results from the earlier transcription experiment. The 23 November 2026 collation checked Modus II only. Its previously reported match of 62% predates the corrected executable trace. The historical scoring results have not been independently reproduced here.

| Modus | Corpus image | Reported match | German excerpt reported in the earlier experiment |
|---|---|---|---|
| XI | 263 | 77% | *diese bucher behal[t]… die heimlich* |
| X | 261 | 75% | *die sachsen [ver]sam[m]elen ein gros [vol]ck…* |
| V | 254 | 65% | *der p[farr]her[z] von bing ist vmb eins…* |
| VI | 255 | 62% | *mor[gen] vmb se[y] gerust vnd wart meiner…* |

| Modus | Corpus image | Reported shift | Reported match | German excerpt reported in the earlier experiment |
|---|---|---|---|---|
| XXXVII | 243 | +18 | 92% | *Jacob Seum hat nun gesprochen, er will dich erstechen… hüt dich vor ihm* |
| XXXIII | 238 | +14 | 89% | *er ist noch new, versuch ihn vor gantz wol… er trinket auch gern Wein* |
| XXXV | 241 | +16 | 87% | *Der Abt von S. Johannes Berg helt Communia… vnd fehret auch im Narrenschiff* |
| XXXVIII | 244 | +19 | 86% | *Wisse das Hans Schwerd viel übel von dir red… nimpt sich doch an für dich* |
| XXXII | 237 | +13 | 78% | *noch… vmb Vhr… du mich an dem Wald… pfeiffen mit einem Schlüssel… kom herab* |
| XXXIX | 245 | +20 | 70% | *Dir wird geschrieben herzu kommen, ist mein Rath… der Anschlag ist dich zuvertrencken* |

The high-mode examples include warnings about an intended attack and slander, a reference for a drinker, an account of an absent abbot, a whistle signal and advice to stay away. The printed *Intentiones* supply a reference text for comparison. Skinner and Clark (2024) give a modern English edition of the *Steganographia*. Ernst (1996) and Reeds (1998) independently analyzed Book III.

## Explore the cipher materials in this corpus

- [**Executable cipher edition** — Modus II, step by step](cipher-solutions.html) — a reproducible worked example with facsimile evidence, explicit editorial status, keyboard-operable navigation, substitution table, plain-text account, and downloadable data.
- [Substitution tables (*Polygraphia VI*, cipher-key renderings)](works/prdl-24390_polygraphiae-libri-vi_style-c-cipher-key.html) — the "Ave Maria" alphabets, rendered alphabet-down / columns-across beside the source facsimile.
- [Rotation figures and the *Orchema numerale* (cipher-grid renderings)](works/prdl-24389_polygraphiae-libri-sex-ioannis-trithemii-abbatis_style-c-cipher-grid.html) — the *tabula recta* family, with facsimiles wherever the OCR collapsed the figure.
- [Worked steganographic examples (*Clavis Steganographiae*)](works/prdl-70281_clavis-generalis-triplex-in-libros-steganographicos_style-c-untranslated.html) — freshly translated passages from the triple key; the letter-pair claves themselves are on the [cipher-key page](works/prdl-70281_clavis-generalis-triplex-in-libros-steganographicos_style-c-cipher-key.html).
- The parallel viewers — e.g. [*Polygraphia VI*](works/prdl-24390_polygraphiae-libri-vi_parallel.html) and [*Clavis triplex*](works/prdl-70281_clavis-generalis-triplex-in-libros-steganographicos_parallel.html) — keep the Latin OCR beside the English throughout.
