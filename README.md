# books

An offline reading-seminar engine. Feed it books and encyclopedias; it finds topics that recur across them, contrasts what each author argues, and writes cited **research briefs** for graduate-level study. Citations are machine-checked, and the same checker can audit any AI answer.

- Pure Python 3 standard library (SQLite FTS5). No network, no API keys, no dependencies.
- Optional local LLM (Ollama) for deeper synthesis; works without one.
- Output is a study aid (positions, tensions, gaps, reading list), **not a submittable paper**.

## Quick start

```bash
python3 books.py ingest ./library          # index your texts
python3 books.py topics --top 25           # topics shared across sources
python3 books.py contrast "alienation"     # side-by-side positions, with passage ids
python3 books.py brief "alienation" --out brief.md
python3 books.py check answer.txt          # audit an AI answer's citations
python3 books.py watch ./library --every 60  # keep scanning as you add books
python3 tests/test_books.py                # run tests
```

## Commands

| Command | What it does |
|---|---|
| `ingest <folder>` | Reads `.txt`/`.md`, strips Project Gutenberg boilerplate, splits into ~180-word passages, indexes them. Re-ingests changed files only. |
| `topics` | Ranks unigrams/bigrams that recur in two or more sources (TF-IDF style). |
| `contrast <topic>` | Best passages per source, surfacing sentences with argumentative cues (argues, however, whereas...). Needs 2+ sources. |
| `brief <topic>` | Seminar-prep brief: positions by source, tensions/assumptions/open questions, reading list, gate verdict. |
| `check <file>` | Audits any text citing `[p<id>]`: unresolved ids, uncited claims, citations that barely match the claim. |
| `watch <folder>` | Polls a folder and announces new cross-book topics. |

Optional sidecar metadata: `mybook.json` next to `mybook.txt`:

```json
{"title": "The Division of Labor in Society", "author": "Durkheim", "year": "1893", "license": "public domain", "kind": "book"}
```

## Using a local LLM

```bash
ollama pull llama3.2
export BOOKS_MODEL=llama3.2            # optional: BOOKS_LLM_URL, BOOKS_DB
python3 books.py brief "anomie" --out brief.md
```

The model sees only retrieved passages, must cite `[p<id>]` after every claim, and every citation is verified against the index. Unresolved ids downgrade the verdict to `CONDITIONAL`. Without a model, `brief` stays extractive and also returns `CONDITIONAL` by design: it tells you the analysis still needs a reader.

## Verdicts

- `ALLOW`: every claim is cited, ids resolve, and wording overlaps its cited passage.
- `CONDITIONAL`: something needs fixing (see the report). Never treat unchecked output as established.

## Where to get texts

Project Gutenberg, Wikisource, Internet Archive public-domain scans, open-access scholarship, government documents, or books you own. Do not ingest material you have no right to copy.

## Responsible use

books is designed for **reading, comparing and preparing**, not for producing work to hand in as your own. Briefs are labelled `research_brief_only`. Check your institution's academic-integrity policy; see `docs/RESEARCH.md` for background.

## Docs

- `docs/STUDY_GUIDE.md`: a master's-level workflow using books.
- `docs/IMPROVING_AI_RESPONSES.md`: grounding, citation checking and prompt patterns.
- `docs/RESEARCH.md`: background research behind the design.

## Limitations

Topic discovery is lexical, not semantic. Contrast quality depends on corpus quality and size. Sentence-cue stance detection is a heuristic. Use a capable local model and 5+ sources per topic for good results.

## License

MIT
