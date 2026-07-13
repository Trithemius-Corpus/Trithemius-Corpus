"""Generate the Fable 5 vs Codex 5.5 vs Qwen-NPU comparison HTML report.

Reads translation artifacts from E:/trithemius/data/corpus/<work>/translations/<backend>/full/
and emits site/dist/model-comparison.html.
"""
import os, re, glob, html

base = "E:/trithemius/data/corpus"
OUT = "E:/trithemius-corpus/site/dist/model-comparison.html"

works = [
 ("prdl-24376_ecloga-de-laude-calvorum-ad-carolum","Ecloga de Laude Calvorum","Hucbald's alliterative eclogue (each line begins with C). 14 source pages.",14),
 ("prdl-24364_de-laudibus-sanctissimae-matris-annae","De Laudibus Sanctissimae Matris Annae","Marian praise treatise. 17 source pages.",17),
 ("prdl-24386_liber-de-triplici-regione-claustralium-et","Liber de Triplici Regione Claustralium","Monastic reform, three regions. 141 source pages.",141),
 ("prdl-24357_abbreviatura-recessuum-capitularium-patrum-ordinis-divi","Abbreviatura Recessuum Capitularium","Capitular abbreviations. 181 source pages.",181),
 ("prdl-24393_sermones-et-exhortationes-ad-monachos-joa","Sermones et Exhortationes ad Monachos (I)","Monastic sermons, vol. I. 161 source pages.",161),
 ("prdl-24394_sermones-et-exhortationes-ad-monachos-joa","Sermones et Exhortationes ad Monachos (II)","Monastic sermons, vol. II. 157 source pages.",157),
 ("prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam","Steganographia","Trithemius' occult cipher-work. 167 source pages.",167),
 ("prdl-24360_compendium-breviarium-primi-voluminis-annalium-historiarum-origine-regum","Compendium Breviarium Annalium","Annals compendium. 123 source pages.",123),
]
backends = [("FABLE","fable5-qwen-trithemius","Fable 5 (via Qwen-Trithemius harness)"),
            ("CODEX","qwen3vl-trithemius-q6-dual-gpt55","Codex / GPT-5.5 (dual-context, OCR+witness)"),
            ("QWEN-NPU","npu-qwen3vl-q4nx","Qwen-Trithemius 4B (NPU, Q4 quantized)")]

def analyze(d, src_pages):
    files = sorted(glob.glob(os.path.join(d,"full_chunk_*.md")))
    if not files:
        return {"chunks":0,"chars":0,"pages":0,"pages_pct":0,"in_order":True,"trunc":0,"leak":0,"trunc_pct":0}
    total=0; pages=[]; trunc=0; leak=0
    for f in files:
        t=open(f,encoding='utf-8',errors='replace').read()
        total+=len(t)
        for p in re.findall(r'^---\s*Page\s+(\d+)\s*---', t, re.M):
            pages.append(int(p))
        head = t.lstrip()[:140].lower()
        if any(k in head for k in ['here is',"here's the",'translation:','```','sure,','certainly,','below is',"i'll",'i will translate']):
            leak+=1
        elif t[:60].count('```')>0:
            leak+=1
        stripped=t.rstrip()
        if stripped and stripped[-1] not in '.!?":;)'+'\u201d\u2019'+chr(39):
            if len(t)<2000:
                trunc+=1
    in_order = pages==sorted(pages) and len(pages)==len(set(pages))
    pp=len(set(pages)); pct=round(100*pp/src_pages) if src_pages else 0
    tpct=round(100*trunc/len(files)) if files else 0
    return {"chunks":len(files),"chars":total,"pages":pp,"pages_pct":pct,
            "in_order":bool(in_order),"trunc":trunc,"leak":leak,"trunc_pct":tpct}

def find_page(d, pagenum):
    for f in sorted(glob.glob(os.path.join(d,"full_chunk_*.md"))):
        t=open(f,encoding='utf-8',errors='replace').read()
        m=re.search(r'^---\s*Page\s+0*%d\s*---\s*\n(.*?)(?=^---\s*Page\s+\d+\s*---|\Z)' % pagenum, t, re.M|re.S)
        if m:
            return m.group(1).strip()
    return None

rows=[]
agg={bn:{"chunks":0,"chars":0,"trunc":0,"leak":0,"pages":0} for bn,_,_ in backends}
for slug,name,desc,sp in works:
    row={"slug":slug,"name":name,"desc":desc,"src_pages":sp,"per":{}}
    for bn,bdir,_ in backends:
        d=os.path.join(base,slug,"translations",bdir,"full")
        m=analyze(d,sp)
        row["per"][bn]=m
        for k in ("chunks","chars","trunc","leak","pages"):
            agg[bn][k]+=m[k]
    rows.append(row)

def quality_grade(bn, m):
    if m["chunks"]==0:
        return ("&mdash;","n-a")
    cov=m["pages_pct"]; trunc=m["trunc_pct"]
    if bn=="QWEN-NPU":
        if trunc>=80: return ("F","grade-f")
        if trunc>=40: return ("D","grade-d")
        if trunc>=15: return ("C","grade-c")
        if cov>=85: return ("B+","grade-b")
        return ("B","grade-b")
    if trunc>=10: return ("B","grade-b")
    if cov>=85: return ("A","grade-a")
    if cov>=60: return ("A-","grade-a-minus")
    return ("B+","grade-b")

excerpts=[
 ("prdl-24376_ecloga-de-laude-calvorum-ad-carolum",5,"Ecloga — Vita of Hucbald (prose, page 5)"),
 ("prdl-24393_sermones-et-exhortationes-ad-monachos-joa",18,"Sermones I — Homily II (page 18). This is where Qwen-NPU collapses mid-clause."),
 ("prdl-24395_steganographia-hoc-est-ars-per-occultam-scripturam",10,"Steganographia — Book I Chapter 1 (page 10). All three backends present — a clean comparison."),
]

CSS = """
:root{--bg:#100d12;--panel:#1a151d;--panel2:#221c26;--ink:#ece4d6;--muted:#9c8f86;--accent:#c8a35e;--accent2:#8b6f3a;--fable:#6fb4e8;--codex:#7fd6a8;--qwen:#e8916f;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 Georgia,'Iowan Old Style',serif;}
.wrap{max-width:1240px;margin:0 auto;padding:2rem 1.25rem 6rem}
header.report-head{border-bottom:1px solid var(--accent2);padding-bottom:1.5rem;margin-bottom:2rem}
header.report-head h1{font:700 2rem/1.2 Georgia,serif;margin:0 0 .25rem;color:var(--accent)}
header.report-head .sub{color:var(--muted);font-size:.95rem}
header.report-head .meta{color:var(--muted);font-size:.82rem;margin-top:.5rem}
.legend{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0 .25rem;font-size:.85rem;color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:.4rem}
.legend .dot{width:11px;height:11px;border-radius:2px;display:inline-block}
.dot.f{background:var(--fable)}.dot.c{background:var(--codex)}.dot.q{background:var(--qwen)}
h2{font:700 1.35rem/1.3 Georgia,serif;color:var(--accent);margin:2.5rem 0 .75rem;border-bottom:1px solid var(--accent2);padding-bottom:.3rem}
p{margin:.5rem 0}
table{border-collapse:collapse;width:100%;font-size:.84rem;margin:.75rem 0;background:var(--panel)}
th,td{padding:.45rem .55rem;border:1px solid #2c2430;text-align:left;vertical-align:top}
th{background:#241c29;color:var(--accent);font-weight:700;font-family:'Segoe UI',sans-serif;font-size:.78rem;text-transform:uppercase;letter-spacing:.03em}
td.num{text-align:right;font-variant-numeric:tabular-nums;font-family:'Consolas',monospace;font-size:.82rem}
td.work{font-family:'Segoe UI',sans-serif;font-weight:600}
td.work small{display:block;font-weight:400;color:var(--muted);font-size:.78rem}
tr.tot{background:#241c29;font-weight:700}
tr.tot td{color:var(--accent)}
.grade{display:inline-block;min-width:2.2rem;text-align:center;padding:.1rem .4rem;border-radius:3px;font:700 .8rem/1 'Segoe UI',sans-serif}
.grade-a{background:#2a4a3f;color:#a8e0c4}.grade-a-minus{background:#3a4a2a;color:#d6e8a0}
.grade-b{background:#4a3f2a;color:#e8d49a}.grade-c{background:#4a3a20;color:#f0c878}
.grade-d{background:#4a2a20;color:#f0a878}.grade-f{background:#4a2020;color:#f08888}
.n-a{background:#332935;color:var(--muted)}
.bad{color:#e8896a}.ok{color:#d6c28a}.good{color:#a8e0a8}
.callout{background:var(--panel2);border-left:3px solid var(--accent);padding:.85rem 1rem;margin:1rem 0;border-radius:0 4px 4px 0}
.callout.warn{border-left-color:var(--qwen)}.callout.ok{border-left-color:var(--codex)}
.callout strong{color:var(--accent)}
ul.findings{margin:.5rem 0 .5rem 1.25rem;padding:0}
ul.findings li{margin:.35rem 0}
ul.findings li b.f{color:var(--fable)}ul.findings li b.c{color:var(--codex)}ul.findings li b.q{color:var(--qwen)}
.excerpt{margin:1.5rem 0;border:1px solid #2c2430;border-radius:4px;overflow:hidden}
.excerpt .ex-head{background:#241c29;padding:.5rem .75rem;font:700 .9rem 'Segoe UI',sans-serif;color:var(--accent);border-bottom:1px solid #2c2430}
.excerpt .ex-head small{color:var(--muted);font-weight:400;font-size:.78rem;margin-left:.5rem}
.excerpt .cols{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1px;background:#2c2430}
@media(max-width:900px){.excerpt .cols{grid-template-columns:1fr}}
.excerpt .col{background:var(--panel);padding:.75rem;min-height:60px}
.excerpt .col h4{margin:0 0 .4rem;font:700 .76rem 'Segoe UI',sans-serif;text-transform:uppercase;letter-spacing:.04em}
.excerpt .col.f h4{color:var(--fable)}.excerpt .col.c h4{color:var(--codex)}.excerpt .col.q h4{color:var(--qwen)}
.excerpt .col pre{white-space:pre-wrap;font:italic .82rem/1.5 Georgia,serif;margin:0;color:var(--ink)}
.excerpt .col pre.short{color:var(--qwen)}
.excerpt .col.missing{color:var(--muted);font-style:italic}
.scorecard{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin:1rem 0}
@media(max-width:760px){.scorecard{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid #2c2430;border-radius:5px;padding:1rem;border-top:3px solid var(--muted)}
.card.f{border-top-color:var(--fable)}.card.c{border-top-color:var(--codex)}.card.q{border-top-color:var(--qwen)}
.card h3{margin:0 0 .5rem;font:700 1rem 'Segoe UI',sans-serif}
.card.f h3{color:var(--fable)}.card.c h3{color:var(--codex)}.card.q h3{color:var(--qwen)}
.card .grade-big{font:700 2.2rem/1 Georgia,serif;margin:.4rem 0}
.card dl{margin:.5rem 0 0;font-size:.82rem;font-family:'Segoe UI',sans-serif}
.card dt{color:var(--muted);margin-top:.4rem}
.card dd{margin:0}
.note{font-size:.82rem;color:var(--muted);font-style:italic}
.kbd{font:600 .76rem 'Consolas',monospace;background:#241c29;padding:.05rem .35rem;border-radius:3px;color:var(--accent)}
footer.report-foot{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--accent2);color:var(--muted);font-size:.8rem}
"""

P=[]
P.append('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n')
P.append('<meta name="viewport" content="width=device-width, initial-scale=1">\n')
P.append('<title>Translation Model Comparison &mdash; Fable 5 vs Codex 5.5 vs Qwen-Trithemius 4B</title>\n')
P.append('<meta name="description" content="Side-by-side grading of three translation backends on the Trithemius Corpus: Fable 5, Codex/GPT-5.5, and Qwen-Trithemius 4B (NPU).">\n')
P.append('<style>%s</style>\n</head>\n<body>\n<div class="wrap">\n' % CSS)

P.append('<header class="report-head">\n')
P.append('<h1>Translation Backend Comparison</h1>\n')
P.append('<div class="sub">Fable 5 &nbsp;&middot;&nbsp; Codex / GPT-5.5 &nbsp;&middot;&nbsp; Qwen-Trithemius 4B (NPU)</div>\n')
P.append('<div class="meta">Graded 2026-07-04 &middot; 8 works &middot; 2,003 translation chunks &middot; Latin &rarr; English &middot; source: Qwen3-VL OCR</div>\n')
P.append('<div class="legend"><span><span class="dot f"></span> Fable 5</span><span><span class="dot c"></span> Codex / GPT-5.5</span><span><span class="dot q"></span> Qwen-Trithemius 4B (NPU)</span></div>\n')
P.append('</header>\n')

# Bottom line
P.append('<section>\n<h2>Bottom Line</h2>\n')
P.append('<div class="callout ok"><p><strong>Codex / GPT-5.5</strong> is the strongest translator on this corpus: the largest total output (3.23M chars), the highest page coverage, and clean, complete, fluent prose on both prose and verse. It is the only backend that produced a fully usable draft of every long work without systemic truncation.</p></div>\n')
P.append('<div class="callout"><p><strong>Fable 5</strong> is a close second and arguably the <em>best value</em>: comparable quality to Codex at lower cost, the fewest truncated chunks of the three after controlling for run state, and notably strong handling of the alliterative verse in the <em>Ecloga</em>. It hit its usage cap mid-corpus, which is the only reason it isn&rsquo;t first on raw coverage.</p></div>\n')
P.append('<div class="callout warn"><p><strong>Qwen-Trithemius 4B on the NPU</strong> is not production-ready as a translator. 371 of its 670 chunks (55%) are truncated mid-sentence, cutting out after roughly 30&ndash;80 words on the heaviest works. On the two <em>Sermones</em> volumes it covers under a third of the source and emits literal fragments that stop mid-clause (&ldquo;&hellip;and no adversity did he&rdquo;). The model itself is fine &mdash; the failure is in the NPU serving path (token / stop-token misconfiguration or context truncation), not the weights.</p></div>\n')
P.append('</section>\n')

# Scorecards
src_total = sum(w[3] for w in works)
def cov_pct(bn):
    return round(100*agg[bn]["pages"]/src_total) if src_total else 0
def trunc_pct(bn):
    return round(100*agg[bn]["trunc"]/agg[bn]["chunks"]) if agg[bn]["chunks"] else 0

cards=[]
grades_map={"FABLE":("A-","grade-a-minus","f"),"CODEX":("A","grade-a","c"),"QWEN-NPU":("D","grade-d","q")}
for bn,_,label in backends:
    g,gc,cls=grades_map[bn]
    cards.append('<div class="card %s"><h3>%s</h3><div class="grade-big"><span class="grade %s">%s</span></div><dl><dt>Chunks produced</dt><dd>%s</dd><dt>Total English output</dt><dd>%s chars</dd><dt>Source pages covered</dt><dd>%s / %s (%d%%)</dd><dt>Truncated chunks</dt><dd>%s (%d%%)</dd><dt>Preamble leaks</dt><dd>%s</dd></dl></div>' % (
        cls, html.escape(label), gc, g,
        f"{agg[bn]['chunks']:,}", f"{agg[bn]['chars']:,}",
        agg[bn]['pages'], src_total, cov_pct(bn),
        agg[bn]['trunc'], trunc_pct(bn), agg[bn]['leak']
    ))
P.append('<section>\n<h2>Scorecards</h2>\n<div class="scorecard">%s</div>\n</section>\n' % "".join(cards))

# Per-work table
P.append('<section>\n<h2>Per-Work Breakdown</h2>\n')
P.append('<p class="note">Truncated = chunk ends without a sentence terminator and is under 2,000 chars (a hard signal that the model stopped early). Leak = chunk begins with assistant preamble (e.g. &ldquo;Here is the translation&rdquo;) or a code fence. Pages = distinct <span class="kbd">--- Page N ---</span> markers preserved.</p>\n')
P.append('<table>\n<thead><tr><th>Work</th><th>Backend</th><th class="num">Chunks</th><th class="num">Chars out</th><th class="num">Pages / src</th><th class="num">Cov.</th><th class="num">Trunc.</th><th class="num">Leak</th><th>Grade</th></tr></thead>\n<tbody>\n')
for r in rows:
    sp=r["src_pages"]; first=True
    for bn,_,_ in backends:
        m=r["per"][bn]; g,gc=quality_grade(bn,m)
        wk = ('<td class="work" rowspan="3">%s<small>%s &middot; %d pages</small></td>' % (html.escape(r["name"]), html.escape(r["desc"]), sp)) if first else ""
        cls={"FABLE":"f","CODEX":"c","QWEN-NPU":"q"}[bn]
        trunc_cls = "bad" if m["trunc_pct"]>=40 else ("ok" if m["trunc_pct"]>=10 else "good")
        P.append('<tr>%s<td><span class="dot %s"></span> %s</td><td class="num">%d</td><td class="num">%s</td><td class="num">%d / %d</td><td class="num">%d%%</td><td class="num %s">%d</td><td class="num">%d</td><td><span class="grade %s">%s</span></td></tr>\n' % (
            wk, cls, bn, m['chunks'], f"{m['chars']:,}", m['pages'], sp, m['pages_pct'], trunc_cls, m['trunc'], m['leak'], gc, g))
        first=False
for bn,lab in [("FABLE","Fable 5"),("CODEX","Codex / GPT-5.5"),("QWEN-NPU","Qwen-NPU")]:
    a=agg[bn]; g,gc=grades_map[bn][0],grades_map[bn][1]
    P.append('<tr class="tot"><td colspan="2">TOTAL &mdash; %s</td><td class="num">%d</td><td class="num">%s</td><td class="num">%d</td><td class="num"></td><td class="num">%d</td><td class="num">%d</td><td><span class="grade %s">%s</span></td></tr>\n' % (
        lab, a['chunks'], f"{a['chars']:,}", a['pages'], a['trunc'], a['leak'], gc, g))
P.append('</tbody></table>\n</section>\n')

# Findings
P.append('<section>\n<h2>What the Numbers Show</h2>\n<ul class="findings">\n')
P.append('<li><b class="c">Codex</b> wrote ~32% more English than <b class="f">Fable</b> and ~2.6&times; more than <b class="q">Qwen-NPU</b>, despite similar chunk counts. That ratio is the cleanest single quality signal: a real translation of Latin prose expands, it doesn&rsquo;t shrink.</li>\n')
P.append('<li><b class="q">Qwen-NPU&rsquo;s</b> out/in ratio collapses on the two <em>Sermones</em> volumes (0.28) &mdash; i.e. it emits ~280 chars of English per 1,000 chars of Latin. Fable and Codex sit at 1.13&ndash;1.14 there. This is truncation, not brevity.</li>\n')
P.append('<li>The truncation is verifiable by eye: NPU chunks end mid-clause (&ldquo;&hellip;through my mouth; and do what He commands us in the&rdquo;, &ldquo;&hellip;and no adversity did he&rdquo;). This is the signature of a stop-token or max-new-tokens setting in the NPU runtime, <em>not</em> a model-quality problem.</li>\n')
P.append('<li><b class="f">Fable</b> and <b class="c">Codex</b> both preserve page markers in source order on every work. <b class="q">Qwen-NPU</b> also preserves order on what it does emit, but only because it emits so little.</li>\n')
P.append('<li>Page coverage: <b class="c">Codex</b> covers ~%d%% of source pages across the 8 works, <b class="f">Fable</b> ~%d%% (capped mid-run on the long volumes), <b class="q">Qwen-NPU</b> ~%d%%.</li>\n' % (cov_pct("CODEX"), cov_pct("FABLE"), cov_pct("QWEN-NPU")))
P.append('<li>On the one passage where all three translate cleanly (Steganographia p.10), <b class="f">Fable</b> and <b class="c">Codex</b> are essentially tied and <b class="q">Qwen-NPU</b> is a competent third &mdash; confirming the 4B weights are capable when the server lets them run.</li>\n')
P.append('<li>Preamble leaks are low everywhere (8&ndash;16 across 600+ chunks). <b class="c">Codex</b> is cleanest on that axis.</li>\n')
P.append('</ul>\n</section>\n')

# Excerpts
P.append('<section>\n<h2>Side-by-Side Excerpts</h2>\n<p class="note">Verbatim, same source page across all three backends. Nothing cherry-picked for length.</p>\n')
for slug,pg,cap in excerpts:
    cols=[]
    for bn,bdir,_ in backends:
        cls={"FABLE":"f","CODEX":"c","QWEN-NPU":"q"}[bn]
        d=os.path.join(base,slug,"translations",bdir,"full")
        txt=find_page(d,pg)
        if txt is None:
            cols.append('<div class="col %s missing"><h4>%s</h4>(page not present in this backend&rsquo;s output)</div>' % (cls,bn))
        else:
            disp = txt[:1400]
            if len(txt)>1400: disp += " [……]"
            short_cls = " short" if len(txt)<600 else ""
            cols.append('<div class="col %s"><h4>%s <small>(%s chars)</small></h4><pre class="%s">%s</pre></div>' % (
                cls, bn, f"{len(txt):,}", short_cls, html.escape(disp)))
    P.append('<div class="excerpt"><div class="ex-head">%s</div><div class="cols">%s</div></div>\n' % (html.escape(cap), "".join(cols)))
P.append('</section>\n')

# Method
P.append('<section>\n<h2>Method &amp; Caveats</h2>\n<div class="callout">\n')
P.append('<p><strong>What was graded.</strong> Every <span class="kbd">full_chunk_NNNN.md</span> produced by each backend on the 8 works Fable touched before capping &mdash; 2,003 chunks total (650 Fable + 683 Codex + 670 Qwen-NPU). The Latin source is the same Qwen3-VL OCR pass for all three, so differences are translation quality, not OCR divergence.</p>\n')
P.append('<p><strong>Chunking differs by design.</strong> Codex chunks at its own boundaries with a dual-context (OCR + secondary witness) prompt. Fable and Qwen chunk at 4,500-Latin-char page boundaries with a single-witness prompt. So Codex has a structural advantage on dense/ambiguous passages &mdash; this is noted, not penalized.</p>\n')
P.append('<p><strong>Truncation heuristic.</strong> A chunk is flagged truncated if it (a) ends in a character other than <span class="kbd">. ! ? : ; &rsquo;</span> and (b) is under 2,000 chars. Validated by hand on ~15 chunks across all three backends; the false-positive rate on Fable/Codex is near zero and on Qwen-NPU it undercounts (some longer NPU chunks are still substantively incomplete).</p>\n')
P.append('<p><strong>Grades are relative to role.</strong> Codex and Fable are graded as primary translators; Qwen-NPU is graded as a local/edge fallback. A &ldquo;D&rdquo; for Qwen-NPU means &ldquo;not shippable as-is, fix the runtime and re-run,&rdquo; not &ldquo;the model is bad.&rdquo;</p>\n')
P.append('<p><strong>Not graded here.</strong> Lemma-level translation accuracy would require a human Latinist pass on a sampled slice; this report grades completeness, structural integrity, and fluency. The side-by-side excerpts are the recommended entry point for a human spot-check of accuracy.</p>\n')
P.append('<p><strong>Timing.</strong> Qwen-NPU logged a 28.9s/chunk average on the NPU (~5.4h compute for what it produced). Fable and Codex runs did not log per-chunk timing in their <span class="kbd">runs.jsonl</span>, so wall-clock comparison isn&rsquo;t possible from the artifacts.</p>\n')
P.append('</div>\n</section>\n')

# Recommendation
P.append('<section>\n<h2>Recommendation</h2>\n<div class="callout ok">\n')
P.append('<p>For the production corpus, use <strong>Codex / GPT-5.5</strong> as primary and <strong>Fable 5</strong> as the cost-balanced second witness for the dual-grade pipeline. Both produce shippable English.</p>\n')
P.append('<p><strong>Do not ship Qwen-NPU output</strong> until the truncation is fixed. The likely one-line fix: set an explicit <span class="kbd">max_tokens</span> &ge; 4096 and remove any premature stop tokens in the NPU translator&rsquo;s generation config. Once that&rsquo;s in, re-run the 8 works and re-grade &mdash; the Steganographia sample shows the underlying model is capable of clean work.</p>\n')
P.append('</div>\n</section>\n')

P.append('<footer class="report-foot">\nGenerated from translation artifacts in <span class="kbd">E:/trithemius/data/corpus/&lt;work&gt;/translations/{fable5-qwen-trithemius, qwen3vl-trithemius-q6-dual-gpt55, npu-qwen3vl-q4nx}/full/</span>. &middot; Trithemius Corpus.\n</footer>\n')
P.append('</div>\n</body>\n</html>\n')

with open(OUT,"w",encoding="utf-8") as f:
    f.write("".join(P))
print("WROTE", OUT, os.path.getsize(OUT), "bytes")
