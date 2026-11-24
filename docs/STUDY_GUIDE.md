# Study guide: syntopical reading with books

Adler's *syntopical reading* means reading several works on one subject and constructing the debate among them. books automates the searching so you can spend time thinking.

## Weekly seminar workflow

1. **Build the shelf.** Put 5-10 sources on one subject in `library/` (add `.json` sidecars for author/year).
2. **Survey.** `python3 books.py topics --top 40`. Pick 3-5 topics that appear in several sources.
3. **Map the disagreement.** For each topic run `contrast "<topic>"`. Read the original passages around each `[p<id>]`, never rely on the excerpt alone.
4. **Name the assumptions.** For each source write one sentence: what must be true for this author's claim to hold? (A local model can draft; you verify.)
5. **Generate the brief.** `brief "<topic>" --out week3_topic.md`. Resolve every `CONDITIONAL` item by reading the source.
6. **Form your own question.** A master's-level contribution is a defensible position on the disagreement, in your own words and argument. The tool supplies evidence maps, not the thesis.
7. **Audit helpers.** Paste any AI-generated summary into a file and run `check` before trusting it.

## Seminar questions to ask of every topic

- Do the authors define the term the same way?
- Are they disagreeing about facts, causes, values, or scope?
- What evidence would each accept from the other?
- Which source is earliest; who is responding to whom?
- What does no source in my library address (a gap)?

## Citing

Passage ids (`[p12]`) are for working notes. Cite the original book and page in your own work using your required style (MLA, APA, Chicago); books does not record page numbers.
