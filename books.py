#!/usr/bin/env python3
"""
books - offline reading-seminar engine.

Ingests books/encyclopedias you supply (plain text/markdown), finds topics that recur
across them, contrasts what each source argues, and writes cited research briefs
at graduate-seminar level. Everything is local: SQLite + FTS5, stdlib only.
An optional local LLM (Ollama, default http://localhost:11434) adds synthesis;
without it, books falls back to extractive, fully cited output.

Output is always a RESEARCH BRIEF (positions, tensions, gaps, reading list), never a
submittable paper. Every claim carries a passage id that is verified against the index.

Usage:
  python books.py ingest ./library
  python books.py topics [--top 25]
  python books.py contrast "alienation"
  python books.py brief "alienation" [--out brief.md]
  python books.py check answer.txt        # audit any AI answer that cites [p<id>]
  python books.py watch ./library [--every 60]
Optional sidecar per file: name.json {"title","author","year","license","kind"}.
Env: BOOKS_DB, BOOKS_MODEL (e.g. llama3.2), BOOKS_LLM_URL.
"""
import argparse, hashlib, json, math, os, re, sqlite3, sys, time, urllib.request
from collections import Counter, defaultdict
from pathlib import Path

DB = Path(os.environ.get("BOOKS_DB", "books.db"))
MODEL = os.environ.get("BOOKS_MODEL", "")
LLM_URL = os.environ.get("BOOKS_LLM_URL", "http://localhost:11434/api/generate")
CHUNK_WORDS = 180

STOP = set("""a about above after again all also am an and any are as at be because been before being
below between both but by can could did do does doing down during each few for from further had has have
having he her here hers him his how i if in into is it its itself just me more most my no nor not now of
off on once only or other our out over own same she should so some such than that the their them then there
these they this those through to too under until up very was we were what when where which while who whom why
will with would you your one two may must upon thus yet said says also however shall""".split())
CONTRAST_CUES = re.compile(
    r"\b(however|whereas|argues?|claims?|contends?|maintains?|rejects?|denies|insists?|"
    r"critici[sz]es|in contrast|on the other hand|unlike|but|although|despite|challenges?)\b", re.I)

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs(id INTEGER PRIMARY KEY, path TEXT UNIQUE, sha TEXT, title TEXT,
  author TEXT, year TEXT, license TEXT, kind TEXT);
CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY, doc_id INTEGER, pos INTEGER, text TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(text, content='chunks', content_rowid='id');
"""

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con

# ---------------------------------------------------------------- ingest
def clean(text):
    m = re.search(r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", text, re.S)
    if m: text = text[m.end():]
    m = re.search(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG", text)
    if m: text = text[:m.start()]
    return text

def chunk(text):
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    out, cur, n = [], [], 0
    for p in filter(None, paras):
        w = len(p.split())
        if cur and n + w > CHUNK_WORDS:
            out.append(" ".join(cur)); cur, n = [], 0
        cur.append(p); n += w
    if cur: out.append(" ".join(cur))
    return out

def ingest_file(con, path):
    raw = path.read_bytes()
    sha = hashlib.sha1(raw).hexdigest()
    row = con.execute("SELECT id, sha FROM docs WHERE path=?", (str(path),)).fetchone()
    if row and row["sha"] == sha:
        return False
    meta = {}
    side = path.with_suffix(".json")
    if side.exists():
        meta = json.loads(side.read_text())
    if row:  # changed file: drop old chunks
        con.execute("DELETE FROM chunks WHERE doc_id=?", (row["id"],))
        con.execute("DELETE FROM docs WHERE id=?", (row["id"],))
    cur = con.execute(
        "INSERT INTO docs(path,sha,title,author,year,license,kind) VALUES(?,?,?,?,?,?,?)",
        (str(path), sha, meta.get("title", path.stem), meta.get("author", "unknown"),
         str(meta.get("year", "n.d.")), meta.get("license", "user-supplied"), meta.get("kind", "book")))
    doc_id = cur.lastrowid
    for i, c in enumerate(chunk(clean(raw.decode("utf-8", "ignore")))):
        con.execute("INSERT INTO chunks(doc_id,pos,text) VALUES(?,?,?)", (doc_id, i, c))
    con.execute("INSERT INTO fts(fts) VALUES('rebuild')")
    con.commit()
    return True

def cmd_ingest(folder):
    con = db()
    n = 0
    for p in sorted(Path(folder).rglob("*")):
        if p.suffix.lower() in (".txt", ".md") and ingest_file(con, p):
            print(f"  ingested {p.name}"); n += 1
    d = con.execute("SELECT count(*) c FROM docs").fetchone()["c"]
    k = con.execute("SELECT count(*) c FROM chunks").fetchone()["c"]
    print(f"{n} new/changed; library: {d} sources, {k} passages")

# ---------------------------------------------------------------- topics
def terms(text):
    words = re.findall(r"[a-z][a-z'-]{2,}", text.lower())
    for w in words:
        pass
    grams = []
    for i, w in enumerate(words):
        if w not in STOP: grams.append(w)
        if i + 1 < len(words) and w not in STOP and words[i + 1] not in STOP:
            grams.append(w + " " + words[i + 1])
    return grams

def discover_topics(con, top=25):
    docs = {r["id"]: r for r in con.execute("SELECT * FROM docs")}
    tf = defaultdict(Counter)
    for r in con.execute("SELECT doc_id, text FROM chunks"):
        tf[r["doc_id"]].update(terms(r["text"]))
    df = Counter()
    for c in tf.values(): df.update(c.keys())
    N = max(len(docs), 1)
    scored = []
    for term, d in df.items():
        if d < 2 and N > 1: continue
        counts = {i: tf[i][term] for i in tf if tf[i][term] >= 2}
        if len(counts) < min(2, N): continue
        idf = math.log(1 + N / d)
        s = sum(math.log(1 + c) for c in counts.values()) * idf * (1.4 if " " in term else 1.0)
        scored.append((s, term, counts))
    scored.sort(reverse=True)
    return [(t, [docs[i]["title"] for i in c], s) for s, t, c in scored[:top]]

def cmd_topics(top):
    con = db()
    rows = discover_topics(con, top)
    if not rows: print("No cross-source topics yet. Ingest at least two sources."); return
    for t, titles, s in rows:
        print(f"{t:<30} {s:5.1f}  in: {'; '.join(titles)}")

# ---------------------------------------------------------------- contrast
def fts_query(topic):
    toks = re.findall(r"\w+", topic.lower())
    return f'"{" ".join(toks)}"' if len(toks) > 1 else (toks[0] if toks else "")

def retrieve(con, topic, per_doc=2, limit=60):
    rows = []
    for q in (fts_query(topic), " OR ".join(re.findall(r"\w+", topic.lower()))):
        if not q: continue
        rows = con.execute(
            "SELECT c.id, c.doc_id, c.pos, c.text, d.title, d.author, d.year FROM fts "
            "JOIN chunks c ON c.id=fts.rowid JOIN docs d ON d.id=c.doc_id "
            "WHERE fts MATCH ? ORDER BY bm25(fts) LIMIT ?", (q, limit)).fetchall()
        if rows: break
    by = defaultdict(list)
    for r in rows:
        if len(by[r["doc_id"]]) < per_doc: by[r["doc_id"]].append(r)
    return by

def stance_sentences(text, k=2):
    sents = re.split(r"(?<=[.!?])\s+", text)
    cued = [s for s in sents if CONTRAST_CUES.search(s)]
    return (cued or sents)[:k]

def snippet(s, n=40):
    w = s.split()
    return " ".join(w[:n]) + (" ..." if len(w) > n else "")

def llm(prompt):
    if not MODEL: return None
    try:
        req = urllib.request.Request(LLM_URL, json.dumps(
            {"model": MODEL, "prompt": prompt, "stream": False}).encode(),
            {"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=300).read())["response"]
    except Exception as e:
        print(f"[local LLM unavailable: {e}; using extractive mode]", file=sys.stderr)
        return None

def verify_citations(text, valid_ids):
    cited = set(re.findall(r"\[p(\d+)\]", text))
    bad = sorted(c for c in cited if int(c) not in valid_ids)
    return cited, bad

def contrast(con, topic):
    by = retrieve(con, topic)
    if len(by) < 2:
        return None, by, set()
    valid = {r["id"] for rs in by.values() for r in rs}
    return by, by, valid

def cmd_contrast(topic):
    con = db()
    by, _, _ = contrast(con, topic)
    if by is None:
        print(f"'{topic}' appears in fewer than two sources; add more reading."); return
    for rs in by.values():
        r = rs[0]
        print(f"\n## {r['title']} ({r['author']}, {r['year']})")
        for x in rs:
            for s in stance_sentences(x["text"]):
                print(f"  [p{x['id']}] {snippet(s)}")

# ---------------------------------------------------------------- brief
def cmd_brief(topic, out=None):
    con = db()
    by, _, valid = contrast(con, topic)
    if by is None:
        print(f"'{topic}' appears in fewer than two sources; add more reading."); return
    sources = [rs[0] for rs in by.values()]
    ev = "\n".join(f"[p{x['id']}] ({x['title']}, {x['author']}) {snippet(x['text'], 120)}"
                   for rs in by.values() for x in rs)
    md = [f"# Research brief: {topic}", "",
          "_Status: research_brief_only. Reading aid for graduate seminar preparation; not a submittable paper._", "",
          "## 1. Positions by source"]
    for rs in by.values():
        r = rs[0]; md.append(f"**{r['title']}** ({r['author']}, {r['year']})")
        for x in rs:
            for s in stance_sentences(x["text"], 1):
                md.append(f"- {snippet(s)} [p{x['id']}]")
        md.append("")
    synth = llm(
        "You are a graduate seminar assistant. Using ONLY the passages below, write: (a) 3 points of "
        "disagreement between the sources, (b) the underlying assumption each source rests on, "
        "(c) 3 open research questions. Cite passages as [p<id>] after every claim. If a claim has no "
        f"passage, write 'unsupported'. Do not write an essay.\nTOPIC: {topic}\nPASSAGES:\n{ev}")
    md.append("## 2. Tensions, assumptions, open questions")
    if synth:
        cited, bad = verify_citations(synth, valid)
        md.append(synth.strip())
        md.append(f"\n_Gate: {len(cited)} citations checked; " +
                  (f"REJECT unresolved ids {bad}" if bad else "all resolved against index") + "._")
        verdict = "CONDITIONAL" if bad or not cited else "ALLOW"
    else:
        md.append("- Compare the passages above: where do sources assign different causes, "
                  "scope, or value to this topic? (Run with BOOKS_MODEL set for generated analysis.)")
        verdict = "CONDITIONAL"
    md += ["", "## 3. Reading list (from your library)"]
    md += [f"- {r['title']}, {r['author']} ({r['year']})" for r in sources]
    md += ["", f"**Gate verdict:** {verdict}  | sources compared: {len(sources)} | "
               f"passages cited: {len(valid)}"]
    text = "\n".join(md)
    if out: Path(out).write_text(text); print(f"wrote {out} (verdict {verdict})")
    else: print(text)

# ---------------------------------------------------------------- check
def content_words(s):
    return {w for w in re.findall(r"[a-z][a-z'-]{3,}", s.lower()) if w not in STOP}

def audit_answer(con, text):
    """Audit an AI answer: unresolved ids, uncited claims, weak lexical support."""
    report = {"unresolved": [], "uncited": [], "weak": [], "ok": 0}
    for sent in re.split(r"(?<=[.!?])\s+", text.strip()):
        ids = [int(i) for i in re.findall(r"\[p(\d+)\]", sent)]
        words = content_words(re.sub(r"\[p\d+\]", "", sent))
        if not ids:
            if len(sent.split()) > 8: report["uncited"].append(snippet(sent, 25))
            continue
        support = 0.0
        for i in ids:
            row = con.execute("SELECT text FROM chunks WHERE id=?", (i,)).fetchone()
            if not row: report["unresolved"].append(i); continue
            support = max(support, len(words & content_words(row["text"])) / max(len(words), 1))
        if support < 0.25: report["weak"].append((snippet(sent, 25), round(support, 2)))
        else: report["ok"] += 1
    bad = report["unresolved"] or report["uncited"] or report["weak"]
    report["verdict"] = "CONDITIONAL" if bad else "ALLOW"
    return report

def cmd_check(path):
    r = audit_answer(db(), Path(path).read_text())
    print(f"verified claims: {r['ok']}")
    for k, label in (("unresolved", "cites passage ids not in library"),
                     ("uncited", "claims with no citation"), ("weak", "citation barely matches claim")):
        for x in r[k]: print(f"  {label}: {x}")
    print(f"verdict: {r['verdict']}")
    return r

# ---------------------------------------------------------------- watch
def cmd_watch(folder, every):
    seen = set()
    print(f"watching {folder} every {every}s (Ctrl-C to stop)")
    while True:
        con = db()
        for p in sorted(Path(folder).rglob("*")):
            if p.suffix.lower() in (".txt", ".md"): ingest_file(con, p)
        for t, titles, s in discover_topics(con, 15):
            if t not in seen and len(titles) >= 2:
                seen.add(t); print(f"NEW TOPIC: {t}  ({'; '.join(titles)})")
        time.sleep(every)

def main():
    ap = argparse.ArgumentParser(prog="books")
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("ingest"); a.add_argument("folder")
    a = sp.add_parser("topics"); a.add_argument("--top", type=int, default=25)
    a = sp.add_parser("contrast"); a.add_argument("topic")
    a = sp.add_parser("brief"); a.add_argument("topic"); a.add_argument("--out")
    a = sp.add_parser("check"); a.add_argument("answer_file")
    a = sp.add_parser("watch"); a.add_argument("folder"); a.add_argument("--every", type=int, default=60)
    n = ap.parse_args()
    {"ingest": lambda: cmd_ingest(n.folder), "topics": lambda: cmd_topics(n.top),
     "contrast": lambda: cmd_contrast(n.topic), "brief": lambda: cmd_brief(n.topic, n.out),
     "check": lambda: cmd_check(n.answer_file),
     "watch": lambda: cmd_watch(n.folder, n.every)}[n.cmd]()

if __name__ == "__main__":
    main()
