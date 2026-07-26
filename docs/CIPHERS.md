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

The rendered chunks show the full anatomy of one concealment: the *Alphabetum* (the substitution table); the *Intentio Mysterij*, the secret message in early-modern German — in one example, *"Ich bittedich komm von stund an zu mir/ es thut sehr noth"* ("I beg you, come to me at once; the need is great"); the *Literae significantes*, the bare ciphertext letters; and the *Exemplum*, the Latin cover prose that carries them, opening *"Creator genyri humani apice Deus…"* (OCR scannos preserved as they appear in the scan).

What of the angels? The *Steganographia*'s instructions are framed as conjurations of spirits — Pamersiel, Padiel, Camuel, Aseliel and dozens more — and strings like *Camuel aperoys, melym mevomanial, casmoyn cralty bufaco aeli lumar photirion theor besamys* are not Latin and not nonsense: they are constructed cipher cover-text. Trithemius framed his cipher schemes in spirit-conjuration language for cover, and the *Clavis* is the antidote he supplied, demonstrating that the "spirit names" resolve into a cryptographic system, not a magical one. This corpus accordingly preserves the magical surface verbatim — spirit names unanglicized, conjuration formulae quoted rather than translated — without glossing over the cryptographic substrate or treating the angels as the real subject. That framing nonetheless cost the book dearly: printed posthumously in 1606, the *Steganographia* was placed on the *Index Librorum Prohibitorum*.

## Solved: the *Clavis* ciphers decoded

The breakthrough was identifying that the *Clavis* cipher is **not a uniform Caesar shift** (which is why brute-force over all 24 shifts scored no better than chance). Each *modus* prints its own **explicit, irregular substitution alphabet**, and the ciphertext is decoded by inverting that alphabet letter by letter. The alphabets are roughly −N on Trithemius's 24-letter alphabet, but irregular enough that the printed *Alphabetum* itself — not a shift rule — is the key. A hand-check on the opening of Modus II confirms it: the cipher stream `gafzgbc…` maps g→i, a→c, f→h, z→b → **"Ich b[…ittedich]"** ("I beg you…").

**The simple *modi* (five worked examples) are solved** — their German plaintext recovered and recognisable:

| Modus | Facsimile page | Match | Recovered plaintext (excerpt) |
|---|---|---|---|
| XI | 263 | 77% | *diese bucher behal[t]… die heimlich* |
| X | 261 | 75% | *die sachsen [ver]sam[m]elen ein gros [vol]ck…* |
| V | 254 | 65% | *der p[farr]her[z] von bing ist vmb eins…* |
| VI | 255 | 62% | *mor[gen] vmb se[y] gerust vnd wart meiner…* |
| II | 251 | 62% | *ich bi[tte] dich kom[m] von st[und] an…* |

The decodes are **letter-for-letter through the printed alphabet** — no guessing. Each recovered plaintext is an ordinary early-modern German sentence (a request to come at once, a report of Saxon musters, a note about keeping books secret), confirming that the *Steganographia*'s "spirit names" and "angelic conjurations" are cover for mundane correspondence, exactly as Trithemius's *Clavis* was designed to demonstrate. The full **char-aligned decodes** — with each cipher letter mapped to its plaintext letter, match shown green and OCR-drift shown red, beside the facsimile crop of the cipher line — are in the [cipher solutions page](cipher-solutions.html).

### Honest scope of the solve

Two limits remain, and they are stated plainly:

- **The residual gap is OCR, not the cipher.** The cipher lines are tiny, period-separated Fraktur letters in 1608 print — at the ceiling of current vision OCR — so a few letters per line drift. The German is recovered and recognisable (62–77% character match on the simple *modi*, 70–92% on the high *modi*), but not a perfect transcription. The high-*modus* cipher lines in particular were beyond vision OCR and were recovered by **human eye-reading** of zoomed facsimile crops against a Fraktur reference key — the one step in the pipeline a machine could not do.
- **The full range of *modi* present in the facsimile is solved — simple (II–XI) and high (XXXII–XXXIX) alike.** The high *modi* use the *same* explicit-alphabet inversion as the simple ones; their "alternating words / null rhythm" rule-language describes only how the cipher *stream* was extracted from the cover letter, not a different decryption. Six high *modi* now decode end-to-end:

| Modus | Facsimile page | Alphabet shift | Match | Recovered plaintext (excerpt) |
|---|---|---|---|---|
| XXXVII | 243 | +18 | 92% | *Jacob Seum hat nun gesprochen, er will dich erstechen… hüt dich vor ihm* |
| XXXIII | 238 | +14 | 89% | *er ist noch new, versuch ihn vor gantz wol… er trinket auch gern Wein* |
| XXXV | 241 | +16 | 87% | *Der Abt von S. Johannes Berg helt Communia… vnd fehret auch im Narrenschiff* |
| XXXVIII | 244 | +19 | 86% | *Wisse das Hans Schwerd viel übel von dir red… nimpt sich doch an für dich* |
| XXXII | 237 | +13 | 78% | *noch… vmb Vhr… du mich an dem Wald… pfeiffen mit einem Schlüssel… kom herab* |
| XXXIX | 245 | +20 | 70% | *Dir wird geschrieben herzu kommen, ist mein Rath… der Anschlag ist dich zuvertrencken* |

Each is an ordinary early-modern German sentence — a warning of a planned stabbing (XXXVII), a character reference for a drinker (XXXIII), a report of an absent abbot (XXXV), a slander warning (XXXVIII), a signal by a woodsman's whistle (XXXII), a counsel to stay away (XXXIX). The "angelic" frame dissolves entirely: these are mundane letters about money, drink, and danger, hidden in Latin cover prose. The high-*modus* decodes were cracked by inverting each *modus*'s printed *Alphabetum* table against a **human-transcribed** cipher line — the dense Fraktur Literae stream being the one input vision OCR could not supply.

For the published *translations* of these works, the cryptographic substitutions are still **passed through as written** — the cipher streams in the body text are transcribed, not decoded inline. The [executable cipher edition](cipher-solutions.html) now traces Modus II from the printed page through a committed transcription and explicit-alphabet inversion. It keeps the imperfect computed output separate from the printed *Intentio*, labels evidence, repair, and inference, and supplies JSON and TSV downloads so the result can be recomputed without the website. For the comprehensive modern English edition of the *Steganographia* and its angelological framing, see Skinner & Clark (2024); for the foundational cryptanalysis, Ernst (1996) and Reeds (1998), who independently solved Book III.

## Explore the cipher materials in this corpus

- [**Executable cipher edition** — Modus II, step by step](cipher-solutions.html) — a reproducible worked example with facsimile evidence, explicit editorial status, keyboard-operable navigation, substitution table, plain-text account, and downloadable data.
- [Substitution tables (*Polygraphia VI*, cipher-key renderings)](works/prdl-24390_polygraphiae-libri-vi_style-c-cipher-key.html) — the "Ave Maria" alphabets, rendered alphabet-down / columns-across beside the source facsimile.
- [Rotation figures and the *Orchema numerale* (cipher-grid renderings)](works/prdl-24389_polygraphiae-libri-sex-ioannis-trithemii-abbatis_style-c-cipher-grid.html) — the *tabula recta* family, with facsimiles wherever the OCR collapsed the figure.
- [Worked steganographic examples (*Clavis Steganographiae*)](works/prdl-70281_clavis-generalis-triplex-in-libros-steganographicos_style-c-untranslated.html) — freshly translated passages from the triple key; the letter-pair claves themselves are on the [cipher-key page](works/prdl-70281_clavis-generalis-triplex-in-libros-steganographicos_style-c-cipher-key.html).
- The parallel viewers — e.g. [*Polygraphia VI*](works/prdl-24390_polygraphiae-libri-vi_parallel.html) and [*Clavis triplex*](works/prdl-70281_clavis-generalis-triplex-in-libros-steganographicos_parallel.html) — keep the Latin OCR beside the English throughout.
