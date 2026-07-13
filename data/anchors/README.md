# Retrieval anchors — per-genre PD Latin/English parallel corpora

This directory holds the curated public-domain Latin/English parallel snippet corpora used to seed the retrieval-augmented few-shot translation index. See [`METHODOLOGY.md §5.2`](../../METHODOLOGY.md) and [`cluster_mapping.json`](../../cluster_mapping.json).

## Layout

One JSONL file per cluster:

```
data/anchors/
├── crypto-occult.jsonl
├── bibliographic.jsonl
├── monastic-reform.jsonl
├── sacerdotal.jsonl
├── marian-hagiographic.jsonl
├── devotional.jsonl
├── apologetic.jsonl
└── verse.jsonl
```

## Pair schema

Each line is one JSON object — one parallel passage:

```jsonc
{
  "id": "cassian-inst-iv-1",                      // stable string ID
  "cluster": "monastic-reform",                   // cluster ID (must match dir filename)
  "work": "Cassian, De Institutis Coenobiorum",   // citation: work
  "section": "Book IV, ch. 1",                    // citation: locus
  "latin": "Quae moderationis virtus...",         // ≤ 1500 chars, clean transcription
  "english": "The moderation that ought to...",   // ≤ 1500 chars, matched translation
  "latin_source": {
    "edition": "Migne PL 49, col. 154",           // Latin source edition
    "url": "https://...",                          // optional public URL
    "public_domain": true                          // affirmation
  },
  "english_source": {
    "translator": "Edgar C. S. Gibson",
    "edition": "NPNF Series II, vol. XI (1894)",
    "url": "https://ccel.org/...",
    "public_domain": true,                         // affirmation
    "public_domain_basis": "published 1894, > 95 years old"
  }
}
```

## Target volumes per cluster

A useful retrieval index typically needs at least ~15-25 representative pairs per cluster. Larger is better up to a point — the index doesn't need to be exhaustive, it just needs to span the register-vocabulary space of the cluster.

| Cluster | Target pairs | Notes |
|---|---|---|
| `crypto-occult` | 25 | Hardest cluster; PD English of hermetic Latin is genuinely thin |
| `bibliographic` | 20 | Jerome's *De Viris Illustribus* alone gives ~30 entries; mine the catalog form |
| `monastic-reform` | 30 | Largest cluster (11 works); Cassian + Athanasius + Benedict together |
| `sacerdotal` | 20 | Gregory's *Regulae Pastoralis* is rich in pastoral idiom |
| `marian-hagiographic` | 25 | Bernard's Marian sermons + Anselm; high-register hymnic Latin |
| `devotional` | 20 | Bernard + Augustine + Imitatio Christi |
| `apologetic` | 15 | Augustine *Retractationes* + Jerome's apologetic letters |
| `verse` | 10 | Smallest cluster; metric/satirical register; harder to curate |

## License affirmation rule

Every pair carries an explicit `public_domain: true` field in **both** the `latin_source` and `english_source` blocks. The build script (`scripts/build_anchor_index.py`, Phase 2c) refuses to index any pair where either field is missing or false. This is the technical enforcement of the v2 policy in METHODOLOGY §5.2.

## Adding new pairs

1. Identify a PD source — typically NPNF, ANF, or pre-1929 published English with the Latin available in Migne PL or a comparable PD edition.
2. Verify the PD status — usually a pub date ≥ 95 years old; for US-published works, anything before 1929 is now PD.
3. Extract a Latin passage and the matched English (paragraph-level granularity is fine; ≤ 1500 chars per side keeps the prompt budget under control).
4. Append to the cluster's `.jsonl` with the schema above.
5. The retrieval index rebuilds automatically on the next translation run.

## Curation workflow tasks

See task #8 in the project tracker. Phase 2b is the labor-intensive curation pass; Phase 2c wires the cluster-aware index into the harness; Phase 2d is the re-translation; Phase 2e is the re-grading.
