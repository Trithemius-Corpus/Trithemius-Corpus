# Anchor curation plan and progress

Progress, target volumes, and sources for the per-cluster public-domain anchor sets.

## Status

| Cluster | Target | Current | % done | Status |
|---|---|---|---|---|
| `monastic-reform` | 30 | 13 | 43 % | starter + RB (Gasquet 1909) |
| `crypto-occult` | 25 | 10 | 40 % | starter (Vulgate+DR) |
| `marian-hagiographic` | 25 | 11 | 44 % | starter + Bernard *Super Missus Est* (Eales 1895) |
| `bibliographic` | 20 | 10 | 50 % | starter (Vulgate+DR) |
| `sacerdotal` | 20 | 12 | 60 % | starter + Gregory *Reg. Past.* (Barmby 1895) |
| `devotional` | 20 | 15 | 75 % | starter + Augustine *Confessions* (Pusey 1838) + Bernard *De Diligendo Deo* (Gardner 1916) |
| `apologetic` | 15 | 10 | 67 % | starter (Vulgate+DR) |
| `verse` | 10 | 10 | 100 % | starter (Vulgate+DR) |
| **Total** | **165** | **87** | **53 %** | starter + Tier-2 batch |

**Starter pass complete** as of 2026-05-14 — every cluster has 10 register-relevant Vulgate+DR pairs sufficient to unblock Phase 2c-2d.

**Tier-2 batch added 2026-05-16** (`scripts/add_tier2_anchors.py`) — 7 curated high-confidence patristic/monastic *sententiae* (Rule of St Benedict, Gregory the Great's *Regula Pastoralis*, Bernard's *De Diligendo Deo* and *Super Missus Est*), each a canonical passage with a public-domain Latin source and a pre-1929 public-domain English. Quality-over-volume per the note below; further Cassian/Jerome expansion remains optional for a future v3.

**Note on Tier-2 fetching:** real-time WebFetch curation of patristic Latin sources hit practical friction in initial attempts — clean plain-text Latin for Cassian's *Institutes* and similar works is either behind large PDFs (Documenta Catholica Omnia), scanned manuscript page images (university digital libraries), or paywalled scholarly editions. The right Phase 2b' approach is a batch-fetch script that pulls from specific known-good PD URLs (CCEL plain-text for NPNF English, archive.org plaintext views for Migne PL Latin) and produces candidate pairs for spot-check. Deferred until after v2 ships. The 4 Augustine *Confessions* pairs added 2026-05-14 to `devotional.jsonl` are a small high-confidence batch from canonical passages with verifiable Migne PL / Pusey 1838 citations.

## Strategy

The retrieval index does not need exhaustive coverage of each PD source to be useful — ~15-30 register-representative pairs per cluster is sufficient. The pipeline can run v2 re-translations with any non-empty cluster index.

**Tier 1 sources (always include in every cluster).** Vulgate (Latin, Clementine 1592/1598) + Douay-Rheims (English, Challoner 1899) for register-relevant scripture. Trithemius quotes the Vulgate constantly, so scriptural anchors lift translation quality across the whole corpus regardless of cluster register. Roughly 8-10 Vulgate+DR pairs per cluster, chosen for cluster-register relevance.

**Tier 2 sources (cluster-specific).** Patristic and early-modern works cited in `cluster_mapping.json`. These provide the cluster-specific register vocabulary that scripture alone doesn't supply.

## Per-cluster source URLs

### crypto-occult

- **Henry Cornelius Agrippa, *Three Books of Occult Philosophy*** (JF tr., London 1651). PD. English at https://www.esotericarchives.com/agrippa/agrippa1.htm and similar.
- **William Lilly, *Of the Seven Secondary Causes* / *De Septem Secundeis*** (London 1647). PD. Latin from Trithemius's own 1508 edition (PD, BSB scan) + Lilly's 1647 English.
- **G.R.S. Mead, *Thrice-Greatest Hermes*** (Theosophical Publishing Society, 1906). PD. Hermetica at https://www.gnosis.org/library/grs-mead/TGH/index.htm
- **Vulgate (Daniel, Acts 19, Exodus 7-8)** — scriptural passages on dreams, prophecy, and the magicians of Pharaoh; relevant to angelological/conjuration register.

### bibliographic

- **Jerome, *De Viris Illustribus*** (tr. Ernest Cushing Richardson, NPNF Series II vol. III, 1892). PD. English at https://www.newadvent.org/fathers/2708.htm
- **Gennadius of Marseille, *De Viris Illustribus*** (continuation; tr. Richardson, NPNF Series II vol. III, 1892). PD. https://www.newadvent.org/fathers/2710.htm
- **Bede, *Historia Ecclesiastica Gentis Anglorum*** (tr. A. M. Sellar, London 1907). PD.
- **Vulgate (2 Maccabees 2:13, Sirach prologue, Ecclesiastes 12:12)** — passages on the collection and writing of books.

### monastic-reform

- **Vulgate** (humility, obedience, mortification, the cross) — **10 pairs already curated** (see `monastic-reform.jsonl`).
- **John Cassian, *De Institutis Coenobiorum*** (English tr. Edgar Gibson, NPNF Series II vol. XI, 1894). PD. https://www.newadvent.org/fathers/3507.htm . Latin in Migne PL 49 (PD) / CSEL 17 Petschenig 1888 (PD); need to source plain-text Latin.
- **John Cassian, *Collationes Patrum*** (Conferences; same NPNF volume).
- **Athanasius, *Vita Antonii*** (Evagrius's Latin tr. + NPNF English tr. Robertson 1892, Series II vol. IV). PD.
- **Sulpitius Severus, *Vita Sancti Martini*** (Latin + NPNF English tr. Roberts, Series II vol. XI). PD.
- **Rule of St. Benedict** — Latin from `archive.osb.org/rb/` or thelatinlibrary.com; PD English from pre-1929 editions (Schuster 1908 or Washbourne 1875).

### sacerdotal

- **Gregory the Great, *Liber Regulae Pastoralis*** (tr. James Barmby, NPNF Series II vol. XII, 1895). PD. https://www.newadvent.org/fathers/3601.htm
- **Augustine, *De Doctrina Christiana*** (tr. J. F. Shaw, NPNF Series I vol. II, 1887). PD. https://www.newadvent.org/fathers/1202.htm
- **Vulgate (1 Timothy 3, Titus 1, Hebrews 5)** — qualifications and duties of priests/bishops.

### marian-hagiographic

- **Bernard of Clairvaux, *Sermones in laudibus Virginis Matris*** (Latin in Migne PL 183; English tr. Samuel J. Eales, London 1895). PD.
- **Bernard of Clairvaux, *Homiliae super Missus est*** (Marian homilies). PD English available.
- **Anselm of Canterbury, *Orationes ad Sanctam Mariam*** (Prayers to Mary). Latin in Migne PL 158; pre-1929 English translations PD.
- **Vulgate (Luke 1-2, Song of Songs, Genesis 3:15)** — Marian-typological passages.

### devotional

- **Bernard of Clairvaux, *De Diligendo Deo*** (tr. Edmund G. Gardner, London 1916). PD.
- **Augustine, *Confessiones*** (tr. E. B. Pusey, London 1838). PD. Latin readily available; English at https://www.newadvent.org/fathers/1101.htm
- **Thomas à Kempis, *De Imitatione Christi*** (Whitford 1556, Stanhope 1696, Knox 1853, etc. — multiple PD English editions).
- **Vulgate (Psalm 50/51, 1 Cor 13, Phil 3)** — contrition, divine love, eschatological hope.

### apologetic

- **Augustine, *Retractationes*** (tr. unknown; portions in NPNF Series I vol. I, 1886). PD.
- **Jerome, *Adversus Rufinum*** + apologetic letters (NPNF Series II vol. III, 1892, tr. Fremantle/Lewis/Martley). PD.
- **Vulgate (Galatians 1-2, 2 Corinthians 10-13)** — Paul's self-defense as canonical register.

### verse

- **Hucbald of St. Amand, *Ecloga de Calvis*** in Thomas Wright, *Latin Poems Commonly Attributed to Walter Mapes* (Camden Society, 1841). PD. Direct generic predecessor of Trithemius's bald-men poem.
- **Erasmus, *Encomium Moriae* (Praise of Folly)** — Wilson 1668 or Kennett 1683 PD English. Renaissance Latin satirical-encomiastic register.
- **Virgil, *Eclogues*** — Dryden 1697 PD English. Eclogue form itself.
- **Vulgate (Wisdom, Lamentations)** — metric/parallelistic Latin in PD.

## Pair-extraction workflow

For each cluster:

1. **Open the cluster's primary PD English source** (URL above).
2. **Pick 15-25 representative paragraph-level passages** spanning the register (e.g. for monastic-reform: rule-giving, vice-correction, obedience exempla, prayer instruction).
3. **Find the matching Latin** in the corresponding PD edition. For NPNF translations the chapter divisions usually match Migne PL exactly.
4. **Format as JSONL** per the schema in `README.md`; include `public_domain: true` affirmation in both source blocks.
5. **Spot-check the pair** before committing: does the English actually translate the Latin? Are both indisputably PD?

## Non-blocker

A 30-pair curation per cluster is the *ideal*, not the *minimum*. The 10 Vulgate+DR pairs already in `monastic-reform.jsonl` will produce a functional retrieval index for that cluster's v2 re-translation pass. Curating the other clusters to a similar starter level (10 Vulgate+DR pairs each, 80 pairs total across all 8 clusters) unblocks Phase 2c-2d immediately; expanding to ~30 pairs per cluster from the Tier-2 sources is a quality lift that can land in a v2.1.
