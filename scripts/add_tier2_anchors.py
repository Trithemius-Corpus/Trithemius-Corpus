"""Phase 2b' — append a small, high-confidence Tier-2 patristic anchor batch.

CURATION.md notes that bulk web-fetching of clean aligned patristic Latin
is impractical (PDFs / scans / paywalls) and that "~15-30 register-relevant
pairs per cluster is sufficient". This adds a *curated* set of the most
canonical, oft-quoted monastic/pastoral/Marian sententiae — passages whose
Latin and a public-domain English are both stable and verifiable — rather
than risk noisy machine-aligned pairs. Quality over volume.

Idempotent: skips any record whose id is already present. Run:
    python scripts/add_tier2_anchors.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANCHORS = ROOT / "data" / "anchors"

# All authors pre-1300; all English translations pre-1929 (public domain).
RECORDS = [
    # ---- monastic-reform: Rule of St Benedict (Gasquet 1909, PD) ----
    {
        "id": "rb-prol-1", "cluster": "monastic-reform",
        "work": "Rule of St Benedict, Prologue", "section": "RB Prol. 1",
        "latin": "Obsculta, o fili, praecepta magistri, et inclina aurem cordis tui, et admonitionem pii patris libenter excipe et efficaciter comple.",
        "english": "Hearken, O my son, to the precepts of thy master, and incline the ear of thine heart; willingly receive and faithfully fulfil the admonition of thy loving father.",
        "latin_source": {"edition": "Regula S. Benedicti, Migne PL 66", "url": "https://www.thelatinlibrary.com/benedict.html", "public_domain": True, "public_domain_basis": "Benedict d. 547; text public domain"},
        "english_source": {"translator": "Francis Aidan Gasquet", "edition": "The Rule of St Benedict (London: Chatto & Windus, 1909)", "url": "https://www.ccel.org/ccel/benedict/rule.html", "public_domain": True, "public_domain_basis": "Gasquet 1909, > 95 years old"},
    },
    {
        "id": "rb-5-1", "cluster": "monastic-reform",
        "work": "Rule of St Benedict, ch. 5 (On Obedience)", "section": "RB 5.1",
        "latin": "Primus humilitatis gradus est oboedientia sine mora. Haec convenit his qui nihil sibi a Christo carius aliquid existimant.",
        "english": "The first degree of humility is obedience without delay. This becometh those who hold nothing dearer to them than Christ.",
        "latin_source": {"edition": "Regula S. Benedicti, Migne PL 66", "url": "https://www.thelatinlibrary.com/benedict.html", "public_domain": True, "public_domain_basis": "Benedict d. 547; text public domain"},
        "english_source": {"translator": "Francis Aidan Gasquet", "edition": "The Rule of St Benedict (London: Chatto & Windus, 1909)", "url": "https://www.ccel.org/ccel/benedict/rule.html", "public_domain": True, "public_domain_basis": "Gasquet 1909, > 95 years old"},
    },
    {
        "id": "rb-7-humility", "cluster": "monastic-reform",
        "work": "Rule of St Benedict, ch. 7 (On Humility)", "section": "RB 7",
        "latin": "Si volumus summae humilitatis culmen attingere et ad exaltationem illam caelestem ad quam per praesentis vitae humilitatem ascenditur volumus velociter pervenire, actibus nostris ascendentibus scala illa erigenda est.",
        "english": "If we wish to reach the summit of the highest humility, and speedily to attain that heavenly exaltation to which we ascend by the humility of the present life, we must by our ascending actions set up that ladder.",
        "latin_source": {"edition": "Regula S. Benedicti, Migne PL 66", "url": "https://www.thelatinlibrary.com/benedict.html", "public_domain": True, "public_domain_basis": "Benedict d. 547; text public domain"},
        "english_source": {"translator": "Francis Aidan Gasquet", "edition": "The Rule of St Benedict (London: Chatto & Windus, 1909)", "url": "https://www.ccel.org/ccel/benedict/rule.html", "public_domain": True, "public_domain_basis": "Gasquet 1909, > 95 years old"},
    },
    # ---- sacerdotal: Gregory the Great, Regula Pastoralis (Barmby 1895, PD) ----
    {
        "id": "gregory-rp-1-1", "cluster": "sacerdotal",
        "work": "Gregory the Great, Regula Pastoralis I.1", "section": "Reg. Past. I.1",
        "latin": "Nulla ars doceri praesumitur, nisi intenta prius meditatione discatur. Ab imperitis ergo pastorale magisterium qua temeritate suscipitur, quando ars est artium regimen animarum?",
        "english": "No one presumes to teach an art till he has first, with intent meditation, learned it. What rashness is it, then, for the unskilful to assume pastoral authority, since the government of souls is the art of arts!",
        "latin_source": {"edition": "Migne, Patrologia Latina 77 (Regula Pastoralis)", "url": "https://www.augustinus.it/latino/regola_pastorale/", "public_domain": True, "public_domain_basis": "Gregory d. 604; Migne PL pub. 1849, > 95 years old"},
        "english_source": {"translator": "James Barmby", "edition": "NPNF Series II, vol. XII (1895)", "url": "https://www.newadvent.org/fathers/3601.htm", "public_domain": True, "public_domain_basis": "Barmby 1895, > 95 years old"},
    },
    {
        "id": "gregory-rp-2-1", "cluster": "sacerdotal",
        "work": "Gregory the Great, Regula Pastoralis II.1", "section": "Reg. Past. II.1",
        "latin": "Sit rector bene agentibus per humilitatem socius, contra delinquentium vitia per zelum iustitiae erectus, ut et bonis nihil sibi praeferat, et cum pravorum culpa exigit, potestatem prioritatis agnoscat.",
        "english": "Let the ruler be, through humility, a companion of those who live well, and, through the zeal of righteousness, rigid against the vices of evil-doers; so that in nothing he prefer himself to the good, and yet, when the fault of the bad requires it, he be at once conscious of the power of his priority.",
        "latin_source": {"edition": "Migne, Patrologia Latina 77 (Regula Pastoralis)", "url": "https://www.augustinus.it/latino/regola_pastorale/", "public_domain": True, "public_domain_basis": "Gregory d. 604; Migne PL pub. 1849, > 95 years old"},
        "english_source": {"translator": "James Barmby", "edition": "NPNF Series II, vol. XII (1895)", "url": "https://www.newadvent.org/fathers/3601.htm", "public_domain": True, "public_domain_basis": "Barmby 1895, > 95 years old"},
    },
    # ---- devotional: Bernard, De Diligendo Deo (Gardner 1916, PD) ----
    {
        "id": "bernard-ddd-1", "cluster": "devotional",
        "work": "Bernard of Clairvaux, De Diligendo Deo I.1", "section": "De Dil. Deo I.1",
        "latin": "Causa diligendi Deum, Deus est; modus, sine modo diligere. Vultis ergo a me audire quare et quomodo diligendus sit Deus? Et ego: Causa diligendi Deum, Deus est.",
        "english": "The cause of loving God is God Himself; the measure, to love Him without measure. Do you wish, then, to hear from me why and in what manner God should be loved? I answer: the cause of loving God is God Himself.",
        "latin_source": {"edition": "Migne, Patrologia Latina 182 (De Diligendo Deo)", "url": "https://www.binetti.ru/bernardus/", "public_domain": True, "public_domain_basis": "Bernard d. 1153; Migne PL pub. 1854, > 95 years old"},
        "english_source": {"translator": "Edmund G. Gardner", "edition": "Saint Bernard on the Love of God (London: Dent, 1916)", "url": "https://www.ccel.org/ccel/bernard/loving_god.html", "public_domain": True, "public_domain_basis": "Gardner 1916, > 95 years old"},
    },
    # ---- marian-hagiographic: Bernard, Super Missus Est (Eales 1895, PD) ----
    {
        "id": "bernard-missus-est-2-17", "cluster": "marian-hagiographic",
        "work": "Bernard of Clairvaux, Homiliae super Missus Est II.17", "section": "Super Missus Est II.17",
        "latin": "Respice stellam, voca Mariam. Ipsam sequens non devias, ipsam rogans non desperas, ipsam cogitans non erras. Ipsa tenente non corruis, ipsa protegente non metuis, ipsa duce non fatigaris, ipsa propitia pervenis.",
        "english": "Look at the star, call upon Mary. Following her thou wilt not go astray; praying to her thou wilt not despair; thinking of her thou wilt not err. While she holds thee thou wilt not fall; while she protects thee thou wilt not fear; while she leads thee thou wilt not be weary; by her favour thou wilt reach the goal.",
        "latin_source": {"edition": "Migne, Patrologia Latina 183 (Homiliae super Missus Est)", "url": "https://www.binetti.ru/bernardus/", "public_domain": True, "public_domain_basis": "Bernard d. 1153; Migne PL pub. 1854, > 95 years old"},
        "english_source": {"translator": "Samuel J. Eales", "edition": "St Bernard's Sermons on the Blessed Virgin Mary (London: Stock, 1895)", "url": "https://archive.org/details/stbernardssermon00bern", "public_domain": True, "public_domain_basis": "Eales 1895, > 95 years old"},
    },
]


def main() -> int:
    by_cluster: dict[str, list[dict]] = {}
    for r in RECORDS:
        by_cluster.setdefault(r["cluster"], []).append(r)

    total_added = 0
    for cluster, recs in by_cluster.items():
        path = ANCHORS / f"{cluster}.jsonl"
        existing_ids = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    existing_ids.add(json.loads(line).get("id"))
        new = [r for r in recs if r["id"] not in existing_ids]
        if not new:
            print(f"{cluster}: all {len(recs)} already present")
            continue
        with path.open("a", encoding="utf-8") as fh:
            for r in new:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        total_added += len(new)
        print(f"{cluster}: +{len(new)} (now {len(existing_ids) + len(new)})")
    print(f"total added: {total_added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
