"""Build the V2 Latin->English training set (~50K pairs) from three sources:

  1. grosenthal/latin_english_parallel (HF) — classical Latin, ~66K non-Bible pairs
  2. Vulgate<->DRB (on disk)              — biblical Latin, ~31K verse pairs
  3. Rule of St. Benedict (Latin Library + Project Gutenberg) — monastic canonical Latin

Output: training_v2.jsonl in the V1 text-only schema:
  {source_id, chunk, latin_ocr, english_translation, adj_faith, adj_fluent, source_file}

adj_faith/adj_fluent are set to 5.0 for clean parallel pairs (no grader run).
"""
import json, os, re, random, html
from pathlib import Path

random.seed(20260704)

OUT = Path("E:/trithemius-corpus/training_v2.jsonl")
GROSENTHAL = Path("E:/trithemius/data/grosenthal_latin_english/data/train-00000-of-00001-9b65fddb561aafc9.parquet")
VULGATE = Path("E:/trithemius/data/biblia/parallel.jsonl")
BENEDICT_LA = Path("E:/trithemius/data/benedict/regula_la.html")
BENEDICT_EN = Path("E:/trithemius/data/benedict/regula_en.txt")

TARGET_TOTAL = 50000
TARGET_BENEDICT = "all"      # small corpus, take every pair
TARGET_VULGATE = 15000
TARGET_CLASSICAL = TARGET_TOTAL - TARGET_VULGATE  # benedict is small, classical fills rest

pairs = []  # list of dicts

def add_pair(src_id, latin, english, src_file, chunk=0):
    latin = latin.strip()
    english = english.strip()
    if len(latin) < 20 or len(english) < 20:
        return
    # reject if english looks like latin (no latin words leaked into target)
    if not re.search(r'\b(the|and|of|to|a|in|is|that|he|for|with|was|his|be|it|from|by|but|not|this|they|are|or|on|at|as|have|you|which)\b',
                     english, re.I):
        return
    pairs.append({
        "source_id": src_id,
        "chunk": chunk,
        "latin_ocr": latin,
        "english_translation": english,
        "adj_faith": 5.0,
        "adj_fluent": 5.0,
        "source_file": src_file,
    })

# ---------- 1. grosenthal classical (drop vulgate subset to avoid double-bible) ----------
import pyarrow.parquet as pq
df = pq.read_table(GROSENTHAL).to_pandas()
# clean + dedup
df = df[(df['la'].str.len() >= 20) & (df['en'].str.len() >= 20)]
df = df.drop_duplicates(subset='la')
classical = df[~df['file'].astype(str).str.contains('Vulgate', na=False)].copy()
# oversample patristic/medieval works (Bede, Gregory, Augustine, Jerome) — they're closer to Trithemius register
patristic_re = re.compile(r'Bede|Gregory|Augustine|Jerome|Benedict|Sulpicius|Eusebius|Gregory|Tertullian|Cyprian|Ambrose|Hilary|Lactantius|Minucius', re.I)
patristic = classical[classical['file'].str.contains(patristic_re, na=False)]
other = classical[~classical['file'].str.contains(patristic_re, na=False)]
print(f"grosenthal: {len(classical)} classical ({len(patristic)} patristic, {len(other)} other)")

# take ALL patristic (it's high-value for register match), then sample the rest
n_classical_needed = TARGET_CLASSICAL
patristic_sample = patristic.sample(n=min(len(patristic), n_classical_needed // 3), random_state=20260704)
remaining_needed = n_classical_needed - len(patristic_sample)
other_sample = other.sample(n=min(len(other), remaining_needed), random_state=20260704)
classical_sample = patristic_sample['_orig'] = None  # placeholder
classical_chosen = list(patristic_sample.index) + list(other_sample.index)
print(f"  taking {len(patristic_sample)} patristic + {len(other_sample)} other classical = {len(classical_chosen)}")

for idx in classical_chosen:
    row = classical.loc[idx]
    add_pair("grosenthal-classical", row['la'], row['en'],
             os.path.basename(row['file']).replace('.json',''))

# ---------- 2. Vulgate (on-disk) ----------
vulgate_pairs = []
for line in open(VULGATE, encoding='utf-8'):
    line = line.strip()
    if not line: continue
    d = json.loads(line)
    add_pair("vulgate-drb", d['latin'], d['english'], f"Vulgate_{d['ref']}")
# the above added all; subsample to TARGET_VULGATE
vulgate_added = [p for p in pairs if p['source_id'] == 'vulgate-drb']
if len(vulgate_added) > TARGET_VULGATE:
    keep = set(id(p) for p in random.sample(vulgate_added, TARGET_VULGATE))
    pairs = [p for p in pairs if p['source_id'] != 'vulgate-drb' or id(p) in keep]
print(f"vulgate: added {min(len(vulgate_added), TARGET_VULGATE)} (of {len(vulgate_added)} available)")

# ---------- 3. Rule of St. Benedict ----------
# Parse Latin from thelatinlibrary HTML
la_html = open(BENEDICT_LA, encoding='utf-8', errors='replace').read()
# strip HTML entities to chars
la_html_clean = html.unescape(la_html)
# extract text in <p>...</p> blocks, drop tags
la_paras = re.findall(r'<p[^>]*>(.*?)</p>', la_html_clean, re.S | re.I)
la_paras = [re.sub(r'<[^>]+>', ' ', p) for p in la_paras]
la_paras = [re.sub(r'\s+', ' ', p).strip() for p in la_paras]
la_paras = [p for p in la_paras if len(p) > 40]
print(f"benedict latin: {len(la_paras)} paragraphs")

# Parse English from Project Gutenberg plain text
en_text = open(BENEDICT_EN, encoding='utf-8', errors='replace').read()
# strip PG header/footer
m = re.search(r'\*\*\* START OF.*?\*\*\*(.*?)\*\*\* END OF', en_text, re.S | re.I)
if m:
    en_body = m.group(1)
else:
    en_body = en_text
# split into paragraphs (blank-line separated); keep CHAPTER headers as their own paras
en_paras = []
for raw in en_body.split('\n\n'):
    p = re.sub(r'\s+', ' ', raw).strip()
    if not p:
        continue
    # chapter headers come on their own line followed by the title — keep them so the splitter sees them
    en_paras.append(p)
print(f"benedict english: {len(en_paras)} paragraphs")

# Pairing strategy: Benedict is hard to align paragraph-by-paragraph across two different editions.
# Safer approach: pair at the chapter level — find chapter boundaries in each and concatenate.
# Both texts use chapter numbers. We'll find "Caput" / "Chapter" markers.
def split_by_chapter_latin(paras):
    """Latin Library uses 'Caput <num>:' short header paragraphs."""
    chapters = {}
    cur_num = 0  # 0 = prologue
    cur_buf = []
    for p in paras:
        m = re.match(r'^Caput\s+(\d+)', p, re.I)
        if m:
            if cur_buf:
                chapters[cur_num] = ' '.join(cur_buf)
            cur_num = int(m.group(1))
            cur_buf = []
        elif p.lower().startswith('incipit prologus') or p.lower() == 'prologus':
            if cur_buf:
                chapters[cur_num] = ' '.join(cur_buf)
            cur_num = 0
            cur_buf = []
        else:
            cur_buf.append(p)
    if cur_buf:
        chapters[cur_num] = ' '.join(cur_buf)
    return chapters

def split_by_chapter_english(paras):
    """Project Gutenberg uses 'CHAPTER <num>' headers (on their own paragraph)."""
    chapters = {}
    cur_num = -1
    cur_buf = []
    for p in paras:
        m = re.match(r'^CHAPTER\s+(\d+)', p, re.I)
        if m:
            if cur_num >= 0 and cur_buf:
                chapters[cur_num] = ' '.join(cur_buf)
            cur_num = int(m.group(1))
            cur_buf = []
        elif re.match(r'^PROLOGUE', p, re.I):
            if cur_num >= 0 and cur_buf:
                chapters[cur_num] = ' '.join(cur_buf)
            cur_num = 0
            cur_buf = []
        elif cur_num >= 0:
            cur_buf.append(p)
    if cur_num >= 0 and cur_buf:
        chapters[cur_num] = ' '.join(cur_buf)
    return chapters

def roman_to_int(s):
    vals = {'i':1,'v':5,'x':10,'l':50,'c':100,'d':500,'m':1000}
    total, prev = 0, 0
    for c in reversed(s.lower()):
        v = vals.get(c, 0)
        total += v if v >= prev else -v
        prev = v
    return total

la_chapters = split_by_chapter_latin(la_paras)
en_chapters = split_by_chapter_english(en_paras)
print(f"benedict latin chapters: {sorted(la_chapters.keys())[:5]}...{sorted(la_chapters.keys())[-3:] if la_chapters else 'none'}")
print(f"benedict english chapters: {sorted(en_chapters.keys())[:5]}...{sorted(en_chapters.keys())[-3:] if en_chapters else 'none'}")

# pair by chapter number. Sentence-level pairing across two different editions is
# unreliable (chapter 4 alone has ~90 list items; off-by-one pairing produces
# garbage), so we keep each chapter as ONE training pair. The LoRA learns the
# canonical register/vocabulary from chapter-level exposure, which is the goal.
# Drop chapters where the Latin Library edition and the Project Gutenberg
# edition diverge sharply in length (ratio outside 0.33-3.0) — those are
# different chapter numberings across editions and would mislead training.
common_chapters = sorted(set(la_chapters) & set(en_chapters))
benedict_count = 0
benedict_dropped = 0
for ch in common_chapters:
    la = la_chapters[ch]
    en = en_chapters[ch]
    if len(la) < 40 or len(en) < 40:
        continue
    ratio = len(la) / max(len(en), 1)
    if not (0.33 <= ratio <= 3.0):
        benedict_dropped += 1
        continue
    add_pair(f"benedict-ch{ch:02d}", la, en, f"Benedict_ch{ch:02d}", chunk=ch)
    benedict_count += 1

print(f"benedict: added {benedict_count} pairs across {len(common_chapters)} chapters "
      f"({benedict_dropped} dropped for bad cross-edition length ratio)")

# ---------- write ----------
random.shuffle(pairs)
with open(OUT, 'w', encoding='utf-8') as f:
    for p in pairs:
        f.write(json.dumps(p, ensure_ascii=False) + '\n')

print(f"\n=== WROTE {len(pairs)} pairs to {OUT} ({OUT.stat().st_size/1024/1024:.1f} MB) ===")
# breakdown
from collections import Counter
sources = Counter(p['source_id'] for p in pairs)
for s, n in sources.most_common():
    print(f"  {s:30s} {n:6d}")
